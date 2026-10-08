# Bloc 4 — The Hobbit (Oric, 1982)

Le **bloc 4** occupe `$2C00`–`$7A80` (20 097 octets) et contient le **programme
principal**. Le loader (bloc 1) lit successivement les blocs 2, 3 puis 4 et saute
à l'adresse de chargement du **dernier lu** (`$2C00`), c'est-à-dire l'autorun.

> Listing désassemblé : [`disasm/block4.asm`](../disasm/block4.asm) (généré par
> [`scripts/disasm.py`](../scripts/disasm.py), radare2 + da65).

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

- `$0B`/`$0C` : autorisation de sortie (putchar) ; `$0D` : flag d'affichage.
- `$32`/`$33` : adresse de chargement renvoyée par le loader ; `$37`/`$38` : pointeur d'écriture.
- `$56`, `$57`, `$5F`, `$65`, `$7E`, `$88`/`$89`, `$8A`/`$8B`, `$C4` : état du jeu.
- `$024D` : mode cassette (fast/slow) ; `$0300`–`$030F` : VIA.

## Outillage

- `scripts/disasm.py` : analyse radare2 (`aaaa`) + génération du listing da65.
  Le résultat de `afl` est mis en cache dans `disasm/.r2_afl.txt`.
- `disasm/hobbit.info` : fichier d'information da65 (ranges code/données + labels).
- `disasm/block4.asm` : listing annoté.

Régénérer :

```
.venv/bin/python scripts/disasm.py
```

## Limites

- Le découpage **code/données est heuristique** (~80 % du bloc 4 classé « code »).
  radare2 rate certaines routines et en détecte dans les données ; quelques zones
  sont donc encore en `.byte` ou inversement.
- Les rôles des vecteurs `vec_init`, `vec_06`, `vec_07` restent à confirmer.
- Prochaines étapes : affiner les frontières, nommer les variables zéro-page,
  explorer le bloc 2 (table `$0500` + textes) et le bloc 3.
