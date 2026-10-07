"""writhd.ini margin_cols/margin_rows: defaults, custom values, cursor-position
offsetting, and the small-terminal fallback to 0. See compute-layout and
load-config in src/writhdeck-cli.tal.
"""
from pathlib import Path
from pty_harness import run

WORKDIR = Path(__file__).resolve().parent / "work" / "margins"
WORKDIR.mkdir(parents=True, exist_ok=True)
doc = WORKDIR / "doc.txt"
doc.write_text("# Heading here\nline two\nline three\n")
ini = WORKDIR / "writhd.ini"

# 1) no ini -> defaults 6/4 -- first text row is screen row 5 (1-based,
# after 4 blank margin rows), left-indented by 6 spaces.
ini.unlink(missing_ok=True)
out, code = run([str(doc)], [b"\x11"], "no ini -- default margins 6/4", cwd=WORKDIR)
assert code == 0
text = out.decode(errors="replace")
assert "\x1b[H\x1b[K\n\x1b[K\n\x1b[K\n\x1b[K\n      \x1b[31m# Heading here" in text, \
    "expected 4 blank rows then 6-space-indented heading with default margins"

# 2) custom ini -- margins 2/1
ini.write_text("[editor]\nmargin_cols = 2\nmargin_rows = 1\n")
out, code = run([str(doc)], [b"\x11"], "custom ini -- margins 2/1", cwd=WORKDIR)
assert code == 0
text = out.decode(errors="replace")
assert "\x1b[H\x1b[K\n  \x1b[31m# Heading here" in text, \
    "expected 1 blank row then 2-space-indented heading with margins 2/1"

# 3) cursor movement: Right then Down from (1,1) with margins 2/1 should
# report screen position (row=text_top+2, col=margin_cols+1+1) = (3,4),
# while the logical status-bar line/col stay margin-independent (2,2).
out, code = run([str(doc)], [b"\x1b[C", b"\x1b[B", b"\x11"],
                 "custom ini -- move right+down, check cursor pos", cwd=WORKDIR)
assert code == 0
text = out.decode(errors="replace")
assert "-- 2,2" in text, "status bar should report logical line 2, col 2"
assert "\x1b[3;4H" in text, "screen cursor should land at row 3 col 4 with margins 2/1"

# 4) margin_rows too large for a 24-row terminal (>=12 forces vertical
# fallback to 0, per compute-layout's per-axis clamp) -- text should start
# at the very first screen row instead of being pushed off-screen.
ini.write_text("[editor]\nmargin_cols = 6\nmargin_rows = 20\n")
out, code = run([str(doc)], [b"\x11"], "margin_rows too large -- vertical fallback to 0", cwd=WORKDIR)
assert code == 0
text = out.decode(errors="replace")
assert "\x1b[H      \x1b[31m# Heading here" in text, \
    "expected no leading blank rows once margin_rows falls back to 0"

print("ALL MARGIN TESTS PASSED")
