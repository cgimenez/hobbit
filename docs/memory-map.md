# Carte mémoire de l'état sauvegardé — plan d'octets (The Hobbit, Oric)

Tout l'état mutable tient dans 4 régions basses, recopiées au boot vers
le workspace haut contigu **`$91D0`–`$9FF7` (`$0E28` o)** et écrites sur
cassette par SAVE (`cmd_save` `$3DD9`, 4 blocs + VERIFY). Chaque ligne
ci-dessous = adresse exacte → signification, relevée dans
`data/hobbit.bin` (image initiale ; le runtime mute via harnais).

Conventions : `+N` = offset dans le bloc ; `L5331` = accès état mutable,
`L530B` = accès record template (`*($2070+id*2)`, id<`$50`, `$2F` nul).

## 0. Vue d'ensemble (SAVE : sources basses → cassette)

| Bloc | Source basse | Taille | Workspace haut | Contenu |
|---|---|---|---|---|
| 1 | `$00BE` | `$0018` (24) | `$9FDF` | Zéro-page `$BE`–`$D5` (§1) |
| 2 | `$1B1A` | `$0556` (1366) | `$91D0` | 61 blocs d'état, clés `$1A62` (§2) |
| 3 | `$28CC` | `$02F1` (753) | `$9726` | 13 tables INDIR + scripts VM + events + entités (§3–§5) |
| 4 | `$211A` | `$05C8` (1480) | `$9A17` | 79 records via `$2070` (§6) |

Contiguïté : `$9726`=`$91D0`+`$556`, `$9A17`=`$9726`+`$2F1`,
`$9FDF`=`$9A17`+`$5C8`, fin `$9FF7`. Offset workspace = `$91D0`+(bas−`$1B1A`)
selon la région (ex. entités `$2B45` → `$999F` = `$9726`+(`$2B45`−`$28CC`)).

## 1. Zéro-page `$00BE`–`$00D5` (24 o) — joueur et contexte

Noms `ZP_NAMES` (`scripts/disasm.py`). Valeurs = image initiale
(écrasées par `init_vars`/le jeu ; ex. `ploc`=`$01` après boot).

