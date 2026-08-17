#!/usr/bin/env python3
"""Driver v2 acceptance suite (DRIVER-V2-SPEC.md §4.2) — sandbox, OUTSIDE any
counted run, no model in the loop: the script itself plays the scenarios and
records what the driver's mechanics produced.

Scenarios (spec §4.2):
  a  corner-miss replay (os-B step 5: click at the exact rect corner + typing)
     -> act-guard v2 must return UNVERIFIED, and report the re-read state.
  a2 positive control on the SAME element: the v2 set_value action must return
     CONFIRMED with the value transition (this is the fault v1 exposed).
  b  toggle: the state must be visible in the view BEFORE and AFTER.
  c  long page: [offscreen] emission + scroll_to.
  d  Chrome settings search: settle must absorb the lazy population, so the
     model would never need WAIT.
  e  action on a static label -> UNVERIFIED.

Two VM boots: --scenario os (a, a2, b, e) and --scenario chrome (b-DNT, c, d).
Writes <out>/acceptance-<scenario>.json.

Usage:
  python acceptance_v2.py --scenario os     --out ../results/osworld-pilot-v2/acceptance
  python acceptance_v2.py --scenario chrome --out ../results/osworld-pilot-v2/acceptance
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "run_condition", os.path.join(HERE, "run_condition.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

OS_TASK = ("os", "13584542-872b-42d8-b299-866967b5c3ef")
CHROME_TASK = ("chrome", "030eeff7-b492-4218-b312-701ec99ee0cc")


class Probe:
    """Thin harness around the driver: no model, scripted scenarios."""

    def __init__(self, drv, out):
        self.drv = drv
        self.out = out
        self.n = 0
        self.registry = {}

    def refresh(self, settle=True):
        self.n += 1
        mech = {}
        if settle:
            self.drv.cur_tree = self.drv.settle(mech)
        else:
            self.drv.cur_tree = self.drv.ctrl.get_accessibility_tree()
        shot = os.path.join(self.out, f"probe-{self.n}.png")
        open(shot, "wb").write(self.drv.ctrl.get_screenshot() or b"")
        view, registry, raw, ns, nh = self.drv.build_view(self.out, shot, mech)
        self.registry = registry
        self.drv.prev_diff_base = raw     # baseline the keyboard guard uses
        open(os.path.join(self.out, f"probe-{self.n}.txt"), "w").write(view)
        return view, registry, mech

    def find(self, pred):
        for eid, rec in self.registry.items():
            if pred(rec):
                return eid, rec
        return None, None

    def act(self, action):
        mech = {}
        hist, verdict, needs_settle, before = self.drv.execute(
            action, self.registry, mech)
        if needs_settle:
            self.drv.cur_tree = self.drv.settle(mech)
            if verdict is None and before is not None:
                verdict = self.drv.scoped_guard(before, mech)
        return {"action": action, "history": hist, "verdict": verdict,
                "mech": mech}


def vm_python(drv, command):
    """Run a python one-liner in the VM. NOT run_bash_script: the server
    baked into the VM image answers /run_bash_script with
    "name '_append_event' is not defined" (image/server version skew,
    measured 2026-08-17); /execute is the endpoint OSWorld itself uses."""
    return drv.ctrl.execute_python_command(command)


def raw_evidence(tree_xml):
    """How many nodes the payload hides entirely (no coords at all) — decides
    whether §2.6 [offscreen] is even expressible from OSWorld's a11y dump."""
    total = len(re.findall(r"<[a-zA-Z][^>]*>", tree_xml or ""))
    with_coord = len(re.findall(r"screencoord=", tree_xml or ""))
    showing_true = len(re.findall(r'showing="true"', tree_xml or ""))
    return {"nodes": total, "nodes_with_coords": with_coord,
            "nodes_showing_true": showing_true,
            "nodes_without_coords": total - with_coord}


