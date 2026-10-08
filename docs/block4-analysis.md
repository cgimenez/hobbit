# Bloc 4 — The Hobbit (Oric, 1982)

Le **bloc 4** occupe `$2C00`–`$7A80` (20 097 octets) et contient le **programme
principal**. Le loader (bloc 1) lit successivement les blocs 2, 3 puis 4 et saute
à l'adresse de chargement du **dernier lu** (`$2C00`), c'est-à-dire l'autorun.

> Listing désassemblé : [`disasm/block4.asm`](../disasm/block4.asm) (généré par
> [`scripts/disasm.py`](../scripts/disasm.py) : descente récursive + point fixe,
> da65). Découpage vérifié par [`scripts/check_disasm.py`](../scripts/check_disasm.py)
> : **RÉSULTAT PROPRE** (0 opcode illégal, 0 BRK, toutes cibles alignées).

## Cartographie mémoire

| Bloc | Adresse | Taille | Rôle |
|------|---------|-------:|------|
| 1 | `$0400`–`$0500` | 257 | loader/chargeur cassette (jetable après usage) |
| 2 | `$0500`–`$2BBD` | 9 918 | table de données + textes + code appelé |
| 4 | `$2C00`–`$7A80` | 20 097 | **programme principal** |
| 3 | `$7AC0`–`$91B1` | 5 874 | overlay de données/code |

## En-tête et table de vecteurs (`$2C00`–`$2C34`)

- `$2C00` : `JMP $2C35` — point d'entrée autorun.
- `$2C03` : `.word $7AC0` — pointeur vers le bloc 3.
- `$2C05`–`$2C34` : **table de 16 `JMP`** (API interne).

| Vecteur | Adresse | Cible | Rôle (déduit) |
|---|---|---|---|
| `vec_init` | `$2C05` | `$77D4` | à déterminer (init/secondaire) |
| `vec_01` | `$2C08` | `$71A8` | attente d'un bit VIA (`$030D`) — timing/tape |
| `vec_02` | `$2C0B` | `$71DB` | **chargement bloc** cassette (via `$0417`) |
| `vec_03` | `$2C0E` | `$7215` | **sauvegarde bloc** cassette (leader + header + data + checksum) |
| `vec_04` | `$2C11` | `$71CB` | chargement (variante, force mode `$024D`) |
| `vec_05` | `$2C14` | `$72A0` | affiche « PREPARE TAPE… » + attente touche |
| `vec_06` | `$2C17` | `$7293` | affichage via `$440D` |
| `vec_07` | `$2C1A` | `$729B` | affichage via `$440D` |
| `vec_08` | `$2C1D` | `$71FF` | `clc / rts` (comparaison OK) |
| `vec_09` | `$2C20` | `$7204` | `STA $030B` = 0 (VIA) |
| `vec_10` | `$2C23` | `$7201` | `JMP print_cr` |
| `vec_11` | `$2C26` | `$7353` | lecture clavier (bas niveau) |
| `keyin` | `$2C29` | `$7481` | attend une touche, retourne le code `& $7F` |
| `print_cr` | `$2C2C` | `$7489` | affiche un CR (`$0D`) |
| `putchar` | `$2C2F` | `$7491` | sortie d'un caractère (activée par `$0B`/`$0C`) |
| `main` | `$2C32` | `$7779` | boucle principale / démarrage du jeu |

## Séquence d'initialisation (`$2C35` → `$2D9E`)

```
start:  JSR $3097          ; init mineure (met $6C=4, copie 6 octets)
        LDX #$FF / TXS     ; pile
        JSR $30BB
        JSR $2DC8          ; RAZ variables ($97.., $AF, $CC/$CD) puis JMP vec_15 (main)
        ; efface $47E3.. (X=$C8)
        ; $56=1, $65=$FF, $5E=$57=$C4=$0A=0, $0B=$0C=1
   si $65==$FF : JSR $4D84 ; puis affiche "> LOOK.\r" et copie "LOOK.\r" en $40BE
   boucle : JSR $2ED5 ; comparaison $D0 -> branchements
```

- `$2DAA` boucle de saisie : affiche les caractères de `$40BE` jusqu'à `$0D`/`$22`,
  écho via `putchar`, puis `JMP $2C99`.
- `$2DC8` finit par `JMP vec_15` (`$7779`) : passage à la **boucle principale**.

## Sous-système cassette

Le bloc 4 réutilise les **vecteurs du bloc 1** (loader resté en `$0400`+), ce qui
explique la présence des patchs ROM décrits dans
[`tape-archive-hobbit-1982-analysis.md`](tape-archive-hobbit-1982-analysis.md) :

- `$0411` setup · `$0405` synchro · `$0408` lecture octet · `$040B` leader ·
  `$040E` écriture octet · `$0414` reset statut · `$0417` lecture bloc complète.

| Adresse | Rôle |
|---|---|
| `$71BC`/`$71C8` | attente du signal cassette (bit `$030D`) |
| `$7215` (`vec_03`) | **SAVE** : leader, en-tête 9 o, données, checksum EOR, reset |
| `$71DB` (`vec_02`) | **LOAD** : via `$0417` puis vérification `$32/$33` |
| `$72FC` | LOAD : synchro `$0411/$0405/$0408`, en-tête en `$35,y`, données en `$37` |
| `$72A0` | invite « PREPARE TAPE FOR GAME SAVE » / « REWIND TAPE FOR VERIFICATION » / « PRESS ANY KEY WHEN READY » |

