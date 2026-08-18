# Anthropic research credits — application package (ready to submit)

> **Read this first.** The authoritative, ready-to-paste text is the
> **"FORM ANSWERS"** section at the bottom of this file. Paste each block into
> the matching form field, verbatim. Everything between here and that section
> is the earlier draft, kept for history — its budget figure ($100, single-run
> design) is **superseded** by the itemised $550 / 3-repetition plan below.

**Where to apply (check both, they change):**
1. https://www.anthropic.com/research — section "researcher access" / external
   researcher program (free API credits for independent researchers; form).
2. https://support.claude.com → contact form, category research/academic, if
   the dedicated form is closed. The "AI for Science" program page
   (anthropic.com/news/ai-for-science-program) also links the current
   application route for academic credits.

**What you need on hand:** an Anthropic Console account (free), your
affiliation (independent researcher is fine — say so plainly), the public
GitHub repo URL, and the two commit hashes below (pre-registration proof).

---

## Superseded draft (2026-08-17, kept for history)

**Project title:** Structured accessibility-derived observations vs.
screenshots for computer-use agents: a pre-registered A/B comparison on
OSWorld.

**Applicant:** Léandre Carpentier, independent researcher
(carpentier.leandre@gmail.com). Public repo:
https://github.com/Leandree/prepixel

**Abstract (150 words).** Computer-use agents overwhelmingly consume
screenshots, which are token-expensive and lossy. We built "prepixel", a
structured observation channel that distills OS accessibility trees into a
compact line grammar, hardened by a pixel-based coverage guard that converts
silent blind spots (custom-painted widgets invisible to accessibility APIs)
into explicit declarations. A 76-cell characterization campaign across
Windows/macOS/Linux measured the channel's coverage and failure classes. Peer
review asked the natural next question: does any of this matter *agent-level*?
We propose a pre-registered comparison on OSWorld (public benchmark, Ubuntu
VM): 50 stratified tasks × 2 conditions (screenshot-only vs. structured
view), same model, same scaffold, temperature 0, interleaved, mechanical
evaluators, no cherry-picking — task list and prompts committed before the
first run. We measure completion rate and real token cost per task. Results
publish either way; negative results are informative.

**Why Claude / the API.** The paper's cost accounting uses Anthropic's public
image-token formula; claude-sonnet-4-6 accepts temperature=0 (required by our
pre-registered protocol) and is strong enough at computer use to avoid floor
effects that would make the A/B contrast uninformative. The unmodified
OSWorld reference agent supports Anthropic models natively, so the API run
uses the benchmark's own scaffold, unmodified — maximal comparability.

**Methods & integrity.** Pre-registration committed before any run: task
subset (seed-42 stratified sample of 50 tasks over 9 OSWorld domains, commit
fb5fdfc), frozen symmetric prompt template and condition driver
(same commit), protocol with interleaving, no-re-run rule, and per-task
JSON schema (campaign/OSWORLD-PROTOCOL.md). Success is judged by OSWorld's
mechanical evaluators; all traces are published in the repo.

**Data & safety.** OSWorld is a public benchmark running in a local VM; no
personal data, no live third-party accounts (the protocol's read-only
discipline), no dual-use content. The model performs ordinary desktop tasks
(office suites, browser, media player).

---
---

# FORM ANSWERS — paste these, verbatim

Seven fields, in the order the form presents them. Fenced blocks are the exact
text to paste; unfenced lines tell you which option to click. Word counts are
verified against the stated caps.

---

## FIELD 1 — "brief description of the individual applicant or team, including the relevant expertise" (cap 200 words; this is 181)

```
I am Leandre Carpentier, an independent researcher working alone from home, with no institutional or corporate affiliation and no external funding.

Relevant expertise: I built and characterised "prepixel", a structured observation channel for computer-use agents that distills OS accessibility trees, toolkit render trees and document models into a compact line grammar instead of screenshots. That work had to be done at the level where the claim is actually decided: Windows UI Automation, macOS AXAPI, Linux AT-SPI, GTK4's render tree (hooked at gsk_renderer_render), LibreOffice's UNO document model, and Anthropic's published image-token formula for exact cost accounting.

The campaign behind it is 76 measured cells across Windows, macOS and Linux. Its most important result was negative: six applications diverged from what was actually painted without declaring it, which is what forced the two runtime guards that now convert those blind spots into explicit declarations.

I work with pre-registration and blind independent replication passes (3/3 match), and I publish the misses -- one silent case was published before I could catch it, and that miss is what recalibrated the guard.

Everything is public: github.com/Leandree/prepixel
```

---

## FIELD 2 — "describe your research or request for free API credits" (cap 300 words; this is 297)

```
Topic. Computer-use agents read the screen as pixels: ~1,000-4,800 vision tokens per screenshot, re-interpreted even when nothing changed. I built a structured alternative -- accessibility trees and document models distilled into a compact line grammar -- measured across 76 cells on three operating systems.

That measures an agent's input; it never measures an agent. The campaign I need credits for is a pre-registered A/B comparison on OSWorld: 50 stratified tasks x 2 conditions, screenshot observation vs the structured view, same model, same scaffold, same step limit, interleaved, scored by OSWorld's mechanical evaluators. Task list, prompt template and driver were committed before the first run (commit fb5fdfc). Metrics: completion rate and real token cost per task.

Why free credits matter. This is a methodology requirement more than a funding one. OSWorld is meant to be run by its own reference agent calling the model API directly. With no API access, my pilot ran through a personal Claude Code subscription: an agent harness between model and benchmark. That injects a system prompt I cannot fully publish, per-step subagent overhead (~20-22k tokens per spawn) contaminating the token-cost metric that is half my result, and a session alias, not a pinned model string. It also gives no sampling control, while my pre-registration fixes temperature=0 so temperature is not a free variable between conditions.

Credits let the campaign run as the benchmark is designed: unmodified reference agent, direct API calls, pinned model strings, temperature=0, everything identical except the observation channel.

Budget. One A/B arm is ~8M input + ~0.4M output tokens. I request $550, itemised in the additional information: three repetitions per task and condition so the contrast carries an error bar, three capability tiers that still accept temperature=0, and a Windows replication on WindowsAgentArena, scored mechanically. Phase one alone is $120.
```

