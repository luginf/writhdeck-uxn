# Changelog

## v0.2.0

- **The terminal build catches up with the graphical one**: Delete, Home/End
  (all the usual escape variants), PgUp/PgDn, Shift+arrows selection with
  Ctrl+A/C/X/V, Ctrl+G go to line, Ctrl+F find, Ctrl+R replace, Ctrl+T table of
  contents, F1 help, word count in the status bar. The editing engine now
  lives in the shared core, used by both builds.
- **Optional mouse in the terminal build** (`writhdeck-uxn -m`): click, drag to
  select, middle click for a word, wheel.
- **The launcher starts the graphical build by default** (terminal build with
  `-c`, or automatically when there is no display).
- **All fonts, VGA included, now live in the font bank**, so the editing
  buffer grew from 43 KB to 46 KB.
- Roms renamed: `writhdeck.rom` is the graphical build and `writhdeck-cli.rom`
  the terminal build (as in v0.1.0 after its update).
- Shared code fixes: word-wrap by character width, undo/redo, protection
  against saving a file that was too big to load.

Usage as before: `uxnemu writhdeck.rom file.txt [WxH] [light] [f1|f2|f3]` and
`uxncli writhdeck-cli.rom file.txt [mouse]`, or the `writhdeck-uxn` launcher in
the repository. Do not open files with `uxn2` (upstream bug).

## v0.1.0

First public release. Two ready-to-run roms:

- `writhdeck.rom` — graphical build, run with `uxnemu` (the emulator must
  support expansion memory: `uxncli`, `uxnemu` and `uxn2` do; fonts live in a
  bank appended to the rom, which is why it is about 94 KB).
- `writhdeck-cli.rom` — terminal build, run with `uxncli` (needs an ANSI/VT100
  terminal in raw mode; the `writhdeck-uxn` launcher does that).

Highlights: UTF-8 aware editing (accented French everywhere), word-wrap,
undo/redo, find / replace / go to line, table of contents, selection and
internal clipboard, mouse (click, drag, middle-click word, wheel), light and
dark themes, four fonts (VGA, Cream 10x16, Cream proportional from `left`,
Cream 10x16 proportional), heading / comment / bold-italic highlighting,
quit confirmation, and protection against overwriting a file that was too big
to load (46 KB limit).

Usage: `uxnemu writhdeck.rom file.txt [WxH] [light] [f1|f2|f3]` or
`uxncli writhdeck-cli.rom file.txt`; the `writhdeck-uxn` launcher in the repository wraps
both. Do **not** open files with `uxn2` (upstream bug truncating File device
addresses). See `docs/MANUAL.md`.

Credits: fonts from the Linux console fonts (VGA), Hundred Rabbits' `left`
(cream, cream12; MIT) and this project (Cream 10x16).

Note: the roms were renamed shortly after this release was first published
(they were `writhdeck-gfx.rom` and `writhdeck.rom`); the assets, notes and the
`v0.1.0` tag were updated accordingly.
