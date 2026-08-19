# Pré-enregistrement : artefacts d'évaluateur dans la campagne des 50

Règle décidée AVANT d'avoir vu une seule cellule du test (ordre manager,
`manager_orders/REPONSEGRANDEPASSE.md`), précisément pour qu'elle ne soit
pas suspecte. Motivée par un cas prouvé sur le dev set :
`multi_apps-da922383-A` (iter-3) — le checker de l'évaluateur imprime
`[1, 1]` (la valeur attendue), mais `pip install PyMuPDF` exécuté au
moment de l'évaluation tire une version dont l'alias `fitz` imprime un
avertissement de dépréciation dans la sortie capturée, et `exact_match`
compare la chaîne brute : `'warning: …\n[1, 1]\n' ≠ '[1, 1]\n'` → score 0
pour une tâche accomplie. Preuve : enveloppe d'évaluation dans
`campaign/results/dev/iter-3/multi_apps-da922383-A/` et rapport iter-3.

## La règle

1. Après la campagne (jamais pendant), TOUTE cellule à score 0 voit son
   enveloppe d'évaluation inspectée (la ligne `{'error': …, 'output': …,
   'returncode': …}` du log driver).
2. Un artefact d'évaluateur est retenu si et seulement si : la sortie
   utile du checker est correcte ET la comparaison échoue sur du bruit
   d'outillage (warning, encodage, préfixe parasite) — preuve citée
   (enveloppe verbatim + règle `expected` de la tâche).
3. Une cellule à artefact prouvé se rapporte DOUBLE : score brut ET score
   corrigé-avec-preuve, les deux publiés côte à côte. Aucun rescoring
   silencieux, aucun score remplacé.
4. La règle est SYMÉTRIQUE : elle s'applique aux deux conditions à
   l'identique, par le même inspecteur, sur le même critère.
5. Les évaluateurs ne sont jamais réparés ni contournés pendant les runs
   (règle constante depuis chrome-93eabf48 et da922383).

Périmètre : campagne des 50 pré-enregistrées (et, par extension, tout
rapport agrégé qui les cite). Le dev set reste rapporté brut avec causes
manuscrites, comme dans les rapports d'itération.
