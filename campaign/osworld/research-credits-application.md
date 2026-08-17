# Anthropic research credits — application package (ready to submit)

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
Budget ask: **$100** (campaign ≈ $25–45 on claude-sonnet-4-6 + margin for
documented infra_failure re-runs and the agent-level smoke test).

---

## Ready-to-paste application text (English)

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

**Budget & timeline.** ≈8M input + 0.4M output tokens ≈ $30–45 on
claude-sonnet-4-6; requesting $100 to cover documented infra-failure re-runs
and the smoke test. Runs complete within 2 weeks of credit grant.

**Data & safety.** OSWorld is a public benchmark running in a local VM; no
personal data, no live third-party accounts (the protocol's read-only
discipline), no dual-use content. The model performs ordinary desktop tasks
(office suites, browser, media player).

---

## Form answers — verbatim, ready to paste (2026-08-17)

Field-by-field for the current Anthropic external-researcher form. Word counts
verified against the stated caps. Post-pilot: figures below reflect the
measured pilot (4/4 success, ~350k subagent tok/run incl. harness overhead;
the API-native metric stays ~8M input + 0.4M output for the 100 runs).

### 1. Applicant / team description (cap 200 words — this is 181)

I am Leandre Carpentier, an independent researcher working alone from home,
with no institutional or corporate affiliation and no external funding.

Relevant expertise: I built and characterised "prepixel", a structured
observation channel for computer-use agents that distills OS accessibility
trees, toolkit render trees and document models into a compact line grammar
instead of screenshots. That work had to be done at the level where the claim
is actually decided: Windows UI Automation, macOS AXAPI, Linux AT-SPI, GTK4's
render tree (hooked at gsk_renderer_render), LibreOffice's UNO document model,
and Anthropic's published image-token formula for exact cost accounting.

The campaign behind it is 76 measured cells across Windows, macOS and Linux.
Its most important result was negative: six applications diverged from what was
actually painted without declaring it, which is what forced the two runtime
guards that now convert those blind spots into explicit declarations.

I work with pre-registration and blind independent replication passes (3/3
match), and I publish the misses — one silent case was published before I could
catch it, and that miss is what recalibrated the guard.

Everything is public: github.com/Leandree/prepixel

### 2. Research / request description (cap 300 words — this is 299)

Topic. Computer-use agents perceive the screen as pixels: one screenshot per
step, ~1,000–4,800 vision tokens each, re-interpreted from scratch even when
nothing changed. I built a structured alternative — accessibility trees and
document models distilled into a compact line grammar — and measured it across
76 cells on three operating systems.

That measures an agent's input; it never measures an agent. The campaign I need
credits for is a pre-registered A/B comparison on OSWorld: 50 stratified tasks
× 2 conditions, standard screenshot observation vs the structured view, same
model, same scaffold, same step limit, interleaved, scored by OSWorld's own
mechanical evaluators. Task list, prompt template and condition driver were
committed before the first run (commit fb5fdfc). Metrics: completion rate and
real token cost per task.

Why free credits matter. This is a methodology requirement more than a funding
one. OSWorld is meant to be run by its own reference agent calling the model
API directly. Having no API access, my pilot ran through a personal Claude Code
subscription: an agent harness between the model and the benchmark. That
injects three uncontrolled variables: a harness system prompt I cannot fully
publish, per-step subagent overhead (~20–22k tokens per spawn) contaminating
the token-cost metric that is half my result, and a session model alias instead
of a pinned model string. It also gives no control over sampling, while my
pre-registration fixes temperature=0 so temperature is not a free variable
between conditions.

Credits let the campaign run the way the benchmark is designed to be run:
unmodified reference agent, direct API calls, one pinned model string,
temperature=0, everything identical except the observation channel. Then the
cost numbers are the model's own and the traces are fully publishable.

~8M input + ~0.4M output tokens, ~$30–45 on claude-sonnet-4-6; asking $100 to
cover documented infrastructure-failure re-runs.

### 3. More than $1000?

**No.** (Ask is ~$100.)

### 4. Quality of service

**I'm fine with receiving a low quality of service.** The workload is offline
batch benchmark runs with no latency requirement; every step is retryable and
the protocol already logs `infra_failure` with evidence, so capacity errors cost
wall clock, not validity.

### 5. GitHub / Scholar link

https://github.com/Leandree/prepixel (profile: https://github.com/Leandree)

### 6. Additional information (optional)

Pre-registration is verifiable before you grant anything: the 50-task
seed-42 stratified sample, the frozen symmetric prompt template and the
condition driver were committed in fb5fdfc, and the protocol
(`campaign/OSWORLD-PROTOCOL.md`) fixes interleaving, a no-re-run rule and a
per-task JSON schema. The 76-cell characterisation that motivates the
comparison is in the same repo, including a surviving silent-failure case I
published before I could catch it.

A 4-run pilot on tasks deliberately outside the pre-registered 50 is already
done — 4/4 success, both guards exercised, zero infrastructure failures, full
step-by-step traces published (`campaign/results/osworld-pilot/`). The full
campaign is ~10–12 h of VM wall clock and completes within two weeks of a
grant.

Model choice is constrained by the pre-registration, not by preference: the
protocol demands temperature=0, and claude-sonnet-4-6 is the current model that
still accepts the parameter — Sonnet 5, Opus 4.7/4.8 and Fable 5 reject it,
which would also mean modifying OSWorld's reference agent. The same string is
used for both conditions. I am not claiming temperature=0 makes runs
bit-identical; it removes sampling temperature as a free variable between the
two conditions, which is what the comparison needs.

The subscription pilot's deviations are already documented in the repo rather
than quietly absorbed (`campaign/results/osworld-agent-returns.md`): session
model alias, no sampling control, harness system prompt not fully publishable,
and guard crops taken from the VM full-screen capture because OSWorld's
observation API has no per-window surface. An API-native run removes the first
three.

No dual-use content: OSWorld runs in a local VM on public benchmark tasks
(office suites, browser, media player), with no personal data and no live
third-party accounts.

### 7. Located in the United States?

**No** (France).
