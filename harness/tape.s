; Stubs cassette B1 pour The Hobbit sous sim65 (adresse $F700).
;
; Patche par scripts/pack_sim.py : JMP stub sur chaque VECTEUR bloc 1
; $0405-$0414 (ROM 1.0, morte sous sim65). $0417 N'EST PAS un vecteur :
; c'est le loader du jeu (scan $24, header 9 o, stockage, verif
; $32/$33, cf. desassemblage $0417-$0465) — son code d'origine est
; conserve, il tourne sur les stubs octets ci-dessous. De meme
; tape_save ($7215) et code_72FC (VERIFY) restent intacts : en-tetes +
; checksum EOR verifies pour de vrai. Seule la couche octet/bloc est
; emulee :
;   $0405 synchro -> rewind lecture (RD := T_DATA)
;   $0408 lecture octet -> A = (RD++), C=0 ; C=1 si fin (EOF)
;   $040B leader -> marqueur @@TAPE-BLOCK (pas de truncate : SAVE
;     ajoute ses 4 blocs a la suite, comme sur vraie cassette)
;   $040E ecriture octet -> bufferise + emet @@TAPE-BYTE (sature si plein)
;   $0411/$0414 setup/reset -> succes no-op (RTS partage)
;
; Buffer en $E800 : RD/WR ($E800-$E803, adresses absolues, init $E804
; par pack_sim), donnees $E804-$EFFF (T_END=$F700, ~3820 o utiles :
; un SAVE+VERIFY+LOAD par session).
; ZP jeu touche : $02 transitoire (pattern paravirt, comme shim_kb) +
; $35-$3E / $37-$39 / $3B / $32-$33 (scratch cassette, exactement comme
; le jeu lui-meme). X/Y preserves partout ; A preserve sauf $0408
; (resultat). Pas d'indirection ZP : auto-modification
; absolue (LD_OP/ST_OP), la zone $F700+ est RAM sous sim65.
;
; Table d'entrees en $F700 (lue par pack_sim.py) : 6 mots
; [s_0405, s_0408, s_040B, s_040E, s_noop, s_noop].

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
        .word s_0405, s_0408, s_040B, s_040E, s_noop, s_noop

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
; NB : LD_OP n'est atteint que par jmp : un lda auto-modifie place juste
; avant l'entree retomberait dedans (boucle + fuite de pile).
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
        bne @read
        inc T_RD+1
@read:  pla
        tay
        jmp LD_OP               ; lit l'octet puis rts vers le jeu
LD_OP:  lda $FFFF               ; operande patche (adresse absolue)
        rts
s_0408 = rd_byte                ; patch $0408 -> ici (C = signal EOF)

; ---- $040E : ecriture octet (A ; A/X/Y gardes ; sature si plein) ----
; Store auto-modifie INLINE : STW est l'instruction executee (son
; operande est patche ci-dessus). NB : `sta STW` stockerait A *a*
; l'adresse STW (l'opcode) — pas ce qu'on veut (bug corrige : le
; buffer restait vide, VERIFY/LOAD tournaient sur des zeros).
MARK_1: .byte "@@TAPE-BYTE", $0A
BYTEBUF:.byte 0
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
        sta @stw+1
        lda T_WR+1
        sta @stw+2
        inc T_WR
        bne @nohi
        inc T_WR+1
@nohi:  lda BYTEBUF
@stw:   sta $FFFF               ; *(WR++) = octet ; operande patche
        lda #<MARK_1            ; emit marqueur + octet brut
        sta P_W
        lda #>MARK_1
        sta P_W+1
        lda #12                 ; "@@TAPE-BYTE" (11) + $0A
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

; ---- fin des stubs : le loader $0417 d'origine tourne dessus ----
