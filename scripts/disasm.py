#!/usr/bin/env python3
"""Génère un listing assembleur annoté du bloc 4 de The Hobbit (Oric).

Le découpage code/données est obtenu par **descente récursive** depuis les
points d'entrée (autorun ``$2C00``, ``$2C35`` et les 16 vecteurs ``$2C05``),
en suivant ``JSR``/``JMP``/branchements, jusqu'à point fixe. Les seeds
radare2 validés (décodage propre) et les entrées manuelles complètent la
couverture (dispatch indirect).

Règle spéciale : ``JSR $440D`` (print_msg) et ``JSR $5B24`` (act_msg,
qui rebondit vers print_msg) sont suivis de 2 octets inline (adresse du
message) ; le code reprend à JSR+5. Les pointeurs nuls sont marqués ``TODO``.
Les actions indirectes (tables ``L7014``/``L7143``) et les routines
avoisinantes sont des ``MANUAL_ENTRIES`` (validées par le checker, règle D).

da65 (cc65) produit ensuite le listing à partir du fichier d'information
(``disasm/hobbit.info``) et de ``data/hobbit.bin``.

Prérequis : ``tools/cc65/bin/da65`` (cf. AGENTS.md).
Vérification : scripts/check_disasm.py.

Usage : .venv/bin/python scripts/disasm.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from opcodes6502 import BRANCH, JMP_ABS, JMP_IND, JSR, INLINE_MSGS, PRINT_MSG, RTI, RTS, BRK, ilen

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
DISASM = ROOT / "disasm"
INFO = DISASM / "hobbit.info"
LISTING = DISASM / "block4.asm"
R2CACHE = DISASM / ".r2_afl.txt"
TOOLS = ROOT / "tools" / "cc65" / "bin"
DA65 = TOOLS / "da65"
CA65 = TOOLS / "ca65"
LD65 = TOOLS / "ld65"

BASE = 0x0400
BLOCK1 = (0x0400, 0x0500)
BLOCK2 = (0x0500, 0x2BBD)
BLOCK3 = (0x7AC0, 0x91B1)
BLOCK4 = (0x2C00, 0x7A80)
ENTRY = 0x2C35

# Entrées manuelles confirmées à la main (dispatch indirect, trampolines).
# La table de vecteurs $2C05-$2C34 (16 x JMP) est du code par construction,
# ainsi que les routines suivantes (vérifiées par décodage jusqu'à un
# terminateur propre) que la descente n'atteint pas directement.
MANUAL_ENTRIES: list[int] = (
    [0x2C05 + 3 * k for k in range(16)]
    + [0x32B9, 0x3C8E, 0x5B44, 0x5BC9, 0x5D31, 0x698B,
       0x6A02, 0x6EA7, 0x6D55, 0x6F2A, 0x4599, 0x4DAF]
    + [0x32E9, 0x3CCE, 0x3D39, 0x4569, 0x6A12, 0x6A24, 0x6A5E, 0x6A86,
       0x6F44, 0x6F7E, 0x70D2, 0x6DD0]
    # Actions dispatchees par les tables L7014/L7143 (indirect -> hors
    # descente). Cf. docs/block4-analysis.md.
    + [0x65DD, 0x65BA, 0x65B6, 0x65F1, 0x66D6, 0x68D0, 0x68E0, 0x690C,
       0x692D, 0x6936, 0x6962, 0x6B72, 0x6C09, 0x6C33, 0x6C8D, 0x6CBE,
       0x6CFA]
    # Suite contigue des handlers d'actions (orphelins confirmes code
    # par le checker, regle D : decode >=85%).
    + [0x65E3, 0x6607, 0x6629, 0x6666, 0x66AA, 0x6902, 0x6903, 0x6915,
       0x6B00, 0x6B27, 0x6B55, 0x6BDB, 0x6C5F, 0x6C79, 0x6CDB, 0x6D3D,
       0x6D9F]
    # Handler du token $09 ($456F, table $4641) : sans seed, la plage
    # code_436C s'arrete au RTS $456E et $456F-$4572 tombent en donnees
    # (le JMP patche est indirect, invisible de la descente).
    + [0x456F]
    # Stubs d'armement des evenements $2B12 en zones donnees : $65A5
    # (cpt e3, queue jsr $6222+$4D95) et $70B5 (cle $16 : ecrit entite
    # $2B61). Seuls des STA $2Bxx les trahissent (scan binaire complet).
    + [0x65A5, 0x70B5]
)

# Seeds radare2 récusés : chevauchent des pointeurs $440D ou du connu.
# $6DCE = fcn.00006dce, octet haut du pointeur $165A (JSR $440D en $6DCA).
SEED_EXCLUDE = {0x6DCE}

# Routines documentées : adresse -> (nom, résumé une ligne).
# Le nom renomme le label (doit être unique, identifiant ca65 valide) ;
# le résumé est émis en commentaire da65 avant le label. Règles :
# - une seule ligne, sans guillemet `"`, <= 160 caractères ;
# - l'adresse doit être un début d'instruction (vérifié par check_disasm.py).
# Détails longs -> docs/block4-analysis.md (référencé par adresse).
ROUTINE_DOCS: dict[int, tuple[str | None, str]] = {
    # nom None = garde le nom existant (VECTORS), ajoute seulement le résumé.
    0x2C35: (None, "init : copies boot, pile, RAZ vars, prompt '> LOOK.', boucle d'input"),
    0x2DC8: ("init_vars", "RAZ variables ($97.., $AF, $CC/$CD) puis JMP main $7779"),
    0x3097: ("boot_copy", "copie $1B1A->$91D0 (1366 o) ; $6C = compteur"),
    0x30BB: ("boot_copyback", "recopie inverse ($8C)->($8A), meme gabarit"),
    0x440D: ("print_msg", "affiche le message du mot inline ; reprend a JSR+5 via JMP ($6A)"),
    0x44BE: ("msgptr_inc", "INC $6A (+ $6B si retenue) ; avance le pointeur message"),
    # Moteur de messages (decodeur valide par reimplementation Python : les
    # 32 mots $1117 et le dictionnaire 5-bit sortent en anglais propre).
    0x4444: ("render_text", "boucle : literaux $20-5F, mots $60-7F ($1117), tokens <$20 ($4641), 2 o si bit7"),
    0x4241: ("word_render", "rend un mot du dico packe 5-bit : pluriels S/ES/IES/ING, espace auto, wrap"),
    0x462D: ("common_lookup", "octet $60-7F -> mot courant de la table $1117 (the/a/and/you/to/...)"),
    0x4641: ("token_jumps", "table des 32 tokens <$20 : <$14 sous-routines (Z=saute $4241), $14/15/16=fins"),
    0x44A0: ("token_dispatch", "JMP auto-patche vers le handler du token (mot L4641+tok*2)"),
    0x44AE: ("text_end", "fin 2 o : $2x=fin, $3x='.', $6x=CR (via $44A3/$44A8)"),
    0x44C5: ("tok_nested", "token $00 : rend le message empile (L466F/$0200), Z=saute"),
    0x44F5: ("tok_stkword", "token $01 : rend le mot a l'adresse empilee (L466F)"),
    0x44FB: ("tok_skip", "token $02 : GOTO offset signe (octet suivant, L4507, tidx=$FF, sans retour)"),
    0x4504: ("tok_noop", "tokens $05/$0A/$0F/$12 reserves : sans effet (lda #0, saute)"),
    0x452E: ("tok_objw", "token $03 : rend le mot pointe par ($71/$72)"),
    0x4539: ("tok_stkvar", "token $04 : variante ($70=1, tables $28BC/$28C4) du mot empile"),
    0x454B: ("tok_objC5", "token $06 : rend le nom de l'objet $C5 via $461B (imbrique $44C7)"),
    0x4557: ("tok_obj15", "token $07 : rend l'objet $15 (direct $43E4 si $73, sinon $43F3)"),
    0x4569: ("tok_ctrl08", "token $08 : appel vecteur interne $2C2F avec A=$08"),
    0x456F: ("tok_obj16", "token $09 : rend l'objet $16 (variante $74)"),
    0x4599: ("tok_recurse", "token $0B : recurse render_text sur offset signe (octet suivant, queues partagees)"),
    0x45B0: ("tok_pronC5", "token $0C : pronom his ($0548->$0A48) si $C5, your ($0C12->$1112) sinon"),
    0x45CA: ("tok_pron15", "token $0E : idem tok_pronC5 avec $15"),
    0x45CF: ("tok_nameC5", "token $10 : nom objet $C5 ($05B2=is si absent, $0958=someone si $FF)"),
    0x45F4: ("tok_name15", "token $11 : idem avec $15 et variante $70=1"),
    0x45FC: ("tok_nameSTK", "token $13 : empile L466F ($76) puis nom objet ($45D4)"),
    0x44E4: ("stk_pop", "depile une adresse L466F ($76) en $5C/$5D"),
    0x460A: ("nested_render", "rend le message imbrique ($5C/$5D) : pile $0200 ($5535)"),
    0x461B: ("obj_lookup", "id objet -> mot : $FF=someone ($0958), sinon rendu $458A"),
    0x46DB: ("cr_aware_out", "putchar + Z si $0D (token $0D = CR inline, saute $4241)"),
    0x42CE: ("word_space", "espace auto ($0D/$0F) + wrap (longueur X vs $04/$05, flag $0E)"),
    # Evenements differes : table $2B12 (entrees 5 o [id,cpt,actA,cond,actB],
    # $FF fin), balayee par world_tick ; actions via table de sauts $7169.
    0x4E75: ("evt_tick", "balaye $2B12 : cpt--, re-arme, dispatch actB via $7169"),
    0x4E9D: ("evt_cond", "si cond<>0 et cond>=cpt : dispatch entree+4 (L4EAB)"),
    0x4EAB: ("evt_fire", "patch L4C64/L4C65 depuis $7169+X*2 puis jsr L4C5D"),
    0x4ECC: ("evt_end", "fin de table ($FF) : $0B=1 puis jmp $471B"),
    0x5DE2: ("evt_lookup", "dispatch $8F via table $709F (cles->$70CB..) sinon $5DFD"),
    0x6689: ("evt_disarme6", "desarme e6 (cpt:=0) + pose bit7 ($1CCB, ($C6)+7/+5)"),
    0x66AA: ("evt_arme6", "arme e6 : cpt := 2+rand(8) (delai aleatoire)"),
    0x65A5: ("evt_arme3", "jsr $6222 + $4D95 puis cpt e3 := id (orphelin)"),
    0x6A19: ("evt_disarme7", "si $C5==0 : $C4:=1 + desarme e7 (cpt:=cond=0)"),
    0x6AEB: ("evt_arme9b", "jsr $4D95, cpt e9 := 6, flags $1C7B, jmp $6D72"),
    0x6B66: ("evt_arme5", "cpt e5 := id + dit $168B (magic door) ; orphelin"),
    0x6C5F: ("evt_act5", "actB e4 : si $C8==$1D dit $1535 (bog) sinon desarme e4"),
    0x6D72: ("evt_print", "dit $1685 (hole vanish) ; queue du sub $6AEB"),
    0x6915: ("evt_tip", "sonde + tirage : ~20% dit $1485 (expect me) ; orphelin"),
    0x70B5: ("evt_arme16", "si ($1DC5&8) : $2B61:=$42 (entite) + bit7 (cle $16)"),
    0x70CB: ("evt_arme2", "cpt e2 := id (cle $1A, table $709F)"),
    0x70D2: ("evt_arme4", "cpt e4 := id (cle $1D)"),
    0x70D9: ("evt_arme9", "cpt e9 := 3 + ecrit entites $2B76/$2B7D (cle $20)"),
    0x70F8: ("evt_arme8", "$BE:=$8F + cpt e8 := id (cles $02/$03)"),
    0x7103: ("evt_gate21", "$1B1B==$13 ? $5DFD + print (cle $21)"),
    0x4E59: ("world_tick", "apres commande reussie : L46E6, L69E7, VM entites, table $2B12"),
    0x4ED5: ("entity_tick", "VM : entree 7 o $2B45 ([id,?,PC,..]), <=6 opcodes/tick (nibble bas)"),
    0x5020: ("script_adv", "avance PC script $8C de A"),
    0x502A: ("script_step4", "+4 (bit $10:+2), reecrit PC dans l'entree"),
    0x502C: ("script_step2", "+2 (bit $10:+2), reecrit PC dans l'entree"),
    0x511C: ("entity_move", "mouvement entite ($13/$15/$16), message si visible"),
    0x5249: ("entity_goto", "positionne PC entite depuis ($8A)+1..2"),
    0x5279: ("say_if_visible", "message (msg_52C6 patche) si entite au lieu du joueur"),
    0x36DB: ("move_core", "resout $13 (L43CB), evalue cond $15/$16, execute, ret A"),
    0x43CB: ("exit_ptr", "($F8) = $26DA + $13*8 (entrees 8 o)"),
    0x3759: ("cond_eval", "slot condition X ($FF=absent), variante selon $73"),
    0x3770: ("move_flags", "derive $73/$74/$80 depuis $78 (bits 7/6, sinon residus)"),
    0x5386: ("act_probe", "sonde : $0C==1 execute, sinon $12=1 et annule un niveau"),
    0x56D7: ("rand_range", "tirage pseudo-aleatoire borne par A (bruit ($93))"),
    0x5B24: ("act_msg", "message d'action $13E8 + epilogue"),
    # Actions dispatchees par la table L7014 (index 0-14), declenchees par
    # les verbes joueur (L4B37). Effets deduits du flot + messages.
    0x5CA9: ("act_p14_04", "objet $15 : test flags ($64D7/$5C88) puis prise/pose"),
    0x5CB6: ("act_p14_14", "objet $C5 : test flags ($5C88) puis bascule $46E9"),
    0x5D06: ("act_p14_05", "objet : seuil ($8A)+2, deplace et fixe $13/$15"),
    0x6041: ("act_p14_13", "flags objet ($19) : bits 0-2, dit $11D3 (swept away) / $13D1 (X dead)"),
    0x60BF: ("act_p14_00", "consomme compteur ($C6)+5, RAZ 16 o ; dit $1525 (gluttony KILLED)"),
    0x60ED: ("act_p14_01", "deplacement objet (bits $78), ecrit $75/$70/$5C/$5D"),
    0x61C9: ("act_p14_02", "objet ($17) : bit5 de ($8A)+7 -> 0 ; sinon $5A9D"),
    0x61E5: ("act_p14_07", "objet $16 : lit bit5 de ($88)+7, branche $5A90"),
    0x6222: ("act_p14_03", "bit5 ($8A)+7 -> 1 ; si id==1 fete $580F (CHEERING CROWD...SUNSET)"),
    0x65B6: ("act_p14_12", "dispatcher objet $16 (cas $0F) -> $65DD/$641D/$6448"),
    0x65BA: ("act_p14_08", "dispatcher objet $16 (cas $04) -> $65DD/$4C57"),
    0x65DD: ("act_p14_06", "dit $140C (X do not fit this lock) sinon $139B (i cannot do that)"),
    0x65F1: ("act_p14_10", "si ($C6)+16==$0F -> $6222 sinon $5A62"),
    0x66D6: ("act_p14_11", "dit $1478 (spiders mend the web) + arme e1 (cpt:=id)"),
    0x6B72: ("act_p14_09", "si $C5==$41 : parcourt ($C1), dit $13E0/$15AB (go...from...to)"),
    # Actions dispatchees par la table L7143 (index 0-14) : comportements
    # autonomes des PNJ dans la VM $4ED5.
    0x68D0: ("act_v14_06", "si meme lieu ($C9==$C8) : sonde + dit $143F (hello)"),
    0x68E0: ("act_v14_01", "oisivete : $1432 (great job) / $143B (hurry up) / $143F (hello)"),
    0x690C: ("act_v14_02", "sonde + dit $1441 (thrains key)"),
    0x692D: ("act_v14_00", "sonde + dit $1427 (WHAT'S this ?)"),
    0x6936: ("act_v14_04", "tirage 0-7 : $4D9E + dec ($14), message $143B"),
    0x6962: ("act_v14_03", "si meme lieu et !($1B21&$80) : dit $14AB (WHERE'S the thief ?)"),
    0x697A: ("act_v14_05", "si $C8==$1DE0 : sonde, $4D9E, ror ($14)"),
    0x6C09: ("act_v14_12", "si $1E4B==$C8 et ($1B21&$80) : message patche ($6C2C)"),
    0x6C33: ("act_v14_11", "one-shot ($CE==1) : RAZ $CE, $3F7F, copie $14/$15 en $2A7B"),
    0x6C8D: ("act_v14_09", "si $C8 in {27,2C,29} : sonde + dit $13F6 (X enter)"),
    0x6CBE: ("act_v14_10", "meme lieu : $153F (dragon : prepare to die) ou $155D (aveugle) si $80"),
    0x6CFA: ("act_v14_07", "si meme lieu : prend l'objet $1FC1 (id $1FB2=41)"),
    0x6D78: ("act_v14_14", "si $C8==$1E4B : tirage, $16B9 (pocket ?) / $16C8 (my precious)"),
    0x6DF9: ("act_v14_13", "cherche lieu $3485, RAZ $D5, dit $15B6 (strangle you)"),
    0x6E59: ("act_v14_08", "si $1F47!=$29 : tirage 0-100, $1582 (dragon flying) / $1596 (burn you)"),
    0x6E8B: ("act_v14_15", "si $C8==5 : sonde, $C5==$47 ? $1615 (BLIMEY, COOK EM) : $162B (MOUTHFUL) [trolls]"),
    0x6CDB: ("act_v14_16", "si meme lieu : sonde, wid=$1B/arg1=0, $60BF + JMP $5FAE"),
    0x6EA7: ("act_v14_17", "sonde + L4D47 ($47/$48), RAZ bit7 $1F94/$1FA6, $214C&~$40, desc $2154=$1645, dit $16EB"),
    0x4737: ("fetch_retaddr", "copie 2 octets de la pile ($0200+$AF-2) en $8A/$8B"),
    0x71DB: ("tape_load", "LOAD bloc cassette via $0417 + verif $32/$33"),
    0x7215: ("tape_save", "SAVE : leader, en-tete 9 o, donnees, checksum EOR"),
    0x72A0: ("tape_prompt", "invites PREPARE TAPE / REWIND / PRESS ANY KEY"),
    0x7353: ("kb_scan", "scan clavier VIA ; A = touche bit7=presente, sinon bit7=0"),
    0x7481: ("kb_wait", "attente bloquante d'une touche (BPL) ; retour & $7F"),
    0x7489: ("cr_out", "affiche CR ($0D) via ch_out"),
    0x7491: ("ch_out", "filtres $0B/$0C/$0D/$C4 (capitales) puis rendu"),
    0x75B4: ("glyph_out", "rend un caractere en hires $A000 (font ($0403), ORA $40)"),
    0x75F6: ("ch_put", "sortie ecran : gere CR, scroll, pause bas d'ecran via kb_scan"),
    0x7619: ("pause_key", "toutes les 16 CR ($11) : touche (10 essais timeout) + relachement, sinon $11++"),
    0x7747: ("hires_clear", "remplit $A000-$BFDF de $40"),
    0x7779: ("game_main", "boucle principale du jeu (atteinte via JMP vec_15)"),
    # Moteur d'illustrations vectorielles (consomme le bloc 3 : table $7AC0
    # [cle,mot] x13 + flux d'octets $00-termine ; valide par rendu sim65 des
    # 13 images via un pilote vec_init + dump hires).
    0x4750: ("img_show", "illustration de la cle A (table $7AC0) : vec_init + keyin, Z si absente"),
    0x77D4: ("vec_image", "dessine une illustration (($28/$29)) : setup L7990 puis boucle dispatch"),
    0x7824: ("vec_fill", "remplissage ($40) : balayage L79FB/L7A0F sur compteurs $32-$36"),
    0x78C9: ("vec_pos", "$08 : pose le curseur $30/$31 (2 o)"),
    0x78DA: ("vec_skip", "$20 : saute jusqu'a $FF (repris comme L78E4)"),
    0x78E4: ("vec_line", "bit7 : segment (2 o : flags+longueur, pas) ; pixel par pixel (lent)"),
    0x7990: ("vec_setup", "efface hires $A000-$B3FF ($40) + aplats depuis l'octet mode"),
    0x79FB: ("vec_testpx", "teste le pixel ($30/$31) : $FF si hors bande $0E-$F2"),
    0x7A0F: ("vec_plot", "allume le pixel ($30/$31) via ($38/$39)+masque L7A5F"),
    0x7A22: ("vec_addr", "adresse+masque du pixel ($30/$31) : X=$7F-$31, Y=$37"),
}

# Zéro-page nommée : adresse -> (nom, résumé une ligne).
# Rôles établis par recoupement exhaustif des usages bloc 4 (cf.
# docs/block4-analysis.md, section zéro-page) : le nom remplace l'opérande
# numérique via un LABEL da65 (l'octet haut se rend `nom+1`). Règles :
# - une seule adresse nommée par paire (le haut suit en `+1`) ;
# - même règles que ROUTINE_DOCS (identifiant unique, 1 ligne <= 160c).
# Les adresses multi-rôles ou non élucidées restent numériques.
ZP_NAMES: dict[int, tuple[str, str]] = {
    # Sortie texte (renderer $44xx + video $74xx-$77xx).
    0x04: ("col", "colonnes restantes (RAZ $28/ligne ; test wrap cpx, conso glyph_out)"),
    0x0B: ("outen", "1=sortie autorisee (init input, annonces PNJ, fin events)"),
    0x0C: ("phase", "0=sonde, 1=execution (actions L506B, parser, print_msg, ch_out)"),
    0x0D: ("raw", "1=mode brut (espace forcee, limite col, capitales L74BB)"),
    0x0E: ("cap", "1=capitaliser la prochaine lettre (pose sur point)"),
    0x0F: ("sppend", "espace en attente avant le prochain mot (word_space)"),
    0x11: ("crcnt", "CR depuis derniere pause (mod 16 ; relu en $39D3)"),
    0x12: ("passok", "sonde reussie (1=passer a l'exec ; cf. L506B/act_probe)"),
    # Operandes de commande (parser L359B, VM L5048/L50AC, $FF=absent).
    0x13: ("wid", "id mot/direction (parser, exit_ptr, move, VM)"),
    0x15: ("arg1", "operande objet 1 ($FF=absent ; match identite $C5)"),
    0x16: ("arg2", "operande objet 2 ($FF=absent)"),
    # Enregistrements d'objets (deref ($..),y ; swap L57A1).
    0x17: ("orec", "enregistrement objet 1 (pointeur ; hi $18)"),
    0x19: ("orec2", "enregistrement objet 2 (pointeur ; hi $1A)"),
    0xC6: ("crec", "enregistrement courant (contexte/compteurs ; hi $C7 ; base $1B1A)"),
    # Moteur de messages (render_text, tokens, pile $466F/$0200).
    0x5C: ("adr", "adresse etagee (message imbrique, mot ; hi $5D)"),
    0x6F: ("tidx", "index texte (curseur Y sauvegarde du renderer)"),
    0x70: ("nest", "niveau d'imbrication du rendu (0=simple)"),
    0x71: ("wptr", "pointeur de mot/nom (tok_objw, L626B ; hi $72)"),
    0x76: ("msgstk", "index pile messages $466F (RAZ a chaque print_msg)"),
    0xAD: ("svA", "A sauvegarde (routines pile $0200)"),
    0xAE: ("svX", "X sauvegarde (routines pile $0200)"),
    0xAF: ("rstk", "index pile retours $0200 (push $46E9/$4702, pop $471E/$4737)"),
    # Mouvement (exit_ptr, code_4141, move_flags, cond_eval).
    0x73: ("direct", "1=direct/sans controles (=bit7 xmode)"),
    0x74: ("variant", "variante (=bit6 xmode ; move_flags)"),
    0x77: ("xaux", "octet auxiliaire de sortie (nibbles +5/+7 ; bit6->$7F)"),
    0x78: ("xmode", "octet mode de sortie (nibbles +1/+3 ; b7 direct, b6 variante)"),
    0xDC: ("cond1", "tampon condition 1 (6 o $DC-$E1)"),
    0xE2: ("cond2", "tampon condition 2 (6 o $E2-$E7)"),
    0xE8: ("svptr", "ptr sauvegarde (contexte move ; hi $E9)"),
    0xF8: ("exitp", "curseur table des sorties ($26DA+wid*8 ; hi $F9)"),
    # Pointeurs de travail universels.
    0x7A: ("ptr3", "3e pointeur de travail (hi $7B)"),
    0x88: ("ptr2", "pointeur secondaire, balayages de tables (hi $89)"),
    0x8A: ("ptr", "pointeur de travail universel (hi $8B)"),
    # Monde (entites, events, tirage).
    0x8F: ("key", "cle de dispatch (table $709F, evt_lookup)"),
    0x93: ("noise", "pointeur source d'entropie (bruit ($93),y ; hi $94)"),
    0xBE: ("exploc", "lieu attendu par l'evenement (copie de key ; grille ploc)"),
    0xC5: ("obj", "objet/entite courant (id ; $FF=personne ; lieu via L57BB)"),
    0xC8: ("ploc", "lieu du joueur (cf. code_5235)"),
    0xC9: ("eloc", "lieu de l'entite (visibilite : eloc==ploc)"),
    0xCE: ("once", "verrou one-shot (pose, teste+consomme)"),
    # Octets hauts des paires (da65 ne rend pas `nom+1` : nommage explicite).
    0x18: ("orec_hi", "haut de orec"),
    0x1A: ("orec2_hi", "haut de orec2"),
    0x5D: ("adr_hi", "haut de adr"),
    0x72: ("wptr_hi", "haut de wptr"),
    0x7B: ("ptr3_hi", "haut de ptr3"),
    0x89: ("ptr2_hi", "haut de ptr2"),
    0x8B: ("ptr_hi", "haut de ptr"),
    0x94: ("noise_hi", "haut de noise"),
    0xC7: ("crec_hi", "haut de crec"),
    0xE9: ("svptr_hi", "haut de svptr"),
    0xF9: ("exitp_hi", "haut de exitp"),
}

# Points d'entrée de la table de vecteurs en $2C05 (16 entrées JMP).
VECTORS = {
    0x2C00: "autorun",
    0x2C03: "ptr_block3",
    0x2C05: "vec_init",
    0x2C08: "vec_01",
    0x2C0B: "vec_02",
    0x2C0E: "vec_03",
    0x2C11: "vec_04",
    0x2C14: "vec_05",
    0x2C17: "vec_06",
    0x2C1A: "vec_07",
    0x2C1D: "vec_08",
    0x2C20: "vec_09",
    0x2C23: "vec_10",
    0x2C26: "vec_11",
    0x2C29: "keyin",
    0x2C2C: "print_cr",
    0x2C2F: "putchar",
    0x2C32: "main",
    0x2C35: "start",
}

# Routines ROM (issues du désassemblage 1.0 et 1.1, cf. docs/).
ROM_LABELS = {
    0xE5C6: "PUTBYTE_10",
    0xE630: "READBYTE_10",
    0xE696: "TAPESYNC_10",
    0xE6BA: "WRITELEADER_10",
    0xE6CA: "SETUPTAPE_10",
    0xF73C: "CHAR2SCR_10",
    0xF960: "RESETSTAT_10",
    0xE65E: "PUTBYTE_11",
    0xE6C9: "READBYTE_11",
    0xE735: "SYNCTAPE_11",
    0xE75A: "WRITELEADER_11",
    0xE76A: "SETUPTAPE_11",
    0xF77C: "CHAR2SCR_11",
    0xF9AA: "RESETSTAT_11",
}


def printable_ratio(data: bytes, a: int, b: int) -> float:
    chunk = data[a - BASE:b - BASE + 1]
    if not chunk:
        return 0.0
    ok = sum(1 for c in chunk if 0x20 <= c < 0x7F or c == 0x0D)
    return ok / len(chunk)


def load_r2_seeds(path: Path) -> list[int]:
    seeds: list[int] = []
    try:
        text = path.read_text()
    except FileNotFoundError:
        return seeds
    for line in text.splitlines():
        m = re.match(r"0x([0-9a-f]+)\s+\d+\s+(\d+)\s", line)
        if m:
            seeds.append(int(m.group(1), 16))
    return seeds


def try_decode(raw: bytes, lo: int, hi: int, addr: int,
               starts: set[int], covered: set[int]) -> bool:
    """Valide un candidat : pas de texte, décodage propre (les octets
    pointeurs déjà connus sont dans `covered`). Les cibles de
    branchements/JSR internes doivent être des opcodes légaux.
    Accepté si terminateur RTS/RTI/JMP (>= 3 o, BRK >= 8 o et non
    inclus) ou fusion avec du connu (>= 4 o)."""

    def B(a: int) -> int:
        return raw[a - BASE]

    def word(a: int) -> int:
        return B(a) | (B(a + 1) << 8)

    def legal(a: int) -> bool:
        return lo <= a <= hi and ilen(B(a)) != 0

    chunk = raw[addr - BASE:addr - BASE + 16]
    if len(chunk) < 4:
        return False
    if sum(1 for c in chunk if 0x20 <= c < 0x7F or c == 0x0D) / len(chunk) > 0.5:
        return False
    pc, n = addr, 0
    while lo <= pc <= hi and n < 1024:
        if pc in starts:
            return n >= 4
        if pc in covered:
            return False
        op = B(pc)
        if op == JSR and pc + 2 <= hi and word(pc + 1) in INLINE_MSGS:
            pc += 5
            n += 5
            continue
        ln = ilen(op)
        if ln == 0 or pc + ln - 1 > hi:
            return False
        if op == BRK:
            return n >= 8  # le BRK final (padding) n'est pas inclus
        if op in BRANCH and pc + 1 <= hi:
            rel = B(pc + 1)
            rel -= 256 if rel >= 128 else 0
            if not legal(pc + 2 + rel):
                return False
        if op == JSR and pc + 2 <= hi:
            t = word(pc + 1)
            if lo <= t <= hi and ilen(B(t)) == 0:
                return False
        n += ln
        if op in (RTS, RTI, JMP_ABS, JMP_IND):
            return n >= 3
        pc += ln
    return False


def msg_preview(raw: bytes, addr: int, n: int = 28) -> str:
    """Aperçu ASCII du message pointé (sanitisé pour da65)."""
    if addr == 0:
        return "TODO pointeur nul"
    off = addr - BASE
    if off < 0 or off >= len(raw):
        return "(hors image)"
    out = []
    for c in raw[off:off + n]:
        out.append(chr(c) if 0x20 <= c < 0x7F else ".")
    return "".join(out).replace('"', "'")


def sanitize_comment(doc: str) -> str:
    """Sanitise un résumé ROUTINE_DOCS pour da65 (une ligne, sans guillemet)."""
    return doc.replace('"', "'")


def descend(raw: bytes, lo: int, hi: int, entries: list[int]):
    """Descente récursive. Renvoie (code_bytes, ptrs, starts, ext, conflicts)."""

    def B(a: int) -> int:
        return raw[a - BASE]

    def word(a: int) -> int:
        return B(a) | (B(a + 1) << 8)

    def region(a: int) -> str:
        if lo <= a <= hi:
            return "here"
        if BLOCK1[0] <= a <= BLOCK1[1]:
            return "bloc1"
        if BLOCK2[0] <= a <= BLOCK2[1]:
            return "bloc2"
        if BLOCK3[0] <= a <= BLOCK3[1]:
            return "bloc3"
        if 0xC000 <= a <= 0xFFFF:
            return "rom"
        return "autre"

    from collections import Counter

    code_bytes: set[int] = set()
    ptrs: dict[int, int] = {}
    starts: set[int] = set()
    conflicts: list[int] = []
    ext: Counter = Counter()
    worklist = list(entries)

    while worklist:
        pc = worklist.pop()
        if pc in starts:
            continue
        if pc in code_bytes:
            conflicts.append(pc)
            continue
        if not (lo <= pc <= hi):
            continue
        while lo <= pc <= hi:
            if pc in starts:
                break
            if pc in code_bytes:
                conflicts.append(pc)
                break
            op = B(pc)
            ln = ilen(op)
            if ln == 0:
                break
            if op == JSR and pc + 2 <= hi and word(pc + 1) in INLINE_MSGS:
                for b in range(pc, pc + 3):
                    code_bytes.add(b)
                ptrs[pc + 3] = word(pc + 3)
                starts.add(pc)
                pc += 5
                continue
            for b in range(pc, pc + ln):
                code_bytes.add(b)
            starts.add(pc)
            if op == JSR:
                t = word(pc + 1)
                r = region(t)
                if r == "here" and t not in starts:
                    worklist.append(t)
                elif r != "here":
                    ext[(r, t)] += 1
                pc += 3
            elif op == JMP_ABS:
                t = word(pc + 1)
                r = region(t)
                if r == "here":
                    worklist.append(t)
                else:
                    ext[(r, t)] += 1
                break
            elif op == JMP_IND:
                break
            elif op in (RTS, RTI, BRK):
                break
            elif op in BRANCH:
                rel = B(pc + 1)
                rel -= 256 if rel >= 128 else 0
                t = pc + 2 + rel
                if region(t) == "here":
                    worklist.append(t)
                pc += 2
            else:
                pc += ln
    return code_bytes, ptrs, starts, ext, conflicts


def build_info(raw: bytes, code_bytes: set[int], ptrs: dict[int, int],
               lo: int, hi: int) -> str:
    ptr_addrs = set()
    for p in ptrs:
        ptr_addrs.add(p)
        ptr_addrs.add(p + 1)

    lines = ['GLOBAL { CPU "6502"; PAGELENGTH 0; };']
    code_ranges: list[list[int]] = []
    cur: list[int] | None = None
    for a in range(lo, hi + 1):
        if a in code_bytes and a not in ptr_addrs:
            if cur is None:
                cur = [a, a]
            else:
                cur[1] = a
        else:
            if cur is not None:
                code_ranges.append(cur)
                cur = None
    if cur is not None:
        code_ranges.append(cur)
    named = {**VECTORS, **ROM_LABELS,
             **{a: n for a, (n, _d) in ZP_NAMES.items()}}
    for addr, (name, _doc) in ROUTINE_DOCS.items():
        if name is not None:
            named[addr] = name
    used: set[int] = set()
    range_starts = {a for a, _b in code_ranges}
    for a, b in code_ranges:
        name = named.get(a, f"code_{a:04X}")
        if a in named:
            used.add(a)
        rng = f'RANGE {{ START ${a:04X}; END ${b:04X}; TYPE CODE; NAME "{name}";'
        doc = ROUTINE_DOCS.get(a, (None, None))[1]
        if a in ROUTINE_DOCS and doc:
            rng += f' COMMENT "{sanitize_comment(doc)}";'
        lines.append(rng + " };")
    for p in sorted(ptrs):
        msg = ptrs[p]
        preview = msg_preview(raw, msg)
        comment = "TODO pointeur $0000" if msg == 0 else f"-> ${msg:04X} {preview}"
        lines.append(f"RANGE {{ START ${p:04X}; END ${p + 1:04X}; TYPE WORDTABLE; }};")
        lines.append(f'LABEL {{ NAME "msg_{p:04X}"; ADDR ${p:04X}; COMMENT "{comment}"; }};')
        used.add(p)
    for addr, (name, doc) in sorted(ROUTINE_DOCS.items()):
        if not (lo <= addr <= hi):
            continue
        if addr in range_starts:
            continue  # déjà nommé+commenté via RANGE (LABEL ferait doublon)
        label = name if name is not None else named.get(addr, f"code_{addr:04X}")
        lines.append(f'LABEL {{ NAME "{label}"; ADDR ${addr:04X}; '
                     f'COMMENT "{sanitize_comment(doc)}"; }};')
        used.add(addr)
    marked = set(code_bytes) | ptr_addrs
    cur = None
    pending: list[list[int]] = []
    for a in range(lo, hi + 1):
        if a not in marked:
            if cur is None:
                cur = [a, a]
            else:
                cur[1] = a
        else:
            if cur is not None:
                pending.append(cur)
                cur = None
    if cur is not None:
        pending.append(cur)
    for ga, gb in pending:
        kind = "TEXTTABLE" if printable_ratio(raw, ga, gb) >= 0.55 else "BYTETABLE"
        lines.append(f"RANGE {{ START ${ga:04X}; END ${gb:04X}; TYPE {kind}; }};")
    for addr, name in named.items():
        if addr not in used:
            doc = ZP_NAMES.get(addr, (None, None))[1]
            if doc:
                lines.append(f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; '
                             f'COMMENT "{sanitize_comment(doc)}"; }};')
            else:
                lines.append(f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; }};')
    return "\n".join(lines) + "\n"


def main() -> int:
    import subprocess

    if not BIN.exists():
        print(f"{BIN} manquant : lancez scripts/extract.py")
        return 1
    DISASM.mkdir(exist_ok=True)
    raw = BIN.read_bytes()
    lo, hi = BLOCK4

    def B(a: int) -> int:
        return raw[a - BASE]

    vec_targets = [B(0x2C05 + 3 * k + 1) | (B(0x2C05 + 3 * k + 2) << 8) for k in range(16)]
    entries = [0x2C00, ENTRY] + vec_targets + MANUAL_ENTRIES
    r2seeds = load_r2_seeds(R2CACHE)

    for it in range(10):
        code_bytes, ptrs, starts, ext, conflicts = descend(raw, lo, hi, entries)
        ptr_bytes = set()
        for p in ptrs:
            ptr_bytes.add(p)
            ptr_bytes.add(p + 1)
        added = 0
        for s in r2seeds:
            if not (lo <= s <= hi):
                continue
            if s in SEED_EXCLUDE:
                continue
            if s in starts or s in code_bytes or s in ptr_bytes:
                continue
            if s in entries:
                continue
            if try_decode(raw, lo, hi, s, starts, code_bytes | ptr_bytes):
                entries.append(s)
                added += 1
        print(f"  itération {it}: {len(code_bytes)} octets code, +{added} entrées")
        if not added:
            break

    INFO.write_text(build_info(raw, code_bytes, ptrs, lo, hi))

    print(f"bloc4 ${lo:04X}-${hi:04X} : {len(code_bytes)} octets code, "
          f"{len(ptrs)} pointeurs inline ($440D/$5B24), "
          f"{len(set(conflicts))} conflits")
    if conflicts:
        print("  conflits :",
              ", ".join(f"${a:04X}" for a in sorted(set(conflicts))[:12]))
    print("  références externes (top) :")
    for (r, t), n in ext.most_common(12):
        print(f"    {r} ${t:04X} x{n}")
    nulls = [p for p, m in ptrs.items() if m == 0]
    print(f"  pointeurs nuls : {len(nulls)}",
          ", ".join(f"${p:04X}" for p in sorted(nulls)))

    if not DA65.is_file():
        print(f"{DA65} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)")
        return 1
    slice_path = Path("/tmp/hobbit_block4.bin")
    slice_path.write_bytes(raw[lo - BASE:hi - BASE + 1])
    subprocess.run(
        [str(DA65), "-i", str(INFO), "-S", f"0x{lo:x}", "-o", str(LISTING), str(slice_path)],
        check=True,
    )
    # En-tête da65 volatil (date d'extraction) : on le neutralise pour un
    # listing déterministe (seule la ligne de version est conservée).
    asm = LISTING.read_text().splitlines(keepends=True)
    asm = [ln for ln in asm
           if not ln.startswith("; Created:")
           and not ln.startswith("; Input file:")
           and not ln.startswith("; Page:")]
    header = (
        "; ============================================================\n"
        "; The Hobbit (Oric, 1982) - bloc 4 ($2C00-$7A80)\n"
        "; Listing généré par scripts/disasm.py (descente récursive + da65)\n"
        "; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.\n"
        "; Convention : JSR $440D + pointeur inline (2 octets, adresse du\n"
        "; message) ; reprise du code à JSR+5.\n"
        "; ============================================================\n\n"
    )
    LISTING.write_text(header + "".join(asm))
    print(f"Listing écrit : {LISTING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
