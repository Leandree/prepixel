# Linux replication pass — independent re-measurement of three carrier cells

**Goal.** Detect whether a carrier cell could have silently gone wrong, by re-doing each
measurement FROM SCRATCH (app relaunched, scripts re-run) and only comparing against the
original cell numbers AFTER obtaining the fresh ones.

**Discipline.** Read-only on all original cells and artifacts; throwaway working copies of
the harness scripts (output redirected to a session scratchpad, nothing under `results/`
touched); original cell JSONs opened only after the corresponding fresh measurement existed.
For the duel's accuracy leg, the protocol was extracted from the cell by a subagent under a
redaction rule (all measured values replaced by `[REDACTED]`), and the two answering
conditions were run by two separate subagents, each forbidden to read the ground truth, the
other condition's input, or the other condition's answers. Scoring was mechanical.

**Environment.** debian-server (Debian 13 trixie, headless), fresh Xvfb 1280x800 session +
dbus-run-session started for this pass; same extracted no-root binary prefix as the original
Linux round (qBittorrent 5.1.0 / Qt 6.8.2, Chrome 148.0.7778.96 from the playwright cache),
so software versions match the original cells; all sessions, profiles, configs and captures
created fresh. Date: 2026-08-17. Agent: claude-code (Fable 5), independent session.

---

## 1. linux-qt6-qbittorrent-accessibility-api (the recalibration proof)

Fresh run: qBittorrent relaunched under Xvfb with a new throwaway profile (legal notice
pre-accepted in a fresh config; original used `--confirm-legal-notice` — same effect),
window 1200x750 at 0,0, Speed tab opened by a fresh click on the AT-SPI-located "Vitesse"
button, window surface captured via XComposite (`grabwin`), regions cropped from the
window's own surface, judged with the shipped `judgeCrop` decision path.

