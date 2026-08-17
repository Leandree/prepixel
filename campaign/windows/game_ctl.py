# -*- coding: utf-8 -*-
"""Step-driver for the menu-vs-gameplay comparison: the vision-piloted loop a
router must run where structure is absent (guard said 0% coverage -> pixels).

subcommands:
  launch <appid> <title_substr>   start via steam://, wait for the Win32 window
  shot <name>                     PrintWindow -> artifacts/<name>.png (+ energy)
  key <VK...>                     force game foreground, send key presses
  probe <name>                    UIA node count + guard energy + shot
  framediff                       two PrintWindows 1 s apart -> changed-pixel %%
  close                           WM_CLOSE, report; kill fallback
State (hwnd) is re-resolved each call from the Win32 map by title substring.
"""
import ctypes, json, os, subprocess, sys, time
from ctypes import wintypes
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import auto, print_window, text_tokens, save_artifact
from guard import content_energy

u = ctypes.windll.user32
ART = os.path.join(os.path.dirname(__file__), "..", "results", "artifacts", "windows")
STATE = os.path.join(os.environ["TEMP"], "ptap-game-state.json")

VK = {"ENTER": 0x0D, "SPACE": 0x20, "ESC": 0x1B, "UP": 0x26, "DOWN": 0x28,
      "LEFT": 0x25, "RIGHT": 0x27, "W": 0x57, "E": 0x45, "F": 0x46, "X": 0x58}

def find_hwnd(substr):
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        buf = ctypes.create_unicode_buffer(128)
        u.GetWindowTextW(h, buf, 128)
        if substr.lower() in buf.value.lower() and u.IsWindowVisible(h):
            found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None

def state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}

def rect_of_hwnd(h):
    r = wintypes.RECT(); u.GetWindowRect(h, ctypes.byref(r))
    return [r.left, r.top, r.right - r.left, r.bottom - r.top]

def force_fg(h):
    for i in range(5):
        u.keybd_event(0x12, 0, 0, 0)
        u.SetForegroundWindow(h)
        u.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.4)
        if u.GetForegroundWindow() == h:
            return True
    return False

cmd = sys.argv[1]
if cmd == "launch":
    appid, sub = sys.argv[2], sys.argv[3]
    subprocess.Popen(["cmd", "/c", "start", "", f"steam://rungameid/{appid}"])
    h = None
    deadline = time.time() + 360
    while time.time() < deadline and h is None:
        time.sleep(5)
        h = find_hwnd(sub)
    json.dump({"sub": sub}, open(STATE, "w"))
    print(json.dumps({"hwnd": h, "found": h is not None,
                      "rect": rect_of_hwnd(h) if h else None}))
elif cmd == "shot":
    name = sys.argv[2]
    h = find_hwnd(state()["sub"])
    img = print_window(h, os.path.join(ART, f"{name}.png"))
    e = content_energy(img) if img else None
    print(json.dumps({"ok": img is not None, "energy": round(e, 3) if e else None,
                      "file": f"{name}.png"}))
elif cmd == "key":
    h = find_hwnd(state()["sub"])
    fg = force_fg(h)
    for k in sys.argv[2:]:
        vk = VK[k.upper()]
        u.keybd_event(vk, 0, 0, 0); time.sleep(0.08)
        u.keybd_event(vk, 0, 2, 0); time.sleep(0.45)
    print(json.dumps({"foreground": fg, "sent": sys.argv[2:]}))
elif cmd == "probe":
    name = sys.argv[2]
    h = find_hwnd(state()["sub"])
    c = auto.ControlFromHandle(h)
    n = 0
    def cnt(x, d=0):
        global n
        n += 1
        if d < 10:
            for k in x.GetChildren():
                cnt(k, d + 1)
    cnt(c)
    img = print_window(h, os.path.join(ART, f"{name}.png"))
    e = content_energy(img) if img else None
    print(json.dumps({"uia_nodes": n, "uia_type": c.ControlTypeName,
                      "energy": round(e, 3) if e else None,
                      "rect": rect_of_hwnd(h), "file": f"{name}.png"}))
elif cmd == "framediff":
    h = find_hwnd(state()["sub"])
    a = print_window(h)
    time.sleep(1.0)
    b = print_window(h)
    sa = a.convert("RGB").resize((128, 72)); sb = b.convert("RGB").resize((128, 72))
    pa, pb = list(sa.getdata()), list(sb.getdata())
    changed = sum(1 for x, y in zip(pa, pb)
                  if abs(x[0]-y[0]) + abs(x[1]-y[1]) + abs(x[2]-y[2]) > 30)
    print(json.dumps({"changed_pixel_pct": round(100 * changed / len(pa), 1)}))
elif cmd == "close":
    h = find_hwnd(state()["sub"])
    if h:
        u.PostMessageW(h, 0x0010, 0, 0)
        time.sleep(8)
        h2 = find_hwnd(state()["sub"])
        if h2:
            pid = wintypes.DWORD()
            u.GetWindowThreadProcessId(h2, ctypes.byref(pid))
            subprocess.run(["taskkill", "/PID", str(pid.value), "/F"], capture_output=True)
            time.sleep(3)
            print(json.dumps({"closed_via": "kill (WM_CLOSE insufficient)",
                              "gone": find_hwnd(state()["sub"]) is None}))
        else:
            print(json.dumps({"closed_via": "WM_CLOSE", "gone": True}))
    else:
        print(json.dumps({"closed_via": "already gone", "gone": True}))
