"""
TESTE: a deteccao por NDVI de uma unica data separa mal pivo de nao-pivo.
A serie temporal separa bem melhor.

Medido num recorte de 31 x 20 km entre Campo Alegre de Goias e Catalao
(BBOX abaixo), maio a outubro de 2025, Sentinel-2 L2A
via Planetary Computer, 20 pivos CONHECIDOS (camada publica) vs 150 areas de
referencia fora de qualquer pivo.

RESULTADOS
  NDVI de UMA data (agosto/2025, a "epoca de seca" citada no pedido):
    pivos 0,256 | refs 0,240 | separacao +0,016 | AUC 0,443  -> NAO separa
    (p25 do max do NDVI na janela: AUC 0,667 - fraco)
  Serie temporal (4-6 cenas limpas, maio-outubro/2025):
    metrica     AUC     pivos    refs
    max         0,813   0,592    0,428
    amp         0,825   0,418    0,188
    std         0,840   0,170    0,071   <-- melhor
    p75         0,667   0,458    0,348
    mean        0,625   0,341    0,301

  Por mes (AUC da separacao NDVI):
    maio +0,047 AUC 0,626 | jun +0,049 AUC 0,499 | jul +0,068 AUC 0,520
    ago +0,016 AUC 0,443

LEITURA
  1. "verde na seca" como LIMIAR UNICO nao funciona: o cerrado nativo tambem
     fica verde (e mais verde que o pivo em agosto, quando a soja de 1a
     safra ja foi colhida e o pivo esta em rotacao).
  2. O que separa e a DINAMICA: a amplitude e o desvio-padrao da serie.
     Um pivo irriga na seca -> a serie tem pico na seca e vale na cheia.
     Vegetação natural tem ciclo invertido.
  3. E por isso que a literatura usa metricas fenologicas + Random Forest
     (Bendini et al. 2019), e nao um limiar de NDVI.

CONSEQUENCIA PARA O PROJETO
  - A deteccao (o gargalo do pedido) parece automatizavel, mas exige serie temporal
    (>=4 cenas limpas por ano) e classificador, nao regra.
  - "Rodar na epoca de seca" e a JANELA de coleta, mas nao o criterio.

RESSALVAS (teste preliminar, vale refazer)
  - conta por pixel, nao por pivo;
  - NAO desconta o deslocamento de +1000 do Sentinel-2 (baseline >= 04.00);
    ver aux_imagens_fila.py para a forma correta;
  - um recorte so, com 20 pivos.

Uso:  python aux_deteccao_temporal.py
"""
import json, os, math, time, urllib.request, urllib.parse
import numpy as np, rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from shapely.geometry import shape, box as sbox
from shapely.ops import unary_union
from rasterio.features import rasterize

HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, ".cache")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS  = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

def out(*t): print(*t, flush=True)
def http_json(url, tries=6, pause=4.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deteccao/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause * (i + 1))
    raise last
_sas = {}
def sign(h):
    if h not in _sas:
        _sas[h] = http_json(SAS + "?href=" + urllib.parse.quote(h, safe=""))["href"]; time.sleep(0.6)
    return _sas[h]

BBOX = (-47.72, -17.60, -47.44, -17.42); N = 700
d = json.load(open(os.path.join(CACHE, "pivos_2020_2023_final.json"), encoding="utf-8"))
janela = sbox(*BBOX)
pub = [shape(f["geometry"]) for f in d if f.get("geometry") and janela.intersects(shape(f["geometry"]))]
tr = rasterio.transform.from_bounds(*BBOX, N, N)
px_m = 111320 * (BBOX[2] - BBOX[0]) / N
pu = unary_union(pub)
import random; random.seed(0); refs = []
for i in range(3000):
    x = random.uniform(BBOX[0], BBOX[2]); y = random.uniform(BBOX[1], BBOX[3])
    p = shape({"type": "Point", "coordinates": (x, y)})
    if pu.buffer(0.003).contains(p): continue
    refs.append(p.buffer(0.0025))
    if len(refs) >= 150: break
