# Journal d'aventure — The Hobbit (Oric), joué sous sim65

Carte exhaustive (statique, 78 lieux) : `docs/map.md`. Ce journal
ne décrit que le terrain vérifié en jeu.

Parties **informées** (depuis 2026-10-08 PM) : fini l'aveugle — coups
décidés en connaissance des commandes (sonde vocabulaire),
PNJ et lieux. Deux images : `build/sim/hobbit_fast.sim` (texte seul,
sim_tickdiff) + `build/sim/hires.sim` (`--fast --hires`, OCR texte).
Cmdfile sim_tickdiff = lignes `\n` (1re = touche boot, `\n`→`\r` par
sim_tickdiff) ; run sim65 brut = mêmes octets en `\r` (`rX.cr`).

Conventions : `> COMMANDE.` = écho jeu (le `.` final est ajouté
par le jeu, jamais tapé) ; tick sim_tickdiff = 1 ligne (même vide :
le prompt-loop tourne — death-check `$00` : un mouvement raté à
`$01` chutes tue au tick suivant, même sur ligne vide) ; tick
monde = 1 commande acceptée (PNJ + timers).

## Carte (lieux visités)

- `$01` tunnel (départ) : hall confortable, porte verte ronde à l'est,
  coffre bois, Gandalf + carte curieuse, Thorin. Sorties testées : EST
  (→ terre morne, OK).
- `$??` terre morne (à l'est du tunnel) : `gloomy empty land with
  dreary hills ahead`, porte verte ronde à l'ouest, sorties
  est/nord/nord-est. Gandalf+Thorin suivent (`enters`).
  Contenu : `nothing` (au LOOK d'arrivée).
- `$05` clairière des trolls (au nord de la terre morne — et à
l'est aussi : `EAST` y mène également) : `You are in the trolls
clearing`, sorties sud-ouest/sud-est/nord.
`the hideous troll` (porte `the large key` = clé `$04`) +
`the vicious troll`. À l'entrée : `The hideous troll says "
Blimey, looks at this !! Can yer cook 'em? ".` +
`The vicious troll says " Yer can try, but he wouldn't make
above a mouthfull ".` Mortel : le hideous mange le joueur au
~3e tick monde de présence (implacable : KILL/TALK/GIVE/THROW/
HIDE/WAIT testés, tous morts). **Sortie : `RUN SOUTH`** (pas
`SOUTH` seul, qui reste sur place) **→ `$09`**.
- `$06` hidden path (au nord-est de la terre morne) : `You are in
a hidden path with trolls foot prints`, `to the north there is
the heavy rock door`, sortie sud, `nothing`. SANS trolls (safe).
`EXAMINE ROCK` → `You examine/see the heavy rock door.` ;
`PUSH ROCK` → `You push.` (sans effet visible) ; `BREAK ROCK`
→ `You strike the heavy rock door.` (tient, contrairement à la
porte verte) ; `OPEN ROCK`/`NORTH` rejetés (0 tick).
- `$09` Rivendell (au sud de la clairière, par `RUN SOUTH`) :
`You are in Rivendell`, sorties est/ouest, `Elrond.` (+ Thorin
suit). `Elrond says " Hello ".` + **`Elrond gives some lunch
to you.`** (clé `$26` : porteur `$FF`→`$00`, eloc `$00`→`$09` =
le lunch). Sorties : `EAST`→`$0A`, `WEST`→`$05` (retour
clairière = mortel). `TALK TO ELROND` accepté ; `EXAMINE
ELROND`/`EXAMINE THORIN`/`EAT LUNCH`/`GIVE LUNCH TO ELROND`
rejetés (0 tick).
- `$0A` Misty mountains (à l'est de Rivendell) : `You are on a
hard dangerous path in the Misty mountains`, sorties
est/nord/ouest/sud, `the vicious warg.` (+ Thorin suit).
`The vicious warg attacks you.` (survécu 1 WAIT ; danger à
mesurer).
- `$0B` (E de `$0A`, libre) → `$0C` (E, libre) → `$16` (E, libre,
sans desc, 5 sorties libres) ; `$0B` N→`$0E` (libre, "LARGE DRY
CAVE", `DOWN`→`$0F` **refusé, cond `$06`** — 2 rythmes testés,
tient).
- `$16` : NE→`$18` (libre, "GATE TO MIRKWOOD"), N→`$31` (libre),
NW→`$31` (**anomalie** : attendu `$14`, obtenu dest de NORTH —
zone sombre à mouvement aléatoire ? à trancher).
- `$18`→`$19` (E, libre) : `$19` "BEWITCHED GLOOMY PLACE", rive
ouest au sud ("fast black river"), `the wood elf.` sur place.
`EAST`→rive (`$42` "WEST BANK") puis **capture par l'elfe :
téléport `$42`→`$1F` (donjon)** + `It is dark.`
- `$44` (N de `$0A`, libre) → E→`$47`, NE→`$45` (libres) ;
`$49` (S de `$0A`, libre) → E→`$4A` → N→`$47` (libres). Hauts
non sombres, sans cond jusqu'ici.
- `$1F` donjon elfe (sombre) : `The wood elf captures you.` +
`It is dark.` + `You hear a noise.` + `Someone locks the red
door with the red key.` (boucle butler). Sorties : SW→`$20`
[cond `$08`], W→`$1E` [cond `$08`], + NE→`$1F` (boucle), N→`$1E`
(libres). **Mouvements = loterie** (`L5F07` : tirage 1..10 + 1er
exit existant, puis cond ; raté = chute `You go somewhere. But
fall…`). `UP`/`SOUTH`/… consomment la fenêtre `$A0`→`$80` et
tombent sauf bon tirage (f10d/f35a : chanceux, pas de sortie
dorée). `SING`/`PUSH RED DOOR` tickent sans bouger (23 deltas,
0 chute — sondes gratuites). **Chasseur `$43`** (record
`$1DD0`, init `$16`) : patrouille `$14`→`$15`→`$16`→`$18`→`$1F`
(+ téléports), tue au contact (`crec=$1DD0` + reboot) —
`UP`-first le déroute/stalle, `(WAIT,SW)` le fait foncer.
- `$1E` (sombre) : `UP`/`SOUTH`/`SOUTHWEST` rebondissent ou
tombent (`You go somewhere. But fall and hit your head.`) ;
rythme `(WAIT,SOUTH)`×N finit par sortir (`$1E`→`$1F` f35a,
`$1E`→`$20` f37c au 3e SOUTH — destinations variables :
**mouvements aléatoires dans le noir**, direction ignorée ?).
- `$20` cellier (sombre, "CELLAR...BARRELS OF WINE") : atteignable
(`$1E` S libre) mais **éjecté au tick-monde suivant :
`$20`→`$1F` forcé** (signature : obj `$BE`→`$30`, +`$0161`
`$01`→`$81`, sans chute — bouncer : butler `$42`, eloc `$20` ?).
Une seule action par visite. `DOWN`→`$21` [cond `$0C`]
**refusé** (chute + éjection) ; `ENTER/BREAK/OPEN/EXAMINE
BARREL` = 0 tick (cible invisible dans le noir). Messages
statiques `$11FA`/`$1206` : `TOO SMALL/TOO FULL FOR YOU TO
ENTER` = `$21` est un **contenant** (tonneau plein).
HELP au donjon : `WAIT AROUND AND TIME YOUR EXIT CAREFULLY.`

## Vocabulaire parser (sondes 63+19+8 verbes, réponses lues)

Connus : OPEN (`OPEN WHAT ?`), CLOSE/LOCK/UNLOCK (`I SEE NOTHING
TO X`), GET/TAKE/LIFT/STEAL (=TAKE), DROP/THROW (=THROW),
GIVE, KILL/ATTACK/HIT (=ATTACK, `ATTACK WHAT ?`), BREAK/SMASH
(=STRIKE, `I SEE NOTHING TO STRIKE`), EAT, DRINK, LIGHT (`You
light.` — ticke (25 deltas) mais n'éclaire pas, et TÉLÉPORTE
`$43` sur le joueur : bannir au donjon), CLIMB, ENTER,
CROSS/SWIM?, DIG, PULL, PUSH (`You push.`), FOLLOW (`FOLLOW WHAT
?`), SLEEP (`You sleep.`), READ=EXAMINE (`EXAMINE WHAT ?`),
SAY=TALK (`TALK TO WHAT ?`), TALK (`You talk to Thorin.`),
SCORE (`YOU'RE DOING FINE.` / `You have mastered X% of this
adventure`), HELP, GO (traverse), RUN/LEAVE (=partir), WEAR,
FILL, EMPTY, TIE, UNTIE, HIDE (`WHAT ?`), TORCH/BARREL/WINE/ROPE
(mots connus, objets absents : `I DO NOT SEE THE X HERE`),
directions NORTH/SOUTH/EAST/WEST/UP/DOWN + N/S/E/W/U/D +
NE/NW/SE/SW (`YOU CANNOT GO X.` sinon).
Inconnus (`I DO NOT KNOW`) : SHUT SHOW FIGHT RUB EXIT SHOUT ASK
TELL SEARCH STAND WAVE KNOCK FEEL SMELL LISTEN BUY SELL STAY
MOVE HELLO LAMP CANDLE LANTERN MATCHES. Ambiguïtés : `WHICH
TROLL ?` (HIDEOUS vs VICIOUS) ; `I DO NOT SEE THE X HERE`
(absent) ; `TALK TO WHAT ?` (personne).
F40a (tunnel, verbes seuls) : `ENTER` ✓ (31 deltas), `SIT`/`SLEEP`
✓ (18, équiv. WAIT) ; `DRINK`/`EMPTY`/`POUR`/`FILL`/`CLIMB` = 0
(mots connus mais sans effet ici).

## Séance 0 — calibration du mode rapide (2026-10-08)

- `sim_pack.py --fast` : patch `$2C4A` (`01`→`00`, `$56=0`, `img_show`
  no-op). Image `build/sim/hobbit_fast.sim` (stock inchangée).
- Correction : le `N` du boot ne désactive rien (`L2C3D` morte depuis
  `start` : `LDX #$FF` / `BNE L2C49` → `$56=1` toujours ; `L2C3D`
  ne vit que via QUIT). `$56` n'est écrit nulle part ailleurs.
- Mesure : 500×`WAIT` + dumps complets (frames+MEM, ~24 Mo) en **3,4 s**
  mur (budget `-x 2000000000` : script consommé en entier, preuve =
  `SCORE` final atteint, `mastered` affiché ; fin en spin EOF).
- Texte lu par OCR hires (`sim_frames.py`) : le texte du jeu
  est blitter en bitmap hires TOUJOURS (même fast) ; l'écran
  texte `$BB80` n'est que du remplissage (`$40` à 83 %, motifs
  périodiques — jamais décodé, inutile). Images `--snapshot
  NOM --hires` + runs directs pacés + OCR = lecture réponses.
