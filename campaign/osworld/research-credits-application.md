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
<COMMIT_PREREG>), frozen symmetric prompt template and condition driver
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

*Fill <COMMIT_PREREG> with the pre-registration commit hash after it lands.*
