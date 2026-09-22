#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    08_build_world_deciles_2016
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Builds the 2012-2016 vintage of the decile worlds, the first stage of the vintage check.
#  Inputs:  the decile worlds from 20260706, plus the 2016-vintage PUMS and LODES downloads.
#  Output:  one <metro>_2016 world per metro (Seattle has its own script below).
#  Note:    also stores the PUMA20-to-PUMA10 map that the ability vintage builder reads.
# ==========================================================
"""Paper 1 — build one metro's 2012-2016 (t0) world for the kappa diagnostic.

Usage:  python3 20260720_p1_build_world_2016.py "Boston"
        (metros: Boston, Washington DC, Bay Area, Los Angeles, New York;
         Seattle was built by 20260720_p1_build_world_2016_seattle.py)

Generalization of the Seattle t0 builder to multi-state metros. Same output
layout, written to data/paper1_metros/worlds/<slug>_2016/, on the SAME PUMA20
locations as the 2022 world so kappa_t0 and kappa_t1 compare per location.
Vintage logic (see the Seattle script's docstring): ACS 2016 tracts allocated
tract10->tract20 by land shares then to PUMA20 by LODES-block majority; LODES8
2016 reuses the 2020-block geography directly; PUMS 2012-16 wages by 2010
POWPUMA with PUMA20 -> PUMA10 centroid containment; travel times, mu_pct,
mc_yr, own_k, L held at 2022.
"""
import sys, os, json, zipfile
import numpy as np
import pandas as pd
import geopandas as gpd

MIN_EARN = 1000
AGE_LO, AGE_HI = 18, 70

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PM   = os.path.join(ROOT, "data", "paper1_metros")
SLUG = {"Boston":"Boston", "Washington DC":"Washington_DC", "Bay Area":"Bay_Area",
        "Los Angeles":"Los_Angeles", "New York":"New_York", "Seattle":"Seattle"}
FIPS2USPS = {"06":"ca","11":"dc","24":"md","25":"ma","33":"nh",
             "34":"nj","36":"ny","51":"va","53":"wa"}

metro = sys.argv[1] if len(sys.argv) > 1 else "Boston"
slug  = SLUG[metro]
T1  = os.path.join(PM, "worlds", slug)
OUT = os.path.join(PM, "worlds", slug + "_2016")
os.makedirs(OUT, exist_ok=True)
meta = {"metro": metro, "vintage": "ACS/PUMS 2012-2016, LODES 2016",
        "held_at_2022": ["traveltime", "mu_pct", "mc_yr", "own_k", "L_km2"]}

# ---------------- 1. location universe = the 2022 world ----------------------
loc1 = pd.read_csv(os.path.join(T1, "locations.csv"), dtype={"gid":str,"state":str,"puma":str})
gids = loc1.gid.tolist(); N = len(gids); gpos = {g:i for i,g in enumerate(gids)}
states = sorted(loc1.state.unique())
print(f"[{metro} t0] {N} PUMA20 locations, states {states}")

# ---------------- 2. block/tract -> PUMA20 maps ------------------------------
shp = pd.concat([gpd.read_file(os.path.join(PM,"shapefiles",f"tl_2022_{st}_puma20.shp"))
                 for st in states])
shp = shp[shp.GEOID20.isin(gids)].set_index("GEOID20")
minx, miny, maxx, maxy = shp.total_bounds
poly = shp[["geometry"]].reset_index()
blk2gid, tract2gid = {}, {}
for st in states:
    us = FIPS2USPS[st]
    xk = pd.read_csv(os.path.join(PM,"lodes","raw",f"{us}_xwalk.csv.gz"),
                     usecols=["tabblk2020","trct","blklatdd","blklondd"],
                     dtype={"tabblk2020":str,"trct":str})
    xk = xk.dropna(subset=["blklatdd","blklondd"])
    xk = xk[(xk.blklondd>=minx)&(xk.blklondd<=maxx)&
            (xk.blklatdd>=miny)&(xk.blklatdd<=maxy)]
    pts = gpd.GeoDataFrame(xk, geometry=gpd.points_from_xy(xk.blklondd, xk.blklatdd),
                           crs="EPSG:4269")
    j = gpd.sjoin(pts, poly, how="inner", predicate="within")
    blk2gid.update(dict(zip(j.tabblk2020, j.GEOID20)))
    tract2gid.update(j.groupby("trct").GEOID20.agg(lambda s: s.mode().iat[0]).to_dict())