def scenario_os(env, drv, probe, rep):
    # Open the exact dialog of the v1 failure, mechanically (no model).
    vm_python(drv, "import subprocess; "
                   "subprocess.Popen(['gnome-terminal', '--preferences'])")
    time.sleep(6)
    view, registry, _ = probe.refresh()

    # the columns spin-button lives on the profile page, not on General:
    # navigate there with a v2 action (this also exercises the ladder on a
    # list-item)
    eid, prof = probe.find(
        lambda r: r["role"] == "list-item"
        and r["label"] not in ("General", "Shortcuts") and r["label"])
    if eid:
        rep["nav_profile"] = probe.act({"action": "click", "target": eid})
        time.sleep(1)
        view, registry, _ = probe.refresh()

    # the columns spin-button = the spin-button just left of the "columns" text
    _, col_txt = probe.find(lambda r: r["kind"] == "text"
                            and r["label"].strip().lower() == "columns")
    spin_eid = spin_rec = None
    if col_txt:
        cy = col_txt["rect"][1]
        for eid, rec in registry.items():
            if rec["role"] == "spin-button" and abs(rec["rect"][1] - cy) < 8 \
                    and rec["rect"][0] < col_txt["rect"][0]:
                spin_eid, spin_rec = eid, rec
                break
    rep["dialog_found"] = bool(spin_rec)
    if not spin_rec:
        rep["error"] = "columns spin-button not found; view saved"
        return

    rep["a_target"] = spin_rec["line"]

    # (a) v1 replay: raw pointer at the EXACT rect corner + typing, then the
    # v2 scoped guard on that element.
    x, y, w, h = spin_rec["rect"]
    before = dict(spin_rec)
    mech = {}
    drv._pyautogui(
        f"import pyautogui, time; pyautogui.click({x}, {y}); time.sleep(0.3); "
        f"pyautogui.hotkey('ctrl', 'a'); pyautogui.typewrite('132'); "
        f"pyautogui.press('enter')")
    drv.cur_tree = drv.settle(mech)
    rep["a_corner_miss"] = {"clicked": [x, y],
                            "verdict": drv.scoped_guard(before, mech)}

    # (a2) positive control: the v2 action on the same element
    view, registry, _ = probe.refresh()
    _, spin_rec2 = probe.find(lambda r: r["role"] == "spin-button"
                              and r["rect"][:2] == spin_rec["rect"][:2])
    eid2 = next((e for e, r in probe.registry.items()
                 if r["rect"][:2] == spin_rec["rect"][:2]
                 and r["role"] == "spin-button"), None)
    rep["a2_before"] = spin_rec2["line"] if spin_rec2 else None
    if eid2:
        rep["a2_set_value"] = probe.act(
            {"action": "set_value", "target": eid2, "value": "132"})
        probe.refresh()
        _, after = probe.find(lambda r: r["role"] == "spin-button"
                              and r["rect"][:2] == spin_rec["rect"][:2])
        rep["a2_after"] = after["line"] if after else None
        # restore (mechanical cleanup, nothing is evaluated here)
        eid3 = next((e for e, r in probe.registry.items()
                     if r["rect"][:2] == spin_rec["rect"][:2]
                     and r["role"] == "spin-button"), None)
        if eid3:
            probe.act({"action": "set_value", "target": eid3, "value": "80"})

    # (e) static label actioned
    view, registry, _ = probe.refresh()
    eid, lab = probe.find(lambda r: r["kind"] == "text" and r["label"].strip()
                          in ("columns", "rows"))
    if eid:
        rep["e_static_label"] = probe.act({"action": "click", "target": eid})
        rep["e_target"] = lab["line"]

    # (b) toggle / check-box: state before and after, then restore
    view, registry, _ = probe.refresh()
    eid, tog = probe.find(lambda r: r["role"] in ("check-box", "toggle-button")
                          and r["label"] and "checked" in r["states"]
                          and r["rect"][1] > rc.TOPBAR_Y)
    if eid:
        want = not tog["states"]["checked"]
        rep["b_before"] = tog["line"]
        rep["b_toggle"] = probe.act({"action": "toggle", "target": eid,
                                     "to": want})
        probe.refresh()
        _, after = probe.find(lambda r: r["role"] == tog["role"]
                              and r["label"] == tog["label"])
        rep["b_after"] = after["line"] if after else None
        eid2 = next((e for e, r in probe.registry.items()
                     if r["role"] == tog["role"] and r["label"] == tog["label"]),
                    None)
        if eid2:
            probe.act({"action": "toggle", "target": eid2,
                       "to": tog["states"]["checked"]})


