# AGENTS.md — Reverse-engineering de The Hobbit (Oric, 1982)

## 1. Contexte

On reverse-engineer **The Hobbit (1982, Melbourne House, Oric-1/Atmos)** : jeu
d'aventure **texte + graphismes vectoriels** (le bitmap aurait occupé trop
d'espace sur une machine comme l'Oric Atmos). Le mode texte décrit la situation
et attend un input ; certains lieux sont illustrés en vectoriel.

Deux systèmes à comprendre et documenter :

- **AnimTalk** : parser textuel évolué (qualité des interactions). S'étudie via
  les entrées/sorties texte (clavier/écran) sous harnais.
- **AnimAction** : personnages autonomes qui vivent leur vie même hors présence
  du joueur. S'étudie par inspection mémoire + traces d'exécution.

Source de vérité : `data/hobbit-1982.tap` → `data/hobbit.bin` (image mémoire
`$0400`–`$91B1`) via `scripts/tape_extract.py`.

## 2. Objectif et méthode

1. **Désassembler** : `scripts/disasm.py` → `disasm/block4.asm` (via da65).
2. **Réassembler à l'identique** : ca65 + ld65 → binaire **byte-identique** à
   `data/hobbit.bin` (preuve de validité n°1).
3. **Exécuter sous sim65** avec shims paravirtualisation (`JSR $FFF1`–`$FFF9`) :
   intercepter les prints, simuler le clavier, dumper le framebuffer — pour
   valider le code et étudier AnimTalk/AnimAction (preuve n°2).

## 3. Toolchain imposée

- **Exclusivement `tools/cc65/bin/`** (`ca65`, `ld65`, `da65`, `sim65`, V2.19).
  Ne jamais utiliser les versions MacPorts (`/opt/local/bin`) ni aucune autre.
- Invoquer les binaires par un chemin dérivé de la racine du repo, jamais via
  une résolution PATH implicite.
- Python : `.venv` du projet (`uv`), scripts dans `scripts/`.

## 4. Règles d'or

- **Ne jamais éditer `disasm/block1.asm`, `disasm/block4.asm` (ni leurs
  `.info`) à la main.** Le modèle vient de
  `scripts/disasm.py` (descente récursive + `MANUAL_ENTRIES` / `SEED_EXCLUDE`
  par bloc, dans `BLOCKS`). Toute correction = patch du script + régénération
  + re-vérification. (Les shims `src/6502/*.s`, eux, sont écrits à la main et
  éditables : ils ne sont pas générés.)
- **Avant chaque commit : `scripts/disasm_check.py --block <bloc>` doit sortir
  exit 0** (`RÉSULTAT: PROPRE`).
- **Documenter les routines via `ROUTINE_DOCS`/`ROUTINE_NOTES` dans
  `scripts/disasm.py`** (nom + résumé une ligne → labels/commentaires
  régénérés dans le listing), jamais en éditant `blockN.asm`. Détails longs →
  `docs/block4-analysis.md` (bloc 4) / `docs/tape-archive.md` (bloc 1).
- **Aucun test sim65 sur un build non byte-identique.**
- Ne pas créer de nouveaux fichiers `.md` sauf demande explicite.
- `tools/cc65/` (toolchain vendue, ~350 Mo) est gitignoré et le reste.

## 5. Conventions binaire connues (à respecter)

- `JSR $440D` (`print_msg`) **et** `JSR $5B24` (`act_msg`) + mot inline =
  adresse du message ; reprise du code à JSR+5 (cf. `INLINE_MSGS`). Queue :
  `JSR $4737` / `JMP ($6A)`, helper `$44BE` (`INC $6A`).
- Tables d'actions `L7014` (verbes joueur, 15 entrées) / `L7143` (PNJ, VM
  `$4ED5`, **18 mots** : sentinelle + 15 connues + 3 inédites `$6E8B`/`$6CDB`/
  `$6EA7` = index VM 16–18, cf. `act_v14_15/16/17`) :
  entrées `word`, index par octet d'action (script `$x1`/`$x3`) / compteur, dispatch indirect
  (`L4C5D`). Corps en bloc 4, souvent orphelins du graphe d'appels →
  recensés en `MANUAL_ENTRIES` (checker D = garde-fou).
