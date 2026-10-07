#!/usr/bin/env python3
"""append_bank.py ROM DATA : pads ROM to 0xff00 bytes (the part loaded at
0x0100..0xffff) then appends DATA, which Varvara loads into expansion bank 1
(each following 0x10000 bytes go to the next bank)."""
import sys
from pathlib import Path
rom, data = Path(sys.argv[1]), Path(sys.argv[2])
b = rom.read_bytes()
if len(b) > 0xff00:
    sys.exit(f"{rom}: {len(b)} bytes, too big to pad to 0xff00")
rom.with_suffix(rom.suffix + '.size').write_text(str(len(b)))
rom.write_bytes(b + bytes(0xff00 - len(b)) + data.read_bytes())
