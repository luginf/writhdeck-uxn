# Architecture console/graphique (writhdeck-uxn)

Suite de `CLAUDE.md` ; contient aussi les pièges #17 à #21 (historiques ; l'état actuel est dans `CLAUDE.md`, « État du projet »).

## Architecture console/graphique : `src/core.tal`

`src/core.tal` contient tout ce qui est indépendant du device de
sortie : tampon plat, édition (`insert-byte`/`backspace`/`shift-*`),
curseur/word-wrap (`move-*`/`wrap-*`/`visual-row-*`), marges/.ini
(`compute-layout`/`load-config`/`parse-ini-*`), classification des
titres (`is-heading`/`is-heading-t2t`), chargement/sauvegarde
(`load-file`/`save-file`, device `File`), et la capture d'argv
(`on-argv`, device `Console` -- partagée car `console_arguments()` est
utilisée par `uxnemu` ET `uxncli`, voir `uxn/src/uxnemu.c:488`). Inclus
en toute fin de `writhdeck.tal` ET `writhdeck-gfx.tal` via `~src/
core.tal` (même idiome que `left.tal`/`menu.tal`/`utils.tal` dans
l'écosystème uxn de référence). Chaque entrée définit son propre
`@entry-finish-boot` (appelé par `core-boot` une fois le fichier/.ini
chargés) pour démarrer sa boucle interactive et son premier rendu à sa
manière.

**Adresses fixes, choisies avec marge** (voir piège #13 : `uxnasm` ne
détecte PAS un chevauchement de `|ADDR` en arrière) : `|0020`-`|002f`
pour les variables propres à CHAQUE entrée (budget volontairement
large : la console y range `wd-esc-state`/`wd-sz-*`/`wd-dcount`, le
graphique `gfx-*`), `|0030` pour les variables PARTAGÉES (`core.tal`),
`|0100` pour le code propre à l'entrée, puis le code partagé
(`core.tal`) et les données : adresses ACTUELLES dans « État du projet »
(elles ont déjà bougé plusieurs fois). Après toute
modification significative de taille d'un des deux fichiers, vérifier
via `.rom.sym` (même technique qu'au piège #13) qu'aucun label
n'atterrit dans une plage réservée à l'autre section, POUR LES DEUX
ROMS -- un chevauchement dans `writhdeck-gfx.tal` ne casserait PAS les
tests automatisés (qui ne couvrent que la console), donc rien ne
l'attraperait autrement.

### 17. (OBSOLÈTE, historique) `writhdeck-gfx.tal` n'avait jamais été vérifié visuellement -- depuis : captures sans fenêtre, voir « État du projet »

`uxnemu` (device Screen) a besoin d'un vrai serveur d'affichage SDL ;
`uxnfb` (framebuffer Linux direct) a besoin d'un vrai `/dev/fb0` et de
périphériques d'entrée réels. Aucun des deux n'est pilotable en boîte
noire dans cet environnement (contrairement à `uxncli`, piloté via pty
pour toute la suite `tests/`) -- `make rom-gfx` assemble sans erreur et
`.rom.sym` confirme l'absence de chevauchement d'adresses, mais rien de
plus n'a jamais tourné à l'écran. Plusieurs bugs réels ont été trouvés
et corrigés a posteriori par relecture manuelle méticuleuse (rejeu
symbole par symbole de la polarité de chaque `?{ }`, voir piège #1) --
pas par test :
- Layout du device `System` copié tel quel depuis un fichier de
  référence DIFFÉRENT (`uxn/projects/examples/gui/terminal.tal`,
  version de spec Varvara différente) au lieu de reprendre le layout
  DÉJÀ VÉRIFIÉ de ce projet (`wst`/`rst`=0x04/0x05, `metadata`=0x06-07,
  `state`=0x0f, confirmé dans `uxn/src/devices/system.c`) -- aurait
  écrit `System/r`/`g`/`b` (thème) aux mauvais ports. Corrigé en
  repartant du layout vérifié et en confirmant `r`/`g`/`b`=0x08/0x0a/
  0x0c via `uxn/src/devices/screen.c:screen_palette` avant d'ajouter
  quoi que ce soit.
- `Controller/button DEI .wd-tmp1 STZ2` -- `DEI` (pas `DEI2`) ne pousse
  qu'UN octet, `STZ2` en dépile deux : même classe de bug que le piège
  #11 (résidu de pile silencieux). Corrigé en `STZ`.
- Trois inversions de polarité `?{ }` DANS DU CODE JAMAIS EXÉCUTÉ (donc
  aucun symptôme observable, juste une relecture symbole-par-symbole
  qui les a trouvées) : (1) `on-button` testait "key != 0" avec `NEQ`
  pour sauter vers le traitement des flèches quand `key==0` -- aurait
  rendu les flèches QUASIMENT INUTILISABLES (le saut n'arrivait que
  quand une touche de texte ET les flèches survenaient au même appel,
  jamais en pratique) ; (2) le test Ctrl-enfoncé utilisait aussi `NEQ`
  au lieu de `EQU`, ce qui aurait fait sauter Ctrl+Q/Ctrl+S/Ctrl+E
  quand Ctrl n'était PAS enfoncé -- taper un 'q'/'s'/'e' minuscule tout
  seul aurait quitté/sauvegardé/déplacé le curseur au lieu de s'insérer
  comme texte ; (3) `draw-str`/`draw-spaces` utilisaient `NEQ`/`NEQ2`
  pour détecter respectivement le NUL de fin de chaîne et le compteur
  à zéro -- aurait causé une boucle infinie lisant la mémoire au-delà
  du terminateur, ou l'inverse (ne jamais dessiner). Les trois corrigés
  en `EQU`/`EQU2`. Rejouer la méthode du piège #1 (calculer le flag
  NATUREL de la condition, PUIS ajouter `#00 EQU`) très explicitement,
  une ligne à la fois, plutôt que de faire confiance à l'intuition --
  c'est exactement ce qui a fini par débusquer ces trois-là.

**Comment appliquer :** avant de faire confiance à du code Uxntal
jamais exécuté, rejouer CHAQUE `?{ }` à la main (table de vérité
complète, pas juste "ça a l'air bon") et vérifier CHAQUE layout de
device fixe contre le fichier `.c` source correspondant dans
`uxn/src/devices/` -- ne jamais copier un layout depuis un AUTRE
fichier `.tal` de référence sans le revérifier, même si ce fichier
fonctionne (il peut cibler une version différente de la spec Varvara).

### 18. `writhdeck-gfx.tal` restait abonné à `Console/vector` après le boot -- tout octet de stdin rechargeait le fichier en boucle

Bug réel signalé par l'utilisateur : `uxn2 writhdeck-gfx.rom < fichier`
"ne chargeait rien". Cause, trouvée en lisant le VRAI émulateur utilisé
(`/temp/github/uxn-all/implementations/uxn2/uxn2.c`, PAS `uxnemu.c` --
vérifier avec `md5sum`/`ls -la` lequel des deux binaires installés est
réellement invoqué avant de chercher dans le mauvais source) :
`uxnemu`/`uxn2` font tourner un THREAD stdin permanent
(`stdin_handler`) qui lit le stdin RÉEL du processus octet par octet,
QUE ce soit un vrai terminal ou une redirection `< fichier`, et pousse
un événement `Console` (type `STD`) par octet -- inconditionnellement,
peu importe si le programme utilise `Console` pour autre chose que
l'argv. `entry-finish-boot` laissait `Console/vector` branché sur
`on-argv` (`core.tal`) après la capture initiale : chaque octet de
stdin retombait dans la branche de repli de `on-argv` (ni `ARG` ni
`EOA`) qui rappelle `core-boot` -- rechargement complet, remise à zéro
du curseur/scroll/dirty, nouveau rendu, UNE FOIS PAR OCTET. Le vrai
chemin de chargement de fichier est l'ARGV (`uxn2 rom fichier.txt`,
voir `on-argv`), jamais stdin -- mais même utilisé correctement, ce
ré-abonnement restait un bug latent (toute frappe tapée dans le
terminal qui a lancé `uxn2`, hors de la fenêtre SDL, aurait eu le même
effet). Corrigé en ajoutant `#0000 .Console/vector DEO2` dans
`entry-finish-boot`, juste après la lecture de `Screen/width`/`height`
-- `console_input()` côté C saute `uxn_eval` entièrement quand
`console_vector==0`, donc ça silence tout futur événement `Console`
proprement. **Ne pas répliquer ce "unbind" côté console
(`writhdeck.tal`)** : là, `Console/vector` DOIT rester branché en
permanence -- c'est le mécanisme même par lequel les frappes clavier
arrivent (`on-keypress`), pas un vestige du boot.

### 19. Accents dans un COMMENTAIRE `.tal` collés à une parenthèse : `uxnasm` lit `char` comme SIGNÉ, tout octet UTF-8 >=0x80 devient un "espace"

Bug réel rencontré en ajoutant le fallback d'accents latin-1 ci-dessous
(`gfx-utf8-decode`) : `make rom-gfx` échouait avec `Comment incomplete`
alors que chaque paire de parenthèses semblait équilibrée à l'œil.
Cause, trouvée en lisant `walkcomment()` dans `uxn/src/uxnasm.c` : la
variable qui reçoit chaque octet lu est déclarée `char c` (SIGNÉ sur ce
compilateur/plateforme) ; le test de fin de token est `c <= 0x20`. Tout
octet de poids >=0x80 -- donc CHAQUE octet d'un caractère UTF-8
multi-octets dans un commentaire (à, é, ç, Ð...) -- devient négatif une
fois stocké dans ce `char` signé, et `c <= 0x20` le traite alors comme
un ESPACE. Une parenthèse collée SANS espace à un caractère accentué
(ex. `(Ð`) se retrouve donc "détachée" par ce faux espace et comptée
comme un token `(`/`)` BARE isolé (le compteur de profondeur de
`walkcomment` ne réagit QU'AUX tokens bare, entourés d'espace des DEUX
côtés -- une parenthèse collée à du texte ASCII normal, elle,
n'affecte jamais le compteur). Ça a désynchronisé le compteur de
profondeur d'un commentaire qui semblait fermé, et l'assembleur a
scanné jusqu'à la fin du fichier en cherchant une fermeture qui
n'arriverait jamais. Diagnostiqué en écrivant un petit script Python
qui rejoue l'algorithme de `walkcomment` sur les OCTETS BRUTS du
fichier (pas le texte décodé Unicode) pour repérer exactement quelle
parenthèse était collée à quel octet >=0x80.

**Comment appliquer :** ne JAMAIS coller un caractère non-ASCII
directement contre une parenthèse dans un commentaire `.tal` (mettre
un espace, ou reformuler sans le caractère accentué juste à côté).
Plus généralement, éviter les accents dans les commentaires `.tal` de
ce projet quand une formulation ASCII équivalente existe -- le risque
ne vaut pas le gain esthétique, et ce piège est facile à réintroduire
sans y penser en écrivant en français.

### 20. `writhdeck-gfx.tal` lancé SANS argument fichier : écran noir pour toujours -- `core-boot` ne demarrait QUE via `on-argv`

Bug réel signalé par l'utilisateur juste après le correctif du piège
#18 ci-dessus : `uxn2 bin/writhdeck-gfx.rom` (sans le moindre argument
fichier, cas "brouillon vide") affichait un écran entièrement noir, en
permanence. Cause : `core-boot` (donc le tout premier `gfx-render`)
n'était déclenché QUE par la branche de repli de `on-argv`
(`core.tal`), elle-même déclenchée par `Console/type` valant `END`(4)
ou `STD`(1). Or, en lisant `main()` dans `uxn2.c`/`uxnemu.c` :
l'envoi de l'argv vers `Console` est un simple `for(; i < argc; i++)`
sur les arguments EXTRA du ROM -- si aucun n'a été passé, cette boucle
ne s'exécute PAS DU TOUT, et n'envoie donc RIEN, ni `ARG`, ni `EOA`, ni
même un `END`/`STD` de circonstance. Le seul autre expéditeur possible
d'un événement `Console` est le thread stdin (voir piège #18) -- qui
lit le VRAI stdin du PROCESSUS (le terminal qui a lancé `uxn2`, pas la
fenêtre SDL), et bloque indéfiniment tant que rien n'y est tapé/piped.
Résultat : sans argument fichier, ET sans activité sur le terminal de
lancement, `on-argv` n'était donc simplement jamais rappelé, et
`core-boot`/`entry-finish-boot`/`gfx-render` ne tournaient JAMAIS --
d'où l'écran noir permanent, symptôme bien plus sévère que le piège
#18 (qui ne touchait que le cas AVEC un fichier passé en argument).

Corrigé en ajoutant un second déclencheur GARANTI, indépendant de
`Console` : `Screen/vector`, que l'émulateur appelle inconditionnellement
à chaque frame une fois la fenêtre ouverte (`screen_update()` dans
`uxn2.c`/`uxnemu.c`), et l'ouverture de la fenêtre (`emu_init()`/
`emu_run()`) arrive TOUJOURS après l'envoi synchrone de l'argv (s'il y
en a un) dans `main()` -- vérifié en lisant l'ordre exact des appels.
`on-first-frame` (nouveau, cablé sur `Screen/vector` depuis `on-reset`)
appelle donc `core-boot` lui-même si `on-argv` ne l'a pas déjà fait
(chemin fichier), protégé par un drapeau `gfx-booted` mis à 1 dans
`entry-finish-boot` -- puis se désabonne immédiatement de
`Screen/vector`, inutile au-delà de ce tout premier appel.

