# Phase de développement : améliorer le système, protéger le test

Cet ordre SUPERSÈDE le go des 47 restantes de BATCH-1-GO.md. Décision
utilisateur + manager : on est en recherche, on améliore d'abord le
système, puis on court le test UNE fois, figé. HOLD sur toute cellule
pré-enregistrée à partir de maintenant.

## 1. Le principe qui rend tout ça non biaisé

Le driver est le système mesuré : l'améliorer est légitime. Ce qui est
interdit, c'est de l'améliorer en regardant le test. Donc :

- **Dev set** : tâches OSWorld HORS des 50 pré-enregistrées, mêmes domaines.
  Tire 20 tâches dev (seed 43, même sampler, exclusion explicite des 50 et
  des 2 tâches pilote), committe `campaign/osworld/tasks-dev.json`. Itère
  librement dessus, autant de runs que tu veux, tout loggé en
  `results/dev/`.
- **Test set** : les 50 pré-enregistrées, INTOUCHÉES pendant toute la phase
  dev. Les 6 cellules du batch 1 sont reclassées `development` (champ
  `phase:"development"` ajouté à leurs JSON, elles restent publiées).
- **Gel** : quand les améliorations plafonnent sur le dev set (critère : une
  itération complète sans gain de succès ni de coût), tag
  `driver-freeze-v3`, et la campagne finale court les 50, une fois, sans
  plus aucune modification. Toute cellule finale porte le hash du freeze.

Règles inchangées de la spec v2 §3 : mécanique déterministe seulement,
aucune heuristique de tâche, aucun conseil de comportement dans les
prompts, mêmes budgets (pas, délai post-action) dans les deux conditions,
condition A jamais modifiée.

## 2. Les améliorations à développer, par priorité

**P1. Le routeur par fenêtre, pour de vrai : CDP pour Chrome.** C'est
l'architecture du papier (canal choisi par signature, par fenêtre) et ce
qu'une prod ferait. Lance le Chrome de la VM avec le port de debug (vérifie
d'abord ce qu'OSWorld fait déjà pour ses evaluators) et bascule les
fenêtres Chromium sur le distiller CDP existant (`src/`), AT-SPI restant le
canal des autres fenêtres. Ça résout d'un coup, par le canal et non par des
rustines : le texte tapé (values CDP), le hors-viewport (page entière →
`scroll_to` redevient implémentable sur les fenêtres CDP), les lignes de
recherche paresseuses, et les états des toggles web. C'est aussi LA
démonstration du compositeur sémantique en conditions agent.

**P2. L'écho de frappe du driver.** Pour les canaux qui n'exposent pas la
valeur d'un champ : le driver SAIT ce qu'il a tapé (c'est son action).
Annoter l'élément focusé `typed-by-driver="do not track"`, étiqueté comme
enregistrement du driver et jamais confondu avec un état lu du canal ; le
guard continue de vérifier ce qui est vérifiable. Mécanique, honnête,
et exactement ce qu'un runtime de prod ferait.

**P3. AT-SPI direct dans la VM, si le payload OSWorld reste le goulot.**
Un helper dans la VM qui interroge AT-SPI en direct (valeurs des entries,
nœuds offscreen, états complets) au lieu du payload appauvri. Compare sur
le dev set : si le payload suffit une fois P1 en place, ne le fais pas.

**P4. Seulement si le dev set le justifie : plafond de pas.** La tâche 3
est morte à 15 pas en plein flux correct. Si le dev set montre des morts
budgétaires récurrentes dans les DEUX conditions, propose un nouveau
plafond unique AVANT le gel (il se pré-enregistre avec le freeze, il ne se
change jamais après).

**P5. Une mémoire de trajectoire, identique dans les deux conditions.**
Les répondeurs sont des process frais et sans état à chaque pas : les
boucles de re-navigation (chrome v1 pas 8-10, pass-2 pas 7-12) et les
abandons par prior sont en partie des pertes de continuité, pas de
perception. Ajoute au schéma de réponse un champ `memo` (2-3 phrases max,
tronqué mécaniquement) que le driver réinjecte verbatim au pas suivant,
dans A comme dans B, même format, même limite. C'est du scaffold d'agent
standard (une prod l'aurait), condition-neutre, et ça ne dit jamais au
modèle QUOI penser, seulement où poser ce qu'il pensait. À mesurer sur le
dev set : c'est probablement le plus gros gain de variance disponible.

**P6. Vérifier la cohérence historique des prompts sans état.** Le
protocole de diff suppose un lecteur qui a vu la vue précédente ; un
process frais ne l'a pas vue. Vérifie que le prompt de B inline TOUJOURS
la vue courante complète (ou la vue + le diff étiqueté comme tel), jamais
un diff seul contre une vue que le répondeur n'a jamais reçue. Même
vérification pour le verdict act-guard (il doit citer l'état, pas
référencer un pas invisible). Comptabilité coût inchangée : on mesure les
tokens réellement envoyés.

**P7. Élargir le barreau 1 là où les logs de fallback pointent.** Les
mechanics loggent chaque `rung1_fallback` avec sa raison
(`no-action-interface`, `no-usable-action`). Sur le dev set, agrège ces
raisons et implémente les interfaces AT-SPI manquantes de façon générique :
`Selection` pour les combo-box et listes, `Text`/caret pour le
positionnement dans un champ, `Value` déjà fait. Critère générique strict :
on implémente une INTERFACE, jamais un cas d'app.

**P8. Le choix du modèle est un paramètre légitime, à fixer sur le dev
set.** Même modèle dans les deux conditions, toujours ; mais RIEN n'impose
que ce soit sonnet. Si le budget le permet, une itération dev A/B avec un
modèle plus fort dira si les échecs par prior (chrome « le réglage a été
supprimé ») sont un plafond de modèle ou un plafond de canal ; ce qui est
en soi une donnée pour le papier. Le modèle retenu se fige avec le driver,
dans le tag de freeze.

## 3. La mesure sur le dev set

Chaque itération dev : les 20 tâches, deux conditions, mêmes métriques que
la campagne, plus un tableau d'itération dans le returns file (succès A/B,
coût médian, cause de chaque échec B en une ligne). C'est ce tableau qui
décide du gel. Les runs dev alimentent aussi l'exposition held-out des
guards (chaque hit loggé), qui servira au papier même si les cellules ne
comptent pas.

## 4. Ce qui finit dans le papier (pour contexte)

La phase dev elle-même se publie : « le driver a été développé sur 20
tâches disjointes, gelé au commit X, puis évalué une fois sur les 50
pré-enregistrées » est la phrase qui rend le résultat crédible. Les
findings de pont (entry text absent du payload, 301/3047 nœuds positionnés)
sont des mesures à part entière. Et si le routeur CDP-par-fenêtre améliore
nettement B sur le dev set, c'est le résultat le plus important de toute la
campagne : le papier dit précisément que le canal se choisit par fenêtre à
partir d'une signature, et on l'aura démontré en agent-level.
