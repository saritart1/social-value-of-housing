# Data

All sources are public. The calibrated worlds in `worlds/` are included in this package, so the raw downloads below are needed only to rebuild them from scratch with `code/build_worlds/`.

## Included: the calibrated worlds

One folder per metro and specification (for example `Boston_abil6` is Boston with six earnings-ability types, the memo's core). Each folder contains:

| File | Content |
|---|---|
| `locations.csv` | PUMA ids, names, land area, housing stock, ACS rents, density, mean income, Opportunity Atlas place effect |
| `abar.csv` | wages by workplace PUMA and type (PUMS, tilted to LODES payroll) |
| `pitarget.csv` | population by residence PUMA and type (the sorting target) |
| `commute.csv` | baseline commuting flows (LODES) |
| `traveltime.csv` | free-flow travel time matrix, minutes (OpenStreetMap routing) |
| `masses.csv` | total mass per type |
| `kids_hh.csv` | children per household by PUMA (ACS B09001), used only by the mobility extension |
| `own.csv` | ownership shares (ACS), used only by incidence extensions |
| `meta.json` | build metadata: vintages, type definition, whether race is included |

The core of the analysis is `<metro>_abil6` (six earnings-ability types); `<metro>_abil6_2016` is its 2012--2016 vintage, used for the residual-vintage check (memo Table 4). The other folders back the type-specification robustness in the memo's limitations and are not part of the core: `<metro>_edu3` (education alone), `<metro>_abil10` (ten ability groups), and `Boston_abil6norace` (ability without race, run for Boston).

## Raw sources (to rebuild the worlds)

The downloads and builds are scripted. The scripts share a working folder, `data/paper1_metros/`, which they create inside the repository; the finished worlds are then copied to `data/worlds/`, which is what the model reads. Run, in this order, from `code/build_worlds/`:

The numeric prefixes are the run order.

- `00_geo_crosswalk.py` builds the PUMA-to-metro crosswalk (409 PUMAs) from TIGER shapefiles.
- `01_acs_pull.py` pulls the ACS aggregates from the Census API (needs the API key).
- `02_pums_download.py` downloads the PUMS person files for the nine metro states (about 650 MB).
- `03_lodes_download.py` downloads the LODES origin-destination files, including the neighbor states needed for cross-border commutes (about 350 MB).
- `04_travel_times.py` computes the drive-time matrices from OpenStreetMap; `05_validate_traveltimes.py` checks them.
- `06_build_world_abil.py` assembles the core `_abil6` worlds.
- Steps 07 to 09 are needed only for the residual-vintage check (memo Table 4): `07_build_world_deciles.py` (the base of the chain), `08_build_world_deciles_2016.py` and its Seattle variant (the 2016 worlds, which store the geography maps), and `09_build_world_abil_2016.py` (the `_abil6_2016` worlds).

`DATA_MANIFEST.md` in this folder documents every downloaded file, its size, its vintage and what it feeds, together with verified coverage counts per metro. The table below summarizes the sources.

The agencies revise these files over time, so if a fresh download produces slightly different numbers, compare your download date with ours below. The calibrated worlds in this package were built from our downloads, so every result that starts from the worlds reproduces regardless of later revisions.

| Source | What we take | Where | Downloaded |
|---|---|---|---|
| ACS 5-year 2018--2022 | housing stock (B25001), median gross rent (B25064), household income, population by PUMA | Census API, `api.census.gov` | 2026-06-29 (additional tables through 2026-08-31) |
| ACS B09001 (children per household) | the mobility extension only | Census API | 2026-07-28 |
| ACS PUMS 2022 | person records: wages, workplace PUMA (POWPUMA), education, age, sex, field of degree, birthplace, citizenship, arrival year, English, race | `census.gov/programs-surveys/acs/microdata` | 2026-06-29 |
| ACS PUMS 2012--2016 | same, for the residual-vintage check | same | 2026-07-20 |
| LODES 8, 2022 | origin-destination job flows and payroll by census block, aggregated to PUMAs | `lehd.ces.census.gov/data/lodes/` | 2026-06-29 |
| LODES 8, 2016 | same, for the residual-vintage check | same | 2026-07-20 |
| OpenStreetMap | drive-time matrix between PUMA centroids, free flow | OSRM on a state extract; see the build script header | 2026-06-29 |
| Opportunity Atlas | tract-level place effects for children born 1978--83, low-income parents, aggregated to PUMAs | `opportunityinsights.org/data` | 2026-06-29 |
| TIGER/Line 2022 | 2020 PUMA shapefiles (for the maps only) and cartographic state boundaries (to clip water) | `census.gov/geographies/mapping-files` | 2026-06-29 (state boundaries 2026-08-03) |

Practical notes from our own pulls:

- A Census API key is required for the ACS pulls; request one at `api.census.gov/data/key_signup.html` and place it in a file named `.census_api_key` at the repository root.
- TIGER PUMA shapefiles include legal water; the map script clips them against the cartographic state boundaries (`cb_2022_us_state_500k`). There is no cartographic PUMA product, so do not look for one.
- LODES is at the census-block level; the build script does the block-to-PUMA aggregation.
- The FHFA land and structure cost data (used only by the permission-value extension, which the memo does not report) are at `fhfa.gov`, land price release 2024.
