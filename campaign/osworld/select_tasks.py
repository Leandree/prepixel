#!/usr/bin/env python3
"""Pre-registration sampler for the OSWorld campaign (OSWORLD-PROTOCOL.md §1).

50 tasks over 9 domains (vs_code excluded by protocol), proportional to domain
size in evaluation_examples/test_all.json with a minimum of 3 per domain,
seeded RNG (seed=42). Fully deterministic:
- quotas: floor(50 * size/total), bump every domain to >=3, then adjust to
  sum=50 by largest fractional remainder (add) / largest surplus (remove,
  never below 3), ties broken alphabetically;
- within-domain sampling: random.Random(42).sample() over the SORTED task-id
  list, domains processed in alphabetical order with the SAME generator.
Run: python3 select_tasks.py /path/to/OSWorld/evaluation_examples/test_all.json
"""
import json, random, sys, math

DOMAINS = ["chrome", "gimp", "libreoffice_calc", "libreoffice_impress",
           "libreoffice_writer", "multi_apps", "os", "thunderbird", "vlc"]
N_TARGET, MIN_PER_DOMAIN, SEED = 50, 3, 42

src = sys.argv[1]
all_tasks = json.load(open(src))
sizes = {d: len(all_tasks[d]) for d in DOMAINS}
total = sum(sizes.values())

share = {d: N_TARGET * sizes[d] / total for d in DOMAINS}
quota = {d: max(MIN_PER_DOMAIN, math.floor(share[d])) for d in DOMAINS}
while sum(quota.values()) < N_TARGET:
    d = max(sorted(DOMAINS), key=lambda d: (share[d] - quota[d], ))
    quota[d] += 1
while sum(quota.values()) > N_TARGET:
    d = max(sorted(DOMAINS), key=lambda d: (quota[d] - share[d]) if quota[d] > MIN_PER_DOMAIN else -1e9)
    quota[d] -= 1

rng = random.Random(SEED)
selected = {}
for d in sorted(DOMAINS):
    ids = sorted(all_tasks[d])
    selected[d] = sorted(rng.sample(ids, quota[d]))

out = {
    "protocol": "OSWORLD-PROTOCOL.md v1 §1",
    "source": "evaluation_examples/test_all.json @ OSWorld main (cloned 2026-08-17)",
    "seed": SEED, "n_target": N_TARGET, "min_per_domain": MIN_PER_DOMAIN,
    "domain_sizes": sizes, "quotas": quota,
    "n_selected": sum(len(v) for v in selected.values()),
    "tasks": selected,
    "amendment_rule": "No task may be added or removed after commit. Infra-broken tasks are marked infra_failure with evidence, never replaced.",
}
print(json.dumps(out, indent=1))
