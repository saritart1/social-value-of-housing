%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    omega_theta_grid
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Re-calibrates and re-solves the model at every point of an (omega, theta) grid.
%  Inputs:  slug; nw, nt, the grid dimensions (default 5 x 5; New York ran 3 x 3).
%  Output:  xl_metros/grid_<slug>.csv (Figures 6-7).
%  Objects: omega in linspace(0.08, 0.16, nw); theta in linspace(2, 5, nt); full re-inversion per cell.
%% =========================================================

function omega_theta_grid(slug, nw, nt)
% OMEGA_THETA_GRID  Replaces the Monte Carlo (Paul, 2026-09-01: a grid is
% preferable to random draws because every cell is a STATED assumption you can
% quote, whereas a random draw's percentile is a percentile of a distribution
% nobody estimated).
%
% Grids the only two parameters that move the answer -- omega (density amenity)
% and theta (residence sorting) -- over their published ranges, holding the rest
% at central values. Each cell is a full re-inversion and re-solve.
if nargin < 2, nw = 5; end
if nargin < 3, nt = 5; end
here = fileparts(mfilename('fullpath'));
out  = fullfile(here,'xl_metros'); if ~exist(out,'dir'), mkdir(out); end
W0 = load_metro(slug, 'v15');
base = metro_cfg(W0.K, 'v15'); base.decompose = false; base.check_unique = false;
OM = linspace(0.08, 0.16, nw);      % Rollet 0.11, ARSW 0.16, our old 0.08
TH = linspace(2.0,  5.0,  nt);      % around Bryan-Morten 3
rows = {};
fprintf('[%s] omega x theta grid, %dx%d = %d cells\n', slug, nw, nt, nw*nt);
for a = 1:nw
    for b = 1:nt
        c = base; c.omega = OM(a); c.theta = TH(b);
        try
            r = pp_engine(W0, c);
            rows(end+1,:) = {OM(a), TH(b), round(r.max_wedge), ...
                string(W0.names(r.max_wedge_loc)), round(r.eta_med,3), ...
                round(corr(r.private, W0.rent_data),3), double(r.converged)}; %#ok<AGROW>
        catch e
            rows(end+1,:) = {OM(a), TH(b), NaN, "FAILED", NaN, NaN, 0}; %#ok<AGROW>
            fprintf('  cell (%.2f, %.2f) failed: %s\n', OM(a), TH(b), e.message);
        end
    end
    fprintf('  omega = %.2f done\n', OM(a));
end
T = cell2table(rows, 'VariableNames', ...
    {'omega','theta','max_wedge_usd','max_wedge_where','eta_med','rent_fit','converged'});
writetable(T, fullfile(out, sprintf('grid_%s.csv', slug)));
w = [T.max_wedge_usd]; loc = string(T.max_wedge_where);
[u,~,ic] = unique(loc); cnt = accumarray(ic,1); [mx,im] = max(cnt);
fprintf('  wedge %d to %d (baseline %d) | top location "%s" in %d/%d cells\n', ...
    min(w), max(w), round(median(w)), u(im), mx, numel(w));
fprintf('  -> xl_metros/grid_%s.csv\n', slug);
end
