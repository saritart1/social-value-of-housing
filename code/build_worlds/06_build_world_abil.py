# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    06_build_world_abil
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Assembles the memo's core worlds: earnings predicted from fixed traits with PUMA fixed effects, cut into six ability groups.
#  Inputs:  the downloads from the scripts above; traits: education, age, sex, field of degree, birthplace and arrival cohort, English, race.
#  Output:  the <metro>_abil6 worlds shipped in data/worlds/ (ABIL_RACE=0 builds the norace variant).
#  Note:    the PUMA fixed effects make the index a trait of the person, not the location.
# ==========================================================
"""
Build a metro world with types = PREDICTED-ABILITY DECILES (2026-08-31).

WHY. In the model k is a fixed ABILITY type: predetermined relative to the
location choice, and productivity-relevant (it indexes w_{m,k} and lambda_k).
Ability is unobserved, so it must be proxied.
  * income deciles  -> match rents well, but income is ENDOGENOUS to location
                       (Paul, 2026-08-18). Logically inconsistent.
  * education alone -> exogenous, but explains only 13-19% of log earnings, so
                       it reproduces ~30% of the cross-PUMA earnings gradient.
  * THIS: rank workers by PREDICTED earnings from characteristics fixed before
                       the location choice, and cut deciles. Exogenous, and
                       reproduces ~50-55% of the gradient.

THE INDEX. Mincer-style wage equation, estimated with PUMA FIXED EFFECTS so the
coefficients are WITHIN-location returns and carry no information about where
anyone lives; the index is then the characteristic part of the fitted value,
with the location effect excluded by construction.

    log earn_n = alpha_{PUMA(n)} + X_n' beta + e_n        (weighted OLS, FE)
    ability_n  = X_n' beta                                (location effect OUT)
    k(n)       = decile of ability_n  (population-weighted)

X = education (6 groups) + age + age^2 + sex + field of degree
    + nativity + citizenship + arrival decade + English proficiency
All are settled before the household picks a neighbourhood.
Occupation and industry are EXCLUDED from the headline index (chosen, plausibly
co-determined with location); ABIL_OCC=1 adds them as a sensitivity.
Race/Hispanic origin is excluded on principle: it predicts earnings through
discrimination, not productivity, so it does not belong in an ability index.

Mirrors 20260824_p1_build_world_edu.py in every other respect.
  SLUG=<metro> [K=10] [ABIL_OCC=0] python3 code/20260831_p1_build_world_abil.py
"""
import zipfile, os, json, shutil, numpy as np, pandas as pd

PM   = "data/paper1_metros"
SLUG = os.environ.get("SLUG", "Boston")
SRC  = os.path.join(PM, "worlds", SLUG)
K    = int(os.environ.get("K", "10"))
OCC  = os.environ.get("ABIL_OCC", "0") == "1"
RACE = os.environ.get("ABIL_RACE", "1") == "1"   # 2026-09-04 (Paul 9/01): race IN by
                                                 # default. Excluding it gives low-earning
                                                 # minorities a HIGHER predicted ability
                                                 # than they have, so they receive LESS
                                                 # welfare weight. Positive, not normative.
DST  = os.path.join(PM, "worlds", f"{SLUG}_abil{K}" + ("occ" if OCC else "")
                    + ("" if RACE else "norace"))
MIN_EARN, AGE_LO, AGE_HI = 1000, 18, 70
FIPS2USPS = {"06":"ca","09":"ct","11":"dc","24":"md","25":"ma","33":"nh",
             "34":"nj","36":"ny","42":"pa","51":"va","53":"wa","54":"wv"}
OWN_BY_DEC = [0.33,0.39,0.46,0.52,0.58,0.65,0.71,0.77,0.84,0.90]

L = pd.read_csv(os.path.join(SRC, "locations.csv"), dtype={"gid": str})
gids = L.gid.astype(str).str.zfill(7).tolist()
gpos = {g: i for i, g in enumerate(gids)}
N = len(gids)
states = sorted(set(g[:2] for g in gids))
print(f"{SLUG} ability world, K={K}{' (+occupation)' if OCC else ''}  (states {states})")

USE = (["ST","PUMA20","POWPUMA20","POWSP","PERNP","ADJINC","PWGTP","AGEP","SCHL",
        "SEX","FOD1P","NATIVITY","CIT","DECADE","ENG"]
       + (["RAC1P","HISP"] if RACE else []) + (["OCCP","INDP"] if OCC else []))