| Addr | Nom | Sens | Init |
|---|---|---|---|
| `$BE` | `exploc` | lieu attendu par l'événement (copie de `key`, grille `ploc`) | `$82` |
| `$BF` | `tblA` | pointeur lo table action/patch `$7116` (pas 4) ; hi `$C0` | `$01` |
| `$C0` | `tblA_hi` | haut de `tblA` | `$87` |
| `$C1` | `tblB` | pointeur lo table errance/desc `$7126` (pas 6) ; hi `$C2` | `$02` |
| `$C2` | `tblB_hi` | haut de `tblB` | `$85` |
| `$C3` | `dflag` | flag action dragon (init `0` par l'intro, jamais armé → inactif) | `$43` |
| `$C4` | `sflag` | flag sortie texte (armé par `evt_disarme7` : ajoute `H` après `s`/`S`) | `$45` |
| `$C5` | `obj` | objet/entité courant (id ; `$FF`=personne ; lieu via `L57BB`) | `$AC` |
| `$C6` | `crec` | enregistrement courant, octet bas (contexte/compteurs ; base `$1B1A`) | `$05` |
| `$C7` | `crec_hi` | haut de `crec` | `$08` |
| `$C8` | `ploc` | lieu du joueur — **miroir** de `player.eloc` (`$1B2A`) ; LOOK/déplacement lisent l'`eloc`, pas `ploc` (patté seul, il est re-dérivé) | `$AC` |
| `$C9` | `eloc` | lieu de l'entité (visibilité : `eloc`==`ploc`) | `$11` |
| `$CA` | `recptr` | pointeur de record de lieu courant (copie de `ptr`) | `$85` |
| `$CB` | `recptr_hi` | haut de `recptr` (toujours `$21`–`$26` = region records) | `$43` |
| `$CC` | `score` | score courant en points (lu par SCORE `$3CD4` ; hi `$CD`) | `$80` |
| `$CD` | `score_hi` | haut du score (remis à 0 après victoire) | `$83` |
| `$CE` | `once` | verrou one-shot (posé, testé+consommé) | `$87` |
| `$CF` | `cand` | index de candidat (tables déplacement `$48D3/$48D5-$D7`, errance) | `$83` |
| `$D0` | `mwt` | budget/poids du déplacement (errance : `$0A` moins les coûts) | `$43` |
| `$D1` | `qrd` | curseur de lecture de la file d'actions `$4905` (RAZ/commande) | `$AD` |
| `$D2` | `qwr` | curseur d'écriture de la file d'actions `$4905` (RAZ/commande) | `$14` |
| `$D3` | `macc` | accumulateur de poids (errance) | `$08` |
| `$D4` | `mcnt` | compteur de candidats retenus (errance) | `$96` |
| `$D5` | `said` | flag « le PNJ a parlé/refusé » (`code_6C2E` pose, `act_v14_13` RAZ) | `$0D` |

`$C3`/`$C4`/`$CF`–`$D5` = **scratch transitoire** (planificateur d'errance
des PNJ + file d'actions `$4905`), nommés ci-dessus ; seuls `$CF`/`$D0`/`$D3`/
`$D4` sont observés muter (sous `@win`/`@goblin_escaped`/`KILL THORIN`).
`$CC`/`$CD` = **score** (points ; SCORE `$3CD4`) ; `$CA`/`$CB` = **recptr**
(pointeur de record de lieu sauvegardé, `$21`–`$26`).

## 2. États `$1B1A`–`$206F` (1366 o) — personnages, objets, lieux

Table des clés **`$1A62`** : **61 triplets** `[clé,lo,hi]` + `$FF` en
`$1B19`. Clés `$00`–`$2B` (44) puis `$3C`–`$4C` (17) ; **trou `$2C`–`$3B`**
(aucune clé). Correction : pas 60 mais **61 clés** (`$4C` inclus,
`$205A`).

**Partition des blocs (corrigé)** : les bases sont non monotones en **ordre
de clé** (`$3C`→`$1B30` < `$2B`→`$1B84`) mais forment une partition
**contiguë en ordre d'adresse** : chaque octet appartient à la clé dont la
base est la plus grande `≤` l'adresse, jusqu'à la base suivante (blocs de
`$12` à `$24` o). Vérifié sur les 32 références littérales de `block4.asm`
(0 ambiguïté) ; encodé par `memmap_defs.state_owner`.

Format de bloc (via `L57BB`, `code_5AF0`, `act_p14_00/01`, `act_p14_13`) :
`+0` = **N, nombre de lieux** ; les `N` lieux suivent en `+$10`, `+$11`, … (balayés
par `L5FFA`). `N`=`$01` = objet **à un seul lieu** (seul cas que `entity_state_resolve`
`$57BB` résout : rend `(fiche)+$10`, sinon `$FF` = « nulle part »). `N`≥`$02` =
**objet multi-lieux** (portes, eau, toile, rivière : ex. eau `$17` en 8 lieux).
`+1` = porteur (id entité, `$FF`=personne : carte `$03`→`$3E` = Gandalf au boot) ;
`+$02` = **volume** (objet) / capacité (conteneur ; `act_p14_13` « IS TOO FULL ») ;
`+$03` = **masse** (poids, comparé au portage par `obj_count_add` `$5C2B`) ;
`+$04` (bits 0-2) = **classe de contenant/type** (`obj_type_route` `$5B9B`) ;
`+$05` = **force**/dégâts (combat, `+10`/coup, `bit7`⇒tué) ; `+$06` = seuil de
robustesse ; `+$07` = **attributs** (8 bits : `b0` verrou, `b1` fluide, `b2` plein,
`b3` cassé/mort, `b4` éclaire, `b5` ouvert, `b6` animal, `b7` visible) ;
`+$08`/`+$09` = **nom** (`noun`, mot du dictionnaire rendu par `word_render` ; lu par
`name_from_record` `$5A9D`) ; `+$0A`/`+$0B` = **adjectif 1** (`adj1`, réutilisé en
pointeur secondaire : `$098F` posé par `$6F1B`) ; `+$0C`/`+$0D` = **adjectif 2**
(`adj2`, tenu pour `descp` : RAZ par `code_5AF0` puis posé par les actions, `$04D6`
→ texte « t while THE… »).

| Clé | Addr | +0 =N | +1 porteur | +8 nom | lieux (+$10..+$10+N-1) |
|---|---|---|---|---|---|
| `$00` | `$1B1A` | `$01` | `$FF` | `$0F` | `$01` |
| `$01` | `$1B63` | `$02` | `$FF` | `$F2` | `07`,`06` (porte rock « heavy rock door » `$06`→`$07` ; `+7` bit0=verrou, bit5=ouvert) |
| `$02` | `$1B96` | `$01` | `$1F` | `$CB` | `$0D` |
| `$03` | `$1BBA` | `$01` | `$3E` | `$95` | `$01` (carte, portée par Gandalf) |
| `$04` | `$1BA8` | `$01` | `$47` | `$CB` | `$05` (la grande clé, portée par le troll hideux `$47` ; ouvre la porte rock) |
| `$05` | `$1B42` | `$02` | `$FF` | `$F2` | `01`,`04` |
| `$06` | `$1BCE` | `$02` | `$FF` | `$48` | `0E`,`0F` |
| `$07` | `$1BE9` | `$05` | `$FF` | `$BB` | `1A`,`1C`,`1B`,`1D`,`32` |
| `$08` | `$1C05` | `$03` | `$FF` | `$F2` | `1F`,`1E`,`20` |
| `$09` | `$1C25` | `$03` | `$FF` | `$66` | `42`,`43`,`19` |
| `$0A` | `$1C55` | `$02` | `$FF` | `$F2` | `13`,`14` |
| `$0B` | `$1C74` | `$02` | `$FF` | `$F2` | `2A`,`2B` |
| `$0C` | `$1C93` | `$02` | `$FF` | `$F2` | `20`,`21` |
| `$0D` | `$1D1F` | `$02` | `$FF` | `$F2` | `1E`,`1C` |
| `$0E` | `$1CB0` | `$01` | `$FF` | `$45` | `$07` (épée « short strong sword », **source de lumière** `+4`=01x, `+7`=$94) |
| `$0F` | `$1CDA` | `$01` | `$42` | `$CB` | `$20` (portée par le butler `$42` → **clé rouge** présumée ; tpl `$CB` = famille « clé » : `$02`,`$04`,`$0F`) |
| `$10` | `$1CC4` | `$01` | `$FF` | `$59` | `$3D` (**the valuable golden ring**, objet au lieu `$3D` ; carrier=`$00` après GET ; `$1CC5`==`$44` → « pocket ? » dans `act_v14_14`/Gollum) |
| `$11` | `$1CEC` | `$02` | `$FF` | `$F2` | `10`,`0D` |
| `$12` | `$1D07` | `$01` | `$FF` | `$77` | `$07` |
| `$13` | `$1D84` | `$01` | `$FF` | `$07` | `$20` |
| `$14` | `$1DA8` | `$01` | `$13` | `$F1` | `$20` |
| `$15` | `$1DE2` | `$01` | `$FF` | `$A0` | `$00` |
| `$16` | `$1DF6` | `$01` | `$FF` | `$A0` | `$00` |
| `$17` | `$1E0A` | `$08` | `$FF` | `$A0` | `08`,`21`,`22`,`24`,`31`,`2D`,`11`,`17` |
| `$18` | `$1E25` | `$03` | `$FF` | `$A0` | `19`,`42`,`43` |
| `$19` | `$1E5F` | `$01` | `$46` | `$69` | `$23` |
| `$1A` | `$1E73` | `$01` | `$46` | `$D1` | `$23` |
| `$1B` | `$1E87` | `$02` | `$FF` | `$EB` | `0D`,`12` |
| `$1C` | `$1EA4` | `$02` | `$FF` | `$E4` | `10`,`1E` |
| `$1D` | `$1EB7` | `$01` | `$FF` | `$9C` | `$0D` |
| `$1E` | `$1ECB` | `$01` | `$1D` | `$F2` | `$0D` |
| `$1F` | `$1EE3` | `$01` | `$1E` | `$A8` | `$0D` |
| `$20` | `$1EF5` | `$01` | `$FF` | `$74` | `$16` |
| `$21` | `$1F0B` | `$01` | `$24` | `$5E` | `$16` |
| `$22` | `$1F23` | `$01` | `$21` | `$29` | `$16` |
| `$23` | `$1F37` | `$01` | `$FF` | `$F6` | `$29` |
| `$24` | `$1F49` | `$01` | `$20` | `$8B` | `$16` |
| `$25` | `$1F5B` | `$01` | `$FF` | `$F0` | `$01` |
| `$26` | `$1FB1` | `$01` | `$FF` | `$7B` | `$00` (lunch : donné par Elrond `$09`, porté `$00`) |
| `$27` | `$1FC5` | `$02` | `$FF` | `$E6` | `21`,`22` |
| `$28` | `$1FDA` | `$01` | `$FF` | `$DC` | `$2F` (= record nul : nulle part ?) |
| `$29` | `$1F75` | `$01` | `$FF` | `$5E` | `$43` |
| `$2A` | `$1C3D` | `$03` | `$FF` | `$66` | `17`,`21`,`22` |
| `$2B` | `$1B84` | `$01` | `$FF` | `$CB` | `$4F` |
| `$3C` | `$1B30` | `$01` | `$FF` | `$FA` | `$29` (futur : identité à confirmer) |
| `$3D` | `$1FEC` | `$01` | `$FF` | `$B1` | `$0F` |
| `$3E` | `$1D38` | `$01` | `$FF` | `$6F` | `$01` (Gandalf, lieu départ) |
| `$3F` | `$1D4A` | `$01` | `$FF` | `$9C` | `$01` |
| `$40` | `$1D60` | `$01` | `$FF` | `$47` | `$1C` |
| `$41` | `$1D72` | `$01` | `$FF` | `$4A` | `$09` (dragon présumé) |
| `$42` | `$1DBE` | `$01` | `$FF` | `$9F` | `$20` (dormant, armé par event) |
| `$43` | `$1DD0` | `$01` | `$FF` | `$8F` | `$15` |
| `$44` | `$1E3B` | `$01` | `$FF` | `$C8` | `$11` (Gollum présumé) |
| `$45` | `$2002` | `$01` | `$FF` | `$B1` | `$3A` |
| `$46` | `$1E4D` | `$01` | `$FF` | `$03` | `$23` (dormant, armé par event) |
| `$47` | `$1F8D` | `$01` | `$FF` | `$0A` | `$05` (lieu 5, trolls) |
| `$48` | `$1F9F` | `$01` | `$FF` | `$0A` | `$05` (lieu 5, trolls) |
| `$49` | `$2018` | `$01` | `$FF` | `$B1` | `$12` |
| `$4A` | `$202E` | `$01` | `$FF` | `$B1` | `$38` |
| `$4B` | `$2044` | `$01` | `$FF` | `$B1` | `$40` |
| `$4C` | `$205A` | `$01` | `$FF` | `$B1` | `$10` |

Chaînes de porteurs (qui tient quoi) : `$03`→`$3E`, `$04`→`$47`,
`$0F`→`$42`, `$14`→`$13`, `$19`/`$1A`→`$46`, `$1E`→`$1D`,
`$1F`→`$1E`, `$21`→`$24`, `$22`→`$21`, `$24`→`$20`, `$02`→`$1F`.

**Nom de chaque clé** : `+$08`/`+$09` est la **clé de dictionnaire** du nom
de l'objet, rendue par `word_render` (`$4241`, page `$05+hi`, offset `lo`) ;
`+$0A`/`+$0B` et `+$0C`/`+$0D` sont les deux **adjectifs** (mêmes pointeurs de
dictionnaire). Nom complet = adj1 + adj2 + nom (ex. `$0E` = `SHORT` `STRONG`
`SWORD`). Décodée sur les 61 clés (l'identifiant unique ajoute la clé quand le
mot se répète) :

| Clé | Nom | Clé | Nom | Clé | Nom | Clé | Nom |
|---|---|---|---|---|---|---|---|
| `$00` | YOU | `$01` | DOOR | `$02` | KEY | `$03` | MAP |
| `$04` | KEY | `$05` | DOOR | `$06` | CRACK | `$07` | WEB |
| `$08` | DOOR | `$09` | RIVER | `$0A` | DOOR | `$0B` | DOOR |
| `$0C` | DOOR | `$0D` | DOOR | `$0E` | SWORD | `$0F` | KEY |
| `$10` | RING | `$11` | DOOR | `$12` | ROPE | `$13` | BARREL |
| `$14` | WINE | `$15` | WATER | `$16` | WATER | `$17` | WATER |
| `$18` | WATER | `$19` | BOW | `$1A` | ARROW | `$1B` | WINDOW |
| `$1C` | TORCH | `$1D` | SAND | `$1E` | DOOR | `$1F` | CACHE |
| `$20` | CURTAIN | `$21` | CUPBOARD | `$22` | FOOD | `$23` | TREASURE |
| `$24` | WALL | `$25` | CHEST | `$26` | LUNCH | `$27` | PORTCULLIS |
| `$28` | STONE | `$29` | BOAT | `$2A` | RIVER | `$2B` | KEY |
| `$3C` | DRAGON | `$3D` | GOBLIN | `$3E` | GANDALF | `$3F` | THORIN |
| `$40` | ELF | `$41` | ELROND | `$42` | BUTLER | `$43` | WARG |
| `$44` | GOLLUM | `$45` | GOBLIN | `$46` | BARD | `$47` | TROLL |
| `$48` | TROLL | `$49` | GOBLIN | `$4A` | GOBLIN | `$4B` | GOBLIN |
| `$4C` | GOBLIN | | | | | | |

Correction : `$41` = **ELROND** (et non « dragon présumé ») ; le **DRAGON**
est `$3C` (dormant). `$40` = ELF, `$43` = WARG, `$46` = BARD, `$3F` =
THORIN.

Lieu `$00` = **nulle part** (objet non posé : `$15`/`$16`/`$26`) ; `$2F` =
**record nul** (`$2070[$2F]`=`$0000`, clé `$28`).

**`$1E4B` = `$44.$10` = `gollum.eloc`** (base `$1E3B`+`$10`) : `act_v14_12`
(`$6C03`) et `act_v14_14` (`$6D78`) le comparent à `ploc` pour exiger la
co-localisation joueur/Gollum (confirme `+$10` = `eloc`).

**Champs de bloc `+$05`/`+$06`/`+$07` (via `act_p14_00` `$60BF` /
`act_p14_01` `$60ED`, combat) et `+$02`/`+$03` (physique : volume/masse,
`act_p14_13` « IS TOO FULL » / `obj_count_add` `$5C2B`)** : `+$05` = **force**
/dégâts (`+10`/coup, `bit7`⇒tué, msg `$1525` ; doublé par la transfo `$6F1B`),
`+$06` = seuil de robustesse, `+$07` = **attributs** (bits `locked/fluide/
plein/cassé/éclaire/ouvert/animal/visible`, cf. table ci-dessous). Encodés dans
`STATE_FIELD` ; l'appartenance des octets est désormais **univoque**
(partition `state_owner`).

**Table des attributs `+$07`** (bit → sens, identique à Wilderland `WL.h`
`ATTR_*`) ; vérifié sur l'image : `rock_door` `$81` (verrou), `sword`/
`torch` `$94` (plein+éclaire), `wine`/`water` `$82` (fluide), PNJ `$E0`
(animal, `bit3`=mort) :

| bit | masque | sens | helpers |
|---|---|---|---|
| 0 | `$01` | verrouillé | `obj_flag1_test $5A70` |
| 1 | `$02` | fluide (eau/vin) | — |
| 2 | `$04` | plein | — |
| 3 | `$08` | cassé / mort | `obj_flag48_test $5B1B` |
| 4 | `$10` | éclaire | — |
| 5 | `$20` | ouvert | `obj_flag20_test $5A85` |
| 6 | `$40` | animal | `obj_flag48_test $5B1B` |
| 7 | `$80` | visible | `$1B21` (`$00.+$07`) |

> **Cross-check externe** (`external_ressources/`) : le moteur ZX du même jeu
> (Megler/Mitchell, `Wilderland/`) partage **tout** le layout objet : `+00`
> nombre de lieux, `+01` porteur, `+02` volume, `+03` masse, `+05` force,
> `+07` attributs, `+08` nom, `+0A`/`+0C` adjectifs, `+10` lieux. Confirmé par
> `HobbitOSX/…/npc_stats.xlsx` (Strength/Mass/Volume des PNJ : Gandalf
> `15/60/70`, Trolls `90/90/A0`, Gollum `05/05/20`…) et par le manuel
> (`HobbitOSX/…/instructions.rtf`, « lois de la physique »).

## 3. Scripts et tables `$28CC`–`$2B11` (753 o) — qui fait quoi, et quand

### 3a. Tables INDIR (sauts 3 o `[clé,lo,hi]`, `$FF` termine sauf `$2943`)

`base` d'une entrée entité = sa table ; opcode `$x5`–`$xD` = `table[0]`,
`$xC` = PATCH (réécrit une ligne, PC inchangé), `$xF` = RAND parmi
`min(opérande,n)` cibles. Clés `$00` partout sauf `$2943` (5 cibles).

| Table | Taille | Entrées `[clé → cible]` |
|---|---|---|
| `$28CC` | 7 o | `00`→`$28E1`, `0B`→`$2940`, `FF` |
| `$28D3` | 7 o | `00`→`$2910`, `0B`→`$2940`, `FF` |
| `$28DA` | 7 o | `00`→`$2934`, `0B`→`$2940`, `FF` |
| `$2943` | 25 o | `00`→`$2964`, `00`→`$2971`, `00`→`$2975`, `00`→`$297A`, `00`→`$297E`, `1D`→`$2B0E`, `30`→`$2B02`, `0B`→`$2AED`, `$FF` |
| `$2984` | 10 o | `00`→`$298E`, `1D`→`$2B0E`, `0B`→`$2AED`, `FF` |
| `$29B2` | 10 o | `00`→`$29BC`, `0B`→`$29BC`, `1D`→`$2B0E`, `FF` |
| `$29C3` | 4 o | `00`→`$29C7`, `FF` |
| `$29E4` | 10 o | `00`→`$29EE`, `0B`→`$29FE`, `1D`→`$2B0E`, `FF` |
| `$2A2E` | 10 o | `00`→`$2A3D`, `0B`→`$2A46`, `1D`→`$2B0E`, `FF` |
| `$2A4D` | 7 o | `00`→`$2A54`, `0B`→$2A66, `FF` |
| `$2A70` | 7 o | `00`→`$2A77`, `0B`→`$2A81`, `FF` |
| `$2A88` | 7 o | `00`→`$2A8F`, `0B`→`$2AC0`, `FF` |
| `$2AC9` | 7 o | `00`→`$2AD5`, `0B`→`$2AED`, `FF` |

### 3b. Scripts VM (`$28E1`–`$2B11`, opcodes nibble bas, ≤6 ops/tick)

Propriétaires par point d'entrée (PC initiaux ; `base` = table §3a).
Détail des programmes : `docs/block4-analysis.md` (§ AnimAction).

| Entrée | Propriétaires (slot entité) |
|---|---|
| `$28E1` | `$3D` GOBLIN (e11), `$45` GOBLIN (e12) — MOVE `$10` arg `$06` + boucle MOVE `$30` |
| `$2910` | `$4B` GOBLIN (e13) — boucle MOVE+GOTO self |
| `$2934` | `$49` `$4A` `$4C` GOBLIN (e14–e16) — boucles MOVE+GOTO self |
| `$295C` | `$3E` GANDALF (e0) — errance (MOVE `$1D`/`$10`/`$24`/`$13`/`$0D`/`$0E`, ACT 1/2, RAND→4 cibles) |
| `$298E` | `$3F` THORIN (e1) — boucle |
| `$29BC` | `$40` ELF (e2) — boucle |
| `$29C7` | `$43` WARG (e3) |
| `$29EE` | `$42` BUTLER dormant (e4) — MOVE `$26`/`$10`/`$0D` arg `$08` |
| `$2A38` | `$41` ELROND (e5) — ACT 7/8 |
| `$2A54` | `$3C` DRAGON dormant (e8) — ACT `$6E59`→`$6C8D`→MOVE `$24` |
| `$2A77` | `$46` BARD dormant (e7) — ACT `$6C33` + MOVE `$13` arg `$25` |
| `$2A8F` | `$44` GOLLUM (e6) — ACT 13/14, MOVE `$0E`/`$01` arg `$10` |
| `$2AD0` | `$47` `$48` TROLL (e9–e10, lieu 5) — ACT 16/17 (trolls) |

### 3c. Événements différés `$2B12` (10×5 o `[id,cpt,actA,cond,actB]`, `$FF` en `$2B44`)

`evt_tick` (`$4E75`) : `cpt==0` → suivante (désarmé) ; sinon `cpt--` : si
`cpt>0`, `cond!=0` et `cond>=cpt` → `actB` (`$7169`) ; si `cpt` tombe à `0`
→ `actA` **une fois** (garde `L4E58`, RAZ par `world_tick`) puis `cpt := L4E58`.
Armement : `cpt := id` (`LDA $2Bxx / STA $2Bxx+1`), immédiat, `0`=désarme,
`e6 := 2+rand(8)` ; `id` = minuterie nominale. Validé harnais : `evt_act0`
(`$688D`) s'exécute à l'échéance de e0 (`$1D94` `$21`→`$20`).
Rôles : `docs/block4-analysis.md` (§ événements).

| Slot | Addr | id | cpt | actA | cond | actB | Rôle |
|---|---|---|---|---|---|---|---|
| e0 | `$2B12` | `$02` | 0 | `$01` | 0 | 0 | `code_6407` |
| e1 | `$2B17` | `$02` | 0 | `$02` | 0 | 0 | araignées `$66E8` |
| e2 | `$2B1C` | `$05` | 0 | `$03` | 0 | 0 | `$70CB` |
| e3 | `$2B21` | `$02` | 0 | `$04` | 0 | 0 | `$65A5` |
| e4 | `$2B26` | `$02` | 0 | `$05` | `$02` | `$05` | `$70D2`/`$6C67` (bog, auto-désarmant) |
| e5 | `$2B2B` | `$04` | 0 | `$06` | `$01` | `$07` | `$6B66` |
| e6 | `$2B30` | `$00` | 0 | `$08` | `$00` | `$00` | `$66A6`/`$66D2`, id nul (slot condamné ?) |
| e7 | `$2B35` | `$05` | 0 | `$09` | `$00` | `$00` | `$6A20` |
| e8 | `$2B3A` | `$04` | 0 | `$0A` | `$03` | `$0B` | `$70F8` |
| e9 | `$2B3F` | `$05` | 0 | `$0C` | `$01` | `$0D` | `$6AF0`/`$6D60`/`$70D9` (`$FF` en `$2B44`) |

### 3d. Entités `$2B45` (17×7 o `[id,nmax,PC_lo,PC_hi,base_lo,base_hi,reply]`, `$FF` en `$2BBC`)

`world_tick` (`$4E59`) → `entity_tick` (`$4ED5`, VM §3b). `nmax` (`+1`) =
**index maximal (0-based) dans la table `base` = nombre d'entrées − 1** (clamp
`script_indir`/`script_rand` : `min(opérande, nmax)`) ; `reply` (`+6`) = **poids
de réplique** : au seul site `npc_say_no` (`$5F81`), borne du tirage
`rand_range` décidant l'émission de `<id>SAY 'NO '` (`$15BE`, énigme ; `0` =
muet). Ni `nmax` ni `reply` ne sont jamais écrits. id `$00` = **dormant**
(`entity_tick` saute l'entrée) ; **l'activation se fait en écrivant l'id réel
dans `+0`**, par deux handlers d'événement dispatchés par la table à clés
`$709F` (`evt_lookup` `$5DE2`) : `evt_arme16` (`$70B5`, clé `$16`) pose `$42`
(BUTLER) puis le bit7 de sa fiche ; `evt_arme9` (`$70D9`, clé `$20`) pose `$3C`
(DRAGON) et `$46` (BARD) et arme l'événement **e9** (`$2B40` = e9.`cpt` := `3`).
Chaque pose est **gardée par le `+$07` bit3 de la fiche cible** (`$1DC5` butler,
`$1B37` dragon, `$1E54` bard) : si ce bit est posé (personnage « à terre » — le
combat le pose quand les PV tombent : `(orec)+7 |= $08`), le spawn est sauté
(un boss vaincu ne revient pas).

| Slot | Addr | id | nmax | PC init | base (table) | reply | Qui |
|---|---|---|---|---|---|---|---|
| e0 | `$2B45` | `$3E` | `$07` | `$295C` | `$2943` | `$05` | GANDALF (eloc `$01`) |
| e1 | `$2B4C` | `$3F` | `$02` | `$298E` | `$2984` | `$06` | THORIN (eloc ?) |
| e2 | `$2B53` | `$40` | `$02` | `$29BC` | `$29B2` | `$01` | ELF |
| e3 | `$2B5A` | `$43` | `$00` | `$29C7` | `$29C3` | `$00` | WARG (eloc `$15`) |
| e4 | `$2B61` | `$00`→`$42` | `$02` | `$29EE` | `$29E4` | `$01` | dormant → `$42` BUTLER (eloc `$20`) |
| e5 | `$2B68` | `$41` | `$02` | `$2A38` | `$2A2E` | `$05` | ELROND (eloc `$09`) |
| e6 | `$2B6F` | `$44` | `$01` | `$2A8F` | `$2A88` | `$03` | GOLLUM (eloc `$11`) |
| e7 | `$2B76` | `$00`→`$46` | `$01` | `$2A77` | `$2A70` | `$03` | dormant → `$46` BARD (eloc `$23`) |
| e8 | `$2B7D` | `$00`→`$3C` | `$01` | `$2A54` | `$2A4D` | `$00` | dormant → `$3C` DRAGON (eloc `$29`) |
| e9 | `$2B84` | `$47` | `$01` | `$2AD0` | `$2AC9` | `$01` | TROLL (eloc `$05`) |
| e10 | `$2B8B` | `$48` | `$01` | `$2AD0` | `$2AC9` | `$01` | TROLL (eloc `$05`) |
| e11 | `$2B92` | `$3D` | `$01` | `$28E1` | `$28CC` | `$00` | GOBLIN (eloc `$0F`) |
| e12 | `$2B99` | `$45` | `$01` | `$28E1` | `$28CC` | `$00` | GOBLIN (eloc `$3A`) |
| e13 | `$2BA0` | `$4B` | `$01` | `$2910` | `$28D3` | `$00` | GOBLIN (eloc `$40`) |
| e14 | `$2BA7` | `$49` | `$01` | `$2934` | `$28DA` | `$00` | GOBLIN (eloc `$12`) |
| e15 | `$2BAE` | `$4A` | `$01` | `$2934` | `$28DA` | `$00` | GOBLIN (eloc `$38`) |
| e16 | `$2BB5` | `$4C` | `$01` | `$2934` | `$28DA` | `$00` | GOBLIN (eloc `$10`) |

## 4. Blocs cassette SAVE (sources basses, §0)

`save_block` (`$3DAA` = `L3D3F` + `vec_03`/`tape_save`) : leader
(`$040B`), header 9 o, `$00`, données `[ptr,end)`, checksum EOR.
Header (écrit `Y=9..1` depuis `$36+Y`, vérifié sur flux réel) :
`$24 FF FF 50 50 end_hi end_lo ptr_hi ptr_lo FF`.
`code_72FC` (VERIFY) relit pareil et compare à `($37)` ; `$32`/`$33`
:= dest ; `$0417` (LOAD) : stub B1 (`harness/tape.s`).

Ordre SAVE/LOAD : ZP (`$0018`@`$00BE`), états (`$0556`@`$1B1A`),
scripts (`$02F1`@`$28CC`), records (`$05C8`@`$211A`) — params inline
`[len_lo,len_hi,src_lo,src_hi]` après chaque `JSR save_block`/`L3D6A`
(chaîne `tape_tramp` `$3D3F`, reprise JSR+4/5).

## 5. Records `$211A`–`$26E1` (1480 o) — lieux, objets, créatures

Table **`$2070`** : 80 mots (id→record, `L530B` ; id≥`$50` refusé,
`$2F`→`$0000` = nul). 79 records non-nuls `$00`–`$4F` sauf `$2F`
(`$50`+ = hors `L530B`, pointeurs vers `$8xxx` non-records).
Record = `[b0, b1, (mot,masque)×3, desc_lo, desc_hi, …]` ; `+8` = desc
(`$0000` = sans description propre) ; `b0`&`$0E` = **index de template** dans
`$2110` (pointeur bloc 3 / gabarit LOOK) ; `b0` bit6 = visite (posé au LOOK) ;
`b0` bit7 = visible/examinable (`act_p14_14` : bit7 clair → « IT IS DARK ») ;
`b1` bit6 = inclusion recherche (`$FF` sauf `$01`=`$A0`, `$2B`=`$B0`) ;
conds = signature d'appartenance (`code_433A`, groupes § factions).

`$00` = gabarit vide (`$FF $FF`, conds nulles, desc `$0000`).
Graphe des sorties par record : `docs/map.md` (triplets
`[dir,cond,dest]` + `$FF` après la desc).
`$13`/`$14` partagent desc `$1931` (b0 `$02`/`$80`).
Groupes : `$0F`+`$34`–`$41` (`AD07 9102 150A`, créatures),
`$44`–`$4A` (`BE17 2207…`, +`$0C` en repli), `$4B`–`$4D`
(`BE17 CD09…`), `$4E`/`$4F`, `$42`=WEST (`FF00 C20B`),
`$43`=EAST (`FF00 3503`), paires `$02`/`$2E` (`6B08 4904`)… ;
rooms quasi toutes uniques (`$01` = `EA14 180B 2906`, desc `$18AA`
= tunnel initial).

| id | Addr | b0 | b1 | conds | desc |
|---|---|---|---|---|---|
| `$00` | `$211A` | `$FF` | `$FF` | — | `$0000` (gabarit vide) |
| `$01` | `$2127` | `$84` | `$A0` | `EA14 180B 2906` | `$18AA` (tunnel départ) |
| `$02` | `$2563` | `$86` | `$FF` | `6B08 4904` | `$0000` |
| `$03` | `$2574` | `$84` | `$FF` | `4904` | `$0000` |
| `$04` | `$2135` | `$84` | `$FF` | `4F06` | `$18B3` |
| `$05` | `$214C` | `$84` | `$FF` | `F501 0F0B` | `$0000` |
| `$06` | `$2160` | `$84` | `$FF` | `BE07 0F0B` | `$18C1` |
| `$07` | `$2171` | `$04` | `$FF` | `E001 0F0B` | `$18D2` |
| `$08` | `$2585` | `$88` | `$FF` | `6608 8C08` | `$0000` |
| `$09` | `$217F` | `$84` | `$FF` | `5D88` | `$0000` |
| `$0A` | `$2190` | `$86` | `$FF` | `F806 D506` | `$18D6` |
| `$0B` | `$21A7` | `$84` | `$FF` | `D017 2207` | `$18E3` |
| `$0C` | `$21BB` | `$86` | `$FF` | `BE17 8802 2207` | `$18F5` |
| `$0D` | `$236A` | `$04` | `$FF` | `2603 B704` | `$0000` |
| `$0E` | `$21CC` | `$04` | `$FF` | `E011 EF05 2303` | `$18FC` |
| `$0F` | `$21DD` | `$04` | `$FF` | `AD07 9102 150A` | `$0000` |
| `$10` | `$22FA` | `$04` | `$FF` | `E401 3A01 B704` | `$190A` |
| `$11` | `$230E` | `$08` | `$FF` | `E705 A002 9102` | `$1922` |
| `$12` | `$231C` | `$04` | `$FF` | `AD07 9102 E40B` | `$0000` |
| `$13` | `$2330` | `$02` | `$FF` | `7684 9205 B704` | `$1931` |
| `$14` | `$2359` | `$80` | `$FF` | `7684 9E07 B704` | `$1931` |
| `$15` | `$237B` | `$84` | `$FF` | `8F07 020B` | `$0000` |
| `$16` | `$238C` | `$84` | `$FF` | `6D85 2B01` | `$0000` |
| `$17` | `$2596` | `$88` | `$FF` | `4F84` | `$0000` |
| `$18` | `$23A6` | `$88` | `$FF` | `7604 4904` | `$1936` |
| `$19` | `$23BA` | `$84` | `$FF` | `D007 3101 9F04` | `$193D` |
| `$1A` | `$23CE` | `$84` | `$FF` | `D007 8F09 A90A` | `$194D` |
| `$1B` | `$23E5` | `$84` | `$FF` | `4904 4409` | `$1955` |
| `$1C` | `$23F6` | `$84` | `$FF` | `F511 0E06 5F03` | `$1960` |
| `$1D` | `$240A` | `$84` | `$FF` | `6601 A002` | `$0000` |
| `$1E` | `$2418` | `$04` | `$FF` | `EE04 5003 D104` | `$0000` |
| `$1F` | `$242C` | `$04` | `$FF` | `2613 9102` | `$196E` |
| `$20` | `$243D` | `$04` | `$FF` | `EA01 5003` | `$1979` |
| `$21` | `$2451` | `$88` | `$FF` | `4F84` | `$0000` |
| `$22` | `$2465` | `$88` | `$FF` | `E785 5E06` | `$0000` |
| `$23` | `$247C` | `$84` | `$FF` | `EE8A E705` | `$198A` |
| `$24` | `$2493` | `$86` | `$FF` | `6688 8C08` | `$1998` |
| `$25` | `$24A4` | `$84` | `$FF` | `B802 0003` | `$19AC` |
| `$26` | `$24B5` | `$84` | `$FF` | `4F8B 8402` | `$19BB` |
| `$27` | `$24C9` | `$88` | `$FF` | `7604 6604` | `$19C5` |
| `$28` | `$24DD` | `$86` | `$FF` | `3188` | `$19D1` |
| `$29` | `$24F1` | `$84` | `$FF` | `EE84 7106` | `$19D9` |
| `$2A` | `$2505` | `$84` | `$FF` | `E408` | `$19E3` |
| `$2B` | `$2519` | `$04` | `$B0` | `AD17 3E09 E109` | `$19FA` |
| `$2C` | `$252A` | `$86` | `$FF` | `F886 5806` | `$1A01` |
| `$2D` | `$2552` | `$88` | `$FF` | `A50B` | `$0000` (objet sans état) |
| `$2E` | `$2541` | `$86` | `$FF` | `6B08 4904` (= `$02`) | `$0000` |
| `$2F` | nul | — | — | — | pointeur `$0000` |
| `$30` | `$25A7` | `$86` | `$FF` | `0007` | `$0000` |
| `$31` | `$25B8` | `$88` | `$FF` | `6608 D104` | `$0000` |
| `$32` | `$25CF` | `$84` | `$FF` | `4904 D604` | `$0000` |
| `$33` | `$25E0` | `$84` | `$FF` | `D007 6503` | `$0000` |
| `$34` | `$21F1` | `$04` | `$FF` | `AD07 9102 150A` | `$0000` |
| `$35` | `$2205` | `$04` | `$FF` | idem | `$0000` |
| `$36` | `$2213` | `$04` | `$FF` | idem | `$0000` |
| `$37` | `$222A` | `$04` | `$FF` | idem | `$0000` |
| `$38` | `$2241` | `$04` | `$FF` | idem | `$0000` |
| `$39` | `$224F` | `$04` | `$FF` | idem | `$0000` |
| `$3A` | `$2263` | `$04` | `$FF` | idem | `$0000` |
| `$3B` | `$227A` | `$04` | `$FF` | idem | `$0000` |
| `$3C` | `$228B` | `$04` | `$FF` | idem | `$0000` |
| `$3D` | `$229F` | `$04` | `$FF` | idem | `$0000` |
| `$3E` | `$22B0` | `$04` | `$FF` | idem | `$0000` |
| `$3F` | `$22BE` | `$04` | `$FF` | idem | `$0000` |
| `$40` | `$22D2` | `$04` | `$FF` | idem | `$0000` |
| `$41` | `$22E6` | `$04` | `$FF` | idem | `$0000` |
| `$42` | `$25F1` | `$86` | `$FF` | `FF00 C20B` | `$1A0F` (WEST) |
| `$43` | `$2602` | `$86` | `$FF` | `FF00 3503` | `$1A14` (EAST) |
| `$44` | `$2613` | `$86` | `$FF` | `BE17 2207` | `$0000` |
| `$45` | `$2627` | `$86` | `$FF` | idem | `$0000` |
| `$46` | `$263B` | `$86` | `$FF` | idem | `$0000` |
| `$47` | `$264C` | `$86` | `$FF` | idem | `$0000` |
| `$48` | `$2660` | `$86` | `$FF` | idem | `$0000` |
| `$49` | `$2674` | `$86` | `$FF` | idem | `$0000` |
| `$4A` | `$2685` | `$86` | `$FF` | idem | `$0000` |
| `$4B` | `$2696` | `$86` | `$FF` | `BE17 CD09` | `$0000` |
| `$4C` | `$26A4` | `$86` | `$FF` | idem | `$0000` |
| `$4D` | `$26B2` | `$86` | `$FF` | idem | `$0000` |
| `$4E` | `$26C0` | `$84` | `$FF` | `4F1B A002 D506` | `$0000` |
| `$4F` | `$26D1` | `$84` | `$FF` | idem | `$0000` |

## 6. Cycle de vie

Boot (`start`) : `boot_copy` (bas→haut, table `L30F9`, 4×6 o
`[len_lo,len_hi,src_lo,src_hi,dst_lo,dst_hi]`) → `keyin` → `boot_copyback`
(haut→bas) → `init_vars` → jeu. SAVE en jeu : prompts (`vec_06` PREPARE,
`vec_07` REWIND + VERIFY) + 4 blocs, retour boucle (`cmd_next` `$3E20`).
LOAD : prompt (`vec_05` PRESS ANY KEY) + `vec_02` + écriture directe en
bas (pas de `boot_copyback` : les dest sont les adresses basses) ;
échec → `TAPE LOADING ERROR` + reboot input (`JMP $2C3D`).

## 7. Résultats harnais (sim_tickdiff direct-SQLite : R2–R7, F1–F4,
repros — `build/sim/hobbit.db`, run `r1` supprimé : artefact)

