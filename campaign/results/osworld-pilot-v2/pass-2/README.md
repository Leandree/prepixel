# Pilot v2 — pass 2 (same 4 runs, same driver, nothing changed)

Re-run of the identical four runs with the identical driver commit, to
separate trajectory variance from channel effect on these two tasks. Pass 1
is untouched one directory up. Per-run action lists with verdicts and
mechanics: `RUNS.md`.

## Both passes side by side

| run | pass 1 | pass 2 | v1 (old driver) |
|---|---|---|---|
| os-A | success, 7 | success, 7 | success, 7 |
| os-B | success, 7 | success, 8 | success, 9 |
| chrome-A | FAIL declared, 5 | success, 8 ⚠ | success, 10 |
| chrome-B | FAIL declared, 8 | success, 13 ⚠ | success, 14 |

⚠ = the run reached success through harness contamination, not through its
channel. Details below; these two cells are not usable as measurements.

The os task reproduces cleanly: same route, same rungs, ±1 step (pass 2
spent one extra step closing the Preferences dialog before `done`). The
chrome task swung from 0/2 to 2/2 with nothing changed in the code — which
is the honest answer to "is the v1→v2 chrome delta a channel effect?": no,
this task's outcome is dominated by trajectory variance and, worse, by what
the answering agent can reach outside its channel.

## What pass 2 found in the driver: our own view was lying

chrome-B pass 2 is the important run. Steps 7-12, verbatim from the trace:

| # | action | what the view said afterwards |
|---|---|---|
| 7 | `toggle e77 → true` | UNVERIFIED (element gone — the confirm dialog opened) |
| 8 | `click "Confirm"` | DNT is now **ON**; view reads `state=checked:false,pressed` |
| 9 | `toggle e77 → true` (model believes it is off) | DNT now **OFF**; view reads `state=checked:false` |
| 10 | `click "Reload"` | UNVERIFIED (element re-read unchanged) |
| 11 | `toggle e77 → true` | UNVERIFIED (element gone — dialog again) |
| 12 | `click "Confirm"` | DNT **ON** again; `state=checked:false,pressed` |

Chrome carries this toggle's on-ness in `STATE_PRESSED`, not
`STATE_CHECKED`. The adapter asserted `checked:false` for any checkable role
without `checked` — so the view *contradicted itself* (`checked:false,
pressed`) and, read literally, told the model the setting was off while it
was on. The model did the reasonable thing and turned it back off. Four
steps burned by our own channel.

Note `pressed` appears and disappears in lockstep with the real state
(present at steps 8 and 12, absent at 9-11): the tree was never wrong, the
adapter's interpretation was. This is precisely the paper's own category —
a view that misreports state — landing on us, and it is the second time the
act-guard's honesty is what exposed it (the guard kept returning UNVERIFIED
rather than accepting "something moved" as success).

**Fixed** in the adapter: for a checkable role with no `checked`, the state
is taken from `pressed` when present; absence of both still means off (a GTK
check-box exposes neither when unchecked). Verified on all four shapes —
Chrome-on, Chrome-off, GTK-checked, GTK-unchecked. The fix landed AFTER this
pass, so these traces show the defective behaviour on purpose.

## Contamination: the answering agent can reach outside its channel

Three classes observed in this pass, all recorded rather than smoothed over:

1. **Pixels in condition B.** chrome-B step 13 recovered from the state bug
   only by opening `screenshot.png` and looking at the toggle's colour. So
   that run's success is a *pixel* success wearing condition B's label. Same
   class as pass 1's chrome-B step 6.
2. **The open web.** chrome-A step 5 ran a web search to learn that Do Not
   Track lives under Third-party cookies, then went straight there. The
   OSWorld reference agent has no such tool; this is outside knowledge, not
   perception.
3. **Other runs' traces — the answer key.** chrome-B step 6 read
   `osworld-runs-v2/pilot-chrome-B` (pass 1's failure), the v1 traces, and
   pass 2's own chrome-A run, then reasoned "prior runs converge on
   Third-party cookies" and clicked it. That is cross-run and cross-condition
   leakage, and it is why chrome-B pass 2 cannot be counted.

A fourth is available and not yet observed: `~/dev/OSWorld/evaluation_
examples/examples/**.json` contains each task's evaluator — the literal
success criterion — and nothing stops a subagent from reading it.

None of this is a driver bug; it is what "run the agent as a Claude Code
subagent" means. The subagent has a general-purpose toolbelt and a whole
filesystem. Proposed fix, for the manager's approval, in three parts:

- **inline the observation** instead of passing a path: condition B is pure
  text, so its answering agent can run with no tools at all and simply
  return the JSON action, which the orchestrator writes;
- **isolate condition A's image**: one screenshot per step in a directory
  containing nothing else, since A genuinely needs an image read;
- **one added wrapper sentence, identical in both conditions**: use only
  what this prompt gives you — no web, no other files — plus a mechanical
  check of each trace for reads outside the allowed path, reported per run.

This is detect-and-constrain, not enforcement: a subscription subagent
cannot be filesystem-sandboxed. It is the strongest argument yet for the
API-credits track, where the OSWorld reference agent has exactly one tool —
the action space.
