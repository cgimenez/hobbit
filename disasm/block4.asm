; ============================================================
; The Hobbit (Oric, 1982)
; Original authors : Veronika Megler & Philip Mitchell (Melbourne House)
; 6502 port : Greg Barrett (Beam Software)
; - bloc 4 ($2C00-$7A80)
; Listing généré par scripts/disasm.py (descente récursive + da65)
; Charge en mémoire à $2C00, entrée autorun $2C00 -> $2C35.
; Convention : JSR $440D + pointeur inline (2 octets, adresse du
; message) ; reprise du code à JSR+5.
; ============================================================

; da65 V2.19 - Git 71746c829


        .setcpu "6502"

L0000           := $0000
col             := $0004                        ; Colonnes restantes sur la ligne courante (remis a jour a chaque ligne ; sert au retour auto)
outen           := $000B                        ; Autorise l'affichage (1 = la sortie texte est autorisee)
phase           := $000C                        ; Phase d'execution : 0 = sonde (simulation), 1 = execution reelle
raw             := $000D                        ; Mode brut : 1 = texte force sans mise en forme (limite de colonnes, capitales)
cap             := $000E                        ; Capitaliser la prochaine lettre affichee (pose apres un point)
sppend          := $000F                        ; Espace en attente a inserer avant le prochain mot
crcnt           := $0011                        ; Compteur de lignes depuis la derniere pause (modulo 16)
passok          := $0012                        ; Reussite d'une sonde : 1 = passer a l'execution reelle
wid             := $0013                        ; Mot/identifiant courant (verbe d'action ou direction)
arg1            := $0015                        ; Premier objet de la commande ($FF = aucun)
arg2            := $0016                        ; Second objet de la commande ($FF = aucun)
orec            := $0017                        ; Pointeur vers l'enregistrement du premier objet (octet haut en $18)
orec_hi         := $0018                        ; Octet haut de orec
orec2           := $0019                        ; Pointeur vers l'enregistrement du second objet (octet haut en $1A)
orec2_hi        := $001A                        ; Octet haut de orec2
adr             := $005C                        ; Adresse de travail : mot de message pointe (octet haut en $5D)
adr_hi          := $005D                        ; Octet haut de adr
L006A           := $006A
tidx            := $006F                        ; Index du caractere en cours dans le message affiche
nest            := $0070                        ; Niveau d'imbrication du rendu (0 = message simple)
wptr            := $0071                        ; Pointeur vers le mot/nom en cours de rendu (octet haut en $72)
wptr_hi         := $0072                        ; Octet haut de wptr
direct          := $0073                        ; Sortie directe sans controle (copie du bit7 de xmode)
variant         := $0074                        ; Sortie en variante (copie du bit6 de xmode)
msgstk          := $0076                        ; Index de la pile de messages $466F (remis a zero a chaque message)
xaux            := $0077                        ; Octet auxiliaire de sortie (drapeaux de mise en forme)
xmode           := $0078                        ; Octet de mode de sortie (bit7 = direct, bit6 = variante)
ptr3            := $007A                        ; Troisieme pointeur de travail (octet haut en $7B)
ptr3_hi         := $007B                        ; Octet haut de ptr3
ptr2            := $0088                        ; Pointeur secondaire, pour balayer les tables (octet haut en $89)
ptr2_hi         := $0089                        ; Octet haut de ptr2
ptr             := $008A                        ; Pointeur de travail universel (octet haut en $8B)
ptr_hi          := $008B                        ; Octet haut de ptr
key             := $008F                        ; Cle d'evenement a declencher (cherchee dans la table $709F)
noise           := $0093                        ; Pointeur vers la source de bruit (entropie des tirages aleatoires)
noise_hi        := $0094                        ; Octet haut de noise
svA             := $00AD                        ; Sauvegarde de l'accumulateur A (routines utilisant la pile $0200)
svX             := $00AE                        ; Sauvegarde du registre X (routines utilisant la pile $0200)
rstk            := $00AF                        ; Index de la pile d'adresses de retour $0200
exploc          := $00BE                        ; Lieu attendu par l'evenement (copie de key, compare a ploc)
obj             := $00C5                        ; Objet/entite courant (id ; $FF = une personne)
crec            := $00C6                        ; Pointeur vers l'enregistrement courant (contexte/compteurs, base $1B1A)
crec_hi         := $00C7                        ; Octet haut de crec
ploc            := $00C8                        ; Lieu du joueur : simple miroir de player.eloc ($1B2A), pas la source
eloc            := $00C9                        ; Lieu d'une entite (visible quand eloc==ploc)
once            := $00CE                        ; Verrou one-shot : pose puis consomme pour n'agir qu'une fois
cond1           := $00DC                        ; Tampon de condition 1 (6 octets $DC-$E1)
cond2           := $00E2                        ; Tampon de condition 2 (6 octets $E2-$E7)
svptr           := $00E8                        ; Sauvegarde du pointeur ptr (contexte de deplacement, octet haut en $E9)
svptr_hi        := $00E9                        ; Octet haut de svptr
exitp           := $00F8                        ; Curseur dans la table des sorties du lieu ($26DA + wid*8)
exitp_hi        := $00F9                        ; Octet haut de exitp
L0405           := $0405
L0408           := $0408
L040B           := $040B
L040E           := $040E
L0411           := $0411
L0414           := $0414
L0417           := $0417
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
autorun:jmp     start

ptr_block3:
        .byte   $C0
L2C04:  .byte   $7A
vec_init:
        jmp     vec_image

vec_01: jmp     code_71A8

vec_02: jmp     tape_load

vec_03: jmp     tape_save

vec_04: jmp     L71CB

vec_05: jmp     tape_prompt

vec_06: jmp     L7293

vec_07: jmp     L729B

vec_08: jmp     L71FF

vec_09: jmp     L7204

vec_10: jmp     L7201

vec_11: jmp     kb_scan

keyin:  jmp     kb_wait

print_cr:
        jmp     cr_out

putchar:jmp     ch_out

main:   jmp     game_main

; Point d'entree : copie la zone sauvegarde, vide la pile, reinitialise les variables, affiche le prompt puis boucle de commandes
; Point de depart du jeu, juste apres le chargement de la cassette.
; Il met de cote l'etat de depart, prepare la memoire, puis entre dans la grande boucle
; du jeu : afficher la situation, lire la commande du joueur, faire avancer le monde.
; Technique : boot_copy, init de la pile, RAZ des variables, puis game_main.
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
        sta     $C4
        sta     $0A
        lda     #$01
        sta     outen
        sta     phase
        lda     $65
        cmp     #$FF
        bne     L2C99
        jsr     code_4D84
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

L2C99:  jsr     L2DEA
        beq     L2CC8
L2C9E:  ldx     #$40
        lda     #$00
L2CA2:  sta     L4782,x
        dex
        bne     L2CA2
        ldx     #$00
        ldy     #$00
L2CAC:  jsr     L2ED5
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
        sta     $D2
        sta     $D1
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        jsr     code_3111
        bne     L2D45
        lda     $5F
        pha
        lda     #$17
        sta     ptr2
        lda     #$4A
        sta     ptr2_hi
        jsr     L3065
        lda     $65
        sta     $B0
        lda     #$00
        sta     $7E
L2CFB:  lda     #$00
        sta     $57
        jsr     L357C
        bne     L2D55
        lda     #$01
        sta     phase
        jsr     L417C
        jsr     L4B37
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
L2D2D:  jsr     L355A
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
        jsr     L3A2D
        jmp     L2D2D

L2D73:  lda     $79
        beq     L2D7F
        jsr     L3B75
L2D7A:  pla
        pla
        jmp     L2C99

L2D7F:  lda     $F2
        sta     L466F
        lda     $F3
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

L2D97:  jsr     L3A0B
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

; Remet a zero les variables de travail ($97.., $AF, $CC/$CD) puis saute a la boucle principale ($7779)
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

L2DDB:  lda     $57
        bne     L2E0F
        lda     #$08
        jsr     putchar
        jsr     putchar
        lda     #$00
        rts

L2DEA:  lda     #$30
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
L2E04:  stx     $B8
        jsr     L406D
        jsr     L2EA9
        jmp     L2E12

L2E0F:  jsr     L406D
L2E12:  cpx     #$00
        bne     L2E1A
        cmp     #$40
        beq     L2DDB
L2E1A:  cmp     #$7F
        bne     L2E24
        jsr     L40AC
        jmp     L2E04

L2E24:  cmp     #$08
        bne     L2E40
        cpx     #$00
        beq     L2E0F
        jsr     putchar
        dex
        lda     L40BE,x
        cmp     #$22
        bne     L2E0F
        lda     $B8
        eor     #$01
        sta     $B8
        jmp     L2E0F

L2E40:  cmp     #$40
        bcs     L2E68
        cmp     #$22
        bne     L2E58
        lda     $B8
        eor     #$01
        sta     $B8
        bne     L2E53
        jsr     L2E98
L2E53:  lda     #$22
        jmp     L2E68

L2E58:  cmp     #$20
        beq     L2E68
        cmp     #$0D
        beq     L2E76
        cmp     #$2E
        beq     L2E68
        cmp     #$2C
        bne     L2E0F
L2E68:  cpx     #$80
        beq     L2E0F
        jsr     putchar
        sta     L40BE,x
        inx
        jmp     L2E0F

L2E76:  lda     $B8
        beq     L2E7D
        jsr     L2E8C
L2E7D:  jsr     L2E98
        lda     #$0D
        sta     L40BE,x
        inx
        jsr     putchar
        lda     #$01
        rts

L2E8C:  jsr     L2E98
        lda     #$22
        sta     L40BE,x
        inx
        jmp     putchar

L2E98:  lda     L40BD,x
        cmp     #$2E
        beq     L2EA8
        lda     #$2E
        sta     L40BE,x
        inx
        jsr     putchar
L2EA8:  rts

L2EA9:  cmp     #$15
        beq     L2ECB
        cmp     #$08
        beq     L2EC6
        cmp     #$0A
        beq     L2ED0
        cmp     #$0B
        beq     L2EBA
        rts

L2EBA:  lda     #$4E
L2EBC:  sta     L40BE,x
        inx
        jsr     putchar
        lda     #$0D
        rts

L2EC6:  lda     #$57
        jmp     L2EBC

L2ECB:  lda     #$45
        jmp     L2EBC

L2ED0:  lda     #$53
        jmp     L2EBC

L2ED5:  tya
        pha
L2ED7:  lda     L40BE,x
        inx
        cmp     #$20
        beq     L2ED7
        dex
        stx     $60
        cmp     #$0D
        beq     L2F26
        jsr     L2FA3
        bne     L2F28
        jsr     L2FBB
        bne     L2EFA
L2EF0:  jsr     L303C
        beq     L2EFF
L2EF5:  jsr     L2FEA
        beq     L2EF0
L2EFA:  lda     #$D0
        jmp     L2F28

L2EFF:  lda     $67
        cmp     $66
        bcs     L2F43
        cmp     #$04
        bcc     L2EF5
        tya
        pha
        lda     $63
        pha
        lda     $64
        pha
        jsr     L2FEA
        bne     L2F3B
        jsr     L303C
        bne     L2F3B
        pla
        sta     $64
        pla
        sta     $63
        pla
        tay
        jmp     L2EF5

L2F26:  lda     #$C0
L2F28:  pha
        lda     #$00
        sta     adr
        sta     adr_hi
        pla
L2F30:  sta     $5B
        ora     adr_hi
        sta     adr_hi
        pla
        tay
        lda     $5B
        rts

L2F3B:  pla
        sta     $64
        pla
        sta     $63
        pla
        tay
L2F43:  tya
        pha
        ldy     #$00
L2F47:  lda     ($63),y
        iny
        and     #$80
        beq     L2F47
        cpy     #$02
        beq     L2F47
        cpy     #$03
        bne     L2F60
        dey
        dey
        lda     ($63),y
        iny
        iny
        and     #$80
        bne     L2F47
L2F60:  dey
        lda     ($63),y
        and     #$40
        beq     L2F78
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
L2F78:  ldy     #$00
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
        lda     $5B
        cmp     #$D0
        bne     L2F30
        jmp     L2EF5

L2FA3:  ldy     #$B0
        cmp     #$2E
        beq     L2FB8
        ldy     #$A0
        cmp     #$2C
        beq     L2FB8
        ldy     #$90
        cmp     #$22
        beq     L2FB8
        lda     #$00
        rts

L2FB8:  inx
        tya
        rts

L2FBB:  ldy     #$00
L2FBD:  lda     L40BE,x
        cmp     #$40
        bcc     L2FCE
        and     #$1F
        sta     L47C3,y
        inx
        iny
        jmp     L2FBD

L2FCE:  sty     $66
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
L2FEA:  tya
        clc
        adc     $63
        sta     $63
        bcc     L2FF4
        inc     $64
L2FF4:  ldy     #$00
        lda     ($63),y
        and     #$1F
        cmp     L47C3
        beq     L3000
        rts

L3000:  sta     L47D3,y
        txa
        pha
        ldx     #$01
        iny
L3008:  lda     ($63),y
        and     #$1F
        beq     L3012
        sta     L47D3,x
        inx
L3012:  lda     ($63),y
        iny
        and     #$80
        beq     L3008
        cpy     #$02
        beq     L3008
        cpy     #$03
        bne     L302B
        dey
        dey
        lda     ($63),y
        iny
        iny
        and     #$80
        bne     L3008
L302B:  stx     $67
        dey
        lda     ($63),y
        iny
        and     #$40
        beq     L3037
        iny
        iny
L3037:  pla
        tax
        lda     #$00
        rts

L303C:  txa
        pha
        tya
        pha
        lda     $66
        cmp     $67
        bcc     L3048
        lda     $67
L3048:  tax
        ldy     #$00
L304B:  lda     L47C3,y
        cmp     L47D3,y
        bne     L305E
        iny
        dex
        bne     L304B
        pla
        tay
        pla
        tax
        lda     #$00
        rts

L305E:  pla
        tay
        pla
        tax
        lda     #$01
        rts

L3065:  jsr     L46E6
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
        jmp     L471B

L308F:  .byte   "> "
L3091:  .byte   "LOOK."
        .byte   $0D
; Copie le bloc sauvegarde $1B1A -> $91D0 (1366 octets) ; $6C = compteur
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
        jsr     L30DF
        bne     L30AB
        dec     $6C
        bne     L309D
        rts

; Recopie le bloc $91D0 -> $1B1A (copie inverse, meme gabarit)
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
        jsr     L30DF
        bne     L30CF
        dec     $6C
        bne     L30C1
        rts

L30DF:  inc     ptr
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
code_3111:
        jsr     L3474
        lda     #$FF
        sta     $6D
        lda     #$C0
        sta     $5B
L311C:  lda     #$00
        sta     $9D
        lda     $6D
        ora     #$C7
        sta     $6D
        lda     $6E
        cmp     #$02
        bne     L3132
        lda     $6D
        and     #$FD
        sta     $6D
L3132:  jsr     L3479
L3135:  ldx     #$09
        lda     #$00
L3139:  sta     $A3,x
        dex
        bpl     L3139
        lda     $6D
        ora     #$10
        sta     $6D
L3144:  jsr     L3485
        lsr     a
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
        jmp     (L315A)

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
code_3172:
        lda     $6D
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
L31B2:  jsr     L356E
        lda     $5B
        cmp     #$A0
        bne     L31BE
        jmp     L311C

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
L3219:  jsr     L4702
        lda     #$0F
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        lda     $65
        sta     $6C
        lda     $57
        beq     L3231
        inc     $6C
        jsr     L34BD
L3231:  jsr     L34CB
L3234:  lda     $6C
        beq     L324C
        jsr     L34CB
        ldy     #$01
        lda     (ptr2),y
        and     #$7F
        dey
        ora     (ptr2),y
        bne     L3249
        jsr     L34D0
L3249:  jmp     L3234

L324C:  lda     $65
        sta     $6C
        jsr     L471E
        jsr     L4702
        jsr     L34A7
L3259:  lda     $6C
        beq     L3289
        jsr     L34A7
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
        jsr     L3516
        jmp     L3259

L3289:  jsr     L471E
        lda     #$00
        rts

        lda     $6D
        and     #$02
        bne     L32EF
        ldx     #$00
        stx     $5B
        lda     $6D
        and     #$04
        bne     L32A2
        jmp     L3554

L32A2:  lda     $6E
        cmp     #$02
        bne     L32AB
        jsr     L3471
L32AB:  lda     $6D
        and     #$FD
        sta     $6D
        ldx     #$02
        jsr     L3546
        jmp     L3135

        lda     $6D
        and     #$F7
        sta     $6D
        pha
        lda     $5B
        pha
L32C3:  jsr     L3485
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
        jmp     code_3172

        lda     $6D
        and     #$FE
        sta     $6D
L32EF:  lda     #$30
        sta     $5B
        lda     $6D
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
        jmp     code_3172

L3314:  jsr     L3474
        lda     $6D
        and     #$04
        bne     L3320
        jmp     L3554

L3320:  lda     $6D
        and     #$08
        beq     L332C
L3326:  jsr     L353E
        jmp     L3135

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
L333B:  jsr     L3485
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

L3360:  jsr     L353E
        pla
        pla
        sta     adr_hi
        pla
        sta     adr
        pla
        pla
        ldx     $02
        jsr     L3546
        jmp     L3135

        lda     $6D
        and     #$EF
        sta     $6D
        jmp     L3144

        lda     $6D
        and     #$04
        beq     L338C
        lda     $5A
        cmp     #$A0
        bne     L338C
        jmp     L32EF

L338C:  lda     #$70
        sta     $5B
L3390:  jsr     L3429
L3393:  jsr     L3485
        cmp     #$70
        beq     L3390
        cmp     #$80
        bne     L33B0
        lda     $6D
        and     #$10
        bne     L33A7
        jmp     L3554

L33A7:  lda     $6D
        and     #$EF
        sta     $6D
        jmp     L3393

L33B0:  cmp     #$60
        beq     L33BF
        cmp     #$50
        beq     L33C8
        lda     $60
        sta     $5F
        jmp     L33D0

L33BF:  jsr     L340B
        jsr     L3485
        jmp     L33B0

L33C8:  lda     adr
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
        jsr     L34BD
        ldy     #$01
        lda     (ptr2),y
        pha
        jsr     L356E
        pla
        bne     L33F4
        jsr     L356E
        jsr     L3479
L33F4:  jsr     L3466
        ldy     #$01
        lda     #$40
        sta     (ptr2),y
L33FD:  jmp     L3135

L3400:  jsr     L3471
L3403:  jsr     L343A
        beq     L33FD
        lda     #$01
        rts

L340B:  ldx     #$06
L340D:  lda     $A3,x
        inx
        ora     $A3,x
        beq     L341F
        inx
        lda     $A3,x
        inx
        ora     $A3,x
        beq     L341F
        jmp     L3552

L341F:  lda     adr_hi
        sta     $A3,x
        dex
        lda     adr
        sta     $A3,x
        rts

L3429:  ldx     $9D
        inx
        stx     $9D
        cpx     #$03
        bcc     L3435
        jmp     L3552

L3435:  ldx     #$00
        jmp     L340D

L343A:  lda     $6D
        and     #$40
        bne     L3466
        lda     $6D
        and     #$80
        bne     L3449
        jmp     L3552

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

L3466:  lda     $6D
        and     #$BF
        sta     $6D
        ldx     #$04
        jmp     L3451

L3471:  jsr     L34A9
L3474:  lda     #$00
        sta     $6E
        rts

L3479:  ldy     #$00
        lda     #$00
L347D:  sta     (ptr2),y
        iny
        cpy     #$1A
        bne     L347D
        rts

L3485:  ldx     $5F
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

L34A7:  dec     $6C
L34A9:  lda     ptr2
        sta     ptr
        lda     ptr2_hi
        sta     ptr_hi
L34B1:  jsr     L34BD
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     L34B1
        rts

L34BD:  lda     ptr2
        sec
        sbc     #$18
        sta     ptr2
        lda     ptr2_hi
        sbc     #$00
        sta     ptr2_hi
        rts

L34CB:  dec     $6C
        jmp     L355A

L34D0:  ldy     #$01
        lda     (ptr),y
        and     #$7F
        ora     (ptr2),y
        sta     (ptr2),y
        dey
        lda     (ptr),y
        sta     (ptr2),y
        jsr     L34BD
        ldy     #$04
        lda     (ptr2),y
        iny
        ora     (ptr2),y
        php
        jsr     L356E
        plp
        bne     L34F1
        rts

L34F1:  lda     $6D
        and     #$80
        bne     L34F8
        rts

L34F8:  ldy     #$08
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
L3516:  jsr     L352E
        ldy     #$02
        lda     (ptr2),y
        iny
        ora     (ptr2),y
        beq     L3523
        rts

L3523:  ldy     #$02
        jsr     L3533
        rts

        ldx     #$06
        jmp     L3535

L352E:  ldx     #$0A
        jmp     L3535

L3533:  ldx     #$02
L3535:  lda     (ptr),y
        sta     (ptr2),y
        iny
        dex
        bne     L3535
        rts

L353E:  lda     $6D
        and     #$FD
        sta     $6D
        ldx     #$00
L3546:  txa
        tay
        lda     adr
        sta     (ptr2),y
        iny
        lda     adr_hi
        sta     (ptr2),y
        rts

L3552:  pla
        pla
L3554:  jmp     L2D45

        lda     #$01
        rts

L355A:  lda     ptr2
        sta     ptr
        lda     ptr2_hi
        sta     ptr_hi
L3562:  jsr     L356E
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     L3562
        rts

L356E:  lda     ptr2
        clc
        adc     #$18
        sta     ptr2
        lda     ptr2_hi
        adc     #$00
        sta     ptr2_hi
        rts

L357C:  jsr     L359B
        beq     L3582
        rts

L3582:  jsr     L36D5
        beq     L358A
        lda     #$00
        rts

L358A:  lda     #$03
        sta     $57
        rts

L358F:  lda     #$00
        sta     raw
        ldx     #$10
L3595:  sta     $D7,x
        dex
        bpl     L3595
        rts

L359B:  lda     #$FF
        sta     arg2
        sta     arg1
        jsr     L358F
        jsr     L3790
        bne     L35AE
        lda     #$01
        sta     $57
        rts

L35AE:  lda     $6C
        sta     wid
        sta     $14
        jsr     move_flags
        jsr     L3674
        lda     #$00
        sta     phase
        lda     xmode
        and     #$0C
        beq     L35E1
        lda     $EC
        sta     $7E
        rol     a
        rol     a
        and     #$01
        sta     $ED
L35CE:  jsr     L35E4
        beq     L35D8
        lda     #$02
        sta     $57
        rts

L35D8:  lda     $7E
        beq     L35E1
        jsr     L363E
        bne     L35CE
L35E1:  lda     #$00
        rts

L35E4:  jsr     L38E5
        bne     L35FD
        lda     $DA
        cmp     #$01
        beq     L35F0
        rts

L35F0:  lda     $F0
        sta     arg1
        jsr     L3690
        jsr     L36BB
        bne     L3622
        rts

L35FD:  inc     $D9
        jsr     L36BB
        beq     L361C
        jsr     L3690
        jsr     L3948
L360A:  beq     L35E4
        lda     $ED
        cmp     #$01
        bne     L3613
        rts

L3613:  lda     arg1
        sta     $F0
        inc     $DA
        jmp     L35E4

L361C:  jsr     L36D5
        jmp     L360A

L3622:  jsr     L3948
        bne     L3635
        lda     $DB
        cmp     #$01
        beq     L362E
        rts

L362E:  lda     $F1
        sta     arg2
        lda     #$00
        rts

L3635:  lda     arg2
        sta     $F1
        inc     $DB
        jmp     L3622

L363E:  jsr     L4702
L3641:  jsr     L356E
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
L3661:  jsr     L53C3
        cmp     #$FF
        beq     L3641
        cmp     arg1
        bne     L3661
        lda     #$01
L366E:  tax
        jsr     L471E
        txa
        rts

L3674:  lda     $7E
        beq     L3679
        rts

L3679:  lda     xaux
        lsr     a
        lsr     a
        jsr     L36A5
        lda     direct
        beq     L3687
        jsr     code_54E9
L3687:  lda     ptr
        sta     svptr
        lda     ptr_hi
        sta     svptr_hi
        rts

L3690:  lda     xaux
        jsr     L36A5
        lda     variant
        beq     L369C
        jsr     code_54E9
L369C:  lda     ptr
        sta     $EA
        lda     ptr_hi
        sta     $EB
        rts

L36A5:  and     #$03
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

L36BB:  lda     xmode
        and     #$04
        bne     L36C2
        rts

L36C2:  lda     $D8
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

L36D5:  jsr     L4B37
        lda     passok
        rts

; Coeur du deplacement : resout la sortie, evalue la condition, execute
; Coeur du deplacement : quand le joueur demande a aller quelque part, cette routine
; retrouve la sortie correspondante du lieu, verifie ses eventuelles conditions (objet
; requis, passage cache...), puis effectue ou refuse le deplacement.
; Technique : exit_ptr(wid), flags via code_4141, conditions cond1/cond2 via cond_eval,
; execution en mode sonde (L4B37) ou en deux temps (L35E4).
move_core:
        lda     svptr
        pha
        lda     svptr_hi
        pha
        lda     exitp
        pha
        lda     exitp_hi
        pha
        jsr     L46E6
        lda     wid
        jsr     exit_ptr
        jsr     L358F
        jsr     code_4141
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
L371E:  jsr     L3679
        lda     #$00
        sta     phase
        lda     xmode
        and     #$0C
        bne     L3733
        jsr     L4B37
        lda     passok
        jmp     L3743

L3733:  lda     #$01
        sta     $ED
        jsr     L35E4
        beq     L3741
        lda     #$00
        jmp     L3743

L3741:  lda     #$01
L3743:  tax
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
        jsr     L471B
        txa
        rts

; Evalue la condition d'une sortie (slot X ; $FF = aucune)
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
        jsr     L43E4
        lda     #$01
        rts

L3769:  txa
        jsr     L43F3
        lda     #$01
        rts

; Derive les drapeaux direct/variante depuis l'octet mode $78
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

L3790:  ldy     #$01
        lda     (ptr2),y
        and     #$80
        sta     $EC
        lda     (ptr2),y
        and     #$7F
        sta     $F3
        dey
        lda     (ptr2),y
        sta     $F2
        ldx     #$03
        lda     #$00
L37A7:  sta     $F4,x
        dex
        bpl     L37A7
        ldx     #$00
        lda     #$02
        sta     $6C
        ldy     #$04
        jsr     L38C9
        ldy     #$0E
        jsr     L38C9
        ldy     #$06
        jsr     L38C9
        ldy     #$10
        jsr     L38C9
        lda     #$00
        sta     $79
        lda     #$E2
        sta     exitp
        lda     #$26
        sta     exitp_hi
        lda     #$01
        sta     $6C
        lda     #$F2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
L37DE:  lda     exitp
        sta     $7C
        lda     exitp_hi
        sta     $7D
        jsr     code_433A
        beq     L3804
        lda     exitp
        clc
        adc     #$08
        sta     exitp
        lda     exitp_hi
        adc     #$00
        sta     exitp_hi
        inc     $6C
        ldy     #$00
        lda     (exitp),y
        iny
        ora     (exitp),y
        bne     L37DE
        rts

L3804:  jsr     L380A
        lda     #$01
        rts

L380A:  txa
        beq     L381C
        ldx     #$01
L380F:  lda     $F4,x
        tay
        lda     $F6,x
        sta     $F4,x
        tya
        sta     $F6,x
        dex
        bpl     L380F
L381C:  jsr     code_4141
        lda     $F4
        ora     $F5
        bne     L382A
        lda     xaux
        jmp     L384A

L382A:  lda     $F4
        ldy     #$0E
        cmp     (ptr2),y
        bne     L3839
        iny
        lda     $F5
        cmp     (ptr2),y
        beq     L3846
L3839:  lda     $F4
        ldy     #$10
        cmp     (ptr2),y
        bne     L3846
        iny
        lda     $F5
        cmp     (ptr2),y
L3846:  bne     L384F
        lda     xmode
L384A:  eor     #$20
        jmp     L3851

L384F:  lda     xmode
L3851:  and     #$20
        beq     L3860
        lda     #$08
        sta     $EE
        lda     #$12
        sta     $EF
        jmp     L3868

L3860:  lda     #$12
        sta     $EE
        lda     #$08
        sta     $EF
L3868:  ldy     $EE
        ldx     #$05
        lda     #$00
        jsr     L38A0
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
L389A:  ldy     $EF
        ldx     #$0B
        lda     #$01
L38A0:  pha
        lda     #$06
L38A3:  pha
        lda     (ptr2),y
        sta     $D7,x
        inx
        iny
        pla
        sec
        sbc     #$01
        bne     L38A3
        ldy     #$06
        lda     #$00
L38B4:  dex
        ora     $D7,x
        dey
        bne     L38B4
        cmp     #$00
        bne     L38C0
        pla
        rts

L38C0:  pla
        tax
        lda     $D7,x
        ora     #$01
        sta     $D7,x
        rts

L38C9:  dec     $6C
        bpl     L38CE
        rts

L38CE:  lda     (ptr2),y
        sta     $F4,x
        iny
        inx
        lda     (ptr2),y
        sta     $F4,x
        dey
        dex
        ora     (ptr2),y
        bne     L38DF
        rts

L38DF:  inx
        inx
        rts

L38E2:
L38E3           := * + 1
L38E4           := * + 2
        jmp     L0000

L38E5:  jsr     L4702
        lda     svptr
        sta     ptr
        lda     svptr_hi
        sta     ptr_hi
        lda     direct
        cmp     #$01
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
L3908:  jsr     L3928
        pha
        lda     ptr
        sta     svptr
        lda     ptr_hi
        sta     svptr_hi
        jsr     L471E
        pla
        cmp     #$FF
        rts

L391B:  lda     #$F8
        sta     L38E3
        lda     #$54
        sta     L38E4
        jmp     L3908

L3928:  lda     #$DC
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     L38E2
        cmp     #$FF
        bne     L3938
        rts

L3938:  sta     arg1
        lda     $D7
        ora     #$02
        sta     $D7
        jsr     code_4B07
        lda     passok
        beq     L3928
        rts

L3948:  jsr     L4702
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
L396D:  jsr     L3993
        pha
        lda     ptr
        sta     $EA
        lda     ptr_hi
        sta     $EB
        lda     xmode
        and     #$01
        sta     $80
        jsr     L471E
        pla
        cmp     #$FF
        rts

L3986:  lda     #$F8
        sta     L38E3
        lda     #$54
        sta     L38E4
        jmp     L396D

L3993:  lda     #$E2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     L38E2
        cmp     #$FF
        bne     L39A3
        rts

L39A3:  sta     arg2
        lda     $D8
        ora     #$02
        sta     $D8
        jsr     L36D5
        beq     L3993
        rts

L39B1:  jsr     L39B7
        jmp     L4402

L39B7:  lda     #$01
        sta     raw
        sta     phase
        rts

L39BE:  sta     $57
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

L39CF:  lda     $EE
        ldy     #$05
L39D3:  jsr     L39BE
        ldx     #$00
        lda     $D7,y
        sta     L466F,x
        inx
        iny
        lda     $D7,y
        sta     L466F,x
        jsr     L39B1
        ldy     crcnt
        lda     #$01
        rts

L39EE:  lda     $D8
        and     #$01
        bne     L39F7
        jmp     L3ADF

L39F7:  lda     $D8
        and     #$02
        beq     L3A36
        lda     $DB
        bne     L3A04
        jmp     L3A2D

L3A04:  lda     $EF
        ldy     #$0B
        jmp     L39D3

L3A0B:  lda     $DA
        cmp     #$01
        beq     L39EE
        lda     $D7
        and     #$01
        bne     L3A1A
        jmp     L3AB5

L3A1A:  lda     $D7
        and     #$02
        beq     L3A6B
        lda     $D9
        beq     L3A2D
        cmp     #$01
        bne     L39CF
        jsr     L36BB
        bne     L39EE
L3A2D:  jsr     L39B7
        jsr     L4B37
        lda     #$00
        rts

L3A36:  jsr     code_54E9
        lda     #$01
        sta     variant
        lda     #$E2
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     L54F8
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
        jsr     L53C3
        cmp     #$FF
        beq     L3AA0
L3A63:  sta     arg2
        jsr     L416A
        lda     #$01
        rts

L3A6B:  jsr     code_54E9
        lda     #$01
        sta     direct
        lda     #$DC
        sta     ptr3
        lda     #$00
        sta     ptr3_hi
        jsr     L54F8
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
        jsr     L53C3
        cmp     #$FF
        beq     L3AA0
L3A98:  sta     arg1
        jsr     L416A
        lda     #$01
        rts

L3AA0:  jsr     L39B7
        lda     ptr3
        sta     L466F
        lda     ptr3_hi
        sta     L4670
        jsr     L4402
        tax
        ora     ($A9),y
        ora     ($60,x)
L3AB5:  ldx     #$00
        lda     $F2
        sta     L466F,x
        inx
        lda     $F3
        sta     L466F,x
        inx
        jsr     L3B26
        lda     $DA
        bne     L3AD2
        jsr     L39B1
        clv
        ora     ($A9),y
        ora     ($60,x)
L3AD2:  lda     $EE
        jsr     L39BE
        jsr     L39B1
        .byte   $9C
code_3ADB:
        ora     ($A9),y
        ora     ($60,x)
L3ADF:  ldx     #$00
        lda     $F2
        sta     L466F,x
        inx
        lda     $F3
        sta     L466F,x
        inx
        jsr     L3B26
        txa
        pha
        lda     arg1
        jsr     L43F3
        pla
        tax
        lda     ptr
        sta     L466F,x
        inx
        lda     ptr_hi
        sta     L466F,x
        inx
        jsr     L3B21
        lda     $DB
        bne     L3B14
        jsr     L39B1
        ldx     $A911,y
        ora     ($60,x)
L3B14:  lda     $EF
        jsr     L39BE
        jsr     L39B1
        tya
        ora     ($A9),y
        ora     ($60,x)
L3B21:  lda     #$F0
        jmp     L3B28

L3B26:  lda     #$D0
L3B28:  sta     L3B34
        sta     L3B58
        ldy     #$03
        lda     (exitp),y
        and     #$20
L3B34:  bne     L3B43
        lda     #$00
        sta     L466F,x
        inx
        sta     L466F,x
        inx
        jmp     L3B52

L3B43:  ldy     #$02
        lda     (exitp),y
        sta     L466F,x
        inx
        iny
        lda     (exitp),y
        sta     L466F,x
        inx
L3B52:  ldy     #$07
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

L3B75:  lda     $F2
        sta     L466F
        lda     $F3
        sta     L4670
        lda     $F4
        sta     L4671
        lda     $F5
        sta     L4672
        lda     $F6
        sta     L4673
        lda     $F7
        sta     L4674
        jsr     L39B1
        dey
        ora     ($A9),y
        ora     ($60,x)
        ldy     #$0D
        ldx     #$00
L3B9F:  lda     adr
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
        jmp     L311C

L3BB7:  lda     L3BE0,x
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
        jmp     L3135

        lda     $6E
        cmp     #$01
        beq     L3C17
        jmp     L3554

L3C17:  lda     #$02
        sta     $6E
        ldy     #$01
        lda     (ptr2),y
        ora     #$80
        sta     (ptr2),y
        jmp     L3135

        lda     $6E
        cmp     #$02
        beq     L3C30
        lda     #$01
        sta     $6E
L3C30:  jmp     L3135

        ldx     #$05
L3C35:  lda     $82,x
        sta     $A7,x
        dex
        bpl     L3C35
        lda     $6D
        and     #$80
        jsr     L3C46
        jmp     L3135

L3C46:  beq     L3C4B
        jmp     L3466

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
        ldx     $D2
        sta     L4905,x
        inc     $D2
L3C73:  jsr     L3485
        cmp     #$90
        bne     L3C73
        lda     adr
        ora     adr_hi
        bne     L3C73
        lda     #$C0
        sta     L4781,x
        jmp     L3135

        .byte   " "
        .byte   $D4
        .byte   "<"
code_3C8B:
        jmp     L2C3D

        lda     obj
        beq     L3C95
        jmp     L3135

L3C95:  jsr     L46E9
        ldx     #$85
        ldy     #$71
        lda     ploc
        jsr     L5399
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
; TODO pointeur $0000
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

        jsr     L3CD4
        jmp     L3C07

L3CD4:  jsr     L46E9
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
        jsr     code_3D14
        beq     L3CF2
        jsr     putchar
L3CF2:  lda     #$0A
        jsr     code_3D14
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
code_3D14:
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

; Trampoline cassette : lit [longueur, source] apres l'appel et saute au handler
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

L3D6A:  jsr     tape_tramp
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

; Commande LOAD : invite 'PRESS ANY KEY' puis charge un bloc cassette (vec_02)
load_handler:
        jsr     L46E6
        jsr     vec_05
        jsr     L3D6A
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
; Ecrit un bloc SAVE sur cassette (appel vec_03 avec [longueur, source] inline)
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
; Echec de SAVE : affiche l'erreur $1A1A, attend une touche puis abandonne
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

; Commande SAVE : ecrit les 4 blocs (ZP, etats, scripts, records) puis verifie
cmd_save:
        jsr     L46E6
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
; Restaure le contexte et revient a la boucle de commandes
cmd_next:
        jsr     L471B
        jmp     L3C07

        .byte   "TAPE LOADING ERROR :- PRESS ANY"



        .byte   " KEY TO RESTART GAME."


        .byte   $14
code_3E5B:
        cmp     #$00
        php
        lda     $D2
        beq     L3E88
        cmp     $D1
        beq     L3E88
        ldx     $D1
        lda     L4905,x
        sta     $91
        inx
        stx     $D1
        lda     arg1
        plp
        php
        bne     L3E8A
        lda     $91
        sta     $5F
L3E7A:  jsr     L3485
        cmp     #$C0
        bne     L3E7A
        ldx     $60
        lda     #$90
        sta     L4783,x
L3E88:  lda     #$00
L3E8A:  sta     $90
        plp
        rts

L3E8E:  lda     $90
        cmp     obj
        bne     L3E95
L3E94:  rts

L3E95:  ldx     #$00
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

L3EB2:  lda     $91
        sta     $5F
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
        lda     #$00
        sta     $65
        sta     $D3
L3EC4:  jsr     code_3111
        beq     L3ED0
        cmp     #$02
        beq     L3ED0
        jmp     L3FCF

L3ED0:  lda     $65
        clc
        adc     $D3
        sta     $D3
        lda     #$00
        sta     $65
        ldx     $5F
        lda     L4783,x
        and     #$F0
        cmp     #$C0
        bne     L3EC4
        lda     #$90
        sta     L4783,x
        lda     #$0A
        sta     $D0
        ldx     #$00
L3EF1:  lda     L48D3,x
        beq     L3F0A
        lda     $D0
        sec
        sbc     L48D4,x
        sta     $D0
        txa
        clc
        adc     #$05
        tax
        cpx     #$32
        bne     L3EF1
        jmp     L3FCF

L3F0A:  lda     $D0
        bne     L3F11
        jmp     L3FCF

L3F11:  lda     #$00
        sta     L48D5,x
        sta     $D4
        sta     $65
        lda     $D3
        sta     $6C
        lda     #$27
        sta     ptr2
        lda     #$49
        sta     ptr2_hi
L3F26:  inc     $65
        jsr     L356E
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        bne     L3F26
        lda     $65
        cmp     $D0
        bcs     L3F3F
        sta     $D4
        dec     $6C
        bne     L3F26
L3F3F:  lda     $D4
        bne     L3F46
        jmp     L3FCF

L3F46:  sta     L48D4,x
        lda     $90
        sta     L48D3,x
        lda     #$00
        sta     $90
        lda     #$0A
        sec
        sbc     $D0
        asl     a
        asl     a
        asl     a
        sta     $D0
        asl     a
        clc
        adc     $D0
        adc     #$E3
        sta     ptr
        lda     #$00
        adc     #$47
        sta     ptr_hi
        ldy     #$00
L3F6C:  ldx     #$18
L3F6E:  lda     L4927,y
        sta     (ptr),y
        iny
        dex
        bne     L3F6E
        dec     $D4
        bne     L3F6C
        jmp     L3F8E

L3F7E:  .byte   $CA
code_3F7F:
        sta     L3F7E
        jsr     L46E6
        lda     $90
        cmp     obj
        bne     L3F8E
        jmp     L3EB2

L3F8E:  jsr     L4035
        lda     L3F7E
        beq     L3FC5
        lda     L48D5,x
        sta     $7E
        lda     L48D6,x
        sta     svptr
        lda     L48D7,x
        sta     svptr_hi
        jsr     L357C
        bne     L3FD4
        jsr     L36D5
        beq     L3FCA
        ldx     $CF
        lda     svptr
        sta     L48D6,x
        lda     svptr_hi
        sta     L48D7,x
        lda     $7E
        sta     L48D5,x
        bne     L3FC5
        jsr     L3FE5
L3FC5:  lda     #$01
        jmp     L471B

L3FCA:  jsr     L3FE5
        bne     L3FCA
L3FCF:  lda     #$00
        jmp     L471B

L3FD4:  lda     $7E
        beq     L3FCA
        ldx     $CF
        lda     #$00
        sta     L48D5,x
        jsr     L3FE5
        jmp     L3F8E

L3FE5:  jsr     L4702
        jsr     fetch_retaddr
L3FEB:  jsr     L356E
        ldy     #$01
        lda     (ptr2),y
        and     #$40
        beq     L3FFA
        inc     $D0
        bne     L3FEB
L3FFA:  lda     #$09
        sec
        sbc     $D0
        sta     $D0
        beq     L4013
        ldy     #$00
L4005:  ldx     #$18
L4007:  lda     (ptr2),y
        sta     (ptr),y
        iny
        dex
        bne     L4007
        dec     $D0
        bne     L4005
L4013:  ldx     $CF
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

L4035:  jsr     L3E8E
L4038:  lda     #$E3
        sta     ptr2
        lda     #$47
        sta     ptr2_hi
        stx     $CF
        tya
        tax
        sta     $D0
        beq     L404E
L4048:  jsr     L355A
        dex
        bne     L4048
L404E:  ldx     $CF
        rts

L4051:  jsr     L46E6
        tax
        lda     obj
        pha
        stx     obj
        jsr     L3E95
        bne     L4067
        jsr     L4038
L4062:  jsr     L3FE5
        bne     L4062
L4067:  pla
        sta     obj
        jmp     L471B

L406D:  jsr     vec_11
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
        bne     L406D
        jsr     L40AC
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

L40AC:  cpx     #$00
        bne     L40B1
        rts

L40B1:  lda     #$08
        jsr     putchar
        dex
        jmp     L40AC

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
code_4141:
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

L416A:  lda     #$00
        sta     passok
        lda     #$01
        sta     phase
        lda     $5E
        bne     L4179
        jsr     L417C
L4179:  lda     #$00
        rts

L417C:  tya
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
        lda     wid
        jsr     exit_ptr
        lda     passok
        beq     L41A2
        lda     obj
        bne     L41A2
        jsr     print_cr
L41A2:  jsr     code_4141
        and     #$10
        beq     L41AC
        jmp     L4229

L41AC:  jsr     L454F
        lda     #$B4
        sta     adr
        lda     #$01
        sta     adr_hi
        lda     passok
        bne     L41BE
        jsr     word_render
L41BE:  ldy     #$06
        jsr     L4232
        jsr     is_dark
        ldy     #$00
        bcc     L41E0
        lda     wid
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

L41E0:  jsr     L4232
L41E3:  lda     xmode
        and     #$08
        beq     L41FE
        lda     xmode
        and     #$20
        beq     L41F2
        jsr     L4232
L41F2:  ldy     #$04
        lda     xaux
        bpl     L41FB
        jsr     L4232
L41FB:  jsr     L455B
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
        jsr     L4232
L4215:  ldy     #$04
        lda     xaux
        bmi     L421E
        jsr     L4232
L421E:  jsr     L4573
L4221:  lda     #$2E
        jsr     putchar
        jsr     print_cr
L4229:  lda     #$00
        sta     $75
        pla
        tax
        pla
        tay
        rts

L4232:  lda     (exitp),y
        sta     adr
        iny
        lda     (exitp),y
        and     #$0F
        sta     adr_hi
        iny
        jmp     word_render

; Rend un mot du dictionnaire packe 5-bit, en appliquant pluriels (S/ES/IES/ING), espaces et retour a la ligne
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
; Gere les espaces entre mots et le retour a la ligne en fin de colonne
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
code_433A:
        sty     L436B
        ldy     #$00
        jsr     code_436C
        bne     L4365
        lda     #$01
        sta     $79
        jsr     code_436C
        bne     L4357
        jsr     code_436C
        bne     L4357
        ldx     #$00
        jmp     L4365

L4357:  ldy     #$02
        jsr     L4387
        bne     L4365
        jsr     L43A8
        php
        ldx     #$01
        plp
L4365:  php
        ldy     L436B
        plp
        rts

L436B:  .byte   "N"
code_436C:
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

L4387:  lda     (ptr3),y
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

L43A8:  lda     (ptr3),y
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

; Calcule $F8 = $26DA + wid*8 : pointe l'entree de sortie du lieu
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

L43E4:  jsr     L530B
        lda     ptr
        clc
        adc     #$02
        sta     ptr
        bcc     L43F2
        inc     ptr_hi
L43F2:  rts

L43F3:  jsr     L5331
        lda     ptr
        clc
        adc     #$08
        sta     ptr
        bcc     L4401
        inc     ptr_hi
L4401:  rts

L4402:  lda     $5E
        beq     L440A
        lda     #$00
        sta     phase
L440A:  jmp     print_msg

; Affiche le message dont l'adresse suit l'appel, puis reprend l'execution apres ce mot (appel de 5 octets)
; Affiche un message. Le message n'est pas passe en argument : son adresse est ecrite
; juste apres l'instruction d'appel, dans le programme. print_msg la lit a cet endroit,
; affiche le texte, puis reprend l'execution juste apres.
; Technique : l'adresse est le mot de 2 octets suivant JSR ; reprise a JSR+5 via jmp ($6A).
print_msg:
        jsr     L46E9
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

; Rend un message octet par octet : litteraux $20-5F, mots courants $60-7F, mots 2 octets (bit7), tokens <$20
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

; Saut auto-modifie vers le handler du token (adresse lue dans la table $4641)
token_dispatch:
L44A1           := * + 1
L44A2           := * + 2
        jmp     token_jumps

L44A3:  lda     #$2E
        jsr     putchar
L44A8:  jsr     print_cr
        jmp     L44BD

; Dernier octet du message : $2x = fin simple, $3x = fin + '.', $6x = fin + retour a la ligne
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

; Avance le pointeur de message courant $6A/$6B de 1 (gere la retenue)
; Petit utilitaire : avance d'un cran le pointeur de lecture du message courant.
; Technique : INC $6A, + $6B si retenue.
msgptr_inc:
        inc     L006A
        bne     L44C4
        inc     $6B
L44C4:  rts

; Token $00 : affiche le message imbrique depile de la pile ($466F) ; retour Z = saute word_render
tok_nested:
        lda     #$00
L44C7:  sta     nest
        jsr     stk_pop
        jsr     L46E9
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

; Depile une adresse de la pile de messages ($466F) vers $5C/$5D
stk_pop:ldx     msgstk
        lda     L466F,x
        sta     adr
        inx
        lda     L466F,x
        sta     adr_hi
        inx
        stx     msgstk
        rts

; Token $01 : affiche le mot dont l'adresse est empilee ($466F)
tok_stkword:
        jsr     stk_pop
        lda     #$01
        rts

; Token $02 : saut (GOTO) a l'offset signe qui suit, sans revenir (deplace le pointeur du message)
tok_skip:
        inc     tidx
        jsr     L4507
        lda     #$FF
        sta     tidx
; Tokens $05/$0A/$0F/$12 non utilises : aucun effet, on passe au suivant
tok_noop:
        lda     #$00
        rts

L4507:  lda     tidx
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

; Token $03 : affiche le mot pointe par le pointeur de travail $71/$72
tok_objw:
        lda     wptr
        sta     adr
        lda     wptr_hi
        sta     adr_hi
        lda     #$01
        rts

; Token $04 : variante du mot empile (lecture dans les tables $28BC/$28C4 si contexte imbrique)
tok_stkvar:
        jsr     stk_pop
        lda     #$01
        sta     nest
        jsr     code_4683
        lda     #$00
        rts

        lda     #$01
        jmp     L44C7

; Token $06 : affiche le nom de l'objet courant $C5 (via $461B)
tok_objC5:
        lda     #$00
        sta     nest
L454F:  lda     obj
        jsr     obj_lookup
        lda     #$00
        rts

; Token $07 : affiche l'objet $15 (selon les tables direct $43E4 ou variante $43F3)
tok_obj15:
        lda     #$01
        sta     nest
L455B:  lda     direct
        beq     L4564
        lda     arg1
        jmp     L4581

L4564:  lda     arg1
        jmp     L458A

; Token $08 : envoie le code $08 a la sortie video (vecteur $2C2F)
tok_ctrl08:
        jsr     putchar
        lda     #$00
        rts

; Token $09 : affiche l'objet $16 (variante)
tok_obj16:
        lda     #$01
        sta     nest
L4573:  lda     variant
        beq     L457C
        lda     arg2
        jmp     L4581

L457C:  lda     arg2
        jmp     L458A

L4581:  jsr     L46E9
        jsr     L43E4
        jmp     L4590

L458A:  jsr     L46E9
        jsr     L43F3
L4590:  jsr     nested_render
        jsr     fetch_retaddr
        lda     #$00
        rts

; Token $0B : reaffiche un texte a l'offset signe qui suit, puis revient (queues de messages partagees)
tok_recurse:
        jsr     L46E9
        inc     tidx
        lda     tidx
        pha
        jsr     L4507
        jsr     render_text
        pla
        sta     tidx
        jsr     fetch_retaddr
        lda     #$00
        rts

; Token $0C : pronom possessif 'his' si l'objet $C5 existe, 'your' sinon
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

; Token $0E : meme chose que $0C mais pour l'objet $15
tok_pron15:
        lda     arg1
        jmp     L45B2

; Token $10 : nom de l'objet $C5 ('is' si absent, 'someone' si $FF)
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

; Token $11 : nom de l'objet $15 (variante imbriquee)
tok_name15:
        lda     arg1
        pha
        lda     #$01
        jmp     L45D4

; Token $13 : nom de l'objet dont l'adresse est empilee
tok_nameSTK:
        ldx     msgstk
        lda     L466F,x
        pha
        inx
        stx     msgstk
        lda     #$01
        jmp     L45D4

; Affiche un message imbrique en sauvant/restaurant l'etat de rendu (pile $0200)
nested_render:
        jsr     L4702
        lda     ptr
        sta     ptr2
        lda     ptr_hi
        sta     ptr2_hi
        jsr     L5535
        jmp     L471E

; Identifiant d'objet -> mot : $FF = someone, sinon nom de l'objet
obj_lookup:
        cmp     #$FF
        beq     L4622
        jmp     L458A

L4622:  lda     #$58
        sta     adr
        lda     #$09
        sta     adr_hi
        jmp     word_render

; Traduit un octet $60-7F en mot courant via la table $1117 (the/a/and/you/to/...)
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

; Table des 32 tokens <$20 : tokens <$14 = sous-routines (retour Z = saute word_render), $14/$15/$16 = fins
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
code_4683:
        lda     adr
        pha
        lda     adr_hi
        pha
        lda     nest
        beq     L4690
        jsr     L469B
L4690:  pla
        and     #$0F
        sta     adr_hi
        pla
        sta     adr
        jmp     word_render

L469B:  lda     adr_hi
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

; Affiche un caractere ; retour Z si c'est un retour a la ligne $0D
cr_aware_out:
        jsr     putchar
        cmp     #$0D
        beq     L46E3
        rts

L46E3:  lda     #$00
        rts

L46E6:  jsr     L4702
L46E9:  sta     svA
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

L4702:  sta     svA
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

L471B:  jsr     fetch_retaddr
L471E:  sta     svA
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

; Copie sur $8A/$8B l'adresse de retour empilee (routine appelee par JSR)
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

; Affiche l'illustration associee a la cle A (table $7AC0) ; retour Z si absente
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
        jsr     L46E9
        ldx     ptr_block3
        ldy     L2C04
        jsr     L5399
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
code_4B07:
        jsr     L46E9
        jsr     code_52CA
        php
        ldx     #$00
        plp
        beq     L4B32
        lda     wid
        ldx     #$AC
        ldy     #$6F
        jsr     L5399
        ldx     #$01
        cmp     #$FF
        bne     L4B32
        lda     arg1
        jsr     L5331
        lda     wid
        jsr     L52EA
        ldx     #$01
        bcs     L4B32
        ldx     #$00
L4B32:  stx     passok
        jmp     fetch_retaddr

L4B37:  jsr     L46E9
        jsr     code_52CA
        bne     L4B42
        jmp     L4C51

L4B42:  jsr     is_dark
        bcc     L4B5F
        lda     $7F
        bne     L4B57
        jsr     L5349
        bcc     L4B57
        lda     arg2
        jsr     L534B
        bcs     L4B5F
L4B57:  jsr     print_msg
; -> $13A0 I SEE NOTHING HERE.
msg_4B5A:
        .word   $13A0
code_4B5C:
        jmp     L4BE9

L4B5F:  lda     direct
        cmp     #$01
        bne     L4B68
L4B65:  jmp     L4C20

L4B68:  lda     arg1
        cmp     #$FF
        beq     L4B65
        jsr     L5331
        lda     ptr
        sta     orec
        lda     ptr_hi
        sta     orec_hi
        lda     arg1
        jsr     L4CDF
        bne     L4BE9
        lda     arg2
        cmp     #$FF
        beq     L4BA3
        lda     variant
        cmp     #$01
        bne     L4B8F
        jmp     L4C20

L4B8F:  lda     arg2
        jsr     L5331
        lda     ptr
        sta     orec2
        lda     ptr_hi
        sta     orec2_hi
        lda     arg2
        jsr     L4CDF
        bne     L4BE9
L4BA3:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     wid
        jsr     L52EA
        bcc     L4C20
L4BB2:  ldy     #$01
        lda     (ptr),y
        asl     a
        tax
        bcs     L4BC9
        lda     L7014,x
        sta     L4C64
        lda     L7015,x
        sta     L4C65
        jmp     L4BD5

L4BC9:  lda     L7114,x
        sta     L4C64
        lda     L7115,x
        sta     L4C65
L4BD5:  jsr     L4C5D
        lda     ptr
        clc
        adc     #$02
        sta     ptr
        bcc     L4BE3
        inc     ptr_hi
L4BE3:  ldy     #$00
        lda     (ptr),y
        beq     L4BB2
L4BE9:  lda     phase
        cmp     #$01
        bne     L4C1D
        lda     obj
        cmp     #$00
        bne     code_4BFF
        jsr     is_dark
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
        jsr     L4C6D
        ldx     wid
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
        lda     arg2
        jsr     L4C6D
L4C1D:  jmp     fetch_retaddr

L4C20:  lda     wid
        ldx     #$AC
        ldy     #$6F
        jsr     L5399
        cmp     #$FF
        beq     L4C51
L4C2D:  ldy     #$01
        lda     (ptr),y
        sta     L4C64
        iny
        lda     (ptr),y
        sta     L4C65
        jsr     L4C5D
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

L4C51:  jsr     L4C57
        jmp     L4C1D

L4C57:  jsr     print_msg
; -> $139B I CANNOT DO THAT
msg_4C5A:
        .word   $139B
code_4C5C:
        rts

L4C5D:  pha
        jsr     L46E6
        txa
        pha
L4C64           := * + 1
L4C65           := * + 2
        jsr     L0000
        pla
        tax
        jsr     L471B
        pla
        rts

L4C6D:  pha
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

; Renvoie 1 si le lieu est sombre : aucune source de lumiere allumee (bit7 de +4, ou +7=$08/$04/$40) dans un objet porte ; sinon affiche 'IT IS DARK.'
is_dark:jsr     L46E6
        ldy     #$04
        lda     (crec),y
        and     #$80
        beq     L4CD5
        ldx     crec
        stx     ptr
        ldy     crec_hi
        sty     ptr_hi
        jsr     L54C8
        cmp     #$FF
        bne     L4CA5
        jsr     L5374
        ldy     #$00
        lda     (ptr),y
        bmi     L4CD5
L4CA5:  lda     #$62
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L4CAD:  jsr     L540F
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
        jsr     code_5439
        beq     L4CAD
L4CD5:  jsr     L471B
        clc
        rts

L4CDA:  jsr     L471B
        sec
        rts

L4CDF:  cmp     #$FF
        bne     L4CE4
        rts

L4CE4:  sta     L4D44
        jsr     L46E9
        lda     obj
        cmp     #$00
        beq     L4CF8
L4CF0:  lda     #$00
L4CF2:  php
        jsr     fetch_retaddr
        plp
        rts

L4CF8:  lda     L4D44
        jsr     L5331
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
        jsr     L534B
        bcs     L4CF0
        jsr     L5331
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

L4D44:  .byte   $3A,$A5,$15
code_4D47:
        cmp     #$00
        bne     L4D4E
        jmp     L5FAE

L4D4E:  jsr     L46E6
        sta     L4D83
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        ora     #$08
        sta     (ptr),y
        lda     L4D83
        jsr     L5713
        lda     L4D83
        jsr     L520D
        cmp     #$FF
        beq     L4D74
        ldy     #$00
        tya
        sta     (ptr2),y
L4D74:  lda     L4D83
        jsr     code_5AF0
        lda     L4D83
        jsr     L4051
        jmp     L471B

L4D83:  .byte   $00
code_4D84:
        lda     #$1A
        sta     crec
        lda     #$1B
        sta     crec_hi
        lda     #$00
        sta     obj
        sta     $D5
        jmp     L6487

L4D95:  lda     phase
        and     passok
        bne     L4D9D
        pla
        pla
L4D9D:  rts

L4D9E:  pla
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

L4DB7:  pha
        lda     #$E0
        sta     msg_4DFC
        lda     #$13
        sta     msg_4DFC+1
        pla
        jmp     L4DE9

L4DC6:  pha
        jsr     L530B
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
        jsr     L46E6
        jsr     code_4DF6
        jmp     L471B

L4DF5:  .byte   $22
code_4DF6:
        jsr     L530B
        jsr     print_msg
; TODO pointeur $0000
msg_4DFC:
        .word   $0000
code_4DFE:
        ldy     #$08
        lda     (ptr),y
        iny
        ora     (ptr),y
        jsr     L4E20
        lda     L4DF5
        jsr     img_show
        jsr     print_cr
        lda     L4DF5
        jsr     code_5959
L4E17:  lda     L4DF5
        jsr     code_5A0D
        jmp     code_57FD

L4E20:  beq     L4E33
        lda     (ptr),y
        sta     msg_4E30+1
        dey
        lda     (ptr),y
        sta     msg_4E30
        jsr     print_msg
; TODO pointeur $0000
msg_4E30:
        .word   $0000
code_4E32:
        rts

L4E33:  jsr     L4702
        lda     ptr
        clc
        adc     #$02
        sta     ptr2
        lda     ptr_hi
        adc     #$00
        sta     ptr2_hi
        jsr     L5535
        jmp     L471E

L4E49:  sta     L4DF5
        jsr     L530B
        jsr     L4E33
        jsr     print_cr
        jmp     L4E17

L4E58:  .byte   $1A
; Fait vivre le monde apres une commande : entites (VM), evenements differes $2B12
; Fait vivre le monde autour du joueur : chaque personnage joue son script (il se deplace,
; parle...), et les evenements differes se declenchent (un PNJ qui arrive, une porte qui
; s'ouvre...). Appele apres chaque commande reussie.
; Technique : L69E7, entity_tick (VM des PNJ), puis evt_tick (table $2B12).
world_tick:
        jsr     L46E6
        jsr     L69E7
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
; Balaye la table $2B12 : decremente les compteurs, re-arme et declenche les actions
; Parcourt la liste des evenements differes. Chaque evenement a un compte a rebours :
; quand il atteint zero, l'action prevue se declenche ; sinon on peut tester une condition.
; Technique : table $2B12, entrees de 5 octets [id, cpt, actA, cond, actB], fin $FF ;
; cpt==0 -> suivante ; cpt-- ; a 0 -> actA (evt_fire), sinon evt_cond.
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

; Si la condition est armee et que cpt l'atteint : execute l'action de l'entree
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
; Ecrit l'action a executer depuis la table $7169 puis l'appelle (L4C5D)
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
        jsr     L4C5D
L4EBE:  lda     ptr2
        clc
        adc     #$05
        sta     ptr2
        bcc     L4EC9
        inc     ptr2_hi
L4EC9:  jmp     evt_tick

; Fin de la table ($FF) : signale la fin ($0B=1) et sort
; Fin de la liste des evenements : on rend la main (et on reautorise l'affichage).
; Technique : outen=1 puis L471B.
evt_end:lda     #$01
        sta     outen
        jmp     L471B

L4ED3:  .byte   $44
L4ED4:  .byte   $0E
; Fait tourner une entite (machine virtuelle) : execute jusqu'a 6 opcodes par tick
; Fait jouer le script d'un personnage : son 'cerveau'. Chaque personnage a une petite
; suite d'instructions (se deplacer, parler, attendre, choisir au hasard) qui s'execute
; un peu a chaque tour, meme quand le joueur est ailleurs.
; Technique : table $2B45 (17 entrees de 7 octets, fin $FF) ; nibble bas de l'opcode =
; MOVE 0-4 / INDIR 5-D / GOTO E / PATCH C / RANDOM F ; au plus 6 opcodes par tick (L4ED3).
entity_tick:
        jsr     code_5235
        lda     #$45
        sta     ptr2
        lda     #$2B
        sta     ptr2_hi
L4EE0:  lda     #$00
        sta     L4ED3
        ldy     #$00
        lda     (ptr2),y
        cmp     #$FF
        bne     L4EF0
        jmp     L5008

L4EF0:  cmp     #$00
        bne     L4EF7
        jmp     L4FFA

L4EF7:  sta     obj
        jsr     L57BB
        sta     eloc
        lda     ptr
        sta     crec
        lda     ptr_hi
        sta     crec_hi
        lda     #$00
        sta     outen
        ldy     #$00
        lda     (ptr2),y
        jsr     L4702
        pha
        lda     #$1A
        sta     ptr2
        lda     #$1B
        sta     ptr2_hi
        pla
        jsr     L54A9
        php
        jsr     L471E
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
        lda     #$00
        sta     outen
L4F43:  lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     L3E8E
        php
        lda     #$00
        plp
        bne     L4F56
        lda     #$01
L4F56:  sta     once
L4F58:  ldy     #$02
        lda     (ptr2),y
        sta     $8C
        iny
        lda     (ptr2),y
        sta     $8D
L4F63:  lda     L4ED3
        cmp     #$06
        bne     L4F6D
        jmp     L4FFA

L4F6D:  ldy     #$00
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
        jsr     code_3F7F
        beq     L4FA5
        lda     #$01
        sta     phase
        sta     passok
        jsr     L46E9
        jsr     L5127
        jmp     L4FFA

L4FA5:  ldy     #$00
        lda     ($8C),y
        and     #$0F
        cmp     #$04
        bne     L4FB2
        jmp     L50AC

L4FB2:  bcs     L4FB7
        jmp     L5048

L4FB7:  jmp     L4FFA

L4FBA:  cmp     #$0E
        bne     L4FCD
        ldy     #$01
        lda     (ptr),y
        iny
        sta     (ptr2),y
        lda     (ptr),y
        iny
        sta     (ptr2),y
        jmp     L4F58

L4FCD:  cmp     #$0C
        bne     L4FE0
        ldy     #$01
        lda     (ptr),y
        tax
        ldy     #$00
        lda     (ptr2),y
        jsr     entity_goto
        jmp     L4F58

L4FE0:  cmp     #$0F
        bne     L4FEA
        jsr     L51CA
        jmp     L4F58

L4FEA:  cmp     #$00
        bne     L4FF4
        jsr     L501E
        jmp     L4F63

L4FF4:  lda     #$00
        tax
        jsr     L51DA
L4FFA:  lda     ptr2
        clc
        adc     #$07
        sta     ptr2
        bcc     L5005
        inc     ptr2_hi
L5005:  jmp     L4EE0

L5008:  lda     #$00
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

L501E:  lda     #$04
; Avance le pointeur de script $8C de A octets
; Avance d'un cran le programme (script) d'un personnage.
; Technique : $8C/$8D += A.
script_adv:
        clc
        adc     $8C
        sta     $8C
        bcc     L5029
        inc     $8D
L5029:  rts

; Avance le pointeur de script de 4 (+2 si le bit $10 est pose)
; Passe a l'instruction suivante du script d'un personnage, en sautant la taille de
; l'instruction courante.
; Technique : +4 (+2 si le bit $10 est pose), puis reecrit le PC dans l'entree de l'entite.
script_step4:
        lda     #$04
; Avance le pointeur de script de 2 (+2 si le bit $10 est pose)
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

L5048:  ldy     #$00
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
        jsr     L4C5D
        lda     passok
        cmp     #$01
        php
        ldx     #$03
        plp
        bne     L50ED
        sta     phase
        jsr     L4C5D
L509A:  ldy     #$00
        lda     (ptr),y
        and     #$20
        bne     L50A5
        jmp     L4FFA

L50A5:  lda     #$00
        sta     (ptr),y
        jmp     L4FFA

L50AC:  lda     #$02
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

L50E7:  ldx     #$02
        bne     L50ED
L50EB:  ldx     #$04
L50ED:  inc     L4ED3
        ldy     #$00
        lda     (ptr),y
        and     #$10
        bne     L50FB
        jmp     L4F58

L50FB:  txa
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

; Deplace une entite ($13/$15/$16) et affiche sa sortie si elle est visible
entity_move:
        jsr     L46E9
        jsr     move_core
        bne     L5127
        jmp     L51C7

L5127:  lda     direct
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
        jsr     L57BB
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
        jsr     L4702
        lda     L4ED4
        cmp     #$02
        beq     L518A
        cmp     #$01
        beq     L5182
        jsr     L417C
        jmp     L518A

L5182:  jsr     print_msg
; -> $1406 YOU HEAR A NOISE
msg_5185:
        .word   $1406
code_5187:
        inc     L4ED4
L518A:  jsr     L471E
        lda     #$00
        sta     outen
        pla
        sta     obj
        jmp     L51A0

L5197:  jsr     L4702
        jsr     L417C
        jsr     L471E
L51A0:  jsr     L4B37
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

L51CA:  ldy     #$01
        lda     (ptr),y
        ldy     #$01
        cmp     (ptr2),y
        bcc     L51D6
        lda     (ptr2),y
L51D6:  jsr     rand_range
        tax
L51DA:  ldy     #$01
        cmp     (ptr2),y
        bcc     L51E3
        lda     (ptr2),y
        tax
L51E3:  jsr     L46E9
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

L520D:  sta     L5234
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
code_5235:
        lda     #$00
        jsr     L57BB
        sta     ploc
        jsr     is_dark
        lda     #$00
        bcc     L5245
        lda     #$01
L5245:  sta     L4ED4
        rts

; Positionne le pointeur de script d'une entite depuis ($8A)+1..2
entity_goto:
        jsr     L46E6
        jsr     L520D
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
        jsr     L5399
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
L5276:  jmp     L471B

; Affiche un message si l'entite partage le lieu du joueur
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
        jsr     L57BB
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
        jsr     L5331
        lda     #$08
        clc
        adc     ptr
        sta     L466F
        lda     #$00
        adc     ptr_hi
        sta     L4670
        jsr     print_msg
; TODO pointeur $0000
msg_52C6:
        .word   $0000
code_52C8:
        rts

L52C9:  .byte   $8A
code_52CA:
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

L52EA:  pha
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
        jsr     L5394
        beq     L5309
        sec
        rts

L5309:  clc
        rts

L530B:  cmp     #$50
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

L5331:  ldx     #$62
        ldy     #$1A
        jsr     L5399
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

L5349:  lda     arg1
L534B:  ldx     #$C5
L534D:  stx     L536C
        cmp     #$FF
        sec
        bne     L5356
        rts

L5356:  jsr     L46E9
        jsr     L535F
        jmp     fetch_retaddr

L535F:  jsr     L5331
        tax
        ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L5371
L536C           := * + 1
        cmp     obj
        bne     L535F
        sec
        rts

L5371:  txa
        clc
        rts

L5374:  pha
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        jsr     L530B
        pla
        rts

; Mode sonde : soit execute (phase 1), soit annule et signale la reussite ($12=1)
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

L5394:  pha
        lda     #$02
        bne     L539C
L5399:  pha
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

L53C3:  jsr     L4702
L53C6:  jsr     L540F
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
        jsr     code_433A
        bne     L53C6
        lda     $80
        bne     L5405
        ldy     #$00
        lda     (ptr),y
        jsr     code_5439
        beq     L53C6
L5405:  ldy     #$00
        lda     (ptr),y
        tax
        jsr     L471E
        txa
        rts

L540F:  lda     ptr
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

L542C:  sta     L5438
        jsr     L540F
        php
        lda     L5438
        plp
        rts

L5438:  .byte   "F"
code_5439:
        sta     L5451
        jsr     L46E9
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     code_5454
        jsr     fetch_retaddr
        lda     L5451
        rts

L5451:  .byte   $08
L5452:  .byte   $C0
L5453:  .byte   $20
code_5454:
        jsr     L46E9
        ldy     #$07
        lda     (ptr2),y
        and     #$80
        beq     L5498
        ldy     #$10
        lda     (ptr),y
        sta     L5453
        jsr     L4702
        jsr     L54C8
        sta     L5452
        jsr     fetch_retaddr
        lda     L5452
        cmp     L5451
        beq     L549D
        jsr     L54C8
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

L54A9:  sta     L5451
        jsr     L54B2
        jsr     code_5454
L54B2:  lda     ptr
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

L54C8:  jsr     L46E9
L54CB:  ldy     #$01
        lda     (ptr),y
        sta     L54E8
        cmp     #$FF
        beq     L54E1
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        and     #$28
        bne     L54CB
L54E1:  jsr     fetch_retaddr
        lda     L54E8
        rts

L54E8:  .byte   $00
code_54E9:
        jsr     L5374
        lda     ptr
        clc
        adc     #$07
        sta     ptr
        bcc     L54F7
        inc     ptr_hi
L54F7:  rts

L54F8:  jsr     L540F
        beq     L5520
        ldy     #$02
        jsr     L46E9
        lda     (ptr),y
        jsr     L530B
        lda     ptr
        clc
        adc     #$02
        sta     $7C
        lda     ptr_hi
        adc     #$00
        sta     $7D
        jsr     fetch_retaddr
        jsr     code_433A
        bne     L54F8
        ldy     #$02
        lda     (ptr),y
L5520:  rts

L5521:  jsr     L4702
        lda     ptr2
        clc
        adc     #$08
        sta     ptr2
        bcc     L552F
        inc     ptr2_hi
L552F:  jsr     L5535
        jmp     L471E

L5535:  lda     nest
        bne     L5563
        ldy     #$00
        lda     (ptr2),y
        sta     adr
        iny
        lda     (ptr2),y
        sta     adr_hi
        jsr     L469B
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
        jsr     code_4683
L5575:  rts

L5576:  sta     L55AC
        jsr     L46E6
        lda     #$00
        sta     L55AD
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L5589:  jsr     L542C
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

L55A5:  jsr     L471B
        lda     L55AD
        rts

L55AC:  .byte   $63
L55AD:  .byte   $00
code_55AE:
        pha
        lda     #$02
        bne     L55B6
L55B3:  pha
        lda     #$03
L55B6:  sta     L55E3
        pla
        sta     L560F
        jsr     L46E6
        ldx     #$00
        jsr     L55C9
        txa
        jmp     L471B

L55C9:  jsr     L46E9
        lda     #$62
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L55D4:  jsr     L542C
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
        jsr     L55C9
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

L5612:  stx     key
        ldx     #$01
        stx     L5611
        jsr     L5651
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
        jsr     L5DCB
        jsr     code_5235
        pla
        sta     crec_hi
        pla
        sta     crec
        pla
        sta     obj
L564B:  lda     #$00
        sta     L5611
        rts

L5651:  sta     L5610
        jsr     L46E6
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L565F:  jsr     L542C
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
L5680:  jsr     L5651
        pla
        sta     L5610
        jmp     L565F

L568A:  jmp     L471B

L568D:  sta     L5610
        jsr     L46E6
        jsr     L530B
        ldy     #$01
        lda     (ptr),y
        sta     L56D6
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L56A5:  jsr     L540F
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
        jmp     L471B

L56D1:  lda     #$00
        jmp     L471B

L56D6:  .byte   $C0
; Tirage pseudo-aleatoire borne par A (source de bruit $93)
; Fabrique un nombre aleatoire borne, utilise pour les comportements imprevisibles
; (errance des personnages, combats...).
; Technique : melange des octets de la source de bruit $93/$94 puis ramene le resultat dans [0, A).
rand_range:
        and     #$7F
L56D9:  sta     L570F
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
code_5711:
        lda     arg1
L5713:  sta     L5710
        jsr     L46E6
        jsr     L5331
        ldy     #$01
        lda     (ptr),y
        sta     L570F
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L572B:  jsr     L542C
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
        jsr     L5521
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

L576A:  jmp     L471B

L576D:  lda     arg1
L576F:  pha
        lda     #$01
        bne     L5777
L5774:  pha
        lda     #$02
L5777:  sta     L5789
        pla
        jsr     L4702
        sta     $6C
        jsr     code_54E9
L5783:  jsr     L540F
        beq     L5790
L5789           := * + 1
        ldy     #$00
        lda     (ptr),y
        cmp     $6C
        bne     L5783
L5790:  jmp     L471E

L5793:  stx     L4C64
        sty     L4C65
        jsr     L579F
        jsr     L4C5D
L579F:  ldy     #$01
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

L57BB:  cmp     #$FF
        bne     L57C0
        rts

L57C0:  jsr     L5331
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

L57D5:  jsr     L4702
        sta     L57FB
        stx     L57FC
        jsr     code_54E9
L57E1:  jsr     L540F
        beq     L57F5
        ldy     #$02
        lda     (ptr),y
        beq     L57E1
        ldy     #$00
        lda     (ptr),y
        cmp     L57FB
        bne     L57E1
L57F5:  ldx     L57FC
        jmp     L471E

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
        jsr     L580F
        pla
        rts

L580F:  stx     L5832
        sta     L5833
        jsr     L4702
        lda     #$00
        sta     L5834
        lda     #$04
        sta     L5835
        jsr     code_5836
        lda     L5834
        bne     code_582F
        jsr     print_msg
; -> $171B NOTHING
msg_582D:
        .word   $171B
code_582F:
        jmp     L471E

L5832:  .byte   $00
L5833:  .byte   "L"
L5834:  .byte   "A"
L5835:  .byte   "S"
code_5836:
        lda     $10
        pha
        lda     L5835
        sta     $10
        jsr     L46E9
        lda     #$5F
        sta     ptr
        lda     #$1A
        sta     ptr_hi
L5849:  jsr     L542C
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
        jsr     code_5439
        beq     L58D6
        inc     L5834
        lda     #$00
        sta     cap
        sta     nest
        jsr     L5521
        lda     obj
        ldy     #$00
        cmp     (ptr),y
        beq     L58DA
        lda     #$2E
        jsr     putchar
        ldy     #$00
        lda     (ptr),y
        jsr     L58E7
        bcs     L58D6
        lda     L5833
        pha
        ldy     #$00
        lda     (ptr),y
        sta     L5833
        inc     L5835
        inc     L5835
        jsr     code_5836
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

L58E7:  sta     L5958
        jsr     L46E9
        lda     L5958
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        and     #$28
        beq     L5951
        lda     L5958
        jsr     L5576
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
L5942:  jsr     L5B9B
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
code_5959:
        sta     L5958
        jsr     L46E6
        lda     L5958
        jsr     L530B
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
        jsr     L5331
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
        jsr     L59E7
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

L59E4:  jmp     L471B

L59E7:  pha
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
code_5A0D:
        sta     L5958
        jsr     L46E6
        lda     L5958
        jsr     L530B
        lda     ptr
        clc
        adc     #$07
        sta     ptr
        bcc     L5A24
        inc     ptr_hi
L5A24:  jsr     L5A43
        beq     L5A40
        jsr     print_msg
; -> $13FE VISIBLE EXITS ARE :
msg_5A2C:
        .word   $13FE
code_5A2E:
        ldy     #$00
        lda     (ptr),y
        jsr     L59E7
        jsr     word_render
        jsr     L5A43
        bne     code_5A2E
        jsr     print_cr
L5A40:  jmp     L471B

L5A43:  lda     ptr
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
        bne     L5A43
        dey
        lda     (ptr),y
        beq     L5A43
        rts

L5A62:  lda     phase
        cmp     #$01
        bne     L5A6B
        jmp     L417C

L5A6B:  lda     #$00
        sta     passok
        rts

L5A70:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (ptr),y
        and     #$01
        php
        lda     #$80
        plp
        beq     L5A85
        rts

L5A85:  ldy     #$07
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

L5A9D:  pha
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
code_5AF0:
        jsr     L46E9
        jsr     L5331
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

L5B1B:  ldy     #$07
        lda     (ptr),y
        and     #$48
        cmp     #$40
        rts

; Affiche le message d'action $13E8 puis execute l'epilogue
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

        jsr     act_probe
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        jsr     L54C8
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
        jsr     L5331
        jsr     L5B9B
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
        jmp     L580F

L5B94:  ldy     #$10
        lda     (crec),y
        jmp     L4DC6

L5B9B:  ldy     #$04
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
; TODO pointeur $0000
msg_5BB8:
        .word   $0000
code_5BBA:
        rts

L5BBB:  jsr     L5349
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

        jsr     L5349
        bcc     L5BD4
        jsr     print_msg
; -> $11E8 <NAME>ALREADY CARRYING<ARG1>.
msg_5BD1:
        .word   $11E8
code_5BD3:
        rts

L5BD4:  jsr     L5C2B
        lda     obj
L5BD9:  jsr     L5331
        lda     arg1
        ldy     #$01
        cmp     (ptr),y
        bne     L5BE7
        jmp     L5A62

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

L5C07:  jsr     L46E9
        jsr     L5331
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

L5C2B:  lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        lda     arg1
        jsr     L55B3
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
        jsr     L55B3
        sec
        sbc     L5C77
        bcs     L5C80
        jsr     L5FBD
        bne     L5C72
        ldy     #$07
        lda     (ptr),y
        and     #$02
        bne     L5C72
        rts

L5C72:  pla
        pla
        jmp     L5A62

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

L5C88:  jsr     L46E9
        jsr     L5331
L5C8E:  ldy     #$01
        lda     (ptr),y
        cmp     #$FF
        beq     L5CA3
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        and     #$20
        bne     L5C8E
        lda     #$01
L5CA3:  php
        jsr     fetch_retaddr
        plp
        rts

; Objet $15 : teste ses drapeaux puis le prend ou le pose
act_p14_04:
        lda     arg1
        jsr     L5331
        jsr     L64D7
        bne     act_p14_14
        jmp     L5A9D

; Objet $C5 : teste ses drapeaux puis bascule son etat
act_p14_14:
        lda     obj
        jsr     L5C88
        beq     L5CBE
        rts

L5CBE:  jsr     L576D
        cmp     #$FF
        bne     L5CC8
L5CC5:  jmp     L5A62

L5CC8:  ldy     #$02
        lda     (ptr),y
        beq     L5CC5
        jsr     act_probe
        jsr     L46E9
        jsr     L530B
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
        jsr     L4DB7
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

; Objet : compare a un seuil (($8A)+2), le deplace et fixe $13/$15
act_p14_05:
        jsr     L576D
L5D09:  cmp     #$FF
        beq     L5CC5
        ldy     #$02
        lda     (ptr),y
        beq     L5CC5
        dey
        lda     (ptr),y
        jsr     L46E9
        jsr     L5E66
        jsr     fetch_retaddr
        bne     L5CC5
        jsr     act_probe
        ldy     #$00
        lda     (ptr),y
        sta     wid
        lda     #$FF
        sta     arg1
        jmp     L5D53

        lda     arg1
        ldx     #$16
        jsr     L534D
        bcc     L5D3D
        jmp     L5BD4

L5D3D:  jsr     print_msg
; -> $1391 <ARG1>IS NOT IN<ARG2>.
msg_5D40:
        .word   $1391
code_5D42:
        rts

L5D43:  .byte   $04
code_5D44:
        jsr     is_dark
        bcc     L5D53
        lda     #$09
        jsr     rand_range
        clc
        adc     #$01
        sta     wid
L5D53:  lda     crec
        sta     ptr2
        lda     crec_hi
        sta     ptr2_hi
        ldy     #$01
        lda     (ptr2),y
        cmp     #$FF
        beq     L5D74
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        and     #$40
        beq     L5D8A
        ldy     #$01
        lda     #$FF
        sta     (ptr2),y
L5D74:  lda     obj
        jsr     code_55AE
        ldy     #$02
        clc
        adc     (ptr2),y
        sta     L5D43
        lda     wid
        jsr     L57D5
        cmp     #$FF
        bne     L5DAF
L5D8A:  jsr     is_dark
        bcs     L5D92
        jmp     L5A62

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
        jmp     L5FAE

L5DAF:  ldy     #$02
        lda     (ptr),y
        beq     L5D8A
        sta     key
        ldy     #$01
        lda     (ptr),y
        jsr     L5E66
        tax
        dex
        beq     L5D8A
        dex
        beq     L5E3E
        dex
        bne     L5DCB
        jmp     L5E47

L5DCB:  jsr     act_probe
        ldy     #$10
        lda     key
        sta     (ptr2),y
        lda     obj
        ldx     key
        jsr     L5612
        lda     obj
        cmp     #$00
        beq     evt_lookup
        rts

; Trouve l'evenement associe a la cle $8F (table $709F), sinon $5DFD
evt_lookup:
        ldx     #$9F
        ldy     #$70
        lda     key
        jsr     L5399
        beq     L5DFD
        ldy     #$01
        lda     (ptr),y
        sta     L4C64
        iny
        lda     (ptr),y
        sta     L4C65
        jsr     L4C5D
L5DFD:  jsr     is_dark
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
        jsr     L5399
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

L5E3E:  jsr     L5E50
        jsr     print_msg
; -> $11FA <W>IS TOO SMALL FOR<OBJ>TO ENTER.
msg_5E44:
        .word   $11FA
code_5E46:
        rts

L5E47:  jsr     L5E50
        jsr     print_msg
; -> $1206 <W>IS TOO FULL FOR<OBJ>TO ENTER.
msg_5E4D:
        .word   $1206
code_5E4F:
        rts

L5E50:  ldy     #$02
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

L5E66:  and     #$FF
        beq     L5E8B
        jsr     L5331
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
        jsr     L530B
        lda     ptr
        sta     $CA
        lda     ptr_hi
        sta     $CB
        lda     #$FF
        ldy     #$01
        cmp     (ptr),y
        beq     L5EAB
        lda     key
        jsr     L568D
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

        jsr     L5BBB
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

        lda     arg1
        jsr     L5774
        jmp     L5D09

L5F07:  lda     #$0A
        jsr     rand_range
        cmp     #$00
        beq     L5F07
        tax
L5F11:  txa
        jsr     L57D5
        cmp     #$FF
        bne     L5F23
        inx
        cpx     #$0B
        bcc     L5F11
        ldx     #$01
        jmp     L5F11

L5F23:  sta     wid
        jmp     code_5D44

        ldy     #$10
        lda     (orec),y
        cmp     (crec),y
        beq     L5F3A
        jsr     L5774
        cmp     #$FF
        beq     L5F3A
        jmp     L5D09

L5F3A:  jsr     print_msg
; -> $13C9 I CANNOT FOLLOW<ARG1>FROM HERE.
msg_5F3D:
        .word   $13C9
code_5F3F:
        rts

        jsr     L5C2B
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
        jsr     L5793
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
        jmp     L4C6D

        jsr     act_probe
        lda     arg1
        jsr     L520D
        cmp     #$FF
        php
        lda     #$00
        plp
        beq     L5FA0
        lda     $D5
        bne     L5FA0
        ldy     #$06
        lda     (ptr2),y
        beq     L5FA0
        jsr     rand_range
        beq     L5FA4
L5FA0:  jsr     code_3E5B
        rts

L5FA4:  jsr     print_msg
; -> $15BE <ARG1>SAY 'NO '
msg_5FA7:
        .word   $15BE
code_5FA9:
        lda     #$00
        jmp     L5FA0

L5FAE:  lda     #$00
        sta     obj
        jsr     print_msg
; -> $13D1 <NAME>DEAD
msg_5FB5:
        .word   $13D1
code_5FB7:
        jsr     L3CD4
        jmp     code_3C8B

L5FBD:  lda     orec
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
        jsr     L64D7
        bne     L5FDD
        jmp     L5A9D

L5FDD:  lda     arg1
        jsr     L5576
        cmp     #$00
        beq     L5FF5
        jsr     act_probe
        jsr     code_5711
        ldy     #$07
        lda     (ptr),y
        and     #$FB
        sta     (ptr),y
        rts

L5FF5:  lda     #$02
        jmp     L5A9D

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
        jmp     L4C57

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
        jsr     L5612
        lda     $1B2A
        bne     L6040
        jmp     L5FAE

L6040:  rts

; Drapeaux de l'objet ($19) bits 0-2 : affiche 'swept away' ($11D3) ou 'X dead' ($13D1)
act_p14_13:
        jsr     L5BBB
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$04
        lda     (orec2),y
        and     #$07
        bne     L6057
        jmp     L5A62

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
        jsr     code_55AE
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
        jsr     L5331
        ldy     #$07
        lda     (ptr),y
        and     #$FD
        sta     (ptr),y
        lda     #$01
        bne     L60C4
; Combat : applique les degats, consomme le compteur puis affiche 'KILLED' ($1525)
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
        jmp     code_4D47

; Deplacement de l'objet (bits de $78), ecrit les pointeurs de rendu $75/$70/$5C/$5D
act_p14_01:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        ldy     #$07
        lda     (orec),y
        and     #$02
        beq     L6100
L60FD:  jmp     L5A62

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
        jsr     L46E9
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
        lda     #$0C
        jsr     L52EA
        jsr     fetch_retaddr
        cmp     #$FF
        beq     L60FD
        ldy     #$05
        lda     (orec2),y
        sta     L6320
L613E:  jsr     act_probe
        lda     #$15
        jsr     L56D9
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
        jsr     code_5AF0
        ldy     #$05
        lda     (orec),y
        lsr     a
        sta     (orec),y
        ldy     #$04
        lda     (orec),y
        cmp     #$02
        bcs     L6178
        jsr     code_5711
L6178:  lda     #$83
        jsr     L5A9D
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
        jsr     L56D9
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
        jsr     code_5AF0
        ldy     #$05
        lda     (orec2),y
        lsr     a
        sta     (orec2),y
        lda     arg2
        jsr     L5713
        lda     orec2
        sta     ptr
        lda     orec2_hi
        sta     ptr_hi
L61C4:  lda     #$83
        jmp     L5A9D

; Objet ($17) : remet a 0 le bit5 de ($8A)+7, sinon branche $5A9D
act_p14_02:
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jsr     L64D7
        bne     L61D9
        jmp     L5A9D

L61D9:  jsr     act_probe
L61DC:  ldy     #$07
        lda     (ptr),y
        and     #$DF
        sta     (ptr),y
        rts

; Objet $16 : lit le bit5 de ($88)+7 et branche a $5A90
act_p14_07:
        jsr     L5BBB
        lda     arg2
        jsr     L576F
        cmp     #$FF
        bne     L61F4
        jmp     L5A62

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
        jmp     L5612

; Pose le bit5 de ($8A)+7 ; si id==1, declenche la fete ($580F : foule en liesse... coucher de soleil)
act_p14_03:
        jsr     L5A70
        beq     L622A
        jmp     L5A9D

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
        jsr     L58E7
        bcc     L6246
        rts

L6246:  ldy     #$10
        lda     (ptr),y
        tax
        lda     arg1
        jmp     L580F

L6250:  ldy     #$04
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

        jsr     L6250
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
        jsr     L6341
        sta     L6320
        jsr     act_probe
        ldy     #$06
        lda     (orec),y
        jsr     L6341
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
; TODO pointeur $0000
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
        jsr     code_4D47
        lda     #$06
        jmp     L5A9D

L6341:  sta     L635A
        lda     #$0A
        jsr     L56D9
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
        .byte   $12,$20,$86,$53,$20,$0D,$44,$CD
        .byte   $11,$A5,$C5,$20,$76,$55,$C9,$00
        .byte   $D0,$06,$20,$0D,$44,$1B,$17,$60
        .byte   $A5,$C6,$85,$8A,$A5,$C7,$85,$8B
        .byte   $A0,$10,$B1,$8A,$AA,$A5,$C5,$4C
        .byte   $0F,$58
code_63A4:
        jsr     act_probe
        lda     arg1
        jsr     L5331
        ldy     #$0E
        lda     (ptr),y
        sta     msg_63C1
        iny
        lda     (ptr),y
        sta     msg_63C1+1
        ora     msg_63C1
        beq     L63C4
        jsr     print_msg
; TODO pointeur $0000
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
        jsr     L5521
        lda     #$2E
        jsr     putchar
        jmp     print_cr

L63DC:  lda     orec2
        sta     ptr2
        lda     orec2_hi
        sta     ptr2_hi
        jsr     L5349
        bcs     L63EF
        jsr     print_msg
; -> $11C8 <NAME>NOT CARRYING IT.
msg_63EC:
        .word   $11C8
code_63EE:
        rts

L63EF:  lda     arg2
        jsr     L55B3
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
        jmp     L5612

L641D:  jsr     L5A70
        beq     L6425
        jmp     L5A9D

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
L645C:  jmp     L5A9D

L645F:  jsr     L5A85
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
        sta     $C3
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
        jsr     L6EF7
        bne     L64CD
        rts

L64CD:  lda     #$00
        sta     (ptr2),y
        iny
        lda     #$10
        sta     (ptr2),y
        rts

L64D7:  ldy     #$07
        lda     (ptr),y
        and     #$20
        php
        lda     #$05
        plp
        rts

        lda     arg1
        cmp     #$13
        beq     L64E9
        rts

L64E9:  jsr     L4D95
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
; Arme l'evenement e3 (cpt := id) apres avoir appele $6222 et $4D95
evt_arme3:
        jsr     act_p14_03
        jsr     L4D95
        lda     $2B21
        sta     $2B22
        rts

        .byte   $A9,$02,$D0,$06
; Repartit l'objet $16 (cas $0F) vers $65DD/$641D/$6448
act_p14_12:
        lda     #$0F
        bne     L65BC
; Repartit l'objet $16 (cas $04) vers $65DD/$4C57
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
        jmp     L4C57

; Affiche 'X do not fit this lock' ($140C), sinon 'i cannot do that' ($139B)
act_p14_06:
        jsr     print_msg
; -> $140C <ARG2>DO NOT FIT THIS LOCK
msg_65E0:
        .word   $140C
code_65E2:
        rts

        jsr     L4D95
        lda     orec
        sta     ptr
        lda     orec_hi
        sta     ptr_hi
        jmp     L622D

; Si ((crec)+16)==$0F saute a $6222, sinon a $5A62
act_p14_10:
        lda     crec
        sta     ptr
        lda     crec_hi
        sta     ptr_hi
        ldy     #$10
        lda     (ptr),y
        cmp     #$0F
        beq     L6604
        jmp     L5A62

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

        jsr     L576D
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
        jsr     L5D53
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
        jmp     code_4D47

L667C:  lda     $1CCB
        and     #$80
        beq     evt_disarme6
        jsr     print_msg
; -> $1454 <NAME>NOT WEARING<ARG1>.
msg_6686:
        .word   $1454
code_6688:
        rts

; Desarme l'evenement e6 (cpt := 0) et pose son bit de drapeau
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

; Arme l'evenement e6 : cpt := 2 + aleatoire(8) (delai aleatoire)
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

; Affiche 'spiders mend the web' ($1478) et arme l'evenement e1
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

        .byte   $A0,$01,$B1,$C6,$C5,$15,$D0,$03
        .byte   $4C,$62,$5A,$A5,$17,$85,$88,$A5
        .byte   $18,$85,$89,$A5,$15,$20,$39,$54
        .byte   $F0,$EE,$A5,$15,$20,$31,$53,$A0
        .byte   $01,$B1,$8A,$C9,$FF,$F0,$08,$C5
        .byte   $C5,$D0,$F1,$A9,$FF,$91,$17,$A5
        .byte   $C5,$20,$AE,$55,$A0,$02,$18,$71
        .byte   $C6,$90,$02,$A9,$FF,$8D,$5F,$67
        .byte   $A5,$17,$85,$8A,$A5,$18,$85,$8B
        .byte   $20,$D7,$64,$D0,$03,$4C,$9D,$5A
        .byte   $A0,$02,$B1,$8A,$C9,$FF,$F0,$0C
        .byte   $38,$ED,$5F,$67,$B0,$06,$20,$0D
        .byte   $44,$1D,$15,$60,$20,$86,$53,$A5
        .byte   $15,$A0,$01,$91,$C6,$60,$00,$A0
        .byte   $04,$B1,$17,$29,$70,$31,$C6,$F0
        .byte   $03,$4C,$62,$5A,$A0,$07,$B1,$17
        .byte   $29,$40,$F0,$F5,$A5,$C5,$A2,$1F
        .byte   $C9,$40,$F0,$06,$C9,$42,$F0,$02
        .byte   $A2,$0D,$E4,$C9,$F0,$E3,$8E,$C9
        .byte   $67,$20,$86,$53,$A0,$10,$AD,$C9
        .byte   $67,$91,$17,$A0,$01,$A9,$FF,$91
        .byte   $17,$A5,$15,$AE,$C9,$67,$20,$12
        .byte   $56,$A5,$15,$C9,$00,$F0,$01,$60
        .byte   $85,$C5,$A9,$1A,$85,$C6,$A9,$1B
        .byte   $85,$C7,$20,$82,$4C,$90,$01,$60
        .byte   $A9,$DC,$8D,$FC,$4D,$A9,$13,$8D
        .byte   $FD,$4D,$AD,$C9,$67,$4C,$E9,$4D
        .byte   $85,$A0,$01,$B1,$17,$C9,$12,$F0
        .byte   $06,$20,$0D,$44,$73,$14,$60,$20
        .byte   $86,$53,$AD,$08,$1D,$A0,$01,$91
        .byte   $17,$60,$A5,$15,$C9,$12,$F0,$6E
        .byte   $A5,$16,$C9,$12,$F0,$0B,$A5,$15
        .byte   $A6,$16,$85,$16,$86,$15,$4C,$62
        .byte   $5A,$20,$BD,$5F,$D0,$F0,$A0,$07
        .byte   $B1,$17,$29,$02,$D0,$E8,$A5,$16
        .byte   $20,$76,$55,$C9,$00,$F0,$06,$20
        .byte   $0D,$44,$60,$14,$60,$A0,$07,$B1
        .byte   $17,$29,$08,$D0,$0D,$B1,$17,$29
        .byte   $40,$D0,$CB,$A5,$16,$20,$4B,$53
        .byte   $90,$C4,$20,$86,$53,$20,$49,$53
        .byte   $A5,$16,$A0,$01,$91,$17,$B0,$13
        .byte   $A9,$00,$85,$0C,$20,$C9,$5B,$A5
        .byte   $12,$08,$A9,$01,$85,$0C,$85,$12
        .byte   $28,$F0,$07,$A5,$C5,$A0,$01,$91
        .byte   $19,$60,$A9,$FF,$D0,$F7,$A2,$E3
        .byte   $A0,$67,$4C,$93,$57,$A5,$C5,$C9
        .byte   $3C,$F0,$03,$4C,$62,$5A,$20,$86
        .byte   $53,$4C,$45,$4D,$A0,$01,$A5,$15
        .byte   $D1,$C6,$F0,$03,$4C,$62,$5A,$20
        .byte   $31,$53,$20,$D7,$64,$D0,$03,$4C
        .byte   $9D,$5A,$20,$86,$53,$A0,$01,$A9
        .byte   $FF,$91,$C6,$60,$A9,$00,$8D,$58
        .byte   $4E,$AD,$1B,$1B,$C9,$13,$D0,$05
        .byte   $20,$0D,$44,$0C,$17,$A9,$22,$8D
        .byte   $94,$1D,$AA,$A9,$13,$20,$12,$56
        .byte   $A9,$20,$8D,$94,$1D,$AD,$8B,$1D
        .byte   $29,$DF,$09,$04,$8D,$8B,$1D,$A9
        .byte   $00,$85,$0B,$A9,$13,$20,$13,$57
        .byte   $A9,$01,$85,$0B,$A9,$20,$8D,$B8
        .byte   $1D,$A9,$13,$8D,$A9,$1D,$60
; Si au meme lieu que le joueur : affiche 'hello' ($143F)
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

; PNJ oisif : 'great job' ($1432) / 'hurry up' ($143B) / 'hello' ($143F)
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

; Affiche 'thrains key' ($1441)
act_v14_02:
        jsr     act_probe
        jsr     act_msg
; -> $1441 THIS WAS THRAINS KEY
msg_6912:
        .word   $1441
code_6914:
        rts

; Sonde et tirage : ~20% de chance d'afficher 'expect me' ($1485)
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

; Affiche 'WHAT'S this ?' ($1427)
act_v14_00:
        jsr     act_probe
        jsr     act_msg
; -> $1427 WHAT'S THIS ?
msg_6933:
        .word   $1427
code_6935:
        rts

; Tirage 0-7 : appelle $4D9E, decremente ($14) et affiche $143B
act_v14_04:
        jsr     act_probe
        lda     #$08
        jsr     rand_range
        cmp     #$05
        bcc     L6943
        rts

L6943:  cmp     #$03
        bcc     L694D
        jsr     L4D9E
        dec     $14,x
        rts

L694D:  cmp     #$03
        bne     L6952
        rts

L6952:  cmp     #$00
        bne     code_695C
        jsr     L4D9E
        .byte   $C7,$14,$60
code_695C:
        jsr     act_msg
; -> $143B HURRY UP
msg_695F:
        .word   $143B
code_6961:
        rts

; Si au meme lieu et que le bit7 de $1B21 est clair : affiche 'WHERE'S the thief ?' ($14AB)
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

; Si $C8==$1DE0 : appelle $4D9E et ajuste ($14)
act_v14_05:
        jsr     act_probe
        lda     ploc
        cmp     $1DE0
        beq     L6985
        rts

L6985:  jsr     L4D9E
        ror     $14
        rts

        lda     #$19
        jsr     L534B
        bcs     L6998
        jsr     print_msg
; -> $1503 <NAME>NOT CARRYING THE BOW
msg_6995:
        .word   $1503
code_6997:
        rts

L6998:  jsr     L6250
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
        jsr     L5B1B
        beq     L69DD
        jmp     act_p14_01

L69DD:  lda     arg1
        jsr     code_4D47
        lda     #$06
        jmp     L5A9D

L69E7:  lda     $1F38
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

        jsr     L4D95
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

; Si $C5 vaut 0 : pose $C4:=1 et desarme l'evenement e7
evt_disarme7:
        lda     #$01
        sta     $C4
        lda     $2B35
        sta     $2B36
        rts

        ldy     #$10
        lda     (orec),y
        sta     L6A5C
        jsr     L5774
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
        jsr     L5612
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
        jmp     L5612

        lda     arg2
        jsr     L576F
        cmp     #$FF
        bne     L6A92
        jmp     L5A62

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
        jsr     L6AE3
        bcs     L6AB9
        jsr     L6AE3
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

L6AC4:  jsr     L6AE3
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
        jsr     L5612
        jsr     print_msg
; -> $134D LAND ON THE OTHER SIDE.
msg_6AE0:
        .word   $134D
code_6AE2:
        rts

L6AE3:  lda     #$64
        jsr     rand_range
        cmp     #$32
        rts

; Arme l'evenement e9 (cpt := 6), pose les drapeaux $1C7B, saute a $6D72
evt_arme9b:
        jsr     L4D95
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
        jmp     L5A62

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
        jmp     L5A62

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

; Arme l'evenement e5 (cpt := id) et affiche 'magic door' ($168B)
evt_arme5:
        lda     $2B2B
        sta     $2B2C
        jsr     print_msg
; -> $168B THE MAGIC DOOR WARN OF ELVES APPROACH.
msg_6B6F:
        .word   $168B
code_6B71:
        rts

; Si $C5==$41 : parcourt la table ($C1) et affiche 'go...from...to' ($13E0/$15AB)
act_p14_09:
        lda     obj
        cmp     #$41
        beq     L6B7B
        jmp     code_63A4

L6B7B:  jsr     act_probe
        ldy     #$01
        lda     ($C1),y
        sta     ptr2
        iny
        lda     ($C1),y
        sta     ptr2_hi
        iny
        lda     $C3
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
        jsr     L43E4
        lda     ptr
        sta     L4673
        lda     ptr_hi
        sta     L4674
        ldy     #$00
        lda     ($C1),y
        jsr     L43E4
        lda     ptr
        sta     L4671
        lda     ptr_hi
        sta     L4672
        ldy     #$03
        lda     ($C1),y
        jsr     L59E7
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

L6BE3:  jsr     L4D95
        lda     $1B9D
        ora     #$08
        sta     $1B9D
        lda     #$02
        jsr     code_5AF0
        lda     #$1A
        sta     ptr2
        lda     #$1B
        sta     ptr2_hi
        lda     #$02
        jsr     L54A9
        bne     L6C03
        rts

L6C03:  jsr     print_msg
; -> $14EB THE SMALL CURIOUS KEY SHATTER.
msg_6C06:
        .word   $14EB
code_6C08:
        rts

; Gollum : si $1E4B==$C8 et drapeau pause, affiche un message (patche)
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
; TODO pointeur $0000
msg_6C2C:
        .word   $0000
code_6C2E:
        lda     #$01
        sta     $D5
        rts

; One-shot (verrou $CE==1) : remet $CE a zero et copie $14/$15 vers $2A7B
act_v14_11:
        lda     once
        cmp     #$01
        beq     L6C3A
        rts

L6C3A:  lda     #$00
        sta     once
        lda     #$01
        jsr     code_3F7F
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

; Action de l'evenement e4 : si au marais ($C8==$1D) affiche $1535, sinon desarme e4
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

L6C76:  jmp     L5FAE

        lda     $1D26
        and     #$DF
        sta     $1D26
        jsr     L6DEF
        beq     L6C87
        rts

L6C87:  jsr     print_msg
; -> $141C THE MAGIC DOOR CLOSE.
msg_6C8A:
        .word   $141C
code_6C8C:
        rts

; Si $C8 vaut 27, 2C ou 29 : affiche 'X enter' ($13F6)
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

; Dragon au meme lieu : 'PREPARE TO DIE' ($153F) ou 'aveugle' ($155D)
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

; Si au meme lieu : simule un combat (wid=$1B/arg1=0) puis saute a $5FAE
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
        jsr     L5A62
        jsr     act_p14_00
        jmp     L5FAE

; Si au meme lieu : prend l'objet $1FC1 (id 41)
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
        jsr     L5A62
        jmp     L63DC

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
        jmp     L5FAE

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

; Affiche le trou qui disparait ($1685)
evt_print:
        jsr     print_msg
; -> $1685 THE HOLE VANISH.
msg_6D75:
        .word   $1685
code_6D77:
        rts

; Gollum et l'Anneau : si $C8==$1E4B, tirage entre 'pocket?' ($16B9) et 'my precious' ($16C8)
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

        .byte   $AD,$7B,$1C
code_6DBE:
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
        jsr     L6DEF
        bne     code_6DE2
        jsr     print_msg
; -> $1415 THE MAGIC DOOR OPEN.
msg_6DE0:
        .word   $1415
code_6DE2:
        jsr     L6DEF
        bne     code_6DEC
        jsr     print_msg
; -> $14F5 AN ELF SWEEPS PAST
msg_6DEA:
        .word   $14F5
code_6DEC:
        jmp     L6E35

L6DEF:  lda     ploc
        cmp     #$1E
        bne     L6DF6
        rts

L6DF6:  cmp     #$1C
        rts

; Cherche un lieu, remet $D5 a zero et affiche 'strangle you' ($15B6)
act_v14_13:
        jsr     act_probe
        lda     #$00
        sta     $D5
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
L6E15:  jsr     L3485
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
        jmp     L5FAE

L6E35:  lda     $1CC5
        cmp     #$FF
        bne     L6E3D
        rts

L6E3D:  jsr     L5331
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
        sta     $C4
        rts

; Smaug : si $1F47!=$29, tirage 0-100 entre 'dragon flying' ($1582) et 'burn you' ($1596)
act_v14_08:
        lda     $1F47
        cmp     #$29
        bne     L6E61
        rts

L6E61:  jsr     act_probe
        lda     #$01
        sta     outen
        jsr     L5374
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
        jmp     L5FAE

; Trolls au lieu 5 : si $C5==$47 affiche 'BLIMEY, COOK EM' ($1615), sinon 'MOUTHFUL' ($162B)
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

; Efface des drapeaux ($1F94/$1FA6), met a jour une description de lieu et affiche $16EB
act_v14_17:
        jsr     act_probe
        lda     #$47
        jsr     code_4D47
        lda     #$48
        jsr     code_4D47
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
        jsr     L5713
        lda     #$48
        jsr     L5713
        lda     #$01
        sta     outen
        jsr     print_msg
; -> $16EB DAY DAWN.
msg_6EE7:
        .word   $16EB
code_6EE9:
        jsr     L6EF7
        bne     L6EEF
        rts

L6EEF:  lda     #$03
        sta     (ptr2),y
        iny
        sta     (ptr2),y
        rts

L6EF7:  lda     ptr_block3
        ora     L2C04
        bne     L6F00
        rts

L6F00:  ldx     ptr_block3
        ldy     L2C04
        lda     #$05
        jsr     L5399
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
        jmp     L5FAE

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
        jmp     L5A62

L6F61:  lda     (ptr),y
        and     #$04
        php
        lda     #$82
        plp
        beq     L6F6E
        jmp     L5A9D

L6F6E:  ldx     #$41
        ldy     #$60
        jmp     L5793

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
        .byte   "\"
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
        .byte   "\ff)f"
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
; Cle $16 : si le drapeau $1DC5 vaut 8, place une entite ($2B61:=$42) et arme
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

; Arme l'evenement e2 (cpt := id) ; cle $1A
evt_arme2:
        lda     $2B1C
        sta     $2B1D
        rts

; Arme l'evenement e4 (cpt := id) ; cle $1D
evt_arme4:
        lda     $2B26
        sta     $2B27
        rts

; Arme l'evenement e9 (cpt := 3) et ecrit les entites $2B76/$2B7D ; cle $20
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

; Cle $02/$03 : copie $8F dans $BE et arme l'evenement e8
evt_arme8:
        lda     key
        sta     exploc
        lda     $2B3A
        sta     $2B3B
        rts

; Cle $21 : si $1B1B vaut $13, declenche $5DFD et affiche
evt_gate21:
        lda     $1B1B
        cmp     #$13
        bne     L710B
        rts

L710B:  jsr     L5DFD
        jsr     print_msg
; -> $1650 <NAME>SWEPT FORCEFULLY AGAINST THE PORTCULLIS
msg_7111:
        .word   $1650
code_7113:
L7114           := * + 1
L7115           := * + 2
        jmp     L5FAE

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
code_71A8:
        lda     $0A
        bne     L71C8
        jsr     L770A
        lda     #$0D
        jsr     L76F9
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

L71CB:  lda     $024D
        sta     $6C
        lda     #$01
        sta     $024D
        jsr     code_72FC
        jmp     L71E8

; Charge un bloc cassette via le loader ROM $0417 et verifie l'en-tete
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
L71FF:  clc
        rts

L7201:  jmp     print_cr

L7204:  lda     #$00
        sta     $030B
        rts

L720A:  jsr     L46E6
        lda     #$2E
        jsr     ch_out
        jmp     L471B

; Ecrit un bloc cassette : leader, en-tete (9 o), donnees, checksum EOR
tape_save:
        jsr     L720A
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

L7293:  jsr     print_msg
; -> $72AA PREPARE TAPE FOR GAME SAVE
msg_7296:
        .word   $72AA
code_7298:
        jmp     tape_prompt

L729B:  jsr     print_msg
; -> $72C5 REWIND TAPE FOR VERIFICATION
msg_729E:
        .word   $72C5
; Affiche les invites 'PREPARE TAPE' / 'REWIND' / 'PRESS ANY KEY'
tape_prompt:
        jsr     print_msg
; -> $72E3 PRESS ANY KEY WHEN READY
msg_72A3:
        .word   $72E3
code_72A5:
        jsr     kb_wait
        clc
        rts

        .byte   "PREPARE TAPE FOR GAME SAVE"



        .byte   $14,$0D
        .byte   "REWIND TAPE FOR VERIFICATION"



        .byte   $14
        .byte   "PRESS ANY KEY WHEN READY"


        .byte   $14
code_72FC:
        jsr     L720A
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

; Scanne le clavier ; A = touche si le bit7 est pose, sinon bit7=0 (pas de touche)
; Lit l'etat du clavier : renvoie la touche appuyee, ou indique qu'aucune touche n'est
; enfoncee.
; Technique : scan de la matrice via le VIA ($0300) ; A = code touche, bit7 pose si presente.
kb_scan:stx     $1E
        sty     $1F
        lda     #$FF
        sta     $0303
        lda     #$F7
        sta     $0302
        lda     #$CC
        sta     $030C
        lda     #$07
        jsr     L7464
        lda     #$FF
        jsr     L7472
        lda     #$0E
        jsr     L7464
        ldx     #$07
L7377:  ldy     #$FE
L7379:  jsr     code_7454
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
        jsr     code_7454
        bne     L73B3
        ldx     #$07
        jsr     code_7454
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
        .byte   "XQ2\"
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
code_7454:
        txa
        ora     #$B0
        sta     $0300
        tya
        jsr     L7472
        lda     $0300
        and     #$08
        rts

L7464:  sta     $0301
        lda     #$EE
        sta     $030C
        lda     #$CC
        sta     $030C
        rts

L7472:  sta     $0301
        lda     #$EC
        sta     $030C
        lda     #$CC
        sta     $030C
        rts

        .byte   "`"
; Attend une touche (bloquant) et renvoie son code sans le bit7
; Attend que le joueur appuie sur une touche, puis renvoie son code.
; Technique : boucle sur kb_scan jusqu'a bit7 pose, retour & $7F.
kb_wait:jsr     kb_scan
        bpl     kb_wait
        and     #$7F
        rts

; Affiche un retour a la ligne ($0D)
; Affiche un retour a la ligne.
; Technique : $0D via ch_out.
cr_out: pha
        lda     #$0D
        jsr     ch_out
        pla
        rts

; Point d'entree d'affichage : filtre certains codes et passe au rendu ecran
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
        lda     $C4
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
        jsr     glyph_out
        jmp     L74E7

L74D1:  cmp     #$08
        beq     L74FD
        cmp     #$61
        bcc     L74DF
        cmp     #$7B
        bcs     L74DF
        and     #$5F
L74DF:  jsr     glyph_out
        jsr     L75A6
        bne     L74F2
L74E7:  jsr     L7514
        lda     #$00
        sta     L0000
        lda     #$28
        sta     col
L74F2:  lda     #$2B
        jsr     glyph_out
        pla
        tax
        pla
        tay
        pla
        rts

L74FD:  lda     #$20
        jsr     glyph_out
        jsr     L75AB
        bne     L74F2
        lda     #$28
        sta     L0000
        jsr     L7558
        lda     #$01
        sta     col
        bne     L74F2
L7514:  pha
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
        jsr     L754B
        lda     $20
        cmp     #$40
        lda     $21
        sbc     #$BF
        bcc     L7527
L7538:  lda     #$40
        sta     ($1E),y
        jsr     L7551
        lda     $1E
        cmp     #$40
        lda     $1F
        sbc     #$BF
        bcc     L7538
        pla
        rts

L754B:  inc     $20
        bne     L7551
        inc     $21
L7551:  inc     $1E
        bne     L7557
        inc     $1F
L7557:  rts

L7558:  pha
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
        jsr     L758F
        lda     $1E
        cmp     #$00
        lda     $1F
        sbc     #$B9
        bcs     L756B
L757C:  lda     #$40
        sta     ($20),y
        jsr     L759A
        lda     $20
        cmp     #$00
        lda     $21
        sbc     #$B9
        bcs     L757C
        pla
        rts

L758F:  lda     $1E
        sec
        sbc     #$01
        sta     $1E
        bcs     L759A
        dec     $1F
L759A:  lda     $20
        sec
        sbc     #$01
        sta     $20
        bcs     L75A5
        dec     $21
L75A5:  rts

L75A6:  inc     L0000
        dec     col
        rts

L75AB:  dec     L0000
        inc     col
        lda     col
        cmp     #$29
        rts

; Dessine un caractere en mode hires ($A000) avec la police ROM
; Dessine un caractere a l'ecran graphique (hires) en recopiant son motif depuis la police
; du jeu, puis fait avancer le curseur.
; Technique : police pointee par $0403/$0404 ; 8 octets en OR $40 (encre) ; ligne += $28.
glyph_out:
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

; Affiche un caractere : gere retour a la ligne, scroll et pause de bas d'ecran
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
        jsr     L76ED
        jsr     L76DF
        dec     $03
        bne     L7607
L7613:  lda     $02
        cmp     #$0D
        bne     L7653
; Toutes les 16 lignes, attend une touche (avec delai) pour pause, sinon incremente le compteur
; Pause de lecture : tous les 16 sauts de ligne, le jeu attend une touche (ou un court
; delai), puis fait defiler l'ecran et remet le compteur de lignes a zero.
; Technique : 10 essais kb_scan avec delai, compteur crcnt mod 16, scroll L7694.
pause_key:
        lda     #$00
        sta     sppend
        jsr     L771A
        lda     crcnt
        cmp     #$0F
        bne     L763B
        ldx     #$0A
L7628:  jsr     kb_scan
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

L7640:  jsr     kb_scan
        bpl     L7640
L7645:  jsr     L7694
        lda     #$80
        sta     $08
        lda     #$28
        sta     $05
        jmp     L768E

L7653:  cmp     #$08
        bne     L7662
        jsr     L76E4
        lda     #$20
        jsr     L76ED
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
L7684:  jsr     L76ED
        sta     sppend
        jsr     L76DF
        beq     pause_key
L768E:  pla
        tay
        pla
        tax
        pla
        rts

L7694:  pha
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
        jsr     L7551
        lda     $1E
        cmp     #$C0
        lda     $1F
        sbc     #$B7
        bcc     L76CC
        pla
        rts

L76DF:  inc     $08
        dec     $05
        rts

L76E4:  dec     $08
        inc     $05
        lda     $05
        cmp     #$28
        rts

L76ED:  ldy     $05
        sta     $02D7,y
        ldx     $08
        ldy     $09
        jmp     L75B8

L76F9:  sta     $0301
        lda     #$A7
        sta     $0300
        nop
        nop
        nop
        lda     #$B7
        sta     $0300
        rts

L770A:  lda     #$FF
        sta     $0303
        lda     #$F7
        sta     $0302
        lda     #$CD
        sta     $030C
        rts

L771A:  pha
        lda     $0A
        beq     L7745
        jsr     L770A
        ldy     $05
        lda     #$0D
        sta     $02D7,y
        lda     #$0A
        sta     $02D6,y
        ldy     #$2A
L7730:  lda     $02D5,y
        jsr     L76F9
L7736:  lda     $030D
        and     #$02
        beq     L7736
        lda     $02D5,y
        dey
        cmp     #$0A
        bne     L7730
L7745:  pla
        rts

; Efface l'ecran hires $A000-$BFDF (remplit de $40)
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

; Boucle principale du jeu (atteinte via le vecteur vec_15)
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
; Dessine une illustration : prepare l'ecran ($7990) puis interprete le flux de trace
vec_image:
        stx     $28
        sty     $29
        pha
        ldy     #$00
        lda     ($28),y
        jsr     vec_setup
        jsr     L781D
L77E3:  ldy     #$00
        lda     ($28),y
        beq     L781B
        cmp     #$08
        beq     L7803
        and     #$80
        bne     L7809
        lda     ($28),y
        and     #$40
        bne     L780F
        lda     ($28),y
        and     #$20
        bne     L7815
L77FD:  jsr     L781D
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

L781D:  inc     $28
        bne     L7823
        inc     $29
L7823:  rts

; Remplissage : balaye la zone avec la couleur $40 sur les compteurs $32-$36
vec_fill:
        tsx
        stx     $32
        lda     $30
        sta     $33
        lda     $31
        sta     $34
        jsr     L781D
        ldy     #$00
        lda     ($28),y
        sta     $30
        jsr     L781D
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

; Instruction $08 : place le curseur en $30/$31 (2 octets)
vec_pos:jsr     L781D
        ldy     #$00
        lda     ($28),y
        sta     $30
        jsr     L781D
        lda     ($28),y
        sta     $31
        rts

; Instruction $20 : saute jusqu'a l'octet $FF
vec_skip:
        jsr     L781D
        lda     ($28),y
        cmp     #$FF
        bne     vec_skip
        rts

; Instruction de trace : segment (bit7, 2 o : drapeaux+longueur, pas), dessine pixel par pixel
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
        jsr     L781D
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

; Efface l'ecran hires $A000-$B3FF et applique les aplats selon l'octet de mode
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

; Teste la validite du pixel ($30/$31) : renvoie $FF hors des bornes $0E-$F2
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

; Allume le pixel ($30/$31) via la ligne ($38/$39) et le masque L7A5F
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

; Calcule l'adresse et le masque du pixel ($30/$31) dans l'ecran hires
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
