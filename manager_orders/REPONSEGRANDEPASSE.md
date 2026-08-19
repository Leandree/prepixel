# Réponse manager au rapport final de la grande passe

Relecture complète faite : rapport, tableau des causes, traces citées,
liste des modifications, incidents. Validation d'ensemble sans réserve sur
la méthode. En particulier : le fix DONE/FAIL via env.step (rendre à
l'évaluateur ce que l'agent déclare, ET rendre les 4 succès volés aux deux
conditions, c'est la définition d'un fix de harnais légitime), les deux
bugs d'évaluateur documentés-pas-réparés (la bonne règle, tenue deux fois
sous tentation), la gestion de l'incident hot-patch (pin archivé, rejeu
étiqueté, cellule morte re-courue proprement), et la section « tentations
écartées » qui est exactement le livrable demandé. La démonstration
CROISÉE de la classe R5 (A perd en iter-3 sur le préfixe que B évite
explicitement, miroir exact d'iter-2) est un résultat de premier ordre
pour le papier : préserve ces deux paires de traces précieusement.

## La décision : pas de gel immédiat. Une itération 4, bornée, terminale.

Ton application du critère §2.7 est correcte au sens strict, et ta
recommandation est défendable. Je la refuse pour la raison suivante : le
critère de gel gouverne le RÉGLAGE ; il ne s'applique pas à un canal non
mesuré. C'est le précédent exact de l'itération 3 : on ne gèle pas tant
qu'un canal du backlog, prouvé faisable, n'a pas été mesuré une fois.
UNO est dans ce cas (ee27aff : faisabilité end-to-end, image préparée), il
couvre LibreOffice soit 17 des 50 tâches du test, c'est le régime le plus
fort de la campagne 76-cellules (lecture document ~18 tokens, actuation
sans coordonnées, et `ListLabelString` qui lève la seule classe d'échec
structurelle identifiée), et la thèse du routeur est « le meilleur canal
par fenêtre ». Courir la campagne finale sans son meilleur canal sur un
tiers du test serait un défaut d'architecture auto-infligé, et un
relecteur le verrait.

Pour fermer le risque de régression infinie, deux bornes explicites :

- **UNO est le DERNIER canal du backlog. Il n'y a pas de P10.**
- **Le gel post-itération-4 est INCONDITIONNEL**, quel que soit le
  résultat, y compris si UNO déçoit. Tag `driver-freeze-v4` (ou re-pose de
  v3 si UNO est retiré), puis campagne des 50, sans autre aller-retour.

## Périmètre de l'itération 4 : deux chantiers, rien d'autre

1. **Le canal UNO dans le routeur**, aux conditions déjà actées :
   opportuniste (jamais de lancement ni relance de soffice en cours de
   tâche), affordance établie au niveau de l'image VM AVANT toute tâche et
   identique pour les DEUX conditions, preuve committée que les snapshots
   par tâche et les évaluateurs sont inaffectés (étends la preuve ee27aff
   à un run d'évaluateur complet sur une tâche dev calc, les deux
   conditions, avant les runs comptés). Même vocabulaire de rôles, mêmes
   ids, même garde, même échelle ; composition par contenance comme pour
   CDP. Le canal se logge par pas (`atspi+uno`), refus légitimes inclus.
2. **La politique des rôles à activation-signal** (le constat radio Qt).
   Elle passe le test de généricité (le mécanisme cité est documenté :
   `Action.toggle` flippe l'état sans émettre le signal d'activation que
   l'app écoute ; c'est une sémantique d'interface, pas un cas d'app).
   Implémente par SÉMANTIQUE DE RÔLE : pour les rôles dont l'activation
   est un signal (radio-button, et documente la liste), le barreau 1
   descend au pointeur synthétisé ; ou, si tu préfères, détection
   « état changé, vue inchangée ailleurs » remontée UNVERIFIED. Choisis
   UNE des deux, justifie en une ligne, valide sur le dev set.

Interdits inchangés : aucun autre réglage, aucun conseil de prompt, cap à
15, A intouché, tâches infaisables et évaluateurs cassés documentés
jamais réparés.

## Mesure

Itération 4 = les 28 tâches dev (20 core + 8 browser), deux conditions,
mêmes métriques, canal par pas. La comparaison porte sur iter-3 (même
périmètre). Les cellules LibreOffice sont le critère primaire déclaré
d'avance : succès et coût sur calc/writer/impress ; le reste du dev set
sert de non-régression. Si UNO n'améliore ni succès ni coût sur ce
sous-ensemble, il reste dans le driver (canal légitime du routeur) mais le
résultat se rapporte tel quel.

## Pré-enregistrement pour la campagne des 50 (à écrire avant le gel)

La classe « évaluateur cassé » que tu as prouvée (da922383-A, warning
PyMuPDF dans l'exact_match) peut exister dans les 50. Règle committée
d'avance : après la campagne, toute cellule à 0 voit son enveloppe
d'évaluation inspectée ; si un artefact d'évaluateur est prouvé (la sortie
utile est correcte, la comparaison échoue sur du bruit d'outillage), la
cellule se rapporte DOUBLE : score brut ET score corrigé-avec-preuve, les
deux publiés, aucun rescoring silencieux, symétrique dans les deux
conditions. On décide de la règle maintenant, avant d'avoir vu une seule
cellule du test, précisément pour qu'elle ne soit pas suspecte.

## Après

Itération 4 → rapport (même format en 5 points, delta vs iter-3) → gel
inconditionnel → campagne des 50 (Google-credentials courues telles
quelles per R4, taux rapportés sur 50 et 48) → rapport final → relecture
manager → intégration au papier. Le bout du tunnel est défini et proche.
