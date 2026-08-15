# -*- coding: utf-8 -*-
"""Runs under LibreOffice's bundled python (which ships the uno module).
Connects to a soffice instance listening on the given port, opens a Writer doc,
writes the sentinel, reads it back, closes without saving. Prints JSON."""
import json, sys, time
import uno

PORT = sys.argv[1] if len(sys.argv) > 1 else "2002"
SENT = "UNO-TAP-SENTINEL The quick brown fox 12345 café naïve élève 日本語 END"
out = {}

t0 = time.perf_counter()
localContext = uno.getComponentContext()
resolver = localContext.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", localContext)
ctx = resolver.resolve(
    f"uno:socket,host=localhost,port={PORT};urp;StarOffice.ComponentContext")
smgr = ctx.ServiceManager
desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
out["connect_ms"] = round((time.perf_counter() - t0) * 1000, 1)

t0 = time.perf_counter()
doc = desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
out["newdoc_ms"] = round((time.perf_counter() - t0) * 1000, 1)
text = doc.getText()
cursor = text.createTextCursor()

t0 = time.perf_counter()
text.insertString(cursor, SENT, False)
out["write_ms"] = round((time.perf_counter() - t0) * 1000, 1)

t0 = time.perf_counter()
got = text.getString()
out["read_ms"] = round((time.perf_counter() - t0) * 1000, 1)
out["exact"] = got == SENT
out["got_tail"] = got[-30:]
out["view_bytes"] = len(got.encode("utf-8"))
out["view_tokens"] = -(-len(got) // 4)

# live model: second insert, immediate re-read
text.insertString(cursor, " LIVE-3v8t", False)
out["live"] = "LIVE-3v8t" in text.getString()

doc.close(False)
print(json.dumps(out, ensure_ascii=False))
