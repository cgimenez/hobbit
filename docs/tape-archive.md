# Analyse de `data/hobbit-1982.tap`

Fichier de **36 212 octets**, **4 blocs** TAP, tous du type **code machine** (`$80`) avec **autorun** (`byte3 ≠ $00`). Le parse consomme exactement tout le fichier.

| # | Offset | Sync | Type | Auto | Adresse | Taille | Nom |
|---|-------:|-----:|------|------|---------|-------:|-----|
| 1 | 0 | `16 16 16 24` | `$80` | `$C7` | `$0400`–`$0500` | 257 | `THE HOBBIT` |
| 2 | 281 | `16 16 16 24` | `$80` | `$01` | `$0500`–`$2BBD` | 9918 | *(vide)* |
| 3 | 10213 | `16 16 16 24` | `$80` | `$01` | `$7AC0`–`$91B1` | 5874 | *(vide)* |
| 4 | 16101 | `16 16 16 24` | `$80` | `$01` | `$2C00`–`$7A80` | 20097 | *(vide)* |

## Points notables sur le format

- La synchronisation réelle est `16 16 16 24` (3×`$16` + `$24`), pas 16 octets comme les cas « Fast » du [format TAP](tape-format.md).
- Les en-têtes confirment le schéma : `reserved(2) | type | autorun | endAddr(2) | startAddr(2) | unused`.
- Les blocs 2–4 ont un **nom vide** (`$00`), typique des blocs de code machine Oric.
- La taille des blocs suit `size = EndAddr - StartAddr + 1` ; la somme des `size` + syncs/en-têtes/noms = 36 212 (fichier entièrement consommé).

## Interprétation du programme

- **Bloc 1** (`$0400`) = bootstrap d'autorun : `JMP $047C` → `SEI`, relocalise des vecteurs en `$0402..`, appelle la ROM. Contient `"Please wait while THE HOBBIT loads"` et `"TAPE ERROR"`.
- **Bloc 2** (`$0500`–`$2BBD`) = moteur de jeu + textes (VIOLENT, VALIANTLY, KILLED, DWARVES, HOBBITS, …).
- **Bloc 4** (`$2C00`–`$7A80`, le plus gros) = données/graphismes + routines cassette (`"PREPARE TAPE FOR GAME SAVE"`, `"REWIND TAPE FOR VERIFICATION"`, `"PRESS ANY KEY WHEN READY"`). Il conserve aussi un **artefact de développement** (`$477C`–`$49B3`) : dans un tampon de travail non effacé subsiste un fragment du fichier de commande d'assemblage, avec directives `.PRINTX` / `INCLUDE` et les **modules source** `SUBS`, `DATA`, `SUBRONE`, `SUBRTWO`, `GENER`, `GENER2`, `ACTION`, le binaire final `ADVORIC` (`:=D:ADVORIC`), et les messages de l'outil `?Command error` / `?File not found` / `?Can't enter file`. Détails : [`block4-analysis.md`](block4-analysis.md).
- **Bloc 3** (`$7AC0`–`$91B1`) = code/overlay complémentaire.

C'est donc une conversion cassette du jeu **The Hobbit (Oric, 1982)**, en pur 6502, chargé puis exécuté via autorun depuis `$0400`.

## Détail du bloc 1 (bootstrap, `$0400`–`$0500`)

> Listing désassemblé : [`disasm/block1.asm`](../disasm/block1.asm) (généré par
> [`scripts/disasm.py`](../scripts/disasm.py) `--block block1` : descente
> récursive + da65). Découpage vérifié par
> [`scripts/disasm_check.py`](../scripts/disasm_check.py) `--block block1` :
> **RÉSULTAT PROPRE** ; round-trip ca65+ld65 **byte-identique** sur
> `$0400`–`$04FF` via [`scripts/disasm_rebuild.py`](../scripts/disasm_rebuild.py).

Le **tape** déclare le bloc 1 sur `$0400`–`$0500` (257 o), mais son dernier
octet `$0500` est **écrasé par le bloc 2** (chargé ensuite) : la mémoire
vivante du bloc 1 s'arrête donc à `$04FF`, plage couverte par le listing.

Entrée `JMP $047C` (`b1_entry`) :

- `$047C` `b1_start` : `SEI` puis `LDA #$7F / STA $030E` (désactive la ROM
  pour accéder aux vecteurs).
