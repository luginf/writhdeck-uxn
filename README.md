# writhdeck-uxn

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
./writhdeck [path]     # opens path, or starts an empty draft if omitted
make run FILE=path    # equivalent, via the Makefile
make test             # builds the rom, then runs the pty regression suite in tests/

make rom-gfx           # assembles src/writhdeck-gfx.tal -> bin/writhdeck-gfx.rom
make run-gfx FILE=path # runs it via uxnemu (needs a real display)
```

`writhdeck` is a small shell wrapper (mirroring the one shipped with
the reference uxn editor `kibi`) that puts the terminal in raw mode
(`stty`) before launching the rom and restores it afterwards —
`uxncli` itself never touches termios, so keys would otherwise be
echoed and line-buffered without it.

`uxnasm`/`uxncli` must be installed and on `PATH` (or set `UXNASM`/
`UXNCLI` when invoking `make`).

### Terminal size

The real terminal size is queried at boot via a DSR request (`ESC[999C
ESC[999B ESC[6n`, moving the cursor to the bottom-right corner then
asking for its position), the same idiom used by the reference uxn
editor `kibi`. Boot blocks until the terminal answers with `ESC[row;
colR` — this requires a real ANSI/VT100-compatible terminal (the
`writhdeck` wrapper already puts the tty in raw mode, which is also
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
in-program). In practice this means: run `writhdeck` from a directory
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
command line; no save-as prompt), Ctrl+Q (quit unconditionally, no
"unsaved changes" confirmation).

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
- Non-ASCII text renders poorly: the bitmap font only has glyphs for
  ASCII `0x20`–`0x7d`. Multi-byte UTF-8 sequences (e.g. typed or loaded
  accented characters) each render as one blank/placeholder glyph per
  byte instead of one correct character — a real loss of fidelity
  compared to the console build, which hands UTF-8 decoding off to the
  host terminal entirely. The underlying buffer and saved file remain
  byte-faithful either way; only the on-screen glyph is wrong.

**No automated verification exists for this entry** — see "Known
limitations".

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
