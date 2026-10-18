; ============================================================
; The Hobbit (Oric, 1982)
; Original authors : Veronika Megler & Philip Mitchell (Beam Software)
; 6502 port : Gregg Barnett (Beam Software)
; Publisher : Melbourne House
; - bloc 4 ($2C00-$7A80) : programme principal
; Listing généré par scripts/disasm.py (descente récursive + da65)
; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.
; ============================================================
;
; COMMENT LIRE CE LISTING
; -----------------------
; Les autres blocs alimentent celui-ci : bloc 1 = chargeur cassette
; (vecteurs ROM conserves en $0400+, reutilises par SAVE/LOAD) ; bloc 2 =
; banque de donnees (dictionnaire, messages, records, scripts des PNJ) ;
; bloc 3 = banque d'illustrations vectorielles.
;
; Cycle du jeu, une iteration par commande du joueur :
;   start ($2C35)      boot (copie cassette -> memoire) puis boucle :
;     read_line        saisit une ligne de commande dans le tampon $40BE
;     tokenize         decoupe la ligne en mots (file de tokens $4783)
;     parse_cmd        construit la commande (wid $13, arg1 $15, arg2 $16)
;     cmd_run          execute la commande du joueur (verbe + objets)
;     world_tick       fait vivre le monde (PNJ puis evenements differes)
;
; Deux moteurs d'animation distincts :
;   AnimTalk   : le parser textuel (saisie -> lexeur 5-bit -> grammaire),
;                qui transforme une phrase en commande interne.
;   AnimAction : les PNJ autonomes ; $4ED5 fait jouer a chaque personnage
;                un opcode de son 'cerveau' (script du bloc 2), meme quand
;                le joueur est ailleurs.
;
; Mode sonde / action reelle : avant d'agir pour de vrai, le jeu rejoue la
; meme sequence en simulation (phase $0C = 0) pour savoir si l'action passe
; (passok $12) ; seule une action qui passe est rejouee en reel (phase = 1).
;
; Conventions de code :
;   - Message inline : JSR $440D ($4444 render_text) ou JSR $5B24 (act_msg),
;     suivi des 2 octets d'adresse du message ; reprise a JSR+5. Chaque site
;     porte un label 'msg_XXXX' avec un apercu du texte en commentaire.
;   - Appel indirect : l'adresse cible est posee dans $4C64/$4C65 puis
;     appelee par indirect_call ($4C5D) ; c'est le mecanisme des tables
;     d'actions $7014 (verbes joueur) / $7143 (PNJ) et de $7169 (evenements).
;   - Pointeurs de travail : ptr/ptr2/ptr3 ($8A/$88/$7A) se sauvent et se
;     restaurent via la pile interne $0200 (push_ptr/pop_ptr, fetch_retaddr).
;   - Les labels 'Lxxxx' / 'code_xxxx' restants sont des adresses que le
;     desassemblage n'a pas encore baptisees.
; ============================================================

; da65 V2.19 - Git 71746c829


        .setcpu "6502"

