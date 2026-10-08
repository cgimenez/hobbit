# Session — exploration bloc 4 (The Hobbit, Oric) : ÉTAT PROPRE

## État

- `disasm/block4.asm` fiabilisé : **15 692 o de code (78 %)**, 79 sites
  `JSR $440D`, **0 conflit**, `scripts/check_disasm.py` → **RÉSULTAT: PROPRE
  (exit 0)** depuis le commit `c6bdde3` + travail ci-dessous (à committer).
- Méthode : descente récursive (`$2C00`, `$2C35`, 16 vecteurs) + point fixe
  (seeds r2 validés + 24 `MANUAL_ENTRIES` + `SEED_EXCLUDE={0x6DCE}`).
- Conflit `$6DCF` résolu : `JSR $440D` en `$6DCA` (cible d'un `BEQ`, idiome
  print-and-return vers `RTS`) confirmé ; seed `fcn.00006dce` exclu
  (chevauchait le pointeur `$165A`) ; routine orpheline `$6DD0` ajoutée
  en manuelle (ses messages `$1415`/`$14F5` contiennent du texte lisible).
- Conflit `$6F6C` résorbé par la couverture du cluster `$6F44`/`$6F7E`.

## Prochaine étape

Round-trip ca65 **prouvé** : `scripts/rebuild.py` (ca65+ld65 via
`build/block4.cfg`, toolchain `tools/cc65/bin` exclusive) → 20 097 octets
byte-identiques `$2C00-$7A80`, exit 0. Listing déterministe (en-tête da65
volatil neutralisé).

Ensuite : harnais sim65 (packer format `sim65` + shims paravirt
`JSR $FFF1-$FFF9` : `putchar`→`PVWrite`, `keyin`→`PVRead`, cassette→stubs,
`PVExit`), puis nommer la zéro-page, explorer bloc 2 (messages `$1370`,
`$165A`, …) et bloc 3.

## Points ouverts (non bloquants)

1. 6 pointeurs `$440D` nuls (`$3CB4 $4DF9 $4E2D $52C3 $5BB5 $631A`) : adresses
   résolues à l'exécution → `TODO` dans le listing.
2. Pointeurs vers le bloc 2 (`$1370`, `$165A`, …) : zone message non analysée.
3. `STA $6A5C` (auto-modification) : octet gardé en donnée, code dès `$6A5E`.
4. Rôles de `vec_init`, `vec_06`, `vec_07` à confirmer.

## Conventions établies

- `JSR $440D` + mot inline = adresse du message ; reprise à JSR+5.
- Queue `$440D` : `JSR $4737` / `JMP ($6A)`, helper `$44BE` (`INC $6A`).
- Base image : `data/hobbit.bin` chargée à `$0400` ; bloc 4 = `$2C00-$7A80`.
- Pas d'appels ROM directs dans le bloc 4 (vecteurs `$0405-$0417` du bloc 1,
  patchés selon ROM 1.0/1.1).
