# -*- coding: utf-8 -*-
"""Cell probe: Zoom IN-MEETING surfaces (macOS AX).

The home window was covered in macos-zoom-accessibility-api; the in-meeting
surfaces were deliberately left untested on the user's live account. This probe
runs while a real meeting is open, on the user's explicit request.

PRIVACY IS PART OF THE PROBE, not an afterthought. A live meeting window can carry
participant names, chat, shared documents and video of real people who did not
consent to being in a research artifact. So:
  - read-only: no action is performed, no input is sent;
  - NO screenshot of the meeting window is ever written to disk;
  - text is classified, not copied. A string is kept verbatim only if it matches a
    known UI-chrome vocabulary (Mute, Participants, Chat, Share...). Anything else
    is stored as a redaction stub recording its LENGTH and CATEGORY, which is all
    the cell needs: what matters scientifically is whether the channel exposes a
    given kind of content, not what that content says.
"""
import json, os, re, sys, unicodedata
import Quartz
from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue)

OUT = os.path.join(os.path.dirname(__file__), '..', 'results', 'artifacts', 'macos')
os.makedirs(OUT, exist_ok=True)

# UI chrome we may quote verbatim: it is the app's own vocabulary, not user content.
CHROME = re.compile(
    r'^(muet|activer|désactiver|couper|son|audio|vidéo|video|participants?|conversation|chat|'
    r'partager|partage|écran|reactions?|réactions?|applications?|notes|tableau blanc|whiteboard|'
    r'enregistrer|record|quitter|terminer|leave|end|mute|unmute|start|stop|share|more|plus|'
    r'affichage|view|galerie|gallery|intervenant|speaker|inviter|invite|sécurité|security|'
    r'sous-titres|captions|zoom workplace|réunion zoom|zoom meeting|fenêtre|window|ok|annuler|cancel)'
    r'[\s\.\u2026:]*$', re.I)

def classify(s):
    """Return (kept_text_or_None, category). Category is what the cell reports."""
    t = s.strip()
    if not t: return None, 'empty'
    if CHROME.match(t): return t, 'ui-chrome'
    # everything else is potentially user/meeting content -> redact, keep shape only
    digits = sum(c.isdigit() for c in t)
    cat = ('timer' if re.fullmatch(r'[\d:\s]+', t)
           else 'possible-person-or-content')
    return None, cat

def probe(pid, wid_title):
    app = AXUIElementCreateApplication(pid)
    err, wins = AXUIElementCopyAttributeValue(app, 'AXWindows', None)
    if err != 0 or not wins:
        return {'axwindows_err': int(err), 'n_windows': 0}
    target = None
    for w in wins:
        e, t = AXUIElementCopyAttributeValue(w, 'AXTitle', None)
        if e == 0 and t and wid_title.lower() in str(t).lower():
            target = w; break
    if target is None: target = wins[0]

    nodes, roles, cats = [], {}, {}
    def g(el, a):
        e, v = AXUIElementCopyAttributeValue(el, a, None)
        return v if e == 0 else None
    def walk(el, d=0):
        if d > 14 or len(nodes) >= 1500: return
        role = str(g(el, 'AXRole') or '')
        roles[role] = roles.get(role, 0) + 1
        kept, cat = None, 'none'
        for a in ('AXTitle', 'AXValue', 'AXDescription'):
            v = g(el, a)
            if isinstance(v, str) and v.strip():
                kept, cat = classify(v); break
        cats[cat] = cats.get(cat, 0) + 1
        pos, size = g(el, 'AXPosition'), g(el, 'AXSize')
        actions = None
        e, acts = AXUIElementCopyAttributeValue(el, 'AXActions', None) if False else (1, None)
        nodes.append({'d': d, 'role': role, 'sub': str(g(el, 'AXSubrole') or ''),
                      'text': kept, 'cat': cat, 'geom': bool(pos and size)})
        e2, kids = AXUIElementCopyAttributeValue(el, 'AXChildren', None)
        if e2 == 0 and kids:
            for k in kids: walk(k, d + 1)
    walk(target)
    return {'axwindows_err': 0, 'n_windows': len(wins), 'n_nodes': len(nodes),
            'max_depth': max([n['d'] for n in nodes], default=0),
            'roles': roles, 'text_categories': cats,
            'ui_chrome_labels': sorted({n['text'] for n in nodes if n['text']}),
            'redacted_nodes': sum(1 for n in nodes if n['cat'] == 'possible-person-or-content'),
            'nodes_with_geometry': sum(1 for n in nodes if n['geom'])}

def main():
    pid = int(sys.argv[1]); which = sys.argv[2] if len(sys.argv) > 2 else 'Réunion'
    out = {'window_probed': which, 'result': probe(pid, which)}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    tag = 'meeting' if 'unio' in which.lower() else 'workplace'
    with open(os.path.join(OUT, f'zoom-inmeeting-{tag}.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

if __name__ == '__main__':
    main()
