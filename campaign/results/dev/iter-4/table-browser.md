| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-368d9ba4` | ✅ | 8 | 0.95 | ❌ | 15 | 2.92 |
| `chrome-7a5a7856` | ✅ | 7 | 0.91 | ❌ | 15 | 2.99 |
| `chrome-b4f95342` | ✅ | 14 | 1.71 | ✅ | 6 | 1.28 |
| `chrome-bb5e4c0d` | ✅ | 5 | 0.26 | ✅ | 4 | 0.42 |
| `chrome-f79439ad` | ✅ | 14 | 1.26 | ❌ | 15 | 3.50 |
| `chrome-fc6d8143` | ✅ | 15 | 0.98 | ✅ | 15 | 3.40 |
| `multi_apps-67890eb6` | ✅ | 7 | 1.04 | ✅ | 13 | 4.26 |
| `multi_apps-da922383` | ❌ | 13 | 1.32 | ❌ | 15 | 3.80 |

| metric | A | B |
|---|---|---|
| cells | 8 | 8 |
| successes | 7 | 4 |
| infra failures | 0 | 0 |
| median steps | 10.50 | 15.00 |
| median cost $ | 1.01 | 3.19 |
| total cost $ | 8.43 | 22.56 |

**Cap deaths (>=15 steps): A=1 B=5.** B guard verdicts: CONFIRMED=58, CROP=4, UNVERIFIED=25, WAIT=5

**Ladder self-corrections:** fingerprint_matches=1

**Condition B mechanics, all steps.** rung: 1=47, 2=11, crop=4, kbd=25 · channel: atspi+cdp=88, atspi+uno=10

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-settable-interface: ` | 6 |
| `cdp: stale-handle: element left the document` | 2 |
| `cdp: page.evaluate: TypeError: el.click is not a function
    at inPage (eval at evaluate ` | 2 |
| `no-usable-action: no-interface` | 1 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `chrome-368d9ba4` — term=max_steps steps=15, A=✅. verdicts {'CONFIRMED': 7, 'UNVERIFIED': 8}. last 13:{"action": "click", "target": "e10", "memo": "Snap Store window had stolen focus (that's w | 14:{"action": "set_value", "target": "e19", "value": "https://www.accuweather.com/en/gb/manch | 15:{"action": "key", "keys": "enter", "memo": "Step 15/15: pressed Enter to commit the addres
  - cause: TODO
- `chrome-7a5a7856` — term=FAIL steps=15, A=✅. verdicts {'UNVERIFIED': 1, 'CONFIRMED': 11, 'CROP': 2}. last 13:{"action": "key", "keys": "escape", "memo": "Pressed Escape to dismiss the lingering 'Edit | 14:{"action": "key", "keys": "f5", "memo": "Reloading chrome://bookmarks to refresh a stale l | 15:{"action": "fail", "memo": "Verified after a full reload of chrome://bookmarks: the 'Bookm
  - cause: TODO
- `chrome-f79439ad` — term=max_steps steps=15, A=✅. verdicts {'CONFIRMED': 9, 'UNVERIFIED': 6}. last 13:{"action": "click", "target": "e85", "memo": "Opened Passengers panel. Next: click + next  | 14:{"action": "click", "target": "e185", "memo": "Clicked + for Adults (should now read 2 Adu | 15:{"action": "click", "target": "e92", "memo": "Adults=2 confirmed (e184). Clicked Search to
  - cause: TODO
- `multi_apps-da922383` — term=FAIL steps=15, A=❌. verdicts {'CONFIRMED': 10, 'WAIT': 4}. last 13:{"action": "key", "keys": "ctrl+p", "memo": "Tab1 (LLM Powered Autonomous Agents): re-pres | 14:{"action": "key", "keys": "ctrl+p", "memo": "Tab1 (LLM Powered Autonomous Agents): ctrl+p  | 15:{"action": "fail", "memo": "Only 1 of 2 blogs saved. 'Thinking about High-Quality Human Da
  - cause: TODO
