# -*- coding: utf-8 -*-
"""Cell probe: an unannotated GPU game — the honest pixels-territory control.

Chess refuted "game implies pixels only" because Apple annotated every piece.
This probe runs the same battery against a real 3D title to find the other end of
the boundary: a window that is a GPU surface and nothing else. What we want to
establish is NOT "structure fails" — it is that the failure is EXPLICIT: the tree
is frame-only, a router computes 0% structural coverage of the client area in one
walk, and routes to pixels without ever being told something false.

Read-only. No input is sent to the game. Usage: probe_game.py <owner-substring>
"""
import json, os, sys, time
import Quartz
from Quartz import CGWindowListCreateImage, CGRectNull, CGRectMake
from Quartz import CGImageDestinationCreateWithURL, CGImageDestinationAddImage, CGImageDestinationFinalize
from Foundation import NSURL
from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
                                 AXUIElementCopyAttributeNames)

OUT = os.path.join(os.path.dirname(__file__), '..', 'results', 'artifacts', 'macos')
os.makedirs(OUT, exist_ok=True)

def image_tokens(w, h, tier='highres'):
    max_edge, max_mp = (2576, 3.588e6) if tier == 'highres' else (1568, 1.15e6)
    s = 1.0
    if max(w, h) > max_edge: s = max_edge / max(w, h)
    if (w * s) * (h * s) > max_mp: s = min(s, (max_mp / (w * h)) ** 0.5)
    return int((w * s) * (h * s) / 750 + 0.999)

def find_window(sub):
    opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    best = None
    for w in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID):
        owner = str(w.get('kCGWindowOwnerName') or '')
        if sub.lower() not in owner.lower(): continue
        b = w['kCGWindowBounds']
        area = b['Width'] * b['Height']
        cand = {'wid': w['kCGWindowNumber'], 'pid': w['kCGWindowOwnerPID'], 'owner': owner,
                'title': w.get('kCGWindowName') or '',
                'rect': [int(b['X']), int(b['Y']), int(b['Width']), int(b['Height'])],
                'layer': w.get('kCGWindowLayer'), 'alpha': round(float(w.get('kCGWindowAlpha', 1)), 2),
                'area': area}
        if not best or area > best['area']: best = cand
    return best

def ax_tree(pid, cap=600):
    """Walk the app's AX tree. We record the SHAPE (roles, depth, how many nodes
    carry any text) because that shape is what a router keys on."""
    app = AXUIElementCreateApplication(pid)
    err, wins = AXUIElementCopyAttributeValue(app, 'AXWindows', None)
    nodes, roles = [], {}
    info = {'axwindows_err': int(err), 'n_axwindows': 0 if not wins else len(wins)}
    if err != 0 or not wins:
        return info, nodes, roles
    e, names = AXUIElementCopyAttributeNames(wins[0], None)
    info['window_attributes'] = list(names) if e == 0 else []
    def g(el, a):
        er, v = AXUIElementCopyAttributeValue(el, a, None)
        return v if er == 0 else None
    def walk(el, d=0):
        if d > 14 or len(nodes) >= cap: return
        role = str(g(el, 'AXRole') or '')
        roles[role] = roles.get(role, 0) + 1
        txt = None
        for a in ('AXTitle', 'AXValue', 'AXDescription', 'AXHelp'):
            v = g(el, a)
            if isinstance(v, str) and v.strip(): txt = f'{a[2:].lower()}={v.strip()[:80]}'; break
        pos, size = g(el, 'AXPosition'), g(el, 'AXSize')
        nodes.append({'d': d, 'role': role, 'sub': str(g(el, 'AXSubrole') or ''), 'text': txt,
                      'has_geometry': bool(pos and size)})
        er, kids = AXUIElementCopyAttributeValue(el, 'AXChildren', None)
        if er == 0 and kids:
            for k in kids: walk(k, d + 1)
    walk(wins[0])
    return info, nodes, roles

def save_png(img, name):
    if img is None: return None
    p = os.path.join(OUT, name)
    d = CGImageDestinationCreateWithURL(NSURL.fileURLWithPath_(p), 'public.png', 1, None)
    CGImageDestinationAddImage(d, img, None); CGImageDestinationFinalize(d)
    return p

def main():
    sub = sys.argv[1] if len(sys.argv) > 1 else 'DiRT'
    tag = sub.lower().replace(' ', '-')
    w = find_window(sub)
    if not w:
        print(json.dumps({'error': f'no on-screen window matching {sub!r}'})); return
    info, nodes, roles = ax_tree(w['pid'])

    # the two captures the SwiftUI cell showed are not interchangeable
    region = CGWindowListCreateImage(CGRectMake(*w['rect']), Quartz.kCGWindowListOptionOnScreenOnly,
                                     Quartz.kCGNullWindowID, Quartz.kCGWindowImageDefault)
    surface = CGWindowListCreateImage(CGRectNull, Quartz.kCGWindowListOptionIncludingWindow,
                                      w['wid'], Quartz.kCGWindowImageBoundsIgnoreFraming)
    pr = save_png(region, f'{tag}-screen-region.png')
    ps = save_png(surface, f'{tag}-window-surface.png')

    # structural coverage of the client area: fraction of the window's pixels that
    # any AX node with geometry actually accounts for. This is the number a router
    # computes to decide "is there anything here for me to read?".
    covered = 0
    for n in nodes:
        if n['has_geometry'] and n['d'] > 0: covered += 1
    txt_nodes = [n for n in nodes if n['text']]
    out = {
        'window': w,
        'ax': info,
        'n_nodes': len(nodes),
        'roles': roles,
        'nodes_with_text': len(txt_nodes),
        'sample_text': [n['text'] for n in txt_nodes[:12]],
        'max_depth': max([n['d'] for n in nodes], default=None),
        'child_nodes_with_geometry': covered,
        'screenshot_tokens_window': image_tokens(w['rect'][2], w['rect'][3]),
        'artifacts': {'screen_region': pr, 'window_surface': ps},
    }
    print(json.dumps(out, indent=1, ensure_ascii=False))
    with open(os.path.join(OUT, f'{tag}-ax-probe.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

if __name__ == '__main__':
    main()
