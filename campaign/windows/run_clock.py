# -*- coding: utf-8 -*-
"""Cell: windows-clock-uia. Clock app (Microsoft.WindowsAlarms, WinUI/XAML).

T4 living screen on the stopwatch, mirroring the macOS Clock cell (38 B/tick).
macOS lesson encoded: NEVER touch a stopwatch that is already running — check
state in-channel first; only start if it reads zero, and reset it afterwards.
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-clock-uia"}
probe = auto.WindowControl(searchDepth=1, RegexName="Horloge|Clock")
if not probe.Exists(2):
    subprocess.Popen(["explorer.exe",
                      r"shell:AppsFolder\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"])
    time.sleep(4.0)

win = auto.WindowControl(searchDepth=1, RegexName="Horloge|Clock")
if not win.Exists(10):
    print(json.dumps({"error": "clock window not found"})); sys.exit(1)

def force_foreground(w):
    hwnd = w.NativeWindowHandle
    for attempt in range(5):
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        try: w.SetActive()
        except Exception: pass
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.5)
        if ctypes.windll.user32.GetForegroundWindow() == hwnd:
            return attempt + 1
    return -1

out["foreground_attempts"] = force_foreground(win)
wrect = rect_of(win)
out["window_rect"] = wrect

view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
save_artifact("clock-uia-view-initial.txt", view)

def find_line(vtext, names):
    for l in vtext.splitlines():
        for n in names:
            if f'"{n}"' in l or n in l:
                return l
    return None

def guarded_click_line(line):
    x, y, w, h = map(int, line.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    if not top or top.NativeWindowHandle != win.NativeWindowHandle:
        return False
    blind_click(cx, cy)
    return True

# navigate to the stopwatch page (Chronomètre) via the nav item in the view
nav = find_line(view, ["Chronomètre", "Stopwatch"])
out["nav_line"] = nav
if nav and guarded_click_line(nav):
    time.sleep(1.5)
else:
    print(json.dumps({**out, "error": "could not navigate to stopwatch"})); sys.exit(1)

sview, _ = distill(win)
save_artifact("clock-uia-view-stopwatch.txt", sview)

# SAFETY: only start if the stopwatch is at zero and not running
state_ok = ("00:00" in sview) and (find_line(sview, ["Démarrer", "Start"]) is not None)
running_already = find_line(sview, ["Arrêter", "Pause", "Interrompre"]) is not None and "00:00" not in sview
out["stopwatch_pristine"] = state_ok
out["stopwatch_already_running"] = running_already
t4 = {"pass": False}
if state_ok and not running_already:
    start = find_line(sview, ["Démarrer", "Start"])
    if start and guarded_click_line(start):
        time.sleep(1.0)
        # poll ~1 Hz: full-window diff AND the time element alone
        ticks = []
        prev, _ = distill(win)
        for i in range(6):
            time.sleep(1.0)
            t0 = time.perf_counter()
            cur, _ = distill(win)
            lat = (time.perf_counter() - t0) * 1000
            d = "\n".join(difflib.unified_diff(prev.splitlines(), cur.splitlines(), lineterm=""))
            # the minimal semantic diff: just the changed lines
            changed = [l for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
            ticks.append({"tick": i + 1, "diff_bytes": len(d.encode("utf-8")),
                          "changed_line_bytes": sum(len(c.encode('utf-8')) for c in changed),
                          "changed_lines": len(changed), "capture_ms": round(lat, 1),
                          "sample": changed[0][:90] if changed else ""})
            prev = cur
        t4["ticks"] = ticks
        t4["pass"] = all(t["changed_lines"] > 0 for t in ticks)
        save_artifact("clock-uia-tick-diff.txt", d)
        # pause, then idle measurement, then reset to pristine
        cur_pause, _ = distill(win)
        pl = find_line(cur_pause, ["Arrêter", "Pause", "Interrompre"])
        if pl and guarded_click_line(pl):
            time.sleep(1.0)
        idle_prev, _ = distill(win)
        time.sleep(1.5)
        idle_cur, _ = distill(win)
        idiff = "\n".join(difflib.unified_diff(idle_prev.splitlines(), idle_cur.splitlines(), lineterm=""))
        out["idle_diff_bytes_paused"] = len(idiff.encode("utf-8"))
        rview, _ = distill(win)
        rl = find_line(rview, ["Réinitialiser", "Reset"])
        if rl and guarded_click_line(rl):
            time.sleep(0.8)
            fview, _ = distill(win)
            out["reset_to_pristine"] = "00:00" in fview
        if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
            screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                           "artifacts", "windows", "clock-uia-shot.png"))
out["t4"] = t4
win.GetPattern(auto.PatternId.WindowPattern).Close()
print(json.dumps(out, ensure_ascii=False, indent=1))
