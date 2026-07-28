# writhdeck-uxn

Uxntal port of [WrithDeck](https://github.com/luginf/writhdeck) for the
[uxn](https://100r.co/site/uxn.html) virtual machine, targeting the
**Console device** (Varvara's `Console` port, `0x10`) — not the
`Screen` device. This means writhdeck-uxn is a terminal program: it
emits plain ANSI/VT100 escapes over stdout and lets the host terminal
do all rendering, exactly like `writhdeck-asm`. Byte-for-byte UTF-8
passthrough falls out of this for free (no glyph/font work needed on
the uxn side) — the Console device moves raw bytes, it never decodes
them.

This is a first **bootstrapping** port (a working minimal editor),
not a feature-complete one. See "Known limitations" below.

## Building and running

```sh
make rom              # assembles src/writhdeck.tal -> bin/writhdeck.rom
./writhdeck [path]     # opens path, or starts an empty draft if omitted
make run FILE=path    # equivalent, via the Makefile
```

`writhdeck` is a small shell wrapper (mirroring the one shipped with
the reference uxn editor `kibi`) that puts the terminal in raw mode
(`stty`) before launching the rom and restores it afterwards —
`uxncli` itself never touches termios, so keys would otherwise be
echoed and line-buffered without it.

`uxnasm`/`uxncli` must be installed and on `PATH` (or set `UXNASM`/
`UXNCLI` when invoking `make`).

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
- **Fixed 24x80 terminal size**, not queried from the real terminal
  (unlike `kibi`, which asks via a DSR escape). A future round should
  read the actual size.
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
- **No automated test harness.** Unlike `writhdeck-asm` (FASM + a
  small TAP-style framework), this port has no in-language unit tests.
  uxn gives no fault protection at all — a stack imbalance causes
  silent data corruption (garbage jumps), never a crash or error
  message — so verification here was done entirely by driving
  `bin/writhdeck.rom` through `uxncli` under a Python `pty` (scripting
  keystrokes, reading the ANSI output, checking the saved file's
  bytes), the same style used to validate `writhdeck-asm`'s terminal
  code. Building a real Uxntal test convention is future work.

## Source layout

Single file, `src/writhdeck.tal`, following the uxn ecosystem's own
convention (every reference program found in the uxn examples/`kibi`
is a single `.tal` file) rather than `writhdeck-asm`'s multi-module
split. Roughly, top to bottom: device declarations and macros,
zero-page state, boot (`on-reset`/`on-argv`/`finish-boot`), file load/
save, the keypress dispatcher and escape-sequence state machine,
editing primitives (`insert-byte`/`backspace`/`shift-left`/
`shift-right`), cursor movement (byte-offset based, `line-start`/
`line-end`/sticky-column `min2` helper for Up/Down), the renderer
(`wd-render`/`render-row`/`wd-status-bar`), and small ANSI/string
utilities (`str-log`, `wd-print-dec`, the `alt-buf-on`/`hide-cursor`/…
wrappers).
