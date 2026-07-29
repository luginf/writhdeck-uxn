"""Word-wrap rendering: a long line should break at the last space before
the text width, never mid-word. See wrap-row-end in src/writhdeck.tal.
"""
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "wrap"
WORKDIR.mkdir(parents=True, exist_ok=True)
ini = WORKDIR / "writhd.ini"
ini.unlink(missing_ok=True)  # default margins 6/4 -> text_width = 80-12 = 68

doc = WORKDIR / "wraptest.txt"
long_line = ("This is a long line that should wrap across more than one visual "
             "row because it exceeds the text width available in this narrow "
             "terminal window for sure.")
doc.write_text(long_line + "\n" + "short line\n")

out, code = run([str(doc)], [b"\x11"], "long line word-wrap render", cwd=WORKDIR)
assert code == 0

text = out.decode(errors="replace")
for expected_row in (
    "This is a long line that should wrap across more than one visual",
    "row because it exceeds the text width available in this narrow",
    "terminal window for sure.",
):
    assert expected_row in text, f"missing expected wrapped row: {expected_row!r}"

# no visual row may end mid-word: for each wrapped row except the last,
# the next character in the ORIGINAL line (right after where this row's
# text ends) must be the space that was broken on, never a letter --
# that's precisely the bug this feature was written to fix (words like
# "exact"/"supporte" getting cut to "ex"/"suppo" at the wrap boundary).
import re
rows = re.findall(r'      ([^\r\n\x1b]*)\x1b\[0m', text)
wrapped_rows = rows[:2]  # first two rows are continuations of long_line
consumed = 0
for row in wrapped_rows:
    assert long_line[consumed:consumed + len(row)] == row, \
        f"row text does not match the source line at this offset: {row!r}"
    next_char = long_line[consumed + len(row):consumed + len(row) + 1]
    assert next_char == " ", \
        f"row ends mid-word: {row!r} is followed by {next_char!r}, not a space"
    consumed += len(row) + 1  # +1 to skip the space that was broken on

print("ALL WRAP RENDER TESTS PASSED")
