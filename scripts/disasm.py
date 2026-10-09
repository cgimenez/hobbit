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

from opcodes6502 import (
    BRANCH,
    JMP_ABS,
    JMP_IND,
    JSR,
    INLINE_MSGS,
    PRINT_MSG,
    RTI,
    RTS,
    BRK,
    ilen,
)
from msgdecode import decode_message

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
    + [
        0x32B9,
        0x3C8E,
        0x5B44,
        0x5BC9,
        0x5D31,
        0x698B,
        0x6A02,
        0x6EA7,
        0x6D55,
        0x6F2A,
        0x4599,
        0x4DAF,
    ]
    + [
        0x32E9,
        0x3CCE,
        0x3D39,
        0x4569,
        0x6A12,
        0x6A24,
        0x6A5E,
        0x6A86,
        0x6F44,
        0x6F7E,
        0x70D2,
        0x6DD0,
    ]
    # Actions dispatchees par les tables L7014/L7143 (indirect -> hors
    # descente). Cf. docs/block4-analysis.md.
    + [
        0x65DD,
        0x65BA,
        0x65B6,
        0x65F1,
        0x66D6,
        0x68D0,
        0x68E0,
        0x690C,
        0x692D,
        0x6936,
        0x6962,
        0x6B72,
        0x6C09,
        0x6C33,
        0x6C8D,
        0x6CBE,
        0x6CFA,
    ]
    # Suite contigue des handlers d'actions (orphelins confirmes code
    # par le checker, regle D : decode >=85%).
    + [
        0x65E3,
        0x6607,
        0x6629,
        0x6666,
        0x66AA,
        0x6902,
        0x6903,
        0x6915,
        0x6B00,
        0x6B27,
        0x6B55,
        0x6BDB,
        0x6C5F,
        0x6C79,
        0x6CDB,
        0x6D3D,
        0x6D9F,
    ]
    # Handler du token $09 ($456F, table $4641) : sans seed, la plage
    # code_436C s'arrete au RTS $456E et $456F-$4572 tombent en donnees
    # (le JMP patche est indirect, invisible de la descente).
    + [0x456F]
    # Stubs d'armement des evenements $2B12 en zones donnees : $65A5
    # (cpt e3, queue jsr $6222+$4D95) et $70B5 (cle $16 : ecrit entite
    # $2B61). Seuls des STA $2Bxx les trahissent (scan binaire complet).
    + [0x65A5, 0x70B5]
    # Handlers SAVE/LOAD + ecriture cassette ($3D3F-$3E40) : atteints
    # uniquement via le dispatch indirect des commandes speciales
    # (table $3BC6/$3BE0, jmp (L3BC4)). Cf. docs/block4-analysis.md.
    + [0x3D3F, 0x3D7F, 0x3DAA, 0x3DBC, 0x3DC4, 0x3DD9, 0x3E20]
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
    0x2C35: (
        None,
        "Point d'entree : copie la zone sauvegarde, vide la pile, reinitialise les variables, affiche le prompt puis boucle de commandes",
    ),
    0x2DC8: ("init_vars", "Remet a zero les variables de travail ($97.., $AF, $CC/$CD) puis saute a la boucle principale ($7779)"),
    0x3097: ("boot_copy", "Copie le bloc sauvegarde $1B1A -> $91D0 (1366 octets) ; $6C = compteur"),
    0x30BB: ("boot_copyback", "Recopie le bloc $91D0 -> $1B1A (copie inverse, meme gabarit)"),
    0x440D: (
        "print_msg",
        "Affiche le message dont l'adresse suit l'appel, puis reprend l'execution apres ce mot (appel de 5 octets)",
    ),
    0x44BE: ("msgptr_inc", "Avance le pointeur de message courant $6A/$6B de 1 (gere la retenue)"),
    0x4C82: (
        "is_dark",
        "Renvoie 1 si le lieu est sombre : aucune source de lumiere allumee (bit7 de +4, ou +7=$08/$04/$40) dans un objet porte ; sinon affiche 'IT IS DARK.'",
    ),
    # Moteur de messages (decodeur valide par reimplementation Python : les
    # 32 mots $1117 et le dictionnaire 5-bit sortent en anglais propre).
    0x4444: (
        "render_text",
        "Rend un message octet par octet : litteraux $20-5F, mots courants $60-7F, mots 2 octets (bit7), tokens <$20",
    ),
    0x4241: (
        "word_render",
        "Rend un mot du dictionnaire packe 5-bit, en appliquant pluriels (S/ES/IES/ING), espaces et retour a la ligne",
    ),
    0x462D: (
        "common_lookup",
        "Traduit un octet $60-7F en mot courant via la table $1117 (the/a/and/you/to/...)",
    ),
    0x4641: (
        "token_jumps",
        "Table des 32 tokens <$20 : tokens <$14 = sous-routines (retour Z = saute word_render), $14/$15/$16 = fins",
    ),
    0x44A0: (
        "token_dispatch",
        "Saut auto-modifie vers le handler du token (adresse lue dans la table $4641)",
    ),
    0x44AE: ("text_end", "Dernier octet du message : $2x = fin simple, $3x = fin + '.', $6x = fin + retour a la ligne"),
    0x44C5: ("tok_nested", "Token $00 : affiche le message imbrique depile de la pile ($466F) ; retour Z = saute word_render"),
    0x44F5: ("tok_stkword", "Token $01 : affiche le mot dont l'adresse est empilee ($466F)"),
    0x44FB: (
        "tok_skip",
        "Token $02 : saut (GOTO) a l'offset signe qui suit, sans revenir (deplace le pointeur du message)",
    ),
    0x4504: (
        "tok_noop",
        "Tokens $05/$0A/$0F/$12 non utilises : aucun effet, on passe au suivant",
    ),
    0x452E: ("tok_objw", "Token $03 : affiche le mot pointe par le pointeur de travail $71/$72"),
    0x4539: (
        "tok_stkvar",
        "Token $04 : variante du mot empile (lecture dans les tables $28BC/$28C4 si contexte imbrique)",
    ),
    0x454B: (
        "tok_objC5",
        "Token $06 : affiche le nom de l'objet courant $C5 (via $461B)",
    ),
    0x4557: (
        "tok_obj15",
        "Token $07 : affiche l'objet $15 (selon les tables direct $43E4 ou variante $43F3)",
    ),
    0x4569: ("tok_ctrl08", "Token $08 : envoie le code $08 a la sortie video (vecteur $2C2F)"),
    0x456F: ("tok_obj16", "Token $09 : affiche l'objet $16 (variante)"),
    0x4599: (
        "tok_recurse",
        "Token $0B : reaffiche un texte a l'offset signe qui suit, puis revient (queues de messages partagees)",
    ),
    0x45B0: (
        "tok_pronC5",
        "Token $0C : pronom possessif 'his' si l'objet $C5 existe, 'your' sinon",
    ),
    0x45CA: ("tok_pron15", "Token $0E : meme chose que $0C mais pour l'objet $15"),
    0x45CF: (
        "tok_nameC5",
        "Token $10 : nom de l'objet $C5 ('is' si absent, 'someone' si $FF)",
    ),
    0x45F4: ("tok_name15", "Token $11 : nom de l'objet $15 (variante imbriquee)"),
    0x45FC: ("tok_nameSTK", "Token $13 : nom de l'objet dont l'adresse est empilee"),
    0x44E4: ("stk_pop", "Depile une adresse de la pile de messages ($466F) vers $5C/$5D"),
    0x460A: (
        "nested_render",
        "Affiche un message imbrique en sauvant/restaurant l'etat de rendu (pile $0200)",
    ),
    0x461B: ("obj_lookup", "Identifiant d'objet -> mot : $FF = someone, sinon nom de l'objet"),
    0x46DB: ("cr_aware_out", "Affiche un caractere ; retour Z si c'est un retour a la ligne $0D"),
    0x42CE: (
        "word_space",
        "Gere les espaces entre mots et le retour a la ligne en fin de colonne",
    ),
    # Evenements differes : table $2B12 (entrees de 5 octets [id,cpt,actA,cond,actB],
    # terminee par $FF), balayee par world_tick ; actions via la table de sauts $7169.
    0x4E75: ("evt_tick", "Balaye la table $2B12 : decremente les compteurs, re-arme et declenche les actions"),
    0x4E9D: ("evt_cond", "Si la condition est armee et que cpt l'atteint : execute l'action de l'entree"),
    0x4EAB: ("evt_fire", "Ecrit l'action a executer depuis la table $7169 puis l'appelle (L4C5D)"),
    0x4ECC: ("evt_end", "Fin de la table ($FF) : signale la fin ($0B=1) et sort"),
    0x5DE2: ("evt_lookup", "Trouve l'evenement associe a la cle $8F (table $709F), sinon $5DFD"),
    0x6689: ("evt_disarme6", "Desarme l'evenement e6 (cpt := 0) et pose son bit de drapeau"),
    0x66AA: ("evt_arme6", "Arme l'evenement e6 : cpt := 2 + aleatoire(8) (delai aleatoire)"),
    0x65A5: ("evt_arme3", "Arme l'evenement e3 (cpt := id) apres avoir appele $6222 et $4D95"),
    0x6A19: ("evt_disarme7", "Si $C5 vaut 0 : pose $C4:=1 et desarme l'evenement e7"),
    0x6AEB: ("evt_arme9b", "Arme l'evenement e9 (cpt := 6), pose les drapeaux $1C7B, saute a $6D72"),
    0x6B66: ("evt_arme5", "Arme l'evenement e5 (cpt := id) et affiche 'magic door' ($168B)"),
    0x6C5F: ("evt_act5", "Action de l'evenement e4 : si au marais ($C8==$1D) affiche $1535, sinon desarme e4"),
    0x6D72: ("evt_print", "Affiche le trou qui disparait ($1685)"),
    0x6915: ("evt_tip", "Sonde et tirage : ~20% de chance d'afficher 'expect me' ($1485)"),
    0x70B5: ("evt_arme16", "Cle $16 : si le drapeau $1DC5 vaut 8, place une entite ($2B61:=$42) et arme"),
    0x70CB: ("evt_arme2", "Arme l'evenement e2 (cpt := id) ; cle $1A"),
    0x70D2: ("evt_arme4", "Arme l'evenement e4 (cpt := id) ; cle $1D"),
    0x70D9: ("evt_arme9", "Arme l'evenement e9 (cpt := 3) et ecrit les entites $2B76/$2B7D ; cle $20"),
    0x70F8: ("evt_arme8", "Cle $02/$03 : copie $8F dans $BE et arme l'evenement e8"),
    0x7103: ("evt_gate21", "Cle $21 : si $1B1B vaut $13, declenche $5DFD et affiche"),
    0x4E59: (
        "world_tick",
        "Fait vivre le monde apres une commande : entites (VM), evenements differes $2B12",
    ),
    # Commandes speciales : table $3BC6 (13 cles [lo,hi&$0F]) + $3BE0
    # (13 cibles, jmp (L3BC4)) ; SAVE=$3DD9 (mot $0DA0), QUIT=$3C88,
    # HELP=$3C8E, SCORE=$3CCE, PAUSE=$3D39. Zone $3D3F-$3E40 atteinte
    # uniquement par ce dispatch (MANUAL_ENTRIES).
    0x3D3F: (
        "tape_tramp",
        "Trampoline cassette : lit [longueur, source] apres l'appel et saute au handler",
    ),
    0x3D7F: (
        "load_handler",
        "Commande LOAD : invite 'PRESS ANY KEY' puis charge un bloc cassette (vec_02)",
    ),
    0x3DAA: (
        "save_block",
        "Ecrit un bloc SAVE sur cassette (appel vec_03 avec [longueur, source] inline)",
    ),
    0x3DBC: (
        "save_err",
        "Echec de SAVE : affiche l'erreur $1A1A, attend une touche puis abandonne",
    ),
    0x3DD9: (
        "cmd_save",
        "Commande SAVE : ecrit les 4 blocs (ZP, etats, scripts, records) puis verifie",
    ),
    0x3E20: (
        "cmd_next",
        "Restaure le contexte et revient a la boucle de commandes",
    ),
    0x4ED5: (
        "entity_tick",
        "Fait tourner une entite (machine virtuelle) : execute jusqu'a 6 opcodes par tick",
    ),
    0x5020: ("script_adv", "Avance le pointeur de script $8C de A octets"),
    0x502A: ("script_step4", "Avance le pointeur de script de 4 (+2 si le bit $10 est pose)"),
    0x502C: ("script_step2", "Avance le pointeur de script de 2 (+2 si le bit $10 est pose)"),
    0x511C: ("entity_move", "Deplace une entite ($13/$15/$16) et affiche sa sortie si elle est visible"),
    0x5249: ("entity_goto", "Positionne le pointeur de script d'une entite depuis ($8A)+1..2"),
    0x5279: ("say_if_visible", "Affiche un message si l'entite partage le lieu du joueur"),
    0x36DB: ("move_core", "Coeur du deplacement : resout la sortie, evalue la condition, execute"),
    0x43CB: ("exit_ptr", "Calcule $F8 = $26DA + wid*8 : pointe l'entree de sortie du lieu"),
    0x3759: ("cond_eval", "Evalue la condition d'une sortie (slot X ; $FF = aucune)"),
    0x3770: ("move_flags", "Derive les drapeaux direct/variante depuis l'octet mode $78"),
    0x5386: ("act_probe", "Mode sonde : soit execute (phase 1), soit annule et signale la reussite ($12=1)"),
    0x56D7: ("rand_range", "Tirage pseudo-aleatoire borne par A (source de bruit $93)"),
    0x5B24: ("act_msg", "Affiche le message d'action $13E8 puis execute l'epilogue"),
    # Actions dispatchees par la table L7014 (index 0-14), declenchees par
    # les verbes du joueur (L4B37). Effets deduits du flot et des messages.
    0x5CA9: ("act_p14_04", "Objet $15 : teste ses drapeaux puis le prend ou le pose"),
    0x5CB6: ("act_p14_14", "Objet $C5 : teste ses drapeaux puis bascule son etat"),
    0x5D06: ("act_p14_05", "Objet : compare a un seuil (($8A)+2), le deplace et fixe $13/$15"),
    0x6041: (
        "act_p14_13",
        "Drapeaux de l'objet ($19) bits 0-2 : affiche 'swept away' ($11D3) ou 'X dead' ($13D1)",
    ),
    0x60BF: (
        "act_p14_00",
        "Combat : applique les degats, consomme le compteur puis affiche 'KILLED' ($1525)",
    ),
    0x60ED: (
        "act_p14_01",
        "Deplacement de l'objet (bits de $78), ecrit les pointeurs de rendu $75/$70/$5C/$5D",
    ),
    0x61C9: ("act_p14_02", "Objet ($17) : remet a 0 le bit5 de ($8A)+7, sinon branche $5A9D"),
    0x61E5: ("act_p14_07", "Objet $16 : lit le bit5 de ($88)+7 et branche a $5A90"),
    0x6222: (
        "act_p14_03",
        "Pose le bit5 de ($8A)+7 ; si id==1, declenche la fete ($580F : foule en liesse... coucher de soleil)",
    ),
    0x65B6: ("act_p14_12", "Repartit l'objet $16 (cas $0F) vers $65DD/$641D/$6448"),
    0x65BA: ("act_p14_08", "Repartit l'objet $16 (cas $04) vers $65DD/$4C57"),
    0x65DD: (
        "act_p14_06",
        "Affiche 'X do not fit this lock' ($140C), sinon 'i cannot do that' ($139B)",
    ),
    0x65F1: ("act_p14_10", "Si ((crec)+16)==$0F saute a $6222, sinon a $5A62"),
    0x66D6: ("act_p14_11", "Affiche 'spiders mend the web' ($1478) et arme l'evenement e1"),
    0x6B72: (
        "act_p14_09",
        "Si $C5==$41 : parcourt la table ($C1) et affiche 'go...from...to' ($13E0/$15AB)",
    ),
    # Actions dispatchees par la table L7143 (index 0-14) : comportements
    # autonomes des PNJ dans la VM $4ED5.
    0x68D0: ("act_v14_06", "Si au meme lieu que le joueur : affiche 'hello' ($143F)"),
    0x68E0: (
        "act_v14_01",
        "PNJ oisif : 'great job' ($1432) / 'hurry up' ($143B) / 'hello' ($143F)",
    ),
    0x690C: ("act_v14_02", "Affiche 'thrains key' ($1441)"),
    0x692D: ("act_v14_00", "Affiche 'WHAT'S this ?' ($1427)"),
    0x6936: ("act_v14_04", "Tirage 0-7 : appelle $4D9E, decremente ($14) et affiche $143B"),
    0x6962: (
        "act_v14_03",
        "Si au meme lieu et que le bit7 de $1B21 est clair : affiche 'WHERE'S the thief ?' ($14AB)",
    ),
    0x697A: ("act_v14_05", "Si $C8==$1DE0 : appelle $4D9E et ajuste ($14)"),
    0x6C09: ("act_v14_12", "Gollum : si $1E4B==$C8 et drapeau pause, affiche un message (patche)"),
    0x6C33: (
        "act_v14_11",
        "One-shot (verrou $CE==1) : remet $CE a zero et copie $14/$15 vers $2A7B",
    ),
    0x6C8D: ("act_v14_09", "Si $C8 vaut 27, 2C ou 29 : affiche 'X enter' ($13F6)"),
    0x6CBE: (
        "act_v14_10",
        "Dragon au meme lieu : 'PREPARE TO DIE' ($153F) ou 'aveugle' ($155D)",
    ),
    0x6CFA: ("act_v14_07", "Si au meme lieu : prend l'objet $1FC1 (id 41)"),
    0x6D78: (
        "act_v14_14",
        "Gollum et l'Anneau : si $C8==$1E4B, tirage entre 'pocket?' ($16B9) et 'my precious' ($16C8)",
    ),
    0x6DF9: ("act_v14_13", "Cherche un lieu, remet $D5 a zero et affiche 'strangle you' ($15B6)"),
    0x6E59: (
        "act_v14_08",
        "Smaug : si $1F47!=$29, tirage 0-100 entre 'dragon flying' ($1582) et 'burn you' ($1596)",
    ),
    0x6E8B: (
        "act_v14_15",
        "Trolls au lieu 5 : si $C5==$47 affiche 'BLIMEY, COOK EM' ($1615), sinon 'MOUTHFUL' ($162B)",
    ),
    0x6CDB: ("act_v14_16", "Si au meme lieu : simule un combat (wid=$1B/arg1=0) puis saute a $5FAE"),
    0x6EA7: (
        "act_v14_17",
        "Efface des drapeaux ($1F94/$1FA6), met a jour une description de lieu et affiche $16EB",
    ),
    0x4737: ("fetch_retaddr", "Copie sur $8A/$8B l'adresse de retour empilee (routine appelee par JSR)"),
    0x71DB: ("tape_load", "Charge un bloc cassette via le loader ROM $0417 et verifie l'en-tete"),
    0x7215: ("tape_save", "Ecrit un bloc cassette : leader, en-tete (9 o), donnees, checksum EOR"),
    0x72A0: ("tape_prompt", "Affiche les invites 'PREPARE TAPE' / 'REWIND' / 'PRESS ANY KEY'"),
    0x7353: ("kb_scan", "Scanne le clavier ; A = touche si le bit7 est pose, sinon bit7=0 (pas de touche)"),
    0x7481: ("kb_wait", "Attend une touche (bloquant) et renvoie son code sans le bit7"),
    0x7489: ("cr_out", "Affiche un retour a la ligne ($0D)"),
    0x7491: ("ch_out", "Point d'entree d'affichage : filtre certains codes et passe au rendu ecran"),
    0x75B4: ("glyph_out", "Dessine un caractere en mode hires ($A000) avec la police ROM"),
    0x75F6: ("ch_put", "Affiche un caractere : gere retour a la ligne, scroll et pause de bas d'ecran"),
    0x7619: (
        "pause_key",
        "Toutes les 16 lignes, attend une touche (avec delai) pour pause, sinon incremente le compteur",
    ),
    0x7747: ("hires_clear", "Efface l'ecran hires $A000-$BFDF (remplit de $40)"),
    0x7779: ("game_main", "Boucle principale du jeu (atteinte via le vecteur vec_15)"),
    # Moteur d'illustrations vectorielles (consomme le bloc 3 : table $7AC0
    # [cle,mot] x13 + flux d'octets termine par $00 ; valide par rendu sim65 des
    # 13 images via un pilote vec_init + dump hires).
    0x4750: (
        "img_show",
        "Affiche l'illustration associee a la cle A (table $7AC0) ; retour Z si absente",
    ),
    0x77D4: (
        "vec_image",
        "Dessine une illustration : prepare l'ecran ($7990) puis interprete le flux de trace",
    ),
    0x7824: (
        "vec_fill",
        "Remplissage : balaye la zone avec la couleur $40 sur les compteurs $32-$36",
    ),
    0x78C9: ("vec_pos", "Instruction $08 : place le curseur en $30/$31 (2 octets)"),
    0x78DA: ("vec_skip", "Instruction $20 : saute jusqu'a l'octet $FF"),
    0x78E4: (
        "vec_line",
        "Instruction de trace : segment (bit7, 2 o : drapeaux+longueur, pas), dessine pixel par pixel",
    ),
    0x7990: (
        "vec_setup",
        "Efface l'ecran hires $A000-$B3FF et applique les aplats selon l'octet de mode",
    ),
    0x79FB: ("vec_testpx", "Teste la validite du pixel ($30/$31) : renvoie $FF hors des bornes $0E-$F2"),
    0x7A0F: ("vec_plot", "Allume le pixel ($30/$31) via la ligne ($38/$39) et le masque L7A5F"),
    0x7A22: ("vec_addr", "Calcule l'adresse et le masque du pixel ($30/$31) dans l'ecran hires"),
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
    0x04: (
        "col",
        "Colonnes restantes sur la ligne courante (remis a jour a chaque ligne ; sert au retour auto)",
    ),
    0x0B: ("outen", "Autorise l'affichage (1 = la sortie texte est autorisee)"),
    0x0C: ("phase", "Phase d'execution : 0 = sonde (simulation), 1 = execution reelle"),
    0x0D: ("raw", "Mode brut : 1 = texte force sans mise en forme (limite de colonnes, capitales)"),
    0x0E: ("cap", "Capitaliser la prochaine lettre affichee (pose apres un point)"),
    0x0F: ("sppend", "Espace en attente a inserer avant le prochain mot"),
    0x11: ("crcnt", "Compteur de lignes depuis la derniere pause (modulo 16)"),
    0x12: ("passok", "Reussite d'une sonde : 1 = passer a l'execution reelle"),
    # Operandes de commande (parser L359B, VM L5048/L50AC, $FF=absent).
    0x13: ("wid", "Mot/identifiant courant (verbe d'action ou direction)"),
    0x15: ("arg1", "Premier objet de la commande ($FF = aucun)"),
    0x16: ("arg2", "Second objet de la commande ($FF = aucun)"),
    # Enregistrements d'objets (deref ($..),y ; swap L57A1).
    0x17: ("orec", "Pointeur vers l'enregistrement du premier objet (octet haut en $18)"),
    0x19: ("orec2", "Pointeur vers l'enregistrement du second objet (octet haut en $1A)"),
    0xC6: ("crec", "Pointeur vers l'enregistrement courant (contexte/compteurs, base $1B1A)"),
    # Moteur de messages (render_text, tokens, pile $466F/$0200).
    0x5C: ("adr", "Adresse de travail : mot de message pointe (octet haut en $5D)"),
    0x6F: ("tidx", "Index du caractere en cours dans le message affiche"),
    0x70: ("nest", "Niveau d'imbrication du rendu (0 = message simple)"),
    0x71: ("wptr", "Pointeur vers le mot/nom en cours de rendu (octet haut en $72)"),
    0x76: ("msgstk", "Index de la pile de messages $466F (remis a zero a chaque message)"),
    0xAD: ("svA", "Sauvegarde de l'accumulateur A (routines utilisant la pile $0200)"),
    0xAE: ("svX", "Sauvegarde du registre X (routines utilisant la pile $0200)"),
    0xAF: ("rstk", "Index de la pile d'adresses de retour $0200"),
    # Mouvement (exit_ptr, code_4141, move_flags, cond_eval).
    0x73: ("direct", "Sortie directe sans controle (copie du bit7 de xmode)"),
    0x74: ("variant", "Sortie en variante (copie du bit6 de xmode)"),
    0x77: ("xaux", "Octet auxiliaire de sortie (drapeaux de mise en forme)"),
    0x78: ("xmode", "Octet de mode de sortie (bit7 = direct, bit6 = variante)"),
    0xDC: ("cond1", "Tampon de condition 1 (6 octets $DC-$E1)"),
    0xE2: ("cond2", "Tampon de condition 2 (6 octets $E2-$E7)"),
    0xE8: ("svptr", "Sauvegarde du pointeur ptr (contexte de deplacement, octet haut en $E9)"),
    0xF8: ("exitp", "Curseur dans la table des sorties du lieu ($26DA + wid*8)"),
    # Pointeurs de travail universels.
    0x7A: ("ptr3", "Troisieme pointeur de travail (octet haut en $7B)"),
    0x88: ("ptr2", "Pointeur secondaire, pour balayer les tables (octet haut en $89)"),
    0x8A: ("ptr", "Pointeur de travail universel (octet haut en $8B)"),
    # Monde (entites, events, tirage).
    0x8F: ("key", "Cle d'evenement a declencher (cherchee dans la table $709F)"),
    0x93: ("noise", "Pointeur vers la source de bruit (entropie des tirages aleatoires)"),
    0xBE: ("exploc", "Lieu attendu par l'evenement (copie de key, compare a ploc)"),
    0xC5: ("obj", "Objet/entite courant (id ; $FF = une personne)"),
    0xC8: ("ploc", "Lieu du joueur : simple miroir de player.eloc ($1B2A), pas la source"),
    0xC9: ("eloc", "Lieu d'une entite (visible quand eloc==ploc)"),
    0xCE: ("once", "Verrou one-shot : pose puis consomme pour n'agir qu'une fois"),
    # Octets hauts des paires (da65 ne rend pas `nom+1` : nommage explicite).
    0x18: ("orec_hi", "Octet haut de orec"),
    0x1A: ("orec2_hi", "Octet haut de orec2"),
    0x5D: ("adr_hi", "Octet haut de adr"),
    0x72: ("wptr_hi", "Octet haut de wptr"),
    0x7B: ("ptr3_hi", "Octet haut de ptr3"),
    0x89: ("ptr2_hi", "Octet haut de ptr2"),
    0x8B: ("ptr_hi", "Octet haut de ptr"),
    0x94: ("noise_hi", "Octet haut de noise"),
    0xC7: ("crec_hi", "Octet haut de crec"),
    0xE9: ("svptr_hi", "Octet haut de svptr"),
    0xF9: ("exitp_hi", "Octet haut de exitp"),
}

