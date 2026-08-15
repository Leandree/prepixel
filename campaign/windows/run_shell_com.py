# -*- coding: utf-8 -*-
"""Cell: windows-explorer-object-model. Shell.Application COM — the Windows
shell's DOCUMENT MODEL (the object-model twin of the UIA Explorer cell,
mirroring macOS Pages-via-AppleScript pairing with AX).

Read the same throwaway folder through COM (no pixels, no coordinates),
WRITE selection state through COM, and cross-verify the on-screen effect
through the independent UIA channel.
"""
import ctypes, json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import auto, distill, rect_of, print_window, text_tokens, save_artifact
import comtypes.client

out = {"cell": "windows-explorer-object-model"}
folder = os.path.join(os.environ["TEMP"], "pipeline-tap-explorer")
os.makedirs(folder, exist_ok=True)
for name, data in (("alpha.txt", b"alpha"), ("beta.md", b"beta")):
    with open(os.path.join(folder, name), "wb") as f: f.write(data)

subprocess.Popen(["explorer.exe", folder])
time.sleep(3.0)

# --- COM channel -------------------------------------------------------------
t0 = time.perf_counter()
shell = comtypes.client.CreateObject("Shell.Application")
win_com = None
for w in shell.Windows():
    try:
        if "pipeline-tap-explorer" in (w.LocationURL or ""):
            win_com = w; break
    except Exception:
        continue
out["com_connect_ms"] = round((time.perf_counter() - t0) * 1000, 1)
if win_com is None:
    print(json.dumps({"error": "no shell window via COM", **out})); sys.exit(1)

t0 = time.perf_counter()
items = win_com.Document.Folder.Items()
listing = [{"name": items.Item(i).Name, "size": items.Item(i).Size,
            "type": items.Item(i).Type} for i in range(items.Count)]
out["t1_read_ms"] = round((time.perf_counter() - t0) * 1000, 1)
view_txt = json.dumps(listing, ensure_ascii=False)
out["t1"] = {"pass": {"alpha", "beta"} <= {i["name"] for i in listing} or
                     {"alpha.txt", "beta.md"} <= {i["name"] for i in listing},
             "listing": listing}
out["view_bytes"] = len(view_txt.encode("utf-8"))
out["view_tokens"] = text_tokens(view_txt)

# --- T3 live model: create a file on disk, re-read through COM ---------------
with open(os.path.join(folder, "gamma-live.txt"), "w") as f: f.write("live")
time.sleep(1.5)
t0 = time.perf_counter()
items2 = win_com.Document.Folder.Items()
names2 = [items2.Item(i).Name for i in range(items2.Count)]
out["t3"] = {"pass": any("gamma-live" in n for n in names2),
             "reread_ms": round((time.perf_counter() - t0) * 1000, 1),
             "names": names2}

# --- WRITE path: select beta.md via COM (no coordinates involved) ------------
t0 = time.perf_counter()
target = None
for i in range(items2.Count):
    if "beta" in items2.Item(i).Name:
        target = items2.Item(i); break
win_com.Document.SelectItem(target, 1 | 4 | 8)  # select + deselect others + focus
out["write_ms"] = round((time.perf_counter() - t0) * 1000, 1)
time.sleep(1.0)

# read back selection through COM
sel = win_com.Document.SelectedItems()
out["selection_via_com"] = [sel.Item(i).Name for i in range(sel.Count)]

# --- cross-channel verification via UIA (independent reader) -----------------
uia_win = auto.WindowControl(searchDepth=1, RegexName=".*pipeline-tap-explorer.*")
xver = {}
if uia_win.Exists(5):
    view, _ = distill(uia_win)
    sel_lines = [l for l in view.splitlines() if "selected=True" in l and l.startswith("listitem")]
    xver["uia_selected_lines"] = sel_lines
    xver["agrees"] = any("beta" in l for l in sel_lines) and len(sel_lines) == 1
    print_window(uia_win.NativeWindowHandle,
                 os.path.join(os.path.dirname(__file__), "..", "results",
                              "artifacts", "windows", "explorer-com-shot.png"))
    save_artifact("explorer-com-uia-view.txt", view)
out["cross_verification"] = xver

# cleanup
if uia_win.Exists(2):
    uia_win.GetPattern(auto.PatternId.WindowPattern).Close()
time.sleep(1.0)
shutil.rmtree(folder, ignore_errors=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
