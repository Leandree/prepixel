# -*- coding: utf-8 -*-
"""Cell: windows-word-object-model. Microsoft Word via COM — the brief's Tier C
'star case': the document itself, above any render tree.

Throwaway document only; closed without saving. Cross-channel: COM writes are
read back via COM AND via UIA (TextPattern on the Word window); keyboard input
is read back via COM.
"""
import ctypes, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact)
import win32com.client

SENT = "WORD-TAP-SENTINEL The quick brown fox 12345 café naïve élève 日本語 END"
out = {"cell": "windows-word-object-model"}

t0 = time.perf_counter()
word = win32com.client.Dispatch("Word.Application")
out["com_dispatch_ms"] = round((time.perf_counter() - t0) * 1000, 1)
out["word_version"] = word.Version
word.Visible = True
doc = word.Documents.Add()
time.sleep(2)

# --- T1: write through the object model, read back ---------------------------
t0 = time.perf_counter()
doc.Range().InsertAfter(SENT)
w_ms = round((time.perf_counter() - t0) * 1000, 1)
t0 = time.perf_counter()
got = doc.Range().Text
r_ms = round((time.perf_counter() - t0) * 1000, 1)
out["t1"] = {"write_ms": w_ms, "read_ms": r_ms,
             "exact": got.strip("\r\x07 ") == SENT,
             "got_tail": got[-40:]}
out["doc_view_tokens"] = text_tokens(got)
out["doc_view_bytes"] = len(got.encode("utf-8"))

# --- T3a: keyboard typing (the 'user' path) read through COM -----------------
win = auto.WindowControl(searchDepth=1, RegexName=".*Word.*|.*Document.*")
t3 = {}
if win.Exists(8):
    hwnd = win.NativeWindowHandle
    for attempt in range(5):
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        try: win.SetActive()
        except Exception: pass
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.4)
        if ctypes.windll.user32.GetForegroundWindow() == hwnd:
            break
    if ctypes.windll.user32.GetForegroundWindow() == hwnd:
        auto.SendKeys("{Ctrl}{End}")
        auto.SendKeys(" TYPED-9k4x", interval=0.02)
        time.sleep(0.8)
        t3["typed_seen_via_com"] = "TYPED-9k4x" in doc.Range().Text
    else:
        t3["skipped"] = "could not verify foreground; no blind typing without it"
out["t3"] = t3

# --- T3b: COM write read through UIA (cross-channel) -------------------------
doc.Range().InsertAfter(" COM-WRITE-7m2p")
time.sleep(0.8)
xchan = {}
if win.Exists(3):
    v, _ = distill(win)
    xchan["com_write_seen_via_uia"] = "COM-WRITE-7m2p" in v
    xchan["sentinel_seen_via_uia"] = "WORD-TAP-SENTINEL" in v
    xchan["uia_view_tokens"] = text_tokens(v)
    save_artifact("word-uia-view.txt", v)
out["cross_channel"] = xchan

# --- T6: pictorial through the object model ----------------------------------
png = os.path.join(os.environ["TEMP"], "ptap-word-img.png")
with open(png, "wb") as f:
    f.write(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000010000000100802000000909168"
        "360000001d4944415478da63fccfc0c0c0c4c0c0c0c0c0f89f819181818189818"
        "10100302e011b1c94f2fa0000000049454e44ae426082"))
t6 = {}
try:
    doc.Range().InsertAfter("\n")
    shp = doc.InlineShapes.AddPicture(png, False, True, doc.Paragraphs.Last.Range)
    time.sleep(0.5)
    t6["inline_shapes_count"] = doc.InlineShapes.Count
    s = doc.InlineShapes(1)
    t6["declared"] = {"type": int(s.Type), "w_pt": round(s.Width, 1), "h_pt": round(s.Height, 1)}
    t6["pass"] = doc.InlineShapes.Count == 1
except Exception as e:
    t6["error"] = str(e)[:200]
out["t6"] = t6

# --- measurements vs pixels --------------------------------------------------
if win.Exists(3):
    wrect = rect_of(win)
    out["window_rect"] = wrect
    out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])
    print_window(win.NativeWindowHandle,
                 os.path.join(os.path.dirname(__file__), "..", "results",
                              "artifacts", "windows", "word-com-shot.png"))

full = doc.Range().Text
out["final_doc_tokens"] = text_tokens(full)
save_artifact("word-com-doc-text.txt", full)

# idle: two reads, no change
a = doc.Range().Text; time.sleep(1.0); b = doc.Range().Text
out["idle_identical"] = a == b

# --- cleanup: close WITHOUT saving ------------------------------------------
doc.Close(False)
word.Quit()
os.remove(png)
out["closed_without_saving"] = True
print(json.dumps(out, ensure_ascii=False, indent=1))
