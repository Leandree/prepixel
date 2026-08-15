# -*- coding: utf-8 -*-
"""Cell: windows-libreoffice-object-model. LibreOffice Writer via UNO on
Windows — completes the UNO family (Linux twin) after the UAC unblock.
Fresh-port retry encoded (Linux lesson: wedged UNO sockets)."""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact)

LO = r"C:\Program Files\LibreOffice\program"
out = {"cell": "windows-libreoffice-object-model"}

inner = None
for port in (2002, 2003):
    proc = subprocess.Popen(
        [os.path.join(LO, "soffice.exe"),
         f"--accept=socket,host=localhost,port={port};urp;",
         "--norestore", "--nologo", "--nodefault"], cwd=LO)
    time.sleep(12)
    r = subprocess.run([os.path.join(LO, "python.exe"),
                        os.path.join(os.path.dirname(__file__), "uno_inner.py"),
                        str(port)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    if r.returncode == 0 and r.stdout.strip().startswith("{"):
        inner = json.loads(r.stdout.strip().splitlines()[-1])
        out["port"] = port
        break
    out[f"port_{port}_error"] = (r.stderr or r.stdout)[-300:]
    proc.terminate(); time.sleep(3)

if inner is None:
    print(json.dumps(out, ensure_ascii=False)); sys.exit(1)
out["uno"] = inner

# UIA dual sample + pixel ground truth of the Writer window (if visible)
win = auto.WindowControl(searchDepth=1, RegexName=".*LibreOffice.*|.*Writer.*")
if win.Exists(5):
    wrect = rect_of(win)
    out["window_rect"] = wrect
    out["screenshot_tokens_window"] = image_tokens(max(wrect[2], 1), max(wrect[3], 1))
    v, st = distill(win)
    out["uia_nodes"] = st["nodes"]
    out["uia_sentinel_seen"] = "UNO-TAP-SENTINEL" in v
    save_artifact("libreoffice-uia-view.txt", v)
    print_window(win.NativeWindowHandle,
                 os.path.join(os.path.dirname(__file__), "..", "results",
                              "artifacts", "windows", "libreoffice-uno-shot.png"))

# terminate the headless-ish soffice we launched
subprocess.run([os.path.join(LO, "soffice.exe"), "--unaccept=all"], timeout=20)
time.sleep(2)
subprocess.run(["taskkill", "/IM", "soffice.bin", "/F"], capture_output=True)
subprocess.run(["taskkill", "/IM", "soffice.exe", "/F"], capture_output=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
