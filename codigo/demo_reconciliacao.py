"""
DEMO v8 — Conciliacao area irrigada x atos de outorga (SEMAD/GO)
==============================================================
V8 corrige um defeito metodologico da v7 (ver NOTA METODOLOGICA no bloco R4):
a regra de vinculo pivo <-> ato passou a usar a MESMA sub-bacia do pivo, com
distancia maxima, em vez de "qualquer ato a montante". A regra antiga media
a posicao na rede de drenagem, nao a documentacao.

V8 tambem:
  - sao tres NIVEIS DE EVIDENCIA (A/B/C), nao uma lista binaria de suspeitos
  - o arquivo de saida chama-se "amostra_para_teste.csv" (nao "candidatos")
  - a area so entra no nivel A se o ato for compativel com a area do pivo

Fonte: WFS publico SemAD/GO + Sentinel-2 via Microsoft Planetary Computer.
"""
import json, urllib.request, urllib.parse, math, csv, os, time, pickle, sys
from collections import defaultdict

WFS  = "https://siga.meioambiente.go.gov.br/geoserver/ows"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS  = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "saida"); CACHE = os.path.join(HERE, ".cache")
os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
_sas = {}

# Limites do vinculo pivo <-> ato (mesma sub-bacia do BHO)
RAIO_A_KM = 5.0     # outorga compativel
RAIO_B_KM = 15.0    # outorga possivel
TOL_AREA  = 0.5     # area declarada do ato >= 50% da area do pivo

def http_json(url, tries=4, pause=2.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "semad-conciliacao/1.0"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause * (i + 1))
    raise last

def wfs(layer, cql=None, props=None, cache_name=None, maxfeatures=250000):
    tag = cache_name or (layer.split(":")[-1] + ("_cql" if cql else ""))
    cf  = os.path.join(CACHE, tag + ".json")
    if os.path.exists(cf): return json.load(open(cf, "r", encoding="utf-8"))
    p = {"service":"WFS","version":"2.0.0","request":"GetFeature","typeName":layer,
         "outputFormat":"application/json","srsName":"EPSG:4674","maxFeatures":maxfeatures}
    if cql: p["CQL_FILTER"] = cql
    if props: p["propertyName"] = ",".join(props)
    url = WFS + "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in p.items())
    t0 = time.time()
    feats = http_json(url).get("features", [])
    out(f"      [wfs] {tag}: {len(feats):,} feats em {time.time()-t0:.0f}s")
    json.dump(feats, open(cf, "w", encoding="utf-8"))
    return feats

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0
def out(*t): print(*t, flush=True)

from shapely.geometry import shape, Point
from shapely.strtree import STRtree

def rings_of(g):
    o = []
    def walk(c):
        if isinstance(c[0], (int, float)): o.append(c); return
        if c and isinstance(c[0][0], (int, float)): o.append(c); return
        for k in c: walk(k)
    walk(g["coordinates"]); return o

def centroid(g):
    rs = rings_of(g)
    if not rs: return (0.0, 0.0)
    r = max(rs, key=len); a = cx = cy = 0.0; n = len(r)
    for i in range(n):
        x1, y1 = r[i][0], r[i][1]; x2, y2 = r[(i+1) % n][0], r[(i+1) % n][1]
        cr = x1*y2 - x2*y1; a += cr; cx += (x1+x2)*cr; cy += (y1+y2)*cr
    if abs(a) < 1e-12: return (sum(p[0] for p in r)/n, sum(p[1] for p in r)/n)
    a *= 0.5; return (cx/(6*a), cy/(6*a))

def pip(pt, rings):
    x, y = pt; inside = False
    for r in rings:
        c = 0; n = len(r)
        for i in range(n):
            x1, y1 = r[i][0], r[i][1]; x2, y2 = r[(i+1) % n][0], r[(i+1) % n][1]
            if (y1 > y) != (y2 > y):
                if x < x1 + (y-y1)*(x2-x1)/(y2-y1): c += 1
        if c % 2 == 1: inside = not inside
    return inside

def hav(lo1, la1, lo2, la2):
    R = 6371.0; p1, p2 = math.radians(la1), math.radians(la2)
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(a))

# ===================================================== R1
out("="*72); out("R1  limite do estado de Goias"); out("="*72)
GO   = wfs("geonode:limite_estadual")[0]
GO_R = rings_of(GO["geometry"])
GO_GEOM = shape(GO["geometry"])
out(f"    {GO['properties'].get('nome')}")

