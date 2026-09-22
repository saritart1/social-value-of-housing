function export_kappa(slugs, ver)
% EXPORT_KAPPA  Dump the inverted location residuals kappa_{j,k} per metro.
%
%   export_kappa()                  % all six metros
%   export_kappa({'Seattle'})      % subset
%
% kappa is the type-specific residual that makes model sorting reproduce the
% ACS target exactly (pp_engine, closed-form inversion). It absorbs the
% exogenous amenity level abar_j and everything else the modeled terms
% (income, rent, density amenity, composition amenity) do not explain.
% Identification: kappa is only defined up to an additive constant per type
% (Fréchet choice probabilities are invariant to common shifts), so any
% analysis must demean within metro x type. The q units normalization from
% load_metro shifts kappa uniformly across locations and is removed by the
% same demeaning.
%
% Output: xl_metros/kappa_<slug>.csv with one row per location: gid,
% baseline observables (density, mean neighbor income, data rent, model rent,
% Opportunity Atlas mu_pct, H, L) and kappa_d1..kappa_d10.
if nargin < 1 || isempty(slugs)
    slugs = {'Seattle','Boston','Washington_DC','Bay_Area','Los_Angeles','New_York'};
end
here = fileparts(mfilename('fullpath'));
outdir = fullfile(here, 'xl_metros');

if nargin < 2, ver = 'v12'; end
for s = 1:numel(slugs)
    slug = slugs{s};
    [W, q] = load_metro(slug, ver);
    cfg = metro_cfg(W.K, ver);
    cfg.baseline_only = true;
    res = pp_engine(W, cfg);
    assert(res.converged, 'baseline did not converge: %s', slug);

    Nj0 = sum(res.N0, 2);                    % households per location (= data)
    T = table(W.gid, Nj0 ./ W.L, res.ybar0, W.rent_data, res.private, ...
              W.mu_pct, W.H, W.L, ...
              'VariableNames', {'gid','dens_hh_km2','ybar_usd','rent_data_yr', ...
                                'r_model_yr','mu_pct','H_units','L_km2'});
    for k = 1:W.K
        T.(sprintf('kappa_d%d', k)) = res.kappa(:, k);
    end
    fp = fullfile(outdir, sprintf('kappa_%s.csv', slug));
    writetable(T, fp);
    fprintf('%-14s N=%3d  q=%.2f  kappa written -> %s\n', slug, W.N, q, fp);
end
end
