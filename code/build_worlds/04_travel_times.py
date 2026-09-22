#!/usr/bin/env python3
# ==========================================================
#  Project:  The Social Value of New Housing by Location
#  Title:    04_travel_times
#  Author:   Sara Restrepo Tamayo
#  Date:     September 2026
#  Resume:   Computes the free-flow drive-time matrices between PUMA centroids from OpenStreetMap.
#  Inputs:  the crosswalk and shapefiles; an OSRM server on a state extract.
#  Output:  one travel-time matrix per metro, in minutes.
# ==========================================================
"""Paper 1 Tier D: build PUMA-to-PUMA free-flow drive-time matrix t_{jm} per metro.

Free, local: OSMnx pulls the metro drive network from OSM, imputes free-flow speeds
and edge travel times, then igraph computes all-pairs shortest times between PUMA
centroids. Free-flow base time is the right t_{jm}; congestion enters the model
separately via delta_c on (E_m/L_m). Usage: python ...travel_times.py "Seattle"
"""
import os, sys, time
import numpy as np, pandas as pd, geopandas as gpd
import osmnx as ox, igraph as ig

ROOT = "/Users/sararestrepotamayo/Documents/Claude/Gradient Fund/GE housing"
SHP  = os.path.join(ROOT, "data", "paper1_metros", "shapefiles")
OUT  = os.path.join(ROOT, "data", "paper1_metros", "travel_times")
os.makedirs(OUT, exist_ok=True)
metro = sys.argv[1]

xw = pd.read_csv(os.path.join(ROOT,"data","paper1_metros","crosswalk","puma_to_metro_crosswalk.csv"),
                 dtype={"state":str,"puma":str})
xw["state"]=xw["state"].str.zfill(2); xw["puma"]=xw["puma"].str.zfill(5)
sub = xw[xw["metro"]==metro].copy()
assert len(sub), f"no PUMAs for metro {metro}"

# load 2020 PUMA polygons for the metro's states, filter, to lat/lon
frames=[]
for st in sorted(sub["state"].unique()):
    g = gpd.read_file(os.path.join(SHP, f"tl_2022_{st}_puma20.shp"))[["STATEFP20","PUMACE20","geometry"]]
    g["state"]=g["STATEFP20"].str.zfill(2); g["puma"]=g["PUMACE20"].str.zfill(5)
    frames.append(g)
polys = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
polys = polys.merge(sub[["state","puma"]], on=["state","puma"]).to_crs(4326)
polys["pid"] = polys["state"]+polys["puma"]
pts = polys.representative_point()
print(f"[{metro}] {len(polys)} PUMAs", flush=True)

t0=time.time()
print(f"[{metro}] downloading drive network ...", flush=True)
footprint = polys.geometry.union_all() if hasattr(polys.geometry,"union_all") else polys.unary_union
G = ox.graph_from_polygon(footprint, network_type="drive", simplify=True)
G = ox.routing.add_edge_speeds(G)
G = ox.routing.add_edge_travel_times(G)
print(f"[{metro}] network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges  ({time.time()-t0:.0f}s)", flush=True)

# snap PUMA centroids to nearest network nodes
nn = ox.distance.nearest_nodes(G, pts.x.values, pts.y.values)

# nx MultiDiGraph -> igraph (directed), weight = travel_time (seconds)
nodes = list(G.nodes()); idx = {n:i for i,n in enumerate(nodes)}
edges, w = [], []
for u,v,k,d in G.edges(keys=True, data=True):
    edges.append((idx[u], idx[v])); w.append(d["travel_time"])
g = ig.Graph(n=len(nodes), edges=edges, directed=True); g.es["tt"]=w
src = [idx[n] for n in nn]
D = np.array(g.distances(source=src, target=src, weights="tt"))/60.0  # minutes

mat = pd.DataFrame(D, index=polys["pid"].values, columns=polys["pid"].values)
mat.to_csv(os.path.join(OUT, f"tmin_{metro.replace(' ','_')}.csv"))
# tidy long form too
long = mat.stack().rename("t_min").reset_index()
long.columns=["origin_pid","dest_pid","t_min"]
long.to_csv(os.path.join(OUT, f"tmin_{metro.replace(' ','_')}_long.csv"), index=False)
finite = np.isfinite(D[~np.eye(len(D),dtype=bool)])
od = D[~np.eye(len(D),dtype=bool)]
print(f"[{metro}] matrix {D.shape}  median off-diag = {np.nanmedian(od[finite]):.1f} min  "
      f"max = {np.nanmax(od[finite]):.1f} min  unreachable pairs = {(~finite).sum()}", flush=True)
print(f"[{metro}] DONE in {time.time()-t0:.0f}s", flush=True)
