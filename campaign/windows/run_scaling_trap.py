# -*- coding: utf-8 -*-
"""P1 — demonstrate the DPI coordinate trap LIVE at 125% scaling.

Target: the 'Horloges supplémentaires' tab of timedate.cpl — its SELECTED
state flips in-channel, giving pixel-free hit verification. The dialog is
positioned so the naive x1.25 miss lands harmlessly inside the same dialog.
Scaling restored in a finally block, verified.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import auto, distill, rect_of, screenshot, save_artifact
from ctypes import wintypes

u = ctypes.windll.user32
PY = sys.executable
CLICKER = os.path.join(os.path.dirname(__file__), "unaware_clicker.py")
out = {"cell": "windows-scaling-blind-click"}

def system_dpi_fresh():
    r = subprocess.run([PY, "-c",
        "import ctypes;ctypes.windll.shcore.SetProcessDpiAwareness(2);"
        "h=ctypes.windll.user32.GetDC(0);print(ctypes.windll.gdi32.GetDeviceCaps(h,88))"],
        capture_output=True, text=True)
    return int(r.stdout.strip())

def set_scale_override(delta):
    return bool(u.SystemParametersInfoW(0x009F, delta, None, 1))

def clicker(mode, x, y):
    r = subprocess.run([PY, CLICKER, mode, str(int(x)), str(int(y))],
                       capture_output=True, text=True)
    return json.loads(r.stdout.strip())

def real_cursor():
    pt = wintypes.POINT()
    u.GetCursorPos(ctypes.byref(pt))
    return [pt.x, pt.y]

def tab_state(win, name):
    v, _ = distill(win)
    for l in v.splitlines():
        if name in l and l.startswith("tabitem"):
            return l
    return None

out["dpi_before"] = system_dpi_fresh()
proc = None
try:
    ok = set_scale_override(1)
    time.sleep(3)
    out["dpi_at_test"] = system_dpi_fresh()
    out["scale_change_ok"] = ok and out["dpi_at_test"] != out["dpi_before"]
    if not out["scale_change_ok"]:
        raise RuntimeError("scale override had no effect")
    scale_true = out["dpi_at_test"] / 96.0
    out["scale_true"] = scale_true

    proc = subprocess.Popen(["control.exe", "timedate.cpl"])
    time.sleep(3)
    win = auto.WindowControl(searchDepth=1, RegexName="Date et heure|Date and Time")
    assert win.Exists(10), "dialog not found"
    hwnd = win.NativeWindowHandle
    u.SetWindowPos(hwnd, 0, 400, 300, 0, 0, 0x0001 | 0x0040)  # NOSIZE|SHOWWINDOW
    time.sleep(0.8)
    for attempt in range(5):
        u.keybd_event(0x12, 0, 0, 0)
        try: win.SetActive()
        except Exception: pass
        u.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.5)
        if u.GetForegroundWindow() == hwnd:
            break
    assert u.GetForegroundWindow() == hwnd, "no foreground"
    wrect = rect_of(win)
    out["dialog_rect_at_125"] = wrect

    TAB = "Horloges supplémentaires"
    line = tab_state(win, TAB)
    assert line and "selected=False" in line, f"unexpected initial tab state: {line}"
    x, y, w, h = map(int, line.split(" ")[1].split(","))
    px, py = x + w // 2, y + h // 2       # PHYSICAL target from UIA
    out["target_line"] = line
    out["target_physical"] = [px, py]
    pred = [round(px * scale_true), round(py * scale_true)]
    inside = (wrect[0] + 5 <= pred[0] <= wrect[0] + wrect[2] - 5 and
              wrect[1] + 40 <= pred[1] <= wrect[1] + wrect[3] - 40)
    out["naive_predicted_landing"] = pred
    assert inside, f"predicted landing {pred} outside safe dialog zone {wrect} — abort"

    # ---- NAIVE: physical coords through the DPI-unaware executor ------------
    naive = clicker("click", px, py)
    time.sleep(1.0)
    landed = real_cursor()
    after_naive = tab_state(win, TAB)
    out["naive"] = {"handed_physical": [px, py], "executor_saw": naive,
                    "landed_physical": landed,
                    "tab_after": after_naive,
                    "hit": bool(after_naive and "selected=True" in after_naive)}

    # ---- CALIBRATION probe ---------------------------------------------------
    probe_pt = [320, 320]
    mv = clicker("move", *probe_pt)
    landed_probe = real_cursor()
    scale_measured = ((landed_probe[0] / probe_pt[0]) + (landed_probe[1] / probe_pt[1])) / 2
    out["calibration"] = {"asked_logical": probe_pt, "landed_physical": landed_probe,
                          "scale_measured": round(scale_measured, 4),
                          "executor_logpixelsx": mv["own_logpixelsx"]}

    # ---- CALIBRATED click ----------------------------------------------------
    cx, cy = px / scale_measured, py / scale_measured
    calib = clicker("click", cx, cy)
    time.sleep(1.0)
    landed2 = real_cursor()
    after_calib = tab_state(win, TAB)
    out["calibrated"] = {"handed_logical": [round(cx, 1), round(cy, 1)],
                         "landed_physical": landed2,
                         "tab_after": after_calib,
                         "hit": bool(after_calib and "selected=True" in after_calib)}
    if u.GetForegroundWindow() == hwnd:
        screenshot(rect_of(win), os.path.join(os.path.dirname(__file__), "..", "results",
                                              "artifacts", "windows", "scaling-trap-shot.png"))
    win.GetPattern(auto.PatternId.WindowPattern).Close()
finally:
    set_scale_override(0)
    time.sleep(3)
    out["dpi_after_revert"] = system_dpi_fresh()
    out["reverted"] = out["dpi_after_revert"] == out["dpi_before"]

save_artifact("scaling-trap-log.json", json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
