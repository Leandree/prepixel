# OSWorld agent — returns to the test manager

## 2026-08-18 — DECISION NEEDED — driver v2 implemented, acceptance run, pilot v2 done; two design calls are yours

Driver v2 per `manager_orders/DRIVER-V2-SPEC.md` §2.1–2.6 is implemented and
committed before any run (6c7f56f, then 68bd62d and 107d39a for defects the
acceptance suite found). Traces: `campaign/results/osworld-pilot-v2/`
(README + RUNS.md + per-step prompt/view/action/mechanics/screenshot),
acceptance evidence in its `acceptance/` subdirectory. v1 untouched.

**The os task, v1 → v2: every diagnosed fault is gone, measured.** os-B went
9 steps → 7, with no geometric retry and no re-do of a state change. The
spin-button that v1 fought twice (corner click at 1315,176, value stayed
`80.0`, verdict wrongly `CONFIRMED (view changed)` because the GNOME clock
sits in the whole-view diff) is now one `set_value` actuated through
`Value.currentValue` with verdict `CONFIRMED (value "80.0"→"132.0")`.
Replaying the v1 corner-click in the sandbox now yields
`UNVERIFIED (element re-read unchanged: still spin-button … value="80.0")`.
4 of 6 targeted actions in os-B were actuated with no pointer at all
(AT-SPI `Action.click` / `Value.currentValue`); the model emitted zero
coordinates all run.

**The chrome task, both conditions failed — not a driver effect.** Both v2
models declared the task impossible, claiming Chrome removed the setting.
Both were wrong; v1's own trace shows the control at Privacy →
**Third-party cookies** → "Do Not Track", and neither v2 run opened that
sub-page. What misled them is real: searching "do not track" in
chrome://settings announces `"1 result"` and exposes no matching row —
polled every 1.5 s for 25.5 s in the sandbox, reproduced live at chrome-B
step 6, and condition A reasoned about the same badge from pixels. Shared
cause, both channels; the v1/v2 difference is that v1's models kept
exploring. Small-n trajectory variance on a misleading UI, which is exactly
why the campaign is 50 tasks.

**Acceptance (§4.2): 4 pass, 1 fails informatively, 1 not exercisable.**
(a) corner-miss → UNVERIFIED ✓; (a2) the same element via `set_value` →
CONFIRMED with the real transition ✓; (b) toggle state visible before/after
✓; (e) static label → UNVERIFIED ✓. (d) fails, but **your diagnostic #4 does
not hold**: the v1 WAIT was not a settle problem, the row never appears at
any budget, so no settle would have absorbed it. (c) is not exercisable:
OSWorld's payload carries coordinates only for showing+visible nodes —
measured 301 of 3047 on a Chrome page — so below-the-fold content has no
position to emit, and §2.6 as specified cannot be implemented from this
payload.

The suite paid for itself: it found four rung-1 defects before the pilot,
each of which would have silently degraded every campaign cell — role names
normalised differently by the server (rung 1 matched nothing, 6/6 fell back
to the pointer), over-aggressive spatial pruning (a stale ancestor hid a
whole preferences page), `EditableText` writing a spin-button's text while
leaving its value behind (`"132" value="80.0"` — caught by the guard), and
`Action.activate` on a text field meaning *submit*, which sent keystrokes to
another Chrome tab.

**Three things I did not decide unilaterally:**

1. **Condition B cannot scroll.** `scroll_to` needs an `[offscreen]` target
   and those are inexpressible here (above). Below-the-fold content is
   therefore unreachable in B except by luck; chrome-B step 5 hit this and
   routed around it via the search box. A plain
   `{"action":"scroll","direction":"down"}` fixes it but deviates from
   §2.2's element-reference-only schema. Your call.
2. **The §2.5 re-probe rule misses the real shape.** It fires on "declared
   count > 0, zero rows exposed"; Chrome's actual contradiction is
   "declares 1, exposes 6 *stale* rows". Generalising to "declared ≠
   exposed" false-fires on ordinary lists, and deciding which rows count as
   results is the task heuristic §3 forbids. Worth your attention: this is a
   real held-out instance of the paper's declare-vs-expose divergence, on a
   stock Chrome settings page.
