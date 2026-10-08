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

## Harnais sim65 : fonctionnel

- `scripts/pack_sim.py` : assemble `harness/shim.s` (`$C000`, zone "ROM" —
  le jeu n'y écrit jamais), patch `JMP $C000` sur `$7353` (scan clavier
  VIA), charge le charset ROM 1.0 (`$FC70-$FFBF`, font lue en `($0403)`),
  packe `/tmp/hobbit.sim` (load `$0400`, reset `$2C00`, SPAddr `$02`).
- `harness/shim.s` (en `$C000`, 512 o) : `shim_kb` — `PVRead` stdin avec
  machine à états pressé/relâché (compatible `BPL`/`BMI` des 4 sites
  d'appel ; EOF → `$00`, le jeu boucle → borner par `sim65 -x`, exit 254
  = fin de script normale), `PVWrite` d'un dump à chaque changement
  d'écran (texte `$BB80` + hires `$A000` si `--hires`), X/Y/ZP préservés,
  pile équilibrée (compter PHA/PLA à la trace : un `PHA` d'entrée oublié
  = `RTS` fantôme).
- Layout sim65 : code `$C000`, vars `$C200` (`KBSTATE`, `HIBIT`, …),
  pile paravirt `$C210`, miroir texte `$C300` (1120 o), miroir hires
  `$C800` (8192 o), charset ROM 1.0 `$FC70-$FFBF`. Protocole stdout :
  `@@FRAME text\n`+1120 o / `@@FRAME hires\n`+8192 o (captures partielle
  si timeout en plein dump → ignorées par le décodeur).
- `scripts/decode_frames.py` : rend les écrans hires en texte (charset
  ROM, grille 8 px, bit5-gauche ; n'affiche que les lignes non vides).
- Recette input : `printf '\rLOOK\r' | sim65 -x 150000000 /tmp/hobbit.sim
  > frames.bin` (CR=`$0D` ; `\r` initial = touche du tourne-page d'intro),
  puis `decode_frames.py frames.bin`.
- Validé : boot → intro 2 pages (`You are in a comfortable tunnel like
  hall` … `to the east there is the round green door` … `Gandalf gives
  the curious map to you.`) → prompt `> LOOK.` ; `LOOK` rejoué (écho
  caractère par caractère, 1 frame/touche) ; `I DO NOT KNOW THE WORD
  " OOK."` observé.
- Pièges résolus : hooks paravirt `$FFF6`=read/`$FFF7`=write (pas
  l'inverse) ; RAM sim65 remplie de `$FF` (état shim explicité au pack :
  `KBSTATE=0`, miroirs=`$FF`) ; Reset() n'init pas SP (le jeu fait `TXS`,
  les shims isolés doivent l'imiter) ; boot recopie `$1B1A`→`$91D0`
  (1366 o) et une table `$28E6`+ vers le workspace haut (2 emplacements
  de shim écrasés avant `$C000`).

## Prochaine étape

AnimTalk (parser : nourrir le harnais — directions, objets, verbes, cas
tordus) et AnimAction (thesis : PNJ autonomes — laisser tourner à EOF avec
dump périodique ? points d'arrêt mémoire ?), puis nommer la zéro-page,
bloc 2 et bloc 3.

## Points ouverts et limites harnais (non bloquants)

1. 6 pointeurs `$440D` nuls (`$3CB4 $4DF9 $4E2D $52C3 $5BB5 $631A`) : adresses
   résolues à l'exécution → `TODO` dans le listing.
2. Pointeurs vers le bloc 2 (`$1370`, `$165A`, …) : zone message non analysée.
3. `STA $6A5C` (auto-modification) : octet gardé en donnée, code dès `$6A5E`.
4. Rôles de `vec_init`, `vec_06`, `vec_07` à confirmer.
5. SAVE/LOAD non testés : les vecteurs cassette (`$0405-$0417`) pointent
   vers la ROM 1.0, morte sous sim65 → tout `SAVE`/`LOAD` plantera (stubs
   à prévoir si on teste ces chemins).
6. Son `$0A` : si jamais positionné, `$771A` boucle sur VIA `$030D`
   (vaut 0 sous sim65 → spin infini). Init le laisse à 0, sans risque
   constaté.
7. Bloc 1 ne tourne pas sous sim65 (reset direct en `$2C00`) : vecteurs et
   base de font restent en configuration 1.0 (image TAP).

## Conventions établies

- `JSR $440D` + mot inline = adresse du message ; reprise à JSR+5.
- Queue `$440D` : `JSR $4737` / `JMP ($6A)`, helper `$44BE` (`INC $6A`).
- Base image : `data/hobbit.bin` chargée à `$0400` ; bloc 4 = `$2C00-$7A80`.
- Pas d'appels ROM directs dans le bloc 4 (vecteurs `$0405-$0417` du bloc 1,
  patchés selon ROM 1.0/1.1).
