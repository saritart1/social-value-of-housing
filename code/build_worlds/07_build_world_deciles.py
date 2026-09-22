#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    07_build_world_deciles
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Assembles worlds with ten income-decile types from the downloads.
#  Inputs:  the downloads from the scripts above.
#  Output:  one world folder per metro, ten income-decile types.
#  Note:    needed only as the first stage of the vintage-check chain (the 2016 builders
#            below start from these worlds); the memo's core worlds come from the ability builder.
# ==========================================================
"""Paper 1 — build one metro's REAL-DATA world for the MATLAB engine.

Usage:  python3 20260706_p1_build_world.py "Seattle"
        (metros: Seattle, Bay Area, Boston, Washington DC, Los Angeles, New York)

Reads the six-metro downloads in data/paper1_metros/ (see DATA_MANIFEST.md) and
writes data/paper1_metros/worlds/<slug>/ with CSVs mirroring pp_fakeworld's W:
  locations.csv   gid,state,puma,name,L_km2,H_units,households,rent_data_yr,
                  mu_pct,mc_yr,lat,lon    (row order = the model's location order)
  abar.csv        N x 10 annual earnings by decile (workplace-coded where possible)
  traveltime.csv  N x N minutes (free-flow, from OSMnx matrices)
  commute.csv     N x N residence->workplace shares (LODES 2022, rows sum to 1)
  pitarget.csv    N x 10 sorting target: PUMA j's share of the metro's decile-k
                  households (columns sum to 1) — the kappa-inversion target
  own.csv         1 x 10 homeownership by decile (PLACEHOLDER national gradient)
  meta.json       parameters, coverage diagnostics, decile cutoffs

v0 approximations (all flagged here and in meta.json):
  - Deciles = PUMS PERSON-earnings deciles for wages, ACS HOUSEHOLD-income
    deciles (B19001) for the sorting target. A household-PUMS join unifies them.
  - PUMS restricted to PUMA20 vintage rows (2022 collection year) for clean 2020
    geography (~1/5 of the 5-yr sample).
  - mc_yr flat per metro (annualized structure cost; FHFA land/structure refines).
  - own_k national-shaped placeholder (needs household PUMS TEN).
  - mu: Opportunity Atlas kfr_p25 rank -> % earnings via RANK2INC x CAUSAL_SHARE.
"""
import sys, os, json, io, zipfile, gzip
import numpy as np
import pandas as pd
import geopandas as gpd

# ---------------- parameters (the v0 judgment calls, all in one place) -------
USER_COST    = 0.05     # annualization of structure value -> $/yr (interest+
                        # depreciation+maintenance); sensitivity 0.04-0.07
MC_YR        = 12000    # fallback flat $/yr if FHFA structure value missing
OWN_BY_DEC   = np.round(np.linspace(0.33, 0.90, 10), 2)   # placeholder tenure
RANK2INC     = 3.0      # % adult earnings per kfr rank point (Chetty rank-rank)
CAUSAL_SHARE = 0.55     # causal share of the observed place gradient (CH movers)
MIN_EARN     = 1000     # $ floor to count as a worker (PUMS)
AGE_LO, AGE_HI = 18, 70

HERE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.normpath(os.path.join(HERE, ".."))
PM    = os.path.join(ROOT, "data", "paper1_metros")
SLUG  = {"Seattle":"Seattle", "Bay Area":"Bay_Area", "Boston":"Boston",
         "Washington DC":"Washington_DC", "Los Angeles":"Los_Angeles",
         "New York":"New_York"}
FIPS2USPS = {"06":"ca","09":"ct","11":"dc","24":"md","25":"ma","33":"nh",
             "34":"nj","36":"ny","42":"pa","51":"va","53":"wa","54":"wv"}

metro = sys.argv[1] if len(sys.argv) > 1 else "Seattle"
slug  = SLUG[metro]
OUT   = os.path.join(PM, "worlds", slug)
os.makedirs(OUT, exist_ok=True)
meta  = {"metro": metro, "params": {"USER_COST": USER_COST, "MC_YR_fallback": MC_YR,
         "RANK2INC": RANK2INC, "CAUSAL_SHARE": CAUSAL_SHARE,
         "OWN_BY_DEC": OWN_BY_DEC.tolist()}}

# ---------------- 1. crosswalk: the metro's PUMAs (the location universe) ----
xw = pd.read_csv(os.path.join(PM, "crosswalk", "puma_to_metro_crosswalk.csv"),
                 dtype={"state":str, "puma":str, "cbsa":str})
