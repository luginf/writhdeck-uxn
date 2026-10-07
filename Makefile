UXNASM ?= uxnasm
UXNCLI ?= uxncli
UXNEMU ?= uxnemu

SRC     = src/writhdeck.tal
ROM     = bin/writhdeck.rom
SRC_GFX = src/writhdeck-gfx.tal
ROM_GFX = bin/writhdeck-gfx.rom

.PHONY: rom rom-gfx run run-gfx clean test layout

bin:
	mkdir -p bin

rom: bin
	$(UXNASM) $(SRC) $(ROM)

fonts/fonts.bank: fonts/cream12.uf2 fonts/cream.uf2 fonts/Cream16x10.psf fonts/vga16.bin tools/mkfont.py
	python3 tools/mkfont.py fonts/cream-latin1.uf2

# the proportional font travels in expansion bank 1 (the rom file is padded
# to 0xff00 bytes then the font follows; Varvara loads it into bank 1)
rom-gfx: bin fonts/fonts.bank
	$(UXNASM) $(SRC_GFX) $(ROM_GFX)
	python3 tools/append_bank.py $(ROM_GFX) fonts/fonts.bank

run: rom
	./writhdeck-uxn $(if $(FILE),$(FILE),-n)

run-gfx: rom-gfx
	$(UXNEMU) $(ROM_GFX) $(FILE) $(SIZE)

layout: rom rom-gfx
	python3 tests/check_layout.py

test: rom rom-gfx layout
	UXNCLI=$(UXNCLI) python3 tests/run_all.py
	python3 tests/gfx_regress.py

clean:
	rm -rf bin
