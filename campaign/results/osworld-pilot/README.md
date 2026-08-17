# OSWorld pilot — full step-by-step traces (manager review)

Four runs, 2 non-pre-registered tasks × both conditions, sonnet subagents.
Layout per run: `result.json` (protocol §3 fields + full action list),
`step-N/prompt.txt` (the EXACT prompt the answering agent saw, rendered from
the frozen template), `step-N/action.json` (its reply), `step-N/view.txt`
(condition B: the guarded structured view), `step-N/screenshot.jpg` (VM
screen at that step, JPEG-compressed from the PNG the agent actually got).
Pilot results are NEVER counted in the campaign (tasks outside the
pre-registered 50). Quota figures per run are in the returns file.

## pilot-os-A — success=True (7 steps, DONE, 254s)
Task: 13584542-872b-42d8-b299-866967b5c3ef (os); model: claude-code-subagent:sonnet (pilot 2026-08-18)
1. `import pyautogui; pyautogui.hotkey('ctrl', 'alt', 't')`
2. `import pyautogui; pyautogui.click(842, 79)`
3. `import pyautogui; pyautogui.click(796, 301)`
4. `import pyautogui; pyautogui.click(1034, 320)`
5. `import pyautogui; pyautogui.tripleClick(1332, 193); pyautogui.typewrite('132', interval=0.05); pyautogui.press('tab'); pyautogui.tripleClick(1522, 193`
6. `import pyautogui; pyautogui.click(1770, 79)`
7. `DONE`

## pilot-os-B — success=True (9 steps, DONE, 563s)
Task: 13584542-872b-42d8-b299-866967b5c3ef (os); model: claude-code-subagent:sonnet (pilot 2026-08-18)
1. `import pyautogui; pyautogui.hotkey('ctrl','alt','t')`  [act-guard: CONFIRMED (view changed)]
2. `import pyautogui; pyautogui.click(843, 79)`  [act-guard: CONFIRMED (view changed)]
3. `import pyautogui; pyautogui.click(843, 302)`  [act-guard: CONFIRMED (view changed)]
4. `import pyautogui; pyautogui.click(995, 296)`  [act-guard: CONFIRMED (view changed)]
5. `import pyautogui; pyautogui.click(1315, 176); pyautogui.hotkey('ctrl','a'); pyautogui.typewrite('132'); pyautogui.press('tab'); pyautogui.click(1507, `  [act-guard: CONFIRMED (view changed)]
6. `import pyautogui; pyautogui.click(1337, 193); pyautogui.hotkey('ctrl','a'); pyautogui.typewrite('132'); pyautogui.press('tab'); pyautogui.click(1525, `  [act-guard: CONFIRMED (view changed)]
7. `import pyautogui; pyautogui.click(1754, 64)`  [act-guard: CONFIRMED (view changed)]
8. `import pyautogui; pyautogui.click(1771, 79)`  [act-guard: CONFIRMED (view changed)]
9. `DONE`
guard: 13 suspects checked, 0 hits, 0 pixel fallbacks

## pilot-chrome-A — success=True (10 steps, DONE, 658s)
Task: 030eeff7-b492-4218-b312-701ec99ee0cc (chrome); model: claude-code-subagent:sonnet (pilot 2026-08-18)
1. `import pyautogui; pyautogui.click(35, 65)`
2. `import pyautogui; pyautogui.click(700, 90); pyautogui.write('chrome://settings/privacy', interval=0.02); pyautogui.press('enter')`
3. `import pyautogui; pyautogui.click(994, 141); pyautogui.write('do not track', interval=0.02)`
4. `import pyautogui; pyautogui.click(1320, 141)`
5. `import pyautogui; pyautogui.click(197, 277)`
6. `import pyautogui; pyautogui.click(994, 141); pyautogui.write('do not track', interval=0.02)`
7. `import pyautogui; pyautogui.click(900, 396)`
8. `import pyautogui; pyautogui.click(1294, 878)`
9. `import pyautogui; pyautogui.click(1195, 704)`
10. `DONE`

## pilot-chrome-B — success=True (14 steps, DONE, 1525s)
Task: 030eeff7-b492-4218-b312-701ec99ee0cc (chrome); model: claude-code-subagent:sonnet (pilot 2026-08-18)
1. `import pyautogui, time; pyautogui.hotkey('ctrl', 'l'); time.sleep(0.3); pyautogui.write('chrome://settings/privacy', interval=0.02); pyautogui.press('`  [act-guard: CONFIRMED (view changed)]
2. `import pyautogui; pyautogui.moveTo(900, 700); pyautogui.scroll(-600)`  [act-guard: CONFIRMED (view changed)]
3. `import pyautogui, time; pyautogui.click(683, 130); time.sleep(0.3); pyautogui.write('do not track', interval=0.03)`  [act-guard: CONFIRMED (view changed)]
4. `WAIT`  [act-guard: WAIT (no action executed)]
5. `import pyautogui, time; pyautogui.press('down'); time.sleep(0.3); pyautogui.press('enter')`  [act-guard: CONFIRMED (view changed)]
6. `import pyautogui; pyautogui.moveTo(900, 500); pyautogui.scroll(-300)`  [act-guard: CONFIRMED (view changed)]
7. `import pyautogui; pyautogui.click(900, 527)`  [act-guard: CONFIRMED (view changed)]
8. `import pyautogui, time; pyautogui.hotkey('ctrl', 'l'); time.sleep(0.3); pyautogui.write('chrome://settings/privacy', interval=0.02); pyautogui.press('`  [act-guard: CONFIRMED (view changed)]
9. `import pyautogui, time; pyautogui.click(683, 130); time.sleep(0.3); pyautogui.write('do not track', interval=0.03)`  [act-guard: CONFIRMED (view changed)]
10. `import pyautogui; pyautogui.click(900, 527)`  [act-guard: CONFIRMED (view changed)]
11. `import pyautogui, time; pyautogui.hotkey('ctrl', 'l'); time.sleep(0.3); pyautogui.write('chrome://settings/cookies', interval=0.02); pyautogui.press('`  [act-guard: CONFIRMED (view changed)]
12. `import pyautogui; pyautogui.click(1295, 878)`  [act-guard: CONFIRMED (view changed)]
13. `import pyautogui; pyautogui.click(1195, 703)`  [act-guard: CONFIRMED (view changed)]
14. `DONE`
guard: 0 suspects checked, 0 hits, 0 pixel fallbacks
