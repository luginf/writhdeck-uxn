"""Dynamic terminal-size detection via DSR at boot. See send-size-query /
on-sizereply in src/writhdeck.tal -- this replaced a hardcoded 24x80 that
clipped the text area to a fake width on any wider real terminal.
"""
import os
import pty
import fcntl
import struct
import subprocess
import termios
import time
import tty
from pathlib import Path

from pty_harness import run, ROM, UXNCLI

WORKDIR = Path(__file__).resolve().parent / "work" / "termsize"
WORKDIR.mkdir(parents=True, exist_ok=True)
ini = WORKDIR / "writhd.ini"
ini.unlink(missing_ok=True)

doc = WORKDIR / "doc.txt"
doc.write_text("This is a long line that should wrap across more than one "
               "visual row because it exceeds the text width available in "
               "this narrow terminal window for sure.\nshort line\n")

# 1) sanity: normal 24x80 behaves exactly like the old hardcoded default.
out, code = run([str(doc)], [b"\x11"], "24x80 (baseline)", cwd=WORKDIR)
assert code == 0

# 2) wide terminal: the line above fit in 68 text columns at 80-wide (with
# default margins) and wrapped. At 200-wide, text_width is comfortably over
# its length, so it must render on ONE row -- proof the real width is used
# instead of the old hardcoded 80.
out, code = run([str(doc)], [b"\x11"], "40x200 (wide terminal)", cwd=WORKDIR, rows=40, cols=200)
assert code == 0
text = out.decode(errors="replace")
assert "This is a long line that should wrap across more than one visual row because it exceeds the text width available in this narrow terminal window for sure." in text, \
    "expected the whole line on one row at 200 columns wide"
assert "\x1b[40;1H\x1b[7m" in text, "status bar should be on row 40, not the old hardcoded row 24"

# 3) small terminal: margin fallback still engages instead of crashing/hanging.
out, code = run([str(doc)], [b"\x11"], "10x20 (small terminal, margin fallback)", cwd=WORKDIR, rows=10, cols=20)
assert code == 0

# 4) no DSR reply at all: boot must block waiting (matches kibi.tal), not
# crash and not proceed with a bogus size.
master, slave = pty.openpty()
fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
tty.setraw(slave)
p = subprocess.Popen([UXNCLI, ROM, str(doc)], stdin=slave, stdout=slave, stderr=slave,
                      close_fds=True, cwd=str(WORKDIR))
os.close(slave)
time.sleep(1.0)
still_running = p.poll() is None
p.kill()
try:
    p.wait(timeout=2)
except subprocess.TimeoutExpired:
    pass
assert still_running, "expected boot to block waiting for the DSR reply, matching kibi.tal"

print("ALL TERMINAL-SIZE TESTS PASSED")
