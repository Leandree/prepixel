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

2. Textual, in two directions that must not be conflated:
   - over the PROMPT, which is what the model received, and is where
     contamination actually lives. Condition B's prompt must carry no
     filesystem path at all except a crop it explicitly asked for (a
     declared pixel fallback, counted in result.json).
   - over the model's own REPLY, for references to the evaluator directory
     or to other runs' traces — evidence it saw material it should not
     have.
   Scanning replies for URLs or the word "pixels" was a mistake corrected
   after dev iteration 1: it produced eight false positives, because typing
   a URL into an address bar IS the task and "crop e40 to see the pixels" is
   condition B using its own action, returned to it verbatim by the P5 memo.
   Web and file access are prevented structurally by the tool list.

   This layer can only catch what appears in text, so it is evidence of
   contamination, never proof of its absence — layer 1 carries the
   guarantee.

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

# Two scans with two different jobs, because conflating them produced eight
# false positives in dev iteration 1.
#
# PROMPT patterns: material that must never REACH the model. This is where
# contamination actually lives, and until iteration 1 the prompt was never
# read at all — so D1's guarantee that condition B's prompt carries no
# filesystem path had gone unaudited since it was written.
PROMPT_PATTERNS = [
    ("evaluator", r"evaluation_examples"),
    ("other-run-traces", r"osworld-runs|osworld-pilot|pilot-(?:os|chrome)-[AB]"),
]
# ANSWER patterns: evidence the model SAW forbidden material. A URL or the
# word "pixels" in an answer proves nothing — typing a URL into the address
# bar IS the task, and "crop e40 to see the pixels" is condition B using its
# own sanctioned action, handed back verbatim by the P5 memo. Web access and
# file reading are prevented structurally by the tool list, which is the real
# guarantee and is checked above.
ANSWER_PATTERNS = [
    ("evaluator", r"evaluation_examples"),
    ("other-run-traces", r"osworld-runs|osworld-pilot|pilot-(?:os|chrome)-[AB]"),
]
# HOST paths only. `/root/Desktop/reminder.docx` is a file inside the VM that
# a task is about — task content, not a channel leak — and flagging it made
# the scan cry wolf on dev iteration 2. What must never reach condition B is
# a path to OUR artefacts: the run directories and the pixel files.
PATH_RE = re.compile(
    r"/home/leandre/[^\s\"'\)\]]+|/[^\s\"'\)\]]*\.(?:png|jpe?g)\b")

# The memo is the model's OWN words, handed back verbatim by P5. Anything in
# it was authored by the model, so it cannot be evidence that the channel
# leaked something to the model. Scanned as an answer, never as a prompt.
MEMO_RE = re.compile(
    r"^YOUR NOTE FROM THE PREVIOUS STEP:\n.*?(?=\n\n)", re.S | re.M)


def _ctx(text, m, pad=60):
    return text[max(0, m.start() - pad):m.end() + pad].replace(
        "\n", " ").strip()


def scan_run(run_dir):
    run_dir = run_dir.rstrip("/")
    rpath = os.path.join(run_dir, "result.json")
    incomplete = None
    if os.path.exists(rpath):
        cond = json.load(open(rpath))["condition"]
    else:
        # A cell that died before writing its result still has prompts and
        # answers on disk, and those are exactly what an audit must read.
        # Crashing here would mean the class of cell most likely to have gone
        # wrong is the one class never scanned. The condition is recoverable
        # from the directory name, which the runner controls.
        cond = "B" if run_dir.endswith("-B") else "A"
        incomplete = "no result.json — cell did not finish"
    rep = {"run": os.path.basename(run_dir), "condition": cond,
           "steps": 0, "violations": [], "tool_lists": []}
    if incomplete:
        rep["incomplete"] = incomplete

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
        # What the model RECEIVED. This is where contamination lives, and it
        # was never read before: D1 says condition B's prompt contains no
        # filesystem path at all, and nothing checked it.
        ppath = os.path.join(sd, "prompt.txt")
        if os.path.exists(ppath):
            prompt = open(ppath, encoding="utf-8", errors="replace").read()
            prompt = MEMO_RE.sub("[memo omitted: model-authored]", prompt)
            for name, pat in PROMPT_PATTERNS:
                m = re.search(pat, prompt, re.I)
                if m:
                    rep["violations"].append(
                        {"step": step, "kind": "prompt-" + name,
                         "detail": _ctx(prompt, m)})
            if cond == "B":
                for m in re.finditer(PATH_RE, prompt):
                    path = m.group(0)
                    # The one path B may legitimately see is a crop it asked
                    # for — a declared pixel fallback, already counted in
                    # result.json. Anything else is a channel leak.
                    if "/crop.png" in path:
                        rep["crops_served"] = rep.get("crops_served", 0) + 1
                    else:
                        rep["violations"].append(
                            {"step": step, "kind": "path-in-B-prompt",
                             "detail": _ctx(prompt, m)})

        # What the model PRODUCED. Only ground-truth material matters here:
        # an answer quoting an evaluator path is evidence it saw something.
        # Scanning answers for "web" or "pixels" was backwards and produced
        # 8 false positives in iteration 1 — a model TYPING a URL into the
        # address bar is the task, and a memo saying "crop e40 to see the
        # pixels" is condition B using its own sanctioned action, handed back
        # to it verbatim by P5.
        apath = os.path.join(sd, "answer.txt")
        text = open(apath, encoding="utf-8", errors="replace").read() \
            if os.path.exists(apath) else ""
        for name, pat in ANSWER_PATTERNS:
            m = re.search(pat, text, re.I)
            if m:
                rep["violations"].append(
                    {"step": step, "kind": "answer-" + name,
                     "detail": _ctx(text, m)})
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
