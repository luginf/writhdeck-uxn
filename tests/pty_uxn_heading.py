"""Markdown heading detection/coloring (`# Title` .. `###### Title`).

See is-heading in src/writhdeck.tal.
"""
import re
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "heading"
WORKDIR.mkdir(parents=True, exist_ok=True)
doc = WORKDIR / "headings.txt"

lines = [
    "# Title one",                      # heading
    "normal text",                      # not heading
    "## Sub heading",                   # heading (level not color-distinguished)
    "###notaheading (no space)",        # not heading: no space after '#'
    "#",                                 # not heading: empty content
    "plain # not at start",              # not heading: '#' not at column 0
]
doc.write_text("\n".join(lines) + "\n")

out, code = run([str(doc)], [b"\x11"], "open headings.txt, quit", cwd=WORKDIR)
assert code == 0, f"bad exit code: {code}"

text = out.decode(errors="replace")

# For each fixture line, check whether it was preceded by the red heading
# escape (\x1b[31m) immediately before its text in the rendered output.
expect_red = {
    "# Title one": True,
    "normal text": False,
    "## Sub heading": True,
    "###notaheading (no space)": False,
    "#": False,
    "plain # not at start": False,
}
for line, should_be_red in expect_red.items():
    plain = f"      {line}\x1b[0m"
    red = f"      \x1b[31m{line}\x1b[0m"
    if should_be_red:
        assert red in text, f"expected heading color on: {line!r}"
    else:
        assert plain in text, f"expected NO heading color on: {line!r}"

print("ALL HEADING TESTS PASSED")
