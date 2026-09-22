#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    04_grids
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Draws the (omega, theta) grid heatmaps (Figures 6-7).
#  Inputs:  results/grid_<slug>.csv and results/<slug>_summary.csv.
#  Output:  charts/grid_overall.png, charts/grid_metros.png.
#  Note:    set the PROJECT constant below to this repository's root.
# ==========================================================
"""The omega x theta grid exhibits (replaces the Monte Carlo tornado band).

  charts/grid_overall.png   the wedge RELATIVE TO BASELINE, averaged across the
                            five completed metros: how the answer varies with
                            the two parameters that matter, in one heatmap
  charts/grid_metros.png    five small multiples, one per metro, dollar values

Reads xl_metros/grid_<slug>.csv. New York ran separately on a 3x3 (Sep 11);
it joins the small multiples but not the five-metro 5x5 average.
"""
import os, csv, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT="/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
XL=os.path.join(PROJECT,"code/matlab_models/xl_metros")
OUT=os.path.join(PROJECT,"presentation/figures/charts")
METROS=["Boston","Seattle","Washington_DC","Bay_Area","Los_Angeles"]
DISPLAY={"Boston":"Boston","Seattle":"Seattle","Washington_DC":"Washington DC",
         "Bay_Area":"Bay Area","Los_Angeles":"Los Angeles"}
SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#898781"; GRID="#e1e0d9"

def load(m):
    R=list(csv.DictReader(open(os.path.join(XL,f"grid_{m}_abil6.csv"))))
    om=sorted({float(r["omega"]) for r in R}); th=sorted({float(r["theta"]) for r in R})
    M=np.full((len(om),len(th)),np.nan)
    for r in R:
        M[om.index(float(r["omega"])), th.index(float(r["theta"]))]=float(r["max_wedge_usd"])
    return np.array(om),np.array(th),M

def style(ax):
    ax.set_facecolor(SURFACE)
    for sp in ax.spines.values(): sp.set_color(GRID)
    ax.tick_params(colors=INK2,length=0)

# ---------- overall: mean ratio to each metro's baseline ----------
oms,ths,rels=None,None,[]
for m in METROS:
    om,th,M=load(m)
    i0=int(np.argmin(np.abs(om-0.12))); j0=int(np.argmin(np.abs(th-3.0)))  # closest to central
    # central cell: omega=0.12 exact; theta grid is 2,2.75,3.5,4.25,5 -> use interp of the two middle? no: ratio to the metro BASELINE value instead
    rels.append(M)  # keep raw; ratio computed against the true baseline below
    oms,ths=om,th
# baselines from the summary files
base={}
for m in METROS:
    S=list(csv.DictReader(open(os.path.join(XL,f"{m}_abil6_summary.csv"))))[0]
    base[m]=float(S["max_wedge_usd"])
REL=np.mean([M/base[m] for m,M in zip(METROS,rels)],axis=0)

fig,ax=plt.subplots(figsize=(7.6,4.6),facecolor=SURFACE); style(ax)
im=ax.imshow(REL,origin="lower",cmap="RdBu_r",vmin=0.4,vmax=2.4,aspect="auto")
for a in range(len(oms)):
    for b in range(len(ths)):
        ax.text(b,a,f"{REL[a,b]:.2f}",ha="center",va="center",fontsize=9.5,
                color=INK if 0.75<REL[a,b]<1.7 else "white")
ax.set_xticks(range(len(ths))); ax.set_xticklabels([f"{t:g}" for t in ths],fontsize=9)
ax.set_yticks(range(len(oms))); ax.set_yticklabels([f"{o:.2f}" for o in oms],fontsize=9)
ax.set_xlabel(r"$\theta$  residence sorting",fontsize=10,color=INK2)
ax.set_ylabel(r"$\omega$  density amenity",fontsize=10,color=INK2)
ax.set_title("The wedge relative to the baseline, averaged over five metros",
             fontsize=11.5,color=INK,loc="left",pad=10)
fig.text(0.012,0.02,"Each cell: full re-calibration and re-solve at that ($\\omega$, $\\theta$). "
         "Baseline cell = 1. Top location unchanged in all 125 cells; New York (coarser 3$\\times$3, run separately) keeps its top in all 9.",
         fontsize=7.8,color=MUTED)
fig.tight_layout(rect=[0,0.05,1,1])
fig.savefig(os.path.join(OUT,"grid_overall.png"),dpi=200,facecolor=SURFACE); plt.close(fig)
print(f"grid_overall.png   ratio range {REL.min():.2f}-{REL.max():.2f}")

# ---------- per-metro small multiples ----------
fig,axes=plt.subplots(2,3,figsize=(11.4,6.2),facecolor=SURFACE)
for ax,m in zip(axes.ravel(),METROS):
    om,th,M=load(m); style(ax)
    im=ax.imshow(M/1000,origin="lower",cmap="RdBu_r",
                 vmin=0.4*base[m]/1000, vmax=2.4*base[m]/1000, aspect="auto")
    for a in range(len(om)):
        for b in range(len(th)):
            ax.text(b,a,f"{M[a,b]/1000:.1f}",ha="center",va="center",fontsize=7.6,
                    color=INK if 0.75<M[a,b]/base[m]<1.7 else "white")
    ax.set_xticks(range(len(th))); ax.set_xticklabels([f"{t:g}" for t in th],fontsize=7)
    ax.set_yticks(range(len(om))); ax.set_yticklabels([f"{o:.2f}" for o in om],fontsize=7)
    ax.set_title(f"{DISPLAY[m]}   baseline \\${base[m]/1000:.1f}k",fontsize=9.5,color=INK,loc="left")
    ax.set_xlabel(r"$\theta$",fontsize=8,color=INK2); ax.set_ylabel(r"$\omega$",fontsize=8,color=INK2)
# New York: 3x3 run, its own panel
DISPLAY["New_York"]="New York (3x3)"
S=list(csv.DictReader(open(os.path.join(XL,"New_York_abil6_summary.csv"))))[0]
base["New_York"]=float(S["max_wedge_usd"])
ax=axes.ravel()[5]; m="New_York"
om,th,M=load(m); style(ax)
im=ax.imshow(M/1000,origin="lower",cmap="RdBu_r",
             vmin=0.4*base[m]/1000, vmax=2.4*base[m]/1000, aspect="auto")
for a in range(len(om)):
    for b in range(len(th)):
        ax.text(b,a,f"{M[a,b]/1000:.1f}",ha="center",va="center",fontsize=7.6,
                color=INK if 0.75<M[a,b]/base[m]<1.7 else "white")
ax.set_xticks(range(len(th))); ax.set_xticklabels([f"{t:g}" for t in th],fontsize=7)
ax.set_yticks(range(len(om))); ax.set_yticklabels([f"{o:.2f}" for o in om],fontsize=7)
ax.set_title(f"{DISPLAY[m]}   baseline \\${base[m]/1000:.1f}k",fontsize=9.5,color=INK,loc="left")
ax.set_xlabel(r"$\theta$",fontsize=8,color=INK2); ax.set_ylabel(r"$\omega$",fontsize=8,color=INK2)
fig.suptitle("Largest wedge (\\$000 per unit per year) at each ($\\omega$, $\\theta$)",
             fontsize=12,color=INK,x=0.012,ha="left",y=0.99)
fig.tight_layout(rect=[0,0.01,1,0.95])
fig.savefig(os.path.join(OUT,"grid_metros.png"),dpi=200,facecolor=SURFACE); plt.close(fig)
print("grid_metros.png    six panels (NY 3x3)")
