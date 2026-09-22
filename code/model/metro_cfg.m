%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    metro_cfg
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Configuration presets for the engine; 'v15' is the memo's core specification, 'v15sigma' adds the composition channel.
%  Inputs:  K, the number of types; ver, the specification string.
%  Output:  cfg, the parameter struct the engine reads.
%  Objects: central values: alpha 0.30, theta 3, eps_w 4.4, lambda_k 0.03-0.06 rising in
%            ability, omega 0.12, delta_c 0.05, kappa 0.01 per minute; sigma 0 ('v15')
%            or 0.05 ('v15sigma'); mobility off in the core.
%% =========================================================

function cfg = metro_cfg(K, ver)
% METRO_CFG  The standard real-metro configuration.
%
%   cfg = metro_cfg(K)          % current standard: v12 (2026-07-28, evening)
%   cfg = metro_cfg(K, 'v11')   % the pinning pass with the old unpriced 0.5
%   cfg = metro_cfg(K, 'v10')   % the pre-pinning mobility chain (flat 0.9
%                               % kids/hh, causal-share 0.55 over 20 years)
%   cfg = metro_cfg(K, 'v9')    % the pre-recentering config (omega = 0.08),
%                               % used by evolution_metro's historical rows
%
% v10 (2026-07-20) = the v9 STRUCTURE (endogenous workplace choice disciplined
% to LODES via exact-hat route constants, efficiency-units income, eps_w = 4.4,
% income-scaled VOT) with two calibration changes, no structural change:
%   (1) omega recentered 0.08 -> 0.12. Four independent lines agree the density
%       amenity sits at 0.11-0.16: Rollet (2025) gamma_RR = 0.11 (causal, NYC);
%       ARSW Berlin 0.16; the eta-locus (inverting our model on Rollet's rent
%       elasticity -0.42) at 0.117-0.13; and the kappa diagnostic (2026-07-20:
%       Delta-kappa co-moves with density growth in all six metros, one-sided
%       evidence against the low end). By-product: model eta moves from -0.46
%       to -0.42/-0.43, onto Rollet's causal estimate.
%   (2) construction costs are the per-PUMA FHFA values (the flat-$12k
%       locations.csv bug was fixed the same day) -- a data repair, listed here
%       because v10 is the first version whose outputs carry it.
% REPORTING: omega and sigma are brackets, not points -- omega in [0.08, 0.16]
% (conservative old value to ARSW), sigma in [0.03, 0.10] (DM sign bound to
% ADI/mapping-B; center 0.05). sensitivity.m carries the bracket ranges.
if nargin < 1, K = 10; end
if nargin < 2, ver = 'v12'; end
cfg = struct();
cfg.commuting          = true;          % baseline = observed LODES shares
cfg.commute_endog      = true;          % v9: live workplace-choice margin
cfg.commute_hat        = true;          %   ...anchored to LODES (exact-hat)
cfg.commute_income     = 'incl';        %   ...efficiency-units income (robustness: 'mean')
cfg.eps_w              = 4.4;           %   Rollet (2025) nu/kappa = 0.044/0.01; theta=3 <= eps_w
cfg.agglom             = true;
cfg.agglom_skillbiased = true;
cfg.lambda             = linspace(0.03, 0.06, K);
cfg.income_het         = 'skillbiased';
cfg.amen_density       = true;
switch ver
    case 'v9',  cfg.omega = 0.08;       % pre-recentering (kept for evolution rows)
    otherwise,  cfg.omega = 0.12;       % v10 central value (bracket [0.08, 0.16])
