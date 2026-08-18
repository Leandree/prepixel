# Driver v2 — sandbox acceptance suite (spec §4.2)

No model in the loop: `campaign/osworld/acceptance_v2.py` plays the scenarios
itself and records what the driver's mechanics produced. Nothing here is a
counted run. Raw reports: `acceptance-os.json`, `acceptance-chrome.json`,
`acceptance-nav.json`; the views the driver rendered at each probe are in
`os-views/` and `chrome-views/`.

Rung 1 = AT-SPI platform action inside the VM. Rung 2 = pointer synthesis at
the resolved anchor. The VM's `/run_python` interpreter can import pyatspi
and reach the session registry (`OSW_PLATFORM_OK 15`), so rung 1 is live.

## Verdicts

| # | Scenario (spec §4.2) | Required | Measured | |
|---|---|---|---|---|
| a | corner-miss replay (os-B step 5: click the exact rect corner, then type) | UNVERIFIED | `UNVERIFIED (element re-read unchanged: still spin-button 515,290,118,34 "80" value="80.0")` | PASS |
| a2 | positive control: the v2 `set_value` on that same element | value actually changes | rung 1 `Value.currentValue` → `CONFIRMED (value "80.0"→"132.0", label "80"→"132")` | PASS |
| b | toggle, state visible before and after | state in the view | before `toggle-button … "Menu" state=checked:false` → after `state=checked:true`, verdict `CONFIRMED (state [checked:false]→[checked:true])`, rung 1 `Action.click` | PASS |
| e | action on a static label | UNVERIFIED | `UNVERIFIED (element re-read unchanged: still text 831,290,32,34 "rows")`, rung 2 after `no-action-interface` | PASS |
| d | Chrome settings search: settle absorbs the lazy population | zero WAIT needed | the result row never appears: polled the tree every 1.5 s for 25.5 s after typing, `track_lines: 0` throughout, while the page announces `text 675,429,84,29 "1 result"` | FAIL — but not for the reason the spec assumed, see below |
| c | long page: `[offscreen]` + `scroll_to` | offscreen emitted and reachable | `c_offscreen_count: 0` — nothing to emit | NOT EXERCISABLE, see below |

The v1 fault each scenario targets, for comparison: the same corner-click in
the pilot v1 trace was reported `CONFIRMED (view changed)` — the whole-view
diff moved because the GNOME clock is in the view. Scoped to the target
element, the same action is now correctly UNVERIFIED, and the re-read state
(`still … value="80.0"`) goes back to the model.

## What the suite found in the driver (fixed, commit 68bd62d)

1. **Role normalisation** — the server writes XML tags as `getRoleName()`
   with spaces turned into dashes, so matching a live `"spin button"`
   against the view's `spin-button` never matched: 6/6 actions silently fell
   back to the pointer. Rung 1 was dead code until this was fixed.
2. **Over-aggressive spatial pruning** — on gnome-terminal's Preferences, an
   ancestor of the profile page reports extents that do not cover the page
   it currently shows; pruning on it made every widget of that page
   unreachable. Pruning now applies only near the top of the tree.
3. **`set_value` interface order** — `EditableText.setTextContents` writes
   the displayed text and leaves the adjustment behind. Measured: the view
   then read `spin-button "132" value="80.0"` — the label moved, the value
   did not. `Value.currentValue` is now tried first.
4. **The guard did not check the ask** — with (3) present, the guard said
   `CONFIRMED (label "80"→"132")` for an action that had not taken effect.
   Now `set_value`/`toggle` carry their expectation into the guard, so an
   unmet ask returns UNVERIFIED with the re-read line, which is literally
   the spec's `still value="80"` requirement.

Each was found by a scenario, not by reading the code — which is the
argument for running §4.2 before the pilot rather than after.

## Scenario (d): the v1 WAIT was not a settle failure

The spec's diagnostic #4 read the v1 `WAIT` at chrome-B step 4 as "lazy web
tree, no settle, no re-probe". Measured, that diagnosis does not hold, and
no settle budget could have fixed it.

