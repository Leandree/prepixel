# -*- coding: utf-8 -*-
"""act-guard — the missing half of coverage-guard.

`src/coverage-guard.mjs` protects the READ side: it catches a view that omits
what the screen shows. Nothing protected the ACT side, and the macOS Swing cell
found why that matters: `AXUIElementPerformAction(button, 'AXPress')` returns
**0 — success** on a Java button while the application never sees the press. An
agent that trusts the return code proceeds believing the world changed.

The contract is channel-agnostic (it applies equally to UIA `Invoke()`, AT-SPI
`do_action`, and CDP `Input.dispatchMouseEvent`):

    pre  = read_state(target)          # cheap, structured
    err  = perform(action)
    if err != 0:      -> EXPLICIT_FAILURE   (the channel said no; believe it)
    post = read_state(target)
    if post == pre:   -> UNVERIFIED         (it said yes and nothing moved)
    else:             -> CONFIRMED

Two design points learned from the read-side guard:

  * `read_state` must be scoped to the region the action was supposed to affect,
    not the whole window — otherwise unrelated churn (a clock, a cursor blink)
    reports a change that never happened where it mattered.
  * A structured re-read is the cheap path; falling back to per-window pixel
    energy is the expensive one, and is only needed when the structured channel
    cannot see the affected region at all — which is exactly the case where the
    read-side guard has already declared the region opaque.

Usage: act_guard.py <pid> <button-AXDescription> <state-prefix>
"""
import json, os, sys, time

from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
                                 AXUIElementCopyActionNames, AXUIElementPerformAction,
                                 AXUIElementSetAttributeValue)

def tok(s): return (len(s) + 3) // 4

def g(el, a):
    er, v = AXUIElementCopyAttributeValue(el, a, None)
    return v if er == 0 else None

def descend(el, out=None):
    out = [] if out is None else out
    out.append(el)
    er, kids = AXUIElementCopyAttributeValue(el, 'AXChildren', None)
    if er == 0 and kids:
        for k in kids: descend(k, out)
    return out

def read_state(elements):
    """The scoped structured re-read. Serialised exactly as a router would send
    it upward, so its token cost is the guard's real price."""
    parts = []
    for el in elements:
        role = str(g(el, 'AXRole') or '')
        val = g(el, 'AXValue')
        if isinstance(val, str) and val.strip():
            parts.append(f'{role} "{val.strip()}"')
    return '\n'.join(parts)

def guarded_act(app, button, state_elements, action='AXPress'):
    er, acts = AXUIElementCopyActionNames(button, None)
    declared = list(acts) if er == 0 and acts else []

    pre = read_state(state_elements)
    t0 = time.time()
    err = AXUIElementPerformAction(button, action)
    time.sleep(0.5)                      # let the app repaint
    post = read_state(state_elements)
    ms = (time.time() - t0) * 1000

    if err != 0:
        verdict, note = 'EXPLICIT_FAILURE', f'channel refused with err {err} — believe it'
    elif post == pre:
        verdict, note = 'UNVERIFIED', 'action reported success and NOTHING changed in the target region'
    else:
        verdict, note = 'CONFIRMED', 'state changed as expected'
    return {
        'declared_actions': declared,
        'perform_err': int(err),
        'state_before': pre[:120],
        'state_after': post[:120],
        'verdict': verdict,
        'note': note,
        'reread_tokens': tok(post),
        'roundtrip_ms': round(ms, 1),
    }

def main():
    pid = int(sys.argv[1]); btn_desc = sys.argv[2]
    app = AXUIElementCreateApplication(pid)
    AXUIElementSetAttributeValue(app, 'AXFrontmost', True); time.sleep(0.8)
    er, wins = AXUIElementCopyAttributeValue(app, 'AXWindows', None)
    els = descend(wins[0])
    btn = [e for e in els if str(g(e, 'AXDescription') or '') == btn_desc
           or str(g(e, 'AXTitle') or '') == btn_desc]
    if not btn:
        print(json.dumps({'error': f'no control matching {btn_desc!r}'})); return
    # the state region: every static text in the window (scoped, cheap)
    state = [e for e in els if str(g(e, 'AXRole') or '') == 'AXStaticText']
    out = guarded_act(app, btn[0], state)
    out['target'] = btn_desc
    print(json.dumps(out, indent=1, ensure_ascii=False))

if __name__ == '__main__':
    main()