- **Commandes sans effet = 0 octet** : `GET MAP` (déjà portée),
  `OPEN DOOR` (déjà ouverte), impasses certaines (tunnel :
  `SOUTH`/`WEST`), verbes rejetés (`LOCK`, `PULL`, `SHOW`,
  `FOLLOW X`, `EXAMINE <PNJ>`, `GET KEY`…). Nuance : mots
  inconnus / ordres manglés tickent quand même (~15 deltas,
  monde tourne) — 0 delta ≠ preuve de non-tick hors impasse ;
  seules les commandes qui réussissent *changent le récit*.
- **Porteur `+1` confirmé** : `$00`=joueur, `$FF`=personne, sinon id
  entité. Carte `$03` : `$3E`→`$00` (donnée au boot),
  `$00`→`$FF` (DROP), `$FF`→`$00` (GET), `$00`→`$3E` (Gandalf la
  reprend en terre morne). Clé `$04` : `$47`→`$FF` (troll mort, objet
  lâché). **`+0` (type) : jamais modifié** (tous runs).
- **Mouvement** : `ploc` `$C8` + `eloc` `$C9` suivent le lieu ;
  `obj` `$C5`/`crec` `$C6`/`$C7` = entité/record rencontrés
  (`$48` dans la salle des trolls) ; `$CC` `$00`→lieu.
  **Cluster résolu (statique)** : `+$10` clé `$00`, `+$B0`,
  `+$22E`, `+$240`, `+$256`, `+$2C6`, `+$331` = **tous des
  `eloc` (+$10)** des clés `$00` (joueur), `$03` (carte portée),
  `$3E` (Gandalf suit : `$01`→`$04`→`$01`), `$3F`/`$40`/`$43`
  (compagnons proches), `$44` (Gollum). `+$22E` « salle
  précédente » = en fait l'eloc de Gandalf qui suit.
