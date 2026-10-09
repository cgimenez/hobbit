# Journal d'aventure — The Hobbit (Oric), joué sous sim65

Carte exhaustive (statique, 78 lieux) : `docs/game-map.md`. Ce journal
ne décrit que le terrain vérifié en jeu.

Parties **informées** (depuis 2026-10-08 PM) : fini l'aveugle — coups
décidés en connaissance des commandes (sonde vocabulaire),
PNJ et lieux. Deux images : `build/sim/hobbit_fast.sim` (texte seul,
tickdiff) + `build/sim/hires.sim` (`--fast --hires`, OCR texte).
Cmdfile tickdiff = lignes `\n` (1re = touche boot, `\n`→`\r` par
tickdiff) ; run sim65 brut = mêmes octets en `\r` (`rX.cr`).

Conventions : `> COMMANDE.` = écho jeu ; tick = commande réussie.

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
[cond `$08`], W→`$1E` [cond `$08`]. **`UP` = sortie dorée :
`$1F`→`$1E`, 0 chute, consomme la fenêtre `$A0` d'arrivée**
(2/2 : f10d, f35a). `SING`/`PUSH RED DOOR` tickent sans bouger
(23 deltas, 0 chute — sondes gratuites).
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
light.`), CLIMB, ENTER, CROSS/SWIM?, DIG, PULL, PUSH (`You
push.`), FOLLOW (`FOLLOW WHAT ?`), SLEEP (`You sleep.`),
READ=EXAMINE (`EXAMINE WHAT ?`), SAY=TALK (`TALK TO WHAT ?`),
TALK (`You talk to Thorin.`), SCORE (`YOU'RE DOING FINE.` /
`You have mastered X% of this adventure`), HELP, GO (traverse),
RUN/LEAVE (=partir), WEAR, FILL, EMPTY, TIE, UNTIE, HIDE
(`WHAT ?`), directions NORTH/SOUTH/EAST/WEST/UP/DOWN +
N/S/E/W/U/D + NE/NW/SE/SW (`YOU CANNOT GO X.` sinon).
Inconnus (`I DO NOT KNOW`) : SHUT SHOW FIGHT RUB EXIT SHOUT ASK
TELL SEARCH STAND WAVE KNOCK FEEL SMELL LISTEN BUY SELL STAY
MOVE HELLO. Ambiguïtés : `WHICH TROLL ?` (HIDEOUS vs VICIOUS) ;
`I DO NOT SEE THE X HERE` (absent) ; `TALK TO WHAT ?` (personne).
F40a (tunnel, verbes seuls) : `ENTER` ✓ (31 deltas), `SIT`/`SLEEP`
✓ (18, équiv. WAIT) ; `DRINK`/`EMPTY`/`POUR`/`FILL`/`CLIMB` = 0
(mots connus mais sans effet ici).

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

## Questions ouvertes (jeu)

- Cellier : vider le tonneau (quel verbe ? butler endormi après
  soak ?) ; sens de `UP $21`→`$00` (mort ?) ; qui éjecte `$20`→`$1F`
  (butler `$42` ?) et comment rester (arriver butler absent ?).
- Cond `$06` (`$0E`/`$0F`) : fenêtre `$A0` mène à `$0D`, pas `$0F` —
  quel rythme donne `$0F` ? Route `$3A`→`$0F` (libre) alternative.
- `$16` NW→`$31` : bug de lecture ou random-noir ? Retester + OCR.
- Dormants `$42`/`$46`/`$3C` : `$42` (eloc `$20`) se réveille au
  cellier ?
