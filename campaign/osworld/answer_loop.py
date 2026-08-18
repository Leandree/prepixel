#!/usr/bin/env python3
"""Answering agent for ONE run, isolated by construction (ruling D1).

Every step is answered by a FRESH `claude -p` process with an explicit tool
list, so isolation is a property of the process, not a request in a prompt:

  condition B -> --tools ""      no tools at all
  condition A -> --tools Read    only file reading, because A's channel IS
                                 an image it has to open

Verified on this machine before first use (see acceptance notes): with
`--tools ""` the model cannot read a canary file — asked for the contents of
/tmp/canary-test.txt it produced an invented value instead of the real
`CANARY-7f3a9c` — while `--tools Read` returned the exact contents, and an
image read describes the screenshot correctly. The process runs from an
empty working directory, and an isolated call reports no CLAUDE.md or user
memory loaded, so the campaign's own notes cannot leak into an answer.

The model never writes `action.json`: it returns one JSON object as text and
this loop writes the file. The raw reply is kept in `step-N/answer.txt` and
the call's metadata (tool list, duration, exit code, attempts) in
`step-N/answer-meta.json`, which is what `scan_contamination.py` audits.

Calls run with `--output-format json`, so each attempt records the CLI's own
token accounting (`usage`, `modelUsage`, `total_cost_usd`) rather than an
offline estimate of it. The manager's freeze criterion is median cost, and
condition A's cost is mostly IMAGE tokens, which no text-side approximation
would have counted honestly. `modelUsage` is kept per model because the CLI
bills a small helper model of its own alongside the answering model; only
the answering model's share is the experiment's cost.

MODEL (user decision 2026-08-18, DEV-PHASE-PLAN P8): `claude-opus-5[1m]`, in
BOTH conditions. Note that the CLI's `opus` alias resolves to Opus 4.8, so
the model is named explicitly rather than by alias.

Usage:
  python answer_loop.py --run <run-dir> --condition A|B [--model M]
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
import time

CALL_TIMEOUT = 420          # s per answer; a stuck call ends the step
MAX_ATTEMPTS = 3            # unparseable reply -> fresh process, same prompt

# This host answers on a Claude Max SUBSCRIPTION, with overflow billing off:
# when the account's limit is reached the call is refused, it does not
# silently become pay-as-you-go. A refusal is an infrastructure fact about
# the host, not the model failing the task, and burning MAX_ATTEMPTS on it
# would turn one refusal into three and then into a "task failure". The loop
# raises a marker the driver reads, and the cell is recorded infra_failure.
RATE_LIMIT_MARKS = ("rate limit", "rate_limit", "429", "usage limit",
                    "quota", "resets at", "too many requests")


def looks_rate_limited(info, reply):
    if str(info.get("api_error_status") or "") == "429":
        return "api_error_status=429"
    hay = ((info.get("stderr") or "") + " " + (reply or "")[:500]).lower()
    for m in RATE_LIMIT_MARKS:
        if m in hay:
            return m
    return None


def extract_action(text):
    """First JSON object in the reply that carries an "action" key."""
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = fenced + re.findall(r"\{[^{}]*\"action\"[^{}]*\}", text, re.S)
    for c in candidates:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "action" in obj:
            return obj
    # last resort: a brace-balanced scan from the first '{'
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict) and "action" in obj:
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
        start = text.find("{", start + 1)
    return None


def answer(prompt, tools, model, workdir):
    cmd = ["claude", "-p", "--model", model, "--tools", tools,
           "--output-format", "json"]
    t0 = time.time()
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       timeout=CALL_TIMEOUT, cwd=workdir)
    info = {"cmd": " ".join(cmd), "tools": tools,
            "seconds": round(time.time() - t0, 1),
            "returncode": p.returncode, "stderr": (p.stderr or "")[-400:]}
    try:
        env = json.loads(p.stdout)
        reply = env.get("result") or ""
        info["usage"] = env.get("usage")
        info["model_usage"] = env.get("modelUsage")
        info["cost_usd"] = env.get("total_cost_usd")
        info["api_error_status"] = env.get("api_error_status")
    except json.JSONDecodeError:
        # The envelope is the CLI's contract, not the model's; if it is
        # missing something went wrong at the CLI level. Keep the raw bytes
        # so the failure is inspectable instead of silently becoming a
        # zero-cost step.
        reply = p.stdout
        info["envelope_parse_failed"] = True
    return reply, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--condition", required=True, choices=["A", "B"])
    ap.add_argument("--model", default="claude-opus-5[1m]")
    args = ap.parse_args()

    # A must open its screenshot; B is given everything inline and gets
    # nothing to open. This single line is the whole isolation contract.
    tools = "Read" if args.condition == "A" else ""
    workdir = tempfile.mkdtemp(prefix="osworld-answer-")   # no CLAUDE.md here
    cur_file = os.path.join(args.run, "CURRENT_STEP")
    done = set()

    while True:
        if not os.path.exists(cur_file):
            time.sleep(2)
            continue
        cur = open(cur_file).read().strip()
        if cur == "FINISHED":
            print("run finished")
            return
        if not cur.isdigit() or cur in done:
            time.sleep(2)
            continue
        step = int(cur)
        sd = os.path.join(args.run, f"step-{step}")
        ppath = os.path.join(sd, "prompt.txt")
        apath = os.path.join(sd, "action.json")
        if not os.path.exists(ppath) or os.path.exists(apath):
            time.sleep(2)
            continue

        prompt = open(ppath).read()
        meta, action, raw = {"attempts": []}, None, ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw, info = answer(prompt, tools, args.model, workdir)
            except subprocess.TimeoutExpired:
                raw, info = "", {"cmd": "timeout", "tools": tools,
                                 "seconds": CALL_TIMEOUT, "returncode": -1,
                                 "stderr": "call timed out"}
            info["attempt"] = attempt
            meta["attempts"].append(info)
            action = extract_action(raw)
            if action is not None:
                break
            # Only now: a call that returned a usable action cannot have been
            # refused, and testing the reply text unconditionally would trip
            # on a task that asks the model to TYPE "429" or "rate limit"
            # into a document — discarding a good cell as infrastructure.
            hit = looks_rate_limited(info, raw)
            if hit:
                meta["rate_limited"] = hit
                json.dump(meta, open(os.path.join(sd, "answer-meta.json"), "w"),
                          indent=1)
                open(os.path.join(sd, "answer.txt"), "w").write(raw)
                open(os.path.join(args.run, "RATE_LIMITED"), "w").write(
                    f"step {step}, attempt {attempt}: {hit}")
                print(f"step {step}: rate limited ({hit}) — stopping the cell")
                return
            print(f"step {step}: no JSON in reply, attempt {attempt}")

        open(os.path.join(sd, "answer.txt"), "w").write(raw)
        meta["tools"] = tools
        meta["parsed"] = action is not None
        json.dump(meta, open(os.path.join(sd, "answer-meta.json"), "w"),
                  indent=1)
        if action is None:
            # Not a model decision we can execute, and not something the
            # loop may invent: leave action.json unwritten so the driver
            # times out and records infra_failure with the evidence on disk.
            print(f"step {step}: unparseable after {MAX_ATTEMPTS} attempts")
            return
        tmp = apath + ".tmp"
        json.dump(action, open(tmp, "w"))
        os.replace(tmp, apath)
        done.add(cur)
        print(f"step {step}: {json.dumps(action)[:120]}")


if __name__ == "__main__":
    main()
