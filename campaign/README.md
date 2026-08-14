# Campaign — multi-OS coverage & safety tests

This folder drives a reproducible campaign to map **where** rendering-pipeline
perception works, where it fails, and whether its boundary is **predictable enough to
be safe for production**.

## Files

- `PROTOCOLE.md` — master protocol (FR): hypotheses, coverage matrix, the "safe"
  (predictability) criterion, deliverables.
- `agent-brief-COMMON.md` — read first: the core H5 question, the T1–T6 battery,
  strict output format, scope discipline.
- `agent-brief-windows.md` / `agent-brief-macos.md` / `agent-brief-linux.md` —
  OS-specific channel maps and app lists.
- `results-schema.json` — JSON schema every result file must validate against.

## How Léandre runs it

On each machine, hand a native coding agent (e.g. Claude Code) the COMMON brief plus
that machine's OS brief, and this repo. The agent probes the listed apps, runs T1–T6,
and writes `results/<os>-<app>-<channel>.json` (+ `results/<os>-FINDINGS.md` and
evidence under `results/artifacts/`).

Collect all `results/*.json` back into this repo. An aggregation script (to be
added) will produce the coverage matrix and the predictability table — the two
figures that decide the paper's verdict on production-safety.

## The verdict we're after

Not "does it work" (we know it sometimes does) but: **can a router know in advance,
from a detectable signature, which channel is available and what it covers — and does
the channel fail explicitly rather than silently?** If yes, the approach is a safe
production primitive with a documented perimeter. If the working set is
unpredictable or fails silently, that is the honest negative the paper must report.
