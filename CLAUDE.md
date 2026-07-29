# CLAUDE.md — writhdeck-uxn

Portage Uxntal (langage d'assemblage de la VM [uxn](https://100r.co/site/uxn.html))
de WrithDeck. Deux entrées produisant deux roms distincts, partageant
toute la logique d'édition via `src/core.tal` (voir "Architecture
console/graphique" plus bas) :
- `src/writhdeck.tal` → `bin/writhdeck.rom`, device **Console** (mode
  terminal, ANSI/VT100) — le portage original, testé automatiquement
  (`tests/`, pty).
- `src/writhdeck-gfx.tal` → `bin/writhdeck-gfx.rom`, device
  **Screen+Controller** (mode graphique, `uxnemu`) — ajouté ensuite,
  **jamais vérifié visuellement** (voir piège #17).

Voir `README.md` pour le périmètre exact (touches supportées, limites
connues, instructions de build). Ce fichier documente les pièges
rencontrés en construisant ce portage et les conventions à connaître
avant d'y toucher, notamment pour reprendre le travail depuis une
autre machine.

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

## Pièges rencontrés (à vérifier avant de toucher du nouveau code)

### 1. `?{ BLOC }` s'exécute quand le flag est 0 (FAUX), PAS quand il est non-nul

Contre-intuitif si on lit ça comme un `if` classique. Vérifié par un
programme de test autonome (poussé sur la pile, comparé, sauté). Règle
mécanique appliquée dans tout le fichier : calculer l'opcode de
comparaison qui correspond littéralement à la condition en français/
anglais (EQU pour "==", NEQ pour "!=", LTH pour "<", GTH pour ">"),
puis **toujours** ajouter `#00 EQU` juste avant `?{` pour inverser.

**Exception documentée dans le code** : une boucle du genre "avancer
tant que compte >= seuil" (`clamp-scroll`) a besoin de la comparaison
BRUTE (non inversée) — inverser ici produit une boucle infinie
silencieuse (uxn n'a aucune protection contre les fautes, voir
ci-dessous), un des bugs les plus longs à isoler de tout ce portage.

### 2. Un label nu (sans préfixe) compile en CALL, pas en push d'adresse

**Le bug le plus répandu rencontré ici (163 occurrences corrigées d'un
coup).** Toute référence à une variable zero-page doit avoir le
préfixe `.` (`.wd-cursor` pour LDZ2/STZ2) — l'oublier fait que
l'assembleur traite l'adresse de la variable comme une cible de saut,
et l'exécution saute silencieusement dans de la donnée traitée comme
du code. Symptôme observé : l'exécution s'arrête net juste après un
`STZ`/`STZ2`, sans aucun message d'erreur d'`uxnasm` ni de `uxncli`.

**Comment appliquer :** si un nouveau fichier `.tal` "s'arrête" sans
raison après une écriture zero-page, grep immédiatement les références
à cette variable pour vérifier le préfixe `.` avant de chercher un bug
de logique ailleurs.

### 3. Le device `System` n'a PAS de champ `/vector`

Contrairement à `Console`/`File`. Layout réel (vérifié dans
`uxn/src/devices/system.c`) : `/wst`=0x04 (1o), `/rst`=0x05 (1o),
`/metadata`=0x06-07 (2o), 6 octets de bourrage (registres couleur
inutilisés ici), `/debug`=0x0e (1o), `/state`=0x0f (1o) — c'est
exactement cet octet que `uxncli.c` (`uxn.dev[0x0f]`) vérifie pour
savoir s'il faut s'arrêter. Déclaration correcte utilisée dans ce
fichier :

```
|04 @System/wst $1 &rst $1 &metadata $2 [ $6 ] &debug $1 &state $1
```

Supposer un `&vector $2` en tête (copier-coller le motif Console/File)
décale tous les champs suivants de 2 octets : l'écriture d'arrêt
atterrit silencieusement à la mauvaise adresse, Ctrl+Q semble "faire
quelque chose" (affiche la séquence de sortie d'alt-buffer) mais le
processus ne se termine jamais.

**Aussi :** l'arrêt doit passer par un `DEO` en mode octet
(`#80 .System/state DEO`), pas `DEO2` — pousser une short 2 octets
avec un `DEO` 1 octet laisse un octet parasite sur la pile et n'écrit
que 0x00 dans le registre, donc le bit d'arrêt n'est jamais réellement
posé.

### 4. uxn n'a AUCUNE protection contre les fautes — méthode de debug

`uxn.c` (`uxn_eval`) n'a aucune vérification de bornes sur les
pointeurs de pile (`Uint8` bruts) : un déséquilibre de pile cause une
corruption de données silencieuse (sauts/valeurs garbage), jamais un
crash ni un message d'erreur. Ni `uxnasm` ni `uxncli` ne signalent
rien de ce genre non plus.

**Ce qui a marché ici :** insérer des marqueurs temporaires
`#XX putc` (XX = octet ASCII distinct) ou `wd-print-dec` (dump la
valeur décimale d'une short zero-page) à chaque point de contrôle
suspecté, réassembler avec `uxnasm`, lancer via un harnais Python pty
(`pty.openpty()` + `tty.setraw(slave)` + `subprocess.Popen(...,
stdin=slave, stdout=slave, stderr=slave)` + polling `select`), et lire
jusqu'où l'exécution est allée et quelles valeurs intermédiaires sont
sorties. C'est ce qui a permis d'isoler le bug `min2` (voir plus bas)
: aucun symptôme autre que "le curseur Haut/Bas atterrit au mauvais
endroit", résolu en dumpant curseur/début-de-ligne/fin-de-ligne à
chaque étape de `move-down`.

**Comment appliquer :** face à un comportement uxn incorrect sans
sortie d'erreur, ne pas chercher une exception — poser des marqueurs
séquentiels `putc`/`wd-print-dec` encadrant chaque routine suspectée,
exactement comme un debug par printf dans un langage sans débogueur.

### 5. `uxncli` n'active pas le mode raw du terminal lui-même

Aucun appel `termios`/`tcsetattr` nulle part dans `uxn/src/` (confirmé
en lisant les sources, et par le TODO du README de `kibi` : "Make
emulator change to raw mode"). Sans ça, les touches tapées sont
échotées et bufferisées ligne par ligne au lieu d'arriver octet par
octet. Corrigé ici par le script `writhdeck` (wrapper shell, motif
copié de `apps/kibi/src/kibi`) qui appelle `stty` avant/après le
lancement du rom. Le harnais de test Python doit faire l'équivalent
via `tty.setraw(slave)` avant `subprocess.Popen`.

### 6. Sandbox fichiers d'`uxncli`

Le device File refuse silencieusement (`/success` = 0, pas d'erreur
visible dans le programme) d'ouvrir un chemin qu'il considère hors de
son "sandbox" — en pratique, lancer `writhdeck` depuis un répertoire
qui contient (ou est) celui du fichier ciblé. Un chemin absolu ailleurs
sur le système, ou un `..` s'échappant d'un cwd sans rapport, peut être
bloqué par `uxncli` avant même que le rom ne le voie. Voir aussi la
note "Sandbox" du `README.md`.

### 7. `DUP`/`POP` pour dupliquer un octet avant deux tests successifs : source de résidu de pile

Un idiome tentant pour "tester un octet contre deux valeurs" est
`DUP #20 EQU ?{ ... } DUP #09 EQU ?{ ... } POP` (dupliquer une fois,
consommer une copie par test, jeter l'original à la fin). Le risque :
si UN SEUL chemin (une branche prise, un retour anticipé au milieu du
bloc) oublie ce `POP` final, il reste un octet parasite sur la pile de
travail — exactement la classe de bug de la note System (`&vector`
fantôme) et de `min2` ci-dessus, sauf que celui-ci ne se voit même pas
à la relecture rapide du code, il faut tracer chaque branche à la main.

**Ce qui a été fait dans `is-heading`** (détection de titre Markdown,
ajoutée pour la coloration syntaxique) : éviter `DUP`/`POP` entièrement
— relire l'octet en mémoire (`.wd-tmpN LDZ2 ;wd-buf ADD2 LDA`) à CHAQUE
comparaison plutôt que de garder une copie sur la pile. Plus verbeux
(une lecture mémoire de plus par comparaison, coût négligeable à cette
échelle), mais chaque bloc `?{ }` devient trivialement équilibré :
rien n'est poussé sans être dépilé sur TOUS les chemins de CE bloc
précis, donc il n'y a plus besoin de tracer l'ensemble de la routine
à la main pour vérifier l'équilibre de la pile.

**Comment appliquer :** pour toute nouvelle routine qui teste un même
octet contre plusieurs valeurs, préférer relire depuis la mémoire
(zero-page ou `;wd-buf ADD2 LDA`) à chaque comparaison plutôt que
`DUP`/`POP` — surtout si la routine a plusieurs points de sortie
(`JMP2r`/`BRK` anticipés), où il est facile d'oublier le `POP` sur un
chemin de sortie précoce.

### 8. uxn/Varvara n'expose AUCUNE variable d'environnement au programme

Pas de `getenv`, pas d'accès a `$HOME` depuis Uxntal — confirmé en
cherchant dans `uxn/src/` : aucun device n'expose l'environnement du
process hote. Consequence concrete : le repli de
`writhdeck-c`/`writhdeck-asm` sur `$HOME/Documents/writhdeck/
writhdeck.ini` quand `writhd.ini` est absent du repertoire courant est
**structurellement impossible** a porter ici, pas juste "pas encore
fait". `load-config` (lecture de `writhd.ini` pour les marges) ne lit
QUE le repertoire courant, avec une note explicite dans son commentaire
d'en-tete et dans le README expliquant pourquoi le second chemin
n'existe pas dans ce port.

**Comment appliquer :** avant de porter une fonctionnalite C/asm qui
suppose une variable d'environnement, verifier d'abord si un device uxn
l'expose (chercher dans `uxn/src/devices/*.c`) plutot que de supposer
qu'un contournement existe — pour `$HOME` specifiquement, il n'y en a
aucun.

### 9. Reutiliser `wd-buf` comme tampon scratch AVANT le chargement du vrai fichier

`load-config` lit `writhd.ini` directement DANS `wd-buf` (le tampon de
~61 Ko du document) plutot que de reserver un tampon .ini dedie —
`wd-buf` n'a AUCUNE place libre pour un tampon separe, il s'etend deja
jusqu'a la toute fin des 64 Ko adressables (`|1100 @wd-buf $ef00` =
`0x1100+0xef00 = 0x10000` pile). Cette reutilisation est sure
UNIQUEMENT parce que `load-config` tourne dans `finish-boot` AVANT
`load-file` (qui ecrasera `wd-buf` avec le vrai contenu) et avant que
quoi que ce soit d'autre n'y touche. `.wd-buflen` est aussi
DELIBEREMENT repointee vers la taille du fichier `.ini` le temps du
parsing (pour reutiliser `line-end`/`buf-has-prefix` tels quels sans
leur passer une borne separee) — ce qui veut dire que `finish-boot`
DOIT explicitement remettre `.wd-buflen` a 0 pour le cas "brouillon
vide" juste apres `load-config` (avant cet ajout, ce cas s'appuyait
IMPLICITEMENT sur le fait que la RAM uxn demarre a zero et n'avait
jamais besoin d'une remise a zero explicite — ça a change des que
`load-config` a commence a l'ecrire).

**Comment appliquer :** toute nouvelle routine de boot qui reutilise
`wd-buf`/`wd-buflen` comme scratch temporaire doit imperativement
tourner AVANT `load-file`, et `finish-boot` doit explicitement remettre
`wd-buflen` dans l'etat attendu par la suite (0 pour un brouillon vide)
juste apres — ne JAMAIS compter sur l'etat "RAM demarre a zero" une
fois qu'une routine de boot a deja ecrit dans cette zone.

### 10. Exception documentée à la règle d'inversion : test "est un chiffre"

`parse-ini-value` (parseur `.ini`) teste si un octet est un chiffre
via `(octet-'0') <= 9` en arithmétique NON SIGNÉE (si `octet<'0'`, la
soustraction sous-flotte et redevient une valeur énorme, donc une
SEULE comparaison `GTH` couvre les deux bornes à la fois). Ceci
introduit une DEUXIÈME exception à la règle "toujours inverser avec
`#00 EQU` avant `?{ }`" (la première étant la boucle `count>=seuil` de
`clamp-scroll`, voir plus haut) : le bloc qui accumule le chiffre doit
s'exécuter sur le FAUX de "diff>9" (c'est un chiffre) — `GTH` brut,
SANS inversion, correspond déjà exactement à ce que `?{ }` attend (0
déclenche). L'inverser donnerait le résultat inverse. Vérifié par
double négation : `GTH #00 EQU #00 EQU` (invert-puis-invert) est
algébriquement identique à `GTH` seul quand l'entrée est un booléen
canonique 0/1 — ce qui confirme que "vouloir le bloc sur le FAUX d'une
comparaison" se traduit par AUCUNE inversion, et "vouloir le bloc sur
le VRAI" se traduit par UNE SEULE inversion, jamais deux. Voir le
commentaire directement au-dessus de `@parse-ini-value` dans le code.

**Comment appliquer :** avant d'ajouter une inversion "par réflexe",
se demander explicitement si le bloc doit s'exécuter sur le VRAI ou le
FAUX de la comparaison — ce n'est PAS toujours le VRAI (deux exceptions
déjà rencontrées dans ce fichier, toutes deux dans des boucles
numériques, pas dans des dispatches de touches/octets classiques où la
règle par défaut s'est toujours revérifiée correcte jusqu'ici).

### 11. `EQU`/`NEQ`/`GTH`/`LTH` (mode octet) contre `EQU2`/`NEQ2`/`GTH2`/`LTH2` (mode short) — piège le plus coûteux du word-wrap

**Confondre les deux a produit le bug le plus long à isoler de tout ce
portage** (ajout du word-wrap pour la colonne collante Haut/Bas et le
défilement en rangées visuelles) : comparer deux valeurs `$2`
(positions dans le tampon, presque tout ce que ce fichier manipule)
avec l'opcode SANS le `2` ne compare que les DEUX OCTETS DE POIDS FORT
restés en haut de pile après un dépilage partiel -- ni une erreur
d'assemblage, ni un crash, juste un résultat de comparaison
n'importe-quoi ET un résidu de pile (2 octets non consommés) qui
continue à circuler sous les valeurs suivantes, décalant TOUT calcul
ultérieur dans la même routine. Trouvé ici dans `move-up`
(`.wd-tmp1 LDZ2 .wd-tmp2 LDZ2 EQU` au lieu de `EQU2`) et
`visual-row-start` (même erreur, deux fois). Symptôme observé, très
trompeur : le programme ne plantait ni ne bouclait au sens strict --
il redevenait silencieusement inerte (plus aucune sortie) après un
Bas/Haut précis, uxncli restant bloqué dans un `read(0, ...)` comme si
de rien n'était, ce qui ressemblait exactement à "la touche suivante
n'arrive jamais" plutôt qu'à "une comparaison a mal tourné trois
fonctions plus haut".

**Comment appliquer :** avant de committer toute nouvelle comparaison,
vérifier explicitement si les DEUX operandes sont `$1` (octet, ex. un
octet lu via `LDA`/`LDZ`/`DEI`) ou `$2` (short, ex. une position dans
`wd-buf`, une largeur, un compteur) -- quasiment tout ce qui vient de
`LDZ2`/`LDA` sur une adresse construite avec `ADD2`/`;wd-buf` est un
short. Une astuce de relecture : grep `LDZ2.*LDZ2.*\bEQU\b` (ou NEQ/
GTH/LTH) sans le `2` dans tout le fichier -- si ça remonte quelque
chose, c'est presque toujours ce bug (voir aussi le piège #7 plus
haut, qui recommande de toujours relire l'octet en mémoire plutôt que
`DUP`/`POP` : ce conseil n'aide PAS ici, puisque le bug est un mauvais
CHOIX D'OPCODE, pas une histoire de résidu de pile lié à `DUP`).

### 12. Mauvais opcode de comparaison choisi (pas juste polarité inversée) : `visual-row-before`

Distinct du piège #11 (mode octet/short) ET des exceptions de polarité
(#10, `clamp-scroll`) : `visual-row-before` utilisait `NEQ2` pour
tester "row-start est-il tout au début du document ?" alors que la
condition voulue est littéralement "line_start == 0" -- `NEQ2` teste
l'INVERSE de ce qui était réellement voulu, pas juste la bonne
comparaison mal polarisée. Trouvé en traçant Haut apres Bas x4 sur un
document a deux lignes : le curseur revenait immediatement lá où il
était au lieu de reculer d'une rangée. Corrigé en `EQU2`.

**Comment appliquer :** relire chaque comparaison en la reformulant
d'abord en français/anglais SANS y penser en opcodes ("est-ce que X
vaut 0 ?" plutôt que "est-ce que je dois inverser ?"), PUIS choisir
l'opcode qui correspond mot-à-mot à cette phrase (EQU pour "vaut",
NEQ pour "ne vaut pas") avant d'appliquer la règle d'inversion du
piège #1 -- l'ordre compte : choisir le bon opcode d'abord, l'inverser
ensuite, jamais les deux en même temps de tête.

### 13. `|1000`/`|1100` (bootstrap initial) étaient des adresses codées en dur, jamais revérifiées à mesure que le fichier grossissait

`uxnasm` ne détecte PAS et ne signale RIEN quand une directive `|ADDR`
rembobine le curseur d'assemblage EN ARRIÈRE par rapport à ce qui a
déjà été écrit plus loin -- elle se contente de repositionner le
curseur, silencieusement, laissant la réservation suivante (`$N`)
écraser/chevaucher tout ce qui avait déjà été assemblé dans cette
plage. Rencontré ici : le word-wrap + les marges + le parseur `.ini`
ont fait grossir le code au-delà de `0x1000` (`|1000 @wd-fname $100`),
si bien qu'`ini-filename`/`ini-section-editor`/`wd-meta` atterrissaient
À L'INTÉRIEUR de l'espace réservé à `wd-fname`, corrompant leur
contenu -- symptôme observé : blocage silencieux au tout premier
Ctrl+Q après ouverture d'un brouillon vide, qui n'avait EN RÉALITÉ
aucun rapport avec Ctrl+Q lui-même (juste la première chose lue depuis
de la mémoire déjà corrompue). Corrigé en repoussant `|1000`→`|1400`
et `|1100`→`|1500`, avec une marge confortable au-dessus de la taille
réellement utilisée à ce moment (~0x1052).

**Comment appliquer :** après tout ajout de code substantiel, vérifier
qu'aucun label ne chevauche `wd-fname`/`wd-buf` en inspectant le
fichier `.sym` généré par `uxnasm` (`python3 -c "..."` pour décoder les
paires adresse/nom, voir le format binaire simple : short big-endian
puis nom NUL-terminé) -- chercher spécifiquement si `wd-fname` apparaît
à l'adresse EXACTE déclarée par `|1400 @wd-fname` (actuellement) et si
un label de DONNÉES (`ini-*`, `wd-meta`) apparaît AVANT lui dans le
fichier, à une adresse strictement inférieure. Repousser `|1400`/
`|1500` avec une marge large (pas juste "assez") avant que ça ne
redevienne un problème.

### 14. Méthode : distinguer un vrai blocage d'un artefact de test AVANT de chasser un bug dans le code

En diagnostiquant le piège #11 ci-dessus, la toute première piste
explorée (mauvaise) était la corruption mémoire du piège #13 -- des
heures de traçage plus tard, `strace -f -o trace.txt uxncli ...` a
révélé que le "blocage" n'était parfois PAS un blocage réel : le
programme lisait bien le SEUL octet stdin envoyé par le test
(`read(0, "\21", 1024) = 1`, `\21` = octal = Ctrl+Q), le traitait
correctement, puis se retrouvait légitimement à attendre une DEUXIÈME
frappe que le script de test n'envoyait jamais (cas "aucun argv" :
`on-argv` consomme le tout premier octet stdin comme signal de fin de
boot, PAS comme une vraie frappe -- comportement préexistant,
documenté dans le commentaire d'`on-argv` lui-même, pas un bug
introduit ici). Confirmé en rejouant le MÊME test sur le dernier
commit connu-bon (`git stash` puis reconstruction) : il "bloquait"
IDENTIQUEMENT, prouvant que le code en cours n'y était pour rien.

