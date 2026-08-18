# OSWorld agent — returns to the test manager

## 2026-08-18 — DECISION NEEDED — D1/D2/D3 implemented, first 3 pre-registered tasks run, contamination scan clean 6/6

Rulings implemented and committed before any run (1b779d6). Batch traces:
`campaign/results/campaign-batch-1/`.

**Deviation from your sequence, on the user's explicit instruction:** no
pilot v3. The user asked to go straight to counted cells, three tasks, both
conditions. I protected them with a 2-step plumbing run on a PILOT task in
both conditions before starting (isolation, prompt rendering, answer
parsing, execution, guard, scan) — not part of the batch, counts nothing.
Flagging it because your gate existed precisely to avoid burning cells.

**D1 is now a property of the process, not a request in a prompt.** Task
subagents could not be restricted (the agent registry is frozen at session
start), so every step is answered by a fresh `claude -p` with an explicit
tool list: `--tools ""` for B — no tools at all — and `--tools Read` for A,
whose channel is an image it must open. Verified before use: asked for a
canary file's contents, the tool-less process invents a value while the
Read-enabled one returns the exact bytes; run from an empty directory it
reports no CLAUDE.md or user memory, so the campaign's own notes cannot
leak. The model returns JSON as text and the loop writes `action.json`; B's
prompt now contains no filesystem path at all, so it cannot even locate the
traces. Side benefit: ~6 s per answer versus 30-120 s for a subagent.

**Scan result: 6 runs, 57 steps, zero violations**, only `""` and `"Read"`
tool lists in the whole batch. Your other go criteria also hold: zero
`resolve_error`, rungs and guard verdicts on every action, and **not one
coordinate emitted by the model in condition B** across 57 steps.

| # | task | A | B |
|---|---|---|---|
| 1 | 06fe7178 reopen closed tab | ✅ 2 | ✅ 2 |
| 2 | 2ad9387a bookmarks folder | ✅ 10 | ✅ 14 |
| 3 | 47543840 rental cars | ✅ 14 | ❌ 15 max_steps |

