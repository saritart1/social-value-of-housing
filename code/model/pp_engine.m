%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    pp_engine
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Solves the spatial equilibrium and computes the social value of one more unit at each location, the wedge, and its channel decomposition.
%  Inputs:  W, a world struct from load_metro; cfg, a configuration from metro_cfg.
%  Output:  res: wedge, private (rent), welfare, eta_med, the decomposition, and the expansion and deregulation results when asked.
%  Objects: N locations, K ability types. Parameters in cfg: alpha (housing share),
%            theta (residence sorting), eps_w (workplace Frechet), lambda_k (agglomeration),
%            omega (density amenity), delta_c (congestion), kappa (iceberg commuting cost).
%            Inverted objects: Abar (workplace productivity), and the location residual.
%  Note:    the code calls the location residual `kappa` for historical reasons;
%            in the memo the residual is xi and kappa is the commuting cost.
%% =========================================================

function res = pp_engine(W, cfg)
% PP_ENGINE  Shared static spatial-GE solver for all model versions.
%
%   res = pp_engine(W, cfg)
%
%   W   : fake world from pp_fakeworld (N locations, K deciles).
%   cfg : struct of FLAGS + parameters. The flags are exactly the columns of
%         Paul's model-tracking table, so each model version = one cfg:
%           .commuting          live!=work, commute via W.piw           (logical)
%           .commute_endog      workplace CHOICE responds to wages and
%                               (congested) travel time -- Frechet shares
%                               ~ net^eps_w, skill-specific (v7+)        (logical)
%           .commute_hat        REAL-DATA discipline (v9): baseline flows
%                               = observed LODES shares EXACTLY (route
%                               constants inverted implicitly; counterfactual
%                               flows pi0.*(net/net0)^eps_w renormalized --
%                               exact-hat, Dekle-Eaton-Kortum 2007)      (logical)
%           .commute_income     'incl' (v9): expected income = Frechet
%                               inclusive value (workplace draw = efficiency
%                               units, Tsivanidis JMP / Zarate; income
%                               includes the selection/option-value term)
%                               'mean' (v7/v8 history + robustness): share-
%                               weighted mean of route nets (dispersion is
%                               behavior only, no income content)        (char)
%           .agglom             density raises productivity              (logical)
%           .agglom_skillbiased lambda varies by decile (workplace)      (logical)
%           .income_het         'none' | 'engel' | 'skillbiased'         (char)
%           .amen_density       omega * log(N/L) in amenity              (logical)
%           .amen_comp          sigma * log(meanincome) in amenity       (logical)
%           .cong_house         extra gamma*log(N/H) (Route C (alpha+gamma)) (logical)
%           .traffic            commute time rises with dest density dc  (logical)
%           .mobility           child place-effect mu in social value    (logical)
%         params: .alpha .theta .lambda .omega .sigma .gamma .dc .VOT
%                 .alpha0 .a1 (Engel)  .mu_w (mobility weight)  .shock (dH share)
%                 .eps_w (commute-choice elasticity, v7+)
%                 .decompose (default true: wedge decomposition by channel)
%         un-priced mobility term, two modes (.mob_mode):
%           'legacy' : social_mob x mu x mob_value  (the old $70k plug, v5/v6)
%           'chetty' : mob_kids x mob_pv1pct x mob_unpriced x mu_pct  (v7+)
%                      mu_pct   = causal place effect on a child's adult
%                                 earnings, % relative to metro mean
%                                 (Chetty-Hendren / Opportunity Atlas units)
%                      mob_pv1pct = PV of lifetime earnings per 1pp place
%                                 effect per child (~$7.7k, see defaults)
%                      mob_kids = children per household (~0.9)
%                      mob_unpriced = share NOT capitalized/internalized
%                                 (fiscal ~0.30 + un-internalized private)
%
%   res : struct with baseline equilibrium, and the ANSWER to OP's question:
%         dWdH(j)   = social value of new housing at location j (welfare / dH)
%                     = dWdH_priv(j) [aggregate surplus, priced]
%                     + dWdH_soc(j)  [UN-priced social value: mobility/fiscal]
%         dGDPdH(j), private(j)=baseline rent, wedge(j)=dWdH-private, ranking.
%         max_wedge, max_wedge_loc = Paul's summary stats (the largest amount
%                     by which social value exceeds price, and where).
%         mc(j) construction cost, profit(j)=private-mc (developer's return /
%                     zoning tax; <0 = market would not build, cap slack),
%         net_social(j)=dWdH-mc (social value net of resource cost).
%         wedge_decomp (N x C) = contribution of each externality channel to
%                     the wedge (freeze-at-baseline; see below), with
%         decomp_channels (1 x C cellstr), wedge_resid (N x 1).
%
%   All magnitudes are illustrative (fake data). The comparable object across
%   model versions is the RANKING of locations by dWdH.

p = defaults(cfg);
N = W.N; K = W.K;

%% =========================================================
%  (0) Abar INVERSION (real-data worlds): strip the agglomeration term
%% =========================================================
% out of the OBSERVED wages so that baseline model wages equal the data,
%   Abar_{m,k} = w^data_{m,k} / (E0_m/L_m)^{lambda_k}
% (redesign doc, Part II). Without this, baseline wages are inflated by
% density^lambda -- more in dense places. Counterfactual wage responses then
% work through density CHANGES from the baseline, as intended. The fake world
% skips it (its Abar IS the primitive).
if p.invert_A && p.agglom
    Nj0i = sum(W.pi_target .* W.M(:)', 2);
    if p.commuting, E0i = W.piw' * Nj0i; else, E0i = Nj0i; end
    dens0i = E0i ./ W.L;
    if p.agglom_skillbiased
        W.Abar = W.Abar ./ (dens0i .^ reshape(p.lambda,1,[]));
    else
        W.Abar = W.Abar ./ (dens0i .^ p.lambda(1));
    end
end

%% =========================================================
%  (1) baseline: impose N0 = target, invert kappa so it reproduces it
%% =========================================================
N0 = W.pi_target .* W.M(:)';                          % N x K  (M is 1 x K)
o  = objects(N0, W.H, p, W, zeros(N,K));
kappa = o.logVt - (1/p.theta) * log(W.pi_target);     % closed-form inversion
% OPEN CITY: add an outside option so population is elastic (migration margin).
% Chosen so the baseline within-metro sorting AND metro population are unchanged
% (the closed city is the s0->0 limit); only the comparative statics differ.
% v8 JOINT DISTRIBUTION: s0 may be a 1 x K VECTOR (outside-pool share differs
% by income decile -- e.g. larger potential pools at low income), and the
% outside option carries its own INCOME y_out = out_income_ratio x the
% decile's metro mean income, used for (a) national GDP netting (migrants'
% foregone outside output) and (b) making the migrant income jump explicit.
if p.open
    s0r = reshape(p.s0, 1, []);
    if numel(s0r) == 1, s0r = s0r * ones(1, K); end
    p.s0k     = s0r;
    p.logVbar = (1/p.theta) * log(s0r ./ (1 - s0r));   % since sum_j V^theta = 1 at baseline
    p.Mbar    = W.M(:)' ./ (1 - s0r);                  % potential population (1 x K)