- `$0482`–`$0495` : teste la ROM (`$FC78`, voir plus bas) et **relocalise la
  table de vecteurs** depuis `$0468` vers `$0403`.
- `$04A4`–`$04AD` : copie le message `"Please wait while THE HOBBIT loads"`
  (`$04CC`, 34 octets) vers `$BC4B`.
- `$04AF`–`$04BA` : boucle de chargement — appelle 3× la routine cassette
  `$0417` (`b1_load`), avec retry (compteur `$40`).
- `$04BC` `JMP ($0032)` : saute vers le programme chargé.
- `$04BF`–`$04CA` : en cas d'échec, copie `"TAPE ERROR"` (`$04EF`) vers
  `$BD19`, puis `BMI $04CA` (boucle infinie, terminateur de descente).

La routine de lecture `$0417` (`b1_load`) appelle les vecteurs : `JSR $0411`
(setup) → `JSR $0405` (sync) → `JSR $0408` (read byte), attend le `$24`, lit
l'en-tête de 9 octets (`STA $0035,Y`), puis les données vers `($37)` avec
**checksum EOR** cumulé en `$3B`.

Plages code/données (fichier `disasm/block1.info`) :

| Plage | Type | Contenu |
|---|---|---|
| `$0400`–`$0402` | CODE | `b1_entry` (`JMP $047C`) |
| `$0403`–`$0404` | BYTE | pointeur police `$FC70` |
| `$0405`–`$0467` | CODE | vecteurs ROM 1.0 `$0405`–`$0416` + `b1_load $0417` |
| `$0468`–`$047B` | BYTE | blob de patch ROM 1.1 (20 o) |
| `$047C`–`$04CB` | CODE | `b1_start` |
| `$04CC`–`$04F8` | TEXT | `"Please wait while THE HOBBIT loads"` + `$0C` + `"TAPE ERROR"` |
| `$04F9`–`$04FF` | BYTE | queue non référencée (fin de bloc) |

Vecteurs nommés : `b1_vec_sync $0405` · `b1_vec_read $0408` ·
`b1_vec_leader $040B` · `b1_vec_write $040E` · `b1_vec_setup $0411` ·
`b1_vec_reset $0414`.

## Détail du bloc 2 (données, `$0500`–`$2BBD`)

> Listing : [`disasm/block2.asm`](../disasm/block2.asm) (généré par
> `scripts/disasm.py --block block2`). Round-trip ca65+ld65 **byte-identique**
> (9918 o) via `scripts/disasm_rebuild.py --block block2` ; checker
> `scripts/disasm_check.py --block block2` : **RÉSULTAT PROPRE** (règle D
> désactivée : bloc de données, sans code).

Bloc **100 % données** (aucun code 6502) : banque de mots + messages, tables
d'état, records de lieux/objets et « cerveau » des PNJ (scripts VM
AnimAction). Formats élucidés dans [`block4-analysis.md`](block4-analysis.md)
et [`memory-map.md`](memory-map.md).

Partition (fichier `disasm/block2.info`) :

| Plage | Type | Contenu |
|---|---|---|
| `$0500`–`$053F` | WORD | index 26 lettres → 1er mot du dictionnaire |
| `$0540`–`$1116` | BYTE | dictionnaire packé 5-bit (~600 mots triés) |
| `$1117`–`$1156` | WORD | 32 mots courants (`$60`–`$7F`) |
| `$1157`–`$1A61` | BYTE | catalogue de messages (171 msgs + 29 desc. lieux `$18AA`) |
| `$1A62`–`$1B19` | BYTE | clés d'état (61 triplets `[clé,lo,hi]` + `$FF`) |
| `$1B1A`–`$206F` | BYTE | 61 blocs d'état (personnages, objets, lieux) |
| `$2070`–`$210F` | WORD | table des records (80 mots `id`→record, `$2F` nul) |
| `$2110`–`$2119` | WORD | 5 gabarits de description (pointeurs bloc 3) |
| `$211A`–`$26E1` | BYTE | 79 records lieux/objets/créatures (cond. + desc + sorties) |
| `$26E2`–`$2731` | BYTE | noms des directions (10 × 8 o : `NORTH`…`DOWN`) |
| `$2732`–`$28CB` | BYTE | sorties étendues conditionnelles |
| `$28CC`–`$2BBD` | BYTE | tables INDIR + scripts VM + events différées + entités |

