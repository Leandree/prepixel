# Agent brief — COMMON preamble (read this first, then your OS-specific brief)

You are an autonomous coding agent running **natively** on one of Léandre's
machines (Windows, macOS, or Linux). You are contributing to a research study on
whether AI computer-use agents can perceive the screen from the **rendering
pipeline's structured representation** (render tree / display list / OS semantic
API) instead of screenshots — and, critically, whether that works **predictably
enough to be safe for production**.

You are NOT trying to prove the idea works. You are trying to **map its real
boundary**: where it works, where it fails, and — most important — whether failure
is *predictable in advance* and *explicit* rather than silent. A channel that
sometimes works but can't be known ahead of time to work is, for our purposes, a
**negative** result. Report it as such, plainly. Negative and "blocked" results
are as valuable as positive ones; do not massage them.

## The core question (H5 — the "safe" criterion)

For every app you probe, answer three things:

1. **Predictable?** Before extracting anything, could a router have *known* which
   channel would be available, from a detectable signature (loaded modules/DLLs,
   linked frameworks, process name, an open debug port, an accessibility-API
   response)? Record the exact signal.
2. **Explicit on failure?** When the structured channel does NOT cover part of the
   screen (a canvas, a custom-drawn region, a game), does it *declare* the gap
   (e.g. an opaque rectangle, an empty node, an error) — or does it silently return
   a view that disagrees with what's actually on screen? A **silent** divergence is
   the disqualifying outcome; hunt for it deliberately.
3. **Verifiable at runtime?** Can you cross-check the structured view against a
   screenshot (ask the same question of both; or re-render the tree and pixel-diff
   where the stack allows)? Report the agreement.

## The standard battery (T1–T6) — run on each app

- **T1 read**: put known text on screen (type a fixed sentence into a field, or open
  a doc containing a known phrase). Extract it through the structured channel.
  Character-exact? Note if text arrives as strings vs glyph IDs (and whether you can
  decode the glyphs).
- **T2 enumerate**: list interactive elements with bounding boxes; compare to what's
  visibly on screen (count, labels, positions).
- **T3 live value**: type a unique string into an input; is the *current* value
  visible in the channel (not just the placeholder)?
- **T4 living screen**: find/open something that updates on its own (a clock, a
  progress bar, a timer, a playing video's controls). Does the channel see the
  change? Sample it a few times: cost per update, and does an idle moment cost zero?
- **T5 blind action**: from channel-derived coordinates ONLY (do not look at a
  screenshot to aim), click a specific target; verify the intended effect happened.
- **T6 pictorial**: on a screen containing an image or canvas, is that region
  declared as an opaque rect you could crop? Or is it silently missing / silently
  full of garbage?

## Measurements to capture per app

Bytes and estimated tokens of the structured view (text: chars/4; image: w·h/750),
bytes of a per-interaction diff, idle cost (should be 0), capture latency in ms,
the stack-detection signature, permissions you had to grant, and the failure class
(`none` / `explicit` / `silent` / `blocked`).

## Output format — STRICT

Produce **one JSON file per (app × channel)** validating against
`results-schema.json` (in this folder). Name them
`results/<os>-<app>-<channel>.json`. Keep raw evidence (dumps, screenshots you took
for verification) under `results/artifacts/` and list their paths in the JSON.

Also append a short prose note per app to `results/<os>-FINDINGS.md`: what surprised
you, any silent-divergence you found, and your honest read on predictability.

## Scope discipline

- Read-only where possible; when you must interact (T3/T5), use throwaway
  documents/fields you created — never modify Léandre's real files or send anything.
- If a channel needs code injection and the OS blocks it (SIP, code signing,
  antivirus), **do not fight it**. Record `verdict: blocked`, `failure_class:
  blocked`, and the exact policy that stopped you. That is a headline result.
- Time-box each app to ~30–45 min. Breadth over depth: better to cover 8 apps at T1–T6
  than to perfect one.
- Prefer the least invasive channel that works, but note ALL channels you could
  detect (e.g. an Electron app exposes both CDP and the OS accessibility tree —
  probe both, they have different coverage/cost).