xw = xw[xw.metro == metro].copy()
xw["gid"] = xw.state + xw.puma
xw = xw.sort_values("gid").reset_index(drop=True)
gids   = xw.gid.tolist()
N      = len(gids)
states = sorted(xw.state.unique())
cbsas  = set(xw.cbsa.unique())
gpos   = {g:i for i,g in enumerate(gids)}
print(f"[{metro}] {N} PUMAs, states {states}, CBSAs {sorted(cbsas)}")

# ---------------- 2. shapefiles: land area + centroid ------------------------
shp = pd.concat([gpd.read_file(os.path.join(PM,"shapefiles",f"tl_2022_{st}_puma20.shp"))
                 for st in states])
shp = shp[shp.GEOID20.isin(gids)].set_index("GEOID20")
L_km2 = (shp.ALAND20.astype(float)/1e6).reindex(gids).values
lat   = shp.INTPTLAT20.astype(float).reindex(gids).values
lon   = shp.INTPTLON20.astype(float).reindex(gids).values

# ---------------- 3. ACS: H, rents, B19001 decile target ---------------------
acs = pd.read_csv(os.path.join(PM,"acs","acs5_2022_puma_6metros.csv"),
                  dtype={"state":str,"puma":str})
acs["gid"] = acs.state + acs.puma
acs = acs.set_index("gid").reindex(gids)
H_units    = acs.B25001_001E.values.astype(float)
households = acs.B19001_001E.values.astype(float)
rent_yr    = acs.B25064_001E.values.astype(float) * 12          # $/yr median gross rent

# B19001 brackets ($000): 16 bins; top bin treated as [200, 400]
EDGES = np.array([0,10,15,20,25,30,35,40,45,50,60,75,100,125,150,200,400], float)*1000
bcols = [f"B19001_{i:03d}E" for i in range(2,18)]
BC    = acs[bcols].values.astype(float)                          # N x 16
tot   = BC.sum(axis=0)                                           # metro counts per bracket
cum   = np.concatenate([[0], np.cumsum(tot)]) / tot.sum()
qcut  = np.interp(np.arange(1,10)/10, cum, EDGES)                # 9 interior cutpoints ($)
DQ    = np.concatenate([[EDGES[0]], qcut, [EDGES[-1]]])          # 11 decile edges
pit   = np.zeros((N,10))
for b in range(16):                                              # uniform within bracket
    lo, hi = EDGES[b], EDGES[b+1]
    for d in range(10):
        ov = max(0.0, min(hi, DQ[d+1]) - max(lo, DQ[d]))
        if ov > 0: pit[:,d] += BC[:,b] * ov/(hi-lo)
pitarget = pit / pit.sum(axis=0)                                 # cols sum to 1
meta["decile_cutoffs_hh_income"] = np.round(DQ).tolist()

# ---------------- 4. LODES: block->PUMA, commute shares, employment ----------
print("LODES: assigning metro blocks to PUMAs...")
# Filter blocks by the metro PUMA polygons themselves (bounding box + spatial
# join), NOT by the LODES cbsa code -- CBSA vintages differ and PUMAs can
# straddle CBSA lines (e.g. DC's Calvert & St. Mary's PUMA lost all its blocks
# under a cbsa filter).
minx, miny, maxx, maxy = shp.total_bounds
blk2gid = {}
poly = shp[["geometry"]].reset_index()
for st in states:
    us = FIPS2USPS[st]
    xk = pd.read_csv(os.path.join(PM,"lodes","raw",f"{us}_xwalk.csv.gz"),
                     usecols=["tabblk2020","blklatdd","blklondd"],
                     dtype={"tabblk2020":str})
    xk = xk.dropna(subset=["blklatdd","blklondd"])
    xk = xk[(xk.blklondd>=minx)&(xk.blklondd<=maxx)&
            (xk.blklatdd>=miny)&(xk.blklatdd<=maxy)]
    pts = gpd.GeoDataFrame(xk, geometry=gpd.points_from_xy(xk.blklondd, xk.blklatdd),
                           crs="EPSG:4269")
    j = gpd.sjoin(pts, poly, how="inner", predicate="within")
    blk2gid.update(dict(zip(j.tabblk2020, j.GEOID20)))