- Piège : pause toutes les 16 CR → touche sacrifiée `\r` tous les
  8 `WAIT` (2 CR/WAIT). Écho persistant (~18 captures/ligne) :
  compter les exécutions par événements, pas par occurrences.
- Observé (gratuit) : Gandalf ouvre la porte, `goes east`, prend la
  carte ; Thorin `waits`/`enters` ; PCs entités et `$2Bxx` progressent
  en MEM (détail : `sim_mems.py`).

## Séance 1 — traversée test + est (2026-10-08, run `build/sim/seance1.bin`)

`OPEN CHEST` → `You open the wooden chest.` (et sur le même tick,
Gandalf ouvre la porte : `Gandalf opens the round green door.`) ;
`GET MAP` → `YOU ARE ALREADY CARRYING THE MAP.` (donnée au boot) ;
`OPEN DOOR` → `THE DOOR IS OPEN.` (déjà ouverte par Gandalf) ;
`EAST` → `You go east.` → terre morne (voir Carte).
À l'arrivée : `Gandalf enters.` + `Thorin enters.`, puis
`Gandalf takes the curious map.` (il reprend la carte !).
Leçon : les PNJ ouvrent/agissent seules — ne pas refaire leurs gestes.

## Séance 2 — R5 exploration (informée, `build/sim/r5.txt`)

`EXAMINE CHEST` → `You examine the wooden chest. You see the
wooden chest.` ; `OPEN CHEST` → `You open...` ; `EXAMINE MAP` →
`There seem to be some symbols on it but you cannot read them.` ;
`TALK TO GANDALF` → `I DO NOT SEE THE GANDALF HERE` (parti à
l'est) ; `TALK TO THORIN` → `You talk to Thorin.` (sans réponse
visible) ; `EAST`/`NORTH` → clairière (voir Carte). `EXAMINE
TROLL` → mort (47 deltas = mort+reboot, voir R6) : la suite
(TALK/SOUTH/WEST/SCORE/INVENTORY) s'exécute rebootée au tunnel
(`YOU CANNOT GO SOUTH/WEST.` ✓ tunnel sans sortie sud/ouest).

