# Bloc 4 — The Hobbit (Oric, 1982)

Le **bloc 4** occupe `$2C00`–`$7A80` (20 097 octets) et contient le **programme
principal**. Le loader (bloc 1) lit successivement les blocs 2, 3 puis 4 et saute
à l'adresse de chargement du **dernier lu** (`$2C00`), c'est-à-dire l'autorun.

> Listing désassemblé : [`disasm/block4.asm`](../disasm/block4.asm) (généré par
> [`scripts/disasm.py`](../scripts/disasm.py) : descente récursive + point fixe,
> da65). Découpage vérifié par [`scripts/disasm_check.py`](../scripts/disasm_check.py)
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
| `main` | `$2C32` | `$7779` | `game_main` : initialisation de l'écran hires (bordure, clear, police) |

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
- `$2DC8` finit par `JMP vec_15` (`$7779`, `game_main`) : celui-ci prépare
  l'écran hires (bordures, clear, police) puis `RTS` **dans** `start`, qui
  poursuit sa boucle. La « boucle principale » est donc `start` (`$2C35`), pas
  `game_main` (correction d'une note antérieure).

## Sous-système cassette

Le bloc 4 réutilise les **vecteurs du bloc 1** (loader resté en `$0400`+), ce qui
explique la présence des patchs ROM décrits dans
[`tape-archive.md`](tape-archive.md) :

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
| `$47C1`+ | traces de compilation (voir ci-dessous) : `'SUBS'`, `D:SUBS.MAC`, `D:DATA.MAC`, `D:SUBRONE.MAC`, `D:SUBRTWO.MAC`, `D:GENER.MAC`, `D:ACTION.MAC`, `D:ADVORIC` |
| `$4992`+ | `"?Command error"`, `"?File not found"`, `"?Can't enter file"` |

### Artefacts de développement (`$477C`–`$49B3`)

Cette zone n'est **pas du code du jeu** : le code s'en sert comme **tampon de travail**
(`sta $4783,y`, `lda $47C3,y`, `cmp $490F,y`, `lda $4927,x`…). Les octets qu'on y lit
sont l'**état périmé** du tampon au moment où la cassette a été enregistrée : les
développeurs n'avaient pas effacé la mémoire, qui contenait encore des restes de leur
session d'assembleur/DOS. C'est donc un fragment du **fichier de commande d'assemblage**
du jeu, décodé en texte (`$477C`–`$494A`) :

```
X 'SUBS'
        INCLUDE D:SUBS.MAC
        .PRINTX 'DATA'
        INCLUDE D:DATA.MAC
        .PRINTX 'SUBRONE'
        INCLUDE D:SUBRONE.MAC
        .PRINTX 'SUBRTWO'
        INCLUDE D:SUBRTWO.MAC
        .PRINTX 'GENER'
        INCLUDE D:GENER.MAC
        .PRINTX 'GENER2'   ...
   INCLUDE D:ACTION.MAC
        .PRINTX 'GENACT'
P..:=D:ADVORIC
```

Enseignements :

- Directives `.PRINTX` / `INCLUDE` : macro-assembleur lisant les sources sur disquette
  (`D:`), extension `.MAC`.
- **Modules source du jeu** : `SUBS`, `DATA`, `SUBRONE`, `SUBRTWO`, `GENER`, `GENER2`,
  `ACTION` (les `.PRINTX` servaient à tracer l'inclusion de chaque module).
- **Nom du binaire final** : `ADVORIC` (= *ADVenture* + *ORIC*), via `:=D:ADVORIC`
  (spécification de sortie de l'éditeur de liens).
- Messages du gestionnaire de fichiers de l'outil (`$4992`+) : `?Command error`,
  `?File not found`, `?Can't enter file`.

Aucun nom d'auteur, copyright, date ni numéro de version n'apparaît dans l'image.

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
- **Lecteur ligne `L406D`** (boucle d'input `L2E04`, prompt `"> "` en
  `L2DEA`) : `JSR vec_11`, si pas de touche compte à rebours `$61`/`$62`
  (rechargé `$7530` à chaque touche) puis **auto-`WAIT` d'inactivité** :
  recopie `L40BA` (`57 41 49 54` = `WAIT`) + `$0D` dans le buffer `$40BE`
  avec écho (`L408F`). Sous harnais EOF = `WAIT` infini (horloge gratuite,
  ~coûteux en cycles : préférer `WAIT` explicite). Écho `> CMD.` sur la
  même ligne que le prompt (pas de `CR` après commande vide ni après
  `SAVE` : plusieurs prompts par ligne possibles).
- **Touches curseur `L2EA9`** : `$08`/`$0A`/`$0B`/`$15` → poke `W`/`S`/`N`/`E`
  + `$0D` dans `$40BE` avec écho (`L2EBC`) : les flèches déplacent
  immédiatement (Oric). `@` (`$40`) en tête → `L2DDB` (2× `$08`, retour 0).
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

## Parser AnimTalk (`$2DDB`–`$356E`)

Le parser transforme une ligne tapée au clavier en une **commande** interne
(verbe, objets, direction), consommée ensuite par la boucle principale
(`start` `$2C35` → `parse_cmd` puis exécution). Trois étages :

```
touches ──read_line──> tampon $40BE ──tokenize (mot à mot)──> file $4783
        ──parse_cmd──> commande (wid $13, arg1 $15, arg2 $16) ──> exécution
```

Toutes les routines de cet étage sont nommées dans le listing (`ROUTINE_DOCS`),
les points chauds annotés au niveau instruction (`INLINE_COMMENTS`).

### 1. Saisie — `read_line` (`$2DEA`)

- Affiche le prompt `"> "`, puis lit les touches (via `L406D`) et les stocke
  dans le **tampon de commande `$40BE`**.
- **Toujours terminer par un point** : `ins_period` (`$2E98`) ajoute `.` si la
  ligne n'en a pas — ce point devient le **marqueur de fin** du lexeur.
- Guillemets `"` : `ins_quote`/`$B8` gèrent l'ouverture/fermeture (un nom
  peut être mis entre guillemets). `line_backspace` (`$2E24`) et `line_del`
  (`$2E1A`, touche DEL) corrigent la saisie.
- **Flèches** : `key_arrow` (`$2EA9`) écrit directement `N`/`S`/`E`/`W` + CR
  (les flèches Oric déplacent donc **immédiatement**, sans verbe).
- `'@'` en tête (`input_abort` `$2DDB`) recule de 2 et annule.
- Retour : `A=1` quand la ligne est close (CR), `A=0` pour annulation.

### 2. Lexeur + dictionnaire — `tokenize` (`$2ED5`)

`tokenize` lit **un mot** à partir de X dans `$40BE` et le cherche dans le
dictionnaire 5-bit du bloc 2 :

1. Saute les espaces ; un CR produit le token de **fin `$C0`** (`lex_cr`).
2. `punct_class` (`$2FA3`) reconnaît la ponctuation : point `$B0`,
   virgule `$A0`, guillemet `$90`.
3. `dict_bucket` (`$2FBB`) décode les lettres du mot (codes 5 bits rangés en
   `$47C3`) et se place sur le **seau** `$0500[2×1ʳᵉ lettre]` ; la boucle
   `dict_next`/`word_prefix_cmp` balaye les entrées (matcher exact/préfixe).
4. `word_finish`/`word_type` (`$2F43`/`$2F78`) extrait le **type** et l'adresse
   du mot. Type `$D0` = entrée **ignorée** par le parser (vocabulaire réservé
   aux messages, cf. classes ci-dessous).

Le **mot est ensuite empilé** dans la file `$4783` par la boucle `$2CAC`, au
format `[type<<4 | page, lo]` (2 octets/mot). Un mot inconnu
(`$D0`) déclenche le message `I DO NOT KNOW THE WORD`. Le lexeur gère les
**abréviations** : `$2EFF` examine un candidat plus court suivi d'une entrée
plus longue (`word_finish`/`dict_next`).

### 3. Grammaire — `parse_cmd` (`$3111`)

`parse_cmd` consomme la file via `next_token` (`$3485`) et **dispatche chaque
mot sur sa classe grammaticale** : `classe = type >> 3` (soit `2×nibble`),
saut indirect via la **table `$315A`** (12 adresses de handlers, auto-patchée
en `$3158/$3159`).

Classes (nibble de type du mot, reconstruit depuis les bits 6-5 des 2 premiers
octets de l'entrée — vérifié en décodant les 600 entrées du bloc 2) :

| nibble | type | classe | contenu observé | handler |
|---|---|---|---|---|
| `$00` | `$00` | 0 | adverbes (QUICKLY, SOFTLY, CAREFULLY…) | `cls_adverb` `$3299` |
| `$10` | `$10` | 1 | IN, INTO | `cls_prep_in` `$337D` |
| `$20` | `$20` | 2 | directions (N/S/E/W, NE, DOWN, UP…) | `cls_direction` `$328F` |
| `$30` | `$30` | 3 | verbes (LOOK, GET, OPEN, KILL…) | `cls_verb` `$32F3` |
| `$40` | `$40` | 4 | GO, RUN | `cls_go` `$32E9` |
| `$50` | `$50` | 5 | noms (objets, créatures, lieux) | `cls_noun` `$33C8` |
| `$60` | `$60` | 6 | adjectifs | `cls_adjective` `$33BF` |
| `$70` | `$70` | 7 | prépositions (ON, WITH, THROUGH…) | `cls_preposition` `$3390` |
| `$80` | `$80` | 8 | articles/déterminants (THE, A, AN…) | `cls_article` `$3374` |
| `$90` | `$90` | 9 | mots-clés spéciaux (SAVE, QUIT, HELP, ALL, EXCEPT…) | `$3B9B` (scan `$3B75`) |
| `$A0` | `$A0` | 10 | AND / virgule | `cls_conj` `$32B9` |
| `$B0` | `$B0` | 11 | THEN / point = **fin de commande** | `cmd_end` `$3172` |
| `$D0` | `$D0` | — | ignoré (le lexeur poursuit la recherche) | — |

> Le point `$B0` est **ajouté par l'éditeur** en fin de ligne : c'est lui qui
> termine proprement la commande (le CR `$C0` n'atteint jamais le dispatch).

Chaque handler renseigne l'état de parsing : `$6D` = drapeaux d'attente,
`$6E` = portée (`0` normal, `1` ALL, `2` EXCEPT — posés par les mots-clés
spéciaux ALL/EXCEPT `$3C26`/`$3C0E`), `$9D` = compteur de virgules, `$65` =
nombre de mots retenus, `$5A`/`$5B` = type précédent/courant, `$5F` = curseur
de file, `$A3..$AC` = **groupe nominal courant**, et `(ptr2)` = enregistrement
de commande de travail (24 octets ; helpers `rec_*` : `$34BD` recule, `$356E`
avance, `$34D0` fusionne).

**Retour** de `parse_cmd` : `A=0` commande construite, `A=1` → `WHAT ?`
(`$1177`), `A=2` → recommencer la saisie (`$2D42`).

### 4. Exécution — `cmd_run` (`$357C`) → `perform_action` (`$4B37`)

Une fois la commande construite, `start` l'exécute :

- `cmd_run` (`$357C`) tente d'abord de la traiter comme un **déplacement** ;
  sinon `cmd_probe` (`$36D5`) la rejoue en **mode sonde** et positionne `$57`
  (1 = commande spéciale, 2 = action de lieu, 3 = rien) pour `start`.
- `perform_action` (`$4B37`) exécute l'action ordinaire : résolution des objets
  (`orec`/`orec2` via `obj_record` `$5331`, contrôle `obj_check` `$4CDF`),
  obscurité (`is_dark` `$4C82` → `I SEE NOTHING HERE.`), compatibilité
  verbe/objet (`verb_obj_ok` `$52EA`), puis dispatch dans la table d'actions
  `$7014` (objet normal) ou `$7114` (étendue) par `indirect_call` (`$4C5D`).
- `describe_room` (`$417C`) rend le texte du lieu à partir de la fiche de sortie
  (`exitp`, `$26DA+wid*8`).
- `special_cmd` (`$3B75`, classe 9) court-circuite les actions : `SAVE`, `LOAD`,
  `QUIT`, `HELP`, `SCORE`, `PAUSE`, `ALL`, `EXCEPT`, `IT`, `ONE`, `PRINT` (tables
  `$3BC6`/`$3BE0`).

Après une action réussie, `world_tick` (`$4E59`) fait avancer le monde : VM des
PNJ (`entity_tick` `$4ED5`) puis événements différés (`evt_tick` `$4E75`).

- Validé sous harnais (cf. `docs/status.md` §AnimTalk) : directions nues,
  `GO EAST` (= verbe transitif), mots inconnus, `OPEN CHEST`, `GET MAP`,
  insensibilité à la casse (écho normalisé en capitales).
- **Ouverts** : sémantique fine des bits de `$6D` ; rôle exact de `cls_prep_in`
  (n=1) et des enregistrements `rec_*` ; cohabitation avec les artefacts de
  développement `$477C`–`$49B3` (les tampons `$4783`/`$47C3`/`$490F`/`$4927`
  recouvrent cette zone : état périmé réutilisé comme scratch).

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

## AnimAction : les personnages autonomes

AnimAction est le second système élucidé du jeu (après AnimTalk) : chaque
personnage **vit sa propre vie** — il se déplace, parle, ramasse des objets,
attaque — **même quand le joueur est ailleurs**. Le « cerveau » de chaque PNJ
est un petit **script** (une suite d'opcodes) rejoué un peu à chaque tour.

Toutes les routines citées ici sont nommées dans
[`disasm/block4.asm`](../disasm/block4.asm) (`ROUTINE_DOCS`/`ROUTINE_NOTES` de
[`scripts/disasm.py`](../scripts/disasm.py)).

### Vue d'ensemble : la boucle du monde (`world_tick` `$4E59`)

`world_tick` est appelée après chaque commande réussie du joueur et fait avancer
le monde en trois temps :

```
world_tick ($4E59)
  ├─ victory_check ($69E7)   condition de victoire (foule + score)
  ├─ entity_tick  ($4ED5)    VM AnimAction : joue les scripts des PNJ
  └─ evt_tick     ($4E75)    événements différés (table $2B12, cf. § événements)
```

### La table des personnages `$2B45`

17 entrées de 7 octets `[id, n, PC_lo, PC_hi, base_lo, base_hi, s6]`, terminée
par `$FF` en `$2BBC` :

- `id` = identifiant du personnage ; `$00` = **slot dormant** (3 slots :
  `$2B61 $2B76 $2B7D`), sauté par la VM.
- `PC` (`+2/+3`) = pointeur du script courant dans le bloc 2.
- `base` (`+4/+5`) = table de sauts 3 o `[clé, lo, hi]` propre à l'entité
  (cibles des `GOTO`/`RAND`/`INDIR`).
- Les **14 entités actives** : `$3E $3F $40 $43 $41 $44 $47 $48 $3D $45 $4B
  $49 $4A $4C` (PC initiaux `$295C $298E $29BC $29C7 $2A38 $2A8F $2AD0×2
  $28E1×2 $2910 $2934×3`). Décodage statique exhaustif (`/tmp/vmdec.py`, non
  promu).

### Le script d'un personnage : format d'opcode

L'opcode est l'octet pointé par le PC. On le dispatche sur son **nibble bas** :

| Opcode | Nom | Taille | Effet |
|---|---|---|---|
| `$x0/$x2` | MOVE long | 4 o (+2) | `wid=(PC)1, arg1=(PC)2, arg2=(PC)3` → `entity_move` |
| `$x1/$x3` | ACT | 3 o (+2) | `(PC)1` = index dans la table d'actions `$7143` |
| `$x4` | MOVE court | 2 o (+2) | `wid=(PC)1` ; `$FF` + bit `$10` = saut inconditionnel |
| `$x5-$xD` | INDIR | 2 o | saute via la table de base (`script_indir` `$51DA`, cible `[0]`) |
| `$xC` | GOTO clé | 2 o | `entity_goto(id, clé)` via la table de base |
| `$xE` | GOTO absolu | 3 o | `PC := (PC)1/(PC)2` |
| `$xF` | RAND | 2 o | tire une cible parmi `min(op, n)` (`script_rand` `$51CA`) |

Bits de contrôle de l'opcode :

- bit `$20` : **auto-modification** — l'opcode est effacé (`sta (ptr),y`) après
  le move, ce qui rend le personnage dormant au tour suivant.
- bit `$10` : **plan de secours** — si l'action échoue, saute de la taille de
  l'instruction (saut calculé, `script_step2`).

> `$xC` (GOTO par clé) n'apparaît **dans aucun des 17 scripts** : chemin
> runtime-only d'après le code (`entity_goto` `$5249`), corrige l'ancienne note
> « PATCH table ».

### Le tour d'une entité (`entity_tick` `$4ED5`)

`entity_tick_init` (`$5235`) prépare le tour : résout le lieu du joueur (`ploc`)
et teste la noirceur (compteur d'ambiance `L4ED4`). Puis, pour chaque entrée de
`$2B45` :

1. `id=$00` → entrelace ; `id=$FF` → fin (`entity_tick_done` `$5008`).
2. `obj=id`, résolution du lieu/fiche (`L57BB`), affichage coupé (`outen=0`).
3. Si noir et PNJ « présent », annonce le bruit `YOU HEAR A NOISE` (une fois).
4. **Préambule one-shot** : si l'entité est en cours de planification
   (`once`, test `cand_check` `$3E8E`) et que l'opcode n'a pas le bit `$40`,
   lance le moteur d'errance (`wander_start` `$3F7F` + `move_announce` `$5127`)
   au lieu de l'opcode.
5. Sinon, exécution des opcodes (dispatch du tableau ci-dessus), **au plus 6
   opcodes par tick** (`L4ED3` = garde-fou contre les boucles `GOTO self` /
   `INDIR` cycliques). Le PC est réécrit dans `(entrée)+2/+3` après chaque
   instruction.
6. Fin : `entity_tick_done` restaure le joueur (`crec=$1B1A`, `eloc=$1B2A`) et
   réautorise l'affichage.

### Déplacement et perception

- `entity_move` (`$511C`) appelle le **moteur de déplacement partagé**
  `move_core` (`$36DB`) : trouvé la sortie du lieu selon `wid`/`arg1`/`arg2`,
  vérifie ses conditions (`cond_eval`), puis déplace ou refuse.
- `move_announce` (`$5127`) traite ce que le joueur **perçoit** du déplacement :
  description de l'arrivée (`describe_room` `$417C`) ou bruit `YOU HEAR A
  NOISE` (une fois par tour), puis exécution de l'action (`perform_action`
  `$4B37`) et répliques éventuelles.
- `say_if_visible` (`$5279`) n'affiche un dialogue que si le personnage est
  **visible du joueur** (même lieu, pas en pleine annonce, drapeau `L5611`).
- `entity_goto` (`$5249`) = saut « nommé » : X = clé, A = id ; la clé est
  résolue dans la table de base de l'entité.

### Les actions autonomes : table `$7143`

L'octet opérande d'un ACT indexe la table `$7143` (38 o : sentinelle `$FF 0B`
+ **18 mots** de pointeurs, pas 15). L'adresse obtenue est posée dans
`$4C64/$4C65` puis appelée par `indirect_call` (`$4C5D`).

- Index 1–15 = actions connues (`act_v14_*`, `$68D0`–`$6EA7`), par ex. :
  `$68D0` « HELLO » ; `$68E0` PNJ oisif (tirage GREAT JOB / HURRY UP / HELLO) ;
  `$692D` « WHAT'S THIS ? » ; `$6936` « HURRY UP » ; `$6962` « WHERE'S THE
  THIEF ? » ; `$6CFA` ramasse un objet ; `$6D78` Gollum (POCKET ? / MY
  PRECIOUS) ; `$6DF9` « SOMEONE STRANGLE YOU » ; `$6E59` dragon (vol / flammes) ;
  `$6CBE` dragon « PREPARE TO DIE ».
- **Index 16–18 = 3 actions inédites** (checker PROPRE, rebuild OK) :
  `$6E8B` trolls (si `$C8`==5 : `$C5`==`$47` ? `$1615` BLIMEY COOK EM :
    `$162B` MOUTHFUL) ;
  `$6CDB` combat simulé (visible : sonde, wid=`$1B`, `$60BF` + `JMP $5FAE` ;
    routine jumelle `$6CF9` collée derrière : tracking objet `$1FC1`/`$1FB2`) ;
  `$6EA7` = `$6E8B`+28 (sonde + `L4D47` ×2, RAZ bit7 `$1F94`/`$1FA6`,
    `$214C`&~`$40`, desc `$2154`=`$1645`, dit `$16EB` — **retombe sur le slot
    mutable des records**).

Chaque action teste d'abord sa **condition de lieu** (`eloc`/`ploc`) ou son
drapeau, puis `act_probe` (`$5386`) : en mode sonde elle n'agit pas mais retient
que l'action passe (`passok`), ce qui permet de la rejouer en mode réel.

### Le moteur d'errance (placement des PNJ)

Quand un personnage doit se déplacer seul, le jeu empile ses commandes dans la
file `$4905` (curseurs `qrd`/`qwr` `$D1/$D2`), en évalue le coût et retient des
destinations candidates dans la table `$48D3` (entrées 5 o `[id, poids, état,
lo, hi]`) sous contrainte de **budget** (`mwt` `$D0`, `$0A` de base) :

- `actq_pull` (`$3E5B`) retire l'action suivante de la file et prépare ses
  tokens (`L4783`) pour le parseur.
- `wander_core` (`$3EB2`) rejoue ces commandes via `parse_cmd` pour évaluer un
  chemin et cumule leur poids (`macc` `$D3`).
- `wander_start` (`$3F7F`) / `wander_step` (`$3F8E`) sélectionnent et tentent le
  déplacement ; `wander_select` (`$4035`) pointe la commande candidate.
- `wander_rewind` (`$3FE5`) consomme le poids et `wander_remove` (`$4051`)
  retire un personnage de la liste (appelée par `code_4D47`).

### États, scripts et activation

- États `$1A62` : 61 clés (`$00-$2B`, `$3C-$4C` ; **trou `$2C-$3B`** ; triplets
  `[clé,lo,hi]` + `$FF` en `$1B19`) → blocs `$1Bxx` (plan d'octets :
  `docs/memory-map.md`) ; `L5331` (état mutable) ≠ `L530B` (record template) ;
  `L57BB` : état+0==1 → `eloc`=état+`$10` (`$3E`=`$01`, map `$03`=`$01` holder
  `$3E` ; `$41`=`$09`, `$43`=`$15`, `$44`=`$11`, `$47`/`$48`=`$05`) ; état+1 =
  porteur ? (`$03`→`$3E` = Gandalf porte la carte au boot) ; état+8 = template
  description (tokens runtime `<t00>`/`<t08>`, illisible statiquement).
- Scripts : `$3E` errance (MOVE `$1D`/`$10`/`$24`/`$13`/`$0D`/`$0E`, ACT 1/2,
  RAND→4 cibles) ; `$44` Gollum présumé (ACT 13/14, MOVE `$0E`/`$01`=NORTH/`$13`
  arg=`$10` = caverne aux torches) ; `$41` dragon présumé (ACT 7/8, eloc `$09`) ;
  `$47`/`$48` (ACT 16/17, eloc `$05`, template `EYE`) ; `$3D`/`$45` en `$28E1`
  (MOVE `$10` arg `$06` + boucle MOVE `$30`) ; `$3F`/`$43`/`$49`/`$4B` boucles
  `MOVE`+`GOTO self`.
- Dormants `$2B45` = **vrais scripts** (pas du garbage) : `$42` (`$29EE` : MOVE
  `$26`/`$10`/`$0D` arg `$08`), `$46` (`$2A77` : ACT `$6C33` + MOVE `$13` arg
  `$25`, loop), `$3C` (`$2A54` : ACT `$6E59`→`$6C8D`→MOVE `$24`, sauts calculés
  bit `$10` chaînés) ; activation = id seul (`evt_arme16` : `$2B61`:=`$42` si
  `($1DC5&8)==0` ; `evt_arme9` : `$2B76`:=`$46`, `$2B7D`:=`$3C`), PC/base
  résiduels valides (`$29EE` table[0]=self).
- Copies boot `L30F9` (4×6 o, via `boot_copy`) : `$1B1A`→`$91D0` (1366 o,
  états), `$28CC`→`$9726` (753 o, bases+scripts+tables — pas `$28E6`, la vraie
  source est `$28CC`), `$211A`→`$9A17` (1480 o, **records mutables**),
  `$00BE`→`$9FDF` (24 o, ZP) ; contiguës (`$9726`=`$91D0`+`$556`, `$9A17`=
  `$9726`+`$2F1`) = image SAVE/LOAD (`boot_copyback` = restore). Corrige le
  « `$28E6`+ » approximatif des notes précédentes.
- Exits étendue (utilisées par les MOVE) : `$26DA`+wid*8 ; wid `$00-$0A`
  directions (mot + `AD 04`), wid `$0B+` **conditionnelles** (format
  `code_4141`, flags `$40`/`$60`/`$80` → direct/variant) jusqu'à ~`$28C2` (wid
  `$30`/`$37` valides : `$285A`/`$2892`) ; wids des scripts : `$01 $06 $0B $0D
  $0E $10 $13 $1D $24 $27 $30 $37` (ex. `$1D` = `8D C4 DE 0A 00 10 00 60`, `$10`
  = `8B 87…40`).
- Ouverts : trou `$2C-$3B` (voir § records : `$2D-$33` objets sans état,
  `$34`/`$35` faction sans état/slot, `$3C` futur — état `$1B30` pré-existant,
  identité à confirmer) ; `$xC` (0 occurrence dans les 17 scripts : runtime-only
  si jamais) ; `n`/`s6` exacts ; eloc non-chambres (`$09`, `$38`/`$3A` =
  conteneurs ?) ; cohabitation scripts `$28E1` / copies boot (zone lue ET
  exécutée, ROM intacte).

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
  identifiés par messages : `$13`=GET, `$0B`=KILL, `$1A`=INVENTORY,
  `$1D`=DROP, `$17`=LOOK, `$1C`=OPEN probable ; `$0E`/`$1F`/`$20`/
  `$24`/`$27`/`$2A`/`$30` = pseudo-mouvements ou sans message
  (`/tmp/verbsc.py`) ;
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

## Carte mémoire de l'état sauvegardé

Voir `docs/memory-map.md` : workspace haut `$91D0`–`$9FF7`
(`$0E28` o, 4 copies `L30F9` contiguës), offsets internes, blocs
cassette SAVE, cycle de vie boot/SAVE/LOAD.

## Bloc 3 : illustrations vectorielles (`$7AC0`–`$91B1`, 5 874 o)

Le bloc 3 est une **banque d'images** : table à clés `$7AC0` (13 entrées
`[clé,mot]`, `$FF` en `$7AE7`, lookup `L5399` pas de 3) + 13 flux d'octets
`$00`-terminés, tuilés sans trou (`$7AE8`→`$91AF`, double `$00` en `$809E`,
`$00 $CB` final). Zéro texte ASCII ≥24 o : tout est dessin.

- Moteur (`vec_init` `$77D4`, X/Y = adresse image) : `vec_setup` (`$7990`,
  octet mode = couleurs : bas = papier (`mode & 7`), bits 4-6 = encre
  (`(mode >> 4) & 7`) ; écrits en col 0/1 comme attributs `16+papier`/`encre`)
  efface hires
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
- Décodage statique : `scripts/vec_decode.py` réplique le moteur (dispatch,
  `vec_pos`/`vec_line`/`vec_fill`/`vec_skip`, `vec_plot`/`vec_addr`) et rasterise
  les 13 images depuis `data/hobbit.bin` → `docs/vectors/vec_<clé>.svg`
  (240×128, palette Oric : papier = `mode & 7`, encre = `(mode >> 4) & 7`).

### Protocole de dessin (commandes)

Entrée : `vec_image` (`$77D4`, = `vec_init`) reçoit **X/Y = adresse de
l'image**, stockée dans `$28/$29` (ZP). Octet 0 = **mode/couleurs** →
`vec_setup` (`$7990`) : efface le hires `$A000`–`$B3FF` (aplats `$40`) puis
fixe papier (`mode & 7`, bas 3 bits) / encre (`(mode >> 4) & 7`, bits 4-6).
La boucle `L77E3` lit l'octet
courant et dispatch dans cet ordre :

| Test | Opcode | Commande | Opérandes |
|---|---|---|---|
| `beq` | `$00` | fin d'image | — |
| `cmp #$08` | `$08` | `vec_pos` (place le curseur) | `x, y` (2 o) |
| `and #$80` | bit7 | `vec_line` (segment) | opcode + 1 o |
| `and #$40` | bit6 | `vec_fill` (remplissage) | `x, y` (2 o) |
| `and #$20` | bit5 | `vec_skip` (saute) | octets jusqu'à `$FF` |
| sinon | — | avance d'1 octet (donnée) | — |

`$08` est testé **avant** les bits (sinon il tomberait dans « avance »). Les
opcodes ligne/fill/skip se recouvrent : bit7 l'emporte sur bit6, qui l'emporte
sur bit5.

- **Curseur** : `$30` = x (0–255 ; zone dessinable `$0E`–`$F1`, sinon clippé
  par `vec_testpx`/`vec_plot`), `$31` = y (0–`$7F`). `vec_addr` : `addr =
  $A002 + 40*y`, masque pixel `L7A5F` = `$20 $10 $08 $04 $02 $01` (6 px/octet).
  La base **`$A002`** (= 2 colonnes) réserve les colonnes 0/1 aux attributs
  paper/ink → **12 px de marge à gauche** de l'illustration (`screen_x = x-2`).
- **`vec_line`** réutilise l'octet opcode + 1 suivant : `$2A/$2B/$2C = op &
  $01/$02/$04` (axe/sens) ; `$2D` = longueur `(op & $78) >> 1` complétée par
  les bits 6-7 de l'octet suivant, **+1** ; `$2E = octet_suivant & $3F` =
  compteur de runs (`dec/bpl` → `$2E+1` passes). Tracé type Bresenham
  « run-length » (pas majeur `$2D`, pas mineur à chaque franchissement).
- **`vec_fill`** : remplissage par **spans** depuis `(x,y)` (balaye à gauche
  jusqu'à un pixel allumé, trace, empile `(x,y)` sur la pile `$32` pour
  remonter/descendre et récurse) — le plot pixel par pixel (`vec_plot`) est la
  cause de la lenteur (~33 M cycles/image).
- **Flux** : chaque image = `[mode, $08, x, y]` puis commandes, **terminée par
  `$00`** ; images tuilées sans trou (`$7AE8`→`$91AF`), cas notables double
  `$00` en `$809E`, final `$00 $CB`.

## Outillage

- `scripts/disasm.py` : **descente récursive** (entries `$2C00`, `$2C35`, 16
  vecteurs) + point fixe (seeds radare2 validés par `try_decode`, `MANUAL_ENTRIES`
  pour le dispatch indirect, `SEED_EXCLUDE` pour les faux positifs comme
  `fcn.00006dce` qui chevauchait un pointeur `$440D`). Le résultat de `afl` est
  mis en cache dans `disasm/.r2_afl.txt`.
- `scripts/disasm_opcodes.py` : table des 150 opcodes légaux 6502.
- `scripts/disasm_check.py` : contrôles A–H (sync linéaire avec règle `$440D`,
  cibles de branches/JSR/JMP, tables ressemblant à du code, ROM, vecteurs,
  pointeurs marqués, `ROUTINE_DOCS`). Sortie 0 = propre.
- `disasm/block4.info` : fichier d'information da65 (ranges code/données + labels).
- `disasm/block4.asm` : listing annoté — **16 980 o de code**, 99 sites
  `$440D` (118 inline `$440D`/`$5B24`), 249 routines documentées (dont le
  parser AnimTalk, la VM AnimAction — `entity_tick`, jeu d'opcodes, 18
  `act_v14_*`, moteur d'errance —, l'exécution des commandes joueur
  (`cmd_run`, `perform_action`, `describe_room`, `special_cmd`), les records
  (`room_record`/`obj_record`/`tbl_lookup`), 10 `vec_*`/`img_show`, 33 actions
  `L7014`/`L7143` et 6 handlers SAVE/LOAD) + commentaires au niveau instruction
  (dispatch de classe du parser, VM des PNJ, exécution des commandes), 0 conflit.

Régénérer et vérifier :

```
.venv/bin/python scripts/disasm.py
.venv/bin/python scripts/disasm_check.py   # viser exit 0 (RÉSULTAT: PROPRE)
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