- **`+0` (type) classé (statique)** : `$01` = localisé (lieu
  courant en `+$10` = eloc) ; `$02` (11 clés), `$03` (`$08 $09
  $18 $2A`), `$05` (`$07`), `$08` (`$17`) = **non-localisés**
  (pas de champ lieu, jamais modifiés tous runs) — régime autre
  (compteurs ? états globaux ?), sens fin ouvert.
- **Visite** : entrer dans une salle pose bit6 du `b0` de son record
  (`$84`→`$C4` : record `$04` en terre morne, `$05` au nord).
- **Ticks 960–966 (soak pur, 3 runs identiques) — les monstres
  s'éteignent, piloté par scripts** : e9/e10 PC figé à `$2AD0`
  pendant 959 ticks (attente multi-ticks tête de script `13 10 00
  D0 2A`), puis marche de blocs 5 o (`03 11 00 04 FF` ×3 +
  queue), dernier bloc = mort (`act_v14_17` `$6EA7` = `L7143`
  entrée 18 : `code_4D47` ×2, RAZ bit7 `$1F94`/`$1FA6`,
  `desc $2154`=`$1645`, `$214C`&=~`$40`, `L5713` ×2, dit
  `$16EB` ; e9/e10 usent aussi entrée 16 `act_v14_15` `$6E8B`
  = check/mange si même lieu, et 17 `act_v14_16` `$6CDB`).
  Dragon e5 : oscillation PC `$2A38`↔`$2A42` puis entrée 9
  (`act_v14_08` `$6E59`, tirage dragon-flying/burn) à 961.
  **Même signature plus tôt (trouvé via DB)** : e3 (`$43`,
  eloc `$15`) `id`→`$00` au **9e** tick monde, e2 (`$40`, eloc
  `$1C`) au **324e** (PC `$BC`→`$C0`, sans autre dégât).
  Table events intacte → countdown dans les opcodes (mécanisme
  exact du compteur : ouvert — `n` innocent).
  Gollum (`$44`) actif, dormants jamais réveillés (`id` `$00` +
  PC figés 1463+ ticks).
