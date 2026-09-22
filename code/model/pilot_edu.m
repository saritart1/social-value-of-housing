%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    pilot_edu
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Runs any world and writes the model-vs-ACS rent comparison behind the fit figure.
%  Inputs:  slug (any world: abil6, edu3, abil10, deciles); ver.
%  Output:  xl_metros/pilot_<slug>.csv (Figure 3).
%% =========================================================

function pilot_edu(slug, ver)
% PILOT_EDU  Run the v14 core on one world and print the comparison numbers.
%   pilot_edu('Boston')        % the income-decile world
%   pilot_edu('Boston_edu4')   % the education-typed pilot world
if nargin < 2, ver = 'v14'; end
[W, q] = load_metro(slug, ver);
cfg = metro_cfg(W.K, ver);
cfg.check_unique = false;
cfg.decompose    = false;   % analytic channels instead: ~4x faster, same split
res = pp_engine(W, cfg);
[mw, j] = max(res.wedge);
fprintf('\n=== %s | K = %d | q = %.3f ===\n', slug, W.K, q);
fprintf('  max wedge      : $%.0f (%.1f%% of price) at %s\n', mw, ...
        100*mw/res.private(j), W.names(j));
fprintf('  price there    : $%.0f   welfare there: $%.0f\n', res.private(j), res.dWdH(j));
fprintf('  eta (median)   : %.3f\n', median(res.eta,'omitnan'));
fprintf('  corr(r_model,r_data): %.3f\n', corr(res.private, W.rent_data));
% channel split at the top PUMA
if isfield(res,'analytic') && isfield(res.analytic,'density_amenity')
    a = res.analytic; z = @(v) (isnan(v))*0 + (~isnan(v)).*v;
    fprintf('  channels at the top PUMA (analytic):\n');
    fprintf('     %-22s %+8.0f\n', 'density_amenity', z(a.density_amenity(j)));
    fprintf('     %-22s %+8.0f\n', 'agglomeration',   z(a.agglomeration(j)));
    fprintf('     %-22s %+8.0f\n', 'traffic',         z(a.traffic(j)));
    fprintf('     %-22s %+8.0f\n', 'interactions', res.wedge(j) ...
        - z(a.density_amenity(j)) - z(a.agglomeration(j)) - z(a.traffic(j)));
end
% top 5 by wedge
[~, ord] = sort(res.wedge, 'descend');
fprintf('  top 5 by wedge:\n');
for t = 1:min(5,numel(ord))
    nm = char(W.names(ord(t))); if numel(nm)>52, nm = nm(1:52); end
    fprintf('     %d. %-54s $%6.0f\n', t, nm, res.wedge(ord(t)));
end
% who takes the marginal unit, by type, at the top PUMA
if isfield(res,'analytic') && isfield(res.analytic,'dN_in')
    din = res.analytic.dN_in(j,:);
    fprintf('  marginal entrant mix at the top PUMA (share of in-flow by type):\n     ');
    fprintf('%6.3f ', din/sum(din)); fprintf('\n');
end
T = table(W.gid, W.names, res.private, res.dWdH, res.wedge, res.eta, ...
    'VariableNames', {'gid','name','price','welfare','wedge','eta'});
% per-PUMA channels. Prefer res.analytic: it is the LINEARISED decomposition,
% computed on the shocked equilibria the headline already uses, so it costs no
% extra solve. res.wedge_decomp is the freeze-and-re-solve version (4x the run
% time) and is used only when it is present. The two agree to a few dollars
% per unit per year (see overleaf/20260728_p1_wedge_decomposition).
try
    a = [];
    if isfield(res,'analytic'), a = res.analytic; end
    if ~isempty(a) && isfield(a,'density_amenity')
        T.density_amenity      = a.density_amenity(:);
        T.agglomeration        = a.agglomeration(:);
        T.traffic              = a.traffic(:);
        T.residual_interactions = res.wedge(:) - ( ...
              fillmissing(a.density_amenity(:),'constant',0) ...
            + fillmissing(a.agglomeration(:),'constant',0) ...
            + fillmissing(a.traffic(:),'constant',0));
    elseif isfield(res,'wedge_decomp') && ~isempty(res.wedge_decomp)
        for c = 1:numel(res.decomp_channels)
            T.(matlab.lang.makeValidName(res.decomp_channels{c})) = res.wedge_decomp(:,c);
        end
        if isfield(res,'wedge_resid'), T.residual_interactions = res.wedge_resid; end
    end
catch me
    fprintf('  [warn] channel export skipped: %s\n', me.message);
end
writetable(T, fullfile('xl_metros', sprintf('pilot_%s.csv', slug)));
fprintf('  -> xl_metros/pilot_%s.csv\n', slug);
end
