/* ABI de l'emulateur WASM (The Hobbit, Oric 1982).
 *
 * Le JS (web/ui/app.js) remplit les slots avec les fichiers fetch() des
 * octets bruts, appelle hob_init() puis hob_run()/hob_key(). Aucune fonction
 * n'alloue cote JS : les slots sont des buffers statiques C dont l'adresse
 * est exposee.
 */
#ifndef HOBBIT_H
#define HOBBIT_H

#include <stdint.h>

#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#define HOB_API EMSCRIPTEN_KEEPALIVE
#else
#define HOB_API
#endif

/* Slots de chargement (remplis par le JS avant hob_init). */
#define HOB_SLOT_IMG   0  /* data/hobbit.bin   (image $0400, 36274 o)   */
#define HOB_SLOT_ROM   1  /* data/basic10.rom  (fonte, lue $FC70)       */
#define HOB_SLOT_SHIM  2  /* build/shim.bin    (shim solveur @ $C000)   */
#define HOB_SLOT_SNAP  3  /* build/snap.bin    (shim SAVE/LOAD @ $F700)*/
#define HOB_SLOT_BLOB  4  /* sauvegarde SAVE ("SNAP"+3623) ou vide      */
#define HOB_SLOT_N    5

/* Adresse + capacite d'un slot (le JS y copie ses octets bruts). */
HOB_API uint8_t *hob_slot(int which);
HOB_API int      hob_slot_cap(int which);

/* Longueurs effectives deposees par le JS (hob_slot_len_set avant init). */
HOB_API void hob_slot_len(int which, int len);

/* Construit l'image en RAM ($0400 + patchs + shims) et reset a $2C00.
 * Rend 0 si OK, <0 si un slot requis manque. */
HOB_API int hob_init(void);

/* Execute jusqu'a un prompt "@@P" (rend 0), budget epuise (rend 1) ou halt
 * (rend 2). max_insn <= 0 : budget par defaut. */
HOB_API int hob_run(int max_insn);

/* Boot : le jeu rejoue lui-meme "> LOOK." (prompt tutoriel) puis decrit le
 * lieu et affiche le vrai prompt. hob_boot() absorbe les deux et rend 0 au
 * vrai prompt (pret pour une commande joueur). */
HOB_API int hob_boot(void);

/* Depose un octet clavier Oric (0x0D = ENTREE) dans la file d'entree. */
HOB_API void hob_key(int c);

/* Efface la file d'entree (mouse/keyboard flush). */
HOB_API void hob_key_flush(void);

/* --- Texte de sortie (cumulatif ; le JS lit le delta) --- */
HOB_API const uint8_t *hob_text_ptr(void);
HOB_API int            hob_text_len(void);

/* --- SAVE : blob "SNAP"+3623 pret (rend 1 apres un SAVE complet) --- */
HOB_API int            hob_save_ready(void);
HOB_API const uint8_t *hob_save_ptr(void);
HOB_API int            hob_save_len(void);
HOB_API void           hob_save_clear(void);

/* --- Etat live (decode de Mem[], cf. state.c) --- */
HOB_API int hob_player_room(void);        /* player.eloc ($1B2A)      */
HOB_API int hob_ploc(void);               /* miroir $C8               */

/* Table d'objets/personnages (cles d'etat $00-$4C). */
HOB_API int         hob_obj_count(void);
HOB_API int         hob_obj_key(int i);
HOB_API const char *hob_obj_name(int i);        /* identite ou "(inconnu)" */
HOB_API const char *hob_obj_noun(int i);        /* mot-nom (word_render)   */
HOB_API int         hob_obj_field(int i, int f);/* HOB_F_*                */
HOB_API int         hob_obj_alive(int i);       /* 1 vivant, 0 mort/absent */
HOB_API int         hob_obj_carrier(int i);     /* id porteur, -1 personne */

/* Champs hob_obj_field. */
#define HOB_F_NLOC    0
#define HOB_F_CARRIER 1
#define HOB_F_VOLUME  2
#define HOB_F_MASS    3
#define HOB_F_HP      4
#define HOB_F_TOUGH   5
#define HOB_F_FLAGS   6
#define HOB_F_ELOC    7
#define HOB_F_NKEY    8

/* Entites VM (table $2B45) : etat courant (id, PC). */
HOB_API int hob_ent_count(void);
HOB_API int hob_ent_id(int i);
HOB_API int hob_ent_pc(int i);

/* Evenements differes (table $2B12) : compteur. */
HOB_API int hob_evt_count(void);
HOB_API int hob_evt_cpt(int i);

/* --- Carte (graphe des lieux, cf. map.c) --- */
HOB_API int         hob_room_count(void);
HOB_API int         hob_room_id(int i);
HOB_API const char *hob_room_name(int id);
HOB_API int         hob_room_exit_count(int id);
HOB_API int         hob_room_exit_dir(int id, int j);
HOB_API int         hob_room_exit_cond(int id, int j);
HOB_API int         hob_room_exit_dst(int id, int j);

/* --- Illustrations vectorielles (cf. vec.c) --- */
/* Rend 1 si le lieu a une illustration, et remplit buf (240 x 128 pixels,
 * 1 octet/pixel : index palette Oric 0-7). */
HOB_API int hob_vec_render(int room, uint8_t *buf);
HOB_API const uint8_t *hob_vec_ptr(void);   /* buffer interne 240*128 */
HOB_API int            hob_vec_key(int room);  /* cle $7AC0 ou -1 */
HOB_API int            hob_vec_mode(int room); /* octet mode ou -1 */
HOB_API int            hob_vec_popcount(void); /* pixels encre du dernier render */

#endif
