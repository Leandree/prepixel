# -*- coding: utf-8 -*-
"""Cell: windows-flstudio-uia. FL Studio 2025 (fully custom-drawn UI — the
brief's prime silent-divergence suspect). STRICTLY READ-ONLY: no clicks, no
keys. UIA walk vs PrintWindow ground truth.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-flstudio-uia"}
FL = r"C:\Program Files\Image-Line\FL Studio 2025\FL64.exe"
proc = subprocess.Popen([FL])
# FL boots slowly (audio engine + plugin db); poll for its window
win = None
for i in range(30):
    time.sleep(3)
    w = auto.WindowControl(searchDepth=1, RegexName=".*FL Studio.*")
    if w.Exists(1):
        win = w; break
if win is None:
    print(json.dumps({"error": "FL window not found after 90s"})); sys.exit(1)
time.sleep(8)  # let the UI settle fully

wrect = rect_of(win)
out["window_rect"] = wrect
out["window_title"] = win.Name

sig = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process FL64).Modules | Where-Object {$_.ModuleName -match 'Qt|XAML|UIAutomation|oleacc'} | Select-Object -ExpandProperty ModuleName | Sort-Object -Unique"],
    capture_output=True, text=True).stdout.strip().splitlines()
out["framework_modules"] = sig

# latch-aware repeated walks (never classify from the first read)
view, stats, attempts = probe_with_latch(lambda: win, settle=1.5, retries=4)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"],
                     "types": stats.get("types", {})}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])
save_artifact("flstudio-uia-view.txt", view)

# raw walk: EVERY node with name/class, to judge honesty precisely
nodes = []
for c, d in walk(win, max_depth=30, max_nodes=15000):
    if c is None: break
    try:
        r = c.BoundingRectangle
        nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:60],
                      "cls": (c.ClassName or "")[:40],
                      "r": [r.left, r.top, r.right - r.left, r.bottom - r.top], "d": d})
    except Exception:
        continue
out["raw_node_count"] = len(nodes)
out["raw_nodes_sample"] = nodes[:25]
save_artifact("flstudio-uia-rawnodes.json", json.dumps(nodes, ensure_ascii=False, indent=1))

img = print_window(win.NativeWindowHandle,
                   os.path.join(os.path.dirname(__file__), "..", "results",
                                "artifacts", "windows", "flstudio-uia-shot.png"))
out["printwindow_ok"] = img is not None

# close read-only: WM_CLOSE to the FL window; then handle any 'save?' dialog by
# choosing the DON'T-save option (we changed nothing, but be safe)
ctypes.windll.user32.PostMessageW(win.NativeWindowHandle, 0x0010, 0, 0)
time.sleep(4)
dlg = auto.WindowControl(searchDepth=1, RegexName=".*FL Studio.*")
if dlg.Exists(2):
    # maybe a confirm dialog replaced the main window; try Invoke on a no/don't-save button
    for name in ("Non", "No", "Don't save", "Ne pas enregistrer", "Discard"):
        b = dlg.ButtonControl(searchDepth=8, Name=name)
        if b.Exists(1):
            try:
                b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                out["close_dialog_answered"] = name
            except Exception:
                pass
            break
time.sleep(3)
still = auto.WindowControl(searchDepth=1, RegexName=".*FL Studio.*")
out["closed"] = not still.Exists(2)
print(json.dumps(out, ensure_ascii=False, indent=1))