---

## FIELD 3 — "Are you requesting more than $1000 API credits?"

Select **No**. Leave the "Autre / Other" box **empty** — $550 is under the
threshold, and the itemised budget goes in Field 6.

---

## FIELD 4 — quality of service

Select **"I'm fine with receiving a low quality of service."**

(Reason, for you, not for the form: the workload is offline batch benchmark
runs with no latency requirement, every step is retryable, and the protocol
already logs `infra_failure` with evidence. Capacity errors cost wall clock,
not validity — so asking for standard QoS would buy nothing and weaken the
application.)

---

## FIELD 5 — "link to your Google Scholar profile or github profile"

```
https://github.com/Leandree/prepixel
```

---

## FIELD 6 — "Additional Information … any additional context or considerations for the review committee" (optional, no cap)

```
Pre-registration is verifiable before you grant anything: the 50-task seed-42 stratified sample, the frozen symmetric prompt template and the condition driver were committed in fb5fdfc, and the protocol (campaign/OSWORLD-PROTOCOL.md) fixes interleaving, a no-re-run rule and a per-task JSON schema. The 76-cell characterisation that motivates the comparison is in the same repo, including a surviving silent-failure case I published before I could catch it.

A 4-run pilot on tasks deliberately outside the pre-registered 50 is already done: 4/4 success, both runtime guards exercised, zero infrastructure failures, full step-by-step traces published (campaign/results/osworld-pilot/). One OSWorld arm is roughly 10-12 hours of VM wall clock. This is a funding and access gap, not an engineering one.

Budget, itemised, $550 total. One A/B arm is 100 runs (50 tasks x 2 conditions), roughly 8M input and 0.4M output tokens.
- Phase 1: OSWorld A/B on claude-sonnet-4-6 at temperature=0, 3 repetitions per task and condition, 300 runs -- about $90
- Phase 1: smoke tests and documented infrastructure-failure re-runs -- about $30
- Phase 2: capability-tier panel, the same design on claude-haiku-4-5 and on an Opus-tier model, 3 repetitions each, 600 runs -- about $180
- Phase 3: the application classes this channel is already known to fail on (custom-painted widgets, game engines), the cases my two runtime guards exist for -- about $80
- Phase 4: Windows replication on WindowsAgentArena, 50-task stratified subset x 2 conditions, 3 repetitions, 300 runs -- about $90
- Re-runs required by a protocol amendment found mid-campaign, each amendment committed before its re-run -- about $50

Phase 1 is the result I commit to. Phases 2 to 4 are contingent on phase 1 producing a usable contrast, and each gets its own pre-registered amendment committed before its first run.

Two design notes behind those lines. Repetitions: one run per cell gives a difference with no variance estimate, so a small margin could not be told apart from agent noise; three repetitions per task and condition is the minimum that lets me report a spread rather than a point. Model panel: the three tiers are not chosen for coverage but because a structured observation channel should plausibly help a weaker perceiver more than a stronger one -- a flat effect across tiers would itself be a result. The panel is restricted to models that still accept temperature=0, since the pre-registration fixes it and current-generation models reject the parameter.

Model choice is therefore constrained by the pre-registration rather than by preference, and claude-sonnet-4-6 is the current model that still accepts the parameter. I am not claiming temperature=0 makes runs bit-identical; it removes sampling temperature as a free variable between the two conditions, which is what this comparison needs.

The subscription pilot's deviations are documented in the repo rather than quietly absorbed (campaign/results/osworld-agent-returns.md): session model alias, no sampling control, harness system prompt not fully publishable, and coverage-guard crops taken from the VM full-screen capture because OSWorld's observation API exposes no per-window surface. An API-native run removes the first three.

One scope limit I want to state rather than have you infer: I am not requesting agent-level runs on macOS. My 76-cell characterisation is cross-OS, but OSWorld and WindowsAgentArena are trustworthy here because their evaluators are mechanical, and I have no macOS equivalent. Hand-scored tasks would reintroduce exactly the judgement this design removes, so macOS stays characterisation work until a mechanically-scored target exists.

No dual-use content: these benchmarks run in local VMs on ordinary desktop tasks (office suites, browser, media player), with no personal data and no live third-party accounts.
```

---

## FIELD 7 — "Are you located within the United States?"

Select **No** (France).

---

## Checklist before submitting

- [ ] Repo is public and the two commits are pushed (`fb5fdfc` pre-registration,
      `2929bca` pilot traces) — a reviewer who clicks the link must land on
      them.
- [ ] Word counts still under cap if you edit anything (181/200 and 299/300 —
      there is almost no slack in Field 2).
- [ ] Phase 4 stays in the budget only if you have checked that
      WindowsAgentArena runs on your hardware and that you can write the UIA
      side of the condition-B adapter. If either is unclear, delete the Phase 4
      line and request $460 instead.
- [ ] No confidential content anywhere — the form states submissions are
      treated as non-confidential.
