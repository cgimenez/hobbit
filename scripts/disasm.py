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
``block2`` = données du jeu, ``block3`` = illustrations vectorielles). da65
(cc65) produit le listing depuis ``disasm/<bloc>.info`` et
``data/hobbit.bin``.

Prérequis : ``tools/cc65/bin/da65`` (cf. AGENTS.md).
Vérification : scripts/disasm_check.py --block <bloc>.

Usage : .venv/bin/python scripts/disasm.py [--block block1|block2|block3|block4]
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
    # Handlers de la table de verbes sans objet $6FAC tombes dans des zones
    # donnees (indirect -> hors descente) : Inventory $637B, Capture $6760,
    # Untie $67CA, Tie To $67E3, Burn $685E, Climb Out Of $686D.
    + [0x637B, 0x6760, 0x67CA, 0x67E3, 0x685E, 0x686D]
    # Action d'objet $66F1 (index 35 de la table de mots $7014, base $7016) :
    # sans seed la zone restait en BYTETABLE decodable comme code (regle D).
    + [0x66F1]
    # Handler du token $09 ($456F, table $4641) : sans seed, la plage
    # code_436C s'arrete au RTS $456E et $456F-$4572 tombent en donnees
    # (le JMP patche est indirect, invisible de la descente).
    + [0x456F]
    # Actions d'evenements differees atteintes via la table de sauts $7169
    # (indirect) et tombees en zones donnees : $688D (index 1, e0) est dans
    # la BYTETABLE $66F1-$68CF ; $6DBB (index 13, e9) est la vraie tete du
    # handler de trou (la plage code_6DBE commencait 3 octets trop loin).
    + [0x688D, 0x6DBB]
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
    0x2DC8: (
        "init_vars",
        "Remet a zero les compteurs de depart (variables de travail, pile de messages, score)",
    ),
    0x3097: (
        "boot_copy",
        "Copie l'etat de depart de la cassette vers la memoire de travail (le jeu joue sur cette copie)",
    ),
    0x30BB: (
        "boot_copyback",
        "Copie la memoire de travail vers la zone de sauvegarde (sens inverse de boot_copy)",
    ),
    # ---- Parser AnimTalk : saisie ($2DDB-$2EA8) ----
    # Editeur de ligne : lit les touches, echo, backspace, guillemets, fleches.
    # Le tampon de commande est $40BE (une ligne, terminee par $0D).
    0x2DDB: (
        "input_abort",
        "'@' en tete de ligne : recule le curseur de 2 et annule la saisie en cours",
    ),
    0x2DEA: (
        "read_line",
        "Saisie d'une commande : affiche '> ', lit les touches et remplit le tampon $40BE",
    ),
    0x2E04: ("line_loop", "Lit une touche, la traduit (fleches) puis la traite"),
    0x2E0F: (
        "line_read",
        "Lit une touche sans traduction (relecture apres effacement)",
    ),
    0x2E12: (
        "line_dispatch",
        "Repartit la touche : fin de ligne, effacement ou edition",
    ),
    0x2E1A: ("line_del", "Touche DEL ($7F) : efface toute la ligne saisie"),
    0x2E24: (
        "line_backspace",
        "Retour arriere ($08) : efface le dernier caractere et suit l'etat guillemet",
    ),
    0x2E40: (
        "line_edit",
        "Edition d'un caractere : guillemets, espaces et ponctuation",
    ),
    0x2E58: (
        "line_classify",
        "Trie le caractere saisi (espace, CR, point, virgule) avant stockage",
    ),
    0x2E68: (
        "line_store",
        "Stocke le caractere dans le tampon de commande $40BE et l'affiche (echo)",
    ),
    0x2E76: (
        "line_cr",
        "Entree : ferme la ligne (guillemet/point manquants), stocke CR et renvoie 1",
    ),
    0x2E8C: ("ins_quote", "Ajoute un guillemet fermant si la saisie en a ouvert un"),
    0x2E98: (
        "ins_period",
        "Ajoute un point final a la commande si elle n'en a pas deja",
    ),
    0x2EA9: (
        "key_arrow",
        "Fleches du clavier : les remplace par N/S/E/W (deplacement immediat, Oric)",
    ),
    0x2EBA: ("key_n", "Fleche haut : ecrit 'N' puis valide"),
    0x2EBC: (
        "key_dir_put",
        "Ecrit la lettre de direction dans le tampon, echo, puis valide par CR",
    ),
    0x2EC6: ("key_w", "Fleche gauche : ecrit 'W' puis valide"),
    0x2ECB: ("key_e", "Fleche droite : ecrit 'E' puis valide"),
    0x2ED0: ("key_s", "Fleche bas : ecrit 'S' puis valide"),
    # ---- Parser AnimTalk : lexeur + dictionnaire ($2ED5-$308E) ----
    # tokenize() lit un mot du tampon $40BE, le cherche dans le dictionnaire
    # 5-bit du bloc 2 ($0540) et renvoie son type + son adresse. La file de
    # tokens est $4783 ([type<<4|page, lo] ; 2 octets par mot).
    0x2ED5: (
        "tokenize",
        "Lit le mot suivant du tampon, le cherche au dictionnaire et renvoie son type et son adresse",
    ),
    0x2F26: ("lex_cr", "Fin de ligne : produit le token de type $C0 (fin de commande)"),
    0x2F28: (
        "lex_emit",
        "Prepare le token courant (adresse vide) puis passe a l'emission du type",
    ),
    0x2F30: (
        "lex_type",
        "Renseigne le type du token ($5B), combine l'adresse et rend la main",
    ),
    0x2F3B: (
        "lex_restore",
        "Restaure le pointeur d'entree sauvegarde apres le test d'abreviation",
    ),
    0x2F43: (
        "word_finish",
        "Mot trouve : suit un eventuel renvoi, extrait son type et son adresse de dictionnaire",
    ),
    0x2F47: (
        "word_skip",
        "Avance jusqu'au dernier octet de lettres du mot (bit7 pose)",
    ),
    0x2F60: (
        "word_grammar",
        "Teste le bit de renvoi de l'entree et suit la redirection de pointeur si pose",
    ),
    0x2F78: (
        "word_type",
        "Extrait le nibble de type (bits 6-5 des 2 premiers octets) et le range dans $5B",
    ),
    0x2FA3: (
        "punct_class",
        "Classe un signe de ponctuation : point ($B0), virgule ($A0) ou guillemet ($90)",
    ),
    0x2FB8: (
        "punct_hit",
        "Signe de ponctuation reconnu : avance le curseur et renvoie son type",
    ),
    0x2FBB: (
        "dict_bucket",
        "Decode les lettres du mot cherche et se place sur le seau de dictionnaire de sa 1re lettre",
    ),
    0x2FCE: (
        "dict_start",
        "Calcule le seau $0500[2*lettre] et positionne le pointeur sur sa 1re entree",
    ),
    0x2FEA: (
        "dict_next",
        "Avance de la taille de l'entree courante et compare la 1re lettre de la suivante",
    ),
    0x2FF4: ("dict_cmp1", "Compare la 1re lettre de l'entree au mot cherche"),
    0x3000: (
        "dict_read",
        "Entree correspondante : decode ses lettres dans $47D3 et mesure sa longueur",
    ),
    0x3008: (
        "dict_letters",
        "Decode les lettres 5 bits d'une entree de dictionnaire (bit7 = suite)",
    ),
    0x3012: (
        "dict_letter_next",
        "Gere les cas particuliers de 2 et 3 lettres (fin de mot)",
    ),
    0x302B: (
        "dict_end",
        "Fin des lettres : note la longueur du candidat ($67) et le bit de renvoi",
    ),
    0x3037: (
        "dict_done",
        "Fin de lecture d'une entree : rend Z (A=0) quand la 1re lettre correspond",
    ),
    0x303C: (
        "word_prefix_cmp",
        "Compare le mot saisi et le candidat sur la longueur commune (prefixe)",
    ),
    0x3048: ("cmp_min", "Longueur de comparaison = minimum des deux longueurs"),
    0x304B: ("cmp_loop", "Boucle de comparaison lettre a lettre"),
    0x305E: ("cmp_diff", "Difference trouvee : rend Z clair (A=1)"),
    0x3065: (
        "cmd_store",
        "Recopie les mots de la commande du tampon de travail $4927 vers $4A17",
    ),
    # ---- Parser AnimTalk : grammaire / interpreteur ($3111-$356E) ----
    # parse_cmd() consomme la file de tokens $4783 et construit la commande
    # (verbe, objets, direction...) en dispatchant sur la classe du mot via
    # la table $315A. Les handlers partagent un petit enregistrement de travail
    # (24 octets) a (ptr2) et l'accumulateur de groupe nominal $A3..$AC.
    0x3111: (
        "parse_cmd",
        "Analyse la suite de tokens et construit la commande (verbe, objets, deplacement)",
    ),
    0x311C: (
        "next_word",
        "Debut d'un nouveau mot a analyser (remet le compteur de virgules $9D)",
    ),
    0x3135: (
        "next_phrase",
        "Reinitialise l'accumulateur de groupe nominal et lit le token suivant",
    ),
    0x3144: (
        "dispatch",
        "Lit le token courant et saute vers le handler de sa classe (table $315A)",
    ),
    0x3172: (
        "cmd_end",
        "Classe 11 (point/THEN) : valide la fin de commande ou poursuit",
    ),
    0x328F: (
        "cls_direction",
        "Classe 2 (direction) : enregistre la direction demandee",
    ),
    0x3299: (
        "cls_adverb",
        "Classe 0 (adverbe) : annonce le mode de l'action (doucement, vite...)",
    ),
    0x32B9: (
        "cls_conj",
        "Classe 10 (AND / virgule) : enchainement de plusieurs objets",
    ),
    0x32E9: ("cls_go", "Classe 4 (GO/RUN) : verbes de deplacement"),
    0x32F3: (
        "cls_verb",
        "Classe 3 (verbe) : fixe le verbe de la commande et attend ses objets",
    ),
    0x3374: (
        "cls_article",
        "Classe 8 (article/determinant : THE, A...) : annonce un nom et lit la suite",
    ),
    0x337D: ("cls_prep_in", "Classe 1 (IN/INTO) : preposition de lieu"),
    0x3390: (
        "cls_preposition",
        "Classe 7 (preposition : ON, THROUGH, WITH...) : separe sujet et complement",
    ),
    0x33BF: (
        "cls_adjective",
        "Classe 6 (adjectif) : ajoute un qualificatif au groupe nominal courant",
    ),
    0x33C8: ("cls_noun", "Classe 5 (nom) : enregistre l'objet ou le lieu designe"),
    0x3471: (
        "rec_back_mode0",
        "Recule a l'enregistrement precedent puis remet le mode de commande a zero",
    ),
    0x3474: ("set_mode0", "Remet le mode de commande ($6E) a zero"),
    0x3479: (
        "rec_clear",
        "Efface l'enregistrement de commande courant (26 octets a (ptr2))",
    ),
    0x3485: (
        "next_token",
        "Lit le token suivant de la file $4783 (type en $5A/$5B, adresse en adr)",
    ),
    0x34A7: (
        "rec_prev_dec",
        "Recule d'un enregistrement et decremente le compteur de commandes",
    ),
    0x34A9: (
        "rec_rewind",
        "Rembobine sur le premier enregistrement de la file courante",
    ),
    0x34B1: (
        "rec_rewind_loop",
        "Boucle de rembobinage (recule tant que le bit $40 est pose)",
    ),
    0x34BD: ("rec_prev", "Enregistrement precedent : (ptr2) -= $18"),
    0x34CB: (
        "rec_fwd_dec",
        "Decremente le compteur et avance a l'enregistrement suivant",
    ),
    0x34D0: (
        "rec_merge",
        "Fusionne l'enregistrement pointe par (ptr) dans (ptr2) puis chaine le suivant",
    ),
    0x34F1: (
        "rec_fixup1",
        "Apres fusion : echange des champs si le drapeau $6D bit7 est pose",
    ),
    0x34F8: (
        "rec_swap6",
        "Echange 6 octets (+8..+$0D) avec (+$12..+$17) dans l'enregistrement",
    ),
    0x3516: (
        "rec_copy_check",
        "Copie un bloc de champs de l'enregistrement puis teste la suite",
    ),
    0x3529: ("rec_copy6", "Copie 6 octets de (ptr) vers (ptr2)"),
    0x352E: ("rec_copy10", "Copie 10 octets de (ptr) vers (ptr2)"),
    0x3533: ("rec_copy2", "Copie 2 octets de (ptr) vers (ptr2)"),
    0x3535: ("copy_bytes", "Copie X octets de (ptr) vers (ptr2)"),
    0x353E: (
        "rec_store_here",
        "Range l'adresse du mot courant dans le champ de l'enregistrement",
    ),
    0x3546: ("rec_store_at", "Ecrit adr/adr_hi a (ptr2)+2*X"),
    0x3552: ("parse_fail_pop", "Abandon : depile deux octets puis signale l'erreur"),
    0x3554: (
        "parse_fail",
        "Echec du parseur : revient a la boucle de commandes avec 'WHAT ?'",
    ),
    0x355A: (
        "rec_rewind2",
        "Rembobine puis avance jusqu'au premier enregistrement marque",
    ),
    0x3562: (
        "rec_rewind2_loop",
        "Boucle d'avance (avance tant que le bit $40 est pose)",
    ),
    0x356E: ("rec_next", "Enregistrement suivant : (ptr2) += $18"),
    0x440D: (
        "print_msg",
        "Affiche le message ecrit juste apres l'appel, puis reprend l'execution apres lui",
    ),
    0x44BE: (
        "msgptr_inc",
        "Avance d'un cran le pointeur de lecture du message courant",
    ),
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
    0x44AE: (
        "text_end",
        "Termine un message et applique sa ponctuation finale (rien, point ou saut de ligne)",
    ),
    0x44C5: (
        "tok_nested",
        "Marqueur $00 : affiche un message imbrique (sous-message empile)",
    ),
    0x44F5: (
        "tok_stkword",
        "Marqueur $01 : affiche un mot dont l'adresse a ete empilee",
    ),
    0x44FB: (
        "tok_skip",
        "Marqueur $02 : saute a un autre endroit du message (sans revenir)",
    ),
    0x4504: (
        "tok_noop",
        "Marqueurs $05/$0A/$0F/$12 : sans effet",
    ),
    0x452E: (
        "tok_objw",
        "Marqueur $03 : affiche le mot pointe par le pointeur de travail",
    ),
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
    0x45FC: (
        "tok_nameSTK",
        "Marqueur $13 : nom de l'objet dont l'adresse a ete empilee",
    ),
    0x44E4: ("stk_pop", "Depile une adresse de la pile de messages"),
    0x460A: (
        "nested_render",
        "Affiche un message imbrique en preservant l'etat du rendu courant",
    ),
    0x461B: (
        "obj_lookup",
        "Traduit un identifiant d'objet en son nom ('someone' si inconnu)",
    ),
    0x46DB: (
        "cr_aware_out",
        "Affiche un caractere, en signalant les retours a la ligne",
    ),
    0x42CE: (
        "word_space",
        "Place les espaces entre les mots et coupe la ligne en fin d'ecran",
    ),
    # Evenements differes : table $2B12 (entrees de 5 octets [id,cpt,actA,cond,actB],
    # terminee par $FF), balayee par world_tick ; actions via la table de sauts $7169.
    0x4E75: (
        "evt_tick",
        "Parcourt les evenements differes : decompte leur minuterie et declenche leur action quand elle est atteinte",
    ),
    0x4E9D: (
        "evt_cond",
        "Teste si la condition d'un evenement est remplie pour le declencher",
    ),
    0x4EAB: (
        "evt_fire",
        "Execute l'action d'un evenement en allant chercher son adresse dans une table",
    ),
    0x4ECC: ("evt_end", "Fin de la liste des evenements : rend la main"),
    0x5DE2: (
        "evt_lookup",
        "Retrouve l'evenement associe a une cle (table des evenements)",
    ),
    0x6689: ("evt_disarme6", "Desarme l'evenement e6 (remet sa minuterie a zero)"),
    0x66AA: ("evt_arme6", "Arme l'evenement e6 avec un delai aleatoire (2 a 10)"),
    0x65A5: ("evt_arme3", "Arme l'evenement e3 (minuterie = id) apres une action"),
    0x64E2: (
        "evt_arme0",
        "Arme l'evenement e0 (minuterie 2) si le tonneau a atteint Forestriver",
    ),
    0x688D: (
        "evt_act0",
        "Action de l'evenement e0 : le tonneau atteint le Long Lake, joueur jete sur la berge",
    ),
    0x6DBB: (
        "evt_hole",
        "Trou secret vers la Montagne : pose l'etat $0B bit7 puis annonce l'apparition du trou",
    ),
    0x6A19: (
        "evt_disarme7",
        "Desarme l'evenement e7 dans un cas particulier (objet present)",
    ),
    0x6AEB: (
        "evt_arme9b",
        "Arme l'evenement e9 (minuterie 6) puis affiche le trou qui disparait",
    ),
    0x6B66: ("evt_arme5", "Arme l'evenement e5 et affiche 'magic door'"),
    0x6C5F: (
        "evt_act5",
        "Action de l'evenement e4 : au marais affiche un message, sinon desarme e4",
    ),
    0x6D72: ("evt_print", "Affiche le trou qui disparait"),
    0x6915: ("evt_tip", "Tirage (~20%) : affiche 'expect me'"),
    0x70B5: (
        "evt_arme16",
        "Cle $16 : reveille le BUTLER (e4 $2B61:=$42) si sa fiche +7 bit3 est clair, puis marque +7 bit7",
    ),
    0x70CB: (
        "evt_arme2",
        "Arme l'evenement e2 (minuterie = id) ; declenche par la cle $1A",
    ),
    0x70D2: (
        "evt_arme4",
        "Arme l'evenement e4 (minuterie = id) ; declenche par la cle $1D",
    ),
    0x70D9: (
        "evt_arme9",
        "Cle $20 : reveille DRAGON (e8 $2B7D:=$3C) et BARD (e7 $2B76:=$46) si leur fiche +7 bit3 est clair, puis arme l'evenement e9 (cpt:=3)",
    ),
    0x70F8: ("evt_arme8", "Declenche par les cles $02/$03 : rearme l'evenement e8"),
    0x7103: (
        "evt_gate21",
        "Cle $21 : dans un cas precis, declenche un ecran et affiche",
    ),
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
        "load_game",
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
        "save_game",
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
    0x502A: (
        "script_step4",
        "Passage a l'instruction suivante du script d'un personnage",
    ),
    0x502C: (
        "script_step2",
        "Passage a l'instruction suivante du script (version courte)",
    ),
    0x511C: (
        "entity_move",
        "Deplace un personnage et annonce son mouvement s'il est visible",
    ),
    0x5249: (
        "entity_goto",
        "Fait sauter le script d'un personnage a une autre instruction",
    ),
    0x5279: (
        "say_if_visible",
        "Affiche un message si le personnage est au meme endroit que le joueur",
    ),
    0x36DB: (
        "move_core",
        "Coeur du deplacement : trouve la sortie, verifie ses conditions, puis deplace ou refuse",
    ),
    0x43CB: (
        "exit_ptr",
        "Retrouve la fiche de la sortie demandee dans la table des sorties du lieu",
    ),
    0x3759: ("cond_eval", "Prepare la condition a remplir pour emprunter une sortie"),
    0x3770: (
        "move_flags",
        "Met de cote les options de la sortie (directe ou en variante)",
    ),
    0x5386: (
        "act_probe",
        "Teste une action : soit l'execute, soit annule et retient qu'elle passe (mode sonde)",
    ),
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
    0x65F1: (
        "act_p14_10",
        "Selon le type de l'objet, poursuit un traitement ou un autre",
    ),
    0x66D6: (
        "act_p14_11",
        "Araignees : annonce qu'elles tissent leur toile et arme un evenement",
    ),
    0x6B72: (
        "act_p14_09",
        "Pour un objet donne, parcourt une liste et affiche 'go...from...to'",
    ),
    0x66F1: (
        "act_p14_35",
        "Action d'objet (index 35 de $7014) : controle le contenant puis deplace l'objet",
    ),
    # ---- Handlers de la table de verbes sans objet $6FAC (wid -> handler) ----
    # Noms officiels des verbes d'apres hobbit.ctl (map #ACTION) ; entree Oric
    # propre (ex. $0E=Drop, absent de la v1.2 ZX). Cf. docs/block4-analysis.md.
    0x5B44: ("action_look", "Verbe Look ($17) : decrit l'objet courant et liste ce qui est visible"),
    0x5BC9: ("action_pickup", "Verbes Take ($13)/Carry ($3B) : prend l'objet (pose le porteur)"),
    0x5D31: ("action_take_out_of", "Verbe Take out of ($14) : verifie le contenant puis prend"),
    0x5D44: ("action_dir", "Verbes $01-$0A (deplacement N..DOWN) : resout le mouvement"),
    0x5EB7: ("action_drop", "Verbe Drop ($0E) : pose l'objet ; un liquide s'evapore"),
    0x5EFF: ("action_enter", "Verbes Enter ($1F)/Go into ($20) : entre dans le contenant"),
    0x5F07: ("action_run", "Verbe Run ($24) : fuit dans une direction aleatoire"),
    0x5F28: ("action_follow", "Verbe Follow ($27) : suit une entite presente"),
    0x5F40: ("action_throw_at", "Verbe Throw At ($2A) : lance l'objet (arme) sur la cible"),
    0x5F81: ("action_talk_to", "Verbe Talk To ($35) : entite arg1, replique liee a son champ 'reply'"),
    0x6272: ("action_strike", "Verbe Strike with ($0B) : combat, ratio de force"),
    0x637B: ("action_inventory", "Verbe Inventory ($1A) : liste ce que porte le joueur"),
    0x63A4: ("action_examine", "Verbe Examine ($1C) : affiche le message propre de l'objet"),
    0x63DC: ("action_give", "Verbe Give To ($1D) : verifie poids/lumiere puis donne l'objet"),
    0x6760: ("action_capture", "Verbe Capture ($30) : tente d'attraper un animal (flag bit6)"),
    0x67CA: ("action_untie", "Verbe Untie ($33) : defait un lien"),
    0x67E3: ("action_tie", "Verbe Tie To ($2E) : noue un objet a une cible"),
    0x685E: ("action_burn", "Verbe Burn ($2D) : met le feu a un objet"),
    0x686D: ("action_climb_out", "Verbe Climb Out Of ($37) : sort d'un contenant/lieu"),
    0x698B: ("action_shoot", "Verbe Shoot ($3A) : tire une fleche (arme)"),
    0x5FAE: (
        "you_are_dead",
        "Mort du joueur : '<NAME>DEAD', affiche le score puis relance (code_3C8B)",
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
    0x6C09: (
        "act_v14_12",
        "Gollum : au bon endroit, affiche un message (prepare par le jeu)",
    ),
    0x6C33: (
        "act_v14_11",
        "Action jouee une seule fois : remet un verrou et memorise des valeurs",
    ),
    0x6C8D: (
        "act_v14_09",
        "PNJ : dans certains lieux, annonce l'arrivee d'un personnage",
    ),
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
    # ---- AnimAction : VM des PNJ (le 'cerveau' d'un personnage, $4E59-$5279) ----
    # entity_tick parcourt la table $2B45 et joue quelques opcodes de script par
    # personnage et par tour. Les helpers ci-dessous implementent le jeu d'opcodes
    # (MOVE/ACT/INDIR/RAND/GOTO) et la mecanique de deplacement/visibilite.
    0x69E7: (
        "victory_check",
        "Victoire : quand le compte est bon, la foule acclame et le score est credite",
    ),
    0x4C5D: (
        "indirect_call",
        "Appelle la routine dont l'adresse a ete posee dans $4C64/$4C65 (dispatch des tables d'actions)",
    ),
    0x5008: (
        "entity_tick_done",
        "Fin de la table des entites : restaure le contexte du joueur",
    ),
    0x5048: (
        "script_move",
        "Opcode MOVE long : avance le PC puis deplace le personnage (ou joue l'action ACT)",
    ),
    0x50AC: (
        "script_move_short",
        "Opcode MOVE court : deplace (wid), ou saute (bit $10) si l'operande vaut $FF",
    ),
    0x5127: (
        "move_announce",
        "Annonce un deplacement de PNJ : si visible du joueur, decrit la scene et joue l'action",
    ),
    0x51CA: (
        "script_rand",
        "Opcode RAND : tire une cible au hasard parmi min(op, n) entrees de la table de base",
    ),
    0x51DA: (
        "script_indir",
        "Opcode INDIR : saute a la cible choisie dans la table de base de l'entite",
    ),
    0x520D: (
        "entity_find",
        "Retrouve l'entree d'un personnage par son id dans la table $2B45",
    ),
    0x5235: (
        "entity_tick_init",
        "Init du tick : lieu du joueur, detection du noir, compteur de bruit",
    ),
    # ---- AnimAction : moteur d'errance / placement des PNJ ($3E5B-$406F) ----
    # Quand un personnage doit se deplacer seul (errance), le jeu empile ses
    # commandes dans $4905 et evalue les destinations candidates ($48D3) sous
    # contrainte de poids (budget $0A). Ces routines constituent ce moteur.
    0x3E5B: (
        "actq_pull",
        "Retire l'action suivante de la file $4905 et prepare ses tokens (reprise du parseur)",
    ),
    0x3E8E: (
        "cand_check",
        "Teste si le personnage courant figure dans la liste de candidats $48D3",
    ),
    0x3EB2: (
        "wander_core",
        "Coeur du moteur d'errance : parse les deplacements en file et calcule leur poids",
    ),
    0x3EC4: (
        "wander_eval",
        "Boucle d'evaluation : rejoue chaque commande de deplacement en file via parse_cmd",
    ),
    0x3ED0: (
        "wander_accum",
        "Cumule le poids de la commande (macc += $65) puis detecte la fin de file ($C0 -> $90)",
    ),
    0x3EF1: (
        "wander_slot",
        "Cherche un slot libre en $48D3 et deduit du budget mwt le poids des candidats retenus",
    ),
    0x3F0A: (
        "wander_budget",
        "Budget restant nul -> abandon ; sinon prepare le comptage des enregistrements",
    ),
    0x3F11: (
        "wander_count_init",
        "Initialise le comptage : mcnt=0, $6C=macc, ptr2=$4927",
    ),
    0x3F26: (
        "wander_count",
        "Parcourt les enregistrements de commande et compte ceux qui tiennent dans le budget",
    ),
    0x3F3F: (
        "wander_count_ok",
        "Aucun enregistrement retenu -> abandon du plan",
    ),
    0x3F46: (
        "wander_retain",
        "Retient le candidat (id $90, poids mcnt) et empile ses enregistrements a $47E3",
    ),
    0x3F6C: (
        "wander_pack",
        "Recopie mcnt enregistrements de commande (24 o) vers $47E3 + 24*(10-mwt)",
    ),
    0x3F6E: (
        "wander_pack_byte",
        "Boucle interne d'empilement : un octet d'enregistrement a la fois",
    ),
    0x3F7F: (
        "wander_start",
        "Declenche le deplacement d'errance retenu pour le personnage courant",
    ),
    0x3F8E: (
        "wander_step",
        "Execute le deplacement d'errance : choisit un candidat, tente le move, memorise l'echec",
    ),
    0x3FE5: (
        "wander_rewind",
        "Rembobine la file des commandes et consomme le poids du deplacement",
    ),
    0x4035: (
        "wander_select",
        "Selectionne l'entree candidate (index) et pointe sa suite de commandes",
    ),
    0x4051: (
        "wander_remove",
        "Retire un personnage de la liste des candidats d'errance",
    ),
    0x4737: ("fetch_retaddr", "Recupere l'adresse de retour empilee"),
    0x71DB: ("tape_load", "Charge un bloc depuis la cassette et verifie son en-tete"),
    0x7215: (
        "tape_save",
        "Ecrit un bloc sur la cassette (leader, en-tete, donnees, checksum)",
    ),
    0x72A0: (
        "tape_prompt",
        "Affiche les invites de cassette ('PREPARE TAPE', 'PRESS ANY KEY'...)",
    ),
    0x7353: (
        "get_key",
        "Lit le clavier : renvoie la touche appuyee, ou 'aucune touche'",
    ),
    0x7481: ("wait_for_key", "Attend que le joueur appuie sur une touche"),
    0x7489: ("cr_out", "Affiche un retour a la ligne"),
    0x7491: (
        "ch_out",
        "Point d'entree de l'affichage : peut ignorer certains caracteres selon le contexte",
    ),
    0x75B4: (
        "print_char",
        "Dessine un caractere a l'ecran graphique avec la police du jeu",
    ),
    0x75F6: (
        "ch_put",
        "Affiche un caractere : gere espaces, saut de ligne, effacement, majuscules et pause",
    ),
    0x7619: (
        "pause_key",
        "Toutes les 16 lignes, marque une pause pour laisser le joueur lire",
    ),
    0x7747: ("hires_clear", "Efface l'ecran graphique"),
    0x7779: (
        "game_main",
        "Prepare l'affichage hires (clear, bordures, pointeurs police/ecran) puis rend la main a start",
    ),
    # Moteur d'illustrations vectorielles (consomme le bloc 3 : table $7AC0
    # [cle,mot] x13 + flux d'octets termine par $00 ; valide par rendu sim65 des
    # 13 images via un pilote vec_init + dump hires).
    0x4750: (
        "img_show",
        "Affiche l'illustration associee a une cle (si elle existe)",
    ),
    0x77D4: (
        "drawing",
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
    0x79FB: (
        "vec_testpx",
        "Illustration : teste si un pixel est dans la zone dessinable",
    ),
    0x7A0F: ("vec_plot", "Illustration : allume un pixel"),
    0x7A22: ("vec_addr", "Illustration : calcule l'adresse d'un pixel"),
    # ---- Execution d'une commande joueur / description ----
    0x357C: (
        "cmd_run",
        "Chaine d'execution d'une commande joueur : tente le deplacement, sinon lance l'action",
    ),
    0x36D5: (
        "cmd_probe",
        "Rejoue la commande en mode sonde (phase=0) et renvoie passok : l'action passe-t-elle ?",
    ),
    0x4B37: (
        "perform_action",
        "Execute la commande du joueur : verifie noirceur et compatibilite verbe/objet, puis lance l'action",
    ),
    0x417C: (
        "describe_room",
        "Decrit le lieu courant : nom, sorties visibles (LOOK et arrivee dans un lieu)",
    ),
    0x4D84: (
        "intro_look",
        "Premier regard au demarrage : cale la fiche du joueur puis decrit le lieu de depart",
    ),
    0x4D47: (
        "unit_remove",
        "Retire un personnage du jeu : marque son record puis le sort des listes d'etat et d'errance",
    ),
    0x3B75: (
        "special_cmd",
        "Dispatch des commandes speciales (SAVE/LOAD/QUIT/HELP/SCORE/PAUSE/ALL/EXCEPT/IT/ONE/PRINT)",
    ),
    # ---- Deplacement joueur : entree et essais en deux temps ----
    0x358F: (
        "move_raz",
        "Remet a zero l'espace de resolution ($D7-$E7) et le mode brut avant un essai de deplacement",
    ),
    0x359B: (
        "move_begin",
        "Entree du deplacement : force arg1/arg2=$FF, raz puis cherche la sortie correspondant au mot",
    ),
    0x35AE: (
        "move_go",
        "Suite d'un deplacement : cale wid sur l'index de sortie ($6C), derive les options et tente l'essai",
    ),
    0x35E4: (
        "move_iter",
        "Un essai de deplacement : resout un objet-porte, sinon enchaine sur l'essai suivant",
    ),
    0x35FD: (
        "move_iter2",
        "Essai suivant : incremente le compteur d'objet ($D9) et reprend la resolution",
    ),
    0x361C: (
        "move_iter_none",
        "Aucun objet-porte : rejoue l'action en sonde (cmd_probe) puis reprend",
    ),
    0x3622: (
        "move_second",
        "Resout le 2e operateur d'un deplacement a plusieurs objets",
    ),
    0x363E: (
        "move_find_obj",
        "Cherche dans les records un objet-porte (record+1 bit6) dont l'id vaut arg1",
    ),
    0x3674: (
        "move_saveopt",
        "Met de cote les options de la sortie (svptr) sauf si une annonce est en cours ($7E)",
    ),
    0x3679: (
        "move_saveptr",
        "Sauve le pointeur de travail dans svptr (branche directe)",
    ),
    0x3690: ("move_saveptr2", "Meme sauvegarde pour la variante (dans $EA/$EB)"),
    0x36A5: (
        "move_pick_tbl",
        "Choisit la table de conditions (directe $1A5F / etendue $1A62) selon xaux",
    ),
    0x36BB: (
        "move_gate",
        "Porte de controle du deplacement : teste xmode/$D8 et rend 1 (continuer) ou 0",
    ),
    0x3743: (
        "move_core_end",
        "Fin de move_core : restaure les pointeurs de travail et rend le resultat",
    ),
    # ---- Resolution de la sortie et des operandes ($37xx-$39xx) ----
    0x3790: (
        "exit_resolve",
        "Construit les arguments VM de la commande puis cherche la sortie du lieu correspondant au mot",
    ),
    0x37DE: (
        "exit_scan",
        "Boucle de parcours des sorties du lieu (pas de 8) jusqu'a correspondance ou fin de table",
    ),
    0x3804: ("exit_found", "Sortie trouvee : assemble ses arguments et rend 1"),
    0x380A: (
        "exit_build_args",
        "Prepare les 2 operandes de la sortie (echange + copie des conditions) et leurs offsets",
    ),
    0x384A: ("exit_arg_swap", "Mise en forme des operandes : echange selon xmode"),
    0x3851: ("exit_arg_mix", "Suite de mise en forme des operandes (bits de xmode)"),
    0x3868: (
        "exit_arg_load",
        "Charge les conditions de la sortie dans l'espace de travail",
    ),
    0x38A0: (
        "op_load_cond",
        "Copie des octets de condition depuis le record vers l'espace de travail",
    ),
    0x38C9: (
        "op_copy_pair",
        "Recopie une paire d'operandes (mot + masque) du record de commande",
    ),
    0x38E2: (
        "op_stub",
        "Saut indirect auto-modifie vers le matcher ($53C3 direct ou $54F8 variante)",
    ),
    0x38E5: (
        "op_resolve1",
        "Boucle de resolution du 1er operande : essaye chaque candidat jusqu'a ce que l'action passe",
    ),
    0x3908: (
        "op_loop1",
        "Corps de la boucle de resolution du 1er operande (sauve/restaure les pointeurs)",
    ),
    0x3928: (
        "op_step1",
        "Un candidat du 1er operande : matche, pose arg1 et rejoue l'action (cmd_probe)",
    ),
    0x3948: ("op_resolve2", "Boucle de resolution du 2e operande"),
    0x396D: ("op_loop2", "Corps de la boucle de resolution du 2e operande"),
    0x3993: (
        "op_step2",
        "Un candidat du 2e operande : matche, pose arg2 et rejoue l'action",
    ),
    # ---- Assemblage des arguments VM / revision d'action ($39xx-$3Bxx) ----
    0x39B1: (
        "print_spc",
        "Affiche le message inline en mode reel (raw=1, phase=1) ; variante de print_msg",
    ),
    0x39B7: ("set_real", "Repasse en mode reel : raw=1 et phase=1"),
    0x39BE: (
        "vm_arg_set",
        "Copie le record de commande (24 o) vers le tampon de travail $490F",
    ),
    0x39CF: (
        "rev_1",
        "Assemble un argument depuis l'espace de travail, affiche le message puis rend 1",
    ),
    0x39D3: (
        "rev_1_loop",
        "Corps de rev_1 : copie une paire d'octets vers l'argument VM",
    ),
    0x39EE: (
        "rev_dispatch",
        "Aiguillage de revision d'apres les etats $D8/$DB (2e operande)",
    ),
    0x3A0B: (
        "rev_dispatch2",
        "Aiguillage de revision d'apres les compteurs $DA/$D9 (1er operande)",
    ),
    0x3A2D: ("rev_real", "Rejoue l'action en mode reel (set_real + perform_action)"),
    0x3A36: ("rev_obj2", "Resolution du 2e objet en variante puis reprise de l'action"),
    0x3A6B: ("rev_obj1", "Resolution du 1er objet en direct puis reprise de l'action"),
    0x3AB5: (
        "rev_exec2",
        "Assemble les arguments VM et enchaine l'execution (variante 2)",
    ),
    0x3ADF: (
        "rev_exec1",
        "Assemble les arguments VM et enchaine l'execution (variante 1)",
    ),
    0x3B21: ("rev_sel_lo", "Fixe la source des 2 derniers mots d'argument (jeu bas)"),
    0x3B26: ("rev_sel_hi", "Fixe la source des 2 derniers mots d'argument (jeu haut)"),
    0x3B28: (
        "rev_sel",
        "Ajoute conditionnellement 2 mots de la fiche de sortie au bloc d'arguments",
    ),
    0x3B52: ("rev_sel2", "Seconde partie de rev_sel (octet +7 bit7 de la sortie)"),
    # ---- Epilogue d'action ----
    0x5A62: (
        "act_look",
        "Epilogue d'action : en mode reel decrit le lieu (describe_room), en sonde rend passok=0",
    ),
    # ---- Objets, records et tables ----
    0x530B: (
        "locate_location",
        "Retrouve la fiche d'un lieu a partir de son identifiant (table $2070, id < $50)",
    ),
    0x5331: (
        "locate_object",
        "Retrouve la fiche d'un objet a partir de son identifiant (table $1A62)",
    ),
    0x5399: (
        "index_id_table",
        "Cherche une cle dans une table d'entrees de 3 octets [cle,lo,hi], fin $FF",
    ),
    0x5394: ("index_id_table2", "Comme index_id_table, mais pour des entrees de 2 octets"),
    0x52EA: (
        "verb_obj_ok",
        "Teste si le verbe courant est autorise pour l'objet (liste attachee au record)",
    ),
    0x4CDF: (
        "obj_check",
        "Verifie l'etat d'un objet avant l'action (porteur, presence) ; peut annoncer qui le porte",
    ),
    # ---- Pile interne des pointeurs de travail ($0200) ----
    0x46E6: (
        "push_ptr",
        "Sauvegarde ptr ($8A) puis ptr2 ($88) sur la pile interne $0200",
    ),
    0x4702: ("push_ptr2", "Sauvegarde ptr2 ($88) sur la pile interne $0200"),
    0x471B: (
        "pop_ptr2",
        "Restaure ptr2 ($88) depuis la pile interne $0200 puis rend la main",
    ),
    0x471E: ("pop_ptr", "Restaure ptr ($8A) depuis la pile interne $0200"),
    # ---- Documentation exhaustive des routines restees anonymes (Lxxxx/code_xxxx) ----
    # Deuxieme passe : chaque sous-routine encore non baptisee est nommee et
    # resume en une ligne (cf. docs/block4-analysis.md). Regroupees par sous-systeme.
    # -- Boot / parser : utilitaires internes --
    0x30DF: (
        "boot_ptr_step",
        "Avance les pointeurs de copie (ptr, $8C) et recule ptr2 d'un cran ; rend Z en fin de segment",
    ),
    0x340B: (
        "noun_slot_set6",
        "Cherche un emplacement libre du groupe nominal a partir de l'offset 6 et y range l'adresse du mot",
    ),
    0x3429: (
        "noun_prep_count",
        "Compteur de prepositions ($9D) : +1, echoue au-dela de 2, sinon cherche un emplacement",
    ),
    0x343A: (
        "noun_slot_put",
        "Range le groupe nominal courant dans l'enregistrement de commande (offset selon $6D) ou echoue",
    ),
    0x3466: (
        "noun_store_adj",
        "Range le groupe nominal courant a l'offset 4 de l'enregistrement (cas adjectif)",
    ),
    # -- Commandes speciales / errance --
    0x3C46: (
        "one_flag_store",
        "IT/ONE : selon le bit7 de $6D, range le groupe nominal a l'offset 4 ou $0E",
    ),
    0x3CD4: (
        "score_show",
        "SCORE : affiche 'YOU HAVE MASTERED' puis le pourcentage du score (code_3CE0)",
    ),
    0x3D14: (
        "score_digit",
        "SCORE : extrait un chiffre decimal d'un compteur BCD par soustractions repetees",
    ),
    0x3D6A: (
        "load_block",
        "LOAD : charge un bloc via tape_tramp et vec_02 ; en echec affiche TAPE LOADING ERROR",
    ),
    0x3E95: (
        "wander_reset",
        "Moteur d'errance : remet a zero les index de parcours (X/Y) avant le balayage",
    ),
    0x4038: (
        "wander_add_cand",
        "Moteur d'errance : retient un candidat $48D3 (index cand, poids mwt)",
    ),
    0x406D: (
        "read_key",
        "Lit une touche au clavier (get_key) et signale si une touche est presente",
    ),
    0x40AC: (
        "line_clear",
        "Efface toute la ligne de saisie (touche DEL) et repositionne le curseur",
    ),
    # -- Deplacement / description du lieu --
    0x4141: (
        "move_flags_decode",
        "Decode les drapeaux de la sortie courante (exitp) vers xaux/xmode (direct ou variante)",
    ),
    0x416A: (
        "move_run_real",
        "Execute le mouvement en mode reel (phase=1) puis decrit le lieu s'il n'y a pas d'annonce",
    ),
    0x4232: (
        "exit_word_out",
        "Affiche le mot de sortie pointe par exitp (adresse + page) via word_render",
    ),
    0x433A: (
        "exit_sig_match",
        "Teste les 3 paires (mot, masque) d'une sortie contre l'entree courante",
    ),
    0x436C: (
        "sig_match_a",
        "Compare la 1re paire (mot, masque) d'une signature a l'operande courant (nibble bas)",
    ),
    0x4387: (
        "sig_match_b",
        "Compare une paire croisee de la signature a l'operande courant",
    ),
    0x43A8: (
        "sig_match_c",
        "Compare une autre paire croisee de la signature a l'operande courant",
    ),
    0x43E4: (
        "room_cond_ptr",
        "Fiche du lieu : pointe record+2 (acces aux conditions de deplacement)",
    ),
    0x43F3: (
        "obj_cond_ptr",
        "Fiche de l'objet : pointe record+8 (acces aux conditions de deplacement)",
    ),
    0x4402: (
        "probe_flag_end",
        "Repasse en mode sonde (phase=0) quand une annonce est en cours ($5E)",
    ),
    # -- Rendu des messages --
    0x4507: (
        "tok_ptr_seek",
        "Rendu : avance le pointeur de travail de tidx (position courante dans le message)",
    ),
    0x454F: (
        "tok_obj_cur",
        "Rendu marqueur $06 : affiche le nom de l'objet courant (obj)",
    ),
    0x455B: (
        "tok_obj_direct",
        "Rendu marqueur $07 : affiche le nom de l'objet direct (arg1)",
    ),
    0x4573: (
        "tok_obj_variant",
        "Rendu marqueur $07 variante : affiche le nom du second objet (arg2)",
    ),
    0x4683: (
        "word_dispatch",
        "Rendu d'un mot : applique la capitalisation puis word_render (tables $28BC/$28C4)",
    ),
    0x469B: (
        "word_cap_fix",
        "Rendu : ajuste majuscule et suffixe (cap) selon le nibble de la tete de mot",
    ),
    0x46E9: (
        "push_ptr_ax",
        "Sauve A et X puis empile ptr ($8A) sur la pile interne $0200 (entree de push_ptr)",
    ),
    # -- Execution de commande --
    0x4B07: (
        "action_probe",
        "Sonde une action sans l'executer : passok=1 si le verbe est autorise pour l'objet",
    ),
    0x4C57: ("cannot_do", "Affiche 'I CANNOT DO THAT' et rend la main"),
    0x4C6D: (
        "announce_move",
        "Annonce le deplacement de l'objet courant aupres du joueur (entity_goto)",
    ),
    # -- Intro / evenements / description des lieux --
    0x4D95: (
        "probe_guard",
        "Garde de sonde : si phase et passok, depile deux octets pour sortir de l'appelant",
    ),
    0x4D9E: (
        "print_via_stack",
        "Empile une adresse de reprise puis saute a print_msg (helper d'affichage inline)",
    ),
    0x4DB7: (
        "intro_caption",
        "Prepare et affiche le message contextuel $13E0 (helper de description)",
    ),
    0x4DF6: (
        "room_image_msg",
        "Affiche la description du lieu courant (locate_location puis texte du record)",
    ),
    0x4E20: (
        "record_desc_out",
        "Affiche le texte de description pointe par un enregistrement",
    ),
    0x4E33: (
        "record_words_out",
        "Affiche les mots d'un enregistrement de lieu (3 paires) via record_words_render",
    ),
    0x501E: (
        "script_adv4",
        "Avance le script d'un personnage de 4 octets (script_adv)",
    ),
    # -- Resolution d'objet / d'operande / d'action --
    0x52CA: (
        "arg1_check",
        "Verifie la presence et le role du 1er objet (arg1/direct/obj/variant) avant l'action",
    ),
    0x5349: (
        "light_from_arg1",
        "Teste si l'objet arg1 fournit de la lumiere (utilise par is_dark)",
    ),
    0x534B: (
        "light_from_a",
        "Teste si l'objet passe dans A fournit de la lumiere (offset de drapeau en X)",
    ),
    0x534D: (
        "light_test_core",
        "Coeur du test de lumiere : cherche un objet dans la fiche courante, rend C=1 si trouve",
    ),
    0x535F: (
        "obj_present",
        "Parcourt les objets presents pour retrouver obj (rend C=1 si trouve)",
    ),
    0x5374: (
        "obj_room_slot",
        "Fiche de l'objet A puis pointe son emplacement de lieu (record+$10)",
    ),
    0x53C3: (
        "cond_match_direct",
        "Matcher direct : filtre les records compatibles (conditions comparees a record+8)",
    ),
    0x540F: (
        "step3byte_table",
        "Avance le pointeur d'enregistrement de 3 octets (rend l'etat Z)",
    ),
    0x542C: (
        "step3byte_table_next",
        "Sauve A, avance de 3 octets (step3byte_table) puis restaure A en conservant le Z",
    ),
    0x5439: (
        "act_try_obj",
        "Tente une action sur un objet (via act_try_core) en sauvant le contexte",
    ),
    0x5454: (
        "act_try_core",
        "Coeur de resolution : parcourt les records compatibles et rejoue l'action",
    ),
    0x54A9: (
        "act_try_swap",
        "Echange (ptr)/(ptr2) puis relance la resolution d'action",
    ),
    0x54B2: (
        "swap_ptr_ptr2",
        "Echange les pointeurs ptr et ptr2 (adresses et octets hauts)",
    ),
    0x54C8: (
        "record_scan",
        "Sauve le contexte puis scanne les enregistrements d'une fiche",
    ),
    0x54E9: ("cond_match_alt", "Matcher variante : compare les conditions a record+2"),
    0x54F8: (
        "cond_match_var",
        "Matcher de variante : balaye les records jusqu'a correspondance de signature",
    ),
    0x5521: (
        "record_copy8",
        "Copie les 8 premiers octets d'un enregistrement vers le suivant (ptr2 += 8)",
    ),
    0x5535: (
        "record_words_render",
        "Affiche les paires de mots d'un enregistrement (word_render) hors imbrication",
    ),
    0x5576: (
        "slot_count",
        "Compte les slots d'un objet dans la table $1A5F (flag bit7) et rend le compte",
    ),
    0x55AE: (
        "slot_alloc3",
        "Cherche un emplacement de taille 3 pour l'objet courant (table $1A62) et rend X",
    ),
    0x55B3: (
        "slot_alloc2",
        "Cherche un emplacement de taille 2 pour l'objet courant (table $1A62) et rend X",
    ),
    0x55C9: (
        "slot_find_free",
        "Cherche un emplacement libre de la table $1A62 et y ecrit l'objet",
    ),
    0x5612: (
        "event_arm_obj",
        "Arme l'evenement de cle X pour l'objet courant (table $1A5F)",
    ),
    0x5651: (
        "event_key_scan",
        "Parcourt $1A5F et fixe la cle d'evenement de l'enregistrement correspondant",
    ),
    0x568D: ("holder_scan", "Parcourt $1A5F et met a jour le porteur d'un objet"),
    0x56D9: (
        "ratio_scale",
        "Ajuste un compteur selon un ratio (comparaison L570F/L5710)",
    ),
    0x5711: ("prob_from_arg1", "Teste une probabilite pour l'objet arg1 (table $1A5F)"),
    0x5713: (
        "prob_scan",
        "Coeur du test de probabilite : parcourt $1A5F pour l'objet courant",
    ),
    0x576D: ("weapon_test_a", "Verifie l'objet arg1 en tant qu'arme (variante A)"),
    0x576F: (
        "item_flag_test",
        "Teste un flag d'objet (A) et met a jour son etat (variante 1)",
    ),
    0x5774: (
        "item_flag_test2",
        "Teste un flag d'objet (A) et met a jour son etat (variante 2)",
    ),
    0x5793: (
        "call_action_at",
        "Pose l'adresse X/Y dans $4C64/$4C65 puis l'appelle (indirect_call)",
    ),
    0x579F: (
        "call_action_off",
        "Prepare l'appel indirect de l'action dont l'adresse est lue dans un record (Y)",
    ),
    0x57BB: (
        "get_object_location",
        "Resout lieu et etat d'un personnage a partir de sa fiche",
    ),
    0x57D5: (
        "obj_render_lookup",
        "Retrouve un objet et affiche son nom (via cond_match_alt)",
    ),
    0x580F: (
        "list_visible_init",
        "Affiche les objets visibles d'un lieu, ou 'NOTHING' si aucun",
    ),
    0x5836: (
        "list_visible_scan",
        "Balaye les objets d'un lieu et les rend (filtre L5835)",
    ),
    0x58E7: (
        "obj_visible",
        "Teste si l'objet A est visible dans le lieu courant (flags du record)",
    ),
    0x5959: (
        "room_objects_out",
        "Affiche les objets presents dans un lieu (record+$0A)",
    ),
    0x59E7: (
        "word_ptr_table",
        "Affiche un mot via une paire de pointeurs (table $59F7)",
    ),
    0x5A0D: (
        "room_desc_show",
        "Affiche la description d'un lieu (locate_location, offset 7)",
    ),
    0x5A43: (
        "rec_ptr_adv3",
        "Avance le pointeur d'enregistrement de 3 octets (parcours)",
    ),
    0x5A70: ("obj_flag1_test", "Teste le bit0 du flag record+7 et branche"),
    0x5A85: ("obj_flag20_test", "Teste le bit5 du flag record+7 et branche"),
    0x5A9D: ("name_from_record", "Affiche un nom d'objet lu a l'adresse (ptr)+8"),
    0x5AF0: (
        "obj_state_clear",
        "Remet a zero des champs d'etat d'un objet (record+$0C/+$0D) et branche",
    ),
    0x5B1B: (
        "obj_flag48_test",
        "Teste les bits du flag record+7 (masque $48) contre $40",
    ),
    0x5B9B: (
        "obj_type_route",
        "Aiguille le traitement selon le type de l'objet (record+4 et 7 == 6)",
    ),
    0x5BBB: ("light_gate", "Teste la presence de lumiere (light_from_arg1) et branche"),
    0x5C2B: (
        "obj_count_add",
        "Ajoute une quantite (record+3) a l'objet via un emplacement de la table",
    ),
    0x5C88: (
        "obj_render_resolve",
        "Resout l'objet courant et l'affiche (locate_object puis rendu)",
    ),
    0x5D53: (
        "combat_round",
        "Tour de combat : resout l'adversaire puis enchaine l'action",
    ),
    0x5DCB: (
        "act_probe_event",
        "Joue act_probe puis arme l'evenement associe (evt_lookup) si le joueur est implique",
    ),
    0x5DFD: (
        "dark_gate",
        "Garde d'obscurite : rend sans rien faire si le lieu est sombre",
    ),
    0x5E50: (
        "obj_two_words",
        "Affiche les 2 mots d'un objet lus a l'adresse $CA (L466F/L4670)",
    ),
    0x5E66: (
        "obj_enter_check",
        "Verifie si un objet peut entrer dans le lieu ou etre porte (flags record+7)",
    ),
    0x5FBD: ("obj_id_minus1", "Lit (orec)+0 moins 1 (index d'objet)"),
    0x6250: (
        "obj_flag_clear",
        "Remet a zero le flag (mask $10) de (orec)+4 selon le contexte",
    ),
    0x6341: (
        "counter_add_ratio",
        "Ajoute un ratio (0-10 via ratio_scale) a un compteur, avec saturation",
    ),
    0x64D7: ("obj_flag20_get", "Teste le bit5 de (ptr)+7 (utilitaire d'action)"),
    0x6AE3: ("rand_half", "Tirage 0-99 compare a 50 (rend C=1 si superieur ou egal)"),
    0x6DEF: ("at_room_1E", "Verifie si le joueur se trouve dans le lieu $1E"),
    0x6EF7: (
        "img_poke",
        "Illustration : si le bloc 3 est present, modifie 2 octets a (ptr)+1",
    ),
    # -- Cassette et affichage hires / vectoriel --
    0x720A: ("tape_dot", "Affiche un point avant une operation cassette"),
    0x72FC: (
        "tape_read_verify",
        "Lit un bloc cassette et verifie son en-tete et son checksum",
    ),
    0x7454: (
        "via_scan",
        "Scan clavier bas niveau : teste une ligne et une colonne du VIA",
    ),
    0x7464: (
        "via_setup_ee",
        "Configure le VIA pour le scan clavier (valeur $EE en $030C)",
    ),
    0x7472: (
        "via_setup_ec",
        "Configure le VIA pour le scan clavier (valeur $EC en $030C)",
    ),
    0x7514: (
        "hires_scroll_setup",
        "Prepare un defilement hires (repertoire de lignes $B940)",
    ),
    0x754B: ("hires_row_next", "Avance d'une ligne la copie d'ecran hires"),
    0x7551: ("hires_col_next", "Avance d'une colonne la copie d'ecran hires"),
    0x7558: (
        "hires_fill_setup",
        "Prepare un remplissage d'ecran hires (pointeurs $BF3F)",
    ),
    0x758F: ("hires_row_prev", "Recule d'une ligne la copie d'ecran hires"),
    0x759A: ("hires_col_prev", "Recule d'une colonne la copie d'ecran hires"),
    0x75A6: ("cursor_adv", "Avance le curseur texte (col--, position++)"),
    0x75AB: ("cursor_back", "Recule le curseur texte (col++)"),
    0x7694: ("hires_clear_zone", "Efface une zone de l'ecran hires par blocs"),
    0x76DF: ("cursor_down", "Descend le curseur texte d'une ligne"),
    0x76E4: ("cursor_up", "Remonte le curseur texte d'une ligne"),
    0x76ED: (
        "char_plot_pos",
        "Dessine le caractere A a la position texte courante (via L75B8)",
    ),
    0x76F9: ("via_write", "Ecrit une valeur sur le port clavier du VIA ($0300/$0301)"),
    0x770A: ("via_reset", "Reinitialise le port clavier du VIA ($0302/$0303)"),
    0x771A: ("screen_scroll", "Defile verticalement l'ecran hires (copie de lignes)"),
    0x781D: ("vec_next_byte", "Illustration : avance le pointeur de flux d'un octet"),
    # -- Cibles des vecteurs $2Cxx encore anonymes --
    0x71A8: (
        "vec_keypause",
        "Illustration (vec_01) : attend une touche avant de poursuivre",
    ),
    0x71CB: ("tape_verify", "Verifie un bloc cassette en le relisant (vec_04)"),
    0x71FF: ("ok_rts", "Rend la main avec C=0 (succes) (vec_08)"),
    0x7201: ("vec_cr", "Affiche un retour a la ligne (vec_10)"),
    0x7204: ("vec_kbd_clear", "Remet a zero le registre clavier VIA $030B (vec_09)"),
    0x7293: ("tape_prompt_save", "Affiche 'PREPARE TAPE FOR GAME SAVE' (vec_06)"),
    0x729B: ("tape_prompt_verify", "Affiche 'REWIND TAPE FOR VERIFICATION' (vec_07)"),
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
    0x0C: (
        "phase",
        "0 = simulation (le jeu calcule sans rien afficher), 1 = action reelle",
    ),
    0x0D: ("raw", "Affichage brut : 1 = texte force, sans mise en forme"),
    0x0E: ("cap", "1 = mettre une majuscule a la prochaine lettre (apres un point)"),
    0x0F: ("sppend", "Un espace a inserer avant le prochain mot"),
    0x11: (
        "crcnt",
        "Nombre de lignes affichees depuis la derniere pause (remis a zero toutes les 16)",
    ),
    0x12: ("passok", "1 = la simulation a reussi, on passe a l'action reelle"),
    # Operandes de commande (parser L359B, VM L5048/L50AC, $FF=absent).
    0x13: ("wid", "Mot courant interprete (verbe ou direction)"),
    0x15: ("arg1", "Premier objet de la commande ($FF = aucun)"),
    0x16: ("arg2", "Second objet de la commande ($FF = aucun)"),
    # Enregistrements d'objets (deref ($..),y ; swap L57A1).
    0x17: ("orec", "Pointeur vers la fiche du premier objet (octet haut en $18)"),
    0x19: ("orec2", "Pointeur vers la fiche du second objet (octet haut en $1A)"),
    0xC6: (
        "crec",
        "Pointeur vers la fiche courante (compteurs du personnage/objet en cours)",
    ),
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
    # Resolution de commande (deplacement/action : $D7-$E7, $EC-$F7).
    0xD7: (
        "op1",
        "Etat du 1er operateur lors de la resolution d'une sortie (bits 0 et 1 testes)",
    ),
    0xD8: ("op2", "Etat du 2e operateur lors de la resolution (bits 0 et 1 testes)"),
    0xD9: ("rn1", "Compteur n°1 de la boucle de resolution d'operande"),
    0xDA: ("rn2", "Compteur n°2 de la boucle de resolution d'operande"),
    0xDB: ("rn3", "Compteur n°3 de la boucle de resolution d'operande"),
    0xEC: ("rbit", "Bit7 du 1er mot de la commande (flag direct/variante)"),
    0xED: ("ralt", "Compteur d'alternatives de la resolution"),
    0xEE: ("roff1", "Offset du 1er operateur dans le record de commande"),
    0xEF: ("roff2", "Offset du 2e operateur dans le record de commande"),
    0xF0: ("rid1", "Id du 1er operateur resolu"),
    0xF1: ("rid2", "Id du 2e operateur resolu"),
    0xF2: (
        "rword",
        "Mot/verbe de la commande en cours (alimente les arguments VM $466F)",
    ),
    0xF4: ("rarg1", "Operande n°1 de la commande (paire de mots VM)"),
    0xF6: ("rarg2", "Operande n°2 de la commande (paire de mots VM)"),
    # Pointeurs de travail universels.
    0x7A: ("ptr3", "Troisieme pointeur de travail (octet haut en $7B)"),
    0x88: ("ptr2", "Pointeur secondaire, pour balayer les tables (octet haut en $89)"),
    0x8A: ("ptr", "Pointeur de travail principal (octet haut en $8B)"),
    # Monde (entites, events, tirage).
    0x8F: ("key", "Cle de l'evenement a declencher"),
    0x93: ("noise", "Source du hasard (pour les tirages aleatoires)"),
    0xBE: ("exploc", "Lieu attendu par l'evenement en cours"),
    0xC5: (
        "obj",
        "Entite/acteur courant ($FF = personne) ; acteur du log AnimAction (ref. Wilderland L_ACTING_ANIMAL)",
    ),
    0xC8: (
        "ploc",
        "Lieu du joueur (simple copie : la vraie valeur est player.eloc en $1B2A)",
    ),
    0xC9: (
        "eloc",
        "Lieu d'un personnage (visible quand il est identique a celui du joueur)",
    ),
    0xCE: ("once", "Verrou 'une seule fois' : pose puis consomme"),
    # Scratch transitoire (moteur d'errance/placement des PNJ + file d'actions).
    0xC3: (
        "dflag",
        "Flag de l'action du dragon : initialise a 0 par l'intro, jamais arme (inactif)",
    ),
    0xC4: (
        "sflag",
        "Flag de sortie texte : arme au desarmement de l'evenement e7, ajoute un H apres s/S",
    ),
    0xCF: (
        "cand",
        "Index de candidat dans les tables de deplacement $48D3/$48D5 (moteur d'errance)",
    ),
    0xD0: (
        "mwt",
        "Budget/poids du deplacement (moteur d'errance : $0A moins les couts)",
    ),
    0xD1: (
        "qrd",
        "Curseur de lecture de la file d'actions $4905 (remis a 0 a chaque commande)",
    ),
    0xD2: (
        "qwr",
        "Curseur d'ecriture de la file d'actions $4905 (remis a 0 a chaque commande)",
    ),
    0xD3: ("macc", "Accumulateur de poids du moteur d'errance"),
    0xD4: ("mcnt", "Compteur de candidats retenus par le moteur d'errance"),
    0xD5: (
        "said",
        "Flag : le PNJ a parle/refuse (pose par code_6C2E, remis a 0 par act_v14_13)",
    ),
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
    0xF3: ("rword_hi", "Octet haut de rword"),
    0xF5: ("rarg1_hi", "Octet haut de rarg1"),
    0xF7: ("rarg2_hi", "Octet haut de rarg2"),
}

# Notes detaillees (multi-lignes) inserees AVANT le label d'une routine,
# en complement du resume une ligne de ROUTINE_DOCS. Servent a expliquer le
# FONCTIONNEMENT (algorithme, entree/sortie, effets), pas seulement le but.
# Cles = adresses de routines nommees (via ROUTINE_DOCS/VECTORS).
ROUTINE_NOTES: dict[int, list[str]] = {
    # --- Parser AnimTalk ---
    0x2DEA: [
        "Editeur de ligne du parser (prompt '> '). Lit les touches une a une et",
        "construit la commande dans le tampon $40BE jusqu'a un CR. Le dernier",
        "caractere doit etre un point ($2E) : ins_period l'ajoute si besoin, ce point",
        'sert de marqueur de fin pour le lexeur. Les guillemets " encadrent un nom ;',
        "l'etat ouvert/ferme est memorise en $B8. Backspace ($08) et DEL ($7F)",
        "corrigent la saisie. Les fleches sont converties en N/S/E/W (key_arrow).",
        "Sortie : A=1 quand la ligne est valide (CR), A=0 pour '@' en tete (annule).",
    ],
    0x2EA9: [
        "Traduit les codes des fleches Oric en lettres de direction : chaque fleche",
        "ecrit directement la lettre + un CR dans la commande ($40BE), ce qui declenche",
        "un deplacement immediat au tour suivant (sans mot-cle de direction).",
    ],
    0x2ED5: [
        "Lexeur : lit un mot du tampon $40BE a partir de X, puis le cherche dans le",
        "dictionnaire 5-bit du bloc 2. Etapes :",
        "  1. saute les espaces ; $60 = position du mot ; un CR donne le token $C0.",
        "  2. ponctuation immediate via punct_class (point $B0, virgule $A0, guillemet $90).",
        "  3. sinon dict_bucket decode le mot (lettres rangees en $47C3) et se place sur",
        "     le seau $0500[2*1re lettre], puis boucle dict_next/word_prefix_cmp.",
        "  4. word_finish (word_type) extrait le type (nibble de classe) et l'adresse du",
        "     mot dans le bloc 2. Type $D0 = entrees ignorees du parseur (mots de messages).",
        "Sortie : $5B = type ($C0 fin, $D0 inconnu, sinon classe<<4) ; adr/adr_hi =",
        "pointeur $0500+... ; A = $5B. Le mot est ensuite copie en file par l'appelant.",
    ],
    0x303C: [
        "Compare le mot saisi (lettres en $47C3, longueur $66) et le candidat du",
        "dictionnaire ($47D3, longueur $67) sur min($66,$67) caracteres. Rend A=0",
        "(Z) si le prefixe commun est identique, A=1 sinon. Sert au matcher.",
    ],
    0x3065: [
        "Recopie $65 mots de 24 octets (enregistrements de commande) depuis $4927",
        "vers $4A17, en n'emportant que les mots marques (bit $40 de l'octet +1).",
        "Prepare la forme consommee plus loin dans la boucle de commandes.",
    ],
    0x3111: [
        "Interpreteur de commande (grammaire). Consomme la file de tokens $4783",
        "construite par le lexeur et classe chaque mot par grammaire via la table",
        "$315A (index = type>>3, soit 2 x le nibble de classe).",
        "",
        "Classes (nibble de type du dictionnaire, cf. bloc 2) :",
        "  $00 adverbe   $10 IN/INTO     $20 direction   $30 verbe",
        "  $40 GO/RUN    $50 nom         $60 adjectif    $70 preposition",
        "  $80 article   $90 mot-cle special (SAVE/QUIT/HELP/ALL/EXCEPT/...)",
        "  $A0 AND/virgule   $B0 THEN/point(=fin de commande)",
        "",
        "Etat interne : $6D = drapeaux d'attente, $6E = portee (0 normal, 1 ALL,",
        "2 EXCEPT), $9D = compteur de virgules, $65 = nb de mots retenus, $5A/$5B =",
        "type precedent/courant, $5F = curseur de file, $A3..$AC = groupe nominal",
        "courant, (ptr2) = enregistrement de commande de travail (24 octets).",
        "Retour : A=0 (commande construite), A=1 ('WHAT ?'), A=2 (recommencer la saisie).",
    ],
    0x3144: [
        "Lit le token suivant (next_token) et calcule l'index de classe = type>>3,",
        "puis saute indirectement via la table $315A (adresses des handlers). La",
        "table est auto-patchee : l'operande de 'jmp ($315A)' est ecrit en $3158/$3159.",
    ],
    0x3485: [
        "Lit un token de la file $4783 a l'offset $5F : octet 0 = type (nibble haut)",
        "et page du pointeur (nibble bas) ; octet 1 = octet bas du pointeur. Recopie",
        "l'ancien type en $5A, le nouveau en $5B, l'adresse en adr/adr_hi, avance $5F.",
        "Sortie : A = $5B (type courant).",
    ],
    0x3172: [
        "Handler de classe 11 ($B0, point ; produit a la fin de chaque commande par",
        "l'editeur, et aussi THEN). Si un groupe nominal est en cours d'attente (bit1",
        "de $6D) mais qu'aucun mot n'a ete retenu, renvoie 2 (saisie a refaire) ; sinon",
        "renvoie 1 ou poursuit la finalisation de la commande a $3196.",
    ],
    0x34D0: [
        "Fusionne le mot pointe par (ptr) dans l'enregistrement courant (ptr2) :",
        "reporte le type et marque les champs ; recule d'un enregistrement (rec_prev)",
        "puis avance (rec_next). Si les champs +4/+5 sont non nuls, applique rec_fixup1.",
    ],
    0x4ED5: [
        "Fait jouer le script d'un personnage : son 'cerveau'. Appele a chaque tour",
        "par world_tick, pour CHAQUE entite active, meme quand le joueur est ailleurs.",
        "",
        "Table $2B45 : 17 entrees de 7 octets [id, nmax, PC_lo, PC_hi, base_lo, base_hi, reply],",
        "terminee par $FF. id=$00 = emplacement dormant (saute). PC = pointeur du script",
        "dans le bloc 2 ; base = table de sauts 3 o [cle, lo, hi] propre a l'entite ;",
        "nmax = index max (0-based) dans la table base (nb d'entrees - 1) ; reply =",
        "poids de replique (borne du tirage gating '<id>SAY NO', cf. action_talk_to ; 0 = muet).",
        "",
        "On execute au plus 6 opcodes par tick (garde-fou L4ED3, evite les boucles",
        "infinies). L'opcode est l'octet pointe par le PC ; on dispatch sur le nibble bas :",
        "  $x0/$x2 MOVE long  : wid=(PC)1, arg1=(PC)2, arg2=(PC)3 -> entity_move",
        "  $x1/$x3 ACT        : (PC)1 = index dans la table d'actions $7143",
        "  $x4     MOVE court : wid=(PC)1 ; $FF + bit $10 = saut inconditionnel",
        "  $x5-$xD INDIR      : saute via la table de base (script_indir $51DA)",
        "  $xC     GOTO cle   : entity_goto(id, cle) via la table de base",
        "  $xE     GOTO absolu: PC := (PC)1/(PC)2",
        "  $xF     RAND       : tire une cible parmi min(op, nmax) (script_rand $51CA)",
        "",
        "Apres un MOVE/ACT : bit $20 pose -> efface l'opcode (auto-modification, l'entite",
        "devient dormante) ; bit $10 pose -> si l'action echoue, saute de la taille de",
        "l'instruction (plan de secours). L'affichage est coupe pendant le calcul",
        "(outen=0) et retabli a la fin (entity_tick_done).",
    ],
    0x5235: [
        "Prepare un tour de la VM des PNJ : resout le lieu du joueur (ploc, via L57BB),",
        "teste s'il fait noir et arme le compteur d'ambiance L4ED4 (1 = noir ; passe a 2",
        "quand le bruit a ete signale). A lancer une fois avant de parcourir $2B45.",
    ],
    0x5008: [
        "Fin de la table $2B45 : remet obj=0, reautorise l'affichage (outen=1) et",
        "restaure le contexte du joueur (crec = sa fiche $1B1A, eloc = son lieu $1B2A).",
    ],
    0x5020: [
        "Avance le PC du script courant de A octets ($8C/$8D). Utilitaire bas niveau",
        "partage par les sauts d'instruction (script_step4 / script_step2).",
    ],
    0x502A: [
        "Passe a l'instruction suivante : avance le PC de 4 octets, +2 de plus si le",
        "bit $10 de l'opcode est pose (operande etendue), puis reecrit le PC dans l'entree",
        "de l'entite ((ptr2)+2/+3).",
    ],
    0x502C: [
        "Comme script_step4 mais pour les instructions courtes : avance de A octets",
        "(2 ou 3 selon l'appelant), +2 si le bit $10 de l'opcode est pose.",
    ],
    0x5048: [
        "Opcode 4 octets : avance le PC de 4 (+2 si bit $10). Si le bit0 de l'opcode",
        "est clair -> MOVE : wid=(PC)1, arg1=(PC)2, arg2=(PC)3 via entity_move. Sinon",
        "ACT : (PC)1 indexe la table $7143 ; l'action est jouee d'abord en mode sonde",
        "(phase=0) puis en reel si elle passe (passok).",
    ],
    0x50AC: [
        "Opcode MOVE court ($x4) : avance le PC de 2 (+2 si bit $10) et lit wid=(PC)1.",
        "Si wid != $FF : deplace la creature (arg1/arg2 = $FF). Si wid = $FF : saute a",
        "l'adresse (PC)2/(PC)3 quand le bit $10 est pose (saut inconditionnel).",
    ],
    0x51CA: [
        "Opcode RAND ($xF) : lit le nombre de choix (PC)1, borne l'index par le champ nmax",
        "de l'entite ((ptr2)+1), tire un index (rand_range) puis script_indir effectue le",
        "saut correspondant dans la table de base. C'est la part d'imprevisibilite des PNJ.",
    ],
    0x51DA: [
        "Opcode INDIR ($x5-$xD) : utilise l'index A (0 pour INDIR, tirage pour RAND),",
        "le borne a nmax ((ptr2)+1 = index max de la table base), lit la cible [index] dans",
        "la table de base ((ptr2)+4/+5, entrees de 3 octets) et pose le PC ((ptr2)+2/+3).",
    ],
    0x520D: [
        "Cherche dans la table $2B45 l'entree dont l'id vaut A (7 octets par entree,",
        "arret sur $FF). Sortie : ptr2 sur l'entree, A = id trouve, ou $FF si absent.",
    ],
    0x5249: [
        "Opcode GOTO par cle ($xC) : X = cle, A = id. Retrouve l'entite (entity_find),",
        "lit dans sa table de base l'entree de cle X (L5399) et reprend le script a",
        "l'adresse [cle] : permet des sauts 'nommes' a l'interieur d'un script.",
    ],
    0x511C: [
        "Deplace un personnage : appelle le moteur de deplacement partage move_core",
        "(trouve la sortie du lieu selon wid/arg1/arg2 et verifie ses conditions). Si le",
        "deplacement reussit, enchaine sur move_announce (visibilite, bruit, action).",
    ],
    0x5127: [
        "Suite d'un deplacement de PNJ : gere ce que le joueur percoit. Selon direct et",
        "la cible, il decrit l'arrivee dans le lieu du joueur (L417C) ou signale un bruit",
        "('YOU HEAR A NOISE', une fois par tour via L4ED4). Joue ensuite l'action (L4B37)",
        "et les repliques eventuelles (say_if_visible).",
    ],
    0x5279: [
        "Affiche un message de dialogue seulement si le personnage est visible du joueur.",
        "Conditions : id valide ($FF/$00 = rien), pas en pleine annonce (L4ED4 != 2),",
        "meme lieu que le joueur (ploc), drapeau L5611 actif. X/Y = adresse du message",
        "inline ; A = id du locuteur.",
    ],
    0x4C5D: [
        "Appel indirect generique : la cible a ete posee dans $4C64/$4C65 (depuis les",
        "tables d'actions $7014/$7143 ou la table d'evenements $7169). Sauve A et X,",
        "appelle la cible, restaure les registres et l'affichage (L471B).",
    ],
    0x69E7: [
        "Teste la condition de victoire ($1F38 == $25) ; si elle est remplie, la foule",
        "acclame (message $1722), ajoute au score et termine la partie (code_5FB7).",
        "Appelee au tout debut de world_tick (avant les PNJ).",
    ],
    0x3E8E: [
        "Parcours la liste de candidats d'errance $48D3 (entrees de 5 octets [id, poids,",
        "etat, lo, hi]) : rend A = $90/obj si le personnage courant y figure, A = 1 sinon.",
        "Sert a savoir si un PNJ est deja en cours de planification de deplacement.",
    ],
    0x3EB2: [
        "Coeur du moteur d'errance. Prologue : $5F := $91 (curseur de tokens), ptr2 := $4927",
        "(enregistrements de commande), $65 := 0 et macc (accumulateur de poids) := 0, puis",
        "entre dans la boucle d'evaluation wander_eval ($3EC4). Le plan retenu est range dans",
        "les candidats $48D3 (entrees de 5 o [id, poids, etat, lo, hi]) et les commandes sont",
        "empilees dans $47E3. Passe ensuite la main a wander_step.",
    ],
    0x3EC4: [
        "Boucle d'evaluation : parse_cmd consomme la commande suivante de la file de tokens",
        "(curseur $5F) et la range dans l'enregistrement de commande courant ; $65 recoit son",
        "nombre de mots retenus (son poids). A=0 (commande construite) ou A=2 poursuivent en",
        "$3ED0 ; tout autre retour (A=1, 'WHAT ?') abandonne le plan ($3FCF).",
    ],
    0x3ED0: [
        "Cumul et fin de file : ajoute le poids de la commande a macc (macc += $65), remet $65",
        "a zero, puis regarde le prochain token de $4783 : tant qu'il n'est pas de type $C0",
        "(fin de commande) la boucle wander_eval continue ; sinon ce token est marque $90 et le",
        "budget mwt est arme a $0A avant la recherche de slot.",
    ],
    0x3EF1: [
        "Recherche de slot candidat : parcourt les 10 entrees de $48D3 (pas de 5 octets). Pour",
        "chaque candidat deja retenu, soustrait son poids (L48D4,x) du budget mwt afin de",
        "reserver la place ; le premier octet d'id nul marque le slot libre -> $3F0A. Sans slot",
        "libre au bout des 10, le plan est abandonne ($3FCF).",
    ],
    0x3F0A: [
        "Controle de budget : si mwt (budget restant apres reservation des autres candidats)",
        "est nul, il n'y a plus de place -> abandon ($3FCF) ; sinon, prepare le comptage.",
    ],
    0x3F11: [
        "Initialisation du comptage : vide l'etat du slot libre (L48D5,x := 0), remet mcnt et",
        "$65 a zero, memorise macc dans $6C (nombre total de commandes en file) et replace",
        "ptr2 sur la base des enregistrements de commande $4927.",
    ],
    0x3F26: [
        "Comptage des enregistrements : avance d'un enregistrement (rec_next ; saute les",
        "chaines marquees par le bit $40) en incrementant $65. S'arrete quand $65 atteint le",
        "budget mwt -> $3F3F, sinon memorise mcnt := $65 et continue tant qu'il reste des",
        "commandes ($6C). mcnt = plus grand nombre d'enregistrements < budget.",
    ],
    0x3F3F: [
        "Aucun enregistrement ne tient dans le budget (mcnt nul) -> le plan est abandonne",
        "($3FCF) ; sinon il y a de quoi retenir un candidat.",
    ],
    0x3F46: [
        "Retention du candidat : note son poids (L48D4,x := mcnt) et son id (L48D3,x := $90),",
        "puis efface $90. Calcule la destination ptr := $47E3 + 24*(10-mwt) : 10-mwt est le",
        "poids des candidats deja reserves, donc chaque candidat est empile a la suite des",
        "precedents.",
    ],
    0x3F6C: [
        "Empilement des commandes : recopie mcnt enregistrements de 24 octets depuis $4927 vers",
        "(ptr) (zone $47E3 indexee par le poids), un octet a la fois (wander_pack_byte), puis",
        "enchaine sur wander_step pour tenter le deplacement.",
    ],
    0x3F6E: [
        "Boucle interne d'empilement : recopie un octet de L4927,y vers (ptr),y et incremente Y",
        "sans le remettre a zero entre enregistrements (copie contigue de mcnt x 24 octets).",
    ],
    0x3F7F: [
        "Amorce un deplacement d'errance. A (mode, = 1 en pratique) est range dans le drapeau",
        "auto-modifie $3F7E, relu par wander_step : 0 = ne pas tenter le pas reel. Compare",
        "ensuite le personnage de la file ($90) a obj : identiques -> recalcul du plan",
        "(wander_core) ; sinon -> simple pas (wander_step). Appele par entity_tick (one-shot)",
        "et act_v14_11.",
    ],
    0x3F8E: [
        "Execute un pas d'errance : selectionne l'entree candidate (wander_select), puis, si le",
        "drapeau $3F7E est arme, rejoue sa commande sauvegardee (cmd_run puis cmd_probe). En cas",
        "d'echec, decremente le poids et reprend (wander_rewind) ; en cas de succes, memorise la",
        "position et valide.",
    ],
    0x3FE5: [
        "Rembobine la file des commandes ($4905) jusqu'a la position du candidat et",
        "consomme le poids du deplacement (dec L48D4[x]) ; libere le slot quand il est",
        "epuise (recopie de la suite).",
    ],
    0x4035: [
        "Selectionne le candidat courant : cherche le personnage dans $48D3 (cand_check),",
        "memorise son index (cand $CF), pointe sa suite de commandes (ptr2 = $47E3) et sa",
        "position dans la file.",
    ],
    0x4051: [
        "Retire un personnage de la liste des candidats $48D3 (retrouve son slot d'apres",
        "l'id et le vide). Appelee par code_4D47 quand un personnage change d'etat.",
    ],
    0x3E5B: [
        "Retire la prochaine action de la file $4905 (curseurs qrd/qwr $D1/$D2) : place son",
        "indice-token en $91, avance qrd et, selon arg1, marque la fin de la commande dans",
        "la file de tokens $4783. Appelee en fin d'action (L5FA0).",
    ],
    0x68D0: [
        "PNJ (Gandalf ?) : s'il est au meme endroit que le joueur, dit 'HELLO' ($143F).",
    ],
    0x68E0: [
        "PNJ oisif : tirage 0-2. 0 -> 'YOU ARE DO A GREAT JOB' ($1432) ; 1 -> 'HURRY UP'",
        "($143B) ; 2 -> 'HELLO' ($143F).",
    ],
    0x690C: [
        "PNJ : dit 'THIS WAS THRAINS KEY' (message $1441).",
    ],
    0x692D: [
        "PNJ : dit 'WHAT'S THIS ?' (message $1427).",
    ],
    0x6936: [
        "PNJ : tirage 0-7. >= 5 : rien ; 3-4 : ajuste un compteur en silence ; 0-2 : dit",
        "'HURRY UP' ($143B), en decrementant aussi un compteur quand le tirage vaut 0.",
    ],
    0x6962: [
        "PNJ : s'il est au meme endroit que le joueur et que le drapeau $1B21 bit7 est",
        "clair, dit 'WHERE'S THE THIEF ?' ($14AB).",
    ],
    0x697A: [
        "PNJ : si le joueur se trouve dans le lieu $1DE0, ajuste un compteur (L4D9E).",
    ],
    0x6C09: [
        "Gollum : si le joueur est dans le lieu $1E4B et le drapeau $1B21 bit7 pose,",
        "affiche un message prealablement construit (pointeur en ($BF)) et arme le",
        "drapeau said.",
    ],
    0x6C33: [
        "Action a jouer une seule fois : si once=1 et que la sonde passe, memorise les",
        "parametres recus dans le script $2A7A (id, wid, arg1, arg2) et rearme le verrou.",
    ],
    0x6C8D: [
        "PNJ : dans l'un des lieux $27/$2C/$29 et si le joueur vient d'y entrer (different",
        "de $1B40), annonce son arrivee : '<message>ENTER.' ($13F6).",
    ],
    0x6CBE: [
        "Dragon : au meme endroit que le joueur. Selon le drapeau $1B21 bit7, dit soit",
        "'PREPARE TO DIE' ($153F), soit l'aveuglement ($155D).",
    ],
    0x6CFA: [
        "PNJ : au meme endroit, joue une action sur l'objet $26 (wid $1D, arg1 $26) s'il",
        "ne l'a pas deja fait ($1FC1/$1FB2), et memorise le lieu courant.",
    ],
    0x6D78: [
        "Gollum et l'Anneau : au lieu $1E4B. Tirage 0-7 ; >= 4 -> 'WHAT HAS IT GOT IN ITS",
        "POCKET ?' ($16B9) ; sinon, si l'Anneau ($44) n'est pas la, 'MY PRECIOUS' ($16C8).",
    ],
    0x6DF9: [
        "PNJ : remet said=0 puis, si $90==$44, parcourt les tokens et peut renoncer ;",
        "sinon affiche 'SOMEONE STRANGLE YOU FROM BEHIND' ($15B6) et tue le joueur.",
    ],
    0x6E59: [
        "Dragon : selon le lieu ($1F47 == $29 : parti). Sinon, si le dragon est actif",
        "(bit7), tirage 0-99 : < $50 -> vol ('...SHAPE OF A MONSTROUS DRAGON...' $1582),",
        "sinon souffle de flammes ($1596) qui tue le joueur.",
    ],
    0x6E8B: [
        "Trolls : au lieu $05. Si obj==$47 (un troll deja cuit) -> 'BLIMEY, LOOK AT THIS",
        "!! CAN YER COOK 'EM?' ($1615), sinon 'YER CAN TRY, BUT...' ($162B).",
    ],
    0x6CDB: [
        "PNJ : au meme endroit que le joueur, simule un combat : wid=$1B, arg1=0, arg2=$FF",
        "via L5A62, puis act_p14_00 (combat) et L5FAE (mort).",
    ],
    0x6EA7: [
        "PNJ : efface des drapeaux ($1F94/$1FA6 bit7, $214C bit6), recolle les objets",
        "$47/$48, met a jour la description $2154 et affiche 'DAY DAWN.' ($16EB).",
    ],
    0x5F81: [
        "Corps d'action orphelin (cible de la table de verbes $6FAC, entree $6FFD :",
        "wid=$35). Cherche l'entite arg1 (entity_find) ; si absente, ou si elle a deja",
        "parle (said != 0), ou si son champ 'reply' est nul -> actq_pull. Sinon tire",
        "rand_range(reply) : resultat nul -> la creature dit '<ARG1>SAY 'NO '' ($15BE,",
        "replique d'enigme type Gollum), puis pull. Seul site du bloc 4 qui lit 'reply'",
        "((ptr2)+6) des entrees $2B45.",
    ],
    0x2C35: [
        "Point de depart du jeu, juste apres le chargement de la cassette.",
        "boot_copy copie l'etat initial (cassette) vers la memoire de travail, la",
        "pile est initialisee, puis la grande boucle prend la main :",
        "  afficher la situation -> lire une commande -> tokenize -> parse_cmd",
        "  -> cmd_run (execution) -> world_tick (le monde avance), et on recommence.",
        "Les commandes speciales (SAVE/LOAD/QUIT/HELP...) sont aiguillees par $57",
        "vers special_cmd, sinon l'action ordinaire passe par perform_action.",
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
        "Parcourt les evenements differes ($2B12, entrees [id,cpt,actA,cond,actB], fin $FF).",
        "Chaque evenement a un compte a rebours cpt ; id = minuterie nominale (l'armement fait",
        "souvent cpt := id). cpt==0 = desarme (on saute). Sinon cpt-- :",
        "  - tant que cpt reste > 0 et que cond!=0 et cond>=cpt, l'action actB se declenche",
        "    (repete a chaque tour) ;",
        "  - quand cpt atteint 0, l'action actA se declenche, une seule fois, puis cpt := L4E58",
        "    (0 = desarme).",
        "Technique : actA passe par evt_fire (index dans la table de sauts $7169). La garde",
        "L4E58, RAZ a chaque world_tick, limite a un seul actA par tour ; un handler d'actA peut",
        "la reposer ($688D) pour en autoriser d'autres.",
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
        "Technique : boucle sur get_key jusqu'a bit7 pose, retour & $7F.",
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
        "Technique : 10 essais get_key avec delai, compteur crcnt mod 16, scroll L7694.",
    ],
    0x4C82: [
        "Determine si la scene est sombre pour le joueur. La fiche du joueur (crec)",
        "et les objets presents sont examines : s'il n'y a aucune source de lumiere",
        "visible aupres de lui, rend C=1 (sombre) ; C=0 sinon. Les appelants en",
        "deduisent 'IT IS DARK.' ou 'I SEE NOTHING HERE.'.",
        "Technique : ne retient que les fiches d'etat a un seul lieu (+0 = $01),",
        "puis teste +$07 (masque $5C) et +$04 bit7 ; la seule source possible est l'epee $0E.",
    ],
    0x57BB: [
        "Resout le lieu d'un personnage/objet a partir de son id : cherche sa fiche (locate_object)",
        "puis lit son champ +0 (N = nombre de lieux). Seul +0 = $01 (objet a un seul lieu) est",
        "resolu : la fiche porte alors son lieu en +$10 ; sinon rend $FF = 'nulle part' (les objets",
        "multi-lieux +0 >= 2, ex. porte/eau/toile, ont leur liste en +$10.. geree par L5FFA).",
        "Meme regle que is_dark, holder_scan et la verification d'arme (act_p14_00).",
    ],
    0x7779: [
        "Initialise l'ecran hires : efface l'affichage, trace les bordures a partir",
        "des motifs $77CA/$77CF, cale les pointeurs d'affichage ($08/$09 = $B680) et",
        "les parametres texte, puis rend la main a start. Malgre son nom, ce n'est",
        "pas la boucle du jeu : c'est l'installation de l'ecran.",
    ],
    0x56D7: [
        "Fabrique un nombre aleatoire borne, utilise pour les comportements imprevisibles",
        "(errance des personnages, combats...).",
        "Technique : melange des octets de la source de bruit $93/$94 puis ramene le resultat dans [0, A).",
    ],
    # --- Boucle du jeu : execution d'une commande joueur ---
    0x357C: [
        "Enchainement d'execution d'une commande joueur (appele par start).",
        "Tente d'abord de la traiter comme un deplacement (move_begin $359B) : si le",
        "mouvement se termine par A<>0, cmd_run le rend tel quel a start. Sinon",
        "cmd_probe ($36D5) evalue l'action en sonde : passok<>0 -> A=0 (start",
        "execute l'action en reel : phase=1, describe_room, perform_action) ;",
        "passok=0 -> $57=3 et A=3 (start declenche rev_real $3A2D).",
        "start interprete $57 : 1 (pas une sortie) -> WAIT ou special_cmd ;",
        "2 (deplacement partiel) -> rev_dispatch2 $3A0B ; 3 (action) -> rev_real.",
    ],
    0x36D5: [
        "Rejoue la commande courante via perform_action ($4B37) en mode sonde",
        "(phase=0). Renvoie passok dans A : <>0 = l'action passe et sera rejouee en",
        "reel ; 0 = elle n'a pas abouti (cmd_run pose alors $57=3).",
    ],
    0x359B: [
        "Chaine d'execution d'un deplacement joueur.",
        "1. Force arg1/arg2=$FF puis remet a zero l'espace de resolution ($D7-$E7).",
        "2. exit_resolve ($3790) : construit les arguments VM ($F2-$F7) depuis le",
        "   record de commande et cherche, dans les sorties du lieu (table $26E2,",
        "   pas de 8), celle dont la signature correspond au mot courant. Rend 1 si",
        "   trouvee ; sinon 0 et $57=1 (cmd_run bascule alors sur l'action).",
        "3. Si trouvee (move_go $35AE) : wid := index de sortie ($6C), derive les",
        "   options (move_flags) puis tente le deplacement en deux temps : une",
        "   sonde (phase=0) et, si elle passe, l'execution reelle.",
        "Espace de travail : $D7/$D8 = etats des operateurs resolus (bits 0/1),",
        "$D9-$DB = compteurs de la boucle, $DC/$E2 = conditions memorisees.",
    ],
    0x3790: [
        "Prepare le bloc d'arguments de la commande puis localise la sortie du lieu.",
        "Arguments : lit le record de commande (ptr2, 24 o) - octet 0 -> $F2, octet",
        "1 (& $80) -> $EC et (& $7F) -> $F3 - puis copie les paires d'operandes",
        "(y=4/$0E puis 6/$10 via op_copy_pair) ; $F4-$F7 = les 2 operandes.",
        "Puis balaye les sorties a partir de $26E2 (pas de 8) : code_433A teste la",
        "signature ; la premiere qui correspond arrete la boucle ($6C = index de",
        "sortie). Rend 1 si une sortie correspond, 0 sinon (fin de table).",
    ],
    0x38E5: [
        "Boucle de resolution du 1er operande d'une commande a objets. Le stub",
        "auto-modifie op_stub ($38E2) pointe le matcher adequat ($53C3 direct ou",
        "$54F8 variante), puis pour chaque candidat de la table de travail $00DC :",
        "pose l'id dans arg1 et rejoue l'action via cmd_probe jusqu'a ce qu'elle",
        "passe (passok). op_resolve2 ($3948) fait de meme pour le 2e operande",
        "(table $00E2).",
    ],
    0x3A0B: [
        "Aiguillage de revision d'une commande classee 'partielle' (start y arrive",
        "via $57=2). Selon les etats $D7/$D8 et les compteurs $D9/$DA/$DB : tente",
        "une nouvelle resolution d'objet (rev_obj1 $3A6B / rev_obj2 $3A36),",
        "reaiguille vers rev_dispatch ($39EE), ou execute pour de bon",
        "(rev_real $3A2D).",
    ],
    0x5A62: [
        "Epilogue d'action partage : en mode reel (phase=1) decrit le lieu courant",
        "(describe_room) ; en mode sonde (phase=0) il se contente de rendre",
        "passok=0, ce qui amene cmd_run a classer la commande en revision ($57=3).",
        "Sert de queue a de nombreux corps d'action ($5BE4, $5C74, $5CC5, $5D8F,",
        "$6054, $60FD, $61F1, $6601, $6A8F, $6B0D, $6B34) et est appele en $6CF1.",
    ],
    0x4B37: [
        "Execution de la commande du joueur (le coeur d'AnimTalk cote action) :",
        "  1. sauve le contexte (L46E9) et resout les objets de la commande.",
        "  2. dans un lieu sombre sans lumiere portee (is_dark) : I SEE NOTHING HERE.",
        "  3. range arg1 (puis arg2) dans orec/orec2 via locate_object ; un objet",
        "     inconnu ou inaccessible est intercepte par obj_check.",
        "  4. verifie la compatibilite verbe/objet (verb_obj_ok) puis appelle",
        "     l'action : table $7014 pour un objet ordinaire, table etendue $7114",
        "     (indexee par le bit7 de (orec)+1) sinon ; appel via indirect_call.",
        "  5. en action reelle (phase=1) : gere l'obscurite puis annonce les objets",
        "     transportes qui reagissent.",
        "Le meme corps sert de sonde a cmd_probe ($36D5).",
    ],
    0x417C: [
        "Decrit le lieu courant : utilise notamment apres un deplacement reussi.",
        "S'appuie sur le pointeur de sortie exitp (rempli par exit_ptr ; L4232 rend",
        "les mots du record) : affiche le nom du lieu puis les sorties autorisees,",
        "en raccourcissant le rendu en mode sonde (passok) et en tenant compte de",
        "l'obscurite (is_dark) et des variantes de sortie (xmode/xaux).",
    ],
    0x4D84: [
        "Au lancement de la partie : cale crec sur la fiche du joueur ($1B1A), remet",
        "obj et said a zero, puis enchaine sur L6487 qui affiche le lieu de depart",
        "(premier LOOK).",
    ],
    0x4D47: [
        "Retire un personnage du jeu (mort ou disparu) : marque son record",
        "((record)+7 bit3), remet son compteur (code_5AF0), le sort de la table des",
        "entites (entity_find) et de la liste d'errance (wander_remove). Appele",
        "quand un personnage change d'etat.",
    ],
    0x3B75: [
        "Mot-cle special du parser (classe $90). Compare l'adresse du mot (adr) a la",
        "table $3BC6 (13 cles de 2 octets) et saute via la table $3BE0 vers le",
        "handler correspondant : ALL, EXCEPT, IT, ONE, PRINT, NOPRINT, LOAD, SAVE,",
        "QUIT, HELP, SCORE, PAUSE. Ces commandes court-circuitent les actions $7014.",
    ],
    # --- Objets, records et tables ---
    0x530B: [
        "Fiche d'un lieu : id < $50, entree de pointeur dans la table $2070. Au-dela",
        "de $4F, aucune fiche (A=0). Le record obtenu porte description et",
        "conditions.",
    ],
    0x5331: [
        "Fiche d'un objet/personnage : cherche l'id dans la table a cles $1A62",
        "(entrees [cle,lo,hi], fin $FF) et pose ptr sur le record pointe.",
    ],
    0x5399: [
        "Recherche lineaire dans une table (X/Y = adresse) d'entrees de 3 octets",
        "[cle,lo,hi] : compare la cle A, avance de 3 tant que non trouve et s'arrete",
        "sur $FF. Rend Z=1 (A=$FF) si absente, Z=0 sinon ; ptr pointe l'entree.",
    ],
    0x5394: [
        "Memes conventions que index_id_table, mais entrees de 2 octets.",
    ],
    0x52EA: [
        "Teste la compatibilite verbe/objet : la liste des verbes autorises est",
        "accolee au record (adresse = ptr + (ptr)+0 + $10, entrees de 2 octets).",
        "Rend C=1 si le verbe A y figure, C=0 sinon.",
    ],
    0x4CDF: [
        "Controle un objet avant que perform_action ne l'utilise : dans le contexte",
        "du joueur (obj=0) il resout la fiche (locate_object) et, selon l'etat et le",
        "drapeau $1B21, annonce que quelqu'un le porte ('... IS CARRYING ...').",
        "Sortie : A=0 si l'objet est utilisable, A<>0 si un cas particulier a ete",
        "traite (l'action est alors sautee).",
    ],
    # --- Pile interne des pointeurs de travail ---
    0x46E6: [
        "Pile interne $0200, indexee par rstk ($AF) : L46E6 empile ptr ($8A) puis",
        "ptr2 ($88) ; L4702 empile ptr2 seul. En depilement, fetch_retaddr ($4737)",
        "restaure ptr et pop_ptr2 ($471B) restaure ptr2 puis rend la main.",
        "Utilisees partout ou une sous-routine doit preserver les pointeurs de",
        "travail (actions, rendu de messages, VM des PNJ).",
    ],
    # --- Parser AnimTalk : sens (jeu) de chaque handler de classe ---
    0x32F3: [
        "Verbe (classe 3) : traite le mot comme predicat de la commande. Selon",
        "l'etat d'attente ($6D bit3), restaure l'enregistrement du groupe nominal",
        "precedent puis cloture (cmd_end), ou installe le verbe et attend ses objets.",
    ],
    0x33C8: [
        "Nom (classe 5) : memorise le nom courant (objet, creature ou lieu) dans le",
        "groupe nominal et l'enregistrement de commande, en tenant compte de la",
        "portee EXCEPT.",
    ],
    0x3299: [
        "Adverbe (classe 0) : impose un mode d'execution a l'action suivante",
        "(doucement, vite...).",
    ],
    0x3374: [
        "Article/determinant (classe 8 : THE, A...) : simple annonce d'un nom ;",
        "passe aussitot au mot suivant.",
    ],
    0x337D: [
        "IN/INTO (classe 1) : preposition de lieu ; peut basculer en verbe de",
        "deplacement (GO) selon le mot precedent.",
    ],
    0x3390: [
        "Preposition (classe 7 : ON, WITH, THROUGH...) : separe le sujet de son",
        "complement dans le groupe nominal.",
    ],
    0x33BF: [
        "Adjectif (classe 6) : ajoute un qualificatif au groupe nominal courant",
        "(sert a lever l'ambiguite entre plusieurs objets).",
    ],
    0x32B9: [
        "AND / virgule (classe 10) : enchaine plusieurs objets dans une meme",
        "commande en sauvegardant l'etat du groupe nominal.",
    ],
    0x32E9: [
        "GO / RUN (classe 4) : verbe de deplacement ; reclasse en verbe ($30) et",
        "traite comme tel.",
    ],
    0x328F: [
        "Direction (classe 2) : enregistre la direction demandee (N/S/E/W...), qui",
        "devient le wid du deplacement.",
    ],
    # --- Notes de la deuxieme passe (routines restees anonymes) ---
    0x30DF: [
        "Avance d'un octet les deux pointeurs de copie : ptr ($8A, report en $8B) et",
        "$8C (report en $8D) ; decremente le compteur de segment ptr2 ($88/$89). Rend Z",
        "(A=0) quand ptr2 atteint zero, ce qui termine le segment courant de boot_copy /",
        "boot_copyback.",
    ],
    0x433A: [
        "Teste l'appartenance d'un objet a une sortie : lit les 3 paires (mot, masque)",
        "(record de sortie +2..+7) et les compare, via sig_match_a/b/c, a l'operande",
        "courant pointe par ($7C) ; une paire (0,0) est absente (ignoree). Rend Z (A=0)",
        "si la signature correspond, Z clair sinon. Pose $79=1 pour activer le repli",
        "croise des paires.",
    ],
    0x53C3: [
        "Matcher de deplacement direct : maintient ptr2 sur la table de conditions",
        "$1A5F et parcourt les records, comparant (record)+7 (masque $48) a $81 et la",
        "condition (record)+8 a celle de l'operande. Rend l'id du record compatible.",
    ],
    0x54F8: [
        "Matcher de variante : parcourt les records et compare cette fois la condition",
        "(record)+2, en s'appuyant sur exit_sig_match (code_433A) pour filtrer selon la",
        "signature de sortie. Utilise par la resolution d'operande en mode variante.",
    ],
    0x5454: [
        "Coeur de la resolution d'action : parcourt les enregistrements de la table de",
        "conditions, demande a act_try_obj/cond_match_alt de selectionner un candidat",
        "compatible, ecrit son id dans l'operande puis rejoue l'action (cmd_probe)",
        "jusqu'a ce qu'elle passe.",
    ],
    0x5576: [
        "Compte combien de slots de la table $1A5F portent l'objet A avec le flag bit7",
        "pose ; rend le total dans A. Distingue un objet unique d'un objet en plusieurs",
        "exemplaires.",
    ],
    0x55AE: [
        "Cherche un emplacement libre dans la table $1A62 (enregistrements de 3 octets)",
        "pour l'objet courant, ecrit l'objet + la cle (X) et rend l'index de slot dans X.",
        "slot_alloc2 ($55B3) fait de meme pour des enregistrements de 2 octets ; les deux",
        "partagent la boucle de recherche de slot_find_free ($55C9).",
    ],
    0x5612: [
        "Arme un evenement indexe par la cle X pour l'objet courant : parcourt $1A5F et",
        "pose la cle dans le slot correspondant. Utilise par les actions de PNJ qui",
        "declenchent un evenement differe ($2B12).",
    ],
    0x568D: [
        "Met a jour le porteur d'un objet dans la table $1A5F : pour chaque",
        "enregistrement correspondant a l'objet, rapporte le compteur de porteur",
        "(L56D6) en soustrayant la quantite du slot.",
    ],
    0x56D9: [
        "Ramene un compteur a une echelle (0-10) : double la valeur, sature a $FF, puis",
        "compare L570F/L5710 (ratio de probabilite). Sert aux tirages ponderes des",
        "actions.",
    ],
    0x580F: [
        "Affiche la liste des objets visibles d'un lieu : fixe le filtre (L5835) puis",
        "appelle list_visible_scan ; si rien n'a ete rendu, affiche 'NOTHING' ($171B).",
    ],
    0x5836: [
        "Balaye les enregistrements d'un lieu (via record_scan) et, pour chaque objet",
        "dont le type correspond au filtre L5835, affiche son nom (name_from_record).",
        "L5834 compte le nombre d'objets rendus.",
    ],
    0x58E7: [
        "Teste si l'objet A est visible dans le lieu courant : lit son record et ses",
        "drapeaux (record+7 masque $28), verifie la quantite (slot_count) puis la",
        "visibilite (bit $40). Rend C=1 si visible.",
    ],
    0x5959: [
        "Affiche les objets presents dans un lieu : pointe (record)+$0A (liste",
        "d'objets) et, pour chacun dont le flag bit7 est pose, rend son nom via",
        "word_render et le message 'THERE IS<MSG>' ($13F1).",
    ],
    0x5D53: [
        "Un tour de combat : resout l'objet/adversaire courant (record, flag bit6) et",
        "enchaine l'action correspondante ; met a jour le compteur de coups et, si",
        "l'adversaire tombe, laisse act_try_core gerer la suite.",
    ],
    0x6341: [
        "Ajoute un ratio (0-10 obtenu via ratio_scale) a une valeur : borne le resultat",
        "entre $00 et $FF (saturation) et rend la somme. Utilise pour les compteurs de",
        "degats ou de competences.",
    ],
    0x6EF7: [
        "Illustration associee a un lieu : si le bloc 3 est present, lit la fiche du",
        "lieu et modifie 2 octets a (ptr)+1 (couleurs/etat) avant d'appeler le moteur",
        "vec_*.",
    ],
    0x72FC: [
        "Relecture cassette : affiche un point, initialise le VIA, cherche le marqueur",
        "$24, lit l'en-tete 9 octets, puis les donnees en accumulant un checksum EOR",
        "qu'il compare. Rend C=0 si le bloc est valide, C=1 sinon.",
    ],
    0x7514: [
        "Prepare un defilement de l'ecran hires : cale les couples de pointeurs source/",
        "destination ($1E/$1F et $20/$21) sur le repertoire de lignes ($B940/$BA40) ;",
        "utilise par le scroll et l'effacement hires.",
    ],
    0x771A: [
        "Defile verticalement l'ecran hires de quelques lignes : copie chaque ligne de",
        "destination vers la precedente via les pointeurs de hires_scroll_setup, en",
        "inserant eventuellement un CR ($0D) en fin de zone.",
    ],
    0x76ED: [
        "Dessine le caractere A a la position texte courante : memorise la ligne (col)",
        "puis saute a print_char ($75B8) avec X/Y = position courante ($08/$09).",
    ],
    0x781D: [
        "Avance d'un octet le pointeur de flux d'illustration ($28/$29) et rend l'octet",
        "suivant ; brique de base de la boucle de trace vec_* a $77E3.",
    ],
    0x46E9: [
        "Entree de push_ptr : sauve A et X, puis empile ptr ($8A/$8B) sur la pile",
        "interne $0200 indexee par rstk ($AF). Appelee directement quand A/X doivent",
        "etre preserves sans empiler ptr2.",
    ],
    0x4B07: [
        "Variante sonde de perform_action : appelle arg1_check puis, si le 1er objet",
        "est utilisable et le verbe autorise pour lui (verb_obj_ok), pose passok=1.",
        "N'execute pas l'action ; sert a savoir si la commande passe avant de la",
        "rejouer en reel.",
    ],
    # --- Actions joueur (table L7014, index 0-14) : corps detailles ---
    0x60BF: [
        "Index 0. Ajoute $0A au compteur (crec)+5 de l'objet ; en cas de debordement",
        "(resultat negatif) la creature meurt de gloutonnerie ('... FOUL GLUTTONY HAS",
        "KILLED <OBJ>.' $1525) et est retiree du jeu (unit_remove) ; sinon la cible",
        "(orec)+1 recoit $FF et ses 16 octets de queue (orec)+$10.. sont effaces.",
    ],
    0x60ED: [
        "Index 1. Attaque avec l'objet courant : verifie les drapeaux (orec)+7 (bit1",
        "arme, bit3 deja touche) et, si une cible arg2 est fournie, son autorisation",
        "(verb_obj_ok $0C) et (orec2)+5>0. Calcule les degats (ratio $15 sur (crec)+5)",
        "et les retranche au compteur (orec)+6 de la cible ; si la cible tombe, pose",
        "son bit3, reduit ses compteurs et annonce le resultat via name_from_record.",
    ],
    0x61C9: [
        "Index 2. Selon le flag bit5 de (orec)+7 : s'il est clair, affiche le nom de",
        "l'objet ; s'il est pose, (act_probe) l'efface et rend la main.",
    ],
    0x6222: [
        "Index 3. Si le flag bit0 de (orec)+7 est deja pose, affiche le nom ; sinon",
        "(act_probe) pose le bit5 de (ptr)+7 et, pour l'objet d'id $01 dont arg1 n'est",
        "pas visible, declenche l'annonce des objets visibles (list_visible_init).",
    ],
    0x5CA9: [
        "Index 4. Resout arg1 (locate_object) ; si son flag bit5 est pose, bascule vers",
        "act_p14_14 (bascule), sinon affiche son nom.",
    ],
    0x5D06: [
        "Index 5. Lance l'objet comme une arme : verifie weapon_test_a, (ptr)+2 puis",
        "obj_enter_check ; si l'entree est possible, cale wid := (ptr)+0, arg1 := $FF",
        "et enchaine sur combat_round ; sinon decrit le lieu (act_look).",
    ],
    0x65DD: [
        "Index 6. Affiche '<ARG2>DO NOT FIT THIS LOCK' ($140C) : l'objet ne va pas",
        "sur cette serrure, ou l'action est impossible.",
    ],
    0x61E5: [
        "Index 7. Allume/eteint un objet a lumiere : item_flag_test sur arg2 ; si",
        "l'objet est absent, decrit le lieu (act_look) ; sinon, selon le bit5 de",
        "(ptr2)+7, retire le flag et arme l'evenement lie a arg1.",
    ],
    0x65BA: [
        "Index 8 (type $04). Aiguille selon le type reel de arg2 : si arg2=$04, vers",
        "L641D ($wid=$25) ou L6448 ; sinon act_p14_06 ($02/$04/$0F) ou cannot_do.",
    ],
    0x6B72: [
        "Index 9. Pour l'objet $41, assemble le message 'GO <W> FROM <MSG> TO GET TO",
        "<MSG>' ($15AB) a partir de la table des lieux (room_cond_ptr / word_ptr_table)",
        "et des arguments VM $466F-$4674 ; sinon renvoie vers code_63A4.",
    ],
    0x65F1: [
        "Index 10. Lit le champ (crec)+$10 : s'il vaut $0F, poursuit en act_p14_03 ;",
        "sinon decrit le lieu (act_look).",
    ],
    0x66D6: [
        "Index 11 (araignees). Si le bit3 de (orec)+7 est pose : pose le bit5, arme",
        "l'evenement e1 ($2B17 -> $2B18) et annonce 'SOME SPIDERS START MEND THE",
        "BROKEN WEB' ($1478) ; sinon ne fait rien.",
    ],
    0x65B6: [
        "Index 12 (type $0F). Meme aiguillage que l'index 8, avec le type $0F : si",
        "arg2=$0F, vers L641D ($wid=$25) ou L6448 ; sinon act_p14_06 / cannot_do.",
    ],
    0x6041: [
        "Index 13. Transfert d'objet d'un contenant a l'autre : selon (orec2)+4 & $07,",
        "verifie la capacite via slot_alloc3 ; si le contenant est trop plein, affiche",
        "'<ARG2>IS TOO FULL' ($11F1) ; sinon deplace le contenu (champ +$10 et porteur).",
    ],
    0x5CB6: [
        "Index 14 (bascule). Resout et affiche l'objet courant (obj_render_resolve) ;",
        "selon l'arme (weapon_test_a) et le contexte de lieu, deplace l'objet ou",
        "decrit le lieu (act_look).",
    ],
    # --- Moteur d'illustrations vectorielles (bloc 3) : decodeur de flux ---
    0x77D4: [
        "Decodeur d'un flux d'illustration (bloc 3 ; cible de la table a cles $7AC0).",
        "Entree : X/Y = adresse du flux. Le 1er octet du flux (lu dans A) est passe a",
        "vec_setup, qui prepare l'ecran hires (fond + bordures). Puis chaque octet",
        "suivant est une commande, repetee jusqu'a $00 :",
        "  $00  fin de flux (retour) ;",
        "  $08  position du curseur (vec_pos) ;",
        "  bit7 ligne (vec_line) ; bit6 remplissage (vec_fill) ;",
        "  bit5 saut jusqu'a un marqueur $FF (vec_skip).",
        "Le test est prioritaire dans cet ordre (bit7 avant bit6 avant bit5).",
        "Le pointeur de flux ($28/$29) avance d'un octet par vec_next_byte.",
    ],
    0x7824: [
        "Remplissage (seed fill) : part du pixel courant ($30/$31) et s'etend",
        "horizontalement, puis empile les positions de reprise sur la pile 6502",
        "(repere de profondeur en $32 ; bornes $30/$31 sauvees en $33/$34) pour",
        "couvrir la zone en tache d'huile. Les drapeaux $35/$36 evitent de repasser",
        "sur une ligne deja remplie. S'arrete sur les pixels occupes ou hors zone",
        "($30 < $0E ou >= $F2, testes par vec_testpx). Utilise par les commandes a",
        "bit6 du flux d'illustration.",
    ],
    0x78E4: [
        "Trace un segment de droite a partir de l'octet de commande ($28),y.",
        "Directions : bit0 = axe majeur vertical ; bit1 = sens vertical ; bit2 = sens",
        "horizontal. La longueur du petit axe est en $2D (bits 3-6 de l'octet + bits",
        "7-6 de l'octet suivant, +1) et le nombre de pas en $2E (bits 5-0 de l'octet",
        "suivant). Deux boucles symetriques (L791C si axe majeur horizontal, L7954",
        "sinon) tracent pas a pas via vec_plot, en rebondissant sur les bornes",
        "($30 dans [$0E,$F2), $31 dans [0,$7F]) ; utilise par les commandes a bit7.",
    ],
    0x7990: [
        "Prepare l'ecran pour une illustration : efface le bitmap hires $A000-$B3FF",
        "(chaque octet recoit $40 = fond), puis trace les bordures gauche ($A000) et",
        "droite ($A001) tous les $28 octets, avec l'encre donnee par A : nibble bas =",
        "bordure gauche, nibble haut = bordure droite (chacun force en $10-$17).",
        "Appelee par drawing avec le 1er octet du flux comme parametre.",
    ],
    0x79FB: [
        "Teste le pixel ($30,$31) : rend A<>0 si un point est deja dessine ou si la",
        "position est hors zone ($30 < $0E ou >= $F2), A=0 si le pixel est libre.",
        "Sert de test de frontiere au remplissage vec_fill (et au trace vec_line).",
    ],
    0x7A0F: [
        "Allume le pixel ($30,$31) dans le bitmap hires (OR du masque L7A5F[X]) ;",
        "hors zone ($30 < $0E ou >= $F2) ne fait rien.",
    ],
    0x7A22: [
        "Calcule l'adresse du pixel ($30,$31) : octet de base $A002 + ($7F-$31)*$28",
        "+ ($30-$0E). Pose l'adresse en $38/$39 ; rend dans A l'octet courant du",
        "bitmap (lu via ($38),Y) et dans X le numero de bit (masque L7A5F[X] :",
        "$20,$10,$08,$04,$02,$01). Le decoupage $30-$0E est divise par 6 (6 pixels",
        "par octet) : le quotient donne l'offset d'octet, le reste le numero de bit.",
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

# Commentaires au niveau instruction (bloc 4) : adresse de debut -> texte,
# insere en fin de ligne par inject_inline_comments(). Sert a annoter le flot
# du parser (dispatch de classe, test de type, bornes) au plus pres du code.
INLINE_COMMENTS: dict[int, str] = {
    0x3118: "$5B = $C0 : on amorce avec un type precedent 'fin de commande'",
    0x3126: "$6E : portee de commande (0 normal, 1 ALL, 2 EXCEPT)",
    0x3144: "dispatch : lit le token suivant et saute vers sa classe",
    0x3147: "index de classe = type >> 3 (2 x le nibble de classe)",
    0x3157: "saut indirect via la table $315A (12 adresses de handlers, indexee par classe)",
    0x3172: "classe 11 ($B0) : point/THEN = fin de commande",
    0x328F: "classe 2 ($20) : direction",
    0x3299: "classe 0 ($00) : adverbe",
    0x32B9: "classe 10 ($A0) : AND / virgule (objets multiples)",
    0x32E9: "classe 4 ($40) : GO / RUN",
    0x32F3: "classe 3 ($30) : verbe",
    0x3374: "classe 8 ($80) : article/determinant (THE, A...)",
    0x337D: "classe 1 ($10) : IN / INTO",
    0x3390: "classe 7 ($70) : preposition (ON, THROUGH, WITH...)",
    0x33BF: "classe 6 ($60) : adjectif",
    0x33C8: "classe 5 ($50) : nom (objet, creature, lieu)",
    0x3B9B: "classe 9 ($90) : mot-cle special (SAVE/QUIT/HELP/ALL/EXCEPT...)",
    0x2E76: "CR : la commande est close (point final + guillemet)",
    0x2ED5: "entree du lexeur : un mot -> un token",
    0x2EE2: "CR en fin de ligne -> token de fin $C0",
    0x2EE6: "test ponctuation (point, virgule, guillemet)",
    0x2F78: "type = bits 6-5 des 2 premiers octets de l'entree de dictionnaire",
    0x2F9A: "type $D0 = entree ignoree par le parseur (mot de message)",
    0x34D0: "fusionne deux mots en un enregistrement de commande",
    # --- AnimAction : flot de la VM des PNJ (entity_tick $4ED5) ---
    0x4EE0: "bout de boucle : compteur d'opcodes remis a 0 pour l'entite",
    0x4EF0: "id $00 = emplacement dormant -> entite suivante",
    0x4EF7: "entite active : obj=id, resolve lieu et fiche (L57BB)",
    0x4F63: "garde-fou : au plus 6 opcodes par tick",
    0x4F6D: "octet d'opcode du script -> test du nibble bas",
    0x4F3F: "fin de l'annonce de bruit : coupe l'affichage (outen=0)",
    0x4F43: "reprend le contexte de l'entite (crec -> ptr)",
    0x4F56: "once := 0 si le PNJ est deja candidat a l'errance (sinon 1)",
    0x4F58: "PC du script := ((ptr2)+2/+3) -> $8C/$8D",
    0x4FA5: "nibble $04 : MOVE court (script_move_short)",
    0x4FB2: "nibble $00-$03 : MOVE long (script_move)",
    0x4FB7: "cas non prevu (nibble > $04 deja aiguille) : passe",
    0x4FBE: "$xE : GOTO absolu (PC := operande)",
    0x4FBA: "nibble >= 5 : GOTO / INDIR / RAND",
    0x4FCD: "$xC : GOTO par cle (entity_goto, table de base)",
    0x4FE0: "$xF : RAND (script_rand)",
    0x4FF4: "$x5-$xD : INDIR table[0] (script_indir)",
    0x5008: "fin de table : restaure le contexte du joueur",
    0x5048: "MOVE long (bit0=0) / ACT (bit0=1)",
    0x50A5: "bit $20 : efface l'opcode (auto-modification, entite dormante)",
    0x50AC: "MOVE court $x4",
    0x50E7: "echec du move : memorise pour le plan de secours",
    0x50FB: "bit $10 : saut de secours vers une autre instruction",
    0x51CA: "opcode RAND : tirage parmi les cibles de la table de base",
    0x5235: "init du tick : lieu joueur, noir, compteur de bruit",
    0x3F7F: "drapeau d'errance $3F7E := A (0 = ne pas tenter le pas reel)",
    0x3F91: "drapeau $3F7E : si arme, tenter le pas reel (sinon sauter)",
    # --- Execution d'une commande joueur ---
    0x357C: "tente d'abord de traiter la commande comme un deplacement (L359B)",
    0x3582: "sinon evalue l'action en sonde (cmd_probe)",
    0x358A: "$57=3 : rien a reviser pour la boucle de start",
    0x3B9F: "compare l'adresse du mot (adr) a la table $3BC6 (classe 9)",
    0x3BB4: "aucun mot-cle reconnu -> mot suivant",
    0x3BB7: "trouve -> cible lue dans $3BE0, saut indirect via $3BC4",
    0x4192: "fiche de sortie du mot courant (wid) -> exitp",
    0x41A2: "drapeaux de la sortie courante (code_4141)",
    0x41AC: "nom du lieu puis champs du record de sortie (L4232)",
    0x41C3: "lieu sombre ? (is_dark)",
    0x41CA: "dans le noir : decrit la sortie directionnelle (wid < $0A)",
    0x4221: "point final + CR",
    0x4B42: "obscurite du lieu (is_dark)",
    0x4B45: "clair -> continue ; sombre -> teste la lumiere portee",
    0x4B5F: "sortie directe (direct) -> verbe sans objet",
    0x4B65: "verbe sans objet -> dispatch de la table $6FAC (L4C20)",
    0x4B6E: "fiche du 1er objet -> orec",
    0x4B7B: "controle du 1er objet (obj_check)",
    0x4B91: "fiche du 2nd objet -> orec2",
    0x4B9E: "controle du 2nd objet",
    0x4BAD: "le verbe est-il autorise pour cet objet ?",
    0x4BB0: "non autorise -> I CANNOT DO THAT (L4C20)",
    0x4BB2: "boucle des actions associees a l'objet",
    0x4BB8: "bit7 de (orec)+1 -> table etendue $7114, sinon $7014",
    0x4BD5: "appel indirect de l'action (indirect_call)",
    0x4BE9: "action reelle ? sinon fin",
    0x4BF5: "noir et sans lumiere -> IT IS DARK",
    0x4C20: "dispatch verbe sans objet (table $6FAC)",
    # --- Deplacement : essais, resolution de sortie et d'operandes ---
    0x35C2: "xmode & $0C : sortie non directe a reviser ?",
    0x37A7: "raz des operandes $F4-$F7",
    0x37B4: "copie des paires d'operandes (y=4/$0E/6/$10)",
    0x37CA: "exitp = $26E2 : debut de la table des sorties du lieu",
    0x37D2: "$6C = 1 : index de sortie",
    0x37E6: "code_433A : la sortie correspond-elle au mot courant ?",
    0x37E9: "correspond -> exit_found ; sinon sortie suivante",
    0x37F8: "index de sortie +1",
    0x38F2: "direct ? choisit le matcher ($53C3 ou $54F8)",
    0x3938: "candidat retenu : arg1 := id, rejoue l'action",
    0x39A3: "candidat retenu : arg2 := id, rejoue l'action",
    0x3A11: "etat du 1er operateur ($D7 bit0)",
    0x3A1C: "etat du 2e operateur ($D7 bit1)",
    0x3A30: "rejoue l'action en mode reel",
    0x3B30: "octet +3 de la sortie (bit5) : ajoute 2 mots d'argument",
    # --- Moteur d'illustrations vectorielles (bloc 3) : boucle de flux ---
    0x77E3: "boucle du flux : octet de commande suivant",
    0x77E5: "octet de commande courant",
    0x77E9: "$08 : position du curseur (vec_pos)",
    0x77ED: "bit7 : trace de ligne (vec_line)",
    0x77F3: "bit6 : remplissage (vec_fill)",
    0x77F9: "bit5 : saut jusqu'a un marqueur (vec_skip)",
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

# Pointeurs de message `.word $0000` remplis a l'execution : adresse du slot ->
# explication (ajoutee au repere "TODO pointeur $0000" du listing). Ces slots
# sont ecrits par le code qui precede le print_msg inline (idiome courant) ; la
# valeur statique est donc nulle, d'ou le TODO conserve.
NULLPTR_NOTES: dict[int, str] = {
    0x3CB7: "slot rempli au runtime : entree lue dans la table $7185 (IT/ONE)",
    0x4DFC: "slot rempli au runtime : amorce de lieu (ex. $13DC) avant la description",
    0x4E30: "slot rempli au runtime : description lue dans l'enregistrement ((ptr)+0/+1)",
    0x52C6: "slot rempli au runtime : message de dialogue du PNJ (say_if_visible)",
    0x5BB8: "slot rempli au runtime : message $13A4/$13A8 selon le type d'objet",
    0x631D: "slot rempli au runtime : message de degats choisi dans $6359/$635A",
    0x63C1: "slot rempli au runtime : message d'objet lu dans la fiche ((ptr)+$0E)",
    0x6C2C: "slot rempli au runtime : message prepare par le jeu (pointeur $BF, Gollum)",
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
    # Commentaires au niveau instruction : adresse de debut d'instruction ->
    # texte, insere en fin de ligne (`; texte`). Permet de documenter
    # precisement un flot (dispatch, tests, branches) la ou les notes de
    # routine ne suffisent pas. Cf. inject_inline_comments().
    inline_comments: dict[int, str] = field(default_factory=dict)


B4_HEADER = (
    "; ============================================================\n"
    "; The Hobbit (Oric, 1982)\n"
    "; Original authors : Veronika Megler & Philip Mitchell (Beam Software)\n"
    "; 6502 port : Gregg Barnett (Beam Software)\n"
    "; Publisher : Melbourne House\n"
    "; - bloc 4 ($2C00-$7A80) : programme principal\n"
    "; Listing généré par scripts/disasm.py (descente récursive + da65)\n"
    "; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.\n"
    "; ============================================================\n"
    ";\n"
    "; COMMENT LIRE CE LISTING\n"
    "; -----------------------\n"
    "; Les autres blocs alimentent celui-ci : bloc 1 = chargeur cassette\n"
    "; (vecteurs ROM conserves en $0400+, reutilises par SAVE/LOAD) ; bloc 2 =\n"
    "; banque de donnees (dictionnaire, messages, records, scripts des PNJ) ;\n"
    "; bloc 3 = banque d'illustrations vectorielles.\n"
    ";\n"
    "; Cycle du jeu, une iteration par commande du joueur :\n"
    ";   start ($2C35)      boot (copie cassette -> memoire) puis boucle :\n"
    ";     read_line        saisit une ligne de commande dans le tampon $40BE\n"
    ";     tokenize         decoupe la ligne en mots (file de tokens $4783)\n"
    ";     parse_cmd        construit la commande (wid $13, arg1 $15, arg2 $16)\n"
    ";     cmd_run          execute la commande du joueur (verbe + objets)\n"
    ";     world_tick       fait vivre le monde (PNJ puis evenements differes)\n"
    ";\n"
    "; Deux moteurs d'animation distincts :\n"
    ";   AnimTalk   : le parser textuel (saisie -> lexeur 5-bit -> grammaire),\n"
    ";                qui transforme une phrase en commande interne.\n"
    ";   AnimAction : les PNJ autonomes ; $4ED5 fait jouer a chaque personnage\n"
    ";                un opcode de son 'cerveau' (script du bloc 2), meme quand\n"
    ";                le joueur est ailleurs.\n"
    ";\n"
    "; Mode sonde / action reelle : avant d'agir pour de vrai, le jeu rejoue la\n"
    "; meme sequence en simulation (phase $0C = 0) pour savoir si l'action passe\n"
    "; (passok $12) ; seule une action qui passe est rejouee en reel (phase = 1).\n"
    ";\n"
    "; Conventions de code :\n"
    ";   - Message inline : JSR $440D ($4444 render_text) ou JSR $5B24 (act_msg),\n"
    ";     suivi des 2 octets d'adresse du message ; reprise a JSR+5. Chaque site\n"
    ";     porte un label 'msg_XXXX' avec un apercu du texte en commentaire.\n"
    ";   - Appel indirect : l'adresse cible est posee dans $4C64/$4C65 puis\n"
    ";     appelee par indirect_call ($4C5D) ; c'est le mecanisme des tables\n"
    ";     d'actions $7014 (verbes joueur) / $7143 (PNJ) et de $7169 (evenements).\n"
    ";   - Pointeurs de travail : ptr/ptr2/ptr3 ($8A/$88/$7A) se sauvent et se\n"
    ";     restaurent via la pile interne $0200 (push_ptr/pop_ptr, fetch_retaddr).\n"
    ";   - Les labels 'Lxxxx' / 'code_xxxx' restants sont des adresses que le\n"
    ";     desassemblage n'a pas encore baptisees.\n"
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
    "; Original authors : Veronika Megler & Philip Mitchell (Beam Software)\n"
    "; 6502 port : Gregg Barnett (Beam Software)\n"
    "; Publisher : Melbourne House\n"
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
    0x0500: "dict_index",  # index 26 lettres -> 1er mot
    0x0540: "dict",  # dico packe 5-bit (~600 mots)
    0x1117: "common_words",  # 32 mots courants ($60-$7F)
    0x1157: "messages",  # catalogue de messages
    0x18AA: "loc_desc",  # 29 descriptions de lieux
    0x1A62: "state_keys",  # 61 triplets [cle,lo,hi] + $FF
    0x1B1A: "states",  # 61 blocs d'etat
    0x2070: "rec_table",  # 80 mots id -> record
    0x2110: "rec_templates",  # 5 gabarits (pointeurs bloc 3)
    0x211A: "records",  # records lieux/objets/creatures
    0x26E2: "dir_names",  # noms des directions (10 x 8 o)
    0x2732: "exits_ext",  # sorties etendues conditionnelles
    0x28CC: "indir0",  # table de sauts 3 o [cle,lo,hi]
    0x28D3: "indir1",
    0x28DA: "indir2",
    0x28E1: "script_goblins",  # VM : gobelins e11/e12
    0x2910: "script_goblin13",  # VM : gobelin e13
    0x2934: "script_goblins14",  # VM : gobelins e14-e16
    0x2943: "indir3",
    0x295C: "script_gandalf",  # VM : Gandalf e0 (errance)
    0x2984: "indir4",
    0x298E: "script_thorin",  # VM : Thorin e1
    0x29B2: "indir5",
    0x29BC: "script_elf",  # VM : elfe e2
    0x29C3: "indir6",
    0x29C7: "script_warg",  # VM : warg e3
    0x29E4: "indir7",
    0x29EE: "script_butler",  # VM : butler dormant e4
    0x2A2E: "indir8",
    0x2A38: "script_elrond",  # VM : Elrond e5
    0x2A4D: "indir9",
    0x2A54: "script_dragon",  # VM : dragon dormant e8
    0x2A70: "indir10",
    0x2A77: "script_bard",  # VM : Bard dormant e7
    0x2A88: "indir11",
    0x2A8F: "script_gollum",  # VM : Gollum e6
    0x2AC9: "indir12",
    0x2AD0: "script_trolls",  # VM : trolls e9/e10 (lieu 5)
    0x2B12: "events",  # 10 x 5 o [id,cpt,actA,cond,actB]
    0x2B45: "entities",  # 17 x 7 o [id,nmax,PC,base,reply]
}

B2_RANGES: dict[int, str] = {
    0x0500: "WORDTABLE",  # index 26 lettres
    0x0540: "BYTETABLE",  # dictionnaire packe
    0x1117: "WORDTABLE",  # 32 mots courants
    0x1157: "BYTETABLE",  # catalogue de messages
    0x1A62: "BYTETABLE",  # cles d'etat
    0x1B1A: "BYTETABLE",  # blocs d'etat
    0x2070: "WORDTABLE",  # table des records
    0x2110: "WORDTABLE",  # gabarits de description
    0x211A: "BYTETABLE",  # records
    0x26E2: "BYTETABLE",  # noms des directions
    0x2732: "BYTETABLE",  # sorties etendues
    0x28CC: "BYTETABLE",  # INDIR + scripts VM + events + entites
}

B2_HEADER = (
    "; ============================================================\n"
    "; The Hobbit (Oric, 1982)\n"
    "; Original authors : Veronika Megler & Philip Mitchell (Beam Software)\n"
    "; 6502 port : Gregg Barnett (Beam Software)\n"
    "; Publisher : Melbourne House\n"
    "; - bloc 2 ($0500-$2BBD) : donnees du jeu (aucun code 6502)\n"
    "; Listing généré par scripts/disasm.py (partitionnement type + labels).\n"
    "; Dictionnaire packe 5-bit, catalogue de messages, etats, records,\n"
    "; tables INDIR, scripts VM AnimAction, events, entites.\n"
    "; Formats : docs/block4-analysis.md, docs/memory-map.md.\n"
    "; ============================================================\n\n"
)


# --- Bloc 3 ($7AC0-$91B1) : banque d'illustrations vectorielles -----------
# Aucun code 6502 : table a cles $7AC0 (13 entrees [cle,lo,hi], $FF en $7AE7)
# + 13 flux d'octets $00-terminés, tuiles sans trou ($7AE8->$91B1). Chaque
# image = [mode,$08,x,y] + commandes ($08 curseur, $20 skip, bit6 fill,
# bit7 ligne). Moteur vec_* en bloc 4 ; decodeur : scripts/vec_decode.py.
B3_LABELS: dict[int, str] = {
    0x7AC0: "img_table",  # 13 entrees [cle, lo, hi] + $FF
    0x7AE8: "img_01",  # mode $05
    0x7D09: "img_06",  # mode $02
    0x7FA4: "img_0b",  # mode $01
    0x809F: "img_25",  # mode $13
    0x82EC: "img_26",  # mode $04
    0x8569: "img_07",  # mode $14
    0x8766: "img_0d",  # mode $03 (contient l'image $15 + 29 o)
    0x8783: "img_15",  # mode $01
    0x887B: "img_20",  # mode $04
    0x8AE4: "img_19",  # mode $04
    0x8D13: "img_29",  # mode $05
    0x8ED0: "img_1a",  # mode $01
    0x90B1: "img_27",  # mode $56
}

B3_RANGES: dict[int, str] = {
    0x7AC0: "BYTETABLE",  # table a cles [cle,lo,hi]
    0x7AE8: "BYTETABLE",  # flux d'images $00-terminés
}

B3_HEADER = (
    "; ============================================================\n"
    "; The Hobbit (Oric, 1982)\n"
    "; Original authors : Veronika Megler & Philip Mitchell (Beam Software)\n"
    "; 6502 port : Gregg Barnett (Beam Software)\n"
    "; Publisher : Melbourne House\n"
    "; - bloc 3 ($7AC0-$91B1) : banque d'illustrations vectorielles\n"
    "; Listing généré par scripts/disasm.py (partitionnement type + labels).\n"
    "; Table a cles $7AC0 + 13 flux d'octets $00-terminés (dessins, pas de\n"
    "; texte). Moteur de rendu vec_* en bloc 4 ; décodeur scripts/vec_decode.py\n"
    "; -> docs/vectors/*.svg. Formats : docs/block4-analysis.md.\n"
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
        inline_comments=INLINE_COMMENTS,
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
    "block3": Block(
        key="block3",
        lo=0x7AC0,
        hi=0x91B1,
        base_entries=[],
        manual_entries=[],
        seed_exclude=set(),
        vectors={},
        routine_docs={},
        routine_notes={},
        info=DISASM / "block3.info",
        listing=DISASM / "block3.asm",
        cfg=ROOT / "disasm" / "block3.cfg",
        header=B3_HEADER,
        vector_table=None,
        use_r2_seeds=False,
        check_rom_diff=False,
        check_code_tables=False,
        labels=B3_LABELS,
        data_ranges=B3_RANGES,
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
        if msg == 0:
            note = NULLPTR_NOTES.get(p)
            comment = "TODO pointeur $0000" + (f" : {note}" if note else "")
        else:
            comment = f"-> ${msg:04X} {preview}"
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
                out.append(";\n" if text == "" else f"; {text}\n")
        out.append(ln)
    return out


# Ligne de texte da65 : label optionnel + `.byte "..."` (sans commentaire).
_TEXT_BYTE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<label>[A-Za-z_][A-Za-z0-9_]*:)?(?P<pad>\s*)"
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


# Un octet $5C (backslash) assemble mais, ecrit tel quel dans une chaine
# `.byte "\"`, fait croire a un echappement de la quote fermante (colorisation
# des editeurs cassee). On le sort en hexadecimal.
def _hex_byte_line(prefix: str, value: int) -> str:
    quote = prefix.rfind('"')
    head = prefix[:quote] if quote != -1 else prefix.rstrip()
    return f"{head}${value:02X}\n"


def split_backslashes(asm: list[str]) -> list[str]:
    """Remplace tout backslash d'une chaine `.byte "..."` par `.byte $5C`.

    Sans effet sur les octets assembles (meme donnee) ; evite la quote
    echappee involontaire dans les listings.
    """
    out: list[str] = []
    for ln in asm:
        m = _TEXT_BYTE_RE.match(ln)
        if m is None or "\\" not in m.group("txt"):
            out.append(ln)
            continue
        prefix = ln[: m.start("txt")]
        segs = m.group("txt").split("\\")
        for idx, seg in enumerate(segs):
            if seg:
                out.append(prefix + seg + '"\n')
            if idx != len(segs) - 1:
                out.append(_hex_byte_line(prefix, 0x5C))
    return out


# Ligne de separation emise par da65 a un niveau de commentaire >= 1 : elle
# n'existe pas dans la sortie par defaut, on la jette pour la retrouver.
_DA65_SEP_RE = re.compile(r"^;\s-{3,}\s*$")
# Commentaire d'adresse da65 (niveau >= 3) : `; AAAA xx xx ...  <parite>`.
_DA65_ADDR_RE = re.compile(
    r"\s*;\s(?P<addr>[0-9A-F]{4})\s+[0-9A-F]{2}(?:\s+[0-9A-F]{2})*\s*(?:[^;].*)?$"
)


def strip_da65_addresses(asm: list[str]) -> tuple[list[str], list[int | None]]:
    """Retire les commentaires d'adresse da65 et note l'adresse de chaque ligne.

    da65 est lance avec ``--comments 4`` : chaque ligne de code/donnee porte en
    fin un commentaire ``; AAAA <octets>  <parite>`` et des lignes de
    separation ``; -----`` apparaissent entre les plages. On les retire pour
    retrouver la sortie par defaut (identite verifiee) tout en conservant,
    pour chaque ligne, l'adresse de son premier octet (None si aucun).
    """
    out: list[str] = []
    addrs: list[int | None] = []
    for ln in asm:
        if _DA65_SEP_RE.match(ln):
            continue
        m = _DA65_ADDR_RE.search(ln)
        if m:
            addrs.append(int(m.group("addr"), 16))
            out.append(ln[: m.start()].rstrip() + "\n")
        else:
            addrs.append(None)
            out.append(ln)
    return out, addrs


def inject_inline_comments(
    asm: list[str], addrs: list[int | None], comments: dict[int, str]
) -> list[str]:
    """Ajoute un commentaire ``; texte`` aux lignes d'instruction ciblees.

    ``comments`` associe une adresse de debut d'instruction au texte a ajouter
    (cf. ``Block.inline_comments``). Sans effet sur les octets assembles. Les
    lignes de donnees (``.byte``/``.word``) sont laissees intactes pour ne pas
    perturber ``reflow_text_tables`` (recollement des ``.byte "..."``).
    """
    if not comments:
        return asm
    out: list[str] = []
    for ln, addr in zip(asm, addrs):
        text = comments.get(addr) if addr is not None else None
        body = ln.rstrip("\n")
        if text is None or body.lstrip().startswith((".byte", ".word")):
            out.append(ln)
            continue
        pad = max(48, len(body) + 1)
        out.append(f"{body.ljust(pad)}; {sanitize_comment(text)}\n")
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

    ap = argparse.ArgumentParser(
        description="Desassemble un bloc en listing da65 annote."
    )
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
            "--comments",
            "4",
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
    # --comments 4 ajoute adresses et separateurs : on les retire (identite
    # avec la sortie par defaut) en gardant l'adresse de chaque ligne.
    asm, addrs = strip_da65_addresses(asm)
    asm = inject_inline_comments(asm, addrs, block.inline_comments)
    asm = reflow_text_tables(asm)
    asm = split_backslashes(asm)
    asm = inject_notes(asm, block)
    asm = drop_unused_equates(asm)
    block.listing.write_text(block.header + "".join(asm))
    print(f"Listing écrit : {block.listing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
