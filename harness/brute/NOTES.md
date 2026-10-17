# harness/brute — émulateur 6502 C++ pour brute-force (The Hobbit, Oric)

Prototype **hors build jeu** : sert à vérifier une séquence gagnante
cold-boot et à la rejouer vite (multithread). Ne fait pas partie de la
toolchain imposée (AGENTS.md §3) ; code expérimental.

## État : GAGNÉ depuis cold boot (déterminisme ×3)

`harness/brute/win_seq.txt` = 111 commandes, fin par `PUT TREASURE` ->
`A cheering crowd of dwarves, hobbits and elves appears ... You have
mastered 80.0% of this adventure.` (message de victoire documenté :
`docs/game_solution.md:189`, `docs/status.md:690`, `docs/journal.md:499`).

Reproduction (ému) :
```
make -C harness/brute brute search
./harness/brute/brute . build/sim/hobbit_fast.sim < harness/brute/win_seq.txt
```

## Cause racine du « blocage façade » (résolue)

`wait_for_key` ($7481) = pause « appuyez sur une touche ». Le jeu fait
`jsr get_key` ($7353) en boucle **sans réafficher de prompt `>`**. Ni le
harnais Python (`Session`, `/tmp/hobplay.py`) ni le WASM ne modélisaient
cette attente -> boucle jusqu'au budget (stall « façade »). En interactif,
le harnais renvoyait la commande suivante comme 1er octet -> désync.

- Ému : `kb_maysuspend` suspend aussi sur ret∈[$7481,$7486]
  (`in_readkey`), et `play_turn` injecte un CR sacrificiel si pas de `>`.
- WASM : auto-touche CR posée dans `web/cpu/web_main.c::hob_run`
  (check `Regs.PC==0x7353 && ret==0x7483` -> `io_key_push(0x0d)`).

## Clés de parité ému vs sim65 (PROUVÉ bit-identique)

- `S=$00` au reset (sim65 `Reset()` ne touche pas SP ; Regs global = 0).
  `S=0xFF` casse le RNG (lit `noise=$0100` résiduel) -> divergence dès le
  boot. C'était LE bug.
- RAM initiale : `$FF` puis image `.sim` (header 12 o, load/exec) copiée.
- Le **vrai shim** $C000 s'exécute (pas de réimplémentation) ; seuls
  `PV_READ $FFF6` / `PV_WRITE $FFF7` sont trapés.
- BCD exact (ADC/SBC décimal).
- Patchs : image `build/sim/hobbit_fast.sim` (déjà `$56=0`) ; `is_sim`
  saute les patchs (déjà appliqués par `sim_pack.py`).
- Parité mesurée : mémoire initiale, régions SAVE ($00BE/$1B1A/$28CC/$211A)
  au boot ET après tour 1 = identiques ; texte 45 tours identiques vs
  `Session` Python (interactif sim65).

## Cadrage corrigé : même core sim65, glue différente

