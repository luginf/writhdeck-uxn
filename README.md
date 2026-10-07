# writhdeck-uxn

A distraction-free text editor for notes (plain text, txt2tags, markdown),
written in Uxntal for the [uxn](https://100r.co/site/uxn.html) virtual
machine: a port of [WrithDeck](https://github.com/luginf/writhdeck).

- **Terminal** build (`writhdeck.rom`, run with `uxncli`) and **graphical**
  build (`writhdeck-gfx.rom`, run with `uxnemu`) with search/replace, undo,
  selection, mouse, table of contents, themes and four fonts.
- Full UTF-8 handling (accented French works everywhere).

```
make rom rom-gfx            # needs uxnasm and python3
./writhdeck-uxn -g notes.txt
./writhdeck-uxn             # help
```

Releases ship the two ready-to-run roms. Read **[docs/MANUAL.md](docs/MANUAL.md)**
for keys and options; design notes are in `docs/`.
