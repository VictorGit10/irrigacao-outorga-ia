"""
Gera a fila de revisao do prototipo: areas de NIVEL C (pivo mapeado, sem
outorga localizavel por este metodo), com par de imagens 2022/2025.

Por que nivel C e nao "pivo novo":
  - o nivel C e MEDIDO e defensavel: o pivo existe na camada, o metodo nao
    achou outorga compativel;
  - o detector de pivo NOVO nao se mostrou confiavel (aux_teste_mudanca.py:
    AUC 0,458 no salto de NDVI 2022->2025), e nao vou inventar uma fila que
    parece funcionar.

O que este arquivo demonstra: o CICLO. candidato -> imagem antes/depois ->
triagem humana -> relatorio estruturado. A peca de deteccao entra no mesmo
lugar da fila quando tiver rotulo suficiente.

Saida: saida/fila_revisao.json + saida/chips/<id>_<ano>.png
"""
import json, os, math, time, urllib.request, urllib.parse, pickle
from collections import defaultdict
import numpy as np, rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.features import rasterize
from shapely.geometry import shape, Point, box as sbox
from shapely.strtree import STRtree
from shapely.ops import unary_union
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
SAIDA = os.path.join(HERE, "saida")
CHIPS = os.path.join(SAIDA, "chips")
os.makedirs(CHIPS, exist_ok=True)

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS  = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
RAIO_A_KM, RAIO_B_KM, TOL_AREA = 5.0, 15.0, 0.5

def out(*t): print(*t, flush=True)

def http_json(url, tries=6, pause=3.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fila/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause * (i + 1))
    raise last

_sas = {}
def sign(h):
    if h not in _sas:
        _sas[h] = http_json(SAS + "?href=" + urllib.parse.quote(h, safe=""))["href"]; time.sleep(0.3)
    return _sas[h]

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0

def hav(lo1, la1, lo2, la2):
    R = 6371.0; p1, p2 = math.radians(la1), math.radians(la2)
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(a))

def cache(nome):
    p = os.path.join(CACHE, nome + ".json")
    if not os.path.exists(p): raise SystemExit(f"falta o cache {p} - rode demo_reconciliacao.py antes")
    return json.load(open(p, encoding="utf-8"))

# ---------------------------------------------------------------- R1/R2
out("1) areas irrigadas + dedup")
GO = shape(cache("limite_estadual")[0]["geometry"])
CAMADAS = [
    ("pivos_2020_2023_final",          "id_2",       "Mapa estadual"),
    ("Area_Irrigada_Bacia_Sao_Marcos", "Cod_Empree", "Bacia Sao Marcos"),
    ("pivos_alto_sao_marcos",          "cod_areair", "Alto Sao Marcos"),
    ("areas_irrigadas_alto_meia_ponte","id",         "Alto Meia Ponte"),
]
brutos = []
for lay, keyc, nome in CAMADAS:
    for f in cache(lay):
        g = f.get("geometry")
        if not g: continue
        p = f["properties"]; sg = shape(g)
        if sg.is_empty: continue
        la = num(p.get("Latitude_c") or p.get("latitude_c"))
        lo = num(p.get("Longitude_") or p.get("longitude_"))
        if not (la and lo):
            rp = sg.representative_point(); lo, la = rp.x, rp.y
        ar = num(p.get("Area") or p.get("area_ha") or p.get("area"))
        if not (GO.contains(Point(lo, la)) or GO.intersects(sg)): continue
        brutos.append(dict(geom=sg, area=ar, camada=nome, id=str(p.get(keyc)),
                           lo=lo, la=la))
arvore = STRtree([b["geom"] for b in brutos])
vistos = set(); pivos = []
for i, b in enumerate(brutos):
    if i in vistos: continue
    b["camadas"] = [b["camada"]]; pivos.append(b)
    for j in arvore.query(b["geom"]):
        if j == i or j in vistos: continue
        if brutos[j]["geom"].contains(b["geom"].representative_point()) or \
           b["geom"].contains(brutos[j]["geom"].representative_point()):
            vistos.add(j); b["camadas"].append(brutos[j]["camada"])
