UXNASM ?= uxnasm
UXNCLI ?= uxncli
UXNEMU ?= uxnemu

# graphical build (main): bin/writhdeck.rom, run with uxnemu
SRC     = src/writhdeck.tal
ROM     = bin/writhdeck.rom
# terminal build: bin/writhdeck-cli.rom, run with uxncli
SRC_CLI = src/writhdeck-cli.tal
ROM_CLI = bin/writhdeck-cli.rom

.PHONY: rom rom-cli run run-cli clean test layout

bin:
	mkdir -p bin

rom-cli: bin
	$(UXNASM) $(SRC_CLI) $(ROM_CLI)

fonts/fonts.bank: fonts/cream12.uf2 fonts/cream.uf2 fonts/Cream16x10.psf fonts/vga16.bin tools/mkfont.py
	python3 tools/mkfont.py fonts/cream-latin1.uf2

# the fonts travel in expansion bank 1 (the rom file is padded to 0xff00
# bytes then the font bank follows; Varvara loads it into bank 1)
rom: bin fonts/fonts.bank
	$(UXNASM) $(SRC) $(ROM)
	python3 tools/append_bank.py $(ROM) fonts/fonts.bank

run-cli: rom-cli
	./writhdeck-uxn -c $(if $(FILE),$(FILE),-n)

run: rom
	$(UXNEMU) $(ROM) $(FILE) $(SIZE)

layout: rom rom-cli
	python3 tests/check_layout.py

test: rom rom-cli layout
	UXNCLI=$(UXNCLI) python3 tests/run_all.py
	python3 tests/gfx_regress.py

clean:
	rm -rf bin
