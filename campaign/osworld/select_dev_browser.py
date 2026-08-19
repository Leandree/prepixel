#!/usr/bin/env python3
"""Browser supplement for the dev set (GRANDE-PASSE-AUTONOME §4, P1).

Iteration 2 could not measure the CDP router: only 2 of the 20 dev cells
had a browser at all, because the core dev sampler is domain-proportional
and CDP exists only where the task's own setup launches Chrome with a
debug port (79 of 369 corpus-wide). This draws 8 EXTRA dev tasks from that
79-task pool, seed 44, so the router gets measured on cells where it can
actually fire. Reported separately (dev-browser) from the 20 (dev-core),
never mixed.

Exclusions, all committed here so the disjointness is auditable: the 50
pre-registered (their IDs only — configs untouched), the 2 pilot tasks,
the 20 dev-core tasks, and any task whose setup needs Google credentials
this host does not have (their infra_failure is already measured; burning
8 supplement slots on known infra failures would measure nothing).

Run: python3 select_dev_browser.py ~/dev/OSWorld/evaluation_examples/test_all.json \
        tasks-selected.json tasks-dev.json
"""
import glob
import json
import os
import random
import sys

SEED, N_TARGET = 44, 8
PILOT = {"13584542-872b-42d8-b299-866967b5c3ef",
         "030eeff7-b492-4218-b312-701ec99ee0cc"}

all_tasks = json.load(open(sys.argv[1]))
preregistered = json.load(open(sys.argv[2]))["tasks"]
dev_core = json.load(open(sys.argv[3]))["tasks"]

excluded = set(PILOT)
for d in preregistered:
    excluded.update(preregistered[d])
for d in dev_core:
    excluded.update(dev_core[d])

base = os.path.expanduser("~/dev/OSWorld/evaluation_examples/examples")
pool = []          # (domain, task_id), sorted for determinism
needs_creds = []
for path in sorted(glob.glob(os.path.join(base, "*", "*.json"))):
    dom = os.path.basename(os.path.dirname(path))
    tid = os.path.basename(path)[:-5]
    if tid in excluded:
        continue
    try:
        cfg = json.load(open(path))
    except Exception:
        continue
    txt = json.dumps(cfg)
    if "--remote-debugging-port" not in txt:
        continue
    if "googledrive" in txt or "client_secrets" in txt or \
            '"login"' in json.dumps([s.get("type") for s in
                                     cfg.get("config", [])]):
        needs_creds.append((dom, tid))
        continue
    pool.append((dom, tid))

rng = random.Random(SEED)
chosen = sorted(rng.sample(pool, N_TARGET))

out = {
    "purpose": "dev-browser supplement — measure the per-window CDP router "
               "on cells where a debug-port Chrome exists "
               "(GRANDE-PASSE-AUTONOME §4 P1)",
    "seed": SEED, "n_target": N_TARGET,
    "pool_size_after_exclusion": len(pool),
    "excluded_needing_credentials": sorted("%s/%s" % t for t in needs_creds),
    "excluded_sets": {"pre_registered_50": True, "pilots": 2,
                      "dev_core_20": True},
    "tasks": {},
    "usage_rule": "Dev cells never count toward the campaign. Reported "
                  "separately from dev-core, never mixed.",
}
for dom, tid in chosen:
    out["tasks"].setdefault(dom, []).append(tid)
print(json.dumps(out, indent=1))
