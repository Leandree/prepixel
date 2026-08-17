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
     grabFocus via run_python_script), (2) pointer synthesis at the rect
     center clamped to the viewport, (3) resolution failure -> error
     observation, never a guess. Every rung choice is logged per step.
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

Usage:
  python run_condition.py --domain chrome --task-id <uuid> --condition A|B \
      --out runs/<id>-A [--max-steps 15] [--osworld ~/dev/OSWorld]
"""
import argparse
import difflib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "distill_osworld", os.path.join(HERE, "distill-osworld.py"))
distill_osworld = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distill_osworld)
_q = distill_osworld._q
_state_str = distill_osworld._state_str

TEMPLATE = open(os.path.join(HERE, "prompt-template.md")).read()

SETTLE_BUDGET = 2.0     # s, fixed post-action delay, identical A and B (§2.5)
TOPBAR_Y = 28           # px, system bar excluded from ALL diffs (§2.4)
GUARD_MARGIN = 8        # px, act-guard match margin around the target (§2.4)
WAIT_SLEEP = 5          # s, model-requested WAIT (unchanged from v1)
VW, VH = 1920, 1080


def template_section(block, marker):
    part = TEMPLATE.split(f"## {{{block}}} block, condition {marker}")[1]
    return part.split("\n## ")[0].strip()


BODY = TEMPLATE.split("---")[1].strip()
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
            role = acc.getRoleName()
        except Exception:
            return
        if ext is not None and role == ROLE:
            x, y, w, h = ext
            d = abs(x - TX) + abs(y - TY) + abs(w - TW) + abs(h - TH)
            if d <= 24 and (best[1] is None or d < best[1]):
                best[0], best[1] = acc, d
        if ext is not None and ext[2] > 0 and ext[3] > 0:
            x, y, w, h = ext
            if x > TX + TW or y > TY + TH or x + w < TX or y + h < TY:
                return          # spatial pruning: subtree cannot contain it
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
        return {"ok": False, "err": "node-not-found"}
    try:
        if VERB == "set_value":
            try:
                et = acc.queryEditableText()
                et.setTextContents(str(VALUE))
                return {"ok": True, "method": "EditableText.setTextContents"}
            except Exception:
                pass
            try:
                vi = acc.queryValue()
                vi.currentValue = float(VALUE)
                return {"ok": True, "method": "Value.currentValue"}
            except Exception as e:
                return {"ok": False, "err": "no-settable-interface: %s" % e}
        if VERB in ("click", "toggle"):
            try:
                ai = acc.queryAction()
            except Exception:
                return {"ok": False, "err": "no-action-interface"}
            names = [ai.getName(i).lower() for i in range(ai.nActions)]
            for pref in ("click", "press", "toggle", "activate", "jump"):
                if pref in names:
                    done = ai.doAction(names.index(pref))
                    return {"ok": bool(done),
                            "method": "Action.%s" % pref,
                            "err": None if done else "doAction returned False"}
            return {"ok": False, "err": "no-usable-action: %s" % names}
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
        self.mech_total = {"platform_available": None, "rung1": 0, "rung2": 0,
                           "kbd": 0, "resolve_errors": 0, "noop_toggles": 0,
                           "rung1_fallbacks": 0, "settle_ms_total": 0,
                           "settle_captures_total": 0, "guard_ms_total": 0,
                           "reprobes": 0, "scroll_iters_total": 0,
                           "waits_after_settle": 0}

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
                x, y, w, h = ic["rect"]
                records.append({
                    "kind": "pixels", "role": "group", "rect": ic["rect"],
                    "label": ic["declaring_text"], "value": "", "states": {},
                    "line": f"[pixels] group {x},{y},{w},{h} "
                            f"[self-inconsistent: declares "
                            f"{ic['declaring_text']}, exposes 0 rows]"})
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
        registry = {}
        out_lines = []
        for i, rec in enumerate(records, 1):
            eid = f"e{i}"
            registry[eid] = rec
            out_lines.append(f"{eid} {rec['line']}")
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
                  "verb": verb, "value": str(value)}
        script = "P = " + json.dumps(params) + "\n" + PLATFORM_SCRIPT
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

        if kind == "type":
            text = str(act.get("text", ""))
            self.mech_total["kbd"] += 1
            mech["rung"] = "kbd"
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

    def _act_on(self, rec, verb, value, mech):
        """Ladder rungs 1-2 for click/toggle/set_value. Returns err or None."""
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
        img = Image.open(os.path.join(sd, "screenshot.png"))
        cx0, cy0 = max(0, x), max(0, y)
        crop_path = os.path.join(sd, "crop.png")
        img.crop((cx0, cy0, min(VW, x + w), min(VH, y + h))).save(crop_path)
        return (f"crop {label}", f"CROP served: {crop_path}", False, None)

    def _do_scroll_to(self, rec, label, mech):
        """§2.6: the driver computes the scroll, re-captures, re-resolves.
        Feedback loop, max 6 scroll rounds, every round logged."""
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
    obs = env.reset(task_config=task)
    drv = Driver(env, args.condition, args.out)
    if args.condition == "B":
        drv.probe_platform()
        drv.cur_tree = obs.get("accessibility_tree") or ""
    cur_shot = obs["screenshot"]

    actions, act_verdicts = [], []
    prev_raw_lines, prev_obs_paths = None, []
    pixel_fallbacks = guard_hits_total = suspects_total = 0
    infra_failure, term = False, "max_steps"

    for step in range(1, args.max_steps + 1):
        sd = os.path.join(args.out, f"step-{step}")
        os.makedirs(sd, exist_ok=True)
        shot = os.path.join(sd, "screenshot.png")
        open(shot, "wb").write(cur_shot)
        mech = {}

        if args.condition == "A":
            observation = OBS_A.replace("{SCREENSHOT_PATH}", shot) \
                .replace("{PREV_SCREENSHOT_PATHS}",
                         "\n".join(prev_obs_paths[-3:]) or "(none)")
            prev_obs_paths.append(shot)
            schema = SCHEMA_A
        else:
            view, registry, raw_lines, n_susp, n_hits = \
                drv.build_view(sd, shot, mech)
            suspects_total += n_susp
            guard_hits_total += n_hits
            vpath = os.path.join(sd, "view.txt")
            open(vpath, "w").write(view)
            id_of = {rec["line"]: eid for eid, rec in registry.items()}
            if prev_raw_lines is None:
                shown = view
            else:
                diff = [d for d in difflib.unified_diff(
                            prev_raw_lines, raw_lines, lineterm="", n=0)
                        if not d.startswith(("---", "+++", "@@"))]
                rendered = []
                for d in diff:
                    body_line = d[1:]
                    if d.startswith("+"):
                        rendered.append(f"+ {id_of.get(body_line, '?')} "
                                        f"{body_line}")
                    else:
                        rendered.append(f"- {body_line}")
                if len(diff) < 0.6 * max(1, len(raw_lines)):
                    shown = ("[diff vs previous view — system bar excluded; "
                             "ids are current-step ids]\n"
                             + "\n".join(rendered)) if rendered \
                        else "[no change vs previous view]"
                else:
                    shown = view + "\n[diff inapplicable: full view re-emitted]"
            prev_raw_lines = raw_lines
            drv.prev_diff_base = raw_lines
            verdict_line = act_verdicts[-1] if act_verdicts else ""
            observation = OBS_B.replace("{VIEW_OR_DIFF}", shown) \
                .replace("{ACT_GUARD_LINE}",
                         f"[act-guard] previous action: {verdict_line}"
                         if verdict_line else "") \
                .replace("{VIEW_PATH}", vpath) \
                .replace("{PREV_VIEW_PATHS}",
                         "\n".join(prev_obs_paths[-3:]) or "(none)")
            prev_obs_paths.append(vpath)
            schema = SCHEMA_B

        history = "\n".join(f"{i+1}. {a}" for i, a in enumerate(actions)) or "(none)"
        prompt = BODY.replace("{INSTRUCTION}", task["instruction"]) \
            .replace("{N}", str(step)).replace("{MAX_STEPS}", str(args.max_steps)) \
            .replace("{ACTION_HISTORY}", history) \
            .replace("{OBSERVATION}", observation) \
            .replace("{ACTION_SCHEMA}",
                     schema.replace("{ACTION_PATH}",
                                    os.path.join(sd, "action.json")))
        open(os.path.join(sd, "prompt.txt"), "w").write(prompt)
        # signal readiness for the orchestrator
        open(os.path.join(args.out, "CURRENT_STEP"), "w").write(str(step))

        apath = os.path.join(sd, "action.json")
        waited = 0
        while not os.path.exists(apath):
            time.sleep(2)
            waited += 2
            if waited > args.step_timeout:
                infra_failure, term = True, "step_timeout"
                break
        if infra_failure:
            break
        time.sleep(1)  # let the writer finish
        act_raw = json.load(open(apath))

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
        "driver": "v2",
        "success": bool(score) if score is not None else False,
        "score_raw": score, "steps": len(actions), "termination": term,
        "input_tokens": None, "output_tokens": None,   # filled by orchestrator
        "wall_clock_s": round(time.time() - t0, 1),
        "pixel_fallbacks": pixel_fallbacks if args.condition == "B" else None,
        "guard_hits": guard_hits_total if args.condition == "B" else None,
        "guard_suspects_checked": suspects_total if args.condition == "B" else None,
        "act_verdicts": act_verdicts if args.condition == "B" else None,
        "mechanics": drv.mech_total if args.condition == "B" else None,
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