Structures nommées (labels) : `dict_index`, `dict`, `common_words`,
`messages`, `loc_desc`, `state_keys`, `states`, `rec_table`, `rec_templates`,
`records`, `dir_names`, `exits_ext`, `indir0`–`indir12`, `script_gandalf`,
`script_thorin`, `script_elf`, `script_warg`, `script_butler`,
`script_elrond`, `script_dragon`, `script_bard`, `script_gollum`,
`script_trolls`, `script_goblins*`, `events`, `entities`.

## Patch de vecteurs selon la ROM

`$0482  LDA $FC78` / `$0485  BNE $0497` :

- `$FC78 ≠ 0` → **pas de patch** : table par défaut (assemblée pour la ROM **1.0 / Oric-1**).
- `$FC78 = 0` → **patch** : `JSR $F73C` devient `JSR $F77C`, et 20 octets de `$0468` sont copiés vers `$0403` (table **1.1 / Atmos**).

`$FC78` sert de détecteur de ROM : valant `$00` dans la ROM Atmos v1.1 (début du jeu de caractères `CHARSET`, l'espace), non nul en Oric-1 v1.0.

Blob de patch en `$0468` : `78 FC 4C 35 E7 4C C9 E6 4C 5A E7 4C 5E E6 4C 6A E7 4C AA F9`.

| Vecteur (JMP cible) | Rôle (routine ROM) | ROM 1.0 (défaut) | ROM 1.1 (patch) |
|---|---|---|---|
| `$0405` | `SYNCTAPE` — synchronisation | `$E696` | `$E735` |
| `$0408` | `READBYTE` — lire un octet | `$E630` | `$E6C9` |
| `$040B` | `WRITELEADER` — écrire le leader | `$E6BA` | `$E75A` |
| `$040E` | `PUTBYTE` — écrire un octet | `$E5C6` | `$E65E` |
| `$0411` | `SETUPTAPE` — init 6522 | `$E6CA` | `$E76A` |
| `$0414` | reset statut cassette / timers | `$F960` | `$F9AA` |
| `JSR $0499` (opérande) | `CHAR2SCR` — afficher le caractère X | `$F73C` | `$F77C` |

Identification vérifiée avec le fichier de symboles ROM 1.0 (`basic10.pch` : `getsync=$E696`, `readbyte=$E630`, `putbyte=$E5C6`, `writeleader=$E6BA`) et le désassemblage de la ROM Atmos v1.1 (`SYNCTAPE=$E735`, `READBYTE=$E6C9`, `WRITELEADER=$E75A`, `PUTBYTE=$E65E`, `SETUPTAPE=$E76A`, `CHAR2SCR=$F77C`).

## Fichiers de données et provenance

### ROM

| Fichier | Taille | Machine | Source |
|---|---:|---|---|
| `data/basic10.rom` | 16 384 | Oric-1 ROM BASIC 1.0 | `Abdess/retrobios` → `bios/Oric/Oric/basic10.rom` |
| `data/basic11b.rom` | 16 384 | Atmos ROM BASIC 1.1b | `Abdess/retrobios` → `bios/Oric/Oric/basic11b.rom` |

Base : `https://raw.githubusercontent.com/Abdess/retrobios/main/bios/Oric/Oric/`

Empreintes SHA-256 :

```
83d341dab126092f7a6d56f6a92bca0643ff3aa6529d896085004f958c9be2ff  basic10.rom
ed28568574716eef5d7c0fde2568d7a47a6e4b1fbca81daff3be05e45723466d  basic11b.rom
```

Contrôles croisés : `$FC78` vaut `$08` en 1.0 et `$00` en 1.1 (détecteur de ROM) ; jetons BASIC `INVERSE`/`NORMAL` (1.0) vs `STORE`/`RECALL` (1.1).

### Archive et extraction

```
c40223684de6966cbe2079b95b1a3f25d161af19d3288f8b83a174837b781736  hobbit-1982.tap
2654c695d6ebfbbd982387e53b7f4463c2cbc205eb73d2ad00a2b96e0d4cbd75  hobbit.bin
```

`hobbit.bin` est produit par `scripts/tape_extract.py` (image mémoire `$0400`–`$91B1`).
