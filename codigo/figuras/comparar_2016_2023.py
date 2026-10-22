"""
Compara o mapa de pivôs de 2016 com o de 2023 (SEMAD-GO) e com a área irrigada do MapBiomas 2020.

Mede quantos pivôs de 2016 continuam no mesmo lugar, quantos são novos e quanto o MapBiomas cobre.
Áreas em projeção cônica equivalente (Albers), só dentro de Goiás.
Uso:  python comparar_2016_2023.py
"""
import json, os, sys
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid
from pyproj import Transformer
T = Transformer.from_crs(4326, "+proj=aea +lat_1=-12 +lat_2=-18 +lat_0=-15 +lon_0=-49 +ellps=GRS80 +units=m", always_xy=True).transform  # Albers equivalente (m)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dados import camada
def load(nome):
    out = []
    for x in camada(nome):
        if x["geometry"]: out.append(make_valid(transform(T, shape(x["geometry"]))).buffer(0))
    return out
go = load("limite_estadual")[0]
p16 = [g for g in load("Pivos_2016") if go.contains(g.centroid)]
p23 = [g for g in load("pivos_2020_2023_final") if go.contains(g.centroid)]
mb20 = [g for g in load("area_irrigada_2020") if go.intersects(g)]
print("GO: 2016", len(p16), round(sum(g.area for g in p16)/1e4), "ha | 2023", len(p23), round(sum(g.area for g in p23)/1e4), "ha")
def match(a, b, thr=0.5):
    t = STRtree(b); n = 0
    for g in a:
        if any(g.intersection(b[i]).area / g.area >= thr for i in t.query(g)): n += 1
    return n
m = match(p16, p23); print("pivôs de 2016 que seguem no mapa de 2023 (>=50% sobrepostos):", m, f"{m/len(p16):.0%}")
m2 = match(p23, p16); print("pivôs de 2023 que já existiam em 2016:", m2, f"{m2/len(p23):.0%}")
# mesmo lugar? deslocamento do centro nos pares
t = STRtree(p23); d = []
for g in p16:
    c = [p23[i] for i in t.query(g) if g.intersection(p23[i]).area / g.area >= 0.5]
    if c: d.append(min(g.centroid.distance(x.centroid) for x in c))
d.sort(); print("deslocamento do centro (m): mediana", round(d[len(d)//2]), "p90", round(d[int(len(d)*.9)]))
U = unary_union(mb20)
cov = sum(g.intersection(U).area for g in p23) / sum(g.area for g in p23)
print("MapBiomas 2020: polígonos", len(mb20), "área", round(U.area/1e4), "ha; área dos pivôs SEMAD 2023 coberta:", f"{cov:.0%}")
P = unary_union(p23); print("área MapBiomas 2020 fora dos pivôs SEMAD 2023:", f"{U.difference(P).area/U.area:.0%}")
t16 = STRtree(p16)
novos = [g for g in p23 if not any(g.intersection(p16[i]).area / g.area >= 0.5 for i in t16.query(g))]
print("pivôs novos 2016->2023:", len(novos), round(sum(g.area for g in novos)/1e4), "ha")
