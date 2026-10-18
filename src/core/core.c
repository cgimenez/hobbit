/* Point d'entree WASM : paravirtualisation (PV_READ/PV_WRITE) + boucle CPU.
 *
 * Remplace tools/cc65/src/sim65/main.c ET paravirt.c : au lieu de pipes et
 * de fichiers, PV_READ puise dans la file clavier C (alimentee par le JS) et
 * PV_WRITE pousse les marqueurs "@@..." dans le parseur io.c. Aucun acces
 * systeme (pas de fork/read/write).
 */

#include <string.h>

#include "6502.h"
#include "memory.h"
#include "peripherals.h"
#include "paravirt.h"
#include "trace.h"
#include "error.h"

#include "hobbit.h"
#include "io.h"
#include "msg.h"

static unsigned long AutokeyCount;   /* diagnostic : nb d'auto-touches pause */
static unsigned long ShimCount, Kb7353Count;
unsigned long hob_autokey_count(void) { return AutokeyCount; }
unsigned long hob_shim_count(void) { return ShimCount; }
unsigned long hob_kb7353_count(void) { return Kb7353Count; }
unsigned long hob_io_dropped(void) { return io_dropped(); }
uint16_t hob_last_pc(void) { return Regs.PC; }
static unsigned char SPAddr;
static int Halt;

/* ---- trace memoire (delta RAM par tour, protocol.md §4.3) ---- */
static int TraceOn;          /* hob_mem_trace(1) */
static int PrevValid;        /* PrevMem fige (etat "avant") */
static int MemTurn;          /* compteur de hob_run traces */
static uint8_t PrevMem[0x10000];
static uint8_t DiffBuf[9 + 0x10000 * 4];  /* "@@D\n"+turn+rc+nlen+recs */
static int DiffLen;

/* ---- paroles PNJ (observatoire hors-champ, passif) ----
 * Piege PC a l'entree de act_msg ($5B24) et say_if_visible ($5279) :
 * aucune modification du flot 6502 (ni RTS simule, ni PC touche), on se
 * contente de photographier (locuteur, message) + decoder la 1re ligne.
 * Conventions verifiees dans disasm/block4.asm :
 *   act_msg : locuteur = ZP obj ($C5, "<OBJ>" du "$13E8 <OBJ>SAY '"),
 *             message = mot inline apres le JSR (via l'adresse de retour
 *             sur la pile 6502) ; les appelants ne passent aucun registre.
 *   say_if_visible : A = id locuteur, X/Y = adresse du message ; on note
 *             la tentative meme si la routine sort tot (code_52C8) car,
 *             loin du joueur, l'affichage est jete (outen=0) : c'est
 *             exactement le hors-champ qui nous interesse.
 * Garde phase==1 ($0C) : en phase 0 (sonde act_probe) aucun message ne
 * part, et on eviterait un double comptage sonde/reel. */
#define EVT_TEXT 80
#define EVT_N 64
#define EVT_REC (8 + EVT_TEXT)
static uint8_t EvtBuf[EVT_N * EVT_REC];
static int EvtCount;
static unsigned EvtTurn;   /* incremente a chaque fin de hob_run */

static void evt_push(int kind, int speaker, int eloc, uint16_t msg)
{
    uint8_t *r;
    char *txt;
    if (EvtCount >= EVT_N) {
        return;   /* sature : les plus anciens sont gardes, pas de shift */
    }
    r = EvtBuf + EvtCount * EVT_REC;
    r[0] = (uint8_t)(EvtTurn & 0xFF);
    r[1] = (uint8_t)((EvtTurn >> 8) & 0xFF);
    r[2] = (uint8_t)kind;      /* 0 = act_msg, 1 = say_if_visible */
    r[3] = (uint8_t)speaker;   /* cle d'etat $3C-$4C */
    r[4] = (uint8_t)eloc;      /* lieu du locuteur au moment du fait */
    r[5] = (uint8_t)(msg & 0xFF);
    r[6] = (uint8_t)(msg >> 8);
    r[7] = 0;                  /* reserve */
    msg_first_line(msg, (char *)(r + 8), EVT_TEXT);
    /* les marqueurs non rendus (ex. <MSG>/<OBJ> en tete) sortent en
     * espaces : purge a gauche pour un "X dit : ..." propre */
    txt = (char *)(r + 8);
    {
        char *s = txt;
        while (*s == ' ' || *s == '\t') {
            s++;
        }
        if (s != txt) {
            memmove(txt, s, strlen(s) + 1);
        }
    }
    EvtCount++;
}

