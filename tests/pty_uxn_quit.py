"""Ctrl+Q confirmation: clean buffer quits at once; a modified buffer asks
first (s save+quit, y discard+quit, any other key cancels)."""
from pathlib import Path
from pty_harness import run

W = Path(__file__).resolve().parent / "work" / "quit"
W.mkdir(parents=True, exist_ok=True)
(W / "writhd.ini").unlink(missing_ok=True)
doc = W / "q.txt"
ORIG = "hello\n"

def fresh():
    doc.write_text(ORIG, encoding="utf-8")

# clean buffer: Ctrl+Q exits at once
fresh()
out, code = run([str(doc)], [b"\x11"], "clean quit", cwd=W, quiet=True)
assert code == 0, f"clean quit: exit {code}"

# modified buffer: Ctrl+Q alone must NOT exit and must show the prompt
fresh()
out, code = run([str(doc)], [b"x", b"\x11"], "dirty quit prompt", cwd=W, quiet=True)
assert code != 0, "modified buffer quit without asking"
assert b"Unsaved changes" in out, "no confirmation prompt shown"

# y: quits, file untouched
fresh()
out, code = run([str(doc)], [b"x", b"\x11", b"y"], "dirty y", cwd=W, quiet=True)
assert code == 0 and doc.read_text() == ORIG, (code, doc.read_text())

# s: saves then quits
fresh()
out, code = run([str(doc)], [b"x", b"\x11", b"s"], "dirty s", cwd=W, quiet=True)
assert code == 0 and doc.read_text() == "x" + ORIG, (code, doc.read_text())

# other key cancels, editing continues, normal save+quit works afterwards
fresh()
out, code = run([str(doc)], [b"x", b"\x11", b"n", b"y", b"\x13", b"\x11"], "dirty cancel", cwd=W, quiet=True)
assert code == 0 and doc.read_text() == "xy" + ORIG, (code, doc.read_text())

print("ALL QUIT-CONFIRMATION TESTS PASSED")
