# Hote natif in-process (embed sim65) : cpu/platform_native.c + host/*.c +
# tools/cc65/src/sim65/{6502,memory,peripherals,error,trace}.c, compiles
# avec le cc systeme. MEME code source que le WASM, autre compilateur.
#
# Usage :
#   make -C cpu cli    # -> build/host/hobplay
#   make -C cpu clean
#
# L'execution attendue se fait depuis la racine du repo
# (chemins data/ et web/build relatifs au CWD, cf. platform_native.c).

ROOT  := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
BUILD := $(ROOT)/build/host

SIM65_DIR := $(ROOT)/tools/cc65/src/sim65
SIM65_SRC := $(SIM65_DIR)/6502.c $(SIM65_DIR)/memory.c \
             $(SIM65_DIR)/peripherals.c $(SIM65_DIR)/error.c \
             $(SIM65_DIR)/trace.c
HOST_SRC  := $(ROOT)/host/core.c $(ROOT)/host/hobbit.c $(ROOT)/host/io.c \
             $(ROOT)/host/state.c $(ROOT)/host/map.c $(ROOT)/host/vec.c \
             $(ROOT)/host/msg.c
CLI_SRC   := $(ROOT)/cpu/platform_native.c
INC       := -I$(SIM65_DIR) -I$(ROOT)/tools/cc65/src/common \
             -I$(ROOT)/host/include -I$(ROOT)/host

CC      ?= cc
CFLAGS  := -O2 -std=gnu11 -Wall

.PHONY: cli clean

cli: $(BUILD)/hobplay

$(BUILD)/hobplay: $(CLI_SRC) $(HOST_SRC) $(SIM65_SRC) $(ROOT)/host/include/hobbit.h $(ROOT)/host/io.h $(ROOT)/host/platform.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(INC) $(CLI_SRC) $(HOST_SRC) $(SIM65_SRC) -o $@
	@echo "hobplay : $@"

clean:
	rm -rf $(BUILD)