## Chaînes et données notables

| Adresse | Contenu |
|---|---|
| `$308F` | `"> LOOK.\r"` (prompt de départ) |
| `$3E25` | `"<TAPE LOADING ERROR :- PRESS ANY KEY TO RESTART GAME."` |
| `$72A9` | `" PREPARE TAPE FOR GAME SAVE"`, `"REWIND TAPE FOR VERIFICATION"`, `"PRESS ANY KEY WHEN READY"` |
| `$47C1`+ | traces de compilation : `'SUBS'`, `D:SUBS.MAC`, `D:DATA.MAC`, `D:SUBRONE.MAC`, `D:SUBRTWO.MAC`, `D:GENER.MAC`, `D:ACTION.MAC`, `D:ADVORIC` |
| `$4992`+ | `"?Command error"`, `"?File not found"`, `"?Can't enter file"` |

## Variables (zéro-page / page 2)

51 adresses nommées via `ZP_NAMES` (`scripts/disasm.py` → LABEL da65,
octet haut en `nom_hi`), rôles établis par recoupement exhaustif des usages
bloc 4 (contexte par routine, valeurs aux `sta`, patterns push/pop et
`($..),y`). Groupes :
- Sortie texte : `col` ($04, colonnes restantes, RAZ $28/ligne),
  `outen` ($0B), `phase` ($0C, 0=sonde/1=exec), `raw` ($0D, mode brut +
  capitales), `cap` ($0E, capitaliser la suivante), `sppend` ($0F),
  `crcnt` ($11, CR mod 16), `passok` ($12, sonde réussie).
- Commande : `wid` ($13, mot/direction), `arg1`/`arg2` ($15/$16,
  $FF=absent), `obj` ($C5, id courant), `orec`/`orec2` ($17/$19, pointeurs
  d'enregistrements, swap `L57A1`), `crec` ($C6, enregistrement courant,
  base $1B1A), `ploc`/`eloc` ($C8/$C9, lieux joueur/entité),
  `once` ($CE, one-shot).
- Messages : `adr` ($5C, adresse étagée), `tidx` ($6F), `nest` ($70),
  `wptr` ($71), `msgstk` ($76, pile $466F), `svA`/`svX` ($AD/$AE),
  `rstk` ($AF, pile retours $0200).
- Mouvement : `direct` ($73, =bit7 `xmode`), `variant` ($74, =bit6),
  `xaux`/`xmode` ($77/$78, nibbles de la sortie), `cond1`/`cond2`
  ($DC/$E2, 6 o), `svptr` ($E8, ptr sauvé), `exitp` ($F8,
  `$26DA+wid*8`).
- Travail : `ptr` ($8A, universel), `ptr2` ($88, balayages), `ptr3` ($7A).
- Monde : `key` ($8F, dispatch $709F), `noise` ($93, entropie),
  `exploc` ($BE, lieu attendu).
- Non nommés (multi-rôles ou non élucidés) : `$00`–`$03`/`$08`–`$0A`/`$10`
  (curseurs video), `$05` (largeur texte ET comparande `L5C07`), `$44`
  (octet de table, pas une variable), `$6A`/`$6B` (retour print_msg ET
  scratch parser), `$6C` (temporaire parser), `$75`/`$7F`/`$80` (bits
  sorties, sens fin inconnu), `$7E` (compteur boucles + temporaire),
  `$8C`/`$8D` (PC script VM ET curseur boot), `$C4` (filtre S→SH ?),
  `$D5`, `$BF`, zones parser `$5x`-`$Dx`, bandeau `$Ex`-`$Fx`, I/O `$1x`-`$3x`.
- `$32`/`$33` : adresse de chargement renvoyée par le loader ; `$37`/`$38` : pointeur d'écriture.
- `$024D` : mode cassette (fast/slow) ; `$0300`–`$030F` : VIA.

## Entrées/sorties (chemins observés sous harnais sim65)

- **Clavier, bas niveau `$7353`** : scan matriciel VIA (`$0302`/`$0303`/`$030C`,
  AY via `$7464`/`$7472`/`$7454`). Retourne A = touche (bit 7 = présente) ou
  bit 7 à 0 (absente). 4 sites d'appel : `keyin`, pauses `$7628`/`$7640`,
  SAVE (`$72A5`). **Seul point à shimmer pour l'input** (patch `JMP` en `$7353`).
- **`keyin` `$7481`** : `JSR $7353` en boucle `BPL` (attente bloquante),
  puis `AND #$7F`. Le `JSR keyin` du boot (`$2C3D`) est du code mort
  (`BNE` toujours pris après `LDX #$FF`).
- **`putchar` `$7491`** : filtrages `$0C`&`$0B`, `$0D`, `$C4` (dont conversion
  en capitales `AND #$5F`), puis rendu. Ne pas shimmer ici (logique jeu).
- **Rendu `$75B4`** : une touche → glyphe 8×6 dans le **bitmap hires `$A000`**
  (pas à pas de `$28`, `ORA #$40`), font = charset ROM via `($0403)` :
  `$FC70` (ROM 1.0) ou `$FC78` (ROM 1.1, après patch bloc 1). L'écran **texte
  `$BB80` n'est jamais écrit par le jeu** (tout l'affichage est en hires).
