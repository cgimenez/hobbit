/* Entrees/sorties du shim solveur : file clavier + filtre texte + SAVE.
 *
 * Reprend la logique de scripts/sim_play.py en C (aucun Python au runtime).
 */
#ifndef HOBBIT_IO_H
#define HOBBIT_IO_H

#include <stdint.h>

/* Reinitialise tous les tampons (appele par hob_init). */
void io_reset(void);

/* Octet ecrit par le shim via PVWrite (0xFFF7) : alimente le parseur. */
void io_write_raw(const uint8_t *p, unsigned n);

/* Octet lu par le shim via PVRead (0xFFF6) : -1 si file vide. */
int io_kb_read(void);

/* Force la resolution d'un @@EOLR en fin de flux (a appeler avant de tester
 * io_prompt_seen, en fin de tour). */
void io_flush(void);

/* Un prompt "@@P" a ete vu depuis le dernier io_clear_prompt(). */
int io_prompt_seen(void);
void io_clear_prompt(void);

/* Nombre d'octets clavier consommes (@@K) depuis io_clear_prompt()
 * (donc depuis le debut du dernier hob_run). */
unsigned io_keys_consumed(void);

/* Copie un octet clavier a emettre par le shim. */
void io_key_push(uint8_t c);
void io_key_flush(void);

/* Reste-t-il des octets clavier en attente (file non vide) ? */
int io_kb_pending(void);

/* Remet a zero le compteur d'octets consommes (@@K). */
void io_keys_reset(void);

/* Texte decode (cumulatif). */
const uint8_t *io_text_ptr(void);
int            io_text_len(void);

/* Blob SAVE ("SNAP"+3623) capture depuis @@SNAP, ou NULL. */
int            io_save_ready(void);
const uint8_t *io_save_ptr(void);
int            io_save_len(void);
void           io_save_clear(void);

#endif
