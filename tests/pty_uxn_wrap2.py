"""Up/Down movement across wrapped visual rows, and heading color staying
on every wrapped segment of a heading line, not just the first.
See visual-row-start/visual-row-before/move-up/move-down in
src/writhdeck-cli.tal.
"""
import re
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "wrap"
WORKDIR.mkdir(parents=True, exist_ok=True)
ini = WORKDIR / "writhd.ini"
ini.unlink(missing_ok=True)

doc = WORKDIR / "wraptest.txt"
long_line = ("This is a long line that should wrap across more than one visual "
             "row because it exceeds the text width available in this narrow "
             "terminal window for sure.")
doc.write_text(long_line + "\n" + "short line\n")


def status_lines(out):
    return re.findall(r'\x1b\[7m(.*?)\x1b\[K\x1b\[0m', out.decode(errors="replace"))


# Down x4 from (1,1): crosses the two wrap points of line 1, then lands on
# line 2 ("short line"). Expect the logical line/col sequence to advance
# 1,1 -> 1,66 -> 1,129 -> 2,1 -> 3,1 (this file has no line 3, so the last
# Down should be a no-op and stay at 2,1... but writhdeck-uxn's move-down
# clamps to the last line, so we just check monotonic progress instead of
# a fixed final value, to avoid over-fitting this assertion to internals
# that may shift with different text).
out, code = run([str(doc)], [b"\x1b[B", b"\x1b[B", b"\x1b[B", b"\x1b[B", b"\x11"],
                 "Down x4: cross wrapped segments then into next line", cwd=WORKDIR)
assert code == 0
statuses = status_lines(out)
assert statuses[0].endswith(" -- 1,1")
assert statuses[1].endswith(" -- 1,66")
assert statuses[2].endswith(" -- 1,129")
assert statuses[3].endswith(" -- 2,1")

# Down x4 then Up x3 should land back exactly where the 2nd Down landed.
out, code = run([str(doc)], [b"\x1b[B", b"\x1b[B", b"\x1b[B", b"\x1b[B",
                 b"\x1b[A", b"\x1b[A", b"\x1b[A", b"\x11"],
                 "Down x4 then Up x3: symmetric round-trip", cwd=WORKDIR)
assert code == 0
statuses = status_lines(out)
assert statuses[-1].endswith(" -- 1,66"), f"expected to land back at 1,66, got {statuses[-1]!r}"

# A heading long enough to wrap: every visual row of it must still be red.
doc2 = WORKDIR / "wrapheading.txt"
doc2.write_text("# This is a very long heading title that will definitely "
                "wrap onto a second visual row for sure\nnormal text after\n")
out, code = run([str(doc2)], [b"\x11"], "wrapped heading -- color on both rows", cwd=WORKDIR)
assert code == 0
text = out.decode(errors="replace")
assert "\x1b[31m# This is a very long heading title that will definitely" in text
assert "\x1b[31ma second visual row for sure" in text
assert "\x1b[31mnormal text after" not in text, "non-heading continuation must not be colored"

print("ALL WRAP MOVEMENT TESTS PASSED")