- **Mort joueur (R5/R6/F3/F4, narratif + deltas)** : dans la clairière,
  le hideous mange le joueur au **~3e tick monde de présence**
  (8 approches testées : KILL ×2, TALK, GIVE ×2, THROW AT, HIDE,
  WAIT — toutes mortes ; f3e : NORTH, WAIT, WAIT-mort+reboot) →
  `act_v14_15` (`$6E8B` : `ploc==5`, `obj==$47` → `$162B`/
  `$1615`), `e9.id` `$47`→`$00` (**gloutonnerie tue aussi le
  troll**), reboot restaure tout (`$00`→`$47`, PC `$D0` ; e10
  `$48` intact). Attaque : `WHICH TROLL ?` si générique (0 tick),
  `You attack the vicious troll. But the effort is wasted.` (20
  deltas, sans effet). Clé `$04` = `the large key` portée par le
  hideous (porteur `$47` confirmé narratif). Score : `You have
  mastered 2.5%…`.
- **Sortie de clairière (F4)** : `RUN SOUTH` (28 deltas) → ploc
  `$05`→`$09` (**Rivendell**, vivant, ticks suivants calmes) ;
  `SOUTH` seul/SW/SE/N/`UP`/`DOWN`/`GO SOUTH` = sur place ou 0.
  Rivendell : Elrond + `gives some lunch` = **clé `$26`**
  (porteur `$FF`→`$00`, eloc `$00`→`$09`). `EAST` terre
  morne→clairière aussi (2 sorties → `$05`). `$06` visité :
  record `$06` `b0` `$84`→`$C4` (premier bit jamais vu avant).
