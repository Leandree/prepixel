#!/usr/bin/env python3
"""Duel figure: accuracy parity (left) + cost gap (right). Validated palette."""
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=os.path.dirname(__file__); RES=os.path.join(HERE,'../results')
rows=json.load(open(f'{RES}/duel/duel-cost.json'))
summ=json.load(open(f'{RES}/duel/duel-summary.json'))

BLUE,ORANGE='#2a78d6','#eb6834'
SURFACE,INK,INK2,MUTED,GRID,BASE='#fcfcfb','#0b0b0b','#52514e','#898781','#e1e0d9','#c3c2b7'
plt.rcParams.update({'font.family':'sans-serif','font.size':11,'figure.facecolor':SURFACE,
 'axes.facecolor':SURFACE,'savefig.facecolor':SURFACE,'text.color':INK,'axes.labelcolor':INK2,
 'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':BASE,'axes.linewidth':0.8})

fig,(axA,axB)=plt.subplots(1,2,figsize=(10.5,4.3),gridspec_kw={'width_ratios':[1,1.25]})

# LEFT: accuracy parity
conds=['Structured\nview','Screenshot\n(pixels)']
acc=[100,100]  # 18/18 both
bars=axA.bar(conds,acc,color=[ORANGE,BLUE],width=0.55,zorder=3)
for b,v in zip(bars,acc): axA.text(b.get_x()+b.get_width()/2,v+1.5,f'{v:.0f}%',ha='center',fontsize=12,color=INK)
axA.set_ylim(0,112); axA.set_ylabel('Task accuracy')
axA.set_title('Accuracy: parity on legible screens',loc='left',fontsize=12,color=INK,pad=10)
axA.text(0.5,-0.22,'18/18 correct in both conditions (n=6 pages × 3 tasks, randomized)',
         transform=axA.transAxes,ha='center',fontsize=8.5,color=MUTED)
for s in ['top','right','left']: axA.spines[s].set_visible(False)
axA.yaxis.grid(True,color=GRID,linewidth=0.7); axA.set_axisbelow(True); axA.tick_params(length=0)

# RIGHT: cost per page (tokens), structured vs pixels, n=20
xs=list(range(len(rows)))
struct=[r['structured']['view_tokens_est'] for r in rows]
pix=[r['pixels']['img_tokens'] for r in rows]
axB.plot(xs,pix,color=BLUE,linewidth=2,marker='o',markersize=3,zorder=3,label='Screenshot (exact image formula)')
axB.plot(xs,struct,color=ORANGE,linewidth=2,marker='o',markersize=3,zorder=3,label='Structured view (est.)')
axB.axhline(sum(pix)/len(pix),color=BLUE,linewidth=0.8,linestyle=':',zorder=2)
axB.axhline(sum(struct)/len(struct),color=ORANGE,linewidth=0.8,linestyle=':',zorder=2)
axB.set_xlabel('page (20 randomized)'); axB.set_ylabel('input tokens')
axB.set_title(f'Cost per page — {summ["avg_cost"]["token_ratio"]}× fewer tokens, {summ["avg_cost"]["byte_ratio"]}× fewer bytes',
              loc='left',fontsize=12,color=INK,pad=10)
axB.legend(frameon=False,fontsize=9,loc='center right')
axB.set_ylim(0,1500)
for s in ['top','right','left']: axB.spines[s].set_visible(False)
axB.yaxis.grid(True,color=GRID,linewidth=0.7); axB.set_axisbelow(True); axB.tick_params(length=0)

fig.tight_layout()
fig.savefig(f'{RES}/duel/fig_duel.png',dpi=200,bbox_inches='tight')
print('wrote fig_duel.png')