end
[N0, conv0] = solveN(W.H, kappa, p, W, N0);           % confirm it is a fixed point
o0   = objects(N0, W.H, p, W, kappa);
%% =========================================================
%  (1b) ROUTE-CONSTANT inversion for the endogenous commute margin (v9)
%% =========================================================
% With commute_hat, the BASELINE is solved on the OBSERVED LODES shares (the
% code path above: p.cal not yet set, so objects() uses fixed shares). The
% bilateral commuting constants that rationalize those shares are then implied
% exactly, and rather than carrying them around we work in CHANGES (exact-hat,
% Dekle-Eaton-Kortum 2007; Monte-Redding-Rossi-Hansberg 2018):
%   pi(j,m|k) = pi0(j,m) * (net/net0)^eps_w / sum_m' pi0 * (net/net0)^eps_w
%   y(j,k)    = y0(j,k) * [sum_m pi0*(net/net0)^eps_w]^(1/eps_w)   ('incl')
% so at baseline (net = net0) flows and income reproduce the data EXACTLY and
% kappa / Abar / q are untouched. Only counterfactual RESPONSES change.
if p.commute_endog && p.commute_hat
    p.cal = commute_cal(o0, p, W);
    o0    = objects(N0, W.H, p, W, kappa);   % identical at baseline by construction
end
%% =========================================================
%  (1c) UNIQUENESS / STABILITY diagnostic (multi-start + contraction)
%% =========================================================
% Motivated by the v10 omega recentering: agglomeration (lambda), density
% amenity (omega) and composition amenity (sigma) are self-reinforcing, and
% strong feedback is the classic multiplicity risk. Two tests, closed city:
%  (a) GLOBAL: re-solve the baseline fixed point from very different starting
%      populations (uniform, reversed sorting, corner, 2 random) and report
%      the max relative deviation from N0; same for a +1% supply shock at the
%      highest-rent location (deviation across starts of the shocked eq.).
%  (b) LOCAL: spectral radius rho of the sorting-map Jacobian at N0
%      (F(N) = M .* sorting(V(N))); rho < 1 = contraction: locally unique
%      and stable, with 1 - rho the margin.
if p.check_unique && ~p.open
    rng(7);
    Mm = W.M(:)'; NK = N*K;
    S = {ones(N,1)/N .* ones(1,K) .* Mm, flipud(W.pi_target) .* Mm, ...
         ((0.9*[1; zeros(N-1,1)] + 0.1/N) .* ones(1,K)) .* Mm};
    for s_ = 1:2
        rr = rand(N,K); S{end+1} = rr ./ sum(rr,1) .* Mm; %#ok<AGROW>
    end
    uq = struct('dev_base',zeros(1,numel(S)), 'conv_base',zeros(1,numel(S)), ...
                'dev_shock',zeros(1,numel(S)), 'conv_shock',zeros(1,numel(S)));
    [~, jr] = max(o0.r); Hs = W.H; Hs(jr) = Hs(jr)*1.01;
    [Nsh_ref, cvr] = solveN(Hs, kappa, p, W, N0);
    for s_ = 1:numel(S)
        [Ns, cvs] = solveN(W.H, kappa, p, W, S{s_});
        uq.dev_base(s_)  = max(abs(Ns(:) - N0(:))) / max(N0(:));
        uq.conv_base(s_) = cvs;
        [Ns2, cvs2] = solveN(Hs, kappa, p, W, S{s_});
        uq.dev_shock(s_)  = max(abs(Ns2(:) - Nsh_ref(:))) / max(Nsh_ref(:));
        uq.conv_shock(s_) = cvs2;
    end
    uq.conv_shock_ref = cvr;
    F0m = sorting(o0.logV, p) .* Mm;                 % the map at N0
    epsu = 1e-5 * max(N0(:));
    J = zeros(NK, NK);
    for c = 1:NK
        Np = N0; Np(c) = Np(c) + epsu;
        oc = objects(Np, W.H, p, W, kappa);
        Fc = sorting(oc.logV, p) .* Mm;
        J(:,c) = (Fc(:) - F0m(:)) / epsu;
    end
    uq.rho = max(abs(eig(J)));
    p.unique = uq;
    fprintf(['  [unique] max dev baseline %.2e | shock %.2e | rho(J) = %.3f ' ...
             '(margin %.3f) | all converged %d\n'], max(uq.dev_base), ...
        max(uq.dev_shock), uq.rho, 1-uq.rho, ...
        all([uq.conv_base uq.conv_shock uq.conv_shock_ref]));
end

Y0k  = sum(N0 .* (o0.y + o0.T), 1);         % 1 x K baseline metro income ($, incl. transfer)
Wel0 = sum(Y0k);                            % total baseline metro income ($) reference
GDP0 = gdp(o0.w, o0.Emk, o0.r, W.H);
if p.open                                    % outside income per decile (v8)
    p.y_out = p.out_income_ratio * sum(N0 .* o0.y, 1) ./ W.M(:)';   % 1 x K $
end

