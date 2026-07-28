UXNASM ?= uxnasm
UXNCLI ?= uxncli

SRC     = src/writhdeck.tal
ROM     = bin/writhdeck.rom

.PHONY: rom run clean

bin:
	mkdir -p bin

rom: bin
	$(UXNASM) $(SRC) $(ROM)

run: rom
	./writhdeck $(FILE)

clean:
	rm -rf bin