**Comment appliquer :** pour tout code Uxntal qui doit démarrer une
séquence de boot au tout début du programme, ne JAMAIS dépendre d'un
seul vecteur/événement qui pourrait ne jamais arriver selon la façon
dont le ROM est lancé (ici : argument fichier présent ou non) --
identifier un événement GARANTI par la boucle principale de
l'émulateur (ici : le premier appel à `Screen/vector`, dès que la
fenêtre existe) comme filet de sécurité, protégé par un drapeau pour
rester idempotent si le déclencheur "normal" a déjà fait le travail.

### 21. Le mode graphique PEUT être testé ici (DISPLAY=:0 + xdotool + import) ; `uxn2` ne charge aucun fichier (bug émulateur)

Contrairement à ce que dit le piège #17, un affichage X existe :
`uxnemu bin/writhdeck-gfx.rom f.txt &`, puis `xdotool search --pid`,
`xdotool key/type`, `import -window ID out.png` et lecture du PNG.
Vérifié : chargement, saisie, flèches, Ctrl+S fonctionnent sous
`uxnemu` (fichier dans le cwd, voir piège #6). Sous `uxn2` (source
`/temp/github/uxn-all/implementations/uxn2/uxn2.c`), `emu_deo(Uint8
addr, ...)` écrase son paramètre 8 bits `addr` avec l'adresse RAM
16 bits de File/name -> nom lu en page 0 = vide, aucun fichier ne se
charge (bug amont, reproduit avec une mini-ROM). Aucun contournement
raisonnable côté ROM : utiliser `uxnemu`. Aussi corrigé : polarité de
`on-first-frame` (`NEQ #00 EQU ?{` relançait `core-boot` quand le boot
avait DÉJÀ eu lieu, et ne le lançait pas sinon).

(Tout ce qui a été ajouté ensuite -- fonctions, polices, souris, mémoire, tests -- est décrit dans la section « État du projet » en haut de ce fichier.)

