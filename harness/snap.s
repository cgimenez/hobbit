; Shims SAVE/LOAD par snapshots pour The Hobbit sous sim65 ($F700).
;
; Patche par scripts/sim_pack.py --snapshot NOM (remplace tape.s) :
;   vec_02 ($2C0B, JMP tape_load $71DB) -> JMP snap_load
;   vec_03 ($2C0E, JMP tape_save $7215) -> JMP snap_save
;   vec_04 ($2C11, JMP L71CB)           -> JMP s_clc
;   + 6 vecteurs bloc 1 $0405-$0414 -> stubs no-op (table $F700).
; vec_05/vec_06 (prompts PREPARE/PRESS ANY KEY + kb_wait) conserves :
; SAVE/LOAD coutent chacun 1 touche sacrificielle, transcript authentique.
;
; Protocole SANS ETAT (index deduit de l'adresse, pas de compteur) :
;   - snap_save (appele 4x/SAVE, src=(ptr)=$8A/$8B) : emet
;     "@@SNAP\n" + NLEN(1) + NOM + IDX(1) + LEN(2) + octets bruts.
;     src inconnu -> succes silencieux (pas de capture, jeu continue).
;   - snap_load (appele 4x/LOAD, dst=(ptr)) : copie blob $E804+off
;     vers (dst). Magique absent ou dst inconnu -> C=1 (erreur propre :
;     le jeu dit TAPE LOADING ERROR + reboot, comme cassette vide).
;   - s_clc : verify toujours OK (C=0, A/X/Y intacts).
;
; Blob $E800 (sim_pack --snapshot) : "SNAP" + 3623 o (ordres idx :
; ZP/etats/scripts/records). $E800-$F62B : pas de code (snap.s est en
; $F700, comme tape.s ; zone "ROM" : RAM sous sim65).
; ZP jeu touche : $02 transitoire (pattern paravirt) ; pointeurs de
; copie en auto-modification absolue (LD_OP/ST_OP), compteurs en $F700+
; (RAM). A/X/Y preserves partout ; C = statut (seul teste par les
; appelants save_block/L3D6A).
;
; Table d'entrees en $F700 (lue par sim_pack.py) : 9 mots
; [s_0405, s_0408, s_040B, s_040E, s_noop, s_noop,
;  snap_save, snap_load, s_clc] ; nom bake a +18/+19.

        .setcpu "6502"
        .segment "CODE"

PV_WRITE = $FFF7
SPADDR   = $02                  ; mot ZP = pile logicielle paravirt
PVTOP    = $C2FF                ; params paravirt en $C2FB-$C2FE

SNAP_BLOB = $E800               ; "SNAP" + 3623 o (sim_pack --snapshot)
SNAP_DATA = $E804

        .org $F700
        .word s_0405, s_0408, s_040B, s_040E, s_noop, s_noop
        .word snap_save, snap_load, s_clc
SNAP_NAMELEN:
        .byte 0                 ; rempli par sim_pack (offset 18)
SNAP_NAME:
        .res 16, 0              ; nom du snapshot (offset 19, NUL-padded)

; ---- table regions : (src_lo, src_hi, idx, off_lo, off_hi, len_lo, len_hi)
; idx 0 = ZP $00BE/$18, 1 = etats $1B1A/$556, 2 = scripts $28CC/$2F1,
; idx 3 = records $211A/$5C8. off = position dans le blob ($E804+off).
REGTAB:
        .byte <$00BE, >$00BE, 0, <0,    >0,    <$0018, >$0018
        .byte <$1B1A, >$1B1A, 1, <24,   >24,   <$0556, >$0556
        .byte <$28CC, >$28CC, 2, <1390, >1390, <$02F1, >$02F1
        .byte <$211A, >$211A, 3, <2143, >2143, <$05C8, >$05C8
S_TRAIL:.res 3                  ; IDX/LENLO/LENHI a emettre (snap_save)
S_CNT:  .word 0                 ; compteur de copie (snap_load)
S_TMP:  .byte 0                 ; sauve index table (snap_save)

; ---- PVWrite(Buf=P_W(*), Count=A/X) vers stdout (autonome) ----
P_W:    .word 0
P_CNT:  .word 0
pv_write:
        sta P_CNT
        stx P_CNT+1
        lda #<(PVTOP-4)         ; SP = PVTOP-4, Y = 0
        sta SPADDR
        lda #>(PVTOP-4)
        sta SPADDR+1
        ldy #0
        lda P_W                 ; Buf (16 bits via Y)
        sta (SPADDR),y
        iny
        lda P_W+1
        sta (SPADDR),y
        iny
        lda #1
        sta (SPADDR),y          ; FD = 1 (stdout)
        iny
        lda #0
        sta (SPADDR),y
        lda P_CNT
        ldx P_CNT+1
        jsr PV_WRITE
        rts

; ---- $0405/$040B/$0411/$0414 : succes no-op ----
s_0405:
s_040B:
s_noop:
        rts

; ---- $0408 : lecture octet -> EOF immediat (ne doit jamais servir) ----
s_0408:
        sec
        lda #0
        rts

; ---- $040E : ecriture octet ignoree (ne doit jamais servir ; A garde) ----
s_040E:
        rts

; ---- verify : toujours OK ----
s_clc:
        clc
        rts

; ---- snap_save : capture un bloc (src=(ptr), 4 appels/SAVE) ----
MARK_S: .byte "@@SNAP", $0A
snap_save:
        pha
        txa
        pha
        tya
        pha
        ldx #0                  ; cherche src dans REGTAB (7 o/entree)
@find:  lda REGTAB,x
        cmp $8A                 ; ptr = src_lo
        bne @next
        lda REGTAB+1,x
        cmp $8B                 ; ptr_hi = src_hi
        beq @got
@next:  txa
        clc
        adc #7
        tax
        cpx #28
        bcc @find
        jmp @ok                 ; src inconnu : succes silencieux
@got:   stx S_TMP               ; sauve index (pv_write clobbe X)
        lda #<MARK_S            ; "@@SNAP\n" (7 o)
        sta P_W
        lda #>MARK_S
        sta P_W+1
        lda #7
        ldx #0
        jsr pv_write
        ldx S_TMP
        lda REGTAB+2,x          ; IDX/LEN -> S_TRAIL (3 o contigus)
        sta S_TRAIL
        lda REGTAB+5,x
        sta S_TRAIL+1
        lda REGTAB+6,x
        sta S_TRAIL+2
        lda #<SNAP_NAMELEN
        sta P_W
        lda #>SNAP_NAMELEN
        sta P_W+1
        lda SNAP_NAMELEN
        clc
        adc #1
        ldx #0
        jsr pv_write
        lda #<S_TRAIL           ; IDX/LENLO/LENHI (3 o)
        sta P_W
        lda #>S_TRAIL
        sta P_W+1
        lda #3
        ldx #0
        jsr pv_write
        ldx S_TMP               ; payload : (ptr), len
        lda $8A
        sta P_W
        lda $8B
        sta P_W+1
        lda REGTAB+5,x
        pha                     ; len_lo de cote (X va servir)
        lda REGTAB+6,x
        tax                     ; len_hi
        pla                     ; len_lo -> A
        jsr pv_write
        ldx S_TMP
@ok:    pla
        tay
        pla
        tax
        pla
        clc
        rts

; ---- snap_load : restaure un bloc (dst=(ptr)) depuis le blob ----
snap_load:
        pha
        txa
        pha
        tya
        pha
        lda SNAP_BLOB           ; magique "SNAP" ?
        cmp #'S'
        beq @m1
        jmp @fail
@m1:    lda SNAP_BLOB+1
        cmp #'N'
        beq @m2
        jmp @fail
@m2:    lda SNAP_BLOB+2
        cmp #'A'
        beq @m3
        jmp @fail
@m3:    lda SNAP_BLOB+3
        cmp #'P'
        beq @m4
        jmp @fail
@m4:    ldx #0                  ; cherche dst dans REGTAB
@find:  lda REGTAB,x
        cmp $8A                 ; ptr = dst_lo
        bne @next
        lda REGTAB+1,x
        cmp $8B
        beq @got
@next:  txa
        clc
        adc #7
        tax
        cpx #28
        bcc @find
        jmp @fail               ; dst inconnu : erreur propre
@got:   lda #<SNAP_DATA         ; S_SRC = $E804+off (auto-modifie)
        clc
        adc REGTAB+3,x
        sta LD_OP+1
        lda #>SNAP_DATA
        adc REGTAB+4,x
        sta LD_OP+2
        lda $8A                 ; S_DST = (ptr)
        sta ST_OP+1
        lda $8B
        sta ST_OP+2
        lda REGTAB+5,x          ; S_CNT = len
        sta S_CNT
        lda REGTAB+6,x
        sta S_CNT+1
        ora S_CNT
        beq @ok                 ; len 0 (impossible) : rien a faire
@loop:  jsr COPYBYTE            ; 1 octet (LD_OP/ST_OP auto-modifies)
        inc LD_OP+1
        bne @a
        inc LD_OP+2
@a:     inc ST_OP+1
        bne @b
        inc ST_OP+2
@b:     lda S_CNT
        bne @c
        dec S_CNT+1
@c:     dec S_CNT
        lda S_CNT
        ora S_CNT+1
        bne @loop
@ok:    pla
        tay
        pla
        tax
        pla
        clc
        rts
@fail:  pla
        tay
        pla
        tax
        pla
        sec
        rts

; ---- paire de copie auto-modifiee (operandes patches par snap_load) ----
COPYBYTE:
LD_OP:  lda $FFFF
ST_OP:  sta $FFFF
        rts

; ---- fin : blob $E800-$F62B, code ci-dessus (~$F700-$F8xx < $FC00) ----
