; ============================================================
; The Hobbit (Oric, 1982)
; Original authors : Veronika Megler & Philip Mitchell (Beam Software)
; 6502 port : Gregg Barnett (Beam Software)
; Publisher : Melbourne House
; - bloc 1 ($0400-$04FF)
; Listing généré par scripts/disasm.py (descente récursive + da65)
; Charge par autorun à $0400 -> JMP $047C (b1_start).
; Vecteurs ROM $0405-$0416 (patchés 1.0/1.1) + b1_load $0417.
; ============================================================

; da65 V2.19 - Git 71746c829


        .setcpu "6502"

L0032           := $0032
PUTBYTE_10      := $E5C6
READBYTE_10     := $E630
TAPESYNC_10     := $E696
WRITELEADER_10  := $E6BA
SETUPTAPE_10    := $E6CA
CHAR2SCR_10     := $F73C
RESETSTAT_10    := $F960
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
L04CC:  .byte   "Please wait while THE HOBBIT loads"
L04EE:  .byte   $0C
        .byte   "TAPE ERROR"
        .byte   $4C,$AA,$F9,$78,$A9,$7F,$8D
