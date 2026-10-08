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
  packe `/tmp/hobbit.sim` (load `$0400`, reset `$2C00`, SPAddr `$02`).
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
- Recette input : `printf '\rLOOK\r' | sim65 -x 150000000 /tmp/hobbit.sim
  > frames.bin` (CR=`$0D` ; `\r` initial = touche du tourne-page d'intro),
  puis `decode_frames.py frames.bin` (OCR hires → texte).
- **Mode rapide** (`pack_sim.py --fast` → `/tmp/hobbit_fast.sim`,
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
  états `$1A62` (60 clés, trou `$2C-$3B`, `L5331`≠`L530B`, eloc=état+`$10`) ;
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
- Coût rendu illustration sous sim65 ≈ plusieurs centaines de M cycles :
  budgets `-x` généreux (2G pour 2 rendus), préférer les commandes
  texte seul (`WAIT`, `INVENTORY`) pour les sondes. `QUIT` perd l'input
  suivant (rendu) — prévoir la touche sacrificielle aussi.

## Prochaine étape

Moteur de messages, armement `$2B12`, zéro-page, bloc 3, système de
messages du bloc 2, records de lieux (structure + exits étendues) et
scripts `$29xx`, layout records `+0..7` et dispatch SAVE/LOAD décodés
(`docs/block4-analysis.md`). Ensuite : stub cassette B1 (`vec_02/03`
→ shim, round-trip save/load), puis jeu tour-par-tour. Sondes en
attente : bit7 `b0`/`b1`, identité `$3C`, eloc runtime, `$xC`.

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
