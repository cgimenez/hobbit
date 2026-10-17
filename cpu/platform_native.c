/* Hote natif in-process (embed sim65) : miroir exact de web/smoke.mjs.
 *
 * Meme sequence, memes octets : slots depuis fichiers, hob_init, hob_boot,
 * puis par ligne (hors vides et #...) : flush, poussee des octets + 0x0D,
 * UN hob_run(0), drain du texte vers stdout, diagnostics vers stderr.
 * Les sorties stdout des deux cotes doivent etre byte-identiques
 * (scripts/host_diff.py).
 *
 * Usage : hobplay [cmdfile]   (sans cmdfile : stdin)
 *   Les chemins d'images sont relatifs a la racine du repo (CWD attendu).
 *
 * Compilé par cpu/Makefile (cc du systeme, -O2) avec les sources host
 * et tools/cc65/src/sim65 (6502, memory, peripherals, error, trace) :
 * le MEME code source que le WASM, autre compilateur.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hobbit.h"
#include "platform.h"

#define LINE_CAP 8192

static int load_slot(const char *path, int slot)
{
    FILE *f = fopen(path, "rb");
    uint8_t *p;
    int cap, n;
    if (!f) {
        fprintf(stderr, "hobplay: illisible %s (lancer `make -C web shims` ?)\n", path);
        return -1;
    }
    p = hob_slot(slot);
    cap = hob_slot_cap(slot);
    n = (int)fread(p, 1, (size_t)cap, f);
    fclose(f);
    hob_slot_len(slot, n);
    return 0;
}

static int text_len = 0;

static void drain(void)
{
    int len = hob_text_len();
    if (len > text_len) {
        fwrite(hob_text_ptr() + text_len, 1, (size_t)(len - text_len), stdout);
        fflush(stdout);
        text_len = len;
    }
}

/* rstrip " \t\r\n" sur place ; rend 0 si ligne vide ou commentaire. */
static int clean(char *s)
{
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t' ||
                     s[n - 1] == '\r' || s[n - 1] == '\n')) {
        s[--n] = '\0';
    }
    return n > 0 && s[0] != '#';
}

static void push_line(const char *s)
{
    const unsigned char *p = (const unsigned char *)s;
    hob_key_flush();
    while (*p) {
        hob_key(*p++);
    }
    hob_key(0x0d);
}

static int find_obj(int key)
{
    int i, n = hob_obj_count();
    for (i = 0; i < n; i++) {
        if (hob_obj_key(i) == key) {
            return i;
        }
    }
    return -1;
}

/* Etat porte rouge ($08) + butler ($42) + entites VM + events. */
static void dump_state(void)
{
    int i08 = find_obj(0x08), i42 = find_obj(0x42), i0f = find_obj(0x0f);
    int e, first = 1;
    fprintf(stderr, "  STATE door08=$%02x butler42=",
            i08 >= 0 ? hob_obj_field(i08, HOB_F_FLAGS) : -1);
    if (i42 >= 0) {
        fprintf(stderr, "flags=$%02x eloc=$%02x alive=%d",
                hob_obj_field(i42, HOB_F_FLAGS),
                hob_obj_field(i42, HOB_F_ELOC), hob_obj_alive(i42));
    } else {
        fprintf(stderr, "absent");
    }
    fprintf(stderr, " key0f_carr=%d ent=",
            i0f >= 0 ? hob_obj_carrier(i0f) : -2);
    for (e = 0; e < hob_ent_count(); e++) {
        int id = hob_ent_id(e);
        fprintf(stderr, "%se%d:%02x:$%x", first ? "" : " ", e, id,
                hob_ent_pc(e));
        first = 0;
    }
    fprintf(stderr, " evt=");
    for (e = 0; e < hob_evt_count(); e++) {
        fprintf(stderr, "%s%d", e ? "," : "", hob_evt_cpt(e));
    }
    fprintf(stderr, "\n");
}

int main(int argc, char **argv)
{
    FILE *in = stdin;
    char line[LINE_CAP];
    int rc, r, stalled = 0, dostate = 0, ai;
    const char *cmdfile = NULL;

    for (ai = 1; ai < argc; ai++) {
        if (!strcmp(argv[ai], "--state")) {
            dostate = 1;
        } else if (!strcmp(argv[ai], "--help")) {
            fprintf(stderr, "usage: hobplay [--state] [cmdfile]\n");
            return PLATFORM_OK;
        } else if (!cmdfile) {
            cmdfile = argv[ai];
        } else {
            fprintf(stderr, "usage: hobplay [--state] [cmdfile]\n");
            return PLATFORM_USAGE;
        }
    }
    if (cmdfile) {
        in = fopen(cmdfile, "rb");
        if (!in) {
            fprintf(stderr, "hobplay: illisible %s\n", cmdfile);
            return PLATFORM_IO_ERR;
        }
    }
    if (load_slot("data/hobbit.bin", 0) || load_slot("data/basic10.rom", 1) ||
        load_slot("web/build/shim.bin", 2) || load_slot("web/build/snap.bin", 3)) {
        return PLATFORM_IO_ERR;
    }
    hob_slot_len(4, 0);

    rc = hob_init();
    if (rc != 0) {
        fprintf(stderr, "hob_init = %d\n", rc);
        return PLATFORM_INIT_ERR;
    }
    rc = hob_boot();
    drain();
    fprintf(stderr, "\n[boot rc=%d texte=%d lieu=$%x]\n",
            rc, hob_text_len(), hob_player_room());

    while (fgets(line, sizeof line, in)) {
        if (!clean(line)) {
            continue;
        }
        push_line(line);
        r = hob_run(0);
        if (r == 1) {
            stalled = 1;
            fprintf(stderr, "  STALL pc=$%x autokey=%lu shim=%lu kb7353=%lu\n",
                    hob_last_pc(), hob_autokey_count(),
                    hob_shim_count(), hob_kb7353_count());
        }
        drain();
        fprintf(stderr, "[%s rc=%d lieu=$%x objs=%d rooms=%d]\n",
                line, r, hob_player_room(),
                hob_obj_count(), hob_room_count());
        if (dostate) {
            dump_state();
        }
    }
    if (in != stdin) {
        fclose(in);
    }
    return stalled ? PLATFORM_STALL : PLATFORM_OK;
}
