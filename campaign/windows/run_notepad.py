# -*- coding: utf-8 -*-
"""Cell: windows-notepad-uia. Win11 Notepad (RichEditD2D custom text control).

T1 read known text / T2 enumerate / T3 live value / T5 blind click (File menu)
+ stale-handle divergence probe (read from a dead element: error or silent?).
Throwaway file only; allowlisted click targets: the Fichier/File menu button.
"""
import json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

SENTINEL = "PIPELINE-TAP-SENTINEL The quick brown fox 12345 café naïve élève 日本語 🚀 END"
LIVE = "UIA-LIVE-9f3k7"
out = {"cell": "windows-notepad-uia"}

tmp = os.path.join(os.environ["TEMP"], "pipeline-tap-probe.txt")
with open(tmp, "w", encoding="utf-8") as f:
    f.write(SENTINEL + "\n")

proc = subprocess.Popen(["notepad.exe", tmp])
time.sleep(2.5)

win = auto.WindowControl(searchDepth=1, RegexName=".*pipeline-tap-probe.*")
if not win.Exists(5):
    print(json.dumps({"error": "notepad window not found"})); sys.exit(1)
win.SetActive()
time.sleep(0.5)
wrect = rect_of(win)
out["window_rect"] = wrect

# --- full distilled view + latch behaviour -----------------------------------
view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_stats"] = stats
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
save_artifact("notepad-uia-view.txt", view)

t0 = time.perf_counter()
view2, stats2 = distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

# screenshot of the window for ground truth + token comparison
img = screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                     "artifacts", "windows", "notepad-uia-shot.png"))
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
out["screenshot_tokens_legacy"] = image_tokens(wrect[2], wrect[3], "legacy")

# --- T1: read the known text through the channel -----------------------------
doc = win.DocumentControl(searchDepth=8)
t1 = {"pass": False}
if doc.Exists(3):
    got = None
    # try TextPattern first (the honest render-adjacent read), then ValuePattern
    try:
        tp = doc.GetPattern(auto.PatternId.TextPattern)
        got = tp.DocumentRange.GetText(-1)
        t1["via"] = "TextPattern"
    except Exception as e:
        t1["textpattern_error"] = str(e)
    if got is None:
        try:
            got = doc.GetPattern(auto.PatternId.ValuePattern).Value
            t1["via"] = "ValuePattern"
        except Exception as e:
            t1["valuepattern_error"] = str(e)
    if got is not None:
        got_clean = got.replace("\r", "").strip()
        t1["exact"] = got_clean == SENTINEL
        t1["got"] = got_clean
        t1["pass"] = SENTINEL in got_clean or t1["exact"]
out["t1"] = t1

# --- T2: enumerate interactive elements --------------------------------------
inter = [l for l in view.splitlines() if l.split(" ")[0] in
         ("button", "menuitem", "tabitem", "edit", "document", "checkbox",
          "combobox", "hyperlink", "splitbutton")]
out["t2"] = {"interactive_lines": len(inter), "sample": inter[:25]}

# --- T3: live value — type a unique string, re-read --------------------------
doc.SetFocus()
time.sleep(0.3)
auto.SendKeys("{Ctrl}{End}")
auto.SendKeys(LIVE, interval=0.02)
time.sleep(0.5)
t3 = {"pass": False}
try:
    tp = doc.GetPattern(auto.PatternId.TextPattern)
    got3 = tp.DocumentRange.GetText(-1)
    t3["pass"] = LIVE in got3
    t3["tail"] = got3[-80:]
except Exception as e:
    t3["error"] = str(e)
out["t3"] = t3

# diff cost of that interaction (re-distill, unified diff size)
view3, _ = distill(win)
diff = "\n".join(difflib.unified_diff(view.splitlines(), view3.splitlines(), lineterm=""))
out["diff_bytes_after_typing"] = len(diff.encode("utf-8"))
save_artifact("notepad-uia-diff-after-typing.txt", diff)

# idle: re-distill with nothing changed
view4, _ = distill(win)
idiff = "\n".join(difflib.unified_diff(view3.splitlines(), view4.splitlines(), lineterm=""))
out["idle_diff_bytes"] = len(idiff.encode("utf-8"))

# --- T5: blind click on the Fichier/File menu button, coords from channel ----
t5 = {"pass": False, "allowlist": ["Fichier", "File"]}
target = None
for line in view3.splitlines():
    if '"Fichier"' in line or '"File"' in line:
        target = line
        break
if target:
    # parse `role x,y,w,h "name"` — coords come from the VIEW LINE, not a fresh query
    coords = target.split(" ")[1].split(",")
    x, y, w, h = map(int, coords)
    cx, cy = x + w // 2, y + h // 2
    t5["target_line"] = target
    t5["clicked_at"] = [cx, cy]
    blind_click(cx, cy)
    time.sleep(1.0)
    # verify IN CHANNEL: a menu popup should now exist with items like Enregistrer/Save
    menu_view = ""
    try:
        for w2 in auto.GetRootControl().GetChildren():
            if w2.ControlTypeName in ("MenuControl", "WindowControl", "PaneControl"):
                nm = (w2.Name or "")
                cls = ""
                try: cls = w2.ClassName
                except Exception: pass
                if "Popup" in cls or w2.ControlTypeName == "MenuControl":
                    mv, _ = distill(w2)
                    menu_view += mv + "\n"
    except Exception as e:
        t5["menu_walk_error"] = str(e)
    # Win11 notepad menu may live inside the app window as an expanded flyout
    mv2, _ = distill(win)
    menu_view += mv2
    t5["menu_seen"] = any(k in menu_view for k in ("Enregistrer", "Save", "Nouvel onglet", "New tab"))
    t5["pass"] = t5["menu_seen"]
    save_artifact("notepad-uia-menu-view.txt", menu_view)
    img2 = screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                          "artifacts", "windows", "notepad-uia-menu-shot.png"))
    auto.SendKeys("{Esc}")
out["t5"] = t5

# --- stale-handle probe: hold the doc element, close the window, read again --
stale = {}
time.sleep(0.3)
# close without saving: Ctrl+W closes tab; use window close + "don't save"
win.SetActive(); time.sleep(0.2)
auto.SendKeys("{Ctrl}w")
time.sleep(1.2)
# if a save prompt appeared, decline it (throwaway file — allowlisted)
try:
    for wht in auto.GetRootControl().GetChildren():
        if wht.ControlTypeName == "WindowControl" and ("Bloc-notes" in (wht.Name or "") or "Notepad" in (wht.Name or "")):
            btn = wht.ButtonControl(RegexName="Ne pas enregistrer|Don't save|Ne pas .*")
            if btn.Exists(2):
                btn.Click(simulateMove=False)
                stale["decline_save"] = True
            break
except Exception as e:
    stale["prompt_error"] = str(e)
time.sleep(1.0)
try:
    v = doc.GetPattern(auto.PatternId.ValuePattern).Value
    stale["read_after_close"] = repr(v)[:120]
    stale["behaviour"] = "SILENT-EMPTY" if v == "" else ("STALE-CONTENT" if SENTINEL in (v or "") else "other")
except Exception as e:
    stale["behaviour"] = "ERROR (explicit)"
    stale["error"] = str(e)[:200]
out["stale_probe"] = stale

try:
    proc.terminate()
except Exception:
    pass

print(json.dumps(out, ensure_ascii=False, indent=1))
