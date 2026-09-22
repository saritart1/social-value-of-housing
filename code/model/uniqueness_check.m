%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    uniqueness_check
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Verifies the equilibrium is unique: five starting points and the contraction margin, per metro.
%  Inputs:  slugs, a cell of world names; ver.
%  Output:  xl_metros/uniqueness_check.csv.
%% =========================================================

function uniqueness_check(slugs, ver)
% UNIQUENESS_CHECK  Is the closed-city equilibrium unique and stable at the
% calibrated (v10) parameters?
%
%   uniqueness_check()               % all six metros
%   uniqueness_check({'Seattle'})   % subset
%
% Runs the engine's check_unique diagnostic (pp_engine block 1c): multi-start
% re-solves of the baseline and of a +1% supply shock (global check: all
% starts must recover the same equilibrium) plus the spectral radius of the
% sorting-map Jacobian at the equilibrium (local check: rho < 1 = contraction,
% 1 - rho = the margin). Motivated by the v10 omega recentering (stronger
% amenity feedback = the classic multiplicity risk in agglomeration models).
% Writes xl_metros/uniqueness_check.csv; the report sentence is the point.
if nargin < 2, ver = 'v12'; end       % 2026-09-01: explicit; ability worlds use 'v15'
if nargin < 1 || isempty(slugs)
    slugs = {'Seattle','Boston','Washington_DC','Bay_Area','Los_Angeles','New_York'};
end
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');

rows = table();
for i = 1:numel(slugs)
    slug = slugs{i};
    [W, q] = load_metro(slug, ver);
    cfg = metro_cfg(W.K, ver);
    cfg.baseline_only = true;
    cfg.check_unique  = true;
    fprintf('[%s] N=%d (NK=%d) ...\n', slug, W.N, W.N*W.K);
    res = pp_engine(W, cfg);
    uq  = res.cfg.unique;
    rows = [rows; table(string(slug), W.N, ...
        max(uq.dev_base), max(uq.dev_shock), uq.rho, 1-uq.rho, ...
        double(all([uq.conv_base uq.conv_shock uq.conv_shock_ref])), ...
        round(q,2), ...
        'VariableNames', {'metro','n_pumas','max_dev_baseline','max_dev_shock', ...
        'rho_jacobian','contraction_margin','all_converged','q'})]; %#ok<AGROW>
end
writetable(rows, fullfile(out, 'uniqueness_check.csv'));
disp(rows);
fprintf('wrote %s\n', fullfile(out, 'uniqueness_check.csv'));
end