After `type "do not track"` into `Search settings` (rung 1
`Component.grabFocus` on the field, then the keystrokes), the driver polled
the raw a11y tree every ~1.5 s for 25.5 s. At no point did any node
mentioning "track" appear. What the page does expose, the whole time, is
`text 675,429,84,29 "1 result"` — plus the six unfiltered
Privacy-and-security rows that were there before the search
(`Delete browsing data`, `Privacy guide`, `Third-party cookies`, `Ads
privacy`, `Security`, `Site settings`). Chrome announces a result count and
never exposes the row it counted.

Two consequences.

1. **Settle is not the lever here.** The tree is not slow, it is
   incomplete — so the model's WAIT was a reasonable response to a genuinely
   unreadable state, and v2 will not remove that WAIT. Raising the budget
   would only cost wall clock in both conditions.
2. **The §2.5 re-probe rule misses the real shape.** It fires on "declared
   count > 0, zero rows exposed". Here the container exposes six rows — the
   *stale* ones — so `exposed == 0` is false and nothing is emitted. The
   contradiction is `declares 1, exposes 6 unrelated`, not `declares 1,
   exposes 0`. I did NOT change the rule to "declared ≠ exposed": on an
   ordinary list ("3 items" + 3 rows + a header) that counts 4 and would
   fire falsely, and inventing a filter for "which rows are results" is
   exactly the task heuristic §3 forbids. This needs a manager decision, and
   it is worth one: a real held-out instance of the paper's declare-vs-expose
   divergence, in Chrome, on a stock settings page.

## Honest limits, measured

**§2.6 `[offscreen]` is not expressible from OSWorld's payload.** The server
only writes `cp:screencoord`/`cp:size` for nodes whose state is
showing+visible. Measured on a Chrome page: **3047 nodes in the dump, 301
with coordinates, 301 showing=true** — every below-the-fold node arrives with
no position at all. The driver emits `[offscreen]` for nodes that keep
showing=true with an off-viewport rect (they exist: e.g. an embedded
`document-web` at `453,1037,1069,602`, extending past the bottom edge), but
for ordinary "content below the fold" there is nothing to emit. Options for
the manager: (i) keep it as is and report the limit; (ii) emit
position-less nodes as `[offscreen, position unknown]` and have `scroll_to`
find them by scrolling and re-probing — implementable, but it changes the
channel's shape and would add thousands of lines on a Chrome page unless
capped. I did not choose unilaterally.

**Rung 2's occlusion sub-rule is not implemented.** AT-SPI exposes no
reliable z-order, so the anchor is always the full-rect centre; every rung-2
action logs `occlusion_check: not-implemented`.

**The VM image's `/run_bash_script` endpoint is broken** (`name
'_append_event' is not defined`) — unrelated to us, but it is why the suite
drives the VM through `/execute` and `/run_python` only.

**Chrome's omnibox autocompletes over typed URLs.** From google.com/chrome,
typing `chrome://settings/` and pressing Enter follows the completion back
to google.com/chrome — in the v1 single-command shape, in the v2
separate-action shape, and with a `delete` before Enter. It is a Chrome UX
trap that hits both conditions equally, not a v2 regression. The driver's
own typing path is measured separately (`acceptance-nav.json`): with
non-colliding URLs, `type`+`key` as separate driver steps navigate
correctly, with and without the settle in between — so the settle does not
break keyboard entry. Scenarios b/c/d therefore open their page with a
launcher instead of the omnibox.

## Cost of the mechanics (harness, not model — spec §3)

One a11y capture costs ~1.5 s on this host, so a settle is ~3 s for two
captures. The post-action budget is 4.0 s in BOTH conditions (A spends it as
`env.step`'s pause, B as its settle deadline), which keeps B's typical
settle under A's fixed sleep: the condition under test is never handed more
stabilisation time than the baseline. The act-guard costs ~20–30 ms per
action.
