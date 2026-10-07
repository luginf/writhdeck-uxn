"""A file bigger than the buffer must be flagged and never overwritten
(saving it would destroy the tail). A file that exactly fills the buffer
is not truncated."""
from pathlib import Path
from pty_harness import run

W = Path(__file__).resolve().parent / "work" / "toobig"
W.mkdir(parents=True, exist_ok=True)
(W / "writhd.ini").unlink(missing_ok=True)
BUF = 0xB200

big = W / "big.txt"
body = ("0123456789" * 8 + "\n") * 700          # 56,700 bytes > buffer
big.write_text(body)
# buffer is full: edit by deleting a char (End, Backspace), then try to save, then quit anyway
out, code = run([str(big)], [b"\x1b[F", b"\x7f", b"\x13", b"\x11", b"y"], "too big", cwd=W, quiet=True, collect=4, key_delay=0.3)
assert code == 0, code
assert big.read_text() == body, "truncated file was overwritten!"
assert b"truncated" in out, "no truncation notice"

exact = W / "exact.txt"
body2 = (b"a" * 79 + b"\n") * 569 + b"a" * 47 + b"\n"
assert len(body2) == BUF
exact.write_bytes(body2)
out, code = run([str(exact)], [b"\x1b[F", b"\x7f", b"\x13", b"\x11"], "exact fit", cwd=W, quiet=True, collect=3)
assert code == 0, code
assert b"truncated" not in out, "exact-size file wrongly flagged"
assert len(exact.read_bytes()) == BUF - 1, len(exact.read_bytes())
print("ALL TOO-BIG FILE TESTS PASSED")
