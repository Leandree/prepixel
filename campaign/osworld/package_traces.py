#!/usr/bin/env python3
"""Package run traces for manager review: copy a run directory into the repo,
JPEG-compress the screenshots, and build the per-run README section.

Screenshots are recompressed (JPEG q55) because the repo must stay clonable;
the PNG the agent actually received is the one in the working directory, and
the JPEG is a faithful-enough visual record of the same frame. Everything the
verdicts depend on (view.txt, prompt.txt, action.json, mechanics.json,
result.json) is copied byte-for-byte.

Usage:
  python package_traces.py --runs <src-dir> --dest <repo-dir> --label v2
"""
import argparse
import json
import os
import shutil

from PIL import Image


def copy_pixels(src, dst):
    """Screenshots live outside the step directories since ruling D1: A's in
    _pixels/step-N/ (alone, because the prompt names them), the coverage
    guard's in _guard/. Both are packaged as JPEG next to their step."""
    for sub, pat in (("_pixels", "step-{}/screenshot.png"),
                     ("_guard", "step-{}.png")):
        base = os.path.join(src, sub)
        if not os.path.isdir(base):
            continue
        for step in range(1, 41):
            p = os.path.join(base, pat.format(step))
            if not os.path.exists(p):
                continue
            dd = os.path.join(dst, f"step-{step}")
            os.makedirs(dd, exist_ok=True)
            try:
                Image.open(p).convert("RGB").save(
                    os.path.join(dd, "screenshot.jpg"), quality=55)
            except Exception:
                shutil.copy2(p, os.path.join(dd, os.path.basename(p)))


def copy_run(src, dst):
    os.makedirs(dst, exist_ok=True)
    for name in ("result.json", "contamination.json"):
        if os.path.exists(os.path.join(src, name)):
            shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    copy_pixels(src, dst)
    for step in sorted(os.listdir(src)):
        if not step.startswith("step-"):
            continue
        sd, dd = os.path.join(src, step), os.path.join(dst, step)
        os.makedirs(dd, exist_ok=True)
        for f in os.listdir(sd):
            s = os.path.join(sd, f)
            if f.endswith(".png"):
                try:
                    Image.open(s).convert("RGB").save(
                        os.path.join(dd, f[:-4] + ".jpg"), quality=55)
                except Exception:
                    shutil.copy2(s, os.path.join(dd, f))
            else:
                shutil.copy2(s, os.path.join(dd, f))


def section(run_dir, name):
    r = json.load(open(os.path.join(run_dir, "result.json")))
    out = [f"## {name} — success={r['success']} ({r['steps']} steps, "
           f"{r['termination']}, {r['wall_clock_s']}s)",
           f"Task: {r['task_id']} ({r['domain']}); model: {r['model']}; "
           f"driver: {r.get('driver', 'v1')}"]
    verdicts = r.get("act_verdicts") or []
    for i, a in enumerate(r["actions"], 1):
        v = verdicts[i - 1] if i <= len(verdicts) else ""
        mech_path = os.path.join(run_dir, f"step-{i}", "mechanics.json")
        rung = ""
        if os.path.exists(mech_path):
            try:
                m = json.load(open(mech_path))
                bits = []
                if m.get("rung") is not None:
                    bits.append(f"rung {m['rung']}")
                if m.get("rung1_method"):
                    bits.append(m["rung1_method"])
                if m.get("rung1_error"):
                    bits.append(f"rung1 fell back: {m['rung1_error']}")
                if m.get("settle_ms") is not None:
                    bits.append(f"settle {m['settle_ms']}ms/"
                                f"{m.get('settle_captures')}cap")
                if m.get("reprobes"):
                    bits.append(f"re-probes {m['reprobes']}")
                if m.get("scroll_iterations"):
                    bits.append(f"scroll rounds {m['scroll_iterations']}")
                if bits:
                    rung = "  [" + "; ".join(str(b) for b in bits) + "]"
            except Exception:
                pass
        line = f"{i}. `{str(a)[:150]}`"
        if v:
            line += f"  [act-guard: {v[:120]}]"
        out.append(line + rung)
    if r.get("guard_suspects_checked") is not None:
        out.append(f"guard: {r['guard_suspects_checked']} suspects checked, "
                   f"{r['guard_hits']} hits, {r['pixel_fallbacks']} pixel "
                   f"fallbacks")
    if r.get("mechanics"):
        out.append("mechanics: " + json.dumps(r["mechanics"]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--label", default="v2")
    args = ap.parse_args()
    os.makedirs(args.dest, exist_ok=True)
    sections = []
    for run in sorted(os.listdir(args.runs)):
        src = os.path.join(args.runs, run)
        if not os.path.isdir(src) or not os.path.exists(
                os.path.join(src, "result.json")):
            continue
        copy_run(src, os.path.join(args.dest, run))
        sections.append(section(src, run))
    open(os.path.join(args.dest, "RUNS.md"), "w").write(
        "\n".join(sections))
    print("\n".join(s.split("\n")[0] for s in sections))


if __name__ == "__main__":
    main()
