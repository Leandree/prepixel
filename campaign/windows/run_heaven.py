# -*- coding: utf-8 -*-
"""Cell: windows-heaven-pixels-baseline. Unigine Heaven 4.0 GPU benchmark —
the Tier G perimeter-law control: a real-time 3D scene. Expectation: UIA sees
a bare window and SAYS NOTHING about content (honest structural zero).
Windowed, short run, terminated after capture.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-heaven-pixels-baseline"}
HDIR = r"C:\Program Files (x86)\Unigine\Heaven Benchmark 4.0"
BIN = os.path.join(HDIR, "bin")
args = [os.path.join(BIN, "Heaven.exe"),
        "-project_name", "Heaven", "-data_path", "../",
        "-engine_config", "../data/heaven_4.0.cfg",
        "-system_script", "heaven/unigine.cpp",
        "-sound_app", "null", "-video_app", "direct3d11",
        "-video_multisample", "0", "-video_fullscreen", "0",
        "-video_mode", "-1", "-video_width", "1280", "-video_height", "720",
        "-extern_define", "RELEASE"]
proc = subprocess.Popen(args, cwd=BIN)
win = None
for i in range(20):
    time.sleep(2)
    w = auto.WindowControl(searchDepth=1, RegexName=".*Heaven.*|.*Unigine.*")
    if w.Exists(1):
        win = w; break
if win is None:
    print(json.dumps({"error": "heaven window not found", "returncode": proc.poll()})); sys.exit(1)
time.sleep(10)  # let the scene load and render

wrect = rect_of(win)
out["window_rect"] = wrect
out["window_title"] = win.Name
out["window_class"] = win.ClassName

view, stats, attempts = probe_with_latch(lambda: win, settle=1.5, retries=3)
out["latch_attempts"] = attempts
out["view"] = view
out["view_stats"] = {"nodes": stats["nodes"], "types": stats.get("types", {})}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1))
save_artifact("heaven-uia-view.txt", view)

nodes = []
for c, d in walk(win, max_depth=20, max_nodes=2000):
    if c is None: break
    try:
        nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:40],
                      "cls": (c.ClassName or "")[:40], "d": d})
    except Exception:
        continue
out["raw_nodes"] = nodes

img = print_window(win.NativeWindowHandle,
                   os.path.join(os.path.dirname(__file__), "..", "results",
                                "artifacts", "windows", "heaven-uia-shot.png"))
out["printwindow_ok"] = img is not None

proc.terminate()
time.sleep(2)
out["terminated"] = proc.poll() is not None
print(json.dumps(out, ensure_ascii=False, indent=1))
