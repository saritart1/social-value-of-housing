%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    weights_test
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Re-ranks locations under welfare weights g_k = ybar_k^(-nu).
%  Inputs:  slug.
%  Output:  xl_metros/weights_<slug>.csv, social value per PUMA at nu = 0, 0.5, 1 (Table 5).
%  Objects: weights are mean one, so only the relative emphasis across types changes.
%% =========================================================

function weights_test(slug)
% WEIGHTS_TEST  Does the location ranking survive progressive welfare weights?
% The wedge tracks local income partly because Omega_i is dollars of spending.
% Re-weight each type's welfare by g_k = y_k^(-nu), mean 1, and re-rank.
% NOTE: under weights the pecuniary block no longer cancels to r_j, so the
% reported object is the WEIGHTED SOCIAL VALUE, not the wedge.
[W, ~] = load_metro(slug);
cfg = metro_cfg(W.K, 'v14'); cfg.check_unique = false; cfg.decompose = false;
res = pp_engine(W, cfg);
ybar_k = sum(W.Abar .* (W.pi_target .* W.M(:)'), 1) ./ sum(W.pi_target .* W.M(:)', 1);
Mk = W.M(:)';
fprintf('\n=== %s | K=%d ===\n', slug, W.K);
fprintf('  type mean wage: '); fprintf('%9.0f', ybar_k); fprintf('\n');
base = res.dWdH;                                   % unweighted social value
[~, r0] = sort(base, 'descend');
T = table(W.gid, W.names, res.private, base, 'VariableNames', {'gid','name','price','sv_nu0'});
for nu = [0.5 1.0]
    g = ybar_k .^ (-nu);
    g = g / (sum(g .* Mk) / sum(Mk));              % population-weighted mean 1
    sv = sum(res.dWdH_dec .* g, 2);                   % weighted social value per unit
    [~, r1] = sort(sv, 'descend');
    rho = corr(tiedrank(base), tiedrank(sv));
    top_same = isequal(r0(1), r1(1));
    fprintf('  nu = %.1f | weights ', nu); fprintf('%6.2f', g);
    fprintf(' | rank corr vs unweighted %.3f | top PUMA unchanged: %d\n', rho, top_same);
    fprintf('       unweighted top: %s\n', extractBefore(W.names(r0(1))+"  ", min(52,strlength(W.names(r0(1))))));
    fprintf('       weighted   top: %s\n', extractBefore(W.names(r1(1))+"  ", min(52,strlength(W.names(r1(1))))));
    T.(sprintf('sv_nu%d', round(nu*10))) = sv;
end
writetable(T, fullfile('xl_metros', sprintf('weights_%s.csv', slug)));
fprintf('  -> xl_metros/weights_%s.csv\n', slug);
end
