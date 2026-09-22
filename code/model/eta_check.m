%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    eta_check
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   The untargeted validation: the model's rent response to a stock expansion, compared with Rollet (2025).
%  Inputs:  slugs, one or a cell of world names; ver.
%  Output:  xl_metros/<slug>_eta.csv, one rent response per PUMA (Figure 2).
%  Note:    the -0.42 benchmark is used nowhere in the calibration; that is what makes this a check.
%% =========================================================

function T = eta_check(slugs, ver)
% ETA_CHECK  Closed vs open city on the real metros: the Rollet eta
% over-identification check AND the wedge comparison, in one pass.
%
%   T = eta_check()                      % all six metros
%   T = eta_check({'New_York'})          % one metro
%
% For every location j: shock H_j by +1%, re-solve, read off
%   eta_j   = dlog r_j / dlog H_j   (Rollet causal benchmark: -0.42)
%   wedge_j = dW/dH_j - price_j     (under each closure)
% The closed city shuts the migration margin (rents must absorb the shock,
% incumbents keep the benefit); the open city lets in-migration bid rents
% back up (the marginal migrant is indifferent, value shows up in output).
%
% Writes xl_metros/eta_check.csv + closure_check.csv (summaries) and, per
% metro, <slug>_eta.csv + <slug>_closure.csv (per-PUMA closed vs open).
if nargin < 1 || isempty(slugs)
    slugs = {'Seattle','Boston','Washington_DC','Bay_Area','Los_Angeles','New_York'};
end
if nargin < 2, ver = 'v12'; end     % 2026-08-31: explicit; ability worlds use 'v14'
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');
if ~exist(out,'dir'), mkdir(out); end

ROLLET = -0.42;
rows = {}; wrows = {};
for i = 1:numel(slugs)
    slug = slugs{i};
    W = load_metro(slug, ver);
    K = W.K;
    base = metro_cfg(K, ver); base.decompose = false;   % eta only: skip decomposition

    % closed city
    rc = pp_engine(W, base);
    % open city (v8 closure; s0 schedule and outside income are the v8
    % illustrative defaults -- calibrate to ACS non-metro data later)
    bo = base; bo.open = true; bo.s0 = linspace(0.60, 0.40, K); bo.out_income_ratio = 0.75;
    ro = pp_engine(W, bo);

    hw = W.households / sum(W.households);         % population weights
    rows(end+1,:) = {string(slug), W.N, ...
        round(median(rc.eta),3), round(sum(hw.*rc.eta),3), ...
        round(median(ro.eta),3), round(sum(hw.*ro.eta),3), ...
        ROLLET, double(rc.converged && ro.converged)};

    Tp = table(W.gid, W.names, round(rc.eta,3), round(ro.eta,3), ...
        round(sum(rc.N0,2)), ...
        'VariableNames', {'gid','name','eta_closed','eta_open','households'});
    writetable(Tp, fullfile(out, [slug '_eta.csv']));

    % ---- wedge comparison under the two closures ----
    migr = ro.dWdH - rc.dWdH;                      % the migration effect on welfare
    Tw = table(W.gid, W.names, round(rc.private), ...
        round(rc.dWdH), round(rc.wedge), round(ro.dWdH), round(ro.wedge), ...
        round(migr), round(ro.dGDPdH), round(ro.dGDPdH_nat), ...
        round(sum(rc.N0,2)), ...
        'VariableNames', {'gid','name','price_usd', ...
        'welfare_closed','wedge_closed','welfare_open','wedge_open', ...
        'migration_usd','dGDPmetro_open','dGDPnat_open','households'});
    writetable(Tw, fullfile(out, [slug '_closure.csv']));
    [mwc, jc] = max(rc.wedge); [mwo, jo] = max(ro.wedge);
    wrows(end+1,:) = {string(slug), ...
        round(mwc), string(W.names(jc)), round(median(rc.wedge)), ...
        round(mwo), string(W.names(jo)), round(median(ro.wedge)), ...
        round(median(migr)), ...
        round(ro.dGDPdH(jc)), round(ro.dGDPdH_nat(jc)), ...
        round(100*sum(hw.*(ro.dGDPdH_nat./max(ro.dGDPdH,1))),0)};

    fprintf('[%s] eta closed %+0.3f open %+0.3f | max wedge closed %+d$ open %+d$ | med migration %+d$\n', ...
        slug, median(rc.eta), median(ro.eta), round(mwc), round(mwo), round(median(migr)));
end
T = cell2table(rows, 'VariableNames', {'metro','n_pumas', ...
    'eta_closed_med','eta_closed_wtd','eta_open_med','eta_open_wtd', ...
    'rollet_target','converged'});
writetable(T, fullfile(out, 'eta_check.csv'));
Tw2 = cell2table(wrows, 'VariableNames', {'metro', ...
    'max_wedge_closed','where_closed','med_wedge_closed', ...
    'max_wedge_open','where_open','med_wedge_open','med_migration_usd', ...
    'dGDPmetro_at_top','dGDPnat_at_top','natGDP_share_pct'});
writetable(Tw2, fullfile(out, 'closure_check.csv'));
end
