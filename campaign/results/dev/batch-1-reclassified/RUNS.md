## chrome-06fe7178-A — success=True (2 steps, DONE, 184.2s)
Task: 06fe7178-4491-4589-810f-2e2bc9502122 (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `import pyautogui; pyautogui.hotkey('ctrl', 'shift', 't')`
2. `DONE`

## chrome-06fe7178-B — success=True (2 steps, DONE, 56.7s)
Task: 06fe7178-4491-4589-810f-2e2bc9502122 (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `key ctrl+shift+t`  [act-guard: CONFIRMED (view changed outside the system bar; focus: push-button 115,909,64,65 "Cookies" state=focused)]  [rung kbd; settle 5650ms/2cap; re-probes 1]
2. `done`
guard: 1 suspects checked, 0 hits, 0 pixel fallbacks
mechanics: {"platform_available": true, "rung1": 0, "rung2": 0, "kbd": 1, "resolve_errors": 0, "noop_toggles": 0, "rung1_fallbacks": 0, "settle_ms_total": 5650, "settle_captures_total": 2, "guard_ms_total": 39, "reprobes": 1, "scroll_iters_total": 0, "waits_after_settle": 0, "scrolls": 0, "declared_count_mismatches": 3, "platform_probe": "OSW_PLATFORM_OK 14"}

## chrome-2ad9387a-A — success=True (10 steps, DONE, 532.4s)
Task: 2ad9387a-65d8-4e33-ad5b-7580065a27ca (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `import pyautogui; pyautogui.click(35, 65)`
2. `import pyautogui; pyautogui.click(1890, 138)`
3. `import pyautogui; pyautogui.click(1897, 90)`
4. `import pyautogui; pyautogui.click(1737, 431)`
5. `import pyautogui; pyautogui.click(1307, 573)`
6. `import pyautogui; pyautogui.click(1888, 141)`
7. `import pyautogui; pyautogui.click(1811, 240)`
8. `import pyautogui; pyautogui.click(994, 591); pyautogui.write('Favorites')`
9. `import pyautogui; pyautogui.click(1200, 662)`
10. `DONE`

## chrome-2ad9387a-B — success=True (14 steps, DONE, 210.1s)
Task: 2ad9387a-65d8-4e33-ad5b-7580065a27ca (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `key ctrl+shift+o`  [act-guard: CONFIRMED (view changed outside the system bar; focus: entry 818,130,653,24 "Search bookmarks" state=focused)]  [rung kbd; settle 5327ms/3cap]
2. `click push-button "Organise"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 2; rung1 fell back: no-usable-action: ['open', 'showcontextmenu']; settle 4493ms/3cap]
3. `click menu-item "Add new folder"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 2; rung1 fell back: no-usable-action: ['select', 'showcontextmenu']; settle 4461ms/3cap]
4. `type "Favorites"`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4452ms/3cap]
5. `type "Favorites"`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4721ms/3cap]
6. `crop entry "Name"`  [act-guard: CROP served: /home/leandre/dev/osworld-campaign/chrome-2ad9387a-B/step-6/crop.png]  [rung crop]
7. `click entry "Name"`  [act-guard: UNVERIFIED (element re-read unchanged: still entry 769,583,452,16 "Name" state=focused)]  [rung 1; Component.grabFocus; settle 4583ms/3cap]
8. `type "Favorites"`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4460ms/3cap]
9. `crop entry "Name"`  [act-guard: CROP served: /home/leandre/dev/osworld-campaign/chrome-2ad9387a-B/step-9/crop.png]  [rung crop]
10. `type "Favorites"`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4459ms/3cap]
11. `key ctrl+a`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4390ms/3cap]
12. `type "Favorites"`  [act-guard: UNVERIFIED (view unchanged outside the system bar; focus: entry 769,583,452,16 "Name" state=focused)]  [rung kbd; settle 4480ms/3cap]
13. `set_value entry "Name" := "Favorites"`  [act-guard: UNVERIFIED (asked value=Favorites, but the target element is no longer in the view)]  [rung 2; rung1 fell back: no-settable-interface: ; settle 4412ms/3cap]
14. `done`
guard: 0 suspects checked, 0 hits, 2 pixel fallbacks
mechanics: {"platform_available": true, "rung1": 1, "rung2": 3, "kbd": 7, "resolve_errors": 0, "noop_toggles": 0, "rung1_fallbacks": 3, "settle_ms_total": 50238, "settle_captures_total": 33, "guard_ms_total": 216, "reprobes": 0, "scroll_iters_total": 0, "waits_after_settle": 0, "scrolls": 0, "declared_count_mismatches": 0, "platform_probe": "OSW_PLATFORM_OK 16"}

