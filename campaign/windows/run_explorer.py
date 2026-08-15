# -*- coding: utf-8 -*-
"""Cell: windows-explorer-uia. File Explorer (win32 shell, CabinetWClass).

Mirror of the macOS Finder cell: throwaway folder with 3 files, enumerate,
blind-click one file, verify the selection flipped IN CHANNEL (SelectionItem).
"""
import ctypes, json, os, shutil, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-explorer-uia"}
folder = os.path.join(os.environ["TEMP"], "pipeline-tap-explorer")
os.makedirs(folder, exist_ok=True)
with open(os.path.join(folder, "alpha.txt"), "w") as f: f.write("alpha")
with open(os.path.join(folder, "beta.md"), "w") as f: f.write("beta")
# tiny valid PNG (1x1 red)
png = bytes.fromhex("89504e470d0a1a0a0000000d494844520000000100000001080200000090"
                    "7753de0000000c4944415408d763f8cfc00000030101" "9a9c1800000000"
                    "49454e44ae426082")
with open(os.path.join(folder, "gamma.png"), "wb") as f: f.write(png)

subprocess.Popen(["explorer.exe", folder])
time.sleep(3.0)

win = auto.WindowControl(searchDepth=1, RegexName=".*pipeline-tap-explorer.*")
if not win.Exists(10):
    print(json.dumps({"error": "explorer window not found"})); sys.exit(1)

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

t0 = time.perf_counter()
view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"]}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
save_artifact("explorer-uia-view.txt", view)

t0 = time.perf_counter(); distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

# T1/T2: the three files must appear as items
t2 = {"files_seen": [n for n in ("alpha.txt", "beta.md", "gamma.png") if n in view]}
t2["pass"] = len(t2["files_seen"]) == 3
out["t2"] = t2

# T5: blind-click beta.md from its view line; verify selection in channel
t5 = {"pass": False}
target = None
for l in view.splitlines():
    if "beta.md" in l and l.startswith("listitem"):
        target = l; break
if target is None:
    for l in view.splitlines():
        if "beta.md" in l:
            target = l; break
t5["target_line"] = target
if target:
    x, y, w, h = map(int, target.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    if top and top.NativeWindowHandle == win.NativeWindowHandle:
        blind_click(cx, cy)
        time.sleep(1.0)
        nview, _ = distill(win)
        sel_line = None
        for l in nview.splitlines():
            if "beta.md" in l and "selected=True" in l:
                sel_line = l; break
        others_sel = [l for l in nview.splitlines()
                      if "selected=True" in l and "beta.md" not in l and l.startswith("listitem")]
        t5["selected_line"] = sel_line
        t5["other_selected"] = others_sel
        t5["pass"] = sel_line is not None and not others_sel
        d = "\n".join(difflib.unified_diff(view.splitlines(), nview.splitlines(), lineterm=""))
        out["diff_bytes_selection"] = len(d.encode("utf-8"))
        if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
            screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                           "artifacts", "windows", "explorer-uia-shot.png"))
    else:
        t5["guard_blocked"] = True
out["t5"] = t5

# idle
v1, _ = distill(win)
time.sleep(1.0)
v2, _ = distill(win)
idiff = "\n".join(difflib.unified_diff(v1.splitlines(), v2.splitlines(), lineterm=""))
out["idle_diff_bytes"] = len(idiff.encode("utf-8"))
if out["idle_diff_bytes"]:
    save_artifact("explorer-uia-idle-diff.txt", idiff)

win.GetPattern(auto.PatternId.WindowPattern).Close()
time.sleep(1.0)
shutil.rmtree(folder, ignore_errors=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