# ===================================================== R2
out("\n" + "="*72); out("R2  areas irrigadas: fora do estado + dedup por sobreposicao"); out("="*72)
CAMADAS = [
    ("geonode:pivos_2020_2023_final",           "id_2",      "Mapa estadual"),
    ("geonode:Area_Irrigada_Bacia_Sao_Marcos",  "Cod_Empree", "Bacia Sao Marcos"),
    ("geonode:pivos_alto_sao_marcos",           "cod_areair", "Alto Sao Marcos"),
    ("geonode:areas_irrigadas_alto_meia_ponte", "id",         "Alto Meia Ponte"),
]
brutos = []
for lay, keyc, nome in CAMADAS:
    fs = wfs(lay); dentro = fora = 0
    for f in fs:
        g = f.get("geometry")
        if not g: continue
        p = f["properties"]; sg = shape(g)
        if sg.is_empty: continue
        la = num(p.get("Latitude_c") or p.get("latitude_c"))
        lo = num(p.get("Longitude_") or p.get("longitude_"))
        if not (la and lo):
            rp = sg.representative_point(); lo, la = rp.x, rp.y
        ar = num(p.get("Area") or p.get("area_ha") or p.get("area"))
        if not (GO_GEOM.contains(Point(lo, la)) or GO_GEOM.intersects(sg)):
            fora += 1; continue
        dentro += 1
        brutos.append({"geom": sg, "area": ar, "camada": nome, "id": str(p.get(keyc)),
                       "emp": str(p.get("Cod_Empree") or p.get("id_pk") or p.get("id_2")),
                       "lo": lo, "la": la, "cultura": p.get("cultura_pr"),
                       "subregiao": p.get("Subregiao")})
    out(f"    {nome:18s} dentro={dentro:>5,} fora={fora:>5,}")
out(f"\n    area bruta (com duplicidade): {len(brutos):,} poligonos | "
    f"{sum(b['area'] for b in brutos):,.1f} ha")

out("\n    deduplicando por sobreposicao real de poligonos ...")
arvore = STRtree([b["geom"] for b in brutos])
vistos = set(); pivos = []
for i, b in enumerate(brutos):
    if i in vistos: continue
    b["camadas"] = [b["camada"]]
    pivos.append(b)
    for j in arvore.query(b["geom"]):
        if j == i or j in vistos: continue
        if brutos[j]["geom"].contains(b["geom"].representative_point()) or \
           b["geom"].contains(brutos[j]["geom"].representative_point()):
            vistos.add(j); b["camadas"].append(brutos[j]["camada"])
out(f"    apos dedup: {len(pivos):,} areas unicas | {sum(p['area'] for p in pivos):,.1f} ha")
out(f"    {len(brutos)-len(pivos):,} poligonos eliminados como duplicatas")

out("\n    preenchendo municipio por spatial join ...")
muns = []
for f in wfs("geonode:municipio2022", cache_name="municipio2022"):
    p = f["properties"]; g = f.get("geometry")
    if not g: continue
    muns.append((str(p.get("Nome") or p.get("NM_MUNICIP")), shape(g)))
mtree = STRtree([m[1] for m in muns])
out(f"    {len(muns):,} municipios de Goias")
for p in pivos:
    hit = mtree.query(p["geom"]); nome = ""
    for j in hit:
        if muns[j][1].contains(p["geom"].representative_point()):
            nome = muns[j][0]; break
    p["mun"] = nome or "(sem mun.)"

# ===================================================== R3
out("\n" + "="*72); out("R3  atos de outorga para irrigacao + dominialidade"); out("="*72)
og = wfs("geonode:vw_usos_outorgados_publico", cql="fin_tfn_ds LIKE '%IRRIGA%'")
out(f"    {len(og):,} atos")
atos = []
for f in og:
    p = f["properties"]
    lo = num(p.get("int_longitude")); la = num(p.get("int_latitude"))
    dom = str(p.get("bho_dedominial") or "").strip().upper()
    dom = "FEDERAL" if dom.startswith("FED") else ("ESTADUAL" if dom.startswith("EST") else "NAO_CLASS")
    atos.append({"lo": lo, "la": la, "ar": num(p.get("sir_ar_irrigada")),
                 "sit": p.get("int_sit_uso"), "tipo": str(p.get("int_ds") or ""),
                 "dom": dom, "cob": str(p.get("bho_cobacia") or ""),
                 "mun": str(p.get("municipio") or ""), "req": str(p.get("requerente") or "")})
