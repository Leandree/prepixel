#!/usr/bin/env python3
"""Semantic compositor / router (PoC).

Reconstructs a MERGED semantic view of the whole desktop that no single rendering
channel provides: the window manager supplies the map (which windows, geometry,
stacking, focus); then per window the router detects the app's toolkit from a
signature and binds the best available structured channel — CDP for Chromium/
Electron, UNO for LibreOffice, render-tree tap for GTK, accessibility/pixels
fallback otherwise. Output: a desktop tree with a per-window verdict of whether
structure is available, all decided BEFORE extracting content (predictability).

Env: DISPLAY set to the running Xvfb desktop. Optional focus content extraction
for the focused window if its channel is cheap (CDP).
"""
import subprocess, os, json, re, socket, sys, glob

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def proc_maps(pid):
    try:
        return open(f'/proc/{pid}/maps').read()
    except Exception:
        return ''

def proc_cmdline(pid):
    try:
        return open(f'/proc/{pid}/cmdline').read().replace('\x00', ' ').strip()
    except Exception:
        return ''

def port_open(port):
    s = socket.socket(); s.settimeout(0.3)
    try:
        s.connect(('127.0.0.1', port)); return True
    except Exception:
        return False
    finally:
        s.close()

# ---- 1. window-manager map (EWMH) -----------------------------------------
def window_map():
    rows = []
    for line in sh('wmctrl -lpG').splitlines():
        p = line.split(None, 8)
        if len(p) < 8: continue
        wid, desk, pid, x, y, w, h = p[0], p[1], int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6])
        title = p[8] if len(p) > 8 else ''
        rows.append({'wid': wid, 'pid': pid, 'geometry': [x, y, w, h], 'title': title})
    # stacking order (bottom->top) from _NET_CLIENT_LIST_STACKING
    stack = sh('xprop -root _NET_CLIENT_LIST_STACKING')
    ids = re.findall(r'0x[0-9a-fA-F]+', stack)
    order = {int(i, 16): k for k, i in enumerate(ids)}
    for r in rows:
        r['z'] = order.get(int(r['wid'], 16), -1)
    # focused window
    active = sh('xprop -root _NET_ACTIVE_WINDOW')
    m = re.search(r'0x[0-9a-fA-F]+', active)
    afocus = int(m.group(0), 16) if m else None
    for r in rows:
        r['focused'] = (int(r['wid'], 16) == afocus)
    rows.sort(key=lambda r: r['z'])
    return rows

# ---- 2. per-window stack detection (signature) ----------------------------
def detect_stack(pid):
    maps = proc_maps(pid); cmd = proc_cmdline(pid)
    sig = None; stack = 'unknown'
    if 'libgtk-4' in maps:
        stack, sig = 'gtk4', 'libgtk-4.so mapped'
    elif re.search(r'libQt[56]', maps):
        stack, sig = 'qt', re.search(r'libQt[56]\w*\.so[.\d]*', maps).group(0) + ' mapped'
    elif 'soffice' in cmd or 'soffice.bin' in maps:
        stack, sig = 'office-native', 'soffice process'
    elif re.search(r'/chrome|/chromium|chrome-sandbox', maps + cmd):
        stack, sig = 'chromium', 'chromium binary mapped'
    elif 'libgtk-3' in maps:
        stack, sig = 'gtk3', 'libgtk-3.so mapped'
    return stack, sig

# ---- 3. channel decision + availability (before extraction) ---------------
def decide_channel(stack, title):
    # returns (channel, verdict, coverage, failure_class, note)
    if stack == 'chromium':
        if port_open(9222):
            return ('cdp', 'works', 'text+widgets+declared-opaque-rects', 'explicit',
                    'CDP :9222 live; covers all Electron apps identically')
        return ('cdp', 'unavailable', '-', 'explicit', 'no --remote-debugging-port; would need relaunch')
    if stack == 'office-native':
        if port_open(2002):
            return ('object-model', 'works', 'full document model (text/tables/shapes)', 'none',
                    'UNO socket :2002 live')
        return ('object-model', 'partial', 'document model if UNO enabled', 'explicit',
                'UNO socket not exposed; needs --accept=socket')
    if stack == 'gtk4':
        return ('render-tree-tap', 'works', 'full render tree (glyph-decoded text)', 'none',
                'gsk_render_node_serialize via hook/gdb; completeness proven separately')
    if stack == 'gtk3':
        return ('accessibility-api', 'partial', 'a11y tree if session bus', 'blocked',
                'GTK3 has no GSK; AT-SPI only')
    if stack == 'qt':
        return ('accessibility-api', 'unavailable', 'no public render-tree; AT-SPI if QAccessible', 'explicit',
                'Qt exposes no render-tree serialization; falls to AT-SPI/pixels')
    return ('pixels-baseline', 'unavailable', 'opaque; vision on crop', 'explicit', 'unknown stack -> pixels')

def main():
    wins = window_map()
    desktop = {'display': os.environ.get('DISPLAY'), 'windows': []}
    for r in wins:
        stack, sig = detect_stack(r['pid'])
        channel, verdict, coverage, fclass, note = decide_channel(stack, r['title'])
        desktop['windows'].append({
            'title': r['title'], 'pid': r['pid'], 'geometry': r['geometry'],
            'z_order': r['z'], 'focused': r['focused'],
            'stack': stack, 'stack_signature': sig,
            'channel': channel, 'verdict': verdict, 'coverage': coverage,
            'failure_class': fclass, 'note': note,
            'predictable_before_use': sig is not None
        })
    print(json.dumps(desktop, indent=2))
    return desktop

if __name__ == '__main__':
    main()
