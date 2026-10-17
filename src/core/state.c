/* Etat live : objets/personnages, entites VM, evenements (port de
 * memmap_defs.py). Lit Mem[] apres hob_init. SSOT = scripts/memmap_defs.py. */

#include <stdio.h>
#include <string.h>

#include "hobbit.h"
#include "msg.h"
#include "6502.h"
#include "memory.h"

/* Etats $1A62 : 61 cles (cle, base). Cf. memmap_defs.STATE_KEYS. */
typedef struct { uint8_t key; uint16_t base; } keybase;
static const keybase KEYS[] = {
    {0x00,0x1B1A},{0x01,0x1B63},{0x02,0x1B96},{0x03,0x1BBA},{0x04,0x1BA8},
    {0x05,0x1B42},{0x06,0x1BCE},{0x07,0x1BE9},{0x08,0x1C05},{0x09,0x1C25},
    {0x0A,0x1C55},{0x0B,0x1C74},{0x0C,0x1C93},{0x0D,0x1D1F},{0x0E,0x1CB0},
    {0x0F,0x1CDA},{0x10,0x1CC4},{0x11,0x1CEC},{0x12,0x1D07},{0x13,0x1D84},
    {0x14,0x1DA8},{0x15,0x1DE2},{0x16,0x1DF6},{0x17,0x1E0A},{0x18,0x1E25},
    {0x19,0x1E5F},{0x1A,0x1E73},{0x1B,0x1E87},{0x1C,0x1EA4},{0x1D,0x1EB7},
    {0x1E,0x1ECB},{0x1F,0x1EE3},{0x20,0x1EF5},{0x21,0x1F0B},{0x22,0x1F23},
    {0x23,0x1F37},{0x24,0x1F49},{0x25,0x1F5B},{0x26,0x1FB1},{0x27,0x1FC5},
    {0x28,0x1FDA},{0x29,0x1F75},{0x2A,0x1C3D},{0x2B,0x1B84},{0x3C,0x1B30},
    {0x3D,0x1FEC},{0x3E,0x1D38},{0x3F,0x1D4A},{0x40,0x1D60},{0x41,0x1D72},
    {0x42,0x1DBE},{0x43,0x1DD0},{0x44,0x1E3B},{0x45,0x2002},{0x46,0x1E4D},
    {0x47,0x1F8D},{0x48,0x1F9F},{0x49,0x2018},{0x4A,0x202E},{0x4B,0x2044},
    {0x4C,0x205A},
};
#define NKEYS ((int)(sizeof KEYS / sizeof KEYS[0]))

/* Identites (mot +$08). Cf. memmap_defs.STATE_IDENTITY. */
static const char *IDENT[0x4D] = {
    [0x00]="you",         [0x01]="rock door",   [0x02]="key",       [0x03]="map",
    [0x04]="large key",   [0x05]="door",       [0x06]="crack",     [0x07]="web",
    [0x08]="red door",    [0x09]="river",      [0x0A]="door",      [0x0B]="door",
    [0x0C]="door",        [0x0D]="door",       [0x0E]="short strong sword",
    [0x0F]="red key",     [0x10]="golden ring",[0x11]="door",      [0x12]="rope",
    [0x13]="barrel",      [0x14]="wine",       [0x15]="water",     [0x16]="water",
    [0x17]="water",       [0x18]="water",      [0x19]="bow",       [0x1A]="arrow",
    [0x1B]="window",      [0x1C]="torch",      [0x1D]="sand",      [0x1E]="door",
    [0x1F]="cache",       [0x20]="curtain",    [0x21]="cupboard",  [0x22]="food",
    [0x23]="treasure",    [0x24]="wall",       [0x25]="chest",     [0x26]="lunch",
    [0x27]="portcullis",  [0x28]="stone",      [0x29]="boat",      [0x2A]="river",
    [0x2B]="key",         [0x3C]="dragon",     [0x3D]="nasty goblin",
    [0x3E]="gandalf",     [0x3F]="thorin",     [0x40]="wood elf",  [0x41]="elrond",
    [0x42]="butler",      [0x43]="warg",       [0x44]="gollum",    [0x45]="hideous goblin",
    [0x46]="bard",        [0x47]="hideous troll", [0x48]="vicious troll",
    [0x49]="horrible goblin", [0x4A]="mean goblin", [0x4B]="vicious goblin",
    [0x4C]="disgusting goblin",
};

