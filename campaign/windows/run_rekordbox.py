# -*- coding: utf-8 -*-
"""Cell: windows-rekordbox-uia. rekordbox 7 (Pioneer DJ) — second custom-drawn
confirmation after FL Studio. STRICTLY READ-ONLY: no clicks, no keys.
Latch-aware walks, raw node shape, PrintWindow ground truth.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-rekordbox-uia"}
RB = r"C:\Program Files\rekordbox\rekordbox 7.0.9\rekordbox.exe"
if not os.path.exists(RB):
    import glob as g
    hits = g.glob(r"C:\Program Files\rekordbox\**\rekordbox.exe", recursive=True)
    if not hits:
        print(json.dumps({"error": "rekordbox.exe not found"})); sys.exit(1)
    RB = hits[0]
out["exe"] = RB
proc = subprocess.Popen([RB], cwd=os.path.dirname(RB))

win = None
for i in range(40):
    time.sleep(3)
    w = auto.WindowControl(searchDepth=1, RegexName=".*rekordbox.*")
    if w.Exists(1):
        win = w; break
if win is None:
    print(json.dumps({"error": "rekordbox window not found after 120s"})); sys.exit(1)
time.sleep(12)  # library load / splash settle

wrect = rect_of(win)
out["window_rect"] = wrect
out["window_title"] = win.Name
out["window_class"] = win.ClassName

sig = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process rekordbox).Modules | Where-Object {$_.ModuleName -match 'Qt|Chrome|libcef|XAML'} | Select-Object -First 6 -ExpandProperty ModuleName | Sort-Object -Unique"],
    capture_output=True, text=True).stdout.strip().splitlines()
out["framework_modules"] = sig

view, stats, attempts = probe_with_latch(lambda: win, settle=2.0, retries=4)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"],
                     "types": stats.get("types", {})}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1))
save_artifact("rekordbox-uia-view.txt", view)

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
by_type = {}
for n in nodes: by_type[n["t"]] = by_type.get(n["t"], 0) + 1
out["raw_types"] = by_type
out["raw_nodes_sample"] = nodes[:20]
save_artifact("rekordbox-uia-rawnodes.json", json.dumps(nodes, ensure_ascii=False, indent=1))

img = print_window(win.NativeWindowHandle,
                   os.path.join(os.path.dirname(__file__), "..", "results",
                                "artifacts", "windows", "rekordbox-uia-shot.png"))
out["printwindow_ok"] = img is not None

# read-only close: WM_CLOSE; answer any quit-confirm with the CONFIRM-quit
# button via InvokePattern (no coordinates)
ctypes.windll.user32.PostMessageW(win.NativeWindowHandle, 0x0010, 0, 0)
time.sleep(4)
for w2 in auto.GetRootControl().GetChildren():
    if "rekordbox" in (w2.Name or "").lower():
        for name in ("OK", "Oui", "Yes", "Quitter", "Fermer"):
            b = w2.ButtonControl(searchDepth=8, Name=name)
            if b.Exists(1):
                try:
                    b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                    out["quit_dialog_answered"] = name
                except Exception:
                    pass
                break
        break
time.sleep(4)
out["closed"] = not auto.WindowControl(searchDepth=1, RegexName=".*rekordbox.*").Exists(2)
if not out["closed"]:
    proc.terminate()
    out["terminated_fallback"] = True
print(json.dumps(out, ensure_ascii=False, indent=1))
