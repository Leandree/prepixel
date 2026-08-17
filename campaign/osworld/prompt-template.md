# OSWorld campaign — frozen prompt template v2 (committed BEFORE any run)

v2 per manager_orders/DRIVER-V2-SPEC.md: the prompt carries the task, the
step budget, the observation and the action schema — NOTHING else. All
behavioral advice removed (§2.2: the driver resolves geometry; advice-shaped
prompt lines were driver gaps). The {ACTION_SCHEMA} block now differs per
condition: A keeps the OSWorld reference pyautogui space UNCHANGED (§3 — the
asymmetry is the object of study); B uses element references resolved by the
driver. The driver renders this template into `step-N/prompt.txt` verbatim;
the orchestrator's spawn wrapper is constant ("Read prompt.txt and follow it
exactly"). No other instruction reaches the answering agent. Amending this
file after the first campaign run is forbidden (protocol §1 spirit); v1→v2
happened pre-campaign, on manager order, and is in git history.

---

You are an agent controlling an Ubuntu desktop (screen 1920x1080) to
accomplish a task. You observe the screen and emit ONE action per step.

TASK: {INSTRUCTION}

STEP {N} of {MAX_STEPS}.

PREVIOUS ACTIONS (oldest first):
{ACTION_HISTORY}

{OBSERVATION}

{ACTION_SCHEMA}

---

## {ACTION_SCHEMA} block, condition A (pixels)

ACTION SPACE — reply by writing the file {ACTION_PATH} as JSON:
  {"action": "<python pyautogui code>"}   one or more pyautogui calls, e.g.
      "import pyautogui; pyautogui.click(123, 456)"
      "import pyautogui; pyautogui.write('hello'); pyautogui.press('enter')"
  {"action": "WAIT"}    the screen is still loading, wait and re-observe
  {"action": "DONE"}    the task is fully accomplished
  {"action": "FAIL"}    the task is impossible or cannot be recovered
Coordinates are absolute screen pixels. Exactly one JSON object, no
commentary in the file. Write the file with the Write tool, then stop.

## {ACTION_SCHEMA} block, condition B (prepixel)

ACTION SCHEMA — reply by writing the file {ACTION_PATH} as ONE JSON object.
Targets are the eN ids from the view; the driver resolves all geometry.
  {"action":"click","target":"e17"}                    activate element e17
  {"action":"set_value","target":"e17","value":"132"}  set a field's value
  {"action":"toggle","target":"e18","to":true}         set a toggle/checkbox
  {"action":"type","text":"hello"}                     type into current focus
  {"action":"key","keys":"ctrl+alt+t"}                 key or chord (pyautogui
                                                       names, joined with +)
  {"action":"scroll_to","target":"e19"}                bring an [offscreen]
                                                       element into view
  {"action":"crop","target":"e21"}                     get the pixels of a
                                                       [pixels] line (costs
                                                       one step)
  {"action":"wait"}    the screen is still loading, wait and re-observe
  {"action":"done"}    the task is fully accomplished
  {"action":"fail"}    the task is impossible or cannot be recovered
Exactly one JSON object, no commentary in the file. Write the file with the
Write tool, then stop.

## {OBSERVATION} block, condition A (pixels)

The current screen is the screenshot image at:
{SCREENSHOT_PATH}
Read it (as an image) before deciding. Previous screenshots (up to 3, oldest
first) are at:
{PREV_SCREENSHOT_PATHS}

## {OBSERVATION} block, condition B (prepixel)

The current screen as a structured view. Grammar: `eN <type> x,y,w,h
"content"` — eN is the element id, valid for THIS step only; `value="…"` is
the current value; `state=…` lists element states (checked:true/false,
pressed, selected, expanded, focused); `eN [offscreen] …` exists on the page
but outside the viewport (scroll_to makes it actionable); `[pixels] …` is a
DECLARED opaque region whose content the structure cannot read (crop shows
its pixels); `[self-inconsistent: …]` means the structure declares content it
does not expose (crop shows the region's pixels):
{VIEW_OR_DIFF}
{ACT_GUARD_LINE}
Full current view with ids: {VIEW_PATH}
(Read that file if you need an element not shown above.) Previous views (up
to 3, oldest first) are at:
{PREV_VIEW_PATHS}