print(f"  {len(blk2gid):,} metro blocks, {len(tract2gid):,} 2020 tracts mapped")

# ---------------- 3. ACS 2016 tracts -> allocate to gid ----------------------
def acs_tract(tbl):
    frames = []
    for st in states:
        d = json.load(open(os.path.join(PM,"acs",f"raw_2016_{tbl}_st{st}_tract.json")))
        df = pd.DataFrame(d[1:], columns=d[0])
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["t11"] = df.state.str.zfill(2) + df.county.str.zfill(3) + df.tract.str.zfill(6)
    keep = [c for c in df.columns if c.endswith("E") and c.startswith(tbl)]
    for c in keep: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("t11")[keep]

b19 = acs_tract("B19001"); b25001 = acs_tract("B25001")
b25064 = acs_tract("B25064"); b25003 = acs_tract("B25003")

cw = pd.read_csv(os.path.join(ROOT,"data","crosswalks","tab20_tract20_tract10_natl.txt"),
                 sep="|", usecols=["GEOID_TRACT_20","GEOID_TRACT_10","AREALAND_PART"],
                 dtype={"GEOID_TRACT_20":str,"GEOID_TRACT_10":str})
cw = cw[cw.GEOID_TRACT_10.str[:2].isin(states)].copy()
tot10 = cw.groupby("GEOID_TRACT_10").AREALAND_PART.transform("sum")
cw["w"] = np.where(tot10 > 0, cw.AREALAND_PART / tot10, 0.0)
cw["gid"] = cw.GEOID_TRACT_20.map(tract2gid)
cw = cw.dropna(subset=["gid"])

def alloc_counts(df, col):
    m = cw.merge(df[[col]], left_on="GEOID_TRACT_10", right_index=True, how="inner")
    m["v"] = m[col].clip(lower=0).fillna(0) * m.w
    return m.groupby("gid").v.sum().reindex(gids).fillna(0).values

households = alloc_counts(b19, "B19001_001E")
H_units    = alloc_counts(b25001, "B25001_001E")
rm = cw.merge(b25064[["B25064_001E"]], left_on="GEOID_TRACT_10", right_index=True) \
       .merge(b25003[["B25003_003E"]], left_on="GEOID_TRACT_10", right_index=True)
rm = rm[(rm.B25064_001E > 0) & (rm.B25003_003E > 0)]
rm["wt"] = rm.B25003_003E * rm.w
rent_yr = (rm.assign(rx=rm.B25064_001E*rm.wt).groupby("gid")[["rx","wt"]].sum()
             .eval("rx/wt").reindex(gids).values) * 12

EDGES = np.array([0,10,15,20,25,30,35,40,45,50,60,75,100,125,150,200,400], float)*1000
bcols = [f"B19001_{i:03d}E" for i in range(2,18)]
BC = np.column_stack([alloc_counts(b19, c) for c in bcols])
tot = BC.sum(axis=0); cum = np.concatenate([[0], np.cumsum(tot)]) / tot.sum()
qcut = np.interp(np.arange(1,10)/10, cum, EDGES)
DQ = np.concatenate([[EDGES[0]], qcut, [EDGES[-1]]])
pit = np.zeros((N,10))
for b in range(16):
    lo, hi = EDGES[b], EDGES[b+1]
    for d in range(10):
        ov = max(0.0, min(hi, DQ[d+1]) - max(lo, DQ[d]))
        if ov > 0: pit[:,d] += BC[:,b] * ov/(hi-lo)
