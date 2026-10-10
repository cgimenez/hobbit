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

Entrée `JMP $047C` :

- `$047C` `SEI` puis `LDA #$7F / STA $030E` : désactive la ROM pour accéder aux vecteurs.
- `$0482`–`$0495` : teste la ROM (`$FC78`, voir plus bas) et **relocalise la table de vecteurs** depuis `$0468` vers `$0403`.
- `$04A4`–`$04AD` : copie le message `"Please wait while THE HOBBIT loads"` (`$04CC`, 34 octets) vers `$BC4B`.
- `$04AF`–`$04BA` : boucle de chargement — appelle 3× la routine cassette `$0417`, avec retry (compteur `$40`).
- `$04BC` `JMP ($0032)` : saute vers le programme chargé.
- `$04BF`–`$04CA` : en cas d'échec, copie `"TAPE ERROR"` (`$04EF`) vers `$BD19` puis boucle infinie.

La routine de lecture `$0417` appelle les vecteurs : `JSR $0411` (setup) → `JSR $0405` (sync) → `JSR $0408` (read byte), attend le `$24`, lit l'en-tête de 9 octets (`STA $0035,Y`), puis les données vers `($37)` avec **checksum EOR** cumulé en `$3B`.

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
