# Version WASM — The Hobbit (Oric, 1982)

Application web jouable « façon Wilderland » : le jeu Oric tourne **dans le
navigateur** (cœur 6502 compilé en WebAssembly) avec, en temps réel, le texte,
la saisie, l'illustration vectorielle du lieu, une table complète des objets et
personnages, et la carte des lieux.

Principe directeur : **aucun Python au runtime ni au build web**. Les scripts
de l'atelier de reverse (`scripts/*.py`) sont **portés en C** et compilés en
WASM ; le Python reste cantonné au reverse hors-ligne (`disasm.py`, checkers,
`sim_pack.py`…) selon [`AGENTS.md`](../AGENTS.md).

## 1. Architecture

Tout vit sous `web/`. Correspondance fichier ↔ script remplacé ↔ source de
vérité (SSOT) :

| Fichier web | Remplace (dev) | Rôle |
|---|---|---|
| `cpu/web_main.c` | `sim65/main.c` + `paravirt.c` | boucle CPU, paravirt `PV_READ`/`PV_WRITE` (file clavier + tampon texte au lieu de pipes), `hob_boot` |
| `core/hobbit.c` | `scripts/sim_pack.py` | pose l'image `fetch` à `$0400`, patchs (clavier, hooks texte, pause, fast, vecteurs), init RAM, reset `$2C00` |
| `core/io.c` | `scripts/sim_play.py` | filtre texte `@@A`/`@@EOL`/`@@EOLR`/`@@P`, file clavier, capture du blob SAVE `@@SNAP` |
| `core/state.c` | `scripts/memmap_defs.py` | objets/PNJ (61 clés `$1A62`), entités VM `$2B45`, events `$2B12` |
| `core/map.c` | `scripts/map_static.py` (+ `map_draw.py`) | graphe des lieux (table `$2070`), sorties, noms |
| `core/vec.c` | `scripts/vec_decode.py` | rasterisation des 13 illustrations (table `$7AC0`) |
| `core/msg.c` | (`word_render`/`decode_msg` de `map_static.py`) | noms de mots/messages du bloc 2 |
| `include/hobbit.h` | — | ABI WASM (exports `hob_*`) |
| `ui/{index.html,app.js,style.css}` | — | UI vanilla (4 panes) |
| `serve.js` | — | serveur dev statique + HMR |
| `smoke.mjs` | — | test boot+commande sans navigateur |

Le cœur 6502 n'est **pas réécrit** : `tools/cc65/src/sim65/{6502,memory,
peripherals,error,trace}.c` sont compilés tels quels par `emcc`. Seuls
`main.c`/`paravirt.c` sont remplacés (I/O C au lieu de fichiers/pipes).

UI : panneau **texte** (sortie jeu), **saisie**, **illustration** (SVG/vecteur
du lieu courant), **table** objets/PNJ + **carte** (pastilles NPC + lieu joueur).

## 2. Toolchain

- **`emcc`** (MacPorts) : compiler C→WASM. C'est un programme **Python** ; il
  refuse le Python 3.9 d'Xcode → forcer `EMSDK_PYTHON=/opt/local/bin/python3.14`
  (déjà intégré au `Makefile` et à `serve.js`).
- **`ca65`/`ld65`** : vendus dans `tools/cc65/bin/` (cf. AGENTS.md §3), servent
  à assembler les shims (`harness/shim.s`, `harness/snap.s`).
- **`make`** pur (pas de cmake), cibles dans `web/Makefile`.
- **`node`** : serveur dev + test CLI.
- L'image (`data/hobbit.bin`), la fonte (`data/basic10.rom`) et les shims sont
  chargés par **`fetch`** → il faut servir en HTTP (le protocole `file://`
  bloque `fetch`).

## 3. Recettes

```
make -C web            # check + shims + wasm + assets -> web/build/
make -C web check      # gardes byte-identiques sur data/hobbit.bin (PROPRE exige)
make -C web test       # boot + OPEN DOOR/EAST en Node (sans navigateur)
make -C web serve      # http://localhost:8000  (HMR actif)
make -C web clean
```

- `make check` vérifie les octets d'origine des sites patchés (`$7353` clavier,
  `$75B8`/`$7694`/`$7514` hooks texte, `$7628` pause, `$2C4A` fast,
  `$2C0B/$2C0E/$2C11` vecteurs cassette) : échec = arrêt avant tout build.
- `make serve` : serveur statique + **HMR**. Éditer `web/{ui,core,cpu,include}`,
  `harness/*.s` ou `web/Makefile` relance `make wasm assets` puis recharge la
  page (SSE `/__hmr`) ; le client HMR est injecté dans le HTML servi, donc
  `ui/index.html` reste propre. `--no-hmr` pour couper.
- Les artefacts (`web/build/`) sont gitignorés.

## 4. Points techniques non triviaux

- **`hob_boot()`** absorbe **deux** prompts : le jeu rejoue lui-même `> LOOK.`
  (tutoriel) avant d'afficher le vrai prompt. Courir au-delà d'un vrai prompt
  déclenche l'auto-`WAIT` d'inactivité du jeu → ne jamais dépasser.
- **Pause** `$7628` patchée `A9 00 EA` (comme `sim_pack.py --solver`) : elle ne
  consomme plus la 1re touche de la commande suivante (indispensable en saisie
  live). Choix de saisie = variante **solveur** du shim (`-D SOLVER`, capture
  ASCII aux hooks `$75B8`/`$7694`/`$7514`), pas de dumps hires/OCR.
