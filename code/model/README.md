# The model

Everything runs in base MATLAB (tested on R2024b). Add this folder to the path and run `main`; the loader finds the worlds in the repository's `data/worlds/` automatically. Outputs are written to `xl_metros/` next to the code; the versions we used are in `results/` at the repository root.

## Run order

MATLAB function names cannot start with a digit, so the model files are not numbered; the ideal order lives in `main.m`, whose numbered sections run every exercise: (1) core exports, (2) the eta check, (3) the rent fit, (4) one parameter at a time, (5) the grid, (6) uniqueness, (7) welfare weights, (8) the residual vintages, (9) the scale checks. Any section runs on its own once the worlds are in place.

## Files

**Core**

| File | Role |
|---|---|
| `pp_engine.m` | the model itself: solves the equilibrium, computes the wedge and its decomposition |
| `pp_realworld.m` | reads a world folder into the struct the engine expects |
| `load_metro.m` | loads a world and calibrates the housing-unit scale `q` under the caller's specification |
| `metro_cfg.m` | configuration presets; `'v15'` is the memo's core, `'v15sigma'` adds the composition channel |
| `saiz_epsS.m` | metro supply elasticities (Saiz 2010), used by the sensitivity runs |

**Exercises in the memo**

| File | Produces |
|---|---|
| `export_metro.m` | rankings, summaries and the channel decomposition per metro (Table 3, Figure 4) |
| `pilot_edu.m` | the rent-fit comparison for any world (Figure 3) |
| `eta_check.m` | the untargeted rent-elasticity check (Figure 2) |
| `sensitivity_v15.m` | one parameter at a time over its published range (Figure 5) |
| `omega_theta_grid.m` | the joint (omega, theta) grid with full re-calibration per cell (Figures 6-7) |
| `uniqueness_check.m` | the contraction margin and the multi-start check |
| `weights_test.m` | the welfare-weight re-ranking (Table 5) |
| `export_kappa.m` | exports the residuals for the vintage comparison (Table 4) |
| `zoning_lab.m` | the uniform stock expansions (the scale check in the limitations) |
| `uneven_lab.m` | the placement experiment: the same units in the best, average and worst locations |

## The extensions

The composition channel is a configuration, not a separate script: `export_metro('<slug>_abil6','v15sigma')`. The children's-outcomes channel switches on through the engine configuration:

```matlab
W = load_metro('Boston_abil6','v15');
c = metro_cfg(W.K,'v15');
c.mobility = true; c.mob_mode = 'chetty_v11';
c.mob_exposure = 0.04; c.mob_unpriced = 0.70;
r = pp_engine(W, c);
```

The welfare weights are `weights_test`; the permission value is not reported in the memo (see its Part V for why).

## The worlds

Each world folder in `data/worlds/` corresponds to a claim in the memo: `<metro>_abil6` is the core (six earnings-ability types); `<metro>_abil6norace` and `<metro>_edu3` and `<metro>_abil10` back the type-specification robustness in the limitations; `<metro>` (ten income deciles) and `<metro>_2016` back the residual-vintage check. The file format is documented in `data/README.md`.
