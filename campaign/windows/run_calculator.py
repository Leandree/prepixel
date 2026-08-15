# -*- coding: utf-8 -*-
"""Cell: windows-calculator-uia. Windows 11 Calculator (WinUI/XAML).

Round 2 — round 1 failed for a harness reason worth keeping as data:
SetForegroundWindow was silently denied (foreground lock), Calculator stayed
BEHIND Notepad, and the blind clicks landed in the wrong app. Mitigations now
encoded, per the briefs: (a) force + VERIFY foreground before acting,
(b) hit-test guard before every blind click — the element under the point must
belong to the target process (Windows analog of AXUIElementCopyElementAtPosition).
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-calculator-uia"}
probe = auto.WindowControl(searchDepth=1, RegexName="Calculatrice|Calculator")
if not probe.Exists(2):
    subprocess.Popen(["explorer.exe",
                      r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"])
    time.sleep(3.0)

win = auto.WindowControl(searchDepth=1, RegexName="Calculatrice|Calculator")
if not win.Exists(8):
    print(json.dumps({"error": "calculator window not found"})); sys.exit(1)

def force_foreground(w):
    """SetActive can be silently denied (foreground lock). Force with the ALT
    trick and VERIFY via GetForegroundWindow — never trust the call."""
    hwnd = w.NativeWindowHandle
    for attempt in range(5):
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)      # ALT down releases the lock
        try:
            w.SetActive()
        except Exception:
            pass
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)      # ALT up
        time.sleep(0.5)
        if ctypes.windll.user32.GetForegroundWindow() == hwnd:
            return attempt + 1
    return -1

out["foreground_attempts"] = force_foreground(win)
if out["foreground_attempts"] < 0:
    print(json.dumps({"error": "could not verify foreground", **out})); sys.exit(1)
time.sleep(0.5)
wrect = rect_of(win)
out["window_rect"] = wrect

view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"]}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
save_artifact("calculator-uia-view.txt", view)

t0 = time.perf_counter(); distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                               "artifacts", "windows", "calculator-uia-shot.png"))
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
out["screenshot_tokens_legacy"] = image_tokens(wrect[2], wrect[3], "legacy")

t1 = {"pass": False}
for line in view.splitlines():
    if "affichage est" in line.lower() or "display is" in line.lower():
        t1["display_line"] = line; t1["pass"] = True; break
out["t1"] = t1

inter = [l for l in view.splitlines() if l.split(" ")[0] in
         ("button", "menuitem", "radiobutton", "listitem", "togglebutton")]
out["t2"] = {"interactive_lines": len(inter)}

def find_line(view_text, names):
    for l in view_text.splitlines():
        for n in names:
            if f'"{n}"' in l:
                return l
    return None

def guarded_blind_click(cx, cy, expect_hwnd):
    """Hit-test BEFORE clicking: whoever owns the pixel gets the click.
    UWP quirk found live: the frame window belongs to ApplicationFrameHost.exe
    while its CONTENT belongs to CalculatorApp.exe — a pid guard false-blocks.
    Guard on the top-level window identity instead."""
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    hwnd = top.NativeWindowHandle if top else None
    if hwnd != expect_hwnd:
        return {"blocked": True, "owner_pid": el.ProcessId if el else None,
                "owner_hwnd": hwnd}
    blind_click(cx, cy)
    return {"blocked": False}

calc_pid = win.NativeWindowHandle
t5 = {"pass": False, "steps": [], "guard": "UIA ControlFromPoint -> GetTopLevelControl hwnd check before every click (pid guard false-blocks on UWP frame/content process split)"}
seq = [("Deux", "Two"), ("Plus", "Plus"), ("Trois", "Three"), ("Est égal à", "Equals")]
cur_view, diffs, ok = view, [], True
for names in seq:
    line = find_line(cur_view, names)
    if not line:
        t5["steps"].append({"target": names[0], "error": "not found in view"}); ok = False; break
    x, y, w, h = map(int, line.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    g = guarded_blind_click(cx, cy, calc_pid)
    step = {"target": names[0], "clicked": [cx, cy], **g}
    if g["blocked"]:
        t5["steps"].append(step); ok = False; break
    time.sleep(0.6)
    new_view, _ = distill(win)
    d = "\n".join(difflib.unified_diff(cur_view.splitlines(), new_view.splitlines(), lineterm=""))
    step["diff_bytes"] = len(d.encode("utf-8"))
    diffs.append(step["diff_bytes"])
    t5["steps"].append(step)
    cur_view = new_view
out["interaction_diff_bytes"] = diffs

res_line = None
for l in cur_view.splitlines():
    if "affichage est" in l.lower() or "display is" in l.lower():
        res_line = l; break
t5["result_line"] = res_line
t5["pass"] = ok and res_line is not None and "5" in (res_line or "")
out["t5_t3"] = t5
save_artifact("calculator-uia-final-view.txt", cur_view)
if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "calculator-uia-final-shot.png"))

v_idle, _ = distill(win)
idiff = "\n".join(difflib.unified_diff(cur_view.splitlines(), v_idle.splitlines(), lineterm=""))
out["idle_diff_bytes"] = len(idiff.encode("utf-8"))

win.GetPattern(auto.PatternId.WindowPattern).Close()
print(json.dumps(out, ensure_ascii=False, indent=1))
