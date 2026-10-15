#!/usr/bin/env python3
"""Esc menu and Ctrl+O file picker, driven in the REAL uxnemu (no window) through
tests/uxnemu_shim.c (LD_PRELOAD, SDL events). Each scenario starts from a folder
with a.txt and sub/c.txt and checks the saved files and the exit code."""
import os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROM = HERE.parent / "bin" / "writhdeck.rom"
UXNEMU = os.environ.get("UXNEMU", "uxnemu")
if not shutil.which(UXNEMU) or not shutil.which("sdl2-config"):
    print("SKIP gfx_pick: uxnemu or sdl2-config not found"); sys.exit(0)
W = HERE / "work" / "pick"; W.mkdir(parents=True, exist_ok=True)
shim = W / "shim.so"
if not shim.exists() or shim.stat().st_mtime < (HERE / "uxnemu_shim.c").stat().st_mtime:
    subprocess.run(["gcc", "-shared", "-fPIC", "-o", str(shim), str(HERE / "uxnemu_shim.c"),
                    *subprocess.check_output(["sdl2-config", "--cflags"], text=True).split(), "-ldl"], check=True)

def ctrl(c): return f"D:400000e0,D:{ord(c):x},U:{ord(c):x},U:400000e0"
SAVE, OPEN, UNDO = ctrl("s"), ctrl("o"), ctrl("z")
ENTER, DOWN, ESC = "D:0d,U:0d,W", "D:40000051,U:40000051,W", "D:1b,U:1b,W"
QUIT = f"{ESC},T:q,W"          # Esc menu, q
failed = []

def case(label, script, expect_a, expect_c, start="a.txt"):
    shutil.rmtree(W / "d", ignore_errors=True)
    (W / "d" / "sub").mkdir(parents=True)
    (W / "d" / "a.txt").write_text("aa\n"); (W / "d" / "sub" / "c.txt").write_text("cc\n")
    env = dict(os.environ, SHIMQ="1", SDL_RENDER_DRIVER="software", SDL_VIDEODRIVER="dummy",
               SDL_AUDIODRIVER="dummy", LD_PRELOAD=str(shim), SHIM="W," + ",".join(script) + ",W")
    r = subprocess.run([UXNEMU, str(ROM), start], cwd=W / "d", env=env, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    got = ((W / "d" / "a.txt").read_text(), (W / "d" / "sub" / "c.txt").read_text())
    if r.returncode != 0 or got != (expect_a, expect_c):
        failed.append(label); print(f"FAIL {label}: rc={r.returncode} {got!r} != {(expect_a, expect_c)!r}")
    else:
        print(f"ok   {label}")

# listing order is readdir order: sub/ is first in a fresh folder, and inside sub/ "../" precedes c.txt
case("Esc menu: q quits", [QUIT], "aa\n", "cc\n")
case("Esc menu: s saves", ["T:W", ESC, "T:s", QUIT], "Waa\n", "cc\n")
case("picker: enter sub/, open c.txt", [ESC, "T:o", ENTER, DOWN, ENTER, "T:X", SAVE, QUIT], "aa\n", "Xcc\n")
case("picker: Ctrl+O, sub/, ../ back, a.txt", [OPEN, ENTER, ENTER, DOWN, ENTER, "T:Y", SAVE, QUIT], "Yaa\n", "cc\n")
case("dirty: y discards then opens", ["T:Z", OPEN, "T:y", ENTER, DOWN, ENTER, UNDO, "T:Q", SAVE, QUIT], "aa\n", "Qcc\n")
case("dirty: s saves then opens", ["T:Z", OPEN, "T:s", ENTER, DOWN, ENTER, QUIT], "Zaa\n", "cc\n")
case("dirty: other key cancels", ["T:Z", OPEN, "T:n", "T:K", SAVE, QUIT], "ZKaa\n", "cc\n")
case("Esc closes the picker, Ctrl+O toggles it", [OPEN, ESC, "T:K", OPEN, OPEN, "T:L", SAVE, QUIT], "KLaa\n", "cc\n")
case("Esc with a selection only clears it (no menu)", [ctrl("a"), ESC, "T:q", SAVE, QUIT], "aa\nq", "cc\n")
print("FAILED: " + ", ".join(failed) if failed else "ALL PICKER TESTS PASSED")
sys.exit(1 if failed else 0)
