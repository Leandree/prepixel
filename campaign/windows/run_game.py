# -*- coding: utf-8 -*-
"""Cell: windows-<game>-pixels-baseline. A REAL AAA 3D game (not a benchmark).

Protocol (read-only, zero input into the game):
  launch via Steam -> wait for the game window -> latch-aware UIA walk
  (expect frame-only) -> coverage-guard with synthesized client suspect ->
  PrintWindow (fall back to screen crop if the swapchain refuses) -> close.
Anticheat policy: only titles WITHOUT kernel anticheat are probed.

usage: run_game.py <steam_appid> <window_regex> <cell_key>
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, screenshot,
                       text_tokens, image_tokens, save_artifact,
                       probe_with_latch, walk)
from guard import spot_check, empty_big_regions, structural_coverage, synthesize_client_suspect

APPID, WINRE, KEY = sys.argv[1], sys.argv[2], sys.argv[3]
ART = os.path.join(os.path.dirname(__file__), "..", "results", "artifacts", "windows")
out = {"cell": f"windows-{KEY}-pixels-baseline", "appid": APPID}

subprocess.Popen(["cmd", "/c", "start", "", f"steam://rungameid/{APPID}"])
win = None
deadline = time.time() + 360   # UE titles can compile shaders on launch
while time.time() < deadline:
    time.sleep(5)
    w = auto.WindowControl(searchDepth=1, RegexName=WINRE)
    if w.Exists(1):
        win = w
        break
if win is None:
    print(json.dumps({**out, "error": "game window not found in 6 min"})); sys.exit(1)
out["t_window_s"] = round(time.time() - (deadline - 360), 1)
time.sleep(25)   # menu/intro settle

win = auto.WindowControl(searchDepth=1, RegexName=WINRE)  # re-resolve
wrect = rect_of(win)
out["window_rect"] = wrect
out["window_title"] = win.Name
out["window_class"] = win.ClassName
hwnd = win.NativeWindowHandle

# UIA shape (latch-aware)
view, stats, attempts = probe_with_latch(lambda: win, settle=2.0, retries=3)
out["latch_attempts"] = attempts
out["uia_nodes"] = stats["nodes"]
out["uia_types"] = stats.get("types", {})
out["view_tokens"] = text_tokens(view)
save_artifact(f"{KEY}-uia-view.txt", view)

nodes = []
for c, d in walk(win, max_depth=20, max_nodes=3000):
    if c is None: break
    try:
        r = c.BoundingRectangle
        nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:60],
                      "cls": (c.ClassName or "")[:40],
                      "r": [r.left, r.top, r.right - r.left, r.bottom - r.top], "d": d})
    except Exception:
        continue

# per-window pixels: PrintWindow first, screen crop fallback (exclusive swapchains)
img = print_window(hwnd, os.path.join(ART, f"{KEY}-shot.png"))
out["printwindow_ok"] = img is not None
capture_mode = "printwindow"
if img is None or (img and img.convert("L").getextrema()[1] == 0):
    img = screenshot(wrect, os.path.join(ART, f"{KEY}-shot.png"))
    capture_mode = "screen-crop (PrintWindow refused/black — declared per macOS rule)"
out["capture_mode"] = capture_mode

cov = structural_coverage(nodes, wrect)
guard = {"coverage_pct": round(cov * 100, 1)}
suspects = empty_big_regions(nodes, min_area=100000)
synth = synthesize_client_suspect(wrect, cov)
if not suspects and synth:
    suspects = [synth]
    guard["synthesized"] = True
checked = spot_check(img, wrect, suspects)
for c in checked:
    c.pop("crop", None)
guard["suspects"] = checked
out["guard"] = guard
out["screenshot_tokens"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1))
out["screenshot_tokens_legacy"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1), "legacy")

# close read-only: WM_CLOSE, then read any confirm dialog through UIA
ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
time.sleep(6)
still = auto.WindowControl(searchDepth=1, RegexName=WINRE)
if still.Exists(2):
    dview, dstats = distill(still)
    out["close_dialog_view"] = dview[:500]
    out["close_dialog_nodes"] = dstats["nodes"]
    # if a confirm button is exposed, use it; else terminate the process
    for name in ("Oui", "Yes", "Quitter", "Quit", "Confirm", "OK"):
        b = still.ButtonControl(searchDepth=10, Name=name)
        if b.Exists(1):
            try:
                b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                out["closed_via"] = f"InvokePattern '{name}'"
            except Exception:
                pass
            break
    time.sleep(6)
if auto.WindowControl(searchDepth=1, RegexName=WINRE).Exists(2):
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process | Where-Object {$_.MainWindowTitle -match '" + WINRE + "'} | Stop-Process -Force"],
                   capture_output=True)
    out["closed_via"] = out.get("closed_via", "process terminate (menu screen, no save at risk)")
out["closed"] = not auto.WindowControl(searchDepth=1, RegexName=WINRE).Exists(3)
save_artifact(f"{KEY}-game-report.json", json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