- Table de 16 vecteurs `JMP` en `$2C05`–`$2C34` (API interne) ; le bloc 4 n'use
  le hardware que via les vecteurs du bloc 1 (`$0405`–`$0417`, patchés selon
  ROM 1.0/1.1). **Zéro appel ROM direct dans le bloc 4** (vérifié, checker E).
- `STA $6A5C` = auto-modification (octet patché, relu par `LDA $6A5C`) :
  garder l'octet en donnée, le code reprend à `$6A5E`.

## 6. Recettes

```
.venv/bin/python scripts/tape_extract.py          # TAP -> data/hobbit.bin
.venv/bin/python scripts/disasm.py           # -> disasm/block4.info + block4.asm
                                             # [--block block1|block2|block3] -> disasm/<bloc>.*
.venv/bin/python scripts/disasm_check.py     # viser exit 0 (RÉSULTAT: PROPRE)
                                             # [--block block1|block2|block3|block4]
.venv/bin/python scripts/disasm_rebuild.py   # round-trip ca65+ld65 (disasm/<bloc>.cfg),
                                             # byte-identique exigé, exit 0
                                             # [--block block1|block2|block3|block4]
.venv/bin/python scripts/disasm_rebuild.py --all  # réassemble les 4 blocs,
                                             # recolle l'image $0400-$91B1
                                             # (trous $00) et compare à hobbit.bin
.venv/bin/python scripts/sim_pack.py [--hires]  # image sim65 (build/sim/hobbit.sim) :
                                             # shim I/O + patch $7353 + charset ROM
.venv/bin/python scripts/sim_pack.py --snapshot NOM  # checkpoint rejouable
                                             # (build/sim/NOM.sim, implique
                                             # --fast) : bypass SAVE/LOAD
                                             # (vec_02/03/04 -> snap.s),
                                             # blob sav/NOM.bin en $E800
.venv/bin/python scripts/sim_tickdb.py snaps     # snapshots (show/diff/verify/init)
./tools/cc65/bin/sim65 -x N build/sim/hobbit.sim < input.txt > frames.bin
.venv/bin/python scripts/sim_frames.py frames.bin   # écrans -> texte
.venv/bin/python scripts/sim_trace.py --input cmdfile.txt \\
    [--range LO HI] [--watch ADDR,..] [--cycles N]  # trace instruction filtrée
                                             # par plage PC (image --fast)
.venv/bin/python scripts/msg_decode.py words  # dump des 600 mots du dictionnaire
                                             # ($0540-$1156, 1/ligne) ; <ADDR> =
                                             # aperçu d'un message ($4444)
.venv/bin/python scripts/memmap.py report    # couverture des variables SAVE/LOAD
                                             # (fusion sim_tickdiff+solver, SSOT
                                             # memmap_defs.py) ; slots/xref/gen
.venv/bin/python scripts/memmap_check.py     # viser exit 0 (RÉSULTAT: PROPRE)
.venv/bin/python scripts/map_draw.py         # carte D2 des lieux (map_static +
                                             # statut visite) -> docs/map.d2 + map.svg
                                             # [--layout dagre|elk] (defaut dagre)
.venv/bin/python scripts/vec_decode.py   # 13 illustrations vectorielles
                                             # (bloc 3) -> docs/vectors/*.svg
                                             # [--out DIR] [--mono] [--scale N]
SOLVER_DB=build/sim/cover.db .venv/bin/python scripts/solver.py \
    --seed NOM --goal coverage --budget B   # BFS depuis un checkpoint
make                 # app web (WASM) : check + shims + wasm + assets
make native          # CLI natif (sim65 embarqué) : build/native/hobplay
make test            # boot + commandes en Node (sans navigateur)
make serve           # http://localhost:8000 (HMR) ; doc : docs/web-wasm.md
```

## 7. État et pistes

- Bloc 4 (`$2C00`–`$7A80`) : checker PROPRE — 17 490 o de code (87 %), 108
  sites `$440D`, 0 conflit. 8 pointeurs nuls (`$3CB7 $4DFC $4E30 $52C6
  $5BB8 $631D $63C1 $6C2C`) = adresses résolues à l'exécution (TODO dans le
  listing). Verbes sans objet `$6FAC` : handlers nommés `action_*` (cf.
  `hobbit.ctl` map `#ACTION`).
