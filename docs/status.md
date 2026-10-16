# Session — exploration bloc 4 (The Hobbit, Oric) : ÉTAT PROPRE

## État

- `disasm/block4.asm` fiabilisé : **16 890 o de code**, 99 sites
  `JSR $440D` (115 pointeurs inline `$440D`/`$5B24`), **0 conflit**,
   `scripts/disasm_check.py` → **RÉSULTAT: PROPRE (exit 0, sections A–H)**.
   Round-trip ca65 prouvé (byte-identique, `scripts/disasm_rebuild.py`). Arbre
   propre, tout commité.
- Méthode : descente récursive (`$2C00`, `$2C35`, 16 vecteurs) + point fixe
  (seeds r2 validés + 77 `MANUAL_ENTRIES` dont 16 vecteurs + 61 orphelins
  dispatch-indirect : 30 actions `L7014`/`L7143` + voisines règle D + token
  `$456F` + stubs d'armement `$65A5`/`$70B5` (en zones données, trahis par
  scan binaire des `STA $2Bxx`) ; `SEED_EXCLUDE={0x6DCE}`).
- Routines documentées via `ROUTINE_DOCS` dans `scripts/disasm.py`
  (**124** : socle + 33 actions + 27 moteur de messages + 20 événements
  `evt_*` (`evt_tick`/`evt_fire`, stubs `evt_armeN`, `evt_lookup`…) + 10
  moteur vectoriel (`drawing`/`vec_line`/`vec_fill`/`vec_pos`/`vec_skip`/
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

- `scripts/sim_pack.py` : assemble `harness/shim.s` (`$C000`, zone "ROM" —
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
  (tables scheduler) — `scripts/sim_mems.py` (diff par trame).
- `scripts/sim_frames.py` : rend les écrans hires en texte (charset
  ROM, grille 8 px, bit5-gauche ; n'affiche que les lignes non vides).
- Recette input : `printf '\rLOOK\r' | sim65 -x 150000000 build/sim/hobbit.sim
  > frames.bin` (CR=`$0D` ; `\r` initial = touche du tourne-page d'intro),
  puis `sim_frames.py frames.bin` (OCR hires → texte).
- **Mode rapide** (`sim_pack.py --fast` → `build/sim/hobbit_fast.sim`,
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
- **Parser documenté** (statique) : éditeur de ligne `read_line` `$2DEA`,
  lexeur `tokenize` `$2ED5` + matcher dictionnaire, grammaire `parse_cmd`
  `$3111` dispatchant sur la **classe du mot** via la table `$315A`. Classes
  décodées en lisant les 600 entrées du bloc 2 : `$00` adverbe, `$20`
  direction, `$30` verbe, `$40` GO/RUN, `$50` nom, `$60` adjectif, `$70`
  préposition, `$80` article, `$90` mot-clé spécial, `$A0` AND/virgule,
  `$B0` point/THEN (= fin, ajouté par l'éditeur), `$D0` ignoré (vocabulaire
  messages). Détail : `docs/block4-analysis.md` §« Parser AnimTalk » ; noms
  et commentaires dans `disasm/block4.asm` (`ROUTINE_DOCS`/`ROUTINE_NOTES`/
  `INLINE_COMMENTS`).

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
   mutation + message). `L7014` : 00 `$60BF` **combat** (dégâts `+10` sur
   `(bloc)+$05`, débordement négatif ⇒ msg `$1525` "KILLED") ; 01 `$60ED`
   **combat/riposte** (dégâts `+$05` vs seuil `+$06`, pose flag `+$07` bit3) ;
   02 `$61C9`/03 `$6222`
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
  `$6FAC` (35 entrées) ; SAVE = 4 blocs (`save_block` `$3DAA` via
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
  `scripts/sim_mems.py` diff par trame) ; frappes d'écho = seuls
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
  ou exécutés au tunnel. `sim_tickdiff SIM CMDFILE` : sim65 hardcodé
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
- **Tick sim_tickdiff vs tick monde** : 1 ligne = 1 tick (lignes vides
  incluses, no-op sans tour) ; 1 commande acceptée = 1 `world_tick`
  (`entity_tick`+`evt_tick`). Règle : 0 delta = pas de tour (rejet
  avant `world_tick`), >0 = un tour. PNJ strictement tour-par-tour
  (jamais de mouvement sur lignes vides ; déterministe vérifié).

## Prochaine étape (snapshots : FAIT, 0-delta prouvé)

**Bascule snapshots implémentée** (`harness/snap.s`, `sim_pack
--snapshot NOM`, `sim_tickdiff @@SNAP`, `sim_tickdb.py snaps/snap-show/
snap-diff/snap-verify/snap-init`) : `vec_02/03/04`
(`$2C0B/$2C0E/$2C11`) → `snap_load`/`snap_save`/`s_clc`, sans état
(index déduit de src/dst : `$00BE/$1B1A/$28CC/$211A`), prompts
`vec_05/06` conservés (1 touche sacrificielle chacun). Stockage double :
`sav/NOM.bin` (`"SNAP"`+3623) + table `snapshots` (run,tick,ploc…,
`data` BLOB). Images par défaut byte-identiques, sim_tickdiff régressé
(`diverge f37c f37c_new` vide).
**Validation** : `sna` (Rivendell `$09`, SAVE tick19, salissure
`EAST`→`$0A`) → `pack --snapshot revise` → `snb` (reboot, LOAD :
`$09` restauré, `INVENTORY`/`EAST` vivants) → **0-delta byte-exact**
(3623 o post-LOAD == SAVE, run direct pacé, `-x` court).
**Pièges trouvés** : `sim_tickdiff` envoyait `sav/` dans `build/sav/`
(dépilage chemin) ; `VALUES` à 10 pour 9 colonnes (prepare silencieux) ;
run direct non pacé : `pause_key` mange les lignes (¿`LOAD` jamais
exécuté) ; **spin EOF-idle pollue la mémoire** (~32 o sur 2G cycles —
comparer à `-x` court ou runs sim_tickdiff, jamais après idle long).
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
**B1** (`harness/tape.s` + `sim_pack.py` + `tape_save.py` +
`tape_diff.py`, 6 vecteurs `$0405`–`$0414` ; `$0417` = loader jeu
conservé, pas un vecteur) : SAVE écrit 4 blocs valides (headers+EOR
vérifiés) ; bugs stub trouvés+fixés (`MARK_1` sans `\n`, header 9 o
pas 10, `rd_byte` qui retombait dans son entrée, `ST_OP` qui écrivait
à côté du buffer). Reste : VERIFY reporte une erreur et LOAD même
session échoue (buffer relu différent ?) — diagnostic en pause,
priorité à l'observation via sim_tickdiff (pas de SAVE/LOAD).
**sim_tickdiff** (`scripts/sim_tickdiff.c` → `build/sim/sim_tickdiff`, + shim
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
Résultats → `memory-map.md` §7 (cluster `+$xxx` = `eloc`,
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
Deux images : `hobbit_fast.sim` (texte seul, sim_tickdiff) +
`hires.sim` (`--fast --hires`, OCR) ; cmdfile sim_tickdiff en `\n`
(1re ligne = touche boot), run brut en `\r` (`tr`).
**DB SQLite** `build/sim/hobbit.db` (gitignorée) via
`scripts/sim_tickdb.py` (`import` + `traj`/`touches`/`diverge`/
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
   du renderer d'illustrations → `drawing` `$77D4`).
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
  (`hobbit.db` sim_tickdiff + `solver.db`/`SOLVER_DB` BFS) → preuves par slot.
  `report` (couverture + var nommés), `slots [--virgin]`, `addr`, `sources`,
  `xref` (réfs littérales de `block4.asm`), `gen [--write]` (annexe du doc
  entre marqueurs AUTO-COUVERTURE).
- **Garde-fou** `scripts/memmap_check.py` → `RÉSULTAT: PROPRE` (sections
  A–F ; `disasm_check.py` reste PROPRE).
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
  gandalf/dragon/butler/gollum/troll_*`), champs `type/carrier/noun/adj1/
  adj2/eloc/falls/lock`, 13 tables INDIR, 10 events `$2B12`, 17 entités `$2B45`,
  79 records `$2070` (via image). `annotate(base,off)` → slots (multi-slot).
- `scripts/memmap.py` : `report` (couverture + var nommés), `slots
  [--virgin]`, `addr <base> <off>` (annotation + preuves = commandes/valeurs),
  `sources`, `xref [base [off]]` (réfs littérales `block4.asm`), `gen
  [--write]` (annexe between markers dans `memory-map.md`).
  Env `SOLVER_DB=` cible une base de run.
- `scripts/memmap_check.py` : PROPRE (A–F ; noms/contiguïté/docs/genres,
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
- **Corrige** l'ancien « pas de lampe au jeu » (séance 9 `journal.md`).
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
(visiter les 55 lieux non vus, cf. `docs/map.md`), identités clés
restantes, `ZP.exploc/once`.

Commandes utiles :
```
.venv/bin/python scripts/memmap.py report           # couverture
.venv/bin/python scripts/memmap.py slots --virgin   # cibles
.venv/bin/python scripts/memmap.py xref 1B63        # qui touche l'état $01
.venv/bin/python scripts/memmap_check.py            # PROPRE
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
  `$04`=`key` ; `docs/journal.md` séance 11 ; §2 `memory-map.md`.
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
`memmap_check.py` exit 0 (RÉSULTAT: PROPRE), `disasm_check.py` PROPRE
(131 routines, 51 ZP), `disasm_rebuild.py` byte-identique, git clean. Aucun
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
- Docs `journal.md` séance 12 (+suites). Toolchain PROPRE. Commits à
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
  rope). `STATE_IDENTITY[0x10]="ring"` ajouté ; `memmap_check` PROPRE.
- Famille clés `tpl=$CB` : `$02`/`$04`/`$0F` ; `$0F`=clé rouge (butler).
- **Prochain** : `WEAR RING` puis guide complet vers le Lac/Montagne.

### Séance 12 (FINALE) — VICTOIRE 80 % (reprise)
- **Victoire atteinte** : `OPEN CHEST` + `PUT TREASURE IN CHEST` au tunnel
  `$01` → « …master adventurer!!! You have mastered 80.0% ». Checkpoint
  **`sav/win.bin`**.
- Parcours complet (10 étapes) consigné dans `docs/journal.md` séance 12
  finale. Mécaniques : `SAY TO X "..."`, Anneau = état `$10` @ `$3D`
  (`sav/ring.bin`), tonneau (`sav/barrel_ride.bin`), Bard
  (`sav/strongriver.bin`→`sav/dragon_hall.bin`), araignées WAIT×2.
- **Reste côté projet** : ingérer les nouveaux états dans la DB
  (`sim_tickdiff`/`solver`) pour faire monter la **couverture memmap**
  (rapport inchangé à 140/3623 o car les `run_one` ne sont pas enregistrés).
- Toolchain PROPRE ; commits à jour.

### Séance 12 (couverture) — ingestion solver après victoire
- BFS solver depuis les checkpoints `ring`/`lake`/`dragon`/`laketown`/
  `goblin_escaped` (DB `build/sim/win.db`, fusionnée dans `solver.db` par
  dédup de hash ; backup `solver_pre_win.db`).
- Couverture passée **140 → 184/3623 octets (3.9 → 5.1 %)** ; `records`
  **18 → 41/79 var**. Annexe AUTO-COUVERTURE régénérée
  (`memmap.py gen --write`). `memmap_check` PROPRE.

## SYNTHÈSE DE REPRISE (fin séance 12) — pour contexte neuf
**État** : le jeu est **terminable de bout en bout** ; **victoire atteinte
(80 %)** — parcours complet en 10 étapes dans `docs/journal.md` séance 12
finale (référence unique). Les addenda « blockers » ci-dessus (guillemets,
Anneau introuvable, couverture inchangée) sont **RÉSOLUS** :
- **Ordres PNJ** : `SAY TO <PERS> "<ORDRE>"` (guillemets doubles). ⚠️ Lire
  `run_one()['full']`/`['blob']`, jamais `['text']` (segmentation cassée
  sur le `.` post-commande ; `echo_ok=False` trompeur).
- **Anneau** = état `$10` (`$1CC4`) au lieu `$3D` ; `GET RING`.
- **Évasion elfique** = tonneau via Anneau (`sav/barrel_ride.bin`).
- **Dragon** = `SAY TO BARD "SHOOT DRAGON"` ; **araignées** = `WAIT`×2.
- **Lieux** : **78/78 records valides visités** (79 slots `$01`–`$4F`, `$2F`
  nul ; graphe parcouru ; 10 conditionnels `08 14 15 1A 1B 1C 1D 32 42 43`
  atteints via patch debug de `player.eloc` ; `$42` rendu via `PATCH:42`,
  `ploc` forcé à `$1F` par l'event *wood elf*). Carte : `docs/map.md`.
- **Lieu autoritaire** lu par LOOK = **`player.eloc`** (`$1B2A`, bloc `$00`
  `+$10`) ; `ploc` (`$C8`) = **miroir** (patté seul, il est re-dérivé).
- **Couverture memmap** : **237/3623 o (6.5 %)** ; `records` **78/79**
  (var 66/79), `etats` 99 var — fusion `build/sim/{hobbit,solver}.db`.

**Toolchain** : `disasm_check`/`memmap_check` PROPRE, `rebuild` byte-identique,
git clean. Derniers commits : `42f6d3a` (exploration lieux), `eb95415`
(lieux 79/79 + eloc), `1444777` (partition blocs), `6a74942` (ZP tblA/tblB),
`f64363d`, `48fb64d` (nommage).
Checkpoints utiles : `sav/win.bin`, `ring.bin`, `lake.bin`, `goblin_escaped.bin`,
`dragon_hall.bin`, `treasure.bin`.

**Pistes mapping (objectif projet)** — zones/états à couvrir :
1. ~~**Gollum `$44`** errant + riddle `act_v14_14`~~ **FAIT** : déclenché
   dynamiquement depuis `sav/ring.bin` à `$3D` — Gollum dit « my precious »
   (`$16C8`) / « pockets ? » (`$16B9`), **reprend l'Anneau**, récite l'énigme
   « It cannot be seen… » ; capture au lac (`$11`) → `$0D`. Détails
   `docs/journal.md` séance 12 (Gollum), checkpoint `sav/gollum_riddle.bin`.
2. ~~Gobelins `$10`–`$13`, `$39`–`$41` ; hauts nord-est `$44`–`$4F`~~ **FAIT** :
   tous visités (cf. `map.md`). Conditions `$07`/`$09`/`$0A` non levées
   en jeu (accès debug uniquement).
3. Événements différés `$2B12` (10 entrées), `$28E6`/`$28CC` init.
4. Portes à événement : magique elfes `$0D+7` bit5 (`$1D26`), trou Montagne
   `$0B+7` bit7 (`$1C7B`), porte rouge `$08`.
5. Slots vierges : `memmap.py slots --virgin` ; ingérer via solver/sim_tickdiff.
6. **Nommage des champs de bloc** — **FAIT** : modèle corrigé en partition
   par ordre d'adresse (`memmap_defs.state_owner`, 32 réfs vérifiées) ;
   champs `+5`(hp)/`+6`(tough)/`+7`(flags)/`+A`(altptr) encodés. `etats` non
   nommés **60 → 6** ; ZP `tblA`/`tblB`. Restent **10** offsets : ZP
   `$C3/$C4/$CF-$D5` + etats `+$0C/+$0D`. Cible : `memmap.py unnamed`.

### Séance 12 (couverture 2) — chaîne canonique + batch BFS
- **Run `canon`** injecté dans `hobbit.db` : les 20 checkpoints du parcours
  dans l'ordre, diffs net par diff (`solver_db.diff_blobs`) → table
  `deltas`. 724 deltas. (Méthode : boucle Python, cf. ci-dessous.)
- **42 seeds BFS** (tous checkpoints `sav/*.bin`, `--goal coverage
  --depth 6 --budget ~200`, DB `build/sim/win.db` puis fusion dédup dans
  `solver.db`) : ~240 nœuds.
- Couverture **184 → 222/3623 o (5.1 → 6.1 %)** ; `records` **41 → 52/79
  var**. Annexe régénérée ; `memmap_check` PROPRE.
- **Limite** : une seule trajectoire ne mute qu'une fraction des zones ;
  le reste exige l'exploration de **branches** (combat/morts, tous les
  lieux, riddle Gollum, PNJ). ROI désormais dans le BFS longue haleine,
  pas dans les seeds alignés sur le parcours.
- **Reproductibilité** : `sav/*.bin`, `build/sim/*.db` et `*.sim` sont
  gitignorés ; le parcours canonique n'est **pas scripté** (joué
  interactivement). Piste : committer les checkpoints (≈3.5 Ko × ~20) et/ou
  un `routes/canon.txt` rejouable.

Repro chaîne (extrait) : `solver_db.diff_blobs(sav/A.bin, sav/B.bin)` →
`INSERT INTO deltas(run,n,base,off,avant,apres)` sous un run `canon`
(`sim_tickdb.connect()`).

### Séance 12 (nommage) — ZP `score`/`recptr`
- `memmap_defs.ZP_NAMES` : `$CC`/`$CD` = **score** (points ; lu par SCORE
  `$3CD4` ; 75/100/550 observés, remis à 0 après victoire), `$CA`/`$CB` =
  **recptr** (pointeur de record de lieu sauvegardé, `$21`–`$26`).
- Confirmé statiquement : **`$1E4B` = `$44.$10` = `gollum.eloc`** (`act_v14_12`/
  `act_v14_14` le comparent à `ploc`) → valide `+$10`=eloc.
- Nouvelle commande **`memmap.py unnamed`** = offsets couverts sans slot nommé
  (workflow de nommage). ZP var couvertes 6→10/11 ; `memmap_check` PROPRE.
- Restent non nommés : ZP `$BF`/`$C0`/`$C1`/`$CF`–`$D5` ; champs de bloc
  `+5/+6/+7/+0A/+0B` (blocks se chevauchant → propriétaire ambigu).

### Séance 12 (modèle blocs) — partition par adresse (fin des chevauchements)
- **Correction de modèle** : les blocs d'état ne se chevauchent PAS ; les
  bases sont non monotones en **ordre de clé** mais forment une **partition
  contiguë en ordre d'adresse** (chaque octet → clé de base la plus grande
  `≤` adresse, jusqu'à la base suivante ; blocs `$12`–`$24` o). Vérifié sur
  les **32 réfs littérales** de `block4.asm` (0 ambiguïté) →
  `memmap_defs.state_owner` ; `annotate` rend désormais **un** slot par octet.
- **Champs encodés** (`STATE_FIELD`) : `+$05`=hp (combat, `act_p14_00` ;
  `+10`/coup, bit7⇒tué, ×2 transfo `$6F1B`), `+$06`=tough (seuil,
  `act_p14_01`), `+$07`=flags (spéciaux portes prioritaires), `+$0A`/`+$0B`=
  `altptr` (ex. `$098F` posé par `$6F1B`).
- **Effet** : offsets couverts non nommés `etats` **60 → 6** (reste
  `+$0C`/`+$0D`, paire RAZ par `code_5AF0`, sens ouvert) ; var couvertes
  `etats` **45 → 99**. Restent non nommés : ZP `$BF/$C0/$C1/$CF-$D5` (7),
  scripts `code$299D/$2A7B/$2A7C` (3).
- `memmap_check` PROPRE ; annexe régénérée ; doc §2 réécrite.

### Séance 12 (nommage ZP 2)
- ZP nommés : `$BF`/`$C0` = **tblA** (pointeur table action/patch `$7116`,
  pas 4 ; `$BF`=`$16`+`rand*4`), `$C1`/`$C2` = **tblB** (pointeur table
  errance/desc `$7126`, pas 6 ; utilisé par « go…from…to » `$8586`). ZP var
  couvertes **13/15**. Restent : `$C3/$C4`, `$CF`–`$D5` (7 au total avec
  `$0C/$0D` etats). `memmap_check` PROPRE.

### Séance 12 (tous les lieux) — 79/79 visités
- Exploration dirigée + `solver --route --record` : **48 → 78/79** lieux
  (ploc) ; NE complet, cavernes gobelines, est, montagne. Reste `$42` dont
  `ploc` diverge (événement force `$1F`) mais le lieu est rendu.
- **Découverte** : le lieu **autoritaire** lu par LOOK = **`player.eloc`**
  (`$1B2A` = bloc `$00` `+$10`) ; `ploc` (`$C8`) n'est qu'un **miroir**. Les
  10 lieux conditionnels (`08 14 15 1A 1B 1C 1D 32 42 43`, gated `$07/$09/$0A`)
  ont été visités/rendus par **patch mémoire debug** de `$1B2A` (offset 44 du
  blob) + LOOK, puis enregistrés (nœuds `PATCH:xx` dans `solver.db`).
- **Couverture** : `records` 71 → **78/79** (var nommées 59 → 66) ; total
  **237/3623 (6.5 %)**. `memmap_check` PROPRE.
- Repro patch : `b=bytearray(sav/ring.bin); b[44]=<ploc>; run_one(b,'LOOK')`.
- *(2026-10-10) Cohérence `solver.db`* : 4 lieux (`$0E $47 $49 $4A`) rejoués
  en **vrai jeu** depuis `sav/ring_surface.bin` (`$0A`, `routes/ne_gaps.txt`),
  nœuds 300/304/305/306 ; `$42` reste *rendu seul* (capture *wood elf* →
  `snap-incomplet`). Comptage rectifié : **78/78 records valides** (79 slots
  `$01`–`$4F`, `$2F` nul), pas « 79/79 ».

### Reprise — élucidation entités `$2B45` / événements `$2B12` / état `+0` (commit `a01cfa0`)

Note pour contexte neuf (détails : `docs/memory-map.md` §2/§3c/§3d,
`docs/block4-analysis.md` § AnimAction/§ événements, `scripts/disasm.py`
`ROUTINE_DOCS`/`NOTES`).

- **Entités `$2B45`** (`[id,nmax,PC,base,reply]`) : `n` (`+1`) → **`nmax`** =
  index max (0-based) de la table `base` = nb d'entrées − 1 (clamp
  `script_indir`/`script_rand` : `min(op,nmax)`) ; `s6` (`+6`) → **`reply`** =
  poids de réplique, lu **au seul site** `action_talk_to` (`$5F81`, orphelin wid
  `$35` de la table `$6FAC`) qui fait dire `<id>SAY 'NO '` (`$15BE`, énigme) ;
  `0` = muet. Ni `nmax` ni `reply` ne sont jamais écrits (DB : deltas `$28CC`
  seulement sur `+0/+2/+3`). **Fix annexe** : `INDIR_TABLES[$2943]` 15 → 25 o
  (8 entrées, pas 5 — les 3 dernières étaient étiquetées « code » à tort).
- **Événements `$2B12`** : `actA` **n'est pas** une voie morte — il tire **une
  fois, à l'échéance de `cpt`**, via la garde `L4E58` (RAZ par `world_tick`,
  reposée par `evt_act0`) ; `actB` tant que `cond>=cpt`. Prouvé harnais : `e0.cpt`
  (`$2B13`) alterne `0↔1` (armé à 2) et `evt_act0` s'exécute (run `f9a` t65,
  `$1D94` `$21`→`$20`). 3 handlers récupérés en zones données : `evt_arme0`
  `$64E2` (tonneau état `$13` à Forestriver `$21` → `e0.cpt:=2`), `evt_act0`
  `$688D` (berge du Long Lake `$170C`), `evt_hole` `$6DBB` (trou Montagne).
  `evt_lookup` `$5DE2` appelé par `act_probe_event` `$5DCB` (`obj==0`).
- **État `+0`** : **corrigé** en « N lieux » (voir entrée plus bas) — `+0` =
  **nombre de lieux N** (et non une classe) ; les N lieux suivent en `+$10..`.
  `N`=`$01` = objet à un seul lieu (seul cas que `get_object_location` `$57BB`,
  `is_dark`, `holder_scan`, arme `act_p14_00/03` résolvent) ; `N`≥`2` =
  multi-lieux (portes/eau/toile) dont la liste est gérée par `L5FFA`.

**Toolchain** : `disasm_check` PROPRE (**441** routines), `memmap_check` PROPRE,
`disasm_rebuild --all` byte-identique (36274 o). Commit `a01cfa0`, arbre propre.

**Pistes ouvertes** : déclencheurs des entrants dormants `$2B61/$2B76/$2B7D` ;
compteur de tête `$2AD0` ; triggers gameplay des events via `$709F` ; B1
cassette VERIFY/LOAD ; couverture memmap (rejouer les branches en jeu).

## Reprise — nommage via Wilderland (moteur ZX de référence)

Ajout local `external_ressources/Wilderland/` (env. ZX Spectrum instrumenté du même jeu, CH /
Valerio Messina) : sert de **dictionnaire sémantique** (adresses ZX ≠ Oric).
Cross-check sur `data/hobbit.bin` :

- **Attributs `+$07`** (8 bits) confirmés identiques à `WL.h ATTR_*` :
  `b0` verrou (`rock_door` `$81`), `b1` fluide (`wine`/`water` `$82`), `b2`
  plein + `b4` éclaire (`sword`/`torch` `$94`), `b3` cassé/mort, `b5` ouvert,
  `b6` animal, `b7` visible (PNJ `$E0`). Helpers Oric `obj_flag1/20/48_test`.
  Corrige l'ancien « `bit1`=combat » (faux : `bit1`=fluide).
- **Champs nom** : `+$08`/`+$09`=**nom** (`noun`, `name_from_record $5A9D`),
  `+$0A`/`+$0B`=**adjectif 1**, `+$0C`/`+$0D`=**adjectif 2** (décodés mot à
  mot : `$0E`=`SHORT STRONG SWORD`, `$10`=`VALUABLE GOLDEN RING`, …). Renomme
  l'ancien `tpl`/`altptr`/`descp` (noms composés, réutilisation runtime gardée).
- **`+$00` = N, nombre de lieux** (et non une « classe ») : les `N` lieux suivent
  en `+$10..` (balayés par `L5FFA`) ; `N`=`$01` = objet à un seul lieu, `N`≥`2` =
  multi-lieux (portes, eau `$17` en **8** lieux, toile, rivière). `get_object_location`
  `$57BB` ne résout que `N`=`$01` (sinon `$FF` = « nulle part »).
- **`+$02`=volume, `+$03`=masse, `+$04`(bits0-2)=classe/contenant** : ma lecture
  initiale (« divergence ») était **fausse** ; `act_p14_13` (« IS TOO FULL ») lit
  `+$02`, `obj_count_add $5C2B` lit `+$03` (l'`adc` va dans un temporaire, pas
  dans l'objet).
- **Confirmation externe** : `npc_stats.xlsx` (Strength/Mass/Volume des PNJ :
  Gandalf `15/60/70`, Thorin `1D/50/68`, Trolls `90/90/A0`, Gollum `05/05/20`…,
  14/16 exacts) → le layout objet Oric **colle à Wilderland sur `+00`..`+10`**.
- **Classes de mots** : `dict_v12.txt` (NOUN/VERB/MOVE_DIR/GO_RUN/IN_INTO…)
  corrobore nos 12 classes du parser ; la table de dispatch des verbes
  **`$6FAC`–`$7014`** (35 entrées `wid`→handler, `$FF` en `$7015`) est
  documentée dans `block4-analysis.md`, croisée avec la liste officielle du
  manuel (10 mouvements, 11 verbes spéciaux, ~30 verbes d'action, prépositions).
- `$C5 obj` = **acteur courant** (= `L_ACTING_ANIMAL` ZX).

**Toolchain** : `disasm_check --block block4` PROPRE, `memmap_check` PROPRE,
`disasm_rebuild --block block4` byte-identique (20097 o).

### Références externes (documentation d'origine)

Sous `external_ressources/` (gitignoré), deux ensembles utiles pour documenter
le code :

- `Wilderland/` (CH, V. Messina) — émulateur ZX du *même* jeu, affiche l'état
  des objets/PNJ ; source des **noms de champs** objet (`+00`..`+10`) et du
  dictionnaire (`dict_v12.txt`, `rooms_v12.txt`).
- `HobbitOSX/` (S. Craig, « hommage » multi-plateformes) — contient :
  - `BDCH_2014_Megler_The_Hobbit_v1.1.pdf` : case history de V. Megler
    (architecture d'origine : 2 moitiés moteur/parser « Inglish », **3 bases**
    location/objet/personnage, physique objet poids/taille/contenants, VM
    d'actions des PNJ avec branchements/aléatoire, « time passes », joueur = un
    personnage, graine aléatoire, dico 5 bits + 3 bits de service) ;
  - `instructions.rtf` : manuel — « lois de la physique » + **liste officielle**
    du vocabulaire (mouvements/verbes/prépositions/adverbes) ;
  - `npc_stats.xlsx` : Strength/Mass/Volume de chaque PNJ (confirme `+02`/`+03`/`+05`) ;
  - images multi-plateformes (dont **BBC 6502** : piste pour croiser les ports 6502).

Lecture du PDF : le modèle ne lit pas les PDF en pièce jointe ; le texte est
extractible en stdlib (`zlib` sur les flux `FlateDecode` + opérateurs `Tj`).

### Désassemblage ZX de référence (`pobtastic/hobbit`)

Sous `external_ressources/hobbit/` (gitignoré) : désassemblage **SkoolKit**
complet de la version ZX Spectrum du même jeu (Paul Maddern, `pobtastic/hobbit`,
2021-2023), **217 labels** nommés. Fichiers : `sources/hobbit.skool` (code Z80
annoté), `sources/hobbit.py` + `utils/hobbitmessages.py`/`hobbitimages.py`
(décodeurs dico/messages/graphismes). Même moteur que l'Oric (adresses ≠) :
confirme la fiche objet, la table d'actions `$C730` (mêmes IDs), les attributs
`+$07`, et fournit des **noms canoniques** (`LocateObject`, `IndexIdTable`,
`ContainerLit`, `CheckValidAction`, `TriggerAction`, `Drawing*`, `Event*`,
`ScriptGandalf_*`).

Renommages adoptés (nom ZX → `snake_case`, notre règle) :

- `locate_object` (`$5331`), `locate_location` (`$530B`),
  `get_object_location` (`$57BB`), `index_id_table`/`index_id_table2`
  (`$5399`/`$5394`), `step3byte_table`/`step3byte_table_next`
  (`$540F`/`$542C`), `print_char` (`$75B4`), `get_key` (`$7353`),
  `wait_for_key` (`$7481`), `save_game` (`$3DD9`), `load_game` (`$3D7F`),
  `tape_verify` (`$71CB`), `drawing` (`$77D4`, flux d'illustration).

Non renommés (pas de correspondance nette) : `act_p14_*` (table d'action Oric à
15 entrées indexées, ≠ `ActionTable` ZX classée par ID), `act_v14_*` (scripts
PNJ par personnage côté ZX), `ch_out`/`ch_put`, `render_text` (≠ `PrintToken`),
les 8 « pointeurs nuls » (= slots de message, pas des routines).

### Handoff — travail en cours (à reprendre)

**État courant** : renommages ZX appliqués dans `scripts/disasm.py` + docs/harness,
listings régénérés. Vérifs vertes : `disasm_check --block block4` PROPRE,
`memmap_check` PROPRE, `disasm_rebuild --all` byte-identique (36274 o).
**Modifs NON commitées** (9 fichiers) : `disasm/block4.{asm,info}`,
`docs/{block4-analysis,memory-map,status}.md`, `harness/{shim,snap}.s`,
`scripts/{disasm,sim_pack}.py`.

**Gisement externe** : `external_ressources/` (gitignoré). Non exploité en majorité.

**Étape 1 — `hobbit/sources/hobbit.ctl` (tables sémantiques). [FAIT]**
Map `#ACTION` lue → noms officiels des `wid` dans `docs/block4-analysis.md`
(§Verbes ordinaires), et **handlers nommés** dans `ROUTINE_DOCS` :
`action_none/look/pickup/take_out_of/dir/drop/enter/run/follow/throw_at/
talk_to/strike/inventory/examine/give/capture/untie/tie/burn/climb_out/shoot`.
Corrige `$0B`→Strike with, `$1C`→Examine, `$1D`→Give To, `$13/$3B`→Take/Carry ;
`$0E`=**Drop** (routine `$5EB7` imprime `EVAPORATE.` = ZX `Action_Putdown`) ;
`$0F/$11`→`act_p14_13` (corps *partagé*) ; `$00`→`entity_tick_init` ; `$2C`→`$61E5`.
6 handlers étaient enfouis en zones données (`$637B $6760 $67CA $67E3 $685E
$686D`) → ajoutés à `MANUAL_ENTRIES` ; + `$66F1` = entrée **[35]** de `L7014`
(attention : **table de mots**, base `$7016`, indexée par `(orec)+1`×2) →
`act_p14_35`. `$5D44` (`action_dir`) : préambule `is_dark` + direction aléatoire
dans le noir, puis `combat_round` ($5D53) qui résout en fait le **déplacement**
(messages « FALL AND HIT YOUR HEAD ») — nom `combat_round` **à revoir**. Vérifié
`disasm_check`/`memmap_check` PROPRE + `rebuild --all` byte-identique.
(NB : `AGENTS.md` §7 « 102 sites $440D » → **108**, à rafraîchir.)

**Étape 2 — `Wilderland/WL.h`/`GlobalVars.h`/`MapCoordinates.h`. [FAIT]**
Ces entêtes sont surtout émulateur/constantes : **pas de table de variables ZP**
(`GlobalVars.h` = SDL/Z80 ; `WL.h` = adresses ZX + macros objet). Aucune ZP
renommée. Apports : `WL.h` `P*_OFF_*` (offsets objet) et `ATTR_*` (attributs) ;
`OBJNR_*` (n° entités `3C`-`4C`) ; `MapCoordinates.h` = carte des `0x50` lieux +
`AnimalInitials`. Reportés dans `scripts/memmap_defs.py` (`STATE_FIELD` renvoie
à `WL.h`, `STATE_IDENTITY` = noms PNJ exacts : nasty/hideous/horrible/mean/
vicious/disgusting goblin, hideous/vicious troll, wood_elf…) et
`docs/memory-map.md`. ZP : noms inchangés (issus du désassemblage + `L_*`).
Non exploité : `WL.c` (98 K, logique carte/menus) et `dict_v12.txt`/`rooms_v12.txt`.

**Étape 3 — reste de `hobbit.skool` (lieux/objets/LocGFX/dico). [FAIT]**
- **Lieux** : nos 79 records `$2070` (`$00-$4F` sauf `$2F`) = **numéro pour
  numéro** les 79 rooms de `Wilderland/rooms_v12.txt` (desc Oric `+8` == desc
  ZX). Table complète (id ↔ nom ZX ↔ desc Oric) ajoutée à
  `docs/block4-analysis.md` §« Records lieux ↔ rooms_v12 ».
- **LocGFX** : clés d'images bloc 3 = **ids de lieux** confirmé (ZX
  `LocGFXTable` `$CC00`). Mapping + noms dans `docs/block4-analysis.md` §Bloc 3
  et `docs/tape-archive.md`. ZX v1.2 = 22 images, Oric v1.0 = 13.
- **Dictionnaire** : notre dico v1.0 (`$0540`) est un **sur-ensemble** du
  `dict_v12.txt` (ZX v1.2) : ~530 mots communs, ~26 ZX-only (`BUTLER DALE LAKE
  LOAD MEAN NARROW NIGHT SAND WALL WARG…`), ~70 Oric-only (mots anglais rares).
  ⚠️ `msg_decode.py words` a ~12 artefacts de frontière (`CBUTLER`, `BDALE`,
  `BFLAKE`… = préfixe 1-2 lettres) → `decode_word_at` à revoir (n'affecte pas le
  décodage des messages).
- **CommonWords** : notre table `$1117` (32 ptr) diffère du ZX `$AD3D`
  (ordre = fréquence chez nous, alphabétique chez ZX ; jeux ≠ : version).
- **Objets** : déjà alignés (`STATE_IDENTITY` = `OBJNR_*`, cf. étape 2).
- **Non exploité** : `Actions`/`TextMessages`/`Script*`/`Event*` nommés ZX (renommage
  de routines Oric par correspondance), `WL.c`, `dict_v12.txt` complet.

**Plus tard (4)** : ports **6502** dans `HobbitOSX/…/BBCDisk`, `Apple2Disk`,
`C64Disk` (v1.00) → extraction + diff pour aligner le code Oric (même CPU).

**Commandes** : `.venv/bin/python scripts/disasm.py` ; `scripts/disasm_check.py
--block block4` ; `scripts/memmap_check.py` ; `scripts/disasm_rebuild.py --all`.
