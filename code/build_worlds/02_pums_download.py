#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    02_pums_download
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Downloads the ACS PUMS person files for the nine metro states.
#  Inputs:  none beyond the state list in the script.
#  Output:  the PUMS zips, about 650 MB.
# ==========================================================
"""Paper 1 Tier C: download ACS 2022 5-year PUMS PERSON files for the 9 metro states.

Person records carry earnings (WAGP/PERNP/PINCP) by PUMA x education (SCHL) x
occupation, the inputs to the skill-biased wage w_{m,k} and the Ā inversion.
2022 5yr PUMS uses 2020 PUMAs (matches the ACS aggregates and crosswalk).
Saved zipped to data/paper1_metros/pums/raw/.
"""
import os, subprocess
ROOT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
RAW  = os.path.join(ROOT, "data", "paper1_metros", "pums", "raw")
os.makedirs(RAW, exist_ok=True)
BASE = "https://www2.census.gov/programs-surveys/acs/data/pums/2022/5-Year"
# metro states only (lowercase 2-letter)
STATES = ["ca","ny","nj","ma","nh","wa","dc","md","va"]

def grab(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  skip {os.path.basename(dest)} (exists)"); return
    print(f"  downloading {os.path.basename(dest)} ...", flush=True)
    r = subprocess.run(["curl","-sL","--retry","4","-o",dest,url])
    mb = (os.path.getsize(dest)/1e6) if os.path.exists(dest) else 0
    print(f"    {'ok' if r.returncode==0 and mb>0 else 'FAIL'} {mb:.0f} MB", flush=True)

for st in STATES:
    print(f"=== {st} ===", flush=True)
    grab(f"{BASE}/csv_p{st}.zip", os.path.join(RAW, f"csv_p{st}.zip"))
print("PUMS DOWNLOAD COMPLETE", flush=True)