## Séance 3 — R6 combat (`build/sim/r6.txt`)

`KILL TROLL` → `WHICH TROLL ?` (désambiguïsation, 0 tick ; idem
ATTACK/HIT/THROW + nom générique). `KILL VICIOUS` (20 deltas) :
`You attack the vicious troll. But the effort is wasted. His
defense is too strong.` + `Thorin sits down and starts singing
about gold.` Puis (tick suivant, 40 deltas = mort+reboot) : `The
hideous troll eats you. His foul gluttony has killed the
hideous troll. You are dead. You have mastered 2.5% of this
adventure`. Deltas : e9.id `$47`→`$00` (tick 9), reboot restaure
`$00`→`$47` + PC `$D0` (tick 10) ; e10 (`$48`) intact. Code :
`act_v14_15` (`$6E8B` : `ploc==5`, `obj==$47` → `$162B`/
`$1615`) ; tueur partagé `code_4D47` (aussi `act_v14_17`).
Leçon : attaque vouée à l'échec, le troll mange le joueur
(et en meurt — gloutonnerie), reboot restaure tout.

## Séance 4 — F1/F2 fuzz + F3 survie + F4 sortie (informée, DB)

F1 (tunnel) : `CLOSE CHEST` ✓, `GIVE MAP TO THORIN` ✓ (26),
`PUSH CHEST` ✓, `OPEN DOOR` ✓ ; rejetés : LOCK/UNLOCK (coffre
et porte), `EXAMINE THORIN/GANDALF` (PNJ non examinables),
`SHOW`, `PULL/BREAK CHEST`, `FOLLOW X`. `GET MAP` déjà porté = 0.
F2 (géo) : `EAST` terre morne→clairière (aussi `NORTH`) ;
`NORTHEAST`→`$06` ; `GIVE MAP TO HIDEOUS` accepté (`You give…`
mais porteur→`$FF` = DROP déguisé, mort ensuite) ; `THROW MAP`
seul, `GET/TAKE/STEAL KEY`, `HIDE` rejetés.
F3 (survie, 8 approches) : `KILL HIDEOUS` (même « defense too
strong »), `TALK TO HIDEOUS`, `GIVE MAP TO VICIOUS`,
`THROW MAP AT HIDEOUS` (`You throw…`, 16) — **tout meurt au
~3e tick monde** (f3e : NORTH, WAIT, WAIT-mort+reboot). Mort =
présence pure, pilotée script (ACT 16/17), inévitable sur place.
F4 (sortie) : `UP`/`DOWN`/`GO SOUTH` = 0 ; `RUN SOUTH` (28) →
**`$09` Rivendell, vivant**. `TAKE/STEAL/GET (LARGE) KEY` = 0
(clé portée = invisible).
F5 (Rivendell, gabarit F4) : `EAST`→`$0A` (23), `WEST`→`$05`
(19, puis mort+reboot tunnel) ; `TALK TO ELROND` ✓ (20, même
signature que le don du lunch) ; `EXAMINE ELROND/THORIN`,
`EAT LUNCH`, `GIVE LUNCH TO ELROND` = 0.

## Séance 5 — donjon elfe + cellier (F6–F41, DB)

F6 (poussée est) : `$0A`→`$0B`→`$0C`→`$16` libres ;
`$16` NE→`$18` (gate Mirkwood), E→`$19` ; elfe + capture
(`$42`→`$1F`). F7–F9 (donjon) : `SOUTHWEST` ne passe qu'au
rythme `(WAIT,SOUTHWEST)` (6e essai, F23/F24 2/2) ; 12 variantes
de rythme échouent (F29–F31) ; `UP` traverse gratis (F10d/F35a).
F10 (verbes donjon) : `SING` ✓, `UP` ✓ (`$1F`→`$1E`) ;
`GIVE LUNCH`/`EAT`/`CLIMB`/`SHOUT`/`OPEN|UNLOCK DOOR` = 0.
F11–F13 : rebonds `$1E`↔`$1F`, budget ~8 chutes.
F14–F17 : nord (`$44`→`$47`→`$4A`, libres) ; rivière infranchissable
(`SOUTH $19`, `RUN EAST` retombe `$1F`).
F18–F22 : `TAKE (RED) KEY` = 0 (invisible) ; 40×WAIT sans événement
neuf (locks + `Day dawns` en boucle) ; `HELP`/`SCORE` = 0 tick.
F23–F28 : rythme `(WAIT,SOUTHWEST)`×6 = entrée à 100 % (5 chutes).
F32–F36 : `SOUTH $1E`→`$20` (F37c, 3e essai) ; spam `SOUTH` = 0
mouvement ; 4 phases testées (F37a–d : `$1F`×3, `$20`×1).
F38–F39 : bounce `$20`→`$1F` systématique au 1er tick-monde ;
`DOWN` refusé (chute+éjection) ; 4 verbes `BARREL` = 0.
Hires F39a : pas de `TOO FULL` affiché, dark-fail générique.

## Séance 6 — nord/est (F42–F45, DB, `-t 100 -s 100`)

