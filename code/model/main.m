%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    main
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Runs every MATLAB exercise in the memo, in the ideal order.
%  Inputs:   the calibrated worlds in data/worlds/ (nothing else).
%  Output:   every CSV in results/, one section per exhibit.
%  Note:     MATLAB function names cannot start with a digit, so the run
%            order lives here rather than in numbered file names. Each
%            section below can also be run on its own.
%% =========================================================

M = {'Boston_abil6','Seattle_abil6','Washington_DC_abil6', ...
     'Bay_Area_abil6','Los_Angeles_abil6','New_York_abil6'};
VER = 'v15';                       % the memo's core specification

%% =========================================================
%  1. Core results: rankings, summaries, decomposition (Table 3, Figure 4)
%% =========================================================
for i = 1:numel(M), export_metro(M{i}, VER); end

%% =========================================================
%  2. Validation: the untargeted rent elasticity (Figure 2)
%% =========================================================
eta_check(M, VER);

%% =========================================================
%  3. Validation: the rent fit (Figure 3)
%% =========================================================
for i = 1:numel(M), pilot_edu(M{i}, VER); end

%% =========================================================
%  4. Sensitivity: one parameter at a time (Figure 5)
%% =========================================================
for i = 1:numel(M), sensitivity_v15(M{i}, 0); end   % New York is costly; skip if needed

%% =========================================================
%  5. Sensitivity: the (omega, theta) grid (Figures 6-7)
%% =========================================================
for i = 1:numel(M)-1, omega_theta_grid(M{i}, 5, 5); end
omega_theta_grid('New_York_abil6', 3, 3);           % coarser: compute cost

%% =========================================================
%  6. Uniqueness of the equilibrium
%% =========================================================
uniqueness_check(M, VER);

%% =========================================================
%  7. Welfare weights (Table 5)
%% =========================================================
for i = 1:numel(M), weights_test(M{i}); end

%% =========================================================
%  8. The residual across data vintages (Table 4)
%% =========================================================
M16 = strcat(M, '_2016');
export_kappa([M, M16], VER);

%% =========================================================
%  9. Scale checks in the limitations: uniform and placed expansions
%% =========================================================
zoning_lab(M, [], VER);
uneven_lab('Boston_abil6', VER, 10, 5);
