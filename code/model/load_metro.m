%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    load_metro
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Loads a world and calibrates the housing-unit scale q under the caller's specification, so model rents match the ACS median.
%  Inputs:  slug (e.g. 'Boston_abil6'); ver, the specification string passed on to metro_cfg.
%  Output:  W with H rescaled by q; q itself.
%  Note:    q must be computed under the same specification the caller will run; see the docstring below.
%% =========================================================

function [W, q] = load_metro(slug, ver)
% LOAD_METRO  Load a real metro world AND calibrate the housing-unit LEVEL.
%
%   [W, q] = load_metro('Seattle')
%
% The raw world counts H in ACS dwelling units, but the model's rent
% r = alpha x spending / H then comes out ~2x the ACS median gross rent
% (owner-occupied units embody more housing services than the median RENTAL
% unit that B25064 prices). This pass rescales H into "median-rental-unit
% service equivalents": solve the baseline once, compute
%   q = median( r_model ./ r_data ),
% set H <- q x H, so the re-solved model rents match the ACS level at the
% median by construction. A common q is a pure units normalization: it shifts
% log r by -log q everywhere, is absorbed by the kappa re-inversion, and
% leaves sorting, rankings and elasticities unchanged -- but it makes every
% $-per-unit object (price, wedge, mc comparisons) interpretable as "per
% median rental unit".
% 2026-08-31: q MUST be computed under the same spec the caller will run.
% It was calibrated on metro_cfg's default (v12, money commuting); running
% v15 (iceberg) afterwards cut income ~21%, so model rents came out ~20%
% below the ACS level the q pass was supposed to match.
if nargin < 2, ver = 'v12'; end
W = pp_realworld(slug);
cfg = metro_cfg(W.K, ver);
cfg.baseline_only = true;
r0 = pp_engine(W, cfg);
q  = median(r0.private ./ W.rent_data);
W.H = W.H * q;
W.service_scale = q;
end