for k in ("ESTADUAL", "FEDERAL", "NAO_CLASS"):
    n = sum(1 for a in atos if a["dom"] == k)
    ar = sum(a["ar"] for a in atos if a["dom"] == k)
    out(f"    {k:10s} {n:>6,} atos  area declarada {ar:>12,.1f} ha")
n_com_ar = sum(1 for a in atos if a["ar"] > 0)
out(f"    com area declarada preenchida: {n_com_ar:,} de {len(atos):,} ({100*n_com_ar/len(atos):.0f}%)")
atos_est = [a for a in atos if a["dom"] == "ESTADUAL"]

# ===================================================== R4
out("\n" + "="*72); out("R4  vinculo pivo <-> ato de outorga"); out("="*72)
out("""
    NOTA METODOLOGICA (a versao anterior foi corrigida aqui)
    A v7 usava: 'existe QUALQUER ato estadual a montante na sub-bacia do pivo'.
    Medindo, isso se revelou defeituoso:
      - a cobertura mudava de 25% (raio 2 km) para 37,6% (sem limite);
      - 12,6% dos pivos so eram 'cobertos' por atos a mais de 25 km;
      - corr(%cobertura, area a montante) = +0,84, contra +0,46 para
        documentacao -> a regra mediava a POSICAO NA REDE DE DRENAGEM.
    A regra adotada usa a MESMA sub-bacia do pivo, com distancia maxima.
    Medida: 24,1% com raio de 5 km e 24,2% sem limite -> estavel.
    E o municipio do ato coincide com o do pivo em 93,7% dos casos.
""")
BHO_PKL = os.path.join(CACHE, "bho_trechos.pkl")
if not os.path.exists(BHO_PKL):
    out("    !! cache da BHO ausente: rode antes  python aux_baixar_bho_stream.py")
    sys.exit(1)
with open(BHO_PKL, "rb") as fh: trechos = pickle.load(fh)
out(f"    {len(trechos):,} trechos (cache local)")
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
out("    achando a sub-bacia de cada area ...")
t0 = time.time()
for p in pivos:
    t = trecho_do_ponto(p["lo"], p["la"])
    p["cob_pivo"] = t[0] if t else ""
    p["dom_pivo"] = t[3] if t else ""
    p["m_atual_pivo"] = t[4] if t else 0.0
out(f"    ok ({time.time()-t0:.0f}s)")

atos_por_cob = defaultdict(list)
for a in atos_est:
    if a["cob"] and a["lo"]: atos_por_cob[a["cob"]].append(a)
out(f"    {len(atos_por_cob):,} sub-bacias com ato de outorga estadual")

out("\n    classificando o vinculo em tres niveis de evidencia ...")
t0 = time.time()
for p in pivos:
    p["nivel"] = "C"; p["d"] = None; p["ato"] = None
    p["tipo_ato"] = ""; p["sit_ato"] = ""; p["area_declarada_ato"] = 0.0; p["ato_mun"] = ""
    if not p["cob_pivo"]: continue
    cand = atos_por_cob.get(p["cob_pivo"], [])
    if not cand: continue
    d, a = min(((hav(p["lo"], p["la"], x["lo"], x["la"]), x) for x in cand), key=lambda z: z[0])
    p["d"] = d; p["ato"] = a
    p["tipo_ato"] = a["tipo"]; p["sit_ato"] = a["sit"]
    p["area_declarada_ato"] = a["ar"]; p["ato_mun"] = a["mun"]
    if d > RAIO_B_KM:
        p["nivel"] = "C"
    elif a["ar"] > 0 and a["ar"] < p["area"] * TOL_AREA:
        p["nivel"] = "C"        # area declarada pequena demais para cobrir o pivo
    elif d <= RAIO_A_KM:
        p["nivel"] = "A"
    else:
        p["nivel"] = "B"
out(f"    ok ({time.time()-t0:.0f}s)")
nA=nB=nC=0; aA=aB=aC=0.0
for p in pivos:
    if p["nivel"]=="A": nA+=1; aA+=p["area"]
    elif p["nivel"]=="B": nB+=1; aB+=p["area"]
    else: nC+=1; aC+=p["area"]
