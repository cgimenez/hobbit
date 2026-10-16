; Shims clavier/ecran pour The Hobbit sous sim65 (adresse $C000).
;
; Patch applique par scripts/sim_pack.py : JMP shim_kb a la place des
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
; Variante SOLVER (ca65 -D SOLVER, cf. sim_pack.py --solver) : aucun dump
; ecran/memoire (shim_kb = lecture clavier pure) ; a la place, capture
; ASCII a la source via 2 hooks poses par sim_pack :
;   - L75B8 (corps commun du plot : print_char + L76ED->L75B8) -> asc_plot :
;     A = caractere final rendu (capitales appliquees) ; emis "@@A"+octet.
;     Le curseur '+' ($2B, reecrit par le caractere suivant) est emis aussi :
;     filtre cote Python. A/X/Y/$02/$03 preserves, octet remplace rejoue.
;   - L7694 (scroll, appele sur chaque CR ch_put) -> asc_eol : emis "@@EOL\n".
;   - L7514 (scroll du mode RAW : echo de la ligne de commande, un par CR)
;     -> asc_eol2 : emis "@@EOL\n".
;   - asc_plot emis "@@P\n" quand le caractere est '>' ($3E = prompt) : fin
;     de tour (segmentation cote Python sur les prompts).
;   - shim_kb (variante solveur) emis "@@K"+octet a chaque lecture stdin :
;     diagnostic des entrees rellement consommees par le jeu.
; Les dumps @@FRAME/@@MEM n'existent pas dans cette variante.
;
; A chaque appel, l'ecran texte ($BB80-$BFDF, 1120 o) est compare a son
; miroir ; en cas de changement, dump sur stdout (fd 1) :
;   "@@FRAME text\n" + 1120 octets bruts. Idem hires ($A000-$BFFF, 8192 o)
; si HIBIT = 1. Quand au moins un ecran a change, dump memoire en plus
; (6 regions, marqueurs "@@MEM addr len\n" 16 o + payload) :
;   $00BE/$0018 (ZP SAVE), $1B1A/$0556 (etats), $28CC/$02F1 (scripts),
;   $211A/$05C8 (records), $0000/$0100 et $2B00/$0100 (historiques).
; Decode via scripts/sim_mems.py ; suivi par tick dans
; scripts/sim_tickdiff.c.

        .setcpu "6502"
        .segment "CODE"

PV_READ  = $FFF6
PV_WRITE = $FFF7

SPADDR   = $02                  ; mot ZP = pile logicielle paravirt
PVTOP    = $C2FF                ; params paravirt en $C2FB-$C2FE

KEYBUF   = $C2F0
KBSTATE  = $C2F1
HIBIT    = $C2F2                ; 1 = dump hires aussi
RESULT   = $C2F3
MEMFLAG  = $C2F8                ; 1 = un ecran a change -> dumper la RAM
.ifdef SOLVER
ASC_CHAR = $C2F9                ; slot libre ($C2F9/$C2FA inutilises)
.endif

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
.ifdef SOLVER
        jsr k_log               ; "@@K"+octet lu (diagnostic entrees)
.endif
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
.ifdef SOLVER
        ; Variante solveur : pas de dump (capture ASCII par hooks L75B8/L7694).
        ; (fallthrough direct vers restore)
.else
        lda #0
        sta MEMFLAG
        jsr dump_text
        lda HIBIT
        beq @nomem
        jsr dump_hires
@nomem: lda MEMFLAG
        beq restore
        jsr dump_mem
.endif
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
P_W      = $C2F4
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
P_CNT    = $C2F6

.ifdef SOLVER
; ---- k_log : "@@K"+octet lu sur stdin (diagnostic entrees). Preserve
; A/X/Y/$02/$03 (meme gabarit que asc_plot). Appele apres sta RESULT :
; KEYBUF = octet brut, A = touche|$80.
k_log:
        pha
        txa
        pha
        tya
        pha
        lda $02
        pha
        lda $03
        pha
        lda KEYBUF
        sta K_BUF+3
        lda #<K_BUF
        sta P_W
        lda #>K_BUF
        sta P_W+1
        lda #4
        ldx #0
        jsr pv_write
        pla
        sta $03
        pla
        sta $02
        pla
        tay
        pla
        tax
        pla
        rts
K_BUF:  .byte "@@K", $00

; ---- hooks ASCII (variante solveur, cf. tete de fichier) ----
; asc_plot : JMP depuis L75B8 (remplace stx L75E0). Entree : A = caractere
; final rendu, X/Y = curseur. Preserve A/X/Y/$02/$03, rejoue stx/sty,
; reprend en $75BE. Le '+' curseur ($2B) est emis comme le reste : filtre
; cote Python (reecrit par le caractere suivant, sauf au repos).
asc_plot:
        sta ASC_BUF+3            ; octet emis (restaure A en sortie)
        txa
        pha
        tya
        pha
        lda $02
        pha
        lda $03
        pha
        lda #<ASC_BUF
        sta P_W
        lda #>ASC_BUF
        sta P_W+1
        lda #4
        ldx #0
        jsr pv_write            ; "@@A"+caractere
        lda ASC_BUF+3
        cmp #$3E                ; '>' = prompt : fin de tour (astuce)
        bne @nop
        lda #<MARK_P
        sta P_W
        lda #>MARK_P
        sta P_W+1
        lda #4
        ldx #0
        jsr pv_write            ; "@@P\n"
