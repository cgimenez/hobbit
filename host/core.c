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

static unsigned long AutokeyCount;   /* diagnostic : nb d'auto-touches pause */
static unsigned long ShimCount, Kb7353Count;
unsigned long hob_autokey_count(void) { return AutokeyCount; }
unsigned long hob_shim_count(void) { return ShimCount; }
unsigned long hob_kb7353_count(void) { return Kb7353Count; }
uint16_t hob_last_pc(void) { return Regs.PC; }
static unsigned char SPAddr;
static int Halt;

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

int hob_run(int max_insn)
{
    long long budget = max_insn > 0 ? max_insn : 100000000LL;

    io_clear_prompt();
    io_keys_reset();
    while (!Halt) {
        /* Pause "press any key" (wait_for_key $7481) : le jeu boucle sur
         * get_key sans jamais imprimer de prompt -> sous harnais tour-par-tour
         * ce serait un blocage infini. On auto-fournit un CR (comme un joueur
         * qui appuie sur une touche), uniquement si aucune entree n'est en
         * file. Le retour de get_key (JSR $7353 depuis wait_for_key) vaut
         * $7483. */
        if (Regs.PC == 0xC000) ShimCount++;
        if (Regs.PC == 0x7353) Kb7353Count++;
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
            return 0;
        }
        if (--budget <= 0) {
            return 1;
        }
    }
    return 2;
}

int hob_boot(void)
{
    int rc = hob_run(0);
    if (rc != 0) {
        return rc;
    }
    return hob_run(0);
}
