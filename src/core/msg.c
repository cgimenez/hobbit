/* Rendu de texte du bloc 2 : port de word_render / decode_msg (map_static.py).
 * Opere sur Mem[] (memory.c). Sert les noms d'objets/lieux. */

#include <string.h>

#include "msg.h"
#include "6502.h"
#include "memory.h"

#define COMMON 0x1117   /* table des 32 mots courants $60-$7F */

static char ch(uint8_t c)
{
    return (c >= 1 && c <= 26) ? (char)('A' + c - 1) : '?';
}

static void put(char *out, int cap, int *n, char c)
{
    if (*n < cap - 1) {
        out[(*n)++] = c;
        out[*n] = 0;
    }
}

static void puts_(char *out, int cap, int *n, const char *s)
{
    while (*s) {
        put(out, cap, n, *s++);
    }
}

void msg_word(uint8_t lo, uint8_t hib, char *out, int cap)
{
    int n = 0;
    uint16_t a;
    int y = 0, x = 0;

    out[0] = 0;
    if ((hib & 0x0F) == 0 && lo == 0) {
        puts_(out, cap, &n, "<null>");
        return;
    }
    a = 0x0500 + ((hib & 0x0F) << 8) + lo;
    /* garde-fou : le dico valide termine toujours par c == 0 en quelques
     * octets (word_render Python boucle de meme) ; borne large (le plus
     * long mot fait < 40 car). */
    for (int k = 0; k < 64; k++) {
        uint8_t b = MemReadByte((uint16_t)(a + y));
        uint8_t c = b & 0x1F;
        if (c == 0) {
            break;
        }
        put(out, cap, &n, ch(c));
        x++;
        y++;
        if (!(MemReadByte((uint16_t)(a + y - 1)) & 0x80)) {
            continue;
        }
        if (x == 2) {
            continue;
        }
        if (x != 3) {
            break;
        }
        if (MemReadByte((uint16_t)(a + y - 2)) & 0x80) {
            continue;
        }
        break;
    }
}

/* Decode jusqu'a la 1re fin de ligne. Les mots consecutifs sont separes par
 * un espace (comme " ".join(words) de map_static.py) ; un litteral ($20-$5F)
 * interrompt la serie (pas d'espace ajoute). */
static void append_word(char *out, int cap, int *n, int *last_word,
                        uint8_t lo, uint8_t hib)
{
    char w[64];
    int k = 0;
    msg_word(lo, hib, w, sizeof w);
    if (*last_word && *n > 0) {
        put(out, cap, n, ' ');
    }
    while (w[k]) {
        put(out, cap, n, w[k++]);
    }
    *last_word = 1;
}

static void decode(uint16_t a, char *out, int cap, int *n, int depth)
{
    int t = 0;
    int last_word = 0;

    while (t < 400) {
        uint8_t b = MemReadByte((uint16_t)(a + t));
        if (b >= 0x80) {
            uint8_t hi = b & 0x7F;
            uint8_t lo = MemReadByte((uint16_t)(a + t + 1));
            uint8_t nib = hi & 0xF0;
            t += 2;
            if (nib == 0x30 || nib == 0x20 || nib == 0x60) {
                break;  /* fin (point / fin / CR) */
            }
            append_word(out, cap, n, &last_word, lo, hi);
        } else if (b >= 0x60) {
            uint8_t lo = MemReadByte((uint16_t)(COMMON + 2 * (b - 0x60)));
            uint8_t hi = MemReadByte((uint16_t)(COMMON + 2 * (b - 0x60) + 1));
            append_word(out, cap, n, &last_word, lo, hi);
            t += 1;
        } else if (b >= 0x20) {
            put(out, cap, n, (char)b);
            last_word = 0;
            t += 1;
        } else if (b == 0x0D || b == 0x14 || b == 0x15 || b == 0x16) {
            break;  /* CR / fins inline */
        } else if (b == 0x0B || b == 0x02) {
            int8_t off = (int8_t)MemReadByte((uint16_t)(a + t + 1));
            if (depth < 6) {
                put(out, cap, n, ' ');
                last_word = 0;
                decode((uint16_t)(a + t + 1 + off), out, cap, n, depth + 1);
            }
            t += 2;
        } else {
            put(out, cap, n, ' ');
            last_word = 0;
            t += 1;
        }
    }
}

void msg_first_line(uint16_t addr, char *out, int cap)
{
    int n = 0;
    out[0] = 0;
    if (addr == 0) {
        puts_(out, cap, &n, "(sans description)");
        return;
    }
    decode(addr, out, cap, &n, 0);
    /* trim espaces de queue */
    while (n > 0 && (out[n - 1] == ' ' || out[n - 1] == '\n')) {
        out[--n] = 0;
    }
}
