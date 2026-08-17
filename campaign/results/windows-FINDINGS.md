# Windows — field notes (claude-code, live desktop PC, Windows 11 Pro 26100, 2026-08-15)

Ran on a **live, in-use machine** (the user present part of the time — their
Notepad session, Discord, Spotify and a real OBS/FL Studio/rekordbox config on
screen), French locale, single 1080p panel at 100%. **19 cells over two
rounds** (round 2 after the user answered the UAC dialog and installed Office).
Windows delivered what the other two OSes didn't: **the first genuinely
silent-class divergences of the campaign** (3), plus a boundary neither macOS
nor Linux has — the **integrity level (elevation) wall** — and, on the way,
live demonstrations of nearly every failure mode the briefs warned about. It
also delivered the study's strongest structured-cost win: **the Word
document read as 18 tokens** — against a window screenshot whose cost scales
with size, so ~80–150x depending on window geometry (80x non-maximized, 150x
maximized per the 2026-08-17 replication). The 18-token invariant is the
headline; the multiplier is the caveat.

## The two silent cells — found where the brief said to look

- **Qt's accessibility bridge (OBS Studio).** The dock semantics are excellent —
  named sliders WITH their current dB values, mute states, selected scene — but
  the video-preview region, which on screen displays a text source ("On arrive
  bientôt"), is covered by an **anonymous QWidget group**: no text, no image
  role, no opacity marker. A consumer asking "what does the preview show?" reads
  *nothing there* and is wrong, unwarned. Unlike the browser's `[pixels]` lines
  or Paint's *named* canvas group, nothing distinguishes "empty pane" from "pane
  full of painted content".
- **FL Studio (fully custom-drawn)** — the same class at whole-app scale: a
  52-node all-`PaneControl` tree whose ~15 nodes carry region captions
  ("Browser", "Channel rack", "Recent projects") and whose content is entirely
  painted. The welcome wizard's *Recent projects* grid node had **zero children**
  while the screen listed the user's projects inside its rect.

- **rekordbox 7 (JUCE)** — round 2, and the most instructive shape of the three:
  the *chrome* refutes FL Studio (549 nodes, 141 named buttons, 17 sliders, live
  state values — deck 'Not Loaded.', BPM '120.00', status '32 Tracks…' — JUCE
  ships an accessibility layer and Pioneer wired it; custom-drawn ≠ silent, the
  boundary is **developer annotation**, the Windows twin of macOS Chess), while
  the *track-browser grid* re-confirms the silent class in a third variant:
  **11 declared column headers, zero rows**, against a screen listing 32 tracks.
  Distinctive nuance: the view is *self-inconsistent in a detectable way* (the
  in-channel '32 Tracks' count contradicts the empty table) — a router heuristic
  ('headers + count>0 + no rows = unexposed list') can flag it from the view
  alone, but nothing declares it, so it is recorded silent.

The taxonomy the Windows data forces: **explicit-by-shape vs silent-by-mimicry.**
Unigine Heaven (a running 3D scene) exposes a *frame-only* tree — 7 nodes, zero
content children — which cannot be mistaken for coverage: a router computes
"structural coverage of client area = 0%" in one walk and routes to pixels.
FL/OBS are the dangerous shape: named containers that *look* like structure and
read as "empty". Both are **predictable a priori** (Qt DLLs / Delphi window class
+ all-Pane tree = the signature), and both are catchable at runtime — we added
`PrintWindow(PW_RENDERFULLCONTENT)` to the probe library, which captures a
window's own surface *without focus*, precisely to pair per-window pixels with
per-window structure. But predictable-and-catchable is not declared: recorded as
silent, per the campaign's own standard.

## The Windows-only boundary: integrity levels

Task Manager auto-elevates on an admin account (no dialog). Measured from a
Medium-IL client: the elevated window is **absent from the UIA root
enumeration entirely** — a whole visible, maximized window missing from "what's
on screen" — while `ControlFromHandle` on its HWND returns an honest 1-node
stub. UIPI blocks input and `WM_CLOSE` symmetrically (reads and writes fail
together), and even `PrintWindow` is refused; only screen-crops see it. The
saving grace, and the reason this is *blocked* rather than silent: **the Win32
window map still sees everything** (hwnd, title, rect, z-order) and
`TokenElevation` answers *before* probing. On Windows the WM map is not a
convenience — it is the mechanism that keeps the elevation blind spot explicit.
The router cell measured it live: 10 windows mapped in 1.0 ms / 201 tokens,
elevated window flagged `[elev] -> pixels-crop`, on a desktop whose full
screenshot costs 2765 tokens.

Corollary for autonomous agents: **UAC is a hard human-in-the-loop step.** The
consent dialog lives on the secure desktop, unreachable at any IL we can hold;
worse, an unanswered prompt holds the Windows Installer service lock, so every
later MSI operation fails with 1618. Our LibreOffice provisioning died there
(machine-scope-only MSI, per-user no-op, admin-extract locked) — recorded as the
blocked office-object-model cell. The block was **exactly one human click
wide**: the user answered the dialog (and installed Office while at it), and
round 2 completed the star cell the same day. One last routing datum from that
unblock: the LibreOffice MSI still never landed — the consent the user granted
belonged to an msiexec whose parent we had already killed, and **an elevation
granted to an orphaned request installs nothing, silently**. After any elevated
step, verify the artifact, never the click.

The object-model family on Windows, now measured end to end:
- **Word via COM — the Tier C star, and the strongest structured-cost win in
  the study**: the document read in **4.6 ms / 18 tokens** — the invariant to
  quote — against a window screenshot whose cost scales with window area, so the
  ratio is geometry-dependent: 1446 tokens / **~80x** at the non-maximized window
  measured here, **~2706 tokens / ~150x** when the 2026-08-17 replication reopened
  Word maximized (Linux UNO was ~65x). Read it as "18 tokens vs a window
  screenshot, ~80–150x by window size". Writes in 14.5 ms, char-exact
  unicode, live in both directions (keyboard-typed text appears in
  `Range().Text`; COM-written text appears in UIA's TextPattern), and inserted
  pictures are **first-class objects** (InlineShape, type+dimensions) rather
  than declared rects. One methodological trap worth keeping: our distiller
  first reported the COM-written text absent from UIA — it only queried
  ValuePattern; Word serves the document via **TextPattern**. The router
  under-used the view again; the view was honest.
- The always-installed object model is the **shell itself**: `Shell.Application`
  COM read our probe folder in 10 ms / **28 tokens** (vs 1470 UIA / 974 pixels),
  wrote selection state in 8 ms with no coordinates, cross-verified through the
  independent UIA channel — the Windows sibling of UNO (21 tok) and
  Pages/AppleScript (21 tok).

## The foreground lock: the incident that pays for two guards

Round 1 of the Calculator cell failed the way the macOS TOCTOU incident did,
but for a Windows-specific reason: `SetForegroundWindow` was **silently denied**
(foreground lock), Calculator stayed behind Notepad, and three
channel-coordinate blind clicks landed in the user's Notepad text area (caret
moves only; the accidental window screenshots — which captured the user's file
content — were purged and retaken). Two guards now in the probe library, both
exercised for real: (1) *force-and-verify* foreground (ALT-nudge +
`GetForegroundWindow` check — never trust the call), and (2) a **pre-click
hit-test**: `ControlFromPoint(x,y) -> GetTopLevelControl` must be the intended
window. The first version of that guard compared PIDs and **false-blocked**,
revealing the UWP split: the frame window belongs to `ApplicationFrameHost.exe`,
its content to `CalculatorApp.exe` — guard on the top-level window, not the pid.
With both guards in place the blind battery went clean: 2+3= driven entirely
from view-line coordinates, result read in-channel ("L'affichage est 5"),
confirmed by pixels after the fact. Same lesson-set, later: when pixel space is
contested, `InvokePattern` acts without coordinates at all (used, allowlisted,
to answer OBS's own safe-mode dialog after our force-kill caused it).

## The Windows AT-latch, quantified

Chromium on Windows has the macOS latch, but *self-arming*: walk 1 returns 257
nodes of browser chrome with **no page content**; the walk itself is the
assistive-client signal; walk 2, ~1.2 s later, returns 328 nodes with the full
page. No flag, no `AXEnhancedUserInterface` incantation, no error codes. Same
channel comparison as macOS, same conclusion: UIA view of the page = 969 tok /
~200 ms; CDP view of the same screen = 273 tok / 8 ms — but UIA sees browser
chrome and speaks screen-global, directly clickable coordinates. Pair them.

## Cost: the density law holds on native Windows — and inverts twice

The duel replicates **to the token** on the third OS: 391 structured vs 1366
image tokens (3.49x), and the blind-subagent accuracy run is again
**18/18 vs 18/18** — parity on legible screens, three OSes now. But the native
cells show the same density inversion the real-web battery showed: **Calculator's
window screenshot (243 tok) is 2.7x cheaper than its structured view (666 tok)**
— a small, control-dense panel is the native Hacker News — and Explorer
(1470 vs 974) and Paint (1901 vs 1770) sit near break-even. Where structure wins
without contest, as everywhere else, is **change and idleness**: the Win32
Date-and-Time clock ticks at ~80 B (~20 tok) per second against a 299-token
re-shot; the Chrome feed at 120–239 B/tick against 1366; idle is 0 bytes in
every cell measured. Capture latencies stratify by bridge: CDP 8–23 ms, Win32
proxies ~37 ms, WinUI/XAML 70–250 ms, Qt 470–640 ms — all far under a
screenshot round-trip, none as fast as CDP.

The DPI story on Windows inverts the macOS framing: display *scaling* doesn't
change capture cost (screenshots are physical pixels; this panel is 1920x1080 at
any %), so on plain 1080p a full-screen look costs 2765 tokens on high-res
models — already 2x the 1280x800 reference — and the Retina-class trap moves to
*panel resolution* (4K -> 4785/1534 by tier; naive `w*h/750` would claim 11060).
What scaling breaks instead is **coordinates** (UIA is physical-px; a
DPI-unaware client gets virtualized px). This machine runs 96 DPI, so that trap
is documented, not demonstrated — stated honestly; every probe here was
per-monitor-DPI-aware as the brief mandates.

## Small prints worth keeping

- **The channel is faithful to the screen, not the filesystem**: Explorer items
  are named 'alpha'/'gamma' (hidden extensions) exactly as painted — my probe's
  first "failure" was comparing against filesystem names. The Shell COM model
  follows the same display rule.
- **Win32's 1990s accessibility is quietly excellent**: the timedate dialog's
  custom-drawn *analog* clock declares the digital time as its accessible name,
  ticking every second; error dialogs (Unigine's fatal error) arrive as perfect
  6-node trees. The most safety-critical text an agent meets — OS errors —
  lives on the structured side even at the edge of pixels territory.
- **Pixels-only semantics exist in the other direction too**: the UAC shield
  glyph on "Changer la date et l'heure..." (the needs-elevation affordance) has
  no structured representation. Monaco/VS Code splits each code line into
  syntax-token spans — reconstructable by y-join, the Electron mirror of
  glyph-run fragmentation.
- **XAML dual-role duplicates** (menu items and breadcrumb parts appearing twice)
  inflate UIA views ~10%; a distiller dedupe pass would claw back cost.
- **1 Hz polling drops ticks** (capture latency 100–270 ms stacked on sleep
  skipped a second on the clock); production routers should subscribe to UIA
  events, not poll.
- **Stale handles fail explicitly here**: after closing a Notepad tab, the held
  element's `GetPattern(ValuePattern)` returns None rather than a phantom value
  — better behaved than the macOS caret-remnant case.
- Ops incidents, all kept in the JSONs rather than smoothed over: the Clock app
  answered first probe with an honest "update needed" splash and later launched
  *itself* mid-campaign (its deferred update completing), covering OBS at
  screenshot time — the very occlusion class we test for, caught by our own
  ground-truth check; OBS's safe-mode dialog after a force-kill; Heaven's
  `-data_path` error; my own harness expectation bugs (extension-less names,
  'Est égal à' vs 'Égal à') — as on macOS, **when the router misfires, suspect
  the router before the view: in every case the view was honest.**

## Permissions ledger (the Windows thesis in one list)

Everything in this campaign — UIA reads on every unelevated app, blind clicks,
Shell COM reads AND writes, CDP on flag-launched browsers, PrintWindow captures
— ran with **zero permission grants, zero dialogs, zero configuration**, as a
plain Medium-IL user process. Windows is the most permissive OS of the three
exactly as the brief predicted. The two walls it does have are absolute for an
autonomous agent: the **integrity boundary** (elevated UI: pixels-only without
a signed uiAccess client) and **UAC consent** (secure desktop, human-only).
macOS gates the channel behind one human toggle; Windows gives the channel away
and gates *power* instead.

---

# Deepening round (2026-08-17) — closing the DEEPENING-PLAN's Windows items

**P0 — the mitigation, proven on the real silent apps.** All three re-opened
(read-only) and run through coverage-guard:

- **OBS**: the guard *auto-found* the exact silent region ('OBSBasicPreview',
  the only structure-empty rect >150k px² in a 46.5%-covered client area),
  energy **0.245** → re-emitted `[pixels] group … [unverified: pixels show
  content]`. The evidence crop literally shows the painted "On arrive bientôt".
  Cost: PrintWindow 30 ms + guard 2.5 ms; the crop is 245 tokens vs 1275 for a
  full-window shot.
- **FL Studio**: 5 suspects auto-found (both wizard grids incl. Recent
  projects, the browser tree, the playlist panel, the toolbar), energies
  0.085–0.621, **5/5 flagged**; crops total 1780 tok < 2642 full-window — the
  guard stays sub-screenshot even when the whole app is painted.
- **rekordbox**: guard A found *nothing* — the table rect contains named
  headers, so it isn't structure-empty — and guard B caught it **from the view
  alone, for free**: '32 Tracks' + 0 rows → `[inconsistent … unexposed list,
  crop]`. The case that proves the two guards are independent and both needed.

The three cells now carry `failure_class: explicit` + a `mitigation` record;
the aggregate reads **0 silent survivors, 3 caught-and-declared**.

**P1 — the coordinate trap, demonstrated live at 125%.** Panel switched 96→120
DPI (reverted and re-verified after). UIA published the timedate tab at
physical (588,358); a deliberately DPI-unaware executor was handed exactly
that and *its own GetCursorPos then echoed (588,358)* — the virtualization
lies to the process about its own miss — while the real cursor sat at
**(735,448)** (=×1.25): tab stayed unselected. One move-and-measure probe
((320,320)→(400,400), scale 1.25 measured), corrected hand-off (470,286) →
landed exactly (588,358) → `[selected=True]` in-channel. Bonus: the safety
precondition (predicted-landing-inside-harmless-zone) aborted the first
attempt against Calculator — mis-scaled clicks land 25% down-right, far enough
to exit the window; bound the blast radius before any uncalibrated click.

**P2 — the two missing tiers + the dedupe.**

- **WPF** (PresentationFramework, no SDK needed): full battery green, 130 tok
  vs 314, capture ~35 ms, everything named out of the box — even a
  Canvas-hosted TextBlock stays structured (the anti-FL-Studio: a retained
  element tree never rasterizes semantics away). Round-1 harness bug kept: a
  BOM-less .ps1 made the APP display mojibake and UIA reported the mojibake
  faithfully — the screen lied, the channel didn't.
- **Java/Swing** (portable JDK, no admin): UIA sees the Heaven shape (7 chrome
  nodes, 4.6% coverage) — which exposed the guard's own blind spot: a
  frame-only tree offers *no container to check*. Fixed
  (`synthesize_client_suspect`): coverage≈0 ⇒ the client area itself becomes
  the suspect; energy 0.186 → declared. Then the **Java Access Bridge**
  channel end-to-end: `jabswitch -enable` (per-user) + the explicit
  `-Djavax.accessibility…AccessBridge` JVM flag + a 60-line ctypes client →
  isJavaWindow TRUE, full tree (roles/names/rects) in **21.7 ms**. Two
  handshake gotchas documented: the JVM-side AT flag beats
  `.accessibility.properties`, and the client must pump ALL messages (a
  starved pump reads isJavaWindow=false forever).
- **Dedupe pass** (`uia_probe.dedupe_view`): 9151→8637 tok over 9 saved views
  (**5.6%**), concentrated exactly where dual-publication lives — Chromium-UIA
  16.9%, WPF 12.3%, Notepad/WinUI 10.6% (confirming the round-1 ~10%
  estimate), ~0% on Qt/JUCE which don't dual-publish. Pure post-pass, no API
  cost, duplicates only.

**Real-web battery, third OS (added on the manager's request).** 16/16 sites,
same URLs as macOS, and the replication is to two decimals: ratio of totals
**0.99** (macOS 1.00), median **1.15** (1.21), mean **1.28** (1.30), structure
ahead **11/16** (10/16) — with per-site echoes like Vercel 3.12 vs 3.11,
Hacker News 0.46 vs 0.47, Wikipedia 0.72 vs 0.72 across different days,
locales and cookie states. The density law is a property of the pages, not of
the OS or the renderer instance. FR locale raised more consent banners (8/16
vs 6/16); 7/16 sites carry canvas/video, all declared.

**Real games, both engines (manager's request).** SILENT HILL 2 (UE5, AAA,
borderless): **1 UIA node** for a full in-engine scene at 54 fps — borderless
sheds even the 7 chrome nodes Heaven had. R.E.P.O. (Unity, fullscreen menu at
576 fps): **1 bare PaneControl** while the screen shows eight clickable menu
items — the starkest structure-vs-screen gap of the campaign, guard energy
0.825 (record). PrintWindow captures both swapchains; the guard declares both
surfaces. The finding beyond the expected zero: **Unity's fullscreen window is
a Pane, not a Window — a UIA WindowControl search misses a running fullscreen
game entirely** while Win32 sees it; the second no-privilege instance of the
enumeration blind spot (after the elevated Task Manager). Doctrine, now
twice-proven: derive window identity from the Win32 map + ControlFromHandle,
never from UIA name/type searches. Anticheat titles (CS2, GTA V Enhanced,
Once Human, Rocket League) were excluded by policy from probing. One
interpretation corrected by the user's review, leaving a sharper lesson: the
in-engine frame captured before WM_CLOSE was first read as interrupted
gameplay; it is far more likely the UE5 title/attract sequence (zero input was
ever sent). The point that survives: at close time the probe could not
DISTINGUISH menu-idle from human-play — lifecycle actions on a live machine
need a recent-input check (GetLastInputInfo) before firing, because
provenance alone cannot answer "is a human in this session right now?".

## What's still open

Nothing Windows-side from the plan. None of this blocks the Windows verdict:

**Verdict (updated after the deepening round): everything was predictable a
priori (23/23 cells carry their signature); the three silent cells the
campaign found are exactly where the brief pointed (custom-drawn content
behind thin accessibility bridges: Qt anonymous container, Delphi named-empty
panes, JUCE headers-without-rows) — and every one is now CAUGHT-AND-DECLARED
by the measured coverage-guard run against the real apps, at sub-screenshot
cost. The coordinate trap is demonstrated, not just encoded. Every tier is
measured or explicitly signatured — including WPF (fully structured) and
Java (UIA-blind but with its own 21-ms structured channel). The annotation
counter-example (rekordbox's chrome) and the 18-token star case (Word, ~80–150x
vs a window screenshot by size) complete
the picture: where developers or document models speak, structure is
unbeatable; where they are silent, the router's documented guards convert
the blind spot to an explicit declaration.**