out(f"   {len(brutos):,} poligonos -> {len(pivos):,} areas unicas")

muns = []
for f in cache("municipio2022"):
    p = f["properties"]; g = f.get("geometry")
    if g: muns.append((str(p.get("Nome") or p.get("NM_MUNICIP")), shape(g)))
mtree = STRtree([m[1] for m in muns])
for p in pivos:
    nome = ""
    for j in mtree.query(p["geom"]):
        if muns[j][1].contains(p["geom"].representative_point()):
            nome = muns[j][0]; break
    p["mun"] = nome or "(sem mun.)"

# ---------------------------------------------------------------- R3/R4
out("2) atos + sub-bacia + niveis")
og = cache("vw_usos_outorgados_publico_cql")
atos = []
for f in og:
    p = f["properties"]
    lo = num(p.get("int_longitude")); la = num(p.get("int_latitude"))
    dom = str(p.get("bho_dedominial") or "").strip().upper()
    dom = "FEDERAL" if dom.startswith("FED") else ("ESTADUAL" if dom.startswith("EST") else "NAO_CLASS")
    atos.append(dict(lo=lo, la=la, ar=num(p.get("sir_ar_irrigada")),
                     sit=p.get("int_sit_uso"), tipo=str(p.get("int_ds") or ""),
                     num=str(p.get("int_nu_ato") or ""), dom=dom,
                     cob=str(p.get("bho_cobacia") or ""), mun=str(p.get("municipio") or "")))
atos_est = [a for a in atos if a["dom"] == "ESTADUAL"]

trechos = pickle.load(open(os.path.join(CACHE, "bho_trechos.pkl"), "rb"))
grid = defaultdict(list)
for i, t in enumerate(trechos): grid[(round(t[5],1), round(t[6],1))].append(i)
def trecho_do_ponto(lo, la):
    best, bi = 1e18, None
    for dx in (-1,-0.5,0,0.5,1):
        for dy in (-1,-0.5,0,0.5,1):
            for i in grid.get((round(lo+dx,1), round(la+dy,1)), []):
                t = trechos[i]; dd = (t[5]-lo)**2 + (t[6]-la)**2
                if dd < best: best, bi = dd, i
    return trechos[bi] if bi is not None else None

atos_por_cob = defaultdict(list)
for a in atos_est:
    if a["cob"] and a["lo"]: atos_por_cob[a["cob"]].append(a)

for p in pivos:
    t = trecho_do_ponto(p["lo"], p["la"])
    p["cob"] = t[0] if t else ""
    p["dom_pivo"] = t[3] if t else ""
    p["nivel"] = "C"; p["d"] = None; p["ato"] = None
    if not p["cob"]: continue
    cand = atos_por_cob.get(p["cob"], [])
    if not cand: continue
    d, a = min(((hav(p["lo"], p["la"], x["lo"], x["la"]), x) for x in cand), key=lambda z: z[0])
    p["d"] = d; p["ato"] = a
    if d > RAIO_B_KM: p["nivel"] = "C"
    elif a["ar"] > 0 and a["ar"] < p["area"] * TOL_AREA: p["nivel"] = "C"
    elif d <= RAIO_A_KM: p["nivel"] = "A"
    else: p["nivel"] = "B"
for k in ("A", "B", "C"):
    sel = [p for p in pivos if p["nivel"] == k]
    out(f"   nivel {k}: {len(sel):,} areas | {sum(p['area'] for p in sel):,.0f} ha")

# ---------------------------------------------------------------- selecao
out("3) selecionando a fila (nivel C, dominio estadual, >= 60 ha)")
cand_c = [p for p in pivos if p["nivel"] == "C"
          and not str(p["dom_pivo"]).lower().startswith("fed") and p["area"] >= 60]
por_mun = defaultdict(list)
for p in cand_c: por_mun[p["mun"]].append(p)
for m in por_mun: por_mun[m].sort(key=lambda x: -x["area"])
escolhidos, ordem = [], sorted(por_mun, key=lambda m: -sum(x["area"] for x in por_mun[m]))
k = 0
while len(escolhidos) < 18 and any(por_mun.values()):
    m = ordem[k % len(ordem)]
    if por_mun[m]:
        escolhidos.append(por_mun[m].pop(0))
    k += 1
    if k > 400: break
