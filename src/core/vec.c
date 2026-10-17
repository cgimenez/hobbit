/* Illustrations vectorielles (port de vec_decode.py). Lit Mem[], rasterise
 * dans vbuf (240x128, 1 octet/pixel = index palette Oric 0-7). La couleur
 * papier/encre vient de l'octet mode (mode&7 papier, (mode>>4)&7 encre). */

#include <string.h>

#include "hobbit.h"
#include "6502.h"
#include "memory.h"

#ifdef HOB_VEC_TRACE
#include <stdio.h>
#define VTR(...) printf(__VA_ARGS__)
#else
#define VTR(...) ((void)0)
#endif

#define TBL   0x7AC0
#define W 240
#define H 128
#define X_ORIGIN 12

static const uint8_t MASK[6] = { 0x20, 0x10, 0x08, 0x04, 0x02, 0x01 };

static uint8_t bits[128][40];
static uint8_t vbuf[W * H];
static uint8_t ink, paper;

#ifdef HOB_VEC_TRACE
static int vpop(void)
{
    int n = 0;
    for (int r = 0; r < 128; r++)
        for (int c = 0; c < 40; c++)
            for (int b = 0; b < 6; b++)
                if (bits[r][c] & MASK[b]) n++;
    return n;
}
#endif

static uint8_t rd(uint16_t a) { return MemReadByte(a); }

/* (x,y) ecran Oric -> (row, col, bit) ; rend 0 si hors zone dessinable. */
static int loc(int x, int y, int *r, int *c, int *b, int *px)
{
    if (x < 0x0E || x >= 0xF2 || y < 0 || y > 0x7F) {
        return 0;
    }
    *px = x - 0x0E;
    *r = 0x7F - y;
    *c = *px / 6;
    *b = *px % 6;
    return 1;
}

static int testpx(int x, int y)
{
    int r, c, b, px;
    if (!loc(x, y, &r, &c, &b, &px)) {
        return 0xFF;
    }
    return bits[r][c] & MASK[b];
}

static void plot(int x, int y)
{
    int r, c, b, px;
    if (!loc(x, y, &r, &c, &b, &px)) {
        return;
    }
    bits[r][c] |= MASK[b];
    /* vbuf est indexe par ligne MEMOIRE (r = $7F - y), comme vec_decode.py
     * (runs() emet r en y SVG) : l'image n'est donc pas miroir. */
    vbuf[(r * W) + px] = ink;
}

/* Segment : op&1 vertical, op&2 y-neg, op&4 x-neg ; $78 = pas mineur ;
 * b&$3F = longueur totale. Rend le point d'arret via ox/oy. */
static void vec_line(int *ox, int *oy, int op, int b)
{
    int x = *ox, y = *oy;
    int vert = op & 1, yneg = op & 2, xneg = op & 4;
    int minor = (((op & 0x78) >> 1) | (((b >> 7) & 1) << 1) |
                 ((b >> 6) & 1)) + 1;
    int total = b & 0x3F;
    int m = minor;

    for (;;) {
        plot(x, y);
        if (!vert) {
            if (!xneg) {
                x = (x + 1) & 0xFF;
                if (x == 0) { x = (x - 1) & 0xFF; break; }
            } else {
                x = (x - 1) & 0xFF;
                if (x == 0xFF) { x = (x + 1) & 0xFF; break; }
            }
        } else {
            if (!yneg) {
                y += 1;
                if (y >= 0x80) { y -= 1; break; }
            } else {
                y -= 1;
                if (y < 0) { y += 1; break; }
            }
        }
        if (--m == 0) {
            m = minor;
            if (!vert) {
                if (!yneg) {
                    y += 1;
                    if (y >= 0x80) { y -= 1; break; }
                } else {
                    y -= 1;
                    if (y < 0) { y += 1; break; }
                }
            } else {
                if (!xneg) {
                    x = (x + 1) & 0xFF;
                    if (x == 0) { x = (x - 1) & 0xFF; break; }
                } else {
                    x = (x - 1) & 0xFF;
                    if (x == 0xFF) { x = (x + 1) & 0xFF; break; }
                }
            }
        }
        if (--total < 0) {
            break;
        }
    }
    *ox = x;
    *oy = y;
}

