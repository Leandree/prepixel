#!/usr/bin/env python3
"""OSWorld condition driver v2 (OSWORLD-PROTOCOL.md §2 +
manager_orders/DRIVER-V2-SPEC.md) — file-mailbox variant.

Boots the OSWorld docker VM for ONE task × ONE condition, then loops:
  1. capture observation (screenshot always; a11y tree in condition B),
  2. condition B: distill to id-carrying records (e1, e2, …), re-probe
     declared-count contradictions once, coverage-guard spot-check, render
     the view + diff (system bar y<28 excluded from all diffs),
  3. render the FROZEN prompt template into <out>/step-N/prompt.txt,
  4. wait for the answering agent to write <out>/step-N/action.json,
  5. condition B: resolve element-reference actions through the LADDER —
     (1) AT-SPI platform action inside the VM (EditableText/Value/Action/
     Selection/Text-caret/grabFocus via run_python_script), (2) pointer
     synthesis at the rect center clamped to the viewport, (3) resolution
     failure -> error observation, never a guess. Every rung choice is
     logged per step.
  6. settle: fixed post-action budget IDENTICAL in both conditions
     (A sleeps SETTLE_BUDGET; B re-captures the tree until two consecutive
     identical captures or the budget runs out),
  7. condition B: act-guard v2 — re-read the TARGETED element only
     (rect + 8 px margin) and attach CONFIRMED / UNVERIFIED (with the
     re-read state) / EXPLICIT_FAILURE to the next prompt. No hidden retry:
     the model decides what happens after an UNVERIFIED.
On termination (DONE/FAIL/max steps) runs the OSWorld evaluator and writes
<out>/result.json (protocol §3 schema + driver-v2 mechanics accounting:
resolution rungs, settle/guard time, re-probes — harness cost reported
separately from model cost, spec §3).

The answering agent is EXTERNAL (Claude Code subagent in the pilot; any
model via the API backend otherwise) — this driver never calls a model, has
no task heuristics, no replanning, no autonomous retry (spec §3).

Known deviation, logged per action in mechanics.json and in the returns
file: rung 2's partial-occlusion sub-rule (anchor at the visible subregion
center) is NOT implemented — AT-SPI gives no reliable z-order; anchor is
always the full-rect center. Occurrences where this could matter are
detectable in traces as UNVERIFIED verdicts on rung-2 clicks.

Development phase (manager_orders/DEV-PHASE-PLAN.md), tuned on the 20
disjoint dev tasks only:
  P2 the driver echoes what it typed as `typed-by-driver="…"` on the focused
     element, labelled as the driver's own record (the payload does not
     expose entry text — probe_entry_text.py, 0/1951 nodes),
  P5 a `memo` field, identical in both conditions, carried verbatim to the
     next step and truncated at MEMO_LIMIT,
  P6 B carries HISTORY_DEPTH previous views inline, matching the previous
     screenshots condition A always carried,
  P7 rung 1 widened BY INTERFACE, never by app: Selection.selectChild on the
     parent when a child exposes no usable Action, Text.setCaretOffset after
     grabFocus so a following `type` appends deterministically.

Usage:
  python run_condition.py --domain chrome --task-id <uuid> --condition A|B \
      --out runs/<id>-A [--max-steps 15] [--osworld ~/dev/OSWorld]
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


CHROMIUM_APPS = ("chromium", "google-chrome", "chrome")
WEB_DOC_ROLES = ("document-web", "document-frame")
CDP_TIMEOUT = 25            # s; a slow page must not stall the whole step


def _inside(rect, box, tol=2):
    """Is this AT-SPI record WHOLLY inside the web content area?

    Containment, not centre-in-box. A centre test looked equivalent and is
    not: the Chromium window frame is centred inside its own content rect,
    so a centre test swallows it — and with it the window title, which is
    the one line naming what the user is looking at. Containment keeps
    anything larger than the content area (the frame, the window, the
    desktop) on AT-SPI, which is the channel that knows about them, and
    replaces only what is genuinely page content.

    An element straddling the boundary stays on AT-SPI too. That can
    duplicate a CDP line for the same thing, which is a visible redundancy
    rather than a silent disappearance — the right way round for this
    campaign."""
    x, y, w, h = rect
    bx, by, bw, bh = box
    return (x >= bx - tol and y >= by - tol
            and x + w <= bx + bw + tol and y + h <= by + bh + tol)


def _chromium_content_rect(tree_xml):
    """Screen rect of the web content area of the ACTIVE Chromium window.

    This is the router's SIGNATURE step (DEV-PHASE-PLAN P1): the channel is
    chosen per window from what the window is, not from the task. A window
    qualifies when its application is a Chromium and it exposes a
    document-web/document-frame that is showing, visible and on screen; the
    largest such rect is the content area, everything outside it is browser
    chrome and stays on AT-SPI.

    Returns (rect, app_name) or (None, reason) so the reason can be logged —
    a router that silently declines is indistinguishable from one that never
    ran.
    """
    try:
        root = ET.fromstring(tree_xml or "<desktop-frame/>")
    except Exception as e:
        return None, "tree-parse: %s" % str(e)[:80]
    best, app_seen = None, None
    for app in root.iter("application"):
        name = (app.get("name") or "").strip().lower()
        if not any(c in name for c in CHROMIUM_APPS):
            continue
        app_seen = name
        for node in app.iter():
            if node.tag not in WEB_DOC_ROLES:
                continue
            if distill_osworld._position(node, VW, VH) != "on":
                continue
            x, y, w, h = distill_osworld._coords(node)
            if w * h > 0 and (best is None or w * h > best[2] * best[3]):
                best = (x, y, w, h)
    if best:
        return best, app_seen
    return None, ("no on-screen web document in %r" % app_seen
                  if app_seen else "no chromium application in the tree")


def _cost_accounting(out, model):
    """Sum what the answering model actually consumed, from the CLI's own
    envelopes in each step's answer-meta.json.

    Two subtleties, both of which would silently distort the comparison:
    the CLI bills a small helper model of its own alongside the answering
    model, so usage is filtered to the model under test; and re-attempts
    after an unparseable reply are real spend, so every attempt is counted,
    not just the one that produced the action."""
    tot = {"input_tokens": 0, "cache_creation_input_tokens": 0,
           "cache_read_input_tokens": 0, "output_tokens": 0,
           "cost_usd": 0.0, "attempts": 0, "steps_with_usage": 0,
           "steps_missing_usage": 0}
    for name in sorted(os.listdir(out)):
        if not name.startswith("step-"):
            continue
        p = os.path.join(out, name, "answer-meta.json")
        if not os.path.exists(p):
            continue
        try:
            meta = json.load(open(p))
        except Exception:
            continue
        saw = False
        for att in meta.get("attempts", []):
            tot["attempts"] += 1
            mu = att.get("model_usage") or {}
            # `model` is the CLI's own name for the answering model; the
            # helper model's key will not match it.
            for key, u in mu.items():
                if model and key != model:
                    continue
                saw = True
                tot["input_tokens"] += u.get("inputTokens", 0)
                tot["cache_creation_input_tokens"] += u.get(
                    "cacheCreationInputTokens", 0)
                tot["cache_read_input_tokens"] += u.get(
                    "cacheReadInputTokens", 0)
                tot["output_tokens"] += u.get("outputTokens", 0)
                tot["cost_usd"] += u.get("costUSD", 0.0) or 0.0
        tot["steps_with_usage" if saw else "steps_missing_usage"] += 1
    tot["cost_usd"] = round(tot["cost_usd"], 6)
    return tot


def _git_head():
    """The exact driver a cell was produced by. The manager's freeze rule —
    every final cell carries the freeze hash — only works if the hash is
    stamped at run time, not transcribed afterwards.

    Dev iterations run from a pinned COPY outside the repo, where `git -C`
    would find nothing, so the runner passes the commit it pinned; the git
    call is the fallback for a driver invoked directly from the worktree."""
    env = os.environ.get("CAMPAIGN_DRIVER_COMMIT")
    if env:
        return env
    try:
        return subprocess.check_output(
            ["git", "-C", HERE, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"

spec = importlib.util.spec_from_file_location(
    "distill_osworld", os.path.join(HERE, "distill-osworld.py"))
distill_osworld = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distill_osworld)
_q = distill_osworld._q
_state_str = distill_osworld._state_str

TEMPLATE = open(os.path.join(HERE, "prompt-template.md")).read()

# Fixed post-action budget, identical in both conditions (§2.5): A spends it
# as env.step's pause, B as its settle deadline. Sized from measurement: one
# a11y capture costs ~1.5 s on this host, so a 2 s budget would let B's second
# capture overrun A's sleep. At 4 s, B's typical settle (2 captures, ~3 s)
# stays UNDER A's fixed sleep, so B is never handed more stabilisation time
# than A — the asymmetry, if any, is against the condition under test.
SETTLE_BUDGET = 4.0
TOPBAR_Y = 28           # px, system bar excluded from ALL diffs (§2.4)
GUARD_MARGIN = 8        # px, act-guard match margin around the target (§2.4)
WAIT_SLEEP = 5          # s, model-requested WAIT (unchanged from v1)
SCROLL_CLICKS = 5       # fixed increment for the D2 scroll action
VW, VH = 1920, 1080
# Roles where a click means "put the caret here", not "activate me"
TEXT_INPUT_ROLES = {"entry", "text", "password-text", "searchbox", "textbox",
                    "textfield", "textarea", "terminal", "document-text",
                    "document-web", "document-frame", "spin-button"}


def template_section(block, marker):
    part = TEMPLATE.split(f"## {{{block}}} block, condition {marker}")[1]
    return part.split("\n## ")[0].strip()


BODY = TEMPLATE.split("---")[1].strip()
HISTORY_DEPTH = 3       # previous observations carried by condition A
# P6, second pass. Matching A's history COUNT was wrong and iteration 1
# measured how wrong: on libreoffice_calc-42e0a640 condition B's prompt
# reached 245 000 characters against A's 3 200 plus four images, and that
# cell cost $17.51 against A's $2.01 — eight times the run's median.
#
# A screenshot costs the same whatever is on it (1920x1080 -> ~3 700 tokens
# by the repo's own imgTokensClaude); a structured view of a spreadsheet
# costs 12 500. Three of each is the same NUMBER of observations and four
# times the payload. The symmetry that means something is the BUDGET, so B
# gets as many recent views as fit inside what A's three screenshots cost,
# and the prompt says plainly when views were left out.
#
# The current view is never truncated — D1 requires it inlined in full, and
# a responder that has never seen the previous step cannot be handed a diff
# against it. Only history is capped.
HISTORY_TOKEN_BUDGET = 3 * 3686     # A's three screenshots, in tokens
CHARS_PER_TOKEN = 4                 # coarse, applied only to B's own history


def _history_block(prev_views):
    """Most recent previous views that fit A's history budget, oldest first.
    Returns (block, n_dropped)."""
    if not prev_views:
        return "(none)", 0
    budget = HISTORY_TOKEN_BUDGET * CHARS_PER_TOKEN
    chosen = []
    for n, v in reversed(prev_views):
        cost = len(v) + 40
        if cost > budget:
            break
        budget -= cost
        chosen.append((n, v))
        if len(chosen) >= HISTORY_DEPTH:
            break
    dropped = len(prev_views) - len(chosen)
    if not chosen:
        return ("(none — the previous views did not fit the history budget "
                "this condition is allowed; the view above is complete)",
                dropped)
    block = "\n\n".join(f"--- view at step {n} ---\n{v}"
                        for n, v in reversed(chosen))
    if dropped:
        block += ("\n\n(%d earlier view(s) omitted: history budget)" % dropped)
    return block, dropped
MEMO_LIMIT = 300        # characters, mechanically truncated (P5)

OBS_A = template_section("OBSERVATION", "A (pixels)")
OBS_B = template_section("OBSERVATION", "B (prepixel)")
SCHEMA_A = template_section("ACTION_SCHEMA", "A (pixels)")
SCHEMA_B = template_section("ACTION_SCHEMA", "B (prepixel)")


def judge_crop(png_path, rect):
    """Run the repo's shipped judgeCrop on a rect of the screenshot."""
    out = subprocess.run(
        ["node", os.path.join(HERE, "judge-crop.mjs"), png_path,
         *(str(v) for v in rect)],
        capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout) if out.returncode == 0 else None


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _center(rect):
    return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0