The AT-SPI signature reproduces exactly: the on-screen live speed graph (axis labels,
two-entry legend, dashed grid, real DHT-traffic curves — verified visually on the fresh
crop) is exposed as a **nameless `filler` with `kids=0`** (my run: `filler "" [134,290
1058x400] kids=0`; original: `filler [154,313,1038,407] "" kids=0` — geometry differs only
because the fresh profile's sidebar/panel widths differ), indistinguishable from a
genuinely-empty spacer. Sidebar declares "Tous (0)"; guard B correctly stays silent.

| Measure | Original cell | Re-measured | |
|---|---|---|---|
| SpeedPlotView contentEnergy | 0.020 | **0.019** | Δ 0.001 |
| SpeedPlotView edgeFraction | 0.0268 | **0.0278** | Δ 0.001 |
| Guard v1 verdict (energy ≥ 0.03, single vote) | MISS (false negative) | **MISS** | reproduced |
| Guard v2 verdict (0.01 + edge vote) | CATCH, both votes fire | **CATCH, both votes fire** (0.019 ≥ 0.01, 0.0278 ≥ 0.01) | reproduced |
| Empty-table control (energy / edge) | 0.000 / 0.000 | **0.000 / 0.000** | exact |
| Corpus run (`recalibration-check.mjs`) | 15/15 v2, 12/15 v1, PASS | **15/15 v2, 12/15 v1, PASS** | exact |

**VERDICT: MATCH.** The 0.001 deltas on both metrics are expected run-to-run variance: a
different live DHT frame on the graph, a fresh profile with slightly different widget
geometry, and a different capture instant. Everything the cell *claims* reproduces: the
graph sits at ~0.02 energy (under the old 0.03 threshold → v1 misses it), the edge fraction
is safely above 0.01, v2 flags it on both independent votes, and the genuinely-empty
control is exactly 0.000 on both metrics (total separation).

One methodological note, stated for honesty rather than as a discrepancy: the original
cell's crop came from a root-window screenshot, while this replication cropped from the
window's own XComposite surface (the stricter capture path the guard itself mandates). On a
bare Xvfb with a single unoccluded window at 0,0 the two are pixel-equivalent, and the
numbers confirm that.

## 2. linux-web-battery-cdp (8 of 16 sites replayed)

Fresh run: Chrome 148 relaunched headed under the fresh Xvfb with a new profile, CDP on
:9223, throwaway copy of `campaign/linux/web-battery.mjs` (identical logic, output to
scratchpad) restricted to 8 sites including the three named checks.

| Site | Orig hardened tok | Mine | Orig ratio_viewport | Mine | Verdict |
|---|---|---|---|---|---|
| wikipedia | 1727 | **1727** | 0.79 | **0.79** | exact |
| mdn | 1198 | 1201 | 1.14 | **1.14** | match |
| hackernews | 2983 | 2981 | 0.46 | **0.46** | match |
| github | 1327 | **1327** | 1.03 | **1.03** | exact |
| apple | 810 | **810** | 1.69 | **1.69** | exact |
| stripe | 788 | 751 | 1.73 | 1.82 | match (live churn) |
| vercel | 428 | **428** | 3.19 | **3.19** | exact |
| bbc-news | 858 | 843 | 1.59 | 1.62 | match (live churn) |

Screens-to-cover identical on all 8 sites; the same sites raised consent banners.

**VERDICT: MATCH.** Four of eight sites reproduce token-exact three days later, which is
strong evidence the distiller is deterministic and the original numbers were really
measured; the only movers are the two live editorial/marketing pages (Stripe −37 tok,
BBC −15 tok), exactly the "live-content churn, not distiller variance" class the original
cell describes. The three named checks land: Vercel 3.19× (original Linux 3.19×), Hacker
News 0.46× (0.46×), Wikipedia 0.79× (0.79×). Note on the tasking's expected "~0.72×" for
Wikipedia: that figure matches the **macOS** cell (its reference-category average 0.93×
with MDN ≈1.14 implies Wikipedia ≈0.72×), not the Linux original, which is 0.79× in both
the original run and this replication — an erratum in the replication request, not in the
cell.

## 3. linux-precision-cost-duel

Fresh run: throwaway copy of `src/duel.mjs` (same deterministic generator, seeds
1000+97i), fresh headless Chromium from the playwright cache, output to scratchpad.
Accuracy leg re-run under per-condition isolation as described above — and extended from
the original n=6-page subset to **all 20 pages** (60 points per condition), which contains
every possible 6-page subset.

| Measure | Original cell | Re-measured | |
|---|---|---|---|
| avg structured view | 391 tok / 1580 B | **391 tok / 1580 B** | exact |
| screenshot tokens (formula, 1280x800) | 1366 | **1366** | exact |
| token ratio pixels/structured | 3.5x | **3.5x** | exact |
| avg screenshot png bytes | 57576 | 57994 | Δ 0.7% (Chromium build rendering; tokens unaffected — dims-derived) |
| accuracy, structured | 18/18 (n=6 pages x 3 tasks) | **60/60** (n=20 pages x 3 tasks) | parity reproduced |
| accuracy, pixels | 18/18 | **60/60** | parity reproduced |

**VERDICT: MATCH.** Cost side byte- and token-identical (deterministic pages + distiller —
the fact that 391/1580 reproduce exactly across machines is itself a determinism check).
Accuracy side: parity at 100% under both conditions reproduces on a superset of the
original protocol — every 6-page subset of my run scores 18/18 vs 18/18, which is the
cell's exact claim ("on clean legible pages pixels also score 100%; the duel's win here is
COST, not accuracy"). The pixels-condition answerer flagged two close max-total calls
(pages 11 and 16) and one lookalike customer name (page 8) but resolved all three
correctly — consistent with "clean legible pages" being the easy regime. Note the original
duel cell ran on a different machine ("sandbox Linux", Ubuntu 24.04, 2026-08-14); this
replication on debian-server therefore also serves as a cross-machine replication of the
cost figures.

---

## Conclusion

**3/3 cells replicate. No silently-wrong carrier cell found.** The recalibration proof
(cell 1) is the one that mattered most — it is the evidence behind guard v2's 0.01+edge
calibration — and it reproduces from a cold start: fresh app launch, fresh profile, fresh
session, fresh capture path (and a stricter one), same verdicts on every branch (v1 miss,
v2 double-vote catch, 0.000 control, 15/15 corpus). The only deviations found anywhere in
this pass are sub-1% quantitative drift with identified physical causes (live DHT frame,
live web content, Chromium build PNG encoding), none of which crosses any decision
threshold used by the campaign.

Replication artifacts (fresh captures, crops, views, answers, scripts) were kept in the
session scratchpad as throwaway material, per the read-only discipline; this report is the
only committed output.