- **Pause `$7619`** (`CR` quand `$11==$0F`) : bip `$771A` (inopérant si
  `$0A==0`, valeur d'init), attente relâchement `$7628` (`BMI`), délai,
  attente pression `$7640` (`BPL`). C'est elle qui consomme le 1er octet
  des scripts : **préfixer d'une touche "page-turn"** (ex. `\rLOOK\r`).
- **Zones mémoire touchées au boot** : copie `$1B1A`→`$91D0` (1366 o, via
  `$3097` ; retour via `$30BB`), table `$28E6`+ → workspace haut (`$9740`+
  observé — base de données jeu probable, cf. AnimAction), fontes vers
  `$B7E8`+, clear hires `$7747` (`$40` sur `$A000`–`$BFDF`).
- **Réponse parser observée** : `I DO NOT KNOW THE WORD " XXX."` (mot inconnu
  quoté) ; `LOOK` re-décrit le lieu (`to the east there is the round green
  door`, `you see : the wooden chest.`, `Gandalf…`, `Thorin.`).

## Convention d'affichage `JSR $440D` / `JSR $5B24`

Le motif dominant du bloc 4 : **`JSR $440D` (`print_msg`) ou `JSR $5B24`
(`act_msg`, rebondit vers `print_msg`) suivi de 2 octets inline** = adresse
du message à afficher ; le code reprend à JSR+5 (queue `JSR $4737` /
`JMP ($6A)`, helper `$44BE` qui incrémente le pointeur). 99 sites `$440D`
recensés (115 pointeurs inline au total), chacun avec son mot pointeur marqué
`.word` (`msg_XXXX`) et un aperçu du texte en commentaire. Sans cette règle,
chaque site décalerait tout le désassemblage aval.

- 7 sites ont un pointeur **nul** (`$3CB4 $4DF9 $4E2D $52C3 $5BB5 $631A $63BE`
  → `TODO pointeur nul`) : slots `.word` remplis à l'exécution (idiome général,
  élucidé : constantes, lookups, `STX/STY` de `say_if_visible`…).
- Quelques pointeurs visent le **bloc 2** (`$1370`, `$165A`, …) : messages ou
  tables hors bloc 4, affichés `(hors image)` / bruts dans le listing.
- Pas d'appels ROM directs dans le bloc 4 : tout passe par les vecteurs du
  bloc 1 (`$0405`–`$0417`), patchés selon ROM 1.0/1.1.

## Moteur de messages (`render_text` $4444, `word_render` $4241)

Format décodé (validé par réimplémentation Python : les 32 mots `$1117` et le
dictionnaire sortent en anglais propre) :

- Octets `$20-$5F` : littéraux (espaces/capitales inclus, ex. `CHEERING CROWD`).
- Octets `$60-$7F` : 32 mots courants via la table bloc 2 `$1117`
  (`the/a/and/you/to/is/of/in/but/with/not/it/see/.../dragon/.../trolls`).
- Bit7 set : mot 2 octets du dictionnaire packé 5-bit (`(b&$1F)+$60`),
  pointeur `($05+(hi&$0F)):lo` (bloc 2, `$0500-$14FF`). Nibble haut = grammaire
  + fin : `$0/$1/$4/$5/$7` continuent (accords via `$C5`/`$15`, suffixes
  `S/ES/IES/ING` en `$4322`, espace auto `$0D`/`$0F`, wrap `$04`/`$05`) ;
  `$2x`=fin, `$3x`=fin+`.`, `$6x`=fin+CR (`text_end` $44AE).
- Octets `<$20` : 32 handlers via saut auto-patché (`token_dispatch` $44A0,
  table $4641 ; 23 valides, `$17-$1F`=0000 inutilisés) : `<$14` sous-routines
  (retour Z = saute `word_render`), `$14/$15/$16` = fins inline, autres =
  interpolation d'état (`tok_nested` $00 messages imbriqués, `tok_objC5` $06 /
  `tok_obj15` $07 / `tok_obj16` $09 noms d'objets, `tok_pronC5` $0C his/your,
   `tok_recurse` $0B recurse sur offset signé (queues partagées), `tok_skip`
   $02 GOTO offset signé (sans retour, `tidx=$FF`)…).
  `$05/$0A/$0F/$12` (`tok_noop`) réservés sans effet ; `$08` = vecteur `$2C2F`,
  `$0D` = CR inline.
- Sous-estimé initialement : le handler `$09` (`$456F`) coupait la plage
  `code_436C` (RTS `$456E`, JMP indirect invisible) → seed manuel, plages
  fusionnées. Espacement exact (flags `$0D`/`$0F` runtime) et pluriels : le
  décodeur statique approxime (espace avant mot sauf après espace/début).

## Bloc 2 : dictionnaire et catalogue de messages (`$0500-$1A0E`)

Le bloc 2 est la **banque de mots + messages** (émulation structurelle de
`render_text` en Python : tout sort en anglais propre, validé sur textes
observés sous harnais — `PREPARE TO DIE`, `WHAT HAS IT GOT IN ITS POCKET ?`,
`A CHEERING CROWD OF DWARVES...`, `I CANNOT DO THAT.`) :

