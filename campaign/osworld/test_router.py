#!/usr/bin/env python3
"""Unit test for the per-window router's signature step (P1).

`_chromium_content_rect` reads namespaced AT-SPI attributes. A wrong
namespace or attribute name does not raise — it just returns None forever,
and the router then declines on every step while the code reads as if the
web channel were wired. That failure is silent in the results and expensive
in an iteration, so it gets a test that does not need a VM.

Run: python3 test_router.py
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("rc", "run_condition.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

S = "https://accessibility.ubuntu.example.org/ns/state"
C = "https://accessibility.ubuntu.example.org/ns/component"


def node(tag, x, y, w, h, showing="true", visible="true", extra=""):
    return (f'<{tag} xmlns:st="{S}" xmlns:cp="{C}" '
            f'st:showing="{showing}" st:visible="{visible}" '
            f'cp:screencoord="({x}, {y})" cp:size="({w}, {h})" {extra}/>')


def tree(apps):
    return (f'<desktop-frame xmlns:st="{S}" xmlns:cp="{C}">'
            + "".join(apps) + "</desktop-frame>")


def app(name, inner):
    return f'<application name="{name}">{inner}</application>'


fails = 0


def check(cond, what, detail=""):
    global fails
    if cond:
        print("  ok   %s" % what)
    else:
        fails += 1
        print("  FAIL %s%s" % (what, (" — " + str(detail)) if detail else ""))


print("router signature:")

# The normal case: a Chromium window with a web document below the toolbar.
t = tree([app("Chromium", node("document-web", 0, 121, 1920, 959))])
rect, why = rc._chromium_content_rect(t)
check(rect == (0, 121, 1920, 959), "finds the content rect of a Chromium",
      (rect, why))

# Google Chrome is the other name the same browser ships under.
t = tree([app("Google Chrome", node("document-frame", 0, 121, 1920, 959))])
rect, _ = rc._chromium_content_rect(t)
check(rect == (0, 121, 1920, 959), "recognises Google Chrome too")

# Not a browser: the router must decline, with a reason.
t = tree([app("libreoffice-calc", node("document-spreadsheet", 0, 0, 800, 600))])
rect, why = rc._chromium_content_rect(t)
check(rect is None and "no chromium" in why,
      "declines on a non-browser window, with a reason", why)

# A Chromium that is present but has no visible document (minimised tab
# strip, devtools-only window): decline rather than route into nothing.
t = tree([app("Chromium", node("document-web", 0, 121, 1920, 959,
                               showing="false"))])
rect, why = rc._chromium_content_rect(t)
check(rect is None and "no on-screen web document" in why,
      "declines when the web document is not showing", why)

# Off-screen document (window scrolled off the desktop): also declines.
t = tree([app("Chromium", node("document-web", 3000, 121, 800, 600))])
rect, why = rc._chromium_content_rect(t)
check(rect is None, "declines when the document is off the viewport", why)

# Two windows: the LARGEST on-screen document wins — the small one is a
# popup or a devtools pane, not the content the user is looking at.
t = tree([app("Chromium",
              node("document-web", 0, 121, 1920, 959)
              + node("document-web", 10, 200, 300, 200))])
rect, _ = rc._chromium_content_rect(t)
check(rect == (0, 121, 1920, 959), "picks the largest on-screen document")

# Malformed payload must not take the driver down.
rect, why = rc._chromium_content_rect("<not-xml")
check(rect is None and "tree-parse" in why, "survives an unparseable tree", why)
rect, why = rc._chromium_content_rect("")
check(rect is None, "survives an empty tree", why)

print("\ngeometric composition:")
box = (0, 121, 1920, 959)
check(rc._inside([100, 300, 50, 20], box),
      "a page element is replaced by the web channel")
check(not rc._inside([100, 60, 50, 20], box),
      "a toolbar element stays on AT-SPI")
# This is the assertion the first version of this test dodged with `or True`.
# The Chromium window frame is CENTRED inside its own content rect, so a
# centre test swallowed it — taking the window title with it. Containment is
# what makes the frame survive, and the test now says so.
check(not rc._inside([0, 0, 1920, 1080], box),
      "the window frame is NOT swallowed (it is larger than the content)")
check(not rc._inside([0, 90, 1920, 30], box),
      "the tab strip is not swallowed by the content rect")
check(not rc._inside([0, 100, 400, 60], box),
      "an element straddling the boundary stays on AT-SPI")

print("\n%s" % ("%d FAILURES" % fails if fails else "ALL PASS"))
sys.exit(1 if fails else 0)
