/* Injecte des evenements SDL scriptes dans le VRAI uxnemu, sans fenetre ni focus :
   gcc -shared -fPIC -o shim.so uxnemu_shim.c $(sdl2-config --cflags) -ldl
   SHIMQ=1 SDL_RENDER_DRIVER=software SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
     LD_PRELOAD=./shim.so SHIM="W,W,T:abc,W,D:400000e0,D:71,U:71,U:400000e0,W" uxnemu bin/writhdeck.rom f.txt
   SHIM : T:texte  D:sym_hex (KEYDOWN)  U:sym_hex (KEYUP)  W (attendre ~30 frames)
          M:x:y (mouvement souris)  P:n (bouton n enfonce)  R:n (relache).
   0x400000e0 = SDLK_LCTRL. Code de sortie 0 = le rom a quitte, 124 (timeout) = toujours la. */
#define _GNU_SOURCE
#include <SDL.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* scripted SDL events: env SHIM = comma list: T:text  D:sym(hex)  U:sym(hex)  W (wait one poll)
   D events set the mod state from SHIM_MODS tracking: LCTRL down => KMOD_LCTRL */
static int (*real_poll)(SDL_Event *);
static SDL_Keymod mods;
static char *script, *pos;
static int started, waitn;
SDL_Keymod SDL_GetModState(void){ return mods; }
int SDL_PollEvent(SDL_Event *e){
	if(!real_poll) real_poll = dlsym(RTLD_NEXT, "SDL_PollEvent");
	if(!script){ script = strdup(getenv("SHIM")); pos = script; }
	if(waitn > 0){ waitn--; return real_poll(e); }
	if(pos && *pos){
		char kind = *pos; char *end;
		memset(e, 0, sizeof *e);
		if(kind == 'T'){
			char *comma = strchr(pos, ','); int n = comma ? comma - pos - 2 : (int)strlen(pos + 2);
			e->type = SDL_TEXTINPUT; memcpy(e->text.text, pos + 2, n); e->text.text[n] = 0;
			pos = comma ? comma + 1 : pos + strlen(pos);
			return 1;
		} else if(kind == 'D' || kind == 'U'){
			long sym = strtol(pos + 2, &end, 16);
			e->type = kind == 'D' ? SDL_KEYDOWN : SDL_KEYUP; e->key.keysym.sym = sym;
			if(sym == SDLK_LCTRL) { if(kind == 'D') mods |= KMOD_LCTRL; else mods &= ~KMOD_LCTRL; }
			pos = (*end == ',') ? end + 1 : end; return 1;
		} else if(kind == 'M'){
			int x = (int)strtol(pos + 2, &end, 10), y = (int)strtol(end + 1, &end, 10);
			e->type = SDL_MOUSEMOTION; e->motion.x = x; e->motion.y = y;
			pos = (*end == ',') ? end + 1 : end; return 1;
		} else if(kind == 'P' || kind == 'R'){
			int b = (int)strtol(pos + 2, &end, 10);
			e->type = kind == 'P' ? SDL_MOUSEBUTTONDOWN : SDL_MOUSEBUTTONUP; e->button.button = b;
			pos = (*end == ',') ? end + 1 : end; return 1;
		} else if(kind == 'W'){ waitn = 30; pos = strchr(pos, ',') ? strchr(pos, ',') + 1 : pos + strlen(pos); return real_poll(e); }
	}
	if(!started){ started = 1; waitn = 90; fprintf(stderr, "SHIM: script done\n"); }
	return real_poll(e);
}
static int (*real_wait)(SDL_Event *);
int SDL_WaitEvent(SDL_Event *e){
	if(!real_wait) real_wait = dlsym(RTLD_NEXT, "SDL_WaitEvent");
	if(!script){ script = strdup(getenv("SHIM")); pos = script; }
	if(waitn > 0 || (pos && *pos)){ SDL_Delay(5); return e ? SDL_PollEvent(e) : 1; }
	return real_wait(e);
}
