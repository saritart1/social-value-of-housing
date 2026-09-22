%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    zoning_lab
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Expands every location's stock together and re-solves, from 0.5% to 50% (the scale check in the limitations).
%  Inputs:  slugs; grid, the expansion percentages (default [0.5 1 2 5 10 20 30 50]); ver.
%  Output:  xl_metros/zoning_lab_<slug>.csv plus the ranking-stability files.
%% =========================================================

function zoning_lab(slugs, grid, ver)
% ZONING_LAB  How far does the marginal ("price is a good signal") logic carry
% when the zoning change is BIG? (Paul 7/14: first moment vs second-order.)
%
%   zoning_lab()                          % Seattle + New York, default ladder
%   zoning_lab({'Seattle'}, [.01 .10])   % custom
%
% For each expansion margin s (stock -> (1+s)H everywhere), the engine solves
% the full new equilibrium and reports (block 3b):
%   - true welfare gain dW(s) vs the naive first-moment prediction
%     (new units valued at today's rents): the ratio is the curvature;
%   - the MARGINAL social value, price, wedge and eta on top of each expanded
%     equilibrium at the max-wedge PUMA and at the max-rent core: how the
%     marginal objects themselves drift as the city is rebuilt.
% kappa / Abar / baseline untouched (policy counterfactual, no re-inversion).
% Writes xl_metros/zoning_lab_<slug>.csv (one row per s, incl. s = 0).
if nargin < 1 || isempty(slugs), slugs = {'Seattle','New_York'}; end
if nargin < 2 || isempty(grid),  grid  = [0.005 0.01 0.02 0.05 0.10 0.20 0.30 0.50]; end
if nargin < 3 || isempty(ver), ver = 'v12'; end   % 2026-08-31: ability worlds use 'v14'
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');

for i = 1:numel(slugs)
    slug = slugs{i};
    [W, ~] = load_metro(slug);
    % tracked locations: jtop = the current (v10) max-wedge PUMA (export CSV);
    % jcore = the max workplace-employment-density PUMA (the congestion core)
    gnum = str2double(string(W.gid));
    E = W.piw' * W.households; [~, jcore] = max(E ./ W.L);
    jtop = jcore;
    rf = fullfile(out, [slug '_rankings.csv']);
    if exist(rf, 'file')
        T = readtable(rf, 'VariableNamingRule','preserve');
        g = T.gid(T.wedge_rank == 1);
        hit = find(gnum == double(g(1)), 1);
        if ~isempty(hit), jtop = hit; end
    end
    cfg = metro_cfg(W.K, ver);
    cfg.decompose    = false;
    cfg.expand_grid  = grid;
    cfg.expand_track = [jtop jcore];
    % RANKING set: all locations for small metros; for big ones the baseline
    % top-20 wedge PUMAs + the bottom 3 + the two tracked (rank drift is about
    % whether the TOP of the ordering is stable; the tail anchors the test)
    if W.N <= 60
        rset = 1:W.N;
    elseif exist(rf, 'file')
        [~, ord] = sort(T.wedge_usd, 'descend');
        rset = [ord(1:20)' ord(end-2:end)'];
    else
        rset = [];
    end
    cfg.shock_locs = unique([rset jtop jcore]);
    fprintf('[%s] zoning lab, %d rungs, jtop=%d (%s) jcore=%d (%s)\n', ...
        slug, numel(grid), jtop, W.names(jtop), jcore, W.names(jcore));
    res = pp_engine(W, cfg);
    xg  = res.expand;

    % s = 0 row from the baseline marginal objects, then the ladder
    rows = table();
    rows = [rows; mkrow(0, 0, 0, 1, 0, ...
        res.dWdH(xg.jtop),  res.private(xg.jtop),  res.eta(xg.jtop), ...
        res.dWdH(xg.jcore), res.private(xg.jcore), res.eta(xg.jcore), 1)];
    for is = 1:numel(xg.s)
        rows = [rows; mkrow(100*xg.s(is), xg.dW(is)/1e9, xg.naive_price(is)/1e9, ...
            xg.dW(is)/xg.naive_price(is), xg.dr_med_pct(is), ...
            xg.marg_w_top(is),  xg.marg_p_top(is),  xg.eta_top(is), ...
            xg.marg_w_core(is), xg.marg_p_core(is), xg.eta_core(is), ...
            xg.conv(is))]; %#ok<AGROW>
    end
    fp = fullfile(out, ['zoning_lab_' slug '.csv']);
    writetable(rows, fp);
    fprintf('%s\n', fp);
    disp(rows(:, {'s_pct','dW_bn','naive_price_bn','ratio_dW_naive', ...
                  'dr_med_pct','marg_wedge_top','marg_wedge_core'}));
    fprintf('  tracked: jtop = %s | jcore = %s\n', W.names(xg.jtop), W.names(xg.jcore));

    % ---- RANK DRIFT: does the where-to-build ordering survive big reforms? --
    rl = find(~isnan(xg.wedge_mat(:,1)));           % the ranking set
    if numel(rl) >= 5
        w0 = res.wedge(rl);                         % s = 0 marginal wedge
        Wm = [w0, xg.wedge_mat(rl,:)];              % |rl| x (1+n_s)
        sp = [0, 100*grid];
        rk = table();
        for c = 1:size(Wm,2)
            [~,o1] = sort(w0,'descend'); [~,r1] = sort(o1);
            [~,o2] = sort(Wm(:,c),'descend'); [~,r2] = sort(o2);
            rho_s = corr(r1, r2, 'type','Spearman');
            [~, t1] = maxk(Wm(:,c), 3);
            rk = [rk; table(sp(c), rho_s, ...
                string(strjoin(extractBefore(W.names(rl(t1))+"--","--"), " | ")), ...
                std(Wm(:,c),'omitnan'), ...
                'VariableNames', {'s_pct','spearman_vs_s0','top3','sd_wedge_usd'})]; %#ok<AGROW>
        end
        writetable(rk, fullfile(out, ['zoning_lab_rank_' slug '.csv']));
        disp(rk);
        % long per-location matrix for figures/audit
        Tl = array2table([Wm xg.price_mat(rl,end)], 'VariableNames', ...
            [compose('wedge_s%g', sp) {'price_s50'}]);
        Tl = [table(W.gid(rl), W.names(rl), 'VariableNames', {'gid','name'}) Tl];
        writetable(Tl, fullfile(out, ['zoning_lab_rankmat_' slug '.csv']));
    end
end
end

function r = mkrow(s_pct, dW_bn, naive_bn, ratio, dr, wt, pt, et, wc, pc, ec, cv)
r = table(s_pct, round(dW_bn,3), round(naive_bn,3), round(ratio,3), round(dr,1), ...
    round(wt - pt), round(wt), round(pt), round(et,3), ...
    round(wc - pc), round(wc), round(pc), round(ec,3), cv, ...
    'VariableNames', {'s_pct','dW_bn','naive_price_bn','ratio_dW_naive', ...
    'dr_med_pct','marg_wedge_top','marg_dWdH_top','marg_price_top','eta_top', ...
    'marg_wedge_core','marg_dWdH_core','marg_price_core','eta_core','converged'});
end
