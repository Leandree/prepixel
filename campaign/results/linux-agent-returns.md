# Linux agent — returns to the test manager

**What this file is.** A two-way log between the Linux agent and the human test
manager. The agent writes here whenever it needs a decision, hits a blocker, or
finds something that changes another agent's work; the manager replies in the same
file under `MANAGER:`. Every OS agent keeps its own — see
`campaign/agent-brief-COMMON.md` § "Returns to the test manager".

**What this file is NOT.** Not the scientific record — measurements go in the
result cells, prose findings in `linux-FINDINGS.md`. This is correspondence.

**Convention.** Newest entry at the top. Each entry dated, with a status:
`DECISION NEEDED` / `FYI` / `BLOCKED` / `DONE`.

---

## 2026-08-17 (round 5) — FYI — the guard spectrum is now five points; 0.03 sits in the middle of real content

Update to the FYI below, with two new measured points from the Tier F cells:
Swing waveform-on-dark panel = 0.036 (caught by 0.006); AppFlowy's ENTIRE login
UI = 0.029 (a whole real screen, under the threshold, because the page is mostly
white). Full spectrum across three OSes: 0.06-0.07 (FL/OBS) / 0.036 (Swing) /
0.029 (AppFlowy full UI) / 0.020 (qBittorrent chart) / 0.000 (every genuinely-
empty control). Threshold 0.01 separates all real content from all empties in
the campaign's data; 0.03 misses or near-misses three real-content cases. The
recommendation below stands, with more force.

Also for the record, the per-window-capture rule now has its X11 implementation
(campaign/linux/grabwin.c, XComposite manual redirection — works on stock Xvfb
with no compositor, reads content under occlusion like PrintWindow) and a
measured Linux verdict flip: screen crop 0.042 vs window surface 0.021 across
the 0.03 boundary with plain window overlap. And two Tier-F interception traps:
java-atk-wrapper execs a hardcoded /usr/bin/xprop (a11y dies without x11-utils —
the -Bsymbolic accident class), and Flutter's bus entry claims toolkit 'gtk'
(the embedder), so the honest Flutter signature is libflutter_linux_gtk.so in
the process, not the toolkit attribute.

---

## 2026-08-17 — FYI — coverage-guard has a FALSE-NEGATIVE regime, complementary to the macOS false-positive one

This concerns whoever owns `src/coverage-guard.mjs` and the Windows agent, whose
P0 mitigation claim ("0 silent survivors") now rests on the 0.03 threshold.

The macOS FYI showed the guard's false-POSITIVE mode (screen-crop through a
transparent overlay inflates energy 129×; rule: per-window capture only). The
Linux qBittorrent cell adds the false-NEGATIVE mode: a real silent region — a
live custom-painted chart (axes, legend, grid, moving curves) whose AT-SPI node
is a nameless `kids=0` filler — measures contentEnergy **0.020**, under the 0.03
threshold that was calibrated on the densely-painted Windows shapes (0.06–0.07).
As shipped, guard A calls the painted chart "genuinely-empty". Sparse line-art
(thin curves, dashed grid, small text on white) is a regime the calibration
never saw.

The margins say this is fixable without false alarms: the genuinely-empty
control region in the same frame (empty transfer-table body, structure agrees
it's empty) measures **0.000** on all three metrics I ran (64×64 modal energy,
full-res modal energy, edge fraction — `campaign/linux/guard-metrics.mjs` logs
all three, per the macOS suggestion to log raw values). Chart vs empty:
0.020/0.025/0.0268 vs 0.000/0.000/0.000. Threshold 0.01, or an edge-density
metric, separates every sample measured so far on any OS. Suggested action for
the module owner: lower the default to 0.01 AND add edge-fraction as a second
vote; the Windows agent may want to re-run its three mitigated cells with the
new calibration to confirm nothing flips back.

Ack on the per-window-capture rule: my crop was a screen crop, which is safe in
this specific environment only (bare Xvfb, no compositor, no WM, opaque
single-window region — verified visually). On a real X11 desktop the rule holds
and needs `XCompositeNameWindowPixmap`; noting it so nobody copies my crop code
onto a composited desktop.

---

## 2026-08-17 — FYI — "AT-SPI is blocked headless" was a sandbox artifact; the no-root recipe

The original Linux reference cell recorded AT-SPI `blocked` (no a11y bus without
a session). On a bare Debian 13 server, under plain
`xvfb-run + dbus-run-session`, the a11y bus D-Bus-activates on first client
contact (at-spi-bus-launcher + registryd), GTK3's atk-bridge registers
automatically and Qt6 registers with `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`. No
seat, no WM, no gsettings. Any future headless agent can run the AT-SPI battery.

Environment recipe that made the whole round possible without root (sudo needs a
password here): `apt-get install --print-uris` → wget the .debs → `dpkg -x` into
a user prefix → PATH/LD_LIBRARY_PATH/GI_TYPELIB_PATH/PYTHONPATH exports. One
real trap: Xvfb hardcodes `/usr/bin/xkbcomp` at build time and ignores
XKB_BINDIR; fixed by patching the 8-byte string to `/tmp/xkb` (same length) in
our extracted copy and symlinking xkbcomp there. Keyboard init fails cryptically
otherwise ("Failed to activate virtual core keyboard").

Also, for the record: two flaky-looking failures during setup were self-inflicted
tooling accidents, not environment problems — a `pkill -f` whose pattern matched
my own shell's command line (killed my own session mid-command), and a session
holder killed by a too-broad `pkill sleep`. Worth knowing if a future agent sees
its Xvfb session die "spontaneously".

---

## 2026-08-17 — DONE — all three LINUX items of DEEPENING-PLAN closed

- **Real-web battery + navigation** (P1): 16/16 + 8/8, replicated
  number-for-number against macOS (ratio of totals 1.00× vs 0.98×; median 1.15×
  identical; same 10/16 wins; MDN toggle = same +16 view lines). With Windows's
  0.99× the OS-invariance point is now measured on all three OSes.
- **AT-SPI in session** (P1): Mousepad/GTK3 + FeatherPad/Qt6 full T1–T6, one
  unmodified pyatspi client for both toolkits; qBittorrent/Qt6 delivered the
  4th silent cell of the campaign (first non-Windows) + the calibration FYI
  above.
- **Native blind click** (P2): the previously-blocked CDP+xdotool run passed
  first try; 4/4 first-attempt across CDP, GTK context menu, Qt menubar/tab.

Read-only discipline kept: throwaway documents only, no accounts, no user files;
qBittorrent ran with `--confirm-legal-notice`, no torrent added (its own DHT
bootstrap animated the graph — convenient, zero-config live data). One deviation
to flag: the brief's Tier B/D/F items (GTK4 render-tap on more apps, UNO
re-run, Flutter/Java) were already covered by earlier rounds or remain the
cross-OS open items; this round targeted exactly the three DEEPENING-PLAN
LINUX bullets, per the manager's instruction.
