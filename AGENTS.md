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
`$0400`–`$91B1`) via `scripts/extract.py`.

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

- **Ne jamais éditer `disasm/block4.asm`, `disasm/hobbit.info` ni les sources
  `src/*.s` à la main.** Le modèle vient de `scripts/disasm.py` (descente
  récursive + `MANUAL_ENTRIES` / `SEED_EXCLUDE` arbitrés à la main). Toute
  correction = patch du script + régénération + re-vérification.
- **Avant chaque commit : `scripts/check_disasm.py` doit sortir exit 0**
  (`RÉSULTAT: PROPRE`).
- **Documenter les routines via `ROUTINE_DOCS` dans `scripts/disasm.py`**
  (nom + résumé une ligne → labels/commentaires régénérés dans le listing),
  jamais en éditant `block4.asm`. Détails longs → `docs/block4-analysis.md`
  (référencés par adresse).
- **Aucun test sim65 sur un build non byte-identique.**
- Ne pas créer de nouveaux fichiers `.md` sauf demande explicite.
- `tools/cc65/` (toolchain vendue, ~350 Mo) est gitignoré et le reste.

## 5. Conventions binaire connues (à respecter)

- `JSR $440D` + mot inline = adresse du message ; reprise du code à JSR+5.
  Queue : `JSR $4737` / `JMP ($6A)`, helper `$44BE` (`INC $6A`).
- Table de 16 vecteurs `JMP` en `$2C05`–`$2C34` (API interne) ; le bloc 4 n'use
  le hardware que via les vecteurs du bloc 1 (`$0405`–`$0417`, patchés selon
  ROM 1.0/1.1). **Zéro appel ROM direct dans le bloc 4** (vérifié, checker E).
- `STA $6A5C` = auto-modification (octet patché, relu par `LDA $6A5C`) :
  garder l'octet en donnée, le code reprend à `$6A5E`.

## 6. Recettes

```
.venv/bin/python scripts/extract.py          # TAP -> data/hobbit.bin
.venv/bin/python scripts/disasm.py           # -> disasm/hobbit.info + block4.asm
.venv/bin/python scripts/check_disasm.py     # viser exit 0 (RÉSULTAT: PROPRE)
.venv/bin/python scripts/rebuild.py          # round-trip ca65+ld65 (build/block4.cfg),
                                             # byte-identique exigé, exit 0
.venv/bin/python scripts/pack_sim.py [--hires]  # image sim65 (/tmp/hobbit.sim) :
                                             # shim I/O + patch $7353 + charset ROM
./tools/cc65/bin/sim65 -x N /tmp/hobbit.sim < input.txt > frames.bin
.venv/bin/python scripts/decode_frames.py frames.bin   # écrans -> texte
```

## 7. État et pistes

- Bloc 4 (`$2C00`–`$7A80`) : checker PROPRE — 15 692 o de code (78 %), 79 sites
  `$440D`, 0 conflit. 6 pointeurs nuls (`$3CB4 $4DF9 $4E2D $52C3 $5BB5 $631A`) =
  adresses résolues à l'exécution (TODO dans le listing).
- Round-trip ca65 prouvé (byte-identique) ; harnais sim65 fonctionnel :
  `harness/shim.s` (clavier + dumps d'écrans via paravirt, en `$C000`),
  boot validé jusqu'au prompt (`You are in a comfortable tunnel like hall`,
  `> LOOK.`), entrées scriptées + réponses parser observées
  (`I DO NOT KNOW THE WORD " OOK."`), écho caractère par caractère OK.
- Détails à jour : `docs/session-status.md`, `docs/block4-analysis.md`,
  `docs/tape-archive-hobbit-1982-analysis.md`, `docs/tap-format.md`.
- Pistes : AnimTalk (parser, via harnais) ; AnimAction (PNJ autonomes :
  l'init recopie une table `$28E6`+ vers le workspace haut — base de données
  jeu probable) ; nommer la zéro-page ; bloc 2 (messages `$1370`/`$165A`/…)
  et bloc 3.
