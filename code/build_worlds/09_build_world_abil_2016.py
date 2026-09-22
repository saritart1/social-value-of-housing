#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    09_build_world_abil_2016
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Builds the 2012-2016 vintage of the ability worlds, so the residual-vintage check runs on the memo's core specification.
#  Inputs:  the <metro>_2016 worlds from the 2016 builders above, plus the 2012-2016 PUMS zips.
#  Output:  the <metro>_abil6_2016 worlds shipped in data/worlds/ (memo Table 4).
#  Note:    the 2012-2016 PUMS is on 2010 PUMA geography: wages map through POWPUMA
#            containment; the sorting target allocates each 2010-PUMA's composition
#            to its 2020 PUMAs in proportion to 2016 households.
# ==========================================================
import sys, os, json, zipfile, shutil
import numpy as np
import pandas as pd

MIN_EARN = 1000
AGE_LO, AGE_HI = 18, 70
K = 6
RACE = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PM   = os.path.join(ROOT, "data", "paper1_metros")
SLUGS = ["Boston", "Seattle", "Washington_DC", "Bay_Area", "Los_Angeles", "New_York"]
FIPS2USPS = {"06":"ca","11":"dc","24":"md","25":"ma","33":"nh",
             "34":"nj","36":"ny","51":"va","53":"wa"}

WANT = ["ST","PUMA","POWPUMA","POWSP","PERNP","ADJINC","PWGTP","AGEP",
        "SCHL","SEX","FOD1P","NATIVITY","CIT","DECADE","ENG","RAC1P","HISP"]

def eg6(s):
    return 0 if s <= 15 else (1 if s <= 17 else (2 if s <= 19 else
          (3 if s == 20 else (4 if s == 21 else 5))))

def dummies(s):
    c = pd.Categorical(pd.Series(s).fillna(-1))
    M = np.zeros((len(c), max(len(c.categories) - 1, 0)))
    for j in range(1, len(c.categories)): M[:, j - 1] = (c.codes == j)
    return M

def design(df):
    cols = [dummies([eg6(v) for v in df.SCHL]),
            df.AGEP.values, df.AGEP.values ** 2,
            dummies(df.SEX), dummies(df.FOD1P),
            dummies(df.NATIVITY), dummies(df.CIT), dummies(df.DECADE), dummies(df.ENG)]
    if RACE: cols += [dummies(df.RAC1P), dummies(df.HISP)]
    return np.column_stack(cols)

