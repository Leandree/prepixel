#!/usr/bin/env python3
"""Development-set sampler (manager_orders/DEV-PHASE-PLAN.md §1).

The driver is the system under measurement, so improving it is legitimate —
improving it while looking at the test set is not. This draws 20 tasks that
are DISJOINT from the pre-registered 50 and from the 2 pilot tasks, over the
same 9 domains, with the same deterministic procedure as `select_tasks.py`
but seed 43.

Same quota algorithm as the pre-registration (proportional to domain size,
minimum 2 per domain at this size, largest-remainder adjustment, ties broken
alphabetically), same "sample from the SORTED id list with one shared
generator, domains in alphabetical order" rule. The only differences are the
seed, the target count, and the exclusion set — which is written into the
output so the disjointness is auditable rather than asserted.

Run: python3 select_dev_tasks.py /path/to/test_all.json \
        campaign/osworld/tasks-selected.json
"""
import json
import math
import random
import sys

DOMAINS = ["chrome", "gimp", "libreoffice_calc", "libreoffice_impress",
           "libreoffice_writer", "multi_apps", "os", "thunderbird", "vlc"]
N_TARGET, MIN_PER_DOMAIN, SEED = 20, 2, 43
# The two pilot tasks, deliberately outside the pre-registered 50 and used
# for driver debugging since v1 — they carry known answers, so they must not
# become dev material either.
PILOT = {"13584542-872b-42d8-b299-866967b5c3ef",
         "030eeff7-b492-4218-b312-701ec99ee0cc"}

all_tasks = json.load(open(sys.argv[1]))
preregistered = json.load(open(sys.argv[2]))["tasks"]
excluded = set(PILOT)
for d in preregistered:
    excluded.update(preregistered[d])

pool = {d: sorted(set(all_tasks[d]) - excluded) for d in DOMAINS}
sizes = {d: len(pool[d]) for d in DOMAINS}
total = sum(sizes.values())

share = {d: N_TARGET * sizes[d] / total for d in DOMAINS}
quota = {d: max(MIN_PER_DOMAIN, math.floor(share[d])) for d in DOMAINS}
while sum(quota.values()) < N_TARGET:
    d = max(sorted(DOMAINS), key=lambda d: (share[d] - quota[d],))
    quota[d] += 1
while sum(quota.values()) > N_TARGET:
    d = max(sorted(DOMAINS),
            key=lambda d: (quota[d] - share[d]) if quota[d] > MIN_PER_DOMAIN
            else -1e9)
    quota[d] -= 1

rng = random.Random(SEED)
selected = {d: sorted(rng.sample(pool[d], quota[d])) for d in sorted(DOMAINS)}

chosen = {t for v in selected.values() for t in v}
assert not (chosen & excluded), "dev set overlaps the test set or the pilots"

out = {
    "purpose": "development set — the driver is tuned on these and NEVER on "
               "the pre-registered 50 (manager_orders/DEV-PHASE-PLAN.md §1)",
    "source": "evaluation_examples/test_all.json @ OSWorld main "
              "(cloned 2026-08-17)",
    "seed": SEED, "n_target": N_TARGET, "min_per_domain": MIN_PER_DOMAIN,
    "excluded": {"pre_registered_50": sorted(
        t for v in preregistered.values() for t in v),
        "pilot_tasks": sorted(PILOT)},
    "pool_sizes_after_exclusion": sizes, "quotas": quota,
    "n_selected": len(chosen), "tasks": selected,
    "disjointness_checked": True,
    "usage_rule": "Dev cells never count toward the campaign. When the "
                  "improvements plateau the driver is tagged driver-freeze-v3 "
                  "and the 50 run once, unmodified.",
}
print(json.dumps(out, indent=1))
