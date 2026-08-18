# Campaign batch 1 — first 3 pre-registered tasks × both conditions

COUNTED cells (unlike everything in `osworld-pilot*/`). Tasks 1-3 of the
seed-42 pre-registered list committed in fb5fdfc, run interleaved per
protocol §4 (task 1 A then B, task 2 A then B, task 3 A then B), one run at
a time on a single VM. Driver frozen at commit 1b779d6 for the whole batch.

Per-run action lists with verdicts and mechanics: `RUNS.md`. Contamination
scan: `contamination.json` (also copied into each run).

**Protocol deviation, on the user's explicit instruction:** the manager's
unblocking sequence asked for a pilot v3 on the two non-counted pilot tasks
as the gate before any counted cell. The user chose to go straight to
counted cells. To protect them, the new wrapper was first exercised on a
2-step plumbing run against a PILOT task in both conditions (isolation,
prompt rendering, answer parsing, action execution, guard, scan) — that
smoke run is not part of this batch and counts nothing.

## Results

| # | task | instruction | A | B |
|---|---|---|---|---|
| 1 | chrome 06fe7178 | reopen the last closed tab | ✅ 2 steps | ✅ 2 steps |
| 2 | chrome 2ad9387a | new bookmarks-bar folder "Favorites" | ✅ 10 steps | ✅ 14 steps |
| 3 | chrome 47543840 | rental cars at Boston Logan, given dates | ✅ 14 steps | ❌ 15 (max_steps) |

A 3/3, B 2/3. Three cells is not a result — it is a batch of raw material.
No aggregate is computed before all 100 runs (protocol §4.5).

## The isolation holds: scan clean on 6/6

Every step of every run was answered by a fresh `claude -p` process with an
explicit tool list — `--tools ""` for condition B (no tools at all),
`--tools Read` for condition A (its channel is an image it must open). The
scan checks two layers: the tool list each step actually ran with, and the
model's own reply text for the evaluator directory, other runs' traces,
pixels in condition B, and the web.

Result: **6 runs, 57 steps, zero violations**, and the only tool lists
observed across the whole batch are `""` and `"Read"`. For comparison,
pilot v2 pass 2 leaked three ways in four runs — a condition-B agent judging
a toggle by its colour in the screenshot, another web-searching for the
answer, a third reading the previous runs' traces.

Also nominal: zero `resolve_error` in all three B cells, rungs logged on
every action, act-guard verdict on every action, and **not one coordinate
emitted by the model in condition B** — the ids-plus-resolver contract held
for 57 steps. Condition A emits coordinates constantly, as it must.

## What the batch measured

**Task 1 — identical, both channels.** Both conditions found `ctrl+shift+t`
immediately. B was faster in wall clock (57 s vs 184 s), which is mostly
answer latency: an image read costs seconds that a text view does not.

**Task 2 — B pays 4 extra steps to a blind spot, and the guard is what
exposes it.** B typed "Favorites" into the folder-name field five times,
cropped the pixels twice, tried `ctrl+a`, and finally used `set_value`. The
cause is in the trace: the field is exposed as
`entry 769,583,452,16 "Name" state=focused` — with **no `value=`**. The
channel cannot read back the text it just entered, so the model could not
tell a successful keystroke from a lost one, and the act-guard correctly
said `UNVERIFIED (view unchanged…)` every time. The coverage guard's `crop`
escape hatch carried the recovery: 2 pixel fallbacks, the first of the
campaign.

Measured follow-up, because "the adapter drops it" and "the payload lacks
it" are very different faults (`probe_entry_text.py`): typing a unique
marker into Chrome's omnibox and dumping the raw tree, the marker appears in
**0 of 1951 nodes**. The text is not in the payload at all. This one is the
bridge, not our adapter — unlike the STATE_PRESSED defect, which was ours.

**Task 3 — B ran out of budget mid-flow, not off-track.** It dismissed three
dialogs, set the pickup location, picked both dates and clicked "Select My
Car", then used the new `scroll` action (ruling D2) on step 15 and hit the
cap. Ten of its actions were AT-SPI platform actions with no pointer at all.
A finished the same flow in 14. This is the step budget biting, and it is
the honest kind of B loss: not confusion, arithmetic.

## Known noise in this batch, deliberately not fixed mid-run

Ruling D3's `declares=N exposes=M` line fires on Chrome's New Tab page with
`declares=9 exposes=106`: our "exposed" count includes every named
descendant of the container, so the two numbers are not comparable and the
line is noise rather than a divergence. It appeared 3 times in one B cell
(3 lines out of ~300) and misled nobody, but it will fire on most pages.

I did not touch the adapter mid-batch — freezing the driver across a batch
matters more than a cosmetic fix, and changing it would have made cells 1-3
incomparable with the rest. Proposed for the manager before the remaining
47: count exposed rows as *the largest group of same-role siblings* inside
the container, which is structural (no task heuristic, §3 safe) and would
give `declares=9 exposes=9` on the New Tab tiles while still firing on
Chrome's real "declares 1, exposes 6 stale rows".
