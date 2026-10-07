# writhdeck-uxn

note: files are limited to 48k max in size!
graphical version:  make run-gfx FILE=test.txt

Uxntal port of [WrithDeck](https://github.com/luginf/writhdeck) for the
[uxn](https://100r.co/site/uxn.html) virtual machine. Two entry points
share the same editing logic (`src/core.tal`) and build to two
separate roms — Varvara has no reliable way to detect at runtime
whether a Screen device is actually being displayed anywhere, so
producing one rom per output device is the idiomatic approach (matches
how the uxn ecosystem itself handles this, e.g. separate `.tal` entry
points per target rather than one rom that probes for a display):

- **Console** (`src/writhdeck.tal` → `bin/writhdeck.rom`, run with
  `uxncli`): the original port, a terminal program that emits plain
  ANSI/VT100 escapes over stdout and lets the host terminal do all
  rendering, exactly like `writhdeck-asm`. Byte-for-byte UTF-8
  passthrough falls out of this for free (no glyph/font work needed on
  the uxn side) — the Console device moves raw bytes, it never decodes
  them. Covered by the automated test suite (`tests/`).
- **Graphical** (`src/writhdeck-gfx.tal` → `bin/writhdeck-gfx.rom`, run
  with `uxnemu`): draws its own 8x16 bitmap font via the Screen device
  and reads input via the Controller device. See "Graphical mode"
  below — **this entry has never been visually verified** (no display
  or Xvfb was available while building it); it assembles cleanly and
  was checked line-by-line by hand, but treat it as unverified until
  someone runs it on a real display.

This is a first **bootstrapping** port (a working minimal editor),
not a feature-complete one. See "Known limitations" below.

## Building and running

```sh
make rom              # assembles src/writhdeck.tal -> bin/writhdeck.rom
./writhdeck-uxn path   # opens path;  ./writhdeck-uxn -n  starts an empty draft
make run FILE=path    # equivalent, via the Makefile
make test             # builds the rom, then runs the pty regression suite in tests/

make rom-gfx           # assembles src/writhdeck-gfx.tal -> bin/writhdeck-gfx.rom
make run-gfx FILE=path # runs it via uxnemu (needs a real display)
```

`writhdeck-uxn` is the single launcher for both builds:

```
./writhdeck-uxn [-c|-g] [-n] [-s WxH] [-z 1|2|3] [file]   # no argument: help
./writhdeck-uxn file.txt                 # terminal (default)
./writhdeck-uxn -g file.txt              # graphical window (uxnemu)
./writhdeck-uxn -g -s 1280x800 file.txt  # graphical, chosen window size
./writhdeck-uxn -g -n -z 2               # graphical, zoomed x2, empty draft
```

It opens the file from the file's own directory (uxn's File device
refuses paths outside the cwd, so `writhd.ini` is also looked up next to
the file), puts the terminal in raw mode before launching the console
rom and restores it afterwards (`uxncli` never touches termios), and
passes `-s` as the 2nd rom argument for the graphical build. Set
`UXNCLI`/`UXNEMU` to pick emulators.

`uxnasm`/`uxncli` must be installed and on `PATH` (or set `UXNASM`/
`UXNCLI` when invoking `make`).

### Terminal size

The real terminal size is queried at boot via a DSR request (`ESC[999C
ESC[999B ESC[6n`, moving the cursor to the bottom-right corner then
asking for its position), the same idiom used by the reference uxn
editor `kibi`. Boot blocks until the terminal answers with `ESC[row;
colR` — this requires a real ANSI/VT100-compatible terminal (the
`writhdeck-uxn` wrapper already puts the tty in raw mode, which is also
what lets the reply reach the rom instead of being echoed). If either
field of the reply is empty (a technically-valid but degenerate DSR
response), that axis falls back to the previous fixed default (24
rows / 80 cols). A pty-based test harness must inject the `ESC[row;
colR` reply itself (no real terminal is present to answer) or boot
never proceeds — see `wd-sz-state`/`on-sizereply` in
`src/writhdeck.tal`.

### Sandbox note

`uxncli`'s File device refuses to open a path it considers outside its
sandbox (silently: `/success` reports 0 bytes read, no error surfaced
in-program). In practice this means: run `writhdeck-uxn` from a directory
that is at or above the target file's location, or pass a path
relative to that directory — an absolute path elsewhere on the
filesystem, or a path escaping via `..` from an unrelated cwd, may be
blocked by `uxncli` itself before the rom ever sees it.

## `.ini` config (margins only)

`writhd.ini` is read from the **current directory only** — same
filename as `writhdeck-c`/`writhdeck-asm`'s primary path, but without
their fallback to `$HOME/Documents/writhdeck/writhdeck.ini`: uxn/
Varvara exposes no environment variables to a running rom (no
`getenv`), so `$HOME` is structurally unreachable from Uxntal and that
fallback cannot be implemented here. Only the `[editor]` section's
`margin_cols`/`margin_rows` keys are recognized (not the
`console_margin_cols`/`console_margin_rows` aliases, and no other
section/key — `word_goal`, `status_*`, `browser_*`, `timer_*`, etc. —
since none of what they'd configure exists in this port anyway).
Missing or unreadable file, or missing keys, default to `6`/`4`, same
defaults as `writhdeck-asm`. Anything non-digit between the key name
and its value (spaces, `=`, tabs) is skipped, so `margin_cols=6`,
`margin_cols = 6` and `margin_cols	=	6` all parse the same.

Margins are applied symmetrically (left/right from `margin_cols`,
top/bottom from `margin_rows`) around the text area, falling back
independently per axis to `0` if the terminal is too small to fit them
— same algorithm and same fallback behavior as `writhdeck-asm`'s
`draw_editor`. The status bar row is never inset by the horizontal
margin and is not affected by the vertical margin (always the last
screen row).

## Supported keys

Arrows (Up/Down/Left/Right, sticky column across lines), Home/End,
Enter, Backspace, Ctrl+S (save — only if a filename was given on the
command line; no save-as prompt), Ctrl+Q (quit; if the buffer is
modified it first asks in the status bar: `s` save and quit, `y` quit
without saving, any other key cancels — both builds).

Graphical build only (the Controller device reports no function keys,
and `uxnemu` keeps F11 for fullscreen, so everything is Ctrl+letter;
**Ctrl+H** shows this list in the program):

| Key | Action |
| --- | --- |
| Ctrl+S | Save (only when a file name was given) |
| Ctrl+Q | Quit; **asks for confirmation** if there are unsaved changes (`s` save and quit, `y` quit without saving, any other key cancels) |
| Ctrl+F | Find, case-insensitive for ASCII: type, Enter = next, Up = previous, Down = next, Esc closes; wraps around; the last query is kept |
| Ctrl+G | Go to line number |
| Ctrl+T | Table of contents: headings indented by level, Up/Down, Enter jumps, Esc cancels |
| Ctrl+D | Dark / light theme (start light with `-l`) |
| Ctrl+H | Help |
| Ctrl+Up / Ctrl+Down | Page up / page down |
| Ctrl+Home | Start of the document |
| Delete / Backspace | Erase forward / backward, **one whole UTF-8 character** at a time |

The status bar shows file, line,column, `[+]` when modified, and a word
count. Left/Right/Delete/Backspace and Up/Down never stop in the middle
of a multi-byte UTF-8 character (this core change also applies to the
console build).

Any byte `>= 0x20` other than `0x7F` is inserted into the buffer as
typed, including the individual bytes of a multi-byte UTF-8 sequence
typed at a terminal that sends them — so accented/non-ASCII characters
can be typed directly, not just displayed from a pre-existing file.

## Syntax highlighting

Two heading styles are detected and rendered in red (ANSI `ESC[31m`),
same color as `writhdeck-asm`'s `UI_ATTR_HEADING` — the whole logical
line is colored, not just the marker, and neither style tracks a
heading *level* for color purposes (matching `writhdeck-c`/
`writhdeck-asm`'s own `classify_line`, which only ever returns a single
`LINE_HEADING`):

- **Markdown**: `# Title` through `###### Title` (1 to 6 `#`
  characters, a mandatory space, then non-empty content). See
  `is-heading` in `src/writhdeck.tal`.
- **txt2tags**: `= Title =` (a single `=`, the same default marker as
  `writhdeck-c`/`writhdeck-asm`'s `heading_marker`, symmetric at both
  ends, non-empty content between them, leading/trailing whitespace
  tolerated). Any number of consecutive `=` also classifies as a
  heading (`== Title ==`, etc.) but — same simplification as above —
  without a level-based color difference. See `is-heading-t2t`.

No other classification (comments, lists) in this bootstrap, and the
heading marker is a fixed constant rather than read from an `.ini`
file (unlike `writhdeck-asm`'s partial `.ini` support) — see "Known
limitations" below.

## Word-wrap

Long lines wrap at the text width (after margins), breaking at the
last space before the limit like a normal word processor — same
greedy algorithm as `writhdeck-c`'s `editor_wrap`: consume up to
`width` bytes, back up to the last space if one exists in range
(excluding the space itself from either side), otherwise cut mid-word
if a single word is longer than the whole width (never hyphenates).
Nothing is precomputed or cached — no dynamic allocator here, so every
visual row boundary is walked fresh from the buffer on every render,
scroll, and cursor move, the same "recompute rather than cache"
philosophy as the rest of this port. Up/Down move by visual row
(crossing wrapped segments before moving to the next logical line);
Home/End still jump to the logical line's start/end, matching
`writhdeck-c`'s own `editor_move_home`/`editor_move_end`. Vertical
scrolling also operates in visual rows, so `wd-scroll` can point
mid-line once a line wraps. See `wrap-row-end`/`wrap-next-start`/
`visual-row-start`/`visual-row-before` in `src/writhdeck.tal`.

## Graphical mode

`src/writhdeck-gfx.tal` (→ `bin/writhdeck-gfx.rom`, run with `uxnemu`)
shares every bit of buffer/editing/word-wrap/margin/`.ini`/heading
logic with the console port (`src/core.tal`); only the I/O layer
differs. It draws an 8x16 bitmap font (`terminus01x02`, copied as-is
from `uxn/projects/examples/gui/terminal.tal` in the reference uxn
ecosystem — the same source already used as a reference for this
port's console bootstrap) via the `Screen` device, and reads input via
the `Controller` device instead of ANSI escapes over `Console`.

Terminal size is simpler here than in console mode: `Screen/width` and
`Screen/height` are exact and available synchronously at boot (no DSR
round-trip needed), so `wd-cols`/`wd-rows` are just those values
divided by the glyph size (8/16px).

**Loading a file: pass it as an argument, not via stdin.** Both
`uxnemu` and `uxn2` read the ROM's first extra argument through
`Console/type` (`ARG`/`EOA`/`END`) exactly the same way `uxncli` does
for the console build — `on-argv` in `core.tal` captures it into
`wd-fname` and loads it before the first frame is drawn:

```
uxnemu bin/writhdeck-gfx.rom path/to/file.txt
# or
make run-gfx FILE=path/to/file.txt
```

**Window size.** Default is 960x576 (120x36 cells). Pass an optional
second argument `WIDTHxHEIGHT` (pixels, 256..2048 x 128..1536, rounded
to multiples of 8/16): `uxnemu bin/writhdeck-gfx.rom file.txt 1280x800`
(`make run-gfx FILE=file.txt SIZE=1280x800`). `uxnemu -2x ...` also
zooms the whole window.

**Use `uxnemu`, not `uxn2`, to load files.** The `uxn2` build checked
here (26 Dec 2025, `implementations/uxn2/uxn2.c`) has an emulator bug:
`emu_deo(Uint8 addr, ...)` reuses its 8-bit port parameter `addr` to
hold the 16-bit RAM address of `File/name`/`File/read`/`File/write`,
truncating it to its low byte. The file name is then read from RAM
page 0 (empty), so every file access fails silently and the editor
starts with an empty buffer (status bar still shows the name). Verified
with a minimal ROM unrelated to this project. `uxnemu` and `uxncli`
are unaffected.

`uxn2 bin/writhdeck-gfx.rom < file.txt` does **not** load `file.txt` —
stdin redirection has nothing to do with argv. Both emulators also run
a background thread that streams the real process stdin (piped file or
not) into the `Console` device as keystrokes for as long as the
program runs, at the C level, unconditionally — confirmed by reading
`uxnemu.c`/`uxn2.c`'s `stdin_handler`. Since this entry has no use for
`Console` past the initial argv capture (input comes from
`Controller`, not `Console`), `entry-finish-boot` explicitly rebinds
`Console/vector` to `0000` right after boot to silence it — earlier
versions of this port left it bound to `on-argv`, so any stray stdin
traffic (e.g. `< file.txt`) kept re-triggering a full reload on every
byte, which looked exactly like "nothing loads".

Launching with **no file argument at all** (`uxnemu bin/writhdeck-gfx.rom`,
empty draft) now works too — it used to leave a permanently black
window. Neither emulator sends a single `Console` event of any kind
when there's no extra argument (their argv-forwarding loop in `main()`
is a plain `for` over the extra arguments and just doesn't run when
there are none), so `on-argv`'s fallback — the only thing that used to
trigger `core-boot`, and thus the first ever `gfx-render` — never
fired, and the window sat on whatever the framebuffer starts at
(black) forever. Fixed by wiring `Screen/vector` (which the emulator
calls once per frame, unconditionally, only after the window opens —
by which point any argv has already been delivered synchronously) to
a one-shot fallback, `on-first-frame`, that runs `core-boot` if
`on-argv` hasn't already done so. Guarded by `gfx-booted` so the two
possible triggers (`on-argv` for the with-file case, `on-first-frame`
for the without-file case) never both fire.

**Typing/loading accented text**: `SDL_TEXTINPUT` delivers the raw
UTF-8 bytes of composed keystrokes through `Controller/key`, one byte
per vector call (confirmed in `uxnemu.c`/`uxn2.c`) — so accented bytes
*are* inserted into the buffer correctly, same as any other byte
`on-button` accepts. The display now has real accented glyphs: the font is the VGA 8x16
bitmap font of `Uni2-VGA16.psf` (same style as the old ASCII font),
covering ASCII, all of Latin-1 and `’ … – — “ ” œ Œ €`. `gfx-utf8-decode`
turns the UTF-8 sequence into a glyph code; any other multi-byte
sequence (emoji, other scripts) draws as a single `?`. Padding and the
cursor column are computed in screen cells, but word-wrap in `core.tal`
still counts bytes, so a line with accents wraps slightly early. The
cursor moves by byte: on a 2-byte letter it takes two Left/Right
presses and is invisible on the second byte.

**Keyboard differences from the console build**, both consequences of
what Varvara's `Controller` device actually exposes, not choices made
by this port:
- **No dedicated End key** — `Controller` only has a Home bit, no
  symmetric End bit. Remapped to **Ctrl+E** (Emacs convention).
- **Ctrl+letter looks different at the device level.** `Controller/
  key` delivers the plain lowercase letter (`'q'` = `0x71`) together
  with the Ctrl bit set in `Controller/button` (bit `0x01`) — *not* a
  control code like `0x11`, unlike `Console/read` in a real terminal.
  Confirmed by reading `get_key()` in `uxn/src/uxnemu.c`. Ctrl+Q/Ctrl+S
  quit/save; anything else falls through to plain insertion.
- Holding an arrow key repeats the move every time the emulator
  re-fires the Controller vector (same as OS-level key repeat in a
  terminal) rather than through explicit key-repeat logic in this
  port.
- Characters outside Latin-1 and the few typographic signs in the font
  (emoji, other scripts) render as `?`; the buffer and saved file stay
  byte-faithful.

**No automated verification exists for this entry** — see "Known
limitations".

### Testing the graphical build without a window

`python3 tests/gfx_headless.py bin/writhdeck-gfx.rom script.txt [rom args]`
builds a scripted copy of `uxn2.c` (no SDL window, so no focus stealing;
the upstream File bug is patched in that copy) and replays commands
(`frame`, `key text`, `ctrl q`, `btn 0x20`, `enter`, `bksp`, `shot out.png`).

## Known limitations

- **Cursor is a byte offset into the buffer, not a decoded character
  index.** Content is a byte-faithful passthrough (accented text
  displays and round-trips through save correctly), but cursor/column
  arithmetic does not decode multi-byte UTF-8 sequences. Concretely:
  Right/Left may need more than one press to cross a multi-byte
  character, and inserting a character while the cursor sits *inside*
  (not before/after) a multi-byte sequence will split it and corrupt
  that character. Home/End are exact (they only look for `\n` bytes);
  Up/Down move by visual (wrapped) row and use a byte count as the
  "sticky column", so on a line containing multi-byte characters the
  landing column may be off by the width of those characters.
  UTF-8-aware cursor movement is the natural next step, not attempted
  in this bootstrap.
- **No save-as / no filename prompt.** Ctrl+S with no file opened (no
  argv path given) is a no-op.
- **Only the first command-line argument is used** as a file path; a
  missing argument starts an empty draft.
- **Flat fixed-capacity buffer** (~61 KB, `\n`-separated), not a
  per-line data structure — there is no dynamic allocator in this
  minimal setup, so line/column positions are recomputed by scanning
  from the buffer edges on every render and every cursor move, the
  same "recompute rather than cache" philosophy as writhdeck-c's
  `editor_wrap`.
- **No in-language unit tests.** Unlike `writhdeck-asm` (FASM + a small
  TAP-style framework), Uxntal has no unit-test convention this project
  uses, and uxn gives no fault protection at all — a stack imbalance
  causes silent data corruption (garbage jumps), never a crash or error
  message. Verification instead lives in `tests/`: Python scripts that
  drive the compiled `bin/writhdeck.rom` through `uxncli` under a real
  `pty` (scripting keystrokes, reading back the ANSI output, checking
  the saved file's bytes), the same style used to validate
  `writhdeck-asm`'s terminal code. Run them with `make test` (builds
  the rom first). Note that boot blocks on a DSR terminal-size reply
  (see "Terminal size" above) which a bare pty doesn't answer on its
  own, so `tests/pty_harness.py` answers it for every test — any new
  test script should go through that harness rather than driving
  `uxncli` directly. **`tests/` only covers the console build** —
  `writhdeck-gfx.tal` has no automated coverage at all, console-mode
  pty tricks don't apply to a Screen-device program (see "Graphical
  mode").

## Source layout

Three files, each a single `.tal` (matching the uxn ecosystem's own
convention of one file per program — `kibi.tal`, `left.tal` — rather
than `writhdeck-asm`'s multi-module split), tied together with `~src/
core.tal` includes (same idiom `left.tal` uses for `menu.tal`/
`utils.tal`/`assets.tal`):

- **`src/core.tal`**: everything device-agnostic. Argv capture
  (`on-argv`) and boot (`core-boot`, calls each entry's own
  `entry-finish-boot`), file load/save (`load-file`/`save-file`),
  editing primitives (`insert-byte`/`backspace`/`shift-left`/
  `shift-right`), cursor movement (byte-offset based, `line-start`/
  `line-end`/sticky-column `min2` helper for Up/Down), word-wrap
  (`wrap-row-end`/`wrap-next-start`/`visual-row-*`), margins/`.ini`
  (`compute-layout`/`load-config`/`parse-ini-*`), heading
  classification (`is-heading`/`is-heading-t2t`). Also `wd-fname`/
  `wd-buf`, the fixed-address data buffers both entries share.
- **`src/writhdeck.tal`**: console entry. Device declarations
  (`System`/`Console`), the DSR terminal-size dance (`send-size-query`/
  `on-sizereply`), the keypress dispatcher and escape-sequence state
  machine (`on-keypress`/`handle-escape`), the ANSI renderer
  (`wd-render`/`render-row`/`wd-status-bar`), and small ANSI/string
  utilities (`str-log`, `wd-print-dec`, `alt-buf-on`/`hide-cursor`/…).
- **`src/writhdeck-gfx.tal`**: graphical entry. Device declarations
  (`System`/`Screen`/`Controller`), the bitmap font and glyph/string/
  decimal drawing (`draw-char`/`draw-str`/`draw-dec`), the Controller
  dispatcher (`on-button`), and the pixel renderer (`gfx-render`/
  `gfx-status-bar`/`gfx-draw-cursor`).
