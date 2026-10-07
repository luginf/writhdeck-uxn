# CLAUDE.md — writhdeck-uxn

Portage Uxntal (langage d'assemblage de la VM [uxn](https://100r.co/site/uxn.html))
de WrithDeck. Deux entrées produisant deux roms distincts, partageant
toute la logique d'édition via `src/core.tal` (voir "Architecture
console/graphique" plus bas) :
- `src/writhdeck-cli.tal` → `bin/writhdeck-cli.rom`, device **Console** (mode
  terminal, ANSI/VT100) — le portage original, testé automatiquement
  (`tests/`, pty).
- `src/writhdeck.tal` → `bin/writhdeck.rom`, device
  **Screen+Controller+Mouse** (mode graphique, `uxnemu`) — ajouté
  ensuite ; testé sans fenêtre (captures PNG, `tests/gfx_*`) et avec le
  vrai `uxnemu` par injection d'événements SDL.

Voir `README.md` pour le périmètre exact (touches supportées, limites
connues, instructions de build). Ce fichier documente les pièges
rencontrés en construisant ce portage et les conventions à connaître
avant d'y toucher, notamment pour reprendre le travail depuis une
autre machine.

> Ce fichier est volontairement court (il doit rester ouvrable en entier
> par nos propres ROM : le tampon d'édition fait 47 104 octets, au-delà un
> fichier est tronqué et la sauvegarde est refusée). Le détail est dans :
> - @docs/PIEGES.md : pièges Uxntal et méthodes de debug (#1 à #16) et le bug `min2`
> - @docs/ARCHITECTURE.md : architecture console/graphique et pièges #17 à #21
> Garder CHAQUE fichier de documentation sous ~40 000 octets (`make test` le vérifie).

## État du projet (octobre 2026) — LIRE EN PREMIER

### Livrables et commandes
- `make rom-cli` → `bin/writhdeck-cli.rom` (console, ~17 Ko) ; `make rom` →
  `bin/writhdeck.rom` (graphique) ; `make test` = tests console pty +
  `tests/check_layout.py` (aucun chevauchement code/données) + suite
  graphique ; `make layout` seul pour la carte mémoire.
- Lanceur unique `./writhdeck-uxn` (sans argument : aide en anglais) :
  `-c/-g` (console/graphique), `-n` brouillon, `-s LxH`, `-z 1|2|3`,
  `-l` clair, `-f vga|cream|prop|creamprop`. Il se place dans le
  répertoire du fichier (sandbox du device File), reconstruit le ROM si une
  source/police/outil est plus récent, met le tty en raw pour la console.
  Emulateur graphique par défaut `uxnemu` (jamais `uxn2`, voir pièges).
- Release GitHub : `tools/release.sh vX.Y.Z [--dry-run]` construit les deux ROM dans
  `dist/` (+ SHA256SUMS, notes extraites de `docs/CHANGELOG.md`) et publie avec `gh`
  (connecté au compte `luginf`) ou, à défaut, `$GH_TOKEN`. v0.1.0 est publiée (assets renommés après coup : `writhdeck.rom` = graphique, `writhdeck-cli.rom` = terminal ; le tag a ensuite été déplacé (force) sur le commit du renommage) :
  https://github.com/luginf/writhdeck-uxn/releases/tag/v0.1.0 . Pour la suivante :
  ajouter une section `## vX.Y.Z` à `docs/CHANGELOG.md`, commiter, taguer
  (`git tag -a`, `git push origin vX.Y.Z`), puis lancer le script (si la release existe déjà il remplace les fichiers et les notes).
- Le ROM graphique fait 0xff00 octets de code PUIS la banque de polices
  (`tools/append_bank.py`) : ~94 Ko au total, chargé par uxncli/uxnemu/uxn2.

### Fonctions (graphique ; la console a : édition, flèches, Ctrl+S/Q, Ctrl+Z/Y, titres/commentaires/marques colorés, retour à la ligne, confirmation de sortie)
Ctrl+S sauver ; Ctrl+Q quitter (confirmation si modifié, trace sur stderr) ;
Ctrl+Z/Y annuler/rétablir ; Ctrl+F recherche ; Ctrl+R remplacer (y/n/a) ;
Ctrl+G ligne ; Ctrl+T table des matières ; Ctrl+D clair/sombre ; Ctrl+P
police (nom affiché dans la barre) ; Ctrl+H aide ; Ctrl+A/C/X/V sélection
et presse-papiers interne (512 o) ; Maj+flèches (Maj GAUCHE seulement) ;
Ctrl+Haut/Bas pages ; Ctrl+Début ; Suppr ; souris (voir plus bas) ;
compteur de mots ; UTF-8 : déplacements/effacements par caractère.
La console n'a PAS (à porter si besoin) : recherche, remplacement, aller à
la ligne, sélection, souris, TOC, thème, aide.

### Architecture
`src/core.tal` (partagé) = tampon plat + édition + curseur + retour à la
ligne + .ini + titres/commentaires/marques + annuler/rétablir + chargement
/sauvegarde. Hooks définis par CHAQUE entrée : `entry-finish-boot`,
`entry-cw ( pos* -- )` (fixe `wd-cwn` octets et `wd-cww` largeur du
caractère), `entry-layout ( -- )` (gfx : `wd-text-width` x8 en pixels pour
les polices de la banque). `wrap-row-end` découpe PAR LARGEUR (colonnes en
console/VGA, pixels pour les polices Cream) ; règle conservée : un espace
n'est un point de coupure que s'il TIENT dans la largeur (sinon
`pty_uxn_wrap` échoue), au moins un caractère par rangée.

### Carte mémoire ACTUELLE (vérifier avec `make layout`)
Code entrée |0100- (graphique : fin `gfx-end` ~|2827 ; console : `con-end`
~|0997, tous deux visibles dans le .sym) ; code partagé `|2900` (finit
~|3860) ; données : ulog |3900, rlog |3d80 (0x480 chacun = 288
enregistrements de 4 o), clip |4200 (0x200), wd-arg2 |4400 (2e argv, 30 o),
gfx-inp |4440, gfx souris |4468-|4478, gfx-rep |44a0, gfx-pglyph |44d0,
gfx-prop/pok/fsel/fbase/fmsg |44f0-|44f5, gfx-pw |4500 (largeurs police en
banque), wd-fname |4600, wd-buf |4700 de 0xb800 = 47 104 octets (jusqu'à
|ff00). Chaque octet de code
gagné rend de la place au tampon : si le code grossit au-delà de la zone,
déplacer `core.tal` ET les données (le tampon rétrécit d'autant).
Historique du tampon : 48 640 o au départ → 43 264 o (annuler 2,3 Ko, TOC,
recherche/remplacement, sélection, polices ~1 Ko, souris ~0,7 Ko, etc.) →
47 104 o après avoir déplacé la police VGA dans la banque (-3,6 Ko de code).
Zero-page : gfx |0000-|002d, core |0030-|00bf (annuler |009c, marques |00aa,
wd-cwn/cww |00bc, wd-trunc |00bf), gfx |00ba-|00bb et |00c0-|00ff : QUASI PLEINE ;
mettre les nouvelles variables gfx en RAM (`;var LDA/STA`, zone |4468).

### Polices (graphique)
- 0 = VGA 8x16 (`Uni2-VGA16.psf` de Linux), 224 glyphes de 16 o
  (`fonts/vga16.bin`) à l'octet 0x6300 de la BANQUE 1 ; `draw-char` copie le
  glyphe (cpyl de 16 o, commande `gfx-xv`) dans `gfx-pglyph`. Codes 0x20-0xff +
  extras 0x80-0x88 (’ … – — “ ” œ Œ €). TOUTE police passe par la banque :
  sans expansion le ROM l'écrit sur stderr et quitte (`msg-nobank`).
- BANQUE 1 (`fonts/fonts.bank`, 3 blobs UF2 de 0x2100 octets : 256 largeurs
  puis 256 glyphes de 32 o = 4 tuiles 8x8 haut-gauche, bas-gauche,
  haut-droite, bas-droite) : 1 = Cream 10x16 (`fonts/Cream16x10.psf`, fourni
  par l'utilisateur, chasse fixe, tout le français) ; 2 = « Cream proportional
  (left) » = `fonts/cream12.uf2` (dépôt `left`, MIT, `fonts/LICENSE-left-MIT.txt`)
  + complément composé par `tools/mkfont.py` pour « » ¿ ¡ ’ … – — “ ” œ Œ € ;
  3 = Cream 10x16 rendue proportionnelle (encre mesurée +2 px, espace 5).
  `fonts/cream.uf2` (ancienne cream ASCII de uxn/projects/fonts) = repli.
- Accès : `gfx-set-font`/`gfx-fetch` copient un glyphe (cpyl via
  `System/expansion`, bloc de commande en RAM `gfx-xw`/`gfx-xg`, adresse
  source patchée aux octets +5/+6) ; largeurs recopiées une fois dans
  `gfx-pw`. Sans support d'expansion `gfx-pok`=0 et on reste en VGA.
- Choix au démarrage : jeton `fN` dans le 2e argv (`gfx-arg-font`).
- Police du dernier `left.rom` (itch.io) = « ank » 12x24 à empattements,
  chasse fixe, NON reprise (24 px de haut : il faudrait paramétrer la hauteur
  de rangée partout). Sources de `left` : le site sourcehut bloque les robots
  (curl/WebFetch : 418/502) mais `git clone https://git.sr.ht/~rabbits/left`
  fonctionne (branche `newfont` aussi) ; `etc/` contient ank_latin24.uf3,
  cream12.uf2, monaco12.uf2...

### Souris (graphique)
`uxnemu` MASQUE le pointeur système (SDL_ShowCursor(DISABLE)) : on dessine une
flèche 8x8 sur la couche AVANT (sprite 0x41, 0x42 bouton enfoncé, 0x40
efface), comme `left`. Clic gauche = curseur, glisser = sélection (ancre au
clic), clic milieu = mot (`gfx-select-word`), molette = 3 rangées (le
curseur peut alors sortir de l'écran : `gfx-draw-cursor` ne dessine pas hors
fenêtre). `gfx-pos-at` convertit pixel → position en rejouant `wrap-row-end`
puis `entry-cw`. Mode édition seulement. Pas d'auto-défilement pendant un
glisser, pas de double-clic.

### Fichier trop gros
`load-file` lit 0xb800 octets puis sonde 1 octet de plus (le device File
continue où il s'est arrêté) ; si ça répond : `wd-trunc`=1, `save-file`
REFUSE d'écrire (sinon la suite du fichier serait détruite), notice au
démarrage (mode gfx 9) + `[file too big, truncated: saving disabled]` dans la
barre ; `[buffer full]` quand le tampon est plein. Une seule ligne de dizaines
de Ko est très lente (retour à la ligne quadratique).

### Tests (méthode)
- Console : `tests/pty_uxn_*.py` via `tests/pty_harness.py` (pty + réponse DSR).
- Graphique SANS fenêtre : `tests/gfx_headless.py` compile une copie de
  `uxn2.c` (bug File corrigé, expansion OK) avec un mode scripté :
  `frame`, `key`, `ctrl X`, `btn 0x..`, `enter/bksp/esc/del`, `mouse X Y`,
  `mdown/mup/mmid`, `wheel N`, `shot f.png`. `tests/gfx_regress.py` rejoue
  des scénarios puis Ctrl+S et compare le FICHIER (moyen fiable de tester la
  logique). Cache du binaire : `/tmp/uxn2-headless` -- le SUPPRIMER quand on
  modifie le générateur (il n'est reconstruit que si uxn2.c est plus récent).
- Vrai `uxnemu` : `tests/uxnemu_shim.c` (LD_PRELOAD, `SDL_VIDEODRIVER=dummy
  SDL_RENDER_DRIVER=software`) injecte clavier/souris SDL ; il remplace aussi
  `SDL_WaitEvent`. Code retour 0 = le ROM a quitté, 124 = toujours là.
- NE JAMAIS piloter `uxnemu` avec xdotool sur le vrai écran de l'utilisateur :
  ses frappes atterrissent dans la fenêtre de test (déjà arrivé).
- Dans les scénarios gfx, finir par `esc` avant `ctrl s` quand un mode
  (recherche, remplacement) est actif, sinon la sauvegarde est interceptée.

### Pièges découverts depuis le piège #21
1. `uxnasm` compte les lambdas (`?{ }`) sur UN OCTET : > 256 dans l'assemblage
   => « Label duplicate: } » absurde. Tout `writhdeck.tal` utilise
   `?&kN ... &kN` (équivalent exact sans lambda) ; faire pareil pour tout
   nouveau bloc gfx. Le cœur partagé et la console utilisent encore `?{ }`.
2. Un vecteur (on-reset, on-first-frame, on-button, on-mouse…) finit par `BRK`,
   JAMAIS `JMP2r` (pile de retour vide : saut n'importe où).
3. Polarité : « exécuter le bloc quand X != 0 » = `X #00 EQU ?{` ;
   « quand X == 0 » = `X #00 EQU #00 EQU ?{` (et `X ?&label` saute quand X != 0).
   Inversée plusieurs fois (gfx-on-input, Retour arrière du cœur, etc.),
   toujours attrapée par un test scénario.
4. `uxnasm` ne détecte pas un chevauchement code/données (piège #13) : le
   journal d'annulation a une fois été placé dans le code partagé sans erreur.
5. Pas de `uxn2` pour les fichiers : bug amont `emu_deo(Uint8 addr, ...)`
   tronque l'adresse RAM de File/name et File/read ; touche aussi `left.rom`.
6. Un espace exactement à la limite de largeur n'est PAS un point de coupure
   (voir Architecture).
7. Les polices en banque : le ROM doit faire exactement 0xff00 octets avant les
   données (sinon la banque 1 est décalée) ; `append_bank.py` écrit `.size`
   (taille du code) pour `check_layout.py`.
8. Les tuiles de glyphe sont opaques : en police proportionnelle on EFFACE la
   rangée entière avant de dessiner (sinon des restes de l'image précédente).
9. Détection de l'émulateur : `Screen/width` vaut 0 sous `uxncli` et est non
   nul sous `uxnemu`/`uxn2` (vérifié).
10. Scroll molette sur une zone dont le curseur sort de l'écran : normal, le
    prochain mouvement/frappe rappelle `clamp-scroll`.

### Idées / à faire (par ordre de rentabilité)
1. **ROM unique console + graphique** (possible, NON fait). `uxncli` n'a pas de
   device Screen : lire `.Screen/width DEI2` au démarrage (0 → console, sinon
   graphique) puis brancher les vecteurs de l'un ou l'autre mode. Il faut :
   préfixer les labels en double des deux entrées (`quit`, `after-edit`,
   `after-move`, `status-*`, `draw-*`…), fusionner les zero-pages
   (console |0020-|002f chevauche gfx), rendre `entry-cw`/`entry-layout`/
   `entry-finish-boot` dynamiques (drapeau de mode), fusionner les deux
   `on-reset`. Coût estimé : ~2,3 Ko de code en plus (tampon -2 Ko) et un
   fichier ROM de 83 Ko pour tout le monde ; gain : un seul ROM, wrapper plus
   simple, `uxncli rom` ou `uxnemu rom` au choix. Les deux suites de tests
   existantes couvrent déjà les deux chemins.
2. (fait : VGA dans la banque) ; journaux d'annulation plus courts si besoin.
3. Porter à la console : recherche, remplacement, aller à la ligne, sélection.
4. Auto-défilement pendant un glisser, double-clic = mot, clic droit.
5. Police « ank » 12x24 de `left` : demande des rangées de hauteur variable.
6. Documents > 64 Ko par banques (README « Ideas / roadmap ») : positions 24
   bits + tampon paginé, réécriture de la plupart de `core.tal`.

## Pourquoi le mode console (contexte de la décision)

Question de départ : est-ce qu'un portage en uxn donnerait le support
UTF-8 ? Réponse vérifiée empiriquement avant de commencer : oui, et
gratuitement, à condition de rester en mode console. Le device Console
déplace des octets bruts sans jamais les décoder — c'est le terminal
hôte qui interprète l'UTF-8, exactement comme `writhdeck-asm`. Le mode
Screen (graphique) aurait au contraire demandé de dessiner les glyphes
soi-même (police bitmap, etc.). D'où le choix du mode console, validé
en assemblant et lançant `uxn/projects/examples/devices/console.read.tal`
avec un flux contenant accents français + emoji 4 octets : chaque octet
ressort inchangé.

## Rappel Uxntal : sémantique des runes (vérifiée en lisant `uxnasm.c`)

- `;label` — pousse une adresse absolue 2 octets (LIT2).
- `.label` — pousse une adresse zero-page 1 octet (LIT), utilisé avec
  LDZ/STZ et les ports de device.
- `,label` — cible de saut relatif courte (±127 octets), pour JMP/JCN.
- `!label` — saut relatif inconditionnel (JMI, portée 16 bits).
- `?label` / `?{ BLOC }` — saut relatif conditionnel (JCI, portée 16
  bits).
- `label` (sans préfixe) — **CALL** (JSI) : pousse l'adresse de retour,
  la routine appelée doit se terminer par `JMP2r`.
- `&label` — sous-label local, dont la portée est tout ce qui précède
  le label `@`-déclaré le plus proche jusqu'à son premier `/`.
- `%nom { ... }` — macro (substitution textuelle pure).
- `[ ... ]` — littéral de données brutes ; un token hexadécimal nu
  (`00`, `1b`...) écrit l'octet directement, `"mot` écrit les
  caractères ASCII de `mot` littéralement (**pas de sémantique de
  guillemet fermant** — `"," ` écrit DEUX octets, la virgule puis le
  guillemet, pas juste une virgule).

## Où regarder pour le contexte fonctionnel

- `README.md` (court) → `docs/MANUAL.md` (manuel d'utilisation, anglais) ;
  `docs/REFERENCE.md` : ancien README détaillé (périmètre exact, algorithmes, limites).
- `docs/PIEGES.md` : pièges Uxntal #1-#16 (polarité de `?{ }`, labels nus,
  EQU/EQU2, layout de System, méthode de debug...) -- à lire AVANT de toucher
  du nouveau code Uxntal.
- `docs/ARCHITECTURE.md` : architecture console/graphique, pièges #17-#21.
- `src/writhdeck-cli.tal` / `src/writhdeck.tal` : les deux entrées ;
  `src/core.tal` : logique partagée.
- `tests/` : `make test` (console pty + graphique sans fenêtre + carte mémoire).
- `../writhdeck-c` et `../writhdeck-asm` : ports de référence pour la logique
  métier ; `../../writhdeck/writhdeck.tcl` : l'original Tcl (fonctions de référence).
