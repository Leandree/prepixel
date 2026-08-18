# Arbitrages manager sur le pilote v2 (réponse au BLOCKED du 2026-08-18)

Validation d'ensemble : driver v2 conforme à la spec, suite d'acceptance
rentabilisée, blocage contamination justifié. Les décisions ci-dessous
débloquent la campagne après un pilote v3 de validation du wrapper.

## D1. Contamination : proposition APPROUVÉE intégralement, plus une porte

- Observation INLINE dans le prompt ; condition B = sous-agent SANS OUTIL
  qui rend son JSON en texte de réponse (pas de Write, pas de Read, rien).
- Condition A : l'image dans un répertoire par étape qui ne contient QUE
  l'image ; l'agent A n'a que l'outil de lecture d'image, rien d'autre si
  le harnais le permet.
- Phrase de cadrage identique dans les deux conditions (« n'utilise que ce
  que ce prompt te donne »), une seule phrase, pas de conseil de
  comportement au-delà.
- Scan mécanique de chaque trace : toute lecture hors du chemin autorisé
  invalide l'étape et se rapporte par run ; le scan couvre explicitement
  `~/dev/OSWorld/evaluation_examples/` (le corrigé), les screenshots, les
  traces des autres runs et conditions, et le web.
- Screenshots du coverage-guard déplacés dans un répertoire frère jamais
  référencé par un prompt ; `crop` matérialisé dans le répertoire d'étape
  uniquement sur demande explicite du modèle.
- Les deux « succès » chrome de la passe 2 restent non comptés, comme tu
  l'as décidé. Le pilote ne compte de toute façon jamais.

## D2. Scroll en condition B : APPROUVÉ en action mécanique sans cible

`{"action":"scroll","direction":"down"|"up"}`, incrément fixe du driver,
même sémantique qu'un `key` : c'est une action sans référence d'élément,
comme `type` et `key` en ont déjà. Ce n'est pas une entorse à §2.2.
§2.6 (`[offscreen]` + `scroll_to`) est déclaré NON IMPLÉMENTABLE depuis le
payload OSWorld (301 nœuds positionnés sur 3047 mesurés) : le documenter
dans l'en-tête de l'adaptateur et dans le returns file. Note papier (je m'en
charge) : sur ce harnais, B perd l'avantage « toute la page en une
lecture » que CDP fournit ; limitation du pont, pas du canal, à rapporter.

## D3. Re-probe « déclare N, expose M » : PAS de généralisation heuristique

Ta objection est correcte : décider quelles lignes « comptent » est
l'heuristique de tâche que §3 interdit. À la place, DÉCLARER sans juger :
quand un conteneur porte un compte déclaré et que le nombre de lignes
exposées diffère, émettre les deux faits bruts sur la ligne du conteneur
(`declares=1 exposes=6`) et logguer l'occurrence. Le modèle décide, le
driver rapporte. Chaque occurrence est une instance held-out de la
divergence déclaré-vs-exposé sur du Chrome stock : compteur dédié dans les
mechanics, ça finit dans le papier.

## D4. Fix STATE_PRESSED : VALIDÉ, et c'est un résultat, pas un bug honteux

Le commit après-passe qui préserve le défaut dans les traces est la bonne
pratique. L'épisode (vue qui misreporte l'état, attrapé par l'act-guard
scopé refusant de confirmer) est de la validation held-out du guard sur
notre propre adaptateur ; conserve les références de traces exactes
(pass-2 chrome-B étapes 7-12, les fallbacks `check`/`uncheck` comme preuve
de l'état réel), j'en fais un encart méthode dans le papier.

## D5. Échec chrome par prior : ACTÉ, aucune correction de prompt autorisée

Aucun coaching (« le réglage existe encore ») dans aucun prompt : ce serait
du conseil de comportement et une fuite d'information de tâche. La variance
de trajectoire est un phénomène que la campagne mesure, pas qu'on gomme.
Mon diagnostic n°4 (settle) était faux, ta correction est retenue : la
ligne n'apparaît à aucun budget ; le trou est dans le pont, pas dans le
timing.

## Séquence de déblocage

1. Implémenter D1, D2, D3 (D4 déjà committé). Committer avant tout run.
2. Pilote v3 : les 4 mêmes runs, nouveau wrapper, dans
   `results/osworld-pilot-v3/`. Critères de go : scan de contamination
   vierge sur les 4 runs, mécaniques nominales (rungs loggés, guard actif,
   zéro resolve_error), et un os-B sans coordonnées émises comme en v2.
3. Sur ces critères, GO campagne (interleavée, protocole §4) SANS nouvelle
   validation manager : ne pas attendre un aller-retour de plus. Si le scan
   n'est pas vierge, BLOCKED et retour ici.
4. Le track crédits API reste le résultat principal s'il se matérialise ;
   la campagne subscription reste étiquetée comme telle dans chaque cellule.
