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

/* Noms courts significatifs (miroir exact de scripts/map_static.py NAMES,
 * 78 lieux). Prioritaires sur la desc statique (phrases brutes du moteur). */
static const struct { uint8_t id; const char *name; } room_names[] = {
    { 0x01, "Tunnel hall" },
    { 0x02, "Forest road" },
    { 0x03, "Forest" },
    { 0x04, "Dreary hills" },
    { 0x05, "Trolls' clearing" },
    { 0x06, "Trolls' path" },
    { 0x07, "Trolls' cave" },
    { 0x08, "Running river" },
    { 0x09, "Rivendell" },
    { 0x0A, "Misty mountains" },
    { 0x0B, "High pass" },
    { 0x0C, "Mountain path" },
    { 0x0D, "Goblins' dungeon" },
    { 0x0E, "Dry cave" },
    { 0x0F, "Dark passage" },
    { 0x10, "Torch cavern" },
    { 0x11, "Underground lake" },
    { 0x12, "Winding passage" },
    { 0x13, "Goblin gate" },
    { 0x14, "Goblin gate" },
    { 0x15, "Treeless opening" },
    { 0x16, "Beorn's house" },
    { 0x17, "Forestriver" },
    { 0x18, "Mirkwood gate" },
    { 0x19, "Bewitched forest" },
    { 0x1A, "Spider place" },
    { 0x1B, "Tangled forest" },
    { 0x1C, "Elvish clearing" },
    { 0x1D, "Deep bog" },
    { 0x1E, "Elvenking's halls" },
    { 0x1F, "Elven dungeon" },
    { 0x20, "Wine cellar" },
    { 0x21, "Barrel" },
    { 0x22, "Long lake" },
    { 0x23, "Wooden town" },
    { 0x24, "Strong river" },
    { 0x25, "Barren land" },
    { 0x26, "Dale ruins" },
    { 0x27, "Mountain gate" },
    { 0x28, "Ravenhill" },
    { 0x29, "Dragon halls" },
    { 0x2A, "Steep bay" },
    { 0x2B, "Straight passage" },
    { 0x2C, "Lonely mountain" },
    { 0x2D, "Waterfall" },
    { 0x2E, "Forest road" },
    { 0x30, "Mountains" },
    { 0x31, "Great river" },
    { 0x32, "Green forest" },
    { 0x33, "Empty place" },
    { 0x34, "Dark passage" },
    { 0x35, "Dark passage" },
    { 0x36, "Dark passage" },
    { 0x37, "Dark passage" },
    { 0x38, "Dark passage" },
    { 0x39, "Dark passage" },
    { 0x3A, "Dark passage" },
    { 0x3B, "Dark passage" },
    { 0x3C, "Dark passage" },
    { 0x3D, "Dark passage" },
    { 0x3E, "Dark passage" },
    { 0x3F, "Dark passage" },
    { 0x40, "Dark passage" },
    { 0x41, "Dark passage" },
    { 0x42, "West bank" },
    { 0x43, "East bank" },
    { 0x44, "Narrow path" },
    { 0x45, "Narrow path" },
    { 0x46, "Narrow path" },
    { 0x47, "Narrow path" },
    { 0x48, "Narrow path" },
    { 0x49, "Narrow path" },
    { 0x4A, "Narrow path" },
    { 0x4B, "Steep path" },
    { 0x4C, "Steep path" },
    { 0x4D, "Steep path" },
    { 0x4E, "Misty valley" },
    { 0x4F, "Misty valley" },
};

const char *hob_room_name(int id)
{
    static char buf[128];
    size_t k;
    if (id < 0 || id >= 0x50 || index_of[id] < 0) {
        return "";
    }
    for (k = 0; k < sizeof(room_names) / sizeof(room_names[0]); k++) {
        if (room_names[k].id == id) {
            return room_names[k].name;
        }
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
