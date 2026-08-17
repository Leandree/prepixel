# Driver v2 : la mécanique dans le harnais, pas dans le prompt

Directive manager suite à l'analyse du pilote v1. Principe directeur, non
négociable : **tout ce qu'un runtime peut calculer de façon déterministe
appartient au driver, jamais au prompt.** Un utilisateur final n'expliquera
pas à son agent qu'il faut viser le centre d'un bouton ; si le pilote a eu
besoin de le faire, c'est que la couche d'actuation était incomplète. C'est
d'ailleurs la thèse du papier : la structure DONNE le grounding. Un modèle
qui recalcule de la géométrie à partir de `x,y,w,h` refait à la main ce que
le canal fournit déjà.

## 1. Diagnostic du pilote v1 (traces à l'appui)

| # | Symptôme observé | Cause | Nature de la faute |
|---|---|---|---|
| 1 | os-B pas 5→6 et 7→8 : clics au coin exact du rect (1315,176), valeur inchangée, retry | le modèle convertit lui-même rect → point | géométrie laissée au modèle |
| 2 | chrome-B pas 8-10 : re-navigation complète après le toggle DNT | `toggle-button` sans état `checked` | état existant (STATE_CHECKED) non émis |
| 3 | verdict CONFIRMED sur une action ratée (os-B pas 5) | act-guard = diff de vue ENTIÈRE, et l'horloge GNOME est dans la vue (change chaque minute) | vérification non scopée |
| 4 | chrome-B pas 4 : WAIT facturé, « 1 result » sans ligne de résultat | arbre web paresseux ; pas de settle ni de re-probe | asynchronie gérée par le modèle au lieu du driver |
| 5 | chrome-B pas 2 et 6 : scrolls exploratoires | hors-viewport jeté par le filtre de visibilité | avantage « toute la page » non implémenté |

Aucune de ces causes n'est le canal. La vue a toujours été honnête (c'est
`value="80.0"` inchangé qui a permis au modèle de rattraper). C'est le
driver qui sous-utilise le canal : la doctrine « suspecter le routeur avant
le canal » du papier, rejouée ici.

## 2. Architecture v2 : action space par référence d'élément

### 2.1 La vue porte des identifiants

Chaque ligne de la vue reçoit un id stable pour l'étape :

```
e17 spin-button 1315,176,118,34 "columns" value="80" state=enabled,focusable
e18 toggle-button 1281,781,27,17 "Do Not Track" state=checked:false
e19 [offscreen] link 291,1240,213,20 "Advanced settings"
```

Règles d'id : séquentiels dans l'ordre de la vue, régénérés à chaque étape
(pas de persistance inter-étapes à garantir ; le modèle référence toujours
la vue courante). Le renderer du diff conserve la correspondance ligne→id.

### 2.2 Les actions référencent des éléments, le driver résout la géométrie

Le modèle répond par une action structurée, plus aucun code pyautogui :

```
{"action":"click","target":"e17"}
{"action":"set_value","target":"e17","value":"132"}
{"action":"toggle","target":"e18","to":true}
{"action":"type","text":"do not track"}          (dans le focus courant)
{"action":"key","keys":"ctrl+alt+t"}
{"action":"scroll_to","target":"e19"}
{"action":"crop","target":"e21"}                  (rect [pixels] déclaré)
{"action":"wait"} {"action":"done"} {"action":"fail"}
```

Résolution par le driver, en échelle de préférence, LOGGÉE à chaque action :

1. **Action de plateforme** quand elle existe : AT-SPI `EditableText.set_text`
   pour set_value, `Action.do_action("click"/"press"/"toggle")`,
   `Component.grab_focus` avant un type. C'est l'actuation sans coordonnées
   du §5 du papier, en vrai.
2. **Synthèse pointeur au point d'ancrage calculé** sinon : centre du rect
   `(x+w/2, y+h/2)`, clampé au viewport ; si l'élément est partiellement
   occulté par un rect au-dessus dans le z-order, ancrage au centre de la
   sous-région visible.
3. Échec de résolution (id inconnu, rect vide) : le driver renvoie une
   observation d'erreur au modèle, il ne devine JAMAIS.

Le prompt ne contient plus AUCUN conseil de comportement (ni « vise le
centre », ni « préfère les raccourcis », ni « ne devine pas les
coordonnées ») : le schéma d'action rend ces fautes impossibles par
construction. Le prompt = tâche, budget d'étapes, observation, schéma. Rien
d'autre.

### 2.3 L'adaptateur émet l'état, pas seulement la géométrie

Depuis AT-SPI, pour chaque élément : `checked`, `pressed`, `selected`,
`expanded`, `focused`, `enabled`, `value=` (déjà fait pour spin), et le
compte déclaré des conteneurs listes/tables. Un toggle sans son état est une
vue qui ment par omission ; c'est notre propre définition du §6.

