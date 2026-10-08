/* tickdiff : pilote sim65 tick par tick et log les diffs memoire.
 *
 * Un processus sim65 est garde vivant (pipes stdin/stdout). Les ordres
 * arrivent un par un (fichier de commandes ou stdin interactif) ; apres
 * chaque ordre, on attend le silence (fin de tick : prompt, plus de
 * frames/dumps) puis on snapshotte les 4 regions SAVE via les marqueurs
 * @@MEM du shim et on diffe contre le tick precedent.
 *
 * Usage : tickdiff [-t timeout_ms] [-o dir] simfile [cmdfile]
 *   sans cmdfile : interactif (ordres tapes au clavier, un par ligne).
 * Sorties dans dir (defaut build/sim/ticks) :
 *   ticks.log   : TICK n cmd="..." + lignes "  $BASE +$OFF: $AV->$AP"
 *   snapNNNN.bin : snapshot brut des 4 regions (ordre fixe, tailles fixes)
 *
 * Ne logue que les deltas (octets changes). Les frames texte/hires sont
 * parsees-et-jetees (servent juste a detecter l'activite).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/select.h>
#include <sys/wait.h>

#define NREG 4
static const unsigned REG_BASE[NREG] = {0x00BE, 0x1B1A, 0x28CC, 0x211A};
static const unsigned REG_LEN[NREG]  = {0x0018, 0x0556, 0x02F1, 0x05C8};

#define OUT_CHUNK 65536

typedef struct {
    unsigned char *data;
    size_t len, cap;
    size_t pos;          /* curseur de parse */
} Stream;

static void stream_push(Stream *s, const unsigned char *b, size_t n) {
    if (s->len + n > s->cap) {
        s->cap = (s->len + n) * 2 + OUT_CHUNK;
        s->data = realloc(s->data, s->cap);
        if (!s->data) { perror("realloc"); exit(1); }
    }
    memcpy(s->data + s->len, b, n);
    s->len += n;
}

/* compacte le prefixe consomme */
static void stream_compact(Stream *s) {
    if (s->pos == 0) return;
    memmove(s->data, s->data + s->pos, s->len - s->pos);
    s->len -= s->pos;
    s->pos = 0;
}

static int start_hex4(const unsigned char *p, unsigned *v) {
    unsigned r = 0;
    for (int i = 0; i < 4; i++) {
        unsigned char c = p[i];
        r <<= 4;
        if (c >= '0' && c <= '9') r |= c - '0';
        else if (c >= 'A' && c <= 'F') r |= c - 'A' + 10;
        else if (c >= 'a' && c <= 'f') r |= c - 'a' + 10;
        else return 0;
    }
    *v = r;
    return 1;
}

static int reg_index(unsigned base) {
    for (int i = 0; i < NREG; i++)
        if (REG_BASE[i] == base) return i;
    return -1;
}

/* etat partage (evite les fonctions imbriquees, non portables) */
static Stream G_s = {0};
static unsigned char G_buf[OUT_CHUNK];
static unsigned char *G_cur[NREG] = {0};
static long G_frames = 0;
static int G_rfd = -1;
static long G_timeout_ms = 300;

