# Session en cours — exploration bloc 4 (The Hobbit, Oric)

## Où on en est

Le listing `disasm/block4.asm` est en cours de fiabilisation :
- `scripts/disasm.py` réécrit : **descente récursive** (entries `$2C00`, `$2C35`,
  16 vecteurs) + point fixe (seeds r2 validés + `MANUAL_ENTRIES`) + règle
  `JSR $440D` (2 octets pointeur inline, reprise à JSR+5).
- `scripts/check_disasm.py` (nouveau) + `scripts/opcodes6502.py` (150 opcodes).
- Dernier `check` : 14875 o code (74 %), **0 illégal, 0 BRK**, 61 pointeurs
  `$440D` tous marqués (dont 5 nuls → TODO), 0 appel ROM direct, vecteurs OK.
- Reste (checker exit 1) : 61 désyncs tous expliqués (splits `$440D`, à
  exempter), ~15 tables-D à trier (12 vérifiées comme code), 2 branches
  queue (`$7A6E`/`$7A78` → `$7A62`), 2 conflits (`$6DCF` RTS légitime,
  `$6F6C` seed r2 à exclure).

## Prochaine commande

Les 12 `MANUAL_ENTRIES` (`$32B9 $3C8E $5B44 $5BC9 $5D31 $698B $6A02 $6EA7
$6D55 $6F2A $4599 $4DAF`) sont dans `scripts/disasm.py` mais le run
n'a pas encore été relancé :

```
.venv/bin/python scripts/disasm.py
.venv/bin/python scripts/check_disasm.py   # viser exit 0
```

## Points ouverts

1. Exempter les désyncs de splits `$440D` dans `check_disasm.py`
   (super-plages via WORDTABLE) ; longueur min pour la règle D.
2. Forcer la table de vecteurs `$2C05-$2C34` en code (16× `JMP`, vérifié).
3. Trancher queue `$7A60+` (données probable, seed `$7A67` à rejeter :
   branche vers `$04` illégal) et conflit `$6F6C` (exclure le seed).
4. Trier les tables-D restantes ; les pointeurs `$0000` (`$4DF9 $4E2D
   $52C3 $5BB5 $631A`) restent en TODO (sémantique runtime inconnue).
5. Mettre à jour `docs/block4-analysis.md` (convention `$440D`, carte
   corrigée), puis commit.

## Conventions établies

- `JSR $440D` + mot inline = adresse du message ; reprise à JSR+5.
- Queue `$440D` : `JSR $4737` / `JMP ($6A)`, helper `$44BE` (`INC $6A`).
- Base image : `data/hobbit.bin` chargée à `$0400` ; bloc 4 = `$2C00-$7A80`.
- Pas d'appels ROM directs dans le bloc 4 (tout passe par les vecteurs
  `$0405-$0417` du bloc 1, patchés selon ROM 1.0/1.1).
