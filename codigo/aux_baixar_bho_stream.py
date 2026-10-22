"""
Baixa a BHO com geometria em STREAMING e extrai so o necessario:
  para cada trecho: cobacia, noorigem, nodestino, dedominial, m_atual, centroide
Evita o JSON de 598 MB em memoria e em disco.
"""
import json, urllib.request, urllib.parse, time, os, pickle
from collections import defaultdict

WFS = "https://siga.meioambiente.go.gov.br/geoserver/ows"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache"); os.makedirs(CACHE, exist_ok=True)
OUT = os.path.join(CACHE, "bho_trechos.pkl")

def out(*t): print(*t, flush=True)

if os.path.exists(OUT):
    out("cache existe:", OUT); raise SystemExit(0)

p = {"service":"WFS","version":"2.0.0","request":"GetFeature","typeName":"geonode:bho_goias",
     "outputFormat":"application/json","srsName":"EPSG:4674","maxFeatures":250000}
url = WFS + "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in p.items())

def centroide_geom(g):
    """Centroide do LineString: media dos vertices (aproximado, suficiente
    para localizar o trecho a 100 m)."""
    pts = []
    def walk(c):
        if not c: return
        if isinstance(c[0], (int, float)): pts.append(c); return
        if c and isinstance(c[0][0], (int, float)): pts.extend(c); return
        for k in c: walk(k)
    walk(g.get("coordinates", []))
    if not pts: return None
    return (sum(q[0] for q in pts)/len(pts), sum(q[1] for q in pts)/len(pts))

out("baixando BHO com geometria (streaming) ...")
req = urllib.request.Request(url, headers={"User-Agent": "semad/1.0"})
t0 = time.time(); n = 0; buf = ""; trechos = []
dec = json.JSONDecoder()
with urllib.request.urlopen(req, timeout=3600) as r:
    # le em blocos e extrai feature por feature
    pend = ""
    while True:
        chunk = r.read(1 << 20)
        if not chunk: break
        pend += chunk.decode("utf-8", "ignore")
        while True:
            i = pend.find('{"type":"Feature"')
            if i < 0: break
            # recua ate o inicio do objeto
            j = pend.find("{", i)
            depth = 0; instr = False; esc = False; k = j
            while k < len(pend):
                ch = pend[k]
                if instr:
                    if esc: esc = False
                    elif ch == "\\": esc = True
                    elif ch == '"': instr = False
                else:
                    if ch == '"': instr = True
                    elif ch == "{": depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            k += 1; break
                k += 1
            if k >= len(pend): break   # objeto incompleto
            try:
                f = json.loads(pend[j:k])
            except Exception:
                break
            pend = pend[k:]
            pr = f.get("properties") or {}
            g = f.get("geometry")
            if g:
                c = centroide_geom(g)
                if c:
                    trechos.append((str(pr.get("cobacia")), str(pr.get("noorigem")),
                                    str(pr.get("nodestino")), pr.get("dedominial"),
                                    pr.get("m_atual"), c[0], c[1]))
            n += 1
            if n % 20000 == 0:
                out(f"   {n:,} features, {time.time()-t0:.0f}s, {len(trechos):,} trechos")
out(f"   {n:,} features em {time.time()-t0:.0f}s -> {len(trechos):,} trechos")
with open(OUT, "wb") as fh: pickle.dump(trechos, fh, protocol=4)
out("gravado:", OUT, os.path.getsize(OUT)/1e6, "MB")
