# Carte mémoire de l'état sauvegardé — The Hobbit (Oric, 1982)

Tout l'état mutable du jeu tient dans une image contiguë du workspace
haut, **`$91D0`–`$9FF7` (`$0E28` o)**, recopiée depuis le bas au boot
(`boot_copy`, table `L30F9`), réécrite en bas au LOAD (`boot_copyback`),
et écrite sur cassette en 4 blocs par SAVE (`cmd_save` `$3DD9`).
Lire une save = lire le monde : personnages, objets, joueur.

## Les 4 copies (`L30F9`, 4×6 o `[len_lo,len_hi,src_lo,src_hi,dst_lo,dst_hi]`)

| # | Source (bas) | Dest (haut) | Taille | Contenu |
|---|--------------|-------------|-------:|---------|
| 1 | `$1B1A` | `$91D0` | `$0556` (1366) | Blocs d'état (60 clés `$1A62` → états) |
| 2 | `$28CC` | `$9726` | `$02F1` (753) | Bases INDIR, scripts `$28E1`–`$2B11`, events `$2B12`, entités `$2B45` |
| 3 | `$211A` | `$9A17` | `$05C8` (1480) | Records (79, `$2F` nul) |
| 4 | `$00BE` | `$9FDF` | `$0018` (24) | Zéro-page `$BE`–`$D5` |

Contiguïté vérifiée : `$9726`=`$91D0`+`$556`, `$9A17`=`$9726`+`$2F1`,
`$9FDF`=`$9A17`+`$5C8`, fin `$9FF7`=`$9FDF`+`$18`.

## Détail par plage

### 1. États (`$91D0`, 1366 o) — personnages, objets placés, joueur ?

- Source : table `$1A62` (60 clés `$00`-`$2B` + `$3C`-`$4B`, trou
  `$2C`-`$3B`) → blocs `$1Bxx` ; offset workspace : `$91D0`+(état−`$1B1A`).
- Format bloc : `+0`==1 → localisé, eloc=`+$10` ; `+1` = porteur
  (ex. carte `$03`→`$3E` au boot) ; `+8` = template de description
  (tokens runtime) / cond d'appartenance ; voir `docs/block4-analysis.md`
  (§ scripts PNJ, § records).
- Elocs initiaux (image) : `$3E`=`$01`, `$41`=`$09`, `$43`=`$15`,
  `$44`=`$11`, `$47`/`$48`=`$05`, `$03`=`$01` ; `$09`, `$38`, `$3A`,
  identité `$3C` : à confirmer en jeu (harnais).

### 2. Scripts et tables (`$9726`, 753 o) — qui fait quoi, et quand

- Entités `$2B45` → workspace `$999F` (`$2B45`+`$279`) : 17 entrées
  7 o `[id,n,PC_lo,PC_hi,base_lo,base_hi,s6]`, `$FF` fin ; id `$00` =
  dormant (3 slots : futurs `$42`/`$46`/`$3C`, activés par events
  `e16`/`e9` par id seul).
- Events `$2B12` → workspace `$976C` (`$2B12`+`$46`) : 10 entrées
  5 o `[id,cpt,actA,cond,actB]`, `$FF` fin ; `cpt` décrémente par tick.
- Bases INDIR (tables 3 o `[clé,lo,hi]`) + scripts `$28E1`–`$2B11`
  (opcodes nibble bas : MOVE/ACT/GOTO/PATCH/RAND/INDIR, budget
  6 ops/tick) ; table d'actions `L7143` = 18 mots (15 + 3 inédites).
- Détails : `docs/block4-analysis.md` (§ scripts PNJ).

### 3. Records (`$9A17`, 1480 o) — lieux, objets, créatures (templates)

- Accès bas : `L530B` (`*($2070+id*2)`, id<$50, `$2F` nul) ; offset
  workspace : `$9A17`+(rec−`$211A`).
- Format : `[b0, b1, 3 paires (mot, masque-nibble), desc_lo, desc_hi,
  …]` ; `b0`&`$0E` = template LOOK (`L4DC6`→`$2110`), bit7 ? ;
  `b1` bit6 = inclusion recherche (`L363E`), `$FF` défaut, `$A0`/`$B0`
  (lieux `$01`/`$2B`) ? ; cond = signature d'appartenance
  (matcher `code_433A`, groupes de factions).
- Détails : `docs/block4-analysis.md` (§ records).

### 4. Zéro-page (`$9FDF`, 24 o) — joueur et contexte immédiat

- `$BE` `exploc`, `$C5` `obj`, `$C6`-`$C7` `crec`, `$C8` **`ploc`
  (lieu du joueur)**, `$C9` `eloc`, `$CE` `once` (noms `ZP_NAMES`).
- Non détaillés : `$BF`, `$C0`-`$C4`, `$CA`-`$CD`, `$CF`-`$D5`.

## Blocs cassette SAVE (params inline `[len src]`, sources basses)

`0018`@`$00BE`, `0556`@`$1B1A`, `02F1`@`$28CC`, `05C8`@`$211A` (+
VERIFY) — en-tête 10 o, checksum EOR. Répartition exacte
`$3DAA`×4 / `$3DC4`×4 (snapshot ? écriture ?) à relire au runtime
(idiome `L3D3F` ouvert).

## Cycle de vie

Boot (`start`) : `boot_copy` (bas→haut, snapshot ROM) → `keyin`
(`N` = sans images, `$56`=0) → `boot_copyback` (haut→bas) →
`init_vars` → jeu. SAVE en jeu : prompts (`vec_06`/`vec_05`) +
4 blocs + VERIFY (`vec_07`), retour boucle (`cmd_next` `$3E20`).
LOAD : prompt + `vec_02` + copies, échec → `TAPE LOADING ERROR`
+ reboot input (`JMP $2C3D`).

## Statuts et ouverts

- Usage en jeu des copies hautes **non observé** (snapshot SAVE /
  restore LOAD uniquement ?).
- Relève du harnais (stub B1) : elocs runtime, bit7 `b0`/`b1`,
  identité `$3C`, `$xC` si rencontré, séquence `$3DAA`/`$3DC4`.
