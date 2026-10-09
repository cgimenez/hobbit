# Session — exploration bloc 4 (The Hobbit, Oric) : ÉTAT PROPRE

## État

- `disasm/block4.asm` fiabilisé : **16 890 o de code**, 99 sites
  `JSR $440D` (115 pointeurs inline `$440D`/`$5B24`), **0 conflit**,
   `scripts/check_disasm.py` → **RÉSULTAT: PROPRE (exit 0, sections A–H)**.
   Round-trip ca65 prouvé (byte-identique, `scripts/rebuild.py`). Arbre
   propre, tout commité.
- Méthode : descente récursive (`$2C00`, `$2C35`, 16 vecteurs) + point fixe
  (seeds r2 validés + 77 `MANUAL_ENTRIES` dont 16 vecteurs + 61 orphelins
  dispatch-indirect : 30 actions `L7014`/`L7143` + voisines règle D + token
  `$456F` + stubs d'armement `$65A5`/`$70B5` (en zones données, trahis par
  scan binaire des `STA $2Bxx`) ; `SEED_EXCLUDE={0x6DCE}`).
- Routines documentées via `ROUTINE_DOCS` dans `scripts/disasm.py`
  (**124** : socle + 33 actions + 27 moteur de messages + 20 événements
  `evt_*` (`evt_tick`/`evt_fire`, stubs `evt_armeN`, `evt_lookup`…) + 10
  moteur vectoriel (`vec_image`/`vec_line`/`vec_fill`/`vec_pos`/`vec_skip`/
  `vec_setup`/`vec_testpx`/`vec_plot`/`vec_addr`, `img_show`) ; nom +
  résumé → labels/commentaires régénérés ; checker H : début d'instruction,
  nom unique/valide). Zéro-page nommée via `ZP_NAMES` (**51** : 40 bases +
  11 `_hi`, da65 ne rendant pas `nom+1` ; checker H : adresse < $100, nom
  unique, label présent dans info). Ne jamais éditer le listing à la main.
- Conflit `$6DCF` résolu : `JSR $440D` en `$6DCA` (cible d'un `BEQ`, idiome
  print-and-return vers `RTS`) confirmé ; seed `fcn.00006dce` exclu
  (chevauchait le pointeur `$165A`) ; routine orpheline `$6DD0` ajoutée
  en manuelle (ses messages `$1415`/`$14F5` contiennent du texte lisible).
- Conflit `$6F6C` résorbé par la couverture du cluster `$6F44`/`$6F7E`.

## Harnais sim65 : fonctionnel

- `scripts/pack_sim.py` : assemble `harness/shim.s` (`$C000`, zone "ROM" —
  le jeu n'y écrit jamais), patch `JMP $C000` sur `$7353` (scan clavier
  VIA), charge le charset ROM 1.0 (`$FC70-$FFBF`, font lue en `($0403)`),
  packe `build/sim/hobbit.sim` (load `$0400`, reset `$2C00`, SPAddr `$02`).
