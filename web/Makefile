# The Hobbit (Oric 1982) - emulateur WASM + UI web.
#
# make pur (pas de cmake). Toolchain : emcc (MacPorts) + ca65/ld65 vendus
# dans tools/cc65/bin (cf. AGENTS.md §3 : chemins deriver de la racine).
#
# Usage :
#   make            # check + shims + wasm + assets
#   make check      # gardes byte-identiques sur data/hobbit.bin
#   make shims      # assemble harness/shim.s (solveur) et snap.s -> build/
#   make wasm       # web/build/hobbit.js + hobbit.wasm
#   make serve      # serveur statique (node) sur http://localhost:8000
#   make clean
#
# emcc est un programme Python (elle-meme) : EMSDK_PYTHON force le 3.14
# MacPorts (le Python Xcode 3.9 est refuse par emscripten >= 3.10).

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
WEB  := $(ROOT)/web
BUILD:= $(WEB)/build

HOST  := $(ROOT)/host
CPU   := $(ROOT)/cpu

CA65 := $(ROOT)/tools/cc65/bin/ca65
LD65 := $(ROOT)/tools/cc65/bin/ld65
EMCC ?= /opt/local/bin/emcc
EMSDK_PYTHON ?= /opt/local/bin/python3.14

SIM65_DIR := $(ROOT)/tools/cc65/src/sim65
SIM65_SRC := $(SIM65_DIR)/6502.c $(SIM65_DIR)/memory.c \
             $(SIM65_DIR)/peripherals.c $(SIM65_DIR)/error.c \
             $(SIM65_DIR)/trace.c
HOST_SRC  := $(HOST)/core.c $(HOST)/hobbit.c $(HOST)/io.c \
              $(HOST)/state.c $(HOST)/map.c $(HOST)/vec.c \
              $(HOST)/msg.c
INC       := -I$(SIM65_DIR) -I$(ROOT)/tools/cc65/src/common -I$(HOST)/include -I$(HOST)

CFLAGS  := -O2 -std=gnu11 -Wno-attributes
EMFLAGS := -s WASM=1 -s MODULARIZE=1 -s EXPORT_ES6=1 -s EXPORT_NAME=createHobbit \
           -s ENVIRONMENT=web,worker,node -s ALLOW_MEMORY_GROWTH=0 \
           -s INITIAL_MEMORY=33554432 -s EXPORTED_RUNTIME_METHODS=HEAPU8,UTF8ToString \
           --no-entry

.PHONY: all check shims wasm assets serve test clean

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

# ---- shims 6502 (ca65/ld65, locales a $C000 / $F700) ----
shims: $(BUILD)/shim.bin $(BUILD)/snap.bin

$(BUILD)/shim.bin: $(ROOT)/harness/shim.s $(ROOT)/harness/shim.cfg
	@mkdir -p $(BUILD)
	$(CA65) -D SOLVER -o $(BUILD)/shim.o $(ROOT)/harness/shim.s
	$(LD65) -C $(ROOT)/harness/shim.cfg -o $@ $(BUILD)/shim.o
	@sz=$$(wc -c < $@); [ $$sz -le 752 ] || { echo "shim trop gros : $$sz > 752"; exit 1; }
	@echo "shim.bin : $$(wc -c < $@) o"

$(BUILD)/snap.bin: $(ROOT)/harness/snap.s $(ROOT)/harness/snap.cfg
	@mkdir -p $(BUILD)
	$(CA65) -o $(BUILD)/snap.o $(ROOT)/harness/snap.s
	$(LD65) -C $(ROOT)/harness/snap.cfg -o $@ $(BUILD)/snap.o
	@sz=$$(wc -c < $@); [ $$sz -le 1280 ] || { echo "snap trop gros : $$sz > 1280"; exit 1; }
	@echo "snap.bin : $$(wc -c < $@) o"

# ---- wasm ----
wasm: $(BUILD)/hobbit.js

$(BUILD)/hobbit.js: $(HOST_SRC) $(SIM65_SRC) $(HOST)/include/hobbit.h $(HOST)/io.h
	@mkdir -p $(BUILD)
	EMSDK_PYTHON=$(EMSDK_PYTHON) $(EMCC) $(CFLAGS) $(INC) $(EMFLAGS) \
	    $(HOST_SRC) $(SIM65_SRC) -o $@
	@echo "wasm : $@ + $(BUILD)/hobbit.wasm"

# ---- assets servis tels quels (fetch cote JS) ----
assets: wasm shims
	@mkdir -p $(BUILD)
	cp $(ROOT)/data/hobbit.bin $(ROOT)/data/basic10.rom $(BUILD)/
	cp $(WEB)/ui/index.html $(WEB)/ui/app.js $(WEB)/ui/style.css $(WEB)/ui/solution.js $(BUILD)/
	@echo "assets : $(BUILD)/{hobbit.bin,basic10.rom,index.html,app.js,style.css,solution.js}"

serve:
	@echo "http://localhost:8000  (HMR : editez web/ui|host|cpu -> rebuild+reload)"
	node $(WEB)/serve.js $(BUILD) 8000

# Boot + une commande, valide le wasm sans navigateur (node).
test: all
	node $(WEB)/smoke.mjs

clean:
	rm -rf $(BUILD)