- Banque `$0540-$1156` : **600 mots triés** (même format 5-bit que `word_render`
  : 2e car bit7 → continue, 3e → continue ssi bit7 du 2e, code 0 = fin).
  Index `$0500-$053F` : 1er mot de chaque lettre (26 entrées, X/Z nuls ;
  25/26 exacts — 7 lettres pointent des isolées D/E/L/N/S/U/W et O est décalé
  d'un : séparateurs de groupes ou entrées périmées, ouvert).
- Table `$1117` : 32 mots courants (`$60-$7F` = THE A AND YOU TO IS OF IN BUT
  WITH NOT IT SEE TOO AT CANNOT THIS I CARRYING BE DO HERE ON RIVER FROM
  DRAGON BLOW SIDE ARE DOOR THIEF TROLLS, pages `$05-$11`).
- Nibble haut du 2e octet = page (`$05`+nib) + flags : `$40` suffixe toujours,
  `$10` suffixe si `arg1`, sinon suffixe si `obj` (table `$4322` :
  S/ES/IES/BS+IES/D/ING — formes exactes = runtime, décodage statique entre
  crochets `[+S?]`), `$50` espace, `$60`/`$30`/`$20` fins, `$70` capitale.
- Catalogue `$1157-$1A0E` : **171 messages**, packing linéaire sans
  chevauchement (micro-messages 1-2 mots inclus : `HELLO` $143F, `THE` $13A6,
  `TO THE` $11EE, `<t10>DEAD.` $13D1). Zones : parser/inventaire `$1157-$1212`
  (erreurs, `TIME PASSES...`), combat `$1212-$1345` (~20 msgs : `VICIOUS CUT
  IN THE RIBS`, `BLOOD DRIPS`, `YOU CANNOT KILL WITH <obj>`), bateau
  `$1346-$139A` (GOTO `$1380→$134D`), prépositions `$13A6-$13BF` (IN/ON/
  BEHIND/UNDER/TIED+TO partageant la queue `THE` par 5 GOTO), templates LOOK
  `$13C0-$1412` (`VISIBLE EXITS ARE :`, micro-messages `<t06>SEE :`,
  `<t00>APPEAR.`), actions/PNJ `$1415-$1535` (warg, araignées, archery, bog),
  dragon `$153F-$155D` (`PREPARE TO DIE` ×2 verbatim), dialogues `$15BE-$1645`
  (riddle, trolls : `CAN YER COOK 'EM?`), portcullis/crack `$1650-$16B8`,
  chaîne Gollum `$16B9-$1721` + victoire `$1722`, score/hints `$178A-$1863`
  (`YOU HAVE MASTERED` + `%OF THIS ADVENTURE` assemblés), **29 descriptions
  de lieux `$18AA-$1A07`** (`$18AA` = tunnel initial : `A COMFORTABLE TUNNEL
  LIKE HALL` en 15 o, 1 littéral + 4 mots inline).
- Restes : suffixes exacts (contexte `obj`/`arg1` = runtime), interpolation
  tokens `$00-$13` (noms/objets), records lieux `$21xx` (slots desc mutables,
  ex. `$2154 := $1645`), mots morts `$07E5-$07F1` (table `$0732` ?).

## Événements différés : qui arme `$2B12`

Seconde moitié de `world_tick` (`evt_tick` `$4E75`, après `entity_tick`) :
balaye une table de **10 entrées 5 octets `[id,cpt,actA,cond,actB]`** en
`$2B12` (`$FF` termine en `$2B44`), dormante à l'init (compteurs 0) :

- `cpt==0` → entrée suivante ; sinon `cpt--`, si `<>0` → `evt_cond` (`$4E9D`).
- `cpt==0` (expire) : `cpt := L4E58` (réarme) ; si `L4E58==1` (jamais : aucun
  autre écrivain, voie `actA` **inactive** — `$688D $6F2A $6F1B $6903 $6C79
  $6E35 $6E54 $6D3D $6D55` intirés par cette voie) → dispatch `actA`.
- `evt_cond` : si `cond==0` → suivante ; si `cond < cpt` → suivante ; sinon
  `evt_fire` (`$4EAB`) : index `×2` dans la **table de sauts `$7169`**
  (16 cibles : `$6915 $688D $6F2A $6F1B $6903 $6C5F $6C79 $6DD0 $6E35 $6E54
  $6D3D $6D9F $6D55 $6DBB $AC06 $0917`), patch `L4C64/L4C65`, `jsr L4C5D`.
  Entrée suivante (`$88+=5`), fin (`$FF`) → `evt_end` (`$4ECC` : `$0B=1`).

Table initiale : e0 `[02,01,00,00]`, e1 `[02,02,00,00]`, e2 `[05,03,00,00]`,
e3 `[02,04,00,00]`, e4 `[02,05,02,05]`, e5 `[04,06,01,07]`, e6 `[00,08,00,00]`,
e7 `[05,09,00,00]`, e8 `[04,0A,03,0B]`, e9 `[05,0C,01,0D]` (`[id,actA,cond,actB]`,
cpt initiaux 0). Seuls `cond<>0` tirent : e4 bog (`$6C5F` : si `$C8==$1D` dit
`$1535` sink into the bog, sinon **auto-désarme** e4 — tirs à C=1,0), e5
(`$6DD0`, tirs C=1,0), e8 yeux (`$6D9F` dit `$16F0` pale bulbous eyes, tirs
C=3,2,1,0 = ×4, sans désarmement), e9 (`$6DBB`, tirs C=1,0). `cond=0` =
compte à rebours silencieux (e0,e1,e2,e3,e6,e7 armés pour rien via cette voie).

Armement (scan binaire exhaustif des `STA $2Bxx` : 17 sites, dont 3 écritures
table entités `$2B61/$2B76/$2B7D`) : idiome `cpt := id` (`LDA $2Bxx/STA $2Bxx+1`)
ou immédiat ou `0`=désarme ou aléatoire. **14 sites** : e0:=2 (queue objet
`code_6407`), e1:=id (araignées `act_p14_11` `$66E8`, avec dit `$1478`),
e2:=id (stub `$70CB`), e3:=id (routine orpheline `$65A5` en **zone données** :
`jsr $6222+$4D95`), e4:=id (stub `$70D2`) / e4:=0 si `$C8<>$1D` (`$6C67`),
e5:=id + dit `$168B` magic door (stub orphelin `$6B66`), e6:=0 (`$66A6`) /
e6:=2+rand(8) (`$66AA`), e7:=cond=0 donc désarme (`$6A19`), e8:=id (stub
`$70F8`), e9:=6 (`$6AEB` + `jmp $6D72` dit `$1685` hole vanish) / e9:=id
(`$6D5D`, tête active uniquement par voie morte) / e9:=3 (`$70D9`).

Une partie des stubs est dispatchée par **table à clés `$709F`**
(`evt_lookup` `$5DE2`, format `L5399`, clé `$8F`) : `$16`→`$70B5` (écrit
entité `$2B61:=$42`, en zone données — seed), `$1A`→`$70CB`,
`$1D`→`$70D2`, `$21`→`$7103`, `$02/$03`→`$70F8`, `$20`→`$70D9`, `$FF` fin.
Appelant de `evt_lookup` non établi (aucune réf. directe — listes `($8A)` ?) ;
idem stubs `$6689/$66AA/$6A19/$6B66/$65A5` (orphelins, via tables de dispatch
données comme la table d'actions étendue `$7020`, 30 mots). Restent intirés
par le ticker : `$6915` (tip aléatoire `$1485`, `actB` des `cond=0`), `$6F2A`
(flags web — le re-mend différé ne part jamais : à confirmer en jeu).

## Bloc 2 : scripts PNJ — VM AnimAction (`$28E1`–`$2B11`, `entity_tick` $4ED5)

Table `$2B45` : 17 entrées 7 o `[id, n, PC_lo, PC_hi, base_lo, base_hi, s6]`,
`$FF` en `$2BBC` ; id `$00` = slot dormant (3 : `$2B61 $2B76 $2B7D`) ;
14 actives `$3E $3F $40 $43 $41 $44 $47 $48 $3D $45 $4B $49 $4A $4C`
(PC initiaux `$295C $298E $29BC $29C7 $2A38 $2A8F $2AD0×2 $28E1×2 $2910
$2934×3`). Décodage statique exhaustif (`/tmp/vmdec.py`, non promu).

- Tour : `once` (test `L3E8E`) → préambule one-shot `$x0-4` (bit `$40`
  clair, via `code_3F7F`/`L46E9`/`L5127`) ; sinon dispatch nibble bas :
  pair `$x0/$x2` = MOVE 4 o (+2 si bit `$10`) `[wid,arg1,arg2]` via
  `entity_move` ; impair `$x1/$x3` = ACT 3 o (+2) via `L7143` ;
  `$x4` = MOVE court (`wid`, arg=`$FF`) ou saut (`$FF`+bit `$10`) ;
  `$xE` = GOTO absolu 3 o ; `$xC` = PATCH table (ligne clé := cible,
  PC courant inchangé — hang apparent, à vérifier sous harnais) ;
  `$xF` = RAND parmi `min(opérande,n)` cibles ; `$x5-$xD` = INDIR
  table[0]. **Budget 6 ops/tick** (`L4ED3`) = garde-fou des boucles
  (`GOTO self`, INDIR cycliques). Après move : bit `$20` → efface
  l'opcode (auto-modification) ; bit `$10` → saut calculé si échec.
- Base (entrée+4,5) = table de sauts 3 o `[clé,lo,hi]` (clés `$00`,
  réécrites par `$xC`) ; ex. `$3E`/`$2943` : 5 cibles `$2964-$297E`.
- ACT : octet b → **mot b** de la table `$7143` (38 o : sent `$FF0B` +
  18 mots — pas 15 !) : 1–15 = connues, **16–18 = 3 inédites**
  documentées (`act_v14_15/16/17`, checker PROPRE, rebuild OK) :
  `$6E8B` (si `$C8`==5 : sonde, `$C5`==`$47` ? `$1615` BLIMEY COOK EM
  : `$162B` MOUTHFUL [trolls]) ; `$6CDB` (visible : sonde, wid=`$1B`,
  `$60BF` + `JMP $5FAE` ; routine jumelle `$6CF9` collée derrière :
  tracking objet `$1FC1`/`$1FB2`) ; `$6EA7` = `$6E8B`+28 (sonde +
  `L4D47` ×2, RAZ bit7 `$1F94`/`$1FA6`, `$214C`&~`$40`, desc
  `$2154`=`$1645`, dit `$16EB` — **retombe sur le slot mutable des
  records**, § précédent).
- Scripts : `$3E` errance (MOVE `$1D`/`$10`/`$24`/`$13`/`$0D`/`$0E`,
  ACT 1/2, RAND→4 cibles) ; `$44` Gollum présumé (ACT 13/14, MOVE
  `$0E`/`$01`=NORTH/`$13` arg=`$10` = caverne aux torches) ; `$41`
  dragon présumé (ACT 7/8, eloc `$09`) ; `$47`/`$48` (ACT 16/17,
  eloc `$05`, template `EYE`) ; `$3D`/`$45` en `$28E1` (MOVE `$10`
  arg `$06` + boucle MOVE `$30`) ; `$3F`/`$43`/`$49`/`$4B` boucles
  `MOVE`+`GOTO self`.
- États `$1A62` : 60 clés (`$00-$2B`, `$3C-$4B` ; **trou `$2C-$3B`**)
  → blocs `$1Bxx` ; `L5331` (état mutable) ≠ `L530B` (record
  template) ; `L57BB` : état+0==1 → eloc=état+`$10` (`$3E`=`$01`,
  map `$03`=`$01` holder `$3E` ; `$41`=`$09`, `$43`=`$15`,
  `$44`=`$11`, `$47`/`$48`=`$05`) ; état+1 = porteur? (`$03`→`$3E`
  = Gandalf porte la carte au boot) ; état+8 = template description
  (tokens runtime `<t00>`/`<t08>`, illisible statiquement).
- Exits étendue : `$26DA`+wid*8 ; wid `$00-$0A` directions (mot +
  `AD 04`), wid `$0B+` **conditionnelles** (format `code_4141`,
  flags `$40`/`$60`/`$80` → direct/variant) jusqu'à ~`$28C2` (wid
  `$30`/`$37` valides : `$285A`/`$2892`) ; wids des scripts :
  `$01 $06 $0B $0D $0E $10 $13 $1D $24 $27 $30 $37` (ex. `$1D` =
  `8D C4 DE 0A 00 10 00 60`, `$10` = `8B 87…40`).
- Ouverts : trou `$2C-$3B` (voir § records : `$2D-$33` objets sans état,
  `$34`/`$35` faction sans état/slot, `$3C` futur — état `$1B30`
  pré-existant, identité à confirmer) ; `$xC` (0 occurrence dans les
  17 scripts : runtime-only si jamais) ; `n`/`s6` exacts ;
  eloc non-chambres (`$09`, `$38`/`$3A` = conteneurs ?) ; cohabitation
  scripts `$28E1` / copies boot (zone lue ET exécutée, ROM intacte).
- Dormants `$2B45` = **vrais scripts** (pas du garbage) : `$42`
  (`$29EE` : MOVE `$26`/`$10`/`$0D` arg `$08`), `$46` (`$2A77` :
  ACT `$6C33` + MOVE `$13` arg `$25`, loop), `$3C` (`$2A54` : ACT
  `$6E59`→`$6C8D`→MOVE `$24`, sauts calculés bit `$10` chaînés) ;
  activation = id seul (`evt_arme16` : `$2B61`:=`$42` si
  `($1DC5&8)==0` ; `evt_arme9` : `$2B76`:=`$46`, `$2B7D`:=`$3C`),
  PC/base résiduels valides (`$29EE` table[0]=self).
- Copies boot `L30F9` (4×6 o, via `boot_copy`) : `$1B1A`→`$91D0`
  (1366 o, états), `$28CC`→`$9726` (753 o, bases+scripts+tables —
  pas `$28E6`, la vraie source est `$28CC`), `$211A`→`$9A17`
  (1480 o, **records mutables**), `$00BE`→`$9FDF` (24 o, ZP) ;
  contiguës (`$9726`=`$91D0`+`$556`, `$9A17`=`$9726`+`$2F1`) =
  image SAVE/LOAD (`boot_copyback` = restore). Corrige le
  « `$28E6`+ » approximatif des notes précédentes.

## Bloc 2 : records lieux — layout `+0..7` élucidé (matcher `code_433A`)

Record = `[b0, b1, cond0_lo, cond0_hi, cond1_lo, cond1_hi, cond2_lo,
cond2_hi, desc_lo, desc_hi, ...]` (`L530B` : `*($2070+id*2)`, id `$2F` =
nul) ; 79 records non-nuls (`$00-$4F` sauf `$2F`), cond nulle
(`$00`×6) = `$00` uniquement.

- `+2..+7` = **3 paires (mot, masque-nibble)** = signature
  d'appartenance, comparée par `code_433A`/`code_436C`/`L4387`/`L43A8`
  (émulation fidèle validée) : paire `(0,0)` = absent (skip) ; sinon
  octet0 égalité complète, octet1 sur nibble bas ; repli `X=1`
  (paires croisées `p3[2,3]`↔`ex[4,5]`, `p3[4,5]`↔`ex[2,3]`, cf.
  `L380A` qui swapp `$F4`/`$F6` si `X=1`).
- Consommateurs (voies `cond_eval` selon `$73`) : direct=0 `L53C3`
  (scan table 3-o, filtre `(record)+7`&`$48` vs `$81`, compare
  **cond ↔ record+8**, retourne `(table)+0`) ; direct=1 `L54F8`
  (compare **cond ↔ record+2**, retourne `(table)+2`) ; `L37DE`
  (compare **cond ↔ entrée exit** depuis `exit_ptr`, `$6C`++,
  stop si paire0 `(0,0)`) ; `L363E` (record+1 bit6 → `ptr3`=record+8,
  cherche id==arg1 dans `$1A5F` filtré par match). Rôle : trouver les
  records compatibles avec la cond de l'argument du move (objets du
  lieu / faction).
