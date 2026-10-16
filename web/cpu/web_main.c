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
