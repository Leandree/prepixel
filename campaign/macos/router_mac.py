# -*- coding: utf-8 -*-
"""Cell: macos-desktop-router. The semantic-compositor router on a LIVE macOS
desktop: CGWindowList (the compositor layer: z-order, geometry, pid, owner,
layer, alpha) + best-channel binding per window decided from signatures BEFORE
reading + content extraction through the bound channel + cross-window occlusion
resolved with a single system-wide hit test.

macOS gives this router one primitive neither Linux nor Windows has in the same
form: AXUIElementCopyElementAtPosition asks the WINDOW SERVER "what is actually
at this screen point", so occlusion is answered by the compositor itself rather
than reconstructed from a z-order list. We use it as the ground truth and check
the z-order reconstruction against it.

Privacy rule, same as the Windows cell: the user's own windows are mapped and
channel-classified ONLY — no content walk, no text in artifacts. Content
extraction is demonstrated on windows WE launched.
"""
import json, os, re, subprocess, sys, time, urllib.request

import Quartz
from ApplicationServices import (
    AXUIElementCreateApplication, AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue, AXUIElementCopyElementAtPosition,
    AXUIElementGetPid,
)

OUT = os.path.join(os.path.dirname(__file__), '..', 'results', 'artifacts', 'macos')
os.makedirs(OUT, exist_ok=True)

# ---------- token accounting (mirror of src/image-tokens.mjs) ----------
def image_tokens(w, h, tier='highres'):
    max_edge, max_mp = (2576, 3.588e6) if tier == 'highres' else (1568, 1.15e6)
    s = 1.0
    if max(w, h) > max_edge: s = max_edge / max(w, h)
    if (w * s) * (h * s) > max_mp: s = min(s, (max_mp / (w * h)) ** 0.5)
    return int((w * s) * (h * s) / 750 + 0.999)

def text_tokens(s): return (len(s) + 3) // 4

# ---------- the compositor map ----------
def window_map():
    """CGWindowList returns windows FRONT TO BACK — that ordering IS the z-order."""
    opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    infos = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID)
    out = []
    for z, w in enumerate(infos):
        b = w.get('kCGWindowBounds', {})
        out.append({
            'z': z,                                     # 0 = frontmost
            'wid': w.get('kCGWindowNumber'),
            'pid': w.get('kCGWindowOwnerPID'),
            'owner': w.get('kCGWindowOwnerName'),
            'title': w.get('kCGWindowName') or '',
            'rect': [int(b.get('X', 0)), int(b.get('Y', 0)), int(b.get('Width', 0)), int(b.get('Height', 0))],
            'layer': w.get('kCGWindowLayer'),
            'alpha': round(float(w.get('kCGWindowAlpha', 1)), 2),
        })
    return out

# ---------- channel binding, from signatures, BEFORE reading content ----------
def proc_args(pid):
    try:
        return subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ''

def cdp_port_of(pid):
    m = re.search(r'--remote-debugging-port=(\d+)', proc_args(pid))
    if not m: return None
    port = int(m.group(1))
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=2) as r:
            return {'port': port, 'browser': json.loads(r.read())['Browser']}
    except Exception:
        return None