/* lit jusqu'au silence (fin de tick) ; rend 0 si l'enfant est parti */
static int wait_quiet(void) {
    for (;;) {
        fd_set rf;
        FD_ZERO(&rf);
        FD_SET(G_rfd, &rf);
        struct timeval tv = { G_timeout_ms / 1000, (G_timeout_ms % 1000) * 1000 };
        int r = select(G_rfd + 1, &rf, 0, 0, &tv);
        if (r < 0) { if (errno == EINTR) continue; perror("select"); return 0; }
        if (r == 0) return 1;  /* silence -> tick fini */
        ssize_t n = read(G_rfd, G_buf, sizeof G_buf);
        if (n <= 0) return 0;  /* EOF / enfant parti */
        stream_push(&G_s, G_buf, (size_t)n);
        for (;;) {
            size_t avail = G_s.len - G_s.pos;
            if (avail == 0) break;  /* tout consomme (sans ca, avail
                                       underflow en size_t -> OOB) */
            unsigned char *p = G_s.data + G_s.pos;
            if (avail >= 13 && !memcmp(p, "@@FRAME text\n", 13)) {
                if (avail < 13 + 1120) break;
                G_s.pos += 13 + 1120; G_frames++;
            } else if (avail >= 14 && !memcmp(p, "@@FRAME hires\n", 14)) {
                if (avail < 14 + 8192) break;
                G_s.pos += 14 + 8192; G_frames++;
            } else if (avail >= 16 && !memcmp(p, "@@MEM ", 6)) {
                unsigned a, ln;
                if (p[10] != ' ' || p[15] != '\n' ||
                    !start_hex4(p + 6, &a) || !start_hex4(p + 11, &ln))
                    { G_s.pos++; continue; }  /* faux-positif : avance */
                if (avail < 16u + ln) break;
                int ri = reg_index(a);
                if (ri >= 0 && ln == REG_LEN[ri])
                    memcpy(G_cur[ri], p + 16, ln);
                G_s.pos += 16 + ln;
            } else if (avail >= 13 && !memcmp(p, "@@TAPE-BLOCK\n", 13)) {
                G_s.pos += 13;
            } else if (avail >= 12 && !memcmp(p, "@@TAPE-BYTE\n", 12)) {
                if (avail < 13) break;
                G_s.pos += 13;
            } else {
                G_s.pos++;
            }
        }
        stream_compact(&G_s);
    }
}

