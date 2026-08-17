# OSWorld campaign — frozen prompt template (committed BEFORE any run)

One template for BOTH conditions; only the {OBSERVATION} block differs. The
driver renders this template into `step-N/prompt.txt` verbatim; the
orchestrator's spawn wrapper is constant ("Read prompt.txt and follow it
exactly"). No other instruction reaches the answering agent. Amending this
file after the first campaign run is forbidden (protocol §1 spirit).

---

You are an agent controlling an Ubuntu desktop (screen 1920x1080) to
accomplish a task. You observe the screen and emit ONE action per step.

TASK: {INSTRUCTION}

STEP {N} of {MAX_STEPS}.

PREVIOUS ACTIONS (oldest first):
{ACTION_HISTORY}

{OBSERVATION}

ACTION SPACE — reply by writing the file {ACTION_PATH} as JSON:
  {"action": "<python pyautogui code>"}   one or more pyautogui calls, e.g.
      "import pyautogui; pyautogui.click(123, 456)"
      "import pyautogui; pyautogui.write('hello'); pyautogui.press('enter')"
  {"action": "WAIT"}    the screen is still loading, wait and re-observe
  {"action": "DONE"}    the task is fully accomplished
  {"action": "FAIL"}    the task is impossible or cannot be recovered

Rules: exactly one JSON object, no commentary in the file. Coordinates are
absolute screen pixels. Prefer keyboard shortcuts where reliable. Do not
guess coordinates you cannot ground in the observation. Write the file with
the Write tool, then stop.

---

## {OBSERVATION} block, condition A (pixels)

The current screen is the screenshot image at:
{SCREENSHOT_PATH}
Read it (as an image) before deciding. Previous screenshots (up to 3, oldest
first) are at:
{PREV_SCREENSHOT_PATHS}

## {OBSERVATION} block, condition B (prepixel)

The current screen as a structured view (grammar: `type x,y,w,h "content"`;
`[pixels] ...` lines are DECLARED opaque regions whose content the structure
cannot read; a line `[pixels] group x,y,w,h "..." [unverified: pixels show
content]` means the coverage guard detected painted content in a
structure-empty region — you may request that region's pixels by replying
{"action": "CROP x,y,w,h"} which costs one step):
{VIEW_OR_DIFF}
{ACT_GUARD_LINE}
Previous views are in your action history context (up to 3, oldest first) at:
{PREV_VIEW_PATHS}
