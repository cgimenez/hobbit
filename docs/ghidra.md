# Ghidra — miroir et chasse AnimAction (déc. 2025 → sessions MCP)

Ce document consigne le travail réalisé avec Ghidra (GUI + pont MCP) :
import du binaire, miroir des noms du listing, convention inline `+5`,
études AnimTalk / AnimAction, et l'élucidation du mécanisme du slot
dormant `e04` (`PC=$2B0E` → `Gandalf.PC=$2B11` sur GIVE).

Le repo reste la source de vérité (`disasm/`, `scripts/`, `docs/`) :
Ghidra est un oracle externe (projet hors repo), jamais l'inverse.

## 1. Montage

- Ghidra 12.1.4 (MacPorts : `/opt/local/share/java/ghidra-12.1.4/`), projet
  hors repo (ne jamais le créer dans le repo : `.gpr` + `.rep/` non ignorés).
- Import : `data/hobbit.bin`, `Raw Binary`, langage `MOS 6502`,
  `Base address 0x0400` (le bloc `RAM 0400-91B1`, 36274 o, est correct ;
  `image_base` affiché `0000` est trompeur, les segments font foi).
- Entrée posée à `$2C00` (`D` désassembler + `F` créer fonction) :
  `2C00: JMP 0x2C35` saute la table des 16 vecteurs `JMP` `$2C05-$2C34`.
  `Set as Entry` superflu.
- Pont MCP : extension `bethington/ghidra-mcp` (release built pour 12.1.4),
  bridge `bridge-mcp-ghidra` déclaré dans OpenCode
  (`opencode mcp add ghidra-mcp --global -- <chemin absolu>`),
  redémarrage de session pour exposer les outils `ghidra-mcp_*`.

## 2. Import initial : constats

- Auto-analyse seule : 186 fonctions, entry parasite à `$0000`
  (`FUN_0000`, faux positif sur ZP non initialisée — bruit connu).
