"""Shared driver for writhdeck-uxn's pty-based tests.

There is no in-language unit test convention for Uxntal in this
project (see README.md, "No automated test harness") -- uxn gives zero
fault protection, so verification here is done by driving the actual
compiled rom through `uxncli` under a real pty (as if a terminal were
typing at it) and inspecting the ANSI bytes it writes back.

Boot blocks waiting for a DSR terminal-size reply (see `on-sizereply`
in src/writhdeck-cli.tal) before it will render anything or accept
keypresses. A real terminal answers that automatically; a bare pty
does not, so `run()` answers it here -- every test in this directory
depends on that happening, which is why it lives in one shared place
rather than being copy-pasted per script (a previous version of these
tests had it duplicated seven times, which meant fixing one bug required
editing all seven).
"""

import os
import pty
import subprocess
import time
import fcntl
import termios
import tty
import struct
import select
from pathlib import Path

UXNCLI = os.environ.get("UXNCLI", "uxncli")
REPO_ROOT = Path(__file__).resolve().parent.parent
ROM = str(REPO_ROOT / "bin" / "writhdeck-cli.rom")


def run(args, keys, label, cwd, rows=24, cols=80, settle=0.3, key_delay=0.12,
        collect=1.5, answer_dsr=True, dsr_rows=None, dsr_cols=None, quiet=False):
    """Launch bin/writhdeck-cli.rom under uxncli on a pty, answer its boot-time
    terminal-size query, send `keys` (raw byte strings), and return
    (all_output_bytes, exit_code)."""
    dsr_rows = rows if dsr_rows is None else dsr_rows
    dsr_cols = cols if dsr_cols is None else dsr_cols

    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    tty.setraw(slave)
    p = subprocess.Popen([UXNCLI, ROM] + list(args), stdin=slave, stdout=slave,
                          stderr=slave, close_fds=True, cwd=str(cwd))
    os.close(slave)
    time.sleep(settle)

    out = b""
    if answer_dsr:
        deadline = time.time() + 1.0
        while time.time() < deadline:
            r, _, _ = select.select([master], [], [], 0.2)
            if not r:
                break
            out += os.read(master, 65536)
        os.write(master, f"\x1b[{dsr_rows};{dsr_cols}R".encode())
        time.sleep(settle)

    for k in keys:
        os.write(master, k)
        time.sleep(key_delay)

    deadline = time.time() + collect
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.2)
        if not r:
            continue
        try:
            chunk = os.read(master, 65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk

    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        p.kill()

    if not quiet:
        print(f"=== {label} ===")
        print("exit:", p.returncode)

    return out, p.returncode
