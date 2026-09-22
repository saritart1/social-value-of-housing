#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    05_validate_traveltimes
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Sanity checks on the travel-time matrices.
#  Inputs:  the travel-time matrices.
#  Output:  printed diagnostics only.
# ==========================================================
"""Cross-check OSMnx free-flow travel times against ACS observed commute times.

Logic: weight the free-flow t_{jm} matrix by LODES commute shares pi^w_{jm} to get a
model-implied mean commute time per residence PUMA, then compare to the ACS B08303
observed mean commute time. They are NOT expected to match exactly: ACS is all-modes,
congested, and includes out-of-metro jobs; ours is auto free-flow within metro. We
check (a) magnitudes are sane, (b) they correlate across PUMAs, (c) the implied
congestion/mode ratio (ACS/free-flow) is plausible (>1, ~1.2-1.7).

Usage: python ...validate_traveltimes.py "Seattle" wa
       (last args = lowercase state(s) whose LODES od files cover the metro)
"""
import os, sys, glob
import numpy as np, pandas as pd, geopandas as gpd

ROOT="/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
P1=os.path.join(ROOT,"data","paper1_metros")
metro=sys.argv[1]; states=[s.lower() for s in sys.argv[2:]]

xw=pd.read_csv(os.path.join(P1,"crosswalk","puma_to_metro_crosswalk.csv"),dtype={"state":str,"puma":str})
xw["state"]=xw["state"].str.zfill(2); xw["puma"]=xw["puma"].str.zfill(5); xw["pid"]=xw["state"]+xw["puma"]
sub=xw[xw["metro"]==metro]; metro_pids=set(sub["pid"])
cbsa=str(sub["cbsa"].iloc[0])

# --- travel-time matrix (free-flow, minutes) ---
T=pd.read_csv(os.path.join(P1,"travel_times",f"tmin_{metro.replace(' ','_')}.csv"),index_col=0)
T.index=T.index.astype(str); T.columns=T.columns.astype(str)

# --- block -> PUMA for metro blocks (spatial join of block points to 2020 PUMA polygons) ---
print(f"[{metro}] building block->PUMA ...",flush=True)
blk2puma={}
for st in states:
    xwlk=pd.read_csv(os.path.join(P1,"lodes","raw",f"{st}_xwalk.csv.gz"),
                     dtype={"tabblk2020":str,"cbsa":str},
                     usecols=["tabblk2020","cbsa","blklatdd","blklondd"])
    xwlk=xwlk[xwlk["cbsa"]==cbsa].dropna(subset=["blklatdd","blklondd"])
    if not len(xwlk): continue
    fips=st_fips=xwlk["tabblk2020"].str[:2].iloc[0]
    poly=gpd.read_file(glob.glob(os.path.join(P1,"shapefiles",f"tl_2022_{st_fips}_puma20.shp"))[0])
    poly["pid"]=poly["STATEFP20"].str.zfill(2)+poly["PUMACE20"].str.zfill(5)
    g=gpd.GeoDataFrame(xwlk,geometry=gpd.points_from_xy(xwlk["blklondd"],xwlk["blklatdd"]),crs=4326).to_crs(poly.crs)
    j=gpd.sjoin(g,poly[["pid","geometry"]],how="left",predicate="within")
    blk2puma.update(dict(zip(j["tabblk2020"],j["pid"])))
print(f"[{metro}] blocks mapped: {len(blk2puma):,}",flush=True)

# --- LODES OD (main + aux) -> PUMA pair flows ---
flows={}
for st in states:
    for kind in ("main","aux"):
        f=os.path.join(P1,"lodes","raw",f"{st}_od_{kind}_JT00_2022.csv.gz")
        if not os.path.exists(f): continue
        od=pd.read_csv(f,dtype={"w_geocode":str,"h_geocode":str},usecols=["w_geocode","h_geocode","S000"])
        od["hp"]=od["h_geocode"].map(blk2puma); od["wp"]=od["w_geocode"].map(blk2puma)
        od=od.dropna(subset=["hp","wp"])
        for hp,wp,s in zip(od["hp"],od["wp"],od["S000"]):
            flows[(hp,wp)]=flows.get((hp,wp),0)+s
fl=pd.DataFrame([(h,w,s) for (h,w),s in flows.items()],columns=["hp","wp","jobs"])
fl=fl[fl["hp"].isin(metro_pids) & fl["wp"].isin(metro_pids)]   # within-metro commutes
print(f"[{metro}] within-metro OD pairs: {len(fl):,}  total jobs: {int(fl['jobs'].sum()):,}",flush=True)

# --- model-implied mean commute time per residence PUMA = sum_m pi_{jm} t_{jm} ---
rows=[]
for hp,grp in fl.groupby("hp"):
    w=grp.set_index("wp")["jobs"]; w=w[w.index.isin(T.columns)]
    if w.sum()==0 or hp not in T.index: continue
    t=T.loc[hp,w.index].astype(float)
    implied=float((w*t).sum()/w.sum())
    rows.append((hp,implied,int(w.sum())))
imp=pd.DataFrame(rows,columns=["pid","implied_freeflow_min","workers"])

# --- ACS observed mean commute time (B08303) per PUMA ---
acs=pd.read_csv(os.path.join(P1,"acs","acs5_2022_puma_6metros.csv"),dtype={"state":str,"puma":str})
acs["state"]=acs["state"].str.zfill(2); acs["puma"]=acs["puma"].str.zfill(5); acs["pid"]=acs["state"]+acs["puma"]
mids=[2.5,7,12,17,22,27,32,37,42,52,74,100]  # B08303_002..013 bin midpoints (min)
cols=[f"B08303_{i:03d}E" for i in range(2,14)]
acs["acs_mean_min"]=sum(acs[c]*m for c,m in zip(cols,mids))/acs[[c for c in cols]].sum(axis=1)
obs=acs[acs["pid"].isin(metro_pids)][["pid","acs_mean_min"]]

m=imp.merge(obs,on="pid")
m["ratio_acs_over_freeflow"]=m["acs_mean_min"]/m["implied_freeflow_min"]
r=np.corrcoef(m["implied_freeflow_min"],m["acs_mean_min"])[0,1]
print(f"\n=== {metro}: free-flow (model) vs ACS observed commute, {len(m)} PUMAs ===")
print(f"  implied free-flow mean: {m['implied_freeflow_min'].mean():.1f} min  (range {m['implied_freeflow_min'].min():.0f}-{m['implied_freeflow_min'].max():.0f})")
print(f"  ACS observed mean:      {m['acs_mean_min'].mean():.1f} min  (range {m['acs_mean_min'].min():.0f}-{m['acs_mean_min'].max():.0f})")
print(f"  ratio ACS/free-flow:    {m['ratio_acs_over_freeflow'].mean():.2f}  (expect >1: congestion+transit+longer trips)")
print(f"  cross-PUMA correlation: {r:.2f}")
m.sort_values("implied_freeflow_min").to_csv(os.path.join(P1,"travel_times",f"validate_{metro.replace(' ','_')}.csv"),index=False)
print(f"  wrote validate_{metro.replace(' ','_')}.csv")
