# Data manifest

Every raw file the memo's pipeline uses, with vintages and download dates. Nothing else from the wider research project is listed here. The calibrated worlds in `worlds/` were built from exactly these files.

**Geography (locked):** 2020 PUMAs. ACS 2022 5-year, PUMS 2022 5-year and LODES8 all use 2020 PUMAs; TIGER 2022 `puma20` shapefiles match.

**Metros (6):** New York, Los Angeles, Bay Area (SF-Oakland MSA 41860 + San Jose MSA 41940), Boston, Washington DC, Seattle.

## Coverage (ACS 2022 5-year, verified)

| Metro | PUMAs | Population | Housing units |
|---|---|---|---|
| New York | 147 | 19,887,346 | 7,955,380 |
| Los Angeles | 91 | 13,111,917 | 4,730,219 |
| Bay Area | 54 | 6,609,073 | 2,539,290 |
| Washington DC | 47 | 6,338,002 | 2,496,452 |
| Boston | 38 | 4,984,228 | 2,059,776 |
| Seattle | 32 | 4,001,701 | 1,657,075 |
| **Total** | **409** | | |

## Files

### Geography and crosswalk (downloaded 2026-06-29)
- `shapefiles/tl_2022_<ST>_puma20.*` — 2020 PUMA polygons, 11 states (CA CT DC MD MA NH NJ NY PA VA WA).
- `shapefiles/tl_2019_us_cbsa.*` — CBSA polygons, used only to assign PUMAs to metros.
- `shapefiles/cb_2022_us_state_500k.*` — cartographic state boundaries, used only to clip water from the maps (downloaded 2026-08-03).
- `crosswalk/puma_to_metro_crosswalk.csv` — 409 rows, the master subset key, built by centroid-in-CBSA spatial join.

### ACS aggregates (downloaded 2026-06-29; additional tables through 2026-08-31)
- `acs/acs5_2022_puma_6metros.csv` — the 409 metro PUMAs. Tables used by the build: B25001 total units (the stock `H_j`), B25064 median gross rent (`r_j`), B19001 household income by bracket, B01003 population, B19013 median household income.
- `kids/` — B09001 children per household by PUMA (downloaded 2026-07-28); feeds only the children's-outcomes extension.

### ACS PUMS person microdata
- `pums/raw/csv_p{ca,dc,ma,md,nh,nj,ny,va,wa}.zip` — 2022 5-year person files, nine metro states, about 650 MB (downloaded 2026-06-29). Feed the wages, the earnings-ability index (education, age, sex, field of degree, birthplace and arrival cohort, English, race) and the sorting targets.
- `pums/raw/csv_p*_2016.zip` — 2012--2016 5-year person files, same states (downloaded 2026-07-20). Feed only the residual-vintage check (memo Table 4). This vintage is on 2010 PUMA geography; see the memo's Table 4 note for how the build handles it.

### LODES8 commuting (48 files, about 350 MB)
- `lodes/raw/*_{od_main,od_aux,wac}_JT00_2022.csv.gz` plus the crosswalks, twelve states including neighbors (CT PA WV) for cross-border commutes (downloaded 2026-06-29). Feed the commuting shares and workplace employment.
- The 2016 counterparts (downloaded 2026-07-20) feed only the residual-vintage check.
- LODES is at the census-block level; blocks are assigned to 2020 PUMAs via the shapefiles in a processing step, because the LODES crosswalk carries no PUMA field.

### Travel times (computed 2026-06-29)
- `travel_times/<metro>.csv` — free-flow drive-time matrices between PUMA centroids, computed with OSRM on OpenStreetMap state extracts by `code/build_worlds/20260629_p1_travel_times.py`.

### Opportunity Atlas (downloaded 2026-06-29)
- `opportunity_atlas/tract_outcomes_simple.csv` (33 MB) — children's adult outcomes by tract, key variable `kfr_pooled_pooled_p25` (children born 1978--83, parents at the 25th percentile), aggregated to PUMAs. Feeds only the children's-outcomes extension.
- `us_tract_2010_2020_crosswalk.csv` — for the tract-vintage alignment.

### FHFA land and structure prices (downloaded 2026-06-29)
- `land_prices/land-prices_2024.xlsx` (Davis-Larson-Oliner-Shui via FHFA) — feeds the construction-cost column `mc_yr` in the worlds. No exhibit in the memo reports a number built from it; the memo's Part V explains why the permission value is not reported.