def bundle_of(pid):
    try:
        return subprocess.run(['lsappinfo', 'info', '-only', 'bundleid', '-app', str(pid)],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ''

SCRIPTABLE = {'com.apple.iWork.Pages', 'com.apple.iWork.Numbers', 'com.apple.iWork.Keynote',
              'com.apple.finder', 'com.apple.TextEdit', 'com.apple.Safari', 'com.apple.mail',
              'com.apple.Music', 'com.apple.Notes'}

def ax_window_count(pid):
    app = AXUIElementCreateApplication(pid)
    err, wins = AXUIElementCopyAttributeValue(app, 'AXWindows', None)
    if err != 0 or wins is None: return -1        # AX refused / not answering
    return len(wins)

def bind_channel(w):
    """Return (channel, signature, predicted_before_read). Order matters: the
    cheapest, most faithful channel first — exactly what a production router does."""
    pid = w['pid']
    cdp = cdp_port_of(pid)
    if cdp:
        return 'cdp', f"--remote-debugging-port={cdp['port']} answers /json/version -> {cdp['browser']}", True
    bid = ''
    # lsappinfo prints: "CFBundleIdentifier"="com.apple.TextEdit" — take the VALUE
    m = re.search(r'=\s*"([\w\.\-]+)"', bundle_of(pid))
    if m: bid = m.group(1)
    n = ax_window_count(pid)
    if bid in SCRIPTABLE and n >= 0:
        return 'accessibility-api+object-model', f'bundle {bid} is AppleScript-scriptable; AX answers {n} windows', True
    if n > 0:
        return 'accessibility-api', f'AXUIElementCreateApplication({pid}) answers {n} windows' + (f'; bundle {bid}' if bid else ''), True
    if n == 0:
        return 'pixels-baseline', f'AX answers but exposes 0 windows (frame-only) -> 0% structural coverage, crop', True
    return 'pixels-baseline', 'AX refused for this pid (no TCC / not an AX client) -> pixels', True

# ---------- cross-window occlusion, answered by the window server itself ----------
def owner_at(x, y):
    """One system-wide hit test. Returns the pid that actually owns that screen
    point — i.e. the compositor's own answer to 'who is on top here'."""
    sysw = AXUIElementCreateSystemWide()
    err, el = AXUIElementCopyElementAtPosition(sysw, float(x), float(y), None)
    if err != 0 or el is None: return None
    err2, pid = AXUIElementGetPid(el, None)
    role = ''
    e3, r = AXUIElementCopyAttributeValue(el, 'AXRole', None)
    if e3 == 0 and r: role = str(r)
    return {'pid': int(pid) if err2 == 0 else None, 'role': role}

def overlaps(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    return (x0, y0, x1 - x0, y1 - y0) if x1 > x0 and y1 > y0 else None

def main():
    t0 = time.time()
    wins = window_map()
    map_ms = (time.time() - t0) * 1000

    # bind a channel to every window, from signatures only
    for w in wins:
        ch, sig, pred = bind_channel(w)
        w['channel'], w['signature'], w['predicted_before_read'] = ch, sig, pred

    # the merged map as the router would serialize it (no content yet)
    lines = [f"win z={w['z']} {w['rect'][0]},{w['rect'][1]},{w['rect'][2]},{w['rect'][3]} "
             f"owner={w['owner']} channel={w['channel']}" + (f" title={w['title']}" if w['title'] else '')
             for w in wins]
    merged = '\n'.join(lines)

    # full-desktop screenshot cost, for the comparison
    disp = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
    sw, sh = int(disp.size.width), int(disp.size.height)

    # OCCLUSION — the cell's core measurement. Two ways to answer "who owns this
    # pixel": (1) reconstruct from the z-order list and the declared rects, which
    # is all Linux/Windows routers can do; (2) ask the window server directly with
    # AXUIElementCopyElementAtPosition. We run BOTH on every overlapping pair and
    # count how often (1) is wrong, because every disagreement is a region a
    # reconstruction router would wrongly mark hidden (or wrongly mark visible).
    def contains(r, x, y): return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]

    def predict_by_zorder(x, y):
        """What a reconstruction router concludes: the first window in front-to-back
        order whose declared rect contains the point. This is the ONLY thing a
        Linux/Windows router can compute — there is no compositor hit test there."""
        for w in wins:                       # wins is already front-to-back
            if contains(w['rect'], x, y):
                return w
        return None

    # probe points = centres of genuine pairwise overlaps (the interesting places)
    points = []
    for i, a in enumerate(wins):
        for b in wins[i + 1:]:
            if a['pid'] == b['pid']: continue
            ov = overlaps(a['rect'], b['rect'])
            if ov and ov[2] >= 40 and ov[3] >= 40:
                points.append((ov[0] + ov[2] // 2, ov[1] + ov[3] // 2))
    seen, uniq = set(), []
    for p in points:
        if p not in seen: seen.add(p); uniq.append(p)

    probes, disagreements = [], 0
    for (cx, cy) in uniq[:40]:
        pred = predict_by_zorder(cx, cy)
        hit = owner_at(cx, cy)
        agree = bool(pred and hit and hit['pid'] == pred['pid'])
        if not agree: disagreements += 1
        probes.append({
            'point': [cx, cy],
            'zorder_predicts': None if not pred else
                {'z': pred['z'], 'owner': pred['owner'], 'pid': pred['pid'],
                 'layer': pred['layer'], 'alpha': pred['alpha'], 'rect': pred['rect']},
            'window_server_says_pid': hit['pid'] if hit else None,
            'window_server_role': hit['role'] if hit else None,
            'agrees': agree,
        })
    # name who the window server actually named, for the disagreements
    bypid = {w['pid']: w['owner'] for w in wins}
    for p in probes:
        p['window_server_owner'] = bypid.get(p['window_server_says_pid'])
    occl = {
        'points_probed': len(probes),
        'zorder_wrong': disagreements,
        'zorder_accuracy': round(1 - disagreements / len(probes), 3) if probes else None,
        'probes': probes,
    }

    # CONTENT, pulled through the bound channel — ONLY for windows we launched
    # ourselves (pids passed on the command line). The user's windows above were
    # mapped and classified; none of their content is read or stored.
    owned = {int(p) for p in sys.argv[1:] if p.isdigit()}
    extracted = []
    for w in wins:
        if w['pid'] not in owned or w['rect'][2] < 100:
            continue
        t0 = time.time()
        view, note = '', ''
        if w['channel'] == 'cdp':
            port = int(re.search(r'port=(\d+)', w['signature']).group(1))
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=3) as r:
                    tabs = [t for t in json.loads(r.read()) if t.get('type') == 'page']
                view = '\n'.join(f"tab {t['title']} {t['url']}" for t in tabs)
                note = 'page-level channel; DOM distillation demonstrated in macos-chrome-cdp'
            except Exception as e:
                note = f'cdp read failed: {e}'
        else:
            app = AXUIElementCreateApplication(w['pid'])
            err, awins = AXUIElementCopyAttributeValue(app, 'AXWindows', None)
            if err == 0 and awins:
                out = []
                def walk(el, d=0):
                    if d > 6 or len(out) > 120: return
                    for attr in ('AXTitle', 'AXValue', 'AXDescription'):
                        e, v = AXUIElementCopyAttributeValue(el, attr, None)
                        if e == 0 and isinstance(v, str) and v.strip():
                            out.append(f"{attr[2:].lower()} \"{v.strip()[:120]}\""); break
                    e2, kids = AXUIElementCopyAttributeValue(el, 'AXChildren', None)
                    if e2 == 0 and kids:
                        for k in kids: walk(k, d + 1)
                walk(awins[0])
                view = '\n'.join(out)
                note = 'AX walk of the focused window of a process we launched'
        extracted.append({'owner': w['owner'], 'channel': w['channel'], 'ms': round((time.time() - t0) * 1000, 1),
                          'view_bytes': len(view), 'view_tokens': text_tokens(view),
                          'shot_tokens_if_pixels': image_tokens(w['rect'][2], w['rect'][3]), 'note': note,
                          'sample': view[:400]})

    report = {
        'n_windows': len(wins),
        'map_latency_ms': round(map_ms, 1),
        'merged_map_bytes': len(merged),
        'merged_map_tokens': text_tokens(merged),
        'screen': [sw, sh],
        'fullscreen_shot_tokens': image_tokens(sw, sh),
        'fullscreen_shot_tokens_retina2x': image_tokens(sw * 2, sh * 2),
        'channels': {},
        'occlusion_probe': occl,
        'content_extracted_from_owned_windows': extracted,
        'windows': wins,
    }
    for w in wins:
        report['channels'][w['channel']] = report['channels'].get(w['channel'], 0) + 1
    print(json.dumps(report, indent=1, ensure_ascii=False))
    with open(os.path.join(OUT, 'router-window-map.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, 'router-merged-map.txt'), 'w', encoding='utf-8') as f:
        f.write(merged + '\n')

if __name__ == '__main__':
    main()