- Groupes (conds partagées) : `$0F`+`$34-$41` (`ad 07 91 02 15 0a`,
  faction créatures), `$44-$4A` (`be 17 22 07…`, +`$0C` en repli),
  `$4B-$4D`, `$4E-$4F`, paires `$02`/`$2E` `$08`/`$24` `$17`/`$21`
  `$03`/`$1B`/`$32`, directions `$42`=WEST (`c2 0b`) `$43`=EAST
  (`35 03`) ; rooms quasi toutes uniques (ex. `$01` =
  `ea 14 18 0b 29 06`).
- `b0`/`b1` = type/flags : `b0`&`$0E` = template LOOK (`L4DC6` →
  `$2110`), bit7 ? (`$13`/`$14` même desc `$1931`, b0 `$02`/`$80`) ;
  `b1` = `$FF` sauf rooms `$01`=`$A0` et `$2B`=`$B0` (bit6 testé par
  `L363E`, absent de `$A0`/`$B0` ; bit7 ?).
  Décodeurs : `/tmp/condmatch.py`, `/tmp/condmat.py` (non promus).

## Bloc 4 : commandes spéciales et SAVE/LOAD (`$3B75`, `$3D3F`–`$3E40`)

- Dispatch (`L3B75`/`L3B9F`) : le mot parsé (`adr`, lo + hi&`$0F`)
  comparé à la table **$3BC6** (13 clés 2 o) ; match → `jmp (L3BC4)`
  vers la table **$3BE0** (13 cibles) : ALL `$3C26`, EXCEPT `$3C0E`,
  IT `$3C33`, ONE `$3135`, PRINT `$3BFA`, NOPRINT `$3C03`,
  (mot impossible `(3D,06)`) `$3D7F` = **LOAD** (prouvé sous harnais :
  taper LOAD → `PRESS ANY KEY WHEN READY`), SAVE `$3DD9` (mot
  `$0DA0`), QUIT `$3C88` (score + `JMP $2C3D`), HELP `$3C8E`,
  SCORE `$3CCE`, PAUSE `$3D39`. Verbes ordinaires : table **$6FAC**
  (23 entrées `[wid,lo,hi]`, `$01-$0A` = mouvements → `$5D44`) ;
  objets : `(orec)+1` bit7 → `L7014` vs `L7114+X` (`L4BA3`) ;
  compatibilité verbe/objet : liste en record+`$10` (`L52EA`).