out(f"\n    A  outorga compativel (mesma sub-bacia, <= {RAIO_A_KM:.0f} km) : {nA:>5,} areas | {aA:>11,.1f} ha")
out(f"    B  outorga possivel   (mesma sub-bacia, {RAIO_A_KM:.0f}-{RAIO_B_KM:.0f} km)      : {nB:>5,} areas | {aB:>11,.1f} ha")
out(f"    C  SEM informacao de outorga localizavel                    : {nC:>5,} areas | {aC:>11,.1f} ha")
out("    (C nao significa 'sem outorga': significa que este metodo nao")
out("     conseguiu localizar uma outorga compativel para aquela area.)")

# ===================================================== R5 federal
out("\n" + "="*72); out("R5  dominio federal (outorga da ANA)"); out("="*72)
nivelC = [p for p in pivos if p["nivel"] == "C"]
fed = [p for p in nivelC if p["dom_pivo"] and str(p["dom_pivo"]).lower().startswith("fed")]
out(f"    nivel C: {len(nivelC):,} areas | {sum(p['area'] for p in nivelC):,.1f} ha")
out(f"    em trecho FEDERAL (a outorga e da ANA, nao da SemAD): {len(fed):,} areas | "
    f"{sum(p['area'] for p in fed):,.1f} ha")
amostra = [p for p in nivelC if p not in fed]
out(f"    SEM informacao de outorga localizavel, em dominio estadual: {len(amostra):,} areas | "
    f"{sum(p['area'] for p in amostra):,.1f} ha")

# ===================================================== R6 NDVI
out("\n" + "="*72); out("R6  NDVI de seca (ago/2025) - Planetary Computer, sem login"); out("="*72)
try:
    import numpy as np, rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    def sign(h):
        if h not in _sas:
            _sas[h] = http_json(SAS + "?href=" + urllib.parse.quote(h, safe=""))["href"]; time.sleep(0.2)
        return _sas[h]
    def ndvi(item, bb):
        arrs = []
        for b in ("B04", "B08"):
            with rasterio.open(sign(item["assets"][b]["href"])) as ds:
                w = from_bounds(*transform_bounds("EPSG:4674", ds.crs, *bb, densify_pts=21),
                                transform=ds.transform)
                arrs.append(ds.read(1, window=w, out_shape=(80,80), resampling=Resampling.bilinear,
                                    boundless=True, fill_value=0).astype("float32"))
        red, nir = arrs
        nd = (nir-red)/(nir+red+1e-6)
        ok = (red>0)&(nir>0)&(nd>-1)&(nd<1)
        return (float(np.nanmean(nd[ok])), float(np.nanmax(nd[ok]))) if ok.sum() else None
    N = int(os.environ.get("NDVI_N","30"))
    teste = sorted(amostra, key=lambda x: -x["area"])[:N]
    out(f"    NDVI nos {len(teste)} maiores areas do nivel C ...")
    for i, p in enumerate(teste):
        bb = (p["lo"]-0.008, p["la"]-0.008, p["lo"]+0.008, p["la"]+0.008)
        u = (f"{STAC}/search?collections=sentinel-2-l2a&bbox={bb[0]},{bb[1]},{bb[2]},{bb[3]}"
             f"&datetime=2025-08-01/2025-09-20&limit=6")
        try:
            sc = http_json(u).get("features", [])
            if not sc: p["ndvi"] = None; continue
            best = min(sc, key=lambda x: x["properties"].get("eo:cloud_cover", 100))
            r = ndvi(best, bb)
            p["ndvi"] = round(r[0],3) if r else None
            p["ndvi_max"] = round(r[1],3) if r else None
        except Exception:
            p["ndvi"] = None
        if (i+1)%10==0: out(f"      {i+1}/{len(teste)}")
    vals=[p["ndvi"] for p in teste if p.get("ndvi") is not None]
    if vals:
        out(f"\n    NDVI medio {sum(vals)/len(vals):.3f} | min {min(vals):.3f} | max {max(vals):.3f}")
        out(f"    NDVI >= 0.25 (verde na seca): {sum(1 for p in teste if (p.get('ndvi') or 0)>=0.25):,} de {len(teste)}")
except ImportError:
    out("    (pulado: instale rasterio+numpy)")
except Exception as e:
    out(f"    (pulado: sem rede para o Planetary Computer - {e})")

# ===================================================== R7
out("\n" + "="*72); out("R7  AGREGACAO POR MUNICIPIO (unidade de acao)"); out("="*72)
seen=set(); ar_mun=defaultdict(float); ar_inst=defaultdict(float); n_atos=defaultdict(int)
for a in atos:
    k=(a["req"], a["cob"], round(a["ar"],2))
    if k in seen: continue
    seen.add(k)
    ar_mun[a["mun"]] += a["ar"]; n_atos[a["mun"]] += 1
    if a["sit"]=="INSTALADO": ar_inst[a["mun"]] += a["ar"]
