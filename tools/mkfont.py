#!/usr/bin/env python3
"""Builds fonts/cream-latin1.uf2 from fonts/cream12.uf2 (the proportional 16x16
font of the `left` editor, with real Latin-1 letters; the older ASCII-only
fonts/cream.uf2 is used if it is missing) by composing the accented
Latin-1 letters and a few typographic signs on top of its glyphs.

Format (uxn UF2): 256 width bytes, then 256 glyphs of 32 bytes. A glyph is
four 8x8 tiles in the order top-left, bottom-left, top-right, bottom-right.
The code space is the one of writhdeck.tal: ASCII 0x20-0x7e, Latin-1
0xa0-0xff, and 0x80-0x88 = ' ... - -- " " oe OE euro.

Geometry of cream: capitals occupy rows 3-11, x-height rows 5-11, descenders
rows 12-14. usage: mkfont.py [out.uf2] [preview.png]"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "fonts" / "cream12.uf2"      # cream as shipped with the recent `left` (MIT), real Latin-1 letters
if not SRC.exists():
    SRC = HERE / "fonts" / "cream.uf2"          # older ASCII-only cream: accents are composed below
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "fonts" / "cream-latin1.uf2"
PSF = HERE / "fonts" / "Cream16x10.psf"
BANK = HERE / "fonts" / "fonts.bank"

src = SRC.read_bytes()
W = bytearray(256)
G = [[0] * 16 for _ in range(256)]          # 16 rows of 16 bits, bit 15 = leftmost


def load(c):
    g = src[256 + c * 32: 256 + c * 32 + 32]
    rows = [0] * 16
    for t, (tx, ty) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        for r in range(8):
            rows[ty * 8 + r] |= g[t * 8 + r] << (8 if tx == 0 else 0)
    return rows


def store(c, rows, w):
    W[c] = w
    G[c] = list(rows)


for c in range(0x20, 0x7f):
    store(c, load(c), src[c])

A = lambda c: (list(G[ord(c)]), W[ord(c)])      # (rows, width) of an ASCII glyph


def shape(*lines):
    rows = []
    for ln in lines:
        v = 0
        for i, ch in enumerate(ln):
            if ch == '#':
                v |= 0x8000 >> i
        rows.append(v)
    return rows, max(len(l) for l in lines)


MARKS = {
    'acute': shape('..#', '.#.'), 'grave': shape('#..', '.#.'),
    'circ': shape('.#.', '#.#'), 'diaer': shape('#.#'),
    'tilde': shape('.#.#', '#.#.'), 'ring': shape('.#.', '#.#', '.#.'),
}


def put(rows, w, mark, y, xoff=0):
    mrows, mw = MARKS[mark]
    x = max(0, (w - mw) // 2) + xoff
    out = list(rows)
    for i, mr in enumerate(mrows):
        if 0 <= y + i < 16:
            out[y + i] |= mr >> x
    return out


def accent(base, mark, upper=None):
    rows, w = A(base)
    if upper is None:
        upper = base.isupper()
    if base in 'ij':                          # drop the dot
        rows[3] = 0
    if mark == 'diaer':
        y = 1 if upper else 3
    elif mark == 'ring':
        y = 0 if upper else 1
    else:
        y = 0 if upper else 2
    return put(rows, w, mark, y), w


def cedilla(base):
    rows, w = A(base)
    rows[12] |= 0x8000 >> (w // 2)
    rows[13] |= (0x8000 >> (w // 2 - 1)) | (0x8000 >> (w // 2))
    return rows, w


def slash(base):
    rows, w = A(base)
    top = 3 if base.isupper() else 5
    h = 11 - top
    for r in range(top, 12):
        x = round((w - 1) - (r - top) * (w - 1) / max(1, h))
        rows[r] |= 0x8000 >> x
    return rows, w


def join(a, b, overlap=1):
    (ra, wa), (rb, wb) = a, b
    sh = wa - overlap
    return [x | (y >> sh) for x, y in zip(ra, rb)], wa + wb - overlap


def flipv(c):
    rows, w = A(c)
    sub = rows[3:12]
    rows[3:12] = sub[::-1]
    return rows, w


COMPOSE = {
    'À': ('A', 'grave'), 'Á': ('A', 'acute'), 'Â': ('A', 'circ'), 'Ã': ('A', 'tilde'), 'Ä': ('A', 'diaer'), 'Å': ('A', 'ring'),
    'È': ('E', 'grave'), 'É': ('E', 'acute'), 'Ê': ('E', 'circ'), 'Ë': ('E', 'diaer'),
    'Ì': ('I', 'grave'), 'Í': ('I', 'acute'), 'Î': ('I', 'circ'), 'Ï': ('I', 'diaer'),
    'Ñ': ('N', 'tilde'), 'Ò': ('O', 'grave'), 'Ó': ('O', 'acute'), 'Ô': ('O', 'circ'), 'Õ': ('O', 'tilde'), 'Ö': ('O', 'diaer'),
    'Ù': ('U', 'grave'), 'Ú': ('U', 'acute'), 'Û': ('U', 'circ'), 'Ü': ('U', 'diaer'), 'Ý': ('Y', 'acute'),
    'à': ('a', 'grave'), 'á': ('a', 'acute'), 'â': ('a', 'circ'), 'ã': ('a', 'tilde'), 'ä': ('a', 'diaer'), 'å': ('a', 'ring'),
    'è': ('e', 'grave'), 'é': ('e', 'acute'), 'ê': ('e', 'circ'), 'ë': ('e', 'diaer'),
    'ì': ('i', 'grave'), 'í': ('i', 'acute'), 'î': ('i', 'circ'), 'ï': ('i', 'diaer'),
    'ñ': ('n', 'tilde'), 'ò': ('o', 'grave'), 'ó': ('o', 'acute'), 'ô': ('o', 'circ'), 'õ': ('o', 'tilde'), 'ö': ('o', 'diaer'),
    'ù': ('u', 'grave'), 'ú': ('u', 'acute'), 'û': ('u', 'circ'), 'ü': ('u', 'diaer'), 'ý': ('y', 'acute'), 'ÿ': ('y', 'diaer'),
}
for ch, (b, m) in COMPOSE.items():
    store(ord(ch), *accent(b, m))
store(0x9f, *accent('Y', 'diaer'))            # unused slot, kept for Y with diaeresis
store(ord('Ç'), *cedilla('C')); store(ord('ç'), *cedilla('c'))
store(ord('Ø'), *slash('O')); store(ord('ø'), *slash('o'))
store(ord('Æ'), *join(A('A'), A('E'))); store(ord('æ'), *join(A('a'), A('e')))
store(ord('ß'), *A('B'))
store(ord('Ð'), *A('D')); store(ord('ð'), *A('d')); store(ord('Þ'), *A('P')); store(ord('þ'), *A('p'))
store(0xa0, [0] * 16, W[0x20])                                   # nbsp
store(0xa1, *flipv('!')); store(0xbf, *flipv('?'))
store(0xa8, *( (put([0] * 16, 3, 'diaer', 3), 3) ))
store(0xb4, *( (put([0] * 16, 3, 'acute', 3), 3) ))
store(0xb0, *( (put([0] * 16, 3, 'ring', 3), 3) ))
store(0xb7, *( (lambda: ([0] * 5 + [0x4000 >> 0] + [0] * 10, 3))() ))
store(0xad, *A('-'))
store(0xab, *join(A('<'), A('<'), 2)); store(0xbb, *join(A('>'), A('>'), 2))
store(0xd7, *A('x')); store(0xf7, *A('/'))
store(0xb1, *A('+')); store(0xb5, *A('u')); store(0xa6, *A('|'))
store(0xaa, *A('a')); store(0xba, *A('o'))
store(0xb2, *A('2')); store(0xb3, *A('3')); store(0xb9, *A('1'))
store(0xa2, *A('c')); store(0xa3, *A('L')); store(0xa5, *A('Y')); store(0xa7, *A('S')); store(0xa9, *A('C'))
store(0xae, *A('R')); store(0xac, *A('-')); store(0xaf, *A('_')); store(0xb6, *A('P')); store(0xb8, *cedilla(' ')) if False else None
store(0xb8, [0] * 16, 3)
store(0xbc, *join(A('1'), A('4'), 0)); store(0xbd, *join(A('1'), A('2'), 0)); store(0xbe, *join(A('3'), A('4'), 0))
store(0xa4, *A('o'))
# extras 0x80-0x88
store(0x80, *A("'"))                                                    # right single quote
dots = A('.'); r, w = dots
three = [0] * 16
for i in range(3):
    three = [a | (b >> (i * 3)) for a, b in zip(three, r)]
store(0x81, three, 9)                                                   # ellipsis
store(0x82, *A('-')); store(0x83, *join(A('-'), A('-'), 0))               # en dash, em dash
store(0x84, *A('"')); store(0x85, *A('"'))
store(0x86, *join(A('o'), A('e'))); store(0x87, *join(A('O'), A('E')))   # oe OE
eur, ew = A('C')
eur[6] |= 0xF000 >> 0; eur[8] |= 0xF000 >> 0
store(0x88, eur, ew)                                                    # euro
# glyphs the source font really draws win over my compositions
# (cream12 has designed accented letters and ae/AE/ss/o-slash, not the
# punctuation and symbols of 0xa0-0xbf nor the typographic signs)
for c in range(0xa0, 0x100):
    r = load(c)
    ink = sum(bin(x).count('1') for x in r)
    if src[c] and ink and ink <= src[c] * 12 and SRC.name != "cream.uf2":
        store(c, r, src[c])
# unknown slots fall back to '?'
for c in list(range(0x89, 0xa0)) + [0x7f]:
    if W[c] == 0:
        W[c] = 0
for c in range(0xa0, 0x100):
    if W[c] == 0 and c != 0xa0:
        store(c, *A('?'))
W[0x20] = src[0x20]


def pack(rows):
    g = bytearray(32)
    for t, (tx, ty) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        for r in range(8):
            v = rows[ty * 8 + r]
            g[t * 8 + r] = (v >> 8) & 0xFF if tx == 0 else v & 0xFF
    return bytes(g)


blob = bytes(W) + b"".join(pack(G[c]) for c in range(256))
assert len(blob) == 256 + 256 * 32
OUT.write_bytes(blob)
print(f"wrote {OUT} ({len(blob)} bytes)")


def psf_blob(proportional=False):
    """fonts/Cream16x10.psf (PSF2, 10x16 monospace, unicode table) -> UF2 blob
    in the writhdeck code space (ASCII, 0x80-0x88 extras, Latin-1)."""
    import struct
    d = PSF.read_bytes()
    hs, flags, n, csz, h, w = struct.unpack('<IIIIII', d[8:32])
    assert d[:4] == b'\x72\xb5\x4a\x86' and h == 16 and w <= 16 and (flags & 1)
    rb = (w + 7) // 8
    glyph = [d[hs + i * csz: hs + (i + 1) * csz] for i in range(n)]
    t = d[hs + n * csz:]
    uni, i, g = {}, 0, 0
    while i < len(t) and g < n:
        if t[i] == 0xff:
            g += 1; i += 1; continue
        if t[i] == 0xfe:
            while t[i] != 0xff: i += 1
            continue
        b = t[i]; ln = 1 if b < 0x80 else 2 if b < 0xe0 else 3 if b < 0xf0 else 4
        uni.setdefault(ord(t[i:i + ln].decode('utf-8', 'replace')), g); i += ln
    extras = [0x2019, 0x2026, 0x2013, 0x2014, 0x201c, 0x201d, 0x153, 0x152, 0x20ac]
    ww = bytearray(256); gg = [[0] * 16 for _ in range(256)]
    def rows(gi):
        return [int.from_bytes(glyph[gi][y * rb:(y + 1) * rb].ljust(2, b'\0'), 'big') for y in range(16)]
    for c in range(0x20, 0x100):
        cp = c if (c < 0x7f or c >= 0xa0) else (extras[c - 0x80] if 0x80 <= c <= 0x88 else None)
        if cp is None or cp not in uni:
            continue
        ww[c] = w; gg[c] = rows(uni[cp])
    for c in range(0xa0, 0x100):                 # unmapped Latin-1 slots show '?'
        if ww[c] == 0:
            ww[c] = w; gg[c] = rows(uni[0x3f])
    if proportional:
        # trim each glyph to its ink: shift it flush left and set the advance
        # to ink width + 2 px of spacing (space: 5 px)
        for c in range(0x20, 0x100):
            if ww[c] == 0:
                continue
            ink = 0
            for r in gg[c]:
                ink |= r
            if ink == 0:
                ww[c] = 5; continue
            left = 15 - (ink.bit_length() - 1)           # first inked column
            right = 15 - ((ink & -ink).bit_length() - 1)  # last inked column
            gg[c] = [(r << left) & 0xFFFF for r in gg[c]]
            ww[c] = max(3, right - left + 1 + 2)
    return bytes(ww) + b"".join(pack(gg[c]) for c in range(256))


if PSF.exists():
    blob2 = psf_blob()
    blob3 = psf_blob(True)
    vga = (HERE / "fonts" / "vga16.bin").read_bytes()    # 224 glyphs of 16 bytes, codes 0x20-0xff
    BANK.write_bytes(blob2 + blob + blob3 + vga)   # 1 = Cream16x10 (monospace), 2 = proportional cream (left), 3 = Cream16x10 made proportional, 0x6300 = VGA 8x16
    print(f"wrote {BANK} ({len(blob2) + len(blob) + len(blob3) + len(vga)} bytes)")
else:
    BANK.write_bytes(blob + blob + blob + (HERE / "fonts" / "vga16.bin").read_bytes())

if len(sys.argv) > 2:
    from PIL import Image
    text = "Les élèves à côté œuvre Œ ÀÉÈÊÔÙÛÜÇ ç ï î ë ñ ö ü ÿ « » ’ … – — € ¿ ¡ ß ø æ Æ ÆÐ"
    cols = ["abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", text,
            "àâäçèéêëîïôöùûüÿ ÀÂÄÇÈÉÊËÎÏÔÖÙÛÜŸ"]
    def code(ch):
        m = {'’': 0x80, '…': 0x81, '–': 0x82, '—': 0x83, '“': 0x84, '”': 0x85, 'œ': 0x86, 'Œ': 0x87, '€': 0x88, 'Ÿ': 0x9f}
        return m.get(ch, ord(ch) if ord(ch) < 0x100 else 0x3f)
    img = Image.new('RGB', (900, 18 * len(cols) + 4), (255, 255, 255))
    for li, line in enumerate(cols):
        x = 4
        for ch in line:
            c = code(ch)
            for y, row in enumerate(G[c]):
                for b in range(16):
                    if row & (0x8000 >> b):
                        img.putpixel((x + b, 2 + li * 18 + y), (0, 0, 0))
            x += W[c] + 1 if W[c] else 0
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.save(sys.argv[2])
