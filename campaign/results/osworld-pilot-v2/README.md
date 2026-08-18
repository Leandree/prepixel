# OSWorld pilot v2 — driver v2, full step-by-step traces (manager review)

Same two non-pre-registered tasks as pilot v1, both conditions, sonnet
subagents, driver v2 (`manager_orders/DRIVER-V2-SPEC.md`). v1 is untouched
in `campaign/results/osworld-pilot/`. Pilot results are NEVER counted in the
campaign.

Layout per run: `result.json` (protocol §3 fields + the v2 `mechanics`
block), `step-N/prompt.txt` (the exact prompt the answering agent saw),
`step-N/action.json` (its reply), `step-N/view.txt` (condition B: the
id-carrying guarded view), `step-N/mechanics.json` (resolution rung, settle
and guard times, re-probes), `step-N/screenshot.jpg` (JPEG of the PNG the
run actually used). Per-run action lists with verdicts: `RUNS.md`.
Acceptance suite (spec §4.2, run before the pilot): `acceptance/`.

## Results

| run | v1 | v2 | steps v1→v2 |
|---|---|---|---|
| os-A | success, 7 steps | success, 7 steps | 7 → 7 |
| os-B | success, 9 steps | **success, 7 steps** | 9 → 7 |
| chrome-A | success, 10 steps | FAIL declared, 5 steps | 10 → 5 |
| chrome-B | success, 14 steps | FAIL declared, 8 steps | 14 → 8 |

The chrome regression is NOT a driver effect — see below. Condition A's
driver is unchanged apart from the post-action budget.

## The os task: every v1 fault is gone, measured

v1 os-B needed 9 steps, two of them wasted fighting the same spin-button
(step 5 clicked the exact rect corner `1315,176`, value stayed `80.0`, the
whole-view guard still said `CONFIRMED (view changed)` because the GNOME
clock ticks inside the diff; step 6 re-did it at the centre).

v2 os-B, 7 steps, every verdict carrying its actual transition:

| # | action | verdict | rung |
|---|---|---|---|
| 1 | `key ctrl+alt+t` | CONFIRMED (view changed outside the system bar; focus: terminal … state=focused) | kbd |
| 2 | `click toggle-button "Menu"` | CONFIRMED (state [checked:false]→[checked:true]) | 1 `Action.click` |
| 3 | `click push-button "Preferences"` | CONFIRMED (element no longer present) | 1 |
| 4 | `click list-item "Unnamed"` | CONFIRMED (state [none]→[selected,focused]) | 2 |
| 5 | `set_value spin-button "80" := "132"` | CONFIRMED (value "80.0"→"132.0", label "80"→"132") | 1 `Value.currentValue` |
| 6 | `set_value spin-button "24" := "43"` | CONFIRMED (value "24.0"→"43.0", label "24"→"43") | 1 `Value.currentValue` |
| 7 | `done` | | |

- **fault 1 (model doing rect→point geometry):** gone by construction. The
  model never emits a coordinate; 4 of 6 targeted actions were actuated
  through AT-SPI with no pointer at all.
- **fault 2 (toggle without `checked`):** the menu toggle reports
  `checked:false`→`checked:true`.
- **fault 3 (CONFIRMED diluted by the clock):** the guard reads one element
  and the `y<28` band is out of every diff. The sandbox replay of the v1
  corner-click now returns `UNVERIFIED (element re-read unchanged: still
  spin-button 515,290,118,34 "80" value="80.0")`.
- **fault 4 (WAIT):** zero WAIT in either v2 run — but see the chrome
  finding, the v1 WAIT was not a settle problem.
- **fault 5 (exploratory scrolls):** zero scrolls in os-B. Not solved for
  the web case, and not solvable as specified — see `acceptance/README.md`.

## The chrome task: both conditions failed, for the same non-driver reason

Both v2 models declared the task impossible, arguing Chrome had removed the
setting. Both were wrong, and v1's own traces prove it: the control lives at
Settings → Privacy → **Third-party cookies** → "Do Not Track"
(`pilot-chrome-B/step-13/view.txt` of v1: `text 739,456,512,282 "Do Not
Track"`). Neither v2 run ever opened that sub-page.

What sent them there is real and reproducible: searching "do not track" in
chrome://settings makes the page announce `text 675,429,84,29 "1 result"`
while exposing no matching row — measured in the acceptance suite by polling
the tree every 1.5 s for 25.5 s, and reproduced live at chrome-B step 6.
Condition A hit the same wall through pixels (its step 5 reasoned about the
same "1 result" badge). So the shared cause is a Chrome UI that declares a
result it does not show, in either channel; the difference between v1 and v2
is that v1's models kept exploring and stumbled into Third-party cookies,
and v2's models reasoned themselves into a confident FAIL. Small-n
trajectory variance on top of a genuinely misleading UI — not evidence about
the channel, and a reminder of why the campaign is 50 tasks and not 2.

## Harness cost (reported apart from model cost, spec §3)

| | os-A | os-B | chrome-A | chrome-B |
|---|---|---|---|---|
| wall clock | 484 s | 413 s | 399 s | 752 s |
| rung 1 / rung 2 / keyboard | – | 4 / 1 / 1 | – | 3 / 0 / 4 |
| settle total | – | 28.0 s (18 captures) | – | 33.4 s (21 captures) |
| act-guard total | – | 122 ms | – | 171 ms |
| re-probes / scroll rounds / WAIT | – | 0 / 0 / 0 | – | 0 / 0 / 0 |

One a11y capture costs ~1.5 s on this host, so a settle is ~4.5 s for three
captures. The post-action budget is 4.0 s in both conditions (A spends it as
`env.step`'s pause), so B is never given more stabilisation time than A.
The act-guard is free by comparison (~25 ms per action).

## Two things the manager needs to decide

1. **Condition B has no way to scroll.** `scroll_to` targets an
   `[offscreen]` element, and `[offscreen]` turns out to be inexpressible
   from OSWorld's payload (coordinates exist only for showing+visible nodes:
   301 of 3047 on a Chrome page). So when content sits below the fold and
   the model is in B, it has no primitive for it — chrome-B step 5 noticed
   exactly this and worked around it with the search box. A plain
   `{"action":"scroll","direction":"down"}` would fix it, but it is a
   deviation from §2.2's element-reference-only schema, so I did not add it
   unilaterally.
2. **Blindness is not enforced.** In chrome-B step 6 the answering agent
   read `step-6/screenshot.png` — the driver writes it next to the prompt
   for the coverage guard — and reasoned about a yellow badge. Condition B
   is supposed to be structure-only with pixels available solely through
   `crop`. Suggested fix before the campaign: keep per-step screenshots in a
   sibling directory that no prompt references, materialise `crop.png` in
   the step directory only when asked, and grep each B trace for pixel reads
   as a contamination check. A subscription-harness subagent cannot be
   filesystem-sandboxed, so the honest posture is detect-and-report, and
   this is one more reason the API-credits track matters.