static int      active[NKEYS];
static int      nactive;
static int      built;

static uint8_t rd(uint16_t a) { return MemReadByte(a); }

void state_build(void)
{
    nactive = 0;
    for (int i = 0; i < NKEYS; i++) {
        uint16_t base = KEYS[i].base;
        int nloc = rd(base);            /* +0 = nombre de lieux */
        int carrier = rd(base + 1);     /* +1 = porteur ($FF = personne) */
        if (nloc > 0 || carrier != 0xFF || KEYS[i].key == 0x00) {
            active[nactive++] = i;
        }
    }
    built = 1;
}

int hob_player_room(void) { return rd(0x1B2A); }  /* player.eloc */
int hob_ploc(void)        { return rd(0x00C8); }

int hob_obj_count(void) { return built ? nactive : 0; }

int hob_obj_key(int i)
{
    if (i < 0 || i >= nactive) return -1;
    return KEYS[active[i]].key;
}

static int key_slot(int i)
{
    return (i < 0 || i >= nactive) ? -1 : active[i];
}

int hob_obj_field(int i, int f)
{
    int s = key_slot(i);
    if (s < 0) return 0;
    uint16_t b = KEYS[s].base;
    switch (f) {
        case HOB_F_NLOC:    return rd(b + 0x00);
        case HOB_F_CARRIER: return rd(b + 0x01);
        case HOB_F_VOLUME:  return rd(b + 0x02);
        case HOB_F_MASS:    return rd(b + 0x03);
        case HOB_F_HP:      return rd(b + 0x05);
        case HOB_F_TOUGH:   return rd(b + 0x06);
        case HOB_F_FLAGS:   return rd(b + 0x07);
        case HOB_F_ELOC:    return rd(b + 0x10);
        case HOB_F_NKEY:    return KEYS[s].key;
        default:            return 0;
    }
}

int hob_obj_carrier(int i)
{
    int c = hob_obj_field(i, HOB_F_CARRIER);
    return c == 0xFF ? -1 : c;
}

int hob_obj_alive(int i)
{
    int s = key_slot(i);
    if (s < 0) return 0;
    uint8_t key = KEYS[s].key;
    if (key >= 0x3C) {           /* creature : mort si flags bit3 */
        return (rd(KEYS[s].base + 0x07) & 0x08) ? 0 : 1;
    }
    return rd(KEYS[s].base) > 0; /* objet : present si nloc > 0 */
}

const char *hob_obj_name(int i)
{
    int s = key_slot(i);
    return s < 0 ? "?" : IDENT[KEYS[s].key];
}

const char *hob_obj_noun(int i)
{
    static char buf[64];
    int s = key_slot(i);
    if (s < 0) return "";
    uint16_t b = KEYS[s].base;
    msg_word(rd(b + 0x08), rd(b + 0x09), buf, sizeof buf);
    return buf;
}

/* --- Entites VM ($2B45, 17 x 7) --- */
#define ENT_N 17
int hob_ent_count(void) { return ENT_N; }
int hob_ent_id(int i)
{
    return (i < 0 || i >= ENT_N) ? -1 : rd((uint16_t)(0x2B45 + 7 * i));
}
int hob_ent_pc(int i)
{
    if (i < 0 || i >= ENT_N) return -1;
    uint16_t a = 0x2B45 + 7 * i;
    return rd(a + 2) | (rd(a + 3) << 8);
}

/* --- Evenements ($2B12, 10 x 5) --- */
#define EVT_N 10
int hob_evt_count(void) { return EVT_N; }
int hob_evt_cpt(int i)
{
    return (i < 0 || i >= EVT_N) ? -1 : rd((uint16_t)(0x2B12 + 5 * i + 1));
}