int main(int argc, char **argv) {
    long timeout_ms = 300;
    const char *outdir = "build/sim/ticks";
    const char *simfile = NULL, *cmdfile = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-t") && i + 1 < argc) timeout_ms = atol(argv[++i]);
        else if (!strcmp(argv[i], "-o") && i + 1 < argc) outdir = argv[++i];
        else if (!simfile) simfile = argv[i];
        else if (!cmdfile) cmdfile = argv[i];
        else { fprintf(stderr, "arg inattendu : %s\n", argv[i]); return 1; }
    }
    if (!simfile) {
        fprintf(stderr, "usage : tickdiff [-t ms] [-o dir] simfile [cmdfile]\n");
        return 1;
    }
    char mk[1024];
    snprintf(mk, sizeof mk, "mkdir -p %s", outdir);
    if (system(mk) != 0) { fprintf(stderr, "mkdir %s impossible\n", outdir); return 1; }
    char logpath[1024];
    snprintf(logpath, sizeof logpath, "%s/ticks.log", outdir);
    FILE *log = fopen(logpath, "w");
    if (!log) { perror("fopen log"); return 1; }

    FILE *cmdf = NULL;
    if (cmdfile) {
        cmdf = fopen(cmdfile, "r");
        if (!cmdf) { perror("fopen cmdfile"); return 1; }
    }

    int to_child[2], from_child[2];
    if (pipe(to_child) || pipe(from_child)) { perror("pipe"); return 1; }
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 1; }
    if (pid == 0) {
        dup2(to_child[0], 0);
        dup2(from_child[1], 1);
        close(to_child[0]); close(to_child[1]);
        close(from_child[0]); close(from_child[1]);
        execl("tools/cc65/bin/sim65", "sim65", "-x", "2000000000",
              simfile, (char *)0);
        perror("execl sim65");
        _exit(127);
    }
    close(to_child[0]);
    close(from_child[1]);
    int wfd = to_child[1], rfd = from_child[0];
    fcntl(rfd, F_SETFL, O_NONBLOCK);

    /* snapshots : prev + cur, 4 regions */
    unsigned char *snap_prev[NREG] = {0};
    for (int i = 0; i < NREG; i++) {
        snap_prev[i] = calloc(1, REG_LEN[i]);
        G_cur[i] = calloc(1, REG_LEN[i]);
    }
    G_rfd = rfd;
    G_timeout_ms = timeout_ms;
    long ticks = 0;

    /* tick 0 : etat boot (avant tout ordre) */
    int alive = wait_quiet();
    {
        char sp[1024];
        snprintf(sp, sizeof sp, "%s/snap0000.bin", outdir);
        FILE *f = fopen(sp, "wb");
        for (int i = 0; i < NREG; i++) fwrite(G_cur[i], 1, REG_LEN[i], f);
        fclose(f);
        fprintf(log, "TICK 0 BOOT (frames=%ld, snapshot snap0000.bin)\n", G_frames);
        fflush(log);
        for (int i = 0; i < NREG; i++) memcpy(snap_prev[i], G_cur[i], REG_LEN[i]);
        ticks = 1;
    }

    char *line = NULL;
    size_t ll = 0;
    FILE *in = cmdf ? cmdf : stdin;
    if (!cmdf)
        fprintf(stderr, "tickdiff interactif : tapez les ordres (Ctrl-D pour finir)\n");
    while (alive) {
        ssize_t n;
        if (cmdf) {
            n = getline(&line, &ll, in);
            if (n < 0) break;
        } else {
            fprintf(stderr, "> ");
            fflush(stderr);
            n = getline(&line, &ll, in);
            if (n < 0) { fprintf(stderr, "\nfin\n"); break; }
        }
        /* envoie l'ordre tel quel au jeu (la ligne inclut \n -> touche CR ?
           le shim lit des octets bruts : on convertit \n final en \r) */
        char *send = line;
        size_t sn = (size_t)n;
        if (sn > 0 && send[sn - 1] == '\n') send[sn - 1] = '\r';
        size_t off = 0;
        while (off < sn) {
            ssize_t w = write(wfd, send + off, sn - off);
            if (w <= 0) { alive = 0; break; }
            off += (size_t)w;
        }
        if (!alive) break;
        /* logue la commande sans le CR */
        char cmd[256];
        snprintf(cmd, sizeof cmd, "%.*s", (int)(sn > 0 ? sn - 1 : 0), send);
        alive = wait_quiet();
        /* snapshot + diff */
        char sp[1024];
        snprintf(sp, sizeof sp, "%s/snap%04ld.bin", outdir, ticks);
        FILE *f = fopen(sp, "wb");
        for (int i = 0; i < NREG; i++) fwrite(G_cur[i], 1, REG_LEN[i], f);
        fclose(f);
        long ndiff = 0;
        fprintf(log, "TICK %ld cmd=\"%s\" (frames=%ld)\n", ticks, cmd, G_frames);
        for (int i = 0; i < NREG; i++) {
            for (unsigned j = 0; j < REG_LEN[i]; j++) {
                if (snap_prev[i][j] != G_cur[i][j]) {
                    fprintf(log, "  $%04X +$%04X: $%02X->$%02X\n",
                            REG_BASE[i], j, snap_prev[i][j], G_cur[i][j]);
                    ndiff++;
                }
            }
            memcpy(snap_prev[i], G_cur[i], REG_LEN[i]);
        }
        if (ndiff == 0) fprintf(log, "  (aucun changement)\n");
        fflush(log);
        fprintf(stderr, "tick %ld cmd=\"%s\" : %ld octets changes\n", ticks, cmd, ndiff);
        ticks++;
    }
    free(line);
    close(wfd);
    /* laisse l'enfant finir, draine le reste */
    {
        ssize_t n;
        do { n = read(rfd, G_buf, sizeof G_buf); } while (n > 0);
    }
    int st = 0;
    waitpid(pid, &st, 0);
    fprintf(log, "FIN (%ld ticks)\n", ticks);
    fclose(log);
    fprintf(stderr, "log : %s (%ld ticks)\n", logpath, ticks);
    return 0;
}
