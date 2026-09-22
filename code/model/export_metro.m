%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    export_metro
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Runs one metro and writes the rankings, the summary and the channel decomposition.
%  Inputs:  slug; ver; do_decomp (false writes the analytic decomposition, the default).
%  Output:  xl_metros/<slug>_{rankings,summary,decomp_analytic}.csv (Table 3, Figure 4).
%% =========================================================

function res = export_metro(slug, ver, do_decomp)
% EXPORT_METRO  Run the current model on a REAL metro world and dump CSVs for
% the tracking workbook (one sheet per metro).
%
%   export_metro('Seattle')      % writes xl_metros/<slug>_rankings.csv,
%                                %        xl_metros/<slug>_decomp.csv,
%                                %        xl_metros/<slug>_summary.csv
%
% Config = v9 (metro_cfg): endogenous workplace choice disciplined to LODES.
% The baseline reproduces the observed LODES flows exactly (route constants
% via exact-hat inside pp_engine); counterfactual flows respond with eps_w and
% income carries the efficiency-units inclusive value.
here = fileparts(mfilename('fullpath'));
out  = fullfile(here, 'xl_metros');
if ~exist(out,'dir'), mkdir(out); end

if nargin < 2, ver = 'v12'; end         % 2026-08-31: version is now explicit;
                                        % ability worlds run 'v14' like the pilots
if nargin < 3, do_decomp = true; end    % freeze-and-re-solve decomposition is ~4x
                                        % the cost; set false to use the ANALYTIC
                                        % channels (verified equivalent) and write
                                        % rankings + summary only
[W, q] = load_metro(slug, ver);              % world + housing-unit LEVEL calibration
cfg = metro_cfg(W.K, ver);              % shared standard metro configuration
cfg.decompose = do_decomp;

res = pp_engine(W, cfg);
res.name = slug;

N = W.N;
[~, wo] = sort(res.dWdH,  'descend'); wrank = zeros(N,1); wrank(wo) = 1:N;
[~, go] = sort(res.wedge, 'descend'); grank = zeros(N,1); grank(go) = 1:N;

% rankings: one row per PUMA
Tr = table(W.gid, W.names, round(res.dWdH), round(res.private), round(W.rent_data), ...
    round(res.wedge), wrank, grank, round(res.dWdH_soc), W.mu_pct, ...
    round(res.mc), round(res.profit), round(res.net_social), round(res.eta,3), ...
    round(sum(res.N0,2)), round(W.H), ...
    'VariableNames', {'gid','name','welfare_usd','price_model_usd','rent_data_usd', ...
    'wedge_usd','welfare_rank','wedge_rank','unpriced_soc_usd','mu_pct', ...
    'mc_usd','profit_usd','net_social_usd','eta_model','households','H_units'});
writetable(Tr, fullfile(out, [slug '_rankings.csv']));

% decomposition: long format (frozen channels; skipped when do_decomp is false,
% in which case the ANALYTIC channels in res.analytic carry the same split)
if do_decomp
    rows = {};
    for j = 1:N
        for c = 1:numel(res.decomp_channels)
            rows(end+1,:) = {W.gid(j), res.decomp_channels{c}, round(res.wedge_decomp(j,c))};
        end
        rows(end+1,:) = {W.gid(j), 'residual_interactions', round(res.wedge_resid(j))};
    end
    writetable(cell2table(rows, 'VariableNames', {'gid','channel','wedge_usd'}), ...
        fullfile(out, [slug '_decomp.csv']));
else
    an = res.analytic;
    resid = res.wedge - (an.agglomeration - an.traffic + an.density_amenity);
    Td = table(W.gid, round(an.density_amenity), round(an.agglomeration), ...
        round(-an.traffic), round(resid), ...
        'VariableNames', {'gid','density_amenity','agglomeration','traffic', ...
        'residual_interactions'});
    writetable(Td, fullfile(out, [slug '_decomp_analytic.csv']));
end

% summary: headline stats + validation moments
cc = corrcoef(res.private, W.rent_data);
% Zoning tax: H-weighted metro share of the price NOT explained by
% construction cost. NOT a validation moment -- GGS (SF 53%, LA 34%, DC 22%,
% Boston 19%, NY 12%) measure a different object on different data and our
% cost side is structure-only (no land), so the levels are not comparable.
% GGS is cited in the deck as motivation, never as a target we hit.
ztax = 100 * sum(W.H .* max(res.profit,0)) / sum(W.H .* res.private);
Ts = table(string(slug), N, double(res.converged), ...
    round(res.max_wedge), string(W.names(res.max_wedge_loc)), ...
    round(100*res.max_wedge/res.private(res.max_wedge_loc),1), ...
    string(W.names(res.ranking(1))), round(res.top_dWdH), ...
    round(cc(1,2),3), round(q,2), round(res.eta_med,3), round(ztax,1), ...
    'VariableNames', {'metro','n_pumas','converged','max_wedge_usd','max_wedge_where', ...
    'max_wedge_pct_price','top_welfare_where','top_welfare_usd', ...
    'corr_rmodel_rdata','service_scale_q','eta_model_med','zoning_tax_metro_pct'});
writetable(Ts, fullfile(out, [slug '_summary.csv']));

fprintf('[%s] N=%d conv=%d | max wedge %+.0f$ (%.1f%%) at %s | corr(r)=%.2f q=%.2f | eta %.3f | zoning tax %.0f%%\n', ...
    slug, N, res.converged, res.max_wedge, 100*res.max_wedge/res.private(res.max_wedge_loc), ...
    W.names(res.max_wedge_loc), cc(1,2), q, res.eta_med, ztax);
end
