# -*- coding: utf-8 -*-
"""Cell: windows-chrome-uia. The DUAL channel on the same app: Chromium's UIA
tree. The hunt: does Windows Chromium have the macOS-style AT-latch (stub tree
until an assistive client is detected), and is the canvas page honest via UIA?

Isolated Chrome instance, temp profile, NO --force-renderer-accessibility —
the point is whether the latch flips on its own when a UIA client walks in.
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(os.environ["TEMP"], "pipeline-tap-chrome-uia-profile")
url = "file:///" + os.path.join(ROOT, "pages", "testapp.html").replace("\\", "/")
out = {"cell": "windows-chrome-uia"}

proc = subprocess.Popen([CHROME, f"--user-data-dir={PROFILE}", "--no-first-run",
                         "--no-default-browser-check", "--window-size=1300,900",
                         "--window-position=40,40", url])
time.sleep(5.0)

win = auto.WindowControl(searchDepth=1, RegexName=".*Acme Console.*")
if not win.Exists(10):
    print(json.dumps({"error": "chrome window not found"})); sys.exit(1)

wrect = rect_of(win)
out["window_rect"] = wrect

# --- the latch experiment: repeated walks, watch the node count --------------
walks = []
t_start = time.perf_counter()
prev_nodes = -1
view = ""
for i in range(8):
    t0 = time.perf_counter()
    view, stats = distill(win)
    dt = (time.perf_counter() - t0) * 1000
    content = ("Dupont SARL" in view)
    walks.append({"walk": i + 1, "t_since_start_s": round(time.perf_counter() - t_start, 1),
                  "nodes": stats["nodes"], "ms": round(dt, 1), "page_content_visible": content})
    if content and stats["nodes"] == prev_nodes:
        break
    prev_nodes = stats["nodes"]
    time.sleep(1.0)
out["latch_walks"] = walks
out["latched"] = any(w["page_content_visible"] for w in walks)
save_artifact("chrome-uia-view-testapp.txt", view)
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])

# --- T1/T2 on the latched view ----------------------------------------------
out["t1"] = {"pass": all(s in view for s in ("Dupont SARL", "3 open orders"))}
inter = [l for l in view.splitlines() if l.split(" ")[0] in
         ("button", "hyperlink", "edit", "combobox")]
out["t2"] = {"interactive_lines": len(inter)}

# --- T3: type into the field via UIA focus + keys ----------------------------
t3 = {"pass": False}
edit = win.EditControl(searchDepth=25, Name="Customer name")
if edit.Exists(3):
    try:
        edit.SetFocus(); time.sleep(0.3)
        auto.SendKeys("UIA-DUAL-42q", interval=0.02); time.sleep(0.5)
        v2, _ = distill(win)
        line = next((l for l in v2.splitlines() if "UIA-DUAL-42q" in l), None)
        t3["value_line"] = line
        t3["pass"] = line is not None
        d = "\n".join(difflib.unified_diff(view.splitlines(), v2.splitlines(), lineterm=""))
        t3["diff_bytes"] = len(d.encode("utf-8"))
    except Exception as e:
        t3["error"] = str(e)[:200]
out["t3"] = t3

# --- T6: the all-canvas page through UIA -------------------------------------
nav = win.EditControl(searchDepth=15, RegexName=".*[Aa]dresse.*")
canvas_url = "file:///" + os.path.join(ROOT, "pages", "allcanvas.html").replace("\\", "/")
t6 = {}
if nav.Exists(3):
    try:
        nav.SetFocus(); time.sleep(0.2)
        auto.SendKeys("{Ctrl}a"); auto.SendKeys(canvas_url, interval=0.005)
        auto.SendKeys("{Enter}"); time.sleep(2.5)
        cview, cstats = distill(win)
        # page content area = below chrome (~y+140); what does UIA declare there?
        doc_lines = [l for l in cview.splitlines()
                     if l.startswith(("document", "pane", "[pixels]", "group", "text"))]
        t6["nodes"] = cstats["nodes"]
        t6["view"] = "\n".join(doc_lines[-15:])
        t6["fabricated_text_in_canvas"] = any(
            l.startswith("text") and int(l.split(" ")[1].split(",")[1]) > wrect[1] + 140
            for l in cview.splitlines())
        save_artifact("chrome-uia-view-allcanvas.txt", cview)
    except Exception as e:
        t6["error"] = str(e)[:200]
out["t6"] = t6

if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "chrome-uia-shot.png"))
proc.terminate()
print(json.dumps(out, ensure_ascii=False, indent=1))
