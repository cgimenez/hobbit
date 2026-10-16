/* Construction de l'image jeu en RAM + slots de chargement (ex-sim_pack.py).
 *
 * Le JS remplit les slots (hob_slot/hob_slot_len) avec les fichiers fetch(),
 * puis hob_init() pose l'image a $0400, les shims, la fonte, applique les
 * patchs (clavier, hooks texte, pause, fast, vecteurs cassette/snapshot) et
 * reset le CPU a $2C00. Zero Python, zero acces fichier.
 */

#include <string.h>

#include "6502.h"
#include "memory.h"
#include "peripherals.h"
#include "paravirt.h"

#include "hobbit.h"
#include "io.h"

/* index live (state.c / map.c) */
void state_build(void);
void map_build(void);

#define IMG_CAP   0x9000
#define ROM_CAP   0x4000
#define SHIM_CAP  0x02F0
#define SNAP_CAP  0x0500
#define BLOB_CAP  3627

#define BASE          0x0400
#define SHIM_ADDR     0xC000
#define SHIM_VARS     0xC2F0
#define SHIM_VARS_END 0xC300
#define HIBIT_ADDR    0xC2F2
#define SNAP_ADDR     0xF700
#define SNAP_BLOB     0xE800
#define ROM_FILE_BASE 0xC000   /* basic10.rom : octet 0 = $C000 */
#define FONT_LO       0xFC70
#define FONT_HI       0xFFC0

#define KB_SCAN     0x7353
#define PLOT_ADDR   0x75B8
#define EOL_ADDR    0x7694
#define EOL2_ADDR   0x7514
#define PAUSE_ADDR  0x7628
#define NOIMG_ADDR  0x2C4A
#define VEC02       0x2C0B
#define VEC03       0x2C0E
#define VEC04       0x2C11
static const uint16_t TAPE_VECS[6] = {
    0x0405, 0x0408, 0x040B, 0x040E, 0x0411, 0x0414
};

static uint8_t  slot_img[IMG_CAP];
static uint8_t  slot_rom[ROM_CAP];
static uint8_t  slot_shim[SHIM_CAP];
static uint8_t  slot_snap[SNAP_CAP];
static uint8_t  slot_blob[BLOB_CAP];
static int      len_img, len_rom, len_shim, len_snap, len_blob;

static uint8_t *slot_ptr(int which)
{
    switch (which) {
        case HOB_SLOT_IMG:  return slot_img;
        case HOB_SLOT_ROM:  return slot_rom;
        case HOB_SLOT_SHIM: return slot_shim;
        case HOB_SLOT_SNAP: return slot_snap;
        case HOB_SLOT_BLOB: return slot_blob;
        default:            return 0;
    }
}

static int slot_cap(int which)
{
    switch (which) {
        case HOB_SLOT_IMG:  return IMG_CAP;
        case HOB_SLOT_ROM:  return ROM_CAP;
        case HOB_SLOT_SHIM: return SHIM_CAP;
        case HOB_SLOT_SNAP: return SNAP_CAP;
        case HOB_SLOT_BLOB: return BLOB_CAP;
        default:            return 0;
    }
}

uint8_t *hob_slot(int which)
{
    return slot_ptr(which);
}

int hob_slot_cap(int which)
{
    return slot_cap(which);
}

void hob_slot_len(int which, int len)
{
    if (len < 0) {
        len = 0;
    }
    if (len > slot_cap(which)) {
        len = slot_cap(which);
    }
    switch (which) {
        case HOB_SLOT_IMG:  len_img = len;  break;
        case HOB_SLOT_ROM:  len_rom = len;  break;
        case HOB_SLOT_SHIM: len_shim = len; break;
        case HOB_SLOT_SNAP: len_snap = len; break;
        case HOB_SLOT_BLOB: len_blob = len; break;
        default: break;
    }
}

static void poke(uint16_t addr, uint8_t v)
{
    MemWriteByte(addr, v);
}

static void jmp_to(uint16_t addr, uint16_t target)
{
    poke(addr, 0x4C);                    /* JMP abs */
    poke(addr + 1, target & 0xFF);
    poke(addr + 2, target >> 8);
}