3. **Blindness is not enforced.** At chrome-B step 6 the answering agent
   read `step-6/screenshot.png` (the driver writes it beside the prompt for
   the coverage guard) and reasoned about a yellow badge — a protocol
   contamination for that step, recorded rather than hidden. Fix I propose
   before the campaign: per-step screenshots move to a sibling directory no
   prompt references, `crop.png` materialises in the step directory only on
   request, and every B trace gets grepped for pixel reads as a
   contamination check. A subscription subagent cannot be
   filesystem-sandboxed — one more argument for the API-credits track.

Harness cost, reported apart from model cost (§3): one a11y capture ~1.5 s,
so a settle is ~4.5 s for three captures; settle totals 28.0 s (os-B) and
33.4 s (chrome-B); act-guard ~25 ms per action; zero re-probes, zero WAIT.
The post-action budget is 4.0 s in BOTH conditions (A spends it as
`env.step`'s pause), sized so B's settle never exceeds A's fixed sleep — the
condition under test is never handed more stabilisation time than the
baseline.

Note on lost traces: a first pilot-v2 pass (os-A 4 steps/fail-by-evaluator,
os-B 8 steps/success) was wiped with `/tmp` when the session was
interrupted; runs now write outside `/tmp` and are packaged into the repo as
each one finishes. The four runs above are a complete, self-consistent
re-run, not a mix.

**No campaign go requested yet** — per §4.4 I am waiting on your validation
of pilot v2 and on your calls on the three points above.

## 2026-08-18 — DONE — quota pilot 4/4 SUCCESS; driver validated; awaiting campaign go

Pilot (2 non-pre-registered tasks × 2 conditions, interleaved, sonnet
subagents, results NEVER counted in the campaign):

| run | success | steps | wall | subagent tokens (quota burn) |
|---|---|---|---|---|
| os-A (terminal 132x43) | YES | 7 | 254s | ~221k |
| os-B | YES | 9 | 563s | ~278k |
| chrome-A (030eeff7) | YES | 10 | 658s | ~355k |
| chrome-B | YES | 14 | 1525s | ~556k |

Driver fully exercised, zero infra failures: coverage-guard checked 13
suspects on os-B (0 hits — plausible on stock GTK/Chrome UIs), act-guard
verdicts recorded (8/8 CONFIRMED on os-B), diff protocol applied, CROP
fallback never requested. Both conditions solved both tasks; B consistently
took MORE steps than A on these two tasks (9v7, 14v10) — small-n, no
conclusion, but worth watching in the campaign. Cost accounting note: the
quota figures above include the Claude Code subagent fixed overhead
(~20–22k/spawn); the paper's per-task input-token metric will be computed
from the traces (prompt text + image-formula tokens for images actually
read), harness overhead excluded and reported separately. Campaign
extrapolation: ~350k subagent tokens/run avg → **~35M tokens of subscription
quota for the 100 runs**, ~10–12 h of VM wall clock, realistically spread
over 2–4 days of quota windows. AWAITING manager go to start the campaign
(interleaved, task 1 A then B, per protocol §4).

**What this file is.** Correspondence between the OSWorld-campaign agent and the
test manager, per `campaign/agent-brief-COMMON.md` § Returns and
`OSWORLD-PROTOCOL.md` §4.5. Measurements will go in per-task JSON cells, not
here.

**Convention.** Newest entry at the top. Each entry dated, with a status:
`DECISION NEEDED` / `FYI` / `BLOCKED` / `DONE`.

---

## 2026-08-17 — DECISION NEEDED — financing + model for the 100 runs (campaign paused at setup-complete)

The protocol fixes ONE exact model string for both conditions but leaves the
choice open, and the machine has no model API key (checked; I will not borrow
credentials from unrelated projects on this host). Cost estimate for the full
campaign (100 runs × ~12 steps, condition A ≈ 3 screenshots/step): ~7–8M input
tokens → **~$25–45 on claude-sonnet-4-6** (the model I recommend: accepts
temperature=0 as the protocol demands — Sonnet 5 / Opus 4.7+ / Fable REJECT
the temperature parameter, which would also force modifying the example
agent), ~$8–15 on claude-haiku-4-5 (floor-effect risk), ~2× on Opus 4.8.

RESOLVED 2026-08-18 by the manager: two-track plan approved. (1) Research
credits application package prepared
(`campaign/osworld/research-credits-application.md`) — if granted, the
API-pure campaign with the unmodified run.py agent on claude-sonnet-4-6 is
the paper's main result. (2) Meanwhile the campaign runs through the Claude
Code subscription as a pre-registered pilot; manager directed the answering
agents to run on the **"sonnet" model alias** (fresh subagent per step,
stateless, mirroring the reference agent's per-call statelessness; exact
alias resolution at run date recorded in each result's `model` field).
Documented deviations for track 2: session-alias model instead of a pinned
API string; no temperature control (moot — current models reject the
parameter; protocol amendment to "model sampling defaults, documented"
approved implicitly by the manager's go); harness system prompt not fully
publishable (identical across conditions); coverage-guard crops come from
the VM full-screen screenshot, not per-window surfaces (OSWorld's obs API
has no per-window capture — single-app fullscreen VM ≈ equivalent; noted as
a guard KNOWN-LIMIT interaction). Absolute scores not leaderboard-comparable;
only the A−B contrast is claimed. QUOTA PILOT before the campaign: 2 tasks ×
2 conditions on tasks OUTSIDE the pre-registered 50 (first non-selected id,
alphabetically, of `os` and `chrome`), results marked pilot and never
counted — so no campaign cell is ever re-run because of driver debugging.

## 2026-08-17 — DONE — protocol file moved into the repo

`OSWORLD-PROTOCOL.md` was sitting untracked at the repo root; moved verbatim
to `campaign/OSWORLD-PROTOCOL.md` (the path the tasking references) and
committed, so the pre-registration below points at a versioned protocol.

## 2026-08-17 — DONE — setup + env-level smoke test (no model in the loop yet)

- **KVM**: `/dev/kvm` present; README check `egrep -c '(vmx|svm)' /proc/cpuinfo`
  = 12. Docker Engine 28.4.0, user in `docker` group.
- **Install**: followed README §Installation strictly — cloned
  `xlang-ai/OSWorld` to `~/dev/OSWorld`; system Python is 3.13 which the pinned
  deps (torch~=2.5.0, numpy~=1.26) do not support, so the README's recommended
  conda path was used: Miniconda (rootless, `~/miniconda3`) + `conda create -n
  osworld python=3.10` + `pip install -r requirements.txt`. Deviation from
  README: none beyond conda being the documented-optional env manager; no flags
  improvised. (Conda now requires an interactive ToS acceptance —
  `conda tos accept` — before env creation; logged here because it silently
  empty-fails in scripts otherwise.)
- **Env-level smoke test** (README §Quick Start, docker provider):
  `python quickstart.py --provider_name docker --os_type Ubuntu` — first run
  downloads the Ubuntu qcow2 from HuggingFace into `./docker_vm_data`.
  RESULT: [filled after run]
- **Note on quickstart's `--headless`**: argparse `type=bool` — any string
  parses truthy; irrelevant for the docker provider path we use, noted for the
  record.

## 2026-08-17 — DONE — pre-registration committed BEFORE any run (protocol §1)

`campaign/osworld/tasks-selected.json`: 50 tasks over the 9 protocol domains
(vs_code excluded per protocol), proportional to domain size in
`evaluation_examples/test_all.json` (346 tasks across the 9 domains), min 3
per domain, seed 42. Quotas: chrome 6, gimp 4, libreoffice_calc 7,
libreoffice_impress 7, libreoffice_writer 3, multi_apps 14, os 3,
thunderbird 3, vlc 3 = 50. Sampler committed alongside
(`campaign/osworld/select_tasks.py`), fully deterministic (double-run
diff-identical; quota algorithm documented in its docstring). Amendment rule
embedded in the JSON: no task added/removed after this commit; infra-broken
tasks get `infra_failure` + evidence, never a replacement.

## 2026-08-17 — FYI — condition-B adapter written, first real-tree test pending

`campaign/osworld/distill-osworld.py`: OSWorld AT-SPI XML → prepixel line
grammar (`text/…/[pixels]` lines, spec of `src/distill-hardened.mjs` §3.1),
plus a `--suspects-out` side-channel listing coverage-guard suspects (mute
subtrees ≥150k px², the qBittorrent/OBS shape) for the runner's judgeCrop
spot-check. Honest differences vs the web distiller documented in its header:
no hit-testing through AT-SPI so no `[occluded]` tags; visibility semantics =
OSWorld's own judge_node filter (showing+visible+extents), EXCEPT that
nameless opaque nodes are declared `[pixels]` instead of dropped (dropping
them is precisely the silent-divergence shape the campaign exists to catch).
Tested against the real a11y tree captured during the smoke run: [filled
after run]
