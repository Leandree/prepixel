#!/usr/bin/env python3
"""Contamination scan for a run's traces (ruling D1).

What the answering agent was ALLOWED to see, per step: its prompt, and — in
condition A only — the screenshot the prompt names, which lives alone in a
per-step pixels directory. Anything else is contamination and invalidates
that step.

Two layers, because they have different strengths:

1. Structural, from `answer-meta.json`: the tool list the process actually
   ran with. Condition B must show `tools: ""` (no tools, so no file, no
   web, no other run's traces can be reached at all) and condition A must
   show `tools: "Read"` (no web, no shell). A tool list outside those is a
   hard violation regardless of what the answer says.

2. Textual, over the model's own reply: references to the evaluator
   directory (the answer key), to other runs' or conditions' traces, to
   screenshots in condition B, or to the web. This layer can only catch what
   the model mentions, so it is evidence of contamination, never proof of
   its absence — the structural layer is what carries the guarantee.

Usage:
  python scan_contamination.py <run-dir> [run-dir ...] [--json out.json]
Exit code 0 = every scanned run is clean, 1 = at least one violation.
"""
import argparse
import json
import os
import re
import sys

ALLOWED_TOOLS = {"A": "Read", "B": ""}

# Each pattern is a way OUT of the channel, in the order they bit us during
# pilot v2: the answer key, other runs' traces, pixels in condition B, web.
PATTERNS = [
    ("evaluator", r"evaluation_examples"),
    ("other-run-traces", r"osworld-runs|osworld-pilot|pilot-(?:os|chrome)-[AB]"),
    ("web", r"https?://|web\s*search|WebSearch|WebFetch"),
]
PIXEL_PATTERNS = [("pixels-in-B", r"screenshot|\.png\b|\.jpg\b|pixel")]


def scan_run(run_dir):
    result = json.load(open(os.path.join(run_dir, "result.json")))
    cond = result["condition"]
    rep = {"run": os.path.basename(run_dir), "condition": cond,
           "steps": 0, "violations": [], "tool_lists": []}
    pats = PATTERNS + (PIXEL_PATTERNS if cond == "B" else [])

    for step in sorted(int(d.split("-")[1])
                       for d in os.listdir(run_dir) if d.startswith("step-")):
        sd = os.path.join(run_dir, f"step-{step}")
        rep["steps"] += 1
        mpath = os.path.join(sd, "answer-meta.json")
        if not os.path.exists(mpath):
            rep["violations"].append(
                {"step": step, "kind": "no-answer-metadata",
                 "detail": "cannot prove which tools answered this step"})
            continue
        meta = json.load(open(mpath))
        tools = meta.get("tools")
        rep["tool_lists"].append(tools)
        if tools != ALLOWED_TOOLS[cond]:
            rep["violations"].append(
                {"step": step, "kind": "tool-list",
                 "detail": f"ran with tools={tools!r}, "
                           f"allowed {ALLOWED_TOOLS[cond]!r}"})
        apath = os.path.join(sd, "answer.txt")
        text = open(apath, encoding="utf-8", errors="replace").read() \
            if os.path.exists(apath) else ""
        for name, pat in pats:
            m = re.search(pat, text, re.I)
            if m:
                line = text[max(0, m.start() - 60):m.end() + 60].replace(
                    "\n", " ")
                rep["violations"].append(
                    {"step": step, "kind": name, "detail": line.strip()})
    rep["clean"] = not rep["violations"]
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args()

    reports = [scan_run(r) for r in args.runs]
    for rep in reports:
        status = "CLEAN" if rep["clean"] else f"{len(rep['violations'])} VIOLATIONS"
        print(f"{rep['run']} ({rep['condition']}, {rep['steps']} steps): {status}")
        for v in rep["violations"]:
            print(f"    step {v['step']} [{v['kind']}] {v['detail'][:140]}")
    if args.json:
        json.dump(reports, open(args.json, "w"), indent=1)
    sys.exit(0 if all(r["clean"] for r in reports) else 1)


if __name__ == "__main__":
    main()
