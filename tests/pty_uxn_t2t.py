"""txt2tags heading detection/coloring (`= Title =`, `== Title ==`, ...).

See is-heading-t2t in src/writhdeck-cli.tal.
"""
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "t2t"
WORKDIR.mkdir(parents=True, exist_ok=True)
doc = WORKDIR / "t2t.txt"

lines = [
    "= Title one =",             # heading (level 1)
    "== Title two ==",           # heading (level 2, still just colored)
    "no marker here",            # not heading
    "=only opening, no close",   # not heading: no closing '='
    "= =",                       # not heading: empty content
    "  = indented title =",      # heading: leading whitespace tolerated
    "= trailing ws title =   ",  # heading: trailing whitespace after closer tolerated
    "text = not at start =",     # not heading: marker not at line start
    "=a=b=",                     # heading: closer at the very end, "a=b" nonblank content
]
doc.write_text("\n".join(lines) + "\n")

out, code = run([str(doc)], [b"\x11"], "open t2t.txt, quit", cwd=WORKDIR)
assert code == 0, f"bad exit code: {code}"

text = out.decode(errors="replace")

expect_red = {
    "= Title one =": True,
    "== Title two ==": True,
    "no marker here": False,
    "=only opening, no close": False,
    "= =": False,
    "  = indented title =": True,
    "= trailing ws title =   ": True,
    "text = not at start =": False,
    "=a=b=": True,
}
for line, should_be_red in expect_red.items():
    plain = f"      {line}\x1b[0m"
    red = f"      \x1b[31m{line}\x1b[0m"
    if should_be_red:
        assert red in text, f"expected heading color on: {line!r}"
    else:
        assert plain in text, f"expected NO heading color on: {line!r}"

print("ALL TXT2TAGS TESTS PASSED")
