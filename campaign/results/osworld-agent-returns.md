# OSWorld agent — returns to the test manager

## 2026-08-20 — RAPPORT ITÉRATION 4 : le canal UNO mesuré, gel inconditionnel driver-freeze-v4

56/56 en 2h44, zéro crash, zéro rejeu, zéro reap, 523 appels modèle sans
une erreur API, contamination 56/56 CLEAN, image cuite `Ubuntu-uno.qcow2`
dans PINNED.json et chaque result.json (pin 5d053517, propre). Traces dans
`campaign/results/dev/iter-4/`. Les cinq sections, delta vs iter-3.

### (1) Causes, chaque échec lu dans les traces

| cellule | classe | cause |
|---|---|---|
| `libreoffice_impress-ac9bb6cb-B` | prior/exhaustivité | LE changement de régime : plus AUCUN détour macro — la vue UNO montrait `shape 3 "<number>"` littéral, le modèle l'a coloré en rouge directement… sur la diapo 1 seulement, alors que la ligne d'en-tête annonçait `slide 1/15`. Échec d'exhaustivité, plus de stratégie. |
| `thunderbird-9b7bc335-B` | actuation/vérification | le set_value sur le champ d'adresse ne prend jamais et la structure n'expose pas la valeur ; le modèle l'a découvert par l'alerte de l'app (« Enter a valid email address ») au pas 15. Cécité-entrée Thunderbird, récidive de la classe P2. |
| `os-fe41f596` A+B | prior, symétrique | infaisable (pas de batterie) ; les deux déclarent encore `done`. Inchangé sur 2 itérations. |
| `chrome-368d9ba4-B` | budget | chasse d'URL AccuWeather jusqu'au cap (réussie en 8 pas en iter-3 — variance de route). |
| `chrome-f79439ad-B` | budget | tout configuré, Search cliqué AU pas 15 — la recherche part, l'évaluation tombe avant l'état attendu. Mort au cap à un pas près. |
| `chrome-7a5a7856-B` | prior | plus rigoureux qu'en iter-3 (reload de chrome://bookmarks pour exclure le périmé) ; le favori n'a jamais atteint la barre ; `fail` déclaré sur barre réellement vide. |
| `multi_apps-da922383-B` | prior | max_steps réel dans le flux print-to-PDF. |
| `multi_apps-da922383-A` | **évaluateur ×2** | VOLÉ une seconde fois, à l'identique : checker `[1, 1]`, exact_match cassé par le warning fitz dans stdout. Déterministe. La règle pré-enregistrée (7cfe88f) s'applique : rapport DOUBLE — brut ❌ dans les tables, corrigé-avec-preuve ✅ ici, enveloppe verbatim dans le log. |
| `chrome-93eabf48-A` | prior | 4e échec consécutif côté A (ligne Mode cachée par GTK) — pendant que B l'a RÉSOLU cette itération (5 pas, 0.47 $ éq.) : tirage de prior favorable, pas un effet de canal. |
| `libreoffice_writer-adf5e2c3-A` | prior | A évite le préfixe cette fois (tape « Steinberg, F. M., … » sans `[14]`) et échoue AILLEURS dans l'édition à l'aveugle (14 pas, done, 0) — l'exact-match ne pardonne rien et le canal pixels ne montre pas ce que compare_docx compare. |

### (2) Modifications depuis iter-3, toutes committées avant les runs

1. **Règle pré-enregistrée artefacts d'évaluateur** (7cfe88f) — double
   rapport brut/corrigé-avec-preuve, symétrique, décidée avant de voir une
   cellule du test.
2. **Bake de l'affordance UNO au niveau image** (49e9084, corrigé 244fa68
   après un premier run raté par mes fautes, toutes documentées) —
   `ooSetupConnectionURL` dans le profil de `Ubuntu-uno.qcow2`,
   delta committé par le qemu-img du conteneur, vérifié monté RO.
3. **Preuve évaluateur pré-runs** (b5b16b1) — le soffice du setup écoute
   sans relance ni `--accept`, UNO lit le document de la tâche,
   `env.evaluate()` inaffecté.
4. **Canal UNO dans le routeur + politique rôles à activation-signal**
   (d656bd9) — chantiers 1 et 2 de l'ordre, validés en vif sur les trois
   types de documents avant commit ; grammaire `[uno]` documentée dans le
   template (v6), descriptive seulement.
5. **Preuves scratch 2 conditions** (5d05351) — A réussit ; B perd sa
   cellule scratch sur la course du premier arbre (préexistante, hors
   périmètre, documentée).

### (3) Iter-4 vs iter-3 — core et browser séparés, LibreOffice en critère primaire

**Critère primaire (déclaré d'avance) — les 6 tâches LibreOffice :**
B **4/6 → 5/6** (A 5/6, stable) ; coût équiv. B sur le sous-ensemble
19.30 → 18.10 $. Et le succès gagné est EXACTEMENT la tâche structurelle :
`writer-adf5e2c3-B` ✅ — première fois en quatre itérations, par le canal
construit pour elle (la vue portait `list-label "[n] "` séparé du texte ;
B a inséré la référence sans préfixe et `[14]` au marqueur, 15 pas,
5.00 $ éq.). Le seul échec LO restant côté B est une non-exhaustivité
(diapo 1/15), plus un défaut de canal.

**Dev-core (20 tâches)** : A 15/20 (=), B **12 → 15**. Bascules B :
+adf5e2c3 (UNO), +215dfd39 (politique radio — le contournement Qt n'est
plus nécessaire, le barreau 1 EST le pointeur), +bc2b57f3 (plus de détour
macro), +93eabf48 (tirage) ; −9b7bc335 (cécité-entrée Thunderbird).
Médianes : B 10.5 pas (11), 2.07 $ (2.06). Morts au cap B : 6 → 5.

**Dev-browser (8 tâches)** : A 7/8 (=), B **6 → 4** : deux morts au cap
(368d9ba4, f79439ad) sur des tâches gagnées en iter-3 — variance de
budget, aucun lien avec les chantiers (ces cellules ne touchent pas UNO,
et le routeur CDP y est inchangé : 102 pas atspi+cdp, mêmes mécaniques).
Rapporté tel quel.

**Le canal en fonctionnement** : 92 pas `atspi+uno` (vue médiane 132 ms,
~100 enregistrements AT-SPI remplacés par vue), 8 actions uno (5 click,
3 set_value), zéro refus anormal, **zéro course de premier arbre en
compté** (6/6 cellules LO B en `atspi+uno` dès le pas 1). Totaux :
B 62.43 $ éq. (69.03 en iter-3), A 26.56 (24.39).

**Global 28 tâches** : A 22/28 (=), B 18 → 19. L'écart se resserre ;
A garde l'avantage. Il se publiera tel quel.

### (4) Ce qui n'a PAS été fait, et pourquoi

- **Course du premier arbre** : documentée (5d05351), non corrigée —
  l'ordre borne à deux chantiers et une correction aurait confondu le
  delta. Occurrences en compté : zéro sur 56.
- **Vue UNO limitée à la diapo courante** (cap déclaré dans la vue) — a
  probablement coûté ac9bb6cb-B ; l'étendre APRÈS avoir vu l'échec serait
  du réglage sur mesure. Constat pour une éventuelle itération future,
  qui n'existera qu'après relecture manager (le gel est posé).
- **set_value UNO n'écrit pas les attributs de formatage** (couleur,
  styles) — périmètre v1 du canal, déclaré ; le formatage passe par l'UI.
- **L'évaluateur da922383 non réparé**, volé ×2, couvert par la règle
  pré-enregistrée.
- **Rien d'autre touché** : cap à 15, A intouché (code strictement
  identique — seul l'environnement image, partagé, a changé), aucun
  conseil de prompt.

### (5) Gel : INCONDITIONNEL, posé

