# writhdeck-uxn

A distraction-free text editor for notes (plain text, txt2tags, markdown),
written in Uxntal for the [uxn](https://100r.co/site/uxn.html) virtual
machine: a port of [WrithDeck](https://github.com/luginf/writhdeck).

- **Terminal** build (`writhdeck-cli.rom`, run with `uxncli`) and **graphical**
  build (`writhdeck.rom`, run with `uxnemu`) with search/replace, undo,
  selection, mouse, table of contents, themes and four fonts.
- Full UTF-8 handling (accented French works everywhere).

```
make rom rom-cli            # needs uxnasm and python3
./writhdeck-uxn notes.txt      # graphical build
./writhdeck-uxn -c notes.txt   # terminal build
./writhdeck-uxn             # help
```

Releases ship the two ready-to-run roms. Read **[docs/MANUAL.md](docs/MANUAL.md)**
for keys and options; design notes are in `docs/`.
