"""
Imagens e serie de NDVI para cada area da fila de triagem.

Le saida/fila_revisao.json (gerada por aux_gerar_fila.py) e, para cada area:
  1. refaz os recortes em cor natural da seca de 2022 e de 2025, escolhendo a
     cena com o recorte inteiro coberto e com menos nuvem DENTRO do recorte
     (o aux_gerar_fila escolhia pela nuvem da cena inteira, e alguns recortes
     saiam com faixa preta na borda da imagem);
  2. calcula a serie de NDVI de abril a outubro de 2025: media dentro do pivo
     e media num anel de 200 a 800 m em volta (o "entorno").

Por que a serie: o teste aux_deteccao_temporal.py mostrou que uma data so
separa mal pivo de vegetacao vizinha; o comportamento ao longo da seca separa
bem melhor. A serie aparece na tela de triagem como um grafico pequeno, para o
revisor ver o que o satelite viu na estacao inteira.

Cuidados:
  - Sentinel-2 L2A com processing baseline >= 04.00 tem um deslocamento de
    +1000 nos valores; e preciso descontar antes de calcular o NDVI.
  - Nuvem e sombra sao removidas pela banda SCL (classes 3, 8, 9 e 10).
  - Uma data so entra na serie se pelo menos 70% do pivo estiver limpo.

Uso:  python aux_imagens_fila.py      (precisa de rede; ~20-40 min)
Saida: saida/chips/<id>_<ano>.png e o campo "serie" em saida/fila_revisao.json
"""
import json, math, os, time, urllib.request, urllib.parse
# Opcoes do GDAL que evitam listar diretorios remotos e juntam pedidos HTTP.
# Sem elas, cada leitura de recorte leva varios segundos.
for k, v in dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                 GDAL_HTTP_MULTIPLEX="YES", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", VSI_CACHE="TRUE").items():
    os.environ.setdefault(k, v)
import numpy as np, rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from shapely.geometry import shape, Point
from shapely.ops import transform as stransform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
SAIDA = os.path.join(HERE, "saida")
CHIPS = os.path.join(SAIDA, "chips")
FILA = os.path.join(SAIDA, "fila_revisao.json")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
SERIE_INI, SERIE_FIM = "2025-04-01", "2025-10-31"
SECA = {2022: ("2022-07-15", "2022-09-30"), 2025: ("2025-07-15", "2025-09-30")}
NUVEM = {3, 8, 9, 10}
PX = 420

def out(*t): print(*t, flush=True)

def http_json(url, tries=8, pause=4.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "triagem/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause * (i + 1))
    raise last

_token = {}
def sign(h):
    """Assina o endereco com o token da colecao (um pedido so, vale ~1 h).
    Assinar arquivo por arquivo esbarra no limite de pedidos do servico."""
    if not _token or time.time() > _token["ate"]:
        t = http_json(SAS.replace("/sign", "/token/sentinel-2-l2a"))
        _token.update(q=t["token"], ate=time.time() + 40 * 60)
    return h + "?" + _token["q"]

def ler(item, banda, bb, shape_out=None):
    """Le a janela bb (graus, EPSG:4674) de uma banda; devolve array e transform."""
    for i in range(5):
        try:
            with rasterio.open(sign(item["assets"][banda]["href"])) as ds:
                w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *bb, densify_pts=21),
                                transform=ds.transform)
                kw = dict(window=w, boundless=True, fill_value=0)
                if shape_out:
                    kw.update(out_shape=shape_out, resampling=Resampling.nearest)
                a = ds.read(1, **kw)
                tr = ds.window_transform(w)
                if shape_out:
                    tr = tr * tr.scale(w.width / shape_out[1], w.height / shape_out[0])
                return a, tr, ds.crs
        except Exception as e:
            out("      leitura falhou, tentando de novo:", type(e).__name__); time.sleep(5 * (i + 1))
    raise RuntimeError("leitura falhou")

def deslocamento(item):
    pb = str(item["properties"].get("s2:processing_baseline", "0"))
    try: return 1000.0 if float(pb) >= 4.0 else 0.0
    except ValueError: return 0.0

