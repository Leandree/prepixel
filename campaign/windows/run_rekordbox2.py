# -*- coding: utf-8 -*-
"""rekordbox round 2: dismiss the Upmgr updater gate, reach the MAIN window."""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-rekordbox-uia", "round": 2}
RB = r"C:\Program Files\rekordbox\rekordbox 7.0.9\rekordbox.exe"
proc = subprocess.Popen([RB], cwd=os.path.dirname(RB))

main = None
deadline = time.time() + 240
while time.time() < deadline:
    time.sleep(3)
    for w in auto.GetRootControl().GetChildren():
        try:
            n = (w.Name or "")
        except Exception:
            continue  # transient window died mid-enumeration (stale-handle race)
        if "Upmgr" in n:
            # dismiss the updater gate (read-only choice: just close it)
            try:
                b = w.ButtonControl(searchDepth=6, Name="Fermer")
                if b.Exists(1):
                    b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                    out["upmgr_dismissed"] = True
            except Exception:
                pass
        elif "rekordbox" in n.lower():
            main = w
    if main is not None:
        break
if main is None:
    print(json.dumps({**out, "error": "main window never appeared"})); sys.exit(1)
time.sleep(15)  # library/audio engine settle

# re-resolve (TOCTOU lesson)
main = auto.WindowControl(searchDepth=1, RegexName=".*rekordbox.*")
if not main.Exists(5):
    print(json.dumps({**out, "error": "main window vanished"})); sys.exit(1)
wrect = rect_of(main)
out["window_rect"] = wrect
out["window_title"] = main.Name
out["window_class"] = main.ClassName

sig = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process rekordbox -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -match 'Qt|libcef|Chrome|JUCE|juce'} | Select-Object -First 8 -ExpandProperty ModuleName | Sort-Object -Unique"],
    capture_output=True, text=True).stdout.strip().splitlines()
out["framework_modules"] = sig

view, stats, attempts = probe_with_latch(lambda: main, settle=2.0, retries=4)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"],
                     "types": stats.get("types", {})}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1))
save_artifact("rekordbox-uia-view.txt", view)

nodes = []
for c, d in walk(main, max_depth=30, max_nodes=15000):
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
named = [n for n in nodes if n["n"]]
out["named_nodes"] = len(named)
out["named_sample"] = [f'{n["t"]}:{n["n"][:40]}' for n in named[:25]]
save_artifact("rekordbox-uia-rawnodes.json", json.dumps(nodes, ensure_ascii=False, indent=1))

img = print_window(main.NativeWindowHandle,
                   os.path.join(os.path.dirname(__file__), "..", "results",
                                "artifacts", "windows", "rekordbox-uia-shot.png"))
out["printwindow_ok"] = img is not None

ctypes.windll.user32.PostMessageW(main.NativeWindowHandle, 0x0010, 0, 0)
time.sleep(5)
for w2 in auto.GetRootControl().GetChildren():
    if "rekordbox" in (w2.Name or "").lower():
        for name in ("OK", "Oui", "Yes"):
            b = w2.ButtonControl(searchDepth=8, Name=name)
            if b.Exists(1):
                try:
                    b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                    out["quit_dialog_answered"] = name
                except Exception:
                    pass
                break
        break
time.sleep(5)
out["closed"] = not auto.WindowControl(searchDepth=1, RegexName=".*rekordbox.*").Exists(2)
if not out["closed"]:
    proc.terminate()
    out["terminated_fallback"] = True
print(json.dumps(out, ensure_ascii=False, indent=1))
