# AUTO PLAY (web/WASM) — échec du rejeu de la solution : diagnostic

Statut : **FERMÉ (résolu 2026-10-17)**. AUTO PLAY gagne désormais :
`cheering crowd of dwarves … mastered 70.0%`, cold boot, 107 commandes,
natif ET WASM (RAM byte-identique tour par tour, `scripts/mem_diff.py`).
La cause n'était **pas** le moteur WASM (innocenté : natif==WASM à l'octet)
mais **la liste** + **le shim** :
- `solution.js` (98 cmds) n'a jamais été gagnante (il manque le padding de
  phase : 13 `WAIT` devant la porte, ordre trésor/dragon inversé, etc.) ;
- le seul gagnant connu (`win_seq.txt`, 111 cmds) avait été validé sur le
  **shim classic** + émulateur custom, jamais sur le **shim solveur** du web
  (le shim forge le RNG via `$C0xx` : sous solveur, la capture elfe et la
  phase butler/porte diffèrent).
Correction (`web/ui/solution.js`, 107 cmds) : SW immédiat en sortie `$1F`,
3e `WEAR RING`→`WAIT`, marche directe `$24→$25→$26→$27→$29` (Bard ne guide
pas mais `SAY SHOOT` depuis `$24` tue le dragon ; le trésor est en `$29`).
L'hypothèse §4 (quiescence) est **infirmée** : premier-`@@P` suffit, la
quiescence ajoutait un `WAIT` fantôme (cf. `docs/protocol.md` §6).
Détails : `docs/journal.md` séances 14-15 (win_seq), 17-18 (adaptation).

--- document d'origine (conservé pour traçabilité) ---

Statut : **ouvert**. Le bouton AUTO PLAY (commit `ecae669`) rejoue
`web/ui/solution.js` sur l'émulateur WASM, mais **ne gagne pas** : la séquence
défile en entier dans le vide. Ce document fige les faits mesurés et la piste
de correction, pour reprise après compaction.

## 0. Décisions actées (utilisateur)