end
cfg.amen_comp          = true;   cfg.sigma = 0.05;   % bracket [0.03, 0.10]
cfg.cong_house         = false;
cfg.traffic            = true;   cfg.dc    = 0.05;
cfg.mobility           = true;   cfg.mu_w  = 0.10;
% v11 (2026-07-28): the Chetty-Hendren PINNING PASS on the mobility chain --
% a calibration fix, no structural change:
%   (1) kids per household is PER-PUMA DATA (ACS B09001/B19001, worlds/
%       <slug>/kids_hh.csv; metro means 0.51-0.66 vs the old flat 0.9 plug);
%   (2) the per-year causal rate is CH's exposure estimate: 4% of the
%       permanent-resident gap per year of childhood (QJE 2018), replacing
%       the old causal-share-0.55 / 20-years arithmetic (= 2.75%/yr). The
%       engine divides mu_pct by mob_causal_legacy to undo the 0.55 baked
%       into the worlds by build_world, then applies mob_exposure directly.
% Net at metro level: the two corrections roughly offset (x0.6 kids, x1.45
% rate); the cross-section REALLOCATES toward family-heavy PUMAs.
% v12 (2026-07-28 evening): the UNPRICED SHARE derived, not assumed.
%   u = tax + (1-i)(1-tax) with tax = 0.30 (CBO effective marginal rate for
%   low/moderate-income workers) and i = 0.43, the caveat-adjusted
%   internalization rate. Evidence: in-house cross-PUMA check (rents on the
%   full-internalization premium, 409 PUMAs: beta = 0.06 (se .09) conditional
%   on income+density -- a LOWER bound on i via control-absorption +
%   attenuation) and CMTO (15% unassisted moves). i = 0.43 concedes the
%   maximum defensible internalization (schools capitalization, affluent
%   marginal buyers, post-Atlas information). u = 0.30 + 0.57x0.70 = 0.70;
%   bracket [0.60, 0.85] (i in [0.21, 0.57]). Memo: 20260728_p1_mu_pinning.
%   ALSO v12: mu_w = 0 -- the priced-mobility term in V is a location
%   constant, absorbed EXACTLY by the kappa inversion (like abar): a no-op,
%   set to zero for cleanliness (results bit-identical by construction).
%   pv1pct = 7700 documented as the 5%-consistent convention ($50k mean
%   earnings x 1% x 30-yr annuity at 5% = 7,690), matching USER_COST = 0.05.
switch ver
    case {'v9','v10'}
        cfg.mob_mode = 'chetty';         % flat-kids, causal/20 chain
    case 'v11'
        cfg.mob_mode = 'chetty_v11';
        cfg.mob_exposure      = 0.04;
        cfg.mob_causal_legacy = 0.55;
    case 'v13'
        % v13 = DIAGNOSTIC, not a candidate model: v12 with the mobility
        % channel removed entirely (s_j = 0, mu_w = 0). zeta = 0 sits OUTSIDE
        % the defensible bracket (the fiscal floor: the Treasury's ~30% share
        % of the kids' future earnings cannot be internalized by anyone), so
        % this row exists for transparency -- "what the ranking would be on
        % GE externalities alone" -- not as a defensible world.
        cfg.mob_mode  = 'legacy';
        cfg.social_mob = 0;
        cfg.mobility  = false;
        cfg.mu_w      = 0;
    case 'v15sigma'
        % v15 + the COMPOSITION amenity switched back on (sigma = 0.05, the
        % centre of the [0.03, 0.10] bracket). Answers Paul 2026-08-26: the
        % density externality currently depends on TOTAL population only, so
        % spatial sorting of types does not move it. This is the sensitivity
        % that puts a number on what turning that channel on would do.
        cfg.commute_form = 'iceberg';
        cfg.kappa        = 0.01;
        cfg.mob_mode  = 'legacy';
        cfg.social_mob = 0;
        cfg.mobility  = false;
        cfg.mu_w      = 0;
        cfg.amen_comp = true;
        cfg.sigma     = 0.05;
    case 'v15'
        % v15 (2026-08-31) = v14 + ICEBERG COMMUTING. The money form
        % (net = w - VOT*t, VOT from US DOT at 50% of the wage) implies a
        % commute cost of ~5% of income, i.e. kappa ~ 0.002. Every paper in
        % this literature uses kappa = 0.01 (~21%): ARSW 2015 (estimated),
        % Tsivanidis 2019 (0.011-0.012), Zarate (0.009), Rollet 2025 (borrows
        % 0.01). Rollet's eps_w = 4.4, which we USE, was derived assuming
        % kappa = 0.01, so the money form was internally inconsistent with it.
        % DOT's VOT answers a different question (willingness to pay for time
        % savings, for project appraisal); kappa is the cost that rationalises
        % observed commuting flows, which is what a location model needs.
        cfg.commute_form = 'iceberg';
        cfg.kappa        = 0.01;
        cfg.mob_mode  = 'legacy';
        cfg.social_mob = 0;
        cfg.mobility  = false;
        cfg.mu_w      = 0;
        cfg.amen_comp = false;
        cfg.sigma     = 0;
    case 'v14'
        % v14 (2026-08-03) = CANDIDATE CORE: the v12 structure with the two
        % contested channels priced at zero -- composition amenity sigma = 0
        % AND the mobility channel zeta = 0 (s_j = 0, mu_w = 0). Motivation
        % documented in the session notes; results identical to
        % export_variant's 'clean' variant by construction.
        cfg.mob_mode  = 'legacy';
        cfg.social_mob = 0;
        cfg.mobility  = false;
        cfg.mu_w      = 0;
        cfg.amen_comp = false;
        cfg.sigma     = 0;
    otherwise                            % v12
        cfg.mob_mode = 'chetty_v11';
        cfg.mob_exposure      = 0.04;    % CH: 4%/yr of the perm-res gap
        cfg.mob_causal_legacy = 0.55;    % build_world's baked-in causal share
        cfg.mob_unpriced      = 0.70;    % DERIVED (see block comment above)
        cfg.mu_w              = 0;       % vestigial (absorbed by kappa)
end
cfg.vot_income         = true;          % VOT scales with the decile's wage
cfg.invert_A           = true;          % Abar = w_PUMS / dens0^lambda (baseline
                                        % wages equal the DATA; redesign Part II)
end
