; ============================================================
; The Hobbit (Oric, 1982)
; Original authors : Veronika Megler & Philip Mitchell (Melbourne House)
; 6502 port : Greg Barrett (Beam Software)
; - bloc 1 ($0400-$04FF)
; Listing généré par scripts/disasm.py (descente récursive + da65)
; Charge par autorun à $0400 -> JMP $047C (b1_start).
; Vecteurs ROM $0405-$0416 (patchés 1.0/1.1) + b1_load $0417.
; ============================================================

; da65 V2.19 - Git 71746c829


        .setcpu "6502"

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
L0032           := $0032
adr             := $005C                        ; Adresse de travail : mot de message en cours (octet haut en $5D)
adr_hi          := $005D                        ; Octet haut de adr
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
obj             := $00C5                        ; Objet ou personnage courant ($FF = un personnage)
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
cond1           := $00DC                        ; Condition memorisee n°1
cond2           := $00E2                        ; Condition memorisee n°2
svptr           := $00E8                        ; Sauvegarde du pointeur de travail
svptr_hi        := $00E9                        ; Octet haut de svptr
exitp           := $00F8                        ; Curseur dans la table des sorties du lieu
exitp_hi        := $00F9                        ; Octet haut de exitp
PUTBYTE_10      := $E5C6
READBYTE_10     := $E630
PUTBYTE_11      := $E65E
TAPESYNC_10     := $E696
WRITELEADER_10  := $E6BA
READBYTE_11     := $E6C9
SETUPTAPE_10    := $E6CA
SYNCTAPE_11     := $E735
WRITELEADER_11  := $E75A
SETUPTAPE_11    := $E76A
CHAR2SCR_10     := $F73C
CHAR2SCR_11     := $F77C
RESETSTAT_10    := $F960
RESETSTAT_11    := $F9AA
; Trampoline d'autorun : saute au demarrage du chargeur (b1_start)
b1_entry:
L0402           := * + 2
        jmp     b1_start

        .byte   $70,$FC
b1_vec_sync:
        jmp     TAPESYNC_10

b1_vec_read:
        jmp     READBYTE_10

b1_vec_leader:
        jmp     WRITELEADER_10

b1_vec_write:
        jmp     PUTBYTE_10

b1_vec_setup:
        jmp     SETUPTAPE_10

b1_vec_reset:
        jmp     RESETSTAT_10

; Lit un bloc complet sur la cassette. Attend le marqueur de synchro,
; lit l'en-tete de 9 octets (range en $0035,Y), puis les donnees vers le
; pointeur ($37), en cumulant un checksum EOR dans $3B ; compare le
; checksum et renvoie C=1 (echec) ou C=0 (succes).
; Technique : JSR $0411 setup, $0405 synchro, $0408 lecture octet ;
; $39/$3A = adresse de fin, $37/$38 = curseur d'ecriture.
b1_load:jsr     b1_vec_setup
        jsr     b1_vec_sync
L041D:  jsr     b1_vec_read
        cmp     #$24
        bne     L041D
        ldy     #$09
L0426:  jsr     b1_vec_read
        sta     $35,y
        dey
        bne     L0426
L042F:  jsr     b1_vec_read
        bne     L042F
        tay
        sta     $3B
        lda     $37
        sta     L0032
        lda     $38
        sta     $33
L043F:  jsr     b1_vec_read
        bcs     L0466
        sta     ($37),y
        eor     $3B
        sta     $3B
        inc     $37
        bne     L0450
        inc     $38
L0450:  lda     $37
        cmp     $39
        lda     $38
        sbc     $3A
        bcc     L043F
        jsr     b1_vec_read
        cmp     $3B
        bne     L0466
        jsr     b1_vec_reset
        clc
        rts

L0466:  sec
L0467:  rts

        .byte   $78,$FC,$4C,$35,$E7,$4C,$C9,$E6
        .byte   $4C,$5A,$E7,$4C,$5E,$E6,$4C,$6A
        .byte   $E7,$4C,$AA,$F9
; Point d'entree autorun ($0400 -> JMP $047C). Coupe les interruptions,
; puis detecte la version de ROM : si l'octet $FC78 est nul (Atmos 1.1),
; recopie un blob de 20 octets ($0468-$047B) sur $0403 pour remplacer les
; vecteurs ROM 1.0 par ceux de la ROM 1.1. Affiche 'Please wait while THE
; HOBBIT loads', puis charge 3 blocs (blocs 2, 3, 4) via b1_load et saute
; au dernier ($2C00). En cas d'echec, affiche 'TAPE ERROR' et boucle.
b1_start:
        sei
        lda     #$7F
        sta     $030E
        lda     $FC78
        bne     L0497
        lda     #$7C
        sta     L049A
        ldy     #$14
L048E:  lda     L0467,y
        sta     L0402,y
        dey
        bne     L048E
L0497:  ldx     #$0C
L049A           := * + 1
        jsr     CHAR2SCR_10
        ldy     #$00
        sty     $BBA3
        sty     $BBAA
        ldy     #$21
L04A6:  lda     L04CC,y
        sta     $BC4B,y
        dey
        bpl     L04A6
        ldx     #$03
        stx     $40
L04B3:  jsr     b1_load
        bcs     L04BF
        dec     $40
        bne     L04B3
        jmp     (L0032)

L04BF:  ldy     #$0A
L04C1:  lda     L04EE,y
        sta     $BD19,y
        dey
        bpl     L04C1
L04CA:  bmi     L04CA
L04CC:  .byte   "Please wait while THE HOBBIT lo"



        .byte   "ads"
L04EE:  .byte   $0C
        .byte   "TAPE ERROR"

        .byte   $4C,$AA,$F9,$78,$A9,$7F,$8D
