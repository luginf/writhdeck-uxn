#!/usr/bin/env python3
"""Pilote writhdeck-gfx.rom SANS fenetre ni focus : emulateur uxn2 compile
a partir de ses sources avec un mode scripte (pas de SDL video, touches
injectees directement dans le Controller, capture PPM -> PNG).

usage : gfx_headless.py ROM SCRIPT.txt [args du rom...]
script : une commande par ligne
  frame           un tour de Screen/vector
  key TEXTE       envoie chaque caractere via Controller/key
  ctrl X          Ctrl+X (bit Ctrl du bouton + lettre en clair)
  btn N           appui+relache d'un bouton (0x10 haut 0x20 bas 0x40 gauche 0x80 droite 0x08 home)
  enter / bksp / esc / del   Entree, Retour arriere, Echap, Suppr
  mouse X Y / mdown / mup / mmid (middle click) / wheel N   pointer position, left button, wheel (N>0 = up)
  shot out.png    capture
Les sources uxn2.c sont lues dans $UXN2_SRC (defaut /temp/github/uxn-all/
implementations/uxn2/uxn2.c). Le bug amont emu_deo(Uint8 addr) qui tronque
les adresses File est corrige dans la copie compilee ici."""
import os, subprocess, sys, tempfile

SRC = os.environ.get("UXN2_SRC", "/temp/github/uxn-all/implementations/uxn2/uxn2.c")
CACHE = os.path.join(tempfile.gettempdir(), "uxn2-headless")

HOOK = r'''
static void hl_shot(const char *path){
	FILE *f = fopen(path, "wb"); int i;
	fprintf(f, "P6\n%d %d\n255\n", screen_width, screen_height);
	for(i = 0; i < screen_width * screen_height; i++){
		unsigned c = screen_pixels[i];
		fputc((c >> 16) & 255, f); fputc((c >> 8) & 255, f); fputc(c & 255, f);
	}
	fclose(f);
}
static void hl_run(const char *script){
	FILE *f = fopen(script, "r"); char l[512]; char *p;
	while(f && fgets(l, sizeof l, f)){
		l[strcspn(l, "\n")] = 0;
		if(!strncmp(l, "frame", 5)) screen_update();
		else if(!strncmp(l, "key ", 4)) { for(p = l + 4; *p; p++) controller_key(*p); }
		else if(!strncmp(l, "ctrl ", 5)) { dev[0x82] |= 1; controller_key(l[5]); dev[0x82] &= ~1; }
		else if(!strncmp(l, "btn ", 4)) { int b = (int)strtol(l + 4, NULL, 0); controller_down(b); controller_up(b); }
		else if(!strncmp(l, "enter", 5)) controller_key(0x0d);
		else if(!strncmp(l, "bksp", 4)) controller_key(0x08);
		else if(!strncmp(l, "esc", 3)) controller_key(0x1b);
		else if(!strncmp(l, "del", 3)) controller_key(0x7f);
		else if(!strncmp(l, "mouse ", 6)) { int x, y; sscanf(l + 6, "%d %d", &x, &y); mouse_pos(x, y); }
		else if(!strncmp(l, "mdown", 5)) mouse_down(1);
		else if(!strncmp(l, "mmid", 4)) { mouse_down(2); mouse_up(2); }
		else if(!strncmp(l, "mup", 3)) mouse_up(1);
		else if(!strncmp(l, "wheel ", 6)) mouse_scroll(0, (int)strtol(l + 6, NULL, 0));
		else if(!strncmp(l, "shot ", 5)) { screen_update(); hl_shot(l + 5); }
		if(dev[0x0f]) break;
	}
}
'''

def build():
    os.makedirs(CACHE, exist_ok=True)
    exe = os.path.join(CACHE, "uxn2h")
    if os.path.exists(exe) and os.path.getmtime(exe) >= os.path.getmtime(SRC):
        return exe
    s = open(SRC).read()
    s = s.replace("emu_deo(Uint8 addr, Uint8 value)\n{\n\tdev[addr] = value;\n\tUint16 len, res;\n\tswitch(addr) {",
                  "emu_deo(Uint8 port, Uint8 value)\n{\n\tUint16 addr = port;\n\tdev[port] = value;\n\tUint16 len, res;\n\tswitch(port) {")
    assert "Uint16 addr = port;" in s, "emu_deo introuvable : source uxn2 differente"
    s = s.replace("void\nemu_resize(void)\n{", "void\nemu_resize(void)\n{\n\tif(getenv(\"UXN_SCRIPT\")) return;", 1) if "void\nemu_resize(void)\n{" in s else s.replace("emu_resize(void)\n{", "emu_resize(void)\n{\n\tif(getenv(\"UXN_SCRIPT\")) return;", 1)
    s = s.replace("emu_redraw(void)\n{", "emu_redraw(void)\n{\n\tif(getenv(\"UXN_SCRIPT\")) return;", 1)
    s = s.replace("int\nmain(int argc, char **argv)", HOOK + "\nint\nmain(int argc, char **argv)", 1)
    s = s.replace("\tif(!dev[0x0f]) {\n\t\tif(!emu_init())",
                  "\tif(getenv(\"UXN_SCRIPT\")) { hl_run(getenv(\"UXN_SCRIPT\")); return dev[0x0f] & 0x7f; }\n\tif(!dev[0x0f]) {\n\t\tif(!emu_init())", 1)
    c = os.path.join(CACHE, "uxn2h.c")
    open(c, "w").write(s)
    flags = subprocess.check_output(["sdl2-config", "--cflags", "--libs"], text=True).split()
    subprocess.check_call(["gcc", "-O1", "-w", "-o", exe, c] + flags)
    return exe

def main():
    rom, script, *args = sys.argv[1:]
    exe = build()
    env = dict(os.environ, UXN_SCRIPT=script, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    shots = [l.split(None, 1)[1].strip() for l in open(script) if l.startswith("shot ")]
    subprocess.run([exe, rom] + args, env=env, check=False, stdin=subprocess.DEVNULL, timeout=30)
    for png in shots:   # le script ecrit du PPM sous le nom demande : on convertit en place
        if os.path.exists(png):   # absent si le rom a quitte avant la capture
            subprocess.run(["convert", png, png], check=True)

if __name__ == "__main__":
    main()
