# Protocole host ↔ sim65 (source de vérité unique)

Contrat bas niveau **identique** natif et WASM. Seuls les backends d'E/S
diffèrent (fd POSIX vs buffers mémoire). Tout le reste (traps, arguments,
marqueurs, décodage) est partagé dans `host/core.c`.

## 1. Traps de paravirtualisation

Le 6502 appelle `JSR $FFF6` (read) / `JSR $FFF7` (write) / `JSR $FFF9` (exit).
Le host intercepte (`ParaVirtHooks`), exécute, simule le `RTS`
(`PC = popped + 1`). Base : `PARAVIRT_BASE = $FFF1`
(`tools/cc65/src/sim65/paravirt.h:48`).

Table (`paravirt.c:369`) : `FFF1 lseek · FFF2 remove · FFF3 map-errno ·
FFF4 open · FFF5 close · FFF6 read · FFF7 write · FFF8 args · FFF9 exit`.
Le jeu n'use que `FFF6/FFF7/FFF9`.

## 2. Convention d'appel

Pile logicielle en page zéro, pointeur = mot à **`SPAddr = $02`**
(`shim.s:47`, en-tête `.sim` octet 7, `ParaVirtInit(0, 0x02)`).

```
$02/$03 ──> [ Buf lo, Buf hi ]   <- PopParam(2)
            [ FD  lo, FD  hi  ]   <- PopParam(2)
registres : A = Count_lo, X = Count_hi   (AX = A | X<<8)
```

- `PVRead` : `Buf=PopParam(2)`, `FD=PopParam(2)` ; retour = octets lus en A/X.
- `PVWrite` : idem ; retour = octets écrits en A/X.
- `PVExit` : ignore tout, arrête (`SimExit` natif / `Halt` WASM).

## 3. Canal d'entrée (host → 6502, fd 0)

Octets clavier Oric bruts, 1 par appel (`Count=1`). Protocole 2 temps
(`shim.s:69-132`) : `KEYBUF|$80` (touche présente), puis 0 (release).
`$0D` = ENTREE. File vide → 0 octet → `RESULT=0` (pas de touche).

## 4. Canal de sortie (6502 → host, fd 1)

Flux d'octets à **marqueurs ASCII** de longueur fixe + charges binaires.
Deux saveurs de shim (choix au link, `ca65 -D SOLVER`) :

### 4.1 Saveur SOLVER (WASM + harnais solveur)

| Marqueur | Taille | Charge | Émis quand |
|---|---|---|---|
| `@@A` | 3 + **1** | octet `c` rendu | chaque caractère affiché |
| `@@EOL\n` | 6 | — | scroll mode texte |
| `@@EOLR\n` | 7 | — | scroll mode RAW (écho commande) |
| `@@P\n` | 4 | — | caractère affiché = `>` (**fin de tour**) |
| `@@K` | 3 + **1** | octet clavier consommé | chaque lecture stdin |
| `@@SNAP\n` | 7 + … | `NLEN(1)`+`NOM(NLEN)`+`IDX(1)`+`LEN(2 LE)`+payload | SAVE (4 blocs) |

Décodage `@@A c` (partagé) : `$0D/$0A`→`\n`, `$08`→`"\b \b"`,
`$2B` (`+`, curseur)→ignoré, `$20-$7E`→littéral, `>$7F`→`?`,
autres contrôles→ignorés.

`@@EOLR\n` : si suivi (après curseurs `@@A+`) d'un `@@EOL\n`, supprimer
le saut (RETURN + réponse = 1 ligne), sinon émettre `\n`.

### 4.2 Saveur classic (outils d'analyse natifs)

| Marqueur | Taille | Charge |
|---|---|---|
| `@@FRAME text\n` | 13 | 1120 o (`$BB80-$BFDF`) |
| `@@FRAME hires\n` | 14 | 8192 o (`$A000-$BFFF`) |
| `@@MEM XXXX YYYY\n` | 16 | payload `len` o (6 régions) |

Le parseur du core (`host/core.c`) décode les **deux** saveurs (superset).

### 4.3 Trace mémoire (`@@M` / `@@D`, opt-in)

Le host peut exposer l'état RAM par tour (`hob_mem_trace(1)`, off par
défaut — le texte jeu et `host_diff.py` restent inchangés). Canal dédié
(`--memfd`, jamais injecté dans `io_text`) :

| Marqueur | Charge | Émis quand |
|---|---|---|
| `@@M\n` | 0x10000 o (`Mem[]` brut) | une fois après `hob_boot()` (base d'induction) |
| `@@D\n` | `turn(2 LE)` + `rc(1)` + `nlen(2 LE)` + `nlen`×`[addr(2 LE), old(1), new(1)]` | à chaque retour de `hob_run()` tracé (rc 0/1/2) |

`old`+`new` inclus → auto-suffisant. Enregistrements triés par adresse
croissante. `scripts/mem_diff.py` compare natif↔WASM en lockstep
(`--serve` des deux côtés) et stoppe au premier octet divergent
(explication via `memmap_defs.annotate`).

## 5. SAVE/LOAD (`harness/snap.s`)

Émission : `@@SNAP\n` + `NLEN(1)` + `NOM` + `IDX(1)` + `LEN(2 LE)` + payload,
4 blocs (idx 0..3 = `$00BE/$18`, `$1B1A/$556`, `$28CC/$2F1`, `$211A/$5C8`).
Le host reconstruit le blob `"SNAP"+3623 o`. Restauration : blob placé
en `$E800` (patché dans le `.sim` / slot WASM), `snap_load` vérifie
le magique et copie (`snap.s:183-264`).

Format `.sim` : en-tête 12 o (`"sim65"`, ver 2, CPU 0, SPAddr `$02`,
load `$0400`, reset `$2C00`) + image. Reset : `Mem[$FFFC]=$2C00`,
`Reset()` → `PC=$2C00`. RAM non écrite = `$FF`.

## 6. Politique de tour unique (canonique)

Un tour = **une ligne d'entrée**, consommée exactement une fois ; le host
s'arrête au **premier `@@P`** (prompt) avec file vide. Les lignes vides
sont des tours légitimes (CR nu = WAIT : le monde avance d'un
`world_tick`) : la solution autoplay inclut celles du harness pour
reproduire la phase (butler/porte rouge).

**Piège prouvé (ne pas faire)** : attendre un « silence » prolongé après
le prompt déclenche l'auto-WAIT authentique du jeu (une inactivité
suffisante fait jouer `WAIT` tout seul, `play.sh`) : tour fantôme qui
décale la phase. Toute attente au-delà du premier prompt est interdite.
Le pacing appartient au flux de lignes, jamais à l'arrêt du run.

## 7. Frontière d'environnement (`host/platform.h`)

Seules fonctions spécifiques à l'exécution (noms imposés `platform_*`) :

| Fonction | natif (`platform_native.c`) | WASM (`platform_wasm.c`) |
|---|---|---|
| `platform_input_*` | `read(0, …)` | anneau rempli par `hob_key()` |
| `platform_output(b, n)` | `write(1, …)` | `memcpy` vers buffer texte |
| `platform_fatal(code)` | `exit`/`SimExit` | `Halt=1` |
| `platform_image_*` | `fopen`/`fread` | slots JS |

Tout le reste (traps, parseur, tour, boot, SAVE, state) = `host/core.c`,
partagé, sans POSIX ni emscripten.