- SAVE (`cmd_save` `$3DD9`) : `vec_06` (PREPARE TAPE) + 4×
  `save_block` (`$3DAA` = `L3D3F` + `vec_03`/`tape_save`, params
  inline `[len src]` : ZP `$0018`@`$00BE`, états `$0556`@`$1B1A`,
  scripts `$02F1`@`$28CC`, records `$05C8`@`$211A`) + `vec_10` +
  `vec_07` (REWIND + VERIFY) + 4× `save_block` via `$3DC4` + fin
  `cmd_next` (`$3E20` : `L471B` + `JMP $3C07`). Échec → `save_err`
  (`$3DBC` : dit `$1A1A`, `keyin`, abandonne params). En-tête bloc :
  10 o (`$FF/start/end/$50/$50/$FF/$FF/$24`), checksum EOR (`$3B`).
- LOAD (`load_handler` `$3D7F`, fall-through après erreur LOAD
  comme `$6EA7` dans `$6E8B`) : `vec_05` (PRESS ANY KEY) +
  `L3D6A` (`L3D3F` + `vec_02`/`tape_load`, `SEC` = échec) + copies
  workspace→bas ; échec → dit `$3E26` (TAPE LOADING ERROR) +
  `JMP $2C3D` (reboot input). Boot : `boot_copy` (bas→haut) puis
  `boot_copyback` (haut→bas, table `L30F9`) ; `$65`≠`$FF` →
  `L2DEA` ; `$56` = flag images (`img_show`, `N` au boot = sans).
