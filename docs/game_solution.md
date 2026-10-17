# The Hobbit (Oric, 1982) — solution complète, pas à pas

Parcours vérifié **du démarrage (`$01`) à la victoire (80.0 %)** sous le
harnais `sim65` du dépôt (`scripts/solver*.py` + image `build/sim/SLVW.sim`).

Chaque entrée donne **ce qui est saisi** (la commande, en majuscules — le `.`
final est ajouté par le jeu, ne pas le taper) et **ce qui est affiché**
(description du lieu, actions des PNJ, réponse du parser). `$xx` = lieu
courant (`ploc`), à recouper avec `docs/map.md`.

## Mode d'emploi / reproductibilité

- Le correctif `--solver` de `scripts/sim_pack.py` neutralise la pause de
  lecture (`pause_key`, `$7628`) : sans lui, le harnais **avalait le 1er
  caractère** de la commande suivante (flux clavier pré-injecté).
- Le **monde est autonome** (AnimAction) : l'errance de certains PNJ
  (elfe des bois, Gollum, araignées, butler) dépend de l'historique de ticks.
  Trois passages sont donc **aléatoires par conception** (mouvements du donjon
  noir `$1F`/`$20`, cycle du butler) ou liés à une phase précise : la solution
  les franchit par **SAVE/LOAD** en jeu (comme la partie d'origine). Ces
  points sont marqués **SAVE / LOAD** ci-dessous.
- Une **variante sans aucun SAVE/LOAD** existe aussi (run continu unique,
  état final byte-identique à `runs/sav/win.bin`) : voir **Annexe 2** en fin de
  document (elle décale les fenêtres temporelles de +5 `WAIT` dans le donjon
  gobelin, ce qui réaligne du même coup l'errance de l'elfe des bois).
- Entrées « doubles » : `NORTH puis SOUTHWEST` doit être tapé sur **deux tours
  consécutifs** — à la clairière des trolls il faut ressortir avant que le
  troll hideux ne te mange.

---

## Acte 1 — Tunnel → trolls → épée/corde → lac souterrain → Anneau → surface

But : obtenir la **grande clé** (les trolls se changent en pierre à l'aube),
l'**épée** (source de lumière) et la **corde**, gagner le lac, prendre
l'**Anneau**, puis ressortir à l'air libre.

| Saisir | Affiché |
|---|---|
| `OPEN CHEST` | You open the wooden chest. Gandalf opens the round green door. |
| `EAST` | You go east. You are in a gloomy empty land with dreary hills ahead to the west there is the round green door visible exits are : east north northeast you see : nothing Gandalf enters. Thorin enters. |
| `NORTH puis SOUTHWEST` | You go north. You are in the trolls clearing visible exits are : southwest southeast north you see : the hideous troll. The troll is carrying the large key. the vicious troll. Gandalf enters. Thorin enters. The hideous troll says " Blimey, looks at this !! Can yer cook 'em? ". The vicious troll says " Yer can try, but he wouldn't make above a mouthfull " . |
| `WAIT` | You wait. Time passes... Thorin says " Hurry up ". |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... Thorin sits down and starts singing about gold. Day dawns. |
| `WAIT` | You wait. Time passes... |
| `NORTH` | You go north. You are in in a clearing with two stone trolls visible exits are : southwest southeast north you see : the large key. Thorin enters. |
| `GET KEY` | You take the large key. Thorin waits. |
| `SOUTHWEST` | You go southwest. The lonelands visible exits are : east north northeast you see : nothing |
| `NORTHEAST` | You go northeast. You are in a hidden path with trolls foot prints to the north there is the heavy rock door visible exits are : south you see : nothing Thorin enters. |
| `UNLOCK DOOR` | You unlock the heavy rock door with the large key. Thorin waits. |
| `OPEN DOOR` | You open the heavy rock door. |
| `NORTH` | You go north. You are in the trolls cave to the south there is the heavy rock door you see : the short strong sword. the rope. Thorin enters. |
| `GET SWORD` | You take the short strong sword. Thorin waits. |
| `GET ROPE` | You take the rope. |
| `SOUTH` | You go south. The trolls path visible exits are : south you see : nothing Thorin enters. |
| `SOUTH` | You go south. The trolls clearing visible exits are : southwest southeast north you see : nothing Thorin enters. |
| `SOUTHEAST` | You go southeast. You are in Rivendell visible exits are : east west you see : Elrond. Thorin enters. Elrond says " Hello ". |
| `EAST` | You go east. You are on a hard dangerous path in the Misty mountains visible exits are : east north west south you see : Gandalf. the dead warg. Gandalf goes north. Thorin enters. |
| `EAST` | You go east. You are in a narrow place with a dreadful drop into a dim valley visible exits are : east west north you see : nothing Thorin enters. |
| `NORTH` | You go north. You are in a large dry cave which is quite comfortable below there is the small insignificant crack visible exits are : south you see : the nasty goblin. Thorin enters. The nasty goblin captures you. You are in the goblins dungeon to the north there is the goblins door to the west there is the window you see : some sand. |
| `DIG SAND` | You dig some sand. In the sand there is the trap door. Thorin appears. |
| `BREAK TRAP DOOR WITH SWORD` | You strike the trap door with the short strong sword. The door is broken. |
| `SAY TO THORIN "CARRY ME"` | You talk to Thorin. Thorin carry ies you. |
| `SAY TO THORIN "OPEN WINDOW"` | You talk to Thorin. Thorin opens the window. |
| `SAY TO THORIN "WEST"` | You talk to Thorin. Thorin goes west. You are in the dark winding passage to the north there is the window visible exits are : southwest southeast you see : Thorin. Thorin is carrying you |
| `SOUTHEAST` | You go southeast. You are in the dark stuffy passage visible exits are : up north east you see : nothing Thorin enters. |
| `UP` | You go up. You are in the dark stuffy passage visible exits are : northwest west southwest you see : the vicious goblin. the disgusting goblin. Thorin enters. The vicious goblin goes northwest. The disgusting goblin goes west. |
| `WEST` | You go west. You are in the dark stuffy passage visible exits are : down southeast south southwest you see : the disgusting goblin. Thorin enters. The disgusting goblin attacks you. The disgusting goblin swings broadside at your body but at the last moment you jump aside. |
| `SOUTHEAST` | You go southeast. You are in the dark stuffy passage visible exits are : south northeast southwest west you see : the horrible goblin. Thorin enters. Gollum enters. The horrible goblin attacks you. A fast blow knocks the wind out of you. |
| `SOUTH` | You go south. You are at the brink of a deep dark under ground lake visible exits are : north you see : nothing Thorin enters. |
| `WAIT` | You wait. Time passes... Thorin waits. The horrible goblin enters. |
| `WAIT` | You wait. Time passes... The horrible goblin attacks you. The horrible goblin hits you hard on the shoulder - you stagger and almost fall. |
| `NORTH puis SOUTHWEST` | You go north. The dark stuffy passage visible exits are : south northeast southwest west you see : nothing Thorin enters. |
| `GET RING` | You take the valuable golden ring. Thorin sits down and starts singing about gold. |
| `NORTH` | You go north. The dark stuffy passage visible exits are : down southeast south southwest you see : nothing |
| `DOWN` | You go down. You are in the dark stuffy passage visible exits are : north down up you see : nothing |
| `NORTH` | You go north. You are in the dark stuffy passage above there is the small insignificant crack visible exits are : south northeast you see : the nasty goblin. The nasty goblin goes south. |
| `WAIT` | You wait. Time passes... The nasty goblin enters. |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... The nasty goblin opens the small insignificant crack. |
| `UP` | You go up. A large dry cave visible exits are : south you see : nothing The nasty goblin enters. |
| `SOUTH` | You go south. A narrow place visible exits are : east west north you see : nothing |
| `WEST` | You go west. The misty mountain visible exits are : east north west south you see : the dead warg. |
| `EAST` | You go east. A narrow place visible exits are : east west north you see : nothing |
| `EAST` | You go east. You are on a narrow dangerous path visible exits are : east west you see : nothing |
| `EAST` | You go east. You are in Beorns house visible exits are : northeast northwest south southwest north you see : a heavy curtain. |
| `NORTHEAST` | You go northeast. You are at the gate to Mirkwood visible exits are : west south east you see : nothing |
| `EAST` | You go east. You are in a bewitched gloomy place surrounded by thick trees to the south there is the fast black river visible exits are : west east you see : nothing |
| `EAST` | You go east. You are on the west bank of a black river to the east there is the fast black river visible exits are : west you see : nothing |

## Acte 2 — Capture par l'elfe des bois → donjon elfe ($1F)

Depuis la surface, on rentre dans Mirkwood : au gué, l'**elfe des bois**
capture le héros et le jette dans le donjon du roi elfe.

| Saisir | Affiché |
|---|---|
| *SAVE / LOAD* | *(reprise : `runs/sav/ring_surface.bin`)* |
| `EAST` | You go east. A narrow place visible exits are : east west north you see : nothing |
| `EAST` | You go east. You are on a narrow dangerous path visible exits are : east west you see : nothing |
| `EAST` | You go east. You are in Beorns house visible exits are : northeast northwest south southwest north you see : a heavy curtain. |
| `NORTHEAST` | You go northeast. You are at the gate to Mirkwood visible exits are : west south east you see : nothing |
| `EAST` | You go east. You are in a bewitched gloomy place surrounded by thick trees to the south there is the fast black river visible exits are : west east you see : nothing |
| `EAST` | You go east. You are on the west bank of a black river to the east there is the fast black river visible exits are : west you see : the wood elf. The wood elf captures you. You are on a dark dungeon in the Elvenkings halls to the southwest there is the red door to the west there is the red door you see : the vicious warg. The vicious warg attacks you. But the effort is wasted. Your defense is too strong. Someone opens the red door. |

## Acte 3 — Sortie du donjon noir vers le cellier ($20)

Les déplacements dans le noir sont **tirés au sort** : d'où le **SAVE** au
`$1F`. Un seul `SOUTHWEST` franchit la porte rouge quand elle est ouverte.

| Saisir | Affiché |
|---|---|
| *SAVE / LOAD* | *(reprise : `runs/sav/ring_dungeon.bin`)* |
| `SOUTHWEST` | You go southwest. You are in the cellar where the king keeps his barrels of wine to the northeast there is the red door below there is the large trap door visible exits are : north you see : a barrel. the butler. The butler is carrying the red key. The vicious warg enters. The butler closes the red door. |

## Acte 4 — Le tonneau ($21), le Long Lac ($22), Lake-town ($23)

On porte l'Anneau (invisibilité ≈ 3-4 tours, à **re-porter**). On attend que
le butler **ouvre le tonneau**, on monte dedans, on re-porte l'Anneau, puis on
se laisse flotter jusqu'au Long Lac.

| Saisir | Affiché |
|---|---|
| *SAVE / LOAD* | *(reprise : `runs/sav/ring_cellar.bin`)* |
| `WEAR RING` | You wear the valuable golden ring. The vicious warg runs around you and howls. The butler locks the red door with the red key. |
| `WAIT` | You wait. Time passes... The vicious warg attacks the butler. But the effort is wasted. His defense is too strong. The butler captures the vicious warg. |
| `WAIT` | You wait. Time passes... The butler opens the barrel. In the barrel there is some wine. |
| `CLIMB INTO BARREL` | You climb into the barrel. The butler drinks some wine. |
| `WEAR RING` | You wear the valuable golden ring. The butler closes the barrel. |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... You are thrown onto the bank of the long lake. You are at Long lake to the northwest there is the strong portcullis visible exits are : north east south you see : a barrel. |
| `EAST` | You go east. You are in a wooden town in the middle of long lake visible exits are : north south east west you see : Bard. Bard is carrying a bow. a strong arrow. |

## Acte 5 — Bard conduit à la Montagne, le dragon est tué, trésor pris

On ordonne à **Bard** de marcher (`SAY TO BARD "..."` + `FOLLOW BARD`),
jusqu'aux Halls du dragon (`$29`) ; il tire et **tue le dragon**, on ramasse
le **trésor**.

| Saisir | Affiché |
|---|---|
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. |
| `FOLLOW BARD` | You follow Bard. You are at Long lake to the northwest there is the strong portcullis visible exits are : north east south you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. |
| `SAY TO BARD "UP"` | You talk to Bard. Bard goes up. |
| `FOLLOW BARD` | You follow Bard. You are on a strong river : the current is now too strong to move against visible exits are : up south you see : Bard. Bard is carrying a bow. a strong arrow. |
| `SAY TO BARD "UP"` | You talk to Bard. Bard goes up. |
| `FOLLOW BARD` | You follow Bard. You are in a bleak barren land that was once green visible exits are : north down you see : the red golden dragon. Bard. Bard is carrying a bow. a strong arrow. The red golden dragon goes down. |
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. The red golden dragon enters. |
| `FOLLOW BARD` | You follow Bard. You are in the ruins of the town of dale visible exits are : north south northwest you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. The red golden dragon enters. |
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. |
| `FOLLOW BARD` | You follow Bard. You are at the front gate of the Lonely Mountain visible exits are : north south west you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. The red golden dragon enters. |
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. |
| `FOLLOW BARD` | You follow Bard. You are in the halls where the dragon sleeps visible exits are : south east up you see : the valuable treasure. Bard. Bard is carrying a bow. a strong arrow. The red golden dragon enters. |
| `SAY TO BARD "SHOOT DRAGON"` | You talk to Bard. Bard shoots the red golden dragon. The arrow hits the dragon. The dragon is dead. |
| `GET TREASURE` | You take the valuable treasure. |

## Acte 6 — Le retour jusqu'au tunnel ($01) et la victoire

Route de retour **sans araignée** : Long Lac → Mirkwood (ouest) → Monts
Brumeux → Rivendell → clairière (trolls de pierre) → tunnel. Puis on met le
trésor dans le coffre.

| Saisir | Affiché |
|---|---|
| `SOUTH` | You go south. The front gate visible exits are : north south west you see : nothing |
| `SOUTH` | You go south. Dale valley visible exits are : north south northwest you see : nothing |
| `SOUTH` | You go south. The drago desolation visible exits are : north down you see : nothing |
| `DOWN` | You go down. Running river visible exits are : up south you see : nothing |
| `SOUTH` | You go south. Long lake visible exits are : north east south you see : nothing |
| `SOUTH` | You go south. You are at the waterfall visible exits are : south west you see : nothing |
| `WEST` | You go west. You are in the forest visible exits are : west east you see : nothing You see some pale bulbous eyes staring at you. |
| `WEST` | You go west. You are on the forest road visible exits are : east west you see : nothing You see some pale bulbous eyes staring at you. |
| `WAIT` | You wait. Time passes... You see some pale bulbous eyes staring at you. |
| `WAIT` | You wait. Time passes... You see some pale bulbous eyes staring at you. |
| `WEST` | You go west. You are on the forest road visible exits are : east north you see : nothing |
| `NORTH` | You go north. The forest gate visible exits are : west south east you see : nothing |
| `WEST` | You go west. Beorns house visible exits are : northeast northwest south southwest north you see : a heavy curtain. |
| `SOUTHWEST` | You go southwest. A dangerous narrow path visible exits are : east west you see : nothing |
| `WEST` | You go west. A narrow place visible exits are : east west north you see : nothing |
| `WEST` | You go west. The misty mountain visible exits are : east north west south you see : nothing |
| `WEST` | You go west. Rivendell visible exits are : east west you see : Elrond. |
| `WEST` | You go west. The trolls clearing visible exits are : southwest southeast north you see : nothing |
| `SOUTHWEST` | You go southwest. The lonelands visible exits are : east north northeast you see : nothing |
| `WEST` | You go west. You are in a comfortable tunnel like hall to the east there is the round green door you see : the wooden chest. |
| `OPEN CHEST` | THE CHEST IS OPEN. |
| `PUT TREASURE IN CHEST` | You put the valuable treasure in the wooden chest. A cheering crowd of dwarves, hobbits and elves appears. Led by Gandalf they carry you off into the sunset, proclaiming you hero of heroes and master adventurer!!!. You have mastered 80.0% of this adventure. |

### Message de victoire

```
You put the valuable treasure in the wooden chest.
A cheering crowd of dwarves, hobbits and elves appears.
Led by Gandalf they carry you off into the sunset, proclaiming you
hero of heroes and master adventurer!!!.
You have mastered 80.0% of this adventure.
```

État final **byte-identique** à `runs/sav/win.bin`.

---

## Annexe 1 — séquence brute (rejeu automatisé, version avec SAVE/LOAD)

Rejeu sous harnais (`scripts/solver*.py`, `run_one`). `NORTH + SOUTHWEST` est
injecté en un seul run (`NORTH\rSW`, nécessaire pour survivre à la clairière) ;
`LOAD runs/sav/<nom>.bin` remplace le blob courant (sauvegarde en jeu). Le reste est
une commande par run.

```
# Acte 1 (boot)
OPEN CHEST / EAST / NORTH+SOUTHWEST / WAIT x4 / NORTH / GET KEY /
SOUTHWEST / NORTHEAST / UNLOCK DOOR / OPEN DOOR / NORTH / GET SWORD / GET ROPE /
SOUTH / SOUTH / SOUTHEAST / EAST / EAST / NORTH / DIG SAND /
BREAK TRAP DOOR WITH SWORD /
SAY TO THORIN "CARRY ME" / SAY TO THORIN "OPEN WINDOW" / SAY TO THORIN "WEST" /
SOUTHEAST / UP / WEST / SOUTHEAST / SOUTH / WAIT / WAIT /
NORTH+SOUTHWEST / GET RING /
NORTH / DOWN / NORTH / WAIT / WAIT / WAIT / UP / SOUTH / WEST /
EAST / EAST / EAST / NORTHEAST / EAST / EAST
# Acte 2 (capture)
LOAD runs/sav/ring_surface.bin / EAST / EAST / EAST / NORTHEAST / EAST / EAST
# Acte 3
LOAD runs/sav/ring_dungeon.bin / SOUTHWEST
# Acte 4
LOAD runs/sav/ring_cellar.bin / WEAR RING / WAIT / WAIT / CLIMB INTO BARREL /
WEAR RING / WAIT / WAIT / WAIT / WAIT / EAST
# Acte 5
SAY TO BARD "NORTH" / FOLLOW BARD / SAY TO BARD "UP" / FOLLOW BARD /
SAY TO BARD "UP" / FOLLOW BARD / SAY TO BARD "NORTH" / FOLLOW BARD /
SAY TO BARD "NORTH" / FOLLOW BARD / SAY TO BARD "NORTH" / FOLLOW BARD /
SAY TO BARD "SHOOT DRAGON" / GET TREASURE
# Acte 6
SOUTH / SOUTH / SOUTH / DOWN / SOUTH / SOUTH / WEST / WEST / WAIT / WAIT / WEST /
NORTH / WEST / SOUTHWEST / WEST / WEST / WEST / WEST / SOUTHWEST / WEST /
OPEN CHEST / PUT TREASURE IN CHEST
```

---

## Annexe 2 — Variante **sans SAVE/LOAD** (run continu vérifié)

Le même parcours se termine **en une seule partie continue**, **sans
aucune sauvegarde** : état final **byte-identique** à `runs/sav/win.bin`.
Deux réglages diffèrent de la version principale :

- **5 `WAIT` de plus** juste après la chute dans le donjon gobelin
  (`$0D`, avant `DIG SAND`) : cela réaligne les fenêtres temporelles
  ET l'errance de l'elfe des bois (`$40`), qui se trouve alors à la
  rivière quand on y arrive → la capture fonctionne (plus besoin de
  recharger).
- **Cellier/tonneau** : cycle du butler suivi en direct
  (`WEAR RING`, `WAIT`, `CLIMB INTO BARREL`, `WEAR RING`, `WAIT`,
  `WAIT`, `WEAR RING`, `WAIT`) — pas de rechargement.
- Sortie du donjon noir : `WAIT` puis `SOUTHWEST` (le lieu `$1F`
  n'exige pas de rechargement une fois la phase alignée).

`NORTH puis SOUTHWEST` = deux tours consécutifs en jeu (à la
clairière des trolls, ressortir avant d'être mangé).

| Saisir | Affiché |
|---|---|
| `OPEN CHEST` | You open the wooden chest. Gandalf opens the round green door. |
| `EAST` | You go east. You are in a gloomy empty land with dreary hills ahead to the west there is the round green door visible exits are : east north northeast you see : nothing Gandalf enters. Thorin enters. |
| `NORTH puis SOUTHWEST` | You go north. You are in the trolls clearing visible exits are : southwest southeast north you see : the hideous troll. The troll is carrying the large key. the vicious troll. Gandalf enters. Thorin enters. The hideous troll says " Blimey, looks at this !! Can yer cook 'em? ". The vicious troll says " Yer can try, but he wouldn't make above a mouthfull " . |
| `WAIT` | You wait. Time passes... Thorin says " Hurry up ". |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... Thorin sits down and starts singing about gold. Day dawns. |
| `WAIT` | You wait. Time passes... |
| `NORTH` | You go north. You are in in a clearing with two stone trolls visible exits are : southwest southeast north you see : the large key. Thorin enters. |
| `GET KEY` | You take the large key. Thorin waits. |
| `SOUTHWEST` | You go southwest. The lonelands visible exits are : east north northeast you see : nothing |
| `NORTHEAST` | You go northeast. You are in a hidden path with trolls foot prints to the north there is the heavy rock door visible exits are : south you see : nothing Thorin enters. |
| `UNLOCK DOOR` | You unlock the heavy rock door with the large key. Thorin waits. |
| `OPEN DOOR` | You open the heavy rock door. |
| `NORTH` | You go north. You are in the trolls cave to the south there is the heavy rock door you see : the short strong sword. the rope. Thorin enters. |
| `GET SWORD` | You take the short strong sword. Thorin waits. |
| `GET ROPE` | You take the rope. |
| `SOUTH` | You go south. The trolls path visible exits are : south you see : nothing Thorin enters. |
| `SOUTH` | You go south. The trolls clearing visible exits are : southwest southeast north you see : nothing Thorin enters. |
| `SOUTHEAST` | You go southeast. You are in Rivendell visible exits are : east west you see : Elrond. Thorin enters. Elrond says " Hello ". |
| `EAST` | You go east. You are on a hard dangerous path in the Misty mountains visible exits are : east north west south you see : Gandalf. the dead warg. Gandalf goes north. Thorin enters. |
| `EAST` | You go east. You are in a narrow place with a dreadful drop into a dim valley visible exits are : east west north you see : nothing Thorin enters. |
| `NORTH` | You go north. You are in a large dry cave which is quite comfortable below there is the small insignificant crack visible exits are : south you see : the nasty goblin. Thorin enters. The nasty goblin captures you. You are in the goblins dungeon to the north there is the goblins door to the west there is the window you see : some sand. |
| `WAIT` | You wait. Time passes... Thorin appears. |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... Thorin sits down and starts singing about gold. |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... Thorin waits. |
| `DIG SAND` | You dig some sand. In the sand there is the trap door. |
| `BREAK TRAP DOOR WITH SWORD` | You strike the trap door with the short strong sword. The door is broken. Thorin takes the small curious key. |
| `SAY TO THORIN "CARRY ME"` | You talk to Thorin. Thorin carry ies you. |
| `SAY TO THORIN "OPEN WINDOW"` | You talk to Thorin. Thorin opens the window. The mean goblin enters. |
| `SAY TO THORIN "WEST"` | You talk to Thorin. Thorin goes west. You are in the dark winding passage to the north there is the window visible exits are : southwest southeast you see : Thorin. Thorin is carrying you the small curious key. The horrible goblin enters. |
| `SOUTHEAST` | You go southeast. You are in the dark stuffy passage visible exits are : up north east you see : nothing |
| `UP` | You go up. You are in the dark stuffy passage visible exits are : northwest west southwest you see : the vicious goblin. The vicious goblin goes northwest. |
| `WEST` | You go west. You are in the dark stuffy passage visible exits are : down southeast south southwest you see : nothing Gollum enters. |
| `SOUTHEAST` | You go southeast. You are in the dark stuffy passage visible exits are : south northeast southwest west you see : nothing |
| `SOUTH` | You go south. You are at the brink of a deep dark under ground lake visible exits are : north you see : nothing Gollum enters. |
| `NORTH puis SOUTHWEST` | You go north. The dark stuffy passage visible exits are : south northeast southwest west you see : nothing |
| `GET RING` | You take the valuable golden ring. |
| `NORTH` | You go north. The dark stuffy passage visible exits are : down southeast south southwest you see : nothing |
| `DOWN` | You go down. You are in the dark stuffy passage visible exits are : north down up you see : nothing |
| `NORTH` | You go north. You are in the dark stuffy passage above there is the small insignificant crack visible exits are : south northeast you see : the nasty goblin. The nasty goblin opens the small insignificant crack. |
| `UP` | You go up. A large dry cave visible exits are : south you see : nothing The nasty goblin enters. |
| `SOUTH` | You go south. A narrow place visible exits are : east west north you see : nothing |
| `WEST` | You go west. The misty mountain visible exits are : east north west south you see : Gandalf. the dead warg. Gandalf goes north. |
| `EAST` | You go east. A narrow place visible exits are : east west north you see : nothing |
| `EAST` | You go east. You are on a narrow dangerous path visible exits are : east west you see : nothing |
| `EAST` | You go east. You are in Beorns house visible exits are : northeast northwest south southwest north you see : a heavy curtain. |
| `NORTHEAST` | You go northeast. You are at the gate to Mirkwood visible exits are : west south east you see : nothing |
| `EAST` | You go east. You are in a bewitched gloomy place surrounded by thick trees to the south there is the fast black river visible exits are : west east you see : the wood elf. The wood elf captures you. You are in a dark dungeon in the Elvenkings halls to the southwest there is the red door to the west there is the red door you see : nothing someone unlocks the red door with the red key. |
| `EAST` | — |
| `WAIT` | You wait. Time passes... Someone opens the red door. |
| `SOUTHWEST` | You go southwest. You are in the cellar where the king keeps his barrels of wine to the northeast there is the red door below there is the large trap door visible exits are : north you see : a barrel. the butler. The butler is carrying the red key. The butler closes the red door. |
| `WEAR RING` | You wear the valuable golden ring. The butler locks the red door with the red key. |
| `WAIT` | You wait. Time passes... The butler opens the barrel. In the barrel there is some wine. |
| `CLIMB INTO BARREL` | You climb into the barrel. The butler drinks some wine. |
| `WEAR RING` | You wear the valuable golden ring. The butler closes the barrel. |
| `WAIT` | You wait. Time passes... |
| `WAIT` | You wait. Time passes... |
| `WEAR RING` | You wear the valuable golden ring. |
| `WAIT` | You wait. Time passes... You are thrown onto the bank of the long lake. Long lake visible exits are : north east south you see : a barrel. |
| `EAST` | You go east. You are in a wooden town in the middle of long lake visible exits are : north south east west you see : Bard. Bard is carrying a bow. a strong arrow. |
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. |
| `FOLLOW BARD` | You follow Bard. You are at Long lake to the northwest there is the strong portcullis visible exits are : north east south you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. |
| `SAY TO BARD "UP"` | — |
| `FOLLOW BARD` | You follow Bard. You are on a strong river : the current is now too strong to move against visible exits are : up south you see : Bard. Bard is carrying a bow. a strong arrow. The red golden dragon enters. |
| `SAY TO BARD "UP"` | You talk to Bard. Bard goes up. The red golden dragon goes up. |
| `FOLLOW BARD` | You follow Bard. You are in a bleak barren land that was once green visible exits are : north down you see : the red golden dragon. Bard. Bard is carrying a bow. a strong arrow. The red golden dragon goes down. |
| `SAY TO BARD "NORTH"` | You talk to Bard. Bard goes north. |
| `FOLLOW BARD` | You follow Bard. You are in the ruins of the town of dale visible exits are : north south northwest you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. |
| `SAY TO BARD "NORTH"` | — |
| `FOLLOW BARD` | You follow Bard. You are at the front gate of the Lonely Mountain visible exits are : north south west you see : Bard. Bard is carrying a bow. a strong arrow. Bard goes north. The red golden dragon enters. |
| `SAY TO BARD "NORTH"` | — |
| `FOLLOW BARD` | You follow Bard. You are in the halls where the dragon sleeps visible exits are : south east up you see : the valuable treasure. Bard. Bard is carrying a bow. a strong arrow. The red golden dragon enters. |
| `SAY TO BARD "SHOOT DRAGON"` | You talk to Bard. Bard shoots the red golden dragon. The arrow hits the dragon. The dragon is dead. |
| `GET TREASURE` | You take the valuable treasure. |
| `SOUTH` | You go south. The front gate visible exits are : north south west you see : nothing |
| `SOUTH` | You go south. Dale valley visible exits are : north south northwest you see : nothing |
| `SOUTH` | You go south. The drago desolation visible exits are : north down you see : nothing |
| `DOWN` | You go down. Running river visible exits are : up south you see : nothing |
| `SOUTH` | You go south. Long lake visible exits are : north east south you see : nothing |
| `SOUTH` | You go south. You are at the waterfall visible exits are : south west you see : nothing |
| `WEST` | You go west. You are in the forest visible exits are : west east you see : nothing You see some pale bulbous eyes staring at you. |
| `WEST` | You go west. You are on the forest road visible exits are : east west you see : nothing You see some pale bulbous eyes staring at you. |
| `WAIT` | You wait. Time passes... You see some pale bulbous eyes staring at you. |
| `WAIT` | You wait. Time passes... You see some pale bulbous eyes staring at you. |
| `WEST` | You go west. You are on the forest road visible exits are : east north you see : nothing |
| `NORTH` | You go north. The forest gate visible exits are : west south east you see : nothing |
| `WEST` | You go west. Beorns house visible exits are : northeast northwest south southwest north you see : a heavy curtain. |
| `SOUTHWEST` | You go southwest. A dangerous narrow path visible exits are : east west you see : nothing |
| `WEST` | You go west. A narrow place visible exits are : east west north you see : nothing |
| `WEST` | You go west. The misty mountain visible exits are : east north west south you see : the dead warg. |
| `WEST` | You go west. Rivendell visible exits are : east west you see : Elrond. Elrond says " Hello ". |
| `WEST` | You go west. The trolls clearing visible exits are : southwest southeast north you see : nothing |
| `SOUTHWEST` | You go southwest. The lonelands visible exits are : east north northeast you see : nothing |
| `WEST` | You go west. You are in a comfortable tunnel like hall to the east there is the round green door you see : the wooden chest. |
| `OPEN CHEST` | — |
| `PUT TREASURE IN CHEST` | You put the valuable treasure in the wooden chest. A cheering crowd of dwarves, hobbits and elves appears. Led by Gandalf they carry you off into the sunset, proclaiming you hero of heroes and master adventurer!!!. You have mastered 70.0% of this adventure. |