pitarget = pit / pit.sum(axis=0)
meta["decile_cutoffs_hh_income"] = np.round(DQ).tolist()

# ---------------- 4. LODES 2016 OD -> commute shares -------------------------
print("LODES 2016: aggregating OD flows...")
F = np.zeros((N,N))
for st in states:
    us = FIPS2USPS[st]
    for part in ("main","aux"):
        fp = os.path.join(PM,"lodes","raw",f"{us}_od_{part}_JT00_2016.csv.gz")
        for ch in pd.read_csv(fp, usecols=["w_geocode","h_geocode","S000"],
                              dtype={"w_geocode":str,"h_geocode":str,"S000":"int32"},
                              chunksize=2_000_000):
            ch["wg"] = ch.w_geocode.map(blk2gid); ch["hg"] = ch.h_geocode.map(blk2gid)
            ch = ch.dropna(subset=["wg","hg"])
            g = ch.groupby(["hg","wg"]).S000.sum()
            for (hg,wg),v in g.items(): F[gpos[hg], gpos[wg]] += v
rs = F.sum(axis=1, keepdims=True)
meta["lodes_zero_flow_pumas"] = int((rs.ravel()==0).sum())
meta["lodes_jobs_within_metro"] = int(F.sum())
rs[rs==0] = 1.0
piw = F / rs
# gravity fallback on the (held-fixed) travel times for zero-flow rows
Tt = pd.read_csv(os.path.join(T1,"traveltime.csv"), header=None).values
zero = F.sum(axis=1) == 0
if zero.any():
    G = np.exp(-0.05*Tt[zero,:]); piw[zero,:] = G/G.sum(axis=1, keepdims=True)
print(f"  {int(F.sum()):,} within-metro jobs; zero-flow PUMAs: {int(zero.sum())}")

# ---------------- 5. PUMA20 -> PUMA10/POWPUMA10 (centroid containment) -------
p10 = pd.concat([gpd.read_file(os.path.join(PM,"shapefiles",f"tl_2016_{st}_puma10.zip"))
                 for st in states])
cent = gpd.GeoDataFrame({"gid": gids},
        geometry=gpd.points_from_xy(loc1.lon, loc1.lat), crs="EPSG:4269")
cj = gpd.sjoin(cent, p10[["GEOID10","geometry"]], how="left", predicate="within")
cj = cj[~cj.index.duplicated(keep="first")]
missing = cj.GEOID10.isna()
if missing.any():
    near = gpd.sjoin_nearest(cent[missing.values], p10[["GEOID10","geometry"]])
    near = near[~near.index.duplicated(keep="first")]
    cj.loc[missing, "GEOID10"] = near.GEOID10.values
