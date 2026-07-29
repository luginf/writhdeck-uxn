"""UTF-8 byte-passthrough regression: open an accented file, move the
cursor, insert plain ASCII, save, and confirm the accented bytes survived
the whole round-trip untouched on disk.
"""
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "utf8"
WORKDIR.mkdir(parents=True, exist_ok=True)
ini = WORKDIR / "writhd.ini"
ini.unlink(missing_ok=True)  # back to default margins for this check

doc = WORKDIR / "regress.txt"
doc.write_text("Café à côté\nélève naïve\n", encoding="utf-8")

keys = [b"\x1b[F", b" ok", b"\x13", b"\x11"]  # End, insert " ok", Ctrl+S, Ctrl+Q
out, code = run([str(doc)], keys, "End+insert ASCII+save+quit with default margins", cwd=WORKDIR)
assert code == 0, f"bad exit code: {code}"

content = doc.read_text(encoding="utf-8")
assert content == "Café à côté ok\nélève naïve\n", f"MISMATCH: {content!r}"

print("ALL UTF-8 ROUND-TRIP TESTS PASSED")
