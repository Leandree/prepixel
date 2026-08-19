| task | A | steps | $ | B | steps | $ |
|---|---|---|---|---|---|---|
| `chrome-121ba48f` | ✅ | 9 | 1.04 | ✅ | 10 | 2.14 |
| `chrome-93eabf48` | ❌ | 8 | 0.80 | ✅ | 5 | 0.47 |
| `gimp-58d3eeeb` | ✅ | 1 | 0.08 | ✅ | 13 | 2.18 |
| `gimp-a746add2` | ✅ | 9 | 0.58 | ✅ | 11 | 1.84 |
| `libreoffice_calc-1334ca3e` | ✅ | 6 | 0.78 | ✅ | 8 | 2.35 |
| `libreoffice_calc-42e0a640` | ✅ | 9 | 1.25 | ✅ | 8 | 1.41 |
| `libreoffice_impress-ac9bb6cb` | ✅ | 13 | 2.31 | ❌ | 14 | 3.89 |
| `libreoffice_impress-ef9d12bd` | ✅ | 3 | 0.16 | ✅ | 6 | 1.34 |
| `libreoffice_writer-0810415c` | ✅ | 6 | 0.63 | ✅ | 15 | 4.11 |
| `libreoffice_writer-adf5e2c3` | ❌ | 14 | 3.67 | ✅ | 15 | 5.00 |
| `multi_apps-897e3b53` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-a0b9dc9c` | ⚠️infra | 0 | — | ⚠️infra | 0 | — |
| `multi_apps-bc2b57f3` | ✅ | 11 | 1.94 | ✅ | 15 | 4.67 |
| `multi_apps-da52d699` | ✅ | 8 | 1.20 | ✅ | 7 | 1.71 |
| `os-ec4e3f68` | ✅ | 3 | 0.16 | ✅ | 4 | 0.19 |
| `os-fe41f596` | ❌ | 5 | 0.34 | ❌ | 14 | 1.60 |
| `thunderbird-9b7bc335` | ✅ | 11 | 0.79 | ❌ | 15 | 2.24 |
| `thunderbird-dd84e895` | ✅ | 4 | 0.27 | ✅ | 6 | 0.56 |
| `vlc-215dfd39` | ✅ | 11 | 0.80 | ✅ | 15 | 2.00 |
| `vlc-5ac2891a` | ✅ | 11 | 1.33 | ✅ | 15 | 2.17 |

| metric | A | B |
|---|---|---|
| cells | 20 | 20 |
| successes | 15 | 15 |
| infra failures | 2 | 2 |
| median steps | 8.00 | 10.50 |
| median cost $ | 0.79 | 2.07 |
| total cost $ | 18.13 | 39.87 |

**Cap deaths (>=15 steps): A=0 B=6.** B guard verdicts: CONFIRMED=123, CROP=9, UNVERIFIED=43, WAIT=7

**Ladder self-corrections:** noop_escalations=5, signal_role_pointer=4

**Condition B mechanics, all steps.** rung: 1=48, 2=24, crop=9, kbd=88, scroll=6 · channel: atspi=100, atspi+cdp=14, atspi+uno=82

| rung-1 fallback reason (P7 input) | n |
|---|---|
| `no-usable-action: no-interface` | 7 |
| `no-settable-interface: ` | 3 |
| `node-not-found` | 3 |
| `no-usable-action: ['open']` | 1 |
| `no-usable-action: ['showmenu']` | 1 |

| router declined the web channel because | n |
|---|---|
| `no chromium application in the tree` | 182 |

| router declined the uno channel because | n |
|---|---|
| `unsupported document: com.sun.star.comp.basic.BasicIDE` | 3 |

**Every B failure, with its mechanical evidence. Cause written by hand after reading the trace — this script never guesses one.**

- `libreoffice_impress-ac9bb6cb` — term=DONE steps=14, A=✅. verdicts {'CONFIRMED': 10, 'WAIT': 2, 'UNVERIFIED': 1}. last 12:{"action": "click", "target": "e109", "memo": "Applied Font Color (last color = Red) to se | 13:{"action": "key", "keys": "ctrl+s", "memo": "Pressed ctrl+s after applying red font color  | 14:{"action": "done", "memo": "Applied red font color to shape 3 (<number>, the slide number 
  - cause: TODO
- `multi_apps-897e3b53` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `multi_apps-a0b9dc9c` — term=setup_error steps=0, A=❌. verdicts {}. last (none)
  - cause: TODO
- `os-fe41f596` — term=DONE steps=14, A=❌. verdicts {'UNVERIFIED': 3, 'CONFIRMED': 7, 'CROP': 3}. last 12:{"action": "crop", "target": "e11", "memo": "Cropping terminal e11 to read output of 'gset | 13:{"action": "crop", "target": "e87", "memo": "Checking the top-right System indicator area: | 14:{"action": "done", "memo": "Set org.gnome.desktop.interface show-battery-percentage=true v
  - cause: TODO
- `thunderbird-9b7bc335` — term=max_steps steps=15, A=✅. verdicts {'UNVERIFIED': 8, 'WAIT': 2, 'CONFIRMED': 5}. last 13:{"action": "set_value", "target": "e116", "value": "anonym-x2024@gmail.com", "memo": "Set  | 14:{"action": "click", "target": "e120", "memo": "Clicked OK on Filter Rules (address entry v | 15:{"action": "click", "target": "e123", "memo": "Alert 'Enter a valid email address to forwa
  - cause: TODO
