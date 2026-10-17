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

/* Noms runtime (miroir de scripts/map_static.py NAMES) pour les lieux
 * sans desc statique (record desc $0000). */
static const struct { uint8_t id; const char *name; } room_names[] = {
    { 0x02, "The forest road" },
    { 0x03, "The forest" },
    { 0x05, "The trolls' clearing" },
    { 0x08, "The running river" },
    { 0x09, "Rivendell" },
    { 0x0D, "The goblins' dungeon" },
    { 0x0F, "The dark stuffy passage" },
    { 0x12, "The dark winding passage" },
    { 0x15, "The treeless opening" },
    { 0x16, "Beorn's house" },
    { 0x17, "Forestriver" },
    { 0x1D, "The deep bog" },
    { 0x1E, "The elvenking's great halls" },
    { 0x21, "The barrel" },
    { 0x22, "Long lake" },
    { 0x2D, "The waterfall" },
    { 0x2E, "The forest road" },
    { 0x30, "The mountains" },
    { 0x31, "The great river" },
    { 0x32, "The green forest" },
    { 0x33, "The empty place" },
    { 0x34, "The dark stuffy passage" },
    { 0x35, "The dark stuffy passage" },
    { 0x36, "The dark stuffy passage" },
    { 0x37, "The dark stuffy passage" },
    { 0x38, "The dark stuffy passage" },
    { 0x39, "The dark stuffy passage" },
    { 0x3A, "The dark stuffy passage" },
    { 0x3B, "The dark stuffy passage" },
    { 0x3C, "The dark stuffy passage" },
    { 0x3D, "The dark stuffy passage" },
    { 0x3E, "The dark stuffy passage" },
    { 0x3F, "The dark stuffy passage" },
    { 0x40, "The dark stuffy passage" },
    { 0x41, "The dark stuffy passage" },
    { 0x44, "The narrow path" },
    { 0x45, "The narrow path" },
    { 0x46, "The narrow path" },
    { 0x47, "The narrow path" },
    { 0x48, "The narrow path" },
    { 0x49, "The narrow path" },
    { 0x4A, "The narrow path" },
    { 0x4B, "The steep path" },
    { 0x4C, "The steep path" },
    { 0x4D, "The steep path" },
    { 0x4E, "The deep misty valley" },
    { 0x4F, "The deep misty valley" },
};

const char *hob_room_name(int id)
{
    static char buf[128];
    size_t k;
    if (id < 0 || id >= 0x50 || index_of[id] < 0) {
        return "";
    }
    if (rooms[index_of[id]].desc) {
        msg_first_line(rooms[index_of[id]].desc, buf, sizeof buf);
        if (buf[0] && strcmp(buf, "(sans description)") != 0) {
            return buf;
        }
    }
    for (k = 0; k < sizeof(room_names) / sizeof(room_names[0]); k++) {
        if (room_names[k].id == id) {
            return room_names[k].name;
        }
    }
    return "";
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
