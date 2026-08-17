# OSWorld agent — returns to the test manager

**What this file is.** Correspondence between the OSWorld-campaign agent and the
test manager, per `campaign/agent-brief-COMMON.md` § Returns and
`OSWORLD-PROTOCOL.md` §4.5. Measurements will go in per-task JSON cells, not
here.

**Convention.** Newest entry at the top. Each entry dated, with a status:
`DECISION NEEDED` / `FYI` / `BLOCKED` / `DONE`.

---

## 2026-08-17 — DECISION NEEDED — financing + model for the 100 runs (campaign paused at setup-complete)

The protocol fixes ONE exact model string for both conditions but leaves the
choice open, and the machine has no model API key (checked; I will not borrow
credentials from unrelated projects on this host). Cost estimate for the full
campaign (100 runs × ~12 steps, condition A ≈ 3 screenshots/step): ~7–8M input
tokens → **~$25–45 on claude-sonnet-4-6** (the model I recommend: accepts
temperature=0 as the protocol demands — Sonnet 5 / Opus 4.7+ / Fable REJECT
the temperature parameter, which would also force modifying the example
agent), ~$8–15 on claude-haiku-4-5 (floor-effect risk), ~2× on Opus 4.8.

RESOLVED 2026-08-18 by the manager: two-track plan approved. (1) Research
credits application package prepared
(`campaign/osworld/research-credits-application.md`) — if granted, the
API-pure campaign with the unmodified run.py agent on claude-sonnet-4-6 is
the paper's main result. (2) Meanwhile the campaign runs through the Claude
Code subscription as a pre-registered pilot; manager directed the answering
agents to run on the **"sonnet" model alias** (fresh subagent per step,
stateless, mirroring the reference agent's per-call statelessness; exact
alias resolution at run date recorded in each result's `model` field).
Documented deviations for track 2: session-alias model instead of a pinned
API string; no temperature control (moot — current models reject the
parameter; protocol amendment to "model sampling defaults, documented"
approved implicitly by the manager's go); harness system prompt not fully
publishable (identical across conditions); coverage-guard crops come from
the VM full-screen screenshot, not per-window surfaces (OSWorld's obs API
has no per-window capture — single-app fullscreen VM ≈ equivalent; noted as
a guard KNOWN-LIMIT interaction). Absolute scores not leaderboard-comparable;
only the A−B contrast is claimed. QUOTA PILOT before the campaign: 2 tasks ×
2 conditions on tasks OUTSIDE the pre-registered 50 (first non-selected id,
alphabetically, of `os` and `chrome`), results marked pilot and never
counted — so no campaign cell is ever re-run because of driver debugging.

## 2026-08-17 — DONE — protocol file moved into the repo

`OSWORLD-PROTOCOL.md` was sitting untracked at the repo root; moved verbatim
to `campaign/OSWORLD-PROTOCOL.md` (the path the tasking references) and
committed, so the pre-registration below points at a versioned protocol.

## 2026-08-17 — DONE — setup + env-level smoke test (no model in the loop yet)

- **KVM**: `/dev/kvm` present; README check `egrep -c '(vmx|svm)' /proc/cpuinfo`
  = 12. Docker Engine 28.4.0, user in `docker` group.
- **Install**: followed README §Installation strictly — cloned
  `xlang-ai/OSWorld` to `~/dev/OSWorld`; system Python is 3.13 which the pinned
  deps (torch~=2.5.0, numpy~=1.26) do not support, so the README's recommended
  conda path was used: Miniconda (rootless, `~/miniconda3`) + `conda create -n
  osworld python=3.10` + `pip install -r requirements.txt`. Deviation from
  README: none beyond conda being the documented-optional env manager; no flags
  improvised. (Conda now requires an interactive ToS acceptance —
  `conda tos accept` — before env creation; logged here because it silently
  empty-fails in scripts otherwise.)
- **Env-level smoke test** (README §Quick Start, docker provider):
  `python quickstart.py --provider_name docker --os_type Ubuntu` — first run
  downloads the Ubuntu qcow2 from HuggingFace into `./docker_vm_data`.
  RESULT: [filled after run]
- **Note on quickstart's `--headless`**: argparse `type=bool` — any string
  parses truthy; irrelevant for the docker provider path we use, noted for the
  record.

## 2026-08-17 — DONE — pre-registration committed BEFORE any run (protocol §1)

`campaign/osworld/tasks-selected.json`: 50 tasks over the 9 protocol domains
(vs_code excluded per protocol), proportional to domain size in
`evaluation_examples/test_all.json` (346 tasks across the 9 domains), min 3
per domain, seed 42. Quotas: chrome 6, gimp 4, libreoffice_calc 7,
libreoffice_impress 7, libreoffice_writer 3, multi_apps 14, os 3,
thunderbird 3, vlc 3 = 50. Sampler committed alongside
(`campaign/osworld/select_tasks.py`), fully deterministic (double-run
diff-identical; quota algorithm documented in its docstring). Amendment rule
embedded in the JSON: no task added/removed after this commit; infra-broken
tasks get `infra_failure` + evidence, never a replacement.

## 2026-08-17 — FYI — condition-B adapter written, first real-tree test pending

`campaign/osworld/distill-osworld.py`: OSWorld AT-SPI XML → prepixel line
grammar (`text/…/[pixels]` lines, spec of `src/distill-hardened.mjs` §3.1),
plus a `--suspects-out` side-channel listing coverage-guard suspects (mute
subtrees ≥150k px², the qBittorrent/OBS shape) for the runner's judgeCrop
spot-check. Honest differences vs the web distiller documented in its header:
no hit-testing through AT-SPI so no `[occluded]` tags; visibility semantics =
OSWorld's own judge_node filter (showing+visible+extents), EXCEPT that
nameless opaque nodes are declared `[pixels]` instead of dropped (dropping
them is precisely the silent-divergence shape the campaign exists to catch).
Tested against the real a11y tree captured during the smoke run: [filled
after run]
