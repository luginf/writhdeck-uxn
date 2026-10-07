"""Console highlighting: % comment lines are green (ESC[32m), **bold**
//italic// __under__ --strike-- spans are cyan (ESC[36m), headings stay red,
and a plain '--' or a lone '**' without closing is not highlighted."""
from pathlib import Path
from pty_harness import run

W = Path(__file__).resolve().parent / "work" / "marks"
W.mkdir(parents=True, exist_ok=True)
(W / "writhd.ini").unlink(missing_ok=True)
doc = W / "m.txt"
doc.write_text("% a comment\n= Title =\nplain **bold** and //it// end\nalone ** star -- dash\n", encoding="utf-8")
out, code = run([str(doc)], [b"\x11"], "marks", cwd=W, quiet=True)
assert code == 0, code
txt = out.decode("utf-8", "replace")
assert "\x1b[32m% a comment" in txt, "comment not green"
assert "\x1b[31m= Title =" in txt, "heading not red"
assert "plain \x1b[36m**bold**\x1b[0m and \x1b[36m//it//\x1b[0m end" in txt, repr(txt[-400:])
assert "alone ** star -- dash" in txt and "\x1b[36m** star" not in txt, "false positive"
print("ALL MARK HIGHLIGHT TESTS PASSED")