- `harness/shim.s` (en `$C000`, ~600 o, zone CODE `$C000-$C2EF`) :
  `shim_kb` — `PVRead` stdin avec machine à états pressé/relâché
  (compatible `BPL`/`BMI` des 4 sites d'appel ; EOF → `$00`, le jeu boucle
  → borner par `sim65 -x`, exit 254 = fin de script normale), `PVWrite`
  d'un dump à chaque changement d'écran (texte `$BB80` + hires `$A000`
  si `--hires`), X/Y/ZP préservés, pile équilibrée (compter PHA/PLA à la
  trace : un `PHA` d'entrée oublié = `RTS` fantôme).
- Layout sim65 : code `$C000`, vars `$C2F0` (`KBSTATE`, `HIBIT`, `MEMFLAG`,
  …), params paravirt `$C2FB-$C2FE`, miroir texte `$C300` (1120 o), miroir
  hires `$C800` (8192 o), charset ROM 1.0 `$FC70-$FFBF`. Protocole stdout :
  `@@FRAME text\n`+1120 o / `@@FRAME hires\n`+8192 o (captures partielle
  si timeout en plein dump → ignorées par le décodeur), puis si écran
  changé : `@@MEM 0000 0100\n`+256 o (ZP) et `@@MEM 2B00 0100\n`+256 o
  (tables scheduler) — `scripts/decode_mems.py` (diff par trame).
- `scripts/decode_frames.py` : rend les écrans hires en texte (charset
  ROM, grille 8 px, bit5-gauche ; n'affiche que les lignes non vides).
- Recette input : `printf '\rLOOK\r' | sim65 -x 150000000 build/sim/hobbit.sim
  > frames.bin` (CR=`$0D` ; `\r` initial = touche du tourne-page d'intro),
  puis `decode_frames.py frames.bin` (OCR hires → texte).
- **Mode rapide** (`pack_sim.py --fast` → `build/sim/hobbit_fast.sim`,
  patch `$2C4A` `01`→`00` : `$56=0`, `img_show` no-op) : texte seul,
  500 ticks + dumps complets en **3,4 s** mur ; lecture par OCR hires
  (les dumps `@@FRAME text` bruts sont des pixels en mode hires).
  Touche sacrifiée `\r` tous les 8 `WAIT` (pause toutes les 16 CR).
- `$56` : **toujours 1 au boot** (`LDX #$FF` / `BNE L2C49`, `L2C3D`
  morte depuis `start`, ne vit que via QUIT ; aucun autre écrivain) —
  l'idée « répondre N au boot » était fausse.
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

## AnimTalk : règles parser observées (harnais)

- Boot : le jeu joue lui-même `LOOK` en tutoriel (écho `> LOOK.` +
  description complète, sans input). Ne pas re-`LOOK` en premier.
- Déplacement = direction nue (`EAST`, `E`, `N`, `NE`→`NORTHEAST`…) ;
  `GO EAST` = verbe transitif → `I SEE NOTHING TO GO THROUGH` (idem
  `GO NORTH`). Bloqué/inexistant → `YOU CANNOT GO <DIR>.` (même message
  porte close et sans sortie).
- Insensible à la casse, écho normalisé en capitales (`go east`→`> GO EAST.`).
- Mots inconnus : `I DO NOT KNOW THE WORD " <mot>."` ; verbe inconnu
  (slot = 2 mots, ex. `LOOK AT`) : `I DO NOT KNOW THE VERB " <mots> "`.
  Connu+inconnu (`OPEN SESAME`) → cite le mot inconnu.
- `GET MAP` (déjà porté) → `YOU ARE ALREADY CARRYING THE MAP.` ;
  `DROP MAP` → `You drop the curious map.` ; `INVENTORY` → `You are
  carrying.` + liste (vide = rien) ; `OPEN CHEST` → `You open the wooden
  chest.` (contenu vu au LOOK suivant) ; `OPEN DOOR` → `You open the round
  green door.` ; `SCORE` → `You have mastered 0.0% of this adventure` ;
  `HELP` → `YOU'RE DOING FINE.` ; `QUIT` → illustration + score, retour au
  prompt (pas de sortie sous harnais) ; commande vide (`> .`) = no-op.
- `WAIT` existe : `You wait.` + `Time passes...` = tick horloge pur (outil
  de sonde AnimAction idéal, sortie texte seule, rapide).

## AnimAction : PNJ autonomes confirmés (1 tick = 1 commande réussie)

- Seules les commandes **réussies** tickent (`LOOK INVENTORY WAIT OPEN GET
  DROP` mouvements…) ; ratées (`CANNOT`, `SEE NOTHING`, `DO NOT KNOW`),
  `HELP`/`SCORE`/vide → aucun tick (vérifié : 0 action PNJ).
- Gandalf (script adaptatif) : donne la carte au boot → ouvre la porte
  verte (même si c'est le joueur qui ouvre le coffre / `INVENTORY`!) →
  `Gandalf goes east.` → `Gandalf takes the curious map.` (prend des objets
  pour son compte). Plusieurs PNJ agissent sur le même tick (`Gandalf goes
  east.` + `Thorin waits.`) ; `Thorin enters.` suit le joueur.
- Mécanisme (lu dans le listing + prouvé par dumps MEM) : `world_tick`
  (`$4E59`, après chaque commande réussie, boucle `$7E` = ticks multiples
  possibles) → `entity_tick` (`$4ED5`) = **VM à scripts** : table `$2B45`
  d'entrées 7 o `[id, ?, PC_lo, PC_hi, ?, ?, ?]` (`$FF` termine) ; ≤6 opcodes
  par entrée et par tick, opcode = nibble bas du script (`$29xx`, bloc 2),
  PC réécrit dans l'entrée (`script_step4/step2` = `L502A/C` : +4/+2,
  +2 si bit `$10`, commit ; `script_adv` = `L5020`) — vu en MEM : PC entité
  `$3E` `$295C→$297A…` (linéaire, plusieurs ops/tick possibles : +13 en un
  tick), autres `$298E↔$29AF` (boucle). Opcodes (nibble bas) : `$x0-3`→`L5048`
  (pair : step+`entity_move` `$13/$15/$16` ; impair : step+appel table `L7143`),
  `$x4`→`L50AC` (step +2, move si octet1≠`$FF`, sinon jump si bit `$10`),
  `$x5-E`→chaîne (`$xE` : PC=script+1..2 ; `$xC`=`entity_goto` ;
  `$xF`=`L51CA`), défaut `$x6,7,8,9,A,B,D`→`L51DA`. `entity_move` (`L511C`) :
  test lieu/flags, `L4B37`, message via `say_if_visible` (`L5279`, **seulement
  si entité au lieu du joueur `$C8`** — règle de visibilité).
  Programme `$3E` décodé : `02 1D 03 00 / 02 10 05 FF / 04 24 14 13 / …`
  (tentatives de mouvement).
- `$13` = **id de direction/mot** (prouvé par MEM sur commandes joueur :
  `NORTH→01 SOUTH→02 EAST→03 WEST→04`, boucle 11 mots `L5F11`+`L57D5`) ;
  `exit_ptr` (`L43CB`, recalculé à la main) : `($F8) = $26DA + $13*8`
  (entrées 8 o : directions = `[d0 d1 00 00 00 00 AD 04]`, ex. E=`35 03…`) ;
  consommé par `move_core` (`L36DB`, joueur et PNJ) qui en extrait `$77/$78`
  (`code_4141`, nibbles) puis évalue `$15/$16` (`cond_eval` = `L3759` :
  `$FF`=absent, sinon avance `$8A` et copie 6 o vers `$DC/$E2`).
- `$73` creusé (hypothèse acteur ** réfutée **) : **flag de mode** —
  `move_flags` (`L3770`) le dérive de `$78` (`$78&$80→$73=1`, sinon `$73=$78&1` ;
  idem `$74` avec bit 6, `$80=$78&1`), le parser le force transitoirement
  (`L3A6B` : 1→0 autour de la résolution d'objet). `1` = direct/sans contrôles
  (saute les checks `L4B37`/`L511C`/`L5127`/`L52D1`, message unique `L51A0`,
  variante `L43E4` de `cond_eval`, redirection d'appel `L38E5`, étape bonus
  `L3679`) ; `0` = conditionnel (matching d'identité `$15==$C5`/`$16`,
  variante `L43F3` via `L5331`). **Observé `=00` dans les 26+ trames MEM**
  (boot, ratés, porte/pontes réussies, ticks PNJ) : le `1` est transitoire
  (jamais capturé en fin de tick) — bit 7 de `$78` = sortie « directe »
  probable (ex. sans porte). `$C8=01` = lieu joueur (salle init) ;
  `$13=$1E` = cas spécial (sans contrôle lieu). Anomalie notée : `NE` accepté
  (`YOU CANNOT GO NORTHEAST.`) mais `$13` final = résidu boot (`05`) —
  chemin diagonal à élucider ; `$13 ∈ {$04,$0E,$10,$13,$1D,$24}` des scripts
  ≠ directions (autre sous-espace : objets/lieux ?).
- Tables d'actions (bande `$70xx-$71xx`, lues au binaire + r2) : `L7014`
  (15 actions `L4B37`, sentinelle index 0 `$FF61`) et `L7143` (15 actions VM,
  sentinelle `$FF0B`), toutes en bloc 4 ; appel via `L4C5D` (saut indirect).
  **Invocation en 2 phases** (`L506B`) : sonde `$0C=0` → `act_probe` (`$5386` :
  `$12=1` + annule un niveau) si gardes OK, sinon stop ; exécution `$0C=1`
  (traverse). Gardes typiques : visibilité `$C9==$C8` (même lieu),
  `$1B21`/`$1E4B`/`$1B40` (lieux), `$CE` (one-shot, auto-consommé),
  `rand_range` (`$56D7`, PRNG bruit `($93)`, `LDA #n/CMP #m/BCC` = proba),
  message via `act_msg` (`$5B24`, `$13E8`). Branche ids `≥$80` (`L4BC9`) :
  table `[$5FAE` + mots hors-bloc4 `$0732…]` — usage non observé (code
  blocs 2/3 ? chemin mort ?). Convergence vérifiée : id VM `$29` et action
  compteur `07` → même `$6DD0` (`L7143`/`$7169` contiguës, fenêtre valide
  index 0-13, `$AC06…` jamais indexés). Seconde table `$2B12` (5 o,
  compteurs, actions via table de sauts `$7169`) : dormante au début
  (compteurs à 0, aucun changement en MEM sur 6 ticks).
- **30 actions documentées** (16 890 o de code bloc 4, checker PROPRE,
  textes décodés par réimplémentation Python du moteur — voir
  `docs/block4-analysis.md`, citations intégrées aux `ROUTINE_DOCS`) :
  corps lus au binaire + r2, nommés `act_p14_ii` (table `L7014`, verbes
  joueur) et `act_v14_ii` (table `L7143`, PNJ). Effets vérifiés (guarde +
  mutation + message). `L7014` : 00 `$60BF` consomme compteur ($C6)+5 + RAZ
  16 o (msg $1525) ; 01 `$60ED` déplace objet ; 02 `$61C9`/03 `$6222`
  bit5 de ($8A)+7 = 0/1 (03 id==1 → `$580F` fête, msg $171B « CHEERING
  CROWD ») ; 04-05 `$5CA9`/`$5D06` prise/pose ; 06 `$65DD` dit $140C ;
  08/12 `$65BA`/`$65B6` dispatch objet $16 ($04/$0F) ; 09 `$6B72` (garde
  $C5==$41) ;   10 `$65F1` gate ; 11 `$66D6` dit $1478 (araignées) + arme e1 ;
  13 `$6041` flags objet ; 07/14 `$61E5`/`$5CB6` lecture flags. `L7143` :
  00 `$692D` dit $1427 ; 01 `$68E0` 1 de 3 messages d'oisiveté ; 02 `$690C`
  dit $1441 ; 03 `$6962` (même lieu) dit $14AB ; 04 `$6936` tirage 0-7
  ($4D9E) ; 05 `$697A` (lieu $1DE0) ; 06 `$68D0` dit $143F ; 07 `$6CFA`
  prend l'objet $1FC1 ; 08 `$6E59` tirage 0-100 msg $1582/$1596 ;
  09 `$6C8D` (lieux 27/2C/29) ; 10 `$6CBE` dit $153F/$155D ; 11 `$6C33`
  one-shot $CE ; 12 `$6C09` ; 13 `$6DF9` cherche via $3485 ; 14 `$6D78`
  tirage msg $16B9/$16C8. Textes décodés (moteur `render_text`, voir
  `docs/block4-analysis.md`) : dragon (`prepare to die`), Gollum
  (`pocket ?`, `my precious`), fête (`CHEERING CROWD…SUNSET`), etc.
- **Phase A SAVE/LOAD terminée** : dispatch commandes spéciales
  (`L3B75` : table `$3BC6` 13 clés + `$3BE0` 13 cibles) — SAVE=`$3DD9`
  (mot `$0DA0`), LOAD=`$3D7F` (prouvé harnais : `PRESS ANY KEY`),
  QUIT=`$3C88`, HELP=`$3C8E`, SCORE=`$3CCE`, PAUSE=`$3D39` ; verbes
  `$6FAC` (23 entrées) ; SAVE = 4 blocs (`save_block` `$3DAA` via
  `vec_03`, params `[len src]`) + VERIFY (`vec_07`) ; +90 o de code,
  130 routines, checker PROPRE, rebuild OK. Reste : idiome `L3D3F`,
  mot `(3D,06)`, `L7114+X`. Ensuite : stub B1.
- **Scripts `$29xx` décodés statiquement** (`/tmp/vmdec.py`, `docs/block4-analysis.md`) :
  17 entrées `$2B45` `[id,n,PC,base,s6]` (3 dormantes id=`$00`, 14 actives),
  opcodes déterministes (MOVE pair 4 o, ACT impair via `L7143`, `$x4`, `$xE`
  GOTO, `$xC` PATCH table, `$xF` RAND, `$x5-D` INDIR table[0], budget 6 ops/tick) ;
  table `L7143` = 18 mots (pas 15) → **3 actions inédites** `act_v14_15/16/17`
  (`$6E8B` trolls lieu 5, `$6CDB` wid=`$1B`, `$6EA7` queue de `$6E8B` qui retombe
  sur le slot mutable `$2154`=`$1645`) ; identifiés : `$3E` Gandalf (eloc `$01`),
  `$44` Gollum (arg `$10` caverne), `$41` dragon, `$47`/`$48` lieu 5 ;
  états `$1A62` (61 clés `$00-$2B`+`$3C-$4C`, trou `$2C-$3B`, `L5331`≠`L530B`, eloc=état+`$10`) ;
  exits étendues `$26DA`+wid*8 jusqu'à ~`$28C2` (wids `$0B+` conditionnelles).
  Ouverts : `+0..7` records, `$xC`, dormants, `$28E6`.
- **Qui arme `$2B12` élucidé** (événements différés, 20 `evt_*`) : `world_tick`
  2e moitié (`evt_tick` `$4E75`) balaye 10 entrées 5 o `[id,cpt,actA,cond,actB]`
  (`$FF` fin) : `cpt--`, réarme, puis `evt_cond` (`$4E9D`) dispatche `actB`
  via table de sauts `$7169` (`evt_fire` `$4EAB` → `L4C5D`) si `cond<>0` et
  `cond>=cpt`. Armement = idiome `cpt := id` (`LDA $2Bxx / STA $2Bxx+1`) ou
  immédiat ou `0`=désarme ou aléatoire (`e6 := 2+rand(8)`) : **14 sites**,
  les 10 entrées couvertes (e0 code_6407, e1 araignées `$66E8`, e2 `$70CB`,
  e3 `$65A5`, e4 `$70D2`/`$6C67`, e5 `$6B66`, e6 `$66A6`/`$66D2`, e7 `$6A20`,
  e8 `$70F8`, e9 `$6AF0`/`$6D60`/`$70D9`), dispatchés pour certains via table
  à clés `$709F` (`evt_lookup`, clé `$8F`). Deux sites trouvés uniquement par
  scan binaire des `STA $2Bxx` (en zones données, seeds `$65A5`/`$70B5`).
  Effectifs : seuls `cond<>0` tirent (e4 bog `$6C5F` auto-désarmant, e5
  `$6DD0`, e8 yeux `$6D9F` ×4, e9 `$6DBB`) ; voie `actA` inactive (`L4E58`
  toujours 0, aucun autre écrivain), `cond=0` = compte à rebours silencieux.
  Détails : `docs/block4-analysis.md`. Validation harnais restante :
  observer `$2B2B` après voyage PNJ.
- Les 7 pointeurs `$440D` nuls (`TODO`) élucidés : **idiome général** —
  slot `.word` rempli juste avant `JSR print_msg` (constantes `$13DC/$13E0`,
  lookup `L5399`, table `L6359,x`, calculé, ou `STX/STY` de `L5279` pour
  `msg_52C6`). Aucun n'est un bug du découpage.
- Sondes : shim dump MEM (`@@MEM 0000 0100` ZP + `@@MEM 2B00 0100` tables,
  `scripts/decode_mems.py` diff par trame) ; frappes d'écho = seuls
  `$0000/$0004` bougent ; chaque tick mute `$2B47/$2B4E/$2B55/$2B5C`
  (PC/entités), `$2B6A/$2B71/$2B94/$2B9B/$2BA2` (état), ZP divers.
- Traversée nominale : `OPEN DOOR` / `EAST` → `You go east.` / `gloomy
  empty land… exits east north northeast` / Gandalf sur place /
  `Thorin enters.`

## Harnais : protocole affiné (cause racine lue dans le listing)

- `pause_key` (`$7619`, relue dans `ch_put`) : **toutes les 16 CR** (`$11`),
  attend une touche avec **timeout (~10 essais)** puis le relâchement —
  consomme donc **1 frappe en attente** si elle existe (`L` de `LOOK`
  → `OOK`, `Y`/`↵` après `QUIT`), sinon continue (sûr sur EOF).
- Recette : après toute sortie longue (illustration : `LOOK`, mouvement,
  `QUIT`), intercaler une touche sacrificielle (`\r` → no-op `> .` au prompt,
  sans tick) avant la commande suivante.
- **Gabarit cmdfile F4/F5 (obligatoire)** : le boot mange la 1re ligne et
  `pause_key` les suivantes → `\n\nLOOK\n` initial puis `\n\nCMD\n` par
  ordre (2 lignes vides avant chaque commande). Sans ça : ordres mangés
  ou exécutés au tunnel. `tickdiff SIM CMDFILE` : sim65 hardcodé
  (`tools/cc65/bin/sim65`), flags `-t/-s/--db/--name` avant positionnels.
- Coût rendu illustration sous sim65 ≈ plusieurs centaines de M cycles :
  budgets `-x` généreux (2G pour 2 rendus), préférer les commandes
  texte seul (`WAIT`, `INVENTORY`) pour les sondes. `QUIT` perd l'input
  suivant (rendu) — prévoir la touche sacrificielle aussi.
- **Timings rapides validés** : `-t 100 -s 100` donne des deltas
  **identiques** (`diverge f37c f37c_fast` vide, `$20` au même tick ;
  30 s vs ~2 min pour 83 ticks). Le coût d'un run ≈ 1,1 s/ligne en
  `-t 300 -s 500` (300+500+300 ms de sleeps muraux par ligne, sim65
  répond en ms) — les runs hires paient en plus les illustrations
  vectorielles (×dizaines par run).
- **Piège construction cmdfile** : `VAR=$(printf ...)` mange les `\n`
  finaux → ticks fusionnés (`SOUTHDOWN`) + rythmes décalés. Toujours
  vérifier (`grep -c`, 1er `diff` d'octets vs référence).
- **Tick tickdiff vs tick monde** : 1 ligne = 1 tick (lignes vides
  incluses, no-op sans tour) ; 1 commande acceptée = 1 `world_tick`
  (`entity_tick`+`evt_tick`). Règle : 0 delta = pas de tour (rejet
  avant `world_tick`), >0 = un tour. PNJ strictement tour-par-tour
  (jamais de mouvement sur lignes vides ; déterministe vérifié).

## Prochaine étape (snapshots : FAIT, 0-delta prouvé)

**Bascule snapshots implémentée** (`harness/snap.s`, `pack_sim
--snapshot NOM`, `tickdiff @@SNAP`, `tickdb.py snaps/snap-show/
snap-diff/snap-verify/snap-init`) : `vec_02/03/04`
(`$2C0B/$2C0E/$2C11`) → `snap_load`/`snap_save`/`s_clc`, sans état
(index déduit de src/dst : `$00BE/$1B1A/$28CC/$211A`), prompts
`vec_05/06` conservés (1 touche sacrificielle chacun). Stockage double :
`sav/NOM.bin` (`"SNAP"`+3623) + table `snapshots` (run,tick,ploc…,
`data` BLOB). Images par défaut byte-identiques, tickdiff régressé
(`diverge f37c f37c_new` vide).
**Validation** : `sna` (Rivendell `$09`, SAVE tick19, salissure
`EAST`→`$0A`) → `pack --snapshot revise` → `snb` (reboot, LOAD :
`$09` restauré, `INVENTORY`/`EAST` vivants) → **0-delta byte-exact**
(3623 o post-LOAD == SAVE, run direct pacé, `-x` court).
**Pièges trouvés** : `tickdiff` envoyait `sav/` dans `build/sav/`
(dépilage chemin) ; `VALUES` à 10 pour 9 colonnes (prepare silencieux) ;
run direct non pacé : `pause_key` mange les lignes (¿`LOAD` jamais
exécuté) ; **spin EOF-idle pollue la mémoire** (~32 o sur 2G cycles —
comparer à `-x` court ou runs tickdiff, jamais après idle long).
Pas de `--tape` (bascule franche, `tape.s` dormant).

Ensuite : checkpoints (`rivendell`, `cellar`…), fin du jeu (tonneau :
vider ? butler endormi ? ; cond `$06`→`$0F` ; `$16` NW ; dragon
`$29`), puis B1 byte-layer en validation croisée. Sondes en
attente : bit7 `b0`/`b1`, identité `$3C`, eloc runtime, `$xC`.

**Pas de ROM exécutée** (point levé) : sim65 = 6502 nu, aucune ROM
chargée ; `basic10.rom` = fonte en DONNÉES (jamais exécutée) ;
tout le code cassette est du code jeu (rebuild byte-identique).
Le snapshot ne contourne donc aucun hardware réel.

Ensuite : checkpoints (`rivendell`, `cellar`…), fin du jeu (tonneau :
vider ? butler endormi ? ; cond `$06`→`$0F` ; `$16` NW ; dragon
`$29`), puis B1 byte-layer en validation croisée. Sondes en
attente : bit7 `b0`/`b1`, identité `$3C`, eloc runtime, `$xC`.
**B1** (`harness/tape.s` + `pack_sim.py` + `save_tape.py` +
`diff_tape.py`, 6 vecteurs `$0405`–`$0414` ; `$0417` = loader jeu
conservé, pas un vecteur) : SAVE écrit 4 blocs valides (headers+EOR
vérifiés) ; bugs stub trouvés+fixés (`MARK_1` sans `\n`, header 9 o
pas 10, `rd_byte` qui retombait dans son entrée, `ST_OP` qui écrivait
à côté du buffer). Reste : VERIFY reporte une erreur et LOAD même
session échoue (buffer relu différent ?) — diagnostic en pause,
priorité à l'observation via tickdiff (pas de SAVE/LOAD).
**tickdiff** (`scripts/tickdiff.c` → `build/sim/tickdiff`, + shim
`dump_mem` 4 régions) : superviseur C, sim65 vivant par pipes, un
ordre = un tick = INSERT direct en SQLite (`--db/--name`, plus
aucun `ticks.log`/`snap*.bin`). Protocole durci : `-t 300 -s 500`
(tassement anti-rafales) + touche sacrificielle (ligne vide) après
chaque sortie longue — sans ça, `pause_key` mange le début de
l'ordre suivant (`SOUTH`→`UTH`, `NORTH`→`RTH`).
**Couverture vraie : 2,5 %** (91/3623 o) — l'ancien 77 % était un
artefact (run `r1` : baseline de zéros → 2779 deltas poubelle au
tick 1, run supprimé de la DB). Vierges : 835 o (`vierges`).
Runs joués : R1 300×WAIT, R2 objets, R3 mouvement (diffs seuls),
R4 1463×WAIT (stop limite 2G cycles, pas un crash),
R5 exploration (`r5.txt`, 18 ordres : EXAMINE/OPEN/TALK/EAST/NORTH,
mort dans la clairière → reboot), R6 combat (`r6.txt` : KILL
VICIOUS → attaque vaine + troll mange joueur + reboot).
Résultats → `savegame-memory-map.md` §7 (cluster `+$xxx` = `eloc`,
`+0` classé, 961/966 piloté scripts, events tous `cpt=0`,
gloutonnerie `act_v14_15`, `n` jamais, `s6` quasi-statique).
Repro 966 : `build/sim/r966.txt` (`\n` + 1000×`WAIT`) → 3 runs
identiques (`ticks_r4`, `ticks_966a/b`) : e9/e10 PC `$2AD0`
959 ticks puis blocs 5 o, terminal ACT 17 ; dragon 961 (ACT 8).
Verdict events : bin == runtime, `cpt=0` partout (R4/R5/R6) →
`evt_tick` saute tout (`beq`) ; l'ancien « e8 armé cpt=3 »
était une lecture désalignée, corrigée (§3c : e6 `00 00 08 00
00`, e7 `05 00 09 00 00`, e8 `04 00 0A 03 0B`, e9 `05 00 0C 01
0D`). Combat n'arme aucun event.
Deux images : `hobbit_fast.sim` (texte seul, tickdiff) +
`hires.sim` (`--fast --hires`, OCR) ; cmdfile tickdiff en `\n`
(1re ligne = touche boot), run brut en `\r` (`tr`).
**DB SQLite** `build/sim/hobbit.db` (gitignorée) via
`scripts/tickdb.py` (`import` + `traj`/`touches`/`diverge`/
`morts`/`lieu`/`query`) : 15 runs importés (R1–R7, repros) ;
table `state` (ploc/eloc/obj/crec par tick, lue des snaps).
Premier gain : `morts` trouve 2 extinctions manquées — e3
(`$43`) au 9e tick monde, e2 (`$40`) au 324e (même signature
`id`→`$00`) ; `diverge 966a 966b` vide (déterministe).
`L7143` = 19 entrées (0–18 : sentinelle + 15 + 3 inédites ;
labels `act_v14_ii` = entrée−1 : `act_v14_15`=`$6E8B` mange,
`act_v14_16`=`$6CDB`, `act_v14_17`=`$6EA7` mort programmée).
Prochaines pistes : **salle `$0A` Misty mountains (sorties
E/N/W/S, warg offensif)** ; triggers d'armement events,
`n`/`s6`, ZP inconnus, nord `$06` (porte rock), Gandalf (R8/R9).

## Bloc 2 : dictionnaire et messages élucidés (émulation statique)

- Banque `$0540-$1156` : **600 mots triés** + index 26 lettres `$0500`
  (25/26) ; 32 mots courants `$1117` (THE…TROLLS) ; format bit7/flags et
  suffixes `$4322` élucidés (émulation fidèle de `word_render`).
- `$02` = **GOTO** (offset signé, sans retour), `$0B` = recurse offset signé
  (queues partagées : prépositions `$13A8` IN/ON/BEHIND/UNDER/TIED+TO sur
  queue `THE`, bateau `$1380→$134D`). Docs `tok_skip`/`tok_recurse` à jour.
- Catalogue `$1157-$1A0E` : **171 messages** (parser, combat ~20, bateau,
  templates LOOK, dragon `PREPARE TO DIE` ×2, Gollum, victoire, score/hints,
  **29 lieux** dont `$18AA` tunnel initial). Décodeurs en `/tmp`
  (`dict.py`, `msgdec.py`, `msgsweep.py`, `bankparse.py`, non promus).

## Bloc 2 : records de lieux cartographiés (statique, non committé)

- Table `$2070` : 80 ids → records (`L530B` : `record = *($2070+id*2)` ;
  id ≥`$50` → 0, id `$2F` nul). Mêmes records lieux + objets + créatures.
- **29 records de lieux** (ids `$01 $04 $06 $07 $0A-$0C $0E $10 $11 $13 $14`
  `$18-$1C... $32`) : champ `+8` = pointeur desc (uniforme, consommateur
  `code_4DF6` du LOOK) ; flags `+1` bit6 (`L363E`), `+7` & `$48` (`L53C3`) ;
  slots mutables (`$2154 := $1645` trolls, bit6 `$214C` clear). `$13`/`$14`
  partagent `$1931`, `$1A07` en 2e desc (`+$0B`) pour 4 lieux.
- Exits `$26DA` : 10 directions + noms décodés (NORTH…DOWN),
  `exit_ptr = $26DA+$13*8`, boucle `L37DE` + matcher `code_433A` (émulé :
  `wid := $6C`) rattachée au choix PNJ (`L35AE`), pas au LOOK. Cond :
  table clés `$1A62` → blocs `$1Bxx`, table 3 o `$1A5F`, flot
  `move_core`/`cond_eval` cartographié ; table `$2732+` à queues `$40`.
- **Ouvert `+0..7` RÉSOLU** : `[b0, b1, 3 paires (mot, masque-nibble)]` =
  signature d'appartenance ; matcher `code_433A` émulé fidèlement
  ((0,0)=absent, octet0 full + octet1-nibble, repli paires croisées) ;
  voies `L53C3` (cond↔record+8), `L54F8` (cond↔record+2), `L37DE`
  (cond↔exit), `L363E` (record+1 bit6, cherche id==arg1) ; groupes :
  `$0F`+`$34-$41`, `$44-$4A`(+`$0C`), `$4B-$4D`, `$4E-$4F`, `$42`=WEST,
  `$43`=EAST, rooms uniques. `b0`&`$0E` = template LOOK (`L4DC6`),
  bit7 ? ; `b1` bit6 = `L363E`, `$A0`/`$B0` ? ; dormants = vrais
  scripts (`$42`/`$46`/`$3C`, id seul par events) ; copies boot `L30F9`
  (états→`$91D0`, `$28CC`→`$9726`, records→`$9A17` mutables, ZP→`$9FDF`).
  Détails `docs/block4-analysis.md`.

## Bloc 3 : illustrations vectorielles élucidées (sous sim65)

- Table `$7AC0` : 13 entrées `[clé,mot]` (`$FF` en `$7AE7`, lookup `L5399`
  pas de 3) ; 13 flux `$00`-terminés tuilés `$7AE8`→`$91AF` (zéro ASCII
  long : que du dessin) ; chaque image = `[mode,$08,x,y]` + commandes
  (`$08` curseur, `$20` skip→`$FF`, bit6 fill, bit7 ligne 2 o).
- Moteur bloc 4 (`vec_init` `$77D4`, 10 routines `vec_*`/`img_show`
  documentées) : setup (efface hires, couleurs), dispatch, plot pixel par
  pixel (`L7A0F`) — lignes puis fills, ~33 M cycles/image (d'où la lenteur
  du rendu).
- Preuve : pilote sim65 (reset sur driver `$E800`, `vec_init` + dump hires
  via `shim_kb`, `-x 600M`) → 13 frames → 13 illustrations distinctes et
  cohérentes (artefacts `/tmp`, pilote non promu dans le repo).
- Cas notés : image `$0D` contient l'image `$15` (+29 o de tête, composite
  confirmé visuellement) ; clé `$05` absente de la table → `L6EF7` poke en
  `$0805`/`$0806` (bloc 2, sans lecteur bloc 4 : ouvert) ; clés
  plausiblement = ids de lieux (à confirmer en jeu).

## Points ouverts et limites harnais (non bloquants)

1. 7 pointeurs `$440D` nuls (`$3CB4 $4DF9 $4E2D $52C3 $5BB5 $631A $63BE`) :
   slots `.word` remplis à l'exécution → `TODO` dans le listing.
2. Bloc 2 messages résolu (171 msgs, catalogue `/tmp/catalog.txt`) ; reste
   l'encodage `+0..7` des records lieux (piste : harnais ciblé ou scripts
   `$29xx`, opcodes VM connus).
3. `STA $6A5C` (auto-modification) : octet gardé en donnée, code dès `$6A5E`.
4. Rôles de `vec_06`, `vec_07` à confirmer (`vec_init` établi : entrée
   du renderer d'illustrations → `vec_image` `$77D4`).
5. SAVE/LOAD non testés : les vecteurs cassette (`$0405-$0417`) pointent
   vers la ROM 1.0, morte sous sim65 → tout `SAVE`/`LOAD` plantera (stubs
   à prévoir si on teste ces chemins).
6. Son `$0A` : si jamais positionné, `$771A` boucle sur VIA `$030D`
   (vaut 0 sous sim65 → spin infini). Init le laisse à 0, sans risque
   constaté.
7. Bloc 1 ne tourne pas sous sim65 (reset direct en `$2C00`) : vecteurs et
   base de font restent en configuration 1.0 (image TAP).

## Conventions établies

- `JSR $440D` (`print_msg`) **et** `JSR $5B24` (`act_msg`, rebondit vers
  `print_msg`) + mot inline = adresse du message ; reprise à JSR+5.
  Mécanique exacte (`print_msg`) : PLA de l'adresse de retour (+1) en
  `$6A/$6B`, lit le pointeur message en `($8A)` via `($6A)`+`$44BE`
  (`msgptr_inc` : `INC $6A`), rend le texte (`$4444`+), puis `JSR $4737`
  (`fetch_retaddr` : adresse empilée → `$8A/$8B`) et `JMP ($6A)` reprend
  l'appelant.
- Base image : `data/hobbit.bin` chargée à `$0400` ; bloc 4 = `$2C00-$7A80`.
- Pas d'appels ROM directs dans le bloc 4 (vecteurs `$0405-$0417` du bloc 1,
  patchés selon ROM 1.0/1.1).

## Carte mémoire : SSOT + registre de couverture (priorité mapping)

Objectif rappelé : terminer le jeu **mais surtout** mapper/nommer toutes les
variables SAVE/LOAD. Socle posé :

- **SSOT** `scripts/memmap_defs.py` : 4 régions + décomposition
  (`ZP_NAMES`, 61 clés `$1A62` + champs, 13 tables INDIR, 10 events `$2B12`,
  17 entités `$2B45`, 79 records `$2070` via image). `annotate(base,off)` →
  slots candidats (blocs d'état chevauchants → multi-slot). Identités connues
  (`map`, `gandalf`, `troll_*`…) portées au nom.
- **Registre** `scripts/memmap.py` : fusion des deltas des **deux** bases
  (`hobbit.db` tickdiff + `solver.db`/`SOLVER_DB` BFS) → preuves par slot.
  `report` (couverture + var nommés), `slots [--virgin]`, `addr`, `sources`,
  `xref` (réfs littérales de `block4.asm`), `gen [--write]` (annexe du doc
  entre marqueurs AUTO-COUVERTURE).
- **Garde-fou** `scripts/check_memmap.py` → `RÉSULTAT: PROPRE` (sections
  A–F ; `check_disasm.py` reste PROPRE).
- **Moteur de couverture** : `solver.py --seed NOM --goal coverage`
  (amorçage checkpoint `sav/NOM.bin`, profondeur 8 par défaut, rapport de
  couverture en fin) ; `SOLVER_DB=...` isole les runs. Multi-seed idempotent.

Baseline : **140/3623 octets (3,9 %)** mutés (union) ; var nommés couverts
ZP 5/7, états 30/187, scripts 32/169, records 18/158. Les 4 checkpoints
(`revise`/`cell20`/`ante2`/`dunj`) ajoutent **0 octet** (saturé) mais le BFS
atteint **7,5 %** (noeud 10 : `NORTH` depuis `cell20`) vs 2,5 % avant.
Prochaine cible de couverture : **états/objets/events non encore atteints**
(fin de jeu, armement d'events, kills) — la couverture d'octets exige de
nouveaux états, pas de la re-marche.

## Reprise 2026-10-09 (suite) — priorité MAPPING + jeu dirigé + lumière

**Objectif rappelé** : terminer le jeu **mais surtout** mapper/nommer toutes
les variables SAVE/LOAD. Infrastructure désormais en place (commits
`6f5d285`, `9dc0536`, `b8c0cbc`, `05ad976`, `4cfc2c1`).

### Outillage mapping (SSOT + registre)
- `scripts/memmap_defs.py` : SSOT. 4 régions + slots nommés : `ZP_NAMES`
  (7), 61 clés d'état `$1A62` (+identités `player/map/key/sword/lunch/
  gandalf/dragon/butler/gollum/troll_*`), champs `type/carrier/tpl/eloc/
  falls/lock`, 13 tables INDIR, 10 events `$2B12`, 17 entités `$2B45`,
  79 records `$2070` (via image). `annotate(base,off)` → slots (multi-slot).
- `scripts/memmap.py` : `report` (couverture + var nommés), `slots
  [--virgin]`, `addr <base> <off>` (annotation + preuves = commandes/valeurs),
  `sources`, `xref [base [off]]` (réfs littérales `block4.asm`), `gen
  [--write]` (annexe between markers dans `savegame-memory-map.md`).
  Env `SOLVER_DB=` cible une base de run.
- `scripts/check_memmap.py` : PROPRE (A–F ; noms/contiguïté/docs/genres,
  61 clés / 13 INDIR / 10 events / 17 entités / 79 records).
- Métrique : **85/290 variables réelles couvertes (29 %)** (var = hors
  constantes : état `+0` type, `b1`, `n`, `balo/bahi`, event `actA/cond`).
  Vierges : `records.b0` 61 (visiter lieux), `états.carrier` 56 + `eloc` 40,
  `scripts` PChi 12 / cpt 8 / id 9 / s6 17, `ZP.exploc/once` 2.

### Jeu dirigé (outillage)
- `solver.py` : `--seed NOM` (checkpoint `sav/NOM.bin`, multi-seed
  idempotent), `--goal coverage` (prof. 8), `--moves-only` (directions),
  `--route FICHIER [--seed N --save N]` (séquence + suivi couverture,
  stop mort/invalide). `SOLVER_DB=build/sim/cover.db` isole les runs.
- `map_static.py --path <from> <to> [--via A,B]` : plus court chemin sur le
  graphe statique (78 records/203 sorties).
- `routes/` : `east.txt`, `barrels.txt` (fichiers de jeu dirigé).
- **Constat** : le BFS sature la couverture dans le monde atteignable
  (0 nouvel octet) ; il faut progresser dans la quête. BFS trouve toutefois
  score **7,5 %** (nœud 10 : `NORTH` depuis `cell20`) vs 2,5 %.

### Découverte : LUMIÈRE = l'épée (donjon franchissable)
- `is_dark` (`$4C82`, doc `ROUTINE_DOCS`) : un lieu est sombre SAUF si un
  état `$1A62` est **au lieu du joueur** avec `+4` bit7 et `+7`
  (bits `$08`/`$04`/`$40` posés, `$10` clair).
- Seule clé matchante : **`$0E`** (`$1CB0`) = **« the short strong sword »**
  (init eloc `$07`). Preuve : patch `state$0E.eloc := ploc` dans `ante2`
  (`$1F`)/`gloomy`(`$04`)/`revise`(`$09`) → LOOK révèle la pièce (plus
  « IT IS DARK ») + liste « the short strong sword ».
- **Corrige** l'ancien « pas de lampe au jeu » (séance 9 `aventure.md`).
- Blocage : épée en `$07` derrière la **porte rock** (`$06 N`, cond `$01`)
  → `NORTH` = `YOU CANNOT GO NORTH` ; `PUSH/BREAK ROCK` inopérants.

### PROCHAINE ÉTAPE (reprise après compactage)
**Trouver ce qui ouvre la porte rock (cond `$01`)** → chercher l'épée `$0E`
→ franchir le donjon `$1E/$1F/$20` → quête (cellier→tonneaux→Lac→Montagne
`$2C`→dragon `$29`).

Chaîne de code du test de condition d'exit :
`move_core` (`$36DB`) : `ldx arg1; lda direct; jsr cond_eval` → si
`direct==0` `L43F3` (`jsr L5331` = état clé `arg1`, puis `ptr += 8`) sinon
`L43E4` (`L530B` record, `ptr += 2`) ; copie `(ptr)+5..0` → `cond1`/`cond2` ;
match via `L3679`/`L4B37`/`code_433A`. Donc **cond `$01` = signature
`état[$01]+8`** (état `$01` @ `$1B63` : `02 FF FF FF 00 00 90 81 F2 02 19 05
6F 08 00 00 07 06 0C 02` ; `+7=$81`). À élucider : quel opcode/action écrit
l'état `$01` (ou déplace l'épée), et pourquoi la porte rock reste fermée.

Autres pistes ouvertes : `scripts.cpt` (armement events), `records.b0`
(visiter les 55 lieux non vus, cf. `docs/game-map.md`), identités clés
restantes, `ZP.exploc/once`.

Commandes utiles :
```
.venv/bin/python scripts/memmap.py report           # couverture
.venv/bin/python scripts/memmap.py slots --virgin   # cibles
.venv/bin/python scripts/memmap.py xref 1B63        # qui touche l'état $01
.venv/bin/python scripts/check_memmap.py            # PROPRE
.venv/bin/python scripts/solver.py --route F --seed N --save M
.venv/bin/python scripts/map_static.py --path 06 07
```

### Addendum cond `$01` (porte rock) — relevés du 2026-10-09
- Record `$06` N→`$07` **[cond `$01`]** confirmé au binaire ; état clé `$01`
  @ `$1B63` = `02 FF FF FF 00 00 90 81 F2 02 19 05 6F 08 00 00 07 ...`
  (`+0=$02` = **non localisé**, `+7=$81` verrou-fenêtre, `+8..+D` signature
  `F2 02 19 05 6F 08`). Aucun xréf littéral (accès via `L5331`).
- Sondage jeu à `$06` : `OPEN/PUSH/BREAK/LIFT/GET/EXAMINE/STRIKE/KILL/PULL/
  MOVE ROCK|DOOR`, `CLIMB`, `ENTER`, `THROW`, `SAY`, `WAIT`×3 → **jamais**
  `NORTH` (`ploc` reste `$06`). Donc cond `$01` = changement global, pas une
  action locale.
- Portes sœurs (à événement) repérées :
  - **trou secret vers la Montagne** : état `$0B`+7 bit7 (`$1C7B`),
    `code_6DBE` (`ora #$80; sta $1C7B`) → `$165A` « A LOUD CRACK AND A HOLE
    APPEAR… SIDE DOOR TO THE MOUNTAIN » au lieu `$2A` ; `$1685` = vanish.
  - **porte magique elfes** : état `$0D`+7 bit5 (`$1D26`, `ora #$20`) →
    `$1415` « THE MAGIC DOOR OPEN » aux lieux `$1E`/`$1C` ; event e5
    (`$2B2B` cpt) → `$168B` « THE MAGIC DOOR WARN OF ELVES APPROACH ».
- Piste : état `$01` = objet/global « porte rock » ; chercher l'opcode/action
  qui pose son flag (ou déplace l'épée `$0E`) — probablement lié aux trolls
  (`$05`) ou à un événement. Alternative : trouver un autre accès à l'épée.

### Résolu (2026-10-09 soir) — trolls → pierre, porte rock, épée
- **`$05` = trolls clearing** ; le troll hideux `$47` porte la grande clé `$04`.
- Quitter `$05` + attendre ~4 ticks → « Day dawns. » → `act_v14_17`
  (`$6EA7`) change les trolls en pierre (RAZ bit7 `$1F94`/`$1FA6`, desc
  record `$05`→`$1645`). Reprendre la clé (`GET KEY`).
- `$06 N` cond `$01` = **état `$01` « the heavy rock door »** (`+7`
  bit0=verrou, bit5=ouvert) : `UNLOCK DOOR` (clé `$04`) efface bit0 ;
  `OPEN DOOR` met bit5 (Gandalf peut refermer, aléatoire) ; `NORTH` passe
  quand `+7=$A0`.
- **`$07` = trolls cave** : prendre « the short strong sword » `$0E`
  (source de lumière). Checkpoint `sav/sword.bin`.
- Idées ajoutées : `scripts/memmap_defs.py` `$01`=`rock_door`,
  `$04`=`key` ; `docs/aventure.md` séance 11 ; §2 `savegame-memory-map.md`.
- **Suivant** : franchir le labyrinthe noir Elvenking (`$1E/$1F/$20`) avec
  l'épée → cellier `$20` → tonneaux → Lac → Montagne → dragon.

### Séance 11 (suite) — donjon éclairé, cellier, trappe (reprise)
- **Épée = lumière confirmée en jeu** : à `$1F` (donjon Elvenking), plus de
  `IT IS DARK.` (vs séance 9). Checkpoints : `dungeon_sword.bin` ($1F),
  `cellar_sword.bin` ($20), `forestriver.bin`.
- **Route rejouable** (depuis `sav/sword.bin`, $07 ; `pad≈20` requis pour
  la capture autour du warg) :
  `S S SE E E E E NE` → `$18` (porte Mirkwood, **warg vicieux**) → `E`
  → `$19` « bewitched gloomy place » → `E` → capture → téléport `$1F`.
  Puis `LOOK` (déclenche « Someone opens the red door. ») → `SW` → `$20`.
  Au cellier : `OPEN TRAP DOOR` → `DOWN` → « You are at Forestriver ».
- **Donjon `$1F`** : porte rouge verrouillée (cond `$08`, clé rouge du
  butler `$42`). Mouvements bloqués hors fenêtre porte rouge. `LOOK`+`SW`
  ouvre la fenêtre.
- **Cellier `$20`** (pas d'éjection ici, actions multiples) : `OPEN BARREL`
  (montre le vin), `BREAK BARREL` (« a barrel is broken »), `DRINK WINE`
  (ivre + capturé → `$1F`), `OPEN TRAP DOOR`, `DOWN`→ Forestriver.
  `ENTER BARREL` refusé.
- **À trancher** : `forestriver.bin` (ploc `$01`) rebondit au hall au tick
  suivant (`LOOK` ultérieur = hall au coffre). Forestriver réel ou artefact ?
- **Prochaines cibles** : Forestriver/Lac (évasion en tonneau : vider un
  tonneau puis « entrer »), Montagne `$29`, dragon `$41`. Attention : la
  couverture memmap reste ~85/290 var ; progresser en jeu (nouveaux lieux)
  est ce qui fera monter la couverture.

### État toolchain (fin séance 11)
`check_memmap.py` exit 0 (RÉSULTAT: PROPRE), `check_disasm.py` PROPRE
(131 routines, 51 ZP), `rebuild.py` byte-identique, git clean. Aucun
process résiduel. Derniers commits : `aecd3d5`, `feb8924`.

### Séance 12 — l'Anneau (reprise)
- **Sortie du donjon elfe = Anneau obligatoire.** `DOWN` cellier et `SWIM`
  → `$21` Forestriver → mort (courant/portcullis) ; route terrestre
  `$18→$2E→$02→$03→$2D` → « waterfall » → mort (araignée). Séquence guide :
  `WEAR RING` continu → `WAIT` (butler ouvre/boit un tonneau) →
  `CLIMB INTO BARREL` → `WAIT` → **Long Lake `$23`**.
- États : `$0C` trappe (`+7` `$80`/`$A0`), `$2A` rivière (`+7=$86`),
  `$27` cond `$21`E→`$22`.
- **Prochaine étape : obtenir l'Anneau** (caverne gobelins / Gollum `$44`,
  arg `$10`). Puis araignées → bateau → palais elfe → tonneau → Lac →
  Montagne `$29` → dragon `$41`.
- Checkpoints : `sav/sword_rope.bin` (map, large key, sword, rope @ `$07`),
  `sav/forestriver17.bin` (`$17`). Toolchain PROPRE, git commit à suivre.

### Séance 12 (suite) — repaire gobelin / Anneau (reprise)
- Route : `sav/sword_rope.bin` ($07) → `S S SE E E N` → **chute crack
  « the small insignificant crack »** → `$0D` **goblins dungeon** (sand,
  goblins door N, window W). Checkpoints `sav/crack.bin`,
  `sav/goblin_dungeon.bin`.
- Donjon gobelin : `DIG SAND` → trap door ; `BREAK TRAP DOOR` long/optionnel ;
  `OPEN WINDOW` = « cannot reach » (sortie = coopération PNJ Thorin,
  syntaxe SAY à trancher). Exits N/W cond (`$11`/`$1B`) bloquées sur place
  (goblins vous gardent).
- **Objectif immédiat** : trouver **Gollum `$44`** (arg `$10`, caverne/
  lac souterrain `$11`/`$10`) → énigme → **Anneau** → `WEAR RING` pour
  l'évasion elfique (barrel escape → Lac `$23`), puis route Montagne
  `$29`/dragon `$41`.
- Toolchain PROPRE ; checkpoints sauvés. Dernier commit `ad2a997`.

### Séance 12 (fin) — donjon gobelin (reprise/blocker)
- **`BREAK TRAP DOOR WITH SWORD`** (il faut l'épée !) → « The door is
  broken. » → **goblins cache** → **small curious key** prise par
  **Thorin** (autonome). Checkpoint `sav/goblin_key.bin`.
- **Blockers** : (1) sortie gobelin = ordre au PNJ `SAY TO THORIN "..."`,
  mais le harnais casse sur le `"` (echo_ok=False) → à investiguer
  (rendu 0x22 / touche quote Oric) ; (2) solver : aucune évasion.
- Indice jeu : `SAY HELP` → « A WINDOW SHOULD BE NO OBSTACLE TO A THIEF
  WITH FRIENDS. »
- **Rappel objectif** : Anneau (Gollum `$44`) → évasion elfique (barrel,
  WEAR RING) → Lac `$23` → Montagne `$29` → dragon `$41`.
- Docs `aventure.md` séance 12 (+suites). Toolchain PROPRE. Commits à
  jour.

### Séance 12 (suite 3) — CRITIQUE : ordres PNJ `SAY TO X "..."` (reprise)
- **`SAY TO THORIN "<ORDRE>"` fonctionne** (guillemets doubles, fermants
  inclus). Prouvé : `"CARRY ME"` (Thorin carry ies you), `"OPEN WINDOW"`,
  `"WEST"`. **Toujours lire `run_one()['full']`/`['blob']`, pas `['text']`**
  (segmentation cassée sur le `.` inséré par le jeu après la commande ;
  `echo_ok=False` trompeur).
- **Évasion gobelin** : `SAY TO THORIN "CARRY ME"` `"OPEN WINDOW"` `"WEST"`
  → `$12`→`SW`→`$10`→…→`$11` lac/Gollum. Checkpoints `sav/goblin_escaped.bin`,
  `sav/lake.bin`.
- **Gollum errant** (état `$44`, `eloc` mouvant) ; riddle `act_v14_14`.
  Anneau introuvable (lac/cache = key). Cellier : Thorin absent ;
  `KILL BUTLER WITH SWORD` = « almost kills » (1 coup insuffisant).
- **Prochain** : obtenir l'Anneau (trouver Gollum au bon lieu / gagner le
  riddle) OU 2e coup au butler ; puis guide complet (bateau/araignées/
  palais/tonneau/Lac `$23`/Montagne `$29`/dragon `$41`).
- Toolchain PROPRE ; commits à jour.

### Séance 12 (suite 4) — Anneau pris (reprise)
- **Anneau = état `$10`** = « the valuable golden ring », au lieu `$3D`.
  Chemin `sav/lake.bin`→`N`($37)→`SW`($3D)→`GET RING`. Checkpoint
  **`sav/ring.bin`** (inventaire : map, large key, sword, golden ring,
  rope). `STATE_IDENTITY[0x10]="ring"` ajouté ; `check_memmap` PROPRE.
- Famille clés `tpl=$CB` : `$02`/`$04`/`$0F` ; `$0F`=clé rouge (butler).
- **Prochain** : `WEAR RING` puis guide complet vers le Lac/Montagne.