Point important (2026-10-17) : le WASM **embarque le core sim65**
(`tools/cc65/src/sim65/{6502,memory,peripherals,...}.c`) — **même code** que
sim65 natif. Ce que le WASM **remplace**, c'est la *glue* : `web/cpu/
web_main.c` + `web/core/io.c` remplacent `sim65/main.c` + `sim65/paravirt.c`
(modèle d'entrée, arrêt de tour, capture), et `web/core/hobbit.c` applique
le jeu de patchs. Donc : core CPU/mémoire = identique (sim65) ; harness/glue
= différent ; `emu.cpp` (celui qui gagne) = **3e moteur custom**, PAS sim65.

=> Les pièges emcc (mémoire non init, pile, UB, bitfields, `long`=4o,
horloge) s'appliquent au core partagé. Vérifs rapides : `CPURegs` = entiers
simples (pas de bitfields) ✓ ; `MemInit()` memset `$FF`, appelé par
`hob_init` ✓ ; `ALLOW_MEMORY_GROWTH=0` ✓ ; core entier pur (pas de
flottants) ✓. Suspect restant : la **glue** (timing d'entrée / segmentation)
qui décale l'horloge d'événements du jeu.

### GAP critique
`win_seq.txt` a été trouvé/validé sur **`emu.cpp`** (custom), **pas** sur
sim65. À revalider sur sim65 natif avant de conclure : si sim65 diverge
d'`emu.cpp`, win_seq ne transfère pas.

### Test décisif proposé
Faire tourner **sim65 natif** et le **WASM** depuis le **même état**
(checkpoint `SLVW`) + **même flux clavier**, différent le texte tour par
tour : divergent → glue WASM/artefact compilation ; identiques → c'est
`emu.cpp` qui dévie. Note : piloter sim65 natif **froid** scripté est non
trivial (`play.sh` interactif ; `solver_run.py` = `SLVW.sim` + keystream
stdin). Reconstruire une image *cold solver* = ajouter le support `--solver`
sans `--snapshot` à `sim_pack.py` (= exactement l'image du WASM).

## PROBLÈME OUVERT : divergence WASM vs ému

Le WASM (`web/`, sim65 source) emprunte un chemin DIFFÉRENT : `hob_run`
rend rc=1 (budget épuisé = boucle infinie) avec le PC, à l'épuisement, dans
le **parseur/dispatch jeu** — `word_dispatch` ($4683-$4782 : $4743, $46E6,
$4714, $4724) et `code_4F3F` ($4F3F-$5184 : $524F, $4F6D, $5212, $525E) —
(jamais dans la couche clavier).

Mesures (diag `hob_shim_count`/`hob_kb7353_count`) : le WASM appelle le shim
clavier $C000 **1665×** (= autant de `PC==$7353`), mais `autokey=0` : il
n'atteint **jamais** `get_key` depuis `wait_for_key` (ret hors $7481-$7486).
Pendant les stalls, les compteurs shim/kb7353 sont **figés** -> le jeu ne
lit plus aucune touche : c'est une boucle de calcul pur.

Repère : sur `win_seq.txt` (identique ému/WASM), les deux moteurs produisent
le même texte jusqu'à « The forest gate » (lieu `$18`). L'ému enchaîne
(`WEST` → « Beorns house » → … → victoire, **68 M insns au total**) ; le WASM
boucle dans le parseur et ne revient jamais au prompt (`rc=1 lieu=$18`
pour toutes les commandes suivantes).

Conclusion (CORRIGÉE le 2026-10-17, voir § pivot Path 1 en fin de fichier) :
ce n'était NI `wait_for_key` NI la glue d'entrée. À même cœur `emu.cpp`,
l'image classic gagne et l'image solveur stalle (turn 52, lieu `$42`) :
c'est l'IMAGE (octets du shim `$C000`), car le RNG du jeu (`rand_range
$56D7`) échantillonne la mémoire brute via `(noise),y` (`$93`/`$94`,
pas de 256 o → couvre tout, y compris `$C0xx` vers les tours 40-45).
Shims classic/solveur différents → RNG forké → elfe absent au tour 52.
`$02` (`$FB` vs `$20` dès tour 0) est un résidu bénin (forcer `$FB` ne
change rien, icount identique). `win_seq.txt` est classic-RNG-spécifique.

Bug latent corrigé au passage : le check autokey testait `ret==$7483` ; le
`jsr get_key` de `wait_for_key` ($7481) a pour retour **$7484** (plage
`in_readkey` $7481-$7486 côté ému). Sans effet ici (ret jamais dans la
plage), mais à garder correct.

Pistes (MAJ 2026-10-17) : voir § pivot Path 1 en fin de fichier.
Historique : l'hypothèse glue (`io.c` vs `play_turn`) est abandonnée
(preuve : même cœur emu, seule l'image change le résultat).
- Diag temporaire en place : `hob_autokey_count`, `hob_last_pc`
  (`web/cpu/web_main.c`, `web/include/hobbit.h`), `web/smoke.mjs` patché
  (log STALL pc=...). À retirer/nettoyer une fois résolu.

## Nettoyage à faire (diag temporaire)

- `web/cpu/web_main.c` : `AutokeyCount`, `hob_autokey_count`, `hob_last_pc`.
- `web/include/hobbit.h` : exports diag.
- `web/smoke.mjs` : logs `autokey`/`STALL`.
- `harness/brute/emu.cpp` : ring-buffer/DUMP/WP/KBLOG (garder ou retirer
  selon usage).

## Fichiers

- `emu.cpp`/`emu.h` : 6502 + paravirt + snapshot + entrée déterministe.
  CONSERVÉ en fallback jusqu'à victoire validée sur sim65 (suppression
  prévue Phase 1.3, choix C validé).
- `main.cpp` : driver replay (`brute <cmds.txt`, tour séparé par
  `@@@TURN@@@` ; `@RAW x` = octet brut ; `lieu=$XX` par tour).
- `search.cpp` : pool 11+1, snapshot dale, juge texte (WIN/HALLS/DRAGON/
  GATE/LOC/SAME/STALL/DEAD), `candidats.txt` (suffixes `|`-séparés).
  REMPLACÉ par `scripts/sim_search.py` (moteur unique sim65).
- `win_seq.txt` : séquence gagnante **classic-RNG** (111 cmds, ému seul).
- `win_seq_solver.txt` : CANDIDATE solveur (112 cmds = win_seq lignes 1-51
  + `WAIT×3` + lignes 54-111 ; capture pendant WAIT prouvée, fin NON validée
  — run complet interrompu). Recette : voir § pivot.
- `Makefile` : `make -C harness/brute brute search`.
- `scripts/sim_search.py` : recherche parallèle à FROID sur sim65
  (remplace search.cpp) : `--prefix/--candidates/--workers`, stdin=PIPE
  tenu ouvert (pas d'EOF → pas de WAIT idle), kill sur echo+prompt,
  verdicts WIN/HALLS/DRAGON/GATE/LOC/DEAD/STALL/SAME/ERR.
- `scripts/sim_cold.py` : pilote froid tour-par-tour (PTY) — DÉPASSÉ par
  l'approche pipée + monitor de sim_search.py (sim65 trop lent en
  interactif) ; à supprimer lors du nettoyage.
- `scripts/sim_pack.py` : `--solver` seul → `build/sim/hobbit_solver.sim`
  (image froide solveur = octets du WASM hors glue : shim `-D SOLVER`,
  hooks `$C0B8/$C104/$C135`, pause `$7628` neutralisée, `$56=0`).
- `sav/SLVW.bin` : STALE (run_one depuis ce blob = texte incohérent /
  `snap-incomplet`) ; ne pas utiliser — racine froide `run_one(None,None)`
  validée à la place.

## État des fichiers modifiés (non commités)

`harness/brute/*` (dont `win_seq_solver.txt` nouveau), `scripts/sim_pack.py`,
`scripts/sim_search.py` + `scripts/sim_cold.py` (nouveaux), `web/cpu/web_main.c`,
`web/include/hobbit.h`, `web/smoke.mjs` (diags temporaires), `docs/journal.md`
(Séances 14-15). Gardes AGENTS.md (`disasm_check`, `memmap_check`,
`rebuild --all`) : PROPRE le 2026-10-17 (à repasser avant commit).

## 2026-10-17 — pivot Path 1 : recherche sous solveur (ÉTAT REPRISABLE)

Décision validée : **C (moteur unique sim65 multiprocessus)** puis
**Path 1 (re-chercher sous solveur)** — PAS Path 2. Motif : Oric-1 vs Atmos
(`data/basic10.rom` vs `data/basic11b.rom`) diffèrent à 96 % y compris aux
positions échantillonnées → le jeu est robuste aux variations RNG ; notre
stall = script rigide sur-ajusté, pas jeu cassé. Inutile (et fragile) de
répliquer le RNG exact ; chercher une trajectoire gagnante sous RNG-solveur.

Recette reprise exacte :
1. `make -C harness/brute brute` (fallback, ne pas supprimer avant victoire sim65).
2. `.venv/bin/python scripts/sim_pack.py --solver` → `build/sim/hobbit_solver.sim`.
3. Réparation locale type (capture elfe) :
   `.venv/bin/python scripts/sim_search.py --prefix /tmp/pre51.txt --candidates /tmp/crepair.txt --workers 5 --timeout 420`
   avec `pre51.txt` = win_seq lignes 1-51, `crepair.txt` = variantes
   (`EAST`, `WAIT|EAST`, …). Résultat : `WAIT×3` → elfe entre + capture
   pendant WAIT → donjon (EAST suivant inutile, échoue proprement).
4. `win_seq_solver.txt` = lignes 1-51 + `WAIT×3` + lignes 54-111 (construit,
   fin à valider) :
   `.venv/bin/python -c "lines=[l.rstrip() for l in open('harness/brute/win_seq.txt') if l.strip()];open('harness/brute/win_seq_solver.txt','w').write('\n'.join(lines[:51]+['WAIT']*3+lines[53:])+'\n')"`
5. Validation froide complète (RESTE À FAIRE, ~5-10 min) :
   adapter `cold_run` de `sim_search.py` en run unique sur les 112 cmds
   (ou boucle `sim_search.py --prefix` vide + 1 candidat full), chercher
   `cheering crowd`. Si stall plus loin (ex. Bard ~tour 76 : dragon tôt,
   `Bard says " No "`) → nouvelle campagne locale depuis le parent du
   point de divergence, même méthode.
6. Une fois victoire sim65 validée : `solution.js` ← séquence validée,
   glue WASM, suppression diags web + `emu.cpp`, commit (gardes vertes).

Pièges connus (ne pas retomber dedans) :
- `run_one` (solver_run.py) NE rejout PAS une trajectoire exacte : LOAD/SAVE
  + pads + discontinuité RNG (SAVE ne couvre pas `$93/$94`, `L570E`) →
  diverge dès ~tour 47. Réservé aux nœuds BFS unitaires.
- stdin FICHIER (EOF) → poll serré → auto-WAIT idle authentique qui pollue
  (morts troll). Toujours stdin=PIPE tenu ouvert + kill sur echo+prompt.
- sim65 lent via PTY/python (~13 o/s) ; pipé + monitor = rapide (~1 s/tour
  début). `sim_cold.py` PTY = trop lent, dépassé.
- `sav/SLVW.bin` stale ; `search.cpp` obsolète (remplacé) ; binaires
  `harness/brute/brute|search` = artefacts non suivis.