def busca(bb, ini, fim, nuvem_max):
    u = (f"{STAC}/search?collections=sentinel-2-l2a&bbox={','.join(map(str, bb))}"
         f"&datetime={ini}/{fim}&limit=100")
    sc = [s for s in http_json(u).get("features", [])
          if s["properties"].get("eo:cloud_cover", 100) <= nuvem_max]
    return sorted(sc, key=lambda s: s["properties"]["datetime"])

def poligonos():
    """Poligonos das 4 camadas de area irrigada, para achar o de cada item."""
    gs = []
    for lay in ("pivos_2020_2023_final", "Area_Irrigada_Bacia_Sao_Marcos",
                "pivos_alto_sao_marcos", "areas_irrigadas_alto_meia_ponte"):
        p = os.path.join(CACHE, lay + ".json")
        if not os.path.exists(p): continue
        for f in json.load(open(p, encoding="utf-8")):
            if f.get("geometry"):
                g = shape(f["geometry"])
                if not g.is_valid: g = g.buffer(0)
                gs.append(g)
    return gs

def mascaras(geom, tr, crs, forma, outros=None):
    """Mascaras de 'dentro do pivo' e do anel de 200-800 m em volta. Do anel saem
    os outros pivos mapeados (com folga de 30 m): o entorno e o que NAO e pivo."""
    para = Transformer.from_crs("EPSG:4674", crs, always_xy=True).transform
    gu = stransform(para, geom)
    dentro = ~geometry_mask([gu.__geo_interface__], out_shape=forma, transform=tr)
    anel = gu.buffer(800).difference(gu.buffer(200))
    if outros is not None and not outros.is_empty:
        anel = anel.difference(stransform(para, outros).buffer(30))
    if anel.is_empty: return dentro, np.zeros(forma, bool)
    em_volta = ~geometry_mask([anel.__geo_interface__], out_shape=forma, transform=tr)
    return dentro, em_volta

def chip_rgb(item, bb, geom):
    bandas = []
    for b in ("B04", "B03", "B02"):
        a, tr, crs = ler(item, b, bb, shape_out=(PX, PX))
        bandas.append(a.astype("float32"))
    if min((x > 0).mean() for x in bandas) < 0.995: return None, 1.0
    scl, _, _ = ler(item, "SCL", bb, shape_out=(PX, PX))
    dentro, _ = mascaras(geom, tr, crs, (PX, PX))
    nuvem = float(np.isin(scl[dentro], list(NUVEM)).mean()) if dentro.any() else 1.0
    rgb = np.dstack(bandas); im = np.zeros_like(rgb, dtype="uint8")
    for c in range(3):
        v = rgb[:, :, c]; lo, hi = np.percentile(v, 2), np.percentile(v, 98)
        im[:, :, c] = np.clip((v - lo) / max(hi - lo, 1) * 255, 0, 255).astype("uint8")
    img = Image.fromarray(im); dr = ImageDraw.Draw(img)
    para = Transformer.from_crs("EPSG:4674", crs, always_xy=True).transform
    gu = stransform(para, geom)
    aneis = [gu.exterior.coords] if gu.geom_type == "Polygon" else [g.exterior.coords for g in gu.geoms]
    for ring in aneis:
        pts = [tuple(~tr * (x, y)) for x, y in ring]
        if len(pts) > 2: dr.line(pts, fill=(255, 214, 0), width=3)
    return img, nuvem

def ndvi_ponto(item, bb, geom, outros=None):
    r, tr, crs = ler(item, "B04", bb)
    n, _, _ = ler(item, "B08", bb)
    scl, _, _ = ler(item, "SCL", bb, shape_out=r.shape)
    off = deslocamento(item)
    valido = (r > 0) & (n > 0) & ~np.isin(scl, list(NUVEM))
    rr, nn = r.astype("float32") - off, n.astype("float32") - off
    valido &= (rr > 0) & (nn > 0)   # pixel escuro demais (sombra, agua) fica fora
    nd = (nn - rr) / np.maximum(nn + rr, 1)
    dentro, em_volta = mascaras(geom, tr, crs, r.shape, outros)
    if dentro.sum() < 20: return None
    ok_d = dentro & valido; ok_v = em_volta & valido
    if ok_d.sum() / dentro.sum() < 0.7: return None
    entorno = round(float(nd[ok_v].mean()), 3) if ok_v.sum() >= 50 else None
    return round(float(nd[ok_d].mean()), 3), entorno

