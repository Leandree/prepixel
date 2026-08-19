# Grande passe autonome : analyse, développement, itération 3

Ordre manager. Cette passe te donne une autonomie élargie : tu analyses
toi-même, tu décides toi-même des chantiers dans le cadre ci-dessous, tu
développes, tu re-testes, tu rends un rapport complet, tu push tout, et le
manager relit. Ce document intègre et remplace ITER-2-RULINGS.md comme
feuille de route ; les règles d'intégrité de DEV-PHASE-PLAN.md et de la
spec v2 §3 restent en vigueur, mot pour mot.

## 1. L'état des lieux, tel que le manager le connaît

- Itération 2 : A 15/18, B 12/18, coût médian B ~1,85× A, pas médians 11,5
  vs 8, plafond de 15 pas atteint 6 fois par B contre 1 par A.
- Déjà en place et validé : driver v2 (action space par référence, échelle
  de résolution loggée, act-guard scopé corrigé label-vs-value, settle,
  memo de trajectoire, budget d'historique aligné sur A, scan de
  contamination par construction `--tools ""` / `--tools Read` +
  `--strict-mcp-config`), routeur CDP opportuniste, D3 largest-sibling,
  reaper de conteneurs.
- Non mesuré : P1 (2 cellules seulement exerçaient CDP ; là où il a tiré,
  succès en 9 pas, 1084 nœuds AT-SPI remplacés par le DOM).
- Non lu : les causes des échecs B d'itération 2 (les TODO de ta table).
- Non expliqué : `libreoffice_writer-adf5e2c3-B` (édit visible dans la vue
  finale, évaluateur à zéro).
- Cadrage coût à garder en tête (ce n'est PAS une excuse, c'est une clef de
  lecture) : le dev set est office-dominant, régime où la loi de densité
  prédit un coût structuré supérieur par écran ; et le harnais
  process-frais-par-pas renvoie la vue complète à chaque pas, donc les
  économies de session (diff, cache) sont hors de portée par construction.

## 2. Les règles qui ne bougent JAMAIS (relis-les avant chaque décision)

1. **Dev/test.** Les 50 pré-enregistrées sont intouchées et invisibles :
   aucun run, aucune lecture de leurs configs pour orienter un choix. Tout
   se joue sur le dev set (les 20 + le supplément navigateur de 8, seed 44,
   à tirer et committer avant les runs). Si tu as besoin de plus de tâches
   dev, tire-les par seed committé, jamais à la main.
2. **Générique seulement.** Toute modification doit passer ce test : on
   aurait pu l'écrire sans avoir vu la tâche qui l'a motivée, en ne citant
   qu'un mécanisme (une interface, un canal, un état). On implémente des
   INTERFACES et des CANAUX, jamais des cas d'app ni des heuristiques de
   tâche. Dans le doute, tu poses la question dans le returns file au lieu
   de coder.
3. **Aucun conseil de comportement dans les prompts.** Le prompt reste :
   tâche, budget, observation, schéma d'action. Si tu as envie d'y écrire
   une phrase d'aide, c'est que la mécanique est incomplète.
4. **Symétrie des budgets.** Même modèle, même plafond de pas, même délai
   post-action, même budget d'historique dans les deux conditions. La
   condition A (agent screenshot OSWorld de référence) ne se modifie
   JAMAIS, à une exception près : un correctif d'infrastructure qui
   s'applique aux deux conditions à l'identique (comme --strict-mcp-config).
5. **Pas de modification d'environnement en cours de tâche.** Jamais de
   relance ou reconfiguration d'app pendant un run. Une affordance de
   plateforme n'est admissible que si elle est établie AVANT toute tâche,
   identiquement dans les VM des deux conditions, sans toucher l'état des
   tâches ni les évaluateurs (voir P9).
6. **Tout est loggé, tout est committé, rien n'est écrasé.** Chaque
   itération dans son dossier, driver pinné par hash dans chaque cellule,
   scan de contamination par run, artefacts conservés. Un résultat
   défavorable se rapporte tel quel ; tu as déjà montré que tu sais le
   faire, continue.
7. **Le gel.** Quand une itération complète n'apporte plus de gain hors
   bruit sur le dev set, tu tags `driver-freeze-v3`, tu déclares le gel
   dans le returns file, et tu t'arrêtes : la campagne des 50 ne se lance
   qu'après relecture du manager.

## 3. Phase 1 : l'analyse (avant toute ligne de code)

Lis les traces, pas les résumés. Pour CHAQUE échec (B ET A) des itérations
1 et 2 :

- remplis la cause à la main, en citant le pas et la ligne de vue ou
  d'action qui la prouve ;
- classe-la : perception (la vue manquait/mentait), actuation (l'action n'a
  pas fait ce qu'elle disait), vérification (le travail est fait mais mal
  confirmé : fichier, évaluateur), budget (mort au plafond en plein flux
  correct), prior modèle (abandon sur croyance), infra ;
