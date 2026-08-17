# -*- coding: utf-8 -*-
"""Cell: windows-desktop-router. The semantic-compositor router on a LIVE
Windows desktop: Win32 window map (the WM/compositor layer: z-order, geometry,
pid, elevation, cloaking) + best-channel binding per window + content
extraction through the bound channel for our own probe windows.

Privacy rule: the user's own windows (Discord, Chrome, Spotify, Terminal,
Notepad) are mapped and channel-classified ONLY — no content walk, no text
lines in artifacts. Content extraction is demonstrated on windows WE launched.
"""
import ctypes
from ctypes import wintypes
import json, os, socket, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, text_tokens, image_tokens,
                       screenshot, save_artifact)

u = ctypes.windll.user32
k = ctypes.windll.kernel32
a = ctypes.windll.advapi32
dwm = ctypes.windll.dwmapi
psapi = ctypes.windll.psapi

def pid_of(hwnd):
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def pname(pid):
    h = k.OpenProcess(0x1000, False, pid)
    if not h: return None
    buf = ctypes.create_unicode_buffer(260)
    n = wintypes.DWORD(260)
    ok = k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    k.CloseHandle(h)
    return os.path.basename(buf.value) if ok else None

def elevated(pid):
    h = k.OpenProcess(0x1000, False, pid)
    if not h: return None
    tok = wintypes.HANDLE()
    if not a.OpenProcessToken(h, 8, ctypes.byref(tok)):
        k.CloseHandle(h); return None
    val = wintypes.DWORD(); ret = wintypes.DWORD()
    a.GetTokenInformation(tok, 20, ctypes.byref(val), 4, ctypes.byref(ret))
    k.CloseHandle(h)
    return bool(val.value)

def cloaked(hwnd):
    v = ctypes.c_int(0)
    dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(v), 4)
    return v.value != 0

def title_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, buf, 256)
    return buf.value

def port_open(port):
    s = socket.socket(); s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", port)); s.close(); return True
    except Exception:
        return False

out = {"cell": "windows-desktop-router"}

# launch our two probe windows (2 more toolkits on screen)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof = os.path.join(os.environ["TEMP"], "ptap-router-chrome")
url = "file:///" + os.path.join(ROOT, "pages", "testapp.html").replace("\\", "/")
chrome = subprocess.Popen([CHROME, "--remote-debugging-port=9235",
                           f"--user-data-dir={prof}", "--no-first-run",
                           "--window-size=900,700", "--window-position=100,100", url])
timedate = subprocess.Popen(["control.exe", "timedate.cpl"])
time.sleep(5)

# ---- layer 1: the window-manager / compositor map (Win32, sees EVERYTHING) --
wins = []
@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lp):
    if not u.IsWindowVisible(hwnd) or cloaked(hwnd):
        return True
    t = title_of(hwnd)
    if not t:
        return True
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    if r.right - r.left <= 0 or r.bottom - r.top <= 0:
        return True
    pid = pid_of(hwnd)
    # macOS router FYI (layer>0 predicts false occlusion): layered/transparent
    # windows declare rects that are upper bounds on what they paint —
    # geometric occlusion reconstruction must not trust them; pixel-spot-check
    # with the per-window surface instead.
    exstyle = u.GetWindowLongW(hwnd, -20)
    wins.append({"z": len(wins), "hwnd": hwnd, "title": t,
                 "rect": [r.left, r.top, r.right - r.left, r.bottom - r.top],
                 "pid": pid, "process": pname(pid), "elevated": elevated(pid),
                 "layered": bool(exstyle & 0x00080000),      # WS_EX_LAYERED
                 "click_through": bool(exstyle & 0x00000020),  # WS_EX_TRANSPARENT
                 "rect_is_upper_bound": bool(exstyle & 0x00080020),
                 "foreground": u.GetForegroundWindow() == hwnd})
    return True
t0 = time.perf_counter()
u.EnumWindows(cb, 0)
out["wm_map_ms"] = round((time.perf_counter() - t0) * 1000, 1)

# ---- layer 2: per-window stack detection -> channel binding -----------------
USER_WINDOWS = ("Discord", "Spotify", "chrome", "WindowsTerminal", "Notepad")
def bind(w):
    p = (w["process"] or "").lower()
    if w["elevated"]:
        return "pixels-crop (UIA blocked by integrity boundary — Win32 map still sees it)"
    if p == "chrome.exe" and port_open(9235) and w["rect"][0] == 100:
        return "cdp (:9235 answers)"
    if p in ("chrome.exe", "discord.exe", "spotify.exe", "msedge.exe"):
        return "uia-latch (Chromium/Electron/CEF: content appears on walk 2)"
    if p in ("notepad.exe", "windowsterminal.exe", "rundll32.exe", "explorer.exe"):
        return "uia (native tree on first walk)"
    return "uia (probe shape first — FL-class apps yield region maps only)"

for w in wins:
    w["channel"] = bind(w)
    mine = (w["process"] or "").lower() in ("chrome.exe", "rundll32.exe") and \
           ("Acme Console" in w["title"] or "Date et heure" in w["title"])
    w["content_extracted"] = bool(mine)

map_lines = [f'{w["z"]} {w["rect"]} {"[elev]" if w["elevated"] else ""}'
             f'{"[fg]" if w["foreground"] else ""} {w["process"]}: "{w["title"][:50]}"'
             f' -> {w["channel"].split(" ")[0]}' for w in wins]
map_txt = "\n".join(map_lines)
out["wm_map_tokens"] = text_tokens(map_txt)
out["windows_mapped"] = len(wins)

# ---- layer 3: content through the bound channel, for OUR windows ------------
content = {}
td = auto.WindowControl(searchDepth=1, RegexName="Date et heure|Date and Time")
if td.Exists(5):
    v, _ = distill(td)
    content["timedate_via_uia"] = {"tokens": text_tokens(v),
                                   "sample": v.splitlines()[2:7]}
try:
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:9235/json", timeout=3) as r:
        tabs = json.loads(r.read())
    page = next(t for t in tabs if t["type"] == "page")
    content["chrome_via_cdp"] = {"target": page["url"].rsplit("/", 1)[-1],
                                 "note": "full distilled extraction proven in windows-chrome-cdp (273 tok)"}
except Exception as e:
    content["chrome_via_cdp"] = {"error": str(e)[:120]}
out["content"] = content

# full-desktop pixel reference
screenshot(None, os.path.join(os.path.dirname(__file__), "..", "results",
                              "artifacts", "windows", "router-desktop-shot.png"))
out["desktop_screenshot_tokens"] = image_tokens(1920, 1080)

save_artifact("router-window-map.txt", map_txt)
save_artifact("router-merged-view.json", json.dumps(
    {"map": [{kk: w[kk] for kk in ("z", "title", "rect", "process", "elevated",
                                   "foreground", "channel", "content_extracted")}
             for w in wins],
     "content": content}, ensure_ascii=False, indent=1))

# cleanup our probes
chrome.terminate()
if td.Exists(2):
    td.GetPattern(auto.PatternId.WindowPattern).Close()
out["map_preview"] = map_lines[:14]
print(json.dumps(out, ensure_ascii=False, indent=1))