Préfixe court (`LOOK,EAST,NORTH,SE,EAST`, ~23 ticks). F42 :
`$0A` N→`$44`, E→`$0B`, S→`$49`, W→`$09` (4/4 libres).
F43 : `$44`→`$47`/`$45`, `$0B`→`$0C`, `$0B`→`$0E`, `$49`→`$4A`
(5/5 libres). F44 : `$0C`→`$16` ✓ ; `DOWN $0E` refusé (cond
`$06`) ; `$4A`→`$47` ✓. F45 : `$16`→`$18`/`$31` ✓,
`$16` NW→`$31` (anomalie, attendu `$14`) ; `(WAIT,)DOWN $0E`
→ **`$0D`** (pas `$0F` ! 2/2 : la fenêtre `$06` dévie vers
`$0D` au lieu d'ouvrir `$0F`).

## Séance 7 — snapshots SAVE/LOAD (sna/snb, DB)

`sna` (image `revise.sim`, squelette `snap-init`) : trajet F5 vers
`$09` + `WAIT` + `SAVE` (+2 sacrificielles : prompt PREPARE) +
`INVENTORY` + `EAST` (salissure `$0A`) → `@@SNAP`×4 capturé
(`sav/revise.bin` 3627 o, DB `snapshots` tick19 `ploc=$09`).
`pack --snapshot revise` (vrai blob). `snb` : reboot + `LOAD`
(+2 sacrificielles : prompt PRESS ANY) → tick7 `ploc=$09`
(restauré, pas `$0A`) + `INVENTORY`/`EAST` vivants. **0-delta** :
run direct pacé (`feed.sh` 0,4 s/ligne — sinon `pause_key` mange
`LOAD`), `-x 100M` (sinon spin idle pollue) : 3623 o post-LOAD ==
SAVE byte-exact. Checkpoint `$09` réutilisable (`revise.sim`).

## Séance 8 — checkpoint dunj + `$43` + ante `$1E` (DB)

`dunj` : préfixe f7a (`LOOK,EAST,NORTH,SE,EAST×4,NORTHEAST,EAST,
EAST`) → `$1F` tick33 (capture elfe, 0 chute !), `SAVE` tick36
→ `sav/dunj.bin` (chutes `$40` intactes, win08=`$A0`,
win0C=`$80`). `try.sim` = clone (nom `try`, `--snap-file`) pour
grinder sans clobber `dunj`.
Porte rouge = fenêtre temporelle `$A0`→`$80`→`$81`→…→`$A0`
(~30 ticks, `WAIT` gratuits) + tirage `L5F07` par tentative
(consomme `$A0`, raté = chute). dunja-d (N/W/SW purs, 2-6
chutes) : rien ; dunje/try1 `(WAIT,SW)×6` : mort 4e SW
(`$43` arrivé `$1F`, `crec=$1DD0`, reboot `$01` —
déterministe) ; try2 (forme `UP` + `SOUTH`/`WAIT`) : 11 ticks
vivant, `$A0` à tick42 ; try4 (+`SOUTH` tick45) : **`$1E` !**
mais mort avant `SAVE` (tick48-49) ; try5 rejoué à l'identique
(`diverge try2/try4` vide jusqu'au tick42) + `SAVE` immédiat
→ **`ante`** (`$1E` stable, mais chutes `$01`, `$43` à `$2E`).
`ante` (`$01`, reproductible) : `SOUTH`×5 + N/E/SW/W/UP (10/10
ratés — à `$80`, condamnés) ; division : `try.sim` (`$40`) =
loterie porte, `ante` = sonde cellier. Tickets `$A0`
(try6-13, mtry1-3 : 6 tentatives à `$A0`, 1 sortie try4) :
hit-rate ~1/9, grind en cours.

## Séance 9 — lampe/torche + inventaires OCR (hires)

`INVENTORY` (`$09`) : carte + lunch (tout). Coffre tunnel :
ouvert vide (`LOOK` ne liste rien, `INVENTORY` = carte seule).
Sondes dico : `TORCH`/`BARREL`/`WINE`/`ROPE` connus-absents
(`$01`/`$04`/`$05`/`$06`/`$09`, 0 delta) ; pas de lampe au jeu.
`LIGHT` (sans torche) : accepté mais attire `$43` et n'éclaire
pas (`ante11` : `SOUTH` tombe pareil). Pas de lampe requise :
4 sorties sans lampe prouvées (f23a×2, f37c, try4) + scramble
`L5F07`. Bonus : warg suit jusqu'à Rivendell (`The vicious
warg enters.`) — 2 traqueurs à l'est (`$43` + warg).

## Questions ouvertes (jeu)

- Cellier : `DOWN` à `$A0` (win0C) depuis `$20` — il faut D'ABORD
  entrer (`$1E` S libre mais noir, 1 chute mini) ; qui éjecte
  `$20`→`$1F` (butler `$42` ?) ; tonneau : vider (quel verbe ?)
  puis `ENTER`/fit (`L5E66`) ; sens de `UP $21`→`$00` (mort ?).
- `ante2` avec budget : sortie `$1F`→`$1E` en ≤2 chutes (tickets
  `$A0` multi-tentatives par cycle : 1re à `$A0`, suivantes à
  `$80` via N libre ~10 %).
- `$43` : identité (template `$8F`) ? déclencheur exact du kill
  (contact + action du joueur ?) ; pourquoi `UP`-first le
  déroute (`$2E`) ?
- Torche : où (objet existant, jamais vu) ? utile ? (non requise).
- Cond `$06` (`$0E`/`$0F`) : fenêtre `$A0` mène à `$0D`, pas `$0F` —
  quel rythme donne `$0F` ? Route `$3A`→`$0F` (libre) alternative.
- `$16` NW→`$31` : scramble (`L5F07`) confirmé, pas de bug.
- Dormants `$42`/`$46`/`$3C` : `$42` (eloc `$20`) se réveille au
  cellier ?

## Séance 10 — source de lumière élucidée (donjon franchissable)

**Correction de la séance 9** (« pas de lampe au jeu ») : la lumière existe.

- Test « sombre » `is_dark` (`$4C82`, doc `ROUTINE_DOCS`) : un lieu est
  sombre sauf si un état `$1A62` se trouve **au lieu du joueur** avec
  `+4` bit7 et `+7` (bits `$08`/`$04`/`$40` posés, `$10` clair).
- Seule la clé **`$0E`** (`$1CB0`, « the short strong sword ») matche :
  c'est la **source de lumière**. Init eloc `$07` (caverne des trolls).
- Preuve par patch : state `$0E`.eloc := `ploc` dans `ante2`($1F) →
  `You are in a dark dungeon in the Elvenkings halls… you see : the short
  strong sword. Thorin.` (plus de `IT IS DARK`) ; idem `$04`/`$09`. Sans
  patch : `I SEE NOTHING HERE. IT IS DARK.`
- Conséquence : pour franchir le labyrinthe noir (`$1E/$1F/$20`), il faut
  l'épée. Accès `$07` bloqué par la **porte rock** (`$06 N`, cond `$01`) —
  `NORTH` → `YOU CANNOT GO NORTH.` (PUSH/BREAK inopérants vus séance 5).
  Prochaine cible : ouvrir la porte rock (ou obtenir l'épée autrement).
- Outillage : `scripts/memmap_defs.py` nomme la clé `$0E` (`sword`) ;
  `scripts/memmap.py` / `memmap_check.py` PROPRE.

## Séance 11 — trolls → pierre, porte rock, épée (2026-10-09)

**Chaîne complète résolue : `$04`→`$05`(trolls) → attente → `$05`(pierre) →
clé → `$06` → UNLOCK → `$07`→ épée.**

- **`$05` = trolls clearing** : le troll hideux (`$47`) **porte la grande
  clé** (`$04`, template `KEY` `$0ACB`) — `GET KEY` → « THE TROLL IS
  CARRYING THE KEY. ». Entrer dans `$05` déclenche les répliques trolls
  (`$1615` BLIMEY / `$162B` MOUTHFUL) ; attendre sur place = mangé (mort).
- **Aube** : quitter `$05` (ex. `SW`→`$04`) et attendre ~4 ticks →
  « Day dawns. » → les trolls **se changent en pierre** (`act_v14_17`
  `$6EA7` : RAZ bit7 `$1F94`/`$1FA6`, desc record `$05`→`$1645`). Retour
  `$05` = « a clearing with two stone trolls », la clé est au sol →
  `GET KEY` (« You take the large key. »).
- **Porte rock** : `$06 N`→`$07` = cond `$01` = état **`$01` = « the heavy
  rock door »** (template `DOOR` `$07F2`, eloc `$07`). `+7` : bit0
  (`$01`) = **verrou**, bit5 (`$20`) = **ouvert**.
  - `OPEN DOOR` verrouillée → « THE DOOR IS LOCKED. » (`act_p14_03` →
    `L5A70` : si `+7` bit0 → échec `L5A9D`).
  - `UNLOCK DOOR` avec la grande clé → « You unlock the heavy rock door
    with the large key. » (efface bit0 : `+7 $81`→`$80`).
  - `OPEN DOOR` → « You open the heavy rock door. » mais Gandalf peut
    **refermer** aussitôt (aléatoire) ; quand il ne referme pas (`+7=$A0`),
    `NORTH` passe.
- **`$07` = trolls cave** : « the short strong sword » (`$0E`) + « the
  rope » (`$12`). `GET SWORD` → source de lumière acquise (séance 10).
- **Outillage** : `sav/sword.bin` = checkpoint `$07` épée en main ;
  `map_static`/`solver --route` rejouent la route. Idées ajoutées
  `$01`=`rock_door`, `$04`=`key` dans `scripts/memmap_defs.py`.
- **Suivant** : avec l'épée, franchir le **labyrinthe noir**
  (`$1E/$1F/$20`, Elvenking) → cellier `$20` → tonneaux → Lac → Montagne
  → dragon `$41`/`$29`.

### Séance 11 (suite) — donjon éclairé, cellier, trappe
- Avec l'épée en main, `$1F` (donjon Elvenking) n'est plus « IT IS DARK »
  (l'épée éclaire). Arrivée : `$07` → … → `$18` (porte Mirkwood) →
  `E` (pad nécessaire, warg) → `$19` « bewitched gloomy place » →
  `E` → capture → téléport `$1F`.
- `$1F` : porte rouge verrouillée (cond `$08`, clé rouge du butler).
  **Timing** : `LOOK` (déclenche « Someone opens the red door. ») puis
  `SW` → **`$20` cellier** (`cellar_sword.bin`).
- `$20` (cellier) : actions multiples possibles (pas d'éjection ici) :
  `OPEN BARREL` (montre le vin), `BREAK BARREL` (« a barrel is broken »),
  `DRINK WINE` (ivre + capturé → `$1F`), `OPEN TRAP DOOR` (marche) puis
  **`DOWN` → « You are at Forestriver »** (portcullis à l'est, trappe
  au-dessus) — `forestriver.bin`. Rebond/téléport immédiat suspecté
  (le `LOOK` suivant revient au hall) : à confirmer.
- Route rejouable jusqu'au cellier (avec le warg à `$18` → `pad`).
  Prochaine cible : Forestriver/Lac (barrel escape ?) → Montagne `$29`
  → dragon `$41`.

## Séance 12 — sortie du donjon elfe = l'Anneau obligatoire (2026-10-09)
- **`$07` = trolls cave** : prendre aussi `GET ROPE` (« the rope »).
  Inventaire après : map, large key, sword, rope. Checkpoint
  `sav/sword_rope.bin`.
- **Pièges mortels de la zone elfe** (confirmés en jeu) :
  - `$20` cellier : `OPEN TRAP DOOR` met `$0C+7` `$80`→`$A0` (trappe
    ouverte = cond `$0C` satisfaite) ; **`DOWN` → `$21` Forestriver**
    (« the fast river »), puis **mort** « swept forcefully against the
    portcullis » (courant). Idem **`SWIM`** depuis `$17` Forestriver.
  - Route **terrestre** `$18 S→$2E E→$02 E→$03 E→$2D` : `$2D` =
    « the waterfall » → **mort** « Some thing drops from above and stings »
    (araignée / pale bulbous eyes, event e8 `$6D9F`).
  - `$17` = « Forestriver » (SE rivière = cond `$2A`, `$2A+7=$86`).
- **Solution (guide externe Melbourne House)** : la sortie du donjon exige
  **l'Anneau** (invisibilité). Séquence : `WEAR RING` en continu ;
  `WAIT` jusqu'à ce que le butler ouvre un tonneau et boive le vin ;
  `CLIMB INTO BARREL` ; `WAIT` jusqu'à atterrir au **Long Lake `$23`**.
  Sans l'Anneau le butler capture (`CLIMB INTO BARREL` → capture → `$1F`).
  Le butler suit un cycle fixe (rouvre la porte rouge régulièrement).
- **Route amont** (pour atteindre le palais elfe sans capture) : bateau
  traversant la rivière (`THROW ROPE`, `PULL ROPE`, `CLIMB INTO BOAT`),
  araignées (`BREAK WEB`), puis `WEAR RING` + `EXAMINE DOOR` (porte
  magique elfe `$0D+7` bit5) — cf. guide ZX.
- États ajoutés au repérage : `$0C` = trappe ($80/$A0), `$2A` = rivière
  (`+7=$86`), `$27` = cond `$21` E→`$22`.
- **Objectif suivant = l'Anneau** : via la caverne des gobelins / énigme
  de Gollum (état `$44`, arg `$10` caverne). Puis araignées → bateau →
  palais elfe → tonneau.
- Checkpoints : `sav/sword_rope.bin` ($07+rope), `sav/forestriver17.bin`
  ($17).

### Séance 12 (suite) — crack des Montagnes → donjon gobelin
- Depuis `$07` : `S`($06 trolls path) `S`($05) `SE`($09 Rivendell)
  `E`($0A) `E`($0B « narrow place, dreadful drop ») `N` → **chute dans
  « the small insignificant crack »** → **`$0D` = the goblins dungeon**
  (capturé : « to the north the goblins door, to the west the window,
  you see : some sand ») — `sav/crack.bin`, `sav/goblin_dungeon.bin`.
- `DIG SAND` → révèle « the trap door » ; `BREAK TRAP DOOR` ×25 sans
  casser (pas de compteur net ; seul `$06+7` `$A0→$80` bouge). `GET KEY`
  ambigu (« YOU ARE ALREADY CARRYING THE KEY » = grande clé). Trappe =
  trésor optionnel (guide : « may take a very long time »).
- `OPEN WINDOW` → « YOU CANNOT REACH THE WINDOW. » Sortie = coopération
  PNJ (« SAY TO THORIN ... » ; syntaxe exacte à trancher : sans guillemets
  le 2e verbe est absorbé, avec guillemets l'input se corrompt).
- **Prochaine étape** : sortir du donjon gobelin (fenêtre + Thorin) ou
  naviguer le repaire gobelin ($10-$13/$39-$41/$11 lac souterrain) pour
  trouver **Gollum `$44`** (arg `$10`) → énigme → **Anneau** (WEAR RING),
  clef de l'évasion elfique.

### Séance 12 (suite 2) — donjon gobelin : clé sous la trappe (épée)
- **`BREAK TRAP DOOR` sans arme = échec infini** (150×). Il faut
  l'**épée** : `BREAK TRAP DOOR WITH SWORD` → « You strike the trap door
  with the short strong sword. **The door is broken.** » (la trappe
  n'était cassable qu'avec une arme — piège).
- La trappe cassée révèle **« the goblins cache »** contenant
  **« the small curious key »**. **Thorin** (PNJ autonome) la prend seul :
  « Thorin takes the small curious key. » / « Thorin says " This was
  Thrains key " ». Checkpoint `sav/goblin_key.bin`.
- **Sortie toujours bloquée** : `OPEN WINDOW` = « cannot reach »,
  `THROW ROPE THROUGH WINDOW` = « THE WINDOW IS CLOSED. », `GO THROUGH
  WINDOW`/`WEST`/`N` refusés ; Thorin reste (« Thorin waits »). `SAY HELP`
  → indice « **A WINDOW SHOULD BE NO OBSTACLE TO A THIEF WITH FRIENDS.** »
- **Blocage syntaxe** : le guide commande le PNJ par
  `SAY TO THORIN "CARRY ME"` / `"OPEN WINDOW"` / `"WEST"`. Notre harnais
  envoie bien la chaîne mais **l'écho casse sur le `"`** (`echo_ok=False`,
  sortie corrompue) ; testé aussi guillemets simples, `TO`, `TELL`,
  `ORDER` → échec. Le solver (vocabulaire standard) ne trouve aucune
  évasion (frontière vide). → **piste : implémenter le rendu du caractère
  `"` (0x22) ou trouver la touche quote Oric** pour tester la commande.

### Séance 12 (suite 3) — BREAKTHROUGH : commandes PNJ `SAY TO X "..."`.
- **La syntaxe d'ordre aux PNJ fonctionne** : `SAY TO THORIN "<ORDRE>"`
  (guillemets doubles obligatoires à l'ouverture ET à la fermeture).
  Prouvé :
  - `SAY TO THORIN "CARRY ME"` → « You talk to Thorin. **Thorin carry
    ies you.** »
  - `SAY TO THORIN "OPEN WINDOW"` → « **Thorin opens the window.** »
  - `SAY TO THORIN "WEST"` → traverse (vers `$12`).
- **Piège harnais** : `run_one()['text']` échoue à segmenter les commandes
  à guillemets (le jeu insère un `.` : `> SAY "HI".`) → lire
  `r['full']` / `r['blob']`, jamais `r['text']` pour ces commandes
  (`echo_ok=False` trompeur).
- **Évasion du donjon gobelin** (indice `SAY HELP` : « A WINDOW SHOULD BE
  NO OBSTACLE TO A THIEF WITH FRIENDS. ») : `SAY TO THORIN "CARRY ME"` +
  `"OPEN WINDOW"` + `"WEST"` → `$12` (dark winding passage) → `SW` → `$10`
  (big cavern) → … → `$11` (brink of underground lake, Gollum).
  Checkpoints `sav/goblin_escaped.bin` ($12), `sav/lake.bin` ($11).
- **Gollum = entité ERRANTE** : état `$44` (`$1E3B`), `eloc` (`+$10`)
  change (`$37`/`$3D`/`$36`). Riddle `act_v14_14` (`$6D78`) : si
  `ploc==$1E4B` (co-localisé) → tirage 0-7 → msg `$16B9` (« pocket ? »,
  si `$1CC5`==`$44`) / `$16C8` (« my precious »). L'Anneau n'est pas
  encore localisé (ni au lac, ni dans le cache gobelin = key).
- **Cellier sans Thorin** : `SAY TO THORIN ...` → « I DO NOT SEE THE
  THORIN HERE ». `KILL BUTLER WITH SWORD` → « Your violent attack almost
  kills the butler » (1 coup insuffisant, puis capture `$1F`). → Anneau
  (ou 2e coup au butler) requis pour l'évasion elfique.
- Guide complet (Spectrum/BBC, porté) désormais exécutable : ordres PNJ
  OK. Reste à obtenir l'Anneau et enchaîner bateau → araignées → palais
  elfe → tonneau → Lac.

### Séance 12 (suite 4) — ANNEau localisé et pris !
- **L'Anneau = état `$10`** (`$1CC4`, template `$0859`) = « **the
  valuable golden ring** », posé au lieu **`$3D`** (dark stuffy passage).
  Identifié par recoupement statique (`act_v14_14` teste `$1CC5` = carrier
  de `$10` == `$44` Gollum → « pocket ? ») puis **confirmé en jeu**.
- Chemin : `sav/lake.bin` ($11) → `N`→`$37` → `SW`→`$3D` : « you see :
  **the valuable golden ring**. » → `GET RING` → « You take the valuable
  golden ring. » → carrier `$FF`→`$00`. Inventaire : map, large key,
  sword, **golden ring**, rope. Checkpoint `sav/ring.bin`.
- **Famille « clé »** : `tpl=$CB` partagé par `$02`, `$04`, `$0F` →
  ce sont des clés ; `$04` = grande clé, `$0F` = **clé rouge** (portée
  par le butler `$42`). `$02` = clé portée par `$1F` au lieu `$0D`.
- **Prochain** : `WEAR RING` + suivre le guide (bateau → araignées →
  palais elfe `EXAMINE DOOR` → tonneau → Lac `$23` → Montagne `$29` →
  dragon `$41`).

### Séance 12 (FINALE) — VICTOIRE 🏆 (2026-10-09)
> « You put the valuable treasure in the wooden chest. A cheering crowd
> of dwarves, hobbits and elves appears. Led by Gandalf they carry you
> off into the sunset, proclaiming you hero of heroes and master
> adventurer!!! **You have mastered 80.0% of this adventure.** »

Checkpoint `sav/win.bin`. **Parcours complet reproductible** (dans l'ordre) :

1. `$01`→`E`→`$04`→trolls→clé→`$06`/`$07` (épée+rope) — cf. séance 11.
2. Monts Brumeux : `$07`→`S S SE E E`→`$0B`→`N` (chute crack)→`$0D`
   donjon gobelin.
3. Donjon gobelin : `DIG SAND` ; **`BREAK TRAP DOOR WITH SWORD`** →
   **« small curious key »** (Thorin la prend) ; `SAY TO THORIN "CARRY ME"`
   `"OPEN WINDOW"` `"WEST"` → `$12`→`SW`→`$10`→…→`$11` lac.
4. **Anneau** : `$11`→`N`→`$37`→`SW`→`$3D` → `GET RING` (« the valuable
   golden ring »).
5. Sortie gobelin : `$0F` (attendre que la fenêtre s'ouvre) `UP`→`$0E`→`S`
   `$0B`→`W` surface `$0A` ; `E E E NE`→`$18` Mirkwood ; `E E`→capture
   `$1F`.
6. Donjon elfe : `WEAR RING` ; `LOOK`+`SW`→`$20` cellier ; `WEAR RING`
   (×, l'effet dure ~3-4 tours) ; suivre le cycle du butler ; quand il ouvre
   le tonneau : `CLIMB INTO BARREL` (puis il ferme) ; `WAIT`×2 → `$21`
   Forestriver → `WAIT` → **Long Lake `$22`**.
7. `E`→`$23` Lake-town ; `SAY TO BARD "NORTH"` `FOLLOW BARD`
   `SAY TO BARD "UP"` `FOLLOW BARD` `SAY TO BARD "NORTH"` `FOLLOW BARD`
   `FOLLOW BARD` `SAY TO BARD "NORTH"` `FOLLOW BARD` → `$29` (Bard suit).
8. `SAY TO BARD "SHOOT DRAGON"` → « Bard shoots the red golden dragon…
   The dragon is dead. » `GET TREASURE`.
9. Retour : `S S S DOWN S S W W W N W N SW W W SW W` → `$01`. **Aux lieux
   « pale bulbous eyes » (araignées `$02`/`$03`), `WAIT`×2 avant de bouger.**
10. `OPEN CHEST` ; `PUT TREASURE IN CHEST` → **victoire** (80 %).

**Mécaniques clés** : ordres PNJ `SAY TO <PERS> "<ORDRE>"` (guillemets
doubles) ; `WEAR RING` = invisibilité ~3-4 tours (re-porter) ; tonneau
flottant ; araignées = WAIT×2 ; Bard conduit au dragon et tire.

### Séance 12 (Gollum) — riddle déclenché dynamiquement (env. `$3D`)
Depuis `sav/ring.bin` (Anneau en poche, lieu `$3D` où Gollum **rôde**), suite
`WAIT` **déterministe** (6 essais identiques) :
- `w3` `Gollum enters.`
- `w4` `Gollum says "My birthday present, how did we loses it, my
  preciouss."` = **`act_v14_14`** (`$6D78`) : tirage `rand_range 8` < 4 **et**
  `$1CC5`≠`$44` (Anneau chez le joueur) → msg `$16C8`.
- `w5` **`Gollum takes the valuable golden ring.`** → **Gollum REPREND
  l'Anneau** (danger réel : ne pas s'attarder à `$3D`).
- `w6` énigme complète : `Gollum says "It cannot be seen, cannot be felt /
  Cannot be heard, cannot be smelt / it lies behind stars and under hills, /
  And empty holes it fills. / It comes first and follows after, ends life,
  kills laughter."` (le « noir »).
- Variante `$16B9` observée : `Gollum says "What has it got in its
  pockets?"` (tirage ≥ 4, ou Anneau encore chez Gollum).
- **Au lac `$11`** sans avoir l'Anneau en poche/à portée : `Gollum enters.`
  → **`The horrible goblin captures you.` → donjon gobelin `$0D`**
  (`act_v14_12`, message patché depuis la donnée de l'entité).
Checkpoint `sav/gollum_riddle.bin`. Conclusion : `act_v14_14` n'est **pas**
un simple tirage décoratif : séquence dialogue + **vol de l'Anneau** + énigme,
toute la chaîne `$16B9-$1721` est du Gollum.

### Séance 13 — comparatif C64/Apple II : 4 fonctions moteur testées (2026-10-16)
Solutions C64 (disk + variante) et Apple II fournies ; 4 mécaniques
« C64/Apple-only » supposées absentes de l'Oric passées au harnais
(`scripts/solver_run.py` → `run_one` depuis `sav/*.bin`, lecture `full`/`blob`).

1. **Ordre PNJ à virgules `SAY TO THORIN "A, B, C"`** — supporté, mais
   **plafonné à 2 sous-ordres** (un seul `,` honoré) :
   - `SAY TO THORIN "CARRY ME, OPEN WINDOW"` → `Thorin carry ies you.`
     puis (tour suivant) `Thorin opens the window.`
   - `SAY TO THORIN "OPEN WINDOW, WEST"` → `Thorin opens the window.` +
     `Thorin goes west.`
   - 3 sous-ordres : le 3e est **silencieusement jeté** (`"CARRY ME, WEST,
     OPEN WINDOW"` → OPEN WINDOW jamais ; `"OPEN WINDOW, WEST, CARRY ME"` →
     CARRY ME jamais).
   ⇒ l'ordre Apple II `"CARRY ME, OPEN WINDOW, GO WEST"` ne peut **pas**
   atteindre GO WEST en un seul ordre : nos 3 ordres séparés restent requis.
   Écho : le jeu insère un `.` interne (`> SAY TO THORIN "CARRY ME."."`) →
   `run_one()['text']` rate la segmentation (`echo_ok=False`), lire `full`.

2. **Gandalf pilotable `SAY TO GANDALF "<ordre>"`** — **NON supporté** (Oric).
   `SAY TO GANDALF "..."` (GO EAST / CARRY ME / KILL WARG / HELLO / WAIT /
   FOLLOW ME / script Apple II complet) → systématiquement `You talk to
   Gandalf. Gandalf says " No "` (script adaptatif, non commandable).
   Contrôles : `SAY TO THORIN "GO EAST"` → `Thorin goes through the round green
   door.` (Thorin obéit) ; `SAY TO ELROND "..."` → `Elrond says " No "`.
   ⇒ l'Apple II commande Gandalf ; l'Oric ne le peut pas.

3. **Combat par procuration `SAY TO THORIN "KILL <créature>"`** — **supporté**.
   Depuis `sav/gollum_riddle.bin` (Thorin + Gollum co-localisés) :
   `SAY TO THORIN "KILL GOLLUM"` → `Thorin attacks Gollum. With one well placed
   blow Thorin cleaves his skull. Gollum is dead.` (idem `ATTACK GOLLUM`).
   Le joueur seul échoue (`KILL GOLLUM` → « the effort is wasted »). Côté
   joueur, `KILL WARG`/`ATTACK WARG` marchent quand le warg est là
   (`sav/ring_dungeon.bin` : « You attack the vicious warg…stunned ») ;
   `FIGHT` est inconnu du dico. Cible absente ⇒ aucune action ni message
   (l'ordre est *muet* si la cible n'est pas co-localisée au tour d'action).

4. **`EAT` / `ALL`** — supportés.
   - `EAT` (et `EAT LUNCH`) avec le lunch porté (`sav/revise.bin`, Rivendell) →
     `You eat some lunch.` (consomme le lunch `$26`, le temps avance) ; sans
     nourriture (`SLVW`) → `I SEE NOTHING TO EAT`. `EAT FOOD` → `I DO NOT SEE
     THE FOOD HERE` (`FOOD` absent du dico Oric ; ici c'est `lunch`).
     Correction vs status antérieur (`EAT LUNCH`=0 : mesuré sans lunch porté).
   - `OPEN ALL` / `TAKE ALL` / `GET ALL` → agissent sur les cibles présentes
     (`TAKE ALL` @caverne trolls → `You take the rope.` ; `OPEN ALL` @cellier →
     `You open the red door.`) ; **muets** et sans effet (ndiff 0) s'il n'y a
     rien à ouvrir/prendre.

Conclusion : sur les 4, trois sont présents dans l'Oric (ordre PNJ comma
plafonné à 2 ; combat PNJ via Thorin ; `EAT`/`ALL`) et **un est absent**
(Gandalf non commandable). Les solutions C64/Apple II surestiment les
capacités de *notre* édition ; `sav/win.bin` reste la référence.

## Séance 14 — brute-force C++ : victoire depuis cold boot (2026-10-17)
- **Émulateur 6502 C++** (`harness/brute/`, prototype hors toolchain) :
  parité **bit-identique** avec sim65 (mémoire initiale + régions SAVE
  `$00BE/$1B1A/$28CC/$211A` au boot et après tour 1 ; texte 45 tours).
  Clé : `S=$00` au reset (sim65 `Reset()` ne fixe pas SP) — sinon le RNG
  (`rand_range $56D7`, `noise=$93/$94` lu en `$0100`) diverge. Détails :
  `harness/brute/NOTES.md`.
- **Cause racine du « blocage façade »** : `wait_for_key` ($7481) = pause
  « appuyez sur une touche », boucle `jsr get_key` sans prompt `>` ; ni le
  `Session` Python ni le WASM ne la modélisaient -> stall jusqu'au budget.
- **`win_seq.txt` = 111 commandes depuis le cold boot -> victoire** :
  `A cheering crowd of dwarves, hobbits and elves appears ... You have
  mastered 80.0% of this adventure.` Déterministe ×3. Fin : `PUT TREASURE`
  (au hall, coffre ouvert). Sans SAVE/LOAD, sans `sav/*.bin`.
- **Ouvert** : le WASM diverge avant `wait_for_key` (stalls `$4743 $46e6
  $524f …`, `autokey=0`). Fix autokey posé (`web/cpu/web_main.c::hob_run`)
  mais insuffisant ; isoler la divergence `web/core/io.c` vs modèle de
  l'ému. Diag temporaire à nettoyer (`hob_autokey_count`, `hob_last_pc`,
  `web/smoke.mjs`).

## Séance 15 — RNG/shim élucidé, pivot Path 1, réparation elfe (2026-10-17)
- **Même cœur `emu.cpp`, deux images** : `hobbit_fast.sim` (classic) GAGNE,
  `hobbit_solver.sim` (solveur) STALLE (tour 52, lieu `$42`). Ni le cœur
  6502, ni `$7628` (testé), ni les hooks texte (ignorés par l'ému), ni
  `k_log` (NOPé sans effet) : reste les **octets du shim `$C000`**.
- **Mécanisme** : `rand_range $56D7` échantillonne la mémoire via
  `(noise),y` (`$93/$94`, pas de 256 o → tout l'espace, dont `$C0xx` vers
  tours 40-45, mesuré). Shims classic/solveur différents → RNG forké →
  elfe absent au tour 52 (pas de capture). `$02` (`$FB` vs `$20` tour 0)
  = résidu bénin (forcer `$FB` : icount identique).
- **Oric-1 vs Atmos** (`data/basic10.rom` vs `data/basic11b.rom`) : 96,1 %
  différents, y compris toutes les positions échantillonnées → les deux
  machines divergent en RNG, donc **le jeu est robuste aux variations RNG**
  (timing bénin) ; notre stall = script rigide sur-ajusté au timing
  classic, pas jeu cassé. Inutile de répliquer le RNG exact.
- **Décisions** : C (moteur unique sim65 multiprocessus, `emu.cpp` gardé en
  fallback) + **Path 1** (re-chercher sous solveur, pas Path 2).
  `scripts/sim_pack.py --solver` seul → `build/sim/hobbit_solver.sim`
  (froide solveur). `sav/SLVW.bin` STALE (ne pas utiliser).
  `run_one` impropre au rejeu exact (LOAD/SAVE + discontinuité RNG `$93/$94`
  → diverge ~tour 47) ; stdin fichier/EOF → auto-WAIT idle (toujours PIPE
  tenu ouvert + kill sur echo+prompt).
- **Outils** : `scripts/sim_search.py` (réécrit : froid parallèle sim65,
  verdicts OK) ; `scripts/sim_cold.py` (PTY, dépassé/lent).
- **Réparation** : sous solveur, `WAIT×3` à la porte → elfe entre + capture
  pendant WAIT → donjon (EAST inutile). `harness/brute/win_seq_solver.txt`
  = win_seq L1-51 + `WAIT×3` + L54-111 (112 cmds, **fin à valider**).
- **Reste** : validation froide complète (~5-10 min, interrompue), puis
  segments suivants (Bard ~tour 76), `solution.js`, glue WASM, suppression
  `emu.cpp` + diags web, commit (gardes PROPRE le 2026-10-17).