- **Rivendell et au-delà (F5)** : `EAST` `$09`→`$0A` (**Misty
  mountains**, `hard dangerous path`, sorties E/N/W/S, `the
  vicious warg` attaque — survécu 1 WAIT ; record `$0A` `b0`
  `$86`→`$C6` = visite) ; `WEST` `$09`→`$05` (retour clairière
  = mort + reboot tunnel). **Déclencheur du lunch** : donné à
  la 1re commande réussie après l'arrivée (f4c : LOOK tick12 ;
  f5e : TALK tick14 — les lignes vides ne comptent pas, 0
  delta). `TALK TO ELROND` ✓ (20, même signature) ;
  `EXAMINE ELROND/THORIN`, `GIVE LUNCH TO ELROND` = 0 (PNJ non
  examinables). `EAT LUNCH` = 0 **avant** réception du lunch ; une fois
  le lunch porté, `EAT` (et `EAT LUNCH`) le **consomme** (« You eat some
  lunch », journal séance 13).
- **Events `$2B12` : armés et déclenchés en jeu** (R2-R6 ne les
  armaient pas, mais la DB complète montre des `cpt` qui montent et
  redescendent). `evt_tick` décompte `cpt` : `actB` tant que
  `cond>=cpt`, `actA` **une fois** à l'échéance (garde `L4E58` = un
  `actA` par `world_tick`, reposée par `evt_act0`). Ex. `e0.cpt`
  (`$2B13`) alterne `0↔1` (armé à 2, décompté dans le tour d'armement)
  et `evt_act0` (`$688D`) s'exécute à l'échéance (`$1D94` `$21`→`$20`,
  run `f9a` tick 65). Armement = 14 sites gameplay (`cpt := id` /
  immédiat / `2+rand(8)`), ex. `evt_arme0` `$64E2` : tonneau (état `$13`)
  à Forestriver `$21` → e0:=2. e6 `id=$00` (slot tagué 0).
- **Entités** : seuls `PClo`/`PChi` bougent (errance : Gandalf 10 PC
  distincts ; boucles MOVE+GOTO `$34`/`$36`, `$38`/`$42`… ;
  e6/Gollum cycle 4 états `$2A8F`/`$2AAA`/`$2ABD`…).
  **Seuls `id` et `PC` mutent** (activation des dormants + errance) ;
  `nmax` et `reply` **jamais écrits** (config) — la DB ne montre que
  des deltas `$28CC` sur `+0/+2/+3` de chaque entité. **Tables INDIR :
  jamais patchées** (`$xC` non observé). `base` : fixe.
- **ZP** : seuls `$CA`/`$CB` bougent par tick (scratch) ;
  `$BF`–`$C4`, `$CD`, `$CF`–`$D5` : statiques partout (rôle inconnu,
  ni tick ni action testée).
- **Records** : 3 mutations vues (`b0` visite ×2, `desc` tick 966) —
  pas des gabarits inertes.
- **Compteur de chutes `+$0005`** (état `$00`, `$1B1A+5`) : `$40`→`$20`→
  `$10`→`$08`→`$04`→`$02`→`$01`→`$00` (>>1 par chute dans le noir),
  `$00`→mort+reboot (restauré `$40`). Budget ≈ 7-8 chutes. Seuls les
  mouvements **ratés** consomment (succès = gratuit) ; `WAIT`/`LOOK`/
  verbes rejetés (0 tick) = gratuits.
- **Lumière / salles sombres (`is_dark` `$4C82`)** : un lieu est sombre
  SAUF si un état `$1A62` est **au lieu du joueur** avec `+4` bit7 posé et
  `+7` (bits `$08`/`$04`/`$40` posés, `$10` clair). Seule la clé **`$0E`**
  (`$1CB0`, « the short strong sword », init eloc `$07`) matche → porter
  l'épée éclaire. Preuve : état `$0E`.eloc patché sur `ploc=$1F`/`$04`/`$09`
  → LOOK révèle la pièce (plus « IT IS DARK ») et liste « the short strong
  sword » ; sans patch : `I SEE NOTHING HERE. IT IS DARK.`. Corrige
  l'ancien « pas de lampe au jeu » (`docs/journal.md` séance 9) : la
  lumière existe, c'est l'épée (caverne des trolls `$07`, porte rock).
- **Verrous-fenêtres `+7` (`$80`/`$81`/`$A0`)** : `+$00F2` (état `$08`,
  porte rouge `$1F`), `+$0180` (état `$0C`, `$20`→`$21`), `+$00BB`
  (état `$06`, `$0E`/`$0F`) — cycle par rythme WAIT/mouvements ;
  seul `$A0` (bit `$20`) ouvre. Recettes : `(WAIT,SOUTHWEST)`×6 →
  `$1F`→`$1E` (5 chutes) ; `UP` → `$1F`→`$1E` **gratuit** (consomme
  le `$A0` d'arrivée, 2/2). `DOWN $0E` + `$A0` → **`$0D`**, pas
  `$0F` (2/2, F45d/e) — la fenêtre dévie, autre rythme requis.
- **Bounce `$20`→`$1F`** : au 1er tick-monde en `$20`, forcé
  (obj `$BE`→`$30`, +`$0161` `$01`→`$81`, +`$0550` `$41`→`$13`,
  sans chute) — suspect butler `$42` (eloc `$20`). Une seule
  action par visite `$20`.
- **Mouvements noir = non déterministes en apparence** : même
  direction, même rythme → dest variables (`$1E`→`$1F` vs `$20`,
  `$16` NW→`$31` vs `$14`). `SOUTH` en rafale ne sort jamais ;
  seul `(WAIT,DIR)` avance. F37c rejoué à l'identique = deltas
  identiques (`f37c_fast`, `-t 100 -s 100` validé) → sim
  déterministe ; les divergences F38 venaient d'un bug de
  construction cmdfile (`$(...)` mange les `\n` finaux →
  tick `SOUTHDOWN` fusionné), pas du hasard.
- **SAVE/LOAD décodés (octets, pas de VM)** : `tape_tramp` poppe
  l'adresse de retour de l'appelant = pointeur sur **params inline
  `[len src]`** (4 o → `ptr2`/`ptr`), reprise à param+4, `jmp ($6A)`
  = exécute le `jsr vec_0x` suivant. Le `18 00` après `jsr
  save_block` = len `$0018` (pas `CLC;BRK` — da65 affiche des params
  comme du code ; idem les « programmes BRK » et le ASCII-salad =
  params + `JSR $2C1D` + `JSR L471B` + `JMP L3C07`). `cmd_save` :
  `vec_06` + 4× `save_block` (ZP/états/scripts/records) + verify ;
  `load_handler` : `vec_05` + 4× `L3D6A` (charge direct en `(ptr)`,
  sans staging) + `jsr $2C1D` (`vec_08`=`L71FF`=`CLC`, no-op) +
  `L471B` + boucle. Pile retours logicielle `$0200`+`rstk`
  (`L46E6` push ptr/ptr2, `L471B`/`fetch_retaddr` pop).
  `($FFFE)` toujours `$FFFF` (jamais écrit) — aucun handler BRK.
- **Snapshots** (`harness/snap.s`, images `--snapshot`, runs
  `sna`/`snb`) : bypass `vec_02/03/04`, marqueur binaire `@@SNAP\n`
  +`NLEN+NOM+IDX+LEN`+payload, `sav/NOM.bin` (`"SNAP"`+3623) +
  table `snapshots`. 0-delta prouvé (LOAD==SAVE byte-exact).
  **Spin EOF-idle non neutre** : ~32 o réécrits sur 2G cycles de
  polls `keyin` à `$00` (pas de tick monde, mais side-effects) —
  valider à `-x` court ou via sim_tickdiff uniquement.
- **Résolus** : `+0` `$02/$03/$05/$08` = objets-figures non localisés, non
  discriminés entre eux (cf. §2) ; driver events (`actA` à l'échéance via la
  garde `L4E58`, cf. §3c) ; activation des entrants dormants (`$2B61`/`$2B76`/
  `$2B7D` par `evt_arme16`/`evt_arme9`, garde `+7` bit3, cf. §3d).
- **Reste ouvert** : compteur de tête `$2AD0`.

<!-- BEGIN AUTO-COUVERTURE -->
couverture (fusion sim_tickdiff+solver) : 237/3623 octets (6.5 %).

| Region | Octets | Couverts | % | Var couverts |
|---|---|---|---|---|
| `$00BE` ZP | 24 | 17 | 70.8 | 17/24 |
| `$1B1A` etats | 1366 | 105 | 7.7 | 105/549 |
| `$28CC` scripts | 753 | 37 | 4.9 | 34/61 |
| `$211A` records | 1480 | 78 | 5.3 | 66/79 |

Detail des variables : `scripts/memmap.py slots [--virgin]` ;
xref statique : `scripts/memmap.py xref`.
<!-- END AUTO-COUVERTURE -->