# Notes detaillees (multi-lignes) inserees AVANT le label d'une routine,
# en complement du resume une ligne de ROUTINE_DOCS. Servent a expliquer le
# FONCTIONNEMENT (algorithme, entree/sortie, effets), pas seulement le but.
# Cles = adresses de routines nommees (via ROUTINE_DOCS/VECTORS).
ROUTINE_NOTES: dict[int, list[str]] = {
    0x4ED5: [
        "Fait jouer le script d'un personnage : son 'cerveau'. Chaque personnage a une petite",
        "suite d'instructions (se deplacer, parler, attendre, choisir au hasard) qui s'execute",
        "un peu a chaque tour, meme quand le joueur est ailleurs.",
        "Technique : table $2B45 (17 entrees de 7 octets, fin $FF) ; nibble bas de l'opcode =",
        "MOVE 0-4 / INDIR 5-D / GOTO E / PATCH C / RANDOM F ; au plus 6 opcodes par tick (L4ED3).",
    ],
    0x2C35: [
        "Point de depart du jeu, juste apres le chargement de la cassette.",
        "Il met de cote l'etat de depart, prepare la memoire, puis entre dans la grande boucle",
        "du jeu : afficher la situation, lire la commande du joueur, faire avancer le monde.",
        "Technique : boot_copy, init de la pile, RAZ des variables, puis game_main.",
    ],
    0x2DC8: [
        "Remet a zero les compteurs de depart (variables de travail, pile de messages, score)",
        "juste avant de lancer la partie.",
        "Technique : $97-$9C = 0, rstk $AF = 0, score $CC/$CD = 0, puis jmp game_main.",
    ],
    0x3097: [
        "Le jeu ne travaille jamais directement sur la cassette : il en recopie le contenu en",
        "memoire haute et joue sur cette copie (le TAPE reste intact et rechargeable).",
        "Cette routine fait la copie initiale sauvegarde -> memoire de travail.",
        "Technique : table de 4 descripteurs en $30F9 ; $6C = nombre de segments.",
    ],
    0x30BB: [
        "Copie en sens inverse : ramene la memoire de travail vers la zone de sauvegarde",
        "(par exemple avant d'ecrire sur la cassette).",
        "Technique : meme table de descripteurs que boot_copy.",
    ],
    0x440D: [
        "Affiche un message. Le message n'est pas passe en argument : son adresse est ecrite",
        "juste apres l'instruction d'appel, dans le programme. print_msg la lit a cet endroit,",
        "affiche le texte, puis reprend l'execution juste apres.",
        "Technique : l'adresse est le mot de 2 octets suivant JSR ; reprise a JSR+5 via jmp ($6A).",
    ],
    0x4444: [
        "Traduit en caracteres le texte compresse d'un message. Un message est une suite de",
        "codes : des lettres telles quelles, des mots courants (the, a, you...), des mots du",
        "dictionnaire, et des marqueurs qui inserrent un nom d'objet ou terminent la phrase.",
        "Technique : $20-$5F = litteral ; $60-$7F = mot courant ($1117) ; bit7 = mot 2 octets",
        "(word_render) ; <$20 = token ($4641).",
    ],
    0x4241: [
        "Affiche un mot du dictionnaire. Pour gagner de la place, les lettres sont stockees sur",
        "5 bits ; cette routine les reconstitue, ajoute la terminaison (pluriel, -ing...), gere",
        "l'espace et le retour a la ligne.",
        "Technique : adresse = page ($05 + (hi&$0F)) : lo ; nibble haut de hi = grammaire",
        "(suffixe $4322, espace, capitale $70, fin $2x/$3x/$6x).",
    ],
    0x462D: [
        "Raccourci pour les mots les plus frequents (the, a, and, you...) : un seul octet suffit",
        "a designer le mot, qui est ensuite affiche par le rendu normal.",
        "Technique : octet $60-$7F -> entree de la table $1117 (pointeur de mot).",
    ],
    0x42CE: [
        "Gere les espaces entre les mots et coupe la ligne quand on arrive au bord de l'ecran.",
        "Technique : insere l'espace en attente puis retour a la ligne quand X >= largeur ($04/$05).",
    ],
    0x44AE: [
        "Termine proprement un message : affiche le dernier mot puis applique la ponctuation",
        "finale demandee (rien, un point, ou un saut de ligne).",
        "Technique : $6x = saut de ligne, $3x = point, $2x = rien.",
    ],
    0x44BE: [
        "Petit utilitaire : avance d'un cran le pointeur de lecture du message courant.",
        "Technique : INC $6A, + $6B si retenue.",
    ],
    0x4641: [
        "Annuaire des marqueurs speciaux d'un message (codes inferieurs a $20). Chaque code",
        "renvoie vers la routine qui sait le traiter : inserer un nom d'objet, un pronom, un",
        "retour a la ligne, ou terminer le message.",
        "Technique : 32 entiers de 2 octets ; <$14 = sous-programmes, $14/$15/$16 = fin, $17-$1F vides.",
    ],
    0x36DB: [
        "Coeur du deplacement : quand le joueur demande a aller quelque part, cette routine",
        "retrouve la sortie correspondante du lieu, verifie ses eventuelles conditions (objet",
        "requis, passage cache...), puis effectue ou refuse le deplacement.",
        "Technique : exit_ptr(wid), flags via code_4141, conditions cond1/cond2 via cond_eval,",
        "execution en mode sonde (L4B37) ou en deux temps (L35E4).",
    ],
    0x3759: [
        "Prepare la condition a remplir pour emprunter une sortie : une sortie peut etre cachee,",
        "verrouillee, ou dependre d'un objet. S'il n'y a pas de condition (X = $FF), rien a verifier.",
        "Technique : A = drapeau direct ; 0 -> fiche du lieu (etat+8, L43F3), sinon fiche de l'objet",
        "(record+2, L43E4). Renvoie A=1 (Z clair) si une condition existe.",
    ],
    0x3770: [
        "Range les options de la sortie sous forme de drapeaux simples (sortie directe ou en",
        "variante) que la suite du deplacement consultera.",
        "Technique : direct = bit7 de xmode, variant = bit6, $7F = bit6 de xaux, $80 = bit0 de xmode.",
    ],
    0x43CB: [
        "Retrouve la fiche de la sortie demandee : chaque lieu a une liste de sorties stockee en",
        "table ; cette routine calcule l'adresse de l'entree voulue (utilisee ensuite pour le",
        "deplacement et pour lire les conditions).",
        "Technique : $F8/$F9 = $26DA + wid*8 (entrees de 8 octets).",
    ],
    0x4E59: [
        "Fait vivre le monde autour du joueur : chaque personnage joue son script (il se deplace,",
        "parle...), et les evenements differes se declenchent (un PNJ qui arrive, une porte qui",
        "s'ouvre...). Appele apres chaque commande reussie.",
        "Technique : L69E7, entity_tick (VM des PNJ), puis evt_tick (table $2B12).",
    ],
    0x4E75: [
        "Parcourt la liste des evenements differes. Chaque evenement a un compte a rebours :",
        "quand il atteint zero, l'action prevue se declenche ; sinon on peut tester une condition.",
        "Technique : table $2B12, entrees de 5 octets [id, cpt, actA, cond, actB], fin $FF ;",
        "cpt==0 -> suivante ; cpt-- ; a 0 -> actA (evt_fire), sinon evt_cond.",
    ],
    0x4E9D: [
        "Teste la condition d'un evenement en cours : si elle est remplie, l'action associee",
        "s'execute.",
        "Technique : si cond (octet 3) != 0 et cond >= cpt -> evt_fire (actB, octet 4).",
    ],
    0x4EAB: [
        "Declenche l'action d'un evenement : va chercher son adresse dans une table, puis l'execute.",
        "Technique : table de sauts $7169 (index*2) -> patch du JMP $4C64/$4C65 -> appel $4C5D.",
    ],
    0x4ECC: [
        "Fin de la liste des evenements : on rend la main (et on reautorise l'affichage).",
        "Technique : outen=1 puis L471B.",
    ],
    0x5020: [
        "Avance d'un cran le programme (script) d'un personnage.",
        "Technique : $8C/$8D += A.",
    ],
    0x502A: [
        "Passe a l'instruction suivante du script d'un personnage, en sautant la taille de",
        "l'instruction courante.",
        "Technique : +4 (+2 si le bit $10 est pose), puis reecrit le PC dans l'entree de l'entite.",
    ],
    0x502C: [
        "Passe a l'instruction suivante du script d'un personnage, en sautant la taille de",
        "l'instruction courante (version courte).",
        "Technique : +2 (+2 si le bit $10 est pose), puis reecrit le PC dans l'entree de l'entite.",
    ],
    0x7353: [
        "Lit l'etat du clavier : renvoie la touche appuyee, ou indique qu'aucune touche n'est",
        "enfoncee.",
        "Technique : scan de la matrice via le VIA ($0300) ; A = code touche, bit7 pose si presente.",
    ],
    0x7481: [
        "Attend que le joueur appuie sur une touche, puis renvoie son code.",
        "Technique : boucle sur kb_scan jusqu'a bit7 pose, retour & $7F.",
    ],
    0x7489: [
        "Affiche un retour a la ligne.",
        "Technique : $0D via ch_out.",
    ],
    0x7491: [
        "Point d'entree pour tout caractere affiche a l'ecran. Il peut etre ignore selon le",
        "contexte (par exemple pendant qu'une scene se prepare).",
        "Technique : si (phase & outen)==0 -> jete ; mode raw -> majuscules ; sinon ch_put.",
    ],
    0x75B4: [
        "Dessine un caractere a l'ecran graphique (hires) en recopiant son motif depuis la police",
        "du jeu, puis fait avancer le curseur.",
        "Technique : police pointee par $0403/$0404 ; 8 octets en OR $40 (encre) ; ligne += $28.",
    ],
    0x75F6: [
        "Affiche un caractere en gerant les details du texte : espaces en attente, passage a la",
        "ligne, effacement, majuscule apres un point, minuscules par defaut. Toutes les 16 lignes",
        "il s'arrete pour laisser le joueur lire (pause).",
        "Technique : scroll L7694, pause pause_key, backspace $08, capitalisation apres '.' ($2E).",
    ],
    0x7619: [
        "Pause de lecture : tous les 16 sauts de ligne, le jeu attend une touche (ou un court",
        "delai), puis fait defiler l'ecran et remet le compteur de lignes a zero.",
        "Technique : 10 essais kb_scan avec delai, compteur crcnt mod 16, scroll L7694.",
    ],
    0x56D7: [
        "Fabrique un nombre aleatoire borne, utilise pour les comportements imprevisibles",
        "(errance des personnages, combats...).",
        "Technique : melange des octets de la source de bruit $93/$94 puis ramene le resultat dans [0, A).",
    ],
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
    chunk = data[a - BASE : b - BASE + 1]
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


def try_decode(
    raw: bytes, lo: int, hi: int, addr: int, starts: set[int], covered: set[int]
) -> bool:
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

    chunk = raw[addr - BASE : addr - BASE + 16]
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


def msg_preview(raw: bytes, addr: int, n: int = 64) -> str:
    """Texte décodé du message pointé (moteur render_text ; cf. msgdecode)."""
    if addr == 0:
        return "TODO pointeur nul"
    if not (BASE <= addr < BASE + len(raw)):
        return "(hors image)"
    text = decode_message(raw, addr, cap=n)
    return text if text else "(vide)"


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


def build_info(
    raw: bytes, code_bytes: set[int], ptrs: dict[int, int], lo: int, hi: int
) -> str:
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
    named = {**VECTORS, **ROM_LABELS, **{a: n for a, (n, _d) in ZP_NAMES.items()}}
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
        lines.append(
            f'LABEL {{ NAME "msg_{p:04X}"; ADDR ${p:04X}; COMMENT "{comment}"; }};'
        )
        used.add(p)
    for addr, (name, doc) in sorted(ROUTINE_DOCS.items()):
        if not (lo <= addr <= hi):
            continue
        if addr in range_starts:
            continue  # déjà nommé+commenté via RANGE (LABEL ferait doublon)
        label = name if name is not None else named.get(addr, f"code_{addr:04X}")
        lines.append(
            f'LABEL {{ NAME "{label}"; ADDR ${addr:04X}; '
            f'COMMENT "{sanitize_comment(doc)}"; }};'
        )
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
                lines.append(
                    f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; '
                    f'COMMENT "{sanitize_comment(doc)}"; }};'
                )
            else:
                lines.append(f'LABEL {{ NAME "{name}"; ADDR ${addr:04X}; }};')
    return "\n".join(lines) + "\n"


def label_name(addr: int) -> str | None:
    """Nom du label d'une routine (pour rattacher ROUTINE_NOTES au listing)."""
    if addr in ROUTINE_DOCS and ROUTINE_DOCS[addr][0]:
        return ROUTINE_DOCS[addr][0]
    if addr in VECTORS:
        return VECTORS[addr]
    if addr in ZP_NAMES:
        return ZP_NAMES[addr][0]
    return ROM_LABELS.get(addr)


def inject_notes(asm: list[str], notes: dict[int, list[str]]) -> list[str]:
    """Insere les notes multi-lignes juste avant le label correspondant."""
    by_name: dict[str, list[str]] = {}
    for addr, lines in notes.items():
        name = label_name(addr)
        if name:
            by_name[name] = lines
    out: list[str] = []
    for ln in asm:
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*):", ln)
        if m and m.group(1) in by_name:
            for text in by_name.pop(m.group(1)):
                out.append(f"; {text}\n")
        out.append(ln)
    return out


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

    vec_targets = [
        B(0x2C05 + 3 * k + 1) | (B(0x2C05 + 3 * k + 2) << 8) for k in range(16)
    ]
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

    print(
        f"bloc4 ${lo:04X}-${hi:04X} : {len(code_bytes)} octets code, "
        f"{len(ptrs)} pointeurs inline ($440D/$5B24), "
        f"{len(set(conflicts))} conflits"
    )
    if conflicts:
        print(
            "  conflits :", ", ".join(f"${a:04X}" for a in sorted(set(conflicts))[:12])
        )
    print("  références externes (top) :")
    for (r, t), n in ext.most_common(12):
        print(f"    {r} ${t:04X} x{n}")
    nulls = [p for p, m in ptrs.items() if m == 0]
    print(
        f"  pointeurs nuls : {len(nulls)}",
        ", ".join(f"${p:04X}" for p in sorted(nulls)),
    )

    if not DA65.is_file():
        print(
            f"{DA65} manquant : toolchain attendue dans tools/cc65/bin (cf. AGENTS.md)"
        )
        return 1
    slice_path = ROOT / "build" / "sim" / "hobbit_block4.bin"
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_path.write_bytes(raw[lo - BASE : hi - BASE + 1])
    subprocess.run(
        [
            str(DA65),
            "-i",
            str(INFO),
            "-S",
            f"0x{lo:x}",
            "-o",
            str(LISTING),
            str(slice_path),
        ],
        check=True,
    )
    # En-tête da65 volatil (date d'extraction) : on le neutralise pour un
    # listing déterministe (seule la ligne de version est conservée).
    asm = LISTING.read_text().splitlines(keepends=True)
    asm = [
        ln
        for ln in asm
        if not ln.startswith("; Created:")
        and not ln.startswith("; Input file:")
        and not ln.startswith("; Page:")
    ]
    asm = inject_notes(asm, ROUTINE_NOTES)
    header = (
        "; ============================================================\n"
        "; The Hobbit (Oric, 1982)\n"
        "; Original authors : Veronika Megler & Philip Mitchell (Melbourne House)\n"
        "; 6502 port : Greg Barrett (Beam Software)\n"
        "; - bloc 4 ($2C00-$7A80)\n"
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
