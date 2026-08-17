# Windows — independent replication pass

**Date:** 2026-08-17
**Agent:** Claude (Fable 5), independent replication run
**Scope:** three carrier cells re-measured **from scratch** — the app reopened / the
script rerun — *before* looking at the origin cell's recorded numbers. I compared
only after locking my own measurement. Origin cells were **not modified**; every
output of this run lives under `campaign/results/verification/` (harnesses redirect
their artifact paths, so no origin artifact was overwritten either).

**Discipline:** read-only, throwaway documents only (Word doc closed without saving;
OBS opened read-only and closed; duel pages are generated throwaways), action
allowlist respected.

**Method note on independence.** The three replication harnesses reuse the *exact*
measurement logic of the origin scripts — the duel generator + `distill-hardened.mjs`
verbatim, and the shared `uia_probe.py` / `guard.py` helpers — with the *only*
change being output paths pointed at the verification folder. That makes this a
faithful re-run of the same measurement, not a re-implementation that could drift on
its own formula. Harnesses: `repl_duel.mjs`, `score_duel.mjs`, `repl_word.py`,
`repl_obs_guard.py`.

| # | Cell | Origin headline | My re-measurement | Verdict |
|---|------|-----------------|-------------------|---------|
| 1 | windows-word-object-model | 18 tok / 79 B; **80×** vs screenshot (1446 tok) | 18 tok / 79 B (exact); **150×** vs screenshot (2706 tok) | **MATCH on structure, ÉCART on the ratio** |
| 2 | windows-obs-qt-uia | preview energy 0.245 / edge 0.0245, both votes, silent→explicit | energy **0.245** / edge **0.0245**, both votes, silent→explicit | **MATCH (exact)** |
| 3 | windows-precision-cost-duel | 391 tok vs 1366; 18/18 accuracy | 391 tok vs 1366; 18/18 (and 60/60 full) | **MATCH (to the byte)** |

---

## Cell 1 — windows-word-object-model (the "star" 80× case)

**What I did (blind to the recorded numbers):** `Dispatch('Word.Application')`, new
throwaway document, inserted the fixed sentinel
`WORD-TAP-SENTINEL The quick brown fox 12345 café naïve élève 日本語 END`, read it back
through `Range().Text`, counted tokens with the shared `text_tokens` (chars/4),
captured the Word window rect and computed `image_tokens` on it, then closed the
document **without saving**. Same formulas as the origin (imported from `uia_probe`).

**My numbers**

| quantity | my value |
|---|---|
| COM read-back char-exact (accents + CJK) | **true** |
| doc structured view | **18 tokens / 79 bytes** |
| write / read latency | 13.4 ms / 10.1 ms |
| Word window rect | **[-8, -8, 1936, 1048]** (maximized) |
| window screenshot cost | **2706 tokens** |
| star ratio (screenshot ÷ doc) | **150.3×** |
| cross-channel: sentinel seen via UIA `distill()` | **false** |
| idle: two reads identical | true |

**Origin numbers:** 18 tok / 79 B, screenshot **1446 tok**, ratio **80×**.

**Verdict: MATCH on the structured side, genuine ÉCART on the headline ratio.**

- The **structured cost is perfectly reproducible**: 18 tokens / 79 bytes, char-exact
  read-back including `café naïve élève 日本語`. Identical to the origin, to the byte.
- The **80× multiplier did not reproduce — I measured 150×.** This is not noise and I
  will not soften it: the ratio's numerator is the *screenshot* cost, which is a pure
  function of the Word window's pixel area at capture time. In my run Word opened
  **maximized** (1936×1048 ≈ 2.03 M px → 2706 tok). The origin's 1446 tok corresponds
  to a **non-maximized** window of ≈1.08 M px (≈1280-wide). Same 18-token document on
  both sides; only the window geometry moved, and it moved the multiplier by ~1.9×.
- **Honest reading:** the *direction and order of magnitude* of the star claim hold —
  the object model is ~two orders of magnitude cheaper than a screenshot of the same
  content, and in my run it was actually *more* extreme (150×). But the specific
  number **"80×" is not a stable constant**; it is "18 tokens vs whatever a screenshot
  of the window happens to cost," and that denominator swings with window state and
  screen resolution. A carrier cell that pins a single multiplier as *the* headline is
  environment-sensitive; the robust, replicable statement is the invariant 18-token /
  79-byte structured cost, not the ratio.

**Second observation (a confirmation, not a new divergence).** My cross-channel check
found the COM-written text **absent** from the UIA view (`sentinel_seen_via_uia:
false`). That *reproduces* the extractor gap the origin already flagged in its own
METHOD NOTE: `distill()`/`uia_probe` reads `ValuePattern`, and Word's document text is
only reachable via a direct `TextPattern` read on the `DocumentControl`. I did **not**
run the `TextPattern` follow-up myself, so I neither confirm nor dispute the origin's
"text IS in UIA via TextPattern" resolution — I only confirm the `ValuePattern`-based
distiller sees nothing, exactly as the origin documented. Not a channel divergence; an
extractor limitation, reproduced.

*Artifacts:* `artifacts/word-com-doc-text-REPL.txt`, `artifacts/word-uia-view-REPL.txt`,
`artifacts/word-com-shot-REPL.png`.

