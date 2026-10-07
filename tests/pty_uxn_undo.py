"""Undo/redo (Ctrl+Z = 0x1a, Ctrl+Y = 0x19) on the console build."""
from pathlib import Path
from pty_harness import run

W = Path(__file__).resolve().parent / "work" / "undo"
W.mkdir(parents=True, exist_ok=True)
(W / "writhd.ini").unlink(missing_ok=True)
doc = W / "u.txt"
Z, Y, S, Q = b"\x1a", b"\x19", b"\x13", b"\x11"

def case(orig, keys, expect, label):
    doc.write_text(orig, encoding="utf-8")
    out, code = run([str(doc)], keys + [S, Q], label, cwd=W, quiet=True)
    got = doc.read_text(encoding="utf-8")
    assert code == 0, f"{label}: exit {code}"
    assert got == expect, f"{label}: {got!r} != {expect!r}"

# typing run is ONE group: undo removes it all
case("abc\n", [b"xyz", Z], "abc\n", "undo typing")
# undo then redo restores it
case("abc\n", [b"xyz", Z, Y], "xyzabc\n", "undo+redo")
# two separated groups: undo only removes the last one
case("abc\n", [b"xy", b"\x1b[C", b"z", Z], "xyabc\n", "undo last group only")
# backspace run undone as one group (restores deleted chars)
case("abcdef\n", [b"\x1b[F", b"\x7f\x7f\x7f", Z], "abcdef\n", "undo backspace run")
# multi-byte char deleted with one backspace, restored by one undo
case("café\n", [b"\x1b[F", b"\x7f", Z], "café\n", "undo utf8 delete")
# Enter starts a group: "ab", then "\ncd" is one group
case("", [b"ab", b"\r", b"cd", Z], "ab", "enter opens group")
# redo is cleared by a new edit
case("abc\n", [b"x", Z, b"y", Y], "yabc\n", "redo cleared by new edit")
# several undo/redo steps
case("abc\n", [b"x", b"\x1b[C", b"y", Z, Z, Y, Y], "xaybc\n", "multi step")
print("ALL UNDO/REDO TESTS PASSED")
