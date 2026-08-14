# Campagne de tests multi-OS — « le bon étage du pipeline de rendu »

*Protocole maître (FR). Les briefs exécutables par des agents IA sont en anglais :
`agent-brief-windows.md`, `agent-brief-macos.md`, `agent-brief-linux.md`, avec un
schéma de résultats commun `results-schema.json`.*

## But

Cartographier, par des tests reproductibles, **où** la perception par représentation
structurée (arbre de rendu / display list / API sémantique) fonctionne, où elle ne
fonctionne pas, et surtout si son périmètre est **prédictible à l'avance** — condition
de son utilisabilité en production par un fournisseur d'IA.

## Hypothèses testées

- **H1 — Complétude** : là où un canal structuré existe, il contient tout ce qui est
  à l'écran (texte, widgets, état), les zones picturales étant *déclarées* (rect) et
  récupérables en crop.
- **H2 — Coût** : la vue structurée coûte nettement moins de tokens qu'un screenshot
  pour le même contenu applicatif.
- **H3 — Économie du changement** : percevoir un changement coûte O(diff), et zéro à
  l'inactivité ; les écrans « vivants » sont suivables en continu.
- **H4 — Actionnabilité** : les coordonnées issues de la vue suffisent pour agir
  (clics aveugles vérifiés).
- **H5 — Prédictibilité (le critère « sûr »)** : la disponibilité et la qualité du
  canal se déduisent d'une **signature de pile détectable avant usage** (modules
  chargés, frameworks liés, process ancestry). Corollaire : les échecs sont
  **explicites** (canal absent → fallback pixels), jamais **silencieux** (vue qui
  diverge de l'écran sans le signaler).

## Le critère de sûreté, formalisé

Un canal est utilisable en production ssi :

1. **Détectable a priori** : un routeur peut décider structure vs pixels *avant*
   d'agir, à partir de signaux fiables (DLL/`.so`/frameworks chargés, nom du
   toolkit, port CDP ouvert, réponse de l'API d'accessibilité).
2. **Échec explicite** : quand le canal ne couvre pas (canvas, zone custom-drawn),
   il le *déclare* (rect opaque) au lieu de renvoyer une vue fausse.
3. **Vérifiable à l'exécution** : on peut auditer la complétude par sondage —
   comparer périodiquement la vue structurée à un screenshot (questions posées aux
   deux, ou re-rendu → diff de pixels quand l'étage le permet, cf. GTK).

Chaque test classe donc les échecs en : `explicit` (absence déclarée, routable),
`silent` (divergence non signalée, **disqualifiant**), `blocked` (OS/permissions,
donnée de couverture), `none`.

## Matrice de couverture visée

| Pile | Windows | macOS | Linux | Canaux à sonder |
|---|---|---|---|---|
| Navigateur/Electron (Chromium) | VS Code, Chrome | Chrome, Slack | fait ✅ | CDP (DOMSnapshot, LayerTree) |
| Office natif | **Word** (cas star) | Word mac | LibreOffice | Modèle objet (COM/UNO), UIA/AX, DirectWrite |
| Toolkit natif moderne | WinUI/XAML (Calculatrice, Réglages) | SwiftUI/AppKit (TextEdit, Finder) | GTK4 fait ✅ | Arbre visuel (XAML diag / CA layers / GSK), API a11y |
| Toolkit natif ancien | Win32/GDI (Notepad++, 7-Zip) | Carbon (rare) | X11 legacy | UIA/MSAA, hooking GDI (optionnel) |
| Qt | OBS ou qBittorrent | idem | Kate/qBittorrent | Scene graph (pas d'API publique — mesurer le refus), a11y |
| Flutter | une app Flutter desktop | idem | idem | VM service / DevTools protocol |
| Java/Swing | JetBrains IDE | idem | idem | Java Access Bridge |
| Pixels purs (contrôle) | un jeu, une vidéo | idem | idem | rien d'attendu — vérifie la loi de périmètre |

Chaque cellule reçoit la **même batterie T1–T6** (voir briefs) et produit le même
JSON — c'est ce qui permet d'agréger la matrice finale du papier.

## Batterie standard (résumé ; détail dans les briefs)

- **T1 lecture** : texte de référence saisi/affiché par l'agent, relu via le canal —
  exactitude caractère par caractère.
- **T2 énumération** : liste des éléments interactifs + boxes vs vérité terrain.
- **T3 état vif** : valeur tapée dans un champ, visible ou non dans le canal.
- **T4 écran vivant** : horloge/progression — le canal voit-il le changement, à quel
  coût, avec quelle latence ?
- **T5 action aveugle** : clic aux coordonnées issues du canal, effet vérifié.
- **T6 complétude picturale** : zones images/canvas déclarées ? crop ciblé possible ?
- **Mesures transverses** : octets/tokens de la vue et du diff, latence de capture,
  signature de détection de pile, classe d'échec, permissions requises.

## Rôles

- **Sandbox Linux (Claude, cette session)** : Chromium/CDP ✅, GTK4 ✅, à compléter :
  Qt, LibreOffice, Flutter, Swing.
- **Machines de Léandre** : agents natifs (ex. Claude Code) exécutant les briefs
  Windows et macOS. Prévoir : droits admin (Windows), permission Accessibilité
  (macOS — **ne pas désactiver SIP** : un refus est une *donnée*, pas un obstacle).
- **Agrégation** : tous les `results/*.json` reviennent dans le repo `pipeline-tap`,
  un script produira la matrice et les figures du papier.

## Livrables attendus de la campagne

1. La **matrice de couverture** remplie (pile × OS × canal × verdict + classe d'échec).
2. Les **chiffres de coût** comparables (structure vs pixels vs diff) par cellule.
3. La **table de prédictibilité** : signature de détection → canal attendu → taux de
   concordance observé (H5 ; c'est LE résultat qui décide « utilisable ou pas »).
4. Les cas d'échec silencieux documentés, s'il y en a (chacun est un contre-exemple
   à discuter dans le papier).
