# -*- coding: utf-8 -*-
"""Cell: windows-swing-java-access-bridge (DEEPENING-PLAN P2: the Java tier).

Portable JDK (no admin), throwaway Swing app. Three questions:
  (1) what does UIA see of a Swing window? (expected: near-empty frame)
  (2) does coverage-guard convert that blind spot to explicit?
  (3) does the JAB channel (jabswitch -enable + WindowsAccessBridge-64.dll)
      expose the real tree, and is it detectable a priori?
"""
import ctypes, glob, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, print_window, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)
from guard import (spot_check, empty_big_regions, structural_coverage,
                   synthesize_client_suspect)

out = {"cell": "windows-swing-jab"}
JDK = glob.glob(os.path.join(os.environ["TEMP"], "ptap-jdk", "*", "bin"))[0]
out["jdk"] = JDK

# enable the Access Bridge BEFORE the app starts (per-user, no admin)
r = subprocess.run([os.path.join(JDK, "jabswitch.exe"), "-enable"],
                   capture_output=True, text=True)
out["jabswitch"] = (r.stdout + r.stderr).strip()[:120]

# compile + launch the probe app
src = os.path.join(os.path.dirname(__file__), "SwingProbe.java")
subprocess.run([os.path.join(JDK, "javac.exe"), "-d", os.environ["TEMP"], src],
               check=True, capture_output=True)
app = subprocess.Popen([os.path.join(JDK, "java.exe"),
                        "-Djavax.accessibility.assistive_technologies=com.sun.java.accessibility.AccessBridge",
                        "-cp", os.environ["TEMP"], "SwingProbe"],
                       stderr=subprocess.PIPE, text=True)
time.sleep(8)

win = auto.WindowControl(searchDepth=1, Name="pipeline-tap Swing probe")
if not win.Exists(15):
    print(json.dumps({"error": "swing window not found", **out})); sys.exit(1)
wrect = rect_of(win)
out["window_rect"] = wrect
hwnd = win.NativeWindowHandle
out["window_class"] = win.ClassName

# ---- (1) the UIA shape ------------------------------------------------------
view, stats, attempts = probe_with_latch(lambda: win, settle=1.0, retries=3)
out["uia"] = {"latch_attempts": attempts, "nodes": stats["nodes"],
              "types": stats.get("types", {}),
              "view_tokens": text_tokens(view),
              "sentinel_visible": "SWING-TAP-SENTINEL" in view}
save_artifact("swing-uia-view.txt", view)

# ---- (2) coverage-guard on the Swing window --------------------------------
nodes = []
for c, d in walk(win, max_depth=20, max_nodes=3000):
    if c is None: break
    try:
        r_ = c.BoundingRectangle
        nodes.append({"t": c.ControlTypeName, "n": (c.Name or "")[:60],
                      "cls": (c.ClassName or "")[:40],
                      "r": [r_.left, r_.top, r_.right - r_.left, r_.bottom - r_.top],
                      "d": d})
    except Exception:
        continue
img = print_window(hwnd, os.path.join(os.path.dirname(__file__), "..", "results",
                                      "artifacts", "windows", "swing-uia-shot.png"))
cov = structural_coverage(nodes, wrect)
guard = {"coverage_pct": round(cov * 100, 1)}
if img:
    suspects = empty_big_regions(nodes, min_area=50000)
    synth = synthesize_client_suspect(wrect, cov)
    if not suspects and synth:
        suspects = [synth]
        guard["synthesized"] = True
    checked = spot_check(img, wrect, suspects)
    for i, c in enumerate(checked):
        if c.get("verdict") == "SILENT->declare-opaque" and "crop" in c:
            c["crop"].convert("RGB").save(os.path.join(
                os.path.dirname(__file__), "..", "results", "artifacts", "windows",
                f"guard-swing-region{i}.png"))
        c.pop("crop", None)
    guard["suspects"] = checked
out["guard"] = guard

# ---- (3) the JAB channel ----------------------------------------------------
dll = os.path.join(JDK, "windowsaccessbridge-64.dll")
if not os.path.exists(dll):
    cand = glob.glob(os.path.join(JDK, "*ccess*ridge*64*.dll"))
    dll = cand[0] if cand else None
out["jab_dll"] = dll
if dll:
    r = subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(__file__), "jab_client.py"),
                        dll, str(hwnd)],
                       capture_output=True, text=True, timeout=90)
    try:
        jab = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        jab = {"error": (r.stderr or r.stdout)[-400:]}
    if "nodes" in jab:
        save_artifact("swing-jab-tree.json", json.dumps(jab["nodes"], ensure_ascii=False, indent=1))
        jab_summary = {k: v for k, v in jab.items() if k != "nodes"}
        jab_summary["sentinel_via_jab"] = any("SWING-TAP-SENTINEL" in (n.get("name") or "")
                                              for n in jab["nodes"])
        jab_summary["field_value_seen"] = any("initial" in (n.get("name") or "")
                                              for n in jab["nodes"])
        jab_summary["roles_sample"] = sorted({n["role"] for n in jab["nodes"]})[:12]
        out["jab"] = jab_summary
    else:
        out["jab"] = jab

app.terminate()
save_artifact("swing-jab-report.json", json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
