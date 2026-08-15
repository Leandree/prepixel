#!/usr/bin/env python3
"""Cross-window occlusion on macOS: does the OS give a router what per-window
structure cannot see, and is there a hit-test primitive?

Back window : Chrome (page content readable via CDP / AX)
Front window: TextEdit, positioned to cover part of it.

Measures:
  1. compositor map (CGWindowList): z-order + bounds -> % of back window covered
  2. AXUIElementCopyElementAtPosition at a covered point -> which app answers?
  3. the back window's own AX view at that same point -> does it still claim content?
"""
import json, subprocess, time, sys
import Quartz
from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication, AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue, AXUIElementCopyElementAtPosition,
    AXUIElementSetAttributeValue, AXValueCreate, AXValueGetValue,
    kAXValueCGPointType, kAXValueCGSizeType, kAXValueCGRectType,
)

def attr(el, a):
    err, v = AXUIElementCopyAttributeValue(el, a, None)
    return v if err == 0 else None

def unwrap(v):
    if v is None: return None
    if 'AXValue' in type(v).__name__:
        for kind, n in ((kAXValueCGRectType,'rect'),(kAXValueCGPointType,'point'),(kAXValueCGSizeType,'size')):
            ok, s = AXValueGetValue(v, kind, None)
            if ok:
                if n=='rect': return {'x':s.origin.x,'y':s.origin.y,'w':s.size.width,'h':s.size.height}
                if n=='point': return {'x':s.x,'y':s.y}
                return {'w':s.width,'h':s.height}
        return str(v)
    return v if isinstance(v,(str,int,float,bool)) else str(v)

def pid_of(name):
    for a in NSWorkspace.sharedWorkspace().runningApplications():
        if a.localizedName() and name.lower() in a.localizedName().lower():
            return a.processIdentifier()
    raise SystemExit(f'{name} not running')

def onscreen_windows():
    wl = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID)
    # CGWindowList is returned front-to-back => index IS the z-order
    return [{'z': i, 'pid': w.get('kCGWindowOwnerPID'), 'owner': w.get('kCGWindowOwnerName'),
             'name': w.get('kCGWindowName'), 'layer': w.get('kCGWindowLayer'),
             'bounds': dict(w['kCGWindowBounds'])} for i, w in enumerate(wl)]

def overlap(a, b):
    x = max(0, min(a['X']+a['Width'], b['X']+b['Width']) - max(a['X'], b['X']))
    y = max(0, min(a['Y']+a['Height'], b['Y']+b['Height']) - max(a['Y'], b['Y']))
    return x*y

# --- place TextEdit over Chrome -------------------------------------------------
te_pid = pid_of('TextEdit')
te_app = AXUIElementCreateApplication(te_pid)
wins = attr(te_app, 'AXWindows') or []
if not wins:
    raise SystemExit('TextEdit has no window')
te_win = wins[0]
pt = AXValueCreate(kAXValueCGPointType, Quartz.CGPoint(300, 260))
sz = AXValueCreate(kAXValueCGSizeType, Quartz.CGSize(520, 380))
AXUIElementSetAttributeValue(te_win, 'AXPosition', pt)
AXUIElementSetAttributeValue(te_win, 'AXSize', sz)
time.sleep(1.0)

wl = onscreen_windows()
chrome = next(w for w in wl if w['owner']=='Google Chrome' and w['layer']==0 and w['bounds']['Width']>400)
te = next(w for w in wl if w['owner']=='TextEdit' and w['layer']==0)

cov = overlap(chrome['bounds'], te['bounds'])
area = chrome['bounds']['Width']*chrome['bounds']['Height']
front_is_textedit = te['z'] < chrome['z']

# a point inside the covered region (centre of the intersection)
ix0 = max(chrome['bounds']['X'], te['bounds']['X']); ix1 = min(chrome['bounds']['X']+chrome['bounds']['Width'], te['bounds']['X']+te['bounds']['Width'])
iy0 = max(chrome['bounds']['Y'], te['bounds']['Y']); iy1 = min(chrome['bounds']['Y']+chrome['bounds']['Height'], te['bounds']['Y']+te['bounds']['Height'])
px, py = (ix0+ix1)/2, (iy0+iy1)/2

# --- 2. OS-level hit test -------------------------------------------------------
sysw = AXUIElementCreateSystemWide()
err, hit = AXUIElementCopyElementAtPosition(sysw, px, py, None)
hit_info = None
if err == 0 and hit is not None:
    hpid = attr(hit, 'AXPid')
    owner = None
    for a in NSWorkspace.sharedWorkspace().runningApplications():
        if a.processIdentifier() == (hpid or -1): owner = a.localizedName()
    hit_info = {'role': unwrap(attr(hit,'AXRole')), 'pid': hpid, 'owner': owner,
                'frame': unwrap(attr(hit,'AXFrame'))}

# --- 3. does the BACK window's own structure still claim that point? ------------
ch_app = AXUIElementCreateApplication(chrome['pid'])
ch_wins = attr(ch_app, 'AXWindows') or []
back_claims = None
if ch_wins:
    bw = ch_wins[0]
    bf = unwrap(attr(bw, 'AXFrame'))
    inside = bf and bf['x'] <= px <= bf['x']+bf['w'] and bf['y'] <= py <= bf['y']+bf['h']
    back_claims = {'window_frame': bf, 'point_inside_back_window': bool(inside)}

print(json.dumps({
  'compositor_map': {
     'front': {'owner': te['owner'], 'z': te['z'], 'bounds': te['bounds']},
     'back':  {'owner': chrome['owner'], 'z': chrome['z'], 'bounds': chrome['bounds']},
     'front_is_textedit': front_is_textedit,
     'covered_fraction_of_back': round(cov/area, 4),
  },
  'probe_point': [px, py],
  'os_hit_test': hit_info,
  'back_window_structure': back_claims,
}, ensure_ascii=False, indent=1))