def navigate(probe, url):
    """ctrl+l, type, kill the inline autocompletion, Enter.

    The `delete` is not politeness: measured on this VM, typing
    "chrome://settings/" leaves Chrome's inline completion pointing at
    google.com/chrome, and Enter follows the completion instead of the typed
    URL — in BOTH the v1 single-command shape and the v2 separate-action
    shape (see acceptance-nav.json). Same UX trap in both conditions."""
    probe.act({"action": "key", "keys": "ctrl+l"})
    probe.act({"action": "type", "text": url})
    probe.act({"action": "key", "keys": "delete"})
    probe.act({"action": "key", "keys": "enter"})
    time.sleep(3)


def scenario_chrome(env, drv, probe, rep):
    # (d) settle vs lazy population: navigate to settings, search, and see
    # whether the SETTLED view already exposes the results.
    navigate(probe, "chrome://settings/")
    view, registry, _ = probe.refresh()
    rep["settings_lines"] = len(view.split("\n"))
    doc = next((r for r in registry.values()
                if r["role"] in ("document-web", "document-frame")), None)
    rep["settings_document"] = doc["label"] if doc else None

    eid, box = probe.find(lambda r: r["role"] in ("entry", "text", "searchbox")
                          and "search" in (r["label"] or "").lower()
                          and "address" not in (r["label"] or "").lower())
    rep["d_searchbox"] = box["line"] if box else None
    if eid:
        rep["d_click"] = probe.act({"action": "click", "target": eid})
        rep["d_type"] = probe.act({"action": "type", "text": "do not track"})
        view, registry, mech = probe.refresh()      # settled view
        rep["d_settle"] = {"settle_ms": mech.get("settle_ms"),
                           "captures": mech.get("settle_captures"),
                           "reprobes": mech.get("reprobes", 0)}
        rep["d_selfinconsistent"] = [l for l in view.split("\n")
                                     if "self-inconsistent" in l]
        rep["d_result_lines"] = [l for l in view.split("\n")
                                 if "track" in l.lower()][:12]

    # (b-DNT) the v1 chrome fault: toggle with its state exposed
    eid, tog = probe.find(lambda r: r["role"] in ("toggle-button", "check-box")
                          and "track" in (r["label"] or "").lower())
    rep["b_dnt_before"] = tog["line"] if tog else None
    if eid:
        want = not tog["states"].get("checked", False)
        rep["b_dnt_toggle"] = probe.act({"action": "toggle", "target": eid,
                                         "to": want})
        probe.refresh()
        _, after = probe.find(lambda r: r["label"] == tog["label"]
                              and r["role"] == tog["role"])
        rep["b_dnt_after"] = after["line"] if after else None
        eid2 = next((e for e, r in probe.registry.items()
                     if r["label"] == tog["label"] and r["role"] == tog["role"]),
                    None)
        if eid2:                      # restore
            probe.act({"action": "toggle", "target": eid2,
                       "to": tog["states"].get("checked", False)})

    # (c) offscreen + scroll_to on a deliberately long local page
    vm_python(drv,
              "open('/tmp/longpage.html', 'w').write('<html><body>' + "
              "''.join('<p>filler paragraph %d</p>' % i for i in range(400))"
              " + '<a href=#>Advanced settings marker</a></body></html>')")
    navigate(probe, "file:///tmp/longpage.html")
    view, registry, _ = probe.refresh()
    off = [(e, r) for e, r in registry.items() if r["kind"] == "offscreen"]
    rep["c_offscreen_count"] = len(off)
    rep["c_offscreen_sample"] = [r["line"] for _, r in off[:5]]
    rep["c_raw_evidence"] = raw_evidence(drv.cur_tree)
    marker = [(e, r) for e, r in registry.items()
              if "Advanced settings marker" in (r["label"] or "")]
    rep["c_marker_in_view"] = [r["line"] for _, r in marker]
    tgt = (off[-1] if off else (marker[0] if marker else None))
    if tgt:
        rep["c_scroll_to"] = probe.act({"action": "scroll_to",
                                        "target": tgt[0]})
        probe.refresh()
    else:
        rep["c_scroll_to"] = "NOT EXERCISABLE: no [offscreen] node emitted " \
            "(see c_raw_evidence: the OSWorld a11y payload only carries " \
            "coordinates for showing+visible nodes)"


