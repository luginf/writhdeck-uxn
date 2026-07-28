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

## Supported keys

Arrows (Up/Down/Left/Right, sticky column across lines), Home/End,
Enter, Backspace, Ctrl+S (save — only if a filename was given on the
command line; no save-as prompt), Ctrl+Q (quit unconditionally, no
"unsaved changes" confirmation).

Any byte `>= 0x20` other than `0x7F` is inserted into the buffer as
typed, including the individual bytes of a multi-byte UTF-8 sequence
typed at a terminal that sends them — so accented/non-ASCII characters
can be typed directly, not just displayed from a pre-existing file.

## Known limitations

- **Cursor is a byte offset into the buffer, not a decoded character
  index.** Content is a byte-faithful passthrough (accented text
  displays and round-trips through save correctly), but cursor/column
  arithmetic does not decode multi-byte UTF-8 sequences. Concretely:
  Right/Left may need more than one press to cross a multi-byte
  character, and inserting a character while the cursor sits *inside*
  (not before/after) a multi-byte sequence will split it and corrupt
  that character. Moving by whole lines (Home/End/Up/Down) is exact,
  since those only look for `\n` bytes. UTF-8-aware cursor movement is
  the natural next step, not attempted in this bootstrap.
- **No word-wrap.** Lines longer than the terminal width are truncated
  on screen (not wrapped); only vertical scrolling is implemented.
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
