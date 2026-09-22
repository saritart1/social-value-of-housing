%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    uneven_lab
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Places the same stock increase in the highest-wedge, average and lowest-wedge locations and compares the welfare gains.
%  Inputs:  slug; ver; budget_pct, the stock increase (10 in the memo); topn, how many locations receive it (5).
%  Output:  xl_metros/uneven_<slug>.csv.
%% =========================================================

function uneven_lab(slug, ver, budget_pct, topn)
% UNEVEN_LAB  The uneven-reform demonstration for the beyond-the-marginal
% appendix: fix a budget of new units (budget_pct of the metro stock) and
% allocate it three ways -- uniformly, all in the TOPN highest-wedge PUMAs,
% all in the TOPN lowest-wedge PUMAs. Full re-solve each time, xi/Abar fixed.
% Writes xl_metros/uneven_<slug>.csv.
if nargin < 2, ver = 'v15'; end
if nargin < 3, budget_pct = 10; end
if nargin < 4, topn = 5; end
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');

W = load_metro(slug, ver);
cfg0 = metro_cfg(W.K, ver); cfg0.decompose = false; cfg0.check_unique = false;
base = pp_engine(W, cfg0);
[~, ow] = sort(base.wedge, 'descend');
B = budget_pct/100 * sum(W.H);

arms = struct('name', {}, 'dH', {});
arms(1).name = 'uniform';      arms(1).dH = B * W.H / sum(W.H);
idx = ow(1:topn);              dH = zeros(W.N,1); dH(idx) = B * W.H(idx)/sum(W.H(idx));
arms(2).name = 'top_wedge';    arms(2).dH = dH;
idx = ow(end-topn+1:end);      dH = zeros(W.N,1); dH(idx) = B * W.H(idx)/sum(W.H(idx));
arms(3).name = 'bottom_wedge'; arms(3).dH = dH;

rows = {};
for a = 1:numel(arms)
    cfg = cfg0; cfg.expand_grid = 1.0; cfg.expand_target = W.H + arms(a).dH;
    cfg.shock_locs = 1;   % dW is aggregate; skip the full marginal map
    r = pp_engine(W, cfg);
    rows(end+1,:) = {arms(a).name, budget_pct, round(r.expand.dW(1)/1e6), ...
        round(r.expand.naive_price(1)/1e6), round(r.expand.dr_med_pct(1),2), ...
        double(r.expand.conv(1))}; %#ok<AGROW>
    fprintf('%s | %-12s dW $%dM/yr | naive $%dM | med rent %+.2f%% | conv %d\n', ...
        slug, arms(a).name, rows{end,3}, rows{end,4}, rows{end,5}, rows{end,6});
end
T = cell2table(rows, 'VariableNames', ...
    {'arm','budget_pct','dW_musd','naive_musd','dr_med_pct','converged'});
writetable(T, fullfile(out, sprintf('uneven_%s.csv', slug)));
end
