; Shims clavier/ecran pour The Hobbit sous sim65 (adresse $9200).
;
; Patch applique par scripts/pack_sim.py : JMP shim_kb a la place des
; 3 premiers octets de $7353 (scan clavier VIA, inutilisable sous sim65).
; Tous les lecteurs clavier du jeu (keyin $7481, pauses $7628/$7640, SAVE)
; passent par $7353 : un seul point d'interception.
;
; Semantique : A = touche lue (bit 7 = presente) ou $00 (absente).
;   - machine a etats : octet script -> [present] -> [relache] -> octet suivant
;   - EOF stdin -> $00 (le jeu boucle, borner avec sim65 -x)
; X, Y et le zero-page utilise sont preserves ; A = resultat (l'original
; n'est pas conserve : pas de PHA d'entree pour A, pile equilibree).
;
; A chaque appel, l'ecran texte ($BB80-$BFDF, 1120 o) est compare a son
; miroir ; en cas de changement, dump sur stdout (fd 1) :
;   "@@FRAME text\n" + 1120 octets bruts. Idem hires ($A000-$BFFF, 8192 o)
; si HIBIT = 1.

        .setcpu "6502"
        .segment "CODE"

PV_READ  = $FFF6
PV_WRITE = $FFF7

SPADDR   = $02                  ; mot ZP = pile logicielle paravirt
PVTOP    = $C210

KEYBUF   = $C200
KBSTATE  = $C201
HIBIT    = $C202                ; 1 = dump hires aussi
RESULT   = $C203

P_TXT    = $04                  ; ptr ZP (sauvegardes, cf. dump_text)
P_SH     = $06

TXT      = $BB80
TXTLEN   = $0460
TXTSH    = $C300
HGR      = $A000
HGRLEN   = $2000
HGRSH    = $C800

; ---- point d'entree (JMP $9200 depuis $7353) ----
shim_kb:
        txa
        pha
        tya
        pha
        lda KBSTATE
        bne release
        ; nouvel octet sur stdin (bloquant ; EOF -> 0 octet -> absent)
        jsr pv_setup
        lda #<KEYBUF
        sta (SPADDR),y          ; Buf (poppe en 1er)
        iny
        lda #>KEYBUF
        sta (SPADDR),y
        iny
        lda #0
        sta (SPADDR),y          ; FD = 0 (stdin, poppe en 2nd)
        iny
        lda #0
        sta (SPADDR),y
        lda #1
        ldx #0                  ; AX = count
        jsr PV_READ
        cmp #1                  ; A = nb d'octets lus (0 = EOF)
        bne nokey
        lda #1
        sta KBSTATE
        lda KEYBUF
        ora #$80                ; bit 7 = touche presente
        sta RESULT
        bne dodump
nokey:
        lda #0
        sta RESULT
        beq dodump
release:
        lda #0
        sta KBSTATE
        sta RESULT
dodump:
        jsr dump_text
        lda HIBIT
        beq restore
        jsr dump_hires
restore:
        pla
        tay
        pla
        tax
        lda RESULT
        rts

; ---- SP = PVTOP-4, Y = 0 (4 octets de params : Buf(2), FD(2)) ----
pv_setup:
        lda #<(PVTOP-4)
        sta SPADDR
        lda #>(PVTOP-4)
        sta SPADDR+1
        ldy #0
        rts

; ---- PVWrite(Buf=P_W(*) , Count=A/X) vers stdout ----
P_W      = $C204
pv_write:
        sta P_CNT
        stx P_CNT+1
        jsr pv_setup
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
P_CNT    = $C206

; ---- dump ecran texte si changement ----
MARK_T: .byte "@@FRAME text", $0A
dump_text:
        lda P_TXT               ; sauve ZP utilise
        pha
        lda P_TXT+1
        pha
        lda P_SH
        pha
        lda P_SH+1
        pha
        lda #<TXT
        sta P_TXT
        lda #>TXT
        sta P_TXT+1
        lda #<TXTSH
        sta P_SH
        lda #>TXTSH
        sta P_SH+1
        ldx #4                  ; 4 pages pleines
@page:  ldy #0
@cmp:   lda (P_TXT),y
        cmp (P_SH),y
        bne @changed
        iny
        bne @cmp
        inc P_TXT+1
        inc P_SH+1
        dex
        bne @page
        ldy #0                  ; reste : $60 octets
@tail:  lda (P_TXT),y
        cmp (P_SH),y
        bne @changed
        iny
        cpy #$60
        bne @tail
        beq @done               ; identique
@changed:
        ; recopie miroir (P_TXT/P_SH ont avance : on les repositionne)
        lda #<TXT
        sta P_TXT
        lda #>TXT
        sta P_TXT+1
        lda #<TXTSH
        sta P_SH
        lda #>TXTSH
        sta P_SH+1
        ldx #4
@pg2:   ldy #0
@cp2:   lda (P_TXT),y
        sta (P_SH),y
        iny
        bne @cp2
        inc P_TXT+1
        inc P_SH+1
        dex
        bne @pg2
        ldy #0
@tl2:   lda (P_TXT),y
        sta (P_SH),y
        iny
        cpy #$60
        bne @tl2
        ; marqueur + contenu
        lda #<MARK_T
        sta P_W
        lda #>MARK_T
        sta P_W+1
        lda #13
        ldx #0
        jsr pv_write
        lda #<TXT
        sta P_W
        lda #>TXT
        sta P_W+1
        lda #<TXTLEN
        ldx #>TXTLEN
        jsr pv_write
@done:
        pla
        sta P_SH+1
        pla
        sta P_SH
        pla
        sta P_TXT+1
        pla
        sta P_TXT
        rts

; ---- dump hires si changement (actif si HIBIT = 1) ----
MARK_H: .byte "@@FRAME hires", $0A
dump_hires:
        lda P_TXT
        pha
        lda P_TXT+1
        pha
        lda P_SH
        pha
        lda P_SH+1
        pha
        lda #<HGR
        sta P_TXT
        lda #>HGR
        sta P_TXT+1
        lda #<HGRSH
        sta P_SH
        lda #>HGRSH
        sta P_SH+1
        ldx #32                 ; 32 pages
@page:  ldy #0
@cmp:   lda (P_TXT),y
        cmp (P_SH),y
        bne @changed
        iny
        bne @cmp
        inc P_TXT+1
        inc P_SH+1
        dex
        bne @page
        beq @done
@changed:
        lda #<HGR
        sta P_TXT
        lda #>HGR
        sta P_TXT+1
        lda #<HGRSH
        sta P_SH
        lda #>HGRSH
        sta P_SH+1
        ldx #32
@pg2:   ldy #0
@cp2:   lda (P_TXT),y
        sta (P_SH),y
        iny
        bne @cp2
        inc P_TXT+1
        inc P_SH+1
        dex
        bne @pg2
        lda #<MARK_H
        sta P_W
        lda #>MARK_H
        sta P_W+1
        lda #14
        ldx #0
        jsr pv_write
        lda #<HGR
        sta P_W
        lda #>HGR
        sta P_W+1
        lda #<HGRLEN
        ldx #>HGRLEN
        jsr pv_write
@done:
        pla
        sta P_SH+1
        pla
        sta P_SH
        pla
        sta P_TXT+1
        pla
        sta P_TXT
        rts
