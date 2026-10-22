"""Figura 2 da apresentação: recorte de Cristalina com pivôs, pontos de captação, mapa de localização e legenda.

Uso:  python figura_cristalina.py   -> docs/apresentacao/img/2_cristalina_zoom_v2.png
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from dados import camada
BG, DARK, TEAL, OCHRE = "#f3f5f0", "#15241f", "#0e7c7b", "#c8892b"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": DARK})

def rings(g):
    t, c = g["type"], g["coordinates"]
    return [c[0]] if t == "Polygon" else [p[0] for p in c] if t == "MultiPolygon" else []

go_g = camada("limite_estadual")[0]["geometry"]
piv = camada("pivos_2020_2023_final"); og = camada("vw_usos_outorgados_publico_cql")
og_pts = [(float(f["properties"]["int_longitude"]), float(f["properties"]["int_latitude"]))
          for f in og if f["properties"].get("int_longitude")]

x0, x1, y0, y1 = -47.75, -47.30, -16.95, -16.60
f = plt.figure(figsize=(15, 9.6), dpi=110)
ax = f.add_axes([0.0, 0.0, 0.70, 1.0])
f.patch.set_facecolor(BG); ax.set_facecolor("#fbfcfa"); ax.set_aspect("equal")
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values(): s.set_color("#c9d2cc")
pp = [MPoly(r, closed=True) for p in piv for r in rings(p["geometry"])
      if x0 < r[0][0] < x1 and y0 < r[0][1] < y1]
ax.add_collection(PatchCollection(pp, facecolor=TEAL, alpha=0.55, edgecolor=TEAL, lw=0.8))
sel = [(x, y) for x, y in og_pts if x0 < x < x1 and y0 < y < y1]
ax.scatter([s[0] for s in sel], [s[1] for s in sel], s=70, marker="^", color=OCHRE, edgecolor=DARK, lw=0.6, zorder=3)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
ax.plot([x1 - 0.13, x1 - 0.13 + 10 / 106.5], [y0 + 0.02] * 2, color=DARK, lw=3)
ax.text(x1 - 0.13 + 5 / 106.5, y0 + 0.03, "10 km", ha="center", fontsize=14)
f.legend(handles=[
    Line2D([], [], marker="o", ls="", ms=16, mfc=TEAL, mec=TEAL, alpha=0.6, label="Pivô\n(mapa da SEMAD,\nimagens de 2020–2023)"),
    Line2D([], [], marker="^", ls="", ms=13, mfc=OCHRE, mec=DARK, label="Captação outorgada\npara irrigação")],
    loc="upper left", bbox_to_anchor=(0.725, 0.50), fontsize=15, frameon=False, labelspacing=1.2, handletextpad=0.6)
# mapa de localização: Goiás e o recorte
ia = f.add_axes([0.73, 0.55, 0.26, 0.42])
ia.set_aspect("equal"); ia.axis("off"); ia.patch.set_alpha(0)
for r in rings(go_g):
    ia.fill(*zip(*r), facecolor="#e4e9e3", edgecolor=DARK, lw=1)
ia.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="#b4472f", lw=2.2))
ia.text(-49.8, -15.6, "Goiás", fontsize=13, weight="bold", ha="center", color="#4f5f58")
print("pivos", len(pp), "pontos", len(sel))
f.savefig(os.path.join(D, "..", "..", "docs", "apresentacao", "img", "2_cristalina_zoom_v2.png"), facecolor=BG, bbox_inches="tight", pad_inches=0.2)
