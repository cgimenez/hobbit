/* tickdiff : pilote sim65 tick par tick et stocke en SQLite.
 *
 * Un processus sim65 est garde vivant (pipes stdin/stdout). Les ordres
 * arrivent un par un (fichier de commandes ou stdin interactif) ; apres
 * chaque ordre, on attend le silence (fin de tick : prompt, plus de
 * frames/dumps) puis on snapshotte les 4 regions SAVE via les marqueurs
 * @@MEM du shim et on diffe contre le tick precedent.
 *
 * Usage : tickdiff [-t timeout_ms] --db base.db --name RUN simfile [cmdfile]
 *   sans cmdfile : interactif (ordres tapes au clavier, un par ligne).
 * Sortie : DB SQLite (runs/ticks/deltas/state, voir scripts/tickdb.py).
 *   Rejouer le meme --name ecrase le run precedent (DELETE + re-INSERT).
 *
 * Ne stocke que les deltas (octets changes) + l'etat ZP par tick.
 * Les frames texte/hires sont parsees-et-jetees (servent juste
 * a detecter l'activite).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <time.h>
#include <sqlite3.h>

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
static int G_seen[NREG] = {0};   /* 1 = au moins un dump recu */
static long G_frames = 0;
static int G_rfd = -1;
static long G_timeout_ms = 300;
static long G_settle_ms = 0;   /* delai de tassement apres le silence (-s) */

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
                if (ri >= 0 && ln == REG_LEN[ri]) {
                    memcpy(G_cur[ri], p + 16, ln);
                    G_seen[ri] = 1;
                }
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
    const char *dbpath = NULL, *runname = NULL;
    const char *simfile = NULL, *cmdfile = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-t") && i + 1 < argc) timeout_ms = atol(argv[++i]);
        else if (!strcmp(argv[i], "-s") && i + 1 < argc) G_settle_ms = atol(argv[++i]);
        else if (!strcmp(argv[i], "--db") && i + 1 < argc) dbpath = argv[++i];
        else if (!strcmp(argv[i], "--name") && i + 1 < argc) runname = argv[++i];
        else if (!simfile) simfile = argv[i];
        else if (!cmdfile) cmdfile = argv[i];
        else { fprintf(stderr, "arg inattendu : %s\n", argv[i]); return 1; }
    }
    if (!simfile || !dbpath || !runname) {
        fprintf(stderr, "usage : tickdiff [-t ms] --db base.db --name RUN simfile [cmdfile]\n");
        return 1;
    }
    sqlite3 *db = NULL;
    if (sqlite3_open(dbpath, &db) != SQLITE_OK) {
        fprintf(stderr, "sqlite open %s: %s\n", dbpath, sqlite3_errmsg(db));
        return 1;
    }
    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", 0, 0, 0);
    const char *schema =
        "CREATE TABLE IF NOT EXISTS runs(run_id INTEGER PRIMARY KEY,"
        " name TEXT UNIQUE, image TEXT, cmdfile TEXT, started TEXT);"
        "CREATE TABLE IF NOT EXISTS ticks(run_id INTEGER, n INTEGER,"
        " cmd TEXT, frames INTEGER, PRIMARY KEY(run_id, n));"
        "CREATE TABLE IF NOT EXISTS deltas(run_id INTEGER, n INTEGER,"
        " base INTEGER, off INTEGER, avant INTEGER, apres INTEGER,"
        " PRIMARY KEY(run_id, n, base, off)) WITHOUT ROWID;"
        "CREATE INDEX IF NOT EXISTS idx_deltas_addr"
        " ON deltas(base, off, run_id, n);"
        "CREATE TABLE IF NOT EXISTS texts(run_id INTEGER, n INTEGER,"
        " reponse TEXT, PRIMARY KEY(run_id, n));"
        "CREATE TABLE IF NOT EXISTS state(run_id INTEGER, n INTEGER,"
        " ploc INTEGER, eloc INTEGER, obj INTEGER, crec INTEGER,"
        " PRIMARY KEY(run_id, n));";
    if (sqlite3_exec(db, schema, 0, 0, 0) != SQLITE_OK) {
        fprintf(stderr, "sqlite schema: %s\n", sqlite3_errmsg(db));
        return 1;
    }
    sqlite3_exec(db, "BEGIN;", 0, 0, 0);
    sqlite3_stmt *st_run = NULL, *st_tick = NULL, *st_delta = NULL,
                 *st_state = NULL;
    sqlite3_prepare_v2(db, "INSERT INTO runs(name) VALUES(?)"
                       " ON CONFLICT(name) DO NOTHING"
                       " RETURNING run_id;", -1, &st_run, 0);
    sqlite3_bind_text(st_run, 1, runname, -1, SQLITE_STATIC);
    long run_id = -1;
    if (sqlite3_step(st_run) == SQLITE_ROW)
        run_id = sqlite3_column_int64(st_run, 0);
    sqlite3_finalize(st_run);
    if (run_id < 0) { /* existait deja : le reutilise */
        sqlite3_prepare_v2(db, "SELECT run_id FROM runs WHERE name=?;",
                           -1, &st_run, 0);
        sqlite3_bind_text(st_run, 1, runname, -1, SQLITE_STATIC);
        if (sqlite3_step(st_run) == SQLITE_ROW)
            run_id = sqlite3_column_int64(st_run, 0);
        sqlite3_finalize(st_run);
    }
    if (run_id < 0) { fprintf(stderr, "run_id impossible\n"); return 1; }
    /* rejouer le meme nom = ecrase (frais, idempotent) */
    sqlite3_prepare_v2(db, "DELETE FROM deltas WHERE run_id=?;",
                       -1, &st_delta, 0);
    sqlite3_bind_int64(st_delta, 1, run_id);
    sqlite3_step(st_delta);
    sqlite3_finalize(st_delta);
    const char *tables[] = {"ticks", "state", "texts"};
    for (int k = 0; k < 3; k++) {
        char q[128];
        snprintf(q, sizeof q, "DELETE FROM %s WHERE run_id=?;", tables[k]);
        sqlite3_prepare_v2(db, q, -1, &st_delta, 0);
        sqlite3_bind_int64(st_delta, 1, run_id);
        sqlite3_step(st_delta);
        sqlite3_finalize(st_delta);
    }
    sqlite3_prepare_v2(db, "INSERT INTO ticks VALUES(?,?,?,?);",
                       -1, &st_tick, 0);
    sqlite3_prepare_v2(db, "INSERT INTO deltas VALUES(?,?,?,?,?,?);",
                       -1, &st_delta, 0);
    sqlite3_prepare_v2(db, "INSERT INTO state VALUES(?,?,?,?,?,?);",
                       -1, &st_state, 0);

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

    /* tick 0 : envoie le 1er ordre (touche boot = 1re ligne, vide en
       general) PUIS attend que les 4 regions aient dumpe. Sans l'ordre
       d'abord, pas de frame donc pas de dumps -> deadlock. */
    char *line = NULL;
    size_t ll = 0;
    FILE *in = cmdf ? cmdf : stdin;
    if (!cmdf)
        fprintf(stderr, "tickdiff interactif : tapez les ordres (Ctrl-D pour finir)\n"
                        "  (1re ligne = touche boot)\n");
    ssize_t n0 = getline(&line, &ll, in);
    if (n0 < 0) { fprintf(stderr, "aucun ordre\n"); return 1; }
    {
        char *send = line;
        size_t sn = (size_t)n0;
        if (sn > 0 && send[sn - 1] == '\n') send[sn - 1] = '\r';
        size_t off = 0;
        while (off < sn) {
            ssize_t w = write(wfd, send + off, sn - off);
            if (w <= 0) { fprintf(stderr, "sim65 parti\n"); return 1; }
            off += (size_t)w;
        }
    }
    int alive = 0;
    {
        int all, guard = 0;
        do {
            alive = wait_quiet();
            all = 1;
            for (int i = 0; i < NREG; i++) all &= G_seen[i];
            guard++;
        } while (alive && !all && guard < 3000);
        if (!all) fprintf(stderr, "avertissement : dumps incomplets (baseline partielle)\n");
    }
    if (!alive) {
        fprintf(stderr, "sim65 parti avant le premier dump complet\n");
        return 1;
    }
    /* etat ZP du boot (snap implicite : G_cur) */
    sqlite3_bind_int64(st_tick, 1, run_id);
    sqlite3_bind_int64(st_tick, 2, 0);
    sqlite3_bind_text(st_tick, 3, "", -1, SQLITE_STATIC);
    sqlite3_bind_int64(st_tick, 4, G_frames);
    sqlite3_step(st_tick);
    sqlite3_reset(st_tick);
    sqlite3_bind_int64(st_state, 1, run_id);
    sqlite3_bind_int64(st_state, 2, 0);
    sqlite3_bind_int64(st_state, 3, G_cur[0][0x0A]);
    sqlite3_bind_int64(st_state, 4, G_cur[0][0x0B]);
    sqlite3_bind_int64(st_state, 5, G_cur[0][0x07]);
    sqlite3_bind_int64(st_state, 6, G_cur[0][0x08] | (G_cur[0][0x09] << 8));
    sqlite3_step(st_state);
    sqlite3_reset(st_state);
    fprintf(stderr, "BOOT (frames=%ld)\n", G_frames);
    for (int i = 0; i < NREG; i++) memcpy(snap_prev[i], G_cur[i], REG_LEN[i]);
    ticks = 1;

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
        if (alive && G_settle_ms > 0) {
            /* tassement : sim65 emet par rafales, le 1er silence peut
               preceder la fin de pagination (pause_key mangerait l'ordre) */
            struct timespec ts = { G_settle_ms / 1000,
                                   (G_settle_ms % 1000) * 1000000L };
            nanosleep(&ts, 0);
            alive = wait_quiet();
        }
        /* ticks + deltas + etat ZP */
        sqlite3_bind_int64(st_tick, 1, run_id);
        sqlite3_bind_int64(st_tick, 2, ticks);
        sqlite3_bind_text(st_tick, 3, cmd, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(st_tick, 4, G_frames);
        sqlite3_step(st_tick);
        sqlite3_reset(st_tick);
        long ndiff = 0;
        for (int i = 0; i < NREG; i++) {
            for (unsigned j = 0; j < REG_LEN[i]; j++) {
                if (snap_prev[i][j] != G_cur[i][j]) {
                    sqlite3_bind_int64(st_delta, 1, run_id);
                    sqlite3_bind_int64(st_delta, 2, ticks);
                    sqlite3_bind_int64(st_delta, 3, REG_BASE[i]);
                    sqlite3_bind_int64(st_delta, 4, j);
                    sqlite3_bind_int64(st_delta, 5, snap_prev[i][j]);
                    sqlite3_bind_int64(st_delta, 6, G_cur[i][j]);
                    sqlite3_step(st_delta);
                    sqlite3_reset(st_delta);
                    ndiff++;
                }
            }
            memcpy(snap_prev[i], G_cur[i], REG_LEN[i]);
        }
        sqlite3_bind_int64(st_state, 1, run_id);
        sqlite3_bind_int64(st_state, 2, ticks);
        sqlite3_bind_int64(st_state, 3, G_cur[0][0x0A]);
        sqlite3_bind_int64(st_state, 4, G_cur[0][0x0B]);
        sqlite3_bind_int64(st_state, 5, G_cur[0][0x07]);
        sqlite3_bind_int64(st_state, 6, G_cur[0][0x08] | (G_cur[0][0x09] << 8));
        sqlite3_step(st_state);
        sqlite3_reset(st_state);
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
    sqlite3_exec(db, "COMMIT;", 0, 0, 0);
    sqlite3_finalize(st_tick);
    sqlite3_finalize(st_delta);
    sqlite3_finalize(st_state);
    sqlite3_close(db);
    fprintf(stderr, "db : %s run=%s (%ld ticks)\n", dbpath, runname, ticks);
    return 0;
}