- Ghidra découpe mieux que la descente récursive le bloc `3172-3AD9`
  (~40 fonctions là où `disasm.py` voit une plage) ; en revanche il rate
  tout le district orphelin dispatch-indirect `~5800-72FC`
  (tables d'actions `L7014`/`L7143`, `JMP ($6A)`) : 0 fonction sur ~60
  plages CODE da65. C'est exactement la valeur de `MANUAL_ENTRIES`.
- Thunks de vecteurs résolus correctement
  (`2C26→get_key $7353`, `2C32→main $7779`…).

## 3. Miroir des noms (tout via MCP, programme sauvegardé à chaque étape)

- 20 renommages initiaux (`autorun`, `world_tick $4E59`,
  `entity_tick $4ED5`, `print_msg $440D`, `parse_cmd $3111`…).
- 24 routines orphelines créées + renommées (handlers `act_*`, `evt_arme*`,
  `tape_*`, `drawing $77D4`, `load_game $3D7F` / `save_game $3DD9`…).
- 80 seeds `MANUAL_ENTRIES` créés (vecteurs `vec_01-11`, `act_v14_*`,
  `act_p14_*`, `evt_*`, ` tape_tramp`, `evt_tip`…) + 14 thunks existants
  renommés (`keyin`, `print_cr`, `putchar`, `main`…).
- 120 chunks anonymes `code_*` créés (couverture totale des 176 plages
  CODE da65 ; 5 chevauchements refusés proprement puis résorbés par
  propagation — total final **529–535 fonctions**).
- 228 renommages issus de `ROUTINE_DOCS` (parser, moteur de déplacement,
  verbes/actions, hires, vec engine `781D-7A22` apparu par propagation…),
  44 plate-comments (résumés une-ligne), 8 labels `msg_*` NULL.
- 77/77 noms zéro-page poussés (`ploc`, `obj`, `ptr/ptr2`, `adr`, `phase`…,
  via `rename_symbol`, gate désactivé) : le décompilé parle le langage
  du listing (cf. §6).
- Programme `hobbit.bin` sauvegardé dans Ghidra après chaque passe.

## 4. Convention inline `+5` (trouvaille structurante)

`JSR $440D` / `JSR $5B24` + mot inline = adresse message, reprise à JSR+5
(`JMP ($6A)`, helper `$44BE`). Ghidra l'ignore : corps tronqués aux ~108
sites, `.word` désassemblés comme du code, `noreturn` fallacieux.

- Prototype validé sur `act_v14_15` (`$6E8B`) : mot typé `word`
  (`$162B`, `$1615` confirmés), EOL `-> $XXXX texte [+5]` visible dans
  le pseudo-C.
- Généralisation : **124/124 sites** (`msg_*` extraits de
  `disasm/block4.asm`, vérifiés `jsr`-précédés à 100 %), mot typé +
  EOL avec aperçu du message ; les 8 pointeurs NULL
  (`3CB7 4DFC 4E30 52C6 5BB8 631D 63C1 6C2C`) commentés
  `msg ptr NULL (runtime-resolved)`.
- Bonus : `say_if_visible $5279` affiche désormais le NULL en direct
  (`WORD_52c6` + `print_msg`), preuve vivante du mécanisme.
- Corrections de lecture : `5B24` = `act_msg` (`JSR $440D`, pas un thunk),
  idem `4C57` ; seul `44A0` (`JMP $4641`) est un vrai trampoline.

## 5. AnimTalk (parser) — validé

Chaîne décompilée, conforme à `docs/block4-analysis.md` :
- `tokenize $2ED5` : espaces, `CR`→`$C0`, `punct_class`, `dict_bucket`
  (masque 5-bit, table `$0500`), boucle `word_prefix_cmp`/`dict_next`,
  type en `$5B` + `adr/adr_hi`, miss → `$D0`.
- `parse_cmd $3111` : `set_mode0`, `rec_clear`, `next_token`, dispatch
  **auto-modifié via `$315A`** (Ghidra signale l'écriture en zone code) —
  2ᵉ site d'auto-modification après `$6A5C`, à noter au doc.
- `cmd_run $357C` : `move_begin` → `cmd_probe` → `$57=3` si passe.
- `cmd_probe $36D5` : `perform_action()` + retourne `passok` (sonde).
- `perform_action $4B37` : `arg1_check`→`cannot_do`, test noirceur
  (`I SEE NOTHING HERE.` EOL visible), `direct/arg1`, `locate_object`,
  `verb_obj_ok`, `index_id_table`→`indirect_call` (`$4C64/65`), table
  `L7014`, table `you_are_dead $7115`, `announce_move` en phase réelle.
- Live (harness hires + OCR) : `LOOK` → description + objets ;
  `FROBNICATE` → `I DO NOT KNOW THE WORD " ROBNICATE."` (`$116B`,
  chemin miss de `dict_bucket`).
- Quirk input à connaître : le pager (`+`) mange la première touche
  (`FROBNICATE` → `ROBNICATE`, `GIVE…` → `IVE…`) ; préfixer d'une touche
  sacrifiée (`LOOK\r GIVE…` : l'espace leading est ignoré par `tokenize`).

## 6. AnimAction (PNJ) — validé

Décompilés, conformes au doc :
- `world_tick $4E59` : `victory_check $69E7` → `entity_tick $4ED5` →
  `evt_tick` (créé à `$4E75`, entrée mid-fonction comme `act_probe`).
- `evt_tick` : curseur `ptr2` sur table `$2B12` (5 o), décompte `[1]`,
  garde un-actA `$4E58`, dispatch `($7169[A])` → `indirect_call`.
- `entity_tick_done $5008` : `obj=0, outen=1, crec=$1B1A, eloc=$1B2A`.
- `script_move[_short]` : MOVE (`wid/arg1/arg2` + `entity_move`) vs
  ACT via `$7143` (sonde phase 0 puis réel si `passok`), bit `$20`
  auto-efface, bit `$10` vecteur de secours, garde-fous 6 opcodes `$4ED3`.
- `script_rand/indirect` : clamp `min(op,nmax)`, table de base `+4/+5`.
- `entity_goto $5249` (`X`=clé, `A`=id) : `entity_find` (scan `$2B45`
  par 7) + `index_id_table` sur base ; GOTO runtime-only.
- `entity_move/move_announce` : `move_core` partagé, `YOU HEAR A NOISE`
  (`$1406`), `perform_action`, `say_if_visible(obj,$F6,$13)`.
- Vivant (3× LOOK, diffs `$2B00`) : 17 entrées, PCs qui avancent par tick
  (Elrond `$2A42→$2A38`, l'exemple du doc ; trolls `47/48` parqués à
  `$2AD0`, boucle d'attente + secours) ; écrans : *« Gandalf gives the
  curious map to you. »* puis *« Gandalf opens the round green door. »* ;
  table événements à zéro (rien d'armé).

## 7. Mécanisme du slot dormant e04 — élucidé (résultat principal)

Contexte doc : `PC=$2B0E` observé, posé hors flot script, mécanisme
d'écriture ouvert (« handler GIVE ? »).

### 7.1 Parking : `announce_move` → tail-`jmp entity_goto` (tick 1)

Trace `sim_trace` (`--watch`, 120 M cycles, image `--fast`), tick LOOK#1 :
- Le MOVE `$295C` de Gandalf (`wid=$1D arg1=$03 arg2=$00`, GIVE map)
  se termine par `announce_move(arg2=$00)` qui, flags `$40`✓/`$08`✗,
  **tail-jumpe vers `entity_goto` avec `A=$00`, `X=$1D`** (pas de JSR :
  invisible aux séquences d'appels).
- `entity_goto` : `entity_find($00)` → slot e04 `@ $2B61` (premier id
  `$00`) ; `index_id_table($1D, base $29E4)` → match vérifié dans
  l'image (`29E4: 00→$29EE, 0B→$29FE, 1D→$2B0E`).
- `5270/5274 : sta ($88),Y A=$2B/Y=03 + A=$0E/Y=02` →
  **e04.PC := `$2B0E`** (unique écriture PC du tick).
- Sens : `arg2=$00` (« pas de second objet ») + wid en clé = routage
  vers le slot scratch ; la table du slot est un dispatch par verbe.

### 7.2 Consommation : GIVE MAP TO GANDALF

- Commande acceptée (`GIVE/MAP/GANDALF` au dico) : *« You give the curious
  map to Gandalf. / Gandalf says " Thank you ". »*.
- Mem-frames : `Gandalf.PC $2964 → $2B11`, e04 inchangé à `$2B0E`.
- Au tour de Gandalf, son entrée contient déjà `$2B0E` (`ptr2=$2B45`
  prouvé : `sta $88=$45/$89=$2B` juste avant, pas de retouche) :
  exécution du fragment parqué `$2B0E: ACT idx=19 → $6915`
  (dispatch `$7143` vu en trace : `lda $7143,X`), writeback `$2B11`.
- Statique (vm_decode + DB) : `$2B0E = ACT 19 → $6915 (actA#1)` ;
  `$2B11 = INDIR table[0](base $2943 de Gandalf) → $2964`
  (tête de boucle). Le détour parqué fait ACT 19 → retour boucle.
- Le cluster `$2B02-$2B11` contient aussi un `GOTO $2B0B→$2B02`
  chevauchant (le « milieu d'instruction » du doc).

### 7.3 Point ouvert (un seul)

Le store exact qui pose `$2B0E` en `$2B47/48` (entrée Gandalf) pendant
la phase joueur du tick GIVE n'a pas été attrapé : absent des ~1,9M
instructions tracées (`$358F-$7300` + défauts : aucun `sta ($88)/($8A)`
ni absolu `$2B47` correspondant ; corps lus de `action_give` et
`event_arm_obj` sans store PC ; seuls écrivains absolus du listing :
`$2B40`, `$2B61`). Restent non tracés : `$2C00-$358E` (parser — improbable
par design), **`$3B75-$4B00` (dispatch `special_cmd`, `actq_pull`,
chaîne `describe/move` — suspect n°1)**, `$7300+` (invraisemblable).
Clôture : un run trace avec `$3B75-$4B00` ajouté.

## 8. Rejouer

```sh
.venv/bin/python scripts/sim_pack.py --hires   # image avec dumps hires
printf '\rLOOK\r GIVE MAP TO GANDALF\r' | ./tools/cc65/bin/sim65 -x 300000000 build/sim/hobbit.sim > /tmp/give.bin
.venv/bin/python scripts/sim_frames.py /tmp/give.bin   # OCR
.venv/bin/python scripts/sim_trace.py --input cmd.txt --image build/sim/hobbit_fast.sim \
    --cycles 120000000 --range 4B00 4E00 --range 4E00 5300 --range 5301 5800 \
    --range 5800 7300 --max 1500000 --out trace.txt
```

## 9. Limites et bruit connus

- `FUN_0000` (faux positif ZP), ~190 `FUN_*` anonymes restants (chunks
  `code_*` également anonymes dans da65 — nommage non prioritaire).
- `thunk_FUN_440d` en `5B24/4C57` : ce sont des `JSR`, pas des sauts
  (renommés `act_msg`/`cannot_do`, flag thunk restant, cosmétique).
- `DAT_0000`-style et `uStack0000`/`in_V`/`in_B` : artefacts 6502 du
  décompilateur (registre P modélisé en variable) — lire autour, pas
  au pied de la lettre ; les `WARNING: Read-only address … is written`
  signalent l'auto-modification et les vecteurs (`$4C64/65`, `$315A`).
- Premier appel `entity_goto` de chaque run : `A=$FF` (recherche du
  terminateur `$2BBC`) — écriture `$0E/$2B` dans le remplissage `$00`
  `$2BBE-$2BFF`, sans effet.
- Comptage de ticks : l'espace pager consomme un tour apparent dans les
  frames hires (f1 `$2960` → f7 `$2964` sans commande visible) ; caler les
  analyses sur les PCs, pas sur les numéros de frames.
