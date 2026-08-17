# -*- coding: utf-8 -*-
"""A deliberately DPI-UNAWARE executor: the classic integration bug where the
router (aware, physical px) hands coordinates to a clicker whose coordinate
system is virtualized. Pure ctypes, NO DPI-awareness call, NO uiautomation
import (that package makes the process aware as a side effect).

usage: unaware_clicker.py move X Y      -> SetCursorPos only, prints own view
       unaware_clicker.py click X Y     -> SetCursorPos + left click
"""
import ctypes, json, sys, time

u = ctypes.windll.user32
mode, x, y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
u.SetCursorPos(x, y)
time.sleep(0.15)
if mode == "click":
    class MI(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class INP(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("mi", MI)]
        _anonymous_ = ("i",)
        _fields_ = [("type", ctypes.c_ulong), ("i", _I)]
    ins = (INP * 2)()
    ins[0].type = 0; ins[0].mi = MI(0, 0, 0, 0x0002, 0, None)
    ins[1].type = 0; ins[1].mi = MI(0, 0, 0, 0x0004, 0, None)
    u.SendInput(2, ctypes.byref(ins), ctypes.sizeof(INP))
pt = ctypes.wintypes.POINT() if hasattr(ctypes, 'wintypes') else None
from ctypes import wintypes
pt = wintypes.POINT()
u.GetCursorPos(ctypes.byref(pt))
hdc = u.GetDC(0)
lpx = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
print(json.dumps({"asked": [x, y], "own_getcursorpos": [pt.x, pt.y],
                  "own_logpixelsx": lpx}))
