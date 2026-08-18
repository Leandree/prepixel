#!/usr/bin/env python3
"""Exercise the web channel's ACTION path inside a real OSWorld VM.

The offline acceptance (test_cdp_view.mjs) drives a local headless Chromium,
and the live router check confirmed the VIEW path in the VM — but its one
element action happened to target a browser tab, so it went through AT-SPI
and `cdp_actions` stayed 0. The action path was therefore still unproven
where it actually has to work.

This is deterministic and model-free on purpose: boot the VM for a chrome
task, distil the page, pick a link BY ITS OWN HANDLE, click it through
cdp_act.mjs, and check the page navigated. A model run could not be relied
on to click a page element at all, which is exactly how the gap survived the
first validation.

Run: python3 test_cdp_act_live.py
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/dev/OSWorld"))
TASK = os.path.expanduser(
    "~/dev/OSWorld/evaluation_examples/examples/chrome/"
    "121ba48f-9e17-48ce-9bc6-a4fb17a7ebba.json")

fails = 0


def check(cond, what, detail=""):
    global fails
    print(("  ok   " if cond else "  FAIL ") + what +
          ("" if cond else " — %s" % detail))
    if not cond:
        fails += 1


def cdp(script, *args):
    p = subprocess.run(["node", os.path.join(HERE, script)] + list(args),
                       capture_output=True, text=True, timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "err": "unparseable: %r" % p.stdout[:200]}


def main():
    from desktop_env.desktop_env import DesktopEnv
    os.chdir(os.path.expanduser("~/dev/OSWorld"))
    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=True)
    try:
        env.reset(task_config=json.load(open(TASK)))
        endpoint = "http://localhost:%d" % env.chromium_port
        print("VM up, CDP endpoint", endpoint)

        v = cdp("cdp_view.mjs", "--endpoint", endpoint, "--offset", "70,114")
        check(v.get("ok"), "the web channel reads the page", v.get("error"))
        if not v.get("ok"):
            return
        recs = v["records"]
        url0 = v["meta"]["url"]
        print("  page:", url0, "| records:", len(recs),
              "| offscreen:", v["meta"]["offscreen_emitted"])

        links = [r for r in recs
                 if r["role"] == "link" and r["kind"] == "element"
                 and r.get("label") and r.get("h") is not None]
        check(bool(links), "the page exposes clickable links with handles")
        if not links:
            return

        # A link that navigates, not an in-page anchor.
        target = links[len(links) // 2]
        print("  clicking %r (handle %d)" % (target["label"][:40],
                                             target["h"]))
        r = cdp("cdp_act.mjs", "--endpoint", endpoint,
                "--handle", str(target["h"]), "--op", "click")
        check(r.get("ok"), "cdp_act clicks through the DOM in the VM",
              r.get("err"))
        check(r.get("method") == "Element.click",
              "it used the element's own click, not a synthesised pointer",
              r.get("method"))

        time.sleep(4)
        v2 = cdp("cdp_view.mjs", "--endpoint", endpoint, "--offset", "70,114")
        check(v2.get("ok"), "the page is still readable after the click")
        moved = v2.get("meta", {}).get("url") != url0 or \
            len(v2.get("records", [])) != len(recs)
        check(moved, "the click actually changed the page",
              "url %s -> %s" % (url0, v2.get("meta", {}).get("url")))

        # scroll_to: the action the router gave back to condition B.
        off = [r for r in v2.get("records", [])
               if r["kind"] == "offscreen" and r.get("h") is not None]
        if off:
            s = cdp("cdp_act.mjs", "--endpoint", endpoint,
                    "--handle", str(off[0]["h"]), "--op", "scroll_to")
            check(s.get("ok"), "scroll_to runs in the VM", s.get("err"))
            # Assert what the action PROMISES, not how it keeps it. The first
            # version of this test compared window scrollY and failed while
            # the action had worked: scrollIntoView often scrolls an inner
            # overflow container, leaving window scrollY at 0. What condition
            # B was promised is "the element is on screen now", so that is
            # what gets checked — its post-scroll rect, in viewport
            # coordinates, must intersect the viewport.
            vh = v2["meta"]["viewport"][1]
            rect = s.get("rect") or [0, -9999, 0, 0]
            on = rect[1] + rect[3] > 0 and rect[1] < vh
            check(on, "scroll_to put the element on screen",
                  "rect=%s viewport height=%s" % (rect, vh))
            # And it must now be an on-screen record, not an offscreen one.
            v3 = cdp("cdp_view.mjs", "--endpoint", endpoint,
                     "--offset", "70,114")
            n_off_after = v3.get("meta", {}).get("offscreen_emitted", -1)
            print("  offscreen records: %d before -> %d after"
                  % (v2["meta"]["offscreen_emitted"], n_off_after))
        else:
            print("  note no offscreen element on this page to scroll to")

        # A handle from a stale view must refuse rather than hit something.
        bad = cdp("cdp_act.mjs", "--endpoint", endpoint,
                  "--handle", "999999", "--op", "click")
        check(not bad.get("ok") and "stale-handle" in str(bad.get("err")),
              "an out-of-range handle refuses instead of acting",
              json.dumps(bad))
    finally:
        try:
            env.close()
        except Exception:
            pass
    print("\n%s" % ("%d FAILURES" % fails if fails else "ALL PASS"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
