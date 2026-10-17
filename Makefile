# The Hobbit (Oric 1982) — Makefile racine unique.
#
# Construit l'emulateur (C partage src/ + ASM 6502 src/6502) pour 3 cibles :
#   shims  : build/shims/{shim,snap}.bin (ca65/ld65 vendus)
#   native : build/native/hobplay (CLI, sim65 embarque, cc systeme)
#   wasm   : build/wasm/hobbit.js + hobbit.wasm + assets stagés (emcc)
#
# Usage :
#   make            # check + wasm + assets
#   make check      # gardes byte-identiques sur data/hobbit.bin (PROPRE exige)
#   make shims      # assemble src/6502/shim.s et snap.s -> build/shims/
#   make native     # build/native/hobplay (miroir exact de smoke.mjs)
#   make wasm       # build/wasm/hobbit.js + hobbit.wasm
#   make assets     # stage data/ + shims + src/web -> build/wasm/
#   make test       # boot + commande en Node (sans navigateur)
#   make serve      # http://localhost:8000 (HMR)
#   make clean      # efface native/wasm/shims (build/sim/ est preserve : DBs)
#
# L'execution attendue se fait depuis la racine du repo
# (chemins data/ et build/ relatifs au CWD, cf. src/native/platform_native.c).
#
# emcc est un programme Python (lui-meme) : EMSDK_PYTHON force le 3.14
# MacPorts (le Python Xcode 3.9 est refuse par emscripten >= 3.10).

ROOT  := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SRC   := $(ROOT)/src
UI    := $(SRC)/web
DEV   := $(ROOT)/dev
BUILD := $(ROOT)/build

SHIMS := $(BUILD)/shims
NATIV := $(BUILD)/native
WASM  := $(BUILD)/wasm

CA65 := $(ROOT)/tools/cc65/bin/ca65
LD65 := $(ROOT)/tools/cc65/bin/ld65
EMCC ?= /opt/local/bin/emcc
EMSDK_PYTHON ?= /opt/local/bin/python3.14

SIM65_DIR := $(ROOT)/tools/cc65/src/sim65
SIM65_SRC := $(SIM65_DIR)/6502.c $(SIM65_DIR)/memory.c \
             $(SIM65_DIR)/peripherals.c $(SIM65_DIR)/error.c \
             $(SIM65_DIR)/trace.c
CORE_SRC  := $(SRC)/core/core.c $(SRC)/core/hobbit.c $(SRC)/core/io.c \
             $(SRC)/core/state.c $(SRC)/core/map.c $(SRC)/core/vec.c \
             $(SRC)/core/msg.c
NATIVE_SRC:= $(SRC)/native/platform_native.c
CORE_HDR  := $(SRC)/include/hobbit.h $(SRC)/core/io.h $(SRC)/core/msg.h \
             $(SRC)/native/platform.h
INC       := -I$(SIM65_DIR) -I$(ROOT)/tools/cc65/src/common \
             -I$(SRC)/include -I$(SRC)/core -I$(SRC)/native

NATIVE_CC ?= cc
CFLAGS  := -O2 -std=gnu11 -Wall
EMCFLAGS:= -O2 -std=gnu11 -Wno-attributes
EMFLAGS := -s WASM=1 -s MODULARIZE=1 -s EXPORT_ES6=1 -s EXPORT_NAME=createHobbit \
           -s ENVIRONMENT=web,worker,node -s ALLOW_MEMORY_GROWTH=0 \
           -s INITIAL_MEMORY=33554432 -s EXPORTED_RUNTIME_METHODS=HEAPU8,UTF8ToString \
           --no-entry

.PHONY: all check shims native wasm assets serve test clean

all: check wasm assets

