"""
Indicador de cobertura documental por municipio.

Complementa o ranking do pipeline principal (demo_reconciliacao.py), que
agrega por nivel de evidencia. Aqui a pergunta e outra: quantos ATOS de
outorga de irrigacao existem no municipio, para cada area irrigada mapeada.

Por que este indicador e nao "area mapeada / area outorgada":
  so 585 de 6.121 atos (10%) tem area declarada preenchida. Comparar areas
  pune quem preencheu o campo e premia quem deixou em branco -> invertido.

Uso:  python aux_indicador_cobertura.py
"""
import json, os, csv
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE= os.path.join(HERE, ".cache"); OUT = os.path.join(HERE, "saida")

def num(v):
    try: return float(v)
    except: return 0.0
def out(*t): print(*t, flush=True)
def norm(s):
    s = str(s or "").strip().upper()
    for a, b in [("Á","A"),("Ã","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),
                 ("Â","A"),("Ê","E"),("Ç","C"),("Õ","O"),("Ô","O"),(" ","")]:
        s = s.replace(a, b)
    return s

# ---- atos de outorga de irrigacao (todos, por municipio)
og = json.load(open(os.path.join(CACHE, "vw_usos_outorgados_publico_cql.json"), encoding="utf-8"))
doc = defaultdict(lambda: {"n": 0, "inst": 0, "fed": 0, "poco": 0, "ar": 0.0})
for f in og:
    p = f["properties"]; m = norm(p.get("municipio"))
    d = doc[m]
    d["n"] += 1
    if p.get("int_sit_uso") == "INSTALADO": d["inst"] += 1
    if str(p.get("bho_dedominial") or "").upper().startswith("FED"): d["fed"] += 1
    if "SUBTERR" in str(p.get("int_ds") or ""): d["poco"] += 1
    d["ar"] += num(p.get("sir_ar_irrigada"))
out(f"atos de irrigacao: {sum(d['n'] for d in doc.values()):,} | municipios com outorga: {len(doc)}")

# ---- areas irrigadas por municipio (saida do pipeline principal)
mp = os.path.join(OUT, "municipios_por_nivel.csv")
if not os.path.exists(mp):
    out("ERRO: rode antes  python demo_reconciliacao.py")
    raise SystemExit(1)
mapeadas = {}
with open(mp, encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        mapeadas[norm(r["municipio"])] = {
            "n": int(num(r["n_areas_mapeadas"])), "area": num(r["area_mapeada_ha"]),
            "A": int(num(r["nivel_A_compativel"])), "B": int(num(r["nivel_B_possivel"])),
            "C": int(num(r["nivel_C_sem_informacao"])), "areaC": num(r["area_nivel_C_ha"])}

rows = []
for m, d in doc.items():
    mp_ = mapeadas.get(m)
    if not mp_ or mp_["n"] < 20: continue
    rows.append({
        "municipio": m, "n_areas_mapeadas": mp_["n"], "area_mapeada_ha": round(mp_["area"], 1),
        "n_atos_irrigacao": d["n"], "atos_instalados": d["inst"],
        "atos_por_area": round(d["n"] / mp_["n"], 3),
        "atos_federais": d["fed"], "atos_subterraneos": d["poco"],
        "area_declarada_ha": round(d["ar"], 1),
        "nivel_A": mp_["A"], "nivel_B": mp_["B"], "nivel_C": mp_["C"],
        "area_nivel_C_ha": round(mp_["areaC"], 1),
        "pct_nivel_C": round(100 * mp_["C"] / mp_["n"], 1)})
rows.sort(key=lambda r: -r["nivel_C"])
out(f"\n{len(rows)} municipios com >= 20 areas irrigadas mapeadas e outorga registrada\n")
out(f"  {'municipio':24s} {'areas':>6} {'atos':>5} {'atos/area':>10} {'n_A':>5} {'n_C':>5} {'%C':>5} {'area_C_ha':>11}")
for r in rows[:20]:
    out(f"  {r['municipio'][:24]:24s} {r['n_areas_mapeadas']:>6} {r['n_atos_irrigacao']:>5} "
        f"{r['atos_por_area']:>10.3f} {r['nivel_A']:>5} {r['nivel_C']:>5} "
        f"{r['pct_nivel_C']:>4.0f}% {r['area_nivel_C_ha']:>11,.0f}")
out("\n  NOTA: n_C alto nao significa irregularidade. Significa que o metodo nao")
out("  localizou outorga compativel. Pode ser outorga da ANA, captação a montante")
out("  nao mapeada, poço, ou pivot declarado e parado.")

cam = os.path.join(OUT, "municipios_indice_cobertura.csv")
with open(cam, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
out(f"\n-> {cam}")