powgid_of = {g: g[:2] + str(int(g[2:]) // 100 * 100).zfill(5) for g in gids}
powset = set(powgid_of.values())
rows = []
for st in states:
    us = FIPS2USPS[st]
    zf = zipfile.ZipFile(os.path.join(PM, "pums", "raw", f"csv_p{us}.zip"))
    nm = [n for n in zf.namelist() if n.endswith(".csv")][0]
    with zf.open(nm) as f:
        for ch in pd.read_csv(f, usecols=USE, chunksize=500_000):
            ch = ch[ch.PUMA20 > 0]
            ch = ch[(ch.AGEP >= AGE_LO) & (ch.AGEP <= AGE_HI)]
            ch["earn"] = ch.PERNP * ch.ADJINC / 1e6
            ch = ch[(ch.earn > MIN_EARN) & ch.SCHL.notna()]
            ch["rgid"] = ch.ST.astype(int).astype(str).str.zfill(2) + \
                         ch.PUMA20.astype(int).astype(str).str.zfill(5)
            pw = pd.to_numeric(ch.POWSP, errors="coerce")
            ok = (pw > 0) & (pw < 60) & (ch.POWPUMA20 > 0)
            ch["powgid"] = ""
            ch.loc[ok, "powgid"] = pw[ok].astype(int).astype(str).str.zfill(2) + \
                (ch.loc[ok, "POWPUMA20"].astype(int) // 100).astype(int).astype(str).str.zfill(3) + "00"
            ch = ch[ch.rgid.isin(gpos) | ch.powgid.isin(powset)]
            rows.append(ch[["rgid","powgid","earn","PWGTP"] +
                           [c for c in USE if c not in ("ST","PUMA20","POWPUMA20","POWSP","PERNP","ADJINC","PWGTP")]])
    zf.close()
P = pd.concat(rows, ignore_index=True)

# ---------------------------------------------------------------- the index
def eg6(s):
    return 0 if s <= 15 else (1 if s <= 17 else (2 if s <= 19 else
          (3 if s == 20 else (4 if s == 21 else 5))))
def dummies(s):
    c = pd.Categorical(pd.Series(s).fillna(-1))
    M = np.zeros((len(c), max(len(c.categories) - 1, 0)))
    for j in range(1, len(c.categories)): M[:, j - 1] = (c.codes == j)
    return M

est = P[P.rgid.isin(gpos)].copy()                 # estimate on metro residents
w   = est.PWGTP.values.astype(float)
ly  = np.log(est.earn.values)
def design(df):
    cols = [dummies([eg6(v) for v in df.SCHL]),
            df.AGEP.values, df.AGEP.values ** 2,
            dummies(df.SEX), dummies(df.FOD1P),
            dummies(df.NATIVITY), dummies(df.CIT), dummies(df.DECADE), dummies(df.ENG)]
    if RACE: cols += [dummies(df.RAC1P), dummies(df.HISP)]
    if OCC:  cols += [dummies(df.OCCP), dummies(df.INDP)]
    return np.column_stack(cols)

Xc  = design(est)
FE  = dummies(est.rgid)                            # PUMA fixed effects
Xf  = np.column_stack([np.ones(len(est)), Xc, FE])
sw  = np.sqrt(w)
b, *_ = np.linalg.lstsq(Xf * sw[:, None], ly * sw, rcond=None)
resid = ly - Xf @ b
mu    = np.average(ly, weights=w)
r2    = 1 - np.average(resid ** 2, weights=w) / np.average((ly - mu) ** 2, weights=w)
bc    = b[1:1 + Xc.shape[1]]                       # CHARACTERISTIC coefficients only
print(f"  wage equation: {len(est):,} workers, R2 (with PUMA FE) = {r2:.3f},"
      f" {Xc.shape[1]} characteristic terms + {FE.shape[1]} FE")

# the index, for EVERY record (residents and in-commuters alike)
# rebuild on the FULL sample with the SAME category ordering
full = P.copy()
Xall = design(full)
if Xall.shape[1] != Xc.shape[1]:      # a category present only among in-commuters
    keep = min(Xall.shape[1], Xc.shape[1])
    Xall = Xall[:, :keep]; bb = bc[:keep]
else:
    bb = bc
full["abil"] = Xall @ bb                            # location effect EXCLUDED

# population-weighted deciles, cut on metro RESIDENTS
r  = full[full.rgid.isin(gpos)]
o  = r.sort_values("abil")
cw = (o.PWGTP.cumsum() / o.PWGTP.sum()).values
cuts = np.interp((np.arange(1, K) / K), cw, o.abil.values)
full["k"] = np.digitize(full.abil.values, cuts)
res = full[full.rgid.isin(gpos)].copy()
print(f"  {len(res):,} metro-resident worker records, {res.PWGTP.sum():,.0f} weighted")

# ---- abar: weighted mean earnings by workplace x type ----------------------
def wavg(df, key, keys):
    d = df[df[key].isin(keys)]
    g = d.assign(wx=d.earn * d.PWGTP).groupby([key, "k"])[["wx", "PWGTP"]].sum()
    return g.wx / g.PWGTP
wp = wavg(full, "powgid", powset)
wr = wavg(res, "rgid", set(gids))
Wp = np.full((N, K), np.nan); Wr = np.full((N, K), np.nan)
for (kk, e), v in wp.items():
    for g2, i in gpos.items():
        if powgid_of[g2] == kk: Wp[i, e] = v
for (kk, e), v in wr.items(): Wr[gpos[kk], e] = v
Abar = np.where(np.isnan(Wp), Wr, Wp)
gmean = np.nanmean(Abar, axis=0)
pmean = np.nanmean(Abar / gmean, axis=1)
Abar = np.where(np.isnan(Abar), np.outer(np.where(np.isnan(pmean), 1, pmean), gmean), Abar)
print(f"  abar cells from workplace: {(~np.isnan(Wp)).sum()}/{N*K}")

# ---- pitarget / masses / own ------------------------------------------------
ct  = res.groupby(["rgid", "k"]).PWGTP.sum().unstack(fill_value=0.0)
ct  = ct.reindex(index=gids, columns=range(K), fill_value=0.0)
pit = np.maximum(ct.values.astype(float), 1e-9)
pit = pit / pit.sum(axis=0, keepdims=True)
shares = res.groupby("k").PWGTP.sum().reindex(range(K), fill_value=0.0).values
shares = shares / shares.sum()
M = shares * L.households.sum()
oo = res.sort_values("earn"); cw2 = (oo.PWGTP.cumsum() / oo.PWGTP.sum()).values
mean_earn = [float(np.average(res.earn[res.k == e], weights=res.PWGTP[res.k == e]))
             if (res.k == e).any() else float("nan") for e in range(K)]
pct = [float(np.interp(m, oo.earn.values, cw2)) for m in mean_earn]
own = np.interp(pct, (np.arange(10) + 0.5) / 10, OWN_BY_DEC)

# ---- write ------------------------------------------------------------------
os.makedirs(DST, exist_ok=True)
for f in ["locations.csv", "traveltime.csv", "commute.csv", "kids_hh.csv"]:
    shutil.copy(os.path.join(SRC, f), os.path.join(DST, f))
np.savetxt(os.path.join(DST, "abar.csv"), Abar, delimiter=",", fmt="%.2f")
np.savetxt(os.path.join(DST, "pitarget.csv"), pit, delimiter=",", fmt="%.10f")
np.savetxt(os.path.join(DST, "own.csv"), own.reshape(1, -1), delimiter=",", fmt="%.4f")
np.savetxt(os.path.join(DST, "masses.csv"), M.reshape(1, -1), delimiter=",", fmt="%.4f")
meta = json.load(open(os.path.join(SRC, "meta.json")))
meta["type_dimension"] = {
    "kind": "predicted_ability_deciles", "K": K, "with_occupation": OCC,
    "wage_equation_r2_with_puma_fe": round(float(r2), 4),
    "index": "characteristic part of a PUMA-fixed-effects log-earnings regression",
    "covariates": (["education(6)","age","age^2","sex","field of degree","nativity",
                    "citizenship","arrival decade","English"]
                   + (["race","hispanic origin"] if RACE else [])
                   + (["occupation","industry"] if OCC else [])),
    "with_race": RACE,
    "group_share_of_workers": shares.round(4).tolist(),
    "mean_earnings": mean_earn,
    "earnings_percentile_of_group_mean": [round(p, 3) for p in pct]}
json.dump(meta, open(os.path.join(DST, "meta.json"), "w"), indent=1)

print(f"\n  {'type':>6} {'share':>7} {'mean earn':>11} {'own':>6}")
for e in range(K):
    print(f"  {e+1:>6} {shares[e]*100:>6.1f}% {mean_earn[e]:>11,.0f} {own[e]:>6.2f}")
print(f"\n  earnings spread across types: {mean_earn[-1]/mean_earn[0]:.2f}x")
print(f"written -> {DST}")
