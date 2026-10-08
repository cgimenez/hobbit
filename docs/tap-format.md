# Oric Tape Format (fichier .tap)

> Par Chloé Avrillon (aka Ladywasky, anciennement waskol)

Les valeurs multi-octets sont en convention **big-endian** : `Valeur/Adresse = octet1*256 + octet2`.

Les tableaux (arrays) sont indexés à partir de zéro en BASIC.

## 1. Synchronisation

| Bloc | Nb d'octets | Valeurs possibles | Commentaire |
|------|-------------|-------------------|-------------|
| Synchronisation | (N+1) octets — N ≥ 4. Typiquement : Fast = 16 octets, Slow = 8 octets | `$16` | octets de synchronisation |
| | 1 | `$24` | fin de synchronisation |

## 2. Bloc typique — BASIC ou bloc mémoire (data ou code machine)

| Bloc | Nb d'octets | Valeurs possibles | Commentaire |
|------|-------------|-------------------|-------------|
| Header | 9 octets | 2 : *varies* | octets réservés (inutilisés) |
| | | 1 : `$00` / `$80` | `$00` = BASIC, `$80` = code machine ou bloc mémoire |
| | | 1 : `$00` / autre (`$C7`) | `$00` = Autorun OFF, `$C7` = Autorun ON |
| | | 1 : EndAddress1 (high) | localisations mémoire |
| | | 1 : EndAddress2 (low) | |
| | | 1 : StartAddress1 (high) | `Adresse = octet1*256 + octet2` |
| | | 1 : StartAddress2 (low) | |
| | | | `SizeOfData = EndAddr - StartAddr + 1` |
| | | 1 : *varies* | inutilisé |
| File name | 15 octets max + `$0` | 15 max : ASCII | nom |
| | | 1 : `$00` | fin du nom |
| File data | SizeOfData | *varies* | succession d'octets |

> **Note :** pas d'octet de fin dans les fichiers Oric.

## 3. Tableau d'entiers (STORE/RECALL)

*(précédé d'une synchronisation identique)*

| Bloc | Nb d'octets | Valeurs possibles | Commentaire |
|------|-------------|-------------------|-------------|
| Header | | 1 : `$80` | flag integer/real (*utilisé seulement par la ROM v1.1*) |
| | | 1 : `$00` / `$40` | `$00` = flag string, `$40` = array |
| | | 1 : `$00` / autre (`$C7`) | `$00` = Autorun OFF, `$C7` = Autorun ON |
| | | 1 : StartAddress1 (high) | adresse du tableau au moment du save |
| | | 1 : StartAddress2 (low) | inutilisé. `$FFFF` pour bi-dim |
| | | 1 : SizeOfData1 (high) | `SizeOfArray = octet1*256 + octet2` |
| | | 1 : SizeOfData2 (low) | `SizeofData = SizeOfArray (*)` |
| | | 1 : `$FF` | inutilisé |
| File name | 15 octets max + `$0` | 15 max ASCII / `$00` | nom / fin du nom |
| File data | (SizeOfData div 2) « integers » | *varies* | succession d'entiers (2 octets) |

> **(\*)** Pas d'indicateur de fin. Les valeurs sont stockées séquentiellement sans dimension ni nom de variable.
> Ce n'est pas exact : il semble y avoir un bug dans la ROM Oric, la taille du tableau est fausse. En réalité `SizeofData = SizeOfArray - offset`.
> L'offset vaut typiquement **6** pour un tableau mono-dimensionnel, **8** pour un tableau bi-dimensionnel (et ce n'est pas toujours vrai).
> Soit la longueur de données fournie est fausse, soit il manque les descripteurs du tableau (dimensions par exemple).

## 4. Tableau de réels (STORE/RECALL)

*(précédé d'une synchronisation identique)*

| Bloc | Nb d'octets | Valeurs possibles | Commentaire |
|------|-------------|-------------------|-------------|
| Header | | 1 : `$00` | flag integer/real (*ROM v1.1 seulement*) |
| | | 1 : `$00` / `$40` | `$00` = flag string, `$40` = array |
| | | 1 : `$00` / autre (`$C7`) | `$00` = Autorun OFF, `$C7` = Autorun ON |
| | | 1 : StartAddress1 (high) | adresse du tableau au moment du save |
| | | 1 : StartAddress2 (low) | inutilisé. `$FFFF` pour bi-dim |
| | | 1 : SizeOfData1 (high) | `SizeOfArray = octet1*256 + octet2` |
| | | 1 : SizeOfData2 (low) | `SizeofData = SizeOfArray (*)` |
| | | 1 : `$FF` | inutilisé |
| File name | 15 octets max + `$0` | 15 max ASCII / `$00` | nom / fin du nom |
| File data | SizeOfData × 5 octets | *varies* | succession de réels (5 octets) |

> **Note :** pas d'indicateur de fin. Les valeurs sont stockées séquentiellement sans dimension ni nom de variable.
> **(\*)** identique au tableau d'entiers.

## 5. Tableau de chaînes (STORE/RECALL)

*(précédé d'une synchronisation identique)*

| Bloc | Nb d'octets | Valeurs possibles | Commentaire |
|------|-------------|-------------------|-------------|
| Header | | 1 : `$00` | flag integer/real (*ROM v1.1 seulement*) |
| | | 1 : `$FF` / `$40` | `$FF` = flag string, `$40` = array |
| | | 1 : `$00` / autre (`$C7`) | `$00` = Autorun OFF, `$C7` = Autorun ON |
| | | 1 : `$FF` | inutilisé |
| | | 1 : `$FF` | |
| | | 1 : SizeOfData1 (high) | `Valeur = octet1*256 + octet2` |
| | | 1 : SizeOfData2 (low) | `SizeofData = SizeOfArray (*)` |
| | | 1 : `$FF` | inutilisé |
| File name | 15 octets max + `$0` | 15 max ASCII / `$00` | nom / fin du nom |
| File data | SizeOfData + strings | *varies* | succession d'octets |
| | n = SizeOfData/3 (n descripteurs de 1 string) | 1 : *varies* | longueur de la chaîne |
| | | 2 : *varies* | adresse de la chaîne (inutile !) |
| | Strings : len(0)+len(1)+…+len(n-1) | *varies* | N chaînes concaténées |

> **Note :** pas d'indicateur de fin. Les valeurs de chaînes sont stockées séquentiellement sans dimension, ni nom de variable, ni séparateurs.
> **(\*)** identique au tableau d'entiers.
