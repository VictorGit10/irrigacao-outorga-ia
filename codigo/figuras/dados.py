"""
Le uma camada do servidor de mapas da SEMAD-GO, usando o cache de codigo/.cache/.

Se a camada nao estiver no cache, baixa do WFS publico e guarda como lista de
feicoes GeoJSON (o mesmo formato que demo_reconciliacao.py usa).
"""
import json, os, urllib.parse, urllib.request

WFS = "https://siga.meioambiente.go.gov.br/geoserver/ows"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache")
# a camada de outorgas fica no cache ja filtrada para irrigacao
FILTROS = {"vw_usos_outorgados_publico_cql": ("vw_usos_outorgados_publico",
           "fin_tfn_ds LIKE '%IRRIGA%'")}

def camada(nome):
    p = os.path.join(CACHE, nome + ".json")
    if not os.path.exists(p):
        os.makedirs(CACHE, exist_ok=True)
        real, cql = FILTROS.get(nome, (nome, None))
        q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "geonode:" + real,
             "outputFormat": "application/json", "srsName": "EPSG:4326"}
        if cql: q["CQL_FILTER"] = cql
        url = WFS + "?" + urllib.parse.urlencode(q)
        print("baixando", nome, "...")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "figuras/1.0"}), timeout=900) as r:
            feats = json.loads(r.read().decode("utf-8"))["features"]
        json.dump(feats, open(p, "w", encoding="utf-8"))
    d = json.load(open(p, encoding="utf-8"))
    return d["features"] if isinstance(d, dict) else d
