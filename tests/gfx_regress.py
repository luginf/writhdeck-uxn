#!/usr/bin/env python3
"""Regression suite for the GRAPHICAL build, run without any window (see
gfx_headless.py). Each case replays keys, saves with Ctrl+S, and checks the
file content. Skipped when the uxn2 sources / gcc / SDL2 are missing."""
import os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROM = HERE.parent / "bin" / "writhdeck-gfx.rom"
SRC = os.environ.get("UXN2_SRC", "/temp/github/uxn-all/implementations/uxn2/uxn2.c")
if not Path(SRC).exists():
    print("SKIP gfx_regress: uxn2 sources not found (set UXN2_SRC)"); sys.exit(0)

W = HERE / "work" / "gfx"; W.mkdir(parents=True, exist_ok=True)
failed = []

def case(label, orig, cmds, expect, size="640x320"):
    doc = W / "g.txt"
    doc.write_text(orig, encoding="utf-8")
    script = W / "g.cmd"
    script.write_text("\n".join(["frame"] + cmds + ["ctrl s"]) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "gfx_headless.py"), str(ROM), str(script), "g.txt", size],
                   cwd=W, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    got = doc.read_text(encoding="utf-8")
    if got != expect:
        failed.append(label); print(f"FAIL {label}: {got!r} != {expect!r}")
    else:
        print(f"ok   {label}")