- Ouverts : idiome exact `L3D3F`/`tape_tramp` (reprise JSR+5 vs
  `JMP W(params)`, à relire) ; mot `(3D,06)` sans entrée dico
  (`LOAD` = `$0B3D`, `BFLOAD` = `$0B3B` : artefact de rendu,
  matching à éclaircir) ; `L7114+X` (`$596C`/`$796C`/`$1B4C`…).
- Harnais : taper LOAD sous sim65 (EOF) affiche le prompt puis
  timeout (exit 254) — le stub B1 nourrira `L0408` en `PVRead`.

## Bloc 3 : illustrations vectorielles (`$7AC0`–`$91B1`, 5 874 o)

Le bloc 3 est une **banque d'images** : table à clés `$7AC0` (13 entrées
`[clé,mot]`, `$FF` en `$7AE7`, lookup `L5399` pas de 3) + 13 flux d'octets
`$00`-terminés, tuilés sans trou (`$7AE8`→`$91AF`, double `$00` en `$809E`,
`$00 $CB` final). Zéro texte ASCII ≥24 o : tout est dessin.

- Moteur (`vec_init` `$77D4`, X/Y = adresse image) : `vec_setup` (`$7990`,
  octet mode = couleurs : bas = encre, haut = papier) efface hires
  `$A000`–`$B3FF` (`$40`) + 2 aplats ; puis dispatch d'octets : `$00` fin,
  `$08` `vec_pos` (curseur `$30`/`$31`, 2 o), `$20` `vec_skip` (saute
  jusqu'à `$FF`, repris en ligne), bit6 `vec_fill` (remplissage), bit7
  `vec_line` (segment, 2 o), sinon avance. Chaque image commence par
  `[mode,$08,x,y]`. Lignes puis fills : le fill boucle pixel par pixel
  (`vec_plot` `$7A0F` via `($38/$39)`+masque `L7A5F`) — **d'où la lenteur**
  (~33 M cycles/image sous sim65).
- Usages bloc 4 : `img_show` (`$4750`, depuis `code_4DF6`) — lookup clé,
  `vec_init`, `keyin` (tourne-page) ; `L6EF7` (clé `$05`, depuis `L64AE`/
  `code_6EE9`) — lit `(ptr)+1/+2` comme **pointeur de données** et y poke
  2 octets (`$00/$10` ou `$03/$03`).
- Clés : `$01 $06 $0B $25 $26 $07 $0D $15 $20 $19 $29 $1A $27` (modes
  `$05 $02 $01 $13 $04 $14 $03 $01 $04 $04 $05 $01 $56`) — plausiblement des
  ids de lieux (à confirmer en jeu : image de la clé == lieu ?).
- Cas notés : l'image `$0D` (`$8766`) **contient** l'image `$15`
  (`$8783`–`$887B`) précédée de 29 o (rendus comparés : composite réel,
  pas d'artefact) ; la clé `$05` est **absente** de la table → `L5399`
  s'arrête au `$FF` (`$7AE7`) et `L6EF7` poke en `$0805`/`$0806` (bloc 2,
  sans lecteur bloc 4 — patch intentionnel, table patchée à l'exécution,
  ou chemin mort : ouvert).
- Validation : pilote sim65 (reset détourné sur driver `$E800` : `vec_init`
  + `shim_kb` pour dumper, 13 cibles) → 13 frames hires → 13 illustrations
  distinctes et cohérentes (visages, scènes, dragon). Coût : `-x 600M`.

## Outillage

- `scripts/disasm.py` : **descente récursive** (entries `$2C00`, `$2C35`, 16
  vecteurs) + point fixe (seeds radare2 validés par `try_decode`, `MANUAL_ENTRIES`
  pour le dispatch indirect, `SEED_EXCLUDE` pour les faux positifs comme
  `fcn.00006dce` qui chevauchait un pointeur `$440D`). Le résultat de `afl` est
  mis en cache dans `disasm/.r2_afl.txt`.
- `scripts/opcodes6502.py` : table des 150 opcodes légaux 6502.
- `scripts/check_disasm.py` : contrôles A–H (sync linéaire avec règle `$440D`,
  cibles de branches/JSR/JMP, tables ressemblant à du code, ROM, vecteurs,
  pointeurs marqués, `ROUTINE_DOCS`). Sortie 0 = propre.
- `disasm/hobbit.info` : fichier d'information da65 (ranges code/données + labels).
- `disasm/block4.asm` : listing annoté — **16 980 o de code**, 99 sites
  `$440D` (118 inline `$440D`/`$5B24`), 130 routines documentées (dont 10
  `vec_*`/`img_show`, 33 actions `L7014`/`L7143` et 6 handlers SAVE/LOAD),
  0 conflit.

Régénérer et vérifier :

```
.venv/bin/python scripts/disasm.py
.venv/bin/python scripts/check_disasm.py   # viser exit 0 (RÉSULTAT: PROPRE)
```

## Limites

- Le découpage **code/données est validé statiquement** (checker exit 0), mais
  7 pointeurs nuls et les zones atteintes par dispatch indirect reposent sur des
  `MANUAL_ENTRIES` arbitrées à la main (trampolines `JSR`+`JMP`, routines
  `LDA $C5`/`LDA $1F76`+`RTS`, 33 actions `L7014`/`L7143`, token `$456F`, etc.).
- Auto-modification : `STA $6A5C` patch un octet relu par `LDA $6A5C` (donnée
  conservée en table, code adjacent marqué à partir de `$6A5E`).
- Les rôles des vecteurs `vec_init`, `vec_06`, `vec_07` restent à confirmer.
- Prochaines étapes : `+0..7` des records lieux, trou `$2C-$3B`, sémantique
  `$xC`, table `$28E6`, dormants `$2B45` (harnais ciblé ou statique).