# ---- gardes byte-identiques (offsets = adresse - $0400) ----
# Les patchs doivent tomber sur les octets attendus de data/hobbit.bin.
check:
	@fail=0; \
	chk() { got=$$(od -An -tx1 -j $$2 -N $$3 $(ROOT)/data/hobbit.bin | tr -d ' \n'); \
	        [ "$$got" = "$$4" ] || { echo "check \$$$1 : $$got (attendu $$4)"; fail=1; }; }; \
	chk 7353 0x6F53 3 861e84; \
	chk 75B8 0x71B8 3 8ee075; \
	chk 7694 0x7294 3 48a900; \
	chk 7514 0x7114 3 48a900; \
	chk 7628 0x7228 3 205373; \
	chk 2C4A 0x284A 1 01; \
	chk 2C0B 0x280B 3 4cdb71; \
	chk 2C0E 0x280E 3 4c1572; \
	chk 2C11 0x2811 3 4ccb71; \
	[ $$fail -eq 0 ] && echo "check : PROPRE" || exit 1

# ---- shims 6502 (ca65/ld65, locaux a $C000 / $F700) ----
shims: $(SHIMS)/shim.bin $(SHIMS)/snap.bin

$(SHIMS)/shim.bin: $(SRC)/6502/shim.s $(SRC)/6502/shim.cfg
	@mkdir -p $(SHIMS)
	$(CA65) -D SOLVER -o $(SHIMS)/shim.o $(SRC)/6502/shim.s
	$(LD65) -C $(SRC)/6502/shim.cfg -o $@ $(SHIMS)/shim.o
	@sz=$$(wc -c < $@); [ $$sz -le 752 ] || { echo "shim trop gros : $$sz > 752"; exit 1; }
	@echo "shim.bin : $$(wc -c < $@) o"

$(SHIMS)/snap.bin: $(SRC)/6502/snap.s $(SRC)/6502/snap.cfg
	@mkdir -p $(SHIMS)
	$(CA65) -o $(SHIMS)/snap.o $(SRC)/6502/snap.s
	$(LD65) -C $(SRC)/6502/snap.cfg -o $@ $(SHIMS)/snap.o
	@sz=$$(wc -c < $@); [ $$sz -le 1280 ] || { echo "snap trop gros : $$sz > 1280"; exit 1; }
	@echo "snap.bin : $$(wc -c < $@) o"

# ---- hote natif (sim65 embarque, MEME code source que le WASM) ----
native: $(NATIV)/hobplay

$(NATIV)/hobplay: $(NATIVE_SRC) $(CORE_SRC) $(SIM65_SRC) $(CORE_HDR)
	@mkdir -p $(NATIV)
	$(NATIVE_CC) $(CFLAGS) $(INC) $(NATIVE_SRC) $(CORE_SRC) $(SIM65_SRC) -o $@
	@echo "hobplay : $@"

# ---- wasm ----
wasm: $(WASM)/hobbit.js

$(WASM)/hobbit.js: $(CORE_SRC) $(SIM65_SRC) $(CORE_HDR)
	@mkdir -p $(WASM)
	EMSDK_PYTHON=$(EMSDK_PYTHON) $(EMCC) $(EMCFLAGS) $(INC) $(EMFLAGS) \
	    $(CORE_SRC) $(SIM65_SRC) -o $@
	@echo "wasm : $@ + $(WASM)/hobbit.wasm"

# ---- assets servis tels quels (fetch cote JS) ----
assets: wasm shims
	@mkdir -p $(WASM)
	cp $(ROOT)/data/hobbit.bin $(ROOT)/data/basic10.rom $(WASM)/
	cp $(SHIMS)/shim.bin $(SHIMS)/snap.bin $(WASM)/
	cp $(UI)/index.html $(UI)/app.js $(UI)/style.css $(UI)/solution.js $(WASM)/
	@echo "assets : $(WASM)/{hobbit.bin,basic10.rom,shim.bin,snap.bin,index.html,app.js,style.css,solution.js}"

serve:
	@echo "http://localhost:8000  (HMR : editez src/web|src -> rebuild+reload)"
	node $(DEV)/serve.js $(WASM) 8000

# Boot + une commande, valide le wasm sans navigateur (node).
test: all
	node $(DEV)/smoke.mjs

clean:
	rm -rf $(NATIV) $(WASM) $(SHIMS)
