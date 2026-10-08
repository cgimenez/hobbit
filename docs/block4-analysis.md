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

- `$0B`/`$0C` : autorisation de sortie (putchar) ; `$0D` : flag d'affichage.
- `$32`/`$33` : adresse de chargement renvoyée par le loader ; `$37`/`$38` : pointeur d'écriture.
- `$56`, `$57`, `$5F`, `$65`, `$7E`, `$88`/`$89`, `$8A`/`$8B`, `$C4` : état du jeu.
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

## Convention d'affichage `JSR $440D`

Le motif dominant du bloc 4 : **`JSR $440D` suivi de 2 octets inline** = adresse
du message à afficher ; le code reprend à JSR+5 (queue `JSR $4737` / `JMP ($6A)`,
helper `$44BE` qui incrémente le pointeur). 79 sites recensés, chacun avec son
mot pointeur marqué `.word` (`msg_XXXX`) et un aperçu du texte en commentaire.
Sans cette règle, chaque site décalerait tout le désassemblage aval.

- 6 sites ont un pointeur **nul** (`$3CB4`, `$4DF9`, `$4E2D`, `$52C3`, `$5BB5`,
  `$631A` → `TODO pointeur nul`) : adresse du message résolue à l'exécution.
- Quelques pointeurs visent le **bloc 2** (`$1370`, `$165A`, …) : messages ou
  tables hors bloc 4, affichés `(hors image)` / bruts dans le listing.
- Pas d'appels ROM directs dans le bloc 4 : tout passe par les vecteurs du
  bloc 1 (`$0405`–`$0417`), patchés selon ROM 1.0/1.1.

## Outillage

- `scripts/disasm.py` : **descente récursive** (entries `$2C00`, `$2C35`, 16
  vecteurs) + point fixe (seeds radare2 validés par `try_decode`, `MANUAL_ENTRIES`
  pour le dispatch indirect, `SEED_EXCLUDE` pour les faux positifs comme
  `fcn.00006dce` qui chevauchait un pointeur `$440D`). Le résultat de `afl` est
  mis en cache dans `disasm/.r2_afl.txt`.
- `scripts/opcodes6502.py` : table des 150 opcodes légaux 6502.
- `scripts/check_disasm.py` : contrôles A–G (sync linéaire avec règle `$440D`,
  cibles de branches/JSR/JMP, tables ressemblant à du code, ROM, vecteurs,
  pointeurs marqués). Sortie 0 = propre.
- `disasm/hobbit.info` : fichier d'information da65 (ranges code/données + labels).
- `disasm/block4.asm` : listing annoté — **15 692 o de code (78 %)**, 79 sites
  `$440D`, 0 conflit.

Régénérer et vérifier :

```
.venv/bin/python scripts/disasm.py
.venv/bin/python scripts/check_disasm.py   # viser exit 0 (RÉSULTAT: PROPRE)
```

## Limites

- Le découpage **code/données est validé statiquement** (checker exit 0), mais
  6 pointeurs nuls et les zones atteintes par dispatch indirect reposent sur des
  `MANUAL_ENTRIES` arbitrées à la main (trampolines `JSR`+`JMP`, routines
  `LDA $C5`/`LDA $1F76`+`RTS`, etc.).
- Auto-modification : `STA $6A5C` patch un octet relu par `LDA $6A5C` (donnée
  conservée en table, code adjacent marqué à partir de `$6A5E`).
- Les rôles des vecteurs `vec_init`, `vec_06`, `vec_07` restent à confirmer.
- Prochaines étapes : nommer les variables zéro-page, explorer le bloc 2
  (table `$0500` + textes, dont les messages pointés depuis le bloc 4) et le
  bloc 3.