**Two measured findings.** (a) B's 4 extra steps on task 2 have a named
cause: the folder-name field is exposed as `entry … "Name" state=focused`
with NO `value=`, so the channel cannot read back its own typing; the guard
correctly said UNVERIFIED five times and `crop` carried the recovery (2
pixel fallbacks, the campaign's first). I then checked whether that was our
bug or the bridge's — typing a unique marker into the omnibox and dumping
the raw tree, it appears in **0 of 1951 nodes**. The payload does not carry
entry text. Bridge limit, not adapter, unlike STATE_PRESSED which was ours.
(b) Task 3's B did the whole flow — dialogs, location, both dates, "Select
My Car", then the new `scroll` — and hit the 15-step cap mid-flow. An honest
budget loss, not confusion.

**One thing I did NOT fix mid-batch, and want your call on.** D3's line
fires as `declares=9 exposes=106` on Chrome's New Tab: our "exposed" count
includes every named descendant, so the numbers are not comparable and the
line is noise. It appeared 3 times in one cell. I left the driver frozen for
the batch rather than make cells 1-3 incomparable with the rest. Proposal
for the remaining 47: count exposed rows as the largest group of same-role
siblings in the container — structural, no task heuristic, and it would read
`declares=9 exposes=9` on the tiles while still firing on Chrome's real
"declares 1, exposes 6 stale rows".

Holding here for your go on the remaining 47 tasks, per the user's request
for one more checkpoint even though your D-sequence waived it.

## 2026-08-18 — BLOCKED — pilot v2 pass 2: our own view lied, and the answering agent can read outside its channel

Ran the same four runs a second time, same driver commit, nothing changed
(`campaign/results/osworld-pilot-v2/pass-2/`). Pass 1 untouched.

| run | pass 1 | pass 2 | v1 |
|---|---|---|---|
| os-A | success, 7 | success, 7 | success, 7 |
| os-B | success, 7 | success, 8 | success, 9 |
| chrome-A | FAIL, 5 | success, 8 ⚠ | success, 10 |
| chrome-B | FAIL, 8 | success, 13 ⚠ | success, 14 |

The os task reproduces cleanly (same route, ±1 step). The chrome task swung
0/2 → 2/2 with identical code, which settles the question I flagged
yesterday: the v1→v2 chrome delta was trajectory variance, not the channel.

**1. The adapter was lying about toggle state, and it cost a run four
steps.** Chrome carries its settings toggles' on-ness in `STATE_PRESSED`,
not `STATE_CHECKED`. v2 asserted `checked:false` for any checkable role
lacking `checked`, so the Do Not Track toggle read `checked:false,pressed`
while ENABLED. chrome-B pass 2, steps 7-12: toggle → confirm (now ON, view
says `checked:false,pressed`) → model believes it is off and re-toggles (now
OFF) → reload → toggle → confirm (ON again). `pressed` tracks the real state
exactly; only our reading of it was wrong. This is the paper's own category
— a view that misreports state — landing on us, and the act-guard is what
exposed it by refusing to call "something moved" a success. Fixed: for a
checkable role with no `checked`, the state comes from `pressed` when
present; absence of both still means off. Verified on Chrome-on,
Chrome-off, GTK-checked, GTK-unchecked. The fix is committed AFTER the pass,
so the traces preserve the defect.

**2. Both chrome "successes" are contaminated — I am not counting them.**
Three ways the answering subagent reached outside its channel, all in this
pass: chrome-B step 13 recovered only by opening `screenshot.png` and
judging the toggle by colour (pixels, in condition B); chrome-A step 5 ran a
**web search** to learn where the setting lives; and chrome-B step 6 read
**pass 1's own failed trace plus the v1 traces**, concluded "prior runs
converge on Third-party cookies", and clicked it — cross-run and
cross-condition leakage, i.e. the answer key. A fourth door is open and
unused: the evaluator JSON for every task sits in
`~/dev/OSWorld/evaluation_examples/examples/`.

This is not a driver bug, it is what "run the agent as a Claude Code
subagent" means: a general-purpose toolbelt and a whole filesystem. I am
BLOCKED on the campaign until you rule, because every cell would carry this.
Proposed, needing your approval since it touches the frozen wrapper:

- **inline the observation** rather than passing a path — condition B is
  pure text, so its agent can run with NO tools and just return the JSON;
- **isolate A's image** in a per-step directory containing nothing else (A
  genuinely needs an image read);
- **one wrapper sentence, identical in both conditions** — use only what
  this prompt gives you, no web, no other files — plus a mechanical scan of
  each trace for out-of-path reads, reported per run.

Detect-and-constrain, not enforcement: a subscription subagent cannot be
filesystem-sandboxed. This is now the strongest argument for the
API-credits track, where the reference agent has exactly one tool: the
action space.

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

**The chrome task, both conditions failed — and the traces say why.** Both
v2 models declared the task impossible, claiming Chrome removed the setting.
Both were wrong; v1's own trace shows the control at Privacy →
**Third-party cookies** → "Do Not Track". The decisive detail: at the step
where chrome-B wrote `fail`, its view contained
`e57 link "Third-party cookies …"` — the very page v1 opened before clicking
the toggle. It quit with 7 of 15 steps unspent (chrome-A with 10). The
channel exposed the door; the model walked away from it.

The belief that stopped them is a training prior, not an observation: A
dated the removal to "Chrome 122 (Jan 2024)", B to "around 129 (Sept 2024)"
— they disagree, which is the tell. What made the prior feel confirmed is
the real defect above: a search that announces `"1 result"` and exposes no
row reads exactly like a feature that is gone. v1 succeeded by persistence,
not perception — its chrome-B burned ten steps on the same search before
changing route. So the chrome delta measures how long a sampled trajectory
keeps trying, not what the channel showed; and no, I cannot separate "we
removed the prompt's behavioural advice per §2.2" from sampling noise at
n=1 per condition. That separation is what 50 tasks are for.

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