@nop:   pla
        sta $03
        pla
        sta $02
        pla
        tay
        pla
        tax
        lda ASC_BUF+3
        stx $75E0                ; octet remplace (L75B8)
        sty $75E1                ; octet remplace (L75BB)
        jmp $75BE                ; reprise (L75B8+6)

; asc_eol : JMP depuis L7694 (scroll, un par CR ch_put ; remplace pha +
; lda #$00). Rejoue les 2 octets, reprend en $7697.
asc_eol:
        sta ASC_CHAR
        txa
        pha
        tya
        pha
        lda $02
        pha
        lda $03
        pha
        lda #<MARK_E
        sta P_W
        lda #>MARK_E
        sta P_W+1
        lda #6
        ldx #0
        jsr pv_write
        pla
        sta $03
        pla
        sta $02
        pla
        tay
        pla
        tax
        lda ASC_CHAR
        pha                      ; octet remplace (L7694)
        lda #$00                 ; octet remplace (L7694+1)
        jmp $7697                ; reprise (L7694+3)

; asc_eol2 : JMP depuis L7514 (scroll du mode RAW : ligne de commande, un par
; CR d'echo ; remplace pha + lda #$00). Rejoue les 2 octets, reprend en $7517.
; Emis "@@EOLR\n" (marqueur distinct) : le filtre Python supprime ce saut s'il
; est immediatement suivi d'un "@@EOL" texte (RETURN + reponse = 1 seul saut).
asc_eol2:
        sta ASC_CHAR
        txa
        pha
        tya
        pha
        lda $02
        pha
        lda $03
        pha
        lda #<MARK_E2
        sta P_W
        lda #>MARK_E2
        sta P_W+1
        lda #7
        ldx #0
        jsr pv_write
        pla
        sta $03
        pla
        sta $02
        pla
        tay
        pla
        tax
        lda ASC_CHAR
        pha                      ; octet remplace (L7514)
        lda #$00                 ; octet remplace (L7514+1)
        jmp $7517                ; reprise (L7514+3)

; ---- donnees hooks (adresses resolues a l'edition de liens ;
; sim_pack.py lit asc_plot/asc_eol dans le listing ca65 -l) ----
ASC_BUF:.byte "@@A", $00
MARK_E: .byte "@@EOL", $0A
MARK_E2:.byte "@@EOLR", $0A
MARK_P: .byte "@@P", $0A

; ---- table de hooks a signature (lecture binaire, sans listing) --------
; L'emulateur web (web/core/hobbit.c) cherche "HSHK" dans le binaire et lit
; les 3 mots qui suivent = asc_plot/asc_eol/asc_eol2. Evite de parser le
; listing ca65 cote C (le harness natif continue d'utiliser le listing).
HOOKMAGIC:
        .byte "HSHK"
HOOKTAB:
        .word asc_plot, asc_eol, asc_eol2

.else
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
        lda #1
        sta MEMFLAG
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
        lda #1
        sta MEMFLAG
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

; ---- dump memoire (seulement si MEMFLAG) ----
; 6 regions : les 4 sources SAVE (octets suivis par sim_tickdiff) + les
; 2 historiques ($0000/$2B00, cf. sim_mems.py). Marqueurs 16 o.
M_S0:   .byte "@@MEM 00BE 0018", $0A
M_S1:   .byte "@@MEM 1B1A 0556", $0A
M_S2:   .byte "@@MEM 28CC 02F1", $0A
M_S3:   .byte "@@MEM 211A 05C8", $0A
M_S4:   .byte "@@MEM 0000 0100", $0A
M_S5:   .byte "@@MEM 2B00 0100", $0A
MEMTAB:
        .byte <M_S0, >M_S0, <$00BE, >$00BE, <$0018, >$0018
        .byte <M_S1, >M_S1, <$1B1A, >$1B1A, <$0556, >$0556
        .byte <M_S2, >M_S2, <$28CC, >$28CC, <$02F1, >$02F1
        .byte <M_S3, >M_S3, <$211A, >$211A, <$05C8, >$05C8
        .byte <M_S4, >M_S4, <$0000, >$0000, <$0100, >$0100
        .byte <M_S5, >M_S5, <$2B00, >$2B00, <$0100, >$0100
dump_mem:
        ldx #0                  ; index table (6 entrees x 6 o)
@reg:   txa
        pha                     ; sauve index (pv_write clobbe X)
        lda MEMTAB,x            ; marqueur 16 o
        sta P_W
        lda MEMTAB+1,x
        sta P_W+1
        lda #16
        ldx #0
        jsr pv_write
        pla
        tax                     ; restaure index
        txa
        pha
        lda MEMTAB+2,x          ; payload [src, len)
        sta P_W
        lda MEMTAB+3,x
        sta P_W+1
        lda MEMTAB+4,x
        pha                     ; len_lo de cote (X va servir)
        lda MEMTAB+5,x
        tax                     ; len_hi
        pla                     ; len_lo -> A
        jsr pv_write
        pla
        tax
        txa
        clc
        adc #6
        tax
        cpx #36
        bcc @reg
        rts
.endif ; (SOLVER / dumps classiques)