D = "0x20"  # Down button
case("type", "abc\n", ["key xy"], "xyabc\n")
case("undo group", "abc\n", ["key xyz", "ctrl z"], "abc\n")
case("undo+redo", "abc\n", ["key xyz", "ctrl z", "ctrl y"], "xyzabc\n")
case("delete forward", "abc\n", ["del"], "bc\n")
case("backspace utf8", "café\n", ["btn 0xc0", "key !", "bksp", "bksp"], "café\n".replace("é", "é"))
case("goto line", "a\nb\nc\n", ["ctrl g", "key 2", "enter", "key X"], "a\nXb\nc\n")
case("goto past end", "a\nb\n", ["ctrl g", "key 99", "enter", "key X"], "a\nb\nX")
case("find next", "aa bb cc bb\n", ["ctrl f", "key bb", "enter", "esc", "key Z"], "aa Zbb cc bb\n")
case("find twice", "aa bb cc bb\n", ["ctrl f", "key bb", "enter", "enter", "esc", "key Z"], "aa bb cc Zbb\n")
case("find case-insensitive", "xx Hello\n", ["ctrl f", "key hello", "enter", "esc", "key Z"], "xx ZHello\n")
case("toc jump", "intro\n= One =\ntext\n= Two =\n", ["ctrl t", "btn 0x20", "btn 0x20", "enter", "key Q"], "intro\n= One =\ntext\nQ= Two =\n")
# Ctrl+Q with unsaved changes must not exit: the later keys + Ctrl+S still run
case("quit confirm cancel", "abc\n", ["key a", "ctrl q", "key n", "key b"], "ababc\n")
case("quit confirm: any key cancels", "abc\n", ["key a", "ctrl q", "key x", "key b"], "ababc\n")
case("replace one then skip", "aa bb aa\n", ["ctrl r", "key aa", "enter", "key X", "enter", "key y", "key n", "esc"], "X bb aa\n")
case("replace all", "aa bb aa\n", ["ctrl r", "key a", "enter", "key bb", "enter", "key a", "esc"], "bbbb bb bbbb\n")
case("replace with empty", "aa bb aa\n", ["ctrl r", "key b", "enter", "enter", "key a", "esc"], "aa  aa\n")
case("replace skips then stops", "ab ab ab\n", ["ctrl r", "key ab", "enter", "key Z", "enter", "key n", "key y", "key n", "esc"], "ab Z ab\n")
case("replace esc stops", "ab ab\n", ["ctrl r", "key ab", "enter", "key Z", "enter", "esc", "key !"], "!ab ab\n")
case("replace not found", "abc\n", ["ctrl r", "key zz", "enter", "key Q", "enter", "esc", "key !"], "!abc\n")
SR = "btn 0x84"   # Shift + Right
case("select+cut+paste", "hello world\n", [SR]*5 + ["ctrl x", "ctrl e", "ctrl v"], " worldhello\n")
case("select+copy+paste", "hello world\n", [SR]*5 + ["ctrl c", "ctrl e", "ctrl v"], "hello worldhello\n")
case("typing replaces selection", "hello world\n", [SR]*5 + ["key X"], "X world\n")
case("backspace deletes selection", "hello world\n", [SR]*5 + ["bksp"], " world\n")
case("delete deletes selection", "hello world\n", [SR]*5 + ["del"], " world\n")
case("select all + delete", "a\nb\n", ["ctrl a", "bksp"], "")
case("move clears selection", "hello\n", [SR]*3 + ["btn 0x80", "key X"], "hellXo\n")
case("select utf8 + copy", "caf\u00e9 x\n", [SR]*4 + ["ctrl c", "ctrl e", "ctrl v"], "caf\u00e9 xcaf\u00e9\n")
case("cut then undo", "hello\n", [SR]*5 + ["ctrl x", "ctrl z"], "hello\n")
case("paste empty clipboard is harmless", "abc\n", ["ctrl v", "key X"], "Xabc\n")
case("esc clears selection", "hello\n", [SR]*3 + ["esc", "key X"], "helXlo\n")
# file bigger than the buffer: notice first (any key closes it), then edits must never be saved
BIG = ("0123456789" * 8 + "\n") * 700
case("too big: never overwritten", BIG, ["key q", "key X"], BIG)
# fonts: the same long line wraps at a different column per font (text width 544 px)
LONG = "i" * 200 + "\n"
def zpos(n): return "i" * n + "Z" + "i" * (200 - n) + "\n"
case("font VGA wraps at 68 cols", LONG, ["btn 0x20", "key Z"], zpos(68))
case("font Cream 10x16 wraps at 54 chars", LONG, ["btn 0x20", "key Z"], zpos(54), size="640x320 f1")
case("font Cream proportional wraps at 136 narrow chars", LONG, ["btn 0x20", "key Z"], zpos(136), size="640x320 f2")
bank = (HERE.parent / "fonts" / "fonts.bank").read_bytes()
wi = bank[0x4200 + ord("i")]
case("font Cream16 proportional wraps by glyph width", LONG, ["btn 0x20", "key Z"], zpos(544 // wi), size="640x320 f3")
case("Ctrl+P cycles fonts", LONG, ["ctrl p", "btn 0x20", "key Z"], zpos(54))
case("Ctrl+P x4 back to VGA", LONG, ["ctrl p", "ctrl p", "ctrl p", "ctrl p", "btn 0x20", "key Z"], zpos(68))
case("cream: accents survive edit+save", "caf\u00e9 \u0153uvre \u00ab x \u00bb\n", ["btn 0x80", "key Z"], "cZaf\u00e9 \u0153uvre \u00ab x \u00bb\n", size="640x320 f1")
case("cream: backspace removes whole char", "caf\u00e9\n", ["btn 0xc0", "key !", "bksp", "bksp"], "caf\u00e9\n", size="640x320 f1")
# mouse (VGA 640x320: text starts at x=48, y=64, cells 8x16)
DOC = "hello world\nsecond\n"
case("mouse click places the cursor", DOC, ["mouse 89 70", "mdown", "mup", "key X"], "helloX world\nsecond\n")
case("mouse click on 2nd line", DOC, ["mouse 49 83", "mdown", "mup", "key X"], "hello world\nXsecond\n")
case("mouse drag selects", DOC, ["mouse 49 70", "mdown", "mouse 89 70", "mup", "ctrl x", "ctrl e", "ctrl v"], " worldhello\nsecond\n")
case("mouse drag then type replaces", DOC, ["mouse 49 70", "mdown", "mouse 89 70", "mup", "key X"], "X world\nsecond\n")
case("mouse middle click selects a word", DOC, ["mouse 113 70", "mmid", "ctrl c", "ctrl e", "ctrl v"], "hello worldworld\nsecond\n")
case("mouse click past line end", DOC, ["mouse 300 70", "mdown", "mup", "key X"], "hello worldX\nsecond\n")
case("mouse above text area clamps to first row", DOC, ["mouse 49 5", "mdown", "mup", "key X"], "Xhello world\nsecond\n")
LINES = "".join("line%02d\n" % i for i in range(1, 60))
case("mouse wheel scrolls (3 rows), click maps to the scrolled row", LINES, ["wheel -1", "mouse 49 70", "mdown", "mup", "key X"], LINES.replace("line04", "Xline04", 1))
case("mouse click in Cream 10x16 (10 px cells)", DOC, ["mouse 99 70", "mdown", "mup", "key X"], "helloX world\nsecond\n", size="640x320 f1")
case("mouse click in proportional font stays inside the line", DOC, ["mouse 400 70", "mdown", "mup", "key X"], "hello worldX\nsecond\n", size="640x320 f2")
print("FAILED: " + ", ".join(failed) if failed else "ALL GFX REGRESSION TESTS PASSED")
sys.exit(1 if failed else 0)