out(f"   {len(escolhidos)} areas em {len(set(p['mun'] for p in escolhidos))} municipios")

# ---------------------------------------------------------------- chips
def chip(ano, bb, px=420):
    u = (f"{STAC}/search?collections=sentinel-2-l2a&bbox={bb[0]},{bb[1]},{bb[2]},{bb[3]}"
         f"&datetime={ano}-07-20/{ano}-09-30&limit=40")
    sc = http_json(u).get("features", [])
    if not sc: return None
    best = min(sc, key=lambda x: x["properties"].get("eo:cloud_cover", 100))
    bands = []
    for b in ("B04", "B03", "B02"):
        with rasterio.open(sign(best["assets"][b]["href"])) as ds:
            w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *bb, densify_pts=21),
                            transform=ds.transform)
            bands.append(ds.read(1, window=w, out_shape=(px, px), resampling=Resampling.average,
                                 boundless=True, fill_value=0).astype("float32"))
    rgb = np.dstack(bands); im = np.zeros_like(rgb, dtype="uint8")
    for c in range(3):
        v = rgb[:, :, c]; ok = v > 0
        if ok.sum() < 10: return None
        lo, hi = np.percentile(v[ok], 2), np.percentile(v[ok], 98)
        if hi <= lo: hi = lo + 1
        im[:, :, c] = np.clip((v - lo) / (hi - lo) * 255, 0, 255).astype("uint8")
    return Image.fromarray(im)

fila = []
out("4) baixando imagens e montando a fila")
for i, p in enumerate(escolhidos):
    cid = f"C-{i+1:02d}"
    # janela que contem o poligono inteiro
    minx, miny, maxx, maxy = p["geom"].bounds
    cx, cy = (minx+maxx)/2, (miny+maxy)/2
    lado = max(maxx-minx, maxy-miny)/2 * 1.9 + 0.006
    bb = (cx-lado, cy-lado, cx+lado, cy+lado)
    arq = {}
    ok = True
    for ano in (2022, 2025):
        img = chip(ano, bb)
        if img is None: ok = False; break
        dr = ImageDraw.Draw(img)
        ctr = rasterio.transform.from_bounds(*bb, 420, 420)
        rings = [p["geom"].exterior.coords] if p["geom"].geom_type == "Polygon" else \
                [g.exterior.coords for g in p["geom"].geoms]
        for ring in rings:
            pts = [tuple(~ctr * (x, y)) for x, y in ring]
            if len(pts) > 2: dr.line(pts, fill=(255, 214, 0), width=3)
        nome = f"{cid}_{ano}.png"; img.save(os.path.join(CHIPS, nome), optimize=True)
        arq[ano] = nome
    if not ok: out(f"   {cid}: sem par de imagens, descartado"); continue
    a = p["ato"]
    fila.append(dict(
        id=cid, tipo="R",
        lon=round(p["lo"], 6), lat=round(p["la"], 6),
        area_ha=round(p["area"], 1), municipio=p["mun"],
        subbacia=p["cob"], camadas=", ".join(p["camadas"]),
        ato_num=a["num"] if a else "", ato_tipo=(a["tipo"] if a else ""),
        ato_sit=(a["sit"] if a else ""), ato_mun=(a["mun"] if a else ""),
        ato_km=round(p["d"], 1) if p["d"] is not None else None,
        chip_2022=arq[2022], chip_2025=arq[2025],
    ))
    out(f"   {cid} {p['mun'][:22]:22s} {p['area']:>7.1f} ha  ato a {p['d'] if p['d'] else '-'} km")

meta = dict(
    gerado_em=time.strftime("%Y-%m-%d %H:%M"),
    n=len(fila),
    tipo="reconciliacao",
    nota="Areas de nivel C: o pivo existe na camada publica, mas o metodo nao "
         "localizou outorga compativel. Nao significa 'sem outorga'.",
)
json.dump(dict(meta=meta, itens=fila),
          open(os.path.join(SAIDA, "fila_revisao.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
out(f"\nFILA: {len(fila)} itens -> saida/fila_revisao.json")
