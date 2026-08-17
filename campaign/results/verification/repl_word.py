# -*- coding: utf-8 -*-
"""Independent replication of cell windows-word-object-model (the 80x star case).

Same sentinel + same COM read-back + same token/image formulas as
campaign/windows/run_word.py (via the shared uia_probe helpers). Throwaway
document, closed WITHOUT saving. Artifacts go to the verification folder only;
no origin cell or origin artifact is touched.
"""
import json, os, sys, time
CW = r"C:\Users\Léandre\dev\prepixel\campaign\windows"
sys.path.insert(0, CW)
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens)

VER_ART = r"C:\Users\Léandre\dev\prepixel\campaign\results\verification\artifacts"
os.makedirs(VER_ART, exist_ok=True)
import win32com.client

# same sentinel string as the origin cell's harness
SENT = "WORD-TAP-SENTINEL The quick brown fox 12345 café naïve élève 日本語 END"
out = {"cell": "windows-word-object-model", "replication": True}

t0 = time.perf_counter()
word = win32com.client.Dispatch("Word.Application")
out["com_dispatch_ms"] = round((time.perf_counter() - t0) * 1000, 1)
out["word_version"] = word.Version
word.Visible = True
doc = word.Documents.Add()
time.sleep(2)

# --- T1: write through the object model, read it back ------------------------
t0 = time.perf_counter()
doc.Range().InsertAfter(SENT)
w_ms = round((time.perf_counter() - t0) * 1000, 1)
t0 = time.perf_counter()
got = doc.Range().Text
r_ms = round((time.perf_counter() - t0) * 1000, 1)
out["t1"] = {"write_ms": w_ms, "read_ms": r_ms,
             "exact": got.strip("\r\x07 ") == SENT,
             "got_len_chars": len(got),
             "got_tail": got[-40:]}
out["doc_view_tokens"] = text_tokens(got)
out["doc_view_bytes"] = len(got.encode("utf-8"))

# --- cross-channel: is the COM write visible via UIA TextPattern? ------------
win = auto.WindowControl(searchDepth=1, RegexName=".*Word.*|.*Document.*")
xchan = {}
doc.Range().InsertAfter(" COM-WRITE-7m2p")
time.sleep(0.8)
if win.Exists(3):
    v, _ = distill(win)
    xchan["com_write_seen_via_uia"] = "COM-WRITE-7m2p" in v
    xchan["sentinel_seen_via_uia"] = "WORD-TAP-SENTINEL" in v
    xchan["uia_view_tokens"] = text_tokens(v)
    with open(os.path.join(VER_ART, "word-uia-view-REPL.txt"), "w", encoding="utf-8") as f:
        f.write(v)
out["cross_channel"] = xchan

# --- measurement vs pixels: the star ratio -----------------------------------
if win.Exists(3):
    wrect = rect_of(win)
    out["window_rect"] = list(wrect)
    out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])
    print_window(win.NativeWindowHandle,
                 os.path.join(VER_ART, "word-com-shot-REPL.png"))

# token count of the sentinel-only doc range (the T1 read view) is what pairs
# with the screenshot for the headline ratio
out["star_ratio_screenshot_over_doc"] = round(
    out["screenshot_tokens_window"] / out["doc_view_tokens"], 1)

full = doc.Range().Text
out["final_doc_tokens"] = text_tokens(full)
with open(os.path.join(VER_ART, "word-com-doc-text-REPL.txt"), "w", encoding="utf-8") as f:
    f.write(full)

# idle: two reads, no change
a = doc.Range().Text; time.sleep(1.0); b = doc.Range().Text
out["idle_identical"] = a == b

# --- cleanup: close WITHOUT saving ------------------------------------------
doc.Close(False)
word.Quit()
out["closed_without_saving"] = True
print(json.dumps(out, ensure_ascii=False, indent=1))
