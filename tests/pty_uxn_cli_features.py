"""Terminal build: keys and features added after the first port -- Delete,
Home/End/PgUp/PgDn escape variants, selection and clipboard, go to line,
find, replace, table of contents, help, word count. Scenarios replay keys,
save with Ctrl+S and compare the file."""
import re
from pathlib import Path
from pty_harness import run

W = Path(__file__).resolve().parent / "work" / "clifeat"
W.mkdir(parents=True, exist_ok=True)
(W / "writhd.ini").unlink(missing_ok=True)
doc = W / "f.txt"
S, Q = b"\x13", b"\x11"
CTRL_C, CTRL_V, CTRL_X, CTRL_A = b"\x03", b"\x16", b"\x18", b"\x01"
ENTER = b"\r"
SHR = b"\x1b[1;2C"      # Shift+Right
failed = []

def case(label, orig, keys, expect, args=(), **kw):
    doc.write_text(orig, encoding="utf-8")
    out, code = run([str(doc), *args], keys + [S, Q], label, cwd=W, quiet=True, **kw)
    got = doc.read_text(encoding="utf-8")
    if code != 0 or got != expect:
        failed.append(label); print(f"FAIL {label}: exit {code}, {got!r} != {expect!r}")
    else:
        print(f"ok   {label}")
    return out

case("delete key", "abc\n", [b"\x1b[3~"], "bc\n")
case("End ~4", "abc\n", [b"\x1b[4~", b"X"], "abcX\n")
case("End ~8", "abc\n", [b"\x1b[8~", b"X"], "abcX\n")
case("End SS3", "abc\n", [b"\x1bOF", b"X"], "abcX\n")
case("Home ~1", "abc\n", [b"\x1b[F", b"\x1b[1~", b"X"], "Xabc\n")
case("Home ~7", "abc\n", [b"\x1b[F", b"\x1b[7~", b"X"], "Xabc\n")
case("Home SS3", "abc\n", [b"\x1b[F", b"\x1bOH", b"X"], "Xabc\n")
case("Ctrl+E end of line", "abc\n", [b"\x05", b"X"], "abcX\n")
case("Ctrl+End / Ctrl+Home", "a\nb\nc\n", [b"\x1b[1;5F", b"X", b"\x1b[1;5H", b"Y"], "Ya\nb\nc\nX")
LINES = "".join("line%02d\n" % i for i in range(1, 60))
case("PgDn then PgUp returns", LINES, [b"\x1b[6~", b"\x1b[5~", b"X"], "X" + LINES)
out = case("PgDn moves down", LINES, [b"\x1b[6~", b"X"], LINES, )  if False else None
doc.write_text(LINES); o, c = run([str(doc)], [b"\x1b[6~", b"X", S, Q], "pgdn", cwd=W, quiet=True)
g = doc.read_text()
if "X" + "line01" in g or g.count("X") != 1 or g.index("X") < 7 * 5:
    failed.append("PgDn moves down"); print("FAIL PgDn did not move a page:", g[:60].replace("\n", "|"))
else:
    print("ok   PgDn moves down")