mp = np.zeros((N, N), dtype=bool); mr = np.zeros((N, N), dtype=bool)
for g in pub: mp |= rasterize([(g, 1)], out_shape=(N, N), transform=tr, fill=0, dtype="uint8").astype(bool)
for g in refs: mr |= rasterize([(g, 1)], out_shape=(N, N), transform=tr, fill=0, dtype="uint8").astype(bool)
out(f"janela {abs(BBOX[2]-BBOX[0])*111:.0f} x {abs(BBOX[3]-BBOX[1])*111:.0f} km | px {px_m:.0f} m")
out(f"pivos conhecidos: {len(pub)} | areas de referencia: {len(refs)}")

u = (f"{STAC}/search?collections=sentinel-2-l2a&bbox={BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}"
     f"&datetime=2025-05-01/2025-10-15&maxRecords=200")
sc = http_json(u).get("features", [])
por_mes = {}
for f in sc:
    dt = f["properties"].get("datetime", "")[:7]; cc = f["properties"].get("eo:cloud_cover", 100)
    if dt not in por_mes or cc < por_mes[dt][1]: por_mes[dt] = (f, cc)
meses = sorted(por_mes)

def ndvi_da_cena(item):
    arrs = {}
    for b in ("B04", "B08"):
        with rasterio.open(sign(item["assets"][b]["href"])) as ds:
            w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *BBOX, densify_pts=21),
                            transform=ds.transform)
            arrs[b] = ds.read(1, window=w, out_shape=(N, N), resampling=Resampling.bilinear,
                              boundless=True, fill_value=0).astype("float32")
    red, nir = arrs["B04"], arrs["B08"]
    return np.where((red + nir) > 0, (nir - red) / (nir + red + 1e-6), np.nan), (red > 0) & (nir > 0)

def auc_of(pv, rf):
    pv = np.nan_to_num(pv, nan=-9); rf = np.nan_to_num(rf, nan=-9)
    a = np.concatenate([pv, rf]); lab = np.concatenate([np.ones(len(pv)), np.zeros(len(rf))])
    o = np.argsort(a); r = np.empty(len(a)); r[o] = np.arange(1, len(a) + 1)
    return (r[lab == 1].sum() - len(pv) * (len(pv) + 1) / 2) / (len(pv) * len(rf))

out("\n" + "=" * 74)
out("A) UMA DATA DE SECA (agosto/2025) SEPARA?")
out("=" * 74)
serie = []
for m in meses:
    item, cc = por_mes[m]
    try: ndvi, valid = ndvi_da_cena(item)
    except Exception: continue
    serie.append((m, ndvi, valid))
    pv = ndvi[mp & valid]; rf = ndvi[mr & valid]
    if pv.size < 20 or rf.size < 20: continue
    out(f"  {m}  nuvem {cc:>5.2f}%  pivos {np.nanmean(pv):+.3f}  refs {np.nanmean(rf):+.3f}  "
        f"separacao {np.nanmean(pv)-np.nanmean(rf):+.3f}  AUC {auc_of(pv, rf):.3f}")

out("\n" + "=" * 74)
out("B) SERIE TEMPORAL: metricas fenologicas")
out("=" * 74)
if len(serie) >= 3:
    stack = np.stack([s[1] for s in serie]); vst = np.stack([s[2] for s in serie])
    def feat(mask):
        v = np.where(mask[None, :] & vst, stack, np.nan)
        return {"max": np.nanmax(v, 0), "p75": np.nanpercentile(v, 75, axis=0),
                "mean": np.nanmean(v, 0), "std": np.nanstd(v, 0),
                "amp": np.nanmax(v, 0) - np.nanmin(v, 0)}
    F = feat(mp); R = feat(mr)
    ap = mp & vst.any(0); ar = mr & vst.any(0)
    out(f"  {'metrica':>6} {'AUC':>8} {'med_pivos':>10} {'med_refs':>9}")
    for k in F:
        out(f"  {k:>6} {auc_of(F[k][ap], R[k][ar]):>8.3f} "
            f"{np.nanmedian(F[k][ap]):>10.3f} {np.nanmedian(R[k][ar]):>9.3f}")
    out("\n  (AUC 0.5 = sem separacao; >0.7 utilizavel; >0.85 forte)")
    out("\n  CONCLUSAO: o que separa pivo de vegetacao natural nao e o nivel de")
    out("  NDVI, e a DINAMICA da serie (amplitude e desvio-padrao). Um pivo")
    out("  irriga na seca; a vegetacao natural faz o contrario. Por isso a")
    out("  literatura usa metricas fenologicas + classificador, e nao limiar.")
out("\nFIM")
