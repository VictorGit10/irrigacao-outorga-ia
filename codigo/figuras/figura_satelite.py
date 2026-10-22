"""Figura 5 da apresentação: Sentinel-2 na seca (agosto de 2025), cor natural e NDVI, em Cristalina.

Desconta o acréscimo de 1000 das imagens Sentinel-2 com processing baseline >= 04.00.
Uso:  python figura_satelite.py   -> docs/apresentacao/img/5a_satelite_cor.png e 5b_satelite_ndvi.png
"""
import json, math, os, sys, urllib.request, urllib.parse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from matplotlib.collections import PatchCollection
from shapely.geometry import shape, Point

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from dados import camada
OUT = os.path.join(D, "..", "..", "docs", "apresentacao", "img"); os.makedirs(OUT, exist_ok=True)
BG, DARK, MUTED, TEAL, OCHRE, RED, LINE = "#f3f5f0", "#15241f", "#5a6b64", "#0e7c7b", "#c8892b", "#b4472f", "#c9d2cc"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": DARK})

go = {"geometry": camada("limite_estadual")[0]["geometry"]}
go_geom = shape(go["geometry"])
piv = camada("pivos_2020_2023_final"); sm = camada("Area_Irrigada_Bacia_Sao_Marcos")
bc = camada("bacias_criticas"); og = camada("vw_usos_outorgados_publico_cql")
og_pts = [(float(f["properties"]["int_longitude"]), float(f["properties"]["int_latitude"]))
          for f in og if f["properties"].get("int_longitude")]

def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon": return [c[0]]
    if t == "MultiPolygon": return [p[0] for p in c]
    return []

def draw_outline(ax, geom, **kw):
    for r in rings(geom):
        xs, ys = zip(*r); ax.plot(xs, ys, **kw)

def fig(w=16, h=9):
    f, ax = plt.subplots(figsize=(w, h), dpi=110)
    f.patch.set_facecolor(BG); ax.set_facecolor(BG); ax.set_aspect("equal"); ax.axis("off")
    return f, ax

def save(f, name):
    f.savefig(os.path.join(OUT, name), facecolor=BG, bbox_inches="tight", pad_inches=0.25); plt.close(f)
    print("ok", name)

def cen(geom):
    s = shape(geom); p = s.representative_point() if not s.is_valid else s.centroid
    return p.x, p.y

# 5. Satélite: Sentinel-2 na seca (agosto de 2025), cor natural e NDVI
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "figs/1.0"}), timeout=120) as r:
        return json.loads(r.read().decode())
bb = (-47.70, -16.50, -47.58, -16.38)
items = get(f"{STAC}/search?collections=sentinel-2-l2a&bbox={','.join(map(str, bb))}&datetime=2025-08-01/2025-08-31&limit=20")["features"]
best = min(items, key=lambda x: x["properties"].get("eo:cloud_cover", 100))
print("cena", best["id"], best["properties"]["datetime"], best["properties"]["eo:cloud_cover"])
bands = {}
for b in ("B02", "B03", "B04", "B08"):
    href = get(SAS + "?href=" + urllib.parse.quote(best["assets"][b]["href"], safe=""))["href"]
    with rasterio.open(href) as ds:
        w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *bb, densify_pts=21), transform=ds.transform)
        bands[b] = ds.read(1, window=w, out_shape=(1100, 1100)).astype("float32") - 1000.0
rgb = np.dstack([bands["B04"], bands["B03"], bands["B02"]])
lo, hi = np.percentile(rgb, 2), np.percentile(rgb, 98)
rgb = np.clip((rgb - lo) / (hi - lo), 0, 1) ** 0.8
nd = (bands["B08"] - bands["B04"]) / (bands["B08"] + bands["B04"] + 1e-6)
ext = (bb[0], bb[2], bb[1], bb[3])
pv_here = []
for p in piv:
    for r in rings(p["geometry"]):
        if bb[0] < r[0][0] < bb[2] and bb[1] < r[0][1] < bb[3]: pv_here.append(r)
for name, img, kw in [("5a_satelite_cor.png", rgb, {}), ("5b_satelite_ndvi.png", nd, {"cmap": "RdYlGn", "vmin": 0.0, "vmax": 0.85})]:
    f, ax = plt.subplots(figsize=(9, 9), dpi=120); f.patch.set_facecolor(BG); ax.axis("off")
    ax.imshow(img, extent=ext, origin="upper", **kw)
    for r in pv_here:
        xs, ys = zip(*r); ax.plot(xs, ys, color="#ffffff", lw=1.1, alpha=0.9)
    ax.set_xlim(bb[0], bb[2]); ax.set_ylim(bb[1], bb[3]); ax.set_aspect(1 / math.cos(math.radians(16.44)))
    save(f, name)
# NDVI por pivô dentro da janela
from rasterio.transform import from_bounds as tfb
T = tfb(*bb, nd.shape[1], nd.shape[0])
from rasterio.features import geometry_mask
vals = []
for r in pv_here:
    m = ~geometry_mask([{"type": "Polygon", "coordinates": [r]}], out_shape=nd.shape, transform=T)
    if m.sum() > 20: vals.append(float(nd[m].mean()))
vals = np.array(vals)
print("pivos na janela", len(vals), "NDVI>0.6:", int((vals > 0.6).sum()), "NDVI<0.35:", int((vals < 0.35).sum()),
      "entorno mediana", round(float(np.median(nd)), 2))
