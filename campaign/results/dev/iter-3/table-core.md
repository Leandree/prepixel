| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-121ba48f` | ✅ | 10 | 0.98 | ✅ | 10 | 2.02 |
| `chrome-93eabf48` | ❌ | 7 | 0.88 | ❌ | 8 | 1.03 |
| `gimp-58d3eeeb` | ✅ | 2 | 0.27 | ✅ | 10 | 1.41 |
| `gimp-a746add2` | ✅ | 9 | 0.55 | ✅ | 13 | 2.10 |
| `libreoffice_calc-1334ca3e` | ✅ | 6 | 0.54 | ✅ | 4 | 0.92 |
| `libreoffice_calc-42e0a640` | ✅ | 9 | 1.06 | ✅ | 15 | 6.25 |
| `libreoffice_impress-ac9bb6cb` | ✅ | 15 | 2.77 | ❌ | 15 | 4.62 |
| `libreoffice_impress-ef9d12bd` | ✅ | 3 | 0.16 | ✅ | 3 | 0.36 |
| `libreoffice_writer-0810415c` | ✅ | 7 | 0.57 | ✅ | 12 | 2.54 |
| `libreoffice_writer-adf5e2c3` | ❌ | 13 | 2.61 | ❌ | 15 | 4.61 |
| `multi_apps-897e3b53` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-a0b9dc9c` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-bc2b57f3` | ✅ | 12 | 1.60 | ❌ | 15 | 5.86 |
| `multi_apps-da52d699` | ✅ | 6 | 0.90 | ✅ | 11 | 4.36 |
| `os-ec4e3f68` | ✅ | 3 | 0.16 | ✅ | 4 | 0.16 |
| `os-fe41f596` | ❌ | 5 | 0.30 | ❌ | 11 | 1.10 |
| `thunderbird-9b7bc335` | ✅ | 14 | 0.95 | ✅ | 14 | 2.26 |
| `thunderbird-dd84e895` | ✅ | 6 | 0.36 | ✅ | 11 | 1.12 |
| `vlc-215dfd39` | ✅ | 10 | 0.69 | ❌ | 15 | 2.77 |
| `vlc-5ac2891a` | ✅ | 11 | 1.74 | ✅ | 15 | 1.99 |

| metric | A | B |
|---|---|---|
| cells | 20 | 20 |
| successes | 15 | 12 |
| infra failures | 2 | 2 |
| median steps | 7.00 | 11.00 |
| median cost $ | 0.79 | 2.06 |
| total cost $ | 17.09 | 45.46 |

**Cap deaths (>=15 steps): A=1 B=6.** B guard verdicts: CONFIRMED=119, CROP=9, UNVERIFIED=53, WAIT=6

**Ladder self-corrections:** noop_escalations=3

**Condition B mechanics, all steps.** rung: 1=55, 2=36, crop=9, kbd=78, scroll=3 · channel: atspi=184, atspi+cdp=17

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-usable-action: no-interface` | 17 |
| `node-not-found` | 9 |
| `no-settable-interface: ` | 5 |
| `cdp: page.evaluate: Target page, context or browser has been closed` | 1 |
| `no-usable-action: ['showmenu']` | 1 |

| router declined the web channel because | n |
|---|---|
| `no chromium application in the tree` | 184 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `chrome-93eabf48` — term=DONE steps=8, A=❌. verdicts {'UNVERIFIED': 6, 'CONFIRMED': 1}. last 6:{"action": "set_value", "target": "e113", "value": "Disabled", "memo": "Set 'Auto Dark Mod | 7:{"action": "click", "target": "e165", "memo": "Flag #enable-force-dark now shows Disabled; | 8:{"action": "done", "memo": "Chrome relaunched; chrome://flags #enable-force-dark now reads
  - cause: TODO
- `libreoffice_impress-ac9bb6cb` — term=max_steps steps=15, A=✅. verdicts {'CONFIRMED': 10, 'UNVERIFIED': 5}. last 13:{"action": "set_value", "target": "e314", "value": "FixNum", "memo": "Basic Macros dialog  | 14:{"action": "click", "target": "e327", "memo": "Clicked Run in Basic Macros dialog with mac | 15:{"action": "click", "target": "e327", "memo": "Final step: clicked Run in Basic Macros dia
  - cause: TODO
- `libreoffice_writer-adf5e2c3` — term=max_steps steps=15, A=❌. verdicts {'CONFIRMED': 13, 'UNVERIFIED': 2}. last 13:{"action": "key", "keys": "escape", "memo": "Find bar closed; '<add here>' should remain s | 14:{"action": "type", "text": "[14]", "memo": "Typed [14] replacing '<add here>' in para 4; r | 15:{"action": "key", "keys": "ctrl+s", "memo": "Saved. Ref [14] Steinberg added to list; [14]
  - cause: TODO
- `multi_apps-897e3b53` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `multi_apps-a0b9dc9c` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `multi_apps-bc2b57f3` — term=DONE steps=15, A=✅. verdicts {'UNVERIFIED': 3, 'CONFIRMED': 11}. last 13:{"action": "type", "text": "Sub FixOrder\nDim oComps, oComp, oDoc, oSheets, i%\nDim n(9) A | 14:{"action": "click", "target": "e938", "memo": "Clicked Run on FixOrder macro. Next: check  | 15:{"action": "done", "memo": "Ran FixOrder macro which reordered sheets to the required orde
  - cause: TODO
- `os-fe41f596` — term=DONE steps=11, A=❌. verdicts {'CONFIRMED': 9, 'UNVERIFIED': 1}. last 9:{"action": "type", "text": "PROMPT_COMMAND='echo -ne \"\\033]0;BATT=$(gsettings get org.gn | 10:{"action": "type", "text": "PS1='$ '\n", "memo": "PROMPT_COMMAND was set (step 9) but Ubun | 11:{"action": "done", "memo": "Verified: window title reads BATT=true, i.e. gsettings get org
  - cause: TODO
- `vlc-215dfd39` — term=max_steps steps=15, A=✅. verdicts {'CONFIRMED': 10, 'WAIT': 2, 'UNVERIFIED': 1, 'CROP': 2}. last 13:{"action": "toggle", "target": "e75", "to": true, "memo": "Tried plain click on 'All' 3x:  | 14:{"action": "key", "keys": "tab", "memo": "Programmatic click/toggle on 'All' only flips ch | 15:{"action": "key", "keys": "right", "memo": "Focus was on unchecked 'Simple' radio; Qt arro
  - cause: TODO
