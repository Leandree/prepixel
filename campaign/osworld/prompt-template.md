# OSWorld campaign — frozen prompt template v3 (committed BEFORE any run)

v3 implements the manager's rulings in `manager_orders/PILOT-V2-RULINGS.md`.

D1 (contamination): the observation is INLINE. No prompt references a file
except condition A's screenshot, which is the channel's own content and
lives alone in a per-step directory. The answering agent no longer writes
`action.json` — it returns the JSON object as its reply and the orchestrator
writes the file — so condition B's agent can run with NO tools at all and
condition A's with image reading only. One framing sentence, identical in
both conditions, closes the prompt; nothing else was added, and no
behavioural advice (§2.2) came back.

D2: condition B gains `scroll`, a mechanical action with no element
reference, in the same family as `type` and `key`.

v2→v3 diff for condition B's observation: the view is inlined in full every
step instead of a diff plus a path to the full view. A leading `~` marks
lines that changed since the previous step, so the diff's signal survives at
the cost of one character per changed line. This RAISES B's per-step token
cost versus v2 and is a direct consequence of D1 — reported, not hidden.

Amending this file after the first campaign run is forbidden (protocol §1
spirit); v1→v2→v3 all happened pre-campaign, on manager order, in git
history.

---

You are an agent controlling an Ubuntu desktop (screen 1920x1080) to
accomplish a task. You observe the screen and emit ONE action per step.

TASK: {INSTRUCTION}

STEP {N} of {MAX_STEPS}.

PREVIOUS ACTIONS (oldest first):
{ACTION_HISTORY}

{OBSERVATION}

{ACTION_SCHEMA}

Use only what this prompt gives you.

---

## {ACTION_SCHEMA} block, condition A (pixels)

ACTION SPACE — reply with exactly ONE JSON object and nothing else:
  {"action": "<python pyautogui code>"}   one or more pyautogui calls, e.g.
      "import pyautogui; pyautogui.click(123, 456)"
      "import pyautogui; pyautogui.write('hello'); pyautogui.press('enter')"
  {"action": "WAIT"}    the screen is still loading, wait and re-observe
  {"action": "DONE"}    the task is fully accomplished
  {"action": "FAIL"}    the task is impossible or cannot be recovered
Coordinates are absolute screen pixels.

## {ACTION_SCHEMA} block, condition B (prepixel)

ACTION SCHEMA — reply with exactly ONE JSON object and nothing else.
Targets are the eN ids from the view; the driver resolves all geometry.
  {"action":"click","target":"e17"}                    activate element e17
  {"action":"set_value","target":"e17","value":"132"}  set a field's value
  {"action":"toggle","target":"e18","to":true}         set a toggle/checkbox
  {"action":"type","text":"hello"}                     type into current focus
  {"action":"key","keys":"ctrl+alt+t"}                 key or chord (pyautogui
                                                       names, joined with +)
  {"action":"scroll","direction":"down"}               scroll the view ("up"
                                                       or "down", fixed step)
  {"action":"crop","target":"e21"}                     get the pixels of a
                                                       [pixels] line (costs
                                                       one step)
  {"action":"wait"}    the screen is still loading, wait and re-observe
  {"action":"done"}    the task is fully accomplished
  {"action":"fail"}    the task is impossible or cannot be recovered

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
pressed, selected, expanded, focused); a leading `~` marks a line that
changed since the previous step; `[pixels] …` is a DECLARED opaque region
whose content the structure cannot read (crop shows its pixels);
`declares=N exposes=M` on a region means the structure announces N items
there and exposes M of them:
{VIEW}
{ACT_GUARD_LINE}