## chrome-47543840-A — success=True (14 steps, DONE, 957.0s)
Task: 47543840-672a-467d-80df-8f7c3b9788c9 (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `WAIT`
2. `import pyautogui; pyautogui.click(1124, 181)`
3. `import pyautogui; pyautogui.click(351, 318)`
4. `import pyautogui; pyautogui.click(1762, 1028)`
5. `import pyautogui; pyautogui.click(608, 651); pyautogui.write('Boston Logan Intl Airport', interval=0.05)`
6. `import pyautogui; pyautogui.click(608, 407)`
7. `import pyautogui; pyautogui.click(958, 292)`
8. `import pyautogui; pyautogui.click(1349, 486)`
9. `import pyautogui; pyautogui.click(1069, 486)`
10. `import pyautogui; pyautogui.click(1528, 292)`
11. `WAIT`
12. `import pyautogui; pyautogui.click(777, 452)`
13. `import pyautogui; pyautogui.click(716, 548)`
14. `DONE`

## chrome-47543840-B — success=False (15 steps, max_steps, 320.7s)
Task: 47543840-672a-467d-80df-8f7c3b9788c9 (chrome); model: claude-code-cli:sonnet (campaign 2026-08-18); driver: v2
1. `click push-button "Never allow"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.press; settle 4766ms/2cap]
2. `click push-button "Agree"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.press; settle 5175ms/3cap]
3. `click push-button "Close"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.press; settle 4987ms/3cap]
4. `key escape`  [act-guard: CONFIRMED (view changed outside the system bar; focus: document-web 70,114,1850,966 "Discount car rental rates and renta]  [rung kbd; settle 4979ms/3cap]
5. `click document-frame "Close"`  [act-guard: UNVERIFIED (element re-read unchanged: still document-frame 680,154,600,456 "Close")]  [rung 1; Component.grabFocus; settle 4790ms/3cap]
6. `crop document-frame "Close"`  [act-guard: CROP served: /home/leandre/dev/osworld-campaign/chrome-47543840-B/step-6/crop.png]  [rung crop]
7. `click entry "Pickup & return"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Component.grabFocus; settle 5082ms/3cap]
8. `type "Boston Logan Intl Airport"`  [act-guard: CONFIRMED (view changed outside the system bar)]  [rung kbd; settle 4958ms/3cap]
9. `click link "Boston Logan International Airport (BOS)"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.jump; settle 5256ms/2cap]
10. `key escape`  [act-guard: CONFIRMED (view changed outside the system bar; focus: document-web 70,114,1850,966 "Cheap Car Rentals | Boston Logan In]  [rung kbd; settle 5110ms/3cap]
11. `click entry "mm/dd/yyyy"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Component.grabFocus; settle 4342ms/2cap]
12. `click table-cell "10"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.click; settle 4425ms/2cap]
13. `click table-cell "11"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.click; settle 5272ms/3cap]
14. `click push-button "Select My Car"`  [act-guard: CONFIRMED (element no longer present — view changed)]  [rung 1; Action.press; settle 7129ms/2cap]
15. `scroll down`  [act-guard: CONFIRMED (view changed outside the system bar)]  [rung scroll; settle 6571ms/2cap]
guard: 6 suspects checked, 0 hits, 1 pixel fallbacks
mechanics: {"platform_available": true, "rung1": 10, "rung2": 0, "kbd": 3, "resolve_errors": 0, "noop_toggles": 0, "rung1_fallbacks": 0, "settle_ms_total": 72842, "settle_captures_total": 36, "guard_ms_total": 537, "reprobes": 0, "scroll_iters_total": 0, "waits_after_settle": 0, "scrolls": 1, "declared_count_mismatches": 0, "platform_probe": "OSW_PLATFORM_OK 16"}
