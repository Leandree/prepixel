# -*- coding: utf-8 -*-
"""P0 — Prove the mitigation ON the real silent apps (DEEPENING-PLAN).

For each of OBS / FL Studio / rekordbox (READ-ONLY, user's real config):
  (1) structural-coverage %% of the client area,
  (2) PrintWindow(PW_RENDERFULLCONTENT) crops of every structure-empty big
      region -> content-energy (Guard A),
  (3) self-consistency on the distilled view (Guard B).
Acceptance: every silent region re-emitted as an EXPLICIT [pixels]/[inconsistent]
line, with energies, costs and the a-priori signature.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)
from guard import (content_energy, self_consistency, spot_check,
                   structural_coverage, empty_big_regions)

ART = os.path.join(os.path.dirname(__file__), "..", "results", "artifacts", "windows")
report = {}


def raw_walk(win):
    nodes = []
    for c, d in walk(win, max_depth=30, max_nodes=20000):
        if c is None:
            break
        try:
            r = c.BoundingRectangle
            nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:60],
                          "cls": (c.ClassName or "")[:40],
                          "r": [r.left, r.top, r.right - r.left, r.bottom - r.top],
                          "d": d})
        except Exception:
            continue
    return nodes


def run_guards(app_key, win):
    wrect = rect_of(win)
    t0 = time.perf_counter()
    view, _ = distill(win)
    nodes = raw_walk(win)
    walk_ms = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter()
    img = print_window(win.NativeWindowHandle)
    pw_ms = round((time.perf_counter() - t0) * 1000, 1)
    if img is None:
        return {"error": "PrintWindow failed"}
    cov = structural_coverage(nodes, wrect)
    suspects = empty_big_regions(nodes)
    t0 = time.perf_counter()
    checked = spot_check(img, wrect, suspects)
    guard_ms = round((time.perf_counter() - t0) * 1000, 1)
    flags_b = self_consistency(view)
    # persist crops of flagged regions as evidence
    for i, c in enumerate(checked):
        if c.get("verdict") == "SILENT->declare-opaque" and "crop" in c:
            c["crop"].convert("RGB").save(os.path.join(ART, f"guard-{app_key}-region{i}.png"))
            c["crop_artifact"] = f"guard-{app_key}-region{i}.png"
        c.pop("crop", None)
    crop_px = sum(c["rect"][2] * c["rect"][3] for c in checked if "energy" in c)
    return {
        "window_rect": wrect,
        "structural_coverage_pct": round(cov * 100, 1),
        "suspects_checked": len([c for c in checked if "energy" in c]),
        "guard_a": checked,
        "guard_b_flags": flags_b,
        "walk_ms": walk_ms, "printwindow_ms": pw_ms, "guard_ms": guard_ms,
        "crop_cost_tokens": -(-crop_px // 750),
        "full_screenshot_tokens": image_tokens(wrect[2], wrect[3]),
        "explicit_lines": [c["line"] for c in checked if c.get("line")] +
                          [f["line"] for f in flags_b],
    }


# ---------- OBS --------------------------------------------------------------
try:
    OBS_DIR = r"C:\Program Files\obs-studio\bin\64bit"
    proc = subprocess.Popen([os.path.join(OBS_DIR, "obs64.exe"), "--disable-updater"], cwd=OBS_DIR)
    time.sleep(12)
    win = auto.WindowControl(searchDepth=1, RegexName="OBS .*")
    if win.Exists(15):
        report["obs"] = run_guards("obs", win)
        win.GetPattern(auto.PatternId.WindowPattern).Close()
        time.sleep(2)
    else:
        report["obs"] = {"error": "window not found"}
except Exception as e:
    report["obs"] = {"error": str(e)[:200]}

# ---------- FL Studio --------------------------------------------------------
try:
    FL = r"C:\Program Files\Image-Line\FL Studio 2025\FL64.exe"
    proc = subprocess.Popen([FL])
    win = None
    for i in range(30):
        time.sleep(3)
        w = auto.WindowControl(searchDepth=1, RegexName=".*FL Studio.*")
        if w.Exists(1):
            win = w
            break
    if win:
        time.sleep(10)
        report["flstudio"] = run_guards("flstudio", win)
        ctypes.windll.user32.PostMessageW(win.NativeWindowHandle, 0x0010, 0, 0)
        time.sleep(4)
        dlg = auto.WindowControl(searchDepth=1, RegexName=".*FL Studio.*")
        if dlg.Exists(2):
            for name in ("Non", "No", "Don't save", "Ne pas enregistrer", "Discard"):
                b = dlg.ButtonControl(searchDepth=8, Name=name)
                if b.Exists(1):
                    try:
                        b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                    except Exception:
                        pass
                    break
    else:
        report["flstudio"] = {"error": "window not found"}
except Exception as e:
    report["flstudio"] = {"error": str(e)[:200]}

# ---------- rekordbox --------------------------------------------------------
try:
    RB = r"C:\Program Files\rekordbox\rekordbox 7.0.9\rekordbox.exe"
    proc = subprocess.Popen([RB], cwd=os.path.dirname(RB))
    main = None
    deadline = time.time() + 240
    while time.time() < deadline:
        time.sleep(3)
        for w in auto.GetRootControl().GetChildren():
            try:
                n = (w.Name or "")
            except Exception:
                continue
            if "Upmgr" in n:
                try:
                    b = w.ButtonControl(searchDepth=6, Name="Fermer")
                    if b.Exists(1):
                        b.GetPattern(auto.PatternId.InvokePattern).Invoke()
                except Exception:
                    pass
            elif "rekordbox" in n.lower():
                main = w
        if main is not None:
            break
    if main:
        time.sleep(15)
        main = auto.WindowControl(searchDepth=1, RegexName=".*rekordbox.*")
        report["rekordbox"] = run_guards("rekordbox", main)
        ctypes.windll.user32.PostMessageW(main.NativeWindowHandle, 0x0010, 0, 0)
        time.sleep(5)
    else:
        report["rekordbox"] = {"error": "window not found"}
except Exception as e:
    report["rekordbox"] = {"error": str(e)[:200]}

save_artifact("windows-mitigation-report.json", json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps(report, ensure_ascii=False, indent=1))