static void evt_speech(int kind)
{
    unsigned sp;
    uint16_t ret, msg;
    int speaker, eloc;

    if (MemReadByte(0x000C) != 1) {   /* phase ($0C) : 1 = action reelle */
        return;
    }
    if (kind == 0) {
        speaker = MemReadByte(0x00C5);   /* obj : acteur courant */
        /* adresse de retour 6502 -> mot inline (convention INLINE_MSGS) */
        sp = Regs.SP;
        ret = (uint16_t)(MemReadByte((uint16_t)(0x0100 + ((sp + 1) & 0xFF)))
              | (MemReadByte((uint16_t)(0x0100 + ((sp + 2) & 0xFF))) << 8));
        msg = MemReadWord((uint16_t)(ret + 1));
    } else {
        if (Regs.AC == 0x00 || Regs.AC == 0xFF) {
            return;   /* rien a dire (miroir du test say_if_visible) */
        }
        speaker = Regs.AC;
        msg = (uint16_t)(Regs.XR | (Regs.YR << 8));
    }
    if (speaker < 0x3C || speaker > 0x4C) {
        return;   /* PNJ seuls ($3C-$4C) : ni joueur ($00) ni objets */
    }
    if (kind == 1 && msg == 0x13F6) {
        return;   /* tentative d'annonce "<MSG>ENTER" (move_announce) :
                     l'arrivee est deja captee par le diff eloc, et le
                     "<MSG>" ne se decode pas en nom de locuteur */
    }
    eloc = MemReadByte(0x00C9);   /* eloc : lieu de l'acteur courant */
    evt_push(kind, speaker, eloc, msg);
}

/* ---- paravirtualisation : pile logicielle ZP (cf. paravirt.c sim65) ---- */

static unsigned GetAX(CPURegs *R)
{
    return R->AC | (R->XR << 8);
}

static void SetAX(CPURegs *R, unsigned v)
{
    R->AC = v & 0xFF;
    R->XR = (v >> 8) & 0xFF;
}

static unsigned char Pop(CPURegs *R)
{
    return MemReadByte(0x0100 + (++R->SP & 0xFF));
}

static unsigned PopParam(unsigned incr)
{
    unsigned sp = MemReadZPWord(SPAddr);
    unsigned val = MemReadWord((uint16_t)sp);
    MemWriteWord(SPAddr, (uint16_t)(sp + incr));
    return val;
}

static void PVRead(CPURegs *R)
{
    unsigned count = GetAX(R);
    unsigned buf = PopParam(2);
    unsigned fd = PopParam(2);
    unsigned n = 0;

    if (fd == 0) {  /* stdin : file clavier */
        while (n < count) {
            int c = io_kb_read();
            if (c < 0) {
                break;
            }
            MemWriteByte((uint16_t)(buf + n), (uint8_t)c);
            n++;
        }
    }
    SetAX(R, n);
}

static void PVWrite(CPURegs *R)
{
    unsigned count = GetAX(R);
    unsigned buf = PopParam(2);
    unsigned fd = PopParam(2);

    (void)fd;
    if (count > 0 && buf < 0x10000) {
        unsigned room = 0x10000 - buf;
        io_write_raw(&Mem[buf], count < room ? count : room);
    }
    SetAX(R, count);
}

static void PVExit(CPURegs *R)
{
    (void)R;
    Halt = 1;
}

void ParaVirtInit(unsigned aArgStart, unsigned char aSPAddr)
{
    (void)aArgStart;
    SPAddr = aSPAddr;
}

void ParaVirtHooks(CPURegs *R)
{
    uint16_t pc = R->PC;
    unsigned lo;

    if (pc < PARAVIRT_BASE || pc >= PARAVIRT_BASE + 9) {
        return;
    }
    switch (pc) {
        case 0xFFF6: PVRead(R);  break;  /* PVRead  */
        case 0xFFF7: PVWrite(R); break;  /* PVWrite */
        case 0xFFF9: PVExit(R);  break;  /* PVExit  */
        default: break;                  /* autres : no-op */
    }
    /* simule le RTS */
    lo = Pop(R);
    R->PC = (uint16_t)(lo + (Pop(R) << 8) + 1);
}

/* ---- API publique ---- */

void hob_key(int c)
{
    io_key_push((uint8_t)c);
}

void hob_key_flush(void)
{
    io_key_flush();
}

int hob_keys_consumed(void)
{
    return (int)io_keys_consumed();
}

uint8_t *hob_mem(void)
{
    return Mem;
}

int hob_mem_len(void)
{
    return 0x10000;
}

void hob_mem_trace(int on)
{
    TraceOn = on ? 1 : 0;
    if (!TraceOn) {
        PrevValid = 0;
    }
}

const uint8_t *hob_memdiff_ptr(void)
{
    return DiffBuf;
}

int hob_memdiff_len(void)
{
    return DiffLen;
}

int hob_mem_turn(void)
{
    return MemTurn;
}

/* --- Paroles PNJ (observatoire hors-champ, cf. evt_speech) ---
 * Chaque record fait HOB_SAY_REC octets : tour(2 LE), espece(1 : 0 =
 * act_msg, 1 = say_if_visible), locuteur(1 : cle $3C-$4C), lieu(1),
 * msg(2 LE), reserve(1), texte (1re ligne decodee, NUL-termine, 80 o).
 * hob_say_clear() vide le tampon (appele par le JS apres lecture du
 * tour) ; sature a HOB_SAY_N records (les plus anciens sont gardes). */
