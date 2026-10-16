/* Graphe des lieux (port de map_static.py build_graph). Lit Mem[]. Construit
 * une fois par hob_init via map_build(). SSOT = scripts/map_static.py. */

#include <string.h>

#include "hobbit.h"
#include "msg.h"
#include "6502.h"
#include "memory.h"

#define MAXROOM 80
#define MAXEX   40

typedef struct { uint8_t dir, cond, dst; } exit_t;
typedef struct {
    uint8_t  id;
    uint16_t addr;
    uint16_t desc;
    int      ne;
    exit_t   ex[MAXEX];
} room_t;

static room_t  rooms[MAXROOM];
static int     nrooms;
static int16_t index_of[0x50];   /* id -> index, -1 sinon */

static uint8_t rd(uint16_t a) { return MemReadByte(a); }
static uint16_t rw(uint16_t a)
{
    return rd(a) | ((uint16_t)rd(a + 1) << 8);
}

void map_build(void)
{
    uint16_t addr[0x50];
    uint8_t  id[0x50];
    int      m = 0;

    nrooms = 0;
    for (int i = 0; i < 0x50; i++) {
        index_of[i] = -1;
    }
    for (int i = 0; i < 0x50; i++) {
        uint16_t r = rw(0x2070 + 2 * i);
        if (r) {
            id[m] = (uint8_t)i;
            addr[m] = r;
            m++;
        }
    }
    /* tri par adresse croissante (comme map_static.srt) */
    for (int i = 1; i < m; i++) {
        uint16_t a = addr[i];
        uint8_t  k = id[i];
        int j = i - 1;
        while (j >= 0 && addr[j] > a) {
            addr[j + 1] = addr[j];
            id[j + 1] = id[j];
            j--;
        }
        addr[j + 1] = a;
        id[j + 1] = k;
    }

    for (int i = 0; i < m && nrooms < MAXROOM; i++) {
        uint16_t r = addr[i];
        uint16_t end = (i + 1 < m) ? addr[i + 1] : (uint16_t)(r + 64);
        int bodylen = 0;
        int done = -1;
        /* corps = [r+10, end) ; terminé par $FF ; longueur multiple de 3 */
        for (uint16_t a = r + 10; a < end && bodylen < 255; a++, bodylen++) {
            if (rd(a) == 0xFF) { done = bodylen; break; }
        }
        if (done < 0 || (done % 3) != 0) {
            continue;   /* pas de terminateur / queue non-triplet : ignore */
        }
        room_t *rr = &rooms[nrooms];
        rr->id = id[i];
        rr->addr = r;
        rr->desc = rw(r + 8);
        rr->ne = done / 3;
        if (rr->ne > MAXEX) {
            rr->ne = MAXEX;
        }
        for (int k = 0; k < rr->ne; k++) {
            uint16_t a = r + 10 + 3 * k;
            rr->ex[k].dir = rd(a);
            rr->ex[k].cond = rd(a + 1);
            rr->ex[k].dst = rd(a + 2);
        }
        index_of[rr->id] = (int16_t)nrooms;
        nrooms++;
    }
}

int hob_room_count(void) { return nrooms; }

int hob_room_id(int i)
{
    return (i < 0 || i >= nrooms) ? -1 : rooms[i].id;
}

const char *hob_room_name(int id)
{
    static char buf[128];
    if (id < 0 || id >= 0x50 || index_of[id] < 0) {
        return "";
    }
    msg_first_line(rooms[index_of[id]].desc, buf, sizeof buf);
    return buf;
}

int hob_room_exit_count(int id)
{
    if (id < 0 || id >= 0x50 || index_of[id] < 0) {
        return 0;
    }
    return rooms[index_of[id]].ne;
}

static const exit_t *exit_at(int id, int j)
{
    if (id < 0 || id >= 0x50 || index_of[id] < 0) {
        return 0;
    }
    const room_t *r = &rooms[index_of[id]];
    if (j < 0 || j >= r->ne) {
        return 0;
    }
    return &r->ex[j];
}

int hob_room_exit_dir(int id, int j)
{
    const exit_t *e = exit_at(id, j);
    return e ? e->dir : -1;
}

int hob_room_exit_cond(int id, int j)
{
    const exit_t *e = exit_at(id, j);
    return e ? e->cond : -1;
}

int hob_room_exit_dst(int id, int j)
{
    const exit_t *e = exit_at(id, j);
    return e ? e->dst : -1;
}
