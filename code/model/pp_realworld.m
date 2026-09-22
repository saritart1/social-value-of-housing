%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    pp_realworld
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Reads a calibrated world folder (locations, wages, flows, travel times) into the struct the engine expects.
%  Inputs:  data/worlds/<slug>/: locations.csv, abar.csv, pitarget.csv, commute.csv, traveltime.csv, masses.csv, kids_hh.csv, own.csv, meta.json.
%  Output:  W: gid, names, H (units), L (land), rent_data, Abar (N x K wages), pi_target, T (travel times, minutes), masses, K.
%% =========================================================

function W = pp_realworld(slug)
% PP_REALWORLD  Load a REAL metro world built by code/20260706_p1_build_world.py
% into the same W struct pp_engine expects (drop-in replacement for pp_fakeworld).
%
%   W = pp_realworld('Seattle')   % slugs: Seattle, Bay_Area, Boston,
%                                 %        Washington_DC, Los_Angeles, New_York
%
% Units: all dollars are ANNUAL (rent $/yr from ACS B25064 x 12; wages = PUMS
% person earnings 2022$). Population masses are actual household counts, so
% model rents r = alpha*spending/H come out in $/unit/yr, comparable to data.
here = fileparts(mfilename('fullpath'));
wd = fullfile(here, '..', '..', 'data', 'worlds', slug);          % repository layout
if exist(wd,'dir') ~= 7
    wd = fullfile(here, '..', '..', 'data', 'paper1_metros', 'worlds', slug);  % research layout
end
assert(exist(wd,'dir')==7, 'world not built: %s (run 20260706_p1_build_world.py)', wd);

T   = readtable(fullfile(wd,'locations.csv'), 'TextType','string', ...
                'VariableNamingRule','preserve');
N   = height(T);
W = struct();
W.N     = N;
W.slug  = slug;
W.gid   = T.gid;
W.names = T.name;
W.L     = T.L_km2;
W.H     = T.H_units;
W.households = T.households;
W.rent_data  = T.rent_data_yr;          % ACS median gross rent, $/yr (validation)
W.mu_pct     = T.mu_pct;                % Opportunity Atlas place effect (% earnings)
W.mu    = 0.5 + T.mu_pct/40;            % legacy-scale mu (only the absorbed amenity)
kf = fullfile(wd, 'kids_hh.csv');     % v11: children per household (ACS B09001)
if exist(kf, 'file')
    Tk = readtable(kf, 'VariableNamingRule','preserve');
    [ok, loc_] = ismember(string(T.gid), string(Tk.gid));
    W.kids = 0.9 * ones(height(T),1);
    W.kids(ok) = Tk.kids_hh(loc_(ok));
else
    W.kids = 0.9 * ones(height(T),1);   % pre-v11 fallback (the old flat plug)
end
W.mc    = T.mc_yr;                      % annualized construction cost (v0: flat)
W.abar  = ones(N,1);                    % exogenous amenity: absorbed by kappa
W.Abar  = readmatrix(fullfile(wd,'abar.csv'));         % N x K wages ($/yr)
% K is READ FROM THE WORLD (2026-08-24), not hardcoded: the decile worlds have
% K = 10, the education-typed pilot worlds have K = 2..4.
K       = size(W.Abar, 2);   W.K = K;
W.t     = readmatrix(fullfile(wd,'traveltime.csv'));   % N x N minutes (free-flow)
W.piw   = readmatrix(fullfile(wd,'commute.csv'));      % N x N LODES shares
W.piw   = W.piw ./ sum(W.piw, 2);       % rows sum to 1 exactly (CSV is rounded;
                                        % required by the v9 exact-hat commute margin)
W.own   = readmatrix(fullfile(wd,'own.csv'));          % 1 x 10 tenure placeholder
pit     = readmatrix(fullfile(wd,'pitarget.csv'));     % N x 10, cols sum to 1
W.pi_target = pit;
% type masses. Income deciles are equal by construction; education groups are
% not, so a world may ship its own masses.csv (1 x K households per type).
mf = fullfile(wd,'masses.csv');
if exist(mf,'file')
    W.M = readmatrix(mf); W.M = W.M(:);
    W.M = W.M * sum(W.households) / sum(W.M);          % scale to the ACS total
else
    W.M = ones(K,1) * sum(W.households)/K;             % equal-decile default
end
W.coords = [T.lon, T.lat];
assert(size(W.Abar,1)==N && size(W.piw,1)==N && size(pit,1)==N, 'world size mismatch');
end
