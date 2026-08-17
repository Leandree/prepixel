# -*- coding: utf-8 -*-
"""Minimal Java Access Bridge client (ctypes over WindowsAccessBridge-64.dll).
Proves the Java structured channel end-to-end: isJavaWindow detection, root
context, recursive walk with names/roles/values. Run in its own process.

usage: jab_client.py <path-to-WindowsAccessBridge-64.dll> <hwnd>
"""
import ctypes, json, sys, time
from ctypes import wintypes

DLL, HWND = sys.argv[1], int(sys.argv[2])
MAX, SHORT = 1024, 256
AC = ctypes.c_int64
jint = ctypes.c_int32


class ACInfo(ctypes.Structure):
    _fields_ = [("name", ctypes.c_wchar * MAX), ("description", ctypes.c_wchar * MAX),
                ("role", ctypes.c_wchar * SHORT), ("role_en_US", ctypes.c_wchar * SHORT),
                ("states", ctypes.c_wchar * SHORT), ("states_en_US", ctypes.c_wchar * SHORT),
                ("indexInParent", jint), ("childrenCount", jint),
                ("x", jint), ("y", jint), ("width", jint), ("height", jint),
                ("accessibleComponent", wintypes.BOOL), ("accessibleAction", wintypes.BOOL),
                ("accessibleSelection", wintypes.BOOL), ("accessibleText", wintypes.BOOL),
                ("accessibleInterfaces", wintypes.BOOL)]


b = ctypes.cdll.LoadLibrary(DLL)
b.Windows_run()
b.isJavaWindow.restype = wintypes.BOOL
b.isJavaWindow.argtypes = [wintypes.HWND]
# pump ALL messages so the bridge completes its window-message handshake,
# retrying the detection as the JVMs answer
u = ctypes.windll.user32
msg = wintypes.MSG()
out = {"isJavaWindow": False}
t0 = time.time()
while time.time() - t0 < 8.0:
    while u.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
        u.TranslateMessage(ctypes.byref(msg))
        u.DispatchMessageW(ctypes.byref(msg))
    if b.isJavaWindow(HWND):
        out["isJavaWindow"] = True
        out["detected_after_s"] = round(time.time() - t0, 1)
        break
    time.sleep(0.1)
if out["isJavaWindow"]:
    vm = ctypes.c_long()
    ac = AC()
    b.getAccessibleContextFromHWND.restype = wintypes.BOOL
    b.getAccessibleContextFromHWND.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(AC)]
    ok = b.getAccessibleContextFromHWND(HWND, ctypes.byref(vm), ctypes.byref(ac))
    out["gotRoot"] = bool(ok)
    if ok:
        b.getAccessibleContextInfo.restype = wintypes.BOOL
        b.getAccessibleContextInfo.argtypes = [ctypes.c_long, AC, ctypes.POINTER(ACInfo)]
        b.getAccessibleChildFromContext.restype = AC
        b.getAccessibleChildFromContext.argtypes = [ctypes.c_long, AC, jint]
        nodes = []

        def walk(c, depth):
            if depth > 8 or len(nodes) > 400:
                return
            info = ACInfo()
            if not b.getAccessibleContextInfo(vm, c, ctypes.byref(info)):
                return
            nodes.append({"role": info.role_en_US, "name": info.name[:80],
                          "r": [info.x, info.y, info.width, info.height],
                          "children": info.childrenCount, "d": depth})
            for i in range(min(info.childrenCount, 64)):
                ch = b.getAccessibleChildFromContext(vm, c, i)
                if ch:
                    walk(ch, depth + 1)

        t0 = time.perf_counter()
        walk(ac, 0)
        out["walk_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["node_count"] = len(nodes)
        out["nodes"] = nodes
print(json.dumps(out, ensure_ascii=False))
