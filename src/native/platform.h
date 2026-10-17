/* Frontiere d'environnement (SEULE limite admise entre natif et WASM).
 *
 * Tout le moteur (traps $FFF6/7/9, parseur de marqueurs, politique de tour,
 * boot, SAVE, lecteurs d'etat) vit dans le repertoire host et ne connait
 * emscripten : l'entree clavier est POUSSEE dans l'anneau partage
 * (io_key_push / hob_key) et le texte est TIRE via hob_text_*.
 * Voir docs/protocol.md (source de verite).
 *
 * Parallele impose :
 *   natif : src/native/platform_native.c  (remplit l'anneau par read(0),
 *                                    vide le texte par write(1))
 *   wasm  : JS (remplit par hob_key(), lit par hob_text_ptr/len)
 *
 * Noms imposes : platform_* (pas plat_*).
 */
#ifndef HOBBIT_PLATFORM_H
#define HOBBIT_PLATFORM_H

/* Codes de sortie du CLI natif (src/native/platform_native.c). */
enum {
    PLATFORM_OK       = 0,  /* session terminee (texte compare/fini) */
    PLATFORM_USAGE    = 1,  /* arguments invalides */
    PLATFORM_IO_ERR   = 2,  /* fichier d'image illisible */
    PLATFORM_INIT_ERR = 3,  /* hob_init() != 0 */
    PLATFORM_STALL    = 4   /* un tour a epuise son budget (rc=1) */
};

#endif
