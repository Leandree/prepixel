## pilot-chrome-A — success=False (5 steps, FAIL, 399.3s)
Task: 030eeff7-b492-4218-b312-701ec99ee0cc (chrome); model: claude-code-subagent:sonnet (pilot v2 2026-08-18); driver: v2
1. `import pyautogui; pyautogui.click(35, 65)`
2. `import pyautogui; pyautogui.click(994, 90); pyautogui.write('chrome://settings/privacy'); pyautogui.press('enter')`
3. `import pyautogui; pyautogui.moveTo(994, 700); pyautogui.scroll(-600)`
4. `import pyautogui; pyautogui.click(994, 141); pyautogui.write('do not track')`
5. `FAIL`

## pilot-chrome-B — success=False (8 steps, FAIL, 751.9s)
Task: 030eeff7-b492-4218-b312-701ec99ee0cc (chrome); model: claude-code-subagent:sonnet (pilot v2 2026-08-18); driver: v2
1. `type "chrome://settings/privacy"`  [act-guard: CONFIRMED (view changed outside the system bar; focus: document-web 70,114,1850,966 "New Tab" state=focused)]  [rung kbd; settle 4485ms/3cap]
2. `click push-button "Close"`  [act-guard: CONFIRMED (label "Close"→"Google apps")]  [rung 1; Action.press; settle 4575ms/3cap]
3. `type "chrome://settings/privacy"`  [act-guard: CONFIRMED (view changed outside the system bar; focus: entry 240,78,1429,24 "Address and search bar" state=focused)]  [rung kbd; settle 4702ms/3cap]
4. `key enter`  [act-guard: CONFIRMED (view changed outside the system bar; focus: entry 683,130,652,24 "Search settings" state=focused)]  [rung kbd; settle 5442ms/3cap]
5. `type "do not track"`  [act-guard: CONFIRMED (view changed outside the system bar; focus: entry 683,130,624,24 "Search settings" state=focused)]  [rung kbd; settle 4986ms/3cap]
6. `click link "Ads privacy Customise the info used by sites to show you ads"`  [act-guard: CONFIRMED (label "Ads privacy Customise the info used by sites to show you ads"→"Ad topics Based on your browsing histor]  [rung 1; Action.jump; settle 4587ms/3cap]
7. `click push-button "Ads privacy sub-page back button"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.press; settle 4608ms/3cap]
8. `fail`
guard: 0 suspects checked, 0 hits, 0 pixel fallbacks
mechanics: {"platform_available": true, "rung1": 3, "rung2": 0, "kbd": 4, "resolve_errors": 0, "noop_toggles": 0, "rung1_fallbacks": 0, "settle_ms_total": 33385, "settle_captures_total": 21, "guard_ms_total": 171, "reprobes": 0, "scroll_iters_total": 0, "waits_after_settle": 0, "platform_probe": "OSW_PLATFORM_OK 16"}

## pilot-os-A — success=True (7 steps, DONE, 484.4s)
Task: 13584542-872b-42d8-b299-866967b5c3ef (os); model: claude-code-subagent:sonnet (pilot v2 2026-08-18); driver: v2
1. `import pyautogui; pyautogui.hotkey('ctrl', 'alt', 't')`
2. `import pyautogui; pyautogui.click(842, 79)`
3. `import pyautogui; pyautogui.click(796, 301)`
4. `import pyautogui; pyautogui.click(1034, 320)`
5. `import pyautogui; pyautogui.click(1338, 193); pyautogui.hotkey('ctrl', 'a'); pyautogui.write('132'); pyautogui.press('tab'); pyautogui.click(1525, 193`
6. `import pyautogui; pyautogui.click(1770, 79)`
7. `DONE`

## pilot-os-B — success=True (7 steps, DONE, 412.6s)
Task: 13584542-872b-42d8-b299-866967b5c3ef (os); model: claude-code-subagent:sonnet (pilot v2 2026-08-18); driver: v2
1. `key ctrl+alt+t`  [act-guard: CONFIRMED (view changed outside the system bar; focus: terminal 260,103,722,434 "Terminal" state=focused)]  [rung kbd; settle 4717ms/3cap]
2. `click toggle-button "Menu"`  [act-guard: CONFIRMED (state [checked:false]→[checked:true])]  [rung 1; Action.click; settle 4405ms/3cap]
3. `click push-button "Preferences"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.click; settle 4669ms/3cap]
4. `click list-item "Unnamed"`  [act-guard: CONFIRMED (state [none]→[selected,focused])]  [rung 2; rung1 fell back: no-action-interface; settle 4551ms/3cap]
5. `set_value spin-button "80" := "132"`  [act-guard: CONFIRMED (value "80.0"→"132.0", label "80"→"132")]  [rung 1; Value.currentValue; settle 4508ms/3cap]
6. `set_value spin-button "24" := "43"`  [act-guard: CONFIRMED (value "24.0"→"43.0", label "24"→"43")]  [rung 1; Value.currentValue; settle 5165ms/3cap]
7. `done`
guard: 10 suspects checked, 0 hits, 0 pixel fallbacks
mechanics: {"platform_available": true, "rung1": 4, "rung2": 1, "kbd": 1, "resolve_errors": 0, "noop_toggles": 0, "rung1_fallbacks": 1, "settle_ms_total": 28015, "settle_captures_total": 18, "guard_ms_total": 122, "reprobes": 0, "scroll_iters_total": 0, "waits_after_settle": 0, "platform_probe": "OSW_PLATFORM_OK 15"}
