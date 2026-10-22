"""
Gera a pagina de triagem (prototipo do ciclo alerta -> inspecao -> relatorio).

  saida/fila_revisao.json + saida/chips/*.png  ->  um HTML unico, que abre offline

Grava em dois lugares:
  - docs/triagem/index.html   (publicado no GitHub Pages)
  - codigo/saida/revisao_pivos.html  (copia local, abre com dois cliques)

A pagina nao usa servidor, login nem bibliotecas externas. As marcacoes ficam
no navegador de quem usa (localStorage) e saem em CSV e num relatorio em
Markdown. Nada e enviado para lugar nenhum.

Uso:  python aux_gerar_interface.py
"""
import base64, io, json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(HERE, "saida")
CHIPS = os.path.join(SAIDA, "chips")
DOCS = os.path.join(HERE, "..", "docs", "triagem")

d = json.load(open(os.path.join(SAIDA, "fila_revisao.json"), encoding="utf-8"))
itens, meta = d["itens"], d["meta"]

def datauri(nome, px=520, q=82):
    im = Image.open(os.path.join(CHIPS, nome)).convert("RGB")
    if max(im.size) > px: im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

imgs = {it["id"]: {"2022": datauri(it["chip_2022"]), "2025": datauri(it["chip_2025"])} for it in itens}
DADOS = json.dumps(dict(meta=meta, itens=itens), ensure_ascii=False)
IMGS = json.dumps(imgs, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triagem de áreas irrigadas · protótipo</title>
<style>
:root{
  --bg:#f3f5f0; --card:#fff; --ink:#15241f; --muted:#56655e; --line:#d9e0da; --soft:#eef2ec;
  --teal:#0e7c7b; --teal-soft:#dcebe9; --ochre:#9a6414; --ochre-soft:#f6e9d3;
  --red:#b4472f; --red-soft:#f7e3dd; --gray:#6b7570; --gray-soft:#e8ebe9;
}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:"Segoe UI",-apple-system,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);
     color:var(--ink);font-size:14px;line-height:1.45}