- pour chaque cause, écris en une ligne la modification GÉNÉRIQUE qui
  l'adresserait, ou « aucune sans biais » si c'est le cas.

Cas obligatoires : `libreoffice_writer-adf5e2c3-B` (run diagnostique dédié
hors comptage, dump du fichier avant/après, évaluateur rejoué à la main) et
`chrome-93eabf48` (échec des deux conditions : lis ce que l'évaluateur
attend exactement ; une tâche infaisable telle qu'énoncée se documente, ne
se « répare » pas). Ajoute la même lecture pour les 6 morts-au-plafond de
B : flux correct interrompu ou vraie confusion ? Ce tableau de causes est
le PREMIER livrable ; c'est lui qui justifie tes chantiers de phase 2.

## 4. Phase 2 : les chantiers (l'ordre suit ton tableau de causes, pas le mien)

Le backlog du manager, à croiser avec ce que ton analyse trouvera :

- **P1, mesurer enfin le routeur CDP.** Supplément dev navigateur : 8
  tâches parmi les 79 du corpus qui lancent Chrome avec port de debug, seed
  44, exclusions (les 50, les 2 pilotes, Google-credentials), committé
  avant les runs. Rapport séparé dev-core / dev-browser.
- **P9, NOUVEAU : UNO pour les fenêtres LibreOffice.** Même logique de
  signature que CDP-pour-Chrome, et c'est le régime le plus fort de la
  campagne 76 cellules (lectures document à ~18 tokens, actuation sans
  coordonnées). Préalable de faisabilité à instruire AVANT d'implémenter :
  peut-on établir l'acceptation UNO au niveau de l'image/du snapshot VM,
  avant toute tâche, identiquement pour A et B, sans altérer les snapshots
  par tâche d'OSWorld ni les évaluateurs ? Documente la réponse (oui ou
  non) avec preuves dans le returns file ; si oui, implémente le canal dans
  le routeur comme CDP (opportuniste, jamais de relance en cours de tâche,
  même vocabulaire de rôles, ids/guard/échelle inchangés). Si la réponse
  est « seulement en relançant soffice pendant la tâche », c'est NON.
- **P7, continuer sur les logs.** `node-not-found` (8 occurrences) est ta
  piste la plus chaude : si c'est un id résolu sur une vue périmée entre le
  rendu et l'action, c'est un défaut de fraîcheur du driver, générique et
  important (re-résolution par empreinte de l'élément plutôt que par id de
  vue, par exemple). Instruis-le.
- **Vérification d'effets au niveau fichier.** Si le run diagnostique R5
  montre que des édits réels sont perdus entre le document et l'évaluateur
  (sauvegarde, format, chemin), une mécanique générique de type « après
  ctrl+s, relire l'état de sauvegarde exposé par le canal » est admissible ;
  un « re-sauver N fois pour être sûr » ne l'est pas.
- **P8, le modèle, en dernier.** Si après le reste il subsiste des abandons
  par prior dans les deux conditions, une itération dev A/B avec un modèle
  plus fort (même modèle des deux côtés, évidemment) départage plafond de
  modèle et plafond de canal. C'est une mesure, pas une opti.
- **Tes propres trouvailles.** Tu as l'autonomie pour proposer et
  implémenter ce que ton analyse révèle, dans le cadre du §2. Chaque
  chantier auto-décidé s'annonce dans le returns file AVANT son
  implémentation, avec une ligne de justification générique. En cas de
  doute sur la frontière du biais : tu demandes, tu ne codes pas.

## 5. Phase 3 : itération 3 et rapport final

- Itération 3 = 20 tâches dev-core + 8 dev-browser, deux conditions,
  interleavé, driver pinné, scan par run, mêmes métriques + les nouvelles
  (canal par pas : atspi/cdp/uno ; verdicts guard ; morts-au-plafond).
- Rapport final dans le returns file, dans cet ordre : (1) le tableau de
  causes de la phase 1 ; (2) la liste EXHAUSTIVE des modifications faites,
  chacune avec sa justification générique et son commit ; (3) les résultats
  iter-3 vs iter-2, dev-core et dev-browser séparés ; (4) ce que tu n'as
  PAS fait et pourquoi (y compris tout ce qui t'a tenté et que tu as jugé
  biaisant : c'est aussi un livrable) ; (5) ta recommandation gel / pas gel
  au regard du critère §2.7.
- Push complet : code, traces, rapport. Le manager relit tout, tranche le
  gel, et la campagne des 50 suit.

Un dernier mot. Sur les deux dernières remises, tu as retiré ton propre
résultat favorable et tu as refusé de relever un plafond qui aurait acheté
un point à B. C'est exactement le niveau demandé. La consigne de cette
passe est simple : trouve tout ce qui peut être amélioré sans tricher, et
si le résultat final reste défavorable au canal, il se publiera tel quel,
avec ton nom de harnais dessus. La valeur du papier est dans l'honnêteté de
la mesure, pas dans le sens du résultat.
