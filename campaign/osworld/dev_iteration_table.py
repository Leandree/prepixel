#!/usr/bin/env python3
"""Iteration table for one dev pass (DEV-PHASE-PLAN §3).

Produces exactly what the freeze decision needs — success A/B, median cost,
and one line of MECHANICAL evidence per B failure — plus the aggregate the
manager asked for in P7: every `rung1_fallback` reason, counted, so the next
interface to implement is chosen from the log rather than from intuition.

Deliberately does not name a cause for a failure. It prints the termination,
the step count, the last actions and the guard verdicts, and the cause is
written by hand after reading the trace. A script that guessed causes would
produce a table that reads like evidence and is not.

Usage:
  python dev_iteration_table.py --runs ~/dev/osworld-dev-iter1 [--md out.md]
"""
import argparse
import collections
import json
import os
import statistics


def load(runs):
    cells = {}
    for name in sorted(os.listdir(runs)):
        p = os.path.join(runs, name, "result.json")
        if not os.path.exists(p):
            continue
        try:
            r = json.load(open(p))
        except Exception:
            continue
        r["_dir"] = os.path.join(runs, name)
        r["_name"] = name
        cells[name] = r
    return cells


def cost_of(r):
    return (r.get("cost") or {}).get("cost_usd")


def steps_of(runs_dir):
    """Per-step mechanics, oldest first."""
    out = []
    for i in range(1, 60):
        p = os.path.join(runs_dir, f"step-{i}", "mechanics.json")
        if not os.path.exists(p):
            continue
        try:
            out.append(json.load(open(p)))
        except Exception:
            pass
    return out


def action_of(runs_dir, i):
    p = os.path.join(runs_dir, f"step-{i}", "action.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--md", default="")
    ap.add_argument("--subset", default="",
                    help="task file: restrict the table to its tasks "
                         "(iteration 3 reports dev-core and dev-browser "
                         "separately, never mixed)")
    a = ap.parse_args()
    runs = os.path.expanduser(a.runs)
    cells = load(runs)
    if a.subset:
        spec = json.load(open(a.subset))["tasks"]
        keep = {t for ids in spec.values() for t in ids}
        cells = {k: v for k, v in cells.items() if v["task_id"] in keep}

    pairs = collections.OrderedDict()
    for name, r in cells.items():
        key = name.rsplit("-", 1)[0]
        pairs.setdefault(key, {})[r["condition"]] = r

    L = []
    W = L.append
    W("| task | A | steps | $ | B | steps | $ |")
    W("|---|---|---|---|---|---|---|")
    for key, p in pairs.items():
        row = ["`%s`" % key]
        for c in ("A", "B"):
            r = p.get(c)
            if not r:
                row += ["—", "—", "—"]
                continue
            mark = "✅" if r["success"] else "❌"
            if r.get("infra_failure"):
                mark = "⚠️infra"
            cu = cost_of(r)
            row += [mark, str(r["steps"]),
                    ("%.2f" % cu) if cu is not None else "—"]
        W("| " + " | ".join(row) + " |")

    def agg(cond, fn):
        vals = [fn(r) for r in cells.values()
                if r["condition"] == cond and fn(r) is not None]
        return vals

    W("")
    W("| metric | A | B |")
    W("|---|---|---|")
    for label, fn in (("cells", lambda r: 1),
                      ("successes", lambda r: 1 if r["success"] else None),
                      ("infra failures",
                       lambda r: 1 if r.get("infra_failure") else None)):
        W("| %s | %d | %d |" % (label, len(agg("A", fn)), len(agg("B", fn))))
    for label, fn in (("median steps", lambda r: r["steps"]),
                      ("median cost $", cost_of),
                      ("total cost $", cost_of)):
        va, vb = agg("A", fn), agg("B", fn)
        if label.startswith("total"):
            sa, sb = sum(va), sum(vb)
        else:
            sa = statistics.median(va) if va else 0
            sb = statistics.median(vb) if vb else 0
        W("| %s | %.2f | %.2f |" % (label, sa, sb))

    # ---- iteration-3 metrics: caps, verdicts, channel per step ----
    caps = {"A": 0, "B": 0}
    verdictc = collections.Counter()
    for r in cells.values():
        if r["steps"] >= 15 or r["termination"] == "max_steps":
            caps[r["condition"]] += 1
        for v in (r.get("act_verdicts") or []):
            verdictc[(v or "").split(" ")[0]] += 1
    W("")
    W("**Cap deaths (>=15 steps): A=%d B=%d.** B guard verdicts: %s" % (
        caps["A"], caps["B"],
        ", ".join("%s=%d" % kv for kv in sorted(verdictc.items()))))

    # ---- P7 input: why rung 1 declined, counted over the whole dev set ----
    reasons = collections.Counter()
    rungs = collections.Counter()
    channels = collections.Counter()
    cdp_decline = collections.Counter()
    escal = collections.Counter()
    for r in cells.values():
        if r["condition"] != "B":
            continue
        for m in steps_of(r["_dir"]):
            if "rung" in m:
                rungs[str(m["rung"])] += 1
            if m.get("escalated_from_rung1"):
                escal["noop_escalations"] += 1
            if m.get("reresolved_rect"):
                escal["fingerprint_matches"] += 1
            if m.get("rung1_error"):
                # keep the reason, drop the element-specific tail
                reasons[str(m["rung1_error"])[:90]] += 1
            channels[m.get("channel", "unknown")] += 1
            c = m.get("cdp") or {}
            if c and not c.get("used"):
                cdp_decline[str(c.get("reason"))[:70]] += 1
    if escal:
        W("")
        W("**Ladder self-corrections:** " +
          ", ".join("%s=%d" % kv for kv in sorted(escal.items())))
    W("")
    W("**Condition B mechanics, all steps.** rung: " +
      ", ".join("%s=%d" % kv for kv in sorted(rungs.items())) +
      " · channel: " + ", ".join("%s=%d" % kv for kv in sorted(channels.items())))
    if reasons:
        W("")
        W("| rung-1 fallback reason (P7 input) | n |")
        W("|---|---|")
        for why, n in reasons.most_common():
            W("| `%s` | %d |" % (why, n))
    if cdp_decline:
        W("")
        W("| router declined the web channel because | n |")
        W("|---|---|")
        for why, n in cdp_decline.most_common():
            W("| `%s` | %d |" % (why, n))

    # ---- evidence for each B failure, cause left blank on purpose ----
    W("")
    W("**Every B failure, with its mechanical evidence. Cause written by "
      "hand after reading the trace — this script never guesses one.**")
    W("")
    for key, p in pairs.items():
        b = p.get("B")
        if not b or b["success"]:
            continue
        ms = steps_of(b["_dir"])
        verdicts = collections.Counter(
            (v or "").split(" ")[0] for v in (b.get("act_verdicts") or []))
        last = []
        for i in range(max(1, b["steps"] - 2), b["steps"] + 1):
            act = action_of(b["_dir"], i)
            if act:
                last.append("%d:%s" % (i, json.dumps(act)[:90]))
        W("- `%s` — term=%s steps=%d, A=%s. verdicts %s. last %s" % (
            key, b["termination"], b["steps"],
            "✅" if p.get("A", {}).get("success") else "❌",
            dict(verdicts), " | ".join(last) or "(none)"))
        W("  - cause: TODO")

    text = "\n".join(L)
    print(text)
    if a.md:
        open(os.path.expanduser(a.md), "w").write(text + "\n")


if __name__ == "__main__":
    main()
