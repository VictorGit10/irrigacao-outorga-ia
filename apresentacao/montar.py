"""
Monta a versao web da apresentacao a partir dos slides em apresentacao/slides/.

  deck.json (ordem) + slides/*.html  ->  docs/apresentacao/index.html
                                         docs/apresentacao/apresentacao.pdf (com --pdf)

Os slides foram escritos para o tipo "Slides" dos Artifacts do Claude: cada um e
um <section> de 1920x1080 com estilos em linha, imagens como /_blob/<id> e dois
elementos proprios (<x-icon> e <x-shape>). Aqui as imagens viram arquivos em
docs/apresentacao/img/, os dois elementos viram SVG/CSS comuns e as notas do
apresentador (<aside>) saem.

Uso:  python montar.py          (so o HTML)
      python montar.py --pdf    (HTML e PDF, usando o Microsoft Edge sem janela)
"""
import json, os, re, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "..", "docs", "apresentacao")

IMAGENS = {
    "149d24fd78c06d322b68c023a486ecd8": "img/1_goias_pivos.png",
    "498d8bdbb8100365b91dca8aaf9a6629": "img/2_cristalina_zoom.png",
    "1de102021b0bbde1db2217b72564ff69": "img/2_cristalina_zoom_v2.png",
    "ca3cd84970510713e1577eb4d1550023": "img/3_sao_marcos_fora.png",
    "c25cc1bc2d92a5c2e70ddca6005eafd2": "img/4_regra_rio_acima.png",
    "cbf64af89bc7a3c1dc17a538219fcc77": "img/5a_satelite_cor.png",
    "1749ff0f76d7fb421f0caf2449c813af": "img/5b_satelite_ndvi.png",
}
ICONES = {  # tracos no estilo Lucide (licenca ISC)
    "CheckCircle": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "Code": '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
    "Users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "Search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "FileText": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
                '<path d="M16 13H8"/><path d="M16 17H8"/>',
}

def icone(m):
    nome, estilo = m.group(1), m.group(2)
    tracos = ICONES.get(nome)
    if not tracos: raise SystemExit(f"icone sem desenho: {nome}")
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="{estilo};flex:none" aria-hidden="true">{tracos}</svg>')

def forma(m):
    tipo, estilo = m.group(1), m.group(2)
    extra = {"ellipse": "border-radius:50%",
             "arrow-up": "clip-path:polygon(50% 0,100% 100%,0 100%)"}.get(tipo)
    if extra is None: raise SystemExit(f"forma sem desenho: {tipo}")
    return f'<div style="{estilo};{extra};flex:none"></div>'

def slide(nome):
    h = open(os.path.join(AQUI, "slides", nome + ".html"), encoding="utf-8").read()
    h = re.sub(r"<aside>.*?</aside>", "", h, flags=re.S)
    h = re.sub(r'<x-icon name="([^"]+)" style="([^"]*)"></x-icon>', icone, h)
    h = re.sub(r'<x-shape kind="([^"]+)" style="([^"]*)"></x-shape>', forma, h)
    def img(m):
        if m.group(1) not in IMAGENS: raise SystemExit(f"imagem sem arquivo: {m.group(1)}")
        return IMAGENS[m.group(1)]
    h = re.sub(r"/_blob/([0-9a-f]{32})", img, h)
    if "<x-" in h or "/_blob/" in h: raise SystemExit(f"sobrou elemento nao convertido em {nome}")
    return h.strip()

deck = json.load(open(os.path.join(AQUI, "deck.json"), encoding="utf-8"))
corpo = "\n".join(slide(n) for n in deck["order"])
fontes = "&".join(f"family={f['family'].replace(' ', '+')}:wght@400;600;700" for f in deck["faces"].values())

HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{deck['title']} · apresentação</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?{fontes}&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;height:100%;background:#0d1714}}
#palco section h1,#palco section h2,#palco section h3,#palco section p{{margin:0}}
#palco section ul{{margin:0;padding-left:1.1em}}
#palco section li{{margin:.15em 0}}
#palco section{{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden;display:none!important}}
#palco section.ativo{{display:flex!important}}
#palco{{position:absolute;width:1920px;height:1080px;transform-origin:0 0}}
.barra{{position:fixed;left:0;right:0;bottom:0;display:flex;align-items:center;gap:10px;padding:8px 14px;
        font:13px "Segoe UI",Arial,sans-serif;color:#cfd8d3;background:rgba(13,23,20,.86)}}
.barra a{{color:#cfd8d3}}
.barra button{{background:#24352f;border:0;color:#eef2ec;border-radius:6px;padding:6px 12px;cursor:pointer;font:inherit}}
.barra .esp{{flex:1}}
@media print{{
  @page{{size:1920px 1080px;margin:0}}
  html,body{{background:#fff;height:auto}}
  .barra{{display:none}}
  #palco{{position:static;transform:none!important}}
  #palco section{{position:relative;display:flex!important;page-break-after:always;break-after:page}}
}}
</style>
</head>
<body>
<div id="palco">
{corpo}
</div>
<div class="barra">
  <a href="../">← voltar ao site</a>
  <span class="esp"></span>
  <button id="ant" aria-label="Slide anterior">←</button>
  <span id="num"></span>
  <button id="prox" aria-label="Próximo slide">→</button>
  <span class="esp"></span>
  <a href="apresentacao.pdf">baixar PDF</a>
</div>
<script>
const S = [...document.querySelectorAll("#palco section")];
let i = Math.max(0, Math.min(S.length - 1, (parseInt(location.hash.slice(1)) || 1) - 1));
function ajustar(){{
  const p = document.getElementById("palco"), h = innerHeight - 44;
  const e = Math.min(innerWidth / 1920, h / 1080);
  p.style.transform = `scale(${{e}})`;
  p.style.left = (innerWidth - 1920 * e) / 2 + "px";
  p.style.top = Math.max(0, (h - 1080 * e) / 2) + "px";
}}
function mostrar(n){{
  i = Math.max(0, Math.min(S.length - 1, n));
  S.forEach((s, k) => s.classList.toggle("ativo", k === i));
  document.getElementById("num").textContent = (i + 1) + " / " + S.length;
  history.replaceState(null, "", "#" + (i + 1));
}}
document.getElementById("ant").onclick = () => mostrar(i - 1);
document.getElementById("prox").onclick = () => mostrar(i + 1);
addEventListener("keydown", e => {{
  if (["ArrowRight", "PageDown", " "].includes(e.key)) {{ e.preventDefault(); mostrar(i + 1); }}
  if (["ArrowLeft", "PageUp"].includes(e.key)) {{ e.preventDefault(); mostrar(i - 1); }}
}});
let x0 = null;
addEventListener("touchstart", e => x0 = e.touches[0].clientX, {{passive: true}});
addEventListener("touchend", e => {{ if (x0 === null) return; const d = e.changedTouches[0].clientX - x0;
  if (Math.abs(d) > 40) mostrar(i + (d < 0 ? 1 : -1)); x0 = null; }});
addEventListener("resize", ajustar);
ajustar(); mostrar(i);
</script>
</body>
</html>
"""
os.makedirs(DESTINO, exist_ok=True)
saida = os.path.join(DESTINO, "index.html")
open(saida, "w", encoding="utf-8").write(HTML)
print(f"ok: {os.path.normpath(saida)} ({len(deck['order'])} slides)")

if "--pdf" in sys.argv:
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    pdf = os.path.join(DESTINO, "apresentacao.pdf")
    url = "file:///" + os.path.abspath(saida).replace("\\", "/")
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    f"--print-to-pdf={pdf}", url], check=True, timeout=180)
    print(f"ok: {os.path.normpath(pdf)}")