def build(slug):
    T0  = os.path.join(PM, "worlds", slug + "_2016")
    OUT = os.path.join(PM, "worlds", slug + "_abil6_2016")
    meta0 = json.load(open(os.path.join(T0, "meta.json")))
    puma10_of = meta0["puma20_to_puma10"]
    powgid_of = {g: p[:2] + str(int(p[2:])//100*100).zfill(5) for g, p in puma10_of.items()}
    loc = pd.read_csv(os.path.join(T0, "locations.csv"), dtype={"gid":str,"state":str})
    gids = loc.gid.tolist(); N = len(gids); gpos = {g:i for i,g in enumerate(gids)}
    states = sorted(loc.state.astype(str).str.zfill(2).unique())
    rset = set(puma10_of.values()); powset = set(powgid_of.values())
    stfips = {int(s) for s in states}
    print(f"[{slug}] {N} PUMA20s, {len(rset)} PUMA10s, states {states}")

    # ---- PUMS 2012-2016: person records with the ability traits -------------
    rows = []
    for st in states:
        us = FIPS2USPS[st]
        zf = zipfile.ZipFile(os.path.join(PM, "pums", "raw", f"csv_p{us}_2016.zip"))
        for name in [n for n in zf.namelist() if n.endswith(".csv")]:
            with zf.open(name) as f:
                hdr = pd.read_csv(f, nrows=0).columns
            use = [c for c in WANT if c in hdr]
            with zf.open(name) as f:
                for ch in pd.read_csv(f, usecols=use, chunksize=500_000):
                    for c in WANT:
                        if c not in ch.columns: ch[c] = np.nan
                    ch = ch[(ch.AGEP >= AGE_LO) & (ch.AGEP <= AGE_HI)]
                    ch["earn"] = ch.PERNP * ch.ADJINC / 1e6
                    ch = ch[(ch.earn > MIN_EARN) & ch.SCHL.notna()]
                    ch["rgid"] = ch.ST.astype(int).astype(str).str.zfill(2) + \
                                 ch.PUMA.astype(int).astype(str).str.zfill(5)
                    pow_st = pd.to_numeric(ch.POWSP, errors="coerce")
                    powp   = pd.to_numeric(ch.POWPUMA, errors="coerce")
                    ok = pow_st.isin(stfips) & (powp > 0)
                    ch["powgid"] = ""
                    ch.loc[ok, "powgid"] = pow_st[ok].astype(int).astype(str).str.zfill(2) + \
                        (powp[ok].astype(int)//100*100).astype(str).str.zfill(5)
                    ch = ch[ch.rgid.isin(rset) | ch.powgid.isin(powset)]
                    rows.append(ch[["rgid","powgid","earn","PWGTP","AGEP","SCHL","SEX",
                                    "FOD1P","NATIVITY","CIT","DECADE","ENG","RAC1P","HISP"]])
        zf.close()
    P = pd.concat(rows, ignore_index=True)

    # ---- the ability index: Mincer with PUMA10 fixed effects ----------------
    est = P[P.rgid.isin(rset)].copy()
    w   = est.PWGTP.values.astype(float)
    ly  = np.log(est.earn.values)
    Xc  = design(est)
    FE  = dummies(est.rgid)
    Xf  = np.column_stack([np.ones(len(est)), Xc, FE])
    sw  = np.sqrt(w)
    b, *_ = np.linalg.lstsq(Xf * sw[:, None], ly * sw, rcond=None)
    resid = ly - Xf @ b
    mu = np.average(ly, weights=w)
    r2 = 1 - np.average(resid**2, weights=w) / np.average((ly-mu)**2, weights=w)
    bc = b[1:1 + Xc.shape[1]]
    print(f"  wage equation: {len(est):,} workers, R2 (with PUMA10 FE) = {r2:.3f}")

    full = P.copy()
    Xall = design(full)
    keep = min(Xall.shape[1], bc.shape[0])
    full["abil"] = Xall[:, :keep] @ bc[:keep]

    r  = full[full.rgid.isin(rset)]
    o  = r.sort_values("abil")
    cw = (o.PWGTP.cumsum() / o.PWGTP.sum()).values
    cuts = np.interp(np.arange(1, K) / K, cw, o.abil.values)
    full["k"] = np.digitize(full.abil.values, cuts)
    res = full[full.rgid.isin(rset)].copy()

    # ---- abar: wages by workplace x k, POWPUMA containment ------------------
    def wavg(df, key, keys):
        d = df[df[key].isin(keys)]
        g = d.assign(wx=d.earn*d.PWGTP).groupby([key,"k"])[["wx","PWGTP"]].sum()
        return g.wx / g.PWGTP
    wp = wavg(full, "powgid", powset)
    wr = wavg(res, "rgid", rset)
    Wp = np.full((N,K), np.nan); Wr = np.full((N,K), np.nan)
    for (key,k),v in wp.items():
        for g,i in gpos.items():
            if powgid_of[g] == key: Wp[i,k] = v
    for (key,k),v in wr.items():
        for g,i in gpos.items():
            if puma10_of[g] == key: Wr[i,k] = v
    Abar = np.where(np.isnan(Wp), Wr, Wp)
    colmean = np.nanmean(Abar, axis=0)
    for k in range(K): Abar[np.isnan(Abar[:,k]), k] = colmean[k]

    # ---- sorting target: PUMA10 composition x 2016 households ---------------
    comp = res.groupby(["rgid","k"]).PWGTP.sum().unstack(fill_value=0.0)
    comp = comp.div(comp.sum(axis=1), axis=0)                   # shares within PUMA10
    hh = loc.set_index("gid")["households"].astype(float)
    C = np.zeros((N,K))
    for g,i in gpos.items():
        p10 = puma10_of[g]
        sh = comp.loc[p10].values if p10 in comp.index else np.full(K, 1.0/K)
        C[i,:] = sh * hh[g]
    masses = res.groupby("k").PWGTP.sum().reindex(range(K), fill_value=0).values.astype(float)
    pit = C / C.sum(axis=0, keepdims=True)                      # column shares

    # ---- write the world ----------------------------------------------------
    if os.path.exists(OUT): shutil.rmtree(OUT)
    shutil.copytree(T0, OUT)
    np.savetxt(os.path.join(OUT,"abar.csv"),     Abar, fmt="%.2f",  delimiter=",")
    np.savetxt(os.path.join(OUT,"pitarget.csv"), pit,  fmt="%.10f", delimiter=",")
    np.savetxt(os.path.join(OUT,"masses.csv"),   masses.reshape(1,-1), fmt="%.4f", delimiter=",")
    meta = dict(meta0)
    meta.update({"types": f"predicted-earnings ability, K={K}, race included: {RACE}",
                 "built_by": os.path.basename(__file__),
                 "wage_eq_R2_with_FE": round(float(r2),3),
                 "residence_allocation": "PUMA10 composition x 2016 households per PUMA20"})
    json.dump(meta, open(os.path.join(OUT,"meta.json"),"w"), indent=1)
    print(f"  -> {OUT}")

if __name__ == "__main__":
    todo = sys.argv[1:] or SLUGS
    for s in todo: build(s)
