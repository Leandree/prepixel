# Campagne OSWorld : comparaison agent-level pixels vs prepixel

Objectif : répondre au point n°2 du review. Le papier mesure l'entrée d'un agent,
jamais un agent. Cette campagne court un sous-ensemble d'OSWorld dans deux conditions
(screenshot-only vs prepixel) avec le même modèle, le même scaffold et les mêmes
limites, et mesure le taux de complétion et le coût réel par tâche. C'est le résultat
qui change le statut du papier (rapport technique → papier de conférence).

## 0. Machine et prérequis

Hôte recommandé : la machine Linux (Debian 13). OSWorld tourne dans une VM Ubuntu ;
le provider Docker demande KVM (`ls /dev/kvm` doit exister). Alternative : VMware
Workstation sur la machine Windows si KVM indisponible.

Setup : cloner `github.com/xlang-ai/OSWorld` et suivre STRICTEMENT le README officiel
du repo (ne pas improviser les flags depuis ce protocole, ils peuvent avoir changé).
Faire un smoke test d'UNE tâche avec l'agent d'exemple du repo avant toute autre chose,
et le rapporter dans le fichier de retour.

## 1. Pré-enregistrement du sous-ensemble (AVANT tout run)

- 50 tâches, échantillonnées par strate de domaine avec un RNG seedé (seed=42), sur
  les domaines : os, libreoffice_calc, libreoffice_writer, libreoffice_impress,
  chrome, gimp, vlc, thunderbird, multi_apps. Proportionnel à la taille de chaque
  domaine, minimum 3 par domaine.
- Écrire la liste dans `campaign/osworld/tasks-selected.json` et la COMMITTER avant
  le premier run. Aucune tâche ne peut être ajoutée/retirée après (si une tâche est
  infra-cassée, la marquer `infra_failure` avec preuve, ne pas la remplacer).

## 2. Les deux conditions

Tout est identique entre A et B (modèle, prompt système hors observation, température,
max 15 pas/tâche, mêmes évaluateurs OSWorld) SAUF l'observation.

**Condition A (baseline pixels).** Observation = screenshot OSWorld standard, un par
pas. C'est l'agent screenshot du repo OSWorld, sans modification.

**Condition B (prepixel).** Observation = la vue structurée :
- Adapter la sortie a11y-tree d'OSWorld (ou AT-SPI directement dans la VM) vers notre
  grammaire de ligne `type x,y,w,h contenu` (spec : `src/distill-hardened.mjs` et
  §3.1 du papier). Écrire l'adaptateur dans `campaign/osworld/distill-osworld.*`.
- Coverage-guard actif : toute région déclarée vide par la structure est spot-checkée
  (seuils du repo : energy>=0.01 OU edge>=0.01, crop par fenêtre) ; si le guard tire,
  la région est remontée à l'agent comme `[pixels] ...` et l'agent PEUT demander le
  crop pixel de ce rectangle uniquement (compté dans le coût de B).
- Act-guard actif : après chaque action, re-lecture ciblée ; verdict
  EXPLICIT_FAILURE / UNVERIFIED / CONFIRMED joint à l'observation suivante.
- Premier pas = vue complète ; pas suivants = diff (protocole du papier §4). Si le
  diff est inapplicable (navigation complète), vue complète re-émise et logguée.

Modèle : le même string de modèle exact pour A et B, température 0, noté dans chaque
résultat. Le choix du modèle est libre mais FIXE pour toute la campagne.

## 3. Métriques par tâche (JSON schema-validé, un fichier par tâche×condition)

```
{ task_id, domain, condition: "A"|"B", model, success: bool (évaluateur OSWorld),
  steps, input_tokens, output_tokens, wall_clock_s,
  pixel_fallbacks (B: nb de crops demandés), guard_hits (B), act_verdicts (B),
  infra_failure: bool, notes }
```

Artefacts par tâche : la trace complète (observations envoyées + actions) sur disque,
comme pour la campagne 76-cellules. Ajouter le schéma dans `campaign/schema/` et le
brancher dans `validate.py` + `aggregate.py`.

## 4. Règles d'intégrité (identiques à la campagne précédente)

1. Interleaver : tâche 1 en A puis en B, tâche 2 en A puis en B, etc. (pas 50×A puis
   50×B), pour neutraliser toute dérive d'environnement.
2. Pas de re-run sauf `infra_failure` documenté (VM crashée, timeout réseau) ; jamais
   parce que « le résultat semble faux ». Chaque re-run est loggué.
3. Ne calculer AUCUN agrégat avant que les 100 runs (50×2) soient terminés et commis.
4. Chaque cellule = JSON validé par schéma AVANT commit ; `validate.py` fait foi.
5. Le retour se fait via `campaign/results/osworld-agent-returns.md` : setup, smoke
   test, déviations du protocole, et tout ce qui a été bizarre, même mineur.

## 5. Ce que le papier attend en sortie

- Taux de complétion A vs B, global et par domaine.
- Coût réel moyen/médian par tâche (input tokens) A vs B, et par tâche réussie.
- Pas moyens par tâche réussie.
- Pour B : taux de fallback pixel par pas, hits du coverage-guard, distribution des
  verdicts act-guard. Chaque hit du guard sur cette campagne est une exposition
  HELD-OUT (le guard n'a pas été calibré sur ces apps) : c'est aussi la validation
  held-out que le review réclame au point 3.
- Honnêteté : si B perd en complétion, ça se publie tel quel. Le papier tient sur la
  caractérisation ; le résultat agent-level est informatif dans les deux sens.