- Bloc 1 (`$0400`–`$04FF`) : bootstrap/chargeur cassette — checker PROPRE,
  182 o de code (3 plages), round-trip byte-identique. Vecteurs ROM 1.0/1.1
  `$0405`–`$0416`, `b1_load $0417`, `b1_start $047C` ; blob de patch ROM
  `$0468`–`$047B` (donnée). Détails : `docs/tape-archive.md`.
- Bloc 2 (`$0500`–`$2BBD`) : **données** (aucun code 6502) — checker PROPRE
  (règle D désactivée), round-trip byte-identique (9918 o). Partition typée +
  labels : dico (`dict`), 32 mots courants (`common_words`), messages
  (`messages`), clés/états (`state_keys`/`states`), records
  (`rec_table`/`records`), sorties (`dir_names`/`exits_ext`), INDIR + scripts
  VM + events + entités. Listing `disasm/block2.asm` (12 plages, 114 labels).
  Détails : `docs/tape-archive.md`.
- Bloc 3 (`$7AC0`–`$91B1`) : **données** (aucun code 6502) — checker PROPRE
  (règle D désactivée), round-trip byte-identique (5874 o). Banque
  d'illustrations vectorielles : table à clés `$7AC0` (13 entrées
  `[clé,lo,hi]`, `$FF` en `$7AE7`) + 13 flux `$00`-terminés (`img_<clé>`),
  tuilés `$7AE8`→`$91B1`. Moteur `vec_*` en bloc 4 ; décodeur
  `scripts/vec_decode.py`. Listing `disasm/block3.asm`. Détails :
  `docs/tape-archive.md`.
- Round-trip ca65 prouvé (byte-identique) : les 4 blocs, et `--all` recolle
  l'image complète `$0400`–`$91B1` (36274 o, 4 blocs + 129 o de remplissage
  `$00` dans les trous `$2BBE-$2BFF`/`$7A81-$7ABF`) = `data/hobbit.bin` ;
   harnais sim65 fonctionnel :
   `src/6502/shim.s` (clavier + dumps d'écrans via paravirt, en `$C000`),
  boot validé jusqu'au prompt (`You are in a comfortable tunnel like hall`,
  `> LOOK.`), entrées scriptées + réponses parser observées
  (`I DO NOT KNOW THE WORD " OOK."`), écho caractère par caractère OK.
- Détails à jour : `docs/status.md`, `docs/block4-analysis.md`,
  `docs/tape-archive.md`, `docs/tape-format.md`, `docs/web-wasm.md`.
- **App web WASM** (`web/`, UI + outillage Node) + **émulateur** (`src/` :
  `core/` moteur C portable, `native/` CLI natif, `6502/` shims ASM,
  build par le `Makefile` racine → `build/{native,wasm,shims}`) : jeu jouable
  dans le navigateur + état live
  (objets/PNC), carte et illustrations vectorielles. Cœur sim65 compilé par
  `emcc` ; les scripts `sim_pack/sim_play/memmap_defs/map_static/vec_decode`
  sont portés en C (zéro Python au runtime). Build/HMR/test :
  `make [native|test|serve]` ; détails et limites : `docs/web-wasm.md`.
- Pistes : AnimTalk (parser, via harnais) ; AnimAction (PNJ autonomes :
  l'init recopie une table `$28E6`+ vers le workspace haut — base de données
  jeu probable) ; zéro-page nommée (51 `ZP_NAMES`) ; bloc 3 élucidé
  (13 illustrations vectorielles, table `$7AC0`, moteur `vec_*`) ; bloc 2
  messages élucidé (600 mots `$0540`, 32 courants `$1117`, 171 messages,
  29 lieux `$18AA`) ; records lieux cartographiés (table `$2070`, desc +8,
  exits étendues `$26DA`+wid*8, états `$1A62`) ; scripts `$29xx` décodés
  (VM `$4ED5`, 14 entités + 3 dormantes, table `L7143` = 18 mots dont 3
  inédites) ; SAVE/LOAD élucidés (dispatch `$3BC6`, handlers `$3D7F`/`$3DD9`,
  4 blocs cassette) ; ensuite : stub cassette B1 puis jeu tour-par-tour.