const uint8_t *hob_say_ptr(void)
{
    return EvtBuf;
}

int hob_say_len(void)
{
    return EvtCount * EVT_REC;
}

int hob_say_count(void)
{
    return EvtCount;
}

void hob_say_clear(void)
{
    EvtCount = 0;
}

/* Refonte session (appele par hob_init) : sans RAZ, un 2e hob_init dans le
 * meme processus (ex. page web boot() puis AUTO PLAY) repartirait avec le
 * Halt d'un PVExit precedent (hob_run rend 2 immediatement) et une base
 * PrevMem obsolete (premier delta trace fantome). TraceOn est conserve tel
 * quel : avec PrevValid=0, le prochain hob_run trace refige sa base. */
void core_reset(void)
{
    Halt = 0;
    AutokeyCount = 0;
    ShimCount = 0;
    Kb7353Count = 0;
    PrevValid = 0;
    MemTurn = 0;
    DiffLen = 0;
    EvtCount = 0;
    EvtTurn = 0;
}

/* Construit le delta "@@D\n"+turn+rc+nlen+recs depuis PrevMem, puis fige
 * l'etat courant comme base du prochain tour. */
static void memdiff_build(int rc)
{
    uint8_t *o = DiffBuf + 9;
    int n = 0;
    unsigned a;

    DiffBuf[0] = '@'; DiffBuf[1] = '@';
    DiffBuf[2] = 'D'; DiffBuf[3] = '\n';
    MemTurn++;
    DiffBuf[4] = (uint8_t)(MemTurn & 0xFF);
    DiffBuf[5] = (uint8_t)((MemTurn >> 8) & 0xFF);
    DiffBuf[6] = (uint8_t)rc;
    for (a = 0; a < 0x10000; a++) {
        uint8_t old = PrevMem[a], cur = Mem[a];
        if (old != cur) {
            if (n == 0xFFFF) {
                break;  /* sature (nlen 2 o) : jamais de record tronque */
            }
            o[0] = (uint8_t)(a & 0xFF);
            o[1] = (uint8_t)((a >> 8) & 0xFF);
            o[2] = old;
            o[3] = cur;
            o += 4;
            n++;
        }
    }
    DiffBuf[7] = (uint8_t)(n & 0xFF);
    DiffBuf[8] = (uint8_t)((n >> 8) & 0xFF);
    DiffLen = (int)(o - DiffBuf);
    memcpy(PrevMem, Mem, 0x10000);
}

int hob_run(int max_insn)
{
    long long budget = max_insn > 0 ? max_insn : 100000000LL;
    int rc = 2;

    io_clear_prompt();
    io_keys_reset();
    if (TraceOn && !PrevValid) {
        memcpy(PrevMem, Mem, 0x10000);
        PrevValid = 1;
    }
    while (!Halt) {
        /* Pause "press any key" (wait_for_key $7481) : le jeu boucle sur
         * get_key sans jamais imprimer de prompt -> sous harnais tour-par-tour
         * ce serait un blocage infini. On auto-fournit un CR (comme un joueur
         * qui appuie sur une touche), uniquement si aucune entree n'est en
         * file. Le retour de get_key (JSR $7353 depuis wait_for_key) vaut
         * $7483. */
        if (Regs.PC == 0xC000) ShimCount++;
        if (Regs.PC == 0x7353) Kb7353Count++;
        if (Regs.PC == 0x5B24) evt_speech(0);   /* act_msg : parole PNJ */
        else if (Regs.PC == 0x5279) evt_speech(1);  /* say_if_visible */
        if (Regs.PC == 0x7353 && !io_kb_pending()) {
            uint16_t ret = (uint16_t)(MemReadByte(0x0100 + ((Regs.SP + 1) & 0xFF))
                           | (MemReadByte(0x0100 + ((Regs.SP + 2) & 0xFF)) << 8));
            /* wait_for_key $7481 : jsr get_key -> retour $7484
             * (plage $7481-$7486). */
            if (ret >= 0x7481 && ret <= 0x7486) {
                AutokeyCount++;
                io_key_push(0x0d);
            }
        }
        ExecuteInsn();
        if (io_kb_pending()) {
            /* Des commandes sont encore en file (ex. "NORTH\rSW" de
             * l'anti-mange) : le prompt affiche n'est pas un point d'arret,
             * on continue pour traiter la suite dans le meme run. */
            io_clear_prompt();
        } else if (io_prompt_seen()) {
            io_flush();
            rc = 0;
            break;
        }
        if (--budget <= 0) {
            rc = 1;
            break;
        }
    }
    if (TraceOn) {
        memdiff_build(rc);
    }
    EvtTurn++;
    return rc;
}

int hob_boot(void)
{
    int rc = hob_run(0);
    if (rc != 0) {
        return rc;
    }
    return hob_run(0);
}
