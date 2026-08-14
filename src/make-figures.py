#!/usr/bin/env python3
"""Generate paper figures from results/*.json — palette & specs per dataviz method."""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, '../results')

# palette (validated: PASS light mode; aqua contrast WARN -> direct labels shipped)
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
SURFACE, INK, INK2, MUTED, GRID, BASE = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 11,
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'text.color': INK, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
    'axes.edgecolor': BASE, 'axes.linewidth': 0.8,
})

def clean(ax, ygrid=True):
    for s in ['top', 'right']: ax.spines[s].set_visible(False)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.7); ax.set_axisbelow(True)
    ax.spines['left'].set_visible(False)
    ax.tick_params(length=0)

reps = json.load(open(f'{RES}/representations.json'))
diffs = json.load(open(f'{RES}/diffs.json'))

# ---- Fig 1: same screen, three representations (tokens) ----
fig, ax = plt.subplots(figsize=(7.2, 4.2))
pages = [r['label'] for r in reps]
series = [
    ('Screenshot (pixels)', BLUE, [r['screenshot']['tokensClaude'] for r in reps]),
    ('DOM view (semantic text)', ORANGE, [r['domSnapshot']['tokensDistilled'] for r in reps]),
    ('Skia paint ops (display list)', AQUA, [r['paintOps']['tokensDistilled'] for r in reps]),
]
W, n = 0.24, len(pages)
for i, (name, color, vals) in enumerate(series):
    x = [j + (i - 1) * (W + 0.02) for j in range(n)]
    bars = ax.bar(x, vals, width=W, color=color, label=name, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 90, f'{v:,}', ha='center', fontsize=9.5, color=INK2)
ax.set_xticks(range(n)); ax.set_xticklabels(['App UI (orders console)', 'Text-heavy article (full page)'], color=INK2)
ax.set_ylabel('LLM input tokens (est.)')
ax.set_title('Same screen, three representations — token cost', loc='left', fontsize=12.5, color=INK, pad=12)
ax.legend(frameon=False, fontsize=9.5, loc='upper left')
clean(ax); ax.set_ylim(0, 7400)
ax.annotate('paint ops: positions only,\ntext content already gone', xy=(1.47, 2400), fontsize=8.5, color=MUTED, ha='right')
fig.tight_layout(); fig.savefig(f'{RES}/fig1_representations.png', dpi=200); plt.close(fig)

# ---- Fig 2: cost of perceiving each change ----
steps = diffs['steps']
labels = ['Click "Ship"\n(badge + toast)', 'Toast fades out', 'Type into field', 'Submit form\n(new row + toast)', 'Nothing changed']
fig, ax = plt.subplots(figsize=(7.2, 4.0))
y = range(len(steps))
H = 0.32
b1 = ax.barh([i + H/2 + 0.02 for i in y], [s['screenshotTokens'] for s in steps], height=H, color=BLUE, label='Re-screenshot policy', zorder=3)
b2 = ax.barh([i - H/2 - 0.02 for i in y], [s['diffTokens'] for s in steps], height=H, color=ORANGE, label='Structured diff policy', zorder=3)
for i, s in enumerate(steps):
    ax.text(s['screenshotTokens'] + 18, i + H/2 + 0.02, f"{s['screenshotTokens']:,}", va='center', fontsize=9, color=INK2)
    ax.text(s['diffTokens'] + 18, i - H/2 - 0.02, f"{s['diffTokens']:,}" if s['diffTokens'] else '0', va='center', fontsize=9, color=INK2)
ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=9.5, color=INK2)
ax.invert_yaxis()
ax.set_xlabel('LLM input tokens to perceive the change')
ax.set_title('Perceiving change: full re-screenshot vs structured diff', loc='left', fontsize=12.5, color=INK, pad=12)
ax.set_xlim(0, 1580)
ax.legend(frameon=False, fontsize=9.5, loc='upper right', bbox_to_anchor=(1, -0.14), ncol=2)
for sp in ['top', 'right', 'left']: ax.spines[sp].set_visible(False)
ax.xaxis.grid(True, color=GRID, linewidth=0.7); ax.set_axisbelow(True); ax.tick_params(length=0)
fig.tight_layout(); fig.savefig(f'{RES}/fig2_change.png', dpi=200, bbox_inches='tight'); plt.close(fig)

# ---- Fig 3: living screen, cumulative tokens ----
liv = diffs['living']
secs = [0] + [s['second'] for s in liv['samples']]
shot_cum = [0]; diff_cum = [0]
for s in liv['samples']:
    shot_cum.append(shot_cum[-1] + diffs['screenshotTokensPerFrame'])
    diff_cum.append(diff_cum[-1] + s['diffTokens'])
fig, ax = plt.subplots(figsize=(7.2, 4.0))
ax.plot(secs, shot_cum, color=BLUE, linewidth=2, marker='o', markersize=5, zorder=3)
ax.plot(secs, diff_cum, color=ORANGE, linewidth=2, marker='o', markersize=5, zorder=3)
ax.text(secs[-1] + 0.08, shot_cum[-1], f'Screenshots @1 fps\n{shot_cum[-1]:,} tok', fontsize=9.5, color=BLUE, va='center')
ax.text(secs[-1] + 0.08, diff_cum[-1], f'Structured diffs\n{diff_cum[-1]:,} tok ({shot_cum[-1]//max(1,diff_cum[-1])}× less)', fontsize=9.5, color=ORANGE, va='center')
ax.set_xlim(0, 7.6); ax.set_ylim(0, max(shot_cum) * 1.12)
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.set_xlabel('Seconds observing a self-updating screen (live feed)')
ax.set_ylabel('Cumulative LLM input tokens')
ax.set_title('Watching a living screen for 6 s — cumulative perception cost', loc='left', fontsize=12.5, color=INK, pad=12)
clean(ax)
fig.tight_layout(); fig.savefig(f'{RES}/fig3_living.png', dpi=200); plt.close(fig)
print('figures written')