**Comment appliquer :** face à un blocage apparent, AVANT de chasser
dans le nouveau code : (1) `strace -f -o trace.txt` le process bloqué,
chercher le dernier `read()`/`write()` pour voir precisement ce qui
est attendu ; (2) `git stash` et retester le DERNIER COMMIT connu-bon
avec le MÊME script -- s'il bloque aussi, le bug (ou l'artefact) est
dans le harnais de test ou l'environnement, pas dans les changements en
cours ; (3) ne revenir au traçage `putc`/`wd-print-dec` dans le code
QUE si (2) prouve que le commit precedent fonctionnait.

### 15. Détection dynamique de la taille du terminal (DSR) : même inversion de polarité que le piège #10, sur un NOUVEAU test "est un chiffre"

`on-sizereply` (parse la réponse `ESC[row;colR` à la requête DSR
envoyée par `send-size-query`, idiome repris de `kibi.tal`) accumule
les chiffres de la rangée puis de la colonne. Première version, cassée
silencieusement : `DUP #30 SUB #09 GTH ?{ POP #00 .wd-sz-state STZ BRK
}` pour "si ce n'est PAS un chiffre, resynchroniser l'état machine à
0". Ça a exécuté le bloc de resync sur CHAQUE chiffre reçu au lieu de
l'inverse -- confusion entre les deux idiomes déjà en place dans
`parse-ini-value` (piège #10) : la boucle de skip y utilise `GTH #00
EQU ?{ avancer }` (règle standard : `?{ }` s'exécute sur la condition
NATURELLE une fois complémentée), alors que la boucle d'accumulation
utilise l'exception documentée `GTH ?{ accumuler }` SANS `#00 EQU`
(parce que `GTH` y vaut déjà 0 exactement quand c'est un chiffre,
polarité qui coïncide par chance avec ce que `?{ }` attend). En
écrivant le test "si non-chiffre, resynchroniser", j'ai copié la
mauvaise moitié de cette paire -- résultat : chaque chiffre de la
réponse DSR déclenchait un retour à l'état 0, qui ignore ensuite tout
octet qui n'est pas ESC, donc toute la réponse `ESC[row;colR` se
faisait avaler sans jamais atteindre `R` → le boot restait bloqué en
silence (aucune erreur, aucun rendu). Diagnostiqué en pilotant le rom
via un script pty qui répond bien au DSR (`ESC[24;80R`) et en observant
zéro octet de sortie après l'avoir envoyé. Corrigé en ajoutant le `#00
EQU` manquant aux DEUX endroits ("si non-chiffre, resync" pour la
rangée ET pour la colonne) -- suit la règle STANDARD du fichier, pas
l'exception.

**Comment appliquer :** avant d'écrire un nouveau test "est un chiffre"
ailleurs dans ce fichier, choisir consciemment laquelle des deux formes
de `parse-ini-value` copier -- `GTH #00 EQU ?{ }` (règle standard, à
utiliser pour "si CE N'EST PAS un chiffre") ou `GTH ?{ }` sans `#00
EQU` (exception, valide UNIQUEMENT pour "si c'EST un chiffre", et
seulement parce que `GTH` y a la polarité qui arrange). Ne jamais
copier l'un en pensant obtenir l'autre.

