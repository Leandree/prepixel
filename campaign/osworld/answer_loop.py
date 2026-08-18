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

# A server-side error is not the model failing the task, and it must not be
# allowed to look like one. Dev iteration 2 made the distinction concrete:
# 21 calls came back `API Error: 529 Overloaded`, each burning one of three
# attempts in ~200 s, and four cells that had SUCCEEDED in iteration 1 were
# recorded as step_timeout failures. The first version of this file only
# looked for 429 and treated everything else as an unparseable reply.
#
# 529 says "try again in a moment", so that is what happens now: a transient
# error does not consume an attempt, it waits and retries. Only a persistent
# one ends the cell, and it ends it as infra_failure carrying the HTTP code,
# never as a task result.
#
# The backoff total stays under the driver's step timeout (1200 s) so the
# driver never has to guess why the answer never came; and when the loop does
# give up it drops a marker the driver reads immediately.
TRANSIENT_BACKOFF = [5, 15, 30, 60, 60, 90, 120, 150, 180]   # ~12 min total
RATE_LIMIT_MARKS = ("rate limit", "rate_limit", "usage limit",
                    "quota", "resets at", "too many requests")


def api_error_of(info, reply):
    """HTTP-ish code for a server-side refusal, or None if the call reached
    the model. Kept separate from 'the reply was unusable' on purpose."""
    code = info.get("api_error_status")
    if code:
        return str(code)
    head = (reply or "")[:200]
    m = re.match(r"\s*API Error:\s*(\d{3})", head)
    if m:
        return m.group(1)
    hay = ((info.get("stderr") or "") + " " + head).lower()
    for mark in RATE_LIMIT_MARKS:
        if mark in hay:
            return "429"
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


# The answering process must carry NOTHING but the channel under test.
# Measured across dev iterations 1 and 2: the CLI was prepending the
# session's MCP tool schemas to every call — 162 129 cached prefix tokens
# per call in iteration 1, 11 702 in iteration 2, against a condition-A
# prompt of 1 204 CHARACTERS. The freeze criterion is median cost, and it
# was dominated by a constant belonging to neither channel, which moved 70x
# between iterations for reasons outside the experiment.
#
# With an empty MCP config the prefix is 2 274 tokens and byte-identical
# across calls (measured three times). Applied to BOTH conditions, so the
# only thing that still differs between them is the observation.
MCP_EMPTY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "answer-mcp-empty.json")


def answer(prompt, tools, model, workdir):
    cmd = ["claude", "-p", "--model", model, "--tools", tools,
           "--output-format", "json",
           "--strict-mcp-config", "--mcp-config", MCP_EMPTY]
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
        meta, action, raw = {"attempts": [], "transient_retries": 0}, None, ""
        attempt, transient, gave_up = 0, 0, None
        while attempt < MAX_ATTEMPTS:
            try:
                raw, info = answer(prompt, tools, args.model, workdir)
            except subprocess.TimeoutExpired:
                raw, info = "", {"cmd": "timeout", "tools": tools,
                                 "seconds": CALL_TIMEOUT, "returncode": -1,
                                 "stderr": "call timed out"}
            code = api_error_of(info, raw)
            if code:
                # The call never reached the model, so it is not one of the
                # model's chances to answer. Wait and try again.
                info["attempt"] = f"transient-{transient + 1}"
                meta["attempts"].append(info)
                if transient >= len(TRANSIENT_BACKOFF):
                    gave_up = code
                    break
                wait = TRANSIENT_BACKOFF[transient]
                transient += 1
                meta["transient_retries"] = transient
                print(f"step {step}: API {code}, retry {transient} "
                      f"in {wait}s")
                time.sleep(wait)
                continue
            attempt += 1
            info["attempt"] = attempt
            meta["attempts"].append(info)
            action = extract_action(raw)
            if action is not None:
                break
            print(f"step {step}: no JSON in reply, attempt {attempt}")

        open(os.path.join(sd, "answer.txt"), "w").write(raw)
        if gave_up:
            meta["api_unavailable"] = gave_up
            json.dump(meta, open(os.path.join(sd, "answer-meta.json"), "w"),
                      indent=1)
            open(os.path.join(args.run, "API_UNAVAILABLE"), "w").write(
                f"step {step}: API {gave_up} after {transient} retries")
            print(f"step {step}: API {gave_up} persisted — stopping the cell")
            return

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
