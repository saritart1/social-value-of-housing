#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    01_headline_figures
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Draws the eta validation and the rent-fit figures from the results CSVs (Figures 2-3).
#  Inputs:  results/<slug>_eta.csv and results/pilot_<slug>.csv; set SUF=_abil6.
#  Output:  charts/eta_validation.png, charts/rent_fit.png.
#  Note:    set the PROJECT constant below to this repository's root.
# ==========================================================
"""The three headline exhibits in the deck, rebuilt from whatever run is current.

  charts/rent_fit.png        model rent vs ACS rent, one panel per metro
  charts/eta_validation.png  model eta per PUMA against Rollet's causal -0.42

Reads code/matlab_models/xl_metros/<slug><SUF>_summary.csv and pilot_<slug><SUF>.csv,
so it follows the world suffix rather than a frozen copy of the results.

  SUF=_abil6 python3 make_headline_figures.py

(mc_tornado.png is NOT built here: it needs sensitivity_v14 output, which has to
be re-run per world. It is listed in the deck and is stale until that happens.)
"""
import os, csv, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
XL   = os.path.join(PROJECT, "code/matlab_models/xl_metros")
OUT  = os.path.join(PROJECT, "presentation/figures/charts")
SUF  = os.environ.get("SUF", "_abil6")
METROS = ["Boston", "New_York", "Bay_Area", "Los_Angeles", "Seattle", "Washington_DC"]
DISPLAY = {"Boston":"Boston","New_York":"New York","Bay_Area":"Bay Area",
           "Los_Angeles":"Los Angeles","Seattle":"Seattle","Washington_DC":"Washington DC"}
SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#898781"
GRID="#e1e0d9"; BLUE="#2a78d6"; ORANGE="#eb6834"; RED="#e34948"
ROLLET = -0.42

def load(m):
    p = os.path.join(XL, f"pilot_{m}{SUF}.csv")
    R = list(csv.DictReader(open(p)))
    for r in R:
        for k in r:
            if k not in ("gid","name"):
                try: r[k] = float(r[k])
                except: r[k] = float("nan")
    s = list(csv.DictReader(open(os.path.join(XL, f"{m}{SUF}_summary.csv"))))[0]
    loc = {r["gid"].zfill(7): float(r["rent_data_yr"])
           for r in csv.DictReader(open(os.path.join(
               PROJECT, "data/paper1_metros/worlds", f"{m}{SUF}", "locations.csv")))}
    for r in R: r["rent_data"] = loc.get(r["gid"].zfill(7), float("nan"))
    return R, s

def style(ax):
    ax.set_facecolor(SURFACE)
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
    for sp in ("left","bottom"): ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=7.5, length=3, width=0.6)
    ax.grid(True, color=GRID, lw=0.5, alpha=0.8); ax.set_axisbelow(True)

# ------------------------------------------------------------- rent fit ----
fig, axes = plt.subplots(2, 3, figsize=(11.2, 6.4), facecolor=SURFACE)
fits = []
for ax, m in zip(axes.ravel(), METROS):
    R, s = load(m); style(ax)
    x = np.array([r["rent_data"] for r in R]); y = np.array([r["price"] for r in R])
    ok = np.isfinite(x) & np.isfinite(y); x, y = x[ok]/1000, y[ok]/1000
    f = float(s["corr_rmodel_rdata"]); fits.append(f)
    lo, hi = min(x.min(), y.min())*0.94, max(x.max(), y.max())*1.06
    ax.plot([lo,hi],[lo,hi], ls=(0,(4,3)), color=MUTED, lw=1.0, zorder=1)
    ax.scatter(x, y, s=17, color=BLUE, alpha=0.72, lw=0, zorder=2)
    ax.set_xlim(lo,hi); ax.set_ylim(lo,hi)
    ax.set_title(f"{DISPLAY[m]}   $r$ = {f:.2f}", fontsize=9.5, color=INK, pad=5, loc="left")
    ax.set_xlabel("ACS rent, \\$000/yr", fontsize=7.5, color=INK2)
    ax.set_ylabel("model rent, \\$000/yr", fontsize=7.5, color=INK2)
fig.suptitle("Model rent against ACS median rent, PUMA by PUMA",
             fontsize=12, color=INK, x=0.012, ha="left", y=0.985)
fig.text(0.012, 0.012, f"Rents are not targeted: the inversion matches wages and populations. "
         f"Correlations {min(fits):.2f} to {max(fits):.2f}; dashed line is 45\u00b0.",
         fontsize=7.8, color=MUTED, ha="left")
fig.tight_layout(rect=[0, 0.035, 1, 0.955])
fig.savefig(os.path.join(OUT, "rent_fit.png"), dpi=200, facecolor=SURFACE); plt.close(fig)
print(f"rent_fit.png      correlations {min(fits):.2f}-{max(fits):.2f}")

# --------------------------------------------------------- eta validation ----
fig, ax = plt.subplots(figsize=(9.2, 4.6), facecolor=SURFACE); style(ax)
meds = []
for i, m in enumerate(METROS):
    R, s = load(m)
    e = np.array([r["eta"] for r in R]); e = e[np.isfinite(e)]
    meds.append(float(s["eta_model_med"]))
    ax.scatter(np.full(e.shape, i) + np.random.default_rng(0).normal(0, .055, e.size),
               e, s=13, color=BLUE, alpha=0.35, lw=0, zorder=2)
    ax.scatter([i], [meds[-1]], s=64, color=ORANGE, zorder=4,
               edgecolor=SURFACE, linewidth=1.1)
ax.axhline(ROLLET, color=RED, lw=1.4, ls=(0,(5,3)), zorder=3)
ax.text(-0.42, ROLLET-0.0022, f"Rollet (2025), causal estimate: {ROLLET}",
        fontsize=8.5, color=RED, ha="left", va="top")
ax.set_ylim(top=max(ax.get_ylim()[1], ROLLET+0.014))
ax.set_xticks(range(len(METROS)))
ax.set_xticklabels([DISPLAY[m] for m in METROS], fontsize=8.5, color=INK2)
ax.set_ylabel("$\\eta$ = d log rent / d log stock", fontsize=9, color=INK2)
ax.set_title("The model reproduces Rollet's rent-supply elasticity, untargeted",
             fontsize=12, color=INK, loc="left", pad=8)
ax.scatter([], [], s=13, color=BLUE, alpha=.5, lw=0, label="one PUMA")
ax.scatter([], [], s=64, color=ORANGE, lw=0, label="metro median")
ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK2)
fig.text(0.012, 0.02, f"Nothing in the calibration targets $\\eta$. Metro medians "
         f"{min(meds):.3f} to {max(meds):.3f}.", fontsize=7.8, color=MUTED, ha="left")
fig.tight_layout(rect=[0, 0.05, 1, 1])
fig.savefig(os.path.join(OUT, "eta_validation.png"), dpi=200, facecolor=SURFACE); plt.close(fig)
print(f"eta_validation.png medians {min(meds):.3f} to {max(meds):.3f}")