def _is_topbar(rec):
    return rec["kind"] in ("element", "text", "pixels") \
        and 0 <= rec["rect"][1] < TOPBAR_Y


# ---------------------------------------------------------------- rung 1 ---
# AT-SPI platform action executed INSIDE the VM (spec §2.2 rung 1). The
# script walks only subtrees whose extents intersect the target rect
# (spatial pruning), has a hard internal time guard, and prints one JSON
# line. Any failure -> the driver falls to rung 2, logged.
# Parameters are injected as a JSON literal header (the body is full of dict
# literals, so str.format is not usable here).
PLATFORM_SCRIPT = r'''
import json, time
def _run():
    try:
        import pyatspi
    except Exception as e:
        return {"ok": False, "err": "pyatspi-import: %s" % e}
    ROLE = P["role"]; TX = P["x"]; TY = P["y"]; TW = P["w"]; TH = P["h"]
    VERB = P["verb"]; VALUE = P["value"]
    T0 = time.time()
    best = [None, None]
    near = []                   # diagnostics when the target is not found
    def extents(acc):
        # same call the OSWorld server uses to build cp:screencoord/cp:size,
        # so the rects we match against are the rects the view showed
        try:
            b = acc.queryComponent().getExtents(pyatspi.XY_SCREEN)
            return int(b[0]), int(b[1]), int(b[2]), int(b[3])
        except Exception:
            return None
    def visit(acc, depth):
        if acc is None or depth > 30 or time.time() - T0 > 10:
            return
        ext = extents(acc)
        try:
            # the server builds XML tags as getRoleName().strip() with spaces
            # turned into dashes ("spin button" -> "spin-button"); match the
            # same normalisation or nothing is ever found
            role = (acc.getRoleName().strip() or "unknown").replace(" ", "-")
        except Exception:
            return
        if ext is not None and role == ROLE:
            x, y, w, h = ext
            d = abs(x - TX) + abs(y - TY) + abs(w - TW) + abs(h - TH)
            if d <= 24 and (best[1] is None or d < best[1]):
                best[0], best[1] = acc, d
            elif len(near) < 5:
                near.append({"rect": [x, y, w, h], "dist": d})
        if ext is not None and ext[2] > 0 and ext[3] > 0 and depth <= 3:
            # spatial pruning only near the top of the tree (other apps and
            # other windows). Deeper containers are NOT pruned: measured on
            # gnome-terminal's Preferences, a stack/viewport ancestor reports
            # extents that do not cover the page it currently shows, and
            # pruning on it made every widget of that page unreachable.
            x, y, w, h = ext
            if x > TX + TW or y > TY + TH or x + w < TX or y + h < TY:
                return
        try:
            n = min(acc.childCount, 256)
        except Exception:
            return
        for i in range(n):
            try:
                visit(acc.getChildAtIndex(i), depth + 1)
            except Exception:
                pass
    try:
        desktop = pyatspi.Registry.getDesktop(0)
        for i in range(desktop.childCount):
            try:
                visit(desktop.getChildAtIndex(i), 0)
            except Exception:
                pass
    except Exception as e:
        return {"ok": False, "err": "walk: %s" % e}
    acc = best[0]
    if acc is None:
        return {"ok": False, "err": "node-not-found",
                "walk_s": round(time.time() - T0, 2), "near": near}
    try:
        if VERB == "set_value":
            # Value first: on a spin button / slider it is the semantic
            # setter. Writing the entry text alone can leave the underlying
            # adjustment on its old value until the widget is activated.
            try:
                vi = acc.queryValue()
                vi.currentValue = float(VALUE)
                return {"ok": True, "method": "Value.currentValue"}
            except Exception:
                pass
            try:
                et = acc.queryEditableText()
                et.setTextContents(str(VALUE))
                committed = None
                try:
                    ai = acc.queryAction()
                    names = [ai.getName(i).lower() for i in range(ai.nActions)]
                    if "activate" in names:
                        ai.doAction(names.index("activate"))
                        committed = "Action.activate"
                except Exception:
                    pass
                return {"ok": True,
                        "method": "EditableText.setTextContents"
                                  + ("+" + committed if committed else "")}
            except Exception as e:
                # Python 3 unbinds the exception name at the end of the
                # block; keep the message for the final report.
                settable_err = str(e)
            # P7, from the dev-set fallback log: `no-settable-interface`
            # fired 5 times, and the case behind it was a chrome://flags
            # dropdown asked to become "Disabled". A combo-box has no
            # settable text and no numeric value — its value IS which child
            # is selected. Generic by interface: Selection, matching the
            # child by its name.
            try:
                sel = acc.querySelection()
                want = str(VALUE).strip().lower()
                for i in range(acc.childCount):
                    ch = acc.getChildAtIndex(i)
                    if (ch.name or "").strip().lower() == want:
                        if sel.selectChild(i):
                            return {"ok": True,
                                    "method": "Selection.selectChild(name)"}
                        break
                # A collapsed combo-box often keeps its options one level
                # down, in a menu/list child that is the real Selection.
                for i in range(acc.childCount):
                    kid = acc.getChildAtIndex(i)
                    try:
                        ksel = kid.querySelection()
                    except Exception:
                        continue
                    for j in range(kid.childCount):
                        gc = kid.getChildAtIndex(j)
                        if (gc.name or "").strip().lower() == want:
                            if ksel.selectChild(j):
                                return {
                                    "ok": True,
                                    "method": "Selection.selectChild(child)"}
                            break
                return {"ok": False,
                        "err": "no-option-named: %r" % str(VALUE)[:40]}
            except Exception:
                pass
            return {"ok": False,
                    "err": "no-settable-interface: %s" % settable_err}
        if VERB in ("click", "toggle"):
            if P["text_input"]:
                # On a text field, AT-SPI's "activate" means SUBMIT, not
                # "put the caret here". Measured on chrome://settings:
                # activating the search box moved focus to another tab and
                # the following keystrokes went there. Focus is the click.
                try:
                    acc.queryComponent().grabFocus()
                except Exception as e:
                    return {"ok": False, "err": "grabFocus: %s" % e}
                # P7: put the caret at the end so a following `type` appends
                # predictably instead of landing wherever the caret happened
                # to be. Text is an interface, not an app special case.
                caret = None
                try:
                    ti = acc.queryText()
                    ti.setCaretOffset(ti.characterCount)
                    caret = "+Text.setCaretOffset"
                except Exception:
                    pass
                return {"ok": True,
                        "method": "Component.grabFocus" + (caret or "")}
            names = []
            try:
                ai = acc.queryAction()
                names = [ai.getName(i).lower() for i in range(ai.nActions)]
                # `dodefault` leads because the dev-set log says so: Chrome
                # exposes exactly ['doDefault', 'showContextMenu'] on its web
                # content nodes, and without it rung 1 declined on every one
                # of them. It is also the AT-SPI action that MEANS "do the
                # thing this element does", so it belongs first on merit.
                for pref in ("dodefault", "click", "press", "toggle",
                             "activate", "jump"):
                    if pref in names:
                        done = ai.doAction(names.index(pref))
                        if done:
                            return {"ok": True, "method": "Action.%s" % pref}
            except Exception:
                pass
            # P7: no usable Action — the fallback logs pointed at list items,
            # table cells and combo-box children, whose real interface is
            # Selection on the PARENT. Generic by interface, not by app.
            try:
                parent = acc.parent
                sel = parent.querySelection()
                idx = acc.getIndexInParent()
                if idx >= 0 and sel.selectChild(idx):
                    return {"ok": True, "method": "Selection.selectChild"}
            except Exception:
                pass
            return {"ok": False,
                    "err": "no-usable-action: %s" % (names or "no-interface")}
        if VERB == "focus":
            acc.queryComponent().grabFocus()
            return {"ok": True, "method": "Component.grabFocus"}
        return {"ok": False, "err": "unknown-verb"}
    except Exception as e:
        return {"ok": False, "err": "verb: %s" % e}
print("OSW_RESULT:" + json.dumps(_run()))
'''