tract2gid = {}
for st in states:      # tract20 -> gid via block majority (for Opportunity Atlas)
    us = FIPS2USPS[st]
    xk = pd.read_csv(os.path.join(PM,"lodes","raw",f"{us}_xwalk.csv.gz"),
                     usecols=["tabblk2020","trct"], dtype=str)
    xk["gid"] = xk.tabblk2020.map(blk2gid)
    xk = xk.dropna(subset=["gid"])
    m  = xk.groupby("trct").gid.agg(lambda s: s.mode().iat[0])
    tract2gid.update(m.to_dict())
print(f"  {len(blk2gid):,} metro blocks, {len(tract2gid):,} tracts mapped")

print("LODES: aggregating OD flows...")
F = np.zeros((N,N))                                              # residence x workplace
for st in states:
    us = FIPS2USPS[st]
    for part in ("main","aux"):
        fp = os.path.join(PM,"lodes","raw",f"{us}_od_{part}_JT00_2022.csv.gz")
        for ch in pd.read_csv(fp, usecols=["w_geocode","h_geocode","S000"],
                              dtype={"w_geocode":str,"h_geocode":str,"S000":"int32"},
                              chunksize=2_000_000):
            ch["wg"] = ch.w_geocode.map(blk2gid); ch["hg"] = ch.h_geocode.map(blk2gid)
            ch = ch.dropna(subset=["wg","hg"])
            g = ch.groupby(["hg","wg"]).S000.sum()
            for (hg,wg),v in g.items(): F[gpos[hg], gpos[wg]] += v
rs = F.sum(axis=1, keepdims=True)
meta["lodes_zero_flow_pumas"] = int((rs.ravel()==0).sum())
rs[rs==0] = 1.0                                                 # gravity fallback below
piw = F / rs
piw[F.sum(axis=1)==0, :] = np.nan                               # marked, filled after T
meta["lodes_jobs_within_metro"] = int(F.sum())

