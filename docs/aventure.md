# Journal d'aventure — The Hobbit (Oric), joué sous sim65

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
le lunch).

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

## Questions ouvertes (jeu)

- Dormants `$42`/`$46`/`$3C` : déclencheurs en jeu ?
- Identités `$3D $3F $40 $43 $45 $49 $4A $4B $4C` : rencontres ?
- Gandalf après son départ est : où le recroiser (FOLLOW/WAIT) ?
- Nord/sud-ouest/sud-est de la clairière : quoi ?
- `+0` `$02 $03 $05 $08` : quels objets/lieux ?