---

## Cell 2 — windows-obs-qt-uia (silent → explicit mitigation)

**What I did (blind to the recorded numbers):** launched OBS (`--disable-updater`,
read-only), walked its UIA tree (185 nodes), computed structural coverage, found the
structure-empty big regions, PrintWindow-captured the OBS window's own surface, cropped
each suspect and ran **both** guard votes — `content_energy` (Guard A) and
`edge_fraction` (the recalibrated second vote) — then closed OBS.

**My numbers**

| quantity | my value |
|---|---|
| window title | `OBS 31.0.3 - Profil: Untitled - Scènes: Untitled` |
| window class (a-priori signature) | `OBSBasic` (Qt widget top-level) |
| nodes walked | 185 |
| structural coverage of client area | **46.5 %** |
| suspect auto-detected | **`OBSBasicPreview` [421, 175, 522, 351]** |
| Guard A content-energy | **0.245** → vote **true** (≥ 0.01) |
| second vote edge-fraction | **0.0245** → vote **true** (≥ 0.01) |
| verdict | **SILENT → declare-opaque** |
| re-emitted explicit line | `[pixels] group 421,175,522,351 "OBSBasicPreview" [unverified: pixels show content]` |
| full-window screenshot cost | **1275 tokens** |
| crop cost | 245 tokens (522×351 ÷ 750) |
| crop content (eyeball check) | painted text **"On arrive bientôt"** over black |

**Origin numbers (mitigation + recalibration_rerun):** same rect `421,175,522,351`,
energy **0.245** / edge **0.0245**, **both votes positive**, coverage **46.5 %**,
full-shot **1275 tok**, identical explicit re-emission line, crop "plainly shows the
painted 'On arrive bientôt'".

**Verdict: MATCH — exact, on every load-bearing quantity.** The preview region is
detected as a structure-empty container, both guard votes fire (energy 0.245 with >2×
margin, edge-fraction 0.0245 with >2× margin), and the region is re-emitted as an
explicit `[pixels]` declaration — the silent→explicit mitigation the cell claims. My
independent crop visibly contains "On arrive bientôt", confirming the pixels genuinely
carry content the UIA tree left unnamed. The window opened at the same size as the
origin run (full-shot 1275 tok both times), so even the screenshot cost coincides.

*Artifacts:* `artifacts/obs-printwindow-REPL.png`, `artifacts/obs-guard-region0-REPL.png`
(the crop), `artifacts/obs-guard-report-REPL.json`.

---

## Cell 3 — windows-precision-cost-duel

**What I did (blind to the recorded numbers):** reran the duel generator verbatim
(mulberry32, seeds `1000+97i`, N=20), headless installed Chrome, viewport 1280×800,
screenshotting + distilling each page with `distill-hardened.mjs`, then scored accuracy
by answering 3 tasks/page (row count, Pending count, max-total customer) **purely by
parsing my own distilled views**, checked against the generator's own truth.

**My numbers**

| quantity | my value | origin |
|---|---|---|
| avg structured view | **391 tok / 1577 B** | 391 tok / 1577 B |
| avg screenshot | **1366 img tok / 38 007 PNG B** | 1366 tok / 38 007 B |
| token ratio (pixels ÷ structured) | **3.5×** (1366/391 = 3.49) | 3.49× |
| byte ratio | **24.1×** | 24.1× |
| accuracy, structured, 6 pages × 3 tasks | **18/18** | 18/18 |
| accuracy, structured, all 20 pages | **60/60** (bonus) | — |
| accuracy, pixels | legible & identical (spot-checked page-0) | 18/18 |

**Verdict: MATCH — to the byte.** `391 tok structuré vs 1366` confirmed exactly, along
with `view_bytes 1577`, `avg PNG 38 007 B`, and both ratios (3.49× token, 24.1× byte).
Accuracy `18/18` confirmed on the 6-page set, and I extended it to **60/60** across all
20 pages for robustness.

**Methodology difference (disclosed, not a divergence).** The origin scored accuracy
with two blind subagents (one seeing only views, one only screenshots). I instead
scored the **structured** condition with a deterministic parser over my own views —
a stricter, non-model reader — and confirmed the **pixels** condition by viewing
page-0's screenshot and verifying it is a faithful, fully-legible transcription of the
same 9 orders/totals/statuses (so a reader answers identically). Same 18/18 result;
the structured side is arguably verified more strictly here, the pixels side by
legibility rather than a second blind agent.

*Artifacts:* `duel-windows-replication/duel-cost.json`, `duel-windows-replication/page-*.view.txt`,
`duel-windows-replication/shots/page-*.png`.

---

## Summary

- **Two of three cells replicate cleanly**, one (OBS) exact on every guard quantity and
  one (duel) exact to the byte on cost and matching on accuracy. No silent turn there.
- **One cell (Word) carries an environment-sensitive headline.** The structured cost
  (18 tok / 79 B, char-exact) is rock-solid; the advertised **"80×" ratio is not a
  stable constant** — I independently measured **150×** because Word opened maximized.
  The qualitative claim survives (and is stronger in my run); the specific multiplier
  should be read as window-geometry-dependent, not a fixed property of the channel.
- No origin cell or origin artifact was modified. All replication outputs are under
  `campaign/results/verification/`.