def scenario_nav(env, drv, probe, rep):
    """Does the settle between keystrokes break omnibox entry?

    v1's model typed hotkey+write+press inside ONE pyautogui command and
    navigated fine. v2's schema is one primitive per step, so ~4 s of a11y
    polling now sits between the typing and the Enter. If that polling
    perturbs Chrome's omnibox, condition B loses URL entry — a driver-level
    problem, not a harness detail. Three variants, same target:
      1. all three in one pyautogui command (the v1 shape)
      2. separate driver actions WITH the settle between them (the v2 shape)
      3. separate driver actions with NO settle between them
    """
    def page():
        drv.cur_tree = drv.ctrl.get_accessibility_tree()
        recs, _, _ = drv.distill(drv.cur_tree)
        doc = next((r for r in recs if r["role"] in
                    ("document-web", "document-frame")), None)
        return doc["label"] if doc else "(no document node)"

    url = "chrome://settings/"
    rep["nav_start"] = page()

    drv._pyautogui("import pyautogui, time; pyautogui.hotkey('ctrl', 'l'); "
                   "time.sleep(0.3); "
                   f"pyautogui.write({url!r}, interval=0.02); "
                   "pyautogui.press('enter')")
    time.sleep(4)
    rep["nav_1_single_command"] = page()

    probe.act({"action": "key", "keys": "ctrl+l"})       # settles internally
    probe.act({"action": "type", "text": "chrome://version/"})
    probe.act({"action": "key", "keys": "enter"})
    time.sleep(4)
    rep["nav_2_separate_with_settle"] = page()

    drv._pyautogui("import pyautogui; pyautogui.hotkey('ctrl', 'l')")
    time.sleep(0.3)
    drv._pyautogui("import pyautogui; "
                   "pyautogui.typewrite('chrome://history/', interval=0.02)")
    time.sleep(0.3)
    drv._pyautogui("import pyautogui; pyautogui.press('enter')")
    time.sleep(4)
    rep["nav_3_separate_no_settle"] = page()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    choices=["os", "chrome", "nav"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--osworld", default=os.path.expanduser("~/dev/OSWorld"))
    args = ap.parse_args()

    sys.path.insert(0, args.osworld)
    from desktop_env.desktop_env import DesktopEnv

    domain, task_id = OS_TASK if args.scenario == "os" else CHROME_TASK
    task = json.load(open(os.path.join(
        args.osworld, "evaluation_examples", "examples", domain,
        f"{task_id}.json")))
    out = os.path.join(args.out, args.scenario)
    os.makedirs(out, exist_ok=True)

    env = DesktopEnv(provider_name="docker", os_type="Ubuntu",
                     action_space="pyautogui", headless=True,
                     require_a11y_tree=True)
    obs = env.reset(task_config=task)
    drv = rc.Driver(env, "B", out)
    drv.probe_platform()
    drv.cur_tree = obs.get("accessibility_tree") or ""
    probe = Probe(drv, out)

    rep = {"scenario": args.scenario, "task": f"{domain}/{task_id}",
           "driver": "v2", "platform_rung_available": drv.platform_available,
           "platform_probe": drv.mech_total.get("platform_probe")}
    try:
        if args.scenario == "os":
            scenario_os(env, drv, probe, rep)
        elif args.scenario == "nav":
            scenario_nav(env, drv, probe, rep)
        else:
            scenario_chrome(env, drv, probe, rep)
    except Exception as e:
        import traceback
        rep["exception"] = traceback.format_exc()[-2000:]
    finally:
        rep["mechanics"] = drv.mech_total
        json.dump(rep, open(os.path.join(
            args.out, f"acceptance-{args.scenario}.json"), "w"), indent=1)
        env.close()
    print(json.dumps(rep, indent=1)[:4000])


if __name__ == "__main__":
    main()
