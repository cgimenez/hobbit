# Journal d'aventure — The Hobbit (Oric), joué sous sim65

Partie **100 % aveugle** : aucune connaissance extérieure mobilisée pour
décider des coups (ni histoire, ni carte). Les lectures de code existent
par ailleurs mais ne guident aucun coup — vérification après coup
uniquement. Mode rapide (`--fast`, `$56=0`, sans images) sauf mention.

Conventions : `> COMMANDE.` = écho jeu ; tick = commande réussie.

## Carte (lieux visités)

- `$01` tunnel (départ) : hall confortable, porte verte ronde à l'est,
  coffre bois, Gandalf + carte curieuse, Thorin. Sorties testées : EST
  (→ terre morne, OK).
- `$??` terre morne (à l'est du tunnel) : `gloomy empty land with
  dreary hills ahead`, porte verte ronde à l'ouest, sorties
  est/nord/nord-est (non testées). Gandalf+Thorin suivent (`enters`).
  Contenu : `nothing` (au LOOK d'arrivée).

## Séance 0 — calibration du mode rapide (2026-10-08)

- `pack_sim.py --fast` : patch `$2C4A` (`01`→`00`, `$56=0`, `img_show`
  no-op). Image `build/sim/hobbit_fast.sim` (stock inchangée).
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

## Séance 1 — traversée test + est (2026-10-08, run `build/sim/seance1.bin`)

`OPEN CHEST` → `You open the wooden chest.` (et sur le même tick,
Gandalf ouvre la porte : `Gandalf opens the round green door.`) ;
`GET MAP` → `YOU ARE ALREADY CARRYING THE MAP.` (donnée au boot) ;
`OPEN DOOR` → `THE DOOR IS OPEN.` (déjà ouverte par Gandalf) ;
`EAST` → `You go east.` → terre morne (voir Carte).
À l'arrivée : `Gandalf enters.` + `Thorin enters.`, puis
`Gandalf takes the curious map.` (il reprend la carte !).
Leçon : les PNJ ouvrent/agissent seules — ne pas refaire leurs gestes.

## Séance 2 — (à jouer) cartographie est/nord/nord-est

Depuis la terre morne : `EAST`, `NORTH`, `NORTHEAST` un par un
(`LOOK` à chaque lieu). Save B1 quand dispo.

## Questions ouvertes (jeu)

- Que font Gandalf/Thorin sur plusieurs centaines de ticks ?
- Lieu 5 (trolls, dialogue `BLIMEY`) : où, quand ?
- Dormants `$42`/`$46`/`$3C` : déclencheurs en jeu ?
- Identité des entités rencontrées (noms via `LOOK`) ?
