#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    01_acs_pull
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Pulls the ACS 5-year tables by PUMA from the Census API.
#  Inputs:  the crosswalk; a Census API key in .census_api_key at the repository root.
#  Output:  the ACS aggregates for the 409 metro PUMAs.
# ==========================================================
"""Paper 1 (6-metro) Tier B/C/E: ACS 2022 5-year PUMA-level tables via Census API.

Pulls table groups for the 9 states that contain metro PUMAs, keeps estimate (_E)
columns, merges on (state, puma), subsets to the metro crosswalk, writes one tidy CSV.
Uses curl for API calls (macOS Python urllib has SSL cert issues here).
"""
import os, re, json, subprocess
import pandas as pd

ROOT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
OUT  = os.path.join(ROOT, "data", "paper1_metros", "acs")
os.makedirs(OUT, exist_ok=True)
KEY  = open(os.path.join(ROOT, ".census_api_key")).read().strip()
XW   = pd.read_csv(os.path.join(ROOT, "data", "paper1_metros", "crosswalk",
                                "puma_to_metro_crosswalk.csv"),
                   dtype={"state":str,"puma":str})
XW["state"] = XW["state"].str.zfill(2); XW["puma"] = XW["puma"].str.zfill(5)
STATES = sorted(XW["state"].unique())
YEAR = 2022

# table -> human label (the full group is pulled; we keep all _E columns)
TABLES = {
    "B19001": "household income by bracket (sorting target)",
    "B25001": "total housing units (H_j lever)",
    "B25024": "units in structure",
    "B25064": "median gross rent (r_j)",
    "B25031": "median gross rent by bedrooms",
    "B08303": "travel time to work",
    "B15003": "educational attainment (skill)",
    "B01003": "total population",
    "B19013": "median household income",
}

def api_get(table, state):
    url = (f"https://api.census.gov/data/{YEAR}/acs/acs5"
           f"?get=group({table})&for=public%20use%20microdata%20area:*"
           f"&in=state:{state}&key={KEY}")
    raw = subprocess.run(["curl","-sL","--retry","3",url],
                         capture_output=True, text=True, check=True).stdout
    rows = json.loads(raw)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    keep = ["state","public use microdata area"] + \
           [c for c in df.columns if re.fullmatch(rf"{table}_\d+E", c)]
    df = df[keep].rename(columns={"public use microdata area":"puma"})
    return df

merged = None
for table, label in TABLES.items():
    print(f"--- {table}: {label}")
    frames = []
    for st in STATES:
        d = api_get(table, st)
        frames.append(d)
        print(f"    state {st}: {len(d)} pumas, {d.shape[1]-2} vars")
    t = pd.concat(frames, ignore_index=True)
    t["state"] = t["state"].str.zfill(2); t["puma"] = t["puma"].str.zfill(5)
    merged = t if merged is None else merged.merge(t, on=["state","puma"], how="outer")

# numeric coercion (ACS uses negative sentinels for missing/jam values)
val_cols = [c for c in merged.columns if c not in ("state","puma")]
for c in val_cols:
    merged[c] = pd.to_numeric(merged[c], errors="coerce")

full = merged.copy()
metro = XW.merge(merged, on=["state","puma"], how="left")

full_path  = os.path.join(OUT, f"acs5_{YEAR}_puma_allstates.csv")
metro_path = os.path.join(OUT, f"acs5_{YEAR}_puma_6metros.csv")
full.to_csv(full_path, index=False)
metro.to_csv(metro_path, index=False)
print(f"\nWrote {full_path}: {len(full)} PUMAs x {full.shape[1]-2} vars")
print(f"Wrote {metro_path}: {len(metro)} metro PUMAs")
print(metro.groupby("metro")["B25001_001E"].sum().rename("total_housing_units").to_string())
