#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    03_lodes_download
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Downloads the LODES origin-destination files, including neighbor states for cross-border commutes.
#  Inputs:  none beyond the state list in the script.
#  Output:  the LODES files, about 350 MB.
# ==========================================================
"""Paper 1 Tier D: download raw LODES8 (2022) for the metro states + cross-border neighbors.

Grabs per state: geography xwalk, OD main + aux (JT00 = all jobs), WAC (S000 JT00).
Raw .csv.gz saved to data/paper1_metros/lodes/raw/. PUMA assignment is a later
processing step (xwalk carries cbsa + block lat/lon; assign to 2020 PUMA shapefiles).
"""
import os, subprocess
ROOT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
RAW  = os.path.join(ROOT, "data", "paper1_metros", "lodes", "raw")
os.makedirs(RAW, exist_ok=True)
BASE = "https://lehd.ces.census.gov/data/lodes/LODES8"
YEAR = 2022
# metro states (ca dc md va ma nh nj ny wa) + cross-border for OD aux (ct pa wv)
STATES = ["ca","ny","nj","ct","pa","ma","nh","wa","dc","md","va","wv"]

def grab(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  skip {os.path.basename(dest)} (exists)"); return
    print(f"  downloading {os.path.basename(dest)} ...", flush=True)
    r = subprocess.run(["curl","-sL","--retry","4","-o",dest,url])
    ok = r.returncode == 0 and os.path.getsize(dest) > 0
    print(f"    {'ok' if ok else 'FAIL'} {os.path.getsize(dest) if os.path.exists(dest) else 0} bytes", flush=True)

for st in STATES:
    print(f"=== {st} ===", flush=True)
    grab(f"{BASE}/{st}/{st}_xwalk.csv.gz",                       os.path.join(RAW, f"{st}_xwalk.csv.gz"))
    grab(f"{BASE}/{st}/od/{st}_od_main_JT00_{YEAR}.csv.gz",      os.path.join(RAW, f"{st}_od_main_JT00_{YEAR}.csv.gz"))
    grab(f"{BASE}/{st}/od/{st}_od_aux_JT00_{YEAR}.csv.gz",       os.path.join(RAW, f"{st}_od_aux_JT00_{YEAR}.csv.gz"))
    grab(f"{BASE}/{st}/wac/{st}_wac_S000_JT00_{YEAR}.csv.gz",    os.path.join(RAW, f"{st}_wac_S000_JT00_{YEAR}.csv.gz"))
print("LODES DOWNLOAD COMPLETE", flush=True)