def processar(it, gs, arv):
    log = [f"{it['id']} {it['municipio']}"]
    pt = Point(it["lon"], it["lat"])
    cands = [gs[i] for i in arv.query(pt) if gs[i].contains(pt)] or [gs[arv.nearest(pt)]]
    geom = max(cands, key=lambda g: g.area)
    # Alguns poligonos do mapa sao so o contorno do pivo (um anel fino, quase sem
    # area). Nesses casos, usa a envoltoria convexa, que e o circulo do pivo.
    ha = geom.area * (111.32e3 ** 2) * math.cos(math.radians(it["lat"])) / 1e4
    if ha < 0.5 * float(it["area_ha"]):
        geom = geom.convex_hull
        log.append(f"   poligono so com o contorno ({ha:.1f} ha): usando a envoltoria convexa")
    minx, miny, maxx, maxy = geom.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    lado = max(maxx - minx, maxy - miny) / 2 * 1.9 + 0.006
    bb = (cx - lado, cy - lado, cx + lado, cy + lado)
    rp = geom.representative_point()
    outros = unary_union([gs[i] for i in arv.query(geom.buffer(0.01))
                          if not gs[i].contains(rp)] or [Point(0, 0).buffer(0)])
    # SO_SERIE=1 refaz so a serie de NDVI, mantendo os recortes ja salvos
    for ano, (ini, fim) in ({} if os.environ.get("SO_SERIE") else SECA).items():
        melhor = None
        for s in sorted(busca(bb, ini, fim, 30), key=lambda s: s["properties"]["eo:cloud_cover"])[:6]:
            img, nuvem = chip_rgb(s, bb, geom)
            if img is None: continue
            if melhor is None or nuvem < melhor[1]:
                melhor = (img, nuvem, s["properties"]["datetime"][:10])
            if nuvem < 0.01: break
        if melhor:
            nome = f"{it['id']}_{ano}.png"; melhor[0].save(os.path.join(CHIPS, nome), optimize=True)
            it[f"chip_{ano}"] = nome; it[f"data_{ano}"] = melhor[2]
            log.append(f"   recorte {ano}: {melhor[2]} (nuvem no pivo {melhor[1]:.0%})")
    serie, vistas = [], set()
    for s in busca(bb, SERIE_INI, SERIE_FIM, 60):
        dia = s["properties"]["datetime"][:10]
        if dia in vistas: continue
        try:
            v = ndvi_ponto(s, bb, geom, outros)
        except RuntimeError:
            v = None
        if v:
            serie.append(dict(data=dia, pivo=v[0], entorno=v[1])); vistas.add(dia)
    it["serie"] = serie
    log.append(f"   serie: {len(serie)} datas limpas")
    return "\n".join(log)

if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor, as_completed
    d = json.load(open(FILA, encoding="utf-8"))
    out("carregando poligonos...")
    gs = poligonos(); arv = STRtree(gs)
    LIM = int(os.environ.get("LIMITE", "0")) or None
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=int(os.environ.get("PARALELO", "4"))) as ex:
        ids = [x for x in os.environ.get("IDS", "").split(",") if x]   # IDS=C-11,C-16 refaz so esses
        futs = [ex.submit(processar, it, gs, arv) for it in d["itens"][:LIM] if not ids or it["id"] in ids]
        for f in as_completed(futs):
            out(f.result(), f"  [{time.time() - t0:.0f} s]")
            json.dump(d, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    d["meta"]["serie"] = dict(periodo=f"{SERIE_INI} a {SERIE_FIM}", fonte="Sentinel-2 L2A, Planetary Computer",
                             entorno="anel de 200 a 800 m em volta do pivo, sem os outros pivos mapeados",
                             nota="NDVI com desconto do deslocamento de +1000 (baseline >= 04.00) e nuvem removida pela SCL")
    json.dump(d, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out("\nok: saida/fila_revisao.json atualizado")
