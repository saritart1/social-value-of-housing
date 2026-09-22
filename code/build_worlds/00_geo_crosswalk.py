#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    00_geo_crosswalk
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Builds the PUMA-to-metro crosswalk (409 PUMAs, six metros) from TIGER shapefiles.
#  Inputs:  the TIGER shapefiles (step 0 in data/README.md).
#  Output:  the crosswalk, inside the working folder the scripts share (see data/README.md).
# ==========================================================
"""Paper 1 (6-metro) Tier A: download TIGER shapefiles and build metro->PUMA crosswalk.

Vintage: 2020 PUMAs (TIGER 2022), to match ACS 2022 5-year (which uses 2020 PUMAs).
Target metros (CBSA GEOID):
  35620 New York-Newark-Jersey City, NY-NJ-PA
  31080 Los Angeles-Long Beach-Anaheim, CA
  41860 San Francisco-Oakland-Berkeley, CA      } Bay Area
  41940 San Jose-Sunnyvale-Santa Clara, CA      } Bay Area
  14460 Boston-Cambridge-Newton, MA-NH
  47900 Washington-Arlington-Alexandria, DC-VA-MD-WV
  42660 Seattle-Tacoma-Bellevue, WA
"""
import os, sys, zipfile, io, subprocess, tempfile
import geopandas as gpd
import pandas as pd

ROOT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
OUT = os.path.join(ROOT, "data", "paper1_metros")
SHP = os.path.join(OUT, "shapefiles")
XW  = os.path.join(OUT, "crosswalk")
for d in (SHP, XW):
    os.makedirs(d, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"}
STATES = {"06":"CA","09":"CT","11":"DC","24":"MD","25":"MA","33":"NH",
          "34":"NJ","36":"NY","42":"PA","51":"VA","53":"WA"}
TARGET_CBSA = {
    "35620":("New York-Newark-Jersey City, NY-NJ-PA","New York"),
    "31080":("Los Angeles-Long Beach-Anaheim, CA","Los Angeles"),
    "41860":("San Francisco-Oakland-Berkeley, CA","Bay Area"),
    "41940":("San Jose-Sunnyvale-Santa Clara, CA","Bay Area"),
    "14460":("Boston-Cambridge-Newton, MA-NH","Boston"),
    "47900":("Washington-Arlington-Alexandria, DC-VA-MD-WV","Washington DC"),
    "42660":("Seattle-Tacoma-Bellevue, WA","Seattle"),
}

def fetch_zip(url, dest_dir, tag):
    """Download a zipped shapefile via curl to dest_dir; skip if .shp already present."""
    marker = os.path.join(dest_dir, tag + ".shp")
    if os.path.exists(marker):
        print(f"  skip {tag} (exists)")
        return marker
    print(f"  downloading {tag} ...")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tmp = tf.name
    subprocess.run(["curl", "-sL", "--retry", "3", "-A", UA["User-Agent"],
                    "-o", tmp, url], check=True)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(dest_dir)
    os.remove(tmp)
    return marker

print("=== CBSA shapefile ===")
cbsa_shp = fetch_zip("https://www2.census.gov/geo/tiger/TIGER2019/CBSA/tl_2019_us_cbsa.zip",
                     SHP, "tl_2019_us_cbsa")
cbsa = gpd.read_file(cbsa_shp)[["GEOID","NAME","geometry"]]
cbsa = cbsa[cbsa["GEOID"].isin(TARGET_CBSA)].to_crs(2163)  # equal-area for centroid test
print("  target CBSAs found:", sorted(cbsa["GEOID"].tolist()))

print("=== state PUMA shapefiles (2020 vintage) ===")
puma_frames = []
for fips, abbr in STATES.items():
    tag = f"tl_2022_{fips}_puma20"
    shp = fetch_zip(f"https://www2.census.gov/geo/tiger/TIGER2022/PUMA/{tag}.zip", SHP, tag)
    g = gpd.read_file(shp)[["STATEFP20","PUMACE20","NAMELSAD20","geometry"]]
    g = g.rename(columns={"NAMELSAD20":"NAMELSAD10"})  # keep downstream name stable
    g["state"] = fips; g["puma"] = g["PUMACE20"]
    puma_frames.append(g)
pumas = gpd.GeoDataFrame(pd.concat(puma_frames, ignore_index=True), crs=puma_frames[0].crs).to_crs(2163)
print(f"  total PUMAs across {len(STATES)} states: {len(pumas)}")

print("=== spatial join: PUMA centroid within target CBSA ===")
pumas["geometry_pt"] = pumas.geometry.representative_point()
pts = pumas.set_geometry("geometry_pt")[["state","puma","NAMELSAD10","geometry_pt"]]
joined = gpd.sjoin(pts, cbsa, how="inner", predicate="within")
joined["cbsa_name"] = joined["GEOID"].map(lambda g: TARGET_CBSA[g][0])
joined["metro"]     = joined["GEOID"].map(lambda g: TARGET_CBSA[g][1])
xwalk = (joined[["state","puma","NAMELSAD10","GEOID","cbsa_name","metro"]]
         .rename(columns={"GEOID":"cbsa","NAMELSAD10":"puma_name"})
         .sort_values(["metro","state","puma"]).reset_index(drop=True))

xwalk_path = os.path.join(XW, "puma_to_metro_crosswalk.csv")
xwalk.to_csv(xwalk_path, index=False)
print(f"\nWrote {xwalk_path}: {len(xwalk)} PUMAs in the 6 metros")
print(xwalk.groupby("metro")["puma"].count().to_string())
print("\nstates with metro PUMAs:", sorted(xwalk["state"].unique()))
