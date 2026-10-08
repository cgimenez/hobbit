# Journal d'aventure — The Hobbit (Oric), joué sous sim65

Partie **100 % aveugle** : aucune connaissance extérieure mobilisée pour
décider des coups (ni histoire, ni carte). Les lectures de code existent
par ailleurs mais ne guident aucun coup — vérification après coup
uniquement. Mode rapide (`--fast`, `$56=0`, sans images) sauf mention.

Conventions : `> COMMANDE.` = écho jeu ; tick = commande réussie.

## Carte (lieux visités)

- `$01` tunnel (départ) : hall confortable, porte verte ronde à l'est,
  coffre bois, Gandalf + carte curieuse, Thorin. Sorties testées : —
  (à suivre : EST après ouverture).

## Séance 0 — calibration du mode rapide (2026-10-08)

- `pack_sim.py --fast` : patch `$2C4A` (`01`→`00`, `$56=0`, `img_show`
  no-op). Image `/tmp/hobbit_fast.sim` (stock inchangée).
- Correction : le `N` du boot ne désactive rien (`L2C3D` morte depuis
  `start` : `LDX #$FF` / `BNE L2C49` → `$56=1` toujours ; `L2C3D`
  ne vit que via QUIT). `$56` n'est écrit nulle part ailleurs.
- Mesure : 500×`WAIT` + dumps complets (frames+MEM, ~24 Mo) en **3,4 s**
  mur (budget `-x 2000000000` : script consommé en entier, preuve =
  `SCORE` final atteint, `mastered` affiché ; fin en spin EOF).
- Texte lu par OCR hires (`decode_frames.py`) — les dumps `@@FRAME
  text` bruts sont des pixels quand l'Oric est en mode hires.
- Piège : pause toutes les 16 CR → touche sacrifiée `\r` tous les
  8 `WAIT` (2 CR/WAIT). Écho persistant (~18 captures/ligne) :
  compter les exécutions par événements, pas par occurrences.
- Observé (gratuit) : Gandalf ouvre la porte, `goes east`, prend la
  carte ; Thorin `waits`/`enters` ; PCs entités et `$2Bxx` progressent
  en MEM (détail : `decode_mems.py`).

## Séance 1 — (à jouer) traversée test + est

`OPEN CHEST`, `GET MAP`, `OPEN DOOR`, `EAST`, puis cartographie :
chaque lieu = sorties essayées une par une. Save B1 quand dispo.

## Questions ouvertes (jeu)

- Que font Gandalf/Thorin sur plusieurs centaines de ticks ?
- Lieu 5 (trolls, dialogue `BLIMEY`) : où, quand ?
- Dormants `$42`/`$46`/`$3C` : déclencheurs en jeu ?
- Identité des entités rencontrées (noms via `LOOK`) ?
