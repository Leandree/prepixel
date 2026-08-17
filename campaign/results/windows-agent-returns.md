# Windows agent — returns to the test manager

Two-way log, per the convention in `agent-brief-COMMON.md` § "Returns to the
test manager". Newest first. Correspondence only — measurements live in the
cells, prose in `windows-FINDINGS.md`.

---

## 2026-08-17 — DONE — real-web battery on Windows (manager overrode my skip recommendation, rightly)

`windows-web-battery-cdp`: 16/16 sites, ratio of totals 0.99 vs macOS 1.00,
median 1.15 vs 1.21, per-site echoes to the second decimal (Vercel 3.12/3.11,
HN 0.46/0.47, Wikipedia 0.72/0.72). The override was the right call: the
OS-invariance claim is now MEASURED on all three OSes instead of asserted from
two. Delta worth noting: FR locale raises consent banners (8/16 vs 6/16).

## 2026-08-17 — DONE (with one incident to own) — real game cells, manager go received

Both cells run: **SILENT HILL 2** (UE5 AAA — 1 UIA node for a full in-engine
scene at 54 fps; PrintWindow works on the UE5 swapchain; guard energy 0.297 →
declared) and **R.E.P.O.** (Unity — 1 bare PaneControl for a menu with EIGHT
clickable items at 576 fps; guard energy 0.825, campaign record). New router
finding from REPO: the Unity fullscreen window is a Pane, not a Window — a UIA
WindowControl search misses a *running fullscreen game entirely* while Win32
sees it; second no-privilege instance of the enumeration blind spot after the
elevated Task Manager. Doctrine: window identity comes from the Win32 map +
ControlFromHandle, never from UIA name/type search.

**The incident (macOS-stopwatch mirror, my fault):** between launch and close,
SH2 had progressed past its intro into an in-game scene — plausibly the user
had taken over the session — and my probe's WM_CLOSE closed it without save
confirmation. Provenance ("I launched this window") is NOT sufficient
authority for lifecycle actions on a live machine: ownership must be
re-verified (recent human input? foreground history?) before closing, or the
close left to the human. Encoded in the cell; apologized to the user; loss
bounded by SH2's autosave.

Also: two harness bugs of mine burned ~12 min — a case-SENSITIVE title regex
('SILENT HILL' vs 'Silent Hill 2  ' with trailing spaces), and the same
name-search issue that the Pane finding then explained. Same recurring
pattern: the channel was fine, the router guessed names instead of using the
WM map.

## 2026-08-17 — SUPERSEDED — real game cells (was: waiting on manager go)

The manager asked for real 3D/demanding games (Heaven was a benchmark, not a
game). Plan ready, runner written (`campaign/windows/run_game.py`, read-only,
zero input into the game, PrintWindow-first with declared screen-crop
fallback): **SILENT HILL 2** (UE5 AAA, no anticheat) then **R.E.P.O.** (Unity,
engine diversity). Excluded by policy — kernel/service anticheat on the
user's real accounts: CS2 (VAC), GTA V Enhanced (BattlEye), Once Human,
Rocket League. Manager said to wait for their signal before launching;
holding. Steam was pre-warmed then shut down.

---

## 2026-08-17 — FYI — per-window capture rule: Windows complies, with converging evidence

Acknowledging the macOS FYI on `coverage-guard` false alarms from screen crops:
the Windows P0 run already read every guard crop from
`PrintWindow(PW_RENDERFULLCONTENT)` (the per-window surface), never a screen
crop — we arrived at that independently after a screenshot at the OBS rect
captured a Clock window covering it. Two OSes hitting the same requirement by
different accidents is good evidence the rule belongs in the module contract,
not in per-OS lore. Suggestion seconded: `contentEnergy` should log raw energy
and normalise by painted area (our OBS crop energy 0.245 includes the region's
dark band; verdict unaffected here).

## 2026-08-17 — FYI — layered-window rule adopted; no live specimen yet

The `layer > 0` false-occlusion FYI is encoded on Windows: the router now maps
`WS_EX_LAYERED` / `WS_EX_TRANSPARENT` per window and marks those rects
`rect_is_upper_bound`. Honest status: the live desktop had **0 of 7** titled
windows with either flag at audit time, so on Windows the rule rests on the
macOS evidence — a Discord/game overlay session would be the natural specimen
if the manager wants it exercised here.

## 2026-08-17 — DONE — deepening round closed (P0, P1, both P2 tiers, dedupe)

- **P0** mitigation on the real apps: OBS auto-flagged (energy 0.245, crop
  shows the painted text), FL 5/5 regions, rekordbox caught view-only by
  guard B. Aggregate: 0 silent survivors, 3 caught-and-declared.
- **P1** the 125% coordinate trap demonstrated live (naive (735,448) miss vs
  calibrated (588,358) hit, in-channel verified; scaling reverted+verified).
- **P2** WPF full green; Java = UIA-blind + JAB tree in 21.7 ms; dedupe 5.6%.
- Harness bugs of mine, on the record (the recurring pattern): guard A had no
  suspect for frame-only trees (fixed: synthesized client-area suspect, found
  by the Swing cell); a BOM-less .ps1 made the WPF app itself display mojibake
  which UIA faithfully reported (screen lied, channel didn't); first JAB
  handshake failed from a starved message pump, not from the channel.

## 2026-08-17 — BLOCKED — LibreOffice/UNO on Windows: orphaned-elevation postmortem

The UAC consent the user granted on 08-15 authorized an msiexec whose parent
(winget) I had already killed — elevation granted to a dead request installs
nothing, silently; the Installer lock (1618) then blocked every alternative
until the prompt was cleared. Word-via-COM (the better Tier C cell) is done,
so I do NOT recommend re-raising a UAC prompt for UNO. If the manager wants
the UNO mirror anyway: one normal LibreOffice install, then
`campaign/windows/run_libreoffice.py` is ready.

## 2026-08-17 — DECISION NEEDED — real-web battery on Windows Chrome?

Last Windows-relevant open line in the plan. My recommendation: **skip** — the
browser stack is OS-invariant (the duel replicated to the token on all three
OSes), macOS ran the 16-site battery, and the marginal information is near
zero for ~1-2 h of live-web flakiness. Default if no answer: not run.

## 2026-08-15 — DONE — main campaign round (19 cells)

Close-out in `windows-FINDINGS.md`. For cross-agent value, the items that
travelled: the AT-latch exists on Windows Chromium (self-arming, ~1.2 s); the
UWP frame/content process split false-blocks pid-based click guards (guard on
top-level hwnd); elevated windows vanish from UIA enumeration while Win32
still sees them (the WM map is the safety mechanism, not a convenience);
`SetForegroundWindow` denial is silent — verify, then hit-test before every
blind click. My own probe bugs cost three false "failures" (extension-less
Explorer names, 'Est égal à' vs 'Égal à', a pid guard) — in every case the
view was honest and the router under-used it.
