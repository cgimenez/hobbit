#!/usr/bin/env python3
"""Génère un listing assembleur annoté d'un bloc de The Hobbit (Oric).

Le découpage code/données est obtenu par **descente récursive** depuis les
points d'entrée du bloc, en suivant ``JSR``/``JMP``/branchements, jusqu'à
point fixe. Les seeds radare2 validés (décodage propre, bloc 4) et les
entrées manuelles complètent la couverture (dispatch indirect).

Règle spéciale (bloc 4) : ``JSR $440D`` (print_msg) et ``JSR $5B24``
(act_msg) sont suivis de 2 octets inline (adresse du message) ; le code
reprend à JSR+5. Les pointeurs nuls sont marqués ``TODO``. Une branche dont
la cible est sa propre adresse (boucle infinie ``xx FE``) est un terminateur.

Moteur commun ; les données (plage, entrées, vecteurs, docs) sont par bloc
dans ``BLOCKS`` (``block4`` par défaut, ``block1`` = bootstrap/chargeur,
``block2`` = données du jeu). da65 (cc65) produit le listing depuis
``disasm/<bloc>.info`` et ``data/hobbit.bin``.

Prérequis : ``tools/cc65/bin/da65`` (cf. AGENTS.md).
Vérification : scripts/disasm_check.py --block <bloc>.

Usage : .venv/bin/python scripts/disasm.py [--block block1|block2|block4]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from disasm_opcodes import (
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
from msg_decode import decode_message

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "data" / "hobbit.bin"
DISASM = ROOT / "disasm"
INFO = DISASM / "block4.info"
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
# - l'adresse doit être un début d'instruction (vérifié par disasm_check.py).
# Détails longs -> docs/block4-analysis.md (référencé par adresse).
ROUTINE_DOCS: dict[int, tuple[str | None, str]] = {
    # nom None = garde le nom existant (VECTORS), ajoute seulement le résumé.
    0x2C35: (
        None,
        "Point de depart du jeu : prepare la memoire, affiche le prompt, puis boucle de commandes",
    ),
    0x2DC8: ("init_vars", "Remet a zero les compteurs de depart (variables de travail, pile de messages, score)"),
    0x3097: ("boot_copy", "Copie l'etat de depart de la cassette vers la memoire de travail (le jeu joue sur cette copie)"),
    0x30BB: ("boot_copyback", "Copie la memoire de travail vers la zone de sauvegarde (sens inverse de boot_copy)"),
    0x440D: (
        "print_msg",
        "Affiche le message ecrit juste apres l'appel, puis reprend l'execution apres lui",
    ),
    0x44BE: ("msgptr_inc", "Avance d'un cran le pointeur de lecture du message courant"),
    0x4C82: (
        "is_dark",
        "Distingue un lieu sombre d'un lieu eclaire (lumiere portee) ; dit 'IT IS DARK.' si sombre",
    ),
    # Moteur de messages (decodeur valide par reimplementation Python : les
    # 32 mots $1117 et le dictionnaire 5-bit sortent en anglais propre).
    0x4444: (
        "render_text",
        "Traduit un message compresse en texte a l'ecran (lettres, mots courants, mots du dictionnaire, marqueurs)",
    ),
    0x4241: (
        "word_render",
        "Affiche un mot du dictionnaire et sa terminaison (pluriel, -ing...), avec espaces et retour a la ligne",
    ),
    0x462D: (
        "common_lookup",
        "Retrouve un mot courant (the, a, you...) a partir d'un seul octet",
    ),
    0x4641: (
        "token_jumps",
        "Liste des marqueurs speciaux d'un message : chacun renvoie vers la routine qui le traite",
    ),
    0x44A0: (
        "token_dispatch",
        "Saut vers la routine du marqueur courant (lue dans la table des marqueurs)",
    ),
    0x44AE: ("text_end", "Termine un message et applique sa ponctuation finale (rien, point ou saut de ligne)"),
    0x44C5: ("tok_nested", "Marqueur $00 : affiche un message imbrique (sous-message empile)"),
    0x44F5: ("tok_stkword", "Marqueur $01 : affiche un mot dont l'adresse a ete empilee"),
    0x44FB: (
        "tok_skip",
        "Marqueur $02 : saute a un autre endroit du message (sans revenir)",
    ),
    0x4504: (
        "tok_noop",
        "Marqueurs $05/$0A/$0F/$12 : sans effet",
    ),
    0x452E: ("tok_objw", "Marqueur $03 : affiche le mot pointe par le pointeur de travail"),
    0x4539: (
        "tok_stkvar",
        "Marqueur $04 : affiche un mot empile (variante selon le contexte)",
    ),
    0x454B: (
        "tok_objC5",
        "Marqueur $06 : affiche le nom de l'objet courant",
    ),
    0x4557: (
        "tok_obj15",
        "Marqueur $07 : affiche le nom de l'objet demande",
    ),
    0x4569: ("tok_ctrl08", "Marqueur $08 : envoie un code de controle a l'affichage"),
    0x456F: ("tok_obj16", "Marqueur $09 : affiche le nom du second objet"),
    0x4599: (
        "tok_recurse",
        "Marqueur $0B : reaffiche un bout de texte partage, puis revient",
    ),
    0x45B0: (
        "tok_pronC5",
        "Marqueur $0C : affiche 'his' si un objet est designe, sinon 'your'",
    ),
    0x45CA: ("tok_pron15", "Marqueur $0E : comme $0C, pour l'autre objet"),
    0x45CF: (
        "tok_nameC5",
        "Marqueur $10 : affiche le nom de l'objet ('is' si absent, 'someone' si inconnu)",
    ),
    0x45F4: ("tok_name15", "Marqueur $11 : nom de l'autre objet"),
    0x45FC: ("tok_nameSTK", "Marqueur $13 : nom de l'objet dont l'adresse a ete empilee"),
    0x44E4: ("stk_pop", "Depile une adresse de la pile de messages"),
    0x460A: (
        "nested_render",
        "Affiche un message imbrique en preservant l'etat du rendu courant",
    ),
    0x461B: ("obj_lookup", "Traduit un identifiant d'objet en son nom ('someone' si inconnu)"),
    0x46DB: ("cr_aware_out", "Affiche un caractere, en signalant les retours a la ligne"),
    0x42CE: (
        "word_space",
        "Place les espaces entre les mots et coupe la ligne en fin d'ecran",
    ),
    # Evenements differes : table $2B12 (entrees de 5 octets [id,cpt,actA,cond,actB],
    # terminee par $FF), balayee par world_tick ; actions via la table de sauts $7169.
    0x4E75: ("evt_tick", "Parcourt les evenements differes : decompte leur minuterie et declenche leur action quand elle est atteinte"),
    0x4E9D: ("evt_cond", "Teste si la condition d'un evenement est remplie pour le declencher"),
    0x4EAB: ("evt_fire", "Execute l'action d'un evenement en allant chercher son adresse dans une table"),
    0x4ECC: ("evt_end", "Fin de la liste des evenements : rend la main"),
    0x5DE2: ("evt_lookup", "Retrouve l'evenement associe a une cle (table des evenements)"),
    0x6689: ("evt_disarme6", "Desarme l'evenement e6 (remet sa minuterie a zero)"),
    0x66AA: ("evt_arme6", "Arme l'evenement e6 avec un delai aleatoire (2 a 10)"),
    0x65A5: ("evt_arme3", "Arme l'evenement e3 (minuterie = id) apres une action"),
    0x6A19: ("evt_disarme7", "Desarme l'evenement e7 dans un cas particulier (objet present)"),
    0x6AEB: ("evt_arme9b", "Arme l'evenement e9 (minuterie 6) puis affiche le trou qui disparait"),
    0x6B66: ("evt_arme5", "Arme l'evenement e5 et affiche 'magic door'"),
    0x6C5F: ("evt_act5", "Action de l'evenement e4 : au marais affiche un message, sinon desarme e4"),
    0x6D72: ("evt_print", "Affiche le trou qui disparait"),
    0x6915: ("evt_tip", "Tirage (~20%) : affiche 'expect me'"),
    0x70B5: ("evt_arme16", "Cle $16 : dans un cas precis, fait apparaitre une entite et arme l'evenement"),
    0x70CB: ("evt_arme2", "Arme l'evenement e2 (minuterie = id) ; declenche par la cle $1A"),
    0x70D2: ("evt_arme4", "Arme l'evenement e4 (minuterie = id) ; declenche par la cle $1D"),
    0x70D9: ("evt_arme9", "Arme l'evenement e9 et place des entites ; declenche par la cle $20"),
    0x70F8: ("evt_arme8", "Declenche par les cles $02/$03 : rearme l'evenement e8"),
    0x7103: ("evt_gate21", "Cle $21 : dans un cas precis, declenche un ecran et affiche"),
    0x4E59: (
        "world_tick",
        "Fait vivre le monde apres chaque commande : PNJ (scripts), puis evenements differes",
    ),
    # Commandes speciales : table $3BC6 (13 cles [lo,hi&$0F]) + $3BE0
    # (13 cibles, jmp (L3BC4)) ; SAVE=$3DD9 (mot $0DA0), QUIT=$3C88,
    # HELP=$3C8E, SCORE=$3CCE, PAUSE=$3D39. Zone $3D3F-$3E40 atteinte
    # uniquement par ce dispatch (MANUAL_ENTRIES).
    0x3D3F: (
        "tape_tramp",
        "Passage vers une routine cassette : lit ses parametres ecrits apres l'appel",
    ),
    0x3D7F: (
        "load_handler",
        "Commande LOAD : demande une touche puis charge un bloc depuis la cassette",
    ),
    0x3DAA: (
        "save_block",
        "Ecrit un bloc sur la cassette (parametres ecrits apres l'appel)",
    ),
    0x3DBC: (
        "save_err",
        "Echec de SAVE : affiche l'erreur, attend une touche puis abandonne",
    ),
    0x3DD9: (
        "cmd_save",
        "Commande SAVE : ecrit les 4 blocs du jeu puis verifie la cassette",
    ),
    0x3E20: (
        "cmd_next",
        "Termine la commande courante et revient a la boucle de commandes",
    ),
    0x4ED5: (
        "entity_tick",
        "Fait jouer le script d'un personnage (se deplacer, parler...), meme loin du joueur",
    ),
    0x5020: ("script_adv", "Avance d'un cran le script d'un personnage"),
    0x502A: ("script_step4", "Passage a l'instruction suivante du script d'un personnage"),
    0x502C: ("script_step2", "Passage a l'instruction suivante du script (version courte)"),
    0x511C: ("entity_move", "Deplace un personnage et annonce son mouvement s'il est visible"),
    0x5249: ("entity_goto", "Fait sauter le script d'un personnage a une autre instruction"),
    0x5279: ("say_if_visible", "Affiche un message si le personnage est au meme endroit que le joueur"),
    0x36DB: ("move_core", "Coeur du deplacement : trouve la sortie, verifie ses conditions, puis deplace ou refuse"),
    0x43CB: ("exit_ptr", "Retrouve la fiche de la sortie demandee dans la table des sorties du lieu"),
    0x3759: ("cond_eval", "Prepare la condition a remplir pour emprunter une sortie"),
    0x3770: ("move_flags", "Met de cote les options de la sortie (directe ou en variante)"),
    0x5386: ("act_probe", "Teste une action : soit l'execute, soit annule et retient qu'elle passe (mode sonde)"),
    0x56D7: ("rand_range", "Fabrique un nombre aleatoire borne"),
    0x5B24: ("act_msg", "Affiche le message d'une action puis termine l'action"),
    # Actions dispatchees par la table L7014 (index 0-14), declenchees par
    # les verbes du joueur (L4B37). Effets deduits du flot et des messages.
    0x5CA9: ("act_p14_04", "Prend ou pose un objet apres avoir verifie ses conditions"),
    0x5CB6: ("act_p14_14", "Bascule l'objet courant (prise/pose) apres verification"),
    0x5D06: ("act_p14_05", "Deplace un objet et met a jour sa position"),
    0x6041: (
        "act_p14_13",
        "Selon les drapeaux de l'objet : l'objet est emporte, ou l'objet est tue",
    ),
    0x60BF: (
        "act_p14_00",
        "Combat : applique les degats, epuise le compteur, annonce la mort",
    ),
    0x60ED: (
        "act_p14_01",
        "Deplace l'objet et prepare son affichage",
    ),
    0x61C9: ("act_p14_02", "Objet : selon un drapeau, agit ou passe la main"),
    0x61E5: ("act_p14_07", "Objet : lit un drapeau et branche vers un cas particulier"),
    0x6222: (
        "act_p14_03",
        "Pose un drapeau ; parfois declenche une scene (fete) selon l'objet",
    ),
    0x65B6: ("act_p14_12", "Choisit le traitement d'un objet selon son type (cas $0F)"),
    0x65BA: ("act_p14_08", "Choisit le traitement d'un objet selon son type (cas $04)"),
    0x65DD: (
        "act_p14_06",
        "Dit que la cle ne va pas sur cette serrure, ou qu'on ne peut pas faire ca",
    ),
    0x65F1: ("act_p14_10", "Selon le type de l'objet, poursuit un traitement ou un autre"),
    0x66D6: ("act_p14_11", "Araignees : annonce qu'elles tissent leur toile et arme un evenement"),
    0x6B72: (
        "act_p14_09",
        "Pour un objet donne, parcourt une liste et affiche 'go...from...to'",
    ),
    # Actions dispatchees par la table L7143 (index 0-14) : comportements
    # autonomes des PNJ dans la machine virtuelle $4ED5.
    0x68D0: ("act_v14_06", "PNJ : dit 'hello' s'il est au meme endroit que le joueur"),
    0x68E0: (
        "act_v14_01",
        "PNJ oisif : dit 'great job', 'hurry up' ou 'hello'",
    ),
    0x690C: ("act_v14_02", "PNJ : dit 'thrains key'"),
    0x692D: ("act_v14_00", "PNJ : dit 'WHAT'S this ?'"),
    0x6936: ("act_v14_04", "PNJ : tirage, ajuste un compteur et dit 'hurry up'"),
    0x6962: (
        "act_v14_03",
        "PNJ : au meme endroit et sans drapeau, dit 'WHERE'S the thief ?'",
    ),
    0x697A: ("act_v14_05", "PNJ : dans un lieu precis, ajuste un compteur"),
    0x6C09: ("act_v14_12", "Gollum : au bon endroit, affiche un message (prepare par le jeu)"),
    0x6C33: (
        "act_v14_11",
        "Action jouee une seule fois : remet un verrou et memorise des valeurs",
    ),
    0x6C8D: ("act_v14_09", "PNJ : dans certains lieux, annonce l'arrivee d'un personnage"),
    0x6CBE: (
        "act_v14_10",
        "Dragon au meme endroit : annonce 'PREPARE TO DIE' ou l'aveuglement",
    ),
    0x6CFA: ("act_v14_07", "PNJ : au meme endroit, ramasse un objet precis"),
    0x6D78: (
        "act_v14_14",
        "Gollum et l'Anneau : au bon endroit, tirage entre 'pocket?' et 'my precious'",
    ),
    0x6DF9: ("act_v14_13", "PNJ : cherche un lieu et annonce qu'il va 'strangle you'"),
    0x6E59: (
        "act_v14_08",
        "Dragon : selon le lieu, tirage entre vol et attaque au feu",
    ),
    0x6E8B: (
        "act_v14_15",
        "Trolls : au bon endroit, dit 'BLIMEY, COOK EM' ou autre",
    ),
    0x6CDB: ("act_v14_16", "PNJ : au meme endroit, simule un combat"),
    0x6EA7: (
        "act_v14_17",
        "PNJ : efface des drapeaux, met a jour une description et affiche un message",
    ),
    0x4737: ("fetch_retaddr", "Recupere l'adresse de retour empilee"),
    0x71DB: ("tape_load", "Charge un bloc depuis la cassette et verifie son en-tete"),
    0x7215: ("tape_save", "Ecrit un bloc sur la cassette (leader, en-tete, donnees, checksum)"),
    0x72A0: ("tape_prompt", "Affiche les invites de cassette ('PREPARE TAPE', 'PRESS ANY KEY'...)"),
    0x7353: ("kb_scan", "Lit le clavier : renvoie la touche appuyee, ou 'aucune touche'"),
    0x7481: ("kb_wait", "Attend que le joueur appuie sur une touche"),
    0x7489: ("cr_out", "Affiche un retour a la ligne"),
    0x7491: ("ch_out", "Point d'entree de l'affichage : peut ignorer certains caracteres selon le contexte"),
    0x75B4: ("glyph_out", "Dessine un caractere a l'ecran graphique avec la police du jeu"),
    0x75F6: ("ch_put", "Affiche un caractere : gere espaces, saut de ligne, effacement, majuscules et pause"),
    0x7619: (
        "pause_key",
        "Toutes les 16 lignes, marque une pause pour laisser le joueur lire",
    ),
    0x7747: ("hires_clear", "Efface l'ecran graphique"),
    0x7779: ("game_main", "Boucle principale du jeu : afficher, lire la commande, faire avancer le monde"),
    # Moteur d'illustrations vectorielles (consomme le bloc 3 : table $7AC0
    # [cle,mot] x13 + flux d'octets termine par $00 ; valide par rendu sim65 des
    # 13 images via un pilote vec_init + dump hires).
    0x4750: (
        "img_show",
        "Affiche l'illustration associee a une cle (si elle existe)",
    ),
    0x77D4: (
        "vec_image",
        "Dessine une illustration en suivant un flux de trace",
    ),
    0x7824: (
        "vec_fill",
        "Remplissage d'une zone de l'illustration",
    ),
    0x78C9: ("vec_pos", "Illustration : place le curseur"),
    0x78DA: ("vec_skip", "Illustration : saute jusqu'a un marqueur"),
    0x78E4: (
        "vec_line",
        "Illustration : trace un segment de ligne",
    ),
    0x7990: (
        "vec_setup",
        "Prepare l'ecran pour une illustration",
    ),
    0x79FB: ("vec_testpx", "Illustration : teste si un pixel est dans la zone dessinable"),
    0x7A0F: ("vec_plot", "Illustration : allume un pixel"),
    0x7A22: ("vec_addr", "Illustration : calcule l'adresse d'un pixel"),
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
        "Nombre de colonnes restantes sur la ligne (pour couper la ligne au bon moment)",
    ),
    0x0B: ("outen", "Autorise ou non l'affichage du texte (1 = autorise)"),
    0x0C: ("phase", "0 = simulation (le jeu calcule sans rien afficher), 1 = action reelle"),
    0x0D: ("raw", "Affichage brut : 1 = texte force, sans mise en forme"),
    0x0E: ("cap", "1 = mettre une majuscule a la prochaine lettre (apres un point)"),
    0x0F: ("sppend", "Un espace a inserer avant le prochain mot"),
    0x11: ("crcnt", "Nombre de lignes affichees depuis la derniere pause (remis a zero toutes les 16)"),
    0x12: ("passok", "1 = la simulation a reussi, on passe a l'action reelle"),
    # Operandes de commande (parser L359B, VM L5048/L50AC, $FF=absent).
    0x13: ("wid", "Mot courant interprete (verbe ou direction)"),
    0x15: ("arg1", "Premier objet de la commande ($FF = aucun)"),
    0x16: ("arg2", "Second objet de la commande ($FF = aucun)"),
    # Enregistrements d'objets (deref ($..),y ; swap L57A1).
    0x17: ("orec", "Pointeur vers la fiche du premier objet (octet haut en $18)"),
    0x19: ("orec2", "Pointeur vers la fiche du second objet (octet haut en $1A)"),
    0xC6: ("crec", "Pointeur vers la fiche courante (compteurs du personnage/objet en cours)"),
    # Moteur de messages (render_text, tokens, pile $466F/$0200).
    0x5C: ("adr", "Adresse de travail : mot de message en cours (octet haut en $5D)"),
    0x6F: ("tidx", "Position du caractere en cours dans le message affiche"),
    0x70: ("nest", "Niveau d'imbrication du message (0 = message simple)"),
    0x71: ("wptr", "Pointeur vers le mot ou nom en cours (octet haut en $72)"),
    0x76: ("msgstk", "Index de la pile des messages imbriques"),
    0xAD: ("svA", "Sauvegarde de l'accumulateur A"),
    0xAE: ("svX", "Sauvegarde du registre X"),
    0xAF: ("rstk", "Index de la pile interne d'adresses"),
    # Mouvement (exit_ptr, code_4141, move_flags, cond_eval).
    0x73: ("direct", "Sortie normale, sans controle particulier"),
    0x74: ("variant", "Sortie en variante (selon le type de commande)"),
    0x77: ("xaux", "Octet auxiliaire : options de mise en forme de la sortie"),
    0x78: ("xmode", "Octet de mode de la sortie (direct, variante...)"),
    0xDC: ("cond1", "Condition memorisee n°1"),
    0xE2: ("cond2", "Condition memorisee n°2"),
    0xE8: ("svptr", "Sauvegarde du pointeur de travail"),
    0xF8: ("exitp", "Curseur dans la table des sorties du lieu"),
    # Pointeurs de travail universels.
    0x7A: ("ptr3", "Troisieme pointeur de travail (octet haut en $7B)"),
    0x88: ("ptr2", "Pointeur secondaire, pour balayer les tables (octet haut en $89)"),
    0x8A: ("ptr", "Pointeur de travail principal (octet haut en $8B)"),
    # Monde (entites, events, tirage).
    0x8F: ("key", "Cle de l'evenement a declencher"),
    0x93: ("noise", "Source du hasard (pour les tirages aleatoires)"),
    0xBE: ("exploc", "Lieu attendu par l'evenement en cours"),
    0xC5: ("obj", "Objet ou personnage courant ($FF = un personnage)"),
    0xC8: ("ploc", "Lieu du joueur (simple copie : la vraie valeur est player.eloc en $1B2A)"),
    0xC9: ("eloc", "Lieu d'un personnage (visible quand il est identique a celui du joueur)"),
    0xCE: ("once", "Verrou 'une seule fois' : pose puis consomme"),
    # Scratch transitoire (moteur d'errance/placement des PNJ + file d'actions).
    0xC3: ("dflag", "Flag de l'action du dragon : initialise a 0 par l'intro, jamais arme (inactif)"),
    0xC4: ("sflag", "Flag de sortie texte : arme au desarmement de l'evenement e7, ajoute un H apres s/S"),
    0xCF: ("cand", "Index de candidat dans les tables de deplacement $48D3/$48D5 (moteur d'errance)"),
    0xD0: ("mwt", "Budget/poids du deplacement (moteur d'errance : $0A moins les couts)"),
    0xD1: ("qrd", "Curseur de lecture de la file d'actions $4905 (remis a 0 a chaque commande)"),
    0xD2: ("qwr", "Curseur d'ecriture de la file d'actions $4905 (remis a 0 a chaque commande)"),
    0xD3: ("macc", "Accumulateur de poids du moteur d'errance"),
    0xD4: ("mcnt", "Compteur de candidats retenus par le moteur d'errance"),
    0xD5: ("said", "Flag : le PNJ a parle/refuse (pose par code_6C2E, remis a 0 par act_v14_13)"),
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


# ---------------------------------------------------------------------------
# Configuration par bloc (moteur commun). Chaque bloc : plage, points
# d'entree, vecteurs nommes, documentation des routines, sorties da65.
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """Parametres d'un bloc desassemble (moteur commun, donnees par bloc)."""

    key: str
    lo: int
    hi: int
    base_entries: list[int]
    manual_entries: list[int]
    seed_exclude: set[int]
    vectors: dict[int, str]
    routine_docs: dict[int, tuple[str | None, str]]
    routine_notes: dict[int, list[str]]
    info: Path
    listing: Path
    cfg: Path
    header: str
    vector_table: tuple[int, int] | None = None
    use_r2_seeds: bool = True
    check_rom_diff: bool = True
    # Bloc de donnees pures (pas de code) : la regle D du checker (tables qui
    # se decodent comme du code) n'a pas de sens -> informatif seulement.
    check_code_tables: bool = True
    # Labels de donnees nommes (nom seul, sans resume) : adresses de tables /
    # structures reconnues, emises en LABEL da65 (cf. ROUTINE_DOCS pour les
    # routines). Fusionnes dans `named` avec les vecteurs et la zero-page.
    labels: dict[int, str] = field(default_factory=dict)
    data_ranges: dict[int, str] = field(default_factory=dict)