class Driver:
    """Deterministic mechanics for one run (spec §3: no task heuristics,
    no replanning, no autonomous retry — the ladder is actuation choice,
    logged, not a retry)."""

    def __init__(self, env, condition, out):
        self.env = env
        self.ctrl = env.controller
        self.condition = condition
        self.out = out
        self.platform_available = None
        self.cur_tree = None
        self.cur_records = None
        self.prev_diff_base = []    # previous view minus system bar (kbd guard)
        self.pending_expect = None  # (what, wanted) the last action asked for
        self.typed_echo = None      # P2: what the driver last typed, and where
        self.prev_views = []        # P6: previous rendered views, oldest first
        self.web_meta = {}          # P1: last CDP page meta (url, scroll, …)
        self.mech_total = {"platform_available": None, "rung1": 0, "rung2": 0,
                           "kbd": 0, "resolve_errors": 0, "noop_toggles": 0,
                           "rung1_fallbacks": 0, "settle_ms_total": 0,
                           "settle_captures_total": 0, "guard_ms_total": 0,
                           "reprobes": 0, "scroll_iters_total": 0,
                           "waits_after_settle": 0, "scrolls": 0,
                           "declared_count_mismatches": 0, "typed_echoes": 0,
                           "memos_carried": 0,
                           # P1 router: how often the web channel was chosen,
                           # what it cost, and how much of the AT-SPI view it
                           # replaced. A decline is counted too — the router
                           # declining is a measurement, not a non-event.
                           "cdp_steps": 0, "cdp_declines": 0,
                           "cdp_ms_total": 0, "cdp_records_total": 0,
                           "atspi_records_replaced": 0,
                           "guard_suspects_superseded": 0,
                           "cdp_actions": 0, "cdp_action_failures": 0,
                           "cdp_scroll_to": 0}

    # -------------------------------------------------------------- probe --
    def probe_platform(self):
        """Rung 1 is only available if the VM's /run_python interpreter can
        import pyatspi AND reach the session's a11y registry (the bus is
        inherited from the server process; import alone proves nothing)."""
        r = self.ctrl.run_python_script(
            "import pyatspi\n"
            "d = pyatspi.Registry.getDesktop(0)\n"
            "print('OSW_PLATFORM_OK', d.childCount)\n")
        self.platform_available = bool(
            r and r.get("status") == "success"
            and "OSW_PLATFORM_OK" in (r.get("output") or ""))
        self.mech_total["platform_probe"] = (
            (r or {}).get("output", "").strip()
            or ((r or {}).get("error") or "")[:200])
        self.mech_total["platform_available"] = self.platform_available
        return self.platform_available

    # ------------------------------------------------------------ capture --
    def settle(self, mech):
        """Re-capture the tree until two consecutive identical captures or
        SETTLE_BUDGET exhausted (B). Returns the final tree."""
        t0 = time.time()
        tree = self.ctrl.get_accessibility_tree()
        caps = 1
        while time.time() - t0 < SETTLE_BUDGET:
            nxt = self.ctrl.get_accessibility_tree()
            caps += 1
            if nxt == tree:
                tree = nxt
                break
            tree = nxt
        ms = int((time.time() - t0) * 1000)
        mech["settle_ms"] = ms
        mech["settle_captures"] = caps
        self.mech_total["settle_ms_total"] += ms
        self.mech_total["settle_captures_total"] += caps
        return tree

    def distill(self, tree):
        return distill_osworld.distill(tree or "<desktop-frame/>", VW, VH)

    # ------------------------------------------------------------- router --
    def route_web(self, tree, records, suspects, mech):
        """Per-window channel router (P1): AT-SPI for the desktop, CDP for
        the content area of an active Chromium window.

        The composition rule is geometric and one-directional: AT-SPI records
        whose centre lies inside the web content rect are REPLACED by the CDP
        records for that same rect. Browser chrome — tabs, omnibox, toolbar,
        the window frame — is outside the rect and stays on AT-SPI, which is
        the channel that actually knows about it.

        The router is strictly OPPORTUNISTIC. It never launches or restarts
        Chrome: CDP exists in this VM only because the task's own setup asked
        for it (measured: 4 of the 20 dev tasks, 79 of 369 corpus-wide — and
        they are the tasks where the browser is the subject, because
        OSWorld's own evaluator needs the same port). Relaunching Chrome to
        get a better channel would hand condition B an environment condition
        A never had, which would not be a measurement any more.
        """
        rect, why = _chromium_content_rect(tree)
        mech["channel"] = "atspi"
        if rect is None:
            mech["cdp"] = {"used": False, "reason": why}
            return records, suspects
        port = getattr(self.env, "chromium_port", None)
        if not port:
            mech["cdp"] = {"used": False, "reason": "no chromium_port on env"}
            return records, suspects
        x, y, w, h = rect
        t0 = time.time()
        try:
            p = subprocess.run(
                ["node", os.path.join(HERE, "cdp_view.mjs"),
                 "--endpoint", "http://localhost:%d" % port,
                 "--offset", "%d,%d" % (x, y)],
                capture_output=True, text=True, timeout=CDP_TIMEOUT)
            out = json.loads(p.stdout or "{}")
        except Exception as e:
            out = {"ok": False, "error": "%s: %s" % (type(e).__name__,
                                                     str(e)[:120])}
        ms = int((time.time() - t0) * 1000)
        if not out.get("ok"):
            # Declining is a normal outcome (no debug port on this task), so
            # it is logged, not raised, and the AT-SPI view is unchanged.
            mech["cdp"] = {"used": False, "ms": ms, "rect": list(rect),
                           "reason": out.get("error", "no output")}
            self.mech_total["cdp_declines"] += 1
            return records, suspects
        web = out.get("records", [])
        kept = [r for r in records if not _inside(r["rect"], rect)]
        dropped = len(records) - len(kept)
        # The coverage guard's suspects for this region were suspicions about
        # AT-SPI's blindness, and AT-SPI is no longer the channel reading it.
        # They are superseded rather than ignored: the CDP channel declares
        # its OWN blind spots (canvas, img, cross-origin frames) as [pixels].
        # Counted, so "the guard went quiet here" stays visible in the record.
        sup = [s for s in suspects if not _inside(s["rect"], rect)]
        self.mech_total["guard_suspects_superseded"] += len(suspects) - len(sup)
        mech["channel"] = "atspi+cdp"
        mech["cdp"] = {"used": True, "ms": ms, "rect": list(rect),
                       "atspi_records_replaced": dropped,
                       "cdp_records": len(web),
                       "offscreen": out.get("meta", {}).get(
                           "offscreen_emitted", 0),
                       "url": out.get("meta", {}).get("url", "")[:200],
                       "scroll": out.get("meta", {}).get("scroll"),
                       "scroll_height": out.get("meta", {}).get(
                           "scrollHeight")}
        skipped = out.get("meta", {}).get("offscreen_skipped", 0)
        if skipped:
            # No silent caps — the AT-SPI channel already declares its
            # offscreen overflow in the view itself, and a web channel that
            # quietly stopped at 60 would be the same silent blind spot this
            # campaign exists to catch. Measured on dota2.com: the cap
            # saturated at 60 with more below it.
            web.append({"kind": "note", "role": "note", "rect": [0, 0, 0, 0],
                        "label": "", "value": "", "states": {},
                        "line": f"[offscreen] +{skipped} more lines truncated "
                                f"(scroll to reveal)"})
            mech["cdp_offscreen_skipped"] = skipped
        self.mech_total["cdp_steps"] += 1
        self.mech_total["cdp_ms_total"] += ms
        self.mech_total["cdp_records_total"] += len(web)
        self.mech_total["atspi_records_replaced"] += dropped
        self.web_meta = out.get("meta", {})
        return kept + web, sup

    # ------------------------------------------------------------- render --
    def build_view(self, step_dir, shot_path, mech):
        """distill + re-probe + coverage guard + id assignment.
        Returns (view_text, registry, diff_base_raw_lines, n_susp, n_hits)."""
        records, suspects, incons = self.distill(self.cur_tree)
        if incons:
            # §2.5 re-probe: one extra walk before declaring a contradiction
            self.mech_total["reprobes"] += 1
            mech["reprobes"] = mech.get("reprobes", 0) + 1
            self.cur_tree = self.ctrl.get_accessibility_tree()
            records, suspects, incons = self.distill(self.cur_tree)
            for ic in incons:
                # D3: state both raw facts, judge neither
                x, y, w, h = ic["rect"]
                self.mech_total["declared_count_mismatches"] += 1
                records.append({
                    "kind": "pixels", "role": "group", "rect": ic["rect"],
                    "label": ic["declaring_text"], "value": "", "states": {},
                    "line": f"[pixels] group {x},{y},{w},{h} "
                            f"declares={ic['declared']} "
                            f"exposes={ic['exposed']}"})
        records, suspects = self.route_web(
            self.cur_tree, records, suspects, mech)
        n_hits = 0
        for s in suspects:
            j = judge_crop(shot_path, s["rect"])
            if j and j.get("silentRisk"):
                n_hits += 1
                x, y, w, h = s["rect"]
                records.append({
                    "kind": "pixels", "role": "group", "rect": s["rect"],
                    "label": s["label"], "value": "", "states": {},
                    "line": f'[pixels] group {x},{y},{w},{h} '
                            f'"{s["label"]}" [unverified: pixels show '
                            f'content]'})
        # P2: annotate the focused element with the driver's typing record
        echo = self.typed_echo
        if echo:
            focused = [r for r in records if r["states"].get("focused")]
            if focused:
                tgt = focused[0]
                if echo["rect"] is None or tgt["rect"] == echo["rect"]:
                    tgt["line"] += f' typed-by-driver={_q(echo["text"])}'
                else:
                    self.typed_echo = None      # focus moved: record is stale
        registry = {}
        out_lines = []
        previous = set(self.prev_diff_base or [])
        first = not self.prev_diff_base
        for i, rec in enumerate(records, 1):
            eid = f"e{i}"
            registry[eid] = rec
            # D1 inlines the whole view every step, so the diff's signal is
            # carried by a one-character mark instead of a separate block
            mark = "" if (first or _is_topbar(rec)
                          or rec["line"] in previous) else "~"
            out_lines.append(f"{mark}{eid} {rec['line']}")
        self.cur_records = records
        diff_base = [r["line"] for r in records if not _is_topbar(r)]
        return "\n".join(out_lines), registry, diff_base, len(suspects), n_hits

    # ------------------------------------------------------------ resolve --
    def _anchor(self, rec):
        cx, cy = _center(rec["rect"])
        return (int(max(0, min(VW - 1, cx))), int(max(0, min(VH - 1, cy))))

    def _platform(self, rec, verb, value, mech):
        x, y, w, h = rec["rect"]
        params = {"role": rec["role"], "x": x, "y": y, "w": w, "h": h,
                  "verb": verb, "value": str(value),
                  "text_input": rec["role"] in TEXT_INPUT_ROLES}
        # repr, not json.dumps: JSON writes `true`, which is not Python and
        # made the whole script die on line 1 (measured — rung 1 silently
        # fell back to the pointer on every text field)
        script = "P = " + repr(params) + "\n" + PLATFORM_SCRIPT
        r = self.ctrl.run_python_script(script)
        outp = (r or {}).get("output") or ""
        m = re.search(r"OSW_RESULT:(\{.*\})", outp)
        if m:
            res = json.loads(m.group(1))
        else:
            res = {"ok": False,
                   "err": "no-result (status=%s, err=%s)"
                          % ((r or {}).get("status"),
                             ((r or {}).get("error") or "")[:120])}
        mech["platform_result"] = res
        return res

    def _pyautogui(self, code):
        """Rung-2 actuation. Executed through the controller, NOT env.step:
        env.step bundles its own pause + full observation, which would make
        the post-action delay asymmetric with condition A (spec §2.5 demands
        one identical fixed budget). The settle loop is the only delay."""
        r = self.ctrl.execute_python_command(code)
        if r is None:
            raise RuntimeError("controller refused the pyautogui command")
        return r

    def execute(self, act, registry, mech):
        """Resolve + execute one condition-B action.
        Returns (history_line, verdict_or_None, needs_settle, before_rec)."""
        kind = str(act.get("action", "")).lower()
        mech["action_kind"] = kind
        # what the action ASKED for; the guard checks the ask, not just "did
        # anything move" (§2.4: an unmet ask must come back as UNVERIFIED
        # with the re-read state, e.g. still value="80")
        self.pending_expect = None
        if kind == "set_value":
            self.pending_expect = ("value", str(act.get("value", "")))
        elif kind == "toggle":
            self.pending_expect = ("checked", bool(act.get("to", True)))

        if kind in ("wait", "done", "fail"):
            return kind, None, kind == "wait", None

        if kind in ("click", "set_value", "toggle", "scroll_to", "crop"):
            tid = act.get("target", "")
            rec = registry.get(tid)
            if rec is None:
                self.mech_total["resolve_errors"] += 1
                mech["resolve_error"] = f"unknown target {tid!r}"
                ids = f"e1..e{len(registry)}" if registry else "(empty view)"
                return (f"{kind} {tid} (RESOLUTION ERROR)",
                        f"EXPLICIT_FAILURE (resolution: unknown target "
                        f"{tid!r}; current view has {ids})", False, None)
            if rec["rect"][2] <= 0 or rec["rect"][3] <= 0:
                self.mech_total["resolve_errors"] += 1
                mech["resolve_error"] = "empty rect"
                return (f"{kind} {tid} (RESOLUTION ERROR)",
                        "EXPLICIT_FAILURE (resolution: element has an empty "
                        "rect)", False, None)
            label = f'{rec["role"]} {_q(rec["label"])}' if rec["label"] \
                else f'{rec["role"]} {",".join(map(str, rec["rect"]))}'

            if kind == "crop":
                return self._do_crop(rec, label, mech)
            if kind == "scroll_to":
                return self._do_scroll_to(rec, label, mech)
            if kind == "toggle":
                want = bool(act.get("to", True))
                cur = rec["states"].get("checked")
                if cur is not None and cur == want:
                    self.mech_total["noop_toggles"] += 1
                    mech["noop"] = True
                    return (f"toggle {label} -> {str(want).lower()}",
                            f"CONFIRMED (already checked:"
                            f"{str(want).lower()} — no action executed)",
                            False, None)
            value = act.get("value", "")
            err = self._act_on(rec, kind, value, mech)
            hist = {"click": f"click {label}",
                    "toggle": f"toggle {label} -> "
                              f"{str(bool(act.get('to', True))).lower()}",
                    "set_value": f"set_value {label} := {_q(str(value))}",
                    }[kind]
            if err:
                return hist, f"EXPLICIT_FAILURE ({err[:160]})", False, rec
            return hist, None, True, rec

        if kind == "scroll":
            # D2: mechanical, no element reference, same family as key/type.
            # The driver owns the increment; the model never computes a delta.
            direction = str(act.get("direction", "down")).lower()
            if direction not in ("up", "down"):
                self.mech_total["resolve_errors"] += 1
                mech["resolve_error"] = f"unknown direction {direction!r}"
                return (f"scroll {direction} (RESOLUTION ERROR)",
                        f"EXPLICIT_FAILURE (resolution: direction must be "
                        f"\"up\" or \"down\", got {direction!r})", False, None)
            self.mech_total["scrolls"] += 1
            mech["rung"] = "scroll"
            clicks = SCROLL_CLICKS if direction == "up" else -SCROLL_CLICKS
            try:
                self._pyautogui(f"import pyautogui; "
                                f"pyautogui.moveTo({VW // 2}, {VH // 2}); "
                                f"pyautogui.scroll({clicks})")
            except Exception as e:
                return (f"scroll {direction}",
                        f"EXPLICIT_FAILURE ({str(e)[:160]})", False, None)
            return f"scroll {direction}", None, True, "KBD"

        if kind == "type":
            text = str(act.get("text", ""))
            self.mech_total["kbd"] += 1
            mech["rung"] = "kbd"
            # P2: the driver KNOWS what it typed — that is its own action, not
            # a reading of the screen. Recorded here, surfaced on the focused
            # element, and always labelled as a driver record.
            focused = next((r for r in (self.cur_records or [])
                            if r["states"].get("focused")), None)
            self.typed_echo = {"text": text,
                               "rect": focused["rect"] if focused else None}
            self.mech_total["typed_echoes"] += 1
            try:
                self._pyautogui("import pyautogui; "
                                f"pyautogui.typewrite({text!r}, interval=0.02)")
            except Exception as e:
                return (f"type {_q(text)}",
                        f"EXPLICIT_FAILURE ({str(e)[:160]})", False, None)
            return f"type {_q(text)}", None, True, "KBD"

        if kind == "key":
            keys = str(act.get("keys", ""))
            parts = [k.strip() for k in keys.split("+") if k.strip()]
            self.mech_total["kbd"] += 1
            mech["rung"] = "kbd"
            try:
                if len(parts) > 1:
                    arg = ", ".join(repr(p) for p in parts)
                    self._pyautogui(f"import pyautogui; pyautogui.hotkey({arg})")
                elif parts:
                    self._pyautogui(f"import pyautogui; "
                                    f"pyautogui.press({parts[0]!r})")
                else:
                    return ("key (empty)", "EXPLICIT_FAILURE (empty keys)",
                            False, None)
            except Exception as e:
                return (f"key {keys}",
                        f"EXPLICIT_FAILURE ({str(e)[:160]})", False, None)
            return f"key {keys}", None, True, "KBD"

        self.mech_total["resolve_errors"] += 1
        mech["resolve_error"] = f"unknown action kind {kind!r}"
        return (f"{kind or '(empty)'} (RESOLUTION ERROR)",
                f"EXPLICIT_FAILURE (resolution: unknown action kind "
                f"{kind!r})", False, None)

    def _cdp_act(self, rec, verb, value, mech):
        """Rung 1 for an element the WEB channel described.

        Symmetry matters here: rung 1 is defined as "the platform's own
        action for the channel that described the element". For AT-SPI that
        is pyatspi inside the VM; for a CDP-described element it is the DOM.
        Routing a web element through AT-SPI instead would make rung 1 fail
        for reasons that have nothing to do with the web channel's quality.
        """
        port = getattr(self.env, "chromium_port", None)
        if not port:
            return {"ok": False, "err": "no chromium_port"}
        op = {"click": "click", "toggle": "toggle",
              "set_value": "set_value", "scroll_to": "scroll_to",
              "focus": "focus"}.get(verb, "click")
        cmd = ["node", os.path.join(HERE, "cdp_act.mjs"),
               "--endpoint", "http://localhost:%d" % port,
               "--handle", str(rec.get("h", -1)), "--op", op]
        if value is not None:
            cmd += ["--value", str(value)]
        if verb == "toggle":
            cmd += ["--to", "true" if value else "false"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=CDP_TIMEOUT)
            return json.loads(p.stdout or '{"ok":false,"err":"no output"}')
        except Exception as e:
            return {"ok": False,
                    "err": "%s: %s" % (type(e).__name__, str(e)[:120])}

    def _act_on(self, rec, verb, value, mech):
        """Ladder rungs 1-2 for click/toggle/set_value. Returns err or None."""
        if rec.get("src") == "cdp":
            res = self._cdp_act(rec, verb, value, mech)
            if res.get("ok"):
                self.mech_total["rung1"] += 1
                self.mech_total["cdp_actions"] += 1
                mech["rung"] = 1
                mech["rung1_method"] = "cdp:" + str(res.get("method"))
                if res.get("noop"):
                    self.mech_total["noop_toggles"] += 1
                return None
            self.mech_total["rung1_fallbacks"] += 1
            self.mech_total["cdp_action_failures"] += 1
            mech["rung1_error"] = "cdp: %s" % res.get("err")
            # Deliberately falls through to rung 2 rather than to AT-SPI: the
            # element was described in web terms, so an AT-SPI lookup for it
            # would be a guess, and the pointer at least aims at the rect the
            # model was actually shown.
            return self._rung2(rec, verb, value, mech)
        if self.platform_available:
            res = self._platform(rec, "click" if verb == "toggle" else verb,
                                 value, mech)
            if res.get("ok"):
                self.mech_total["rung1"] += 1
                mech["rung"] = 1
                mech["rung1_method"] = res.get("method")
                return None
            self.mech_total["rung1_fallbacks"] += 1
            mech["rung1_error"] = res.get("err")
        return self._rung2(rec, verb, value, mech)

    def _rung2(self, rec, verb, value, mech):
        """Pointer synthesis at the rect centre, clamped to the viewport."""
        self.mech_total["rung2"] += 1
        mech["rung"] = 2
        mech["occlusion_check"] = "not-implemented (full-rect center)"
        ax, ay = self._anchor(rec)
        mech["anchor"] = [ax, ay]
        try:
            if verb in ("click", "toggle"):
                self._pyautogui(f"import pyautogui; pyautogui.click({ax}, {ay})")
            elif verb == "set_value":
                self._pyautogui(
                    f"import pyautogui; pyautogui.click({ax}, {ay}); "
                    f"import time; time.sleep(0.3); "
                    f"pyautogui.hotkey('ctrl', 'a'); "
                    f"pyautogui.typewrite({str(value)!r}, interval=0.03); "
                    f"pyautogui.press('enter')")
        except Exception as e:
            return str(e)
        return None

    def _do_crop(self, rec, label, mech):
        x, y, w, h = rec["rect"]
        if x >= VW or y >= VH or x + w <= 0 or y + h <= 0:
            return (f"crop {label} (offscreen)",
                    "EXPLICIT_FAILURE (crop rect outside the viewport — "
                    "scroll_to first)", False, None)
        mech["rung"] = "crop"
        from PIL import Image
        step = int(open(os.path.join(self.out, "CURRENT_STEP")).read().strip())
        sd = os.path.join(self.out, f"step-{step}")
        # source is the guard's copy, outside any prompt-referenced path;
        # crop.png appears in the step directory ONLY because the model
        # asked for it (D1)
        img = Image.open(os.path.join(self.out, "_guard", f"step-{step}.png"))
        cx0, cy0 = max(0, x), max(0, y)
        crop_path = os.path.join(sd, "crop.png")
        img.crop((cx0, cy0, min(VW, x + w), min(VH, y + h))).save(crop_path)
        return (f"crop {label}", f"CROP served: {crop_path}", False, None)

    def _do_scroll_to(self, rec, label, mech):
        """§2.6: the driver computes the scroll, re-captures, re-resolves.
        Feedback loop, max 6 scroll rounds, every round logged.

        On a CDP-described element this is not a feedback loop at all — the
        page knows where its own content is, so one scrollIntoView puts it on
        screen exactly. That difference is the point of the router, and it is
        why scroll_to is offered again: the action was withdrawn because the
        AT-SPI path had to guess a scroll distance from rects the payload
        mostly does not supply below the fold (301 of 3047 nodes positioned).
        The AT-SPI path below is unchanged and still guesses; the web path
        does not have to."""
        if rec.get("src") == "cdp":
            res = self._cdp_act(rec, "scroll_to", None, mech)
            mech["rung"] = 1 if res.get("ok") else "scroll"
            mech["rung1_method"] = "cdp:" + str(res.get("method"))
            if res.get("ok"):
                self.mech_total["cdp_scroll_to"] += 1
                self.mech_total["rung1"] += 1
                mech["cdp_scroll"] = res.get("scroll")
                return (f"scroll_to {label}", None, True, 1)
            self.mech_total["cdp_action_failures"] += 1
            mech["rung1_error"] = "cdp: %s" % res.get("err")
            # falls through to the pointer-scroll loop below
        mech["rung"] = "scroll"
        target_role, target_label = rec["role"], rec["label"]
        cur_rect = rec["rect"]
        iters = 0
        for _ in range(6):
            cy = cur_rect[1] + cur_rect[3] / 2.0
            if TOPBAR_Y <= cy < VH and cur_rect[1] < VH \
                    and cur_rect[1] + cur_rect[3] > 0:
                break
            dy = cy - VH / 2.0
            clicks = max(1, min(10, int(abs(dy) // 80)))
            amount = -clicks if dy > 0 else clicks
            try:
                self._pyautogui(f"import pyautogui; "
                                f"pyautogui.moveTo({VW // 2}, {VH // 2}); "
                                f"pyautogui.scroll({amount})")
            except Exception as e:
                mech["scroll_iterations"] = iters
                return (f"scroll_to {label}",
                        f"EXPLICIT_FAILURE ({str(e)[:160]})", False, None)
            iters += 1
            self.cur_tree = self.settle(mech)
            records, _, _ = self.distill(self.cur_tree)
            cand = [r for r in records if r["role"] == target_role
                    and r["label"] == target_label]
            if not cand:
                cur_rect = None
                break
            cand.sort(key=lambda r: abs(r["rect"][1] + r["rect"][3] / 2
                                        - VH / 2))
            cur_rect = cand[0]["rect"]
        mech["scroll_iterations"] = iters
        self.mech_total["scroll_iters_total"] += iters
        if cur_rect is None:
            return (f"scroll_to {label}",
                    "UNVERIFIED (element not found again after scrolling — "
                    "re-observe)", False, None)
        cy = cur_rect[1] + cur_rect[3] / 2.0
        if TOPBAR_Y <= cy < VH:
            return (f"scroll_to {label}",
                    f"CONFIRMED (element now in viewport at "
                    f"{','.join(map(str, cur_rect))})", False, None)
        return (f"scroll_to {label}",
                f"UNVERIFIED (element still offscreen at "
                f"{','.join(map(str, cur_rect))} after {iters} scroll "
                f"rounds)", False, None)

    # -------------------------------------------------------------- guard --
    def scoped_guard(self, before, mech):
        """Act-guard v2 (§2.4): re-read the targeted element only."""
        t0 = time.time()
        after_records, _, _ = self.distill(self.cur_tree)
        try:
            if before == "KBD":
                return self._kbd_guard(after_records)
            bx, by, bw, bh = before["rect"]
            cand, best = None, -1.0
            for r in after_records:
                if r["role"] != before["role"] or r["kind"] == "offscreen":
                    continue
                cx, cy = _center(r["rect"])
                inside = (bx - GUARD_MARGIN <= cx <= bx + bw + GUARD_MARGIN
                          and by - GUARD_MARGIN <= cy <= by + bh + GUARD_MARGIN)
                i = _iou(r["rect"], before["rect"])
                if inside or i > 0.3:
                    score = i + (0.5 if r["label"] == before["label"] else 0)
                    if score > best:
                        cand, best = r, score
            if cand is None:
                if getattr(self, "pending_expect", None):
                    what, wanted = self.pending_expect
                    return (f"UNVERIFIED (asked {what}={wanted}, but the "
                            f"target element is no longer in the view)")
                return "CONFIRMED (element no longer present — view changed)"
            changes = []
            if cand["value"] != before["value"]:
                changes.append(f'value {_q(before["value"])}→'
                               f'{_q(cand["value"])}')
            if cand["states"] != before["states"]:
                changes.append(
                    f'state [{_state_str(before["states"]) or "none"}]→'
                    f'[{_state_str(cand["states"]) or "none"}]')
            if cand["label"] != before["label"]:
                changes.append(f'label {_q(before["label"])}→'
                               f'{_q(cand["label"])}')
            expect = getattr(self, "pending_expect", None)
            if expect:
                what, wanted = expect
                if what == "value":
                    got = cand["value"]
                    ok, via = (got == wanted), "value"
                    try:
                        ok = ok or float(got) == float(wanted)
                    except (TypeError, ValueError):
                        pass
                    if not ok and cand["label"] == wanted:
                        # Measured on libreoffice_writer-adf5e2c3-B: the guard
                        # said UNVERIFIED twice while its OWN re-read line
                        # read `text … "<add here>"` and `text … "[14]"` —
                        # the values it was asked to confirm. This payload
                        # does not expose entry text as `value` at all (0 of
                        # 1951 nodes, probe_entry_text.py); it exposes it as
                        # the label. Demanding `value` was demanding proof the
                        # channel structurally cannot give, so every set_value
                        # on a text field came back unverified and the model
                        # paid for it in steps.
                        ok, via = True, "label"
                    if not ok:
                        return (f'UNVERIFIED (asked value={_q(wanted)}, '
                                f'element re-read: {cand["line"]})')
                    if via == "label":
                        return (f'CONFIRMED (asked value={_q(wanted)}, found '
                                f'as the element\'s text — this channel does '
                                f'not expose entry values: {cand["line"]})')
                elif what == "checked":
                    if cand["states"].get("checked") is not wanted:
                        return (f'UNVERIFIED (asked checked:'
                                f'{str(wanted).lower()}, element re-read: '
                                f'{cand["line"]})')
            if changes:
                return "CONFIRMED (" + ", ".join(changes) + ")"
            return f"UNVERIFIED (element re-read unchanged: still {cand['line']})"
        finally:
            ms = int((time.time() - t0) * 1000)
            mech["guard_ms"] = ms
            self.mech_total["guard_ms_total"] += ms

    def _kbd_guard(self, after_records):
        """type/key have no target element: scope = view minus system bar
        (§2.4 excludes the clock band from EVERY diff), plus the focused
        element's re-read line."""
        before_lines = self.prev_diff_base or []
        after_lines = [r["line"] for r in after_records if not _is_topbar(r)]
        foc = next((r for r in after_records
                    if r["states"].get("focused")), None)
        suffix = f"; focus: {foc['line']}" if foc else ""
        if after_lines != before_lines:
            return f"CONFIRMED (view changed outside the system bar{suffix})"
        return f"UNVERIFIED (view unchanged outside the system bar{suffix})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--condition", required=True, choices=["A", "B"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--osworld", default=os.path.expanduser("~/dev/OSWorld"))
    ap.add_argument("--phase", default="development",
                    choices=["development", "campaign"])
    ap.add_argument("--step-timeout", type=int, default=1200,
                    help="seconds to wait for action.json before infra_failure")
    args = ap.parse_args()

    sys.path.insert(0, args.osworld)
    from desktop_env.desktop_env import DesktopEnv

    task_path = os.path.join(args.osworld, "evaluation_examples", "examples",
                             args.domain, f"{args.task_id}.json")
    task = json.load(open(task_path))
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=(args.condition == "B"))
    try:
        obs = env.reset(task_config=task)
    except Exception as e:
        # A setup that cannot run is a fact about the cell, and a cell with
        # no result.json is indistinguishable from one that was never
        # launched. Measured on the dev set: two multi_apps tasks need Google
        # Drive credentials this host does not have, and they failed leaving
        # nothing behind. Write the record, then get out.
        json.dump({
            "task_id": args.task_id, "domain": args.domain,
            "condition": args.condition,
            "model": os.environ.get("CAMPAIGN_MODEL", "UNSET"),
            "driver": "v3-dev", "phase": args.phase,
            "driver_commit": _git_head(),
            "success": False, "score_raw": None, "steps": 0,
            "termination": "setup_error", "wall_clock_s": round(
                time.time() - t0, 1),
            "infra_failure": True,
            "notes": "env.reset failed before step 1: %s" % str(e)[:400],
            "actions": [],
        }, open(os.path.join(args.out, "result.json"), "w"), indent=1)
        open(os.path.join(args.out, "CURRENT_STEP"), "w").write("FINISHED")
        try:
            env.close()
        except Exception:
            pass
        print(json.dumps({"task_id": args.task_id,
                          "condition": args.condition,
                          "termination": "setup_error",
                          "infra_failure": True}))
        return
    drv = Driver(env, args.condition, args.out)
    if args.condition == "B":
        drv.probe_platform()
        drv.cur_tree = obs.get("accessibility_tree") or ""
    cur_shot = obs["screenshot"]

    actions, act_verdicts = [], []
    memo = None                 # P5: verbatim note the answerer left itself
    prev_obs_paths = []
    pixel_fallbacks = guard_hits_total = suspects_total = 0
    infra_failure, term = False, "max_steps"

    for step in range(1, args.max_steps + 1):
        sd = os.path.join(args.out, f"step-{step}")
        os.makedirs(sd, exist_ok=True)
        mech = {}
        # D1: pixels never sit beside the prompt. Condition A's screenshot is
        # alone in its own per-step directory (it IS A's channel); the
        # coverage guard's copy lives in a sibling tree no prompt names.
        if args.condition == "A":
            pdir = os.path.join(args.out, "_pixels", f"step-{step}")
            os.makedirs(pdir, exist_ok=True)
            shot = os.path.join(pdir, "screenshot.png")
        else:
            gdir = os.path.join(args.out, "_guard")
            os.makedirs(gdir, exist_ok=True)
            shot = os.path.join(gdir, f"step-{step}.png")
        open(shot, "wb").write(cur_shot)

        if args.condition == "A":
            observation = OBS_A.replace("{SCREENSHOT_PATH}", shot) \
                .replace("{PREV_SCREENSHOT_PATHS}",
                         "\n".join(prev_obs_paths[-HISTORY_DEPTH:]) or "(none)")
            prev_obs_paths.append(shot)
            schema = SCHEMA_A
        else:
            view, registry, raw_lines, n_susp, n_hits = \
                drv.build_view(sd, shot, mech)
            suspects_total += n_susp
            guard_hits_total += n_hits
            open(os.path.join(sd, "view.txt"), "w").write(view)
            # D1: the view is INLINE and complete; `~` marks changed lines,
            # so nothing sends the model to a file
            drv.prev_diff_base = raw_lines
            verdict_line = act_verdicts[-1] if act_verdicts else ""
            prev_block, dropped = _history_block(drv.prev_views)
            mech["history_views"] = len(drv.prev_views) - dropped
            mech["history_views_dropped"] = dropped
            observation = OBS_B.replace("{VIEW}", view) \
                .replace("{ACT_GUARD_LINE}",
                         f"[act-guard] previous action: {verdict_line}"
                         if verdict_line else "") \
                .replace("{PREV_VIEWS}", prev_block)
            drv.prev_views.append((step, view))
            schema = SCHEMA_B

        mech["memo_in"] = bool(memo)
        history = "\n".join(f"{i+1}. {a}" for i, a in enumerate(actions)) or "(none)"
        prompt = BODY.replace("{INSTRUCTION}", task["instruction"]) \
            .replace("{N}", str(step)).replace("{MAX_STEPS}", str(args.max_steps)) \
            .replace("{ACTION_HISTORY}", history) \
            .replace("{MEMO}", memo or "(none)") \
            .replace("{OBSERVATION}", observation) \
            .replace("{ACTION_SCHEMA}", schema)
        open(os.path.join(sd, "prompt.txt"), "w").write(prompt)
        # signal readiness for the orchestrator
        open(os.path.join(args.out, "CURRENT_STEP"), "w").write(str(step))

        apath = os.path.join(sd, "action.json")
        # The answering side raises this when the API refuses the call —
        # rate limit, or a server-side 5xx that persisted through the whole
        # backoff. That is an infrastructure fact, not the model failing the
        # task, and the two must never end up in the same column. Dev
        # iteration 2 is the reason this is explicit: 21 `529 Overloaded`
        # replies turned four cells that had SUCCEEDED in iteration 1 into
        # step_timeout failures.
        rl_path = os.path.join(args.out, "API_UNAVAILABLE")
        waited = 0
        while not os.path.exists(apath):
            if os.path.exists(rl_path):
                infra_failure = True
                term = "api_unavailable: " + open(rl_path).read()[:200]
                break
            time.sleep(2)
            waited += 2
            if waited > args.step_timeout:
                infra_failure, term = True, "step_timeout"
                break
        if infra_failure:
            break
        time.sleep(1)  # let the writer finish
        act_raw = json.load(open(apath))
        # P5: carried verbatim, mechanically truncated, identical in A and B
        new_memo = act_raw.get("memo")
        if isinstance(new_memo, str) and new_memo.strip():
            memo = new_memo.strip()[:MEMO_LIMIT]
            drv.mech_total["memos_carried"] += 1
            mech["memo_out"] = True
        elif new_memo is not None:
            memo = None

        if args.condition == "A":
            action = str(act_raw["action"]).strip()
            actions.append(action)
            up = action.upper()
            if up in ("DONE", "FAIL"):
                term = up
                break
            if up == "WAIT":
                time.sleep(WAIT_SLEEP + SETTLE_BUDGET)
                cur_shot = env.controller.get_screenshot() or cur_shot
                continue
            try:
                # reference path, unchanged (§3); pause = the same fixed
                # post-action budget B spends in its settle loop (§2.5)
                a_obs, _r, _d, _i = env.step(action, pause=SETTLE_BUDGET)
                cur_shot = a_obs["screenshot"] or cur_shot
            except Exception as e:
                mech["exec_error"] = str(e)[:200]
                cur_shot = env.controller.get_screenshot() or cur_shot
            json.dump(mech, open(os.path.join(sd, "mechanics.json"), "w"),
                      indent=1)
            continue

        # ---------------- condition B ----------------
        kind = str(act_raw.get("action", "")).lower()
        if kind == "done" or kind == "fail":
            actions.append(kind)
            term = kind.upper()
            break
        if kind == "wait":
            actions.append("wait")
            time.sleep(WAIT_SLEEP)
            drv.cur_tree = drv.settle(mech)
            cur_shot = env.controller.get_screenshot() or cur_shot
            act_verdicts.append("WAIT (no action executed)")
            drv.mech_total["waits_after_settle"] += 1
            json.dump(mech, open(os.path.join(sd, "mechanics.json"), "w"),
                      indent=1)
            continue

        hist, verdict, needs_settle, before = drv.execute(act_raw, registry,
                                                          mech)
        actions.append(hist)
        if str(act_raw.get("action", "")).lower() == "crop":
            pixel_fallbacks += 1
        if needs_settle:
            drv.cur_tree = drv.settle(mech)
            cur_shot = env.controller.get_screenshot() or cur_shot
            if verdict is None and before is not None:
                verdict = drv.scoped_guard(before, mech)
        elif verdict is not None and mech.get("rung") == "scroll":
            # scroll_to settled internally; refresh the screenshot
            cur_shot = env.controller.get_screenshot() or cur_shot
        act_verdicts.append(verdict or "UNVERIFIED (no guard basis)")
        json.dump(mech, open(os.path.join(sd, "mechanics.json"), "w"),
                  indent=1)

    score = None
    if not infra_failure:
        try:
            score = env.evaluate()
        except Exception as e:
            infra_failure = True
            term = f"evaluator_error: {str(e)[:200]}"
    env.close()

    result = {
        "task_id": args.task_id, "domain": args.domain,
        "condition": args.condition,
        "model": os.environ.get("CAMPAIGN_MODEL", "UNSET"),
        "driver": "v3-dev",
        # Defaults to "development" on purpose: a campaign cell mislabelled as
        # dev is a bookkeeping nuisance, a dev cell mislabelled as campaign is
        # a corrupted record. The final run passes --phase campaign explicitly.
        "phase": args.phase,
        "driver_commit": _git_head(),
        "success": bool(score) if score is not None else False,
        "score_raw": score, "steps": len(actions), "termination": term,
        "wall_clock_s": round(time.time() - t0, 1),
        "pixel_fallbacks": pixel_fallbacks if args.condition == "B" else None,
        "guard_hits": guard_hits_total if args.condition == "B" else None,
        "guard_suspects_checked": suspects_total if args.condition == "B" else None,
        "act_verdicts": act_verdicts if args.condition == "B" else None,
        "mechanics": drv.mech_total if args.condition == "B" else None,
        "cost": _cost_accounting(
            args.out, os.environ.get("CAMPAIGN_ANSWER_MODEL", "")),
        "infra_failure": infra_failure, "notes": "",
        "actions": actions,
    }
    json.dump(result, open(os.path.join(args.out, "result.json"), "w"), indent=1)
    open(os.path.join(args.out, "CURRENT_STEP"), "w").write("FINISHED")
    print(json.dumps({k: result[k] for k in
                      ("task_id", "condition", "success", "steps",
                       "termination", "infra_failure")}))


if __name__ == "__main__":
    main()