/* Remplissage par spans (seed-fill, replique $783F-$78C0 de vec_decode.py). */
#define FILL_STACK (1 << 18)
static void vec_fill(int *px_, int *py_)
{
    int x = *px_, y = *py_;
    static int stack[FILL_STACK][2];
    int sp = 0;

    for (;;) {
        int below, above;
        if (testpx(x, y) == 0) {
            while (x != 0 && testpx(x, y) == 0) {
                x -= 1;
            }
            if (testpx(x, y) != 0) {
                x += 1;
            }
        }
        below = above = 0;
        for (;;) {
            plot(x, y);
            if (y != 0x7F) {
                y += 1;
                if (testpx(x, y) == 0) {
                    if (!below && sp < FILL_STACK) { stack[sp][0] = x; stack[sp][1] = y; sp++; below = 1; }
                } else {
                    below = 0;
                }
                y -= 1;
            }
            if (y != 0) {
                y -= 1;
                if (testpx(x, y) == 0) {
                    if (!above && sp < FILL_STACK) { stack[sp][0] = x; stack[sp][1] = y; sp++; above = 1; }
                } else {
                    above = 0;
                }
                y += 1;
            }
            x = (x + 1) & 0xFF;
            if (x == 0 || testpx(x, y) != 0) {
                break;
            }
        }
        if (sp == 0) {
            break;
        }
        sp--;
        x = stack[sp][0];
        y = stack[sp][1];
    }
    *px_ = x;
    *py_ = y;
}

static int find_entry(int room)
{
    for (int i = 0; i < 64; i++) {
        uint8_t key = rd((uint16_t)(TBL + 3 * i));
        if (key == 0xFF) {
            return -1;
        }
        if (key == room) {
            return rd((uint16_t)(TBL + 3 * i + 1)) |
                   (rd((uint16_t)(TBL + 3 * i + 2)) << 8);
        }
    }
    return -1;
}

int hob_vec_key(int room)
{
    for (int i = 0; i < 64; i++) {
        uint8_t key = rd((uint16_t)(TBL + 3 * i));
        if (key == 0xFF) {
            return -1;
        }
        if (key == room) {
            return key;
        }
    }
    return -1;
}

int hob_vec_render(int room, uint8_t *buf)
{
    int addr = find_entry(room);
    if (addr < 0) {
        return 0;
    }
    memset(bits, 0, sizeof bits);
    uint8_t mode = rd((uint16_t)addr);
    paper = mode & 7;
    ink = (mode >> 4) & 7;
    memset(vbuf, paper, sizeof vbuf);

    uint16_t p = (uint16_t)(addr + 1);
    int x = 0, y = 0;
    for (;;) {
        uint8_t op = rd(p);
        if (op == 0) {
            VTR("END pop=%d\n", vpop());
            break;
        }
        if (op == 0x08) {
            p += 1; x = rd(p);
            p += 1; y = rd(p);
            p += 1;
            VTR("CUR x=%d y=%d pop=%d\n", x, y, vpop());
        } else if (op & 0x80) {
            uint8_t b = rd(p + 1);
            vec_line(&x, &y, op, b);
            p += 2;
            VTR("LINE %02X/%02X -> x=%d y=%d pop=%d\n", op, b, x, y, vpop());
        } else if (op & 0x40) {
            p += 1; x = rd(p);
            p += 1; y = rd(p);
            p += 1;
            VTR("FILL seed x=%d y=%d\n", x, y);
            vec_fill(&x, &y);
            VTR("  after fill x=%d y=%d pop=%d\n", x, y, vpop());
        } else if (op & 0x20) {
            p += 1;
            while (rd(p) != 0xFF) {
                p += 1;
            }
            p += 1;
            VTR("SKIP pop=%d\n", vpop());
        } else {
            p += 1;
            VTR("? %02X pop=%d\n", op, vpop());
        }
    }
    if (buf && buf != vbuf) {
        memcpy(buf, vbuf, sizeof vbuf);
    }
    return 1;
}

const uint8_t *hob_vec_ptr(void)
{
    return vbuf;
}

int hob_vec_mode(int room)
{
    int addr = find_entry(room);
    return addr < 0 ? -1 : rd((uint16_t)addr);
}

int hob_vec_popcount(void)
{
    int n = 0;
    for (int r = 0; r < 128; r++) {
        for (int c = 0; c < 40; c++) {
            for (int b = 0; b < 6; b++) {
                if (bits[r][c] & MASK[b]) {
                    n++;
                }
            }
        }
    }
    return n;
}
