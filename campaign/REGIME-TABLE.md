# When to use prepixel — the regime map (measured, all three OSes)

The single table a paper reader needs: the win is not uniform, it is a function of
what the screen IS. Pixel cost is **flat** (set by viewport/panel resolution);
structured cost scales with **information density** and with **change over time**.
So the method wins decisively in some regimes, ties in others, and loses in a few —
and every one of those is measured, not asserted.

## Cost regimes (single screen unless noted)

| Regime | Representative cells | Structured vs pixels | Winner |
|---|---|---|---|
| **Document model** (Word/Pages/LibreOffice) | Word COM 18 tok vs 1446 | **80x** (Win), 65x (Linux), Pages 21 tok (mac) | **Structure, no contest** |
| **High-DPI / Retina screen** | 2× capture | 438 vs 4784 tok high-res tier | **~11x structure** |
| **Change / living screen** | clock, feed | ~20 tok/tick vs 299–1366; **idle = 0** | **Structure, no contest** |
| **Full multi-step session** | 20-step sim | 626 vs 28,686 tok | **45.8x structure** |
| **App UI, moderate density** | orders duel (n=20) | 391 vs 1366 | **3.5x structure** |
| **Real web, averaged (16 sites)** | Amazon…HN | ~1.0–1.2x (totals/median) | **≈ parity** |
| **Dense static text** | Hacker News, Wikipedia | 0.47–0.8x | **Pixels** |
| **Small control-dense panel** | Calculator (native) | 666 vs 243 tok | **Pixels (2.7x)** |
| **Custom-drawn, unannotated** | FL Studio, games | structure empty → guard→crop | **Pixels (declared)** |

## Capability regimes (independent of cost)

| Property | Structure | Pixels |
|---|---|---|
| Exact click coordinates | given, free | must be grounded (hallucination risk) |
| Off-viewport content | whole page/tree | one screen only |
| Semantic actuation (no coords) | Word/Shell/UNO: yes | no |
| Reads painted/canvas/game content | no → **declares** blind spot | yes |
| Cost under animation/idle | diff / 0 | full every frame |
| Font-fallback / glyph faithfulness | reports text held, not painted | shows actual glyphs |

## The decision rule a router encodes

1. Detect stack signature → known channel + known coverage class (predictable a priori; 57/57 cells).
2. If a document/object model exists (Office/Shell/iWork) → use it (dominant).
3. Else read the structured tree; run **coverage-guard**: any region structure calls
   empty but whose pixels show content → declare `[pixels] … [unverified]` and crop
   (this is what makes the 3 Windows silent cells explicit).
4. Stream **deltas**, not full views, across the session (45x lever); reuse the
   prompt cache on the stable identity.
5. Where coverage is ~0% (games, unannotated custom-drawn, elevated windows) → pixels,
   declared, not silently "empty".

Net: **structure as backbone, pixels as a declared, guarded fallback**, chosen per
region from a signature known before acting — cheaper in the regimes that dominate
long-horizon agent work (change, document editing, high-DPI, multi-step sessions),
at parity on a single real-web screen, and never silently wrong once the guard runs.
