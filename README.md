# Replication package: The Social Value of New Housing by Location

This package reproduces every table, figure and number in the memo *The Social Value of New Housing by Location* (Restrepo Tamayo, 2026), prepared for Coefficient Giving. It covers six US metropolitan areas (New York, the San Francisco Bay Area, Los Angeles, Boston, Washington DC and Seattle) at the level of 2020 PUMAs, 409 locations in total.

## Structure

```
replication/
  README.md            this file
  code/
    build_worlds/      Python scripts that build the calibrated inputs from raw public data
    model/             the MATLAB model: engine, calibration, and every exercise in the memo
    figures/           Python scripts that produce the figures from the results CSVs
  data/
    README.md          data sources and download instructions for the raw files
    worlds/            the calibrated model inputs ("worlds"), one folder per metro and specification
  results/             the output CSVs behind every exhibit in the memo
```

## Requirements

- MATLAB R2024b (no toolboxes beyond base MATLAB).
- Python 3.10+ with `pandas`, `numpy`, `matplotlib`; `geopandas` only for the maps.
- A US Census API key, only if you rebuild the worlds from raw data.

## Two ways to replicate

**From the calibrated worlds (recommended; no raw data needed).** The `data/worlds/` folders contain everything the model needs: locations, populations by type, wages by workplace, commuting flows, travel times, and metadata. Each world is a set of small CSVs, documented in `code/model/README.md`. From MATLAB, with `code/model` on the path:

```matlab
main    % runs every exercise in the ideal order, one numbered section per exhibit
```

`code/model/main.m` is the master script; its numbered sections can also be run one at a time, and `code/model/README.md` documents what each function produces.

The specification string `'v15'` is the memo's core: iceberg commuting, composition and mobility channels at zero. Every run writes CSVs; the ones we used are already in `results/`, so the figures can be reproduced without running MATLAB at all.

**From raw data.** The numbered scripts in `code/build_worlds/` rebuild the worlds from ACS, PUMS and LODES files; `data/README.md` lists every source and how to download it. Expect several GB of raw data and a few hours of pulls. The travel-time matrices come from an OpenStreetMap routing step documented in the script header.

## Map from the memo's exhibits to this package

| Exhibit | Produced by | Output used |
|---|---|---|
| Figure 1 (model loop) | drawn in the memo's TeX | -- |
| Table 1 (borrowed parameters) | hand-collected from the cited papers | -- |
| Table 2 (data sources) | see `data/README.md` | -- |
| Figure 2 (rent response, eta) | `code/figures/01_headline_figures.py` | `results/*_abil6_eta.csv` |
| Figure 3 (rent fit) | `code/figures/01_headline_figures.py` | `results/pilot_*_abil6.csv` |
| Figure 4 (wedge maps) | `code/figures/02_wedge_maps.py` | `results/*_abil6_rankings.csv` + TIGER shapefiles |
| Table 3 (largest wedges) | `export_metro` | `results/*_abil6_summary.csv` |
| Section 3.2 numbers | `sensitivity_v15`, `omega_theta_grid`, `uniqueness_check`, `export_kappa` | `results/sensitivity_v15_*.csv`, `results/grid_*.csv`, `results/uniqueness_check.csv`, `results/kappa_*.csv` |
| Figure 5 (tornado) | `code/figures/03_tornado.py` | `results/sensitivity_v15_*_abil6.csv` |
| Figures 6-7 (grids) | `code/figures/04_grids.py` | `results/grid_*_abil6.csv` |
| Table 5 (welfare weights) | `weights_test` | `results/weights_*_abil6.csv` |
| Table 4 (residual vintages) | `export_kappa` on the abil6 and abil6_2016 worlds, `'v15'` | `results/kappa_*_abil6*.csv` |
| Limitations: scale checks | `zoning_lab`, `uneven_lab` | `results/zoning_lab_*_abil6.csv`, `results/uneven_Boston_abil6.csv` |
| Extensions: composition, children | `export_metro` with `'v15sigma'`; `pp_engine` with the mobility channel on | run commands in `code/model/README.md` |

Note on the figure scripts: each one sets a `PROJECT` path constant at the top; point it at this repository's root before running.

## Notes and caveats

- The model's core is the six-ability-type specification (`worlds/*_abil6`), and `worlds/*_abil6_2016` is its 2012--2016 vintage for the residual check. Every other world backs one clause of the type-specification robustness in limitation 4 ("education alone, with and without race, six or ten groups"): `*_edu3` is education alone, `*_abil10` is ten ability groups, and `Boston_abil6norace` is the without-race variant, which we ran for Boston. None of these is part of the core analysis.
- The residual-vintage check (Table 4) runs on the core specification: it compares `worlds/<metro>_abil6` with `worlds/<metro>_abil6_2016`, both inverted under `'v15'`. The 2016 vintage is built by `code/build_worlds/09_build_world_abil_2016.py`; its geography notes are in the memo's Table 4 note; the build chain is steps 07-09 of `code/build_worlds/`.
- The interactive map is built by `presentation/interactive/` in the research repository and is not required for any number in the memo.

## Contact

Sara Restrepo Tamayo, UC San Diego.
