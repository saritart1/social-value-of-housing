%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    sensitivity_v15
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Moves one parameter at a time across its published range and re-solves the model.
%  Inputs:  slug; ndraws (0 runs only the one-at-a-time block).
%  Output:  xl_metros/sensitivity_v15_<slug>.csv (Figure 5).
%  Objects: ranges: alpha [0.25,0.35], theta [2,5], omega [0.08,0.16],
%            delta_c [0.02,0.10], lambda scale, kappa [0.007,0.014].
%% =========================================================

function sensitivity_v15(slug, ndraws)
% SENSITIVITY_V14  Paul's confidence table on the v14 CANDIDATE CORE
% (2026-08-03: v12 structure with sigma = 0 and the mobility channel off;
% = export_variant 'clean'): one-at-a-time parameter ranges + Monte Carlo
% confidence intervals for the headline objects.
%
%   sensitivity_v14('Seattle', 200)
%
% Same design as sensitivity_v14, with base cfg = metro_cfg(K,'v15') and the
% parameter list PRUNED to the channels alive in v14: sigma and the mobility
% rows (mob_pv1pct, mob_unpriced, mob_exposure) are REMOVED because those
% channels are priced at zero in v14.
%
% Writes xl_metros/sensitivity_v15_<slug>.csv (one-at-a-time)
%    and xl_metros/mc_ci_v15_<slug>.csv (Monte Carlo summary + stability).
if nargin < 1 || isempty(slug),   slug = 'Seattle'; end
if nargin < 2 || isempty(ndraws), ndraws = 200;     end
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');
if ~exist(out,'dir'), mkdir(out); end

W0 = load_metro(slug, 'v15');
K  = W0.K;
base = metro_cfg(K, 'v15'); base.decompose = false;
base.dereg_epsS = saiz_epsS(slug);    % metro-specific Saiz (2010) elasticity

% parameter ranges (documented in reference_ge_housing_borrowed_params +
% CLAUDE.md parameter table; mc_scale = user cost 4-7% around 5%).
% v15: sigma + all mob_* rows removed (channels off); VOT replaced by
% kappa (iceberg commuting), range spanning the four published estimates.
P = { ...
 'alpha',        0.25, 0.35;    % housing share (Diamond 0.30)
 'theta',        2.0,  5.0;     % Frechet sorting (Bryan-Morten 3)
 'lambda_scale', 0.67, 1.33;    % agglomeration 0.02-0.08 around 0.03-0.06
 'omega',        0.08, 0.16;    % density amenity BRACKET (v10, 2026-07-20)
 'dc',           0.02, 0.10;    % traffic congestion
 'kappa',        0.007, 0.014;  % iceberg commuting: ARSW 0.010,
                                % Tsivanidis 0.011-0.012, Zarate 0.009
 'mc_scale',     0.80, 1.40;    % user cost 4%-7% (construction cost level)
 'dereg_epsS',   0.50, 2.00 };  % unregulated supply elasticity

% ---- one-at-a-time ----
rows = {};
o = run1(base, W0);
rows(end+1,:) = {"baseline", NaN, o{:}};
for ip = 1:size(P,1)
    for v = [P{ip,2}, P{ip,3}]
        [c, Wv] = applyp(base, W0, P{ip,1}, v);
        o = run1(c, Wv);
        rows(end+1,:) = {string(P{ip,1}), v, o{:}};
    end
    fprintf('  %-13s done\n', P{ip,1});
end
T = cell2table(rows, 'VariableNames', {'param','value','max_wedge_usd', ...
    'max_wedge_where','eta_med','dereg_net_per_hh','converged'});
writetable(T, fullfile(out, ['sensitivity_v15_' slug '.csv']));

% ---- Monte Carlo CI (joint uniform draws) ----
mw = zeros(ndraws,1); et = zeros(ndraws,1); ng = zeros(ndraws,1);
locs = strings(ndraws,1); cv = zeros(ndraws,1);
for d = 1:ndraws
    rng(1000+d);
    c = base; Wv = W0;
    for ip = 1:size(P,1)
        v = P{ip,2} + rand*(P{ip,3}-P{ip,2});
        [c, Wv] = applyp(c, Wv, P{ip,1}, v);
    end
    o = run1(c, Wv);
    mw(d) = o{1}; locs(d) = o{2}; et(d) = o{3}; ng(d) = o{4}; cv(d) = o{5};
    if mod(d,25)==0, fprintf('  MC %d/%d\n', d, ndraws); end
end
[ul,~,ic] = unique(locs); cnt = accumarray(ic,1);
[mx, im] = max(cnt);
q = @(x,p) round(quantile(x,p), 3);
S = table( ...
    ["max_wedge_usd"; "eta_med"; "dereg_net_per_hh"], ...
    [q(mw,.05); q(et,.05); q(ng,.05)], ...
    [q(mw,.50); q(et,.50); q(ng,.50)], ...
    [q(mw,.95); q(et,.95); q(ng,.95)], ...
    'VariableNames', {'object','p5','p50','p95'});
writetable(S, fullfile(out, ['mc_ci_v15_' slug '.csv']));
fid = fopen(fullfile(out, ['mc_ci_v15_' slug '_location.csv']), 'w');
fprintf(fid, 'modal_top_wedge_location,share_of_draws,n_draws,converged_share\n');
fprintf(fid, '"%s",%.3f,%d,%.3f\n', ul(im), mx/ndraws, ndraws, mean(cv));
fclose(fid);
fprintf('[%s v14] MC (%d draws): max wedge [%d, %d, %d]$, eta [%.3f, %.3f, %.3f], net/hh [%d, %d, %d]$\n', ...
    slug, ndraws, round(quantile(mw,.05)), round(median(mw)), round(quantile(mw,.95)), ...
    quantile(et,.05), median(et), quantile(et,.95), ...
    round(quantile(ng,.05)), round(median(ng)), round(quantile(ng,.95)));
fprintf('        top-wedge location = "%s" in %.0f%% of draws\n', ul(im), 100*mx/ndraws);

% ---- nested helpers ----
    function [c, Wv] = applyp(c, Wv, name, v)
        switch name
            case 'lambda_scale', c.lambda = linspace(0.03, 0.06, K) * v;
            case 'mc_scale',     Wv.mc = Wv.mc * v;
            otherwise,           c.(name) = v;
        end
    end
    function o = run1(c, Wv)
        r = pp_engine(Wv, c);
        o = {round(r.max_wedge), string(Wv.names(r.max_wedge_loc)), ...
             round(r.eta_med,3), round(r.cf.net/sum(Wv.households)), ...
             double(r.converged && r.cf.converged)};
    end
end
