| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-368d9ba4` | ✅ | 6 | 0.44 | ✅ | 8 | 1.27 |
| `chrome-7a5a7856` | ✅ | 8 | 0.54 | ❌ | 15 | 3.14 |
| `chrome-b4f95342` | ✅ | 8 | 0.55 | ✅ | 8 | 1.63 |
| `chrome-bb5e4c0d` | ✅ | 6 | 0.37 | ✅ | 4 | 0.41 |
| `chrome-f79439ad` | ✅ | 13 | 1.02 | ✅ | 12 | 2.57 |
| `chrome-fc6d8143` | ✅ | 12 | 0.81 | ✅ | 15 | 3.35 |
| `multi_apps-67890eb6` | ✅ | 12 | 2.05 | ✅ | 14 | 7.30 |
| `multi_apps-da922383` | ❌ | 13 | 1.50 | ❌ | 15 | 3.89 |

| metric | A | B |
|---|---|---|
| cells | 8 | 8 |
| successes | 7 | 6 |
| infra failures | 0 | 0 |
| median steps | 10.00 | 13.00 |
| median cost $ | 0.68 | 2.86 |
| total cost $ | 7.30 | 23.57 |

**Cap deaths (>=15 steps): A=0 B=3.** B guard verdicts: CONFIRMED=56, CROP=5, UNVERIFIED=18, WAIT=5

**Ladder self-corrections:** fingerprint_matches=1

**Condition B mechanics, all steps.** rung: 1=42, 2=4, crop=5, kbd=28 · channel: atspi=1, atspi+cdp=90

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-settable-interface: ` | 1 |
| `cdp: page.evaluate: TypeError: el.click is not a function
    at inPage (eval at evaluate ` | 1 |
| `cdp: stale-handle: element left the document` | 1 |
| `no-usable-action: no-interface` | 1 |

| router declined the web channel because | n |
|---|---|
| `no on-screen web document in 'google chrome'` | 1 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `chrome-7a5a7856` — term=FAIL steps=15, A=✅. verdicts {'UNVERIFIED': 2, 'CONFIRMED': 10, 'CROP': 2}. last 13:{"action": "click", "target": "e9", "memo": "Opened Bookmarks manager tab to verify. Conce | 14:{"action": "click", "target": "e50", "memo": "Clicked 'Bookmarks bar' folder in bookmarks  | 15:{"action": "fail", "memo": "Verified in the Bookmarks manager: the 'Bookmarks bar' folder 
  - cause: TODO
- `multi_apps-da922383` — term=max_steps steps=15, A=❌. verdicts {'CONFIRMED': 11, 'CROP': 2, 'WAIT': 2}. last 13:{"action": "key", "keys": "ctrl+p", "memo": "Tab1 'LLM Powered Autonomous Agents'. Print d | 14:{"action": "key", "keys": "ctrl+p", "memo": "Tab1 'LLM Powered Autonomous Agents'. Print p | 15:{"action": "type", "text": "\n/home/user/Documents/Blog/LLM Powered Autonomous Agents\n", 
  - cause: TODO