case("select + cut + paste", "hello world\n", [SHR] * 5 + [CTRL_X, b"\x05", CTRL_V], " worldhello\n")
case("select + copy + paste", "hello world\n", [SHR] * 5 + [CTRL_C, b"\x05", CTRL_V], "hello worldhello\n")
case("typing replaces selection", "hello world\n", [SHR] * 5 + [b"X"], "X world\n")
case("backspace deletes selection", "hello world\n", [SHR] * 5 + [b"\x7f"], " world\n")
case("delete key deletes selection", "hello world\n", [SHR] * 5 + [b"\x1b[3~"], " world\n")
case("select all + delete", "a\nb\n", [CTRL_A, b"\x7f"], "")
case("plain move clears selection", "hello\n", [SHR] * 3 + [b"\x1b[C", b"X"], "hellXo\n")
case("select utf8 + copy/paste", "café x\n", [SHR] * 4 + [CTRL_C, b"\x05", CTRL_V], "café xcafé\n")
case("cut then undo", "hello\n", [SHR] * 5 + [CTRL_X, b"\x1a"], "hello\n")
case("go to line", "a\nb\nc\n", [b"\x07", b"2", ENTER, b"X"], "a\nXb\nc\n")
case("go to line ignores letters", "a\nb\nc\n", [b"\x07", b"x3", ENTER, b"X"], "a\nb\nXc\n")
case("find next", "aa bb cc bb\n", [b"\x06", b"bb", ENTER, CTRL_C, b"Z"], "aa Zbb cc bb\n")
case("find twice (Enter)", "aa bb cc bb\n", [b"\x06", b"bb", ENTER, ENTER, CTRL_C, b"Z"], "aa bb cc Zbb\n")
case("find previous (Up)", "aa bb cc bb\n", [b"\x06", b"bb", ENTER, ENTER, b"\x1b[A", CTRL_C, b"Z"], "aa Zbb cc bb\n")
case("find is case-insensitive", "xx Hello\n", [b"\x06", b"hello", ENTER, CTRL_C, b"Z"], "xx ZHello\n")
case("Esc then a key cancels a prompt", "abc\n", [b"\x07", b"\x1b", b"x", b"Y"], "Yabc\n")
case("replace one then skip", "aa bb aa\n", [b"\x12", b"aa", ENTER, b"X", ENTER, b"y", b"n", CTRL_C], "X bb aa\n")
case("replace all", "aa bb aa\n", [b"\x12", b"a", ENTER, b"bb", ENTER, b"a", CTRL_C], "bbbb bb bbbb\n")
case("replace with empty", "aa bb aa\n", [b"\x12", b"b", ENTER, ENTER, b"a", CTRL_C], "aa  aa\n")
case("replace not found", "abc\n", [b"\x12", b"zz", ENTER, b"Q", ENTER, CTRL_C, b"!"], "!abc\n")
TOC = "intro\n= One =\ntext\n= Two =\n"
case("toc jump", TOC, [b"\x14", b"\x1b[B", ENTER, b"Q"], "intro\n= One =\ntext\nQ= Two =\n")
case("toc cancel", TOC, [b"\x14", b"\x1b[B", CTRL_C, b"Q"], "Qintro\n= One =\ntext\n= Two =\n")
out = case("help screen closes on any key", "abc\n", [b"\x1bOP", b"x", b"Y"], "Yabc\n")
if b"keys" not in out:
    failed.append("help text"); print("FAIL help text not shown")
doc.write_text("one two three\nfour\n")
out, code = run([str(doc)], [Q], "word count", cwd=W, quiet=True)
if b"4 words" not in out:
    failed.append("word count"); print("FAIL word count:", out[-200:])
else:
    print("ok   word count")
doc.write_text("hello world\n")
out, code = run([str(doc)], [SHR, SHR, SHR, Q, b"y"], "selection is drawn in reverse video", cwd=W, quiet=True)
if b"\x1b[7mhel\x1b[27m" not in out:
    failed.append("selection render"); print("FAIL selection render:", out[-300:])
else:
    print("ok   selection is drawn in reverse video")
# mouse (-m): terminal 24x80, text starts at column 7, row 5 (margins 6 / 4)
def ev(b, x, y, up=False):
    return ("\x1b[<%d;%d;%d%s" % (b, x, y, "m" if up else "M")).encode()
DOC = "hello world\nsecond\n"
M = ("mouse",)
out = case("mouse click places the cursor", DOC, [ev(0, 12, 5), ev(0, 12, 5, True), b"X"], "helloX world\nsecond\n", args=M)
if b"\x1b[?1006h" not in out or b"\x1b[?1000l" not in out:
    failed.append("mouse enable/disable"); print("FAIL mouse reporting not enabled/disabled")
case("mouse click on 2nd line", DOC, [ev(0, 7, 6), ev(0, 7, 6, True), b"X"], "hello world\nXsecond\n", args=M)
case("mouse drag selects", DOC, [ev(0, 7, 5), ev(32, 12, 5), ev(0, 12, 5, True), CTRL_X, b"\x05", CTRL_V], " worldhello\nsecond\n", args=M)
case("mouse middle click selects a word", DOC, [ev(1, 15, 5), ev(1, 15, 5, True), CTRL_C, b"\x05", CTRL_V], "hello worldworld\nsecond\n", args=M)
case("mouse click past line end", DOC, [ev(0, 60, 5), ev(0, 60, 5, True), b"X"], "hello worldX\nsecond\n", args=M)
case("mouse wheel scrolls then click maps to the scrolled row", LINES, [ev(65, 1, 1), ev(0, 7, 5), ev(0, 7, 5, True), b"X"], LINES.replace("line04", "Xline04", 1), args=M)
case("mouse utf8 click", "caf\u00e9 x\n", [ev(0, 11, 5), ev(0, 11, 5, True), b"Z"], "caf\u00e9Z x\n", args=M)
out, code = run([str(doc)], [Q, b"y"], "no mouse reporting without -m", cwd=W, quiet=True)
if b"\x1b[?1006h" in out:
    failed.append("mouse default off"); print("FAIL mouse reporting enabled without -m")
else:
    print("ok   mouse reporting is off by default")
print("FAILED: " + ", ".join(failed) if failed else "ALL CLI FEATURE TESTS PASSED")
raise SystemExit(1 if failed else 0)
