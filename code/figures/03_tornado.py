#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    03_tornado
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Draws the one-parameter-at-a-time figure (Figure 5).
#  Inputs:  results/sensitivity_v15_<slug>.csv.
#  Output:  charts/tornado_metros.png.
#  Note:    set the PROJECT constant below to this repository's root.
# ==========================================================
"""Robustness II: what moves the answer, one parameter at a time.

Reads xl_metros/sensitivity_v15_<slug>.csv (and mc_ci_v15_<slug>.csv if the
Monte Carlo has finished) and writes charts/mc_tornado.png.

  SLUG=Seattle_abil6 python3 make_tornado.py
"""
import os, csv, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT="/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
XL=os.path.join(PROJECT,"code/matlab_models/xl_metros")
OUT=os.path.join(PROJECT,"presentation/figures/charts")
SLUG=os.environ.get("SLUG","Seattle_abil6")
PRETTY={"Seattle_abil6":"Seattle","Boston_abil6":"Boston","New_York_abil6":"New York",
        "Bay_Area_abil6":"Bay Area","Los_Angeles_abil6":"Los Angeles",
        "Washington_DC_abil6":"Washington DC"}
LABEL={"omega":(r"$\omega$","density amenity"), "theta":(r"$\theta$","residence sorting"),
       "alpha":(r"$\alpha$","housing share"), "lambda_scale":(r"$\lambda_k$","agglomeration"),
       "dc":(r"$\delta_c$","congestion"), "kappa":(r"$\kappa$","commuting cost"),
       "mc_scale":("MC","construction cost"), "dereg_epsS":(r"$\varepsilon_S$","supply elasticity")}
SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#898781"
GRID="#e1e0d9"; BLUE="#2a78d6"; BAND="#eceae4"

R=list(csv.DictReader(open(os.path.join(XL,f"sensitivity_v15_{SLUG}.csv"))))
base=float([r for r in R if r["param"]=="baseline"][0]["max_wedge_usd"])
rows={}
for r in R:
    if r["param"]=="baseline": continue
    rows.setdefault(r["param"],[]).append(float(r["max_wedge_usd"]))
rows={k:(min(v),max(v)) for k,v in rows.items() if len(v)==2}
inert=[k for k,(lo,hi) in rows.items() if hi-lo < 1]             # do not move it at all
rows={k:v for k,v in rows.items() if k not in inert}
order=sorted(rows, key=lambda k: rows[k][1]-rows[k][0])          # widest at top

ci=None
p=os.path.join(XL,f"mc_ci_v15_{SLUG}.csv")
if os.environ.get("NOBAND")=="1": p="/nonexistent"
if os.path.exists(p):
    for r in csv.DictReader(open(p)):
        if r.get("object")=="max_wedge_usd":
            ci=(float(r["p5"]),float(r["p50"]),float(r["p95"]))

fig,ax=plt.subplots(figsize=(9.4,4.2),facecolor=SURFACE)
ax.set_facecolor(SURFACE)
for sp in ("top","right","left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.tick_params(colors=INK2,labelsize=8.5,length=3,width=.6)
ax.grid(axis="x",color=GRID,lw=.5); ax.set_axisbelow(True)

if ci:
    ax.axvspan(ci[0],ci[2],color=BAND,zorder=0)
for y,k in enumerate(order):
    lo,hi=rows[k]
    ax.plot([lo,hi],[y,y],color=BLUE,lw=10,solid_capstyle="butt",alpha=.85,zorder=3)
    ax.text(lo-45,y,f"${lo:,.0f}",fontsize=8.5,color=INK2,va="center",ha="right")
    ax.text(hi+45,y,f"${hi:,.0f}",fontsize=8.5,color=INK2,va="center",ha="left")
ax.axvline(base,color=INK,lw=1.1,zorder=4)
ax.text(base,len(order)-0.28,f" baseline ${base:,.0f}",fontsize=8,color=INK,va="bottom",ha="left")
ax.set_yticks(range(len(order)))
ax.set_yticklabels([f"{LABEL[k][0]}   {LABEL[k][1]}" for k in order],fontsize=9,color=INK)
ax.set_ylim(-0.7,len(order)-0.15)
ax.set_xlabel("largest wedge in the metro, \\$ per unit per year",fontsize=8.5,color=INK2)
lo_all=min(v[0] for v in rows.values()); hi_all=max(v[1] for v in rows.values())
if ci: lo_all=min(lo_all,ci[0]); hi_all=max(hi_all,ci[2])
pad=0.13*(hi_all-lo_all); ax.set_xlim(lo_all-pad, hi_all+pad)
if ci:
    ax.annotate(f"shaded: 90% interval when all\nparameters are drawn together\n\\${ci[0]:,.0f} to \\${ci[2]:,.0f}",
                xy=(ci[2]-0.02*(hi_all-lo_all), len(order)-1.15),
                fontsize=8, color=MUTED, ha="right", va="top", linespacing=1.35)
if inert:
    names=", ".join(LABEL[k][1] for k in inert)
    ax.text(0.0,-0.235,f"Across their whole published range, {names} do not move the wedge at all.",
            transform=ax.transAxes,fontsize=8,color=MUTED,ha="left")
ax.set_title(f"What moves the answer: {PRETTY.get(SLUG,SLUG)}, one parameter at a time",
             fontsize=11.5,color=INK,loc="left",pad=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT,"mc_tornado.png"),dpi=200,facecolor=SURFACE)
print(f"mc_tornado.png  {PRETTY.get(SLUG,SLUG)}  baseline ${base:,.0f}"
      + (f"  CI ${ci[0]:,.0f}-${ci[2]:,.0f}" if ci else "  (Monte Carlo band pending)"))
