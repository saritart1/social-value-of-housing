#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    02_wedge_maps
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Draws the wedge maps from the rankings and the TIGER shapefiles (Figure 4).
#  Inputs:  results/<slug>_rankings.csv; TIGER PUMA shapefiles plus the cartographic state boundaries.
#  Output:  maps/<metro>_wedge_map.png and the per-metro charts.
#  Note:    TIGER PUMAs include legal water; the state boundaries clip it. Set PROJECT and RESULTS_DIR below.
# ==========================================================
"""Presentation exhibits for Paper 1 (v14/clean spec).

Produces, for each metro with a <slug>_rankings.csv in RESULTS_DIR:
  maps/<slug>_wedge_map.png            PUMA choropleth of wedge_usd (diverging, centered at 0)
  charts/<slug>_wedge_sorted.png       sorted bar chart of wedge_usd
  charts/<slug>_welfare_vs_price.png   grouped bars welfare_usd vs price_model_usd
and, for each metro that ALSO has <slug>_decomp.csv:
  charts/<slug>_wedge_channels.png     stacked channel decomposition

Rerunning picks up any new <slug>_decomp.csv automatically.
"""

import glob
import os

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

PROJECT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
RESULTS_DIR = os.environ.get("RESULTS_DIR", os.path.join(PROJECT, "code/matlab_models/xl_metros/clean"))
SHP_DIR = os.path.join(PROJECT, "data/paper1_metros/shapefiles")
OUT = os.path.join(PROJECT, "presentation/figures")
MAPS_DIR = os.path.join(OUT, "maps")
CHARTS_DIR = os.path.join(OUT, "charts")

DISPLAY = {
    "Boston": "Boston",
    "New_York": "New York",
    "Bay_Area": "Bay Area",
    "Los_Angeles": "Los Angeles",
    "Seattle": "Seattle",
    "Washington_DC": "Washington DC",
}

# ---------------------------------------------------------------- palette ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE = "#2a78d6"      # categorical slot 1 / diverging positive pole
ORANGE = "#eb6834"    # slot 2
AQUA = "#1baf7a"      # slot 3
YELLOW = "#eda100"    # slot 4
RED = "#e34948"       # diverging negative pole
DIV_MID = "#f0efec"   # diverging neutral midpoint

# diverging colormap: red (negative) -> neutral gray -> blue (positive),
# with darker extremes so large magnitudes stay readable
DIV_CMAP = LinearSegmentedColormap.from_list(
    "wedge_div", ["#8f1d1d", RED, DIV_MID, BLUE, "#104281"]
)

CHANNELS = [
    ("agglomeration", "Agglomeration", BLUE),
    ("traffic", "Traffic", ORANGE),
    ("density_amenity", "Density amenity", AQUA),
    ("residual_interactions", "Residual / interactions", YELLOW),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "axes.grid": False,
    "font.size": 16,
    "axes.titlesize": 24,
    "axes.titleweight": "bold",
    "axes.titlepad": 16,
    "axes.labelsize": 18,
    "xtick.labelsize": 15,
    "ytick.labelsize": 15,
    "legend.fontsize": 16,
    "svg.fonttype": "none",
})

FIGSIZE = (12.8, 8.0)   # 16:10 for beamer
DPI = 200


def usd_fmt(v, _pos=None):
    if abs(v) >= 1000:
        k = abs(v) / 1000
        s = f"{k:,.1f}".rstrip("0").rstrip(".") + "k"
    else:
        s = f"{abs(v):,.0f}"
    return ("−$" + s) if v < 0 else ("$" + s)


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def sym_norm(values):
    lim = max(abs(np.nanmin(values)), abs(np.nanmax(values)))
    lim = lim if lim > 0 else 1.0
    return Normalize(vmin=-lim, vmax=lim)


# ------------------------------------------------------------------- maps ----
_shp_cache = {}


def state_pumas(fips):
    if fips not in _shp_cache:
        path = os.path.join(SHP_DIR, f"tl_2022_{fips:02d}_puma20.shp")
        g = gpd.read_file(path)
        g["gid"] = g["GEOID20"].astype(int)
        _shp_cache[fips] = g
    return _shp_cache[fips]


_land_cache = {}


def land_union(states):
    key = tuple(states)
    if key not in _land_cache:
        st = gpd.read_file(os.path.join(SHP_DIR, "cb_2022_us_state_500k",
                                        "cb_2022_us_state_500k.shp"))
        fips = [f"{f:02d}" for f in states]
        _land_cache[key] = st[st.STATEFP.isin(fips)].union_all()
    return _land_cache[key]


