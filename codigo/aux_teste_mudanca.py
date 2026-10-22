"""
TESTE: deteccao por MUDANCA (nao por limiar).

A ideia do DETER/INPE nao e classificar "isto e floresta", e sim detectar
"isto MUDOU em relacao ao que era". Aplicado a pivo:

  para cada pixel, compara o NDVI de seca de 2022 com o de 2025.
  pivo instalado entre 2022 e 2025 -> salto grande e positivo na seca.
  pivo que ja existia -> delta ~ 0.
  vegetacao natural -> delta ~ 0 (ou negativo).

Isso resolve o problema do limiar unico (AUC 0,44): nao perguntamos
"quao verde esta?", perguntamos "quanto ficou mais verde do que era?".

Mede: separa o delta os pivos conhecidos das areas de referencia?
E: aparecem deltas grandes FORA da camada publica (= pivo novo)?
"""
import json, os, math, time, urllib.request, urllib.parse
import numpy as np, rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from shapely.geometry import shape, box as sbox
from shapely.ops import unary_union
from rasterio.features import rasterize
from scipy.ndimage import uniform_filter, label

HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, ".cache")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS  = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
def out(*t): print(*t, flush=True)
def http_json(url, tries=6, pause=4.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "delta/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause * (i + 1))
    raise last
_sas = {}
def sign(h):
    if h not in _sas:
        _sas[h] = http_json(SAS + "?href=" + urllib.parse.quote(h, safe=""))["href"]; time.sleep(0.4)
    return _sas[h]

BBOX = (-47.72, -17.60, -47.44, -17.42); N = 700

def ndvi_sazonal(ano):
    """NDVI de seca (ago/set) do ano pedido."""
    u = (f"{STAC}/search?collections=sentinel-2-l2a&bbox={BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}"
         f"&datetime={ano}-07-20/{ano}-09-30&limit=30")
    sc = http_json(u).get("features", [])
    if not sc: return None, None
    best = min(sc, key=lambda x: x["properties"].get("eo:cloud_cover", 100))
    arrs = {}
    for b in ("B04", "B08"):
        with rasterio.open(sign(best["assets"][b]["href"])) as ds:
            w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *BBOX, densify_pts=21),
                            transform=ds.transform)
            arrs[b] = ds.read(1, window=w, out_shape=(N, N), resampling=Resampling.bilinear,
                              boundless=True, fill_value=0).astype("float32")
    red, nir = arrs["B04"], arrs["B08"]
    nd = np.where((red + nir) > 0, (nir - red) / (nir + red + 1e-6), np.nan)
    ok = (red > 0) & (nir > 0) & (nd > -1) & (nd < 1)
    out(f"  {ano}: cena {best['id'][:38]} nuvem {best['properties'].get('eo:cloud_cover',0):.3f}%")
    return nd, ok

out("1) NDVI de seca em dois anos")
nd22, ok22 = ndvi_sazonal(2022)
nd25, ok25 = ndvi_sazonal(2025)
if nd22 is None or nd25 is None: raise SystemExit("sem cena")
val = ok22 & ok25
delta = nd25 - nd22
out(f"   pixels comparaveis: {val.sum():,}/{N*N:,}")

# ---- amostras rotuladas pela camada publica
d = json.load(open(os.path.join(CACHE, "pivos_2020_2023_final.json"), encoding="utf-8"))
janela = sbox(*BBOX)
pub = [shape(f["geometry"]) for f in d if f.get("geometry") and janela.intersects(shape(f["geometry"]))]
tr = rasterio.transform.from_bounds(*BBOX, N, N)
px_m = 111320 * (BBOX[2] - BBOX[0]) / N
mp = np.zeros((N, N), dtype=bool)
for g in pub:
    mp |= rasterize([(g, 1)], out_shape=(N, N), transform=tr, fill=0, dtype="uint8").astype(bool)

pu = unary_union(pub)
import random; random.seed(0); refs = []
for i in range(3000):
    x = random.uniform(BBOX[0], BBOX[2]); y = random.uniform(BBOX[1], BBOX[3])
    p = shape({"type": "Point", "coordinates": (x, y)})
    if pu.buffer(0.003).contains(p): continue
    refs.append(p.buffer(0.0025))
    if len(refs) >= 150: break
mr = np.zeros((N, N), dtype=bool)
for g in refs:
    mr |= rasterize([(g, 1)], out_shape=(N, N), transform=tr, fill=0, dtype="uint8").astype(bool)

def auc(pv, rf):
    pv = np.nan_to_num(pv, nan=-9); rf = np.nan_to_num(rf, nan=-9)
    a = np.concatenate([pv, rf]); lab = np.concatenate([np.ones(len(pv)), np.zeros(len(rf))])
    o = np.argsort(a); r = np.empty(len(a)); r[o] = np.arange(1, len(a) + 1)
    return (r[lab == 1].sum() - len(pv) * (len(pv) + 1) / 2) / (len(pv) * len(rf))

pv = delta[mp & val]; rf = delta[mr & val]
out(f"\n2) DELTA de NDVI (2025 - 2022) na seca")
out(f"   pivos conhecidos: media {np.nanmean(pv):+.3f} mediana {np.nanmedian(pv):+.3f} p75 {np.nanpercentile(pv,75):+.3f}")
out(f"   areas de referencia: media {np.nanmean(rf):+.3f} mediana {np.nanmedian(rf):+.3f} p75 {np.nanpercentile(rf,75):+.3f}")
out(f"   AUC = {auc(pv, rf):.3f}   (0,5 = sem separacao)")

# ---- o sinal aparece FORA da camada? (candidatos a pivo novo)
out(f"\n3) Deltas grandes FORA da camada publica (candidatos a irrigacao nova)")
media = uniform_filter(np.nan_to_num(delta, nan=0.0), size=int(round(500/px_m)) | 1)
forte = (delta > 0.20) & (delta - media > 0.10) & val & ~mp
lab, n = label(forte)
cands = []
for i in range(1, n + 1):
    m = lab == i; cnt = int(m.sum())
    if cnt * (px_m ** 2) / 10000 < 4: continue
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    w = x1 - x0 + 1; h = y1 - y0 + 1
    if w < 3 or h < 3: continue
    preench = cnt / (w * h)
    # circulo rasterizado preenche ~pi/4 = 0,785 do bbox; quadrado preenche 1,0.
    # entao "circular" = preenchimento proximo de 0,785, nao proximo de 0.
    comp = abs(preench - math.pi / 4)
    cands.append(dict(ha=cnt * (px_m ** 2) / 10000, preench=preench, comp=comp,
                      lo=BBOX[0] + (x0 + x1) / 2 * (BBOX[2] - BBOX[0]) / N,
                      la=BBOX[3] - (y0 + y1) / 2 * (BBOX[3] - BBOX[1]) / N))
cands.sort(key=lambda c: -c["ha"])
out(f"   manchas com salto > 0,20 e contraste > 0,10: {len(cands)}")
out(f"   {'ha':>8} {'preench':>8} {'circ':>6}  {'lat':>9} {'lon':>10}  forma")
for c in cands[:12]:
    forma = "CIRCULAR" if c["comp"] < 0.12 and c["preench"] > 0.62 else ""
    out(f"   {c['ha']:>8.1f} {c['preench']:>8.2f} {c['comp']:>6.2f}  {c['la']:>9.4f} {c['lo']:>10.4f}  {forma}")
out("\n(FIM)")
