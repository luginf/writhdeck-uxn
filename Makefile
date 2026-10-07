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

rom-gfx: bin
	$(UXNASM) $(SRC_GFX) $(ROM_GFX)

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
