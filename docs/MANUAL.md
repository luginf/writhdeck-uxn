# writhdeck-uxn — user manual

writhdeck-uxn is a distraction-free text editor for plain text and
txt2tags/markdown notes, written in Uxntal for the
[uxn / Varvara](https://100r.co/site/uxn.html) virtual machine. It is a port
of [WrithDeck](https://github.com/luginf/writhdeck). Two builds share one
editing core:

| Build | File | Runs with | Needs |
| --- | --- | --- | --- |
| Terminal | `writhdeck-cli.rom` | `uxncli` | an ANSI/VT100 terminal |
| Graphical | `writhdeck.rom` | `uxnemu` | a window; the emulator must support expansion memory (`uxncli`, `uxnemu`, `uxn2` do) |

## Install and run

```
make rom rom-cli          # needs uxnasm and python3
./writhdeck-uxn notes.txt # terminal build
./writhdeck-uxn -g notes.txt
```

`writhdeck-uxn` is a small launcher (run it without argument for its help):

| Option | Meaning |
| --- | --- |
| `-c` / `-g` | terminal (default) / graphical build |
| `-n` | start an empty draft, no file |
| `-s WxH` | graphical window size in pixels, e.g. `1280x800` (default 960x576) |
| `-z 1\|2\|3` | zoom the graphical window |
| `-l` | start in the light theme (black on white) |
| `-f NAME` | start font: `vga` (default), `cream`, `prop`, `creamprop` |

It opens the file from the file's own directory (the uxn File device cannot
reach paths outside the current directory), rebuilds a rom that is older than
its sources, and puts the terminal in raw mode for the terminal build. Set
`UXNCLI` / `UXNEMU` to choose the emulators. You can also run the roms
directly: `uxnemu writhdeck.rom notes.txt 1280x800 light f2`.
**Do not use `uxn2` to open files**: that build has a bug that truncates the
File device addresses, so nothing loads (the `left` editor is affected too).

## Keys

Both builds: arrows (Up/Down follow wrapped rows), Home / Ctrl+E (start / end
of line), Enter, Backspace, **Ctrl+S** save, **Ctrl+Q** quit (asks `s` save and
quit, `y` quit without saving, any other key cancels, when there are unsaved
changes), **Ctrl+Z / Ctrl+Y** undo / redo. Saving needs a file name given at
start-up.

Graphical build only (the Varvara Controller reports no function keys, so
everything is Ctrl+letter; Ctrl+H shows this list):

| Key | Action |
| --- | --- |
| Ctrl+F | Find (not case sensitive for ASCII): type, Enter = next, Up = previous, Esc closes |
| Ctrl+R | Replace: find text, Enter, replacement, Enter, then `y` this one, `n` skip, `a` all, Esc stop |
| Ctrl+G | Go to line |
| Ctrl+T | Table of contents (headings indented by level; Up/Down, Enter, Esc) |
| Ctrl+D | Dark / light theme |
| Ctrl+P | Cycle the font; its name shows in the status bar |
| Ctrl+H | Help |
| Shift+arrows | Select (left Shift only), Ctrl+A select all |
| Ctrl+C / X / V | Copy / cut / paste (internal clipboard, 512 bytes) |
| Delete | Erase forward (Backspace erases backward, whole characters) |
| Ctrl+Up / Down, Ctrl+Home | Page up / down, start of document |

**Mouse**: click places the cursor, drag selects (typing then replaces the
selection), middle click selects a word, the wheel scrolls three rows. The
program draws its own pointer because `uxnemu` hides the system one.

The status bar shows the file, line and column, `[+]` when modified and a word
count.

## Text and highlighting

- UTF-8 is handled by character: cursor moves, deletion and wrapping never cut
  a multi-byte letter. Accented French letters, `œ`, guillemets, dashes, `…`
  and `€` are displayed; other multi-byte characters show as `?`.
- Long lines wrap at the last space that fits.
- Colours: headings (`= Title =`, `== Title ==`, `# Title`) red; lines
  starting with `%` are comments (green in the terminal, accent colour in the
  graphical build); `**bold**`, `//italic//`, `__underline__`, `--strike--`
  spans use the accent colour (cyan, blue in the light theme).

## Fonts (graphical build)

| `-f` | Font |
| --- | --- |
| `vga` | VGA 8x16 (default) |
| `cream` | Cream 10x16, monospace, thin hand-drawn style, complete French coverage |
| `prop` | Cream proportional (left): the cream font of the `left` editor |
| `creamprop` | Cream 10x16 made proportional |

The fonts are stored inside the rom (expansion bank 1), so nothing has to be
installed next to it.

## Configuration

An optional `writhd.ini` in the file's directory:

```
[editor]
margin_cols = 6
margin_rows = 4
```

Margins default to 6 columns and 4 rows and shrink when the window is small.
Nothing else is read (uxn cannot read environment variables, so there is no
`$HOME` fallback).

## Limits

- **File size**: the document lives in one buffer of 47,104 bytes. A bigger
  file is loaded truncated, a notice appears and **saving is disabled** so the
  original is never overwritten with only its beginning. `[buffer full]`
  appears when typing fills the buffer. Split big texts into several files.
  Very long single lines (tens of KB without a newline) are slow.
- No save-as, no system clipboard, left Shift only, no F-keys.
- The terminal build lacks the graphical extras (find, replace, go to line,
  selection, mouse, table of contents, themes).

## Tests

`make test` runs the terminal tests (pseudo-terminal driven), a memory-map
check and the graphical regression suite (no window needed: it replays keys
and mouse events in a scripted emulator and compares the saved files).

## Credits

Fonts: VGA 8x16 (Linux console font `Uni2-VGA16`), Cream 10x16 (this
project), cream and cream12 (Hundred Rabbits, `left`; MIT, see
`fonts/LICENSE-left-MIT.txt`). Design notes: [REFERENCE.md](REFERENCE.md),
[PIEGES.md](PIEGES.md), [ARCHITECTURE.md](ARCHITECTURE.md).
