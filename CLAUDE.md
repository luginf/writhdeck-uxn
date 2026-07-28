# CLAUDE.md — writhdeck-uxn

Portage Uxntal (langage d'assemblage de la VM [uxn](https://100r.co/site/uxn.html))
de WrithDeck, ciblant le device **Console** (mode terminal, pas le
device Screen/graphique) — voir `README.md` pour le périmètre exact
(touches supportées, limites connues, instructions de build). Ce
fichier documente les pièges rencontrés en construisant ce portage et
les conventions à connaître avant d'y toucher, notamment pour
reprendre le travail depuis une autre machine.

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
  (curseur en octets, pas de wrap, pas de tests automatisés, sandbox
  fichiers), instructions de build/run.
- `src/writhdeck.tal` : commentaire d'en-tête qui documente la règle
  de polarité `?{ }` et les décisions de portée du bootstrap.
- `../writhdeck-c` et `../writhdeck-asm` : ports de référence pour la
  logique métier (buffer, édition, rendu) en cas de doute sur un
  comportement souhaité au-delà de ce premier amorçage.
