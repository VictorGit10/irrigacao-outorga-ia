"""
Mapa da demonstracao: area irrigada mapeada + atos de outorga + candidatos.
Gera PNG (sem matplotlib: gera SVG, que abre em qualquer navegador/QGIS).
"""
import json, urllib.request, urllib.parse, math, os, pickle
from collections import defaultdict

WFS  = "https://siga.meioambiente.go.gov.br/geoserver/ows"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE= os.path.join(HERE, ".cache"); OUT = os.path.join(HERE, "saida")
os.makedirs(OUT, exist_ok=True)

def http_json(url, tries=4, pause=2.0):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"semad/1.0"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e; time.sleep(pause*(i+1))
    raise last

def wfs(layer, cql=None, cache_name=None, maxfeatures=250000):
    tag = cache_name or (layer.split(":")[-1] + ("_cql" if cql else ""))
    cf  = os.path.join(CACHE, tag + ".json")
    if os.path.exists(cf): return json.load(open(cf, "r", encoding="utf-8"))
    p = {"service":"WFS","version":"2.0.0","request":"GetFeature","typeName":layer,
         "outputFormat":"application/json","srsName":"EPSG:4674","maxFeatures":maxfeatures}
    if cql: p["CQL_FILTER"] = cql
    url = WFS + "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k,v in p.items())
    feats = http_json(url).get("features", [])
    json.dump(feats, open(cf,"w",encoding="utf-8"))
    return feats

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0

def rings_of(g):
    o=[]
    def walk(c):
        if isinstance(c[0],(int,float)): o.append(c); return
        if c and isinstance(c[0][0],(int,float)): o.append(c); return
        for k in c: walk(k)
    walk(g["coordinates"]); return o

def centroid(g):
    rs=rings_of(g)
    if not rs: return (0.0,0.0)
    r=max(rs,key=len); a=cx=cy=0.0; n=len(r)
    for i in range(n):
        x1,y1=r[i][0],r[i][1]; x2,y2=r[(i+1)%n][0],r[(i+1)%n][1]
        cr=x1*y2-x2*y1; a+=cr; cx+=(x1+x2)*cr; cy+=(y1+y2)*cr
    if abs(a)<1e-12: return (sum(p[0] for p in r)/n, sum(p[1] for p in r)/n)
    a*=0.5; return (cx/(6*a), cy/(6*a))

def esc(s):
    return (str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

print("carregando...", flush=True)
GO = wfs("geonode:limite_estadual")[0]
gov = GO["geometry"]
pivos = wfs("geonode:pivos_2020_2023_final")
acts  = wfs("geonode:vw_usos_outorgados_publico", cql="fin_tfn_ds LIKE '%IRRIGA%'")

# bbox
xs=[];ys=[]
for f in [GO]+pivos:
    for r in rings_of(f["geometry"]):
        for x,y in r: xs.append(x); ys.append(y)
x0,x1,y0,y1 = min(xs)-0.15, max(xs)+0.15, min(ys)-0.15, max(ys)+0.15
W,H = 1600, 1200
def X(lon): return (lon-x0)/(x1-x0)*W
def Y(lat): return H - (lat-y0)/(y1-y0)*H
print(f"bbox {x0:.2f},{y0:.2f} -> {x1:.2f},{y1:.2f}", flush=True)

s = [f'<?xml version="1.0" encoding="UTF-8"?>',
     f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
     '<rect width="100%" height="100%" fill="#f7f5ef"/>']

# grade de long/lat
for lon in range(int(x0), int(x1)+1):
    s.append(f'<line x1="{X(lon):.1f}" y1="0" x2="{X(lon):.1f}" y2="{H}" stroke="#dcd8cc" stroke-width="1"/>')
    s.append(f'<text x="{X(lon):.1f}" y="{H-8}" font-size="11" fill="#8a8578" text-anchor="middle">{lon}°</text>')
for lat in range(int(y0), int(y1)+1):
    s.append(f'<line x1="0" y1="{Y(lat):.1f}" x2="{W}" y2="{Y(lat):.1f}" stroke="#dcd8cc" stroke-width="1"/>')
    s.append(f'<text x="6" y="{Y(lat)-4:.1f}" font-size="11" fill="#8a8578">{lat}°</text>')

# limite de Goias
for r in rings_of(gov):
    pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x,y in r)
    s.append(f'<polygon points="{pts}" fill="#ffffff" stroke="#5a5347" stroke-width="2.5"/>')

# pivos: area do pivo
for f in pivos:
    p=f["properties"]; g=f.get("geometry")
    if not g: continue
    la=num(p.get("latitude_c") or p.get("Latitude_c")); lo=num(p.get("longitude_") or p.get("Longitude_"))
    if not (la and lo): lo,la=centroid(g)
    ar=num(p.get("area_ha") or p.get("Area"))
    r=6+ (min(ar,400)/400)*16
    s.append(f'<circle cx="{X(lo):.1f}" cy="{Y(la):.1f}" r="{r:.1f}" fill="#3d7a3d" fill-opacity="0.30" stroke="#2d5c2d" stroke-width="0.6"/>')

# atos de outorga: ponto de captacao
for f in acts:
    p=f["properties"]
    lo=num(p.get("int_longitude")); la=num(p.get("int_latitude"))
    if not (lo and la): continue
    dom=str(p.get("bho_dedominial") or "").upper()
    col = "#c0392b" if dom.startswith("FED") else "#1f4e9c"
    s.append(f'<circle cx="{X(lo):.1f}" cy="{Y(la):.1f}" r="3" fill="{col}" fill-opacity="0.85" stroke="#fff" stroke-width="0.5"/>')

# legende
s.append(f'<rect x="16" y="16" width="330" height="118" fill="#ffffff" fill-opacity="0.93" stroke="#5a5347" stroke-width="1"/>')
s.append('<text x="28" y="38" font-size="14" font-family="sans-serif" font-weight="bold" fill="#2d2a24">Areas irrigadas mapeadas (SemAD)</text>')
s.append('<circle cx="40" cy="58" r="8" fill="#3d7a3d" fill-opacity="0.35" stroke="#2d5c2d"/>')
s.append('<text x="58" y="62" font-size="12" font-family="sans-serif" fill="#2d2a24">pivo / area irrigada (tamanho = area)</text>')
s.append('<circle cx="40" cy="80" r="3" fill="#1f4e9c"/>')
s.append('<text x="58" y="84" font-size="12" font-family="sans-serif" fill="#2d2a24">ponto de captacao - outorga ESTADUAL (SemAD)</text>')
s.append('<circle cx="40" cy="100" r="3" fill="#c0392b"/>')
s.append('<text x="58" y="104" font-size="12" font-family="sans-serif" fill="#2d2a24">ponto de captacao - dominio FEDERAL (ANA)</text>')
s.append('<text x="28" y="124" font-size="10" font-family="sans-serif" fill="#6b6559">Fonte: WFS publico SemAD/GO (siga.meioambiente.go.gov.br/geoserver) - EPSG:4674</text>')
s.append("</svg>")
svg = "\n".join(s)
p = os.path.join(OUT, "mapa_reconciliacao.svg")
open(p, "w", encoding="utf-8").write(svg)
print("gravado:", p, os.path.getsize(p)/1e3, "KB")