### 2.4 Act-guard v2 : automatique, scopé, et silencieux quand tout va bien

Après CHAQUE action ciblée, le driver re-lit l'état du SEUL élément visé
(rect + marge de 8 px), compare, et produit le verdict du contrat du papier :
`err != 0` → EXPLICIT_FAILURE ; état inchangé → UNVERIFIED ; état changé →
CONFIRMED. Corrections v1→v2 :

- diff scopé à l'élément, jamais la vue entière ;
- la barre système (bandeau y<28 : horloge, Activities) est exclue de TOUT
  diff, guard comme protocole de diff inter-étapes ;
- le verdict est joint à l'observation suivante automatiquement ; UNVERIFIED
  est remonté au modèle avec l'état relu (`still value="80"`), et c'est le
  MODÈLE qui décide de la suite. Aucun retry caché dans le driver : un
  driver qui re-clique tout seul devient un agent, et la comptabilité « une
  décision de modèle par étape » saute.

Test d'acceptance du guard (hors runs, sandbox) : rejouer le scénario
os-B pas 5 (clic au coin + saisie ratée) et vérifier verdict UNVERIFIED ;
une action sur un label statique doit aussi rendre UNVERIFIED.

### 2.5 Settle et re-probe : l'asynchronie appartient au driver

Après chaque action : re-capture de l'arbre jusqu'à deux captures
consécutives identiques ou timeout 2 s, AVANT de rendre le prompt. Délai
post-action fixe IDENTIQUE dans les deux conditions (symétrie A/B ; A le
passe en sleep, B en settle). Le WAIT du modèle devrait devenir rarissime ;
s'il survit au settle, c'est une info (chargement long réel).

Cas « compte déclaré > 0, zéro ligne exposée » (le « 1 result » de Chrome,
forme rekordbox du papier) : le driver re-walke le sous-arbre une fois
(re-probe façon AT-latch) ; si toujours vide, il ÉMET la contradiction dans
la vue (`[self-inconsistent: declares 1 result, exposes 0 rows]` + rect
déclaré `[pixels]` croppable). Chaque déclenchement est loggé : c'est de
l'exposition held-out des guards, à comptabiliser pour le papier.

### 2.6 Hors-viewport : émis, marqué, actionnable

Les nœuds qui échouent le filtre de visibilité pour cause de position (et
non d'état hidden) sont émis en `[offscreen]` avec leurs coordonnées de
page. `scroll_to` les rend actionnables : le driver calcule le scroll,
re-capture, re-résout la cible dans la nouvelle vue. Le modèle ne calcule
jamais un delta de scroll.

## 3. Ce que le driver n'a PAS le droit de faire

Le driver v2 est de la mécanique déterministe, pas de l'intelligence :

- aucune heuristique de tâche, aucun replanning, aucun retry autonome ;
- chaque mécanique est loggée par étape (rung de résolution, temps de
  settle, temps de guard, re-probes) pour la comptabilité de coût du
  papier : le coût du harnais se rapporte séparément du coût modèle ;
- la condition A reste l'agent screenshot de référence d'OSWorld, INCHANGÉ.
  L'asymétrie est le sujet même de l'étude : chaque condition utilise
  l'interface naturelle de son canal (A : pixels + coordonnées estimées ;
  B : structure + références résolues). À documenter dans l'amendement de
  protocole, pas à « équilibrer » artificiellement.

## 4. Séquence d'exécution

1. Implémenter 2.1 à 2.6 (adaptateur, renderer, résolveur, guard v2,
   settle/re-probe, offscreen). Committer AVANT tout run.
2. Tests d'acceptance sandbox (hors runs comptés) : (a) scénario coin-raté →
   UNVERIFIED ; (b) toggle → état visible avant/après ; (c) page longue →
   `[offscreen]` + `scroll_to` fonctionnel ; (d) champ de recherche Chrome →
   settle absorbe le peuplement, zéro WAIT ; (e) label statique actionné →
   UNVERIFIED.
3. Pilote v2 : les 2 MÊMES tâches hors pré-enregistrement, dans
   `results/osworld-pilot-v2/` (v1 conservé tel quel, jamais écrasé).
   Attendu : disparition des retries géométriques, des redos d'état et des
   WAIT ; les écarts d'étapes restants sont de l'information honnête.
4. Retour dans le returns file avec le tableau v1 vs v2 par étape.
   PAS de go campagne avant validation manager du pilote v2.

## 5. Note pour le papier (le manager s'en charge, pour contexte)

Ce driver v2 est la « semantic compositor → deployable perception layer »
annoncée en travaux futurs, au périmètre d'OSWorld : ids + résolution
d'ancrage + états + guard scopé + settle. Les findings du pilote v1
(coin-raté, toggle sans état, CONFIRMED dilué par l'horloge) deviennent des
exemples mesurés de la section méthode : ils montrent que le contrat de
sûreté doit être porté par la couche, pas par la docilité du modèle.
