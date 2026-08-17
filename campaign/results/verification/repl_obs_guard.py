# -*- coding: utf-8 -*-
"""Independent replication of cell windows-obs-qt-uia (silent->explicit mitigation).

Reopens OBS, walks its UIA tree, finds structure-empty big regions (the preview
canvas is the target), PrintWindow-crops each and runs BOTH guard votes:
  Guard A  content_energy (modal-color ink ratio)
  vote 2   edge_fraction (adjacent-pixel deltas)
A region is SILENT->declare-opaque if EITHER vote crosses 0.01, and is then
re-emitted as an explicit [pixels] line. Crops written to the verification
folder only. OBS is opened READ-ONLY and closed at the end.
"""
import ctypes, json, os, subprocess, sys, time
CW = r"C:\Users\Léandre\dev\prepixel\campaign\windows"
sys.path.insert(0, CW)
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, walk)
from guard import (content_energy, edge_fraction, self_consistency, spot_check,
                   structural_coverage, empty_big_regions)

VER_ART = r"C:\Users\Léandre\dev\prepixel\campaign\results\verification\artifacts"
os.makedirs(VER_ART, exist_ok=True)


def raw_walk(win):
    nodes = []
    for c, d in walk(win, max_depth=30, max_nodes=20000):
        if c is None:
            break
        try:
            r = c.BoundingRectangle
            nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:60],
                          "cls": (c.ClassName or "")[:40],
                          "r": [r.left, r.top, r.right - r.left, r.bottom - r.top],
                          "d": d})
        except Exception:
            continue
    return nodes


out = {"cell": "windows-obs-qt-uia", "replication": True}
OBS_DIR = r"C:\Program Files\obs-studio\bin\64bit"
proc = subprocess.Popen([os.path.join(OBS_DIR, "obs64.exe"), "--disable-updater"], cwd=OBS_DIR)
time.sleep(12)
win = auto.WindowControl(searchDepth=1, RegexName="OBS .*")
if not win.Exists(15):
    print(json.dumps({**out, "error": "OBS window not found"}, ensure_ascii=False, indent=1))
    sys.exit(1)

out["window_title"] = win.Name
# a-priori signature: Qt class name on the top window
try:
    out["window_class"] = win.ClassName
except Exception:
    out["window_class"] = None

wrect = rect_of(win)
out["window_rect"] = list(wrect)
view, stats = distill(win)
nodes = raw_walk(win)
out["nodes_walked"] = len(nodes)

img = print_window(win.NativeWindowHandle)
if img is None:
    print(json.dumps({**out, "error": "PrintWindow failed"}, ensure_ascii=False, indent=1))
    sys.exit(1)
img.convert("RGB").save(os.path.join(VER_ART, "obs-printwindow-REPL.png"))

cov = structural_coverage(nodes, wrect)
out["structural_coverage_pct"] = round(cov * 100, 1)
suspects = empty_big_regions(nodes)
checked = spot_check(img, wrect, suspects)

# persist crops + build the report of every checked region
regions = []
for i, c in enumerate(checked):
    rec = {k: c[k] for k in ("label", "rect", "node_type", "energy",
                             "edge_fraction", "votes", "verdict", "line") if k in c}
    if c.get("verdict") == "SILENT->declare-opaque" and "crop" in c:
        c["crop"].convert("RGB").save(os.path.join(VER_ART, f"obs-guard-region{i}-REPL.png"))
        rec["crop_artifact"] = f"obs-guard-region{i}-REPL.png"
    regions.append(rec)
out["suspects_checked"] = len([c for c in checked if "energy" in c])
out["guard_a_regions"] = regions
out["guard_b_flags"] = self_consistency(view)

# identify the biggest silent region (the preview canvas)
silent = [r for r in regions if r.get("verdict") == "SILENT->declare-opaque"]
if silent:
    biggest = max(silent, key=lambda r: r["rect"][2] * r["rect"][3])
    out["preview_region"] = biggest

out["full_screenshot_tokens"] = image_tokens(wrect[2], wrect[3])
out["explicit_lines"] = [c["line"] for c in checked if c.get("line")] + \
                        [f["line"] for f in out["guard_b_flags"]]

# close OBS
try:
    win.GetPattern(auto.PatternId.WindowPattern).Close()
    time.sleep(2)
    out["obs_closed"] = True
except Exception as e:
    out["obs_close_error"] = str(e)[:120]

with open(os.path.join(VER_ART, "obs-guard-report-REPL.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
