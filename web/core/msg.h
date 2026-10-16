/* Rendu de mots/messages du bloc 2 (port de map_static.py word_render/
 * decode_msg). Lit Mem[] : aucun acces fichier. */
#ifndef HOBBIT_MSG_H
#define HOBBIT_MSG_H

#include <stdint.h>

/* Rend l'entree de dictionnaire (lo,hib) dans out (NUL-termine). */
void msg_word(uint8_t lo, uint8_t hib, char *out, int cap);

/* Decode le message a addr dans out, S'ARRETE a la 1re fin de ligne
 * (1re ligne seule, comme short_desc). */
void msg_first_line(uint16_t addr, char *out, int cap);

#endif