puma10_of = dict(zip(cj.gid, cj.GEOID10))
powgid_of = {g: p[:2] + str(int(p[2:])//100*100).zfill(5) for g,p in puma10_of.items()}
meta["puma20_to_puma10"] = puma10_of
print(f"  {len(set(puma10_of.values()))} distinct PUMA10s, "
      f"{len(set(powgid_of.values()))} POWPUMAs")

# ---------------- 6. PUMS 2016: wages by workplace POWPUMA x decile ----------
print("PUMS 2012-2016: earnings by POWPUMA x decile...")
rset = set(puma10_of.values()); powset = set(powgid_of.values())
stfips = {int(s) for s in states}
rows = []
for st in states:
    us = FIPS2USPS[st]
    zf = zipfile.ZipFile(os.path.join(PM,"pums","raw",f"csv_p{us}_2016.zip"))
    for name in [n for n in zf.namelist() if n.endswith(".csv")]:
        with zf.open(name) as f:
            for ch in pd.read_csv(f, usecols=["ST","PUMA","POWPUMA","POWSP","PERNP",
                                              "ADJINC","PWGTP","AGEP"], chunksize=500_000):
                ch = ch[(ch.AGEP>=AGE_LO)&(ch.AGEP<=AGE_HI)]
                ch["earn"] = ch.PERNP * ch.ADJINC/1e6
                ch = ch[ch.earn > MIN_EARN]
                ch["rgid"] = ch.ST.astype(int).astype(str).str.zfill(2) + \
                             ch.PUMA.astype(int).astype(str).str.zfill(5)
                pow_st = pd.to_numeric(ch.POWSP, errors="coerce")
                powp   = pd.to_numeric(ch.POWPUMA, errors="coerce")
                ok = pow_st.isin(stfips) & (powp>0)
                ch["powgid"] = ""
                ch.loc[ok,"powgid"] = pow_st[ok].astype(int).astype(str).str.zfill(2) + \
                    (powp[ok].astype(int)//100*100).astype(str).str.zfill(5)
                ch = ch[ch.rgid.isin(rset) | ch.powgid.isin(powset)]
                rows.append(ch[["rgid","powgid","earn","PWGTP"]])
    zf.close()
P = pd.concat(rows, ignore_index=True)
res = P[P.rgid.isin(rset)].copy()
o = res.sort_values("earn"); cwm = o.PWGTP.cumsum()/o.PWGTP.sum()
cuts = np.interp(np.arange(1,10)/10, cwm, o.earn)
meta["decile_cutoffs_person_earnings"] = np.round(cuts).tolist()
P["dec"] = np.searchsorted(cuts, P.earn) + 1
res["dec"] = np.searchsorted(cuts, res.earn) + 1
print(f"  {len(res):,} metro-resident workers (t0)")

def wavg_table(df, col, keys):
    d = df[df[col].isin(keys)]
    g = d.assign(wx=d.earn*d.PWGTP).groupby([col,"dec"])[["wx","PWGTP"]].sum()
    return (g.wx/g.PWGTP)

wp = wavg_table(P, "powgid", powset)
wr = wavg_table(res, "rgid", rset)
Wp = np.full((N,10), np.nan); Wr = np.full((N,10), np.nan)
for (k,d),v in wp.items():
    for g2,i in gpos.items():
        if powgid_of[g2] == k: Wp[i,d-1] = v
for (k,d),v in wr.items():
    for g2,i in gpos.items():
        if puma10_of[g2] == k: Wr[i,d-1] = v
Abar = np.where(np.isnan(Wp), Wr, Wp)
decmean = np.nanmean(Abar, axis=0)
pumamean = np.nanmean(Abar/decmean, axis=1)
fill = np.outer(np.where(np.isnan(pumamean),1,pumamean), decmean)
Abar = np.where(np.isnan(Abar), fill, Abar)
meta["pums"] = {"workers_metro_res": int(len(res)),
                "cells_workplace": int((~np.isnan(Wp)).sum())}

# ---------------- 7. write the world -----------------------------------------
loc = loc1.copy()
loc["H_units"]      = np.round(H_units).astype(int)
loc["households"]   = np.round(households).astype(int)
loc["rent_data_yr"] = np.round(rent_yr).astype(int)
loc.to_csv(os.path.join(OUT,"locations.csv"), index=False)
np.savetxt(os.path.join(OUT,"abar.csv"),     np.round(Abar), "%d", delimiter=",")
np.savetxt(os.path.join(OUT,"commute.csv"),  np.round(piw,5), "%.5f", delimiter=",")
np.savetxt(os.path.join(OUT,"pitarget.csv"), np.round(pitarget,6), "%.6f", delimiter=",")
for f in ("traveltime.csv","own.csv"):
    pd.read_csv(os.path.join(T1,f), header=None).to_csv(
        os.path.join(OUT,f), header=False, index=False)
with open(os.path.join(OUT,"meta.json"),"w") as f: json.dump(meta, f, indent=1)
print(f"wrote {OUT}  (N={N})")
print(f"  households t0 total {households.sum()/1e6:.2f}M; "
      f"mean rent t0 ${np.nanmean(rent_yr):,.0f}/yr")
