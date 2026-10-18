/* Entrees/sorties du shim solveur -> texte + blob SAVE (port de sim_play.py).
 *
 * Le shim (src/6502/shim.s -D SOLVER) emet sur PVWrite :
 *   "@@A"+octet   caractere final rendu ('+' = curseur, 0x08 = backspace)
 *   "@@EOL\n"     scroll mode texte (6 o)
 *   "@@EOLR\n"    scroll mode RAW = fin de ligne de commande (7 o)
 *   "@@P\n"       prompt '>' = fin de tour (4 o)
 *   "@@K"+octet   octet clavier consomme (diagnostic)
 *   "@@SNAP\n"    SAVE/LOAD : NLEN(1)+NOM+IDX(1)+LEN(2)+payload
 */

#include "io.h"

#include <string.h>

#define RAW_CAP  (1u << 20)
#define TXT_CAP  (1u << 20)
#define KEY_CAP  16384  /* >= LINE_CAP (8192) : pire cas 8191 + CR tient
                         * (anneau : capacite utile CAP-1) */

#define SAVE_HDR 8   /* "@@SNAP\n" + NLEN */
/* Blob SAVE = "SNAP" + 4 regions (ordre REGTAB snap.s). */
static const unsigned REGION_LEN[4] = { 0x0018, 0x0556, 0x02F1, 0x05C8 };
#define BLOB_LEN (4 + 0x0018 + 0x0556 + 0x02F1 + 0x05C8)

static uint8_t  raw[RAW_CAP];
static unsigned rawlen, rawpos;

static uint8_t  txt[TXT_CAP];
static unsigned txtlen;

static uint8_t  keyq[KEY_CAP];
static unsigned khead, ktail;

static uint8_t  blob[BLOB_LEN];
static int      blob_got[4];
static int      blob_ready;
static int      blob_len;

static int      prompt_flag;
static unsigned keys_consumed;   /* @@K vus depuis io_clear_prompt() */
static unsigned long dropped;    /* octets perdus (raw/txt/cles pleins) */

void io_reset(void)
{
    rawlen = rawpos = 0;
    txtlen = 0;
    khead = ktail = 0;
    memset(blob, 0, sizeof blob);
    memset(blob_got, 0, sizeof blob_got);
    blob_ready = 0;
    blob_len = 0;
    prompt_flag = 0;
    keys_consumed = 0;
    dropped = 0;
}

static void emit(uint8_t c)
{
    if (txtlen < TXT_CAP) {
        txt[txtlen++] = c;
    } else {
        dropped++;
    }
}

/* Prefixe strict d'un marqueur : "@@A"+octet et "@@K"+octet (4),
 * "@@P\n" (4), "@@EOL\n" (6), "@@EOLR\n"/"@@SNAP\n" (7). Un PVWrite peut
 * couper un marqueur en deux : attendre la suite au lieu de
 * resynchroniser. */
static const struct { const char *s; unsigned n; } MARKS[] = {
    { "@@A", 4 }, { "@@P\n", 4 }, { "@@K", 4 },
    { "@@EOL\n", 6 }, { "@@EOLR\n", 7 }, { "@@SNAP\n", 7 },
};

static int marker_prefix(const uint8_t *p, unsigned avail)
{
    for (unsigned m = 0; m < sizeof MARKS / sizeof MARKS[0]; m++) {
        unsigned n = MARKS[m].n;
        if (avail < n && memcmp(p, MARKS[m].s, avail) == 0) {
            return 1;
        }
    }
    return 0;
}

/* Consomme le plus de marqueurs possible ; s'arrete sur un marqueur incomplet
 * (donnees a cheval sur deux PVWrite) ou sur un @@EOLR indecidable. */