a{color:var(--teal)}
button{font:inherit}
header{background:var(--ink);color:#eef2ec;padding:12px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:650}
header .sub{font-size:12px;color:#b9c8c1}
header .voltar{color:#b9c8c1;font-size:12.5px;text-decoration:none}
header .voltar:hover{color:#fff}
.spacer{flex:1}
.tabs{display:flex;gap:4px}
.tab{padding:6px 12px;border-radius:6px;border:1px solid transparent;background:none;cursor:pointer;color:#b9c8c1}
.tab.on{background:#eef2ec;color:var(--ink);font-weight:650}
.aviso-topo{background:var(--ochre-soft);border-bottom:1px solid #ead6b3;color:#5f430f;font-size:13px;padding:9px 20px;
            display:flex;gap:12px;align-items:flex-start}
.aviso-topo button{margin-left:auto;background:none;border:0;color:#5f430f;cursor:pointer;font-size:18px;line-height:1}
main{max-width:1240px;margin:0 auto;padding:16px 20px 80px}
.fila{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 14px}
.pill{border:1px solid var(--line);background:#fff;border-radius:999px;padding:3px 9px;font-size:12px;cursor:pointer;
      font-variant-numeric:tabular-nums;color:var(--muted)}
.pill.atual{outline:2px solid var(--ink);outline-offset:1px;color:var(--ink);font-weight:650}
.pill.s-irr_sem{background:var(--red-soft);border-color:#e7b9ad;color:var(--red)}
.pill.s-irr_com{background:var(--teal-soft);border-color:#b9d6d3;color:var(--teal)}
.pill.s-nao{background:var(--gray-soft);border-color:#cfd5d2;color:var(--gray)}
.pill.s-incerto{background:var(--ochre-soft);border-color:#ead6b3;color:var(--ochre)}
.ferramentas{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
input[type=text],select,textarea{border:1px solid var(--line);border-radius:7px;padding:7px 9px;font:inherit;background:#fff;color:var(--ink)}
.grade{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:16px}
@media(max-width:900px){.grade{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.pad{padding:16px}
.imgbox{position:relative;background:#e3e8e4;aspect-ratio:1/1}
.imgbox img{width:100%;height:100%;object-fit:cover;display:block}
.alterna{position:absolute;left:10px;bottom:10px;display:flex;background:rgba(21,36,31,.82);border-radius:8px;padding:3px}
.alterna button{border:0;background:none;color:#cfd8d3;padding:5px 11px;border-radius:6px;cursor:pointer;font-size:12.5px}
.alterna button.on{background:#fff;color:var(--ink);font-weight:650}
.legenda-img{position:absolute;right:10px;bottom:10px;color:#fff;font-size:11.5px;background:rgba(21,36,31,.82);padding:4px 8px;border-radius:6px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 8px;font-weight:650}
h3{font-size:17px;margin:0 0 10px}
.serie-nota{font-size:12.5px;color:var(--muted);margin:6px 0 0}
.chave{display:flex;gap:14px;font-size:12px;color:var(--muted);margin-top:4px}
.chave i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:5px;border-radius:2px}
dl.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin:0;font-size:13.5px}
dl.kv dt{color:var(--muted)} dl.kv dd{margin:0;font-variant-numeric:tabular-nums}
.sep{height:1px;background:var(--line);margin:14px 0}
.caixa{border-radius:8px;padding:10px 12px;font-size:13px}
.caixa.amarela{background:var(--ochre-soft);color:#5f430f}
.decisoes{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.dec{padding:10px 10px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer;text-align:left;
     font-weight:600;color:var(--ink);display:flex;gap:8px;align-items:flex-start}
.dec small{display:block;font-weight:400;color:var(--muted);font-size:11.5px;margin-top:2px}
.dec kbd{font:11px ui-monospace,Consolas,monospace;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--muted)}
.dec:hover{background:var(--soft)}
.dec.sel[data-d=irr_sem]{background:var(--red-soft);border-color:var(--red)}
.dec.sel[data-d=irr_com]{background:var(--teal-soft);border-color:var(--teal)}
.dec.sel[data-d=nao]{background:var(--gray-soft);border-color:var(--gray)}
.dec.sel[data-d=incerto]{background:var(--ochre-soft);border-color:var(--ochre)}
#campoAto{display:none;margin-top:10px}
#campoAto input{width:100%}
textarea{width:100%;min-height:62px;resize:vertical;margin-top:10px}
.nav{display:flex;align-items:center;gap:8px;margin-top:14px}
.nav button,.bt{padding:7px 13px;border:1px solid var(--line);background:#fff;border-radius:7px;cursor:pointer;color:var(--ink)}
.nav button:disabled{opacity:.4;cursor:default}
.bt.prim{background:var(--ink);color:#fff;border-color:var(--ink)}
.cont{margin-left:auto;color:var(--muted);font-size:12px}
.salvo{font-size:12px;color:var(--teal);min-height:16px;margin-top:6px}
.oculto{display:none}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:14px}
@media(max-width:700px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}
.kpi b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.kpi span{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tabela-rolagem{overflow-x:auto}
pre{background:#15241f;color:#dfe8e3;padding:14px;border-radius:8px;overflow:auto;font-size:12px;white-space:pre-wrap}
.texto{max-width:760px}
.texto p,.texto li{font-size:14.5px}
.passos{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:14px 0}
@media(max-width:800px){.passos{grid-template-columns:1fr 1fr}}
.passo{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px}
.passo b{display:block;color:var(--teal);font-size:12px}
.passo span{font-size:13px}
.passo.pessoa{background:var(--teal-soft);border-color:#b9d6d3}
.rodape{color:var(--muted);font-size:12px;margin-top:16px}
</style>
</head>
<body>
<header>
  <div>
    <h1>Triagem de áreas irrigadas</h1>
    <div class="sub">Protótipo de demonstração · 18 áreas reais de exemplo · imagens Sentinel-2</div>
  </div>
  <a class="voltar" href="../">← voltar ao site</a>
  <div class="spacer"></div>
  <div class="tabs">
    <button class="tab on" data-tab="triagem">Triagem</button>
    <button class="tab" data-tab="relatorio">Relatório</button>
    <button class="tab" data-tab="como">Como funciona</button>
  </div>
</header>
<div class="aviso-topo" id="avisoTopo">
  <div><b>Protótipo feito num teste com IA.</b> As áreas são pivôs reais do mapa público da SEMAD-GO em que um
  método simples não achou outorga de irrigação por perto. <b>Isso não quer dizer que sejam irregulares</b>:
  a outorga pode estar em outro órgão, longe do pivô ou num ponto que o método não ligou. As marcações ficam só
  neste navegador.</div>
  <button title="Fechar aviso" onclick="this.parentNode.remove()">×</button>
</div>

<main>
<section id="viTriagem">
  <div class="ferramentas">
    <input type="text" id="revisor" placeholder="Seu nome (vai no relatório)" style="width:240px">
    <select id="filtro">
      <option value="todos">Todas as áreas</option>
      <option value="pendentes">Só as pendentes</option>
    </select>
    <div class="spacer"></div>
    <button class="bt" id="btCSV">Baixar CSV</button>
    <button class="bt" id="btLimpar">Apagar marcações</button>
  </div>
  <div class="fila" id="fila"></div>

  <div class="grade">
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="card">
        <div class="imgbox">
          <img id="img" alt="Recorte de satélite em cor natural com o contorno do pivô em amarelo">
          <div class="alterna">
            <button data-ano="2022">Seca de 2022</button>
            <button data-ano="2025" class="on">Seca de 2025</button>
          </div>
          <div class="legenda-img" id="legImg"></div>
        </div>
      </div>
      <div class="card"><div class="pad">
        <h2>Verde ao longo da seca de 2025 (NDVI)</h2>
        <div id="grafico"></div>
        <div class="chave"><span><i style="background:var(--teal)"></i>dentro do pivô</span>
          <span><i style="background:#9aa6a0"></i>em volta (200 a 800 m, fora de outros pivôs)</span></div>
        <p class="serie-nota">Pivô irrigado costuma ficar verde enquanto o entorno seca. Uma queda e depois
        uma subida em plena seca indica colheita e novo plantio irrigado. Cada ponto é uma data sem nuvem.</p>
      </div></div>
    </div>

    <div class="card"><div class="pad">
      <h3 id="titulo">—</h3>
      <dl class="kv" id="kv"></dl>
      <div class="sep"></div>
      <h2>O que o método achou de outorga</h2>
      <div id="outorga"></div>
      <div class="sep"></div>
      <h2>O que você vê</h2>
      <div class="decisoes">
        <button class="dec" data-d="irr_sem"><kbd>1</kbd><span>Irrigada, sem outorga conhecida<small>vai para o encaminhamento</small></span></button>
        <button class="dec" data-d="irr_com"><kbd>2</kbd><span>Irrigada, com outorga conhecida<small>o método errou: ajuda a corrigi-lo</small></span></button>
        <button class="dec" data-d="nao"><kbd>3</kbd><span>Não irrigada ou parada<small>pivô desativado, colhido ou outro uso</small></span></button>
        <button class="dec" data-d="incerto"><kbd>4</kbd><span>Incerto<small>precisa de outra imagem ou de campo</small></span></button>
      </div>
      <div id="campoAto"><input type="text" id="ato" placeholder="Número do ato ou do processo de outorga (se souber)"></div>
      <textarea id="obs" placeholder="Observação (opcional): o que te fez decidir"></textarea>
      <div class="salvo" id="salvo"></div>
      <div class="nav">
        <button id="btAnt">← anterior</button>
        <button id="btProx" class="bt prim">próxima →</button>
        <div class="cont" id="cont"></div>
      </div>
    </div></div>
  </div>
  <p class="rodape" id="rodape"></p>
</section>

<section id="viRelatorio" class="oculto">
  <div class="kpis" id="kpis"></div>
  <div class="card"><div class="pad">
    <h2>Para encaminhamento: irrigadas sem outorga conhecida</h2>
    <div class="tabela-rolagem"><table id="tabEnc"><thead><tr><th>ID</th><th>Município</th><th class="num">Área (ha)</th>
      <th>Coordenadas</th><th>Observação</th></tr></thead><tbody></tbody></table></div>
    <p class="rodape">Marcar uma área aqui registra que ela parece irrigada na imagem e que nem o método nem o revisor
    conhecem uma outorga para ela. <b>Não conclui irregularidade.</b> A verificação e a decisão são do setor competente.</p>
  </div></div>
  <div class="card" style="margin-top:14px"><div class="pad">
    <h2>Relatório (Markdown)</h2>
    <div class="ferramentas"><button class="bt" id="btMD">Baixar .md</button><button class="bt" id="btCopiar">Copiar</button>
      <button class="bt" id="btCSV2">Baixar CSV</button></div>
    <pre id="md"></pre>
  </div></div>
</section>

<section id="viComo" class="oculto texto">
  <h3>Para que serve esta página</h3>
  <p>Hoje, achar área irrigada sem outorga depende de alguém procurar à mão, caso a caso. A ideia aqui é inverter:
  o computador faz a parte repetitiva (achar candidatos, juntar imagens e outorgas próximas) e a pessoa faz só a
  parte que exige julgamento, olhando um caso de cada vez. O que ela decide sai num relatório pronto.</p>
  <div class="passos">
    <div class="passo"><b>1 · Detectar</b><span>Achar pivôs nas imagens de satélite, de tempos em tempos.</span></div>
    <div class="passo"><b>2 · Cruzar</b><span>Procurar outorga de irrigação perto de cada pivô.</span></div>
    <div class="passo"><b>3 · Montar a fila</b><span>Separar os casos sem outorga por perto, com imagens.</span></div>
    <div class="passo pessoa"><b>4 · Inspecionar</b><span>Uma pessoa olha cada caso e marca o que vê.</span></div>
    <div class="passo"><b>5 · Relatório</b><span>As marcações viram tabela e texto para o próximo passo.</span></div>
  </div>
  <p><b>Neste protótipo</b>, a etapa 1 ainda não existe: os pivôs vêm do mapa público da SEMAD (imagens de 2020 a 2023).
  As etapas 2 a 5 funcionam com os dados públicos, numa regra simples: a mesma sub-bacia e até 15 km de distância.</p>
  <h3>Por que a marcação da pessoa é a peça mais valiosa</h3>
  <p>Para ensinar um programa a reconhecer pivô irrigado, é preciso de exemplos já conferidos, e eles quase nunca
  existem. Cada marcação aqui é um exemplo conferido. Depois de uma estação seca de uso, haveria exemplos
  suficientes para treinar e medir um detector de verdade. É o mesmo princípio do DETER, do INPE: alerta automático,
  verificação humana e só então o laudo.</p>
  <p>A opção <b>“irrigada, com outorga conhecida”</b> é tão útil quanto as outras: ela mostra onde a regra de cruzamento
  erra e ajuda a corrigi-la.</p>
  <h3>Como ler as imagens</h3>
  <ul>
    <li><b>Recorte em cor natural:</b> a melhor imagem sem nuvem da seca de 2022 e da de 2025, com o contorno do pivô em amarelo.
    Comparar as duas mostra se o pivô já existia e se continua em uso.</li>
    <li><b>Gráfico de verde (NDVI):</b> quanto mais perto de 1, mais vegetação ativa. Na seca, a vegetação sem irrigação cai
    para perto de 0,2. Um pivô que se mantém verde, ou que volta a ficar verde em agosto ou setembro, provavelmente está irrigando.</li>
  </ul>
  <h3>Limites</h3>
  <ul>
    <li>A regra de cruzamento é simples e erra nos dois sentidos. Uma área sem outorga “por perto” pode ter outorga em rio federal
    (ANA), em poço ou num ponto de captação distante.</li>
    <li>São 18 casos de exemplo, escolhidos entre os maiores de cada município. Não é uma amostra do estado.</li>
    <li>As marcações ficam no navegador. Para guardar, baixe o CSV ou o relatório.</li>
  </ul>
  <p>Mais detalhes, código e dados: veja a <a href="../">página do projeto</a>.</p>
</section>
</main>

<script>
const DADOS = @@dados@@;
const IMGS  = @@imgs@@;
const CHAVE = "triagem-irrigacao-v2";
const ROTULO = {irr_sem:"Irrigada, sem outorga conhecida", irr_com:"Irrigada, com outorga conhecida",
                nao:"Não irrigada ou parada", incerto:"Incerto"};
const itens = DADOS.itens;
let estado = {revisor:"", itens:{}};
try { estado = Object.assign(estado, JSON.parse(localStorage.getItem(CHAVE) || "{}")); } catch(e) {}
let idx = 0, ano = "2025", filtro = "todos";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt = (n, d=1) => (n === null || n === undefined || n === "") ? "—" :
  Number(n).toLocaleString("pt-BR", {minimumFractionDigits:d, maximumFractionDigits:d});
const dataBR = s => s ? s.split("-").reverse().join("/") : "";

function salvar(){ try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch(e) {} }
function reg(id){ return estado.itens[id] || {}; }
function visiveis(){ return filtro === "pendentes" ? itens.filter(i => !reg(i.id).decisao) : itens; }
function atual(){ const v = visiveis(); if (idx >= v.length) idx = Math.max(0, v.length - 1); return v[idx]; }

function grafico(serie){
  if (!serie || !serie.length) return '<p class="serie-nota">Sem datas limpas para esta área.</p>';
  const W = 520, H = 170, m = {l:34, r:8, t:8, b:22};
  const x0 = Date.parse("2025-04-01"), x1 = Date.parse("2025-10-31");
  const X = s => m.l + (Date.parse(s) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => m.t + (1 - Math.max(0, Math.min(1, v))) * (H - m.t - m.b);
  let g = "";
  [0, 0.25, 0.5, 0.75, 1].forEach(v => {
    g += `<line x1="${m.l}" x2="${W-m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e3e8e4"/>`;
    g += `<text x="${m.l-6}" y="${Y(v)+4}" font-size="10" text-anchor="end" fill="#56655e">${v.toFixed(2).replace(".",",")}</text>`;
  });
  ["04","05","06","07","08","09","10"].forEach((mes, k) => {
    const xx = X(`2025-${mes}-15`);
    g += `<text x="${xx}" y="${H-6}" font-size="10" text-anchor="middle" fill="#56655e">${["abr","mai","jun","jul","ago","set","out"][k]}</text>`;
  });
  const linha = (campo, cor, larg) => {
    const ok = serie.filter(p => p[campo] !== null && p[campo] !== undefined);
    const pts = ok.map(p => `${X(p.data).toFixed(1)},${Y(p[campo]).toFixed(1)}`).join(" ");
    return `<polyline points="${pts}" fill="none" stroke="${cor}" stroke-width="${larg}" stroke-linejoin="round"/>` +
      ok.map(p => `<circle cx="${X(p.data).toFixed(1)}" cy="${Y(p[campo]).toFixed(1)}" r="2.4" fill="${cor}"><title>${dataBR(p.data)}: ${fmt(p[campo],2)}</title></circle>`).join("");
  };
  g += linha("entorno", "#9aa6a0", 1.6) + linha("pivo", "#0e7c7b", 2.4);
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Série de NDVI do pivô e do entorno de abril a outubro de 2025">${g}</svg>`;
}

function desenharFila(){
  const it = atual();
  $("#fila").innerHTML = itens.map(i => {
    const r = reg(i.id), cls = ["pill"];
    if (r.decisao) cls.push("s-" + r.decisao);
    if (it && i.id === it.id) cls.push("atual");
    return `<button class="${cls.join(" ")}" data-id="${i.id}" title="${esc(i.municipio)}${r.decisao ? " · " + ROTULO[r.decisao] : ""}">${i.id}</button>`;
  }).join("");
  document.querySelectorAll(".pill").forEach(b => b.onclick = () => {
    filtro = "todos"; $("#filtro").value = "todos"; idx = itens.findIndex(i => i.id === b.dataset.id); desenhar();
  });
}

function desenhar(){
  const v = visiveis(), it = atual();
  desenharFila();
  if (!it){ $("#titulo").textContent = "Nenhuma área pendente."; return; }
  const r = reg(it.id);
  $("#titulo").textContent = it.id + " · " + it.municipio;
  $("#img").src = IMGS[it.id][ano];
  $("#legImg").textContent = "Sentinel-2 · " + (dataBR(it["data_" + ano]) || ("seca de " + ano));
  document.querySelectorAll(".alterna button").forEach(b => b.classList.toggle("on", b.dataset.ano === ano));
  const maps = `https://www.google.com/maps/@${it.lat},${it.lon},2500m/data=!3m1!1e3`;
  $("#kv").innerHTML = [
    ["Área do pivô", fmt(it.area_ha) + " ha"],
    ["Município", esc(it.municipio)],
    ["Coordenadas", `${fmt(it.lat,5)}, ${fmt(it.lon,5)} · <a href="${maps}" target="_blank" rel="noopener">ver no mapa</a>`],
    ["Sub-bacia (BHO)", esc(it.subbacia) || "—"],
    ["Origem do polígono", esc(it.camadas) + " (SEMAD)"],
  ].map(x => `<dt>${x[0]}</dt><dd>${x[1]}</dd>`).join("") +
    (it.aviso_poligono ? `<dt>Atenção</dt><dd>${esc(it.aviso_poligono)}</dd>` : "");
  const regra = it.ato_num
    ? `O ato mais próximo na mesma sub-bacia (${esc(it.ato_num)}, a ${fmt(it.ato_km)} km) não atende à regra
       de distância ou de área declarada.`
    : `A regra (mesma sub-bacia, até 15 km) não encontrou outorga de irrigação estadual.`;
  const prox = it.outorgas_proximas || [];
  const lista = prox.length
    ? `<p style="margin:10px 0 4px;font-size:13px">Outorgas de irrigação a até 5 km, em qualquer sub-bacia:</p>
       <div class="tabela-rolagem"><table><thead><tr><th class="num">km</th><th>Ato</th><th>Captação</th><th>Situação</th><th>Mesma sub-bacia</th></tr></thead><tbody>` +
       prox.map(o => `<tr><td class="num">${fmt(o.km, 1)}</td><td>${esc(o.ato) || "—"}</td><td>${esc(o.captacao)}</td>
         <td>${esc(o.situacao)}</td><td>${o.mesma_subbacia ? "sim" : "não"}</td></tr>`).join("") + `</tbody></table></div>`
    : `<p style="margin:10px 0 0;font-size:13px">Nenhuma outorga de irrigação a até 5 km, em qualquer sub-bacia.</p>`;
  $("#outorga").innerHTML = `<div class="caixa amarela">${regra} <b>Isso não quer dizer que não exista outorga</b>:
    ela pode estar em rio federal (ANA), em poço ou num ponto que a regra não ligou.</div>` + lista;
  $("#grafico").innerHTML = grafico(it.serie);
  document.querySelectorAll(".dec").forEach(b => b.classList.toggle("sel", b.dataset.d === r.decisao));
  $("#campoAto").style.display = r.decisao === "irr_com" ? "block" : "none";
  $("#ato").value = r.ato || "";
  $("#obs").value = r.obs || "";
  $("#salvo").textContent = r.decisao ? `Marcado: ${ROTULO[r.decisao]}${r.quando ? " · " + new Date(r.quando).toLocaleString("pt-BR") : ""}` : "";
  $("#cont").textContent = `${idx + 1} de ${v.length}`;
  $("#btAnt").disabled = idx === 0;
  $("#btProx").disabled = idx >= v.length - 1;
  $("#rodape").innerHTML = `Fila gerada em ${esc(DADOS.meta.gerado_em)}. Imagens: Sentinel-2 L2A (Copernicus), via Microsoft
    Planetary Computer. Polígonos e outorgas: servidor público de mapas da SEMAD-GO. Atalhos: 1 a 4 marcam, ← e → navegam.`;
}

function atualizar(campos){
  const it = atual(); if (!it) return;
  estado.itens[it.id] = Object.assign({}, reg(it.id), campos);
  salvar();
}
function decidir(dd){
  const it = atual(); if (!it) return;
  const r = reg(it.id);
  if (r.decisao === dd) { atualizar({decisao: "", quando: ""}); }
  else atualizar({decisao: dd, revisor: $("#revisor").value, quando: new Date().toISOString()});
  desenhar();
}
const ir = passo => { const v = visiveis(); const n = idx + passo; if (n >= 0 && n < v.length){ idx = n; desenhar(); } };

function linhasCSV(){
  const cab = ["id","municipio","area_ha","lat","lon","subbacia","outorga_mais_proxima","outorga_km",
               "decisao","decisao_texto","ato_informado","observacao","revisor","quando"];
  const L = [cab];
  // separador ";" e vírgula decimal: abre direto no Excel em português
  const dec = v => (v === null || v === undefined || v === "") ? "" : String(v).replace(".", ",");
  itens.forEach(i => { const r = reg(i.id), op = (i.outorgas_proximas || [])[0] || {};
    L.push([i.id, i.municipio, dec(i.area_ha), dec(i.lat), dec(i.lon), i.subbacia, op.ato || "", dec(op.km),
            r.decisao || "", ROTULO[r.decisao] || "", r.ato || "", (r.obs || "").replace(/\s+/g, " "), r.revisor || "", r.quando || ""]); });
  return L.map(l => l.map(c => `"${String(c ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");
}
function baixar(nome, txt, tipo){
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([txt], {type: tipo + ";charset=utf-8"}));
  a.download = nome; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const baixarCSV = () => baixar("triagem_areas_irrigadas.csv", "﻿" + linhasCSV(), "text/csv");
const porDecisao = dd => itens.filter(i => reg(i.id).decisao === dd);
const somaHa = l => l.reduce((s, i) => s + Number(i.area_ha), 0);

function markdown(){
  const grupos = ["irr_sem","irr_com","nao","incerto"].map(k => [k, porDecisao(k)]);
  const pend = itens.filter(i => !reg(i.id).decisao).length;
  const L = [];
  L.push("# Relatório de triagem de áreas irrigadas", "");
  L.push(`- **Data:** ${new Date().toLocaleDateString("pt-BR")}`);
  L.push(`- **Revisor:** ${estado.revisor || "(não informado)"}`);
  L.push(`- **Casos na fila:** ${itens.length}, em ${new Set(itens.map(i => i.municipio)).size} municípios`);
  L.push(`- **Imagens:** Sentinel-2 L2A, seca de 2022 e de 2025, e série de NDVI de abril a outubro de 2025`);
  L.push(`- **Critério da fila:** pivô do mapa público da SEMAD-GO sem outorga de irrigação estadual na mesma sub-bacia até 15 km`, "");
  L.push("## Resumo", "", "| Resultado da inspeção | Áreas | Área (ha) |", "|---|---:|---:|");
  grupos.forEach(([k, l]) => L.push(`| ${ROTULO[k]} | ${l.length} | ${fmt(somaHa(l))} |`));
  L.push(`| Pendente | ${pend} | — |`, "");
  const bloco = (titulo, l, extra) => {
    L.push(`## ${titulo}`, "");
    if (!l.length) { L.push("_Nenhum caso._", ""); return; }
    l.forEach(i => { const r = reg(i.id);
      L.push(`### ${i.id} · ${i.municipio} (${fmt(i.area_ha)} ha)`, "");
      L.push(`- Coordenadas: ${Number(i.lat).toFixed(5)}, ${Number(i.lon).toFixed(5)}`);
      L.push(`- Sub-bacia (BHO): ${i.subbacia || "não identificada"}`);
      const op = (i.outorgas_proximas || [])[0];
      L.push(`- Outorga de irrigação mais próxima (qualquer sub-bacia): ${op ? `ato ${op.ato || "sem número"}, a ${fmt(op.km)} km` : "nenhuma a até 5 km"}`);
      if (extra) extra(i, r);
      if (r.obs) L.push(`- Observação: ${r.obs}`);
      L.push(""); });
  };
  bloco("Para encaminhamento: irrigadas sem outorga conhecida", grupos[0][1]);
  bloco("Irrigadas com outorga conhecida (o cruzamento não achou)", grupos[1][1],
        (i, r) => L.push(`- Outorga informada pelo revisor: ${r.ato || "(sem número)"}`));
  bloco("Não irrigadas ou paradas", grupos[2][1]);
  bloco("Incertas", grupos[3][1]);
  L.push("---", "");
  L.push("> Este relatório registra o que foi visto em imagens de satélite e o que o cruzamento automático encontrou.");
  L.push("> Ele **não conclui irregularidade** e não substitui a verificação, o contraditório e a decisão do setor competente.");
  return L.join("\n");
}
function desenharRelatorio(){
  const k = [["irr_sem","sem outorga conhecida"],["irr_com","com outorga conhecida"],["nao","não irrigadas"],["incerto","incertas"]];
  $("#kpis").innerHTML = k.map(([c, t]) => `<div class="kpi"><b>${porDecisao(c).length}</b><span>${t}</span></div>`).join("") +
    `<div class="kpi"><b>${itens.filter(i => !reg(i.id).decisao).length}</b><span>pendentes</span></div>`;
  const l = porDecisao("irr_sem");
  $("#tabEnc tbody").innerHTML = l.length ? l.map(i => `<tr><td>${i.id}</td><td>${esc(i.municipio)}</td>
      <td class="num">${fmt(i.area_ha)}</td><td>${fmt(i.lat,4)}, ${fmt(i.lon,4)}</td><td>${esc(reg(i.id).obs)}</td></tr>`).join("")
    : `<tr><td colspan="5" style="color:var(--muted)">Nenhum caso marcado ainda.</td></tr>`;
  $("#md").textContent = markdown();
}

document.querySelectorAll(".dec").forEach(b => b.onclick = () => decidir(b.dataset.d));
document.querySelectorAll(".alterna button").forEach(b => b.onclick = () => { ano = b.dataset.ano; desenhar(); });
document.querySelectorAll(".tab").forEach(b => b.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("on", x === b));
  ["triagem","relatorio","como"].forEach(t => $("#vi" + t[0].toUpperCase() + t.slice(1)).classList.toggle("oculto", t !== b.dataset.tab));
  if (b.dataset.tab === "relatorio") desenharRelatorio();
  history.replaceState(null, "", "#" + b.dataset.tab);
});
$("#btAnt").onclick = () => ir(-1);
$("#btProx").onclick = () => ir(1);
$("#obs").oninput = () => atualizar({obs: $("#obs").value});
$("#ato").oninput = () => atualizar({ato: $("#ato").value});
$("#revisor").value = estado.revisor || "";
$("#revisor").oninput = () => { estado.revisor = $("#revisor").value; salvar(); };
$("#filtro").onchange = e => { filtro = e.target.value; idx = 0; desenhar(); };
$("#btCSV").onclick = baixarCSV; $("#btCSV2").onclick = baixarCSV;
$("#btMD").onclick = () => baixar("relatorio_triagem.md", markdown(), "text/markdown");
$("#btCopiar").onclick = () => navigator.clipboard && navigator.clipboard.writeText(markdown());
$("#btLimpar").onclick = () => { if (confirm("Apagar todas as marcações guardadas neste navegador?")) { estado.itens = {}; salvar(); idx = 0; desenhar(); } };
document.addEventListener("keydown", e => {
  if (["TEXTAREA","INPUT","SELECT"].includes(e.target.tagName) || e.ctrlKey || e.metaKey || e.altKey) return;
  const mapa = {"1":"irr_sem","2":"irr_com","3":"nao","4":"incerto"};
  if (mapa[e.key]) decidir(mapa[e.key]);
  if (e.key === "ArrowLeft") ir(-1);
  if (e.key === "ArrowRight") ir(1);
});
desenhar();
function abaDoEndereco(){
  const aba = location.hash.slice(1);
  const b = document.querySelector(`[data-tab="${["relatorio","como"].includes(aba) ? aba : "triagem"}"]`);
  if (!b.classList.contains("on")) b.click();
}
addEventListener("hashchange", abaDoEndereco);
abaDoEndereco();
</script>
</body>
</html>
"""

HTML = HTML.replace("@@dados@@", DADOS).replace("@@imgs@@", IMGS)
os.makedirs(DOCS, exist_ok=True)
for destino in (os.path.join(DOCS, "index.html"), os.path.join(SAIDA, "revisao_pivos.html")):
    open(destino, "w", encoding="utf-8").write(HTML)
    print(f"ok: {os.path.normpath(destino)}  ({os.path.getsize(destino) / 1024 / 1024:.1f} MB)")
