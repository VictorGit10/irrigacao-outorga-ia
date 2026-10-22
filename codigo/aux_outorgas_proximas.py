"""
Acrescenta a cada area da fila as outorgas de irrigacao mais proximas,
de QUALQUER sub-bacia, ate 5 km.

Por que: a regra do cruzamento (mesma sub-bacia, ate 15 km) deixa de fora
captacoes que ficam do outro lado de um divisor de agua ou num afluente
vizinho. O revisor precisa ver essas outorgas para decidir. Na fila original,
5 das 18 areas tinham uma outorga de irrigacao a menos de 2 km.

Mostra so dados do ato (numero, distancia, tipo de captacao, situacao),
nunca o nome ou o CPF/CNPJ do requerente.

Uso:  python aux_outorgas_proximas.py   (depois de aux_gerar_fila.py)
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
FILA = os.path.join(HERE, "saida", "fila_revisao.json")
OUTORGAS = os.path.join(HERE, ".cache", "vw_usos_outorgados_publico_cql.json")
RAIO_KM, MAX = 5.0, 3

def hav(lo1, la1, lo2, la2):
    R = 6371.0; p1, p2 = math.radians(la1), math.radians(la2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

atos = []
for f in json.load(open(OUTORGAS, encoding="utf-8")):
    p = f["properties"]; lo, la = num(p.get("int_longitude")), num(p.get("int_latitude"))
    if lo and la:
        atos.append(dict(lo=lo, la=la, ato=str(p.get("int_nu_ato") or ""), captacao=str(p.get("int_ds") or "").capitalize(),
                         situacao=str(p.get("int_sit_uso") or "").capitalize(), dominio=str(p.get("bho_dedominial") or "").capitalize(),
                         subbacia=str(p.get("bho_cobacia") or ""), area_ha=num(p.get("sir_ar_irrigada"))))

d = json.load(open(FILA, encoding="utf-8"))
for it in d["itens"]:
    perto = sorted(((hav(it["lon"], it["lat"], a["lo"], a["la"]), a) for a in atos), key=lambda x: x[0])
    it["outorgas_proximas"] = [dict(km=round(k, 2), ato=a["ato"], captacao=a["captacao"], situacao=a["situacao"],
                                    dominio=a["dominio"], mesma_subbacia=(a["subbacia"] == it["subbacia"]),
                                    area_declarada_ha=a["area_ha"])
                               for k, a in perto[:MAX] if k <= RAIO_KM]
    print(it["id"], [o["km"] for o in it["outorgas_proximas"]])
json.dump(d, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok:", FILA)