mun_area=defaultdict(float); mun_n=defaultdict(int)
mun_A=defaultdict(int); mun_B=defaultdict(int); mun_C=defaultdict(int)
mun_Car=defaultdict(float)
for p in pivos:
    mun_area[p["mun"]] += p["area"]; mun_n[p["mun"]] += 1
    if p["nivel"]=="A": mun_A[p["mun"]] += 1
    elif p["nivel"]=="B": mun_B[p["mun"]] += 1
    else:
        mun_C[p["mun"]] += 1; mun_Car[p["mun"]] += p["area"]
rows=[]
for mun in set(list(mun_area)+list(ar_mun)):
    ma=mun_area.get(mun,0.0); ao=ar_mun.get(mun,0.0); na=n_atos.get(mun,0)
    if ma < 50: continue
    rows.append({"municipio":mun, "n_areas_mapeadas":mun_n.get(mun,0),
                 "area_mapeada_ha":round(ma,1), "n_atos_irrigacao":na,
                 "atos_por_area":round(na/mun_n[mun],2) if mun_n.get(mun) else "",
                 "area_outorgada_ha":round(ao,1), "area_outorgada_instalada_ha":round(ar_inst.get(mun,0.0),1),
                 "nivel_A_compativel":mun_A.get(mun,0), "nivel_B_possivel":mun_B.get(mun,0),
                 "nivel_C_sem_informacao":mun_C.get(mun,0),
                 "area_nivel_C_ha":round(mun_Car.get(mun,0.0),1)})
rows.sort(key=lambda r: -r["area_nivel_C_ha"])
out(f"    {len(rows)} municipios com area irrigada mapeada >= 50 ha\n")
out("    municipio                     areas   atos  atos/area   area_map  n_A   n_B   n_C   area_nivel_C")
for r in rows[:20]:
    out(f"    {r['municipio'][:24]:24s} {r['n_areas_mapeadas']:>5} {r['n_atos_irrigacao']:>5} "
        f"{str(r['atos_por_area']):>10} {r['area_mapeada_ha']:>9,.0f} "
        f"{r['nivel_A_compativel']:>4} {r['nivel_B_possivel']:>4} {r['nivel_C_sem_informacao']:>5} "
        f"{r['area_nivel_C_ha']:>13,.0f}")
cam=os.path.join(OUT,"municipios_por_nivel.csv")
with open(cam,"w",newline="",encoding="utf-8-sig") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
out(f"\n    -> {cam}")

prio = {r["municipio"] for r in rows[:20] if r["area_nivel_C_ha"] > 0}
prows=[]
for p in sorted(amostra, key=lambda x: -x["area"]):
    if p["mun"] not in prio: continue
    prows.append({"municipio":p["mun"],"area_id":p["id"],"empreendimento":p["emp"],
                  "area_ha":round(p["area"],2),"lon":round(p["lo"],6),"lat":round(p["la"],6),
                  "nivel_evidencia":p["nivel"],
                  "nivel_descricao":"C = sem informacao de outorga localizavel por este metodo",
                  "subbacia":p["cob_pivo"],"dominialidade":p["dom_pivo"],
                  "ato_mais_proximo_km":round(p["d"],2) if p["d"] is not None else "",
                  "ato_tipo":p["tipo_ato"],"ato_situacao":p["sit_ato"],
                  "ato_area_declarada_ha":p["area_declarada_ato"],
                  "ndvi_ago2025":p.get("ndvi",""),"cultura":p["cultura"] or "",
                  "subregiao":p.get("subregiao") or "","camadas":",".join(p["camadas"])})
cam2=os.path.join(OUT,"amostra_para_teste.csv")
with open(cam2,"w",newline="",encoding="utf-8-sig") as fh:
    w=csv.DictWriter(fh,fieldnames=list(prows[0].keys())); w.writeheader(); w.writerows(prows)
out(f"    -> {cam2}  ({len(prows):,} areas em {len(prio)} municipios)")
out("       NAO inclui requerente nem cpf_cnpj (dado pessoal)")
out("       ATENCAO: e uma AMOSTRA PARA TESTAR A REGRA, nao lista de infratores.")
out("\nFIM")
