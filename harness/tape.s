; Stubs cassette B1 pour The Hobbit sous sim65 (adresse $F700).
;
; Patche par scripts/pack_sim.py : JMP stub sur chaque vecteur bloc 1
; $0405-$0417 (ROM 1.0, morte sous sim65). Garde tape_save ($7215) et
; code_72FC (VERIFY) intacts : en-tetes + checksum EOR verifies pour de
; vrai. Seule la couche octet/bloc est emulee :
;   $0405 synchro -> rewind lecture (RD := T_DATA)
;   $0408 lecture octet -> A = (RD++), C=0 ; C=1 si fin (EOF)
;   $040B leader -> marqueur @@TAPE-BLOCK (pas de truncate : SAVE
;     ajoute ses 4 blocs a la suite, comme sur vraie cassette)
;   $040E ecriture octet -> bufferise + emet @@TAPE-BYTE (sature si plein)
;   $0411/$0414 setup/reset -> succes no-op (RTS partage)
;   $0417 lecture bloc -> parse header, stocke a (ptr), $32/$33 := dest,
;     C selon EOR ; auto-rewind une fois (l'utilisateur « rembobine ») ;
;     dumps @@MEM des 4 regions apres chaque bloc (cf. tape_check.py)
;
; Buffer en $E800 : RD/WR ($E800-$E803, adresses absolues, init $E804
; par pack_sim), donnees $E804-$EFFF (T_END=$F700, ~3820 o utiles :
; un SAVE+VERIFY+LOAD par session).
; ZP jeu touche : $02 transitoire (pattern paravirt, comme shim_kb) +
; $35-$3E / $37-$39 / $3B / $32-$33 (scratch cassette, exactement comme
; le jeu lui-meme). X/Y preserves partout ; A preserve sauf $0408
; (resultat) et $0417. Pas d'indirection ZP : auto-modification
; absolue (LD_OP/ST_OP), la zone $F700+ est RAM sous sim65.
;
; Table d'entrees en $F700 (lue par pack_sim.py) : 7 mots
; [s_0405, s_0408, s_040B, s_040E, s_0411, s_0414, s_0417].

        .setcpu "6502"
        .segment "CODE"

PV_WRITE = $FFF7
SPADDR   = $02                  ; mot ZP = pile logicielle paravirt
PVTOP    = $C2FF                ; params paravirt en $C2FB-$C2FE

T_RD     = $E800                ; curseur lecture (absolu, 2 o)
T_WR     = $E802                ; curseur ecriture (absolu, 2 o)
T_DATA   = $E804
T_END    = $F700                ; exclus : capacite $EFC = 3820 o

        .org $F700
        .word s_0405, s_0408, s_040B, s_040E, s_noop, s_noop, s_0417

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

; ---- $0405 : synchro = rewind lecture ----
s_0405:
        pha
        lda #<T_DATA
        sta T_RD
        lda #>T_DATA
        sta T_RD+1
        pla
        rts

; ---- $0411/$0414 : succes no-op ----
s_noop:
        rts

; ---- $040B : leader = marqueur de bloc ----
MARK_B: .byte "@@TAPE-BLOCK", $0A
s_040B:
        pha
        txa
        pha
        tya
        pha
        lda #<MARK_B
        sta P_W
        lda #>MARK_B
        sta P_W+1
        lda #13
        ldx #0
        jsr pv_write
        pla
        tay
        pla
        tax
        pla
        rts

; ---- lecture octet : A = (RD++), C=0 ; fin -> C=1, A=0 (X/Y gardes) ----
LD_OP:  lda $FFFF               ; operande patche (adresse absolue)
rd_byte:
        tya
        pha
        lda T_RD+1              ; RD < WR ?
        cmp T_WR+1
        bcc @ok
        bne @eof
        lda T_RD
        cmp T_WR
        bcc @ok
@eof:   pla
        tay
        sec
        lda #0
        rts
@ok:    lda T_RD
        sta LD_OP+1
        lda T_RD+1
        sta LD_OP+2
        inc T_RD
        bne LD_OP               ; RD++ puis execute LD_OP (tombe dedans)
        inc T_RD+1
LD_OP2 = LD_OP
        bne LD_OP2              ; (toujours pris : RD <$10000 ici)
s_0408 = rd_byte                ; patch $0408 -> ici (C = signal EOF)

; ---- $040E : ecriture octet (A ; A/X/Y gardes ; sature si plein) ----
MARK_1: .byte "@@TAPE-BYTE", $0A
BYTEBUF:.byte 0
ST_OP:  sta $FFFF               ; operande patche (adresse absolue)
s_040E:
        sta BYTEBUF             ; STA ne touche ni A ni flags
        pha
        txa
        pha
        tya
        pha
        lda T_WR+1              ; WR < T_END ?
        cmp #>T_END
        bcc @store
        bne @restore            ; plein : ni store ni emit
        lda T_WR
        cmp #<T_END
        bcs @restore
@store: lda T_WR
        sta ST_OP+1
        lda T_WR+1
        sta ST_OP+2
        inc T_WR
        bne @nohi
        inc T_WR+1
@nohi:  lda BYTEBUF
        sta ST_OP               ; *(WR++) = octet (absolu patche)
        lda #<MARK_1            ; emit marqueur + octet brut
        sta P_W
        lda #>MARK_1
        sta P_W+1
        lda #11
        ldx #0
        jsr pv_write
        lda #<BYTEBUF
        sta P_W
        lda #>BYTEBUF
        sta P_W+1
        lda #1
        ldx #0
        jsr pv_write
@restore:
        pla
        tay
        pla
        tax
        pla                     ; A = octet d'origine
        rts

; ---- $0417 : lecture bloc (miroir code_72FC, mais STOCKAGE) ----
ATT:    .byte 0                 ; 1 = rembobinage auto deja tente
s_0417:
        txa
        pha
        tya
        pha
        lda #0
        sta ATT
        ldy #0
        sty $3B                 ; EOR := 0 (comme VERIFY)
@scan:  jsr rd_byte             ; cherche $24
        bcs @rewind
        cmp #$24
        bne @scan
        ldy #9                  ; header : 9 octets en $35+Y (Y=9..1)
@hdr:   jsr rd_byte
        bcs @fail
        sta $35,y
        dey
        bne @hdr
        ; $37/$38 = dest (ptr), $39/$3A = fin : effet de bord du
        ; header, exactement comme le jeu (cf. code_72FC)
@sep:   jsr rd_byte             ; separateur $00 (miroir L7317)
        bcs @fail
        bne @sep
        lda $37                 ; (miroir L7328 : $37/$38 -> $32/$33)
        sta $32
        lda $38
        sta $33
        ldy #0
@data:  jsr rd_byte
        bcs @fail
        sta ($37),y             ; STOCKAGE (vs CMP du VERIFY)
        eor $3B
        sta $3B
        inc $37
        bne @cmp
        inc $38
@cmp:   lda $37
        cmp $39
        lda $38
        sbc $3A
        bcc @data
        jsr rd_byte             ; checksum
        bcs @fail
        cmp $3B
        bne @fail
        jsr tape_dumps          ; @@MEM des 4 regions (detruit A/X/Y/C)
        clc
        pla
        tay
        pla
        tax
        clc
        rts
@rewind:
        lda ATT
        bne @fail               ; deja rembobine -> vrai echec
        inc ATT
        lda #<T_DATA            ; RD := debut (l'utilisateur rembobine)
        sta T_RD
        lda #>T_DATA
        sta T_RD+1
        jmp @scan
@fail:  pla
        tay
        pla
        tax
        sec
        rts

; ---- dumps @@MEM post-bloc (format decode_mems.py) ----
M0:     .byte "@@MEM 0000 0100", $0A
M1:     .byte "@@MEM 1B1A 0556", $0A
M2:     .byte "@@MEM 28CC 02F1", $0A
M3:     .byte "@@MEM 211A 05C8", $0A
P_SRC:  .word 0
memdump:                        ; P_W = marqueur (16 o), P_SRC/LEN = zone
        sta P_CNT
        stx P_CNT+1
        lda #16
        ldx #0
        jsr pv_write
        lda P_SRC
        sta P_W
        lda P_SRC+1
        sta P_W+1
        lda P_CNT
        ldx P_CNT+1
        jmp pv_write
tape_dumps:
        lda #<M0
        sta P_W
        lda #>M0
        sta P_W+1
        lda #<$0000
        sta P_SRC
        lda #>$0000
        sta P_SRC+1
        lda #<$0100
        ldx #>$0100
        jsr memdump
        lda #<M1
        sta P_W
        lda #>M1
        sta P_W+1
        lda #<$1B1A
        sta P_SRC
        lda #>$1B1A
        sta P_SRC+1
        lda #<$0556
        ldx #>$0556
        jsr memdump
        lda #<M2
        sta P_W
        lda #>M2
        sta P_W+1
        lda #<$28CC
        sta P_SRC
        lda #>$28CC
        sta P_SRC+1
        lda #<$02F1
        ldx #>$02F1
        jsr memdump
        lda #<M3
        sta P_W
        lda #>M3
        sta P_W+1
        lda #<$211A
        sta P_SRC
        lda #>$211A
        sta P_SRC+1
        lda #<$05C8
        ldx #>$05C8
        jmp memdump