1. État de départ = **cold boot** (pas de checkpoint).
2. **Seeder depuis `sav/*.bin` = magouille** → interdit.
3. Correction souhaitée = **reproduire le protocole du harness** (pas
   d'adaptatif conditionnel, pas de rustine).
4. « Aucune raison que ça marche en local (harness) et pas en WASM » → le but
   est de rendre le WASM fidèle, pas de contourner. On **ne retire pas** le
   bouton.

## 1. Le problème en une phrase

`docs/game_solution.md` Annexe 2 est une trajectoire **verrouillée sur la
phase de ticks** du monde, vérifiée sous le harness natif (protocole
`scripts/solver_run.py`). Le WASM rejoue les mêmes commandes mais **dans un
autre modèle d'exécution**, donc la phase diverge et les portes pilotées par
les PNJ tombent au mauvais moment.

## 2. Faits mesurés (reproductibles)

### 2.1 Ce n'est PAS un bug de patch ni d'image
`src/core/hobbit.c` applique les **mêmes** patchs que l'image harness vérifiée :
`$2C4A`=00 (`$56=0` fast, sans illustrations), pause `$7628` = `A9 00 EA`
(neutralisée), stubs cassette `$2C0B/$2C0E/$2C11`, hook clavier `$7353`, hooks
texte `$75B8/$7694/$7514`. Le checker `make check` garde les octets
source. **Rien à corriger de ce côté.**

### 2.2 Bug parser (réel, indépendant du WASM)
Le parser de **cette** édition Oric mappe mal les diagonales *écrites* :
- `SOUTHWEST` → « YOU CANNOT GO **SOUTH** »
- `NORTHWEST` → « You go **NORTH** »
- (`SOUTHEAST`/`NORTHEAST` écrits, eux, marchent.)

Le harness vérifié utilise les **abréviations** : `docs/game_solution.md`
Annexe 1 dit explicitement `NORTH\rSW`, et `routes/*.txt` n'emploient que
`SW/SE/NE/NW`. Donc la table du doc (mots en clair) est une normalisation
humaine : la recopier telle quelle injecte des commandes non fonctionnelles.
→ `solution.js` doit utiliser les abréviations pour les diagonales.

### 2.3 Anti-mange de la clairière
`NORTH` puis `SW` doivent partir **dans le même run** (`NORTH\rSW`) : sinon le
troll hideux mange le joueur (tour fatal à la clairière `$05`).

### 2.4 L'annexe n'est PAS un script « from boot » portable
Rejeu **natif** brut (pipe) de la séquence → échoue **aussi** : le `SW` est
mangé (`> .` ligne vide) → mort à la clairière (`mastered 2.5%`). La commande
native utilisée :
`./tools/cc65/bin/sim65 -x 6000000000 build/sim/play.sim < flux.bin | .venv/bin/python scripts/sim_play.py out.bin`
⇒ l'annexe dépend du **protocole** du harness (un run par commande, attente
d'inactivité, touches sacrificielles), pas juste des octets d'entrée.

### 2.5 Jusqu'où va le WASM avec 2.2 + 2.3
Avec abréviations + anti-mange, le WASM va **beaucoup plus loin** : il atteint
le donjon elfe `$1F` (capture par l'elfe des bois), puis **bute sur la porte
rouge** — elle s'ouvre après **~11 `WAIT`** chez nous, **1** dans le doc.
⇒ décalage de **phase** (elfe/butler = PNJ pilotés par les ticks), pas un bug
bloquant.

### 2.6 Seed checkpoint = incohérent (piste écartée)
Charger `sav/SLVW.bin` (magic `SNAP`) via le slot BLOB puis `LOAD` : le statut
dit « sauvegarde locale restauree » mais l'état est incohérent (lieu `$00`,
texte tronqué `THE CANNOT OPEN THE D ARGE CHEST`). De toute façon **écarté par
décision** (§0.2).

## 3. Modèle d'exécution : harness vs WASM

| | Harness natif (`solver_run.run_one`) | WASM (`src/core/core.c` : `hob_run`) |
|---|---|---|
| Unité | 1 commande = 1 process `sim65` | 1 commande = 1 `hob_run()` |
| Entrée | payload complet (blancs + `LOAD` + cmd + blancs + `SAVE`) écrit d'un coup | file clavier remplie puis `hob_run` |
| Fin de tour | attente « silence » (prompt, plus d'activité) | arrêt au **premier** `@@P` (prompt) |
| État monde | restauré par blob (SAVE/LOAD par nœud) | continu (mémoire persistante) |
| Boot | run « root » : page-turn + blancs + SAVE | `hob_boot()` = 2 prompts, file vide |

`build_cmd` (racine) : `["","","SAVE"] + blancs` ; (nœud) :
`["","","LOAD"] + blancs + ["","",cmd] + blancs + ["","SAVE"] + blancs`.
Chaque ligne vide = un **tour** → avance le monde (donc la phase !).

Touches sacrificielles : le harness natif (image non-solver / `play.sim`) a
besoin d'une ligne vide après chaque sortie longue, sinon `pause_key` mange le
1er caractère de l'ordre suivant (`SOUTH`→`UTH`). Le WASM neutralise
`pause_key`, mais **la cadence de tours reste le vrai sujet de phase**.

## 4. Hypothèse de la cause racine

Le WASM consomme un nombre de **tours/ticks différent** du harness avant et
pendant le rejeu :
- au **boot** : `hob_boot` court avec file vide jusqu'à 2 prompts ; le harness
  root envoie des lignes (tours) ;
- en **cours de rejeu** : le WASM s'arrête au prompt (pas d'« attente
  d'inactivité ») et, pour l'anti-mange, **court volontairement au-delà d'un
  prompt** (cf. `hob_run` modifié : continue tant que la file clavier n'est pas
  vide) → risque d'**auto-`WAIT`** parasite = tours fantômes → décalage.

Conséquence : d'abord la capture de l'elfe se fait un tour plus tard, puis la
porte rouge est dans la mauvaise moitié de son cycle.

## 5. Piste de correction (à implémenter)

Rendre le WASM fidèle au **protocole harness**, à modèle d'exécution constant :
1. **Un tour = un run borné** avec « attente d'inactivité » : ne rendre la main
   que sur prompt **stable** (plus aucun `@@A`/`@@P` émis pendant N instructions)
   — pas au premier `@@P`.
2. **Injecter la ligne + les touches sacrificielles** comme le harness (ligne
   vide avant/après), pour absorber la pause et aligner la cadence.
3. **Boot identique** au root : reproduire la séquence de page-turn/blancs du
   boot (nombre de tours) au lieu du `hob_boot` à file vide.
4. Vérifier par **diff de transcription** natif↔WASM sur le même flux.

À valider empiriquement : après (1)-(3), la capture elfe doit se faire sur
**1** `EAST` et la porte rouge s'ouvrir après **1** `WAIT` (comme le doc).

## 6. État du code (working tree, NON commité)

- `web/ui/solution.js` : liste **nue** (98 entrées), abréviations diagonales +
  `NORTH\rSW` ; commentaires expliquant 2.2/2.3. **Pas d'adaptatif.**
- `web/ui/app.js` : autoplay **simple** (string-only). `EXPECTED_VICTORY =
  'cheering crowd of dwarves'` (l'ancien `mastered 70.0` matchait aussi le
  résumé de **mort** → faux positifs).
- `src/core/io.c`/`io.h`, `src/include/hobbit.h`, `src/core/core.c` :
  compteur `@@K` → `hob_keys_consumed()` (diagnostic « commande mangée »).
  À garder ou retirer selon besoin.
- `build/wasm/SLVW.bin` : copie temporaire (gitignoré).

Déjà commité : `ecae669` (bouton AUTO PLAY + disclaimer + `solution.js`
initial), `b0dc9e5`/`304d60a` docs, etc. Le `solution.js` commité est la
version **fausse** (mots en clair) — à corriger par le travail ci-dessus.

## 7. Repro du diagnostic

Test navigateur headless (Chrome CDP, zéro dépendance) : scripts jetables
`/tmp/opencode/hobdiag.mjs` (rejeu tour par tour + `@@K`/lieu/delta),
`hobprobe.mjs`/`hobprobe2.mjs` (cycle porte rouge `$1F`), `hobwords.mjs`
(mapping des directions), `hobseed*.mjs` (seed, écarté). Motif : `spawn node
web/serve.js build/wasm <port> --no-hmr`, puis pilotage via un hook
`window.__hob` **temporaire** ajouté à `app.js` (pensé à être retiré).

Test natif : `sim65 -x <cycles> build/sim/play.sim < flux.bin | python
scripts/sim_play.py out.bin` (flux = commandes + `\r`).

## 8. Pièges

- `mastered X%` s'affiche **aussi à la mort** → ne jamais s'en servir comme
  test de victoire (utiliser `cheering crowd of dwarves`).
- `SOUTHWEST`/`NORTHWEST` écrits = cassés ; utiliser `SW`/`NW`.
- L'anti-mange exige `NORTH\rSW` dans **le même run**.
- `hob_run` « court au-delà du prompt » si la file n'est pas vide → peut
  déclencher l'auto-`WAIT` (tours fantômes).