/* Cherche la signature "HSHK" dans le shim -> (asc_plot, asc_eol, asc_eol2). */
static int find_hooks(uint16_t out[3])
{
    for (int i = 0; i + 4 + 6 <= len_shim; i++) {
        if (slot_shim[i] == 'H' && slot_shim[i + 1] == 'S' &&
            slot_shim[i + 2] == 'H' && slot_shim[i + 3] == 'K') {
            const uint8_t *w = slot_shim + i + 4;
            out[0] = w[0] | (w[1] << 8);
            out[1] = w[2] | (w[3] << 8);
            out[2] = w[4] | (w[5] << 8);
            return 0;
        }
    }
    return -1;
}

int hob_init(void)
{
    uint16_t hooks[3];
    uint16_t snap_ent[9];

    if (len_img <= 0 || len_rom <= 0 || len_shim <= 0 || len_snap <= 0) {
        return -1;
    }
    if (find_hooks(hooks) < 0) {
        return -2;
    }
    for (int i = 0; i < 9; i++) {
        snap_ent[i] = slot_snap[2 * i] | (slot_snap[2 * i + 1] << 8);
    }

    MemInit();
    PeripheralsInit();

    /* image jeu a $0400 */
    for (int i = 0; i < len_img; i++) {
        MemWriteByte((uint16_t)(BASE + i), slot_img[i]);
    }
    /* fonte ROM : basic10.rom octet 0 = $C000, utile $FC70-$FFBF */
    for (int a = FONT_LO; a < FONT_HI; a++) {
        int off = a - ROM_FILE_BASE;
        if (off >= 0 && off < len_rom) {
            MemWriteByte((uint16_t)a, slot_rom[off]);
        }
    }
    /* shims */
    for (int i = 0; i < len_shim; i++) {
        MemWriteByte((uint16_t)(SHIM_ADDR + i), slot_shim[i]);
    }
    for (int i = 0; i < len_snap; i++) {
        MemWriteByte((uint16_t)(SNAP_ADDR + i), slot_snap[i]);
    }
    /* blob SAVE optionnel en $E800 */
    if (len_blob > 0) {
        for (int i = 0; i < len_blob; i++) {
            MemWriteByte((uint16_t)(SNAP_BLOB + i), slot_blob[i]);
        }
    }

    /* patchs */
    jmp_to(KB_SCAN, SHIM_ADDR);                 /* clavier -> shim */
    jmp_to(PLOT_ADDR, hooks[0]);                /* hook plot  */
    jmp_to(EOL_ADDR, hooks[1]);                 /* hook scroll texte */
    jmp_to(EOL2_ADDR, hooks[2]);                /* hook scroll RAW   */
    poke(PAUSE_ADDR, 0xA9); poke(PAUSE_ADDR + 1, 0x00); poke(PAUSE_ADDR + 2, 0xEA);
    poke(NOIMG_ADDR, 0x00);                     /* $56=0 (fast) */
    jmp_to(VEC02, snap_ent[7]);                 /* vec_02 -> snap_load */
    jmp_to(VEC03, snap_ent[6]);                 /* vec_03 -> snap_save */
    jmp_to(VEC04, snap_ent[8]);                 /* vec_04 -> s_clc */
    for (int i = 0; i < 6; i++) {
        jmp_to(TAPE_VECS[i], snap_ent[i]);      /* stubs cassette B1 */
    }

    /* etat initial du shim : vars a 0, HIBIT=0 (pas de dump), miroir texte $FF */
    for (int a = SHIM_VARS; a < SHIM_VARS_END; a++) {
        poke((uint16_t)a, 0x00);
    }
    poke(HIBIT_ADDR, 0x00);

    io_reset();

    /* index live (objets/personnages, graphe des lieux) */
    state_build();
    map_build();

    /* reset CPU */
    MemWriteWord(0xFFFC, 0x2C00);
    ParaVirtInit(0, 0x02);
    Reset();
    return 0;
}

/* ---- acces texte / save (delegue a io.c) ---- */

const uint8_t *hob_text_ptr(void)
{
    return io_text_ptr();
}

int hob_text_len(void)
{
    return io_text_len();
}

int hob_save_ready(void)
{
    return io_save_ready();
}

const uint8_t *hob_save_ptr(void)
{
    return io_save_ptr();
}

int hob_save_len(void)
{
    return io_save_len();
}

void hob_save_clear(void)
{
    io_save_clear();
}
