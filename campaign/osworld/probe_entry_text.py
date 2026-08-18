#!/usr/bin/env python3
"""Does OSWorld's payload expose the text a user typed into an entry?

Raised by campaign cell chrome-2ad9387a-B: the bookmark-folder "Name" entry
never showed a `value=`, so the model could not read back its own typing,
retried five times and fell back to pixels twice. Two very different causes:
either the a11y payload does not carry the text (a bridge limit, nothing to
fix) or it does and our adapter drops it (our bug, like the STATE_PRESSED
one). This decides it on the raw XML, not by argument.

Focuses Chrome's omnibox, types a marker, dumps the node's raw attributes
and text, and reports whether the marker appears anywhere in the payload.

Usage: python probe_entry_text.py [--osworld ~/dev/OSWorld]
"""
import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

MARKER = "zqmarker7f3a"
NS_COMP = "https://accessibility.ubuntu.example.org/ns/component"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osworld", default=os.path.expanduser("~/dev/OSWorld"))
    ap.add_argument("--out", default=os.path.expanduser(
        "~/dev/osworld-smoke/entry-text-probe.json"))
    args = ap.parse_args()
    sys.path.insert(0, args.osworld)
    from desktop_env.desktop_env import DesktopEnv

    task = json.load(open(os.path.join(
        args.osworld, "evaluation_examples", "examples", "chrome",
        "030eeff7-b492-4218-b312-701ec99ee0cc.json")))
    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=True)
    env.reset(task_config=task)
    ctrl = env.controller
    rep = {"marker": MARKER}
    try:
        ctrl.execute_python_command(
            "import pyautogui, time; pyautogui.hotkey('ctrl', 'l'); "
            "time.sleep(0.5); "
            f"pyautogui.typewrite({MARKER!r}, interval=0.05)")
        time.sleep(3)
        tree = ctrl.get_accessibility_tree() or ""
        rep["marker_in_payload"] = MARKER in tree
        rep["payload_nodes"] = len(re.findall(r"<[a-zA-Z][^>]*>", tree))
        # every node that mentions the marker, with all its attributes
        hits = []
        for node in ET.fromstring(tree).iter():
            blob = json.dumps(node.attrib) + (node.text or "")
            if MARKER in blob:
                hits.append({
                    "role": node.tag,
                    "name": node.get("name", ""),
                    "text": (node.text or "").strip()[:120],
                    "rect": node.get("{%s}screencoord" % NS_COMP, ""),
                    "attrs_with_marker": [k for k, v in node.attrib.items()
                                          if MARKER in str(v)]})
        rep["nodes_carrying_marker"] = hits
        # what our adapter makes of the same tree
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "d", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "distill-osworld.py"))
        d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(d)
        recs, _, _ = d.distill(tree)
        rep["view_lines_with_marker"] = [r["line"] for r in recs
                                         if MARKER in r["line"]]
        rep["omnibox_lines"] = [r["line"] for r in recs
                                if "address" in (r["label"] or "").lower()]
    finally:
        env.close()
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(rep, open(args.out, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:2500])


if __name__ == "__main__":
    main()