### 16. Un harnais de test pty doit répondre à la requête DSR, sinon le boot ne démarre jamais

Depuis l'ajout de la détection dynamique de taille (piège #15), le
boot envoie `ESC[999C ESC[999B ESC[6n` et attend la réponse `ESC[row;
colR` AVANT de basculer vers `on-keypress`/premier rendu -- comme
`kibi.tal`. Un vrai terminal répond automatiquement ; un pty piloté par
un script Python ne le fait PAS tout seul (rien n'interprète les
séquences ANSI côté maître du pty). Tous les scripts de test pty de ce
projet ont dû être mis à jour pour injecter la réponse eux-mêmes
(`os.write(master, f"\x1b[{rows};{cols}R".encode())`) après un court
délai suivant le démarrage -- sans ça, chaque test se bloque
indéfiniment au même endroit (voir piège #14 pour la méthode qui
distingue ce genre de blocage-par-conception d'un vrai bug). C'est
précisément pourquoi cette logique vit maintenant dans UN SEUL endroit
partagé, `tests/pty_harness.py::run()`, plutôt que dupliquée dans
chaque script `tests/pty_uxn_*.py` -- avant cette factorisation, le fix
ci-dessus a dû être appliqué identiquement dans six fichiers séparés.
Tout nouveau script de test doit passer par ce harnais, pas piloter
`uxncli` directement.

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
`|0100` pour le code propre à l'entrée, `|2000` pour le code partagé
(`core.tal`), `|4000`/`|4100` pour `wd-fname`/`wd-buf`. Après toute
modification significative de taille d'un des deux fichiers, vérifier
via `.rom.sym` (même technique qu'au piège #13) qu'aucun label
n'atterrit dans une plage réservée à l'autre section, POUR LES DEUX
ROMS -- un chevauchement dans `writhdeck-gfx.tal` ne casserait PAS les
tests automatisés (qui ne couvrent que la console), donc rien ne
l'attraperait autrement.

### 17. `writhdeck-gfx.tal` n'a JAMAIS été vérifié visuellement -- aucun affichage ni Xvfb dans cet environnement

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

## Bug de logique réel (pas un piège de langage) : `min2`

`move-up`/`move-down` utilisent `min2 ( a* b* -- min* )` pour clamper
la "colonne collante" du curseur à la fin de la ligne visée. Une
première version avait `NIP2`/`POP2` inversés (NIP2 garde le TOP et
jette le second ; POP2 jette le TOP) : `min2` renvoyait systématiquement
le MAX au lieu du MIN, donc Haut/Bas clampaient toujours le curseur au
bout de la ligne plutôt qu'à la colonne visée. Corrigé, avec le
commentaire explicatif directement dans le code à côté de `@min2` —
relire ce commentaire avant de retoucher cette routine, l'erreur est
facile à réintroduire en pensant "NIP2 = garder le premier, POP2 =
garder le second" sans revérifier la sémantique exacte des deux
opcodes.

## Où regarder pour le contexte fonctionnel

- `README.md` : périmètre exact, touches supportées, limites connues
  (curseur en octets, sandbox fichiers), instructions de build/run/test
  pour les DEUX entrées (console et graphique).
- `src/writhdeck.tal` : commentaire d'en-tête qui documente la règle
  de polarité `?{ }` et les décisions de portée du bootstrap.
- `src/core.tal` : logique partagée console/graphique -- voir
  "Architecture console/graphique" plus haut.
- `src/writhdeck-gfx.tal` : entrée graphique, JAMAIS vérifiée
  visuellement (piège #17) -- toute modification doit être relue à la
  main aussi rigoureusement qu'écrite, pas juste "ça assemble".
- `tests/` : suite de régression pty (`make test`) -- COUVRE
  UNIQUEMENT LA CONSOLE (voir piège #17, `uxnemu`/`uxnfb` non
  pilotables en boîte noire ici). `tests/pty_harness.py` pour le
  harnais partagé (répond notamment à la requête DSR de taille de
  terminal, voir piège #16).
- `../writhdeck-c` et `../writhdeck-asm` : ports de référence pour la
  logique métier (buffer, édition, rendu) en cas de doute sur un
  comportement souhaité au-delà de ce premier amorçage.