L0000           := $0000
col             := $0004                        ; Nombre de colonnes restantes sur la ligne (pour couper la ligne au bon moment)
outen           := $000B                        ; Autorise ou non l'affichage du texte (1 = autorise)
phase           := $000C                        ; 0 = simulation (le jeu calcule sans rien afficher), 1 = action reelle
raw             := $000D                        ; Affichage brut : 1 = texte force, sans mise en forme
cap             := $000E                        ; 1 = mettre une majuscule a la prochaine lettre (apres un point)
sppend          := $000F                        ; Un espace a inserer avant le prochain mot
crcnt           := $0011                        ; Nombre de lignes affichees depuis la derniere pause (remis a zero toutes les 16)
passok          := $0012                        ; 1 = la simulation a reussi, on passe a l'action reelle
wid             := $0013                        ; Mot courant interprete (verbe ou direction)
arg1            := $0015                        ; Premier objet de la commande ($FF = aucun)
arg2            := $0016                        ; Second objet de la commande ($FF = aucun)
orec            := $0017                        ; Pointeur vers la fiche du premier objet (octet haut en $18)
orec_hi         := $0018                        ; Octet haut de orec
orec2           := $0019                        ; Pointeur vers la fiche du second objet (octet haut en $1A)
orec2_hi        := $001A                        ; Octet haut de orec2
adr             := $005C                        ; Adresse de travail : mot de message en cours (octet haut en $5D)
adr_hi          := $005D                        ; Octet haut de adr
L006A           := $006A
tidx            := $006F                        ; Position du caractere en cours dans le message affiche
nest            := $0070                        ; Niveau d'imbrication du message (0 = message simple)
wptr            := $0071                        ; Pointeur vers le mot ou nom en cours (octet haut en $72)
wptr_hi         := $0072                        ; Octet haut de wptr
direct          := $0073                        ; Sortie normale, sans controle particulier
variant         := $0074                        ; Sortie en variante (selon le type de commande)
msgstk          := $0076                        ; Index de la pile des messages imbriques
xaux            := $0077                        ; Octet auxiliaire : options de mise en forme de la sortie
xmode           := $0078                        ; Octet de mode de la sortie (direct, variante...)
ptr3            := $007A                        ; Troisieme pointeur de travail (octet haut en $7B)
ptr3_hi         := $007B                        ; Octet haut de ptr3
ptr2            := $0088                        ; Pointeur secondaire, pour balayer les tables (octet haut en $89)
ptr2_hi         := $0089                        ; Octet haut de ptr2
ptr             := $008A                        ; Pointeur de travail principal (octet haut en $8B)
ptr_hi          := $008B                        ; Octet haut de ptr
key             := $008F                        ; Cle de l'evenement a declencher
noise           := $0093                        ; Source du hasard (pour les tirages aleatoires)
noise_hi        := $0094                        ; Octet haut de noise
svA             := $00AD                        ; Sauvegarde de l'accumulateur A
svX             := $00AE                        ; Sauvegarde du registre X
rstk            := $00AF                        ; Index de la pile interne d'adresses
exploc          := $00BE                        ; Lieu attendu par l'evenement en cours
dflag           := $00C3                        ; Flag de l'action du dragon : initialise a 0 par l'intro, jamais arme (inactif)
sflag           := $00C4                        ; Flag de sortie texte : arme au desarmement de l'evenement e7, ajoute un H apres s/S
obj             := $00C5                        ; Entite/acteur courant ($FF = personne) ; acteur du log AnimAction (ref. Wilderland L_ACTING_ANIMAL)
crec            := $00C6                        ; Pointeur vers la fiche courante (compteurs du personnage/objet en cours)
crec_hi         := $00C7                        ; Octet haut de crec
ploc            := $00C8                        ; Lieu du joueur (simple copie : la vraie valeur est player.eloc en $1B2A)
eloc            := $00C9                        ; Lieu d'un personnage (visible quand il est identique a celui du joueur)
once            := $00CE                        ; Verrou 'une seule fois' : pose puis consomme
cand            := $00CF                        ; Index de candidat dans les tables de deplacement $48D3/$48D5 (moteur d'errance)
mwt             := $00D0                        ; Budget/poids du deplacement (moteur d'errance : $0A moins les couts)
qrd             := $00D1                        ; Curseur de lecture de la file d'actions $4905 (remis a 0 a chaque commande)
qwr             := $00D2                        ; Curseur d'ecriture de la file d'actions $4905 (remis a 0 a chaque commande)
macc            := $00D3                        ; Accumulateur de poids du moteur d'errance
mcnt            := $00D4                        ; Compteur de candidats retenus par le moteur d'errance
said            := $00D5                        ; Flag : le PNJ a parle/refuse (pose par code_6C2E, remis a 0 par act_v14_13)
op1             := $00D7                        ; Etat du 1er operateur lors de la resolution d'une sortie (bits 0 et 1 testes)
op2             := $00D8                        ; Etat du 2e operateur lors de la resolution (bits 0 et 1 testes)
rn1             := $00D9                        ; Compteur n°1 de la boucle de resolution d'operande
rn2             := $00DA                        ; Compteur n°2 de la boucle de resolution d'operande
rn3             := $00DB                        ; Compteur n°3 de la boucle de resolution d'operande
cond1           := $00DC                        ; Condition memorisee n°1
cond2           := $00E2                        ; Condition memorisee n°2
svptr           := $00E8                        ; Sauvegarde du pointeur de travail
svptr_hi        := $00E9                        ; Octet haut de svptr
rbit            := $00EC                        ; Bit7 du 1er mot de la commande (flag direct/variante)
ralt            := $00ED                        ; Compteur d'alternatives de la resolution
roff1           := $00EE                        ; Offset du 1er operateur dans le record de commande
roff2           := $00EF                        ; Offset du 2e operateur dans le record de commande
rid1            := $00F0                        ; Id du 1er operateur resolu
rid2            := $00F1                        ; Id du 2e operateur resolu
rword           := $00F2                        ; Mot/verbe de la commande en cours (alimente les arguments VM $466F)
rword_hi        := $00F3                        ; Octet haut de rword
rarg1           := $00F4                        ; Operande n°1 de la commande (paire de mots VM)
rarg1_hi        := $00F5                        ; Octet haut de rarg1
rarg2           := $00F6                        ; Operande n°2 de la commande (paire de mots VM)
rarg2_hi        := $00F7                        ; Octet haut de rarg2
exitp           := $00F8                        ; Curseur dans la table des sorties du lieu
exitp_hi        := $00F9                        ; Octet haut de exitp
L0405           := $0405
L0408           := $0408
L040B           := $040B
L040E           := $040E
L0411           := $0411
L0414           := $0414
L0417           := $0417
autorun:jmp     start

ptr_block3:
        .byte   $C0
L2C04:  .byte   $7A
vec_init:
        jmp     drawing

vec_01: jmp     vec_keypause

vec_02: jmp     tape_load

vec_03: jmp     tape_save

vec_04: jmp     tape_verify

vec_05: jmp     tape_prompt

vec_06: jmp     tape_prompt_save

vec_07: jmp     tape_prompt_verify

vec_08: jmp     ok_rts

vec_09: jmp     vec_kbd_clear

vec_10: jmp     vec_cr

vec_11: jmp     get_key

keyin:  jmp     wait_for_key

print_cr:
        jmp     cr_out

putchar:jmp     ch_out

main:   jmp     game_main

; Point de depart du jeu, juste apres le chargement de la cassette.
; boot_copy copie l'etat initial (cassette) vers la memoire de travail, la
; pile est initialisee, puis la grande boucle prend la main :
;   afficher la situation -> lire une commande -> tokenize -> parse_cmd
;   -> cmd_run (execution) -> world_tick (le monde avance), et on recommence.
; Les commandes speciales (SAVE/LOAD/QUIT/HELP...) sont aiguillees par $57
; vers special_cmd, sinon l'action ordinaire passe par perform_action.
start:  jsr     boot_copy
        ldx     #$FF
        txs
        bne     L2C49
L2C3D:  jsr     keyin
        cmp     #$4E
        bne     L2C49
        lda     #$00
        jmp     L2C4B

L2C49:  lda     #$01
L2C4B:  sta     $56
        lda     #$FF
        sta     $65
        jsr     boot_copyback
        jsr     init_vars
        ldx     #$C8
        lda     #$00
L2C5B:  sta     L47E2,x
        dex
        bne     L2C5B
        sta     $5E
        sta     $57
        sta     sflag
        sta     $0A
        lda     #$01
        sta     outen
        sta     phase
        lda     $65
        cmp     #$FF
        bne     L2C99
        jsr     intro_look
        lda     #$01
        sta     raw
        ldx     #$00
L2C7E:  lda     L308F,x
        jsr     putchar
        inx
        cmp     #$0D
        bne     L2C7E
        ldx     #$00
L2C8B:  lda     L3091,x
        sta     L40BE,x
        inx
        cmp     #$0D
        bne     L2C8B
        jmp     L2C9E

L2C99:  jsr     read_line
        beq     L2CC8
L2C9E:  ldx     #$40
        lda     #$00
L2CA2:  sta     L4782,x
        dex
        bne     L2CA2
        ldx     #$00
        ldy     #$00
L2CAC:  jsr     tokenize
        cmp     #$D0
        bne     L2CB6
        jmp     L2D9F

L2CB6:  lda     adr_hi
        sta     L4783,y
        iny
        lda     adr
        sta     L4783,y
        iny
        lda     $5B
        cmp     #$C0
        bne     L2CAC
L2CC8:  lda     #$00
        sta     $5F
        sta     crcnt
L2CCE:  lda     #$00
        sta     $65
        sta     $90
        sta     qwr
        sta     qrd
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        jsr     parse_cmd
        bne     L2D45
        lda     $5F
        pha
        lda     #$17
        sta     ptr2
        lda     #$4A
        sta     ptr2_hi
        jsr     cmd_store
        lda     $65
        sta     $B0
        lda     #$00
        sta     $7E
L2CFB:  lda     #$00
        sta     $57
        jsr     cmd_run
        bne     L2D55
        lda     #$01
        sta     phase
        jsr     describe_room
        jsr     perform_action
L2D0E:  lda     $57
        pha
        lda     $7E
        pha
        lda     svptr
        pha
        lda     svptr_hi
        pha
        jsr     world_tick
        pla
        sta     svptr_hi
        pla
        sta     svptr
        pla
        sta     $7E
        pla
        sta     $57
        lda     $7E
        bne     L2CFB
L2D2D:  jsr     rec_rewind2
        dec     $B0
        bne     L2CFB
        pla
        sta     $5F
        ldy     $5F
        lda     L4783,y
        and     #$F0
        cmp     #$C0
        bne     L2CCE
L2D42:  jmp     L2C99

L2D45:  cmp     #$02
        beq     L2D42
        lda     #$01
        sta     raw
        jsr     print_msg
; -> $1177 WHAT ?
msg_2D50:
        .word   $1177
code_2D52:
        jmp     L2C99

L2D55:  lda     $57
        pha
        lda     #$00
        sta     $57
        lda     $7E
        beq     L2D64
        pla
        jmp     L2D2D

L2D64:  pla
        cmp     #$01
        beq     L2D73
        cmp     #$02
        beq     L2D97
        jsr     rev_real
        jmp     L2D2D

L2D73:  lda     $79
        beq     L2D7F
        jsr     special_cmd
L2D7A:  pla
        pla
        jmp     L2C99

L2D7F:  lda     rword
        sta     L466F
        lda     rword_hi
        sta     L4670
        lda     #$00
        sta     raw
        sta     $7E
        jsr     print_msg
; -> $117C YOU<W>. TIME PASSES...
msg_2D92:
        .word   $117C
code_2D94:
        jmp     L2D0E

L2D97:  jsr     rev_dispatch2
        bne     L2D7A
        jmp     L2D2D

L2D9F:  lda     #$01
        sta     raw
        jsr     print_msg
; -> $116B I DO NOT KNOW THE WORD '
msg_2DA6:
        .word   $116B
code_2DA8:
        ldx     $60
L2DAA:  lda     L40BE,x
        cmp     #$0D
        beq     L2DBD
        cmp     #$22
        beq     L2DBD
        jsr     putchar
        inx
        cmp     #$20
        bne     L2DAA
L2DBD:  lda     #$22
        jsr     putchar
        jsr     print_cr
        jmp     L2C99

; Remet a zero les compteurs de depart (variables de travail, pile de messages, score)
; juste avant de lancer la partie.
; Technique : $97-$9C = 0, rstk $AF = 0, score $CC/$CD = 0, puis jmp game_main.
init_vars:
        lda     #$00
        ldx     #$05
L2DCC:  sta     $97,x
        dex
        bpl     L2DCC
        sta     rstk
        sta     $CC
        sta     $CD
        cld
        jmp     main

; '@' en tete de ligne : annule la commande tapee et reaffiche le prompt
input_abort:
        lda     $57
        bne     line_read
        lda     #$08
        jsr     putchar
        jsr     putchar
        lda     #$00
        rts

; QUOI : lit la commande du joueur (prompt '> ', ex. TAKE LAMP puis ENTREE).
; ENTREE : rien ; SORTIE : tampon $40BE rempli jusqu'au CR, A=1 (ok) ou 0 ('@' annule).
; EXEMPLE : le joueur tape OPEN GREEN DOOR. -> $40BE recoit la phrase + point final.
; COMMENT : boucle touche par touche (line_loop) ; ins_period ajoute le point
; manquant, ins_quote ferme le guillemet ; $B8 = etat guillemet ; DEL efface tout,
; RETOUR efface une lettre ; les fleches deviennent N/S/E/W (key_arrow).
read_line:
        lda     #$30
        sta     $61
        lda     #$75
        sta     $62
        lda     #$01
        sta     raw
        sta     phase
        lda     #$3E
        jsr     putchar
        lda     #$20
        jsr     putchar
        ldx     #$00
; Saisie : lit une touche du joueur puis l'aiguille vers son traitement
line_loop:
        stx     $B8
        jsr     read_key
        jsr     key_arrow
        jmp     line_dispatch

; Saisie : relit une touche apres un effacement, sans retraduire les fleches
line_read:
        jsr     read_key
; Saisie : aiguille la touche vers fin de ligne, effacement ou edition
line_dispatch:
        cpx     #$00
        bne     line_del
        cmp     #$40
        beq     input_abort
; Saisie : touche DEL efface toute la ligne tapee par le joueur
line_del:
        cmp     #$7F
        bne     line_backspace
        jsr     line_clear
        jmp     line_loop

; Saisie : touche RETOUR efface la derniere lettre tapee par le joueur
line_backspace:
        cmp     #$08
        bne     line_edit
        cpx     #$00
        beq     line_read
        jsr     putchar
        dex
        lda     L40BE,x
        cmp     #$22
        bne     line_read
        lda     $B8
        eor     #$01
        sta     $B8
        jmp     line_read

; Saisie : accepte une lettre, un guillemet ou un espace tapes par le joueur
line_edit:
        cmp     #$40
        bcs     line_store
        cmp     #$22
        bne     line_classify
        lda     $B8
        eor     #$01
        sta     $B8
        bne     L2E53
        jsr     ins_period
L2E53:  lda     #$22
        jmp     line_store

; Saisie : trie espace, ENTREE, point et virgule tapes par le joueur
line_classify:
        cmp     #$20
        beq     line_store
        cmp     #$0D
        beq     line_cr
        cmp     #$2E
        beq     line_store
        cmp     #$2C
        bne     line_read
; Saisie : ajoute la lettre tapee a la commande et l'affiche en echo
line_store:
        cpx     #$80
        beq     line_read
        jsr     putchar
        sta     L40BE,x
        inx
        jmp     line_read

; Saisie : ENTREE termine la commande du joueur et la rend utilisable
line_cr:lda     $B8                             ; CR : la commande est close (point final + guillemet)
        beq     L2E7D
        jsr     ins_quote
L2E7D:  jsr     ins_period
        lda     #$0D
        sta     L40BE,x
        inx
        jsr     putchar
        lda     #$01
        rts

; Saisie : ferme le guillemet oublie par le joueur en fin de ligne
ins_quote:
        jsr     ins_period
        lda     #$22
        sta     L40BE,x
        inx
        jmp     putchar

; Saisie : ajoute le point final oublie par le joueur en fin de commande
ins_period:
        lda     L40BD,x
        cmp     #$2E
        beq     L2EA8
        lda     #$2E
        sta     L40BE,x
        inx
        jsr     putchar
L2EA8:  rts

; QUOI : une fleche Oric joue un deplacement sans taper de commande.
; EXEMPLE : fleche haut -> le jeu recoit N. comme si le joueur avait tape NORTH.
; COMMENT : ecrit la lettre + CR dans $40BE (key_dir_put), declenche GO au tour suivant.
key_arrow:
        cmp     #$15
        beq     key_e
        cmp     #$08
        beq     key_w
        cmp     #$0A
        beq     key_s
        cmp     #$0B
        beq     key_n
        rts

; Fleche haut : le joueur va au NORD sans taper de commande
key_n:  lda     #$4E
; Fleche : ecrit la direction voulue dans la commande et valide par ENTREE
key_dir_put:
        sta     L40BE,x
        inx
        jsr     putchar
        lda     #$0D
        rts

; Fleche gauche : le joueur va a l'OUEST sans taper de commande
key_w:  lda     #$57
        jmp     key_dir_put

; Fleche droite : le joueur va a l'EST sans taper de commande
key_e:  lda     #$45
        jmp     key_dir_put

; Fleche bas : le joueur va au SUD sans taper de commande
key_s:  lda     #$53
        jmp     key_dir_put

; QUOI : decoupe la phrase du joueur en mots connus (ex. TAKE -> verbe, LAMP -> nom).
; ENTREE : tampon $40BE, curseur X ; SORTIE : $5B = nature du mot, adr = fiche dico, A = $5B.
; EXEMPLE : TAKE LAMP. -> [verbe TAKE][nom LAMP][fin .] ; mot inconnu -> $D0 puis WHAT ?.
; COMMENT : 1. saute espaces ($60 = position), CR -> $C0 ; 2. ponctuation $B0/$A0/$90
; (punct_class) ; 3. decode lettres en $47C3 puis balaye le seau $0500[2*lettre]
; (dict_next/word_prefix_cmp) ; 4. word_type lit la classe dans le bloc 2.
tokenize:
        tya                                     ; entree du lexeur : un mot -> un token
        pha
L2ED7:  lda     L40BE,x
        inx
        cmp     #$20
        beq     L2ED7
        dex
        stx     $60
        cmp     #$0D                            ; CR en fin de ligne -> token de fin $C0
        beq     lex_cr
        jsr     punct_class                     ; test ponctuation (point, virgule, guillemet)
        bne     lex_emit
        jsr     dict_bucket
        bne     L2EFA
L2EF0:  jsr     word_prefix_cmp
        beq     L2EFF
L2EF5:  jsr     dict_next
        beq     L2EF0
L2EFA:  lda     #$D0
        jmp     lex_emit

L2EFF:  lda     $67
        cmp     $66
        bcs     word_finish
        cmp     #$04
        bcc     L2EF5
        tya
        pha
        lda     $63
        pha
        lda     $64
        pha
        jsr     dict_next
        bne     lex_restore
        jsr     word_prefix_cmp
        bne     lex_restore
        pla
        sta     $64
        pla
        sta     $63
        pla
        tay
        jmp     L2EF5

; Fin de commande : le joueur a tape ENTREE, on clot la phrase
lex_cr: lda     #$C0
; Lexeur : prepare un mot sans adresse (ponctuation, fin de phrase)
lex_emit:
        pha
        lda     #$00
        sta     adr
        sta     adr_hi
        pla
; Lexeur : range la nature du mot (verbe, nom, fin...) et rend la main
lex_type:
        sta     $5B
        ora     adr_hi
        sta     adr_hi
        pla
        tay
        lda     $5B
        rts

; Lexeur : abandonne un essai d'abrege et reprend la recherche au mot entier
lex_restore:
        pla
        sta     $64
        pla
        sta     $63
        pla
        tay
; Mot reconnu : retrouve sa fiche dictionnaire et sa nature (verbe, nom...)
word_finish:
        tya
        pha
        ldy     #$00
; Dictionnaire : saute les lettres d'un mot pour passer au mot suivant
word_skip:
        lda     ($63),y
        iny
        and     #$80
        beq     word_skip
        cpy     #$02
        beq     word_skip
        cpy     #$03
        bne     word_grammar
        dey
        dey
        lda     ($63),y
        iny
        iny
        and     #$80
        bne     word_skip
; Dictionnaire : suit le renvoi vers la vraie fiche du mot (synonyme)
word_grammar:
        dey
        lda     ($63),y
        and     #$40
        beq     word_type
        iny
        lda     ($63),y
        clc
        adc     #$00
        pha
        iny
        lda     ($63),y
        adc     #$05
        sta     $64
        pla
        sta     $63
; Mot reconnu : lit sa nature grammaticale (verbe, nom, adjectif...)
word_type:
        ldy     #$00                            ; type = bits 6-5 des 2 premiers octets de l'entree de dictionnaire
        lda     ($63),y
        rol     a
        and     #$C0
        sta     $5B
        iny
        lda     ($63),y
        ror     a
        and     #$30
        ora     $5B
        sta     $5B
        lda     $63
        sec
        sbc     #$00
        sta     adr
        lda     $64
        sbc     #$05
        sta     adr_hi
        pla
        tay
        lda     $5B                             ; type $D0 = entree ignoree par le parseur (mot de message)
        cmp     #$D0
        bne     lex_type
        jmp     L2EF5

; Ponctuation du joueur : distingue le point, la virgule et le guillemet
punct_class:
        ldy     #$B0
        cmp     #$2E
        beq     punct_hit
        ldy     #$A0
        cmp     #$2C
        beq     punct_hit
        ldy     #$90
        cmp     #$22
        beq     punct_hit
        lda     #$00
        rts

; Ponctuation reconnue : avance apres le signe et rend sa nature
punct_hit:
        inx
        tya
        rts

; Cherche le mot tape par le joueur dans la tranche de sa 1re lettre
dict_bucket:
        ldy     #$00
L2FBD:  lda     L40BE,x
        cmp     #$40
        bcc     dict_start
        and     #$1F
        sta     L47C3,y
        inx
        iny
        jmp     L2FBD

; Dictionnaire : se place au debut des mots commencant par cette lettre
dict_start:
        sty     $66
        lda     L47C3
        clc
        adc     L47C3
        tay
        lda     $0500,y
        clc
        adc     #$00
        sta     $63
        iny
        lda     $0500,y
        adc     #$05
        sta     $64
        ldy     #$00
; Dictionnaire : passe au mot suivant commencant par la meme lettre
dict_next:
        tya
        clc
        adc     $63
        sta     $63
        bcc     dict_cmp1
        inc     $64
; Dictionnaire : verifie que le candidat commence pareil
dict_cmp1:
        ldy     #$00
        lda     ($63),y
        and     #$1F
        cmp     L47C3
        beq     dict_read
        rts

; Candidat serieux : decode ses lettres pour comparaison complete
dict_read:
        sta     L47D3,y
        txa
        pha
        ldx     #$01
        iny
; Dictionnaire : decode les lettres tassees 5-bit d'un mot du jeu
dict_letters:
        lda     ($63),y
        and     #$1F
        beq     dict_letter_next
        sta     L47D3,x
        inx
; Dictionnaire : gere les mots tres courts de 2-3 lettres (ex. GO, IN)
dict_letter_next:
        lda     ($63),y
        iny
        and     #$80
        beq     dict_letters
        cpy     #$02
        beq     dict_letters
        cpy     #$03
        bne     dict_end
        dey
        dey
        lda     ($63),y
        iny
        iny
        and     #$80
        bne     dict_letters
; Candidat decode : note sa longueur pour la comparaison finale
dict_end:
        stx     $67
        dey
        lda     ($63),y
        iny
        and     #$40
        beq     dict_done
        iny
        iny
; Lecture finie : dit si la 1re lettre correspondait au mot tape
dict_done:
        pla
        tax
        lda     #$00
        rts

; QUOI : accepte les abreges du joueur (N. pour NORTH, L. pour LOOK...).
; ENTREE : mot tape ($47C3, long. $66) et candidat ($47D3, long. $67).
; SORTIE : A=0 (Z) si le debut coincide, A=1 sinon.
; COMMENT : compare sur min($66,$67) lettres (cmp_min/cmp_loop).
word_prefix_cmp:
        txa
        pha
        tya
        pha
        lda     $66
        cmp     $67
        bcc     cmp_min
        lda     $67
; Abrege : compare sur la longueur du plus court des 2 mots
cmp_min:tax
        ldy     #$00
; Abrege : compare lettre a lettre le mot tape et le candidat
cmp_loop:
        lda     L47C3,y
        cmp     L47D3,y
        bne     cmp_diff
        iny
        dex
        bne     cmp_loop
        pla
        tay
        pla
        tax
        lda     #$00
        rts

; Mots differents : le candidat est rejete, on passe au suivant
cmp_diff:
        pla
        tay
        pla
        tax
        lda     #$01
        rts

; QUOI : garde les propositions comprises avant de les executer (ex. avant/apres AND).
; ENTREE : $65 propositions de 24 o en $4927 ; SORTIE : copie filtree en $4A17.
; EXEMPLE : TAKE LAMP AND SWORD -> 2 propositions gardees pour execution.
; COMMENT : ne garde que les mots marques (bit $40 de l'octet +1).
cmd_store:
        jsr     push_ptr
        lda     #$27
        sta     ptr
        lda     #$49
        sta     ptr_hi
        lda     $65
        sta     $6C
        ldy     #$00
L3076:  ldx     #$18
L3078:  lda     (ptr),y
        sta     (ptr2),y
        iny
        dex
        bne     L3078
        iny
        lda     (ptr),y
        dey
        and     #$40
        bne     L3076
        dec     $6C
        bne     L3076
        jmp     pop_ptr2

L308F:  .byte   "> "
L3091:  .byte   "LOOK."
        .byte   $0D
; Le jeu ne travaille jamais directement sur la cassette : il en recopie le contenu en
; memoire haute et joue sur cette copie (le TAPE reste intact et rechargeable).
; Cette routine fait la copie initiale sauvegarde -> memoire de travail.
; Technique : table de 4 descripteurs en $30F9 ; $6C = nombre de segments.
boot_copy:
        lda     #$04
        sta     $6C
        ldx     #$00
L309D:  ldy     #$00
L309F:  lda     L30F9,x
        sta     ptr2,y
        inx
        iny
        cpy     #$06
        bne     L309F
L30AB:  ldy     #$00
        lda     (ptr),y
        sta     ($8C),y
        jsr     boot_ptr_step
        bne     L30AB
        dec     $6C
        bne     L309D
        rts

; Copie en sens inverse : ramene la memoire de travail vers la zone de sauvegarde
; (par exemple avant d'ecrire sur la cassette).
; Technique : meme table de descripteurs que boot_copy.
boot_copyback:
        lda     #$04
        sta     $6C
        ldx     #$00
L30C1:  ldy     #$00
L30C3:  lda     L30F9,x
        sta     ptr2,y
        inx
        iny
        cpy     #$06
        bne     L30C3
L30CF:  ldy     #$00
        lda     ($8C),y
        sta     (ptr),y
        jsr     boot_ptr_step
        bne     L30CF
        dec     $6C
        bne     L30C1
        rts

; Avance d'un octet les deux pointeurs de copie : ptr ($8A, report en $8B) et
; $8C (report en $8D) ; decremente le compteur de segment ptr2 ($88/$89). Rend Z
; (A=0) quand ptr2 atteint zero, ce qui termine le segment courant de boot_copy /
; boot_copyback.
boot_ptr_step:
        inc     ptr
        bne     L30E5
        inc     ptr_hi
L30E5:  inc     $8C
        bne     L30EB
        inc     $8D
L30EB:  lda     ptr2
        sec
        sbc     #$01
        sta     ptr2
        bcs     L30F6
        dec     ptr2_hi
L30F6:  ora     ptr2_hi
        rts

L30F9:  .byte   $56,$05,$1A,$1B,$D0,$91,$F1,$02
        .byte   $CC,$28,$26,$97,$C8,$05,$1A,$21
        .byte   $17,$9A,$18,$00,$BE,$00,$DF,$9F
; QUOI : comprend la phrase (GO NORTH, TAKE ALL EXCEPT LAMP, OPEN DOOR WITH KEY).
; ENTREE : file de mots $4783 ; SORTIE : fiche commande 24 o a (ptr2), A=0 ok / 1 WHAT ? / 2 refaire.
; EXEMPLE : TAKE ALL EXCEPT LAMP -> portee ALL ($6E=1) sauf LAMP.
; COMMENT : dispatch chaque mot par sa classe via table $315A (index = type>>3) ;
; etat : $6D attente, $6E portee (0 normal, 1 ALL, 2 EXCEPT), $9D virgules, $65 mots,
; $5A/$5B precedant/courant, $5F curseur, $A3..$AC groupe nominal courant.
;
; Classes dictionnaire (cf. bloc 2) :
;   $00 adverbe   $10 IN/INTO     $20 direction   $30 verbe
;   $40 GO/RUN    $50 nom         $60 adjectif    $70 preposition
;   $80 article   $90 mot-cle special (SAVE/QUIT/HELP/ALL/EXCEPT...)
;   $A0 AND/virgule   $B0 THEN/point(=fin de commande)
parse_cmd:
        jsr     set_mode0
        lda     #$FF
        sta     $6D
        lda     #$C0                            ; $5B = $C0 : on amorce avec un type precedent 'fin de commande'
        sta     $5B
; Grammaire : commence une nouvelle proposition (ex. apres AND ou THEN)
next_word:
        lda     #$00
        sta     $9D
        lda     $6D
        ora     #$C7
        sta     $6D
        lda     $6E                             ; $6E : portee de commande (0 normal, 1 ALL, 2 EXCEPT)
        cmp     #$02
        bne     L3132
        lda     $6D
        and     #$FD
        sta     $6D
L3132:  jsr     rec_clear
; Grammaire : oublie le groupe de mots precedent et lit la suite
next_phrase:
        ldx     #$09
        lda     #$00
L3139:  sta     $A3,x
        dex
        bpl     L3139
        lda     $6D
        ora     #$10
        sta     $6D
; QUOI : aiguille chaque mot vers son traitement (verbe, nom, direction...).
; ENTREE : mot courant (next_token) ; SORTIE : saut vers le handler de classe.
; COMMENT : index = type>>3, saut indirect table $315A ; operande auto-patche en $3158/$3159.
dispatch:
        jsr     next_token                      ; dispatch : lit le token suivant et saute vers sa classe
        lsr     a                               ; index de classe = type >> 3 (2 x le nibble de classe)
        lsr     a
        lsr     a
        clc
        adc     #$5A
        sta     L3158
        lda     #$31
        adc     #$00
        sta     L3159
L3158           := * + 1
L3159           := * + 2
        jmp     (L315A)                         ; saut indirect via la table $315A (12 adresses de handlers, indexee par classe)

L315A:  .byte   $99
        .byte   "2}3"
        .byte   $8F
        .byte   "2"
        .byte   $F3
        .byte   "2"
        .byte   $E9
        .byte   "2"
        .byte   $C8
        .byte   "3"
        .byte   $BF
        .byte   "3"
        .byte   $90
        .byte   "3t3"
        .byte   $9B
        .byte   ";"
        .byte   $B9
        .byte   "2r1"
; QUOI : le point final valide la commande du joueur (ou THEN l'enchaine).
; ENTREE : attente $6D, mots $65 ; SORTIE : poursuit, A=1 WHAT ? ou A=2 saisie a refaire.
; EXEMPLE : GO NORTH. -> valide ; phrase vide -> WHAT ?.
; COMMENT : si un groupe nominal attendait (bit1 $6D) sans mot retenu, echec ; sinon
; finalise en $3196 (portee ALL/EXCEPT, rec_next, fusions).
cmd_end:lda     $6D                             ; classe 11 ($B0) : point/THEN = fin de commande
        and     #$02
        beq     L3196
        lda     $65
        bne     L3196
        lda     $57
        bne     L3196
        lda     $5A
        cmp     #$C0
        beq     L318A
        cmp     #$B0
        bne     L3193
L318A:  lda     $5B
        cmp     #$B0
        bne     L3193
        lda     #$02
        rts

L3193:  lda     #$01
        rts

L3196:  lda     $6E
        cmp     #$01
        bne     L31A6
        ldy     #$01
        lda     (ptr2),y
        ora     #$80
        sta     (ptr2),y
        lda     $6E
L31A6:  cmp     #$02
        bne     L31B0
        lda     $5B
        cmp     #$A0
        beq     L31B2
L31B0:  inc     $65
L31B2:  jsr     rec_next
        lda     $5B
        cmp     #$A0
        bne     L31BE
        jmp     next_word

L31BE:  ldy     $57
        beq     L3219
        ldx     #$08
        lda     L4927,x
        inx
        ora     L4927,x
        beq     L31F0
        lda     L4927,x
        iny
        cmp     L490F,y
        bne     L31E0
        dey
        dex
        lda     L490F,y
        cmp     L4927,x
        beq     L31F0
L31E0:  ldx     #$12
        lda     L4927,x
        inx
        ora     L4927,x
        bne     L3219
        ldy     #$12
        jmp     L31F2

L31F0:  ldy     #$08
L31F2:  ldx     $57
        lda     #$03
L31F6:  pha
        lda     L4927,y
        inx
        iny
        ora     L4927,y
        bne     L3211
        lda     L490F,x
        sta     L4927,y
        dex
        dey
        lda     L490F,x
        sta     L4927,y
        inx
        iny
L3211:  inx
        iny
        pla
        sec
        sbc     #$01
        bne     L31F6
L3219:  jsr     push_ptr2
        lda     #$0F
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        lda     $65
        sta     $6C
        lda     $57
        beq     L3231
        inc     $6C
        jsr     rec_prev
L3231:  jsr     rec_fwd_dec
L3234:  lda     $6C
        beq     L324C
        jsr     rec_fwd_dec
        ldy     #$01
        lda     (ptr2),y
        and     #$7F
        dey
        ora     (ptr2),y
        bne     L3249
        jsr     rec_merge
L3249:  jmp     L3234

L324C:  lda     $65
        sta     $6C
        jsr     pop_ptr
        jsr     push_ptr2
        jsr     rec_prev_dec
L3259:  lda     $6C
        beq     L3289
        jsr     rec_prev_dec
        ldy     #$12
        lda     (ptr2),y
        iny
        ora     (ptr2),y
        bne     L3259
        ldy     #$00
        lda     (ptr2),y
        cmp     (ptr),y
        bne     L3259
        iny
        lda     (ptr2),y
        cmp     (ptr),y
        bne     L3259
        ldy     #$0E
        lda     (ptr),y
        iny
        ora     (ptr),y
        beq     L3259
        ldy     #$0E
        jsr     rec_copy_check
        jmp     L3259

L3289:  jsr     pop_ptr
        lda     #$00
        rts

; Direction (classe 2) : enregistre la direction demandee (N/S/E/W...), qui
; devient le wid du deplacement.
cls_direction:
        lda     $6D                             ; classe 2 ($20) : direction
        and     #$02
        bne     L32EF
        ldx     #$00
        stx     $5B
; Adverbe (classe 0) : impose un mode d'execution a l'action suivante
; (doucement, vite...).
cls_adverb:
        lda     $6D                             ; classe 0 ($00) : adverbe
        and     #$04
        bne     L32A2
        jmp     parse_fail

L32A2:  lda     $6E
        cmp     #$02
        bne     L32AB
        jsr     rec_back_mode0
L32AB:  lda     $6D
        and     #$FD
        sta     $6D
        ldx     #$02
        jsr     rec_store_at
        jmp     next_phrase

; AND / virgule (classe 10) : enchaine plusieurs objets dans une meme
; commande en sauvegardant l'etat du groupe nominal.
cls_conj:
        lda     $6D                             ; classe 10 ($A0) : AND / virgule (objets multiples)
        and     #$F7
        sta     $6D
        pha
        lda     $5B
        pha
L32C3:  jsr     next_token
        cmp     #$A0
        beq     L32C3
        ldx     $5F
        dex
        dex
        stx     $5F
        stx     $9E
        pla
        sta     $5B
        pla
        sta     $6D
        sta     $9F
        lda     ptr2
        sta     $A0
        lda     ptr2_hi
        sta     $A1
        lda     $65
        sta     $A2
        jmp     cmd_end

; GO / RUN (classe 4) : verbe de deplacement ; reclasse en verbe ($30) et
; traite comme tel.
cls_go: lda     $6D                             ; classe 4 ($40) : GO / RUN
        and     #$FE
        sta     $6D
L32EF:  lda     #$30
        sta     $5B
; Verbe (classe 3) : traite le mot comme predicat de la commande. Selon
; l'etat d'attente ($6D bit3), restaure l'enregistrement du groupe nominal
; precedent puis cloture (cmd_end), ou installe le verbe et attend ses objets.
cls_verb:
        lda     $6D                             ; classe 3 ($30) : verbe
        and     #$08
        bne     L3314
        lda     $9E
        sta     $5F
        lda     #$B0
        sta     $5B
        lda     $9F
        sta     $6D
        lda     $A2
        sta     $65
        lda     $A0
        sta     ptr2
        lda     $A1
        sta     ptr2_hi
        jmp     cmd_end

L3314:  jsr     set_mode0
        lda     $6D
        and     #$04
        bne     L3320
        jmp     parse_fail

L3320:  lda     $6D
        and     #$08
        beq     L332C
L3326:  jsr     rec_store_here
        jmp     next_phrase

L332C:  lda     $5B
        pha
        lda     $6D
        pha
        lda     adr
        pha
        lda     adr_hi
        pha
        lda     $5F
        pha
L333B:  jsr     next_token
        cmp     #$00
        beq     L333B
        lda     $6D
        ora     #$01
        sta     $6D
        lda     $5B
        cmp     #$20
        beq     L3360
        pla
        sta     $5F
        pla
        sta     adr_hi
        pla
        sta     adr
        pla
        sta     $6D
        pla
        sta     $5B
        jmp     L3326

L3360:  jsr     rec_store_here
        pla
        pla
        sta     adr_hi
        pla
        sta     adr
        pla
        pla
        ldx     $02
        jsr     rec_store_at
        jmp     next_phrase

; Article/determinant (classe 8 : THE, A...) : simple annonce d'un nom ;
; passe aussitot au mot suivant.
cls_article:
        lda     $6D                             ; classe 8 ($80) : article/determinant (THE, A...)
        and     #$EF
        sta     $6D
        jmp     dispatch

; IN/INTO (classe 1) : preposition de lieu ; peut basculer en verbe de
; deplacement (GO) selon le mot precedent.
cls_prep_in:
        lda     $6D                             ; classe 1 ($10) : IN / INTO
        and     #$04
        beq     L338C
        lda     $5A
        cmp     #$A0
        bne     L338C
        jmp     L32EF

L338C:  lda     #$70
        sta     $5B
; Preposition (classe 7 : ON, WITH, THROUGH...) : separe le sujet de son
; complement dans le groupe nominal.
cls_preposition:
        jsr     noun_prep_count                 ; classe 7 ($70) : preposition (ON, THROUGH, WITH...)
L3393:  jsr     next_token
        cmp     #$70
        beq     cls_preposition
        cmp     #$80
        bne     L33B0
        lda     $6D
        and     #$10
        bne     L33A7
        jmp     parse_fail

L33A7:  lda     $6D
        and     #$EF
        sta     $6D
        jmp     L3393

L33B0:  cmp     #$60
        beq     cls_adjective
        cmp     #$50
        beq     cls_noun
        lda     $60
        sta     $5F
        jmp     L33D0

; Adjectif (classe 6) : ajoute un qualificatif au groupe nominal courant
; (sert a lever l'ambiguite entre plusieurs objets).
cls_adjective:
        jsr     noun_slot_set6                  ; classe 6 ($60) : adjectif
        jsr     next_token
        jmp     L33B0

; Nom (classe 5) : memorise le nom courant (objet, creature ou lieu) dans le
; groupe nominal et l'enregistrement de commande, en tenant compte de la
; portee EXCEPT.
cls_noun:
        lda     adr                             ; classe 5 ($50) : nom (objet, creature, lieu)
        sta     $A7
        lda     adr_hi
        sta     $A8
L33D0:  lda     #$50
        sta     $5B
        lda     $6E
        cmp     #$02
        bne     L3403
        lda     $A3
        ora     $A4
        bne     L3400
        jsr     rec_prev
        ldy     #$01
        lda     (ptr2),y
        pha
        jsr     rec_next
        pla
        bne     L33F4
        jsr     rec_next
        jsr     rec_clear
L33F4:  jsr     noun_store_adj
        ldy     #$01
        lda     #$40
        sta     (ptr2),y
L33FD:  jmp     next_phrase

L3400:  jsr     rec_back_mode0
L3403:  jsr     noun_slot_put
        beq     L33FD
        lda     #$01
        rts

; Cherche un emplacement libre du groupe nominal a partir de l'offset 6 et y range l'adresse du mot
noun_slot_set6:
        ldx     #$06
L340D:  lda     $A3,x
        inx
        ora     $A3,x
        beq     L341F
        inx
        lda     $A3,x
        inx
        ora     $A3,x
        beq     L341F
        jmp     parse_fail_pop

L341F:  lda     adr_hi
        sta     $A3,x
        dex
        lda     adr
        sta     $A3,x
        rts

; Compteur de prepositions ($9D) : +1, echoue au-dela de 2, sinon cherche un emplacement
noun_prep_count:
        ldx     $9D
        inx
        stx     $9D
        cpx     #$03
        bcc     L3435
        jmp     parse_fail_pop

L3435:  ldx     #$00
        jmp     L340D

; Range le groupe nominal courant dans l'enregistrement de commande (offset selon $6D) ou echoue
noun_slot_put:
        lda     $6D
        and     #$40
        bne     noun_store_adj
        lda     $6D
        and     #$80
        bne     L3449
        jmp     parse_fail_pop

L3449:  lda     $6D
        and     #$7F
        sta     $6D
        ldx     #$0E
L3451:  tya
        pha
        txa
        tay
        ldx     #$00
L3457:  lda     $A3,x
        sta     (ptr2),y
        inx
        iny
        cpx     #$0A
        bne     L3457
        pla
        tay
        lda     #$00
        rts

; Range le groupe nominal courant a l'offset 4 de l'enregistrement (cas adjectif)
noun_store_adj:
        lda     $6D
        and     #$BF
        sta     $6D
        ldx     #$04
        jmp     L3451

; Grammaire : revient a la proposition precedente en mode normal
rec_back_mode0:
        jsr     rec_rewind
; Grammaire : quitte le mode ALL/EXCEPT, revient au normal
set_mode0:
        lda     #$00
        sta     $6E
        rts

; Grammaire : efface la proposition en cours pour la reecrire
rec_clear:
        ldy     #$00
        lda     #$00
L347D:  sta     (ptr2),y
        iny
        cpy     #$1A
        bne     L347D
        rts

; QUOI : lit le mot suivant de la phrase du joueur (verbe, nom, fin...).
; ENTREE : curseur $5F dans $4783 ; SORTIE : $5A ex-mot, $5B mot courant, adr sa fiche, A = $5B.
; COMMENT : octet 0 = nature (haut) + page (bas), octet 1 = octet bas ; avance $5F de 2.
next_token:
        ldx     $5F
        stx     $60
        lda     $5B
        sta     $5A
        lda     L4783,x
        and     #$0F
        sta     adr_hi
        lda     L4783,x
        and     #$F0
        sta     $5B
        inx
        lda     L4783,x
        sta     adr
        inx
        stx     $5F
        lda     $5B
        rts

; Propositions : revient en arriere et compte une proposition de moins
rec_prev_dec:
        dec     $6C
; Propositions : revient a la premiere proposition de la commande
rec_rewind:
        lda     ptr2
        sta     ptr
        lda     ptr2_hi
        sta     ptr_hi
; Propositions : recule jusqu'a la premiere (ex. TAKE A AND B -> TAKE A)
rec_rewind_loop:
        jsr     rec_prev
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     rec_rewind_loop
        rts

; Propositions : recule d'une proposition (24 octets)
rec_prev:
        lda     ptr2
        sec
        sbc     #$18
        sta     ptr2
        lda     ptr2_hi
        sbc     #$00
        sta     ptr2_hi
        rts

; Propositions : avance d'une proposition et compte une de moins
rec_fwd_dec:
        dec     $6C
        jmp     rec_rewind2

; QUOI : assemble deux bouts de commande (GREEN + DOOR -> GREEN DOOR).
; ENTREE : bout en (ptr), fiche en (ptr2) ; SORTIE : fiche completee.
; COMMENT : reporte le type, recule (rec_prev) puis avance (rec_next) ; si +4/+5
; non nuls, remet l'ordre via rec_fixup1 (echange sujet/complement si bit7 $6D).
rec_merge:
        ldy     #$01                            ; fusionne deux mots en un enregistrement de commande
        lda     (ptr),y
        and     #$7F
        ora     (ptr2),y
        sta     (ptr2),y
        dey
        lda     (ptr),y
        sta     (ptr2),y
        jsr     rec_prev
        ldy     #$04
        lda     (ptr2),y
        iny
        ora     (ptr2),y
        php
        jsr     rec_next
        plp
        bne     rec_fixup1
        rts

; Apres assemblage : remet sujet et complement dans le bon ordre si besoin
rec_fixup1:
        lda     $6D
        and     #$80
        bne     rec_swap6
        rts

; Assemblage : echange objet et complement dans la proposition
rec_swap6:
        ldy     #$08
        ldx     #$00
L34FC:  lda     (ptr2),y
        sta     $A7,x
        iny
        inx
        cpx     #$06
        bne     L34FC
        ldy     #$12
L3509           := * + 1
        ldx     #$00
L350A:  lda     $A7,x
        sta     (ptr2),y
        iny
        inx
        cpx     #$06
        bne     L350A
        ldy     #$04
; Assemblage : recopie un groupe de mots puis verifie qu'il est complet
rec_copy_check:
        jsr     rec_copy10
        ldy     #$02
        lda     (ptr2),y
        iny
        ora     (ptr2),y
        beq     L3523
        rts

L3523:  ldy     #$02
        jsr     rec_copy2
        rts

; Assemblage : recopie un petit groupe de mots (6 octets)
rec_copy6:
        ldx     #$06
        jmp     copy_bytes

; Assemblage : recopie un groupe de mots (10 octets)
rec_copy10:
        ldx     #$0A
        jmp     copy_bytes

; Assemblage : recopie un mot (2 octets)
rec_copy2:
        ldx     #$02
; Assemblage : recopie X octets d'une proposition vers l'autre
copy_bytes:
        lda     (ptr),y
        sta     (ptr2),y
        iny
        dex
        bne     copy_bytes
        rts

; Grammaire : range le mot reconnu dans la proposition en cours
rec_store_here:
        lda     $6D
        and     #$FD
        sta     $6D
        ldx     #$00
; Grammaire : range le mot reconnu a sa place dans la fiche
rec_store_at:
        txa
        tay
        lda     adr
        sta     (ptr2),y
        iny
        lda     adr_hi
        sta     (ptr2),y
        rts

; Phrase refusee : abandonne proprement la commande
parse_fail_pop:
        pla
        pla
; QUOI : phrase incomprise -> le jeu repond WHAT ? et redemande.
; EXEMPLE : joueur tape BLORP. -> WHAT ? puis nouveau prompt '> '.
; COMMENT : saut vers la boucle start ($2D45), sans toucher au monde.
parse_fail:
        jmp     L2D45

        lda     #$01
        rts

; Propositions : repart du debut pour executer la commande validee
rec_rewind2:
        lda     ptr2
        sta     ptr
        lda     ptr2_hi
        sta     ptr_hi
; Propositions : avance jusqu'a la premiere a executer
rec_rewind2_loop:
        jsr     rec_next
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     rec_rewind2_loop
        rts

; Propositions : avance a la proposition suivante (24 octets)
rec_next:
        lda     ptr2
        clc
        adc     #$18
        sta     ptr2
        lda     ptr2_hi
        adc     #$00
        sta     ptr2_hi
        rts

; QUOI : joue l'ordre du joueur (GO NORTH deplace, TAKE LAMP agit).
; EXEMPLE : GO NORTH -> move_begin ; TAKE LAMP -> cmd_probe puis perform_action.
; COMMENT : tente move_begin ($359B), sinon sonde cmd_probe ($36D5) : passok<>0 -> A=0
; (start rejoue en reel : phase=1, describe_room, perform_action) ; passok=0 -> $57=3, A=3
; (start via rev_real $3A2D). $57 : 1 pas une sortie -> WAIT/special_cmd ; 2 partiel ->
; rev_dispatch2 $3A0B ; 3 action -> rev_real.
cmd_run:jsr     move_begin                      ; tente d'abord de traiter la commande comme un deplacement (L359B)
        beq     L3582
        rts

L3582:  jsr     cmd_probe                       ; sinon evalue l'action en sonde (cmd_probe)
        beq     L358A
        lda     #$00
        rts

L358A:  lda     #$03                            ; $57=3 : rien a reviser pour la boucle de start
        sta     $57
        rts

; Deplacement : oublie la tentative precedente avant d'essayer GO NORTH
move_raz:
        lda     #$00
        sta     raw
        ldx     #$10
L3595:  sta     op1,x
        dex
        bpl     L3595
        rts

; QUOI : GO NORTH cherche la sortie NORD parmi les sorties du lieu.
; ENTREE : mot courant ; SORTIE : 1 sortie trouvee (move_go $35AE), 0 sinon ($57=1 -> action).
; EXEMPLE : GO NORTH dans le tunnel -> sortie NORD ; GO UP sans sortie -> action/WHAT ?.
; COMMENT : arg1/arg2=$FF, raz $D7-$E7 ; exit_resolve ($3790) balaye $26E2 par pas de 8 ;
; si trouvee wid := index ($6C), move_flags puis essai sonde (phase=0) puis reel.
move_begin:
        lda     #$FF
        sta     arg2
        sta     arg1
        jsr     move_raz
        jsr     exit_resolve
        bne     move_go
        lda     #$01
        sta     $57
        rts

; Sortie trouvee : tente d'abord pour de faux, puis vraiment si ca passe
move_go:lda     $6C
        sta     wid
        sta     $14
        jsr     move_flags
        jsr     move_saveopt
        lda     #$00
        sta     phase
        lda     xmode
        and     #$0C
        beq     L35E1                           ; xmode & $0C : sortie non directe a reviser ?
        lda     rbit
        sta     $7E
        rol     a
        rol     a
        and     #$01
        sta     ralt
L35CE:  jsr     move_iter
        beq     L35D8
        lda     #$02
        sta     $57
        rts

L35D8:  lda     $7E
        beq     L35E1
        jsr     move_find_obj
        bne     L35CE
L35E1:  lda     #$00
        rts

; Deplacement avec porte (ex. OPEN DOOR) : trouve la porte puis l'ouvre
move_iter:
        jsr     op_resolve1
        bne     move_iter2
        lda     rn2
        cmp     #$01
        beq     L35F0
        rts

L35F0:  lda     rid1
        sta     arg1
        jsr     move_saveptr2
        jsr     move_gate
        bne     move_second
        rts

; Autre porte possible : essaie l'objet-porte suivant (ex. 2e porte)
move_iter2:
        inc     rn1
        jsr     move_gate
        beq     move_iter_none
        jsr     move_saveptr2
        jsr     op_resolve2
L360A:  beq     move_iter
        lda     ralt
        cmp     #$01
        bne     L3613
        rts

L3613:  lda     arg1
        sta     rid1
        inc     rn2
        jmp     move_iter

; Sans porte : joue directement l'action (ex. GO NORTH simple)
move_iter_none:
        jsr     cmd_probe
        jmp     L360A

; Deplacement a 2 objets (ex. GO THROUGH DOOR WITH KEY) : vise le 2e
move_second:
        jsr     op_resolve2
        bne     L3635
        lda     rn3
        cmp     #$01
        beq     L362E
        rts

L362E:  lda     rid2
        sta     arg2
        lda     #$00
        rts

L3635:  lda     arg2
        sta     rid2
        inc     rn3
        jmp     move_second

; Retrouve la porte visee (ex. GREEN DOOR) parmi les objets du jeu
move_find_obj:
        jsr     push_ptr2
L3641:  jsr     rec_next
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        beq     L366E
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
        lda     ptr2
        clc
        adc     #$08
        sta     ptr3
        lda     ptr2_hi
        adc     #$00
        sta     ptr3_hi
L3661:  jsr     cond_match_direct
        cmp     #$FF
        beq     L3641
        cmp     arg1
        bne     L3661
        lda     #$01
L366E:  tax
        jsr     pop_ptr
        txa
        rts

; Deplacement : met de cote la sortie prevue sauf si on annonce deja
move_saveopt:
        lda     $7E
        beq     move_saveptr
        rts

; Deplacement : memorise ou on en est (aller direct)
move_saveptr:
        lda     xaux
        lsr     a
        lsr     a
        jsr     move_pick_tbl
        lda     direct
        beq     L3687
        jsr     cond_match_alt
L3687:  lda     ptr
        sta     svptr
        lda     ptr_hi
        sta     svptr_hi
        rts

; Deplacement : memorise ou on en est (chemin detourne)
move_saveptr2:
        lda     xaux
        jsr     move_pick_tbl
        lda     variant
        beq     L369C
        jsr     cond_match_alt
L369C:  lda     ptr
        sta     $EA
        lda     ptr_hi
        sta     $EB
        rts

; Deplacement : choisit la liste des sorties (normales ou secretes)
move_pick_tbl:
        and     #$03
        beq     L36B2
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
        rts

L36B2:  lda     #$62
        sta     ptr
        lda     #$1A
        sta     ptr_hi
        rts

; Porte : dit si on continue (ouverte) ou si on s'arrete (fermee)
move_gate:
        lda     xmode
        and     #$04
        bne     L36C2
        rts

L36C2:  lda     op2
        and     #$01
        beq     L36C9
        rts

L36C9:  lda     xmode
        and     #$02
        bne     L36D2
        lda     #$01
        rts

L36D2:  lda     #$00
        rts

; QUOI : simule l'ordre sans rien afficher (ex. porte fermee -> ca ne passe pas).
; ENTREE : commande prete ; SORTIE : A = passok (1 ca passe, 0 refuse, alors $57=3).
; COMMENT : rejoue perform_action ($4B37) en phase=0.
cmd_probe:
        jsr     perform_action
        lda     passok
        rts

; QUOI : deplace joueur ou PNJ (GO NORTH) : trouve la sortie, verifie porte/noir, bouge ou refuse.
; EXEMPLE : porte fermee -> YOU CANNOT... ; noir sans lampe -> I SEE NOTHING.
; COMMENT : exit_ptr(wid), flags code_4141, conditions cond1/cond2 via cond_eval,
; essai sonde (L4B37) ou deux temps (L35E4).
move_core:
        lda     svptr
        pha
        lda     svptr_hi
        pha
        lda     exitp
        pha
        lda     exitp_hi
        pha
        jsr     push_ptr
        lda     wid
        jsr     exit_ptr
        jsr     move_raz
        jsr     move_flags_decode
        jsr     move_flags
        ldx     arg1
        lda     direct
        jsr     cond_eval
        beq     L370B
        ldy     #$05
L3703:  lda     (ptr),y
        sta     cond1,y
        dey
        bpl     L3703
L370B:  ldx     arg2
        lda     variant
        jsr     cond_eval
        beq     L371E
        ldy     #$05
L3716:  lda     (ptr),y
        sta     cond2,y
        dey
        bpl     L3716
L371E:  jsr     move_saveptr
        lda     #$00
        sta     phase
        lda     xmode
        and     #$0C
        bne     L3733
        jsr     perform_action
        lda     passok
        jmp     move_core_end

L3733:  lda     #$01
        sta     ralt
        jsr     move_iter
        beq     L3741
        lda     #$00
        jmp     move_core_end

L3741:  lda     #$01
; Deplacement fini : range les pointeurs et dit reussi/refuse
move_core_end:
        tax
        lda     #$01
        sta     phase
        pla
        sta     exitp_hi
        pla
        sta     exitp
        pla
        sta     svptr_hi
        pla
        sta     svptr
        jsr     pop_ptr2
        txa
        rts

; Prepare la condition a remplir pour emprunter une sortie : une sortie peut etre cachee,
; verrouillee, ou dependre d'un objet. S'il n'y a pas de condition (X = $FF), rien a verifier.
; Technique : A = drapeau direct ; 0 -> fiche du lieu (etat+8, L43F3), sinon fiche de l'objet
; (record+2, L43E4). Renvoie A=1 (Z clair) si une condition existe.
cond_eval:
        cpx     #$FF
        bne     L375E
        rts

L375E:  and     #$FF
        beq     L3769
        txa
        jsr     room_cond_ptr
        lda     #$01
        rts

L3769:  txa
        jsr     obj_cond_ptr
        lda     #$01
        rts

; Range les options de la sortie sous forme de drapeaux simples (sortie directe ou en
; variante) que la suite du deplacement consultera.
; Technique : direct = bit7 de xmode, variant = bit6, $7F = bit6 de xaux, $80 = bit0 de xmode.
move_flags:
        lda     xaux
        and     #$40
        sta     $7F
        lda     xmode
        tax
        and     #$01
        sta     $80
        txa
        and     #$80
        beq     L3784
        lda     #$01
L3784:  sta     direct
        txa
        and     #$40
        beq     L378D
        lda     #$01
L378D:  sta     variant
        rts

; QUOI : prepare verbe+objets puis localise la sortie (ex. NORD) du lieu.
; ENTREE : fiche commande 24 o a (ptr2) ; SORTIE : 1 sortie trouvee ($6C = index), 0 sinon.
; COMMENT : octet 0 -> $F2, octet 1 -> $EC/$F3, paires via op_copy_pair ($F4-$F7) ; balaye
; $26E2 par pas de 8, signature testee par code_433A, arret a la 1re qui correspond.
exit_resolve:
        ldy     #$01
        lda     (ptr2),y
        and     #$80
        sta     rbit
        lda     (ptr2),y
        and     #$7F
        sta     rword_hi
        dey
        lda     (ptr2),y
        sta     rword
        ldx     #$03
        lda     #$00
L37A7:  sta     rarg1,x                         ; raz des operandes $F4-$F7
        dex
        bpl     L37A7
        ldx     #$00
        lda     #$02
        sta     $6C
        ldy     #$04
        jsr     op_copy_pair                    ; copie des paires d'operandes (y=4/$0E/6/$10)
        ldy     #$0E
        jsr     op_copy_pair
        ldy     #$06
        jsr     op_copy_pair
        ldy     #$10
        jsr     op_copy_pair
        lda     #$00
        sta     $79
        lda     #$E2                            ; exitp = $26E2 : debut de la table des sorties du lieu
        sta     exitp
        lda     #$26
        sta     exitp_hi
        lda     #$01                            ; $6C = 1 : index de sortie
        sta     $6C
        lda     #$F2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
; Passe les sorties du lieu en revue (NORD, SUD...) jusqu'a la bonne
exit_scan:
        lda     exitp
        sta     $7C
        lda     exitp_hi
        sta     $7D
        jsr     exit_sig_match                  ; code_433A : la sortie correspond-elle au mot courant ?
        beq     exit_found                      ; correspond -> exit_found ; sinon sortie suivante
        lda     exitp
        clc
        adc     #$08
        sta     exitp
        lda     exitp_hi
        adc     #$00
        sta     exitp_hi
        inc     $6C                             ; index de sortie +1
        ldy     #$00
        lda     (exitp),y
        iny
        ora     (exitp),y
        bne     exit_scan
        rts

; Bonne sortie trouvee : prepare ses objets et continue
exit_found:
        jsr     exit_build_args
        lda     #$01
        rts

; Sortie : prepare ses 2 conditions (ex. porte fermee + cle) et leurs places
exit_build_args:
        txa
        beq     L381C
        ldx     #$01
L380F:  lda     rarg1,x
        tay
        lda     rarg2,x
        sta     rarg1,x
        tya
        sta     rarg2,x
        dex
        bpl     L380F
L381C:  jsr     move_flags_decode
        lda     rarg1
        ora     rarg1_hi
        bne     L382A
        lda     xaux
        jmp     exit_arg_swap

L382A:  lda     rarg1
        ldy     #$0E
        cmp     (ptr2),y
        bne     L3839
        iny
        lda     rarg1_hi
        cmp     (ptr2),y
        beq     L3846
L3839:  lda     rarg1
        ldy     #$10
        cmp     (ptr2),y
        bne     L3846
        iny
        lda     rarg1_hi
        cmp     (ptr2),y
L3846:  bne     L384F
        lda     xmode
; Conditions : remet objet et complement dans le bon ordre
exit_arg_swap:
        eor     #$20
        jmp     exit_arg_mix

L384F:  lda     xmode
; Conditions : ajuste l'ordre pour les sorties detournees
exit_arg_mix:
        and     #$20
        beq     L3860
        lda     #$08
        sta     roff1
        lda     #$12
        sta     roff2
        jmp     exit_arg_load

L3860:  lda     #$12
        sta     roff1
        lda     #$08
        sta     roff2
; Conditions : charge ce qu'exige la sortie (ex. porte, cle)
exit_arg_load:
        ldy     roff1
        ldx     #$05
        lda     #$00
        jsr     op_load_cond
        bne     L3882
        lda     $6C
        cmp     #$35
        bne     L3882
        ldx     #$05
L387B:  lda     $97,x
        sta     cond1,x
        dex
        bpl     L387B
L3882:  ldx     #$05
L3884:  lda     cond1,x
        sta     $82,x
        dex
        bpl     L3884
        lda     $6C
        cmp     #$35
        bne     L389A
        ldx     #$05
L3893:  lda     cond1,x
        sta     $97,x
        dex
        bpl     L3893
L389A:  ldy     roff2
        ldx     #$0B
        lda     #$01
; Conditions : recopie ce qu'exige la sortie vers la zone de travail
op_load_cond:
        pha
        lda     #$06
L38A3:  pha
        lda     (ptr2),y
        sta     op1,x
        inx
        iny
        pla
        sec
        sbc     #$01
        bne     L38A3
        ldy     #$06
        lda     #$00
L38B4:  dex
        ora     op1,x
        dey
        bne     L38B4
        cmp     #$00
        bne     L38C0
        pla
        rts

L38C0:  pla
        tax
        lda     op1,x
        ora     #$01
        sta     op1,x
        rts

; Commande : recopie un couple verbe+objet (mot + precision)
op_copy_pair:
        dec     $6C
        bpl     L38CE
        rts

L38CE:  lda     (ptr2),y
        sta     rarg1,x
        iny
        inx
        lda     (ptr2),y
        sta     rarg1,x
        dey
        dex
        ora     (ptr2),y
        bne     L38DF
        rts

L38DF:  inx
        inx
        rts

; Test : appelle le bon comparateur (direct ou detourne)
op_stub:
L38E3           := * + 1
L38E4           := * + 2
        jmp     L0000

; Boucle de resolution du 1er operande d'une commande a objets. Le stub
; auto-modifie op_stub ($38E2) pointe le matcher adequat ($53C3 direct ou
; $54F8 variante), puis pour chaque candidat de la table de travail $00DC :
; pose l'id dans arg1 et rejoue l'action via cmd_probe jusqu'a ce qu'elle
; passe (passok). op_resolve2 ($3948) fait de meme pour le 2e operande
; (table $00E2).
op_resolve1:
        jsr     push_ptr2
        lda     svptr
        sta     ptr
        lda     svptr_hi
        sta     ptr_hi
        lda     direct
        cmp     #$01                            ; direct ? choisit le matcher ($53C3 ou $54F8)
        beq     L391B
        lda     #$C3
        sta     L38E3
        lda     #$53
        sta     L38E4
        lda     xaux
        ror     a
        ror     a
        and     #$03
        sta     $81
; Essaie chaque 1er objet possible (sauve puis restaure la position)
op_loop1:
        jsr     op_step1
        pha
        lda     ptr
        sta     svptr
        lda     ptr_hi
        sta     svptr_hi
        jsr     pop_ptr
        pla
        cmp     #$FF
        rts

L391B:  lda     #$F8
        sta     L38E3
        lda     #$54
        sta     L38E4
        jmp     op_loop1

; Essaie un 1er objet (ex. GREEN DOOR) : verifie puis rejoue l'action
op_step1:
        lda     #$DC
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     op_stub
        cmp     #$FF
        bne     L3938
        rts

L3938:  sta     arg1                            ; candidat retenu : arg1 := id, rejoue l'action
        lda     op1
        ora     #$02
        sta     op1
        jsr     action_probe
        lda     passok
        beq     op_step1
        rts

; Trouve le bon 2e objet (ex. laquelle des cles) en les essayant
op_resolve2:
        jsr     push_ptr2
        lda     #$00
        sta     $80
        lda     $EA
        sta     ptr
        lda     $EB
        sta     ptr_hi
        lda     variant
        cmp     #$01
        beq     L3986
        lda     #$C3
        sta     L38E3
        lda     #$53
        sta     L38E4
        lda     xaux
        and     #$03
        sta     $81
; Essaie chaque 2e objet possible
op_loop2:
        jsr     op_step2
        pha
        lda     ptr
        sta     $EA
        lda     ptr_hi
        sta     $EB
        lda     xmode
        and     #$01
        sta     $80
        jsr     pop_ptr
        pla
        cmp     #$FF
        rts

L3986:  lda     #$F8
        sta     L38E3
        lda     #$54
        sta     L38E4
        jmp     op_loop2

; Essaie un 2e objet (ex. BRASS KEY) : verifie puis rejoue l'action
op_step2:
        lda     #$E2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     op_stub
        cmp     #$FF
        bne     L39A3
        rts

L39A3:  sta     arg2                            ; candidat retenu : arg2 := id, rejoue l'action
        lda     op2
        ora     #$02
        sta     op2
        jsr     cmd_probe
        beq     op_step2
        rts

; Action : affiche son message final en mode reel (ex. YOU TAKE...)
print_spc:
        jsr     set_real
        jmp     probe_flag_end

; Action : repasse en vrai affichage avant de jouer l'effet
set_real:
        lda     #$01
        sta     raw
        sta     phase
        rts

; Action : recopie verbe+objets vers la zone de l'effet a jouer
vm_arg_set:
        sta     $57
        tya
        pha
        ldy     #$17
L39C4:  lda     (ptr2),y
        sta     L490F,y
        dey
        bpl     L39C4
        pla
        tay
        rts

; Action : prepare un objet, montre son message, puis continue
rev_1:  lda     roff1
        ldy     #$05
; Action : recopie un objet mot a mot vers l'effet a jouer
rev_1_loop:
        jsr     vm_arg_set
        ldx     #$00
        lda     op1,y
        sta     L466F,x
        inx
        iny
        lda     op1,y
        sta     L466F,x
        jsr     print_spc
        ldy     crcnt
        lda     #$01
        rts

; Apres essai : aiguille selon l'etat du 2e objet (reussi, porte, echec)
rev_dispatch:
        lda     op2
        and     #$01
        bne     L39F7
        jmp     rev_exec1

L39F7:  lda     op2
        and     #$02
        beq     rev_obj2
        lda     rn3
        bne     L3A04
        jmp     rev_real

L3A04:  lda     roff2
        ldy     #$0B
        jmp     rev_1_loop

; Aiguillage de revision d'une commande classee 'partielle' (start y arrive
; via $57=2). Selon les etats $D7/$D8 et les compteurs $D9/$DA/$DB : tente
; une nouvelle resolution d'objet (rev_obj1 $3A6B / rev_obj2 $3A36),
; reaiguille vers rev_dispatch ($39EE), ou execute pour de bon
; (rev_real $3A2D).
rev_dispatch2:
        lda     rn2
        cmp     #$01
        beq     rev_dispatch
        lda     op1                             ; etat du 1er operateur ($D7 bit0)
        and     #$01
        bne     L3A1A
        jmp     rev_exec2

L3A1A:  lda     op1
        and     #$02                            ; etat du 2e operateur ($D7 bit1)
        beq     rev_obj1
        lda     rn1
        beq     rev_real
        cmp     #$01
        bne     rev_1
        jsr     move_gate
        bne     rev_dispatch
; Essai reussi : rejoue l'action vraiment (ex. YOU GO NORTH)
rev_real:
        jsr     set_real
        jsr     perform_action                  ; rejoue l'action en mode reel
        lda     #$00
        rts

; 2e objet flou (ex. KEY) : precise lequel puis rejoue l'action
rev_obj2:
        jsr     cond_match_alt
        lda     #$01
        sta     variant
        lda     #$E2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     cond_match_var
        cmp     #$FF
        bne     L3A63
        lda     #$02
        sta     $81
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
        lda     #$00
        sta     variant
        jsr     cond_match_direct
        cmp     #$FF
        beq     L3AA0
L3A63:  sta     arg2
        jsr     move_run_real
        lda     #$01
        rts

; 1er objet flou (ex. DOOR) : precise lequel puis rejoue l'action
rev_obj1:
        jsr     cond_match_alt
        lda     #$01
        sta     direct
        lda     #$DC
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     cond_match_var
        cmp     #$FF
        bne     L3A98
        lda     #$02
        sta     $81
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
        lda     #$00
        sta     direct
        jsr     cond_match_direct
        cmp     #$FF
        beq     L3AA0
L3A98:  sta     arg1
        jsr     move_run_real
        lda     #$01
        rts

L3AA0:  jsr     set_real
        lda     ptr3
        sta     L466F
        lda     ptr3_hi
        sta     L4670
        jsr     probe_flag_end
        tax
        ora     ($A9),y
        ora     ($60,x)
; Action : prepare ses objets (variante detournee) puis joue l'effet
rev_exec2:
        ldx     #$00
        lda     rword
        sta     L466F,x
        inx
        lda     rword_hi
        sta     L466F,x
        inx
        jsr     rev_sel_hi
        lda     rn2
        bne     L3AD2
        jsr     print_spc
        clv
        ora     ($A9),y
        ora     ($60,x)
L3AD2:  lda     roff1
        jsr     vm_arg_set
        jsr     print_spc
        .byte   $9C
code_3ADB:
        ora     ($A9),y
        ora     ($60,x)
; Action : prepare ses objets (chemin direct) puis joue l'effet
rev_exec1:
        ldx     #$00
        lda     rword
        sta     L466F,x
        inx
        lda     rword_hi
        sta     L466F,x
        inx
        jsr     rev_sel_hi
        txa
        pha
        lda     arg1
        jsr     obj_cond_ptr
        pla
        tax
        lda     ptr
        sta     L466F,x
        inx
        lda     ptr_hi
        sta     L466F,x
        inx
        jsr     rev_sel_lo
        lda     rn3
        bne     L3B14
        jsr     print_spc
        ldx     $A911,y
        ora     ($60,x)
L3B14:  lda     roff2
        jsr     vm_arg_set
        jsr     print_spc
        tya
        ora     ($A9),y
        ora     ($60,x)
; Effet : prend les 2 derniers mots dans le bas du jeu
rev_sel_lo:
        lda     #$F0
        jmp     rev_sel

; Effet : prend les 2 derniers mots dans le haut du jeu
rev_sel_hi:
        lda     #$D0
; Effet : ajoute si besoin 2 mots de la sortie (ex. condition cachee)
rev_sel:sta     L3B34
        sta     L3B58
        ldy     #$03
        lda     (exitp),y                       ; octet +3 de la sortie (bit5) : ajoute 2 mots d'argument
        and     #$20
L3B34:  bne     L3B43
        lda     #$00
        sta     L466F,x
        inx
        sta     L466F,x
        inx
        jmp     rev_sel2

L3B43:  ldy     #$02
        lda     (exitp),y
        sta     L466F,x
        inx
        iny
        lda     (exitp),y
        sta     L466F,x
        inx
; Effet : ajoute la 2e moitie cachee de la condition de sortie
rev_sel2:
        ldy     #$07
        lda     (exitp),y
        and     #$80
L3B58:  bne     L3B65
        lda     #$00
        sta     L466F,x
        inx
        sta     L466F,x
        inx
        rts

L3B65:  ldy     #$04
        lda     (exitp),y
        sta     L466F,x
        inx
        iny
        lda     (exitp),y
        sta     L466F,x
        inx
        rts

; QUOI : ordres speciaux (SAVE/LOAD/QUIT/HELP/SCORE/PAUSE/ALL/EXCEPT/IT...).
; EXEMPLE : SCORE -> YOU HAVE MASTERED...% ; SAVE -> ecrit la cassette.
; COMMENT : compare adr a table $3BC6 (13 cles) puis saute via $3BE0 ; court-circuite $7014.
special_cmd:
        lda     rword
        sta     L466F
        lda     rword_hi
        sta     L4670
        lda     rarg1
        sta     L4671
        lda     rarg1_hi
        sta     L4672
        lda     rarg2
        sta     L4673
        lda     rarg2_hi
        sta     L4674
        jsr     print_spc
        dey
        ora     ($A9),y
        ora     ($60,x)
        ldy     #$0D                            ; classe 9 ($90) : mot-cle special (SAVE/QUIT/HELP/ALL/EXCEPT...)
        ldx     #$00
L3B9F:  lda     adr                             ; compare l'adresse du mot (adr) a la table $3BC6 (classe 9)
        cmp     L3BC6,x
        bne     L3BAF
        lda     adr_hi
        and     #$0F
        cmp     L3BC7,x
        beq     L3BB7
L3BAF:  inx
        inx
        dey
        bne     L3B9F
        jmp     next_word                       ; aucun mot-cle reconnu -> mot suivant

L3BB7:  lda     L3BE0,x                         ; trouve -> cible lue dans $3BE0, saut indirect via $3BC4
        sta     L3BC4
        lda     L3BE1,x
        sta     L3BC5
L3BC4           := * + 1
L3BC5           := * + 2
        jmp     L0000

L3BC6:  .byte   $00
L3BC7:  .byte   $00,$85,$00,$A3,$03,$B5,$05,$84
        .byte   $07,$0B,$08,$3F,$07,$3D,$06,$A0
        .byte   $08,$28,$08,$23,$05,$AA,$08,$C2
        .byte   $07
L3BE0:  .byte   $4E
L3BE1:  .byte   $3C,$26,$3C,$0E,$3C,$33,$3C,$35
        .byte   $31,$FA,$3B,$03,$3C,$7F,$3D,$D9
        .byte   $3D,$88,$3C,$8E,$3C,$CE,$3C
code_3BF8:
        and     $203D,y
        php
        bit     $08D0
        lda     #$01
        bne     L3C05
        lda     #$00
L3C05:  sta     $0A
L3C07:  lda     $5A
        sta     $5B
        jmp     next_phrase

        lda     $6E
        cmp     #$01
        beq     L3C17
        jmp     parse_fail

L3C17:  lda     #$02
        sta     $6E
        ldy     #$01
        lda     (ptr2),y
        ora     #$80
        sta     (ptr2),y
        jmp     next_phrase

        lda     $6E
        cmp     #$02
        beq     L3C30
        lda     #$01
        sta     $6E
L3C30:  jmp     next_phrase

        ldx     #$05
L3C35:  lda     $82,x
        sta     $A7,x
        dex
        bpl     L3C35
        lda     $6D
        and     #$80
        jsr     one_flag_store
        jmp     next_phrase

; IT/ONE : selon le bit7 de $6D, range le groupe nominal a l'offset 4 ou $0E
one_flag_store:
        beq     L3C4B
        jmp     noun_store_adj

L3C4B:  jmp     L3449

        ldy     #$00
        lda     (ptr2),y
        bne     L3C6A
        iny
        lda     (ptr2),y
        and     #$0F
        bne     L3C6A
        lda     #$0A
        sta     (ptr2),y
        dey
        lda     #$55
        sta     (ptr2),y
        lda     $6D
        and     #$FD
        sta     $6D
L3C6A:  lda     $5F
        ldx     qwr
        sta     L4905,x
        inc     qwr
L3C73:  jsr     next_token
        cmp     #$90
        bne     L3C73
        lda     adr
        ora     adr_hi
        bne     L3C73
        lda     #$C0
        sta     L4781,x
        jmp     next_phrase

        .byte   " "
        .byte   $D4
        .byte   "<"
code_3C8B:
        jmp     L2C3D

        lda     obj
        beq     L3C95
        jmp     next_phrase

L3C95:  jsr     push_ptr_ax
        ldx     #$85
        ldy     #$71
        lda     ploc
        jsr     index_id_table
        beq     L3CBF
        ldy     #$01
        lda     (ptr),y
        sta     msg_3CB7
        iny
        lda     (ptr),y
        sta     msg_3CB7+1
        lda     #$01
        sta     raw
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : entree lue dans la table $7185 (IT/ONE)
msg_3CB7:
        .word   $0000
code_3CB9:
        jsr     fetch_retaddr
        jmp     L3C07

L3CBF:  lda     #$01
        sta     raw
        jsr     print_msg
; -> $179D YOU'RE DO FINE.
msg_3CC6:
        .word   $179D
code_3CC8:
        jsr     fetch_retaddr
        jmp     L3C07

        jsr     score_show
        jmp     L3C07

; SCORE : affiche 'YOU HAVE MASTERED' puis le pourcentage du score (code_3CE0)
score_show:
        jsr     push_ptr_ax
        lda     #$00
        sta     raw
        jsr     print_msg
; -> $178A YOU HAVE MASTERED
msg_3CDE:
        .word   $178A
code_3CE0:
        lda     $CC
        sta     ptr
        lda     $CD
        sta     ptr_hi
        lda     #$64
        jsr     score_digit
        beq     L3CF2
        jsr     putchar
L3CF2:  lda     #$0A
        jsr     score_digit
        jsr     putchar
        lda     #$2E
        jsr     putchar
        lda     ptr
        clc
        adc     #$30
        jsr     putchar
        lda     #$00
        sta     cap
        jsr     print_msg
; -> $1798 %OF THIS ADVENTURE
msg_3D0E:
        .word   $1798
code_3D10:
        jmp     fetch_retaddr

L3D13:  .byte   $D5
; SCORE : extrait un chiffre decimal d'un compteur BCD par soustractions repetees
score_digit:
        ldx     #$2F
        sta     L3D13
L3D19:  inx
        sec
        lda     ptr
        sbc     L3D13
        sta     ptr
        lda     ptr_hi
        sbc     #$00
        sta     ptr_hi
        bcs     L3D19
        lda     ptr
        adc     L3D13
        sta     ptr
        bcc     L3D35
        inc     ptr_hi
L3D35:  txa
        cpx     #$30
        rts

        jsr     keyin
        jmp     L3C07

; Passage vers une routine cassette : lit ses parametres ecrits apres l'appel
tape_tramp:
        pla
        clc
        adc     #$01
        sta     L006A
        pla
        adc     #$00
        sta     $6B
        pla
        sta     $8C
        pla
        sta     $8D
        lda     $8C
        clc
        adc     #$04
        tax
        lda     $8D
        adc     #$00
        pha
        txa
        pha
        ldy     #$04
L3D5F:  lda     ($8C),y
        sta     $87,y
        dey
        bne     L3D5F
        jmp     (L006A)

; LOAD : charge un bloc via tape_tramp et vec_02 ; en echec affiche TAPE LOADING ERROR
load_block:
        jsr     tape_tramp
        jsr     vec_02
        bcs     L3D73
        rts

L3D73:  lda     #$01
        sta     raw
        jsr     print_msg
; -> $3E26 TAPE LOADING ERROR :- PRESS ANY KEY TO RESTART GAME.
msg_3D7A:
        .word   $3E26
code_3D7C:
        jmp     L2C3D

; Commande LOAD : demande une touche puis charge un bloc depuis la cassette
load_game:
        jsr     push_ptr
        jsr     vec_05
        jsr     load_block
        clc
        brk
        .byte   $BE,$00
        .byte   " j=V"
        .byte   $05,$1A,$1B
        .byte   " j="
        .byte   $F1,$02,$CC
        .byte   "( j="
        .byte   $C8,$05,$1A
        .byte   "! "
        .byte   $1D
        .byte   ", "
        .byte   $1B
        .byte   "GL"
        .byte   $07
        .byte   "<"
; Ecrit un bloc sur la cassette (parametres ecrits apres l'appel)
save_block:
        jsr     tape_tramp
        jsr     vec_03
        bcs     L3DB3
        rts

L3DB3:  lda     #$01
        sta     raw
        jsr     print_msg
; -> $1A1A TAPE SAVING ERROR:-PRESS ANY KEY TO CONTINUE.
msg_3DBA:
        .word   $1A1A
; Echec de SAVE : affiche l'erreur, attend une touche puis abandonne
save_err:
        jsr     keyin
        pla
        pla
        jmp     cmd_next

        jsr     tape_tramp
        jsr     vec_04
        bcs     L3DCD
        rts

L3DCD:  lda     #$01
        sta     raw
        jsr     print_msg
; -> $1A38 TAPE VERIFICATION ERROR:-PRESS ANY KEY TO CONTINUE.
msg_3DD4:
        .word   $1A38
code_3DD6:
        jmp     save_err

; Commande SAVE : ecrit les 4 blocs du jeu puis verifie la cassette
save_game:
        jsr     push_ptr
        jsr     vec_06
        jsr     save_block
        clc
        brk
        .byte   $BE,$00,$20,$AA,$3D,$56,$05,$1A
        .byte   $1B,$20,$AA,$3D,$F1,$02,$CC,$28
        .byte   $20,$AA,$3D,$C8,$05,$1A,$21,$20
        .byte   $20,$2C,$20,$1A,$2C,$20,$C4,$3D
        .byte   $18,$00,$BE,$00,$20,$C4,$3D,$56
        .byte   $05,$1A,$1B,$20,$C4,$3D,$F1,$02
        .byte   $CC,$28,$20,$C4,$3D,$C8,$05,$1A
        .byte   $21,$20,$23,$2C
; Termine la commande courante et revient a la boucle de commandes
cmd_next:
        jsr     pop_ptr2
        jmp     L3C07

        .byte   "TAPE LOADING ERROR :- PRESS ANY KEY TO RESTART GAME."
        .byte   $14
; Retire la prochaine action de la file $4905 (curseurs qrd/qwr $D1/$D2) : place son
; indice-token en $91, avance qrd et, selon arg1, marque la fin de la commande dans
; la file de tokens $4783. Appelee en fin d'action (L5FA0).
actq_pull:
        cmp     #$00
        php
        lda     qwr
        beq     L3E88
        cmp     qrd
        beq     L3E88
        ldx     qrd
        lda     L4905,x
        sta     $91
        inx
        stx     qrd
        lda     arg1
        plp
        php
        bne     L3E8A
        lda     $91
        sta     $5F
L3E7A:  jsr     next_token
        cmp     #$C0
        bne     L3E7A
        ldx     $60
        lda     #$90
        sta     L4783,x
L3E88:  lda     #$00
L3E8A:  sta     $90
        plp
        rts

; Parcours la liste de candidats d'errance $48D3 (entrees de 5 octets [id, poids,
; etat, lo, hi]) : rend A = $90/obj si le personnage courant y figure, A = 1 sinon.
; Sert a savoir si un PNJ est deja en cours de planification de deplacement.
cand_check:
        lda     $90
        cmp     obj
        bne     wander_reset
L3E94:  rts

; Moteur d'errance : remet a zero les index de parcours (X/Y) avant le balayage
wander_reset:
        ldx     #$00
        ldy     #$00
L3E99:  lda     L48D3,x
        cmp     obj
        beq     L3E94
        tya
        clc
        adc     L48D4,x
        tay
        txa
        clc
        adc     #$05
        tax
        cpx     #$32
        bne     L3E99
        lda     #$01
        rts

; Coeur du moteur d'errance. Prologue : $5F := $91 (curseur de tokens), ptr2 := $4927
; (enregistrements de commande), $65 := 0 et macc (accumulateur de poids) := 0, puis
; entre dans la boucle d'evaluation wander_eval ($3EC4). Le plan retenu est range dans
; les candidats $48D3 (entrees de 5 o [id, poids, etat, lo, hi]) et les commandes sont
; empilees dans $47E3. Passe ensuite la main a wander_step.
wander_core:
        lda     $91
        sta     $5F
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        lda     #$00
        sta     $65
        sta     macc
; Boucle d'evaluation : parse_cmd consomme la commande suivante de la file de tokens
; (curseur $5F) et la range dans l'enregistrement de commande courant ; $65 recoit son
; nombre de mots retenus (son poids). A=0 (commande construite) ou A=2 poursuivent en
; $3ED0 ; tout autre retour (A=1, 'WHAT ?') abandonne le plan ($3FCF).
wander_eval:
        jsr     parse_cmd
        beq     wander_accum
        cmp     #$02
        beq     wander_accum
        jmp     L3FCF

; Cumul et fin de file : ajoute le poids de la commande a macc (macc += $65), remet $65
; a zero, puis regarde le prochain token de $4783 : tant qu'il n'est pas de type $C0
; (fin de commande) la boucle wander_eval continue ; sinon ce token est marque $90 et le
; budget mwt est arme a $0A avant la recherche de slot.
wander_accum:
        lda     $65
        clc
        adc     macc
        sta     macc
        lda     #$00
        sta     $65
        ldx     $5F
        lda     L4783,x
        and     #$F0
        cmp     #$C0
        bne     wander_eval
        lda     #$90
        sta     L4783,x
        lda     #$0A
        sta     mwt
        ldx     #$00
; Recherche de slot candidat : parcourt les 10 entrees de $48D3 (pas de 5 octets). Pour
; chaque candidat deja retenu, soustrait son poids (L48D4,x) du budget mwt afin de
; reserver la place ; le premier octet d'id nul marque le slot libre -> $3F0A. Sans slot
; libre au bout des 10, le plan est abandonne ($3FCF).
wander_slot:
        lda     L48D3,x
        beq     wander_budget
        lda     mwt
        sec
        sbc     L48D4,x
        sta     mwt
        txa
        clc
        adc     #$05
        tax
        cpx     #$32
        bne     wander_slot
        jmp     L3FCF

; Controle de budget : si mwt (budget restant apres reservation des autres candidats)
; est nul, il n'y a plus de place -> abandon ($3FCF) ; sinon, prepare le comptage.
wander_budget:
        lda     mwt
        bne     wander_count_init
        jmp     L3FCF

; Initialisation du comptage : vide l'etat du slot libre (L48D5,x := 0), remet mcnt et
; $65 a zero, memorise macc dans $6C (nombre total de commandes en file) et replace
; ptr2 sur la base des enregistrements de commande $4927.
wander_count_init:
        lda     #$00
        sta     L48D5,x
        sta     mcnt
        sta     $65
        lda     macc
        sta     $6C
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
; Comptage des enregistrements : avance d'un enregistrement (rec_next ; saute les
; chaines marquees par le bit $40) en incrementant $65. S'arrete quand $65 atteint le
; budget mwt -> $3F3F, sinon memorise mcnt := $65 et continue tant qu'il reste des
; commandes ($6C). mcnt = plus grand nombre d'enregistrements < budget.
wander_count:
        inc     $65
        jsr     rec_next
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     wander_count
        lda     $65
        cmp     mwt
        bcs     wander_count_ok
        sta     mcnt
        dec     $6C
        bne     wander_count
; Aucun enregistrement ne tient dans le budget (mcnt nul) -> le plan est abandonne
; ($3FCF) ; sinon il y a de quoi retenir un candidat.
wander_count_ok:
        lda     mcnt
        bne     wander_retain
        jmp     L3FCF

; Retention du candidat : note son poids (L48D4,x := mcnt) et son id (L48D3,x := $90),
; puis efface $90. Calcule la destination ptr := $47E3 + 24*(10-mwt) : 10-mwt est le
; poids des candidats deja reserves, donc chaque candidat est empile a la suite des
; precedents.
wander_retain:
        sta     L48D4,x
        lda     $90
        sta     L48D3,x
        lda     #$00
        sta     $90
        lda     #$0A
        sec
        sbc     mwt
        asl     a
        asl     a
        asl     a
        sta     mwt
        asl     a
        clc
        adc     mwt
        adc     #$E3
        sta     ptr
        lda     #$00
        adc     #$47
        sta     ptr_hi
        ldy     #$00
; Empilement des commandes : recopie mcnt enregistrements de 24 octets depuis $4927 vers
; (ptr) (zone $47E3 indexee par le poids), un octet a la fois (wander_pack_byte), puis
; enchaine sur wander_step pour tenter le deplacement.
wander_pack:
        ldx     #$18
; Boucle interne d'empilement : recopie un octet de L4927,y vers (ptr),y et incremente Y
; sans le remettre a zero entre enregistrements (copie contigue de mcnt x 24 octets).
wander_pack_byte:
        lda     L4927,y
        sta     (ptr),y
        iny
        dex
        bne     wander_pack_byte
        dec     mcnt
        bne     wander_pack
        jmp     wander_step

L3F7E:  .byte   $CA
; Amorce un deplacement d'errance. A (mode, = 1 en pratique) est range dans le drapeau
; auto-modifie $3F7E, relu par wander_step : 0 = ne pas tenter le pas reel. Compare
; ensuite le personnage de la file ($90) a obj : identiques -> recalcul du plan
; (wander_core) ; sinon -> simple pas (wander_step). Appele par entity_tick (one-shot)
; et act_v14_11.
wander_start:
        sta     L3F7E                           ; drapeau d'errance $3F7E := A (0 = ne pas tenter le pas reel)
        jsr     push_ptr
        lda     $90
        cmp     obj
        bne     wander_step
        jmp     wander_core

; Execute un pas d'errance : selectionne l'entree candidate (wander_select), puis, si le
; drapeau $3F7E est arme, rejoue sa commande sauvegardee (cmd_run puis cmd_probe). En cas
; d'echec, decremente le poids et reprend (wander_rewind) ; en cas de succes, memorise la
; position et valide.
wander_step:
        jsr     wander_select
        lda     L3F7E                           ; drapeau $3F7E : si arme, tenter le pas reel (sinon sauter)
        beq     L3FC5
        lda     L48D5,x
        sta     $7E
        lda     L48D6,x
        sta     svptr
        lda     L48D7,x
        sta     svptr_hi
        jsr     cmd_run
        bne     L3FD4
        jsr     cmd_probe
        beq     L3FCA
        ldx     cand
        lda     svptr
        sta     L48D6,x
        lda     svptr_hi
        sta     L48D7,x
        lda     $7E
        sta     L48D5,x
        bne     L3FC5
        jsr     wander_rewind
L3FC5:  lda     #$01
        jmp     pop_ptr2

L3FCA:  jsr     wander_rewind
        bne     L3FCA
L3FCF:  lda     #$00
        jmp     pop_ptr2

L3FD4:  lda     $7E
        beq     L3FCA
        ldx     cand
        lda     #$00
        sta     L48D5,x
        jsr     wander_rewind
        jmp     wander_step

; Rembobine la file des commandes ($4905) jusqu'a la position du candidat et
; consomme le poids du deplacement (dec L48D4[x]) ; libere le slot quand il est
; epuise (recopie de la suite).
wander_rewind:
        jsr     push_ptr2
        jsr     fetch_retaddr
L3FEB:  jsr     rec_next
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        beq     L3FFA
        inc     mwt
        bne     L3FEB
L3FFA:  lda     #$09
        sec
        sbc     mwt
        sta     mwt
        beq     L4013
        ldy     #$00
L4005:  ldx     #$18
L4007:  lda     (ptr2),y
        sta     (ptr),y
        iny
        dex
        bne     L4007
        dec     mwt
        bne     L4005
L4013:  ldx     cand
        dec     L48D4,x
        beq     L401B
        rts

L401B:  txa
        clc
        adc     #$05
        tay
L4020:  cpy     #$32
        beq     L402F
        lda     L48D3,y
        sta     L48D3,x
        inx
        iny
        jmp     L4020

L402F:  lda     #$00
        sta     L48D3,x
        rts

; Selectionne le candidat courant : cherche le personnage dans $48D3 (cand_check),
; memorise son index (cand $CF), pointe sa suite de commandes (ptr2 = $47E3) et sa
; position dans la file.
wander_select:
        jsr     cand_check
; Moteur d'errance : retient un candidat $48D3 (index cand, poids mwt)
wander_add_cand:
        lda     #$E3
        sta     ptr2
        lda     #$47
        sta     ptr2_hi
        stx     cand
        tya
        tax
        sta     mwt
        beq     L404E
L4048:  jsr     rec_rewind2
        dex
        bne     L4048
L404E:  ldx     cand
        rts

; Retire un personnage de la liste des candidats $48D3 (retrouve son slot d'apres
; l'id et le vide). Appelee par code_4D47 quand un personnage change d'etat.
wander_remove:
        jsr     push_ptr
        tax
        lda     obj
        pha
        stx     obj
        jsr     wander_reset
        bne     L4067
        jsr     wander_add_cand
L4062:  jsr     wander_rewind
        bne     L4062
L4067:  pla
        sta     obj
        jmp     pop_ptr2

; Lit une touche au clavier (get_key) et signale si une touche est presente
read_key:
        jsr     vec_11
        bmi     L409F
        lda     #$20
L4074:  nop
        nop
        sec
        sbc     #$01
        bne     L4074
        lda     $61
        sec
        sbc     #$01
        sta     $61
        lda     $62
        sbc     #$00
        sta     $62
        ora     $61
        bne     read_key
        jsr     line_clear
L408F:  lda     L40BA,x
        sta     L40BE,x
        jsr     putchar
        inx
        cpx     #$04
        bne     L408F
        lda     #$0D
L409F:  and     #$7F
        pha
        lda     #$30
        sta     $61
        lda     #$75
        sta     $62
        pla
        rts

; Efface toute la ligne de saisie (touche DEL) et repositionne le curseur
line_clear:
        cpx     #$00
        bne     L40B1
        rts

L40B1:  lda     #$08
        jsr     putchar
        dex
        jmp     line_clear

L40BA:  .byte   $57,$41,$49
L40BD:  .byte   $54
L40BE:  .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$01,$87,$38,$00
        .byte   $00,$44,$31,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$5C,$25,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$20,$20,$20
        .byte   $20,$20,$20,$20,$20,$20,$20,$20
        .byte   $20,$20,$20,$20,$20,$20,$20,$00
        .byte   $20,$20,$20,$20,$20,$20,$20,$20
        .byte   $20,$20,$20,$20,$20,$20,$20,$20
        .byte   $20,$20,$F5,$3F,$33,$38,$34,$38
        .byte   $00,$37,$27,$20,$20,$20,$20,$20
        .byte   $20,$20,$20,$20,$20,$20,$20,$20
        .byte   $20,$20,$20,$20,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $0D,$0D,$0D
; Decode les drapeaux de la sortie courante (exitp) vers xaux/xmode (direct ou variante)
move_flags_decode:
        ldy     #$05
        lda     (exitp),y
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     xaux
        ldy     #$07
        lda     (exitp),y
        and     #$F0
        ora     xaux
        sta     xaux
        ldy     #$01
        lda     (exitp),y
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     xmode
        ldy     #$03
        lda     (exitp),y
        and     #$F0
        ora     xmode
        sta     xmode
        rts

; Execute le mouvement en mode reel (phase=1) puis decrit le lieu s'il n'y a pas d'annonce
move_run_real:
        lda     #$00
        sta     passok
        lda     #$01
        sta     phase
        lda     $5E
        bne     L4179
        jsr     describe_room
L4179:  lda     #$00
        rts

; QUOI : decrit le lieu (nom, sorties, objets visibles, ex. YOU ARE IN...).
; EXEMPLE : apres GO NORTH reussi ou LOOK.
; COMMENT : via exitp (exit_ptr), mots par L4232 ; raccourci en sonde (passok), tient compte
; de is_dark et xmode/xaux.
describe_room:
        tya
        pha
        txa
        pha
        lda     #$01
        sta     $75
        lda     #$00
        sta     nest
        lda     #$01
        ldx     passok
        beq     L4190
        lda     #$00
L4190:  sta     raw
        lda     wid                             ; fiche de sortie du mot courant (wid) -> exitp
        jsr     exit_ptr
        lda     passok
        beq     L41A2
        lda     obj
        bne     L41A2
        jsr     print_cr
L41A2:  jsr     move_flags_decode               ; drapeaux de la sortie courante (code_4141)
        and     #$10
        beq     L41AC
        jmp     L4229

L41AC:  jsr     tok_obj_cur                     ; nom du lieu puis champs du record de sortie (L4232)
        lda     #$B4
        sta     adr
        lda     #$01
        sta     adr_hi
        lda     passok
        bne     L41BE
        jsr     word_render
L41BE:  ldy     #$06
        jsr     exit_word_out
        jsr     is_dark                         ; lieu sombre ? (is_dark)
        ldy     #$00
        bcc     L41E0
        lda     wid                             ; dans le noir : decrit la sortie directionnelle (wid < $0A)
        cmp     #$0A
        bcs     L41E0
        lda     #$5F
        sta     adr
        lda     #$09
        sta     adr_hi
        jsr     word_render
        iny
        iny
        jmp     L41E3

L41E0:  jsr     exit_word_out
L41E3:  lda     xmode
        and     #$08
        beq     L41FE
        lda     xmode
        and     #$20
        beq     L41F2
        jsr     exit_word_out
L41F2:  ldy     #$04
        lda     xaux
        bpl     L41FB
        jsr     exit_word_out
L41FB:  jsr     tok_obj_direct
L41FE:  lda     arg2
        cmp     #$FF
        beq     L4221
        lda     xmode
        and     #$04
        beq     L4221
        ldy     #$02
        lda     xmode
        and     #$20
        bne     L4215
        jsr     exit_word_out
L4215:  ldy     #$04
        lda     xaux
        bmi     L421E
        jsr     exit_word_out
L421E:  jsr     tok_obj_variant
L4221:  lda     #$2E                            ; point final + CR
        jsr     putchar
        jsr     print_cr
L4229:  lda     #$00
        sta     $75
        pla
        tax
        pla
        tay
        rts

; Affiche le mot de sortie pointe par exitp (adresse + page) via word_render
exit_word_out:
        lda     (exitp),y
        sta     adr
        iny
        lda     (exitp),y
        and     #$0F
        sta     adr_hi
        iny
        jmp     word_render

; Affiche un mot du dictionnaire. Pour gagner de la place, les lettres sont stockees sur
; 5 bits ; cette routine les reconstitue, ajoute la terminaison (pluriel, -ing...), gere
; l'espace et le retour a la ligne.
; Technique : adresse = page ($05 + (hi&$0F)) : lo ; nibble haut de hi = grammaire
; (suffixe $4322, espace, capitale $70, fin $2x/$3x/$6x).
word_render:
        lda     adr_hi
        sta     $5B
        and     #$0F
        ora     adr
        bne     L424C
        rts

L424C:  tya
        pha
        txa
        pha
        lda     adr_hi
        and     #$0F
        sta     adr_hi
        lda     #$00
        clc
        adc     adr
        sta     adr
        lda     #$05
        adc     adr_hi
        sta     adr_hi
        ldy     #$00
        ldx     #$00
L4267:  lda     (adr),y
        and     #$1F
        beq     L428D
        clc
        adc     #$60
        sta     L430E,x
        inx
        lda     (adr),y
        iny
        and     #$80
        beq     L4267
        cpx     #$02
        beq     L4267
        cpx     #$03
        bne     L428D
        dey
        dey
        lda     (adr),y
        iny
        iny
        and     #$80
        bne     L4267
L428D:  lda     $5B
        and     #$F0
        cmp     #$50
        beq     word_space
        cmp     #$40
        beq     L42A6
        cmp     #$10
        beq     L42A2
        lda     obj
        jmp     L42A4

L42A2:  lda     arg1
L42A4:  beq     word_space
L42A6:  ldy     #$01
        lda     (adr),y
        and     #$80
        beq     word_space
        iny
        lda     (adr),y
        and     #$E0
        lsr     a
        lsr     a
        lsr     a
        tay
        lda     #$04
L42B9:  pha
        lda     L4322,y
        bne     L42C3
        pla
        jmp     word_space

L42C3:  sta     L430E,x
        iny
        inx
        pla
        sec
        sbc     #$01
        bne     L42B9
; Gere les espaces entre les mots et coupe la ligne quand on arrive au bord de l'ecran.
; Technique : insere l'espace en attente puis retour a la ligne quand X >= largeur ($04/$05).
word_space:
        lda     raw
        pha
        bne     L42D5
        lda     sppend
L42D5:  beq     L42DC
        lda     #$20
        jsr     putchar
L42DC:  pla
        bne     L42E4
        cpx     $05
        jmp     L42E6

L42E4:  cpx     col
L42E6:  bcc     L42F1
        beq     L42F1
        lda     cap
        jsr     print_cr
        sta     cap
L42F1:  lda     $5B
        and     #$F0
        cmp     #$70
        bne     L42FD
        lda     #$01
        sta     cap
L42FD:  ldy     #$00
L42FF:  lda     L430E,y
        jsr     putchar
        iny
        dex
        bne     L42FF
        pla
        tax
        pla
        tay
        rts

L430E:  .byte   $00,$00,$00,$00,$00,$00,$AC,$C7
        .byte   $FA,$C8,$1A,$C9,$00,$00,$00,$00
        .byte   $00,$00,$05,$CC
L4322:  .byte   $53,$00,$00,$00,$45,$53,$00,$00
        .byte   $49,$45,$53,$00,$08,$49,$45,$53
        .byte   $44,$00,$00,$00,$49,$4E,$47,$00
; Teste l'appartenance d'un objet a une sortie : lit les 3 paires (mot, masque)
; (record de sortie +2..+7) et les compare, via sig_match_a/b/c, a l'operande
; courant pointe par ($7C) ; une paire (0,0) est absente (ignoree). Rend Z (A=0)
; si la signature correspond, Z clair sinon. Pose $79=1 pour activer le repli
; croise des paires.
exit_sig_match:
        sty     L436B
        ldy     #$00
        jsr     sig_match_a
        bne     L4365
        lda     #$01
        sta     $79
        jsr     sig_match_a
        bne     L4357
        jsr     sig_match_a
        bne     L4357
        ldx     #$00
        jmp     L4365

L4357:  ldy     #$02
        jsr     sig_match_b
        bne     L4365
        jsr     sig_match_c
        php
        ldx     #$01
        plp
L4365:  php
        ldy     L436B
        plp
        rts

L436B:  .byte   "N"
; Compare la 1re paire (mot, masque) d'une signature a l'operande courant (nibble bas)
sig_match_a:
        lda     (ptr3),y
        iny
        ora     (ptr3),y
        beq     L4383
        lda     (ptr3),y
        eor     ($7C),y
        and     #$0F
        bne     L4383
        dey
        lda     (ptr3),y
        cmp     ($7C),y
        php
        iny
        plp
L4383:  php
        iny
        plp
        rts

; Compare une paire croisee de la signature a l'operande courant
sig_match_b:
        lda     (ptr3),y
        iny
        ora     (ptr3),y
        beq     L43A4
        lda     (ptr3),y
        iny
        iny
        eor     ($7C),y
        dey
        dey
        and     #$0F
        bne     L43A4
        dey
        lda     (ptr3),y
        iny
        iny
        cmp     ($7C),y
        php
        dey
        plp
L43A4:  php
        iny
        plp
        rts

; Compare une autre paire croisee de la signature a l'operande courant
sig_match_c:
        lda     (ptr3),y
        iny
        ora     (ptr3),y
        beq     L43C7
        lda     (ptr3),y
        dey
        dey
        eor     ($7C),y
        iny
        iny
        and     #$0F
        bne     L43C7
        dey
        lda     (ptr3),y
        dey
        dey
        cmp     ($7C),y
        php
        iny
        iny
        iny
        plp
L43C7:  php
        iny
        plp
        rts

; Retrouve la fiche de la sortie demandee : chaque lieu a une liste de sorties stockee en
; table ; cette routine calcule l'adresse de l'entree voulue (utilisee ensuite pour le
; deplacement et pour lire les conditions).
; Technique : $F8/$F9 = $26DA + wid*8 (entrees de 8 octets).
exit_ptr:
        rol     a
        rol     $6C
        rol     a
        rol     $6C
        rol     a
        rol     $6C
        and     #$F8
        clc
        adc     #$DA
        sta     exitp
        lda     $6C
        and     #$07
        adc     #$26
        sta     exitp_hi
        rts

; Fiche du lieu : pointe record+2 (acces aux conditions de deplacement)
room_cond_ptr:
        jsr     locate_location
        lda     ptr
        clc
        adc     #$02
        sta     ptr
        bcc     L43F2
        inc     ptr_hi
L43F2:  rts

; Fiche de l'objet : pointe record+8 (acces aux conditions de deplacement)
obj_cond_ptr:
        jsr     locate_object
        lda     ptr
        clc
        adc     #$08
        sta     ptr
        bcc     L4401
        inc     ptr_hi
L4401:  rts

; Repasse en mode sonde (phase=0) quand une annonce est en cours ($5E)
probe_flag_end:
        lda     $5E
        beq     L440A
        lda     #$00
        sta     phase
L440A:  jmp     print_msg

; Affiche un message. Le message n'est pas passe en argument : son adresse est ecrite
; juste apres l'instruction d'appel, dans le programme. print_msg la lit a cet endroit,
; affiche le texte, puis reprend l'execution juste apres.
; Technique : l'adresse est le mot de 2 octets suivant JSR ; reprise a JSR+5 via jmp ($6A).
print_msg:
        jsr     push_ptr_ax
        pla
        clc
        adc     #$01
        sta     L006A
        pla
        adc     #$00
        sta     $6B
        tya
        pha
        txa
        pha
        ldy     #$00
        sty     msgstk
        lda     (L006A),y
        sta     ptr
        jsr     msgptr_inc
        lda     (L006A),y
        sta     ptr_hi
        jsr     msgptr_inc
        lda     phase
        bne     L4437
        sta     passok
L4437:  jsr     render_text
        pla
        tax
        pla
        tay
        jsr     fetch_retaddr
        jmp     (L006A)

; Traduit en caracteres le texte compresse d'un message. Un message est une suite de
; codes : des lettres telles quelles, des mots courants (the, a, you...), des mots du
; dictionnaire, et des marqueurs qui inserrent un nom d'objet ou terminent la phrase.
; Technique : $20-$5F = litteral ; $60-$7F = mot courant ($1117) ; bit7 = mot 2 octets
; (word_render) ; <$20 = token ($4641).
render_text:
        ldy     #$00
        sty     tidx
L4448:  ldy     tidx
        lda     (ptr),y
        bpl     L4471
        and     #$7F
        sta     adr_hi
        iny
        lda     (ptr),y
        sta     adr
        sty     tidx
        lda     adr_hi
        and     #$F0
        cmp     #$30
        beq     text_end
        cmp     #$20
        beq     text_end
        cmp     #$60
        beq     text_end
L4469:  jsr     word_render
L446C:  inc     tidx
        jmp     L4448

L4471:  cmp     #$20
        bcc     L4482
        cmp     #$60
        bcc     L447C
        jmp     common_lookup

L447C:  jsr     cr_aware_out
        jmp     L446C

L4482:  clc
        pha
        rol     a
        tax
        lda     token_jumps,x
        sta     L44A1
        inx
        lda     token_jumps,x
        sta     L44A2
        pla
        cmp     #$14
        bcs     token_dispatch
        jsr     token_dispatch
        beq     L446C
        jmp     L4469

; Saut vers la routine du marqueur courant (lue dans la table des marqueurs)
token_dispatch:
L44A1           := * + 1
L44A2           := * + 2
        jmp     token_jumps

L44A3:  lda     #$2E
        jsr     putchar
L44A8:  jsr     print_cr
        jmp     L44BD

; Termine proprement un message : affiche le dernier mot puis applique la ponctuation
; finale demandee (rien, un point, ou un saut de ligne).
; Technique : $6x = saut de ligne, $3x = point, $2x = rien.
text_end:
        jsr     word_render
        lda     $5B
        and     #$F0
        cmp     #$60
        beq     L44A8
        cmp     #$30
        beq     L44A3
L44BD:  rts

; Petit utilitaire : avance d'un cran le pointeur de lecture du message courant.
; Technique : INC $6A, + $6B si retenue.
msgptr_inc:
        inc     L006A
        bne     L44C4
        inc     $6B
L44C4:  rts

; Marqueur $00 : affiche un message imbrique (sous-message empile)
tok_nested:
        lda     #$00
L44C7:  sta     nest
        jsr     stk_pop
        jsr     push_ptr_ax
        lda     adr
        sta     ptr
        lda     adr_hi
        sta     ptr_hi
        ora     adr
        beq     L44DE
        jsr     nested_render
L44DE:  jsr     fetch_retaddr
        lda     #$00
        rts

; Depile une adresse de la pile de messages
stk_pop:ldx     msgstk
        lda     L466F,x
        sta     adr
        inx
        lda     L466F,x
        sta     adr_hi
        inx
        stx     msgstk
        rts

; Marqueur $01 : affiche un mot dont l'adresse a ete empilee
tok_stkword:
        jsr     stk_pop
        lda     #$01
        rts

; Marqueur $02 : saute a un autre endroit du message (sans revenir)
tok_skip:
        inc     tidx
        jsr     tok_ptr_seek
        lda     #$FF
        sta     tidx
; Marqueurs $05/$0A/$0F/$12 : sans effet
tok_noop:
        lda     #$00
        rts

; Rendu : avance le pointeur de travail de tidx (position courante dans le message)
tok_ptr_seek:
        lda     tidx
        clc
        adc     ptr
        sta     ptr
        bcc     L4512
        inc     ptr_hi
L4512:  ldy     #$00
        lda     (ptr),y
        bmi     L4522
        clc
        adc     ptr
        sta     ptr
        bcc     L4521
        inc     ptr_hi
L4521:  rts

L4522:  clc
        adc     ptr
        sta     ptr
        lda     ptr_hi
        adc     #$FF
        sta     ptr_hi
        rts

; Marqueur $03 : affiche le mot pointe par le pointeur de travail
tok_objw:
        lda     wptr
        sta     adr
        lda     wptr_hi
        sta     adr_hi
        lda     #$01
        rts

; Marqueur $04 : affiche un mot empile (variante selon le contexte)
tok_stkvar:
        jsr     stk_pop
        lda     #$01
        sta     nest
        jsr     word_dispatch
        lda     #$00
        rts

        lda     #$01
        jmp     L44C7

; Marqueur $06 : affiche le nom de l'objet courant
tok_objC5:
        lda     #$00
        sta     nest
; Rendu marqueur $06 : affiche le nom de l'objet courant (obj)
tok_obj_cur:
        lda     obj
        jsr     obj_lookup
        lda     #$00
        rts

; Marqueur $07 : affiche le nom de l'objet demande
tok_obj15:
        lda     #$01
        sta     nest
; Rendu marqueur $07 : affiche le nom de l'objet direct (arg1)
tok_obj_direct:
        lda     direct
        beq     L4564
        lda     arg1
        jmp     L4581

L4564:  lda     arg1
        jmp     L458A

; Marqueur $08 : envoie un code de controle a l'affichage
tok_ctrl08:
        jsr     putchar
        lda     #$00
        rts

; Marqueur $09 : affiche le nom du second objet
tok_obj16:
        lda     #$01
        sta     nest
; Rendu marqueur $07 variante : affiche le nom du second objet (arg2)
tok_obj_variant:
        lda     variant
        beq     L457C
        lda     arg2
        jmp     L4581

L457C:  lda     arg2
        jmp     L458A

L4581:  jsr     push_ptr_ax
        jsr     room_cond_ptr
        jmp     L4590

L458A:  jsr     push_ptr_ax
        jsr     obj_cond_ptr
L4590:  jsr     nested_render
        jsr     fetch_retaddr
        lda     #$00
        rts

; Marqueur $0B : reaffiche un bout de texte partage, puis revient
tok_recurse:
        jsr     push_ptr_ax
        inc     tidx
        lda     tidx
        pha
        jsr     tok_ptr_seek
        jsr     render_text
        pla
        sta     tidx
        jsr     fetch_retaddr
        lda     #$00
        rts

; Marqueur $0C : affiche 'his' si un objet est designe, sinon 'your'
tok_pronC5:
        lda     obj
L45B2:  beq     L45BF
        lda     #$48
        sta     adr
        lda     #$05
        sta     adr_hi
        lda     #$01
        rts

L45BF:  lda     #$12
        sta     adr
        lda     #$0C
        sta     adr_hi
        lda     #$01
        rts

; Marqueur $0E : comme $0C, pour l'autre objet
tok_pron15:
        lda     arg1
        jmp     L45B2

; Marqueur $10 : affiche le nom de l'objet ('is' si absent, 'someone' si inconnu)
tok_nameC5:
        lda     obj
        pha
        lda     #$00
L45D4:  sta     nest
        pla
        pha
        jsr     obj_lookup
        pla
        beq     L45E9
        lda     #$B2
        sta     adr
        lda     #$05
        sta     adr_hi
        lda     #$01
        rts

L45E9:  lda     #$BE
        sta     adr
        lda     #$00
        sta     adr_hi
        lda     #$01
        rts

; Marqueur $11 : nom de l'autre objet
tok_name15:
        lda     arg1
        pha
        lda     #$01
        jmp     L45D4

; Marqueur $13 : nom de l'objet dont l'adresse a ete empilee
tok_nameSTK:
        ldx     msgstk
        lda     L466F,x
        pha
        inx
        stx     msgstk
        lda     #$01
        jmp     L45D4

; Affiche un message imbrique en preservant l'etat du rendu courant
nested_render:
        jsr     push_ptr2
        lda     ptr
        sta     ptr2
        lda     ptr_hi
        sta     ptr2_hi
        jsr     record_words_render
        jmp     pop_ptr

; Traduit un identifiant d'objet en son nom ('someone' si inconnu)
obj_lookup:
        cmp     #$FF
        beq     L4622
        jmp     L458A

L4622:  lda     #$58
        sta     adr
        lda     #$09
        sta     adr_hi
        jmp     word_render

; Raccourci pour les mots les plus frequents (the, a, and, you...) : un seul octet suffit
; a designer le mot, qui est ensuite affiche par le rendu normal.
; Technique : octet $60-$7F -> entree de la table $1117 (pointeur de mot).
common_lookup:
        sec
        sbc     #$60
        clc
        rol     a
        tax
        lda     $1117,x
        sta     adr
        inx
        lda     $1117,x
        sta     adr_hi
        jmp     L4469

; Annuaire des marqueurs speciaux d'un message (codes inferieurs a $20). Chaque code
; renvoie vers la routine qui sait le traiter : inserer un nom d'objet, un pronom, un
; retour a la ligne, ou terminer le message.
; Technique : 32 entiers de 2 octets ; <$14 = sous-programmes, $14/$15/$16 = fin, $17-$1F vides.
token_jumps:
        cmp     $44
        sbc     $44,x
        .byte   $FB,$44,$2E,$45,$39,$45,$04,$45
        .byte   $4B,$45,$57,$45,$69,$45,$6F,$45
        .byte   $04,$45,$99,$45,$B0,$45,$DB,$46
        .byte   $CA,$45,$04,$45,$CF,$45,$F4,$45
        .byte   $04,$45,$FC,$45,$A8,$44,$A3,$44
        .byte   $BD,$44
L466F:  .byte   $00
L4670:  .byte   $00
L4671:  .byte   $00
L4672:  .byte   $00
L4673:  .byte   $00
L4674:  .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00
; Rendu d'un mot : applique la capitalisation puis word_render (tables $28BC/$28C4)
word_dispatch:
        lda     adr
        pha
        lda     adr_hi
        pha
        lda     nest
        beq     L4690
        jsr     word_cap_fix
L4690:  pla
        and     #$0F
        sta     adr_hi
        pla
        sta     adr
        jmp     word_render

; Rendu : ajuste majuscule et suffixe (cap) selon le nibble de la tete de mot
word_cap_fix:
        lda     adr_hi
        bpl     L46B1
        and     #$0F
        cmp     #$0C
        bne     L46AC
        lda     adr
        cmp     #$0F
        bne     L46AC
        rts

L46AC:  lda     #$01
        sta     cap
        rts

L46B1:  lda     adr_hi
        and     #$F0
        lsr     a
        lsr     a
        lsr     a
        tax
        lda     raw
        ora     $75
        beq     L46CD
        lda     $28C4,x
        sta     adr
        inx
        lda     $28C4,x
        sta     adr_hi
        jmp     word_render

L46CD:  lda     $28BC,x
        sta     adr
        inx
        lda     $28BC,x
        sta     adr_hi
        jmp     word_render

; Affiche un caractere, en signalant les retours a la ligne
cr_aware_out:
        jsr     putchar
        cmp     #$0D
        beq     L46E3
        rts

L46E3:  lda     #$00
        rts

; Pile interne $0200, indexee par rstk ($AF) : L46E6 empile ptr ($8A) puis
; ptr2 ($88) ; L4702 empile ptr2 seul. En depilement, fetch_retaddr ($4737)
; restaure ptr et pop_ptr2 ($471B) restaure ptr2 puis rend la main.
; Utilisees partout ou une sous-routine doit preserver les pointeurs de
; travail (actions, rendu de messages, VM des PNJ).
push_ptr:
        jsr     push_ptr2
; Entree de push_ptr : sauve A et X, puis empile ptr ($8A/$8B) sur la pile
; interne $0200 indexee par rstk ($AF). Appelee directement quand A/X doivent
; etre preserves sans empiler ptr2.
push_ptr_ax:
        sta     svA
        stx     svX
        ldx     rstk
        lda     ptr
        sta     $0200,x
        inx
        lda     ptr_hi
        sta     $0200,x
        inx
        stx     rstk
        ldx     svX
        lda     svA
        rts

; Sauvegarde ptr2 ($88) sur la pile interne $0200
push_ptr2:
        sta     svA
        stx     svX
        ldx     rstk
        lda     ptr2
        sta     $0200,x
        inx
        lda     ptr2_hi
        sta     $0200,x
        inx
        stx     rstk
        ldx     svX
        lda     svA
        rts

; Restaure ptr2 ($88) depuis la pile interne $0200 puis rend la main
pop_ptr2:
        jsr     fetch_retaddr
; Restaure ptr ($8A) depuis la pile interne $0200
pop_ptr:sta     svA
        stx     svX
        ldx     rstk
        dex
        lda     $0200,x
        sta     ptr2_hi
        dex
        lda     $0200,x
        sta     ptr2
        stx     rstk
        ldx     svX
        lda     svA
        rts

; Recupere l'adresse de retour empilee
fetch_retaddr:
        sta     svA
        stx     svX
        ldx     rstk
        dex
        lda     $0200,x
        sta     ptr_hi
        dex
        lda     $0200,x
        sta     ptr
        stx     rstk
        ldx     svX
        lda     svA
        rts

; Affiche l'illustration associee a une cle (si elle existe)
img_show:
        pha
        lda     ptr_block3
        ora     L2C04
        beq     L475D
        lda     $56
        bne     L475F
L475D:  pla
        rts

L475F:  pla
        pha
        jsr     push_ptr_ax
        ldx     ptr_block3
        ldy     L2C04
        jsr     index_id_table
        beq     L477E
        ldy     #$01
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        tay
        jsr     vec_init
        jsr     keyin
L477E:  jsr     fetch_retaddr
L4781:  pla
L4782:  rts

L4783:  .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A,$1A,$1A
        .byte   $1A,$1A,$1A,$1A,$1A,$1A
        .byte   "X "
L47C3:  .byte   "'SUBS'"
        .byte   $0D
        .byte   "        I"
L47D3:  .byte   "NCLUDE D:SUBS.M"
L47E2:  .byte   "AC"
        .byte   $0D
        .byte   "        .PRINTX 'DATA'"
        .byte   $0D
        .byte   "        INCLUDE D:DATA.MAC"
        .byte   $0D
        .byte   "        .PRINTX 'SUBRONE'"
        .byte   $0D
        .byte   "        INCLUDE D:SUBRONE.MAC"
        .byte   $0D
        .byte   "        .PRINTX 'SUBRTWO'"
        .byte   $0D
        .byte   "        INCLUDE D:SUBRTWO.MAC"
        .byte   $0D
        .byte   "        .PRINTX 'GENER'"
        .byte   $0D
        .byte   "        INCLUDE D:GENER.MAC"
        .byte   $0D
        .byte   "        .PRINTX 'GENER2'"
L48D3:  .byte   $00
L48D4:  .byte   $00
L48D5:  .byte   $00
L48D6:  .byte   $00
L48D7:  .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00
L4905:  .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00
L490F:  .byte   "   INCLUDE D:ACTION.MAC"
        .byte   $0D
L4927:  .byte   "        .PRINTX 'GENACT'"
        .byte   $0D
        .byte   "P"
        .byte   $0C,$03
        .byte   ":=D:ADVORIC"
        .byte   $0D,$0A,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00
        .byte   "/H?Command error"
        .byte   $00
        .byte   "?File not found"
        .byte   $00
        .byte   "?Can't enter file"
        .byte   $00
        .byte   "~"
        .byte   $E6,$7F,$C8,$CD,$93
        .byte   "L#"
        .byte   $C3,$A4
        .byte   "H!sH"
        .byte   $C3,$BE
        .byte   "H!"
        .byte   $82
        .byte   "H"
        .byte   $C3,$BE
        .byte   "H!"
        .byte   $92
        .byte   "H"
        .byte   $CD,$A4
        .byte   "H"
        .byte   $C3,$DF
        .byte   "H"
        .byte   $22,$04
        .byte   "C*"
        .byte   $06,$00
        .byte   "+"
        .byte   $F9
        .byte   "++"
        .byte   $22
        .byte   "ZB*"
        .byte   $04
        .byte   "C"
        .byte   $E5
        .byte   ":fB"
        .byte   $B7,$C2,$00,$00
        .byte   "2]B*ZB"
        .byte   $F9,$CD,$F0
        .byte   "K:!H"
        .byte   $FE,$0D,$CA,$DF
        .byte   "H"
        .byte   $AF
        .byte   "2jB2aB2hB2gB2`B2dB2eB2cB2iB<2bB"
        .byte   $01,$AF
        .byte   "H"
        .byte   $C5,$AF
        .byte   "2YB"
        .byte   $CD,$86
        .byte   "J"
        .byte   $D8,$11,$10
        .byte   "C"
        .byte   $CD
        .byte   "iJ"
        .byte   $11,$05
        .byte   "C"
        .byte   $1A,$FE
        .byte   " "
        .byte   $C2
        .byte   ".I>"
        .byte   $80
        .byte   "2YB"
        .byte   $E5
        .byte   "!kB"
        .byte   $CD
        .byte   "]J"
        .byte   $E1
        .byte   "> 2"
        .byte   $05
        .byte   "C2"
        .byte   $0D
        .byte   "C"
        .byte   $AF
        .byte   "2"
        .byte   $04
        .byte   "Cy"
        .byte   $D6
        .byte   ","
        .byte   $B7
        .byte   "2cB"
        .byte   $C2
        .byte   "XI:YB"
        .byte   $EE,$80
        .byte   "2cB"
        .byte   $CD,$86
        .byte   "J"
        .byte   $D8,$11,$16
        .byte   "C:dB"
        .byte   $B7,$CA
        .byte   "eI"
        .byte   $11,$13
        .byte   "C"
        .byte   $CD
        .byte   "iJ"
        .byte   $11,$05
        .byte   "C:"
        .byte   $04
        .byte   "C2_B"
        .byte   $1A,$D6
        .byte   " 2^B"
        .byte   $C2,$82
        .byte   "I:YB"
        .byte   $C6
        .byte   "@2YB"
        .byte   $E5
        .byte   "!"
        .byte   $8C
        .byte   "B"
        .byte   $CD
        .byte   "]J"
        .byte   $E1
        .byte   "y"
        .byte   $FE
        .byte   "=7"
        .byte   $C0,$CD,$86
        .byte   "J"
        .byte   $FE,$0D
        .byte   "7"
        .byte   $C0,$11,$06,$01,$CD
        .byte   "iJ"
        .byte   $11,$04
        .byte   "C"
        .byte   $1A,$13,$B7,$FA,$AA
        .byte   "I"
        .byte   $1A,$FE
        .byte   " 7"
        .byte   $C8,$E5
        .byte   "!"
        .byte   $AD
        .byte   "B"
        .byte   $CD
        .byte   "]J"
        .byte   $E1
        .byte   ":YB"
        .byte   $87
        .byte   "!kB"
        .byte   $DC
        .byte   "=J"
        .byte   $87
        .byte   "!"
        .byte   $8C
        .byte   "B"
        .byte   $F5
        .byte   ":dB"
        .byte   $B7,$CA,$DA
        .byte   "I"
        .byte   $11,$95
        .byte   "B"
        .byte   $01,$13
        .byte   "C>"
        .byte   $03,$F5,$0A,$12,$13,$03,$F1
        .byte   "="
        .byte   $C2,$D0
        .byte   "I"
        .byte   $F1,$DC
        .byte   "=J:aB"
        .byte   $B7,$C2,$EF
        .byte   "I:"
; Variante sonde de perform_action : appelle arg1_check puis, si le 1er objet
; est utilisable et le verbe autorise pour lui (verb_obj_ok), pose passok=1.
; N'execute pas l'action ; sert a savoir si la commande passe avant de la
; rejouer en reel.
action_probe:
        jsr     push_ptr_ax
        jsr     arg1_check
        php
        ldx     #$00
        plp
        beq     L4B32
        lda     wid
        ldx     #$AC
        ldy     #$6F
        jsr     index_id_table
        ldx     #$01
        cmp     #$FF
        bne     L4B32
        lda     arg1
        jsr     locate_object
        lda     wid
        jsr     verb_obj_ok
        ldx     #$01
        bcs     L4B32
        ldx     #$00
L4B32:  stx     passok
        jmp     fetch_retaddr

; QUOI : execute vraiment l'ordre (TAKE LAMP -> YOU TAKE... ; noir sans lampe -> I SEE NOTHING).
; ENTREE : fiche commande ; SORTIE : effet joue via table $7014 (ordinaire) ou $7114 (etendue).
; COMMENT : sauve contexte, resout arg1/arg2 en orec via locate_object (obj_check filtre),
; teste is_dark puis compatibilite verb_obj_ok, appelle via indirect_call ; sert aussi de sonde.
perform_action:
        jsr     push_ptr_ax
        jsr     arg1_check
        bne     L4B42
        jmp     L4C51

L4B42:  jsr     is_dark                         ; obscurite du lieu (is_dark)
        bcc     L4B5F                           ; clair -> continue ; sombre -> teste la lumiere portee
        lda     $7F
        bne     L4B57
        jsr     light_from_arg1
        bcc     L4B57
        lda     arg2
        jsr     light_from_a
        bcs     L4B5F
L4B57:  jsr     print_msg
; -> $13A0 I SEE NOTHING HERE.
msg_4B5A:
        .word   $13A0
code_4B5C:
        jmp     L4BE9

L4B5F:  lda     direct                          ; sortie directe (direct) -> verbe sans objet
        cmp     #$01
        bne     L4B68
L4B65:  jmp     L4C20                           ; verbe sans objet -> dispatch de la table $6FAC (L4C20)

L4B68:  lda     arg1
        cmp     #$FF
        beq     L4B65
        jsr     locate_object                   ; fiche du 1er objet -> orec
        lda     ptr
        sta     orec
        lda     ptr_hi
        sta     orec_hi
        lda     arg1
        jsr     obj_check                       ; controle du 1er objet (obj_check)
        bne     L4BE9
        lda     arg2
        cmp     #$FF
        beq     L4BA3
        lda     variant
        cmp     #$01
        bne     L4B8F
        jmp     L4C20

L4B8F:  lda     arg2
        jsr     locate_object                   ; fiche du 2nd objet -> orec2
        lda     ptr
        sta     orec2
        lda     ptr_hi
        sta     orec2_hi
        lda     arg2
        jsr     obj_check                       ; controle du 2nd objet
        bne     L4BE9
L4BA3:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     wid
        jsr     verb_obj_ok                     ; le verbe est-il autorise pour cet objet ?
        bcc     L4C20                           ; non autorise -> I CANNOT DO THAT (L4C20)
L4BB2:  ldy     #$01                            ; boucle des actions associees a l'objet
        lda     (ptr),y
        asl     a
        tax
        bcs     L4BC9                           ; bit7 de l'octet d'action de l'entree [verbe,action] -> table etendue $7114, sinon $7014
        lda     L7014,x
        sta     L4C64
        lda     L7015,x
        sta     L4C65
        jmp     L4BD5

L4BC9:  lda     L7114,x
        sta     L4C64
        lda     L7115,x
        sta     L4C65
L4BD5:  jsr     indirect_call                   ; appel indirect de l'action (indirect_call)
        lda     ptr
        clc
        adc     #$02
        sta     ptr
        bcc     L4BE3
        inc     ptr_hi
L4BE3:  ldy     #$00
        lda     (ptr),y
        beq     L4BB2
L4BE9:  lda     phase                           ; action reelle ? sinon fin
        cmp     #$01
        bne     L4C1D
        lda     obj
        cmp     #$00
        bne     code_4BFF
        jsr     is_dark                         ; noir et sans lumiere -> IT IS DARK
        bcc     code_4BFF
        jsr     print_msg
; -> $11F6 IT IS DARK
msg_4BFD:
        .word   $11F6
code_4BFF:
        ldx     wid
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     arg1
        jsr     announce_move
        ldx     wid
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
        lda     arg2
        jsr     announce_move
L4C1D:  jmp     fetch_retaddr

L4C20:  lda     wid                             ; dispatch verbe sans objet (table $6FAC)
        ldx     #$AC
        ldy     #$6F
        jsr     index_id_table
        cmp     #$FF
        beq     L4C51
L4C2D:  ldy     #$01
        lda     (ptr),y
        sta     L4C64
        iny
        lda     (ptr),y
        sta     L4C65
        jsr     indirect_call
        lda     ptr
        clc
        adc     #$03
        sta     ptr
        bcc     L4C48
        inc     ptr_hi
L4C48:  ldy     #$00
        lda     (ptr),y
        beq     L4C2D
        jmp     L4BE9

L4C51:  jsr     cannot_do
        jmp     L4C1D

; Affiche 'I CANNOT DO THAT' et rend la main
cannot_do:
        jsr     print_msg
; -> $139B I CANNOT DO THAT
msg_4C5A:
        .word   $139B
code_4C5C:
        rts

; Appel indirect generique : la cible a ete posee dans $4C64/$4C65 (depuis les
; tables d'actions $7014/$7143 ou la table d'evenements $7169). Sauve A et X,
; appelle la cible, restaure les registres et l'affichage (L471B).
indirect_call:
        pha
        jsr     push_ptr
        txa
        pha
L4C64           := * + 1
L4C65           := * + 2
        jsr     L0000
        pla
        tax
        jsr     pop_ptr2
        pla
        rts

; Annonce le deplacement de l'objet courant aupres du joueur (entity_goto)
announce_move:
        pha
        ldy     #$07
        lda     (ptr),y
        and     #$40
        beq     L4C80
        lda     (ptr),y
        and     #$08
        bne     L4C80
        pla
        jmp     entity_goto

L4C80:  pla
        rts

; Determine si la scene est sombre pour le joueur. La fiche du joueur (crec)
; et les objets presents sont examines : s'il n'y a aucune source de lumiere
; visible aupres de lui, rend C=1 (sombre) ; C=0 sinon. Les appelants en
; deduisent 'IT IS DARK.' ou 'I SEE NOTHING HERE.'.
; Technique : ne retient que les fiches d'etat a un seul lieu (+0 = $01),
; puis teste +$07 (masque $5C) et +$04 bit7 ; la seule source possible est l'epee $0E.
is_dark:jsr     push_ptr
        ldy     #$04
        lda     (crec),y
        and     #$80
        beq     L4CD5
        ldx     crec
        stx     ptr
        ldy     crec_hi
        sty     ptr_hi
        jsr     record_scan
        cmp     #$FF
        bne     L4CA5
        jsr     obj_room_slot
        ldy     #$00
        lda     (ptr),y
        bmi     L4CD5
L4CA5:  lda     #$62
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L4CAD:  jsr     step3byte_table
        beq     L4CDA
        ldy     #$00
        lda     (ptr2),y
        cmp     #$01
        bne     L4CAD
        ldy     #$07
        lda     (ptr2),y
        eor     #$B7
        and     #$5C
        bne     L4CAD
        ldy     #$04
        lda     (ptr2),y
        and     #$80
        beq     L4CAD
        ldy     #$00
        lda     (ptr),y
        jsr     act_try_obj
        beq     L4CAD
L4CD5:  jsr     pop_ptr2
        clc
        rts

L4CDA:  jsr     pop_ptr2
        sec
        rts

; Controle un objet avant que perform_action ne l'utilise : dans le contexte
; du joueur (obj=0) il resout la fiche (locate_object) et, selon l'etat et le
; drapeau $1B21, annonce que quelqu'un le porte ('... IS CARRYING ...').
; Sortie : A=0 si l'objet est utilisable, A<>0 si un cas particulier a ete
; traite (l'action est alors sautee).
obj_check:
        cmp     #$FF
        bne     L4CE4
        rts

L4CE4:  sta     L4D44
        jsr     push_ptr_ax
        lda     obj
        cmp     #$00
        beq     L4CF8
L4CF0:  lda     #$00
L4CF2:  php
        jsr     fetch_retaddr
        plp
        rts

L4CF8:  lda     L4D44
        jsr     locate_object
        ldy     #$08
        lda     (ptr),y
        sta     L4671
        iny
        lda     (ptr),y
        sta     L4672
        ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L4CF0
        lda     L4D44
        jsr     light_from_a
        bcs     L4CF0
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$40
        beq     L4CF0
        lda     $1B21
        and     #$80
        beq     L4CF0
        ldy     #$08
        lda     (ptr),y
        sta     L466F
        iny
        lda     (ptr),y
        sta     L4670
        jsr     print_msg
; -> $13C4 <W>IS CARRYING<W>.
msg_4D3D:
        .word   $13C4
code_4D3F:
        lda     #$01
        jmp     L4CF2

L4D44:  .byte   ":"
code_4D45:
        lda     arg1
; QUOI : fait disparaitre un personnage (mort/disparu, ex. tue au combat).
; COMMENT : marque record+7 bit3, raz compteur (code_5AF0), sort de $2B45 (entity_find)
; et d'errance (wander_remove).
unit_remove:
        cmp     #$00
        bne     L4D4E
        jmp     you_are_dead

L4D4E:  jsr     push_ptr
        sta     L4D83
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        ora     #$08
        sta     (ptr),y
        lda     L4D83
        jsr     prob_scan
        lda     L4D83
        jsr     entity_find
        cmp     #$FF
        beq     L4D74
        ldy     #$00
        tya
        sta     (ptr2),y
L4D74:  lda     L4D83
        jsr     obj_state_clear
        lda     L4D83
        jsr     wander_remove
        jmp     pop_ptr2

L4D83:  .byte   $00
; QUOI : debut de partie, montre le tunnel comme apres un LOOK.
; COMMENT : crec sur fiche joueur ($1B1A), obj/said=0, puis L6487 affiche le lieu.
intro_look:
        lda     #$1A
        sta     crec
        lda     #$1B
        sta     crec_hi
        lda     #$00
        sta     obj
        sta     said
        jmp     L6487

; Garde de sonde : si phase et passok, depile deux octets pour sortir de l'appelant
probe_guard:
        lda     phase
        and     passok
        bne     L4D9D
        pla
        pla
L4D9D:  rts

; Empile une adresse de reprise puis saute a print_msg (helper d'affichage inline)
print_via_stack:
        pla
        tax
        pla
        tay
        lda     #$4D
        pha
        lda     #$AE
        pha
        tya
        pha
        txa
        pha
        jmp     print_msg

        lda     #$2E
        jsr     putchar
        jmp     print_cr

; Prepare et affiche le message contextuel $13E0 (helper de description)
intro_caption:
        pha
        lda     #$E0
        sta     msg_4DFC
        lda     #$13
        sta     msg_4DFC+1
        pla
        jmp     L4DE9

L4DC6:  pha
        jsr     locate_location
        ldy     #$00
        lda     (ptr),y
        and     #$0E
        tax
        lda     $2110,x
        sta     $13DE
        inx
        lda     $2110,x
        sta     $13DD
        lda     #$DC
        sta     msg_4DFC
        lda     #$13
        sta     msg_4DFC+1
        pla
L4DE9:  sta     L4DF5
        jsr     push_ptr
        jsr     room_image_msg
        jmp     pop_ptr2

L4DF5:  .byte   $22
; Affiche la description du lieu courant (locate_location puis texte du record)
room_image_msg:
        jsr     locate_location
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : amorce de lieu (ex. $13DC) avant la description
msg_4DFC:
        .word   $0000
code_4DFE:
        ldy     #$08
        lda     (ptr),y
        iny
        ora     (ptr),y
        jsr     record_desc_out
        lda     L4DF5
        jsr     img_show
        jsr     print_cr
        lda     L4DF5
        jsr     room_objects_out
L4E17:  lda     L4DF5
        jsr     room_desc_show
        jmp     code_57FD

; Affiche le texte de description pointe par un enregistrement
record_desc_out:
        beq     record_words_out
        lda     (ptr),y
        sta     msg_4E30+1
        dey
        lda     (ptr),y
        sta     msg_4E30
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : description lue dans l'enregistrement ((ptr)+0/+1)
msg_4E30:
        .word   $0000
code_4E32:
        rts

; Affiche les mots d'un enregistrement de lieu (3 paires) via record_words_render
record_words_out:
        jsr     push_ptr2
        lda     ptr
        clc
        adc     #$02
        sta     ptr2
        lda     ptr_hi
        adc     #$00
        sta     ptr2_hi
        jsr     record_words_render
        jmp     pop_ptr

L4E49:  sta     L4DF5
        jsr     locate_location
        jsr     record_words_out
        jsr     print_cr
        jmp     L4E17

L4E58:  .byte   $1A
; QUOI : apres chaque ordre, les PNJ jouent (bougent, parlent) puis les evenements tombent.
; EXEMPLE : Gollum avance meme si le joueur est ailleurs ; le tonneau derive.
; COMMENT : L69E7 (victoire), entity_tick (VM PNJ), puis evt_tick ($2B12).
world_tick:
        jsr     push_ptr
        jsr     victory_check
        jsr     entity_tick
        lda     #$00
        sta     L4E58
        lda     #$01
        sta     passok
        sta     phase
        lda     #$12
        sta     ptr2
        lda     #$2B
        sta     ptr2_hi
; Parcourt les evenements differes ($2B12, entrees [id,cpt,actA,cond,actB], fin $FF).
; Chaque evenement a un compte a rebours cpt ; id = minuterie nominale (l'armement fait
; souvent cpt := id). cpt==0 = desarme (on saute). Sinon cpt-- :
;   - tant que cpt reste > 0 et que cond!=0 et cond>=cpt, l'action actB se declenche
;     (repete a chaque tour) ;
;   - quand cpt atteint 0, l'action actA se declenche, une seule fois, puis cpt := L4E58
;     (0 = desarme).
; Technique : actA passe par evt_fire (index dans la table de sauts $7169). La garde
; L4E58, RAZ a chaque world_tick, limite a un seul actA par tour ; un handler d'actA peut
; la reposer ($688D) pour en autoriser d'autres.
evt_tick:
        ldy     #$00
        lda     (ptr2),y
        cmp     #$FF
        beq     evt_end
        ldy     #$01
        lda     (ptr2),y
        beq     L4EBE
        sec
        sbc     #$01
        sta     (ptr2),y
        bne     evt_cond
        lda     L4E58
        cmp     #$01
        sta     (ptr2),y
        beq     evt_cond
        lda     #$01
        sta     L4E58
        ldy     #$02
        jmp     evt_fire

; Teste la condition d'un evenement en cours : si elle est remplie, l'action associee
; s'execute.
; Technique : si cond (octet 3) != 0 et cond >= cpt -> evt_fire (actB, octet 4).
evt_cond:
        ldy     #$03
        lda     (ptr2),y
        beq     L4EBE
        ldy     #$01
        cmp     (ptr2),y
        bcc     L4EBE
        ldy     #$04
; Declenche l'action d'un evenement : va chercher son adresse dans une table, puis l'execute.
; Technique : table de sauts $7169 (index*2) -> patch du JMP $4C64/$4C65 -> appel $4C5D.
evt_fire:
        lda     (ptr2),y
        asl     a
        tax
        lda     L7169,x
        sta     L4C64
        lda     L716A,x
        sta     L4C65
        jsr     indirect_call
L4EBE:  lda     ptr2
        clc
        adc     #$05
        sta     ptr2
        bcc     L4EC9
        inc     ptr2_hi
L4EC9:  jmp     evt_tick

; Fin de la liste des evenements : on rend la main (et on reautorise l'affichage).
; Technique : outen=1 puis L471B.
evt_end:lda     #$01
        sta     outen
        jmp     pop_ptr2

L4ED3:  .byte   $44
L4ED4:  .byte   $0E
; Fait jouer le script d'un personnage : son 'cerveau'. Appele a chaque tour
; par world_tick, pour CHAQUE entite active, meme quand le joueur est ailleurs.
;
; Table $2B45 : 17 entrees de 7 octets [id, nmax, PC_lo, PC_hi, base_lo, base_hi, reply],
; terminee par $FF. id=$00 = emplacement dormant (saute). PC = pointeur du script
; dans le bloc 2 ; base = table de sauts 3 o [cle, lo, hi] propre a l'entite ;
; nmax = index max (0-based) dans la table base (nb d'entrees - 1) ; reply =
; poids de replique (borne du tirage gating '<id>SAY NO', cf. action_talk_to ; 0 = muet).
;
; On execute au plus 6 opcodes par tick (garde-fou L4ED3, evite les boucles
; infinies). L'opcode est l'octet pointe par le PC ; on dispatch sur le nibble bas :
;   $x0/$x2 MOVE long  : wid=(PC)1, arg1=(PC)2, arg2=(PC)3 -> entity_move
;   $x1/$x3 ACT        : (PC)1 = index dans la table d'actions $7143
;   $x4     MOVE court : wid=(PC)1 ; $FF + bit $10 = saut inconditionnel
;   $x5-$xD INDIR      : saute via la table de base (script_indir $51DA)
;   $xC     GOTO cle   : entity_goto(id, cle) via la table de base
;   $xE     GOTO absolu: PC := (PC)1/(PC)2
;   $xF     RAND       : tire une cible parmi min(op, nmax) (script_rand $51CA)
;
; Apres un MOVE/ACT : bit $20 pose -> efface l'opcode (auto-modification, l'entite
; devient dormante) ; bit $10 pose -> si l'action echoue, saute de la taille de
; l'instruction (plan de secours). L'affichage est coupe pendant le calcul
; (outen=0) et retabli a la fin (entity_tick_done).
entity_tick:
        jsr     entity_tick_init
        lda     #$45
        sta     ptr2
        lda     #$2B
        sta     ptr2_hi
L4EE0:  lda     #$00                            ; bout de boucle : compteur d'opcodes remis a 0 pour l'entite
        sta     L4ED3
        ldy     #$00
        lda     (ptr2),y
        cmp     #$FF
        bne     L4EF0
        jmp     entity_tick_done

L4EF0:  cmp     #$00                            ; id $00 = emplacement dormant -> entite suivante
        bne     L4EF7
        jmp     L4FFA

L4EF7:  sta     obj                             ; entite active : obj=id, resolve lieu et fiche (L57BB)
        jsr     get_object_location
        sta     eloc
        lda     ptr
        sta     crec
        lda     ptr_hi
        sta     crec_hi
        lda     #$00
        sta     outen
        ldy     #$00
        lda     (ptr2),y
        jsr     push_ptr2
        pha
        lda     #$1A
        sta     ptr2
        lda     #$1B
        sta     ptr2_hi
        pla
        jsr     act_try_swap
        php
        jsr     pop_ptr
        plp
        beq     L4F43
        lda     L4ED4
        cmp     #$02
        beq     L4F43
        lda     #$01
        sta     outen
        lda     L4ED4
        cmp     #$01
        bne     L4F43
        inc     L4ED4
        jsr     print_msg
; -> $1406 YOU HEAR A NOISE
msg_4F3D:
        .word   $1406
code_4F3F:
        lda     #$00                            ; fin de l'annonce de bruit : coupe l'affichage (outen=0)
        sta     outen
L4F43:  lda     crec                            ; reprend le contexte de l'entite (crec -> ptr)
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     cand_check
        php
        lda     #$00
        plp
        bne     L4F56
        lda     #$01
L4F56:  sta     once                            ; once := 0 si le PNJ est deja candidat a l'errance (sinon 1)
L4F58:  ldy     #$02                            ; PC du script := ((ptr2)+2/+3) -> $8C/$8D
        lda     (ptr2),y
        sta     $8C
        iny
        lda     (ptr2),y
        sta     $8D
L4F63:  lda     L4ED3                           ; garde-fou : au plus 6 opcodes par tick
        cmp     #$06
        bne     L4F6D
        jmp     L4FFA

L4F6D:  ldy     #$00                            ; octet d'opcode du script -> test du nibble bas
        lda     $8C
        sta     ptr
        lda     $8D
        sta     ptr_hi
        lda     ($8C),y
        and     #$0F
        cmp     #$05
        bcs     L4FBA
        lda     once
        cmp     #$01
        bne     L4FA5
        lda     ($8C),y
        and     #$40
        bne     L4FA5
        lda     #$00
        sta     once
        lda     #$01
        jsr     wander_start
        beq     L4FA5
        lda     #$01
        sta     phase
        sta     passok
        jsr     push_ptr_ax
        jsr     move_announce
        jmp     L4FFA

L4FA5:  ldy     #$00                            ; nibble $04 : MOVE court (script_move_short)
        lda     ($8C),y
        and     #$0F
        cmp     #$04
        bne     L4FB2
        jmp     script_move_short

L4FB2:  bcs     L4FB7                           ; nibble $00-$03 : MOVE long (script_move)
        jmp     script_move

L4FB7:  jmp     L4FFA                           ; cas non prevu (nibble > $04 deja aiguille) : passe

L4FBA:  cmp     #$0E                            ; nibble >= 5 : GOTO / INDIR / RAND
        bne     L4FCD
        ldy     #$01                            ; $xE : GOTO absolu (PC := operande)
        lda     (ptr),y
        iny
        sta     (ptr2),y
        lda     (ptr),y
        iny
        sta     (ptr2),y
        jmp     L4F58

L4FCD:  cmp     #$0C                            ; $xC : GOTO par cle (entity_goto, table de base)
        bne     L4FE0
        ldy     #$01
        lda     (ptr),y
        tax
        ldy     #$00
        lda     (ptr2),y
        jsr     entity_goto
        jmp     L4F58

L4FE0:  cmp     #$0F                            ; $xF : RAND (script_rand)
        bne     L4FEA
        jsr     script_rand
        jmp     L4F58

L4FEA:  cmp     #$00
        bne     L4FF4
        jsr     script_adv4
        jmp     L4F63

L4FF4:  lda     #$00                            ; $x5-$xD : INDIR table[0] (script_indir)
        tax
        jsr     script_indir
L4FFA:  lda     ptr2
        clc
        adc     #$07
        sta     ptr2
        bcc     L5005
        inc     ptr2_hi
L5005:  jmp     L4EE0

; Fin de la table $2B45 : remet obj=0, reautorise l'affichage (outen=1) et
; restaure le contexte du joueur (crec = sa fiche $1B1A, eloc = son lieu $1B2A).
entity_tick_done:
        lda     #$00                            ; fin de table : restaure le contexte du joueur
        sta     obj
        lda     #$01
        sta     outen
        lda     #$1A
        sta     crec
        lda     #$1B
        sta     crec_hi
        lda     $1B2A
        sta     eloc
        rts

; Avance le script d'un personnage de 4 octets (script_adv)
script_adv4:
        lda     #$04
; Avance d'un cran le programme (script) d'un personnage.
; Technique : $8C/$8D += A.
script_adv:
        clc
        adc     $8C
        sta     $8C
        bcc     L5029
        inc     $8D
L5029:  rts

; Passe a l'instruction suivante du script d'un personnage, en sautant la taille de
; l'instruction courante.
; Technique : +4 (+2 si le bit $10 est pose), puis reecrit le PC dans l'entree de l'entite.
script_step4:
        lda     #$04
; Passe a l'instruction suivante du script d'un personnage, en sautant la taille de
; l'instruction courante (version courte).
; Technique : +2 (+2 si le bit $10 est pose), puis reecrit le PC dans l'entree de l'entite.
script_step2:
        jsr     script_adv
        ldy     #$00
        lda     (ptr),y
        and     #$10
        beq     L503C
        lda     #$02
        jsr     script_adv
L503C:  ldy     #$02
        lda     $8C
        sta     (ptr2),y
        iny
        lda     $8D
        sta     (ptr2),y
        rts

; Opcode 4 octets : avance le PC de 4 (+2 si bit $10). Si le bit0 de l'opcode
; est clair -> MOVE : wid=(PC)1, arg1=(PC)2, arg2=(PC)3 via entity_move. Sinon
; ACT : (PC)1 indexe la table $7143 ; l'action est jouee d'abord en mode sonde
; (phase=0) puis en reel si elle passe (passok).
script_move:
        ldy     #$00                            ; MOVE long (bit0=0) / ACT (bit0=1)
        lda     (ptr),y
        and     #$01
        bne     L506B
        jsr     script_step4
        ldy     #$01
        lda     (ptr),y
        sta     wid
        iny
        lda     (ptr),y
        sta     arg1
        iny
        lda     (ptr),y
        sta     arg2
        jsr     entity_move
        bne     L509A
        jmp     L50EB

L506B:  lda     #$03
        jsr     script_step2
        ldy     #$01
        lda     (ptr),y
        asl     a
        tax
        lda     L7143,x
        sta     L4C64
        lda     L7144,x
        sta     L4C65
        lda     #$00
        sta     phase
        sta     passok
        jsr     indirect_call
        lda     passok
        cmp     #$01
        php
        ldx     #$03
        plp
        bne     L50ED
        sta     phase
        jsr     indirect_call
L509A:  ldy     #$00
        lda     (ptr),y
        and     #$20
        bne     L50A5
        jmp     L4FFA

L50A5:  lda     #$00                            ; bit $20 : efface l'opcode (auto-modification, entite dormante)
        sta     (ptr),y
        jmp     L4FFA

; Opcode MOVE court ($x4) : avance le PC de 2 (+2 si bit $10) et lit wid=(PC)1.
; Si wid != $FF : deplace la creature (arg1/arg2 = $FF). Si wid = $FF : saute a
; l'adresse (PC)2/(PC)3 quand le bit $10 est pose (saut inconditionnel).
script_move_short:
        lda     #$02                            ; MOVE court $x4
        jsr     script_step2
        ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L50C9
        sta     wid
        lda     #$FF
        sta     arg1
        sta     arg2
        jsr     entity_move
        beq     L50E7
        jmp     L4FFA

L50C9:  ldy     #$00
        lda     (ptr),y
        and     #$10
        bne     L50D4
        jmp     L4FFA

L50D4:  ldy     #$02
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        ldy     #$03
        sta     (ptr2),y
        dey
        txa
        sta     (ptr2),y
        jmp     L4FFA

L50E7:  ldx     #$02                            ; echec du move : memorise pour le plan de secours
        bne     L50ED
L50EB:  ldx     #$04
L50ED:  inc     L4ED3
        ldy     #$00
        lda     (ptr),y
        and     #$10
        bne     L50FB
        jmp     L4F58

L50FB:  txa                                     ; bit $10 : saut de secours vers une autre instruction
        clc
        adc     ptr
        sta     ptr
        bcc     L5105
        inc     ptr_hi
L5105:  ldy     #$00
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        ldy     #$03
        sta     (ptr2),y
        sta     $8D
        dey
        txa
        sta     (ptr2),y
        sta     $8C
        jmp     L4F63

; Deplace un personnage : appelle le moteur de deplacement partage move_core
; (trouve la sortie du lieu selon wid/arg1/arg2 et verifie ses conditions). Si le
; deplacement reussit, enchaine sur move_announce (visibilite, bruit, action).
entity_move:
        jsr     push_ptr_ax
        jsr     move_core
        bne     move_announce
        jmp     L51C7

; Suite d'un deplacement de PNJ : gere ce que le joueur percoit. Selon direct et
; la cible, il decrit l'arrivee dans le lieu du joueur (L417C) ou signale un bruit
; ('YOU HEAR A NOISE', une fois par tour via L4ED4). Joue ensuite l'action (L4B37)
; et les repliques eventuelles (say_if_visible).
move_announce:
        lda     direct
        cmp     #$01
        beq     L51A0
        lda     wid
        cmp     #$1E
        bne     L513A
        lda     eloc
        cmp     $1B2A
        bne     L51A0
L513A:  lda     arg1
        cmp     #$FF
        beq     L5197
        jsr     get_object_location
        sta     $92
        cmp     #$FF
        bne     L5197
        lda     ploc
        cmp     eloc
        beq     L5197
        ldy     #$00
        lda     (ptr),y
        ldy     #$10
        tax
L5156:  lda     (ptr),y
        cmp     ploc
        beq     L5163
        iny
        dex
        bne     L5156
        jmp     L5197

L5163:  lda     obj
        pha
        lda     #$FF
        sta     obj
        lda     #$01
        sta     outen
        jsr     push_ptr2
        lda     L4ED4
        cmp     #$02
        beq     L518A
        cmp     #$01
        beq     L5182
        jsr     describe_room
        jmp     L518A

L5182:  jsr     print_msg
; -> $1406 YOU HEAR A NOISE
msg_5185:
        .word   $1406
code_5187:
        inc     L4ED4
L518A:  jsr     pop_ptr
        lda     #$00
        sta     outen
        pla
        sta     obj
        jmp     L51A0

L5197:  jsr     push_ptr2
        jsr     describe_room
        jsr     pop_ptr
L51A0:  jsr     perform_action
        lda     #$C9
        sta     L529B
        lda     obj
        ldx     #$F6
        ldy     #$13
        jsr     say_if_visible
        lda     direct
        cmp     #$01
        beq     L51C5
        lda     #$92
        sta     L529B
        lda     arg1
        ldx     #$FA
        ldy     #$13
        jsr     say_if_visible
L51C5:  lda     #$01
L51C7:  jmp     fetch_retaddr

; Opcode RAND ($xF) : lit le nombre de choix (PC)1, borne l'index par le champ nmax
; de l'entite ((ptr2)+1), tire un index (rand_range) puis script_indir effectue le
; saut correspondant dans la table de base. C'est la part d'imprevisibilite des PNJ.
script_rand:
        ldy     #$01                            ; opcode RAND : tirage parmi les cibles de la table de base
        lda     (ptr),y
        ldy     #$01
        cmp     (ptr2),y
        bcc     L51D6
        lda     (ptr2),y
L51D6:  jsr     rand_range
        tax
; Opcode INDIR ($x5-$xD) : utilise l'index A (0 pour INDIR, tirage pour RAND),
; le borne a nmax ((ptr2)+1 = index max de la table base), lit la cible [index] dans
; la table de base ((ptr2)+4/+5, entrees de 3 octets) et pose le PC ((ptr2)+2/+3).
script_indir:
        ldy     #$01
        cmp     (ptr2),y
        bcc     L51E3
        lda     (ptr2),y
        tax
L51E3:  jsr     push_ptr_ax
        txa
        sta     ptr
        asl     a
        clc
        adc     ptr
        tax
        ldy     #$04
        lda     (ptr2),y
        sta     ptr
        iny
        lda     (ptr2),y
        sta     ptr_hi
        inx
        txa
        tay
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        ldy     #$03
        sta     (ptr2),y
        dey
        txa
        sta     (ptr2),y
        jmp     fetch_retaddr

; Cherche dans la table $2B45 l'entree dont l'id vaut A (7 octets par entree,
; arret sur $FF). Sortie : ptr2 sur l'entree, A = id trouve, ou $FF si absent.
entity_find:
        sta     L5234
        lda     #$45
        sta     ptr2
        lda     #$2B
        sta     ptr2_hi
L5218:  ldy     #$00
        lda     (ptr2),y
        cmp     L5234
        beq     L5233
        cmp     #$FF
        beq     L5233
        lda     #$07
        clc
        adc     ptr2
        sta     ptr2
        bcc     L5230
        inc     ptr2_hi
L5230:  jmp     L5218

L5233:  rts

L5234:  .byte   $E1
; Prepare un tour de la VM des PNJ : resout le lieu du joueur (ploc, via L57BB),
; teste s'il fait noir et arme le compteur d'ambiance L4ED4 (1 = noir ; passe a 2
; quand le bruit a ete signale). A lancer une fois avant de parcourir $2B45.
entity_tick_init:
        lda     #$00                            ; init du tick : lieu joueur, noir, compteur de bruit
        jsr     get_object_location
        sta     ploc
        jsr     is_dark
        lda     #$00
        bcc     L5245
        lda     #$01
L5245:  sta     L4ED4
        rts

; Opcode GOTO par cle ($xC) : X = cle, A = id. Retrouve l'entite (entity_find),
; lit dans sa table de base l'entree de cle X (L5399) et reprend le script a
; l'adresse [cle] : permet des sauts 'nommes' a l'interieur d'un script.
entity_goto:
        jsr     push_ptr
        jsr     entity_find
        cmp     #$FF
        beq     L5276
        txa
        pha
        ldy     #$04
        lda     (ptr2),y
        tax
        iny
        lda     (ptr2),y
        tay
        pla
        jsr     index_id_table
        cmp     #$FF
        beq     L5276
        ldy     #$01
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        ldy     #$03
        sta     (ptr2),y
        dey
        txa
        sta     (ptr2),y
L5276:  jmp     pop_ptr2

; Affiche un message de dialogue seulement si le personnage est visible du joueur.
; Conditions : id valide ($FF/$00 = rien), pas en pleine annonce (L4ED4 != 2),
; meme lieu que le joueur (ploc), drapeau L5611 actif. X/Y = adresse du message
; inline ; A = id du locuteur.
say_if_visible:
        cmp     #$FF
        beq     code_52C8
        cmp     #$00
        beq     code_52C8
        stx     msg_52C6
        sty     msg_52C6+1
        sta     L5234
        lda     L4ED4
        cmp     #$02
        beq     code_52C8
        lda     L5234
        jsr     get_object_location
        sta     L52C9
L529B           := * + 1
        cmp     L0000
        beq     code_52C8
        lda     ploc
        cmp     L52C9
        bne     code_52C8
        lda     L5611
        beq     code_52C8
        lda     #$01
        sta     outen
        lda     L5234
        jsr     locate_object
        lda     #$08
        clc
        adc     ptr
        sta     L466F
        lda     #$00
        adc     ptr_hi
        sta     L4670
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : message de dialogue du PNJ (say_if_visible)
msg_52C6:
        .word   $0000
code_52C8:
        rts

L52C9:  .byte   $8A
; Verifie la presence et le role du 1er objet (arg1/direct/obj/variant) avant l'action
arg1_check:
        ldx     arg1
        inx
        bne     L52D1
        inx
        rts

L52D1:  dex
        lda     direct
        bne     L52E0
        cpx     obj
        bne     L52DB
        rts

L52DB:  cpx     arg2
        bne     L52E0
        rts

L52E0:  lda     variant
        beq     L52E5
        rts

L52E5:  ldx     arg2
        cpx     obj
        rts

; Teste la compatibilite verbe/objet : la liste des verbes autorises est
; accolee au record (adresse = ptr + (ptr)+0 + $10, entrees de 2 octets).
; Rend C=1 si le verbe A y figure, C=0 sinon.
verb_obj_ok:
        pha
        ldy     #$00
        lda     (ptr),y
        clc
        adc     #$10
        tax
        lda     #$00
        adc     #$00
        tay
        txa
        clc
        adc     ptr
        tax
        tya
        adc     ptr_hi
        tay
        pla
        jsr     index_id_table2
        beq     L5309
        sec
        rts

L5309:  clc
        rts

; Fiche d'un lieu : id < $50, entree de pointeur dans la table $2070. Au-dela
; de $4F, aucune fiche (A=0). Le record obtenu porte description et
; conditions.
locate_location:
        cmp     #$50
        bcc     L5312
        lda     #$00
        rts

L5312:  pha
        clc
        rol     a
        php
        adc     #$70
        sta     ptr
        lda     #$00
        adc     #$20
        plp
        adc     #$00
        sta     ptr_hi
        ldy     #$00
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        sta     ptr_hi
        stx     ptr
        pla
        rts

; Fiche d'un objet/personnage : cherche l'id dans la table a cles $1A62
; (entrees [cle,lo,hi], fin $FF) et pose ptr sur le record pointe.
locate_object:
        ldx     #$62
        ldy     #$1A
        jsr     index_id_table
        php
        pha
        ldy     #$01
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        sta     ptr_hi
        stx     ptr
        pla
        plp
        rts

; Teste si l'objet arg1 fournit de la lumiere (utilise par is_dark)
light_from_arg1:
        lda     arg1
; Teste si l'objet passe dans A fournit de la lumiere (offset de drapeau en X)
light_from_a:
        ldx     #$C5
; Coeur du test de lumiere : cherche un objet dans la fiche courante, rend C=1 si trouve
light_test_core:
        stx     L536C
        cmp     #$FF
        sec
        bne     L5356
        rts

L5356:  jsr     push_ptr_ax
        jsr     obj_present
        jmp     fetch_retaddr

; Parcourt les objets presents pour retrouver obj (rend C=1 si trouve)
obj_present:
        jsr     locate_object
        tax
        ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L5371
L536C           := * + 1
        cmp     obj
        bne     obj_present
        sec
        rts

L5371:  txa
        clc
        rts

; Fiche de l'objet A puis pointe son emplacement de lieu (record+$10)
obj_room_slot:
        pha
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        jsr     locate_location
        pla
        rts

; Teste une action sans l'executer (ex. TAKE mur = non, TAKE LAMP = oui)
act_probe:
        lda     phase
        cmp     #$01
        bne     L538D
        rts

L538D:  lda     #$01
        sta     passok
        pla
        pla
        rts

; Memes conventions que index_id_table, mais entrees de 2 octets.
index_id_table2:
        pha
        lda     #$02
        bne     L539C
; Recherche lineaire dans une table (X/Y = adresse) d'entrees de 3 octets
; [cle,lo,hi] : compare la cle A, avance de 3 tant que non trouve et s'arrete
; sur $FF. Rend Z=1 (A=$FF) si absente, Z=0 sinon ; ptr pointe l'entree.
index_id_table:
        pha
        lda     #$03
L539C:  sta     L53B6
        pla
        stx     ptr
        sty     ptr_hi
        sta     $6C
        ldy     #$00
L53A8:  lda     (ptr),y
        cmp     $6C
        beq     L53C0
        cmp     #$FF
        beq     L53C0
        lda     ptr
        clc
L53B6           := * + 1
        adc     #$03
        sta     ptr
        bcc     L53BD
        inc     ptr_hi
L53BD:  jmp     L53A8

L53C0:  cmp     #$FF
        rts

; Matcher de deplacement direct : maintient ptr2 sur la table de conditions
; $1A5F et parcourt les records, comparant (record)+7 (masque $48) a $81 et la
; condition (record)+8 a celle de l'operande. Rend l'id du record compatible.
cond_match_direct:
        jsr     push_ptr2
L53C6:  jsr     step3byte_table
        beq     L5405
        lda     #$02
        cmp     $81
        beq     L53E6
        ldy     #$07
        lda     (ptr2),y
        and     #$48
        cmp     #$40
        bne     L53E0
        lda     #$01
        jmp     L53E2

L53E0:  lda     #$00
L53E2:  cmp     $81
        bne     L53C6
L53E6:  lda     ptr2
        clc
        adc     #$08
        sta     $7C
        lda     ptr2_hi
        adc     #$00
        sta     $7D
        jsr     exit_sig_match
        bne     L53C6
        lda     $80
        bne     L5405
        ldy     #$00
        lda     (ptr),y
        jsr     act_try_obj
        beq     L53C6
L5405:  ldy     #$00
        lda     (ptr),y
        tax
        jsr     pop_ptr
        txa
        rts

; Avance le pointeur d'enregistrement de 3 octets (rend l'etat Z)
step3byte_table:
        lda     ptr
        clc
        adc     #$03
        sta     ptr
        bcc     L541A
        inc     ptr_hi
L541A:  ldy     #$01
        lda     (ptr),y
        sta     ptr2
        iny
        lda     (ptr),y
        sta     ptr2_hi
        ldy     #$00
        lda     (ptr),y
        cmp     #$FF
        rts

; Sauve A, avance de 3 octets (step3byte_table) puis restaure A en conservant le Z
step3byte_table_next:
        sta     L5438
        jsr     step3byte_table
        php
        lda     L5438
        plp
        rts

L5438:  .byte   "F"
; Tente une action sur un objet (via act_try_core) en sauvant le contexte
act_try_obj:
        sta     L5451
        jsr     push_ptr_ax
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     act_try_core
        jsr     fetch_retaddr
        lda     L5451
        rts

L5451:  .byte   $08
L5452:  .byte   $C0
L5453:  .byte   $20
; Coeur de la resolution d'action : parcourt les enregistrements de la table de
; conditions, demande a act_try_obj/cond_match_alt de selectionner un candidat
; compatible, ecrit son id dans l'operande puis rejoue l'action (cmd_probe)
; jusqu'a ce qu'elle passe.
act_try_core:
        jsr     push_ptr_ax
        ldy     #$07
        lda     (ptr2),y
        and     #$80
        beq     L5498
        ldy     #$10
        lda     (ptr),y
        sta     L5453
        jsr     push_ptr2
        jsr     record_scan
        sta     L5452
        jsr     fetch_retaddr
        lda     L5452
        cmp     L5451
        beq     L549D
        jsr     record_scan
        cmp     L5452
        bne     L5498
        cmp     #$FF
        bne     L549D
        ldy     #$00
        lda     (ptr),y
        tax
        ldy     #$10
L548D:  lda     (ptr),y
        cmp     L5453
        beq     L549D
        iny
        dex
        bne     L548D
L5498:  lda     #$00
        jmp     L549F

L549D:  lda     #$01
L549F:  sta     L5451
        jsr     fetch_retaddr
        lda     L5451
        rts

; Echange (ptr)/(ptr2) puis relance la resolution d'action
act_try_swap:
        sta     L5451
        jsr     swap_ptr_ptr2
        jsr     act_try_core
; Echange les pointeurs ptr et ptr2 (adresses et octets hauts)
swap_ptr_ptr2:
        lda     ptr
        tax
        lda     ptr2
        sta     ptr
        stx     ptr2
        lda     ptr_hi
        tax
        lda     ptr2_hi
        sta     ptr_hi
        stx     ptr2_hi
        lda     L5451
        rts

; Sauve le contexte puis scanne les enregistrements d'une fiche
record_scan:
        jsr     push_ptr_ax
L54CB:  ldy     #$01
        lda     (ptr),y
        sta     L54E8
        cmp     #$FF
        beq     L54E1
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$28
        bne     L54CB
L54E1:  jsr     fetch_retaddr
        lda     L54E8
        rts

L54E8:  .byte   $00
; Matcher variante : compare les conditions a record+2
cond_match_alt:
        jsr     obj_room_slot
        lda     ptr
        clc
        adc     #$07
        sta     ptr
        bcc     L54F7
        inc     ptr_hi
L54F7:  rts

; Matcher de variante : parcourt les records et compare cette fois la condition
; (record)+2, en s'appuyant sur exit_sig_match (code_433A) pour filtrer selon la
; signature de sortie. Utilise par la resolution d'operande en mode variante.
cond_match_var:
        jsr     step3byte_table
        beq     L5520
        ldy     #$02
        jsr     push_ptr_ax
        lda     (ptr),y
        jsr     locate_location
        lda     ptr
        clc
        adc     #$02
        sta     $7C
        lda     ptr_hi
        adc     #$00
        sta     $7D
        jsr     fetch_retaddr
        jsr     exit_sig_match
        bne     cond_match_var
        ldy     #$02
        lda     (ptr),y
L5520:  rts

; Copie les 8 premiers octets d'un enregistrement vers le suivant (ptr2 += 8)
record_copy8:
        jsr     push_ptr2
        lda     ptr2
        clc
        adc     #$08
        sta     ptr2
        bcc     L552F
        inc     ptr2_hi
L552F:  jsr     record_words_render
        jmp     pop_ptr

; Affiche les paires de mots d'un enregistrement (word_render) hors imbrication
record_words_render:
        lda     nest
        bne     L5563
        ldy     #$00
        lda     (ptr2),y
        sta     adr
        iny
        lda     (ptr2),y
        sta     adr_hi
        jsr     word_cap_fix
        ldy     #$02
        lda     (ptr2),y
        sta     adr
        iny
        lda     (ptr2),y
        sta     adr_hi
        jsr     word_render
        ldy     #$04
        lda     (ptr2),y
        sta     adr
        iny
        lda     (ptr2),y
        sta     adr_hi
        jsr     word_render
L5563:  ldy     #$00
        lda     (ptr2),y
        sta     adr
        iny
        lda     (ptr2),y
        sta     adr_hi
        ora     adr
        beq     L5575
        jsr     word_dispatch
L5575:  rts

; Compte combien de slots de la table $1A5F portent l'objet A avec le flag bit7
; pose ; rend le total dans A. Distingue un objet unique d'un objet en plusieurs
; exemplaires.
slot_count:
        sta     L55AC
        jsr     push_ptr
        lda     #$00
        sta     L55AD
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L5589:  jsr     step3byte_table_next
        beq     L55A5
        ldy     #$01
        lda     (ptr2),y
        cmp     L55AC
        bne     L5589
        ldy     #$07
        lda     (ptr2),y
        and     #$80
        beq     L5589
        inc     L55AD
        jmp     L5589

L55A5:  jsr     pop_ptr2
        lda     L55AD
        rts

L55AC:  .byte   $63
L55AD:  .byte   $00
; Cherche un emplacement libre dans la table $1A62 (enregistrements de 3 octets)
; pour l'objet courant, ecrit l'objet + la cle (X) et rend l'index de slot dans X.
; slot_alloc2 ($55B3) fait de meme pour des enregistrements de 2 octets ; les deux
; partagent la boucle de recherche de slot_find_free ($55C9).
slot_alloc3:
        pha
        lda     #$02
        bne     L55B6
; Cherche un emplacement de taille 2 pour l'objet courant (table $1A62) et rend X
slot_alloc2:
        pha
        lda     #$03
L55B6:  sta     L55E3
        pla
        sta     L560F
        jsr     push_ptr
        ldx     #$00
        jsr     slot_find_free
        txa
        jmp     pop_ptr2

; Cherche un emplacement libre de la table $1A62 et y ecrit l'objet
slot_find_free:
        jsr     push_ptr_ax
        lda     #$62
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L55D4:  jsr     step3byte_table_next
        beq     L5607
        ldy     #$01
        lda     (ptr2),y
        cmp     L560F
        bne     L55D4
L55E3           := * + 1
        ldy     #$00
        txa
        clc
        adc     (ptr2),y
        bcs     L560A
        tax
        lda     L55E3
        cmp     #$02
        beq     L5604
        lda     L560F
        pha
        ldy     #$00
        lda     (ptr),y
        sta     L560F
        jsr     slot_find_free
        pla
        sta     L560F
L5604:  jmp     L55D4

L5607:  jmp     fetch_retaddr

L560A:  ldx     #$FF
        jmp     L5607

L560F:
L5610           := * + 1
L5611           := * + 2
        jmp     (L0000)

; Arme un evenement indexe par la cle X pour l'objet courant : parcourt $1A5F et
; pose la cle dans le slot correspondant. Utilise par les actions de PNJ qui
; declenchent un evenement differe ($2B12).
event_arm_obj:
        stx     key
        ldx     #$01
        stx     L5611
        jsr     event_key_scan
        lda     L5611
        beq     L5622
        rts

L5622:  lda     $1B2A
        beq     L564B
        lda     obj
        pha
        lda     crec
        pha
        lda     crec_hi
        pha
        lda     #$00
        sta     obj
        lda     #$1A
        sta     crec
        lda     #$1B
        sta     crec_hi
        jsr     act_probe_event
        jsr     entity_tick_init
        pla
        sta     crec_hi
        pla
        sta     crec
        pla
        sta     obj
L564B:  lda     #$00
        sta     L5611
        rts

; Parcourt $1A5F et fixe la cle d'evenement de l'enregistrement correspondant
event_key_scan:
        sta     L5610
        jsr     push_ptr
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L565F:  jsr     step3byte_table_next
        beq     L568A
        ldy     #$01
        lda     (ptr2),y
        cmp     L5610
        bne     L565F
        ldy     #$10
        lda     key
        sta     (ptr2),y
        lda     L5610
        pha
        ldy     #$00
        lda     (ptr),y
        bne     L5680
        sta     L5611
L5680:  jsr     event_key_scan
        pla
        sta     L5610
        jmp     L565F

L568A:  jmp     pop_ptr2

; Met a jour le porteur d'un objet dans la table $1A5F : pour chaque
; enregistrement correspondant a l'objet, rapporte le compteur de porteur
; (L56D6) en soustrayant la quantite du slot.
holder_scan:
        sta     L5610
        jsr     push_ptr
        jsr     locate_location
        ldy     #$01
        lda     (ptr),y
        sta     L56D6
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L56A5:  jsr     step3byte_table
        beq     L56CB
        ldy     #$00
        lda     (ptr2),y
        cmp     #$01
        bne     L56A5
        ldy     #$10
        lda     (ptr2),y
        cmp     L5610
        bne     L56A5
        lda     L56D6
        sec
        ldy     #$02
        sbc     (ptr2),y
        sta     L56D6
        bcc     L56D1
        jmp     L56A5

L56CB:  lda     L56D6
        jmp     pop_ptr2

L56D1:  lda     #$00
        jmp     pop_ptr2

L56D6:  .byte   $C0
; Fabrique un nombre aleatoire borne, utilise pour les comportements imprevisibles
; (errance des personnages, combats...).
; Technique : melange des octets de la source de bruit $93/$94 puis ramene le resultat dans [0, A).
rand_range:
        and     #$7F
; Ramene un compteur a une echelle (0-10) : double la valeur, sature a $FF, puis
; compare L570F/L5710 (ratio de probabilite). Sert aux tirages ponderes des
; actions.
ratio_scale:
        sta     L570F
        asl     a
        bcc     L56E1
        lda     #$FF
L56E1:  sta     L5710
L56E4:  inc     noise_hi
        bne     L56EA
        inc     noise
L56EA:  ldy     #$00
        lda     L570E
        clc
        adc     (noise),y
        ldy     ptr
        eor     (noise),y
        cmp     L570E
        beq     L56E4
        sta     L570E
L56FE:  cmp     L5710
        bcc     L5709
        beq     L5709
        lsr     a
        jmp     L56FE

L5709:  sec
        sbc     L570F
        rts

L570E:  .byte   $22
L570F:  .byte   $00
L5710:  .byte   $00
; Teste une probabilite pour l'objet arg1 (table $1A5F)
prob_from_arg1:
        lda     arg1
; Coeur du test de probabilite : parcourt $1A5F pour l'objet courant
prob_scan:
        sta     L5710
        jsr     push_ptr
        jsr     locate_object
        ldy     #$01
        lda     (ptr),y
        sta     L570F
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L572B:  jsr     step3byte_table_next
        beq     L576A
        ldy     #$01
        lda     (ptr2),y
        cmp     L5710
        bne     L572B
        ldy     #$07
        lda     (ptr2),y
        and     #$02
        beq     L5760
        ldy     #$10
        lda     #$00
        sta     (ptr2),y
        lda     #$01
        lda     #$FF
        sta     (ptr2),y
        ldy     #$07
        lda     (ptr2),y
        and     #$7F
        sta     (ptr2),y
        jsr     record_copy8
        jsr     print_msg
; -> $1522 EVAPORATE.
msg_575B:
        .word   $1522
code_575D:
        jmp     L572B

L5760:  ldy     #$01
        lda     L570F
        sta     (ptr2),y
        jmp     L572B

L576A:  jmp     pop_ptr2

; Verifie l'objet arg1 en tant qu'arme (variante A)
weapon_test_a:
        lda     arg1
; Teste un flag d'objet (A) et met a jour son etat (variante 1)
item_flag_test:
        pha
        lda     #$01
        bne     L5777
; Teste un flag d'objet (A) et met a jour son etat (variante 2)
item_flag_test2:
        pha
        lda     #$02
L5777:  sta     L5789
        pla
        jsr     push_ptr2
        sta     $6C
        jsr     cond_match_alt
L5783:  jsr     step3byte_table
        beq     L5790
L5789           := * + 1
        ldy     #$00
        lda     (ptr),y
        cmp     $6C
        bne     L5783
L5790:  jmp     pop_ptr

; Pose l'adresse X/Y dans $4C64/$4C65 puis l'appelle (indirect_call)
call_action_at:
        stx     L4C64
        sty     L4C65
        jsr     call_action_off
        jsr     indirect_call
; Prepare l'appel indirect de l'action dont l'adresse est lue dans un record (Y)
call_action_off:
        ldy     #$01
L57A1:  lda     orec,y
        tax
        lda     orec2,y
        sta     orec,y
        txa
        sta     orec2,y
        dey
        bpl     L57A1
        lda     arg1
        ldx     arg2
        sta     arg2
        stx     arg1
        rts

; Resout le lieu d'un personnage/objet a partir de son id : cherche sa fiche (locate_object)
; puis lit son champ +0 (N = nombre de lieux). Seul +0 = $01 (objet a un seul lieu) est
; resolu : la fiche porte alors son lieu en +$10 ; sinon rend $FF = 'nulle part' (les objets
; multi-lieux +0 >= 2, ex. porte/eau/toile, ont leur liste en +$10.. geree par L5FFA).
; Meme regle que is_dark, holder_scan et la verification d'arme (act_p14_00).
get_object_location:
        cmp     #$FF
        bne     L57C0
        rts

L57C0:  jsr     locate_object
        ldy     #$00
        lda     (ptr),y
        cmp     #$01
        php
        lda     #$FF
        plp
        beq     L57D0
        rts

L57D0:  ldy     #$10
        lda     (ptr),y
        rts

; Retrouve un objet et affiche son nom (via cond_match_alt)
obj_render_lookup:
        jsr     push_ptr2
        sta     L57FB
        stx     L57FC
        jsr     cond_match_alt
L57E1:  jsr     step3byte_table
        beq     L57F5
        ldy     #$02
        lda     (ptr),y
        beq     L57E1
        ldy     #$00
        lda     (ptr),y
        cmp     L57FB
        bne     L57E1
L57F5:  ldx     L57FC
        jmp     pop_ptr

L57FB:  .byte   $C0
L57FC:  .byte   $20
code_57FD:
        pha
        jsr     print_msg
; -> $13E3 <OBJ>SEE :
msg_5801:
        .word   $13E3
code_5803:
        ldy     #$10
        lda     (crec),y
        tax
        lda     #$FF
        jsr     list_visible_init
        pla
        rts

; Affiche la liste des objets visibles d'un lieu : fixe le filtre (L5835) puis
; appelle list_visible_scan ; si rien n'a ete rendu, affiche 'NOTHING' ($171B).
list_visible_init:
        stx     L5832
        sta     L5833
        jsr     push_ptr2
        lda     #$00
        sta     L5834
        lda     #$04
        sta     L5835
        jsr     list_visible_scan
        lda     L5834
        bne     code_582F
        jsr     print_msg
; -> $171B NOTHING
msg_582D:
        .word   $171B
code_582F:
        jmp     pop_ptr

L5832:  .byte   $00
L5833:  .byte   "L"
L5834:  .byte   "A"
L5835:  .byte   "S"
; Balaye les enregistrements d'un lieu (via record_scan) et, pour chaque objet
; dont le type correspond au filtre L5835, affiche son nom (name_from_record).
; L5834 compte le nombre d'objets rendus.
list_visible_scan:
        lda     $10
        pha
        lda     L5835
        sta     $10
        jsr     push_ptr_ax
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L5849:  jsr     step3byte_table_next
        bne     L5851
        jmp     L58E0

L5851:  ldy     #$01
        lda     (ptr2),y
        cmp     L5833
        beq     L585D
        jmp     L5849

L585D:  pha
        dey
        lda     (ptr2),y
        tax
        pla
        pha
        cmp     #$FF
        bne     L586C
        cpx     #$01
        bne     L58D6
L586C:  ldy     #$10
        lda     (ptr2),y
        cmp     L5832
        beq     L5880
        dex
        beq     L58D6
        iny
        lda     (ptr2),y
        cmp     L5832
        bne     L58D6
L5880:  lda     obj
        ldy     #$00
        cmp     (ptr),y
        bne     L588F
        lda     #$04
        cmp     L5835
        beq     L58D6
L588F:  lda     (ptr),y
        jsr     act_try_obj
        beq     L58D6
        inc     L5834
        lda     #$00
        sta     cap
        sta     nest
        jsr     record_copy8
        lda     obj
        ldy     #$00
        cmp     (ptr),y
        beq     L58DA
        lda     #$2E
        jsr     putchar
        ldy     #$00
        lda     (ptr),y
        jsr     obj_visible
        bcs     L58D6
        lda     L5833
        pha
        ldy     #$00
        lda     (ptr),y
        sta     L5833
        inc     L5835
        inc     L5835
        jsr     list_visible_scan
        dec     L5835
        dec     L5835
        pla
        sta     L5833
L58D6:  pla
        jmp     L5849

L58DA:  jsr     print_cr
        jmp     L58D6

L58E0:  jsr     fetch_retaddr
        pla
        sta     $10
        rts

; Teste si l'objet A est visible dans le lieu courant : lit son record et ses
; drapeaux (record+7 masque $28), verifie la quantite (slot_count) puis la
; visibilite (bit $40). Rend C=1 si visible.
obj_visible:
        sta     L5958
        jsr     push_ptr_ax
        lda     L5958
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$28
        beq     L5951
        lda     L5958
        jsr     slot_count
        cmp     #$00
        beq     L5951
        ldy     #$07
        tax
        lda     (ptr),y
        and     #$40
        beq     L591C
        lda     L5958
        sta     L466F
        jsr     print_msg
; -> $11D0 <NAME>CARRYING
msg_5917:
        .word   $11D0
code_5919:
        jmp     code_594A

L591C:  ldy     #$08
        lda     (ptr),y
        sta     L466F
        iny
        lda     (ptr),y
        and     #$0F
        sta     L4670
        lda     #$B2
        sta     L4671
        lda     #$05
        sta     L4672
        dex
        beq     L5942
        lda     #$BE
        sta     L4671
        lda     #$00
        sta     L4672
L5942:  jsr     obj_type_route
        jsr     print_msg
; -> $13BF <W>THERE<W>
msg_5948:
        .word   $13BF
code_594A:
        clc
L594B:  php
        jsr     fetch_retaddr
        plp
        rts

L5951:  jsr     print_cr
        sec
        jmp     L594B

L5958:  .byte   $00
; Affiche les objets presents dans un lieu : pointe (record)+$0A (liste
; d'objets) et, pour chacun dont le flag bit7 est pose, rend son nom via
; word_render et le message 'THERE IS<MSG>' ($13F1).
room_objects_out:
        sta     L5958
        jsr     push_ptr
        lda     L5958
        jsr     locate_location
        lda     ptr
        clc
        adc     #$0A
        sta     ptr2
        lda     ptr_hi
        adc     #$00
        sta     ptr2_hi
L5972:  ldy     #$01
        lda     (ptr2),y
        beq     code_59CE
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$80
        beq     code_59CE
        lda     ptr
        clc
        adc     #$08
        sta     L466F
        lda     ptr_hi
        adc     #$00
        sta     L4670
        ldy     #$00
        lda     (ptr2),y
        jsr     word_ptr_table
        cmp     #$09
        bcc     L59B5
        beq     L59AA
        lda     #$26
        sta     adr
        lda     #$01
        sta     adr_hi
        jmp     L59C6

L59AA:  lda     #$4C
        sta     adr
        lda     #$00
        sta     adr_hi
        jmp     L59C6

L59B5:  lda     adr
        pha
        lda     adr_hi
        pha
        jsr     print_msg
; -> $11EE TO THE
msg_59BE:
        .word   $11EE
code_59C0:
        pla
        sta     adr_hi
        pla
        sta     adr
L59C6:  jsr     word_render
        jsr     print_msg
; -> $13F1 THERE IS<MSG>
msg_59CC:
        .word   $13F1
code_59CE:
        lda     ptr2
        clc
        adc     #$03
        sta     ptr2
        bcc     L59D9
        inc     ptr2_hi
L59D9:  ldy     #$00
        lda     (ptr2),y
        cmp     #$FF
        beq     L59E4
        jmp     L5972

L59E4:  jmp     pop_ptr2

; Affiche un mot via une paire de pointeurs (table $59F7)
word_ptr_table:
        pha
        rol     a
        and     #$FE
        tax
        lda     L59F7,x
        sta     adr
        inx
        lda     L59F7,x
        sta     adr_hi
L59F7:  pla
        rts

        lsr     $07
        jmp     (L3509)

        .byte   $03,$C2,$0B,$4B,$07,$54,$07,$71
        .byte   $09,$7A,$09,$42,$0B,$F6,$02
; Affiche la description d'un lieu (locate_location, offset 7)
room_desc_show:
        sta     L5958
        jsr     push_ptr
        lda     L5958
        jsr     locate_location
        lda     ptr
        clc
        adc     #$07
        sta     ptr
        bcc     L5A24
        inc     ptr_hi
L5A24:  jsr     rec_ptr_adv3
        beq     L5A40
        jsr     print_msg
; -> $13FE VISIBLE EXITS ARE :
msg_5A2C:
        .word   $13FE
code_5A2E:
        ldy     #$00
        lda     (ptr),y
        jsr     word_ptr_table
        jsr     word_render
        jsr     rec_ptr_adv3
        bne     code_5A2E
        jsr     print_cr
L5A40:  jmp     pop_ptr2

; Avance le pointeur d'enregistrement de 3 octets (parcours)
rec_ptr_adv3:
        lda     ptr
        clc
        adc     #$03
        sta     ptr
        bcc     L5A4E
        inc     ptr_hi
L5A4E:  ldy     #$00
        lda     (ptr),y
        cmp     #$FF
        bne     L5A57
        rts

L5A57:  iny
        lda     (ptr),y
        bne     rec_ptr_adv3
        dey
        lda     (ptr),y
        beq     rec_ptr_adv3
        rts

; Epilogue d'action partage : en mode reel (phase=1) decrit le lieu courant
; (describe_room) ; en mode sonde (phase=0) il se contente de rendre
; passok=0, ce qui amene cmd_run a classer la commande en revision ($57=3).
; Sert de queue a de nombreux corps d'action ($5BE4, $5C74, $5CC5, $5D8F,
; $6054, $60FD, $61F1, $6601, $6A8F, $6B0D, $6B34) et est appele en $6CF1.
act_look:
        lda     phase
        cmp     #$01
        bne     L5A6B
        jmp     describe_room

L5A6B:  lda     #$00
        sta     passok
        rts

; Teste le bit0 du flag record+7 et branche
obj_flag1_test:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        and     #$01
        php
        lda     #$80
        plp
        beq     obj_flag20_test
        rts

; Teste le bit5 du flag record+7 et branche
obj_flag20_test:
        ldy     #$07
        lda     (ptr),y
        and     #$20
        php
        lda     #$85
        plp
        rts

L5A90:  pha
        ldy     #$08
        lda     (ptr2),y
        tax
        iny
        lda     (ptr2),y
        tay
        jmp     L5AA7

; Affiche un nom d'objet lu a l'adresse (ptr)+8
name_from_record:
        pha
        ldy     #$08
        lda     (ptr),y
        tax
        iny
        lda     (ptr),y
        tay
L5AA7:  stx     L466F
        sty     L4670
        pla
        bmi     L5AC7
        rol     a
        and     #$FE
L5AB3:  tax
        lda     L5AD0,x
        sta     L4671
        inx
        lda     L5AD0,x
        sta     L4672
        jsr     print_msg
; -> $1397 <W>IS<W>.
msg_5AC4:
        .word   $1397
code_5AC6:
        rts

L5AC7:  rol     a
        and     #$FE
        clc
        adc     #$10
        jmp     L5AB3

L5AD0:  .byte   $35,$0B,$00,$00,$65,$03,$00,$00
        .byte   $72,$07,$12,$02,$9C,$02,$00,$00
        .byte   $45,$06,$00,$00,$6B,$04,$89,$01
        .byte   $7D,$07,$8B,$07,$80,$00,$00,$00
; Remet a zero des champs d'etat d'un objet (record+$0C/+$0D) et branche
obj_state_clear:
        jsr     push_ptr_ax
        jsr     locate_object
        ldy     #$0C
        lda     #$00
        sta     (ptr),y
        iny
        sta     (ptr),y
        ldy     #$07
        lda     (ptr),y
        ldx     #$89
        ldy     #$01
        and     #$40
        beq     L5B0F
        ldx     #$9C
        ldy     #$02
L5B0F:  tya
        ldy     #$0B
        sta     (ptr),y
        dey
        txa
        sta     (ptr),y
        jmp     fetch_retaddr

; Teste les bits du flag record+7 (masque $48) contre $40
obj_flag48_test:
        ldy     #$07
        lda     (ptr),y
        and     #$48
        cmp     #$40
        rts

; Action : montre son message (ex. YOU TAKE...) puis termine
act_msg:jsr     print_msg
; -> $13E8 <OBJ>SAY '
msg_5B27:
        .word   $13E8
code_5B29:
        lda     #$01
        sta     cap
        pla
        tax
        pla
        tay
        lda     #$5B
        pha
        lda     #$3D
        pha
        tya
        pha
        txa
        pha
        jmp     print_msg

        jsr     print_msg
; -> $13EE '.
msg_5B41:
        .word   $13EE
code_5B43:
        rts

; Verbe Look ($17) : decrit l'objet courant et liste ce qui est visible
action_look:
        jsr     act_probe
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     record_scan
        cmp     #$FF
        beq     L5B94
        pha
        lda     #$80
        sta     $13DD
        lda     #$00
        sta     $13DE
        jsr     print_msg
; -> $13DC <NAME>''
msg_5B64:
        .word   $13DC
code_5B66:
        pla
        pha
        jsr     locate_object
        jsr     obj_type_route
        ldy     #$08
        lda     (ptr),y
        sta     adr
        iny
        lda     (ptr),y
        and     #$0F
        sta     adr_hi
        jsr     word_render
        lda     #$2E
        jsr     putchar
        jsr     print_cr
        jsr     print_msg
; -> $13E3 <OBJ>SEE :
msg_5B89:
        .word   $13E3
code_5B8B:
        ldy     #$10
        lda     (ptr),y
        tax
        pla
        jmp     list_visible_init

L5B94:  ldy     #$10
        lda     (crec),y
        jmp     L4DC6

; Aiguille le traitement selon le type de l'objet (record+4 et 7 == 6)
obj_type_route:
        ldy     #$04
        lda     (ptr),y
        and     #$07
        cmp     #$06
        bne     L5BA7
        lda     #$01
L5BA7:  rol     a
        rol     a
        adc     #$A4
        sta     msg_5BB8
        lda     #$00
        adc     #$13
        sta     msg_5BB8+1
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : message $13A4/$13A8 selon le type d'objet
msg_5BB8:
        .word   $0000
code_5BBA:
        rts

; Teste la presence de lumiere (light_from_arg1) et branche
light_gate:
        jsr     light_from_arg1
        bcc     L5BC1
        rts

L5BC1:  pla
        pla
        jsr     print_msg
; -> $11C8 <NAME>NOT CARRYING IT.
msg_5BC6:
        .word   $11C8
code_5BC8:
        rts

; Verbes Take ($13)/Carry ($3B) : prend l'objet (pose le porteur)
action_pickup:
        jsr     light_from_arg1
        bcc     L5BD4
        jsr     print_msg
; -> $11E8 <NAME>ALREADY CARRYING<ARG1>.
msg_5BD1:
        .word   $11E8
code_5BD3:
        rts

L5BD4:  jsr     obj_count_add
        lda     obj
L5BD9:  jsr     locate_object
        lda     arg1
        ldy     #$01
        cmp     (ptr),y
        bne     L5BE7
        jmp     act_look

L5BE7:  lda     (ptr),y
        cmp     #$FF
        bne     L5BD9
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     act_probe
L5BF8:  ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        bne     L5C07
L5C00:  lda     obj
        ldy     #$01
        sta     (ptr),y
        rts

L5C07:  jsr     push_ptr_ax
        jsr     locate_object
        ldy     #$04
        lda     (ptr),y
        and     #$07
        cmp     $05
        beq     L5C1D
        jsr     fetch_retaddr
        jmp     L5C00

L5C1D:  ldx     ptr
        ldy     ptr_hi
        jsr     fetch_retaddr
        stx     ptr
        sty     ptr_hi
        jmp     L5BF8

; Ajoute une quantite (record+3) a l'objet via un emplacement de la table
obj_count_add:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     arg1
        jsr     slot_alloc2
        ldy     #$03
        clc
        adc     (ptr),y
        bcc     L5C41
        lda     #$FF
L5C41:  sta     L5C77
        lda     crec
        sta     ptr2
        lda     crec_hi
        sta     ptr2_hi
        ldy     #$03
        lda     (ptr2),y
        sec
        sbc     L5C77
        bcc     code_5C78
        sta     L5C77
        lda     obj
        jsr     slot_alloc2
        sec
        sbc     L5C77
        bcs     L5C80
        jsr     obj_id_minus1
        bne     L5C72
        ldy     #$07
        lda     (ptr),y
        and     #$02
        bne     L5C72
        rts

L5C72:  pla
        pla
        jmp     act_look

L5C77:  .byte   $00
code_5C78:
        pla
        pla
        jsr     print_msg
; -> $11DB <ARG1>IS TOO HEAVY TO LIFT
msg_5C7D:
        .word   $11DB
code_5C7F:
        rts

L5C80:  pla
        pla
        jsr     print_msg
; -> $11E3 <NAME>CARRYING TOO MUCH
msg_5C85:
        .word   $11E3
code_5C87:
        rts

; Resout l'objet courant et l'affiche (locate_object puis rendu)
obj_render_resolve:
        jsr     push_ptr_ax
        jsr     locate_object
L5C8E:  ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L5CA3
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$20
        bne     L5C8E
        lda     #$01
L5CA3:  php
        jsr     fetch_retaddr
        plp
        rts

; Index 4. Resout arg1 (locate_object) ; si son flag bit5 est pose, bascule vers
; act_p14_14 (bascule), sinon affiche son nom.
act_p14_04:
        lda     arg1
        jsr     locate_object
        jsr     obj_flag20_get
        bne     act_p14_14
        jmp     name_from_record

; Index 14 (bascule). Resout et affiche l'objet courant (obj_render_resolve) ;
; selon l'arme (weapon_test_a) et le contexte de lieu, deplace l'objet ou
; decrit le lieu (act_look).
act_p14_14:
        lda     obj
        jsr     obj_render_resolve
        beq     L5CBE
        rts

L5CBE:  jsr     weapon_test_a
        cmp     #$FF
        bne     L5CC8
L5CC5:  jmp     act_look

L5CC8:  ldy     #$02
        lda     (ptr),y
        beq     L5CC5
        jsr     act_probe
        jsr     push_ptr_ax
        jsr     locate_location
        ldy     #$00
        lda     (ptr),y
        jsr     fetch_retaddr
        and     #$80
        beq     L5D00
        lda     crec
        sta     ptr2
        lda     crec_hi
        sta     ptr2_hi
        ldy     #$10
        lda     (ptr2),y
        pha
        ldy     #$02
        lda     (ptr),y
        ldy     #$10
        sta     (ptr2),y
        jsr     intro_caption
        pla
        ldy     #$10
        sta     (ptr2),y
        rts

L5D00:  jsr     print_msg
; -> $11F6 IT IS DARK
msg_5D03:
        .word   $11F6
code_5D05:
        rts

; Index 5. Lance l'objet comme une arme : verifie weapon_test_a, (ptr)+2 puis
; obj_enter_check ; si l'entree est possible, cale wid := (ptr)+0, arg1 := $FF
; et enchaine sur combat_round ; sinon decrit le lieu (act_look).
act_p14_05:
        jsr     weapon_test_a
L5D09:  cmp     #$FF
        beq     L5CC5
        ldy     #$02
        lda     (ptr),y
        beq     L5CC5
        dey
        lda     (ptr),y
        jsr     push_ptr_ax
        jsr     obj_enter_check
        jsr     fetch_retaddr
        bne     L5CC5
        jsr     act_probe
        ldy     #$00
        lda     (ptr),y
        sta     wid
        lda     #$FF
        sta     arg1
        jmp     combat_round

; Verbe Take out of ($14) : verifie le contenant puis prend
action_take_out_of:
        lda     arg1
        ldx     #$16
        jsr     light_test_core
        bcc     L5D3D
        jmp     L5BD4

L5D3D:  jsr     print_msg
; -> $1391 <ARG1>IS NOT IN<ARG2>.
msg_5D40:
        .word   $1391
code_5D42:
        rts

L5D43:  .byte   $04
; Verbes $01-$0A (deplacement N..DOWN) : resout le mouvement
action_dir:
        jsr     is_dark
        bcc     combat_round
        lda     #$09
        jsr     rand_range
        clc
        adc     #$01
        sta     wid
; Un tour de combat : resout l'objet/adversaire courant (record, flag bit6) et
; enchaine l'action correspondante ; met a jour le compteur de coups et, si
; l'adversaire tombe, laisse act_try_core gerer la suite.
combat_round:
        lda     crec
        sta     ptr2
        lda     crec_hi
        sta     ptr2_hi
        ldy     #$01
        lda     (ptr2),y
        cmp     #$FF
        beq     L5D74
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$40
        beq     L5D8A
        ldy     #$01
        lda     #$FF
        sta     (ptr2),y
L5D74:  lda     obj
        jsr     slot_alloc3
        ldy     #$02
        clc
        adc     (ptr2),y
        sta     L5D43
        lda     wid
        jsr     obj_render_lookup
        cmp     #$FF
        bne     L5DAF
L5D8A:  jsr     is_dark
        bcs     L5D92
        jmp     act_look

L5D92:  jsr     act_probe
        clc
        ldy     #$05
        lda     $1B1A,y
        lsr     a
        sta     $1B1A,y
        beq     L5DA7
        jsr     print_msg
; -> $1157 BUT FALL AND HIT YOUR HEAD
msg_5DA4:
        .word   $1157
code_5DA6:
        rts

L5DA7:  jsr     print_msg
; -> $1161 BUT FALL AND SMASH YOUR SKULL
msg_5DAA:
        .word   $1161
code_5DAC:
        jmp     you_are_dead

L5DAF:  ldy     #$02
        lda     (ptr),y
        beq     L5D8A
        sta     key
        ldy     #$01
        lda     (ptr),y
        jsr     obj_enter_check
        tax
        dex
        beq     L5D8A
        dex
        beq     L5E3E
        dex
        bne     act_probe_event
        jmp     L5E47

; Joue act_probe puis arme l'evenement associe (evt_lookup) si le joueur est implique
act_probe_event:
        jsr     act_probe
        ldy     #$10
        lda     key
        sta     (ptr2),y
        lda     obj
        ldx     key
        jsr     event_arm_obj
        lda     obj
        cmp     #$00
        beq     evt_lookup
        rts

; Retrouve l'evenement associe a une cle (table des evenements)
evt_lookup:
        ldx     #$9F
        ldy     #$70
        lda     key
        jsr     index_id_table
        beq     dark_gate
        ldy     #$01
        lda     (ptr),y
        sta     L4C64
        iny
        lda     (ptr),y
        sta     L4C65
        jsr     indirect_call
; Garde d'obscurite : rend sans rien faire si le lieu est sombre
dark_gate:
        jsr     is_dark
        bcc     L5E03
        rts

L5E03:  lda     obj
        php
        lda     key
        plp
        bne     L5E3B
        ldy     #$00
        lda     ($CA),y
        and     #$40
        beq     L5E18
        lda     key
        jmp     L4E49

L5E18:  lda     ($CA),y
        ora     #$40
        sta     ($CA),y
        lda     key
        ldx     #$74
        ldy     #$70
        jsr     index_id_table
        beq     L5E39
        ldy     #$01
        lda     (ptr),y
        clc
        adc     $CC
        sta     $CC
        iny
        lda     (ptr),y
        adc     $CD
        sta     $CD
L5E39:  lda     key
L5E3B:  jmp     L4DC6

L5E3E:  jsr     obj_two_words
        jsr     print_msg
; -> $11FA <W>IS TOO SMALL FOR<OBJ>TO ENTER.
msg_5E44:
        .word   $11FA
code_5E46:
        rts

L5E47:  jsr     obj_two_words
        jsr     print_msg
; -> $1206 <W>IS TOO FULL FOR<OBJ>TO ENTER.
msg_5E4D:
        .word   $1206
code_5E4F:
        rts

; Affiche les 2 mots d'un objet lus a l'adresse $CA (L466F/L4670)
obj_two_words:
        ldy     #$02
        lda     $CA
        sta     ptr
        lda     $CB
        sta     ptr_hi
        lda     (ptr),y
        sta     L466F
        iny
        lda     (ptr),y
        sta     L4670
        rts

; Verifie si un objet peut entrer dans le lieu ou etre porte (flags record+7)
obj_enter_check:
        and     #$FF
        beq     L5E8B
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$28
        beq     L5EB4
        lda     obj
        bne     L5E81
        ldy     #$04
        lda     (ptr),y
        and     #$80
        bne     L5EB4
L5E81:  ldy     #$02
        lda     L5D43
        sec
        sbc     (ptr),y
        bcs     L5EAE
L5E8B:  lda     key
        jsr     locate_location
        lda     ptr
        sta     $CA
        lda     ptr_hi
        sta     $CB
        lda     #$FF
        ldy     #$01
        cmp     (ptr),y
        beq     L5EAB
        lda     key
        jsr     holder_scan
        sec
        sbc     L5D43
        bcc     L5EB1
L5EAB:  lda     #$00
        rts

L5EAE:  lda     #$03
        rts

L5EB1:  lda     #$02
        rts

L5EB4:  lda     #$01
        rts

; Verbe Drop ($0E) : pose l'objet ; un liquide s'evapore
action_drop:
        jsr     light_gate
        jsr     act_probe
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$01
        lda     (ptr),y
        cmp     #$12
        bne     L5ED5
        lda     #$07
        sta     ptr
        lda     #$1D
        sta     ptr_hi
L5ED5:  ldy     #$01
        lda     (crec),y
        sta     (ptr),y
        ldy     #$07
        lda     (ptr),y
        and     #$02
        bne     L5EE4
        rts

L5EE4:  ldy     #$10
        lda     #$00
        sta     (ptr),y
        lda     #$08
        clc
        adc     ptr
        sta     L466F
        lda     #$00
        adc     ptr_hi
        sta     L4670
        jsr     print_msg
; -> $1521 <MSG>EVAPORATE.
msg_5EFC:
        .word   $1521
code_5EFE:
        rts

; Verbes Enter ($1F)/Go into ($20) : entre dans le contenant
action_enter:
        lda     arg1
        jsr     item_flag_test2
        jmp     L5D09

; Verbe Run ($24) : fuit dans une direction aleatoire
action_run:
        lda     #$0A
        jsr     rand_range
        cmp     #$00
        beq     action_run
        tax
L5F11:  txa
        jsr     obj_render_lookup
        cmp     #$FF
        bne     L5F23
        inx
        cpx     #$0B
        bcc     L5F11
        ldx     #$01
        jmp     L5F11

L5F23:  sta     wid
        jmp     action_dir

; Verbe Follow ($27) : suit une entite presente
action_follow:
        ldy     #$10
        lda     (orec),y
        cmp     (crec),y
        beq     L5F3A
        jsr     item_flag_test2
        cmp     #$FF
        beq     L5F3A
        jmp     L5D09

L5F3A:  jsr     print_msg
; -> $13C9 I CANNOT FOLLOW<ARG1>FROM HERE.
msg_5F3D:
        .word   $13C9
code_5F3F:
        rts

; Verbe Throw At ($2A) : lance l'objet (arme) sur la cible
action_throw_at:
        jsr     obj_count_add
        ldy     #$07
        lda     (orec2),y
        and     #$40
        beq     L5F54
        lda     #$0B
        ldx     #$72
        ldy     #$62
        jmp     L5F5A

L5F54:  lda     #$0C
        ldx     #$ED
        ldy     #$60
L5F5A:  sta     wid
        jsr     call_action_at
        lda     #$2A
        sta     wid
        lda     phase
        cmp     #$01
        beq     L5F6A
        rts

L5F6A:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$01
        lda     #$FF
        sta     (ptr),y
        lda     #$0B
        sta     wid
        lda     arg1
        jmp     announce_move

; Corps d'action orphelin (cible de la table de verbes $6FAC, entree $6FFD :
; wid=$35). Cherche l'entite arg1 (entity_find) ; si absente, ou si elle a deja
; parle (said != 0), ou si son champ 'reply' est nul -> actq_pull. Sinon tire
; rand_range(reply) : resultat nul -> la creature dit '<ARG1>SAY 'NO '' ($15BE,
; replique d'enigme type Gollum), puis pull. Seul site du bloc 4 qui lit 'reply'
; ((ptr2)+6) des entrees $2B45.
action_talk_to:
        jsr     act_probe
        lda     arg1
        jsr     entity_find
        cmp     #$FF
        php
        lda     #$00
        plp
        beq     L5FA0
        lda     said
        bne     L5FA0
        ldy     #$06
        lda     (ptr2),y
        beq     L5FA0
        jsr     rand_range
        beq     L5FA4
L5FA0:  jsr     actq_pull
        rts

L5FA4:  jsr     print_msg
; -> $15BE <ARG1>SAY 'NO '
msg_5FA7:
        .word   $15BE
code_5FA9:
        lda     #$00
        jmp     L5FA0

; Mort du joueur : '<NAME>DEAD', affiche le score puis relance (code_3C8B)
you_are_dead:
        lda     #$00
        sta     obj
        jsr     print_msg
; -> $13D1 <NAME>DEAD
msg_5FB5:
        .word   $13D1
code_5FB7:
        jsr     score_show
        jmp     code_3C8B

; Lit (orec)+0 moins 1 (index d'objet)
obj_id_minus1:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$00
        lda     (ptr),y
        sec
        sbc     #$01
        rts

        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     obj_flag20_get
        bne     L5FDD
        jmp     name_from_record

L5FDD:  lda     arg1
        jsr     slot_count
        cmp     #$00
        beq     L5FF5
        jsr     act_probe
        jsr     prob_from_arg1
        ldy     #$07
        lda     (ptr),y
        and     #$FB
        sta     (ptr),y
        rts

L5FF5:  lda     #$02
        jmp     name_from_record

L5FFA:  jsr     act_probe
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
        ldy     #$00
        lda     (ptr),y
        tax
        ldy     #$10
L600C:  lda     (ptr),y
        cmp     eloc
        beq     L6019
        iny
        dex
        bne     L600C
        jmp     cannot_do

L6019:  iny
        lda     (ptr),y
        dex
        bne     L6021
        lda     #$00
L6021:  pha
        jsr     print_msg
; -> $11D3 AND IT GET SWEPT AWAY
msg_6025:
        .word   $11D3
code_6027:
        pla
        ldy     #$10
        sta     (orec),y
        tax
        ldy     #$01
        lda     #$FF
        sta     (orec),y
        lda     arg1
        jsr     event_arm_obj
        lda     $1B2A
        bne     L6040
        jmp     you_are_dead

L6040:  rts

; Index 13. Transfert d'objet d'un contenant a l'autre : selon (orec2)+4 & $07,
; verifie la capacite via slot_alloc3 ; si le contenant est trop plein, affiche
; '<ARG2>IS TOO FULL' ($11F1) ; sinon deplace le contenu (champ +$10 et porteur).
act_p14_13:
        jsr     light_gate
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$04
        lda     (orec2),y
        and     #$07
        bne     L6057
        jmp     act_look

L6057:  cmp     #$06
        beq     L5FFA
        lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        ldy     #$07
        lda     (ptr2),y
        and     #$20
        beq     L609A
        ldy     #$02
        lda     (ptr2),y
        sec
        sbc     (ptr),y
        bcc     L6084
        pha
        lda     arg2
        jsr     slot_alloc3
        sta     $6C
        pla
        sec
        sbc     $6C
        beq     L6084
        bcs     L608A
L6084:  jsr     print_msg
; -> $11F1 <ARG2>IS TOO FULL
msg_6087:
        .word   $11F1
code_6089:
        rts

L608A:  jsr     act_probe
        ldy     #$10
        lda     (ptr2),y
        sta     (ptr),y
        lda     arg2
        ldy     #$01
        sta     (ptr),y
        rts

L609A:  lda     #$05
        jmp     L5A90

        jsr     act_probe
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$01
        cmp     #$FF
        beq     act_p14_00
        jsr     locate_object
        ldy     #$07
        lda     (ptr),y
        and     #$FD
        sta     (ptr),y
        lda     #$01
        bne     L60C4
; Index 0. Ajoute $0A au compteur (crec)+5 de l'objet ; en cas de debordement
; (resultat negatif) la creature meurt de gloutonnerie ('... FOUL GLUTTONY HAS
; KILLED <OBJ>.' $1525) et est retiree du jeu (unit_remove) ; sinon la cible
; (orec)+1 recoit $FF et ses 16 octets de queue (orec)+$10.. sont effaces.
act_p14_00:
        jsr     act_probe
        lda     #$0A
L60C4:  ldy     #$05
        clc
        adc     (crec),y
        bmi     L60E3
        sta     (crec),y
        ldy     #$01
        lda     #$FF
        sta     (orec),y
        ldy     #$00
        lda     (orec),y
        tax
        ldy     #$10
L60DA:  lda     #$00
        sta     (orec),y
        iny
        dex
        bne     L60DA
        rts

L60E3:  jsr     print_msg
; -> $1525 <HIS>FOUL GLUTTONY HAS KILLED<OBJ>.
msg_60E6:
        .word   $1525
code_60E8:
        lda     obj
        jmp     unit_remove

; Index 1. Attaque avec l'objet courant : verifie les drapeaux (orec)+7 (bit1
; arme, bit3 deja touche) et, si une cible arg2 est fournie, son autorisation
; (verb_obj_ok $0C) et (orec2)+5>0. Calcule les degats (ratio $15 sur (crec)+5)
; et les retranche au compteur (orec)+6 de la cible ; si la cible tombe, pose
; son bit3, reduit ses compteurs et annonce le resultat via name_from_record.
act_p14_01:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (orec),y
        and     #$02
        beq     L6100
L60FD:  jmp     act_look

L6100:  lda     (orec),y
        and     #$08
        beq     L6109
        jmp     L61C4

L6109:  ldy     #$06
        lda     (orec),y
        beq     L60FD
        lda     #$00
        sta     L6320
        lda     arg2
        cmp     #$FF
        beq     L613E
        ldy     #$05
        lda     (orec2),y
        beq     L60FD
        jsr     push_ptr_ax
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
        lda     #$0C
        jsr     verb_obj_ok
        jsr     fetch_retaddr
        cmp     #$FF
        beq     L60FD
        ldy     #$05
        lda     (orec2),y
        sta     L6320
L613E:  jsr     act_probe
        lda     #$15
        jsr     ratio_scale
        clc
        adc     L6320
        ldy     #$05
        adc     (crec),y
        bcc     L6152
        lda     #$FF
L6152:  ldy     #$06
        sec
        sbc     (orec),y
        bcc     L617D
        ldy     #$07
        lda     (orec),y
        ora     #$08
        sta     (orec),y
        lda     arg1
        jsr     obj_state_clear
        ldy     #$05
        lda     (orec),y
        lsr     a
        sta     (orec),y
        ldy     #$04
        lda     (orec),y
        cmp     #$02
        bcs     L6178
        jsr     prob_from_arg1
L6178:  lda     #$83
        jsr     name_from_record
L617D:  lda     arg2
        cmp     #$FF
        bne     L6184
        rts

L6184:  ldy     #$07
        lda     (orec2),y
        and     #$08
        beq     L618D
        rts

L618D:  lda     #$15
        jsr     ratio_scale
        ldy     #$06
        clc
        adc     (orec2),y
        bcc     L619B
        lda     #$FF
L619B:  lda     #$06
        sec
        sbc     (orec),y
        bcs     L61A3
        rts

L61A3:  ldy     #$07
        lda     (orec2),y
        ora     #$08
        sta     (orec2),y
        lda     arg2
        jsr     obj_state_clear
        ldy     #$05
        lda     (orec2),y
        lsr     a
        sta     (orec2),y
        lda     arg2
        jsr     prob_scan
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
L61C4:  lda     #$83
        jmp     name_from_record

; Index 2. Selon le flag bit5 de (orec)+7 : s'il est clair, affiche le nom de
; l'objet ; s'il est pose, (act_probe) l'efface et rend la main.
act_p14_02:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     obj_flag20_get
        bne     L61D9
        jmp     name_from_record

L61D9:  jsr     act_probe
L61DC:  ldy     #$07
        lda     (ptr),y
        and     #$DF
        sta     (ptr),y
        rts

; Index 7. Allume/eteint un objet a lumiere : item_flag_test sur arg2 ; si
; l'objet est absent, decrit le lieu (act_look) ; sinon, selon le bit5 de
; (ptr2)+7, retire le flag et arme l'evenement lie a arg1.
act_p14_07:
        jsr     light_gate
        lda     arg2
        jsr     item_flag_test
        cmp     #$FF
        bne     L61F4
        jmp     act_look

L61F4:  lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        ldy     #$07
        lda     (ptr2),y
        and     #$20
        php
        lda     #$05
        plp
        bne     L620B
        jmp     L5A90

L620B:  jsr     act_probe
        ldy     #$02
        lda     (ptr),y
        tax
        ldy     #$10
        sta     (orec),y
        lda     #$FF
        ldy     #$01
        sta     (orec),y
        lda     arg1
        jmp     event_arm_obj

; Index 3. Si le flag bit0 de (orec)+7 est deja pose, affiche le nom ; sinon
; (act_probe) pose le bit5 de (ptr)+7 et, pour l'objet d'id $01 dont arg1 n'est
; pas visible, declenche l'annonce des objets visibles (list_visible_init).
act_p14_03:
        jsr     obj_flag1_test
        beq     L622A
        jmp     name_from_record

L622A:  jsr     act_probe
L622D:  ldy     #$07
        lda     (ptr),y
        ora     #$20
        sta     (ptr),y
        ldy     #$00
        lda     (ptr),y
        cmp     #$01
        beq     L623E
        rts

L623E:  lda     arg1
        jsr     obj_visible
        bcc     L6246
        rts

L6246:  ldy     #$10
        lda     (ptr),y
        tax
        lda     arg1
        jmp     list_visible_init

; Remet a zero le flag (mask $10) de (orec)+4 selon le contexte
obj_flag_clear:
        ldy     #$04
        lda     obj
        bne     L6262
        lda     (orec),y
        and     #$10
        beq     L6262
        lda     (orec),y
        and     #$EF
        sta     (orec),y
L6262:  lda     (orec),y
        and     #$70
        and     (crec),y
        bne     L626B
        rts

L626B:  pla
        pla
        lda     #$00
        sta     passok
        rts

; Verbe Strike with ($0B) : combat, ratio de force
action_strike:
        jsr     obj_flag_clear
        lda     #$F6
        sta     wptr
        lda     #$03
        sta     wptr_hi
        lda     arg2
        cmp     #$FF
        beq     L628E
        ldy     #$08
        lda     (orec2),y
        sta     wptr
        iny
        lda     (orec2),y
        sta     wptr_hi
L628E:  ldy     #$05
        lda     (crec),y
        sta     L6320
        lda     arg2
        cmp     #$FF
        beq     L62B8
        ldy     #$00
        lda     (orec2),y
        cmp     #$01
        beq     L62A9
        jsr     print_msg
; -> $133F YOU CANNOT KILL WITH<ARG2>.
msg_62A6:
        .word   $133F
code_62A8:
        rts

L62A9:  ldy     #$05
        lda     (orec2),y
        clc
        adc     L6320
        bcc     L62B5
        lda     #$FF
L62B5:  sta     L6320
L62B8:  lda     L6320
        jsr     counter_add_ratio
        sta     L6320
        jsr     act_probe
        ldy     #$06
        lda     (orec),y
        jsr     counter_add_ratio
        cmp     L6320
        bcc     L62D6
        jsr     print_msg
; -> $1330 BUT THE EFFORT IS WASTED.<HIS>DEFENSE IS TOO STRONG
msg_62D3:
        .word   $1330
code_62D5:
        rts

L62D6:  sta     L6321
        clc
        adc     #$10
        bcc     L62E0
        lda     #$FF
L62E0:  cmp     L6320
        bcc     code_6322
        lda     L6320
        sec
        sbc     L6321
        asl     a
        tax
        lda     L6359,x
        sta     msg_631D
        lda     L635A,x
        sta     msg_631D+1
        txa
        lsr     a
        lsr     a
        sta     L6321
        eor     #$FF
        clc
        ldy     #$05
        adc     (orec),y
        bcc     L630B
        sta     (orec),y
L630B:  lda     L6321
        lsr     a
        eor     #$FF
        clc
        ldy     #$06
        adc     (orec),y
        bcc     L631A
        sta     (orec),y
L631A:  jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : message de degats choisi dans $6359/$635A
msg_631D:
        .word   $0000
code_631F:
        rts

L6320:  .byte   $00
L6321:  .byte   $00
code_6322:
        jsr     print_msg
; -> $1212 WITH ONE WELL PLACE BLOW<OBJ>CLEAVE<HIS>SKULL
msg_6325:
        .word   $1212
code_6327:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        ora     #$08
        sta     (ptr),y
        lda     arg1
        jsr     unit_remove
        lda     #$06
        jmp     name_from_record

; Ajoute un ratio (0-10 obtenu via ratio_scale) a une valeur : borne le resultat
; entre $00 et $FF (saturation) et rend la somme. Utilise pour les compteurs de
; degats ou de competences.
counter_add_ratio:
        sta     L635A
        lda     #$0A
        jsr     ratio_scale
        tax
        clc
        adc     L635A
        bcc     L6359
        txa
        bmi     L6357
        lda     #$FF
        bne     L6359
L6357:  lda     #$00
L6359:  rts

L635A:  .byte   $00,$16,$13,$05,$13,$FA,$12,$EF
        .byte   $12,$E3,$12,$CE,$12,$BC,$12,$AB
        .byte   $12,$94,$12,$86,$12,$71,$12,$64
        .byte   $12,$52,$12,$48,$12,$31,$12,$20
        .byte   $12
; Verbe Inventory ($1A) : liste ce que porte le joueur
action_inventory:
        jsr     act_probe
        jsr     print_msg
; -> $11CD <NAME>CARRYING.
msg_6381:
        .word   $11CD
code_6383:
        lda     obj
        jsr     slot_count
        cmp     #$00
        bne     L6392
        jsr     print_msg
; -> $171B NOTHING
msg_638F:
        .word   $171B
code_6391:
        rts

L6392:  lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        tax
        lda     obj
        jmp     list_visible_init

; Verbe Examine ($1C) : affiche le message propre de l'objet
action_examine:
        jsr     act_probe
        lda     arg1
        jsr     locate_object
        ldy     #$0E
        lda     (ptr),y
        sta     msg_63C1
        iny
        lda     (ptr),y
        sta     msg_63C1+1
        ora     msg_63C1
        beq     L63C4
        jsr     print_msg
; TODO pointeur $0000 : slot rempli au runtime : message d'objet lu dans la fiche ((ptr)+$0E)
msg_63C1:
        .word   $0000
code_63C3:
        rts

L63C4:  jsr     print_msg
; -> $13E0 <OBJ>SEE
msg_63C7:
        .word   $13E0
code_63C9:
        lda     ptr
        sta     ptr2
        lda     ptr_hi
        sta     ptr2_hi
        jsr     record_copy8
        lda     #$2E
        jsr     putchar
        jmp     print_cr

; Verbe Give To ($1D) : verifie poids/lumiere puis donne l'objet
action_give:
        lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        jsr     light_from_arg1
        bcs     L63EF
        jsr     print_msg
; -> $11C8 <NAME>NOT CARRYING IT.
msg_63EC:
        .word   $11C8
code_63EE:
        rts

L63EF:  lda     arg2
        jsr     slot_alloc2
        ldy     #$03
        clc
        adc     (ptr),y
        sta     $6C
        lda     (ptr2),y
        sec
        sbc     $6C
        bcs     L6408
        jsr     print_msg
; -> $11E3 <NAME>CARRYING TOO MUCH
msg_6405:
        .word   $11E3
code_6407:
        rts

L6408:  jsr     act_probe
        lda     arg2
        ldy     #$01
        sta     (orec),y
        ldy     #$10
        lda     (ptr2),y
        sta     (orec),y
        tax
        lda     arg1
        jmp     event_arm_obj

L641D:  jsr     obj_flag1_test
        beq     L6425
        jmp     name_from_record

L6425:  lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        ldy     #$07
        lda     (ptr2),y
        and     #$08
        php
        lda     #$83
        plp
        beq     L643C
        jmp     L5A90

L643C:  jsr     act_probe
        ldy     #$07
        lda     (ptr),y
        ora     #$01
        sta     (ptr),y
        rts

L6448:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        and     #$01
        php
        lda     #$00
        plp
        bne     L645F
L645C:  jmp     name_from_record

L645F:  jsr     obj_flag20_test
        bne     L645C
        lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        ldy     #$07
        lda     (ptr2),y
        and     #$08
        php
        lda     #$83
        plp
        beq     L647B
        jmp     L5A90

L647B:  jsr     act_probe
        ldy     #$07
        lda     (ptr),y
        and     #$FE
        sta     (ptr),y
        rts

L6487:  lda     #$00
        sta     dflag
        lda     #$04
        jsr     rand_range
        asl     a
        sta     $6C
        asl     a
        clc
        adc     $6C
        adc     #$26
        sta     $C1
        lda     #$00
        adc     #$71
        sta     $C2
        ldy     #$01
        lda     ($C1),y
        sta     ptr2
        iny
        lda     ($C1),y
        sta     ptr2_hi
        ldy     #$02
L64AE:  lda     #$00
        sta     (ptr2),y
        dey
        bpl     L64AE
        lda     #$03
        jsr     rand_range
        asl     a
        asl     a
        clc
        adc     #$16
        sta     $BF
        lda     #$00
        adc     #$71
        sta     $C0
        jsr     img_poke
        bne     L64CD
        rts

L64CD:  lda     #$00
        sta     (ptr2),y
        iny
        lda     #$10
        sta     (ptr2),y
        rts

; Teste le bit5 de (ptr)+7 (utilitaire d'action)
obj_flag20_get:
        ldy     #$07
        lda     (ptr),y
        and     #$20
        php
        lda     #$05
        plp
        rts

; Arme l'evenement e0 (minuterie 2) si le tonneau a atteint Forestriver
evt_arme0:
        lda     arg1
        cmp     #$13
        beq     L64E9
        rts

L64E9:  jsr     probe_guard
        lda     $1D94
        cmp     #$21
        beq     L64F4
        rts

L64F4:  lda     #$02
        sta     $2B13
        rts

        .byte   $20,$86,$53,$60,$20,$86,$53,$20
        .byte   $0D,$44,$DA,$14,$4C,$6E,$66,$A0
        .byte   $07,$B1,$17,$29,$08,$D0,$01,$60
        .byte   $B1,$17,$29,$F7,$91,$17,$A2,$00
        .byte   $A5,$15,$DD,$76,$65,$F0,$08,$8A
        .byte   $18,$69,$06,$AA,$4C,$1A,$65,$BD
        .byte   $77,$65,$85,$88,$BD,$78,$65,$85
        .byte   $89,$A5,$15,$A0,$00,$91,$88,$A0
        .byte   $10,$BD,$79,$65,$91,$17,$48,$A0
        .byte   $0A,$BD,$7A,$65,$91,$17,$C8,$BD
        .byte   $7B,$65,$91,$17,$20,$0D,$44,$48
        .byte   $14,$68,$CD,$2A,$1B,$F0,$01,$60
        .byte   $A9,$A6,$85,$5C,$A9,$00,$85,$5D
        .byte   $20,$41,$42,$A9,$B1,$85,$5C,$A9
        .byte   $04,$85,$5D,$20,$41,$42,$20,$0D
        .byte   $44,$F7,$13,$60,$3D,$92,$2B,$0F
        .byte   $28,$07,$45,$99,$2B,$3A,$35,$05
        .byte   $49,$A7,$2B,$12,$65,$05,$4A,$AE
        .byte   $2B,$38,$B5,$06,$4B,$A0,$2B,$40
        .byte   $6B,$0B,$4C,$B5,$2B,$10,$D8,$02
        .byte   $A0,$10,$B1,$C6,$C9,$10,$F0,$03
        .byte   $4C,$62,$5A
; Arme l'evenement e3 (minuterie = id) apres une action
evt_arme3:
        jsr     act_p14_03
        jsr     probe_guard
        lda     $2B21
        sta     $2B22
        rts

        .byte   $A9,$02,$D0,$06
; Index 12 (type $0F). Meme aiguillage que l'index 8, avec le type $0F : si
; arg2=$0F, vers L641D ($wid=$25) ou L6448 ; sinon act_p14_06 / cannot_do.
act_p14_12:
        lda     #$0F
        bne     L65BC
; Index 8 (type $04). Aiguille selon le type reel de arg2 : si arg2=$04, vers
; L641D ($wid=$25) ou L6448 ; sinon act_p14_06 ($02/$04/$0F) ou cannot_do.
act_p14_08:
        lda     #$04
L65BC:  cmp     arg2
        bne     L65CC
        lda     wid
        cmp     #$25
        bne     L65C9
        jmp     L641D

L65C9:  jmp     L6448

L65CC:  lda     arg2
        cmp     #$02
        beq     act_p14_06
        cmp     #$04
        beq     act_p14_06
        cmp     #$0F
        beq     act_p14_06
        jmp     cannot_do

; Index 6. Affiche '<ARG2>DO NOT FIT THIS LOCK' ($140C) : l'objet ne va pas
; sur cette serrure, ou l'action est impossible.
act_p14_06:
        jsr     print_msg
; -> $140C <ARG2>DO NOT FIT THIS LOCK
msg_65E0:
        .word   $140C
code_65E2:
        rts

        jsr     probe_guard
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jmp     L622D

; Index 10. Lit le champ (crec)+$10 : s'il vaut $0F, poursuit en act_p14_03 ;
; sinon decrit le lieu (act_look).
act_p14_10:
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        cmp     #$0F
        beq     L6604
        jmp     act_look

L6604:  jmp     act_p14_03

        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        cmp     #$20
        beq     L661D
        jsr     print_msg
; -> $14FD YOU CANNOT REACH<ARG1>.
msg_661A:
        .word   $14FD
code_661C:
        rts

L661D:  lda     wid
        cmp     #$0D
        bne     L6626
        jmp     act_p14_02

L6626:  jmp     act_p14_03

        jsr     weapon_test_a
        ldy     #$02
        lda     (ptr),y
        bne     L6636
        jsr     act_probe
        rts

L6636:  ldy     #$00
        lda     wid
        pha
        lda     arg1
        pha
        lda     (ptr),y
        sta     wid
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        pha
        ora     #$20
        sta     (ptr),y
        lda     #$FF
        sta     arg1
        jsr     combat_round
        pla
        ldy     #$07
        sta     (orec),y
        pla
        sta     arg1
        pla
        sta     wid
        rts

        jsr     act_probe
        jsr     print_msg
; -> $1494 AS SOON AS<OBJ>TOUCH THE RIVER<OBJ>FALL ASLEEP AND GENTLY FLOAT 
msg_666C:
        .word   $1494
code_666E:
        lda     obj
        pha
        bne     code_6678
        jsr     print_msg
; -> $1181 TIME PASSES...
msg_6676:
        .word   $1181
code_6678:
        pla
        jmp     unit_remove

L667C:  lda     $1CCB
        and     #$80
        beq     evt_disarme6
        jsr     print_msg
; -> $1454 <NAME>NOT WEARING<ARG1>.
msg_6686:
        .word   $1454
code_6688:
        rts

; Desarme l'evenement e6 (remet sa minuterie a zero)
evt_disarme6:
        jsr     act_probe
        ldy     #$07
        lda     (crec),y
        ora     #$80
        sta     (crec),y
        lda     $1CCB
        ora     #$80
        sta     $1CCB
        ldy     #$05
        lda     (crec),y
        asl     a
        asl     a
        sta     (crec),y
        lda     #$00
        sta     $2B31
        rts

; Arme l'evenement e6 avec un delai aleatoire (2 a 10)
evt_arme6:
        jsr     act_probe
        ldy     #$07
        lda     (crec),y
        and     #$7F
        sta     (crec),y
        ldy     #$05
        lda     (crec),y
        lsr     a
        lsr     a
        sta     (crec),y
        lda     $1CCB
        and     #$7F
        sta     $1CCB
        lda     obj
        sta     $1CC5
        lda     #$08
        jsr     rand_range
        clc
        adc     #$02
        sta     $2B31
        rts

; Index 11 (araignees). Si le bit3 de (orec)+7 est pose : pose le bit5, arme
; l'evenement e1 ($2B17 -> $2B18) et annonce 'SOME SPIDERS START MEND THE
; BROKEN WEB' ($1478) ; sinon ne fait rien.
act_p14_11:
        ldy     #$07
        lda     (orec),y
        and     #$08
        bne     L66DF
        rts

L66DF:  lda     (orec),y
        ora     #$20
        sta     (orec),y
        lda     $2B17
        sta     $2B18
        jsr     print_msg
; -> $1478 SOME SPIDERS START MEND THE BROKEN WEB
msg_66EE:
        .word   $1478
code_66F0:
        rts

; Contenant (ex. BARREL) : verifie l'interieur puis y met/sort l'objet
act_p14_35:
        ldy     #$01
        lda     (crec),y
        cmp     arg1
        bne     L66FC
L66F9:  jmp     act_look

L66FC:  lda     orec
        sta     ptr2
        lda     orec_hi
        sta     ptr2_hi
        lda     arg1
        jsr     act_try_obj
        beq     L66F9
        lda     arg1
L670D:  jsr     locate_object
        ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L6720
        cmp     obj
        bne     L670D
        lda     #$FF
        sta     (orec),y
L6720:  lda     obj
        jsr     slot_alloc3
        ldy     #$02
        clc
        adc     (crec),y
        bcc     L672E
        lda     #$FF
L672E:  sta     L675F
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     obj_flag20_get
        bne     L6741
        jmp     name_from_record

L6741:  ldy     #$02
        lda     (ptr),y
        cmp     #$FF
        beq     L6755
        sec
        sbc     L675F
        bcs     L6755
        jsr     print_msg
; -> $151D <NAME>TOO BIG
msg_6752:
        .word   $151D
code_6754:
        rts

L6755:  jsr     act_probe
        lda     arg1
        ldy     #$01
        sta     (crec),y
        rts

L675F:  .byte   $00
; Verbe Capture ($30) : tente d'attraper un animal (flag bit6)
action_capture:
        ldy     #$04
        lda     (orec),y
        and     #$70
        and     (crec),y
        beq     L676D
L676A:  jmp     act_look

L676D:  ldy     #$07
        lda     (orec),y
        and     #$40
        beq     L676A
        lda     obj
        ldx     #$1F
        cmp     #$40
        beq     L6783
        cmp     #$42
        beq     L6783
        ldx     #$0D
L6783:  cpx     eloc
        beq     L676A
        stx     L67C9
        jsr     act_probe
        ldy     #$10
        lda     L67C9
        sta     (orec),y
        ldy     #$01
        lda     #$FF
        sta     (orec),y
        lda     arg1
        ldx     L67C9
        jsr     event_arm_obj
        lda     arg1
        cmp     #$00
        beq     L67A9
        rts

L67A9:  sta     obj
        lda     #$1A
        sta     crec
        lda     #$1B
        sta     crec_hi
        jsr     is_dark
        bcc     L67B9
        rts

L67B9:  lda     #$DC
        sta     msg_4DFC
        lda     #$13
        sta     msg_4DFC+1
        lda     L67C9
        jmp     L4DE9

L67C9:  .byte   $85
; Verbe Untie ($33) : defait un lien
action_untie:
        ldy     #$01
        lda     (orec),y
        cmp     #$12
        beq     L67D8
        jsr     print_msg
; -> $1473 <ARG1>IS NOT TIED
msg_67D5:
        .word   $1473
code_67D7:
        rts

L67D8:  jsr     act_probe
        lda     $1D08
        ldy     #$01
        sta     (orec),y
        rts

; Verbe Tie To ($2E) : noue un objet a une cible
action_tie:
        lda     arg1
        cmp     #$12
        beq     L6857
        lda     arg2
        cmp     #$12
        beq     L67FA
L67EF:  lda     arg1
        ldx     arg2
        sta     arg2
        stx     arg1
        jmp     act_look

L67FA:  jsr     obj_id_minus1
        bne     L67EF
        ldy     #$07
        lda     (orec),y
        and     #$02
        bne     L67EF
        lda     arg2
        jsr     slot_count
        cmp     #$00
        beq     L6816
        jsr     print_msg
; -> $1460 <ARG2>IS ALREADY TIED
msg_6813:
        .word   $1460
code_6815:
        rts

L6816:  ldy     #$07
        lda     (orec),y
        and     #$08
        bne     L682B
        lda     (orec),y
        and     #$40
        bne     L67EF
        lda     arg2
        jsr     light_from_a
        bcc     L67EF
L682B:  jsr     act_probe
        jsr     light_from_arg1
        lda     arg2
        ldy     #$01
        sta     (orec),y
        bcs     L684C
        lda     #$00
        sta     phase
        jsr     action_pickup
        lda     passok
        php
        lda     #$01
        sta     phase
        sta     passok
        plp
        beq     L6853
L684C:  lda     obj
L684E:  ldy     #$01
        sta     (orec2),y
        rts

L6853:  lda     #$FF
        bne     L684E
L6857:  ldx     #$E3
        ldy     #$67
        jmp     call_action_at

; Verbe Burn ($2D) : met le feu a un objet
action_burn:
        lda     obj
        cmp     #$3C
        beq     L6867
        jmp     act_look

L6867:  jsr     act_probe
        jmp     code_4D45

; Verbe Climb Out Of ($37) : sort d'un contenant/lieu
action_climb_out:
        ldy     #$01
        lda     arg1
        cmp     (crec),y
        beq     L6878
        jmp     act_look

L6878:  jsr     locate_object
        jsr     obj_flag20_get
        bne     L6883
        jmp     name_from_record

L6883:  jsr     act_probe
        ldy     #$01
        lda     #$FF
        sta     (crec),y
        rts

; Action de l'evenement e0 : le tonneau atteint le Long Lake, joueur jete sur la berge
evt_act0:
        lda     #$00
        sta     L4E58
        lda     $1B1B
        cmp     #$13
        bne     code_689E
        jsr     print_msg
; -> $170C YOU ARE THROWN ONTO THE BANK OF THE LONG LAKE
msg_689C:
        .word   $170C
code_689E:
        lda     #$22
        sta     $1D94
        tax
        lda     #$13
        jsr     event_arm_obj
        lda     #$20
        sta     $1D94
        lda     $1D8B
        and     #$DF
        ora     #$04
        sta     $1D8B
        lda     #$00
        sta     outen
        lda     #$13
        jsr     prob_scan
        lda     #$01
        sta     outen
        lda     #$20
        sta     $1DB8
        lda     #$13
        sta     $1DA9
        rts

; PNJ (Gandalf ?) : s'il est au meme endroit que le joueur, dit 'HELLO' ($143F).
act_v14_06:
        lda     eloc
        cmp     ploc
        beq     L68D7
        rts

L68D7:  jsr     act_probe
        jsr     act_msg
; -> $143F HELLO
msg_68DD:
        .word   $143F
code_68DF:
        rts

; PNJ oisif : tirage 0-2. 0 -> 'YOU ARE DO A GREAT JOB' ($1432) ; 1 -> 'HURRY UP'
; ($143B) ; 2 -> 'HELLO' ($143F).
act_v14_01:
        jsr     act_probe
        lda     #$02
        jsr     rand_range
        cmp     #$00
        bne     L68F2
        jsr     act_msg
; -> $1432 YOU ARE DO A GREAT JOB
msg_68EF:
        .word   $1432
code_68F1:
        rts

L68F2:  cmp     #$01
        bne     L68FC
        jsr     act_msg
; -> $143B HURRY UP
msg_68F9:
        .word   $143B
code_68FB:
        rts

L68FC:  jsr     act_msg
; -> $143F HELLO
msg_68FF:
        .word   $143F
code_6901:
        rts

        rts

        lda     $1CF3
        and     #$DF
        sta     $1CF3
        rts

; PNJ : dit 'THIS WAS THRAINS KEY' (message $1441).
act_v14_02:
        jsr     act_probe
        jsr     act_msg
; -> $1441 THIS WAS THRAINS KEY
msg_6912:
        .word   $1441
code_6914:
        rts

; Tirage (~20%) : affiche 'expect me'
evt_tip:jsr     act_probe
        lda     #$0A
        jsr     rand_range
        cmp     #$08
        bcc     L6927
        jsr     act_msg
; -> $1485 WHAT DO YOU EXPECT ME TO DO WITH THIS ?
msg_6924:
        .word   $1485
code_6926:
        rts

L6927:  jsr     act_msg
; -> $1423 THANK YOU
msg_692A:
        .word   $1423
code_692C:
        rts

; PNJ : dit 'WHAT'S THIS ?' (message $1427).
act_v14_00:
        jsr     act_probe
        jsr     act_msg
; -> $1427 WHAT'S THIS ?
msg_6933:
        .word   $1427
code_6935:
        rts

; PNJ : tirage 0-7. >= 5 : rien ; 3-4 : ajuste un compteur en silence ; 0-2 : dit
; 'HURRY UP' ($143B), en decrementant aussi un compteur quand le tirage vaut 0.
act_v14_04:
        jsr     act_probe
        lda     #$08
        jsr     rand_range
        cmp     #$05
        bcc     L6943
        rts

L6943:  cmp     #$03
        bcc     L694D
        jsr     print_via_stack
        dec     $14,x
        rts

L694D:  cmp     #$03
        bne     L6952
        rts

L6952:  cmp     #$00
        bne     code_695C
        jsr     print_via_stack
        .byte   $C7,$14,$60
code_695C:
        jsr     act_msg
; -> $143B HURRY UP
msg_695F:
        .word   $143B
code_6961:
        rts

; PNJ : s'il est au meme endroit que le joueur et que le drapeau $1B21 bit7 est
; clair, dit 'WHERE'S THE THIEF ?' ($14AB).
act_v14_03:
        lda     eloc
        cmp     ploc
        beq     L6969
        rts

L6969:  lda     $1B21
        and     #$80
        beq     L6971
        rts

L6971:  jsr     act_probe
        jsr     act_msg
; -> $14AB WHERE'S THE THIEF ?
msg_6977:
        .word   $14AB
code_6979:
        rts

; PNJ : si le joueur se trouve dans le lieu $1DE0, ajuste un compteur (L4D9E).
act_v14_05:
        jsr     act_probe
        lda     ploc
        cmp     $1DE0
        beq     L6985
        rts

L6985:  jsr     print_via_stack
        ror     $14
        rts

; Verbe Shoot ($3A) : tire une fleche (arme)
action_shoot:
        lda     #$19
        jsr     light_from_a
        bcs     L6998
        jsr     print_msg
; -> $1503 <NAME>NOT CARRYING THE BOW
msg_6995:
        .word   $1503
code_6997:
        rts

L6998:  jsr     obj_flag_clear
        jsr     act_probe
        lda     #$0B
        sta     wid
        lda     obj
        cmp     #$46
        beq     L69BD
        lda     arg1
        cmp     #$3C
        bne     L69B4
L69AE:  jsr     print_msg
; -> $1509 THE ARROW MISS<ARG2>BY A WIDE MARGIN
msg_69B1:
        .word   $1509
code_69B3:
        rts

L69B4:  lda     #$08
        jsr     rand_range
        cmp     #$03
        bcc     L69AE
L69BD:  lda     arg1
        cmp     #$1A
        beq     L69C8
        lda     #$FF
        sta     $1E74
L69C8:  jsr     print_msg
; -> $1516 THE ARROW HIT<ARG1>.
msg_69CB:
        .word   $1516
code_69CD:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     obj_flag48_test
        beq     L69DD
        jmp     act_p14_01

L69DD:  lda     arg1
        jsr     unit_remove
        lda     #$06
        jmp     name_from_record

; Teste la condition de victoire ($1F38 == $25) ; si elle est remplie, la foule
; acclame (message $1722), ajoute au score et termine la partie (code_5FB7).
; Appelee au tout debut de world_tick (avant les PNJ).
victory_check:
        lda     $1F38
        cmp     #$25
        beq     L69EF
        rts

L69EF:  jsr     print_msg
; -> $1722 A CHEERING CROWD OF DWARVES, HOBBITS AND ELVES APPEAR. LED BY GA
msg_69F2:
        .word   $1722
code_69F4:
        lda     $CC
        clc
        adc     #$FA
        sta     $CC
        bcc     L69FF
        inc     $CD
L69FF:  jmp     code_5FB7

        jsr     probe_guard
        lda     obj
        beq     L6A0A
        rts

L6A0A:  jsr     print_msg
; -> $1380 WITH A LURCH THE BOAT GLIDES ACROSS THE RIVER AND LAND ON THE OT
msg_6A0D:
        .word   $1380
code_6A0F:
        jmp     code_6A6E

        lda     obj
        cmp     #$00
        beq     evt_disarme7
        rts

; Desarme l'evenement e7 dans un cas particulier (objet present)
evt_disarme7:
        lda     #$01
        sta     sflag
        lda     $2B35
        sta     $2B36
        rts

        ldy     #$10
        lda     (orec),y
        sta     L6A5C
        jsr     item_flag_test2
        cmp     #$FF
        bne     L6A38
L6A32:  jsr     print_msg
; -> $16E1 <OBJ>CANNOT JUMP ONTO<ARG1>FROM HERE.
msg_6A35:
        .word   $16E1
code_6A37:
        rts

L6A38:  ldy     #$00
        lda     (ptr),y
        cmp     #$0A
        bne     L6A32
        jsr     act_probe
        ldx     L6A5C
        lda     arg1
        ldy     #$01
        sta     (crec),y
        jsr     event_arm_obj
        lda     obj
        cmp     #$00
        beq     L6A56
        rts

L6A56:  lda     L6A5C
        jmp     L4DC6

L6A5C:  .byte   "N`"
code_6A5E:
        jsr     act_probe
        lda     $1F76
        cmp     #$12
        beq     L6A69
        rts

L6A69:  jsr     print_msg
; -> $1370 THE BOAT GLIDES ACROSS THE RIVER AND LAND ON THIS SIDE.
msg_6A6C:
        .word   $1370
code_6A6E:
        lda     $1F85
        ldx     #$42
        cmp     #$42
        bne     L6A79
        ldx     #$43
L6A79:  stx     $1F85
        lda     #$FF
        sta     $1F76
        lda     #$29
        jmp     event_arm_obj

        lda     arg2
        jsr     item_flag_test
        cmp     #$FF
        bne     L6A92
        jmp     act_look

L6A92:  jsr     act_probe
        jsr     print_msg
; -> $1346 IT SAIL ACROSS AND
msg_6A98:
        .word   $1346
code_6A9A:
        lda     $1F85
        ldy     #$02
        cmp     (ptr),y
        bne     L6AC4
        jsr     rand_half
        bcs     L6AB9
        jsr     rand_half
        bcs     L6AB3
        jsr     print_msg
; -> $1367 <0B>SOON SLIDE OUT AGAIN
msg_6AB0:
        .word   $1367
code_6AB2:
        rts

L6AB3:  jsr     print_msg
; -> $1355 FALL JUST SHORT OF THE OTHER SIDE.
msg_6AB6:
        .word   $1355
code_6AB8:
        rts

L6AB9:  lda     #$12
        sta     $1F76
        jsr     print_msg
; -> $1361 LAND IN THE BOAT
msg_6AC1:
        .word   $1361
code_6AC3:
        rts

L6AC4:  jsr     rand_half
        bcs     L6AB3
        ldy     #$02
        lda     (ptr),y
        ldy     #$10
        sta     (orec),y
        tax
        lda     #$FF
        ldy     #$01
        sta     (orec),y
        lda     arg1
        jsr     event_arm_obj
        jsr     print_msg
; -> $134D LAND ON THE OTHER SIDE.
msg_6AE0:
        .word   $134D
code_6AE2:
        rts

; Tirage 0-99 compare a 50 (rend C=1 si superieur ou egal)
rand_half:
        lda     #$64
        jsr     rand_range
        cmp     #$32
        rts

; Arme l'evenement e9 (minuterie 6) puis affiche le trou qui disparait
evt_arme9b:
        jsr     probe_guard
        lda     #$06
        sta     $2B40
        lda     $1C7B
        and     #$7F
        ora     #$01
        sta     $1C7B
        jmp     evt_print

        lda     obj
        cmp     #$00
        bne     L6B16
        lda     $1B1B
        cmp     #$FF
        beq     L6B10
        jmp     act_look

L6B10:  jsr     print_msg
; -> $14FD YOU CANNOT REACH<ARG1>.
msg_6B13:
        .word   $14FD
code_6B15:
        rts

L6B16:  lda     wid
        cmp     #$0D
        bne     L6B1F
        jmp     act_p14_02

L6B1F:  cmp     #$10
        bne     L6B26
        jmp     act_p14_03

L6B26:  rts

        lda     obj
        cmp     #$00
        bne     L6B3D
        lda     $1B1B
        cmp     #$FF
        beq     L6B37
        jmp     act_look

L6B37:  jsr     print_msg
; -> $14FD YOU CANNOT REACH<ARG1>.
msg_6B3A:
        .word   $14FD
code_6B3C:
        rts

L6B3D:  lda     wid
        cmp     #$1E
        bne     L6B46
        jmp     act_p14_05

L6B46:  cmp     #$0C
        bne     L6B4D
        jmp     act_p14_01

L6B4D:  cmp     #$18
        bne     L6B54
        jmp     act_p14_04

L6B54:  rts

        jsr     act_probe
        ldy     #$07
        lda     (crec),y
        and     #$80
        beq     evt_arme5
        jsr     print_msg
; -> $13D4 <OBJ>SEE NOTHING SPECIAL HERE.
msg_6B63:
        .word   $13D4
code_6B65:
        rts

; Arme l'evenement e5 et affiche 'magic door'
evt_arme5:
        lda     $2B2B
        sta     $2B2C
        jsr     print_msg
; -> $168B THE MAGIC DOOR WARN OF ELVES APPROACH.
msg_6B6F:
        .word   $168B
code_6B71:
        rts

; Index 9. Pour l'objet $41, assemble le message 'GO <W> FROM <MSG> TO GET TO
; <MSG>' ($15AB) a partir de la table des lieux (room_cond_ptr / word_ptr_table)
; et des arguments VM $466F-$4674 ; sinon renvoie vers code_63A4.
act_p14_09:
        lda     obj
        cmp     #$41
        beq     L6B7B
        jmp     action_examine

L6B7B:  jsr     act_probe
        ldy     #$01
        lda     ($C1),y
        sta     ptr2
        iny
        lda     ($C1),y
        sta     ptr2_hi
        iny
        lda     dflag
        bne     L6BA2
        ldx     #$00
L6B90:  tya
        pha
        lda     ($C1),y
        pha
        txa
        tay
        pla
        sta     (ptr2),y
        pla
        tay
        iny
        inx
        cpx     #$03
        bne     L6B90
L6BA2:  ldy     #$05
        lda     ($C1),y
        jsr     room_cond_ptr
        lda     ptr
        sta     L4673
        lda     ptr_hi
        sta     L4674
        ldy     #$00
        lda     ($C1),y
        jsr     room_cond_ptr
        lda     ptr
        sta     L4671
        lda     ptr_hi
        sta     L4672
        ldy     #$03
        lda     ($C1),y
        jsr     word_ptr_table
        lda     adr
        sta     L466F
        lda     adr_hi
        sta     L4670
        jsr     act_msg
; -> $15AB GO<W>FROM<MSG>TO GET TO<MSG>
msg_6BD8:
        .word   $15AB
code_6BDA:
        rts

        lda     $1D51
        and     #$08
        bne     L6BE3
        rts

L6BE3:  jsr     probe_guard
        lda     $1B9D
        ora     #$08
        sta     $1B9D
        lda     #$02
        jsr     obj_state_clear
        lda     #$1A
        sta     ptr2
        lda     #$1B
        sta     ptr2_hi
        lda     #$02
        jsr     act_try_swap
        bne     L6C03
        rts

L6C03:  jsr     print_msg
; -> $14EB THE SMALL CURIOUS KEY SHATTER.
msg_6C06:
        .word   $14EB
code_6C08:
        rts

; Gollum : si le joueur est dans le lieu $1E4B et le drapeau $1B21 bit7 pose,
; affiche un message prealablement construit (pointeur en ($BF)) et arme le
; drapeau said.
act_v14_12:
        lda     $1E4B
        cmp     ploc
        beq     L6C11
        rts

L6C11:  lda     $1B21
        and     #$80
        bne     L6C19
        rts

L6C19:  jsr     act_probe
        ldy     #$02
        lda     ($BF),y
        sta     msg_6C2C
        iny
        lda     ($BF),y
        sta     msg_6C2C+1
        jsr     act_msg
; TODO pointeur $0000 : slot rempli au runtime : message prepare par le jeu (pointeur $BF, Gollum)
msg_6C2C:
        .word   $0000
code_6C2E:
        lda     #$01
        sta     said
        rts

; Action a jouer une seule fois : si once=1 et que la sonde passe, memorise les
; parametres recus dans le script $2A7A (id, wid, arg1, arg2) et rearme le verrou.
act_v14_11:
        lda     once
        cmp     #$01
        beq     L6C3A
        rts

L6C3A:  lda     #$00
        sta     once
        lda     #$01
        jsr     wander_start
        bne     L6C46
        rts

L6C46:  lda     #$00
        sta     passok
        lda     $14
        sta     $2A7B
        lda     arg1
        sta     $2A7C
        lda     arg2
        sta     $2A7D
        lda     #$42
        sta     $2A7A
        rts

; Action de l'evenement e4 : au marais affiche un message, sinon desarme e4
evt_act5:
        lda     ploc
        cmp     #$1D
        beq     L6C6B
        lda     #$00
        sta     $2B27
        rts

L6C6B:  jsr     print_msg
; -> $1535 <NAME>SLOWLY SINK INTO THE BOG
msg_6C6E:
        .word   $1535
code_6C70:
        lda     $2B27
        beq     L6C76
        rts

L6C76:  jmp     you_are_dead

        lda     $1D26
        and     #$DF
        sta     $1D26
        jsr     at_room_1E
        beq     L6C87
        rts

L6C87:  jsr     print_msg
; -> $141C THE MAGIC DOOR CLOSE.
msg_6C8A:
        .word   $141C
code_6C8C:
        rts

; PNJ : dans l'un des lieux $27/$2C/$29 et si le joueur vient d'y entrer (different
; de $1B40), annonce son arrivee : '<message>ENTER.' ($13F6).
act_v14_09:
        lda     ploc
        cmp     #$27
        beq     L6C9C
        cmp     #$2C
        beq     L6C9C
        cmp     #$29
        beq     L6C9C
        rts

L6C9C:  jsr     act_probe
        lda     ploc
        cmp     $1B40
        bne     L6CA7
        rts

L6CA7:  sta     $1B40
        lda     #$01
        sta     outen
        lda     #$38
        sta     L466F
        lda     #$1B
        sta     L4670
        jsr     print_msg
; -> $13F6 <MSG>ENTER.
msg_6CBB:
        .word   $13F6
code_6CBD:
        rts

; Dragon : au meme endroit que le joueur. Selon le drapeau $1B21 bit7, dit soit
; 'PREPARE TO DIE' ($153F), soit l'aveuglement ($155D).
act_v14_10:
        lda     ploc
        cmp     eloc
        beq     L6CC5
        rts

L6CC5:  jsr     act_probe
        lda     $1B21
        and     #$80
        beq     L6CD5
        jsr     print_msg
; -> $153F THE DRAGON SAY 'WELL THIEF YOUR CUNNING HAS FAILED YOU THIS TIME
msg_6CD2:
        .word   $153F
code_6CD4:
        rts

L6CD5:  jsr     print_msg
; -> $155D THE DRAGON SAY 'I MAY NOT BE ABLE TO SEE YOU THIEF BUT I CAN STI
msg_6CD8:
        .word   $155D
code_6CDA:
        rts

; PNJ : au meme endroit que le joueur, simule un combat : wid=$1B, arg1=0, arg2=$FF
; via L5A62, puis act_p14_00 (combat) et L5FAE (mort).
act_v14_16:
        lda     eloc
        cmp     ploc
        beq     L6CE2
        rts

L6CE2:  jsr     act_probe
        lda     #$1B
        sta     wid
        lda     #$00
        sta     arg1
        lda     #$FF
        sta     arg2
        jsr     act_look
        jsr     act_p14_00
        jmp     you_are_dead

; PNJ : au meme endroit, joue une action sur l'objet $26 (wid $1D, arg1 $26) s'il
; ne l'a pas deja fait ($1FC1/$1FB2), et memorise le lieu courant.
act_v14_07:
        lda     eloc
        cmp     ploc
        beq     L6D01
        rts

L6D01:  lda     $1FC1
        beq     L6D0E
        lda     $1FB2
        cmp     #$41
        beq     L6D0E
        rts

L6D0E:  jsr     act_probe
        lda     eloc
        sta     $1FC1
        lda     #$41
        sta     $1FB2
        lda     #$00
        sta     arg2
        lda     #$26
        sta     arg1
        lda     #$1D
        sta     wid
        lda     #$B1
        sta     orec
        lda     #$1F
        sta     orec_hi
        lda     #$1A
        sta     orec2
        lda     #$1B
        sta     orec2_hi
        jsr     act_look
        jmp     action_give

        lda     ploc
        cmp     #$02
        beq     L6D48
        cmp     #$03
        beq     L6D48
        rts

L6D48:  jsr     print_msg
; -> $16F0 <OBJ>SEE SOME PALE BULBOUS EYES STAR AT<OBJ>.
msg_6D4B:
        .word   $16F0
code_6D4D:
        jsr     print_msg
; -> $16FF SOME THING DROP FROM ABOVE AND STING.
msg_6D50:
        .word   $16FF
code_6D52:
        jmp     you_are_dead

        lda     $1C7B
        and     #$20
        beq     L6D5D
        rts

L6D5D:  lda     $2B3F
        sta     $2B40
        lda     $1C7B
        and     #$7F
        sta     $1C7B
        lda     ploc
        cmp     #$2A
        beq     evt_print
        rts

; Affiche le trou qui disparait
evt_print:
        jsr     print_msg
; -> $1685 THE HOLE VANISH.
msg_6D75:
        .word   $1685
code_6D77:
        rts

; Gollum et l'Anneau : au lieu $1E4B. Tirage 0-7 ; >= 4 -> 'WHAT HAS IT GOT IN ITS
; POCKET ?' ($16B9) ; sinon, si l'Anneau ($44) n'est pas la, 'MY PRECIOUS' ($16C8).
act_v14_14:
        lda     ploc
        cmp     $1E4B
        beq     L6D80
        rts

L6D80:  jsr     act_probe
        lda     #$08
        jsr     rand_range
        cmp     #$04
        bcc     L6D92
L6D8C:  jsr     act_msg
; -> $16B9 WHAT HAS IT GOT IN ITS POCKET ?
msg_6D8F:
        .word   $16B9
code_6D91:
        rts

L6D92:  lda     #$44
        cmp     $1CC5
        beq     L6D8C
        jsr     act_msg
; -> $16C8 MY BIRTHDAY PRESENT 'HOW DID WE LOSE IT MY PRECIOUS '
msg_6D9C:
        .word   $16C8
code_6D9E:
        rts

        jsr     print_msg
; -> $16F0 <OBJ>SEE SOME PALE BULBOUS EYES STAR AT<OBJ>.
msg_6DA2:
        .word   $16F0
code_6DA4:
        lda     ploc
        cmp     exploc
        bne     L6DAB
        rts

L6DAB:  lda     #$02
        cmp     exploc
        bne     L6DB3
        lda     #$03
L6DB3:  cmp     ploc
        bne     L6DB8
        rts

L6DB8:  jmp     code_6D4D

; Trou secret vers la Montagne : pose l'etat $0B bit7 puis annonce l'apparition du trou
evt_hole:
        lda     $1C7B
        ora     #$80
        sta     $1C7B
        lda     ploc
        cmp     #$2A
        beq     L6DCA
        rts

L6DCA:  jsr     print_msg
; -> $165A THERE IS A LOUD CRACK AND A HOLE APPEAR ABOUT THREE FEET FROM TH
msg_6DCD:
        .word   $165A
code_6DCF:
        rts

        lda     $1D26
        ora     #$20
        sta     $1D26
        jsr     at_room_1E
        bne     code_6DE2
        jsr     print_msg
; -> $1415 THE MAGIC DOOR OPEN.
msg_6DE0:
        .word   $1415
code_6DE2:
        jsr     at_room_1E
        bne     code_6DEC
        jsr     print_msg
; -> $14F5 AN ELF SWEEPS PAST
msg_6DEA:
        .word   $14F5
code_6DEC:
        jmp     L6E35

; Verifie si le joueur se trouve dans le lieu $1E
at_room_1E:
        lda     ploc
        cmp     #$1E
        bne     L6DF6
        rts

L6DF6:  cmp     #$1C
        rts

; PNJ : remet said=0 puis, si $90==$44, parcourt les tokens et peut renoncer ;
; sinon affiche 'SOMEONE STRANGLE YOU FROM BEHIND' ($15B6) et tue le joueur.
act_v14_13:
        jsr     act_probe
        lda     #$00
        sta     said
        lda     $90
        cmp     #$44
        bne     L6E29
        lda     $91
        sta     $5F
        ldy     #$00
        lda     ($BF),y
        sta     ptr
        iny
        lda     ($BF),y
        sta     ptr_hi
L6E15:  jsr     next_token
        cmp     #$C0
        beq     L6E29
        lda     adr
        cmp     ptr
        bne     L6E15
        lda     adr_hi
        cmp     ptr_hi
        bne     L6E15
        rts

L6E29:  lda     #$01
        sta     outen
        jsr     print_msg
; -> $15B6 SOMEONE STRANGLE YOU FROM BEHIND
msg_6E30:
        .word   $15B6
code_6E32:
        jmp     you_are_dead

L6E35:  lda     $1CC5
        cmp     #$FF
        bne     L6E3D
        rts

L6E3D:  jsr     locate_object
        lda     ptr
        sta     crec
        lda     ptr_hi
        sta     crec_hi
        ldy     #$07
        lda     (ptr),y
        and     #$80
        beq     L6E51
        rts

L6E51:  jmp     L667C

        lda     #$00
        sta     sflag
        rts

; Dragon : selon le lieu ($1F47 == $29 : parti). Sinon, si le dragon est actif
; (bit7), tirage 0-99 : < $50 -> vol ('...SHAPE OF A MONSTROUS DRAGON...' $1582),
; sinon souffle de flammes ($1596) qui tue le joueur.
act_v14_08:
        lda     $1F47
        cmp     #$29
        bne     L6E61
        rts

L6E61:  jsr     act_probe
        lda     #$01
        sta     outen
        jsr     obj_room_slot
        ldy     #$00
        lda     (ptr),y
        and     #$80
        bne     L6E74
        rts

L6E74:  lda     #$64
        jsr     rand_range
        cmp     #$50
        bcs     L6E83
        jsr     print_msg
; -> $1582 IN THE DISTANCE YOU SEE THE SHAPE OF A MONSTROUS DRAGON FLYING A
msg_6E80:
        .word   $1582
code_6E82:
        rts

L6E83:  jsr     print_msg
; -> $1596 THE DRAGON DESCENDS AND IN A TERRIFIC SPOUT OF FLAMES BURN YOU T
msg_6E86:
        .word   $1596
code_6E88:
        jmp     you_are_dead

; Trolls : au lieu $05. Si obj==$47 (un troll deja cuit) -> 'BLIMEY, LOOK AT THIS
; !! CAN YER COOK 'EM?' ($1615), sinon 'YER CAN TRY, BUT...' ($162B).
act_v14_15:
        lda     ploc
        cmp     #$05
        beq     L6E92
        rts

L6E92:  jsr     act_probe
        lda     obj
        cmp     #$47
        beq     L6EA1
        jsr     act_msg
; -> $162B YER CAN TRY,BUT HE WOULDN'T MAKE ABOVE A MOUTHFULL
msg_6E9E:
        .word   $162B
code_6EA0:
        rts

L6EA1:  jsr     act_msg
; -> $1615 BLIMEY,LOOK AT THIS !!CAN YER COOK 'EM?
msg_6EA4:
        .word   $1615
code_6EA6:
        rts

; PNJ : efface des drapeaux ($1F94/$1FA6 bit7, $214C bit6), recolle les objets
; $47/$48, met a jour la description $2154 et affiche 'DAY DAWN.' ($16EB).
act_v14_17:
        jsr     act_probe
        lda     #$47
        jsr     unit_remove
        lda     #$48
        jsr     unit_remove
        lda     $1F94
        and     #$7F
        sta     $1F94
        lda     $1FA6
        and     #$7F
        sta     $1FA6
        lda     #$45
        sta     $2154
        lda     #$16
        sta     $2155
        lda     $214C
        and     #$BF
        sta     $214C
        lda     #$47
        jsr     prob_scan
        lda     #$48
        jsr     prob_scan
        lda     #$01
        sta     outen
        jsr     print_msg
; -> $16EB DAY DAWN.
msg_6EE7:
        .word   $16EB
code_6EE9:
        jsr     img_poke
        bne     L6EEF
        rts

L6EEF:  lda     #$03
        sta     (ptr2),y
        iny
        sta     (ptr2),y
        rts

; Illustration associee a un lieu : si le bloc 3 est present, lit la fiche du
; lieu et modifie 2 octets a (ptr)+1 (couleurs/etat) avant d'appeler le moteur
; vec_*.
img_poke:
        lda     ptr_block3
        ora     L2C04
        bne     L6F00
        rts

L6F00:  ldx     ptr_block3
        ldy     L2C04
        lda     #$05
        jsr     index_id_table
        ldy     #$01
        lda     (ptr),y
        sta     ptr2
        iny
        lda     (ptr),y
        sta     ptr2_hi
        ldy     #$00
        lda     #$01
        rts

        lda     ploc
        cmp     #$1A
        beq     L6F22
        rts

L6F22:  jsr     print_msg
; -> $14DF THE SPIDER WEB IS SLOWLY SMOTHERING YOU.
msg_6F25:
        .word   $14DF
code_6F27:
        jmp     you_are_dead

        lda     $1BF0
        and     #$D7
        sta     $1BF0
        lda     $1BEE
        asl     a
        sta     $1BEE
        lda     #$8F
        sta     $1BF3
        lda     #$09
        sta     $1BF4
        rts

        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     arg2
        cmp     #$17
        beq     L6F75
        cmp     #$18
        beq     L6F7E
L6F56:  ldy     #$07
        lda     (orec2),y
        and     #$02
        bne     L6F61
        jmp     act_look

L6F61:  lda     (ptr),y
        and     #$04
        php
        lda     #$82
        plp
        beq     L6F6E
        jmp     name_from_record

L6F6E:  ldx     #$41
        ldy     #$60
        jmp     call_action_at

L6F75:  ldx     #$E2
        ldy     #$1D
        lda     #$15
        jmp     L6F84

L6F7E:  ldx     #$F6
        ldy     #$1D
        lda     #$16
L6F84:  stx     orec2
        sty     orec2_hi
        sta     arg2
        ldy     #$01
        lda     #$FF
        sta     (orec2),y
        jmp     L6F56

        jsr     act_probe
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        and     #$20
        beq     L6FA9
        jmp     L61DC

L6FA9:  jmp     L622D

        .byte   $01
        .byte   "D]"
        .byte   $02
        .byte   "D]"
        .byte   $03
        .byte   "D]"
        .byte   $04
        .byte   "D]"
        .byte   $05
        .byte   "D]"
        .byte   $06
        .byte   "D]"
        .byte   $07
        .byte   "D]"
        .byte   $08
        .byte   "D]"
        .byte   $09
        .byte   "D]"
        .byte   $0A
        .byte   "D]"
        .byte   $13,$C9
        .byte   "["
        .byte   $0E,$B7
        .byte   "^"
        .byte   $0B
        .byte   "rb"
        .byte   $17
        .byte   "D["
        .byte   $1A
        .byte   "{c"
        .byte   $1C,$A4
        .byte   "c"
        .byte   $1D,$DC
        .byte   "c"
        .byte   $1F,$FF
        .byte   "^ "
        .byte   $FF
        .byte   "^$"
        .byte   $07
        .byte   "_'(_*@_0`g"
        .byte   $00
        .byte   "5R3"
        .byte   $CA
        .byte   "g."
        .byte   $E3
        .byte   "g-^h5"
        .byte   $81
        .byte   "_:"
        .byte   $8B
        .byte   "i;"
        .byte   $C9
        .byte   "[7mh"
        .byte   $0F
        .byte   "A`"
        .byte   $11
        .byte   "A`"
        .byte   $14
        .byte   "1],"
        .byte   $E5
L7014:  .byte   "a"
L7015:  .byte   $FF,$BF
        .byte   "`"
        .byte   $ED
        .byte   "`"
        .byte   $C9
        .byte   "a"
        .byte   $22
        .byte   "b"
        .byte   $A9
        .byte   $5C
        .byte   $06
        .byte   "]"
        .byte   $DD
        .byte   "e"
        .byte   $E5
        .byte   "a"
        .byte   $BA
        .byte   "erk"
        .byte   $F1
        .byte   "e"
        .byte   $D6
        .byte   "f"
        .byte   $B6
        .byte   "eA`"
        .byte   $B6
        .byte   $5C
        .byte   "ff)f"
        .byte   $EB
        .byte   "j"
        .byte   $B2
        .byte   "e"
        .byte   $E3
        .byte   "e"
        .byte   $07
        .byte   "f"
        .byte   $E2
        .byte   "d"
        .byte   $AA
        .byte   "f|f"
        .byte   $9A
        .byte   "e"
        .byte   $86
        .byte   "j"
        .byte   $E3
        .byte   "g^jUkrb"
        .byte   $DB
        .byte   "kA`Do"
        .byte   $CD
        .byte   "_$j"
        .byte   $F1
        .byte   "f"
        .byte   $9F
        .byte   "`"
        .byte   $12
        .byte   "j"
        .byte   $FE
        .byte   "d"
        .byte   $FA
        .byte   "d'k"
        .byte   $00
        .byte   "k"
        .byte   $93
        .byte   "o1]"
        .byte   $02
        .byte   "j"
        .byte   $09
        .byte   "e"
        .byte   $AE
        .byte   "_"
        .byte   $04,$19,$00,$07
        .byte   "2"
        .byte   $00,$0B,$19,$00,$16,$19,$00,$0D
        .byte   "K"
        .byte   $00
        .byte   "A2"
        .byte   $00,$1B,$19,$00,$1C,$19,$00,$1F
        .byte   "2"
        .byte   $00,$22
        .byte   "d"
        .byte   $00
        .byte   "&"
        .byte   $19,$00
        .byte   "*"
        .byte   $19,$00
        .byte   "+2"
        .byte   $00
        .byte   ")"
        .byte   $C8,$00,$FF,$16,$B5
        .byte   "p"
        .byte   $1A,$CB
        .byte   "p"
        .byte   $1D,$D2
        .byte   "p!"
        .byte   $03
        .byte   "q"
        .byte   $02,$F8
        .byte   "p"
        .byte   $03,$F8
        .byte   "p "
        .byte   $D9
        .byte   "p"
        .byte   $FF
; Cle $16 : reveille le BUTLER (e4 $2B61:=$42) si sa fiche +7 bit3 est clair, puis marque +7 bit7
evt_arme16:
        lda     $1DC5
        and     #$08
        beq     L70BD
        rts

L70BD:  lda     #$42
        sta     $2B61
        lda     $1DC5
        ora     #$80
        sta     $1DC5
        rts

; Arme l'evenement e2 (minuterie = id) ; declenche par la cle $1A
evt_arme2:
        lda     $2B1C
        sta     $2B1D
        rts

; Arme l'evenement e4 (minuterie = id) ; declenche par la cle $1D
evt_arme4:
        lda     $2B26
        sta     $2B27
        rts

; Cle $20 : reveille DRAGON (e8 $2B7D:=$3C) et BARD (e7 $2B76:=$46) si leur fiche +7 bit3 est clair, puis arme l'evenement e9 (cpt:=3)
evt_arme9:
        lda     #$03
        sta     $2B40
        lda     $1B37
        and     #$08
        bne     L70EA
        lda     #$3C
        sta     $2B7D
L70EA:  lda     $1E54
        and     #$08
        beq     L70F2
        rts

L70F2:  lda     #$46
        sta     $2B76
        rts

; Declenche par les cles $02/$03 : rearme l'evenement e8
evt_arme8:
        lda     key
        sta     exploc
        lda     $2B3A
        sta     $2B3B
        rts

; Cle $21 : dans un cas precis, declenche un ecran et affiche
evt_gate21:
        lda     $1B1B
        cmp     #$13
        bne     L710B
        rts

L710B:  jsr     dark_gate
        jsr     print_msg
; -> $1650 <NAME>SWEPT FORCEFULLY AGAINST THE PORTCULLIS
msg_7111:
        .word   $1650
code_7113:
L7114           := * + 1
L7115           := * + 2
        jmp     you_are_dead

        .byte   $32,$07,$C8,$15,$92,$06,$97,$16
        .byte   $32,$07,$C8,$15,$92,$06,$97,$16
        .byte   $16,$A2,$23,$01,$00,$31,$18,$B6
        .byte   $23,$03,$00,$19,$15,$88,$23,$04
        .byte   $00,$14,$22,$72,$24,$03,$00,$23
        .byte   $0A,$9A,$21,$03,$00
L7143:  .byte   $0B
L7144:  .byte   $FF,$2D,$69,$E0,$68,$0C,$69,$62
        .byte   $69,$36,$69,$7A,$69,$D0,$68,$FA
        .byte   $6C,$59,$6E,$8D,$6C,$BE,$6C,$33
        .byte   $6C,$09,$6C,$F9,$6D,$78,$6D,$8B
        .byte   $6E,$DB,$6C,$A7,$6E
L7169:  .byte   $15
L716A:  .byte   $69,$8D,$68,$2A,$6F,$1B,$6F,$03
        .byte   $69,$5F,$6C,$79,$6C,$D0,$6D,$35
        .byte   $6E,$54,$6E,$3D,$6D,$9F,$6D,$55
        .byte   $6D,$BB,$6D,$06,$AC,$17,$09,$B9
        .byte   $17,$0D,$CC,$17,$42,$EF,$17,$1F
        .byte   $FE,$17,$20,$0E,$18,$2A,$2D,$18
        .byte   $2E,$37,$18,$29,$4B,$18,$1A,$63
        .byte   $18,$05,$72,$18,$FF,$FF
; Illustration (vec_01) : attend une touche avant de poursuivre
vec_keypause:
        lda     $0A
        bne     L71C8
        jsr     via_reset
        lda     #$0D
        jsr     via_write
        ldx     #$00
        ldy     #$00
L71B8:  lda     $030D
        and     #$02
        bne     L71C8
        dex
        bne     L71B8
        dey
        bne     L71B8
        lda     #$01
        rts

L71C8:  lda     #$00
        rts

; Verifie un bloc cassette en le relisant (vec_04)
tape_verify:
        lda     $024D
        sta     $6C
        lda     #$01
        sta     $024D
        jsr     tape_read_verify
        jmp     L71E8

; Charge un bloc depuis la cassette et verifie son en-tete
tape_load:
        lda     $024D
        sta     $6C
        lda     #$01
        sta     $024D
        jsr     L0417
L71E8:  php
        lda     $6C
        sta     $024D
        plp
        bcc     L71F3
L71F1:  sec
        rts

L71F3:  lda     ptr
        cmp     $32
        bne     L71F1
        lda     ptr_hi
        cmp     $33
        bne     L71F1
; Rend la main avec C=0 (succes) (vec_08)
ok_rts: clc
        rts

; Affiche un retour a la ligne (vec_10)
vec_cr: jmp     print_cr

; Remet a zero le registre clavier VIA $030B (vec_09)
vec_kbd_clear:
        lda     #$00
        sta     $030B
        rts

; Affiche un point avant une operation cassette
tape_dot:
        jsr     push_ptr
        lda     #$2E
        jsr     ch_out
        jmp     pop_ptr2

; Ecrit un bloc sur la cassette (leader, en-tete, donnees, checksum)
tape_save:
        jsr     tape_dot
        lda     $024D
        sta     $6C
        lda     #$01
        sta     $024D
        lda     #$FF
        sta     $36
        sta     $3D
        sta     $3E
        lda     #$50
        sta     $3B
        sta     $3C
        lda     #$24
        sta     $3F
        lda     ptr
        sta     $37
        clc
        adc     ptr2
        sta     $39
        lda     ptr_hi
        sta     $38
        adc     ptr2_hi
        sta     $3A
        jsr     L0411
        jsr     L040B
        ldy     #$09
L724D:  lda     $36,y
        jsr     L040E
        dey
        bpl     L724D
        lda     #$00
        jsr     L040E
        ldy     #$00
        sty     $3B
L725F:  lda     ($37),y
        jsr     L040E
        lda     ($37),y
        eor     $3B
        sta     $3B
        inc     $37
        bne     L7270
        inc     $38
L7270:  lda     $37
        cmp     $39
        lda     $38
        sbc     $3A
        bcc     L725F
        lda     $3B
        jsr     L040E
        ldx     #$40
        ldy     #$00
L7283:  dey
        bne     L7283
        dex
        bne     L7283
        jsr     L0414
        lda     $6C
        sta     $024D
        clc
        rts

; Affiche 'PREPARE TAPE FOR GAME SAVE' (vec_06)
tape_prompt_save:
        jsr     print_msg
; -> $72AA PREPARE TAPE FOR GAME SAVE
msg_7296:
        .word   $72AA
code_7298:
        jmp     tape_prompt

; Affiche 'REWIND TAPE FOR VERIFICATION' (vec_07)
tape_prompt_verify:
        jsr     print_msg
; -> $72C5 REWIND TAPE FOR VERIFICATION
msg_729E:
        .word   $72C5
; Affiche les invites de cassette ('PREPARE TAPE', 'PRESS ANY KEY'...)
tape_prompt:
        jsr     print_msg
; -> $72E3 PRESS ANY KEY WHEN READY
msg_72A3:
        .word   $72E3
code_72A5:
        jsr     wait_for_key
        clc
        rts

        .byte   "PREPARE TAPE FOR GAME SAVE"
        .byte   $14,$0D
        .byte   "REWIND TAPE FOR VERIFICATION"
        .byte   $14
        .byte   "PRESS ANY KEY WHEN READY"
        .byte   $14
; Relecture cassette : affiche un point, initialise le VIA, cherche le marqueur
; $24, lit l'en-tete 9 octets, puis les donnees en accumulant un checksum EOR
; qu'il compare. Rend C=0 si le bloc est valide, C=1 sinon.
tape_read_verify:
        jsr     tape_dot
        jsr     L0411
        jsr     L0405
L7305:  jsr     L0408
        cmp     #$24
        bne     L7305
        ldy     #$09
L730E:  jsr     L0408
        sta     $35,y
        dey
        bne     L730E
L7317:  jsr     L0408
        bne     L7317
        lda     $37
        ldy     $38
        sta     $32
        sty     $33
        ldy     #$00
        sty     $3B
L7328:  jsr     L0408
        bcs     L7351
        cmp     ($37),y
        bne     L7351
        eor     $3B
        sta     $3B
        inc     $37
        bne     L733B
        inc     $38
L733B:  lda     $37
        cmp     $39
        lda     $38
        sbc     $3A
        bcc     L7328
        jsr     L0408
        cmp     $3B
        bne     L7351
        jsr     L0414
        clc
        rts

L7351:  sec
        rts

; Lit l'etat du clavier : renvoie la touche appuyee, ou indique qu'aucune touche n'est
; enfoncee.
; Technique : scan de la matrice via le VIA ($0300) ; A = code touche, bit7 pose si presente.
get_key:stx     $1E
        sty     $1F
        lda     #$FF
        sta     $0303
        lda     #$F7
        sta     $0302
        lda     #$CC
        sta     $030C
        lda     #$07
        jsr     via_setup_ee
        lda     #$FF
        jsr     via_setup_ec
        lda     #$0E
        jsr     via_setup_ee
        ldx     #$07
L7377:  ldy     #$FE
L7379:  jsr     via_scan
        bne     L738F
L737E:  tya
        sec
        rol     a
        tay
        cmp     #$EF
        beq     L737E
        cmp     #$FF
        bne     L7379
        dex
        bpl     L7377
        bmi     L73BA
L738F:  tya
        ldy     #$FF
L7392:  iny
        clc
        ror     a
        bcs     L7392
        tya
        asl     a
        asl     a
        asl     a
        tay
        dey
L739D:  iny
        dex
        bpl     L739D
        tya
        pha
        ldy     #$EF
        ldx     #$04
        jsr     via_scan
        bne     L73B3
        ldx     #$07
        jsr     via_scan
        beq     L73C5
L73B3:  pla
        tay
        lda     L7414,y
        bne     L73CA
L73BA:  lda     #$00
L73BC:  sta     $22
L73BE:  ldx     $1E
        ldy     $1F
        pha
        pla
        rts

L73C5:  pla
        tay
        lda     L73D4,y
L73CA:  ora     #$80
        cmp     $22
        bne     L73BC
        lda     #$00
        beq     L73BE
L73D4:  .byte   "7JMK UY8NT69,IHL5RB;.OG0VF4-"
        .byte   $8B
        .byte   "PE/"
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $B1,$00,$DA,$00,$88,$88,$C1,$8D
        .byte   "XQ2"
        .byte   $5C
        .byte   $8A
        .byte   "]S"
        .byte   $00
        .byte   "3DC"
        .byte   $A7,$95
        .byte   "[W="
L7414:  .byte   "&JMK UY*NT^(<IHL%RB:>OG)VF$_"
        .byte   $8B
        .byte   "PE?"
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $A1,$00,$DA,$00,$88,$FF,$C1,$8D
        .byte   "XQ@|"
        .byte   $8A
        .byte   "}S"
        .byte   $00
        .byte   "#DC"
        .byte   $A2,$95
        .byte   "{W+"
; Scan clavier bas niveau : teste une ligne et une colonne du VIA
via_scan:
        txa
        ora     #$B0
        sta     $0300
        tya
        jsr     via_setup_ec
        lda     $0300
        and     #$08
        rts

; Configure le VIA pour le scan clavier (valeur $EE en $030C)
via_setup_ee:
        sta     $0301
        lda     #$EE
        sta     $030C
        lda     #$CC
        sta     $030C
        rts

; Configure le VIA pour le scan clavier (valeur $EC en $030C)
via_setup_ec:
        sta     $0301
        lda     #$EC
        sta     $030C
        lda     #$CC
        sta     $030C
        rts

        .byte   "`"
; Attend que le joueur appuie sur une touche, puis renvoie son code.
; Technique : boucle sur get_key jusqu'a bit7 pose, retour & $7F.
wait_for_key:
        jsr     get_key
        bpl     wait_for_key
        and     #$7F
        rts

; Affiche un retour a la ligne.
; Technique : $0D via ch_out.
cr_out: pha
        lda     #$0D
        jsr     ch_out
        pla
        rts

; Point d'entree pour tout caractere affiche a l'ecran. Il peut etre ignore selon le
; contexte (par exemple pendant qu'une scene se prepare).
; Technique : si (phase & outen)==0 -> jete ; mode raw -> majuscules ; sinon ch_put.
ch_out: pha
        lda     phase
        and     outen
        bne     L749A
        pla
        rts

L749A:  lda     raw
        bne     L74BB
        pla
        jsr     ch_put
        pha
        lda     sflag
        bne     L74A9
        pla
        rts

L74A9:  pla
        cmp     #$53
        beq     L74B3
        cmp     #$73
        beq     L74B3
        rts

L74B3:  pha
        lda     #$48
        jsr     ch_put
        pla
        rts

L74BB:  pla
        sta     $02
        pha
        tya
        pha
        txa
        pha
        lda     $02
        cmp     #$0D
        bne     L74D1
        lda     #$20
        jsr     print_char
        jmp     L74E7

L74D1:  cmp     #$08
        beq     L74FD
        cmp     #$61
        bcc     L74DF
        cmp     #$7B
        bcs     L74DF
        and     #$5F
L74DF:  jsr     print_char
        jsr     cursor_adv
        bne     L74F2
L74E7:  jsr     hires_scroll_setup
        lda     #$00
        sta     L0000
        lda     #$28
        sta     col
L74F2:  lda     #$2B
        jsr     print_char
        pla
        tax
        pla
        tay
        pla
        rts

L74FD:  lda     #$20
        jsr     print_char
        jsr     cursor_back
        bne     L74F2
        lda     #$28
        sta     L0000
        jsr     hires_fill_setup
        lda     #$01
        sta     col
        bne     L74F2
; Prepare un defilement de l'ecran hires : cale les couples de pointeurs source/
; destination ($1E/$1F et $20/$21) sur le repertoire de lignes ($B940/$BA40) ;
; utilise par le scroll et l'effacement hires.
hires_scroll_setup:
        pha
        lda     #$00
        sta     $1E
        lda     #$B9
        sta     $1F
        lda     #$40
        sta     $20
        lda     #$BA
        sta     $21
        ldy     #$00
L7527:  lda     ($20),y
        sta     ($1E),y
        jsr     hires_row_next
        lda     $20
        cmp     #$40
        lda     $21
        sbc     #$BF
        bcc     L7527
L7538:  lda     #$40
        sta     ($1E),y
        jsr     hires_col_next
        lda     $1E
        cmp     #$40
        lda     $1F
        sbc     #$BF
        bcc     L7538
        pla
        rts

; Avance d'une ligne la copie d'ecran hires
hires_row_next:
        inc     $20
        bne     hires_col_next
        inc     $21
; Avance d'une colonne la copie d'ecran hires
hires_col_next:
        inc     $1E
        bne     L7557
        inc     $1F
L7557:  rts

; Prepare un remplissage d'ecran hires (pointeurs $BF3F)
hires_fill_setup:
        pha
        lda     #$3F
        sta     $20
        lda     #$BF
        sta     $21
        lda     #$FF
        sta     $1E
        lda     #$BD
        sta     $1F
        ldy     #$00
L756B:  lda     ($1E),y
        sta     ($20),y
        jsr     hires_row_prev
        lda     $1E
        cmp     #$00
        lda     $1F
        sbc     #$B9
        bcs     L756B
L757C:  lda     #$40
        sta     ($20),y
        jsr     hires_col_prev
        lda     $20
        cmp     #$00
        lda     $21
        sbc     #$B9
        bcs     L757C
        pla
        rts

; Recule d'une ligne la copie d'ecran hires
hires_row_prev:
        lda     $1E
        sec
        sbc     #$01
        sta     $1E
        bcs     hires_col_prev
        dec     $1F
; Recule d'une colonne la copie d'ecran hires
hires_col_prev:
        lda     $20
        sec
        sbc     #$01
        sta     $20
        bcs     L75A5
        dec     $21
L75A5:  rts

; Avance le curseur texte (col--, position++)
cursor_adv:
        inc     L0000
        dec     col
        rts

; Recule le curseur texte (col++)
cursor_back:
        dec     L0000
        inc     col
        lda     col
        cmp     #$29
        rts

; Dessine un caractere a l'ecran graphique (hires) en recopiant son motif depuis la police
; du jeu, puis fait avancer le curseur.
; Technique : police pointee par $0403/$0404 ; 8 octets en OR $40 (encre) ; ligne += $28.
print_char:
        ldx     L0000
        ldy     $01
L75B8:  stx     L75E0
        sty     L75E1
        sec
        sbc     #$20
        ldy     #$00
        sty     $21
        asl     a
        rol     $21
        asl     a
        rol     $21
        asl     a
        rol     $21
        clc
        adc     $0403
        sta     $20
        lda     $21
        adc     $0404
        sta     $21
L75DB:  lda     ($20),y
        ora     #$40
L75E0           := * + 1
L75E1           := * + 2
        sta     $A000
        lda     L75E0
        clc
        adc     #$28
        sta     L75E0
        bcc     L75F0
        inc     L75E1
L75F0:  iny
        cpy     #$08
        bne     L75DB
        rts

; Affiche un caractere en gerant les details du texte : espaces en attente, passage a la
; ligne, effacement, majuscule apres un point, minuscules par defaut. Toutes les 16 lignes
; il s'arrete pour laisser le joueur lire (pause).
; Technique : scroll L7694, pause pause_key, backspace $08, capitalisation apres '.' ($2E).
ch_put: sta     $02
        pha
        txa
        pha
        tya
        pha
        lda     sppend
        bne     L7613
        lda     $10
        beq     L7613
        sta     $03
L7607:  lda     #$20
        jsr     char_plot_pos
        jsr     cursor_down
        dec     $03
        bne     L7607
L7613:  lda     $02
        cmp     #$0D
        bne     L7653
; Pause de lecture : tous les 16 sauts de ligne, le jeu attend une touche (ou un court
; delai), puis fait defiler l'ecran et remet le compteur de lignes a zero.
; Technique : 10 essais get_key avec delai, compteur crcnt mod 16, scroll L7694.
pause_key:
        lda     #$00
        sta     sppend
        jsr     screen_scroll
        lda     crcnt
        cmp     #$0F
        bne     L763B
        ldx     #$0A
L7628:  jsr     get_key
        bmi     L7640
        lda     #$64
        sta     $03
L7631:  dec     $03
        bne     L7631
        dex
        bpl     L7628
        jmp     L7645

L763B:  inc     crcnt
        jmp     L7645

L7640:  jsr     get_key
        bpl     L7640
L7645:  jsr     hires_clear_zone
        lda     #$80
        sta     $08
        lda     #$28
        sta     $05
        jmp     L768E

L7653:  cmp     #$08
        bne     L7662
        jsr     cursor_up
        lda     #$20
        jsr     char_plot_pos
        jmp     L768E

L7662:  cmp     #$41
        bcc     L766C
        cmp     #$5B
        bcs     L766C
        ora     #$20
L766C:  ldx     cap
        beq     L767E
        cmp     #$61
        bcc     L767E
        cmp     #$7B
        bcs     L767E
        and     #$5F
        ldx     #$00
        stx     cap
L767E:  cmp     #$2E
        bne     L7684
        inc     cap
L7684:  jsr     char_plot_pos
        sta     sppend
        jsr     cursor_down
        beq     pause_key
L768E:  pla
        tay
        pla
        tax
        pla
        rts

; Efface une zone de l'ecran hires par blocs
hires_clear_zone:
        pha
        lda     #$00
        sta     $1E
        lda     #$A0
        sta     $1F
        lda     #$40
        sta     $20
        lda     #$A1
        sta     $21
        ldx     #$17
        ldy     #$FF
L76A9:  lda     ($20),y
        sta     ($1E),y
        dey
        cpy     #$FF
        bne     L76A9
        inc     $1F
        inc     $21
        cpx     #$02
        bne     L76BC
        ldy     #$7F
L76BC:  dex
        bne     L76A9
        lda     $1E
        sec
        sbc     #$80
        sta     $1E
        bcs     L76CA
        dec     $1F
L76CA:  ldy     #$00
L76CC:  lda     #$40
        sta     ($1E),y
        jsr     hires_col_next
        lda     $1E
        cmp     #$C0
        lda     $1F
        sbc     #$B7
        bcc     L76CC
        pla
        rts

; Descend le curseur texte d'une ligne
cursor_down:
        inc     $08
        dec     $05
        rts

; Remonte le curseur texte d'une ligne
cursor_up:
        dec     $08
        inc     $05
        lda     $05
        cmp     #$28
        rts

; Dessine le caractere A a la position texte courante : memorise la ligne (col)
; puis saute a print_char ($75B8) avec X/Y = position courante ($08/$09).
char_plot_pos:
        ldy     $05
        sta     $02D7,y
        ldx     $08
        ldy     $09
        jmp     L75B8

; Ecrit une valeur sur le port clavier du VIA ($0300/$0301)
via_write:
        sta     $0301
        lda     #$A7
        sta     $0300
        nop
        nop
        nop
        lda     #$B7
        sta     $0300
        rts

; Reinitialise le port clavier du VIA ($0302/$0303)
via_reset:
        lda     #$FF
        sta     $0303
        lda     #$F7
        sta     $0302
        lda     #$CD
        sta     $030C
        rts

; Defile verticalement l'ecran hires de quelques lignes : copie chaque ligne de
; destination vers la precedente via les pointeurs de hires_scroll_setup, en
; inserant eventuellement un CR ($0D) en fin de zone.
screen_scroll:
        pha
        lda     $0A
        beq     L7745
        jsr     via_reset
        ldy     $05
        lda     #$0D
        sta     $02D7,y
        lda     #$0A
        sta     $02D6,y
        ldy     #$2A
L7730:  lda     $02D5,y
        jsr     via_write
L7736:  lda     $030D
        and     #$02
        beq     L7736
        lda     $02D5,y
        dey
        cmp     #$0A
        bne     L7730
L7745:  pla
        rts

; Efface l'ecran graphique
hires_clear:
        lda     #$00
        sta     L7756
        lda     #$A0
        sta     L7757
        ldy     #$00
L7753:  lda     #$40
L7756           := * + 1
L7757           := * + 2
        sta     $A000,y
        inc     L7756
        bne     L7760
        inc     L7757
L7760:  lda     L7757
        cmp     #$BF
        bne     L7753
        lda     L7756
        cmp     #$40
        bne     L7753
        ldy     #$A0
        lda     #$00
L7772:  sta     $BF3F,y
        dey
        bne     L7772
        rts

; Initialise l'ecran hires : efface l'affichage, trace les bordures a partir
; des motifs $77CA/$77CF, cale les pointeurs d'affichage ($08/$09 = $B680) et
; les parametres texte, puis rend la main a start. Malgre son nom, ce n'est
; pas la boucle du jeu : c'est l'installation de l'ecran.
game_main:
        lda     #$1E
        sta     $BFDF
        jsr     hires_clear
        lda     #$00
        sta     $10
        sta     sppend
        lda     #$01
        sta     cap
        lda     #$28
        sta     col
        sta     $05
        lda     #$E8
        sta     L0000
        lda     #$B7
        sta     $01
        ldx     #$04
L779B:  ldy     #$27
L779D:  lda     L77CF,x
        sta     (L0000),y
        dey
        lda     L77CA,x
        sta     (L0000),y
        dey
        bpl     L779D
        lda     L0000
        clc
        adc     #$28
        sta     L0000
        bcc     L77B6
        inc     $01
L77B6:  dex
        bpl     L779B
        lda     #$00
        sta     L0000
        lda     #$BE
        sta     $01
        lda     #$80
        sta     $08
        lda     #$B6
        sta     $09
        rts

L77CA:  .byte   "aZDZa"
L77CF:  .byte   "aVHVa"
; Decodeur d'un flux d'illustration (bloc 3 ; cible de la table a cles $7AC0).
; Entree : X/Y = adresse du flux. Le 1er octet du flux (lu dans A) est passe a
; vec_setup, qui prepare l'ecran hires (fond + bordures). Puis chaque octet
; suivant est une commande, repetee jusqu'a $00 :
;   $00  fin de flux (retour) ;
;   $08  position du curseur (vec_pos) ;
;   bit7 ligne (vec_line) ; bit6 remplissage (vec_fill) ;
;   bit5 saut jusqu'a un marqueur $FF (vec_skip).
; Le test est prioritaire dans cet ordre (bit7 avant bit6 avant bit5).
; Le pointeur de flux ($28/$29) avance d'un octet par vec_next_byte.
drawing:stx     $28
        sty     $29
        pha
        ldy     #$00
        lda     ($28),y
        jsr     vec_setup
        jsr     vec_next_byte
L77E3:  ldy     #$00                            ; boucle du flux : octet de commande suivant
        lda     ($28),y                         ; octet de commande courant
        beq     L781B
        cmp     #$08                            ; $08 : position du curseur (vec_pos)
        beq     L7803
        and     #$80                            ; bit7 : trace de ligne (vec_line)
        bne     L7809
        lda     ($28),y
        and     #$40                            ; bit6 : remplissage (vec_fill)
        bne     L780F
        lda     ($28),y
        and     #$20                            ; bit5 : saut jusqu'a un marqueur (vec_skip)
        bne     L7815
L77FD:  jsr     vec_next_byte
        jmp     L77E3

L7803:  jsr     vec_pos
        jmp     L77FD

L7809:  jsr     vec_line
        jmp     L77FD

L780F:  jsr     vec_fill
        jmp     L77FD

L7815:  jsr     vec_skip
        jmp     L77FD

L781B:  pla
        rts

; Avance d'un octet le pointeur de flux d'illustration ($28/$29) et rend l'octet
; suivant ; brique de base de la boucle de trace vec_* a $77E3.
vec_next_byte:
        inc     $28
        bne     L7823
        inc     $29
L7823:  rts

; Remplissage (seed fill) : part du pixel courant ($30/$31) et s'etend
; horizontalement, puis empile les positions de reprise sur la pile 6502
; (repere de profondeur en $32 ; bornes $30/$31 sauvees en $33/$34) pour
; couvrir la zone en tache d'huile. Les drapeaux $35/$36 evitent de repasser
; sur une ligne deja remplie. S'arrete sur les pixels occupes ou hors zone
; ($30 < $0E ou >= $F2, testes par vec_testpx). Utilise par les commandes a
; bit6 du flux d'illustration.
vec_fill:
        tsx
        stx     $32
        lda     $30
        sta     $33
        lda     $31
        sta     $34
        jsr     vec_next_byte
        ldy     #$00
        lda     ($28),y
        sta     $30
        jsr     vec_next_byte
        lda     ($28),y
        sta     $31
L783F:  jsr     vec_testpx
        bne     L7851
L7844:  lda     $30
        beq     L7851
        dec     $30
        jsr     vec_testpx
        beq     L7844
        inc     $30
L7851:  lda     #$00
        sta     $35
        sta     $36
L7857:  jsr     vec_plot
        lda     $31
        cmp     #$7F
        bne     L7863
        jmp     L7881

L7863:  inc     $31
        jsr     vec_testpx
        bne     L787B
        lda     $35
        bne     L787F
        lda     $30
        pha
        lda     $31
        pha
        lda     #$01
        sta     $35
        jmp     L787F

L787B:  lda     #$00
        sta     $35
L787F:  dec     $31
L7881:  lda     $31
        bne     L7888
        jmp     L78A6

L7888:  dec     $31
        jsr     vec_testpx
        bne     L78A0
        lda     $36
        bne     L78A4
        lda     $30
        pha
        lda     $31
        pha
        lda     #$01
        sta     $36
        jmp     L78A4

L78A0:  lda     #$00
        sta     $36
L78A4:  inc     $31
L78A6:  inc     $30
        beq     L78B2
        jsr     vec_testpx
        bne     L78B2
        jmp     L7857

L78B2:  tsx
        cpx     $32
        beq     L78C0
        pla
        sta     $31
        pla
        sta     $30
        jmp     L783F

L78C0:  lda     $33
        sta     $30
        lda     $34
        sta     $31
        rts

; Illustration : place le curseur
vec_pos:jsr     vec_next_byte
        ldy     #$00
        lda     ($28),y
        sta     $30
        jsr     vec_next_byte
        lda     ($28),y
        sta     $31
        rts

; Illustration : saute jusqu'a un marqueur
vec_skip:
        jsr     vec_next_byte
        lda     ($28),y
        cmp     #$FF
        bne     vec_skip
        rts

; Trace un segment de droite a partir de l'octet de commande ($28),y.
; Directions : bit0 = axe majeur vertical ; bit1 = sens vertical ; bit2 = sens
; horizontal. La longueur du petit axe est en $2D (bits 3-6 de l'octet + bits
; 7-6 de l'octet suivant, +1) et le nombre de pas en $2E (bits 5-0 de l'octet
; suivant). Deux boucles symetriques (L791C si axe majeur horizontal, L7954
; sinon) tracent pas a pas via vec_plot, en rebondissant sur les bornes
; ($30 dans [$0E,$F2), $31 dans [0,$7F]) ; utilise par les commandes a bit7.
vec_line:
        lda     ($28),y
        and     #$01
        sta     $2A
        lda     ($28),y
        and     #$02
        sta     $2B
        lda     ($28),y
        and     #$04
        sta     $2C
        lda     ($28),y
        and     #$78
        lsr     a
        sta     $2D
        jsr     vec_next_byte
        lda     ($28),y
        and     #$C0
        clc
        rol     a
        rol     a
        rol     a
        ora     $2D
        sta     $2D
        inc     $2D
        lda     ($28),y
        and     #$3F
        sta     $2E
        lda     $2A
        bne     L7954
        lda     $2D
        sta     $2F
L791C:  jsr     vec_plot
        lda     $2C
        bne     L792A
        inc     $30
        bne     L7935
        dec     $30
        rts

L792A:  dec     $30
        lda     $30
        cmp     #$FF
        bne     L7935
        inc     $30
        rts

L7935:  dec     $2F
        bne     L794F
        lda     $2D
        sta     $2F
        lda     $2B
        bne     L7948
        inc     $31
        bpl     L794F
        dec     $31
        rts

L7948:  dec     $31
        bpl     L794F
        inc     $31
        rts

L794F:  dec     $2E
        bpl     L791C
        rts

L7954:  lda     $2D
        sta     $2F
L7958:  jsr     vec_plot
        lda     $2B
        bne     L7966
        inc     $31
        bpl     L796D
        dec     $31
        rts

L7966:  dec     $31
        bpl     L796D
        inc     $31
        rts

L796D:  dec     $2F
        bne     L798B
        lda     $2D
        sta     $2F
        lda     $2C
        bne     L7980
        inc     $30
        bne     L798B
        dec     $30
        rts

L7980:  dec     $30
        lda     $30
        cmp     #$FF
        bne     L798B
        inc     $30
        rts

L798B:  dec     $2E
        bpl     L7958
        rts

; Prepare l'ecran pour une illustration : efface le bitmap hires $A000-$B3FF
; (chaque octet recoit $40 = fond), puis trace les bordures gauche ($A000) et
; droite ($A001) tous les $28 octets, avec l'encre donnee par A : nibble bas =
; bordure gauche, nibble haut = bordure droite (chacun force en $10-$17).
; Appelee par drawing avec le 1er octet du flux comme parametre.
vec_setup:
        pha
        lda     #$A0
        sta     L79AD
        sta     L79C4
        sta     L79E4
        lda     #$01
        sta     L79E3
        ldx     #$00
        stx     L79C3
        stx     L79AC
        lda     #$40
L79AB:
L79AC           := * + 1
L79AD           := * + 2
        sta     $A000,x
        dex
        bne     L79AB
        inc     L79AD
        ldy     L79AD
        cpy     #$B4
        bne     L79AB
        pla
        pha
        and     #$07
        ora     #$10
        tax
L79C2:
L79C3           := * + 1
L79C4           := * + 2
        stx     $A000
        lda     L79C3
        clc
        adc     #$28
        sta     L79C3
        bcc     L79C2
        inc     L79C4
        lda     L79C4
        cmp     #$B4
        bne     L79C2
        pla
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        and     #$07
        tax
L79E2:
L79E3           := * + 1
L79E4           := * + 2
        stx     $A001
        lda     L79E3
        clc
        adc     #$28
        sta     L79E3
        bcc     L79E2
        inc     L79E4
        lda     L79E4
        cmp     #$B4
        bne     L79E2
        rts

; Teste le pixel ($30,$31) : rend A<>0 si un point est deja dessine ou si la
; position est hors zone ($30 < $0E ou >= $F2), A=0 si le pixel est libre.
; Sert de test de frontiere au remplissage vec_fill (et au trace vec_line).
vec_testpx:
        lda     $30
        cmp     #$0E
        bcc     L7A0C
        cmp     #$F2
        bcs     L7A0C
        jsr     vec_addr
        and     L7A5F,x
        rts

L7A0C:  lda     #$FF
        rts

; Allume le pixel ($30,$31) dans le bitmap hires (OR du masque L7A5F[X]) ;
; hors zone ($30 < $0E ou >= $F2) ne fait rien.
vec_plot:
        lda     $30
        cmp     #$0E
        bcc     L7A21
        cmp     #$F2
        bcs     L7A21
        jsr     vec_addr
        ora     L7A5F,x
        sta     ($38),y
L7A21:  rts

; Calcule l'adresse du pixel ($30,$31) : octet de base $A002 + ($7F-$31)*$28
; + ($30-$0E). Pose l'adresse en $38/$39 ; rend dans A l'octet courant du
; bitmap (lu via ($38),Y) et dans X le numero de bit (masque L7A5F[X] :
; $20,$10,$08,$04,$02,$01). Le decoupage $30-$0E est divise par 6 (6 pixels
; par octet) : le quotient donne l'offset d'octet, le reste le numero de bit.
vec_addr:
        lda     #$02
        sta     $38
        lda     #$A0
        sta     $39
        lda     #$7F
        sec
        sbc     $31
        tax
        beq     L7A40
        lda     #$02
L7A34:  clc
        adc     #$28
        bcc     L7A3B
        inc     $39
L7A3B:  dex
        bne     L7A34
        sta     $38
L7A40:  lda     $30
        sec
        sbc     #$0E
        sta     $37
        ldx     #$08
        lda     #$00
L7A4B:  asl     $37
        rol     a
        cmp     #$06
        bcc     L7A56
        sbc     #$06
        inc     $37
L7A56:  dex
        bne     L7A4B
        tax
        ldy     $37
        lda     ($38),y
        rts

L7A5F:  .byte   $20,$10,$08,$04,$02,$01,$AD,$E3
        .byte   $79,$18,$69,$28,$8D,$E3,$79,$90
        .byte   $F2,$EE,$E4,$79,$AD,$E4,$79,$C9
        .byte   $B4,$D0,$E8,$60,$A5,$30,$C9,$0E
        .byte   $90,$FA