# ---------------- 5. PUMS: wages by workplace POWPUMA x decile ----------------
# POWPUMA20 is a COARSER geography than PUMA20 (county groups; code =
# floor(PUMA/100)*100 with minor variants). So workplace wages are identified
# at POWPUMA level and each PUMA inherits its POWPUMA's wage schedule;
# residence-PUMA wages fill any missing cells.
print("PUMS: earnings by workplace POWPUMA x decile...")
powgid_of = {g: g[:2] + str(int(g[2:])//100*100).zfill(5) for g in gids}
powset    = set(powgid_of.values())
rows = []
for st in states:
    us = FIPS2USPS[st]
    zf = zipfile.ZipFile(os.path.join(PM,"pums","raw",f"csv_p{us}.zip"))
    name = [n for n in zf.namelist() if n.endswith(".csv")][0]
    with zf.open(name) as f:
        for ch in pd.read_csv(f, usecols=["ST","PUMA20","POWPUMA20","POWSP","PERNP",
                                          "ADJINC","PWGTP","AGEP"],
                              chunksize=500_000):
            ch = ch[(ch.PUMA20 > 0)]                              # 2022-vintage rows only
            ch = ch[(ch.AGEP>=AGE_LO)&(ch.AGEP<=AGE_HI)]
            ch["earn"] = ch.PERNP * ch.ADJINC/1e6
            ch = ch[ch.earn > MIN_EARN]
            ch["rgid"] = ch.ST.astype(int).astype(str).str.zfill(2) + \
                         ch.PUMA20.astype(int).astype(str).str.zfill(5)
            pow_st = pd.to_numeric(ch.POWSP, errors="coerce")
            ok = (pow_st>0)&(pow_st<60)&(ch.POWPUMA20>0)
            ch["powgid"] = ""
            ch.loc[ok,"powgid"] = pow_st[ok].astype(int).astype(str).str.zfill(2) + \
                (ch.loc[ok,"POWPUMA20"].astype(int)//100*100).astype(str).str.zfill(5)
            ch = ch[ch.rgid.isin(gpos) | ch.powgid.isin(powset)]
            rows.append(ch[["rgid","powgid","earn","PWGTP"]])
    zf.close()
P = pd.concat(rows, ignore_index=True)
res = P[P.rgid.isin(gpos)].copy()
# metro-wide weighted earnings decile cutoffs (residents)
o = res.sort_values("earn"); cw = o.PWGTP.cumsum()/o.PWGTP.sum()
cuts = np.interp(np.arange(1,10)/10, cw, o.earn)
meta["decile_cutoffs_person_earnings"] = np.round(cuts).tolist()
P["dec"] = np.searchsorted(cuts, P.earn) + 1                     # 1..10
res["dec"] = np.searchsorted(cuts, res.earn) + 1
pow_match = float(res.powgid.isin(powset).mean())
meta["pums"] = {"workers_metro_res": int(len(res)),
                "powpuma_match_rate": round(pow_match,3)}
print(f"  {len(res):,} metro-resident workers; POWPUMA-in-metro match {pow_match:.2f}")

def wavg_table(df, col, keys):
    d = df[df[col].isin(keys)]
    g = d.assign(wx=d.earn*d.PWGTP).groupby([col,"dec"])[["wx","PWGTP"]].sum()
    return (g.wx/g.PWGTP)                                        # Series (key, dec)

wp = wavg_table(P, "powgid", powset)                             # workplace wages
wr = wavg_table(res, "rgid", set(gids))                          # residence fallback
Wp = np.full((N,10), np.nan); Wr = np.full((N,10), np.nan)
for (k,d),v in wp.items():
    for g2,i in gpos.items():
        if powgid_of[g2] == k: Wp[i,d-1] = v
for (k,d),v in wr.items(): Wr[gpos[k], d-1] = v
Abar = np.where(np.isnan(Wp), Wr, Wp)
decmean = np.nanmean(Abar, axis=0)                               # fill remaining gaps
pumamean = np.nanmean(Abar/decmean, axis=1)
fill = np.outer(np.where(np.isnan(pumamean),1,pumamean), decmean)
Abar = np.where(np.isnan(Abar), fill, Abar)
meta["pums"]["cells_workplace"] = int((~np.isnan(Wp)).sum())
meta["pums"]["cells_gap_filled"] = int(np.isnan(np.where(np.isnan(Wp),Wr,Wp)).sum())

# ---------------- 6. travel times (already built) -----------------------------
tt = pd.read_csv(os.path.join(PM,"travel_times",f"tmin_{slug}.csv"), index_col=0)
tt.index = tt.index.astype(str).str.zfill(7); tt.columns = [c.zfill(7) for c in tt.columns.astype(str)]
T = tt.reindex(index=gids, columns=gids).values
assert not np.isnan(T).any(), "travel-time matrix misaligned"
# impute non-finite cells (disconnected OSM nodes, e.g. one Bay Area PUMA):
# centroid haversine distance at 36 mph free-flow x 1.3 route factor
bad = ~np.isfinite(T)
if bad.any():
    la, lo = np.radians(lat), np.radians(lon)
    dla = la[:,None]-la[None,:]; dlo = lo[:,None]-lo[None,:]
    a = np.sin(dla/2)**2 + np.cos(la)[:,None]*np.cos(la)[None,:]*np.sin(dlo/2)**2
    km = 6371*2*np.arcsin(np.sqrt(a))
    T[bad] = (km/0.6*1.3)[bad]
    meta["traveltime_imputed_cells"] = int(bad.sum())
np.fill_diagonal(T, np.maximum(np.diag(T), 0.5*np.sqrt(L_km2/np.pi)/0.6))  # nonzero self-time
# gravity fallback for any PUMA with zero LODES flows (uses the final T)
nanrows = np.isnan(piw).any(axis=1)
if nanrows.any():
    G = np.exp(-0.05*T[nanrows,:]); piw[nanrows,:] = G/G.sum(axis=1, keepdims=True)

# ---------------- 7. Opportunity Atlas mobility -------------------------------
print("Opportunity Atlas: kfr_p25 -> mu_pct...")
oa = pd.read_csv(os.path.join(PM,"opportunity_atlas","tract_outcomes_simple.csv"),
                 usecols=["state","county","tract","kfr_pooled_pooled_p25"],
                 dtype={"state":str,"county":str,"tract":str})
oa["t10"] = oa.state.str.zfill(2)+oa.county.str.zfill(3)+oa.tract.str.zfill(6)
cw10 = pd.read_csv(os.path.join(ROOT,"data","crosswalks","tab20_tract20_tract10_natl.txt"),
                   sep="|", usecols=["GEOID_TRACT_20","GEOID_TRACT_10","AREALAND_PART"],
                   dtype={"GEOID_TRACT_20":str,"GEOID_TRACT_10":str})
cw10 = cw10[cw10.GEOID_TRACT_20.str[:2].isin(states)]
cw10 = cw10.sort_values("AREALAND_PART").drop_duplicates("GEOID_TRACT_20", keep="last")
t20 = cw10.merge(oa[["t10","kfr_pooled_pooled_p25"]], left_on="GEOID_TRACT_10",
                 right_on="t10", how="inner")
t20["gid"] = t20.GEOID_TRACT_20.map(tract2gid)
kfr = t20.dropna(subset=["gid","kfr_pooled_pooled_p25"]).groupby("gid") \
         .kfr_pooled_pooled_p25.mean().reindex(gids)
kfr = kfr.fillna(kfr.mean())
mu_pct = ((kfr.values - np.average(kfr.values, weights=households)) * 100
          * RANK2INC * CAUSAL_SHARE)
meta["mu_pct_range"] = [round(float(mu_pct.min()),2), round(float(mu_pct.max()),2)]

# ---------------- 7b. FHFA land/structure -> construction cost mc_j -----------
# Davis-Larson-Oliner-Shui (FHFA) tract cross-section: structure value =
# property value (as-is) x (1 - land share). mc_yr = USER_COST x structure
# value. This is the CONSTRUCTION side of the price; the land/scarcity part is
# what deregulation competes away. Single-family parcels (v1 caveat: the
# marginal multifamily unit's structure cost differs).
print("FHFA: structure value -> mc_yr...")
fh = pd.read_excel(os.path.join(PM,"land_prices","land-prices_2024.xlsx"),
                   sheet_name="Cross-Section Census Tracts", skiprows=1)
fh.columns = ["state_name","county_name","tract","land_val_std","land_val_acre",
              "land_share","lot_size","sqft","prop_val_std","prop_val_asis"]
fh["t11"] = fh.tract.astype(str).str.replace(".0","",regex=False).str.zfill(11)
fh = fh[fh.t11.str[:2].isin(states)]
fh["struct_val"] = pd.to_numeric(fh.prop_val_asis, errors="coerce") * \
                   (1 - pd.to_numeric(fh.land_share, errors="coerce"))
# try 2020-tract match first; if poor, treat FHFA tracts as 2010 vintage and
# route through the tract10->tract20 crosswalk (largest-overlap assignment)
fh["gid"] = fh.t11.map(tract2gid)
mm = fh.dropna(subset=["gid","struct_val"])
match20 = len(mm)
if match20 < 0.5 * len(tract2gid):
    t10to20 = (cw10.sort_values("AREALAND_PART")
                   .drop_duplicates("GEOID_TRACT_10", keep="last")
                   .set_index("GEOID_TRACT_10").GEOID_TRACT_20)
    fh["gid"] = fh.t11.map(t10to20).map(tract2gid)
    mm = fh.dropna(subset=["gid","struct_val"])
    meta.setdefault("fhfa", {})["vintage"] = "2010-routed"
match20 = len(mm)
mc_struct = mm.groupby("gid").struct_val.median().reindex(gids)
mc_struct = mc_struct.fillna(mc_struct.median())
mc = (USER_COST * mc_struct.values)
mc = np.where(np.isnan(mc), MC_YR, mc)
meta.setdefault("fhfa", {}).update({"tracts_matched": int(match20),
                "mc_yr_range": [int(np.nanmin(mc)), int(np.nanmax(mc))],
                "struct_val_median": int(np.nanmedian(mc_struct.values))})
print(f"  {match20:,} tracts matched; mc_yr {int(mc.min()):,} - {int(mc.max()):,} $/yr")

# ---------------- 8. write the world ------------------------------------------
loc = pd.DataFrame({"gid":gids, "state":xw.state, "puma":xw.puma,
    "name":xw.puma_name.str.replace(" PUMA","",regex=False),
    "L_km2":np.round(L_km2,2), "H_units":H_units.astype(int),
    "households":households.astype(int), "rent_data_yr":np.round(rent_yr).astype(int),
    "mu_pct":np.round(mu_pct,2), "mc_yr":np.round(mc).astype(int),
    "lat":np.round(lat,4), "lon":np.round(lon,4)})
loc.to_csv(os.path.join(OUT,"locations.csv"), index=False)
np.savetxt(os.path.join(OUT,"abar.csv"),        np.round(Abar),      "%d", delimiter=",")
np.savetxt(os.path.join(OUT,"traveltime.csv"),  np.round(T,1),       "%.1f", delimiter=",")
np.savetxt(os.path.join(OUT,"commute.csv"),     np.round(piw,5),     "%.5f", delimiter=",")
np.savetxt(os.path.join(OUT,"pitarget.csv"),    np.round(pitarget,6),"%.6f", delimiter=",")
np.savetxt(os.path.join(OUT,"own.csv"),         OWN_BY_DEC[None,:],  "%.2f", delimiter=",")
with open(os.path.join(OUT,"meta.json"),"w") as f: json.dump(meta, f, indent=1)
print(f"wrote {OUT}  (N={N})")