- **Table `HSHK`** ajoutée à `harness/shim.s` : signature binaire suivie des 3
  adresses `asc_plot/asc_eol/asc_eol2`, lue directement dans le shim par
  `core/hobbit.c` (évite de parser le listing ca65 côté C ; le harness natif
  continue de lire le listing).
- **SAVE/LOAD** : `harness/snap.s` (`vec_02/03/04` → `snap_load/save/clc`). Le
  blob `"SNAP"`+3623 o émis via `@@SNAP` est capturé par `io.c` puis stocké en
  `localStorage` ; au boot suivant il est déposé en `$E800` et restauré par un
  `LOAD` automatique.
- **Orientation des illustrations** : `vec.c` écrit `vbuf` en **ligne mémoire**
  `r = $7F - y` (comme `runs()` de `vec_decode.py`), sinon l'image est miroir.
- **Paravirt** : `PARAVIRT_BASE=$FFF1`, `$FFF6`=read (file clavier), `$FFF7`=write
  (tampon texte) ; le hook simule le `RTS` (PC = adresse empilée + 1), comme
  `sim65/paravirt.c`.

## 5. État et validation

Validé (commit `e3774c9`) :

- **Boot** → prompt `> LOOK.` (texte identique au harnais natif) ;
  `OPEN DOOR` / `EAST` → « You go east. », lieu `$01`→`$04`, PNJ autonomes
  (`Gandalf goes east.`, `Thorin enters.`).
- **Table live** : 61 objets/PNJ décodés (eloc, porteur, PV, attributs
  `v A o * b f F l`, mots-noms) ; **78 lieux** avec noms ; **13 illustrations**
  vectorielles (popcounts identiques à `vec_decode.py`, images superposables
  aux `docs/vectors/*.svg`).
- **SAVE/LOAD** round-trip : `SAVE` → blob 3627 o → `localStorage`, `LOAD`
  restaure (`$01`→`$04` vérifié).
- Garde-fous intacts : `scripts/disasm_check.py --block block4` PROPRE,
  `scripts/memmap_check.py` PROPRE, `scripts/disasm_rebuild.py --all`
  byte-identique.

## 6. Limites V1 connues

- Carte : layout **schématique** calculé en JS (BFS sur les sorties) ; pas
  encore les coordonnées de `Wilderland/MapCoordinates.h`.
- Pas de fenêtre « log » des actions NPC **hors vue du joueur** (filtre
  `say_if_visible $5279`) — le flux texte capté est celui montré au joueur.
- Pas de rendu hires live ni d'OCR : texte via hooks, illustrations via le
  rasteriseur ; le footer ASCII `$BF68+` de l'écran Oric est ignoré.
- Pas de gestion clavier spéciale Oric (au-delà de `$0D`=ENTREE et des
  guillemets pour `SAY TO X "..."`).

## 7. Reprise (handoff)

**État** : tout est commité (`e3774c9` web, `9f5f680` + `3b534df` doc) ;
`web/build/` est gitignoré → régénérer avec `make -C web` avant `serve`/`test`.
Toolchain déjà validée : `emcc` + `EMSDK_PYTHON=/opt/local/bin/python3.14`.

**ABI WASM** (`web/include/hobbit.h`, exports `EMSCRIPTEN_KEEPALIVE`) :
slots `hob_slot/_cap/_len` ; cycle `hob_init` → `hob_boot` → `hob_key` +
`hob_run` ; texte `hob_text_ptr/_len` ; SAVE `hob_save_ready/_ptr/_len/_clear` ;
état `hob_player_room`, `hob_obj_*` (61), `hob_ent_*` (17), `hob_evt_*` (10) ;
carte `hob_room_*` (78) ; vecteurs `hob_vec_render/_ptr/_key/_mode/_popcount`.
Le JS (`web/ui/app.js`) ne fait que `fetch` + appels + rendu.

**Pistes V1+ (par ordre de valeur)**
1. **Coordonnées de carte réelles** : porter `MapCoordinates.h` (ZX, lieux 1:1)
   dans `map.c`/`app.js` (remplace le layout BFS ; cf. `status.md` P4).
2. **Fenêtre log NPC hors-vue** : exploiter `entity_tick` + filtre
   `say_if_visible $5279` (actions des PNJ invisibles au joueur).
3. **Clavier Oric** : flèches → `N/S/E/W` (`key_arrow $2EA9`), `@` = répéter,
   touche quote pour `SAY TO X "..."`.
4. **Table** : tri/filtre (vivants/portés), surlignage joueur, timeline.
5. Optionnel : rendu hires live (`$A000`+footer `$BF68`) au lieu des SVG.

**Pièges à ne pas rouvrir**
- `hob_boot` = **2 prompts** (`> LOOK.` tutoriel puis vrai prompt) ; ne jamais
  courir au-delà d'un vrai prompt (auto-`WAIT` du jeu = tour parasite).
- Ne pas re-`LOOK` en 1re commande après boot (le jeu le fait déjà).
- Patchs sensibles (`make check` les garde) : `$7353`, `$75B8/$7694/$7514`,
  `$7628`, `$2C4A`, `$2C0B/$2C0E/$2C11`.
- `vbuf` en ligne mémoire `r = $7F - y` (sinon image miroir).
- HMR : serveur dev uniquement (`web/serve.js`), jamais dans `web/build`.