% baseline_only: solve and return the baseline equilibrium, skip the shocks,
% the decomposition and the counterfactual (used by load_metro's level pass).
if p.baseline_only
    res = struct('cfg',p, 'converged',conv0, 'N0',N0, 'r0',o0.r, 'w0',o0.w, ...
        'y0',o0.y, 'E0',o0.E, 'ybar0',o0.ybar, 'Y0k',Y0k, ...
        'welfare0',Wel0, 'gdp0',GDP0, 'private',o0.r, 'kappa',kappa);
    return
end

%% =========================================================
%  (2) the answer: social value of new housing at each location
%% =========================================================
% Welfare change is money-metric AGGREGATE SURPLUS (Paul, 6/30: "aggregate
% surplus instead of average"): each location x decile cell's utility change
% is valued at that CELL's own dollar income (Harberger, trapezoid population
% weights so mover/migrant surplus is captured). Valuing cells at their own
% income makes pure rent TRANSFERS net out exactly (first-order), so the wedge
% is externality content only. The older measure (type-level inclusive-value
% EV scaled by the type's aggregate income) valued winners' and losers'
% dollars at different rates and left a spurious pecuniary wedge (~3% of
% price at the core in the fake world).
[dWdH, dWdH_priv, dWdH_soc, dGDPdH, dGDPdH_nat, dWdH_dec, dWdH_rent, eta, convS, analytic] = ...
    shockruns(W, p, N0, kappa, o0, GDP0);
conv0 = conv0 && convS;

private = o0.r;                       % per-unit price a developer captures
wedge   = dWdH - private;             % social minus private (illustrative units)
dsort = dWdH; dsort(isnan(dsort)) = -Inf;  % non-shocked locations rank last
[~, ranking] = sort(dsort, 'descend');
[max_wedge, max_wedge_loc] = max(wedge);   % Paul's summary stats (max skips NaN)
mc = W.mc(:);                         % construction side (annualized cost/unit)
profit     = private - mc;            % developer return; the GGS zoning tax
net_social = dWdH - mc;               % social value net of resource cost

%% =========================================================
%  (3) wedge decomposition by channel (freeze-at-baseline)
%% =========================================================
% For each ACTIVE externality channel, re-run the counterfactuals with that
% channel FROZEN at its baseline value (wages at baseline density, amenity at
% baseline population, etc). The baseline equilibrium -- and hence kappa and
% the price -- is unchanged by construction, so
%   contribution(channel) = dWdH(full) - dWdH(channel frozen)
% is that channel's share of the wedge; the leftover is the interaction
% residual (small; verified ~0.03% of price with ALL channels frozen).
mob_on = strcmp(p.mob_mode,'chetty') || strcmp(p.mob_mode,'chetty_v11') || p.social_mob > 0;
channels = {};
if p.agglom,          channels{end+1} = 'agglomeration';       end
if p.traffic,         channels{end+1} = 'traffic';             end
if p.amen_density,    channels{end+1} = 'density_amenity';     end
if p.amen_comp,       channels{end+1} = 'composition_amenity'; end
if p.cong_house,      channels{end+1} = 'housing_congestion';  end
if mob_on,            channels{end+1} = 'mobility_unpriced';   end
if p.open,            channels{end+1} = 'migration';           end
C = numel(channels);
decomp = zeros(N, max(C,1)); decomp = decomp(:,1:C);
if p.decompose && C > 0
    dens0 = o0.E ./ W.L;                      % baseline workplace density
    Nj0   = sum(N0, 2);                       % baseline residents
    % OPEN models: measure the ordinary channels within the CLOSED counterpart
    % (same baseline by the s0 calibration) and define
    %   migration = dW(open full) - dW(closed full),
    % which then carries the migration x channel interactions by construction
    % (channels measured inside the open city would double-count them and
    % blow up the residual).
    base = dWdH;
    if p.open
        pcl = p; pcl.open = false;
        base = shockruns(W, pcl, N0, kappa, o0, GDP0);   % closed counterpart
    end
    for c = 1:C
        if strcmp(channels{c}, 'migration')
            decomp(:,c) = dWdH - base;        % the pure migration margin
            continue
        end
        pc = p; if p.open, pc.open = false; end
        switch channels{c}
            case 'agglomeration',       pc.frz.dens_w = dens0;
            case 'traffic',             pc.frz.dens_t = dens0;
            case 'density_amenity',     pc.frz.Nj_a   = Nj0;
            case 'composition_amenity', pc.frz.ybar_c = o0.ybar;
            case 'housing_congestion',  pc.frz.cong0  = p.gamma*log(Nj0 ./ W.H);
            case 'mobility_unpriced',   pc.mob_mode = 'legacy'; pc.social_mob = 0;
        end
        dWc = shockruns(W, pc, N0, kappa, o0, GDP0);
        decomp(:,c) = base - dWc;
    end
end
wedge_resid = wedge - sum(decomp, 2);   % channel interactions (small)

%% =========================================================
%  (3b) ZONING LAB: expansion ladder (Paul 7/14: "changes big enough that
%% =========================================================
% the 1st moment is no longer the main factor") -------------------------------
% Scale the whole stock H -> (1+s) H for each margin s in p.expand_grid, solve
% the full new equilibrium (kappa/Abar/baseline untouched), and record:
%   dW(s)          true welfare change (same trapezoid aggregate-surplus money
%                  metric + unpriced mobility as the dereg block)
%   naive_price(s) the first-moment prediction: value the new units at TODAY'S
%                  rents, sum_j r0_j x dH_j ("price is a good signal" applied
%                  naively to a non-marginal change)
%   marginal objects ON TOP of each expanded equilibrium at two tracked
%   locations (p.expand_track = e.g. the max-wedge PUMA; plus the max-rent
%   core): marginal social value, price, wedge and eta at stock (1+s)H.
% The ratio dW/naive_price and the drift of the marginal wedge/eta along s ARE
% the second-order effects: where the curve leaves 1, the marginal logic ends.
xg = struct('on', ~isempty(p.expand_grid));
if xg.on && ~p.open
    svec = p.expand_grid(:)'; n_s = numel(svec);
    tr = p.expand_track(:)';                 % [jtop jcore] (runner-provided);
    if isempty(tr), [~, tr] = max(o0.r); end % fallback: max model rent
    jtop = tr(1); jcore = tr(end);
    xg.s = svec; xg.jtop = jtop; xg.jcore = jcore;
    z = zeros(1, n_s);
    xg.dW=z; xg.naive_price=z; xg.dr_med_pct=z; xg.conv=z;
    xg.marg_w_top=z; xg.marg_p_top=z; xg.marg_w_core=z; xg.marg_p_core=z;
    xg.eta_top=z; xg.eta_core=z;
    sjx = sj_chain(p, W);
    Nx = N0;
    for is = 1:n_s
        s  = svec(is);
        if isempty(p.expand_target)
            Hs = W.H * (1+s);                         % uniform ladder (analytic arm)
        else
            % PATH mode: s in (0,1] interpolates log-linearly from today's H to
            % the target stock (e.g. the deregulation endpoint) -- the policy-
            % shaped, NON-uniform expansion where resorting/congestion/
            % composition margins are live and rankings can genuinely drift.
            Hs = W.H .* (p.expand_target(:) ./ W.H) .^ s;
        end
        [Nx, cvs] = solveN(Hs, kappa, p, W, Nx);      % warm start along the ladder
        os = objects(Nx, Hs, p, W, kappa);
        wgt0x = N0 .* (o0.y + o0.T);  wgt1x = Nx .* (os.y + os.T);
        dSurx = sum(sum(0.5*(wgt0x + wgt1x) .* (os.logV - o0.logV)));
        dSocx = sum(sjx .* (sum(Nx,2) - sum(N0,2)));
        xg.dW(is)          = dSurx + dSocx;
        xg.naive_price(is) = sum(o0.r .* (Hs - W.H));
        xg.dr_med_pct(is)  = median(100*(os.r ./ o0.r - 1));
        W2 = W; W2.H = Hs;
        p2 = p;                      % marginal objects tracked at cfg.shock_locs
        if isempty(p.shock_locs)     % (the runner passes the RANKING set there);
            p2.shock_locs = unique([jtop jcore]);   % fallback: the two tracked
        else
            p2.shock_locs = unique([p.shock_locs(:)' jtop jcore]);
        end
        GDPs = gdp(os.w, os.Emk, os.r, Hs);
        [dWx, ~, ~, ~, ~, ~, ~, eta_x, cvm] = shockruns(W2, p2, Nx, kappa, os, GDPs);
        xg.marg_w_top(is)  = dWx(jtop);  xg.marg_p_top(is)  = os.r(jtop);
        xg.marg_w_core(is) = dWx(jcore); xg.marg_p_core(is) = os.r(jcore);
        xg.eta_top(is) = eta_x(jtop);    xg.eta_core(is) = eta_x(jcore);
        xg.dW_mat(:,is)    = dWx;        % N x n_s: marginal social value per loc
        xg.wedge_mat(:,is) = dWx - os.r; % (NaN outside shock_locs) for RANK drift
        xg.price_mat(:,is) = os.r;
        xg.conv(is) = double(cvs && cvm);
    end
end

%% =========================================================
%  (4) DEREGULATION counterfactual (Paul 6/23: "cap vs no cap")
%% =========================================================
% Remove the zoning cap: competitive supply builds at every location until
% the rent falls to the (rising) marginal cost of construction,
%     r_j = mc_j(H_j),   mc_j(H) = mc0_j * (H/H0_j)^(1/dereg_epsS),
% with dereg_epsS the BORROWED unregulated supply elasticity (Saiz-style;
% sensitivity parameter -- his estimates include regulation, so they are a
% lower bound on the deregulated elasticity). No demolition (H >= H0).
% Solved jointly with the sorting fixed point; kappa/baseline unchanged.
cf = struct('on', p.dereg_epsS > 0);
if cf.on
    e = p.dereg_epsS;
    Hc = W.H; Ncf = N0;
    for it = 1:400
        [Ncf, cvc] = solveN(Hc, kappa, p, W, Ncf);
        ocf = objects(Ncf, Hc, p, W, kappa);
        mcH = W.mc(:) .* (Hc./W.H).^(1/e);
        gap = log(ocf.r ./ mcH);                 % >0: building still profitable
        gap(Hc <= W.H*(1+1e-9) & gap < 0) = 0;   % cap slack: no forced demolition
        step = gap ./ (1/e + 0.5);               % quasi-Newton (|dlog r/dlog H| ~ 0.5)
        Hn = max(W.H, Hc .* exp(0.7*step));
        moved = max(abs(log(Hn./Hc)));
        Hc = Hn;
        if moved < 1e-8, break; end
    end
    [Ncf, cvc] = solveN(Hc, kappa, p, W, Ncf);
    ocf  = objects(Ncf, Hc, p, W, kappa);
    mcH  = W.mc(:) .* (Hc./W.H).^(1/e);
    % welfare: the same aggregate-surplus money metric as the wedge
    wgt0cf = N0  .* (o0.y  + o0.T);
    wgtcf  = Ncf .* (ocf.y + ocf.T);
    dSur_k = sum(0.5*(wgt0cf + wgtcf) .* (ocf.logV - o0.logV), 1);   % 1 x K $
    sjc = sj_chain(p, W);
    dSoc = sum(sjc .* (sum(Ncf,2) - sum(N0,2)));
    % annualized resource cost of the new units: integral of mc(H) dH
    cost = W.mc(:) .* W.H .* (e/(e+1)) .* ((Hc./W.H).^((e+1)/e) - 1);
    GDPc = gdp(ocf.w, ocf.Emk, ocf.r, Hc);
    cf.converged = cvc;   cf.epsS = e;
    cf.H0 = W.H;          cf.H = Hc;      cf.dH_pct = 100*(Hc./W.H - 1);
    cf.r0 = o0.r;         cf.r = ocf.r;   cf.dr_pct = 100*(ocf.r./o0.r - 1);
    cf.mc_end = mcH;      cf.N = Ncf;     cf.dN = sum(Ncf,2) - sum(N0,2);
    cf.dSur_k = dSur_k;   cf.dSoc = dSoc; cf.cost = cost;
    cf.gross = sum(dSur_k) + dSoc;        cf.net = cf.gross - sum(cost);
    cf.dGDP = GDPc - GDP0;
    if p.open
        cf.dGDP_nat = cf.dGDP + sum(p.y_out .* ((p.Mbar - sum(Ncf,1)) - (p.Mbar - sum(N0,1))));
    else
        cf.dGDP_nat = cf.dGDP;
    end
end

%% =========================================================
%  (5) TARGETED-OCCUPANCY experiment (LIHTC analog; omega/sigma program)
%% =========================================================
% Place e.share x H_j households of the chosen deciles at location j in
% OFF-MARKET units (p.Nexog): they count for density, composition and labor
% supply but not for market rent clearing. The market-rent response at j is
% then the model's analog of the Diamond-McQuade LIHTC price effect; run in
% rich vs poor PUMAs, the CONTRAST isolates the composition channel (sigma).
% Baseline, kappa, Abar untouched (the overlay applies only here). Closed city.
tx = struct('on', ~isempty(p.exp_target));
if tx.on
    e = p.exp_target;            % .locs, .share (units / H_j), .deciles
    Lx = numel(e.locs);
    tx.loc = e.locs(:); tx.dlogr_per_share = zeros(Lx,1);
    tx.dybar_pct = zeros(Lx,1);  tx.dNj_pct = zeros(Lx,1); tx.conv = true;
    for ii = 1:Lx
        j = e.locs(ii);
        Nex = zeros(N, K);
        Nex(j, e.deciles) = e.share * W.H(j) / numel(e.deciles);
        p2 = p; p2.Nexog = Nex;
        [Nt, cvt] = solveN(W.H, kappa, p2, W, N0);
        ot = objects(Nt, W.H, p2, W, kappa);
        tx.dlogr_per_share(ii) = (log(ot.r(j)) - log(o0.r(j))) / e.share;
        tx.dybar_pct(ii) = 100*(ot.ybar(j)/o0.ybar(j) - 1);
        tx.dNj_pct(ii)   = 100*(sum(Nt(j,:))/sum(N0(j,:)) - 1);
        tx.conv = tx.conv && cvt;
    end
end

res = struct('cfg',p, 'converged',conv0, 'N0',N0, 'r0',o0.r, 'w0',o0.w, ...
    'y0',o0.y, 'E0',o0.E, 'ybar0',o0.ybar, 'texp',tx, ...
    'welfare0',Wel0, 'gdp0',GDP0, 'dWdH',dWdH, 'dGDPdH',dGDPdH, ...
    'dGDPdH_nat',dGDPdH_nat, ...
    'dWdH_priv',dWdH_priv, 'dWdH_soc',dWdH_soc, 'Y0k',Y0k, ...
    'private',private, 'wedge',wedge, 'ranking',ranking, 'dWdH_dec',dWdH_dec, ...
    'dWdH_rent',dWdH_rent, ...
    'max_wedge',max_wedge, 'max_wedge_loc',max_wedge_loc, ...
    'mc',mc, 'profit',profit, 'net_social',net_social, ...
    'eta',eta, 'eta_med',median(eta,'omitnan'), 'cf',cf, 'expand',xg, ...
    'wedge_decomp',decomp, 'decomp_channels',{channels}, 'wedge_resid',wedge_resid, ...
    'top_location',ranking(1), 'top_dWdH',dWdH(ranking(1)), 'kappa',kappa, ...
    'analytic',analytic);
end

% =========================================================================
function [dW, dWp, dWs, dG, dGn, dWdec, dWrent, eta, conv, an] = shockruns(W, p, N0, kappa, o0, GDP0)
% Shock each location's housing stock by p.shock and collect the responses.
% Shared by the headline run and the frozen-channel decomposition runs (the
% baseline objects are identical across them, so they are passed in once).
%
% Welfare = money-metric AGGREGATE SURPLUS: sum over location x decile cells
% of [population weight] x [cell $ income] x [utility (logV) change], with
% trapezoid (avg of baseline and shocked) weights so the surplus of movers /
% migrants along the choice margin is captured. kappa cancels in the logV
% difference. Cells that gain mass are new residents' surplus; the outside
% option (open city) has dlogV = 0 so it contributes nothing directly.
N = W.N; K = W.K; s = p.shock; conv = true;
% shock_locs: optional subset of locations to shock (grid/sensitivity runs on
% large metros); non-shocked locations return NaN and are skipped downstream.
locs = p.shock_locs; if isempty(locs), locs = 1:N; end
dW = nan(N,1); dWp = nan(N,1); dWs = nan(N,1); dG = nan(N,1);
dGn = nan(N,1); dWdec = nan(N,K); dWrent = nan(N,K);
eta = nan(N,1);                                  % own rent response dlog r_j / dlog H_j
wgt0 = N0 .* (o0.y + o0.T);                      % baseline $ weights per cell
% national GDP netting (open city): migrants' foregone OUTSIDE output. The
% metro GDP change counts an in-migrant's full metro output; the NATIONAL
% (Hsieh-Moretti misallocation) gain nets what they stop producing outside.
if p.open, GDPnat0 = GDP0 + sum(p.y_out .* (p.Mbar - sum(N0,1))); end
% UN-priced social value per household (fiscal + un-internalized child
% mobility): accrues to society (largely the NEXT generation) but NOT to the
% developer's rent. Two modes:
%  'chetty' (v7+, disciplined): kids/hh x PV of adult earnings per 1pp place
%           effect x un-priced share x place effect mu_pct (%).
%  'legacy' (v5/v6 history): social_mob x mu x mob_value -- the old plug.
sj = sj_chain(p, W);   % un-priced mobility value per household-year (see sj_chain)
%% =========================================================
%  ANALYTIC (linearized) channel weights, computed only when asked
%% =========================================================
% The linearization of the money-metric surplus (see 20260728_p1_wedge_
% decomposition.tex): the rent change and the lump-sum rebate cancel to
% exactly r_j, so dW/dH_j - r_j is externality content only, and each channel
% is (elasticity) x (baseline dollar weight) x (GE response).
an = struct();
want_an = nargout >= 10;
if want_an
    dens0 = o0.E ./ W.L;
    teff0 = times_eff(dens0, p, W);
    if p.vot_income
        wbar = mean(W.Abar, 1);
        mid  = max(1, floor(W.K/2)) : min(W.K, floor(W.K/2)+1);
        votk = p.VOT * wbar / mean(wbar(mid));
    else
        votk = p.VOT * ones(1, W.K);
    end
    pi0 = W.piw; if isfield(p,'cal'), pi0 = p.cal.pi0; end
    Om0 = sum(N0 .* (o0.y + o0.T), 2);          % N x 1  dollar weight per location
    Gm  = zeros(N,1);                            % agglomeration weight per workplace
    Dm  = zeros(N,1);                            % traffic weight per workplace
    for k = 1:K
        [~, wshare, cshare] = commute_net(o0.w(:,k), teff0, votk(k), p);
        lam_k = p.lambda(min(k, numel(p.lambda)));
        wgtk = (N0(:,k) .* o0.y(:,k))';          % 1 x N over residence
        if p.agglom
            Gm = Gm + lam_k * (wgtk * (pi0 .* wshare))';
        end
        if p.traffic
            Dm = Dm + p.dc * (wgtk * (pi0 .* cshare))';
        end
    end
    an.Gm = Gm; an.Dm = Dm; an.Om0 = Om0; an.sj = sj;
    an.agglomeration = nan(N,1); an.traffic = nan(N,1);
    an.density_amenity = nan(N,1); an.composition_amenity = nan(N,1);
    an.mobility_unpriced = nan(N,1);
    an.raw_dlogN = nan(N,1); an.raw_dlogy = nan(N,1);
    % marginal-composition capture (2026-08-02): who the marginal household
    % is, by decile. dN_in = in-flow at the shocked PUMA per unit of housing;
    % mob_dec = the mobility term decomposed by decile (rows sum to
    % mobility_unpriced). Diagnostic for the p25-parent anchoring of sj.
    an.dN_in = nan(N,K); an.mob_dec = nan(N,K);
end
for j = locs(:)'
    Hs = W.H; Hs(j) = Hs(j)*(1+s);
    [Nj, cj] = solveN(Hs, kappa, p, W, N0);
    oj   = objects(Nj, Hs, p, W, kappa);
    wgt1 = Nj .* (oj.y + oj.T);
    dSur = sum(0.5*(wgt0 + wgt1) .* (oj.logV - o0.logV), 1);   % 1 x K dollars
    % rent-channel component of the surplus (for the tenure-incidence table:
    % owner-occupiers are hedged against rent changes on their own home)
    dRnt = sum(0.5*(wgt0 + wgt1) .* ...
               (-(oj.ae .* log(oj.r) - o0.ae .* log(o0.r))), 1);   % 1 x K $
    dN   = sum(Nj,2) - sum(N0,2);                % change in residents per location
    dSoc = sum(sj .* dN);
    GDPj = gdp(oj.w, oj.Emk, oj.r, Hs);
    dWp(j)     = sum(dSur) / (s*W.H(j));         % $ priced (private surplus) per unit
    dWs(j)     = dSoc      / (s*W.H(j));         % $ un-priced social per unit
    dW(j)      = dWp(j) + dWs(j);                % $ social welfare per housing unit
    dWdec(j,:) = dSur / (s*W.H(j));              % $ priced welfare per unit, BY decile
    dWrent(j,:)= dRnt / (s*W.H(j));              % $ rent-channel component, BY decile
    dG(j)      = (GDPj - GDP0) / (s*W.H(j));     % $ metro GDP per housing unit
    % Rollet over-ID moment: the model's own rent-supply response at j
    % (net, after resorting/migration). Compare to eta = -0.42 (NYC upzoning).
    eta(j)     = (log(oj.r(j)) - log(o0.r(j))) / log(1+s);
    if p.open
        GDPnatj = GDPj + sum(p.y_out .* (p.Mbar - sum(Nj,1)));
        dGn(j)  = (GDPnatj - GDPnat0) / (s*W.H(j));   % $ NATIONAL GDP per unit
    else
        dGn(j)  = dG(j);                         % closed city: no outside margin
    end
    if want_an
        u   = s * W.H(j);
        dld = log(oj.E) - log(o0.E);             % dlog workplace density (L fixed)
        dlN = log(sum(Nj,2)) - log(sum(N0,2));   % dlog residents
        dly = log(oj.ybar) - log(o0.ybar);       % dlog mean neighbour income
        if p.agglom,       an.agglomeration(j)       =  (Gm' * dld) / u; end
        if p.traffic,      an.traffic(j)             = -(Dm' * dld) / u; end
        an.raw_dlogN(j) = (Om0' * dlN) / u;
        an.raw_dlogy(j) = (Om0' * dly) / u;
        if p.amen_density, an.density_amenity(j)     = p.omega * (Om0' * dlN) / u; end
        if p.amen_comp,    an.composition_amenity(j) = p.sigma * (Om0' * dly) / u; end
        an.mobility_unpriced(j) = sum(sj .* (sum(Nj,2) - sum(N0,2))) / u;
        an.dN_in(j,:)   = (Nj(j,:) - N0(j,:)) / u;
        an.mob_dec(j,:) = (sj' * (Nj - N0)) / u;
    end
    conv = conv && cj;
end
end

% =========================================================================
function o = objects(Nmat, H, p, W, kappa)
% All equilibrium objects implied by a population matrix Nmat (N x K).
% p.frz.* (if set) FREEZES one externality channel at its baseline value --
% used by the wedge decomposition; at the baseline itself frozen == actual.
Nj = sum(Nmat, 2);                                   % residents per location

% value of time: common (p.VOT $/yr per commute-minute) or scaled by each
% decile's wage (vot_income=true; US DOT: VOT ~ 50% of the wage). The common
% VOT charges low earners the MEDIAN worker's time value, which can push their
% commute-netted income negative in real metros.
if p.vot_income
    wbar = mean(W.Abar, 1);                          % 1 x K mean wage by decile
    mid  = max(1, floor(W.K/2)) : min(W.K, floor(W.K/2)+1);
    votk = p.VOT * wbar / mean(wbar(mid));           % 1 x K, median decile = p.VOT
else
    votk = p.VOT * ones(1, W.K);
end

% the endogenous margin engages only once the route calibration exists (with
% commute_hat, the BASELINE itself is defined on the fixed observed shares)
endog_on = p.commute_endog && (~p.commute_hat || isfield(p, 'cal'));
if endog_on
    % ---- endogenous commuting (v7+): Frechet workplace choice ----
    % A decile-k worker living at j picks workplace m with share ~ net^eps_w,
    % net(j,m,k) = w(m,k) - VOT * t_eff(j,m). Flows determine workplace
    % employment E, which feeds back into wages (agglomeration) and travel
    % times (traffic), so flows <-> E is a small inner fixed point.
    % v9 (commute_hat): shares and income in CHANGES off the observed baseline
    % (see flows()); v7/v8 fake-world mode: shares ~ net^eps_w directly.
    E = W.piw' * Nj;                                 % init from gravity shares
    for it2 = 1:200
        dens = E ./ W.L;
        w    = wages(dens, p, W);
        teff = times_eff(dens, p, W);
        [Emk, y] = flows(w, teff, Nmat, votk, p, W);
        Enew = sum(Emk, 2);
        dE = max(abs(Enew - E) ./ max(E, 1e-9));
        E  = 0.5*E + 0.5*Enew;
        if dE < 1e-10, break; end
    end
    dens = E ./ W.L;
    w    = wages(dens, p, W);
    teff = times_eff(dens, p, W);
    [Emk, y] = flows(w, teff, Nmat, votk, p, W);
elseif p.commuting
    % ---- FIXED commute shares (v1-v6 gravity; real metros: observed LODES) ----
    % Same $1 route-net floor as flows(), so the commute_hat baseline (defined
    % on this branch) and the hat counterfactual map agree exactly.
    E    = W.piw' * Nj;
    dens = E ./ W.L;
    w    = wages(dens, p, W);
    teff = times_eff(dens, p, W);
    y    = zeros(W.N, W.K);
    for k = 1:W.K
        net    = commute_net(w(:,k), teff, votk(k), p);   % N x N $
        y(:,k) = sum(W.piw .* net, 2);
    end
    Emk  = W.piw' * Nmat;
else
    E = Nj; dens = E ./ W.L;
    w = wages(dens, p, W);
    y = w; Emk = Nmat;                               % live = work, no commute cost
end
y = max(y, 1e-4);

% reference income first (so the Engel share survives any USD rescaling)
ybar_agg = sum(sum(Nmat.*y)) / sum(Nj);

% housing share (Engel = falls with RELATIVE income; else common alpha)
if strcmp(p.income_het, 'engel')
    ae = min(max(p.alpha0 - p.a1*log(y./ybar_agg), 0.10), 0.60);  % N x K
else
    ae = p.alpha * ones(W.N, W.K);
end
abar_a = mean(ae(:));
T = abar_a/(1-abar_a) * ybar_agg;
r = sum(ae .* Nmat .* (y + T), 2) ./ H;              % N x 1
ybar = sum(Nmat.*y, 2) ./ Nj;                        % N x 1

% targeted-occupancy overlay (v10 experiment): p.Nexog (N x K) households are
% PLACED exogenously (LIHTC-analog: off-market units). They count for density,
% composition, and labor supply (already in Nmat), but NOT for market rent
% clearing -- they occupy reserved non-market units, so market rents clear on
% the FREE population and the unchanged market stock. Recompute r on Nfree:
if ~isempty(p.Nexog)
    Nfree = max(Nmat - p.Nexog, 0);
    r = sum(ae .* Nfree .* (y + T), 2) ./ H;
end

% amenity (density / composition / mobility optional), then minus kappa
loga = log(W.abar);
if p.amen_density
    Na = Nj;
    if isfield(p.frz,'Nj_a'), Na = p.frz.Nj_a; end   % density amenity frozen
    loga = loga + p.omega*log(Na./W.L);
end
if p.amen_comp
    yb = ybar;
    if isfield(p.frz,'ybar_c'), yb = p.frz.ybar_c; end   % composition frozen
    loga = loga + p.sigma*log(yb);
end
if p.mobility,     loga = loga + p.mu_w*W.mu;          end
cong = zeros(W.N,1);
if p.cong_house
    if isfield(p.frz,'cong0'), cong = p.frz.cong0;   % housing congestion frozen
    else, cong = p.gamma*log(Nj./H);
    end
end

logV  = log(y + T) - ae.*log(r) - cong + (loga - kappa);   % N x K
o = struct('logV',logV, 'logVt',logV + kappa, 'r',r, 'w',w, 'y',y, ...
           'E',E, 'Emk',Emk, 'ybar',ybar, 'T',T, 'ae',ae);
end

% =========================================================================
function w = wages(dens, p, W)
% Wages w(m,k): productivity x agglomeration in workplace density (freezable).
if p.agglom
    dw = dens;
    if isfield(p.frz,'dens_w'), dw = p.frz.dens_w; end   % agglomeration frozen
    if p.agglom_skillbiased
        lam = reshape(p.lambda, 1, []);              % 1 x K (avoid .^/transpose precedence)
        w = W.Abar .* (dw .^ lam);                   % (N x 1) .^ (1 x K) = N x K
    else
        w = W.Abar .* (dw .^ p.lambda(1));           % scalar lambda
    end
else
    w = W.Abar;                                      % productivity straight from data
end
end

% =========================================================================
function teff = times_eff(dens, p, W)
% Effective travel times (minutes): congested by DESTINATION density (freezable).
if p.traffic
    dt = dens;
    if isfield(p.frz,'dens_t'), dt = p.frz.dens_t; end   % traffic frozen
    teff = W.t .* (dt' .^ p.dc);
else
    teff = W.t;
end
end

% =========================================================================
function [Emk, ynet] = flows(w, teff, Nmat, votk, p, W)
% Endogenous commute flows: decile-k worker at residence j chooses workplace m
% with Frechet share  pi(j,m|k) ~ net(j,m,k)^eps_w,  net = w(m,k) - VOT_k*t_eff.
% Returns workplace employment Emk (N x K) and expected chosen net income
% ynet (N x K). Skill-specific flows: high deciles chase the wage premium
% harder than the commute cost, so flows differ by k (full-rank behavior).
%
% Two design axes (v9):
%  p.cal set (commute_hat, real data): EXACT-HAT off the observed baseline.
%    pi(j,m|k) = pi0(j,m)*(net/net0)^eps_w, renormalized. The observed LODES
%    shares ARE the route constants (they absorb every systematic bilateral
%    friction/affinity), so the baseline reproduces the data exactly and only
%    counterfactual responses differ (Dekle-Eaton-Kortum; MRRH 2018).
%  p.commute_income:
%    'incl': workplace draw = EFFICIENCY UNITS (Tsivanidis JMP; Zarate), so
%       expected chosen money income is the Frechet expected max = inclusive
%       value; in hat form  y = y0 * [sum_m pi0*(net/net0)^eps_w]^(1/eps_w).
%       Selection is income: movers land where their match draw is good.
%    'mean': share-weighted mean of route nets (v7/v8 history; robustness
%       row where the dispersion is behavior only and carries no income).
N = W.N; K = W.K;
Emk = zeros(N, K); ynet = zeros(N, K);
hat = isfield(p, 'cal');
for k = 1:K
    net = commute_net(w(:,k), teff, votk(k), p);     % N(res) x N(work) $/yr
    if hat
        rel = (net ./ p.cal.net0(:,:,k)) .^ p.eps_w; % (net-hat)^eps_w
        num = p.cal.pi0 .* rel;
        den = sum(num, 2);                           % N x 1 inclusive-value hat^eps_w
        sh  = num ./ den;                            % rows sum to 1; = pi0 at baseline
        if strcmp(p.commute_income, 'incl')
            ynet(:,k) = p.cal.y0(:,k) .* den.^(1/p.eps_w);
        else
            ynet(:,k) = sum(sh .* net, 2);
        end
    else
        sh  = net .^ p.eps_w;
        S   = sum(sh, 2);
        sh  = sh ./ S;                               % choice shares, rows sum to 1
        if strcmp(p.commute_income, 'incl')
            % expected max of z*net, z ~ Frechet(eps_w): Gamma(1-1/eps_w) * IV
            ynet(:,k) = gamma(1 - 1/p.eps_w) * S.^(1/p.eps_w);
        else
            ynet(:,k) = sum(sh .* net, 2);           % share-weighted mean
        end
    end
    Emk(:,k)  = sh' * Nmat(:,k);                     % workplace employment
end
end

% =========================================================================
function cal = commute_cal(o0, p, W)
% Baseline route-level calibration for the exact-hat commute margin (v9).
% Stores the observed shares pi0 (the implicit route constants), the baseline
% route nets net0 (at converged baseline wages and congested times), and the
% baseline commute-weighted income y0 -- all reproduced exactly at net = net0.
if p.vot_income
    wbar = mean(W.Abar, 1);
    mid  = max(1, floor(W.K/2)) : min(W.K, floor(W.K/2)+1);
    votk = p.VOT * wbar / mean(wbar(mid));
else
    votk = p.VOT * ones(1, W.K);
end
dens0 = o0.E ./ W.L;
teff0 = times_eff(dens0, p, W);
cal = struct('pi0', W.piw);
cal.net0 = zeros(W.N, W.N, W.K);
cal.y0   = zeros(W.N, W.K);
for k = 1:W.K
    net0 = commute_net(o0.w(:,k), teff0, votk(k), p);% same form as flows()
    cal.net0(:,:,k) = net0;
    cal.y0(:,k)     = sum(W.piw .* net0, 2);         % == o0.y(:,k) by the fixed branch
end
end

% =========================================================================
function [Nmat, conv] = solveN(H, kappa, p, W, Nmat)
% Fixed point in the population matrix given H and kappa (damped iteration).
d = inf;
for it = 1:2000
    o  = objects(Nmat, H, p, W, kappa);
    pn = sorting(o.logV, p);
    if p.open, Mmass = p.Mbar; else, Mmass = W.M(:)'; end
    if isempty(p.Nexog)
        Nn = pn .* Mmass;
    else
        % targeted overlay: placed households don't re-sort; the free pool
        % (totals minus placed mass) sorts as usual. Closed city only.
        Nn = pn .* (Mmass - sum(p.Nexog, 1)) + p.Nexog;
    end
    d  = max(abs(Nn(:) - Nmat(:)));
    Nmat = 0.5*Nmat + 0.5*Nn;
    if d < 1e-10, break; end
end
conv = d < 1e-7;
end

% =========================================================================
function pim = sorting(logV, p)
% Frechet/logit shares per decile column. Open city adds the outside option
% to the denominator, so shares of the POTENTIAL population sum to < 1 (the
% remainder stays outside the metro); closed city omits it (shares sum to 1).
m  = max(logV, [], 1);
ex = exp(p.theta*(logV - m));
denom = sum(ex, 1);
if p.open, denom = denom + exp(p.theta*(p.logVbar - m)); end
pim = ex ./ denom;
end

% =========================================================================
function G = gdp(w, Emk, r, H)
% Labour product at the workplace + housing services.
G = sum(sum(w .* Emk)) + sum(r .* H);
end

% =========================================================================
function sj = sj_chain(p, W)
% SJ_CHAIN  Un-priced mobility value per household-year at each location.
%  'chetty_v11' (2026-07-28 pinning pass): per-PUMA kids (ACS B09001) x
%     lifetime PV per 1% earnings x CH exposure rate (4%/yr of the PERM-RES
%     gap, QJE 2018) x un-internalized share. build_world baked causal-share
%     0.55 into mu_pct, so divide it back out to recover the observed
%     gradient before applying the exposure rate.
%  'chetty' (v7-v10): flat kids/hh x (PV/years) x unpriced x causal mu_pct.
%  'legacy' (v5/v6): the old plug.
if strcmp(p.mob_mode, 'chetty_v11')
    kids = 0.9 * ones(W.N,1);
    if isfield(W, 'kids'), kids = W.kids(:); end
    sj = kids .* (p.mob_pv1pct * p.mob_exposure * p.mob_unpriced ...
                  .* (W.mu_pct(:) / p.mob_causal_legacy));
elseif strcmp(p.mob_mode, 'chetty')
    sj = p.mob_kids * (p.mob_pv1pct / p.mob_years) * p.mob_unpriced * W.mu_pct;
    sj = sj(:) .* ones(W.N,1);
else
    sj = p.social_mob * W.mu * p.mob_value;
end
sj = sj(:);
end

% =========================================================================
function p = defaults(cfg)
% Fill any missing flag/param with a sensible default.
d = struct('commuting',true,'commute_endog',false,'agglom',true, ...
    'agglom_skillbiased',false, ...
    'income_het','skillbiased','amen_density',false,'amen_comp',false, ...
    'cong_house',false,'traffic',false,'mobility',false, ...
    'alpha',0.30,'theta',3.0,'lambda',0.05,'omega',0.08,'sigma',0.05, ...
    'gamma',0.10,'dc',0.05,'VOT',175,'vot_income',false, ...
    'alpha0',0.32,'a1',0.05,'mu_w',0.10, ...
    'eps_w',4.4,'commute_hat',false,'commute_income','mean', ...
    'open',false,'s0',0.5,'out_income_ratio',0.75, ...
    'mob_mode','legacy','social_mob',0,'mob_value',70000, ...
    'mob_kids',0.9,'mob_pv1pct',7700,'mob_unpriced',0.5,'mob_years',20, ...
    'mob_exposure',0.04,'mob_causal_legacy',0.55, ...
    'decompose',true,'shock',0.001,'dereg_epsS',0,'baseline_only',false, ...
    'commute_form','money', 'kappa',0.01, ...
    'invert_A',false,'shock_locs',[],'Nexog',[],'exp_target',[],'frz',struct(), ...
    'check_unique',false,'expand_grid',[],'expand_track',[],'expand_target',[]);
    % check_unique: multi-start + contraction-margin diagnostic (uniqueness_check.m).
    % expand_grid: vector of proportional stock expansions s for the zoning lab
    %   (block 3b; zoning_lab.m); expand_track = location index whose marginal
    %   objects are tracked along the ladder (default: the max-rent core).
    % Nexog (N x K): exogenously placed households (targeted-occupancy /
    % LIHTC-analog experiment, building_experiment.m). Counted in density,
    % composition and labor supply; excluded from market rent clearing
    % (off-market units). Closed city only. Empty = off (all standard runs).
    % shock_locs: subset of locations to shock (empty = all). Used by the
    % (omega,sigma) grid on large metros; non-shocked locations return NaN.
    % dereg_epsS > 0 switches on the no-cap counterfactual (supply expands
    % until rent = rising marginal cost; epsS = unregulated supply elasticity).
    % shock=0.001: the deliverable is the MARGINAL social value dW/dH; larger
    % shocks contaminate the wedge with curvature (the rent decline over the
    % shock): ~2pp of price at 10%, ~$300/unit at 1% -- comparable to the
    % channel contributions themselves once mobility is in annual units.
    % open=true lets population migrate against an outside option (Hsieh-Moretti);
    % s0 = baseline share of the potential population living outside the metro.
    % VOT=175: $0.35/min (US DOT) x 2 trips/day x 250 workdays = $/yr per minute
    % of one-way commute. alpha0=0.32: reference housing share at mean income.
    % eps_w=4.4: workplace-choice (Frechet) elasticity = Rollet (2025, NYC)
    %   eps_W = nu/kappa = 0.044/0.01, PPML gravity on LODES + Google times.
    %   Range for sensitivity: Tsivanidis (AER 2026, Bogota) 3.4; Zarate
    %   (2024, Mexico City) 3.1-4.7; ARSW (2015, Berlin) 6.83. Nested
    %   consistency with the residence margin: eps_w >= theta (4.4 > 3).
    %   v7/v8 history files set eps_w=4 explicitly.
    % commute_hat=true (v9 real data): baseline commute flows = observed LODES
    %   shares exactly; counterfactuals in changes (exact-hat). Requires the
    %   engine to build p.cal after the baseline solve.
    % commute_income='incl' (v9): workplace draw = efficiency units, so
    %   expected income = Frechet inclusive value (selection is income);
    %   'mean' = v7/v8 history + robustness (dispersion moves flows only).
    % 'chetty' mobility calibration (v7+), replaces the old $70k plug:
    %   mob_pv1pct=$7,700: PV of ONE child's lifetime adult earnings per 1pp
    %     causal place effect = 1% x $70k mean HH income x 23.1 (40-yr annuity
    %     @3%) x 0.48 (discount ~25 yrs back to childhood).
    %   mob_kids=0.9 children per household (Census, all households).
    %   mob_unpriced=0.5: share of the gain NOT internalized in the location
    %     choice = fiscal ~0.30 (taxes/transfers on the earnings gain) + part
    %     of the private gain parents don't internalize (CMTO information
    %     frictions). Sensitivity range 0.30-0.65.
    %   mob_years=20: Chetty-Hendren exposure window; divides the PV into a
    %     per-year-of-residence flow so the term is in the same ANNUAL units
    %     as rents/wages (all channels of dW/dH are annual flows).
f = fieldnames(d);
for i = 1:numel(f)
    if ~isfield(cfg, f{i}) || isempty(cfg.(f{i})), cfg.(f{i}) = d.(f{i}); end
end
p = cfg;
end

% =========================================================================
% NOTE (2026-08-31): p.kappa here is the ICEBERG COMMUTING cost. The variable
% `kappa` elsewhere in this file is the LOCATION RESIDUAL, a different object,
% written xi in the deck and derivation doc. Code names were left unchanged.
function [net, wshare, cshare] = commute_net(w_k, teff, votk_k, p)
% COMMUTE_NET  Wage net of commuting, in dollars, in one of two forms.
%
%   'money'   (pre-2026-08-31 default): net = w - VOT_k * t_eff, floored at $1.
%             VOT borrowed from US DOT (50% of the wage, local personal travel).
%   'iceberg' (2026-08-31, the literature standard): net = w * exp(-kappa*t_eff),
%             following Ahlfeldt-Redding-Sturm-Wolf (2015) kappa = 0.01, and
%             Tsivanidis (2019) who puts the iceberg on EARNINGS rather than
%             utility, so net stays in dollars and the money-metric welfare
%             chain is untouched. No VOT: the cost is proportional to the wage
%             by construction, and net can never go negative (no $1 floor).
%
% wshare, cshare are the two weights the ANALYTIC channel decomposition needs:
%   dlog(net)/dlog(w)      = wshare   (agglomeration rides on this)
%   -dlog(net)/dlog(t_eff) = cshare   (congestion rides on this)
if strcmp(p.commute_form, 'iceberg')
    net    = w_k(:)' .* exp(-p.kappa * teff);        % N(res) x N(work), > 0
    wshare = ones(size(net));
    cshare = p.kappa * teff;
else
    raw    = w_k(:)' - votk_k * teff;
    net    = max(raw, 1);                            % $1 floor
    livein = double(raw > 1);                        % floor kills the derivative
    wshare = livein .* (w_k(:)' ./ net);
    cshare = livein .* (votk_k * teff ./ net);
end
end
