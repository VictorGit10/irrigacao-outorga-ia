"""
Diagnostico do dedup: as 4 camadas de area irrigada se sobrepoem de verdade?
Compara por sobreposicao real de poligonos (shapely STRtree), nao por
coordenada arredondada. Objetivo: mostrar se o mapa estadual e a bacia
Sao Marcos descrevem OS MESMOS pivos (com digitacao levemente diferente).
"""
import json, os, math
from collections import defaultdict
from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE= os.path.join(HERE, ".cache")

def wfs(layer, cql=None, cn=None):
    tag = cn or (layer.split(":")[-1] + ("_cql" if cql else ""))
    return json.load(open(os.path.join(CACHE, tag + ".json"), encoding="utf-8"))

def num(v):
    try: return float(v)
    except: return 0.0

CAMADAS = [
    ("geonode:pivos_2020_2023_final",           "id_2",      "Mapa estadual"),
    ("geonode:Area_Irrigada_Bacia_Sao_Marcos",  "Cod_Empree", "Bacia S. Marcos"),
    ("geonode:pivos_alto_sao_marcos",           "cod_areair", "Alto S. Marcos"),
    ("geonode:areas_irrigadas_alto_meia_ponte", "id",         "Alto Meia Ponte"),
]

geoms = []   # (geom, area_attr, camada, id, lat, lon)
for lay, keyc, nome in CAMADAS:
    for f in wfs(lay):
        g = f.get("geometry")
        if not g: continue
        p = f["properties"]
        try: sg = shape(g)
        except Exception: continue
        if sg.is_empty: continue
        ar = num(p.get("Area") or p.get("area_ha") or p.get("area"))
        la = num(p.get("Latitude_c") or p.get("latitude_c"))
        lo = num(p.get("Longitude_") or p.get("longitude_"))
        if not (la and lo):
            c = sg.representative_point(); lo, la = c.x, c.y
        geoms.append((sg, ar, nome, str(p.get(keyc)), la, lo))

print(f"total de poligonos brutos: {len(geoms):,}")

# area total bruta por camada
tot = defaultdict(lambda: [0, 0.0])
for sg, ar, nome, _id, la, lo in geoms:
    tot[nome][0] += 1; tot[nome][1] += sg.area
print("\narea bruta por camada (EPSG:4674, graus^2 -> nao comparar direto com ha):")
for k, v in tot.items(): print(f"  {k:18s} {v[0]:>6,} poligonos")

# ---- sobreposicao real entre camadas
tree = STRtree([g[0] for g in geoms])
print("\nsobreposicao por PAR DE CAMADAS (IoU do centroide dentro do outro):")
pares = defaultdict(lambda: [0, 0, 0])   # n, sobrepostos, area_duplicada
for i, (sg, ar, nome, _id, la, lo) in enumerate(geoms):
    # ponto representativo do pivo
    pt = sg.representative_point()
    for j in tree.query(sg):
        if j <= i: continue
        sg2, ar2, nome2, _id2, la2, lo2 = geoms[j]
        if nome == nome2: continue
        # um centroide esta dentro do outro?
        if sg2.contains(pt) or sg.contains(sg2.representative_point()):
            k = tuple(sorted((nome, nome2)))
            pares[k][0] += 1
            pares[k][1] += 1
            pares[k][2] += min(ar, ar2)
for k, v in sorted(pares.items(), key=lambda x: -x[1][2]):
    print(f"  {k[0][:18]:18s} x {k[1][:18]:18s} {v[1]:>5,} pares  area duplicada ~{v[2]:>11,.1f} ha")

# ---- dedup correto: uniao geometrica
print("\nDEDUP CORRETO (uniao geometrica, area computada da geometria):")
uniao = unary_union([g[0] for g in geoms])
print(f"  area da uniao: {uniao.area:.6f} graus2")
print(f"  soma das areas: {sum(g[0].area for g in geoms):.6f} graus2")
print(f"  reducao: {100*(1-uniao.area/sum(g[0].area for g in geoms)):.1f}%")

# area por municipio via uniao, so para checar Cristalina
muns = wfs("geonode:municipio2022", cn="municipio2022")
print("\n  checagem por municipio (uniao vs soma bruta):")
mgeom = []
for f in muns:
    p = f["properties"]; g = f.get("geometry")
    if not g: continue
    mgeom.append((p.get("Nome") or p.get("NM_MUNICIP"), shape(g)))
for nome, mg in mgeom:
    if nome != "Cristalina": continue
    inter = uniao.intersection(mg)
    soma_bruta = sum(g[0].area for g in geoms if mg.contains(g[0].representative_point()))
    n_bruta = sum(1 for g in geoms if mg.contains(g[0].representative_point()))
    print(f"    {nome}:")
    print(f"       soma bruta ......... {n_bruta:>5,} poligonos")
    print(f"       uniao (dedup) ...... {inter.area:.6f} graus2 vs bruta {soma_bruta:.6f} "
          f"({100*(1-inter.area/soma_bruta):.1f}% de sobreposicao)")