B4_HEADER = (
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

# --- Bloc 1 ($0400-$04FF) : bootstrap / chargeur cassette ---
# Entree autorun $0400 -> JMP $047C. Le loader $0417 lit un bloc complet ;
# les 6 vecteurs ROM $0405-$0414 sont atteints par JSR depuis $0417, sauf
# $040B/$040E (utilises seulement par le SAVE du bloc 4) -> MANUAL_ENTRIES.
B1_ROUTINE_DOCS: dict[int, tuple[str | None, str]] = {
    0x0400: (
        None,
        "Trampoline d'autorun : saute au demarrage du chargeur (b1_start)",
    ),
    0x0417: (
        "b1_load",
        "Lit un bloc complet sur cassette : synchro, en-tete 9 octets, donnees, checksum EOR",
    ),
    0x047C: (
        "b1_start",
        "Demarrage : detecte la ROM, relocalise les vecteurs, charge les blocs puis lance le jeu",
    ),
}

B1_ROUTINE_NOTES: dict[int, list[str]] = {
    0x047C: [
        "Point d'entree autorun ($0400 -> JMP $047C). Coupe les interruptions,",
        "puis detecte la version de ROM : si l'octet $FC78 est nul (Atmos 1.1),",
        "recopie un blob de 20 octets ($0468-$047B) sur $0403 pour remplacer les",
        "vecteurs ROM 1.0 par ceux de la ROM 1.1. Affiche 'Please wait while THE",
        "HOBBIT loads', puis charge 3 blocs (blocs 2, 3, 4) via b1_load et saute",
        "au dernier ($2C00). En cas d'echec, affiche 'TAPE ERROR' et boucle.",
    ],
    0x0417: [
        "Lit un bloc complet sur la cassette. Attend le marqueur de synchro,",
        "lit l'en-tete de 9 octets (range en $0035,Y), puis les donnees vers le",
        "pointeur ($37), en cumulant un checksum EOR dans $3B ; compare le",
        "checksum et renvoie C=1 (echec) ou C=0 (succes).",
        "Technique : JSR $0411 setup, $0405 synchro, $0408 lecture octet ;",
        "$39/$3A = adresse de fin, $37/$38 = curseur d'ecriture.",
    ],
}

B1_VECTORS: dict[int, str] = {
    0x0400: "b1_entry",
    0x0405: "b1_vec_sync",
    0x0408: "b1_vec_read",
    0x040B: "b1_vec_leader",
    0x040E: "b1_vec_write",
    0x0411: "b1_vec_setup",
    0x0414: "b1_vec_reset",
}

B1_HEADER = (
    "; ============================================================\n"
    "; The Hobbit (Oric, 1982)\n"
    "; Original authors : Veronika Megler & Philip Mitchell (Melbourne House)\n"
    "; 6502 port : Greg Barrett (Beam Software)\n"
    "; - bloc 1 ($0400-$04FF)\n"
    "; Listing généré par scripts/disasm.py (descente récursive + da65)\n"
    "; Charge par autorun à $0400 -> JMP $047C (b1_start).\n"
    "; Vecteurs ROM $0405-$0416 (patchés 1.0/1.1) + b1_load $0417.\n"
    "; ============================================================\n\n"
)


# --- Bloc 2 ($0500-$2BBD) : donnees du jeu ------------------------------
# Aucun code 6502 : dictionnaire packe 5-bit, catalogue de messages, table
# des cles d'etat, blocs d'etat, records de lieux/objets, tables de sorties,
# tables INDIR, scripts VM AnimAction, events differees et entites. Le listing
# est un partitionnement type (WORDTABLE/BYTETABLE) + labels des structures.
# Detail des formats : docs/block4-analysis.md, docs/memory-map.md.
B2_LABELS: dict[int, str] = {
    0x0500: "dict_index",       # index 26 lettres -> 1er mot
    0x0540: "dict",             # dico packe 5-bit (~600 mots)
    0x1117: "common_words",     # 32 mots courants ($60-$7F)
    0x1157: "messages",         # catalogue de messages
    0x18AA: "loc_desc",         # 29 descriptions de lieux
    0x1A62: "state_keys",       # 61 triplets [cle,lo,hi] + $FF
    0x1B1A: "states",           # 61 blocs d'etat
    0x2070: "rec_table",        # 80 mots id -> record
    0x2110: "rec_templates",    # 5 gabarits (pointeurs bloc 3)
    0x211A: "records",          # records lieux/objets/creatures
    0x26E2: "dir_names",        # noms des directions (10 x 8 o)
    0x2732: "exits_ext",        # sorties etendues conditionnelles
    0x28CC: "indir0",           # table de sauts 3 o [cle,lo,hi]
    0x28D3: "indir1",
    0x28DA: "indir2",
    0x28E1: "script_goblins",   # VM : gobelins e11/e12
    0x2910: "script_goblin13",  # VM : gobelin e13
    0x2934: "script_goblins14",  # VM : gobelins e14-e16
    0x2943: "indir3",
    0x295C: "script_gandalf",   # VM : Gandalf e0 (errance)
    0x2984: "indir4",
    0x298E: "script_thorin",    # VM : Thorin e1
    0x29B2: "indir5",
    0x29BC: "script_elf",       # VM : elfe e2
    0x29C3: "indir6",
    0x29C7: "script_warg",      # VM : warg e3
    0x29E4: "indir7",
    0x29EE: "script_butler",    # VM : butler dormant e4
    0x2A2E: "indir8",
    0x2A38: "script_elrond",    # VM : Elrond e5
    0x2A4D: "indir9",
    0x2A54: "script_dragon",    # VM : dragon dormant e8
    0x2A70: "indir10",
    0x2A77: "script_bard",      # VM : Bard dormant e7
    0x2A88: "indir11",
    0x2A8F: "script_gollum",    # VM : Gollum e6
    0x2AC9: "indir12",
    0x2AD0: "script_trolls",    # VM : trolls e9/e10 (lieu 5)
    0x2B12: "events",           # 10 x 5 o [id,cpt,actA,cond,actB]
    0x2B45: "entities",         # 17 x 7 o [id,n,PC,base,s6]
}

B2_RANGES: dict[int, str] = {
    0x0500: "WORDTABLE",   # index 26 lettres
    0x0540: "BYTETABLE",   # dictionnaire packe
    0x1117: "WORDTABLE",   # 32 mots courants
    0x1157: "BYTETABLE",   # catalogue de messages
    0x1A62: "BYTETABLE",   # cles d'etat
    0x1B1A: "BYTETABLE",   # blocs d'etat
    0x2070: "WORDTABLE",   # table des records
    0x2110: "WORDTABLE",   # gabarits de description
    0x211A: "BYTETABLE",   # records
    0x26E2: "BYTETABLE",   # noms des directions
    0x2732: "BYTETABLE",   # sorties etendues
    0x28CC: "BYTETABLE",   # INDIR + scripts VM + events + entites
}

B2_HEADER = (
    "; ============================================================\n"
    "; The Hobbit (Oric, 1982)\n"
    "; Original authors : Veronika Megler & Philip Mitchell (Melbourne House)\n"
    "; 6502 port : Greg Barrett (Beam Software)\n"
    "; - bloc 2 ($0500-$2BBD) : donnees du jeu (aucun code 6502)\n"
    "; Listing généré par scripts/disasm.py (partitionnement type + labels).\n"
    "; Dictionnaire packe 5-bit, catalogue de messages, etats, records,\n"
    "; tables INDIR, scripts VM AnimAction, events, entites.\n"
    "; Formats : docs/block4-analysis.md, docs/memory-map.md.\n"
    "; ============================================================\n\n"
)


BLOCKS: dict[str, Block] = {
    "block4": Block(
        key="block4",
        lo=BLOCK4[0],
        hi=BLOCK4[1],
        base_entries=[0x2C00, ENTRY],
        manual_entries=list(MANUAL_ENTRIES),
        seed_exclude=set(SEED_EXCLUDE),
        vectors=VECTORS,
        routine_docs=ROUTINE_DOCS,
        routine_notes=ROUTINE_NOTES,
        info=INFO,
        listing=LISTING,
        cfg=ROOT / "disasm" / "block4.cfg",
        header=B4_HEADER,
        vector_table=(0x2C05, 16),
        use_r2_seeds=True,
        check_rom_diff=True,
    ),
    "block1": Block(
        key="block1",
        lo=0x0400,
        hi=0x04FF,
        base_entries=[0x0400, 0x047C],
        manual_entries=[0x040B, 0x040E],
        seed_exclude=set(),
        vectors=B1_VECTORS,
        routine_docs=B1_ROUTINE_DOCS,
        routine_notes=B1_ROUTINE_NOTES,
        info=DISASM / "block1.info",
        listing=DISASM / "block1.asm",
        cfg=ROOT / "disasm" / "block1.cfg",
        header=B1_HEADER,
        vector_table=None,
        use_r2_seeds=False,
        check_rom_diff=False,
        # $0468-$047B = blob de vecteurs ROM 1.1 (copie, pas du texte) ;
        # $04F9-$04FF = queue non referencee (fin de bloc).
        data_ranges={0x0468: "BYTETABLE", 0x04F9: "BYTETABLE"},
    ),
    "block2": Block(
        key="block2",
        lo=0x0500,
        hi=0x2BBD,
        base_entries=[],
        manual_entries=[],
        seed_exclude=set(),
        vectors={},
        routine_docs={},
        routine_notes={},
        info=DISASM / "block2.info",
        listing=DISASM / "block2.asm",
        cfg=ROOT / "disasm" / "block2.cfg",
        header=B2_HEADER,
        vector_table=None,
        use_r2_seeds=False,
        check_rom_diff=False,
        check_code_tables=False,
        labels=B2_LABELS,
        data_ranges=B2_RANGES,
    ),
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
    """Texte décodé du message pointé (moteur render_text ; cf. msg_decode)."""
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
                if t == pc:
                    break  # boucle infinie (branche sur elle-meme) : terminateur
                if region(t) == "here":
                    worklist.append(t)
                pc += 2
            else:
                pc += ln
    return code_bytes, ptrs, starts, ext, conflicts


def build_info(
    raw: bytes, code_bytes: set[int], ptrs: dict[int, int], block: Block
) -> str:
    lo, hi = block.lo, block.hi
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
    named = {
        **block.vectors,
        **block.labels,
        **ROM_LABELS,
        **{a: n for a, (n, _d) in ZP_NAMES.items()},
    }
    for addr, (name, _doc) in block.routine_docs.items():
        if name is not None:
            named[addr] = name
    used: set[int] = set()
    range_starts = {a for a, _b in code_ranges}
    for a, b in code_ranges:
        name = named.get(a, f"code_{a:04X}")
        if a in named:
            used.add(a)
        rng = f'RANGE {{ START ${a:04X}; END ${b:04X}; TYPE CODE; NAME "{name}";'
        doc = block.routine_docs.get(a, (None, None))[1]
        if a in block.routine_docs and doc:
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
    for addr, (name, doc) in sorted(block.routine_docs.items()):
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
    # Plages de donnees a type impose (par bloc) : chaque adresse force une
    # frontiere et impose le type de la plage qui commence la.
    forced = dict(block.data_ranges)
    cur = None
    pending: list[list[int]] = []
    for a in range(lo, hi + 1):
        if a not in marked:
            if cur is None or a in forced:
                if cur is not None:
                    pending.append(cur)
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
        kind = forced.get(ga)
        if kind is None:
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


def label_name(block: Block, addr: int) -> str | None:
    """Nom du label d'une routine (pour rattacher ROUTINE_NOTES au listing)."""
    if addr in block.routine_docs and block.routine_docs[addr][0]:
        return block.routine_docs[addr][0]
    if addr in block.vectors:
        return block.vectors[addr]
    if addr in block.labels:
        return block.labels[addr]
    if addr in ZP_NAMES:
        return ZP_NAMES[addr][0]
    return ROM_LABELS.get(addr)


def inject_notes(asm: list[str], block: Block) -> list[str]:
    """Insère les notes multi-lignes juste avant le label correspondant.

    Quand une routine a une note, celle-ci (déjà rédigée « humain d'abord »)
    remplace le résumé une ligne de ROUTINE_DOCS pour éviter un doublon.
    """
    by_name: dict[str, list[str]] = {}
    for addr, lines in block.routine_notes.items():
        name = label_name(block, addr)
        if name:
            by_name[name] = lines
    doc_by_name: dict[str, str] = {}
    for addr, (_name, doc) in block.routine_docs.items():
        name = label_name(block, addr)
        if name and doc:
            doc_by_name[name] = f"; {sanitize_comment(doc)}\n"
    out: list[str] = []
    for ln in asm:
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*):", ln)
        if m and m.group(1) in by_name:
            name = m.group(1)
            if out and out[-1] == doc_by_name.get(name):
                out.pop()
            for text in by_name.pop(name):
                out.append(f"; {text}\n")
        out.append(ln)
    return out


# Ligne de texte da65 : label optionnel + `.byte "..."` (sans commentaire).
_TEXT_BYTE_RE = re.compile(
    r'^(?P<indent>\s*)(?P<label>[A-Za-z_][A-Za-z0-9_]*:)?(?P<pad>\s*)'
    r'\.byte\s+"(?P<txt>[^"]*)"\s*$'
)


def reflow_text_tables(asm: list[str]) -> list[str]:
    """Recolle les morceaux `.byte "..."` d'un meme texte (TEXTTABLE).

    da65 (TextTable(), src/da65/data.c) coupe chaque texte a
    ``BytesPerLine*4-1`` = 31 caracteres et emet un ``LineFeed`` vide par
    tranche de ``BytesPerLine`` (8) octets : le listing est coupe et parseme
    de lignes vides. Non configurable ; on recolle ici les morceaux
    consecutifs (sans label intercale) en un seul ``.byte "..."`` et on jette
    les lignes vides parasites (octets assembles identiques).
    """
    out: list[str] = []
    i, n = 0, len(asm)
    while i < n:
        m = _TEXT_BYTE_RE.match(asm[i])
        if m is None:
            out.append(asm[i])
            i += 1
            continue
        prefix = asm[i][: m.start("txt")]
        text = m.group("txt")
        j = i + 1
        while True:
            k = j
            while k < n and asm[k].strip() == "":
                k += 1
            if k < n:
                m2 = _TEXT_BYTE_RE.match(asm[k])
                if m2 is not None and not m2.group("label"):
                    text += m2.group("txt")
                    j = k + 1
                    continue
            j = k
            break
        out.append(prefix + text + '"\n')
        i = j
    return out


# Equate da65 hors plage assemblee : `sym := $addr`.
_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:=\s*\$[0-9A-Fa-f]{4}\b")


def drop_unused_equates(asm: list[str]) -> list[str]:
    """Supprime les equates da65 inutilises (`sym := $addr`).

    build_info emet un LABEL pour chaque nom connu (zero-page `ZP_NAMES`,
    routines ROM `ROM_LABELS`) dans tous les blocs ; da65 rend ceux hors de la
    plage assemblee en equates `sym := $addr`. On ne garde que les noms
    reellement references ailleurs dans le listing (operandes ; commentaires
    ignores). Sans effet sur les octets assembles (un equate n'emet rien) ;
    l'`.info` reste complet (la regle H du checker porte sur l'`.info`).
    """
    defs: dict[int, str] = {}
    counts: dict[str, int] = {}
    for i, ln in enumerate(asm):
        code = ln.split(";", 1)[0]
        m = _ASSIGN_RE.match(ln)
        if m:
            defs[i] = m.group(1)
        for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code):
            counts[name] = counts.get(name, 0) + 1
    out: list[str] = []
    for i, ln in enumerate(asm):
        name = defs.get(i)
        if name is not None and counts.get(name, 0) <= 1:
            continue
        out.append(ln)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    import subprocess

    ap = argparse.ArgumentParser(description="Desassemble un bloc en listing da65 annote.")
    ap.add_argument(
        "--block",
        default="block4",
        choices=sorted(BLOCKS),
        help="bloc a desassembler (defaut : block4)",
    )
    args = ap.parse_args(argv)
    block = BLOCKS[args.block]

    if not BIN.exists():
        print(f"{BIN} manquant : lancez scripts/tape_extract.py")
        return 1
    DISASM.mkdir(exist_ok=True)
    raw = BIN.read_bytes()
    lo, hi = block.lo, block.hi

    def B(a: int) -> int:
        return raw[a - BASE]

    entries = list(block.base_entries)
    if block.vector_table is not None:
        va, n = block.vector_table
        entries += [B(va + 3 * k + 1) | (B(va + 3 * k + 2) << 8) for k in range(n)]
    entries += block.manual_entries
    r2seeds = load_r2_seeds(R2CACHE) if block.use_r2_seeds else []

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
            if s in block.seed_exclude:
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

    block.info.write_text(build_info(raw, code_bytes, ptrs, block))

    print(
        f"{block.key} ${lo:04X}-${hi:04X} : {len(code_bytes)} octets code, "
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
    slice_path = ROOT / "build" / "sim" / f"hobbit_{block.key}.bin"
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_path.write_bytes(raw[lo - BASE : hi - BASE + 1])
    subprocess.run(
        [
            str(DA65),
            "-i",
            str(block.info),
            "-S",
            f"0x{lo:x}",
            "-o",
            str(block.listing),
            str(slice_path),
        ],
        check=True,
    )
    # En-tête da65 volatil (date d'extraction) : on le neutralise pour un
    # listing déterministe (seule la ligne de version est conservée).
    asm = block.listing.read_text().splitlines(keepends=True)
    asm = [
        ln
        for ln in asm
        if not ln.startswith("; Created:")
        and not ln.startswith("; Input file:")
        and not ln.startswith("; Page:")
    ]
    asm = reflow_text_tables(asm)
    asm = inject_notes(asm, block)
    asm = drop_unused_equates(asm)
    block.listing.write_text(block.header + "".join(asm))
    print(f"Listing écrit : {block.listing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