static void parse(void)
{
    for (;;) {
        if (rawpos >= rawlen) {
            break;
        }
        uint8_t *p = raw + rawpos;
        unsigned avail = rawlen - rawpos;

        if (avail >= 4 && p[0] == '@' && p[1] == '@' && p[2] == 'A') {
            uint8_t c = p[3];
            if (c == 0x0D || c == 0x0A) {
                emit('\n');
            } else if (c == 0x08) {
                emit('\b'); emit(' '); emit('\b');
            } else if (c == '+') {
                /* curseur transient / repos : jete */
            } else if (c >= 0x20 && c < 0x7F) {
                emit(c);
            } else if (c > 0x7F) {
                emit('?');
            }
            rawpos += 4;
            continue;
        }
        if (avail >= 6 && memcmp(p, "@@EOL\n", 6) == 0) {
            emit('\n');
            rawpos += 6;
            continue;
        }
        if (avail >= 7 && memcmp(p, "@@EOLR\n", 7) == 0) {
            /* lookahead : sauter les curseurs "@@A+" puis tester "@@EOL" */
            unsigned q = rawpos + 7;
            while (rawlen - q >= 4 && raw[q] == '@' && raw[q + 1] == '@' &&
                   raw[q + 2] == 'A' && raw[q + 3] == '+') {
                q += 4;
            }
            if (rawlen - q >= 6) {
                if (memcmp(raw + q, "@@EOL\n", 6) != 0) {
                    emit('\n');      /* pas de scroll texte : ligne isolee */
                }
                rawpos += 7;
                continue;
            }
            /* suivant non-"@@A+" disponible mais < 6 o : si ce n'est deja
             * pas "@@E", ce ne peut pas etre "@@EOL" -> emettre. */
            if (rawlen - q >= 3 && !(raw[q] == '@' && raw[q + 1] == '@' &&
                                     raw[q + 2] == 'E')) {
                emit('\n');
                rawpos += 7;
                continue;
            }
            break;  /* indecidable : attendre (resolu par io_flush) */
        }
        if (avail >= 4 && memcmp(p, "@@P\n", 4) == 0) {
            prompt_flag = 1;
            rawpos += 4;
            continue;
        }
        if (avail >= 4 && p[0] == '@' && p[1] == '@' && p[2] == 'K') {
            keys_consumed++;
            rawpos += 4;
            continue;
        }
        if (avail >= 7 && memcmp(p, "@@SNAP\n", 7) == 0) {
            if (avail < SAVE_HDR + 1) {
                break;
            }
            unsigned nl = p[7];
            if (avail < SAVE_HDR + nl + 3) {
                break;
            }
            unsigned idx = p[SAVE_HDR + nl];
            unsigned ln  = p[SAVE_HDR + nl + 1] |
                           ((unsigned)p[SAVE_HDR + nl + 2] << 8);
            if (idx >= 4 || ln != REGION_LEN[idx]) {
                rawpos++;
                continue;
            }
            if (avail < SAVE_HDR + nl + 3 + ln) {
                break;
            }
            if (idx == 0) {
                memset(blob_got, 0, sizeof blob_got);
                blob_ready = 0;
                blob[0] = 'S'; blob[1] = 'N'; blob[2] = 'A'; blob[3] = 'P';
            }
            unsigned off = 4;
            for (unsigned k = 0; k < idx; k++) {
                off += REGION_LEN[k];
            }
            memcpy(blob + off, p + SAVE_HDR + nl + 3, ln);
            blob_got[idx] = 1;
            if (blob_got[0] && blob_got[1] && blob_got[2] && blob_got[3]) {
                blob_ready = 1;
                blob_len = BLOB_LEN;
            }
            rawpos += SAVE_HDR + nl + 3 + ln;
            continue;
        }
        /* octet hors marqueur : resynchronisation, sauf si c'est le debut
         * d'un marqueur coupe (attendre la suite dans le prochain
         * PVWrite). */
        if (marker_prefix(p, avail)) {
            break;
        }
        rawpos++;
    }

    if (rawpos >= (1u << 16) || rawpos == rawlen) {
        if (rawpos) {
            memmove(raw, raw + rawpos, rawlen - rawpos);
            rawlen -= rawpos;
            rawpos = 0;
        }
    }
}

void io_write_raw(const uint8_t *p, unsigned n)
{
    unsigned room = (unsigned)sizeof raw - rawlen;
    if (n > room) {
        dropped += n - room;
        n = room;
    }
    if (n) {
        memcpy(raw + rawlen, p, n);
        rawlen += n;
    }
    parse();
}

/* Force la resolution d'un @@EOLR en fin de flux (appele a chaque prompt). */
void io_flush(void)
{
    if (rawpos + 7 <= rawlen && memcmp(raw + rawpos, "@@EOLR\n", 7) == 0) {
        emit('\n');
        rawpos += 7;
    }
    /* Un prefixe de marqueur ne peut plus se completer en fin de tour (le
     * shim emet chaque marqueur d'un bloc ; un vrai marqueur coupe aurait
     * ete complete avant le prompt) : resynchroniser pour ne pas laisser
     * le parseur bloque sur des octets fantomes. */
    while (rawpos < rawlen && marker_prefix(raw + rawpos, rawlen - rawpos)) {
        rawpos++;
    }
    parse();
}

int io_kb_read(void)
{
    if (khead == ktail) {
        return -1;
    }
    uint8_t c = keyq[ktail];
    ktail = (ktail + 1) % KEY_CAP;
    return c;
}

void io_key_push(uint8_t c)
{
    unsigned nt = (khead + 1) % KEY_CAP;
    if (nt != ktail) {
        keyq[khead] = c;
        khead = nt;
    }
}

void io_key_flush(void)
{
    khead = ktail = 0;
}

int io_prompt_seen(void)
{
    return prompt_flag;
}

void io_clear_prompt(void)
{
    prompt_flag = 0;
}

void io_keys_reset(void)
{
    keys_consumed = 0;
}

int io_kb_pending(void)
{
    return khead != ktail;
}

unsigned io_keys_consumed(void)
{
    return keys_consumed;
}

unsigned long io_dropped(void)
{
    return dropped;
}

const uint8_t *io_text_ptr(void)
{
    return txt;
}

int io_text_len(void)
{
    return (int)txtlen;
}

int io_save_ready(void)
{
    return blob_ready;
}

const uint8_t *io_save_ptr(void)
{
    return blob;
}

int io_save_len(void)
{
    return blob_len;
}

void io_save_clear(void)
{
    blob_ready = 0;
    blob_len = 0;
    memset(blob_got, 0, sizeof blob_got);
}