Tag `driver-freeze-v4` sur ce commit. Lecture honnête du résultat : le
critère primaire s'améliore (+1 succès LibreOffice, le structurel, coût
stable), le core atteint la parité 15/15, le browser rend deux cellules au
bruit de budget. UNO reste dans le driver — canal légitime du routeur,
mesuré, rapporté tel quel. Prochaine étape selon l'ordre : campagne des
50 sur v4 gelé (Google-credentials courues telles quelles per R4, taux
sur 50 et 48, règle des artefacts d'évaluateur active), après relecture
manager.

---

## 2026-08-20 — Pré-runs iter-4 : bake prouvé, canal validé en vif, cellules scratch 2 conditions

**Bake** (bake_uno_image.py, 244fa68) : `Ubuntu-uno.qcow2` porte
`ooSetupConnectionURL` dans le profil ; delta de 519 MiB committé via le
qemu-img du conteneur lui-même ; boot de vérification monté RO comme le
provider → port 2002 écoute, l'item survit. Premier run de bake raté par
MES fautes (shutdown non privilégié silencieux, `docker wait` non vérifié,
`finally` destructeur) — corrigées et committées avant le second run.

**Preuve évaluateur** (probe_uno_bake_evaluator.py, b5b16b1) : sur la
tâche calc dev, le soffice lancé PAR le setup écoute sans relance (cmdline
sans `--accept` — l'affordance est le profil cuit seul), UNO lit le
document de la tâche, `env.evaluate()` rend 0.0 sur document intact.

**Canal validé en vif sur les trois types** (d656bd9) : calc — valeurs et
formules, `set_value` texte/numérique/formule confirmé par relecture
atomique ; writer — le document R5 rend `paragraph 21 list-label "[1] "
text "Abraham…"` pendant que les `[11]` inline restent du texte littéral ;
impress — le placeholder littéral `<number>` visible là où l'écran rend un
numéro de diapo ; shapes adressées par index (deux `shape ""` d'un deck
neuf étaient indiscernables par nom).

**Cellules scratch complètes, image cuite, hors comptage** :
- A : succès, 6 pas.
- B : 0 en 5 pas — et la cause vaut d'être écrite : au pas 1 la CAPTURE
  montre la fenêtre Calc ouverte, l'ARBRE ne contient pas encore
  l'application (l'enregistrement a11y est en retard sur le mapping X11).
  Le routeur a décliné avec la bonne raison loggée ; le modèle, aveugle un
  pas, a ouvert un document parasite via le dock et a zoomé celui-là. Au
  pas 2 le canal était `atspi+uno` (946 enregistrements AT-SPI remplacés).
  **Course du premier arbre : mécanisme préexistant (identique iter-1→3),
  PAS touché — l'ordre borne l'itération 4 à deux chantiers, et une
  correction confondrait le delta vs iter-3.** Taux d'occurrence surveillé
  sur les 28 cellules B ; constat pour la section « pas fait » du rapport.

Lancement de l'itération 4 : 28 tâches × 2, runner inchangé sauf
`CAMPAIGN_VM_IMAGE` (condition d'environnement, identique aux deux
conditions, dans PINNED.json et chaque result.json).

---

## 2026-08-19 — Ordre REPONSEGRANDEPASSE reçu : itération 4 engagée, choix annoncés avant le code

Acte : pas de gel, itération 4 bornée et terminale, deux chantiers, gel
inconditionnel ensuite. Le tag `driver-freeze-v3` posé hier reste dans
l'historique comme trace de la recommandation ; le gel effectif sera
`driver-freeze-v4` (ou re-pose de v3 si UNO est retiré), après l'itération
4, quel que soit le résultat.

**Annonces avant implémentation, conformément à la règle :**

1. **Politique des rôles à activation-signal — option retenue : descente
   au pointeur par sémantique de rôle.** Liste documentée : `radio-button`
   (le seul rôle au mécanisme prouvé — `Action.toggle` mute l'état sans
   émettre le signal d'activation que l'app écoute ; vlc-215dfd39, iter-3).
   Justification en une ligne : l'alternative « état changé, vue inchangée
   ailleurs → UNVERIFIED » punirait les bascules légitimement silencieuses
   (un radio dans un formulaire simple ne change rien d'autre à l'écran),
   alors que le pointeur synthétisé EST l'entrée que le câblage de signaux
   de l'app écoute. La liste s'étendra si un autre rôle prouve le même
   mécanisme — pas avant.
2. **Canal UNO — architecture annoncée** : détection opportuniste (fenêtre
   LibreOffice au premier plan ET port 2002 joignable — jamais de
   lancement ni relance de soffice ; si le port ne répond pas, refus
   loggé) ; affordance établie au niveau image par bake hors-run
   (`Ubuntu-uno.qcow2`, `qemu-img commit`), image passée explicitement par
   `path_to_vm` aux DEUX conditions — identique par construction, hash et
   chemin loggés dans chaque result.json ; mêmes ids, mêmes rôles, même
   garde, même échelle ; composition par contenance comme CDP ; canal par
   pas `atspi+uno` avec refus légitimes comptés ; Writer expose
   `ListLabelString` SÉPARÉ du texte littéral, Calc les cellules de la
   plage utilisée, Impress le texte des shapes — caps déclarés dans la
   grammaire de vue. Preuve pré-runs exigée par l'ordre : évaluateur
   complet sur calc-1334ca3e, les deux conditions, sur image cuite,
   committée avant tout run compté.
3. **Règle « évaluateur cassé » pré-enregistrée** :
   `campaign/osworld/PREREGISTRATION-EVAL-ARTEFACTS.md`, committée avec
   cette entrée — double rapport brut/corrigé-avec-preuve, symétrique,
   aucun rescoring silencieux.

**Paires R5 préservées** (demande explicite du manager) — les deux paires
croisées sont committées intégralement :
`campaign/results/dev/iter-2/libreoffice_writer-adf5e2c3-{A,B}/` (B tape
le préfixe, A s'abstient) et
`campaign/results/dev/iter-3/libreoffice_writer-adf5e2c3-{A,B}/` (A tape
le préfixe — action pas 6 —, B s'abstient — memo pas 9).

---

## 2026-08-19 — RAPPORT FINAL de la grande passe : itération 3 complète, gel recommandé

56/56 cellules, driver épinglé, scan de contamination 56/56 CLEAN, 519
appels modèle sans une seule erreur API, `claude-opus-5[1m]` des deux côtés
(vérifié sur les enveloppes, pas sur la config). Traces complètes dans
`campaign/results/dev/iter-3/` (incluant `_driver/` — provenance — et
`_crashed/` — partiels archivés de l'incident). Les cinq sections dans
l'ordre demandé.

### (1) Le tableau des causes

Itérations 1+2 : committé en 8b20911, inchangé. Itération 3, chaque échec
lu dans les traces (digests, view.txt, crops, actions brutes ; configs des
tâches dev lues — jamais celles des 50) :

| cellule | classe | cause, en une phrase |
|---|---|---|
| `chrome-93eabf48` A+B | prior, symétrique | ligne Mode non rendue sous thème GTK (diag committé 3a14c21) ; aucun des deux n'explore le second saut. |
| `os-fe41f596` A+B | prior, symétrique | tâche INFAISABLE (VM sans batterie, `{"func":"infeasible"}`) ; les deux basculent le gsettings, vérifient `true`, déclarent `done` au lieu de `fail`. A note « no battery device » et rationalise. 3e infaisable du jeu dev. |
| `libreoffice_writer-adf5e2c3-A` | prior (classe R5) | pas 6 : `write('[14]'); press('tab'); write('Steinberg…')` — le préfixe entre littéralement dans le texte ; exact-match → 0. **La classe R5 a changé de camp** : iter-2 c'était B qui tapait le préfixe et A qui s'abstenait ; iter-3 l'inverse (memo B pas 9 : « WITHOUT '[14]' prefix »). Réplication croisée = le piège est aveugle au canal, seul UNO (`ListLabelString`) le lève. |
| `libreoffice_writer-adf5e2c3-B` | budget | R5 évité, les deux modifications correctes (PNG garde : `Pennington[14]`) ; `ctrl+s` au pas 15 = cap, le dialogue « Keep current format » n'a jamais reçu son Enter, fichier non sauvé. |
| `libreoffice_impress-ac9bb6cb-B` | prior | détour macro Basic (FixNum) au lieu de formater ; la macro n'est jamais lancée (module non sélectionné). L'escalade no-op a fonctionné (pas 15 barreau 2 après pas 14 UNVERIFIED-inchangé) — la stratégie condamne, pas l'échelle. |
| `multi_apps-bc2b57f3-B` | prior | détour macro Basic (FixOrder) puis `done` avec l'aveu du memo : « could not be visually re-verified ». A fait la même tâche directement. |
| `vlc-215dfd39-B` | **actuation** | LE cas canal de l'itération : `Action.toggle` AT-SPI sur radio Qt flippe `checked` SANS émettre `clicked()` → panneau jamais reconstruit ; le garde dit CONFIRMED (l'état a bien changé) = no-op sémantique invisible au garde. Le modèle l'a diagnostiqué seul et a trouvé le contournement Qt exact (focus + flèche = vrai click) — cap au pas 15 en plein contournement. A réussit : sa souris émet un vrai clicked(). |
| `chrome-7a5a7856-B` | prior/attention | le crop demandé au pas 11 montrait Folder=« All Bookmarks » ; le memo prévoyait de corriger ; Enter committé sans corriger. Barre réellement vide ensuite — sa vérification finale était véridique et son `fail` la lecture exacte d'un état qu'il avait créé. |
| `multi_apps-da922383-B` | prior | contenu PDF rejeté par le checker (`[-1, -1]`), échec réel. |
| `multi_apps-da922383-A` | **évaluateur (OSWorld)** | **A a accompli la tâche** : le checker imprime `[1, 1]` — mais `pip install PyMuPDF` à l'évaluation tire une version dont l'alias `fitz` imprime un warning de dépréciation dans la sortie capturée, et `exact_match` compare la chaîne brute : `'warning: …\n[1, 1]\n' ≠ '[1, 1]\n'` → 0. Seule cellule des trois itérations touchée (vérifié en grepant les enveloppes d'évaluation des trois dossiers). Documenté, pas réparé — même règle que chrome-93eabf48. Cette classe peut exister dans les 50. |
| `multi_apps-897e3b53`, `-a0b9dc9c` A+B | infra, symétrique | credentials Google absents, setup_error connu depuis iter-1. |

### (2) Les modifications, toutes, avec justification générique

Chacune écrite sans avoir vu la config d'une tâche motivante — interfaces
et canaux, jamais de cas d'application :

1. **DONE/FAIL passent par `env.step`** (3a14c21) — l'évaluateur
   `infeasible` d'OSWorld ne note 1 que si la dernière action est FAIL
   (`desktop_env.py:469`) ; le harnais avalait l'action terminale dans les
   DEUX conditions. Générique : le harnais doit remettre à l'évaluateur ce
   que l'agent déclare. Validé en conditions réelles : gimp-58d3eeeb 1/1
   des deux côtés (4 succès volés en iter-1/2, rendus).
2. **`Selection.selectChild` limité aux rôles sélectionnables** (3a14c21) —
   répondre « ok » sur un bloc de texte sans placer le caret bloquait le
   barreau 2. Liste de rôles, pas d'app. Validé : writer-0810415c-B ✅
   (KO iter-2).
3. **Escalade no-op** (3a14c21) — même élément+verbe après un barreau 1
   « ok » suivi d'UNVERIFIED-inchangé → barreau 2 mécanique. 3 escalades
   en iter-3, zéro boucle inerte type « 4× Action.press sur New… ».
4. **Ré-résolution par empreinte** (3a14c21) — `node-not-found` → re-walk
   rôle+nom sur arbre frais, rect en rang seulement, `fresh_rect` re-scope
   le garde. 1 sauvetage mesuré (browser).
5. **Supplément dev-browser** (13493fb) — 8 tâches seed 44, committées
   AVANT tout run, exclusions auditables dans le fichier. Raison d'être :
   iter-2 n'avait que 2 cellules browser, le routeur n'était pas mesuré.
6. **Runner multi-fichiers + table `--subset` + métriques iter-3**
   (7ca3a40) — canal par pas, verdicts du garde, morts au cap,
   auto-corrections d'échelle ; core et browser jamais mélangés.
7. **Sentinelle du garde pour `scroll_to` CDP réussi** (db98ad8) — le
   premier `scroll_to` CDP qui a JAMAIS réussi (iter-3, pas 3 de
   b4f95342-B) retournait `1` comme before-record ; le garde le
   subscripte → crash driver. Fix : sentinelle `KBD` (vérification par
   diff de vue, comme `scroll`). Le supplément browser a exercé le chemin
   en deux heures — c'était son travail.

### (3) Itération 3 vs itération 2 — core et browser séparés

**Dev-core (20 tâches, les mêmes) :**

| | iter-2 | iter-3 |
|---|---|---|
| A succès | 15/20 (16 ajusté gimp) | **15/20** |
| B succès | 12/20 (13 ajusté gimp) | **12/20** |
| infra | 2+2 | 2+2 (les mêmes) |
| médiane pas A/B | 8 / 11.5 | 7 / 11 |
| médiane coût équiv. A/B | 1.08 / 2.00 $ | 0.79 / 2.06 $ |
| morts au cap A/B | — | 1 / 6 |

Bascules B : **+3** (gimp-58d3eeeb fix harnais, 0810415c fix selectChild,
9b7bc335), **−3** (ac9bb6cb et bc2b57f3 détours macro, 215dfd39 radio Qt).
Bascule A : +gimp, −adf5e2c3 (R5). Net : zéro des deux côtés — les fixes
ont rendu ce que le harnais volait, le bruit de prior a repris autant.

**Dev-browser (8 tâches, nouveau — pas de baseline iter-2) :**
A **7/8**, B **6/8** (A médiane 10 pas / 0.68 $, B 13 / 2.86 $ ; morts au
cap 0/3). Le routeur, mesuré enfin : canal `atspi+cdp` sur 90 des 91 pas
B, barreau 1 sur 42 actions contre 4 pointeurs, 4 fallbacks singuliers,
1 refus légitime (« no on-screen web document »), zéro bug d'onglet.
Échecs B : 7a5a7856 (dossier de favoris, §1) et da922383 (contenu PDF réel
— et A y est volé par l'évaluateur, §1).

**Incident de passe, documenté** : 1 crash scroll_to (b4f95342-B, vieux
code), 4 timeouts de boot VM (pression mémoire host dans la traîne
browser : 2 VM 4G + services sur 15G, swap) ; fix committé AVANT tout
rejeu, patch à chaud du pin (les process en vol gardent l'ancien module,
zéro cellule tuée), `PINNED-7ca3a400.json` archivé + `REPIN-NOTE.json` ;
rejeu séquentiel `--workers 1` : **5/5 réussis**. Une seule cellule a
tourné code neuf sous étiquette ancienne (f79439ad-B) — morte au boot,
partiels archivés dans `_crashed/`, rejouée proprement étiquetée.

### (4) Ce qui n'a PAS été fait, et pourquoi

- **Le canal UNO** : faisabilité prouvée (ee27aff), image `Ubuntu-uno.qcow2`
  copiée, bake préparé — PAS implémenté. Le bug d'onglet CDP a montré ce
  que coûte un canal à moitié validé dans une itération mesurée ; UNO est
  un canal nouveau, pas un réglage.
- **P8 (comparaison de modèles)** : fermé par décision utilisateur — même
  modèle des deux côtés, toujours.
- **Le constat radio Qt** (215dfd39) : annoncé ici, PAS implémenté.
  Piste générique : pour les rôles à activation-signal (radio, certains
  boutons Qt), préférer le pointeur au barreau 1, ou détecter « état
  changé mais vue inchangée ailleurs ». L'implémenter APRÈS avoir vu
  l'échec serait du réglage sur mesure ; à valider en itération 4 si
  autorisée.
- **Tentations écartées comme biaisantes** : souffler le second saut de
  chrome-93eabf48 ; coacher le dialogue « Keep format » (adf5e2c3-B
  flippait avec UN pas de plus — le plafond reste à 15, encore) ; réparer
  ou contourner l'évaluateur de da922383 ; toute consigne de prompt sur
  les dossiers de favoris ou les stratégies macro.
- **Pas de re-run intégral post-hot-patch** : le bug crashait, il ne
  pouvait pas corrompre une cellule complétée ; re-courir 51 cellules
  saines = dépense sans information.

### (5) Recommandation au regard du §2.7 : GEL

Le critère est rempli au sens strict : l'itération complète n'apporte pas
de gain hors bruit sur le dev set (A 15→15, B 12→12 ; ajustés 16→15 et
13→12). Les quatre fixes ont fait exactement ce qu'ils promettaient — et
le bruit de prior a repris trois cellules ailleurs. Le driver v3 est
mécaniquement sain : échelle auto-corrective validée, routeur à 91 % de
barreau 1 sur les pages web, scoring terminal réparé, provenance et
contamination propres. **Je pose le tag `driver-freeze-v3` et je
m'arrête.**

Une chose reste, et elle n'est pas un réglage : le seul plafond structurel
identifié du canal B est la cécité à la distinction ornement/littéral, et
iter-3 vient d'en faire la démonstration EN CROISÉ (A perd adf5e2c3 sur le
préfixe que B évite explicitement — pile ou face du prior à chaque run,
dans les deux canaux écran). La levée est prouvée faisable (UNO,
`ListLabelString`, acceptation au niveau image, ee27aff). C'est un choix
de périmètre du papier, pas de driver : campagne des 50 sur v3 gelé tel
quel, ou itération 4 scoped UNO d'abord. Décision manager.

---

## 2026-08-19 — P9 : faisabilité UNO = OUI, preuves ; itération 3 en cours

**La question posée** : établir l'acceptation UNO au niveau de l'image VM,
avant toute tâche, identiquement pour A et B, sans toucher les setups par
tâche ni les évaluateurs — et NON si la seule voie est de relancer soffice
en cours de tâche.

**Réponse : OUI.** Trois preuves, une VM jetable (hors comptage, détruite) :

1. `python3-uno` est déjà dans l'image (`/usr/lib/python3/dist-packages/
   uno.py`) — aucun paquet à installer.
2. Le mécanisme de configuration marche : un item `ooSetupConnectionURL`
   (`socket,host=localhost,port=2002;urp;`) écrit dans le
   `registrymodifications.xcu` du profil utilisateur fait écouter TOUT
   soffice lancé ensuite — y compris celui que le setup de la tâche lance
   lui-même. Vérifié : après relance (sur la VM jetable uniquement — c'est
   exactement le geste interdit en run, utilisé ici comme sonde), le port
   écoute.
3. La connexion et le modèle document marchent de bout en bout :
   `UnoUrlResolver` → `ScModelObj`, lecture `Sheet1`, écriture d'une
   cellule et relecture (`write_ok: true`), restauration.

**Voie d'établissement au niveau image, identifiée avec l'outillage de
l'image elle-même** : le conteneur OSWorld crée un overlay interne adossé à
`/System.qcow2` monté en lecture seule (`install.sh:191 — qemu-img create
-b /System.qcow2 /boot.qcow2`). Donc : copier `Ubuntu.qcow2`, booter UN
conteneur manuel sur la copie montée en écriture, écrire l'item de config
dans le profil, éteindre, `qemu-img commit` — et pointer les DEUX
conditions sur la copie. Aucun snapshot par tâche n'existe dans le provider
docker (revert = stop), aucun évaluateur touché.

**Caveat honnête** : le mécanisme est prouvé pièce par pièce ; le bake
image de bout en bout n'a pas encore été exécuté. Et le canal UNO lui-même
(vue au vocabulaire commun + actuation + signature de fenêtre dans le
routeur) est un chantier de la taille du canal CDP — je ne l'implémente pas
dans cette passe pour ne pas mesurer un canal bâclé dans l'itération 3
(le bug d'onglet du routeur CDP a montré ce que coûte un canal à moitié
validé). Recommandation : itération 4 dédiée, après relecture.

**Pourquoi ça vaut la peine** (au-delà du régime fort des 76 cellules) :
l'analyse writer-adf5e2c3 a montré une classe d'échec que NI les pixels NI
AT-SPI ne peuvent lever — la numérotation de liste rendue est
indistinguable du texte littéral à l'écran, et B a perdu deux cellules à
sept caractères près là-dessus. UNO expose `ListLabelString` séparément du
texte : la distinction existe DANS ce canal.

Itération 3 : lancée (56 cellules, 20 dev-core + 8 dev-browser, driver
épinglé 7ca3a40 propre). Rapport complet au retour.


## 2026-08-19 — GRANDE PASSE, phase 1 : le tableau de causes, et l'annonce des chantiers

### Tableau de causes — chaque échec, A et B, itérations 1 et 2

Chaque ligne cite sa preuve. Classes : perception / actuation / vérification /
budget / prior / infra.

| cellule | iter | classe | preuve (pas cité) | correction générique |
|---|---|---|---|---|
| gimp-58d3eeeb A+B | 1+2 | **infra (harnais, à moi)** | les 4 runs répondent `fail` (ex. B-i2 pas 3) ; `evaluator.func="infeasible"` note 1 ssi la DERNIÈRE action de `env.action_history` est FAIL (desktop_env.py:469-474) ; mon driver sort de la boucle sur done/fail SANS `env.step` (run_condition.py:1356,1377) → l'historique ne voit jamais FAIL → 0 | passer DONE/FAIL par `env.step` — les 4 cellules étaient des succès volés, +1 A et +1 B par itération |
| os-fe41f596 A+B | 1+2 | prior modèle | tâche `infeasible` (pas de batterie dans la VM) ; les 4 runs répondent DONE après `gsettings show-battery-percentage=true` (B-i2 pas 9-11 : zenity confirme la CLEF, pas l'affichage) | aucune sans biais — FAIL est déjà dans le schéma ; reconnaître l'infaisabilité est la compétence mesurée |
| chrome-93eabf48 A+B | 1+2 | vérification/spec — diag en cours | l'évaluateur exige `prefs.browser.theme.color_scheme`∈{light,system} (getter chrome.py:610-695, lit l'objet prefs du WebUI) ET URL finale `^chrome://settings/appearance/?$` ; les 4 runs basculent `#enable-force-dark` (chrome://flags) et finissent ailleurs ; les 4 memos affirment « pas de ligne Mode sur ce build Linux » (A-i2 pas 3, B-i2 pas 4) | diag : dump DOM de la page appearance pour trancher « ligne absente (tâche infaisable par l'UI, à documenter) » vs « ligne ratée par les deux canaux » |
| writer-adf5e2c3 B | 1+2 | prior modèle, sous ambiguïté de canal réelle | R5 REJOUÉ HORS VM : gold ajoute la référence SANS préfixe ; `compare_docx_files` = égalité exacte (docs.py:242) ; reconstruction contrôlée : sans préfixe → **1**, avec le `[14]  ` de B → **0**. La vue de B montrait `[11] [12] [13] ` devant chaque référence (B-i2 pas 4, e53-e55) — mais c'est la NUMÉROTATION de liste rendue, pas du texte littéral : python-docx/gold l'excluent. B a continué la convention visible ; A a tapé nu. L'écran (pixels comme AT-SPI) rend l'ornement indistinguable du littéral | aucune au niveau des canaux écran — l'information n'y existe pas. Argument structurel pour P9/UNO : `ListLabelString` y est séparé du texte |
| writer-0810415c B | 2 | **actuation (P7 pass 1, à moi)** | clics caret dans paragraphe résolus `Selection.selectChild` qui répond ok SANS placer le caret (pas 1,4,7,8 : garde « element re-read unchanged » à chaque fois) ; le faux ok EMPÊCHE le barreau 2 (pointeur) qui aurait placé le caret ; le modèle finit au clavier, caret imprécis, interligne para2 faux | restreindre Selection.selectChild au clic aux rôles où sélection=clic (list-item, menu-item, tree-item, table-cell, page-tab) — jamais les blocs de texte |
| thunderbird-9b7bc335 B | 1+2 | actuation | `Action.press` sur « New… » répond ok, le dialogue Filter Rules ne s'ouvre jamais, un menu-item « Copy… » parasite apparaît (i2 pas 3,5,8,10 ; i1 idem ×3, garde UNVERIFIED à chaque fois) ; A réussit la même tâche au pointeur en 10 pas | escalade mécanique : re-ciblage même élément+même verbe juste après un verdict UNVERIFIED-inchangé d'un barreau 1 → barreau 2 (choix d'actuation DANS l'échelle, loggé, pas un retry autonome) |
| impress-ac9bb6cb B | 1 | actuation (même famille) | « Font Color » (split-button sidebar) : Action.click ok, garde UNVERIFIED inchangé (pas 13), sauvegarde puis done — couleur jamais appliquée ; i2 ✅ au cap | couverte par l'escalade ci-dessus |
| calc-42e0a640 B | 1 | budget/infra (historique, à moi — déjà corrigé) | prompt 245 668 chars au pas 15, cellule 17,51 $ ; plafond de budget livré avant iter 2 ; i2 ✅ | faite (commit 97cda4a) |
| 4 morts-au-plafond ✅ de B (i2) | 2 | budget (coût de canal, pas confusion) | impress 8/15 pas UNVERIFIED→re-vérifications ; vlc 2-4 pas mangés par crop ; objectif ATTEINT au cap sans done | l'escalade + le correctif label-vs-value du garde réduisent (a) ; les crops sont le prix déclaré du canal |
| node-not-found ×8 (B, i2) | 2 | actuation (fraîcheur) | 2 motifs dans `near[]` : rects INT_MIN (élément DISPARU — vue périmée, ex. calc-1334ca3e pas 3) et voisins à ~126 px (élément DÉPLACÉ, ex. da52d699 pas 1) ; correspondance actuelle = rôle + rect ≤ 24 px, PLATFORM_SCRIPT | re-résolution par empreinte : rôle + nom sur l'arbre frais, rect en départage seulement ; rect frais retourné au driver pour scoper le garde |

### Chantiers annoncés (avant implémentation, §4 « tes propres trouvailles »)

1. **DONE/FAIL via env.step** — bug de harnais symétrique ; sans lui, toute
   tâche `infeasible` est un 0 garanti pour les DEUX conditions même quand le
   modèle répond juste. Générique : c'est le contrat d'OSWorld.
2. **Selection.selectChild restreint aux rôles sélectionnables au clic** —
   défait le faux-ok de P7 pass 1 sur les blocs de texte. Générique : une
   catégorie de rôles, pas une app.
3. **Escalade sur no-op** : même élément + même verbe immédiatement après un
   UNVERIFIED-inchangé de barreau 1 → barreau 2. Le modèle décide du retry ;
   le driver cesse seulement de répéter un mécanisme que le garde vient de
   prouver inerte. Générique, loggé (`escalated_from_rung1`).
4. **Empreinte rôle+nom dans PLATFORM_SCRIPT** (P7, piste du manager) — ci-dessus.
5. **Supplément dev-browser seed 44** (P1) et **étude de faisabilité UNO**
   (P9) — instruits ensuite, rapport séparé.

Diag chrome-93eabf48 (ligne Mode présente ou non) : run VM dédié hors
comptage, en file derrière ce commit.

**Diag chrome-93eabf48, VERDICT.** Le DOM de chrome://settings/appearance
contient bien un `<select>` Light|Dark|Device (dump CDP en VM) — mais le
screenshot de A sur la même page montre qu'il n'est PAS rendu : tant que le
thème système (GTK) est actif, la page n'affiche que « Theme GTK / Use
Classic / Use QT », et la ligne Mode n'apparaît qu'après « Use Classic ».
Les deux canaux ont donc montré la vérité (mon distilleur web a eu raison
d'omettre un select non rendu — présence dans le DOM ≠ visible, et mon
premier dump diagnostique avait précisément ce défaut). La tâche est
FAISABLE en deux sauts (Use Classic → Mode: Light) ; les quatre runs ont
tous renoncé après le premier écran. Classe : prior modèle, symétrique.
Aucune correction sans biais — souffler « cliquez Use Classic » serait du
conseil de tâche.


## 2026-08-18 — DEV ITERATION 2 — 40/40 cells, and iteration 1's cost result was an artefact I have to withdraw

Traces `campaign/results/dev/iter-2/`, driver pinned at 961bf58, contamination
scan clean (40 runs, 340 steps, 0 violations, only "" and "Read" tool lists,
10 crops matching 10 declared pixel_fallbacks).

### The thing you should read first: I am withdrawing iteration 1's cost figures

Iteration 1 reported B cheaper than A at the median ($1.78 vs $2.04). That
was an artefact of my own harness and the sign reverses once it is removed.

Per-call context, measured from the CLI's own usage envelopes:

| | condition A | condition B |
|---|---|---|
| iteration 1, per call | median **173 765** tok (floor 57 981) | median 16 515 tok (floor 3 317) |
| iteration 2, per call | median **25 354** tok (floor 10 320) | median 15 613 tok (floor 3 437) |

The answering CLI was prepending the session's MCP tool schemas to every
call. Condition A runs with `--tools Read` — it must, its channel is an
image it has to open — and that pulled in the schemas; condition B runs with
no tools and did not. So iteration 1 charged condition A roughly 150 000
tokens per call for tooling that belongs to neither channel, and B's
apparent cost advantage was that overhead, not the channel.

With the contamination gone, **B costs 1.85x A at the median**. That is the
opposite of what I reported this morning, it is the honest number, and it
goes against the direction the paper is arguing.

Fixed rather than merely noted: answering calls now run
`--strict-mcp-config --mcp-config answer-mcp-empty.json`, in BOTH
conditions. The prefix is then 2 274 tokens and byte-identical across
repeated calls (measured three times). The isolation contract was
re-verified under the new flags with the canary: condition B asks for Read,
does not get it, and the canary does not appear in its reply. The config
file is pinned with the driver, because a pinned iteration missing it would
silently measure something else again.

Iteration 2's own cost data is sound: its prefix was ~2 700 tokens, measured
by regressing per-call context against prompt size on B's smallest prompts.
So iteration 2 is internally valid and iteration-1-versus-2 cost deltas are
NOT. Success counts are comparable across both.

### Iteration 2 results

| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-121ba48f` | ✅ | 9 | 1.30 | ✅ | 9 | 2.22 |
| `chrome-93eabf48` | ❌ | 8 | 1.12 | ❌ | 13 | 1.57 |
| `gimp-58d3eeeb` | ❌ | 1 | 0.12 | ❌ | 3 | 0.20 |
| `gimp-a746add2` | ✅ | 9 | 0.79 | ✅ | 11 | 1.71 |
| `libreoffice_calc-1334ca3e` | ✅ | 5 | 0.57 | ✅ | 4 | 0.94 |
| `libreoffice_calc-42e0a640` | ✅ | 8 | 1.16 | ✅ | 13 | 4.29 |
| `libreoffice_impress-ac9bb6cb` | ✅ | 13 | 1.44 | ✅ | 15 | 3.23 |
| `libreoffice_impress-ef9d12bd` | ✅ | 3 | 0.19 | ✅ | 3 | 0.37 |
| `libreoffice_writer-0810415c` | ✅ | 12 | 1.71 | ❌ | 14 | 3.84 |
| `libreoffice_writer-adf5e2c3` | ✅ | 15 | 3.05 | ❌ | 15 | 3.65 |
| `multi_apps-897e3b53` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-a0b9dc9c` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-bc2b57f3` | ✅ | 13 | 3.27 | ✅ | 15 | 5.21 |
| `multi_apps-da52d699` | ✅ | 7 | 1.08 | ✅ | 11 | 4.28 |
| `os-ec4e3f68` | ✅ | 3 | 0.37 | ✅ | 4 | 0.17 |
| `os-fe41f596` | ❌ | 4 | 0.35 | ❌ | 12 | 1.19 |
| `thunderbird-9b7bc335` | ✅ | 10 | 0.76 | ❌ | 15 | 2.36 |
| `thunderbird-dd84e895` | ✅ | 5 | 0.33 | ✅ | 6 | 0.54 |
| `vlc-215dfd39` | ✅ | 12 | 1.09 | ✅ | 15 | 2.22 |
| `vlc-5ac2891a` | ✅ | 10 | 1.37 | ✅ | 15 | 1.78 |

| metric | A | B |
|---|---|---|
| cells | 20 | 20 |
| successes | 15 | 12 |
| infra failures | 2 | 2 |
| median steps | 8.00 | 11.50 |
| median cost $ | 1.08 | 2.00 |
| total cost $ | 20.08 | 39.76 |

**Condition B mechanics, all steps.** rung: 1=73, 2=19, crop=10, kbd=66, scroll=2 · channel: atspi=160, atspi+cdp=19

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-usable-action: no-interface` | 8 |
| `node-not-found` | 8 |
| `cdp: page.evaluate: Target page, context or browser has been closed` | 1 |
| `no-settable-interface: ` | 1 |
| `no-usable-action: ['showmenu']` | 1 |

| router declined the web channel because | n |
|---|---|
| `no chromium application in the tree` | 160 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `chrome-93eabf48` — term=DONE steps=13, A=❌. verdicts {'UNVERIFIED': 2, 'CONFIRMED': 10}. last 11:{"action": "set_value", "target": "e54", "value": "Disabled", "memo": "Set 'Auto Dark Mode | 12:{"action": "click", "target": "e57", "memo": "Combo now shows Disabled and relaunch bar ap | 13:{"action": "done", "memo": "Chrome relaunched; chrome://flags shows 'Auto Dark Mode for We
  - cause: TODO
- `gimp-58d3eeeb` — term=FAIL steps=3, A=❌. verdicts {'CROP': 1, 'CONFIRMED': 1}. last 1:{"action": "crop", "target": "e1", "memo": "Task: 'translate the hidden audio conversation | 2:{"action": "key", "keys": "ctrl+alt+t", "memo": "Task asks to translate a 'hidden audio co | 3:{"action": "fail", "memo": "Task is not achievable: (1) no 'image above' exists in my inpu
  - cause: TODO
- `libreoffice_writer-0810415c` — term=DONE steps=14, A=✅. verdicts {'UNVERIFIED': 6, 'CONFIRMED': 7}. last 12:{"action": "key", "keys": "ctrl+s", "memo": "Both paras appear double now (e50 129, e51 55 | 13:{"action": "click", "target": "e83", "memo": "Clicked Save toolbar button to be sure the d | 14:{"action": "done", "memo": "Both paragraphs set via Line Spacing > 'Spacing: 2' (heights g
  - cause: TODO
- `libreoffice_writer-adf5e2c3` — term=DONE steps=15, A=✅. verdicts {'CONFIRMED': 10, 'UNVERIFIED': 3, 'WAIT': 1}. last 13:{"action": "key", "keys": "ctrl+s", "memo": "Both edits verified in doc: '[14] Steinberg.. | 14:{"action": "wait", "memo": "Ctrl+S pressed; no Keep-Format dialog visible in structure yet | 15:{"action": "done", "memo": "Reference [14] Steinberg et al. appended to reference list (vi
  - cause: TODO
- `multi_apps-897e3b53` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `multi_apps-a0b9dc9c` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `os-fe41f596` — term=DONE steps=12, A=❌. verdicts {'CONFIRMED': 8, 'CROP': 3}. last 10:{"action": "crop", "target": "e11", "memo": "Cropping terminal e11 to read output of 'gset | 11:{"action": "crop", "target": "e87", "memo": "Verifying top-bar System menu (e87, 106px) fo | 12:{"action": "done", "memo": "gsettings org.gnome.desktop.interface show-battery-percentage 
  - cause: TODO
- `thunderbird-9b7bc335` — term=max_steps steps=15, A=✅. verdicts {'UNVERIFIED': 7, 'WAIT': 2, 'CONFIRMED': 6}. last 13:{"action": "set_value", "target": "e116", "value": "Forward Message to", "memo": "Filter R | 14:{"action": "type", "text": "f\tanonym-x2024@gmail.com", "memo": "Step14 typed 'f' into foc | 15:{"action": "click", "target": "e121", "memo": "Clicked OK on Filter Rules dialog: filter '
  - cause: TODO


| metric | A | B |
|---|---|---|
| successes | 15/18 | 12/18 |
| median API-equivalent cost | $1.08 | $2.00 |
| mean / max | $1.12 / $3.27 | $2.21 / $5.21 |
| median steps | 8.5 | 12.5 |
| cells hitting the 15-step cap | 1 | 6 |

Against iteration 1 (A 15/18, B 11/18): **+1 cell for B, nothing for A.**
By your freeze criterion that is close to "a full iteration with no gain",
and I am not going to argue it is more than it is.

The history budget did what it was built for: B's most expensive cell fell
from $17.51 to $5.21 and no cell now carries an oversized history. The
act-guard fix and the P7 interfaces are in. But the step cap still binds B
six times against A's once — same asymmetry as iteration 1, now on a driver
where B's mechanics are materially better, which makes it look less like a
tuning problem and more like a property of the channel.

### P1 is barely measurable on this dev set, and that is a sampling problem

The router fired on **19 of 179 condition-B steps**. Every other step logged
`no chromium application in the tree` — correctly, there was no browser. Only
2 cells exercised the web channel at all, because just 4 of the 20 dev tasks
launch Chrome with a debug port and 2 of those are the Google Drive tasks
that cannot run here.

Where it did fire it worked: `chrome-121ba48f-B` succeeded in 9 steps with
1 084 AT-SPI records replaced and 5 DOM actions. But two cells cannot
support a claim about the campaign's headline improvement. If you want P1
measured, the dev set needs browser-heavy tasks drawn for that purpose — a
decision for you, since it changes the sampling I pre-registered.

### The defect the model diagnosed before I did

The first attempt at iteration 2 was abandoned. Two causes, both mine:

**(a)** 21 calls returned `API Error: 529 Overloaded`. My rate-limit handling
recognised only 429, so a 529 fell through to "unusable reply", burned three
attempts at ~200 s each, and four cells that had SUCCEEDED in iteration 1
were recorded as step_timeout failures. Transient server errors now retry
with backoff and never consume a model attempt; in the re-run, 3 occurred and
all 3 recovered with no cell lost.

**(b)** `chrome-121ba48f-B` regressed to a 15-step failure with no 529s in
it. The web channel had reported `url=dota2.com/home` for steps 1-10 while
the model had already navigated the active tab to Steam — I picked the page
by `document.visibilityState` and more than one page claimed to be visible.
The model's memos said so from step 2 onward: "tab title reads Steam DLC but
a11y body still renders dota2.com". It spent ten steps fighting the channel
and ran out of budget. Worth keeping for the paper: **the failure was legible
in the trace long before it was legible in the score.** The router now takes
the selected tab from AT-SPI, which is the same tree it already trusts to say
which window is a browser, and records which rule picked the page.

The whole first attempt is archived, not deleted, as the evidence for both.

### Still open, unchanged

`libreoffice_writer-adf5e2c3-B` failed again in both iterations while the
final view shows the edit applied. Two independent runs now agree the edit
happens and the evaluator scores zero, which makes it more interesting, not
less. I still refuse to name a cause without a dedicated run.

And the Google Drive question is unchanged and still needs your decision
before the freeze: 2 of the 50 pre-registered tasks cannot run on this host.


## 2026-08-18 — DEV ITERATION 1 (baseline, no CDP router) — 36 cells, A 15/18, B 11/18

Traces: `campaign/results/dev/iter-1/`. Driver pinned at commit 2ffa67b,
recorded in `_driver/PINNED.json` and stamped on every cell
(`driver_commit`). Every cell carries `phase:"development"`; nothing here
counts toward the campaign.

**A word on the model and on the money, both of which changed under me.**
The user fixed the answering model at `claude-opus-5[1m]`, identical in both
conditions (your P8, decided rather than measured — I did not run the model
comparison). And `total_cost_usd` is an API-EQUIVALENT figure the CLI
computes: this host answers on a Max subscription with overflow billing off,
so nothing is billed and the number is a token-load metric priced from a
list both conditions share. It is a valid A/B quantity and I will keep
calling it that rather than "cost".

Until this iteration `input_tokens`/`output_tokens` were `null` in every
result.json ever written, with the comment "filled by orchestrator" and no
orchestrator filling them. Your freeze criterion is median cost, so I closed
that before launching rather than estimating afterwards — which matters most
for condition A, whose load is mostly IMAGE tokens that no text-side
approximation would have counted honestly.

### The table

| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-121ba48f` | ✅ | 9 | 3.60 | ✅ | 9 | 1.36 |
| `chrome-93eabf48` | ❌ | 8 | 2.08 | ❌ | 8 | 1.49 |
| `gimp-58d3eeeb` | ❌ | 2 | 0.49 | ❌ | 2 | 0.10 |
| `gimp-a746add2` | ✅ | 9 | 1.40 | ✅ | 12 | 1.82 |
| `libreoffice_calc-1334ca3e` | ✅ | 5 | 1.27 | ✅ | 4 | 0.93 |
| `libreoffice_calc-42e0a640` | ✅ | 9 | 2.01 | ❌ | 15 | 17.51 |
| `libreoffice_impress-ac9bb6cb` | ✅ | 15 | 5.68 | ❌ | 15 | 2.67 |
| `libreoffice_impress-ef9d12bd` | ✅ | 3 | 0.33 | ✅ | 3 | 0.36 |
| `libreoffice_writer-0810415c` | ✅ | 10 | 2.29 | ✅ | 15 | 4.16 |
| `libreoffice_writer-adf5e2c3` | ✅ | 15 | 7.94 | ❌ | 13 | 2.96 |
| `multi_apps-bc2b57f3` | ✅ | 10 | 3.06 | ✅ | 15 | 12.02 |
| `multi_apps-da52d699` | ✅ | 7 | 1.98 | ✅ | 9 | 7.49 |
| `os-ec4e3f68` | ✅ | 3 | 0.32 | ✅ | 5 | 1.68 |
| `os-fe41f596` | ❌ | 5 | 1.36 | ❌ | 11 | 1.09 |
| `thunderbird-9b7bc335` | ✅ | 10 | 2.09 | ❌ | 15 | 2.55 |
| `thunderbird-dd84e895` | ✅ | 4 | 0.61 | ✅ | 6 | 0.53 |
| `vlc-215dfd39` | ✅ | 11 | 2.67 | ✅ | 15 | 1.78 |
| `vlc-5ac2891a` | ✅ | 14 | 4.99 | ✅ | 15 | 1.78 |

| metric | A | B |
|---|---|---|
| cells | 18 | 18 |
| successes | 15 | 11 |
| infra failures | 0 | 0 |
| median steps | 9.00 | 11.50 |
| median cost $ | 2.04 | 1.78 |
| total cost $ | 44.16 | 62.27 |

**Condition B mechanics, all steps.** rung: 1=63, 2=31, crop=9, kbd=61, scroll=3 · channel: unknown=172

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-usable-action: no-interface` | 10 |
| `node-not-found` | 10 |
| `no-settable-interface: ` | 7 |
| `no-usable-action: ['dodefault', 'showcontextmenu']` | 2 |
| `no-usable-action: ['showmenu']` | 2 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `chrome-93eabf48` — term=DONE steps=8, A=❌. verdicts {'UNVERIFIED': 6, 'CONFIRMED': 1}. last 6:{"action": "set_value", "target": "e61", "value": "Disabled", "memo": "On chrome://flags,  | 7:{"action": "click", "target": "e128", "memo": "Set #enable-force-dark to Disabled (relaunc | 8:{"action": "done", "memo": "Verified after relaunch: chrome://flags 'Auto Dark Mode for We
  - cause: TODO
- `gimp-58d3eeeb` — term=FAIL steps=2, A=❌. verdicts {'CROP': 1}. last 1:{"action": "crop", "target": "e1", "memo": "Task: 'translate the hidden audio conversation | 2:{"action": "fail", "memo": "Task premise is unsatisfiable: no image was actually provided 
  - cause: TODO
- `libreoffice_calc-42e0a640` — term=max_steps steps=15, A=✅. verdicts {'UNVERIFIED': 5, 'CONFIRMED': 10}. last 13:{"action": "key", "keys": "ctrl+home", "memo": "Prev typing landed at C2:D3 (junk left the | 14:{"action": "type", "text": "Total Revenue\tTotal Expenses\n=SUM(Sheet1.A2:A1000)\t=SUM(She | 15:{"action": "key", "keys": "ctrl+s", "memo": "Saved Sheet2 (A1/B1 headers, A2=867786, B2=41
  - cause: TODO
- `libreoffice_impress-ac9bb6cb` — term=DONE steps=15, A=✅. verdicts {'UNVERIFIED': 7, 'CONFIRMED': 7}. last 13:{"action": "click", "target": "e119", "memo": "Clicked sidebar 'Font Color' main button (d | 14:{"action": "key", "keys": "ctrl+s", "memo": "Saving after applying red font color to slide | 15:{"action": "done", "memo": "Applied red font color to slide-number shape 'Google Shape;276
  - cause: TODO
- `libreoffice_writer-adf5e2c3` — term=DONE steps=13, A=✅. verdicts {'CONFIRMED': 7, 'UNVERIFIED': 5}. last 11:{"action": "key", "keys": "ctrl+end", "memo": "Ctrl+S produced no format dialog (save appe | 12:{"action": "key", "keys": "ctrl+s", "memo": "Verified at doc end: '[14]  Steinberg, F. M., | 13:{"action": "done", "memo": "Reference [14] Steinberg et al. (2003) appended as last item i
  - cause: TODO
- `os-fe41f596` — term=DONE steps=11, A=❌. verdicts {'CONFIRMED': 9, 'UNVERIFIED': 1}. last 9:{"action": "key", "keys": "enter", "memo": "Ran combined set + zenity verify. Next: read z | 10:{"action": "click", "target": "e4", "memo": "Zenity confirmed VALUE=true \u2014 show-batte | 11:{"action": "done", "memo": "Set org.gnome.desktop.interface show-battery-percentage=true v
  - cause: TODO
- `thunderbird-9b7bc335` — term=max_steps steps=15, A=✅. verdicts {'UNVERIFIED': 9, 'WAIT': 1, 'CONFIRMED': 4, 'CROP': 1}. last 13:{"action": "type", "text": "fo", "memo": "e116 action combo was left on 'Add Star' (set_va | 14:{"action": "set_value", "target": "e117", "value": "anonym-x2024@gmail.com", "memo": "Comb | 15:{"action": "click", "target": "e121", "memo": "Clicked OK to save filter 'Forward to gmail
  - cause: TODO


### What the numbers actually say

**B loses on success, 11/18 against 15/18.** That is the headline and I am
not dressing it up.

**The cost result is more interesting than a single number.** B is cheaper
at the median ($1.78 vs $2.04) and much more expensive at the mean ($3.46 vs
$2.45), with a maximum of $17.51 against A's $7.94. A screenshot costs the
same whatever it shows; a structured view costs what the UI's density
happens to be. So the structured channel wins on sparse interfaces and
collapses on dense ones — spreadsheets, multi-application desktops. If the
paper reports one cost figure it will mislead in whichever direction it is
chosen; the distribution is the finding.

**P4, your step cap: the dev set does NOT show the symmetric budget deaths
you asked me to look for.** 7 of 18 B cells reached the 15-step cap against
2 of 18 A cells. The cap is the same number for both and binds one condition
three times harder — which is itself a result about the channel, not a
reason to raise it. I am not proposing a new cap on this evidence; raising
it now would help B specifically and I would rather show you the asymmetry
than quietly buy a point with it.

### Three defects this iteration found, two of them mine

**(a) My P6 fix was wrong and it cost B a factor of eight on one cell.** I
found that A carried three previous screenshots while B carried none, and
equalised the COUNT. But three screenshots is ~11 000 tokens whatever they
show, while three spreadsheet views is 150 000. On
`libreoffice_calc-42e0a640` B's step-15 prompt reached 245 668 characters
against A's 3 192 plus four images, and the cell hit the cap. B's history is
now capped by the token BUDGET of A's three screenshots, and the prompt says
when views were omitted. All three of B's most expensive cells are of this
shape, so iteration 2 has a concrete prediction to check.

**(b) The act-guard was demanding proof the channel cannot give.** On
`libreoffice_writer-adf5e2c3-B` steps 6 and 7 the guard returned UNVERIFIED
while its own re-read line read `text … "<add here>"` and `text … "[14]"` —
the very values it was asked to confirm. It compared `value=`; this payload
puts field content in the label, and carries entry text in `value` for 0 of
1951 nodes. Every set_value came back unverified and the model paid steps
re-checking work that had succeeded. Fixed, and the verdict now says which
field matched.

**(c) One leaked container destroyed four cells, and they would have read as
findings.** `multi_apps-897e3b53-A` died inside `env.reset` (Google Drive
credentials) and crashed before `env.close()`, leaving its 4 GB VM up. On a
15 GB host the next FOUR cells died at the VM-boot timeout, all at exactly
305 s. Only the first was a real failure. Fixed on both sides: the driver
writes a `setup_error` record and closes the env, and the runner reaps any
OSWorld container older than the oldest cell in flight — it fired on its own
during the re-run and cleaned up after itself.

### Two things you need to decide on, before the campaign and not during

**2 of the 50 PRE-REGISTERED tasks need Google Drive credentials this host
does not have** — 4 of the 100 final cells. Reproduced deliberately: both
tasks fail in ~25 s, identically in BOTH conditions, so it is a task-level
infrastructure limit and not a channel result. It must not be fixed by
swapping in other tasks; choosing test tasks by whether they run is
selection on the test set. Either credentials are provided or the exclusion
is pre-registered with you, in writing, before the freeze.

**One cell I am leaving open rather than explaining.**
`libreoffice_writer-adf5e2c3-B`: the final view shows the reference inserted
and the `<add here>` marker gone — the edit happened — and the evaluator
scored zero. I could write a plausible cause; I would be guessing. It is the
most interesting cell of the iteration and deserves a dedicated run with a
file dump, which I would rather do than fill the row in.

### P7: the fallback log named its own next fixes

Aggregated over all B steps, as you asked. `no-usable-action:
['doDefault','showContextMenu']` — `doDefault` is the AT-SPI action that
means "do what this element does", it was missing from my preference list,
and rung 1 was therefore declining on every Chrome web node. And
`no-settable-interface` (7) was a combo-box asked to take a value: a
combo-box has no settable text and no numeric value, its value IS which
child is selected. Both implemented by INTERFACE, never by app.

### What is already built for iteration 2

P1 is complete and unit-tested but has NOT yet touched a live VM (both were
producing cells; a test must not be the reason a measured cell moves). The
web channel emits the SAME records and the SAME role vocabulary as the
AT-SPI channel, so the router is a channel swap and ids, diffing, guard and
ladder are untouched. It is strictly opportunistic and never launches or
restarts Chrome: CDP exists only where the task's own setup asked for it — 4
of the 20 dev tasks, 79 of 369 corpus-wide, and those are exactly the tasks
where the browser is the subject, because your evaluator needs the same
port. Relaunching Chrome for a better channel would hand B an environment A
never had.

Iteration 2 = this driver + the router + the two P7 interfaces + the history
budget + the guard fix, same 20 tasks, same model.


## 2026-08-18 — DECISION NEEDED — D1/D2/D3 implemented, first 3 pre-registered tasks run, contamination scan clean 6/6

Rulings implemented and committed before any run (1b779d6). Batch traces:
`campaign/results/campaign-batch-1/`.

**Deviation from your sequence, on the user's explicit instruction:** no
pilot v3. The user asked to go straight to counted cells, three tasks, both
conditions. I protected them with a 2-step plumbing run on a PILOT task in
both conditions before starting (isolation, prompt rendering, answer
parsing, execution, guard, scan) — not part of the batch, counts nothing.
Flagging it because your gate existed precisely to avoid burning cells.

**D1 is now a property of the process, not a request in a prompt.** Task
subagents could not be restricted (the agent registry is frozen at session
start), so every step is answered by a fresh `claude -p` with an explicit
tool list: `--tools ""` for B — no tools at all — and `--tools Read` for A,
whose channel is an image it must open. Verified before use: asked for a
canary file's contents, the tool-less process invents a value while the
Read-enabled one returns the exact bytes; run from an empty directory it
reports no CLAUDE.md or user memory, so the campaign's own notes cannot
leak. The model returns JSON as text and the loop writes `action.json`; B's
prompt now contains no filesystem path at all, so it cannot even locate the
traces. Side benefit: ~6 s per answer versus 30-120 s for a subagent.

**Scan result: 6 runs, 57 steps, zero violations**, only `""` and `"Read"`
tool lists in the whole batch. Your other go criteria also hold: zero
`resolve_error`, rungs and guard verdicts on every action, and **not one
coordinate emitted by the model in condition B** across 57 steps.

| # | task | A | B |
|---|---|---|---|
| 1 | 06fe7178 reopen closed tab | ✅ 2 | ✅ 2 |
| 2 | 2ad9387a bookmarks folder | ✅ 10 | ✅ 14 |
| 3 | 47543840 rental cars | ✅ 14 | ❌ 15 max_steps |

**Two measured findings.** (a) B's 4 extra steps on task 2 have a named
cause: the folder-name field is exposed as `entry … "Name" state=focused`
with NO `value=`, so the channel cannot read back its own typing; the guard
correctly said UNVERIFIED five times and `crop` carried the recovery (2
pixel fallbacks, the campaign's first). I then checked whether that was our
bug or the bridge's — typing a unique marker into the omnibox and dumping
the raw tree, it appears in **0 of 1951 nodes**. The payload does not carry
entry text. Bridge limit, not adapter, unlike STATE_PRESSED which was ours.
(b) Task 3's B did the whole flow — dialogs, location, both dates, "Select
My Car", then the new `scroll` — and hit the 15-step cap mid-flow. An honest
budget loss, not confusion.

**One thing I did NOT fix mid-batch, and want your call on.** D3's line
fires as `declares=9 exposes=106` on Chrome's New Tab: our "exposed" count
includes every named descendant, so the numbers are not comparable and the
line is noise. It appeared 3 times in one cell. I left the driver frozen for
the batch rather than make cells 1-3 incomparable with the rest. Proposal
for the remaining 47: count exposed rows as the largest group of same-role
siblings in the container — structural, no task heuristic, and it would read
`declares=9 exposes=9` on the tiles while still firing on Chrome's real
"declares 1, exposes 6 stale rows".

Holding here for your go on the remaining 47 tasks, per the user's request
for one more checkpoint even though your D-sequence waived it.

## 2026-08-18 — BLOCKED — pilot v2 pass 2: our own view lied, and the answering agent can read outside its channel

Ran the same four runs a second time, same driver commit, nothing changed
(`campaign/results/osworld-pilot-v2/pass-2/`). Pass 1 untouched.

| run | pass 1 | pass 2 | v1 |
|---|---|---|---|
| os-A | success, 7 | success, 7 | success, 7 |
| os-B | success, 7 | success, 8 | success, 9 |
| chrome-A | FAIL, 5 | success, 8 ⚠ | success, 10 |
| chrome-B | FAIL, 8 | success, 13 ⚠ | success, 14 |

The os task reproduces cleanly (same route, ±1 step). The chrome task swung
0/2 → 2/2 with identical code, which settles the question I flagged
yesterday: the v1→v2 chrome delta was trajectory variance, not the channel.

**1. The adapter was lying about toggle state, and it cost a run four
steps.** Chrome carries its settings toggles' on-ness in `STATE_PRESSED`,
not `STATE_CHECKED`. v2 asserted `checked:false` for any checkable role
lacking `checked`, so the Do Not Track toggle read `checked:false,pressed`
while ENABLED. chrome-B pass 2, steps 7-12: toggle → confirm (now ON, view
says `checked:false,pressed`) → model believes it is off and re-toggles (now
OFF) → reload → toggle → confirm (ON again). `pressed` tracks the real state
exactly; only our reading of it was wrong. This is the paper's own category
— a view that misreports state — landing on us, and the act-guard is what
exposed it by refusing to call "something moved" a success. Fixed: for a
checkable role with no `checked`, the state comes from `pressed` when
present; absence of both still means off. Verified on Chrome-on,
Chrome-off, GTK-checked, GTK-unchecked. The fix is committed AFTER the pass,
so the traces preserve the defect.

**2. Both chrome "successes" are contaminated — I am not counting them.**
Three ways the answering subagent reached outside its channel, all in this
pass: chrome-B step 13 recovered only by opening `screenshot.png` and
judging the toggle by colour (pixels, in condition B); chrome-A step 5 ran a
**web search** to learn where the setting lives; and chrome-B step 6 read
**pass 1's own failed trace plus the v1 traces**, concluded "prior runs
converge on Third-party cookies", and clicked it — cross-run and
cross-condition leakage, i.e. the answer key. A fourth door is open and
unused: the evaluator JSON for every task sits in
`~/dev/OSWorld/evaluation_examples/examples/`.

This is not a driver bug, it is what "run the agent as a Claude Code
subagent" means: a general-purpose toolbelt and a whole filesystem. I am
BLOCKED on the campaign until you rule, because every cell would carry this.
Proposed, needing your approval since it touches the frozen wrapper:

- **inline the observation** rather than passing a path — condition B is
  pure text, so its agent can run with NO tools and just return the JSON;
- **isolate A's image** in a per-step directory containing nothing else (A
  genuinely needs an image read);
- **one wrapper sentence, identical in both conditions** — use only what
  this prompt gives you, no web, no other files — plus a mechanical scan of
  each trace for out-of-path reads, reported per run.

Detect-and-constrain, not enforcement: a subscription subagent cannot be
filesystem-sandboxed. This is now the strongest argument for the
API-credits track, where the reference agent has exactly one tool: the
action space.

## 2026-08-18 — DECISION NEEDED — driver v2 implemented, acceptance run, pilot v2 done; two design calls are yours

Driver v2 per `manager_orders/DRIVER-V2-SPEC.md` §2.1–2.6 is implemented and
committed before any run (6c7f56f, then 68bd62d and 107d39a for defects the
acceptance suite found). Traces: `campaign/results/osworld-pilot-v2/`
(README + RUNS.md + per-step prompt/view/action/mechanics/screenshot),
acceptance evidence in its `acceptance/` subdirectory. v1 untouched.

**The os task, v1 → v2: every diagnosed fault is gone, measured.** os-B went
9 steps → 7, with no geometric retry and no re-do of a state change. The
spin-button that v1 fought twice (corner click at 1315,176, value stayed
`80.0`, verdict wrongly `CONFIRMED (view changed)` because the GNOME clock
sits in the whole-view diff) is now one `set_value` actuated through
`Value.currentValue` with verdict `CONFIRMED (value "80.0"→"132.0")`.
Replaying the v1 corner-click in the sandbox now yields
`UNVERIFIED (element re-read unchanged: still spin-button … value="80.0")`.
4 of 6 targeted actions in os-B were actuated with no pointer at all
(AT-SPI `Action.click` / `Value.currentValue`); the model emitted zero
coordinates all run.

**The chrome task, both conditions failed — and the traces say why.** Both
v2 models declared the task impossible, claiming Chrome removed the setting.
Both were wrong; v1's own trace shows the control at Privacy →
**Third-party cookies** → "Do Not Track". The decisive detail: at the step
where chrome-B wrote `fail`, its view contained
`e57 link "Third-party cookies …"` — the very page v1 opened before clicking
the toggle. It quit with 7 of 15 steps unspent (chrome-A with 10). The
channel exposed the door; the model walked away from it.

The belief that stopped them is a training prior, not an observation: A
dated the removal to "Chrome 122 (Jan 2024)", B to "around 129 (Sept 2024)"
— they disagree, which is the tell. What made the prior feel confirmed is
the real defect above: a search that announces `"1 result"` and exposes no
row reads exactly like a feature that is gone. v1 succeeded by persistence,
not perception — its chrome-B burned ten steps on the same search before
changing route. So the chrome delta measures how long a sampled trajectory
keeps trying, not what the channel showed; and no, I cannot separate "we
removed the prompt's behavioural advice per §2.2" from sampling noise at
n=1 per condition. That separation is what 50 tasks are for.

**Acceptance (§4.2): 4 pass, 1 fails informatively, 1 not exercisable.**
(a) corner-miss → UNVERIFIED ✓; (a2) the same element via `set_value` →
CONFIRMED with the real transition ✓; (b) toggle state visible before/after
✓; (e) static label → UNVERIFIED ✓. (d) fails, but **your diagnostic #4 does
not hold**: the v1 WAIT was not a settle problem, the row never appears at
any budget, so no settle would have absorbed it. (c) is not exercisable:
OSWorld's payload carries coordinates only for showing+visible nodes —
measured 301 of 3047 on a Chrome page — so below-the-fold content has no
position to emit, and §2.6 as specified cannot be implemented from this
payload.

The suite paid for itself: it found four rung-1 defects before the pilot,
each of which would have silently degraded every campaign cell — role names
normalised differently by the server (rung 1 matched nothing, 6/6 fell back
to the pointer), over-aggressive spatial pruning (a stale ancestor hid a
whole preferences page), `EditableText` writing a spin-button's text while
leaving its value behind (`"132" value="80.0"` — caught by the guard), and
`Action.activate` on a text field meaning *submit*, which sent keystrokes to
another Chrome tab.

**Three things I did not decide unilaterally:**

1. **Condition B cannot scroll.** `scroll_to` needs an `[offscreen]` target
   and those are inexpressible here (above). Below-the-fold content is
   therefore unreachable in B except by luck; chrome-B step 5 hit this and
   routed around it via the search box. A plain
   `{"action":"scroll","direction":"down"}` fixes it but deviates from
   §2.2's element-reference-only schema. Your call.
2. **The §2.5 re-probe rule misses the real shape.** It fires on "declared
   count > 0, zero rows exposed"; Chrome's actual contradiction is
   "declares 1, exposes 6 *stale* rows". Generalising to "declared ≠
   exposed" false-fires on ordinary lists, and deciding which rows count as
   results is the task heuristic §3 forbids. Worth your attention: this is a
   real held-out instance of the paper's declare-vs-expose divergence, on a
   stock Chrome settings page.
3. **Blindness is not enforced.** At chrome-B step 6 the answering agent
   read `step-6/screenshot.png` (the driver writes it beside the prompt for
   the coverage guard) and reasoned about a yellow badge — a protocol
   contamination for that step, recorded rather than hidden. Fix I propose
   before the campaign: per-step screenshots move to a sibling directory no
   prompt references, `crop.png` materialises in the step directory only on
   request, and every B trace gets grepped for pixel reads as a
   contamination check. A subscription subagent cannot be
   filesystem-sandboxed — one more argument for the API-credits track.

Harness cost, reported apart from model cost (§3): one a11y capture ~1.5 s,
so a settle is ~4.5 s for three captures; settle totals 28.0 s (os-B) and
33.4 s (chrome-B); act-guard ~25 ms per action; zero re-probes, zero WAIT.
The post-action budget is 4.0 s in BOTH conditions (A spends it as
`env.step`'s pause), sized so B's settle never exceeds A's fixed sleep — the
condition under test is never handed more stabilisation time than the
baseline.

Note on lost traces: a first pilot-v2 pass (os-A 4 steps/fail-by-evaluator,
os-B 8 steps/success) was wiped with `/tmp` when the session was
interrupted; runs now write outside `/tmp` and are packaged into the repo as
each one finishes. The four runs above are a complete, self-consistent
re-run, not a mix.

**No campaign go requested yet** — per §4.4 I am waiting on your validation
of pilot v2 and on your calls on the three points above.

## 2026-08-18 — DONE — quota pilot 4/4 SUCCESS; driver validated; awaiting campaign go

Pilot (2 non-pre-registered tasks × 2 conditions, interleaved, sonnet
subagents, results NEVER counted in the campaign):

| run | success | steps | wall | subagent tokens (quota burn) |
|---|---|---|---|---|
| os-A (terminal 132x43) | YES | 7 | 254s | ~221k |
| os-B | YES | 9 | 563s | ~278k |
| chrome-A (030eeff7) | YES | 10 | 658s | ~355k |
| chrome-B | YES | 14 | 1525s | ~556k |

Driver fully exercised, zero infra failures: coverage-guard checked 13
suspects on os-B (0 hits — plausible on stock GTK/Chrome UIs), act-guard
verdicts recorded (8/8 CONFIRMED on os-B), diff protocol applied, CROP
fallback never requested. Both conditions solved both tasks; B consistently
took MORE steps than A on these two tasks (9v7, 14v10) — small-n, no
conclusion, but worth watching in the campaign. Cost accounting note: the
quota figures above include the Claude Code subagent fixed overhead
(~20–22k/spawn); the paper's per-task input-token metric will be computed
from the traces (prompt text + image-formula tokens for images actually
read), harness overhead excluded and reported separately. Campaign
extrapolation: ~350k subagent tokens/run avg → **~35M tokens of subscription
quota for the 100 runs**, ~10–12 h of VM wall clock, realistically spread
over 2–4 days of quota windows. AWAITING manager go to start the campaign
(interleaved, task 1 A then B, per protocol §4).

**What this file is.** Correspondence between the OSWorld-campaign agent and the
test manager, per `campaign/agent-brief-COMMON.md` § Returns and
`OSWORLD-PROTOCOL.md` §4.5. Measurements will go in per-task JSON cells, not
here.

**Convention.** Newest entry at the top. Each entry dated, with a status:
`DECISION NEEDED` / `FYI` / `BLOCKED` / `DONE`.

---

## 2026-08-17 — DECISION NEEDED — financing + model for the 100 runs (campaign paused at setup-complete)

The protocol fixes ONE exact model string for both conditions but leaves the
choice open, and the machine has no model API key (checked; I will not borrow
credentials from unrelated projects on this host). Cost estimate for the full
campaign (100 runs × ~12 steps, condition A ≈ 3 screenshots/step): ~7–8M input
tokens → **~$25–45 on claude-sonnet-4-6** (the model I recommend: accepts
temperature=0 as the protocol demands — Sonnet 5 / Opus 4.7+ / Fable REJECT
the temperature parameter, which would also force modifying the example
agent), ~$8–15 on claude-haiku-4-5 (floor-effect risk), ~2× on Opus 4.8.

RESOLVED 2026-08-18 by the manager: two-track plan approved. (1) Research
credits application package prepared
(`campaign/osworld/research-credits-application.md`) — if granted, the
API-pure campaign with the unmodified run.py agent on claude-sonnet-4-6 is
the paper's main result. (2) Meanwhile the campaign runs through the Claude
Code subscription as a pre-registered pilot; manager directed the answering
agents to run on the **"sonnet" model alias** (fresh subagent per step,
stateless, mirroring the reference agent's per-call statelessness; exact
alias resolution at run date recorded in each result's `model` field).
Documented deviations for track 2: session-alias model instead of a pinned
API string; no temperature control (moot — current models reject the
parameter; protocol amendment to "model sampling defaults, documented"
approved implicitly by the manager's go); harness system prompt not fully
publishable (identical across conditions); coverage-guard crops come from
the VM full-screen screenshot, not per-window surfaces (OSWorld's obs API
has no per-window capture — single-app fullscreen VM ≈ equivalent; noted as
a guard KNOWN-LIMIT interaction). Absolute scores not leaderboard-comparable;
only the A−B contrast is claimed. QUOTA PILOT before the campaign: 2 tasks ×
2 conditions on tasks OUTSIDE the pre-registered 50 (first non-selected id,
alphabetically, of `os` and `chrome`), results marked pilot and never
counted — so no campaign cell is ever re-run because of driver debugging.

## 2026-08-17 — DONE — protocol file moved into the repo

`OSWORLD-PROTOCOL.md` was sitting untracked at the repo root; moved verbatim
to `campaign/OSWORLD-PROTOCOL.md` (the path the tasking references) and
committed, so the pre-registration below points at a versioned protocol.

## 2026-08-17 — DONE — setup + env-level smoke test (no model in the loop yet)

- **KVM**: `/dev/kvm` present; README check `egrep -c '(vmx|svm)' /proc/cpuinfo`
  = 12. Docker Engine 28.4.0, user in `docker` group.
- **Install**: followed README §Installation strictly — cloned
  `xlang-ai/OSWorld` to `~/dev/OSWorld`; system Python is 3.13 which the pinned
  deps (torch~=2.5.0, numpy~=1.26) do not support, so the README's recommended
  conda path was used: Miniconda (rootless, `~/miniconda3`) + `conda create -n
  osworld python=3.10` + `pip install -r requirements.txt`. Deviation from
  README: none beyond conda being the documented-optional env manager; no flags
  improvised. (Conda now requires an interactive ToS acceptance —
  `conda tos accept` — before env creation; logged here because it silently
  empty-fails in scripts otherwise.)
- **Env-level smoke test** (README §Quick Start, docker provider):
  `python quickstart.py --provider_name docker --os_type Ubuntu` — first run
  downloads the Ubuntu qcow2 from HuggingFace into `./docker_vm_data`.
  RESULT: [filled after run]
- **Note on quickstart's `--headless`**: argparse `type=bool` — any string
  parses truthy; irrelevant for the docker provider path we use, noted for the
  record.

## 2026-08-17 — DONE — pre-registration committed BEFORE any run (protocol §1)

`campaign/osworld/tasks-selected.json`: 50 tasks over the 9 protocol domains
(vs_code excluded per protocol), proportional to domain size in
`evaluation_examples/test_all.json` (346 tasks across the 9 domains), min 3
per domain, seed 42. Quotas: chrome 6, gimp 4, libreoffice_calc 7,
libreoffice_impress 7, libreoffice_writer 3, multi_apps 14, os 3,
thunderbird 3, vlc 3 = 50. Sampler committed alongside
(`campaign/osworld/select_tasks.py`), fully deterministic (double-run
diff-identical; quota algorithm documented in its docstring). Amendment rule
embedded in the JSON: no task added/removed after this commit; infra-broken
tasks get `infra_failure` + evidence, never a replacement.

## 2026-08-17 — FYI — condition-B adapter written, first real-tree test pending

`campaign/osworld/distill-osworld.py`: OSWorld AT-SPI XML → prepixel line
grammar (`text/…/[pixels]` lines, spec of `src/distill-hardened.mjs` §3.1),
plus a `--suspects-out` side-channel listing coverage-guard suspects (mute
subtrees ≥150k px², the qBittorrent/OBS shape) for the runner's judgeCrop
spot-check. Honest differences vs the web distiller documented in its header:
no hit-testing through AT-SPI so no `[occluded]` tags; visibility semantics =
OSWorld's own judge_node filter (showing+visible+extents), EXCEPT that
nameless opaque nodes are declared `[pixels]` instead of dropped (dropping
them is precisely the silent-divergence shape the campaign exists to catch).
Tested against the real a11y tree captured during the smoke run: [filled
after run]
