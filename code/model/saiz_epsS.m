%% =========================================================
%  Project:  The Social Value of New Housing by Location
%  Title:    saiz_epsS
%  Author:   Sara Restrepo Tamayo
%  Date:     September 2026
%  Resume:   Metro housing-supply elasticities from Saiz (2010), used in the sensitivity runs.
%  Inputs:  slug; specification suffixes such as _abil6 are stripped.
%  Output:  the supply elasticity for that metro.
%% =========================================================

function e = saiz_epsS(slug)
% SAIZ_EPSS  Metro housing supply elasticities from Saiz (2010, QJE 125(3),
% Table VI, pp. 1283-84) -- VERIFIED against the published table 2026-07-06.
%   LA-Long Beach 0.63 | San Francisco 0.66 | Oakland 0.70 | San Jose 0.76 |
%   New York 0.76 | Boston-Worcester-Lawrence 0.86 | Seattle-Bellevue 0.88 |
%   Washington DC-MD-VA-WV 1.61.
% Bay Area = stock-weighted SF/Oakland/San Jose ~ 0.70. New York uses the NY
% PMSA value (the dominant unit in CBSA 35620; Newark 1.16 / Jersey City 1.42
% would pull the metro average up slightly).
% CAVEAT: Saiz elasticities are estimated WITH regulation in place, so for the
% deregulation counterfactual they are a LOWER bound on the no-cap supply
% elasticity; the sensitivity range (0.5-2.0) spans the deregulated case.
% 2026-08-31: strip any world-variant suffix (_abil6, _edu3, _wdec10, ...) so
% the elasticity is looked up on the underlying metro geography.
slug = regexprep(slug, '_(abil|edu|wdec)\d*.*$', '');
switch slug
    case 'Seattle',       e = 0.88;
    case 'Boston',        e = 0.86;
    case 'Washington_DC', e = 1.61;
    case 'Bay_Area',      e = 0.70;
    case 'Los_Angeles',   e = 0.63;
    case 'New_York',      e = 0.76;
    otherwise, error('no Saiz elasticity mapped for %s', slug);
end
end
