"""Figuras 1 a 4 da apresentação (mapas e esquema), a partir dos dados públicos da SEMAD-GO.

A figura 2 foi refeita depois em figura_cristalina.py (com mapa de localização e legenda).
Uso:  python figuras_apresentacao.py   -> docs/apresentacao/img/
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

# 1. Goiás: pivôs mapeados e bacias críticas
f, ax = fig(9, 9)
draw_outline(ax, go["geometry"], color=DARK, lw=1.4)
patches = [MPoly(r, closed=True) for b in bc for r in rings(b["geometry"])]
ax.add_collection(PatchCollection(patches, facecolor=TEAL, alpha=0.18, edgecolor=TEAL, lw=1.2))
cs = [cen(p["geometry"]) for p in piv]
ax.scatter([c[0] for c in cs], [c[1] for c in cs], s=3, color=OCHRE, alpha=0.8, lw=0)
for b in bc:
    nm = b["properties"]["nome"]
    if nm in ("Meia Ponte", "Rio Vermelho", "Alto São Marcos"):
        c = shape(b["geometry"]).representative_point()
        ax.annotate(nm, (c.x, c.y), fontsize=14, color=TEAL, weight="bold", ha="center",
                    xytext=(0, 0), textcoords="offset points")
save(f, "1_goias_pivos.png")

# 2. Zoom em Cristalina: pivôs (polígonos) e pontos de captação
x0, x1, y0, y1 = -47.75, -47.30, -16.95, -16.60
f, ax = fig(12, 9)
pp = []
for p in piv:
    for r in rings(p["geometry"]):
        if x0 < r[0][0] < x1 and y0 < r[0][1] < y1: pp.append(MPoly(r, closed=True))
ax.add_collection(PatchCollection(pp, facecolor=TEAL, alpha=0.55, edgecolor=TEAL, lw=0.8))
sel = [(x, y) for x, y in og_pts if x0 < x < x1 and y0 < y < y1]
ax.scatter([s[0] for s in sel], [s[1] for s in sel], s=70, marker="^", color=OCHRE, edgecolor=DARK, lw=0.6, zorder=3)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
ax.plot([x1 - 0.12, x1 - 0.12 + 10 / 106.5], [y0 + 0.02] * 2, color=DARK, lw=3)
ax.text(x1 - 0.12 + 5 / 106.5 / 1, y0 + 0.032, "10 km", ha="center", fontsize=14)
print("zoom: pivos", len(pp), "pontos", len(sel))
save(f, "2_cristalina_zoom.png")

# 3. Bacia do São Marcos: dentro e fora de Goiás
f, ax = fig(9, 9)
draw_outline(ax, go["geometry"], color=DARK, lw=1.6)
din, fora = [], []
for p in sm:
    for r in rings(p["geometry"]):
        (din if go_geom.contains(Point(r[0][0], r[0][1])) else fora).append(MPoly(r, closed=True))
ax.add_collection(PatchCollection(din, facecolor=TEAL, alpha=0.7, edgecolor=TEAL, lw=0.5))
ax.add_collection(PatchCollection(fora, facecolor=RED, alpha=0.75, edgecolor=RED, lw=0.5))
allx = [r[0][0] for p in sm for r in rings(p["geometry"])]; ally = [r[0][1] for p in sm for r in rings(p["geometry"])]
ax.set_xlim(min(allx) - 0.1, max(allx) + 0.1); ax.set_ylim(min(ally) - 0.1, max(ally) + 0.1)
print("sao marcos dentro", len(din), "fora", len(fora))
save(f, "3_sao_marcos_fora.png")

# 4. Esquema: a regra "qualquer outorga rio acima"
f, ax = plt.subplots(figsize=(14, 8), dpi=110); f.patch.set_facecolor(BG); ax.set_facecolor(BG); ax.axis("off")
ax.set_xlim(0, 14); ax.set_ylim(0, 8)
main = [(1, 7.2), (4, 6.0), (7, 4.6), (10, 3.2), (13, 1.2)]
ax.plot(*zip(*main), color=TEAL, lw=7, solid_capstyle="round")
tribs = [[(2, 3.8), (4, 6.0)], [(5.5, 7.6), (7, 4.6)], [(6.5, 1.6), (10, 3.2)], [(1.2, 5.2), (2, 3.8)], [(8.6, 7.4), (10, 3.2)]]
for t in tribs: ax.plot(*zip(*t), color=TEAL, lw=3.5, alpha=0.7, solid_capstyle="round")
ups = [(2.3, 6.8), (3.2, 5.0), (5.9, 6.6), (6.0, 5.3), (7.8, 5.4), (8.9, 6.4), (8.0, 2.4), (9.0, 4.0)]
ax.scatter(*zip(*ups), marker="^", s=170, color=OCHRE, edgecolor=DARK, zorder=4)
for (x, y, lab, ok) in [(1.35, 5.0, "Pivô na cabeceira", False), (11.6, 2.6, "Pivô rio abaixo", True)]:
    ax.add_patch(plt.Circle((x, y), 0.42, color=(RED if not ok else TEAL), alpha=0.9, zorder=5))
    ax.text(x, y - 0.85, lab, ha="center", fontsize=16, weight="bold")
save(f, "4_regra_rio_acima.png")
