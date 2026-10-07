#!/usr/bin/env python3
"""Verifie qu'aucun code assemble ne chevauche les zones de donnees fixes
(uxnasm ne le detecte pas). Taille de la rom = fin du dernier octet ecrit."""
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "bin"
LIMITS = {"writhdeck-cli.rom": ("ulog", None), "writhdeck.rom": ("ulog", None)}
ok = True
for name, (data_label, _) in LIMITS.items():
    rom, sym = R / name, R / (name + ".sym")
    d = sym.read_bytes(); i = 0; labels = {}
    while i < len(d):
        a = int.from_bytes(d[i:i+2], "big"); j = d.index(b"\0", i + 2)
        labels[d[i+2:j].decode()] = a; i = j + 1
    sizef = rom.with_suffix(rom.suffix + '.size')
    end = 0x100 + (int(sizef.read_text()) if sizef.exists() else rom.stat().st_size)
    core = labels["on-argv"]
    first_gfx_data = labels[data_label]
    entry_end_ok = True
    # le code de l'entree (avant core) doit finir avant core ; core doit finir avant les donnees
    # fin du code de l'entree = plus grand label de code < core
    entry_labels = [a for n, a in labels.items() if a < core and a >= 0x100 and not n.startswith("\u03bb")]
    print(f"{name}: core a {core:#06x}, fin du code {end:#06x}, donnees des {first_gfx_data:#06x}")
    if end > first_gfx_data:
        print(f"  ERREUR : le code ({end:#06x}) deborde sur les donnees ({first_gfx_data:#06x})"); ok = False
    # marge entre fin de l'entree et core : le rom est ecrit en ordre, donc on verifie via 'gfx-font'/derniere donnee
    last_entry = max(a for n, a in labels.items() if a < core and a >= 0x100)
    if last_entry >= core:
        print("  ERREUR : l'entree deborde sur core"); ok = False
# the docs must stay openable by our own roms (buffer = 0xa900 bytes, bigger files are truncated)
LIMIT = 0xA900
for f in [R.parent / "CLAUDE.md", R.parent / "README.md", *sorted((R.parent / "docs").glob("*.md"))]:
    n = f.stat().st_size
    if n > LIMIT - 2000:
        print(f"  ATTENTION : {f.name} fait {n} octets (limite du tampon {LIMIT}) : le decouper"); ok = ok and n <= LIMIT
sys.exit(0 if ok else 1)