def make_map(slug, df):
    states = sorted({int(g) // 100000 for g in df["gid"]})
    shp = pd.concat([state_pumas(f) for f in states], ignore_index=True)
    shp = gpd.GeoDataFrame(shp, geometry="geometry", crs=_shp_cache[states[0]].crs)
    # TIGER PUMAs include legal water area; clip to the cartographic shoreline
    shp = shp.copy()
    shp["geometry"] = shp.geometry.intersection(land_union(states))
    shp = shp[~shp.geometry.is_empty]
    merged = shp.merge(df[["gid", "wedge_usd"]], on="gid", how="inner")

    n_csv, n_match = len(df), len(merged)
    if n_match < n_csv:
        missing = sorted(set(df["gid"]) - set(merged["gid"]))
        print(f"  [WARN] {slug}: {n_csv - n_match}/{n_csv} gids unmatched in shapefile: {missing}")
    else:
        print(f"  {slug}: shapefile match {n_match}/{n_csv} PUMAs")

    merged = merged.to_crs(epsg=3857)
    norm = sym_norm(merged["wedge_usd"].values)

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    merged.plot(
        column="wedge_usd", cmap=DIV_CMAP, norm=norm, ax=ax,
        edgecolor="white", linewidth=0.9,
    )
    ax.set_axis_off()
    ax.set_title(f"{DISPLAY[slug]}: social value wedge per unit ($/yr)", loc="left")

    sm = plt.cm.ScalarMappable(cmap=DIV_CMAP, norm=norm)
    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal",
                        fraction=0.05, pad=0.03, aspect=45, shrink=0.8)
    cbar.ax.tick_params(labelsize=15, color=BASELINE, labelcolor=INK2)
    cbar.outline.set_edgecolor(BASELINE)
    cbar.set_label("$ per unit per year", fontsize=16, color=INK2)
    lim = norm.vmax
    ticks = [t for t in cbar.get_ticks() if -lim <= t <= lim]
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([usd_fmt(t) for t in ticks])

    fig.tight_layout()
    out = os.path.join(MAPS_DIR, f"{slug}_wedge_map.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------------------------------------------------- sorted wedge ----
def make_wedge_sorted(slug, df):
    d = df.sort_values("wedge_usd", ascending=False).reset_index(drop=True)
    norm = sym_norm(d["wedge_usd"].values)
    colors = [DIV_CMAP(norm(v)) for v in d["wedge_usd"]]

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    x = np.arange(len(d))
    ax.bar(x, d["wedge_usd"], width=0.86, color=colors)
    ax.axhline(0, color=INK2, linewidth=1.2)
    style_axes(ax)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    ax.set_xlim(-0.8, len(d) - 0.2)
    ax.yaxis.set_major_formatter(FuncFormatter(usd_fmt))
    ax.set_ylabel("$ per unit per year")
    ax.set_xlabel(f"PUMAs, sorted ({len(d)} total)")
    n_neg = int((d["wedge_usd"] < 0).sum())
    ax.set_title(f"{DISPLAY[slug]}: social value wedge per unit ($/yr)",
                 loc="left", pad=44)
    ax.text(0, 1.012, f"{len(d) - n_neg} PUMAs positive, {n_neg} negative",
            transform=ax.transAxes, fontsize=16, color=INK2, va="bottom")

    fig.tight_layout()
    out = os.path.join(CHARTS_DIR, f"{slug}_wedge_sorted.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


# ------------------------------------------------------ welfare vs price ----
def make_welfare_vs_price(slug, df):
    d = df.sort_values("welfare_usd", ascending=False).reset_index(drop=True)
    corr = np.corrcoef(d["welfare_usd"], d["price_model_usd"])[0, 1]

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    x = np.arange(len(d))
    w = 0.42
    ax.bar(x - w / 2, d["welfare_usd"], width=w, color=BLUE, label="Social value (welfare)")
    ax.bar(x + w / 2, d["price_model_usd"], width=w, color=MUTED, label="Market price")
    style_axes(ax)
    ax.set_xticks([])
    ax.set_xlim(-0.8, len(d) - 0.2)
    ax.yaxis.set_major_formatter(FuncFormatter(usd_fmt))
    ax.set_ylabel("$ per unit per year")
    ax.set_xlabel(f"PUMAs, sorted by social value ({len(d)} total)")
    ax.set_title(f"{DISPLAY[slug]}: social value vs market price per unit ($/yr)",
                 loc="left", pad=44)
    corr_txt = ">0.999" if corr >= 0.9995 else f"{corr:.3f}"
    ax.text(0, 1.012, f"correlation {corr_txt}: prices track social value almost one for one",
            transform=ax.transAxes, fontsize=16, color=INK2, va="bottom")
    ax.legend(loc="upper right", frameon=False, ncols=2)

    fig.tight_layout()
    out = os.path.join(CHARTS_DIR, f"{slug}_welfare_vs_price.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


# ------------------------------------------------------------ decomposition ----
def make_channels(slug, df, decomp):
    wide = decomp.pivot_table(index="gid", columns="channel", values="wedge_usd",
                              aggfunc="sum")
    missing_ch = [c for c, _, _ in CHANNELS if c not in wide.columns]
    if missing_ch:
        print(f"  [WARN] {slug}: decomp missing channels {missing_ch}")
        for c in missing_ch:
            wide[c] = 0.0
    wide["total"] = wide[[c for c, _, _ in CHANNELS]].sum(axis=1)

    # placeholder guard: a real decomposition has nonzero mass outside the
    # residual channel; stub files put the whole wedge in residual_interactions
    named = [c for c, _, _ in CHANNELS if c != "residual_interactions"]
    if wide[named].abs().to_numpy().max() < 1.0:
        print(f"  [SKIP] {slug}: decomp file is a placeholder "
              f"(all named channels zero; wedge sits in residual_interactions)")
        return None

    # consistency check vs rankings wedge
    chk = wide.join(df.set_index("gid")["wedge_usd"], how="inner")
    gap = (chk["total"] - chk["wedge_usd"]).abs().max()
    if gap > max(1.0, 0.01 * chk["wedge_usd"].abs().max()):
        print(f"  [WARN] {slug}: decomp channels do not sum to wedge_usd (max gap ${gap:,.0f})")

    d = wide.sort_values("total", ascending=False).reset_index()
    x = np.arange(len(d))

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    pos = np.zeros(len(d))
    neg = np.zeros(len(d))
    for col, label, color in CHANNELS:
        v = d[col].values
        base = np.where(v >= 0, pos, neg)
        ax.bar(x, v, width=0.86, bottom=base, color=color, label=label,
               edgecolor=SURFACE, linewidth=0.5)
        pos += np.clip(v, 0, None)
        neg += np.clip(v, None, 0)
    ax.plot(x, d["total"], color=INK, linewidth=1.6, label="Net wedge")
    ax.axhline(0, color=INK2, linewidth=1.2)

    style_axes(ax)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    ax.set_xlim(-0.8, len(d) - 0.2)
    ax.yaxis.set_major_formatter(FuncFormatter(usd_fmt))
    ax.set_ylabel("$ per unit per year")
    ax.set_xlabel(f"PUMAs, sorted by net wedge ({len(d)} total)")
    ax.set_title(f"{DISPLAY[slug]}: wedge by channel ($/yr)", loc="left")
    ax.legend(loc="upper right", frameon=False, ncols=1)

    fig.tight_layout()
    out = os.path.join(CHARTS_DIR, f"{slug}_wedge_channels.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


# ------------------------------------------------------------------- main ----
def main():
    os.makedirs(MAPS_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)
    produced = []
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "*_rankings.csv"))):
        slug = os.path.basename(path)[: -len("_rankings.csv")]
        if slug not in DISPLAY:
            DISPLAY[slug] = slug.replace("_", " ")
        df = pd.read_csv(path)
        print(f"{slug}: {len(df)} PUMAs")
        produced.append(make_map(slug, df))
        produced.append(make_wedge_sorted(slug, df))
        produced.append(make_welfare_vs_price(slug, df))
        dpath = os.path.join(RESULTS_DIR, f"{slug}_decomp.csv")
        if os.path.exists(dpath):
            out = make_channels(slug, df, pd.read_csv(dpath))
            if out:
                produced.append(out)
            else:
                stale = os.path.join(CHARTS_DIR, f"{slug}_wedge_channels.png")
                if os.path.exists(stale):
                    os.remove(stale)
                    print(f"  removed stale placeholder chart {stale}")
        else:
            print(f"  {slug}: no decomp file yet (skipping channels chart)")
    print("\nProduced:")
    for p in produced:
        print(" ", p)


if __name__ == "__main__":
    main()
