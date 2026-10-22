# Contexto para assistentes de IA

Este arquivo é para o assistente de IA (Claude, ChatGPT, Copilot ou outro) que for ajudar alguém com este repositório. Leia-o inteiro antes de responder ou mexer em qualquer coisa. Ele resume o que está na pasta `documentacao/`; na dúvida, a documentação é a referência.

## Do que se trata

Um **teste exploratório**, de outubro de 2026, sobre como identificar **áreas irrigadas sem outorga de uso da água em Goiás** com sensoriamento remoto e IA. Nasceu de um pedido de um servidor da área de recursos hídricos da SEMAD-GO, que quer automatizar uma análise hoje feita à mão: achar pivôs nas imagens, cruzar com o banco de outorgas e gerar relatórios padronizados, começando pelas bacias com criticidade hídrica e rodando em épocas estratégicas como a seca.

O teste foi feito em algumas horas, com IAs escrevendo o código e uma pessoa (Victor Amaral, LAPIG/UFG) conferindo cada passo. **Não é um sistema oficial**, não usa dados internos da SEMAD, e os números são preliminares.

Quem provavelmente está pedindo ajuda é alguém da SEMAD, com conhecimento de recursos hídricos e geoprocessamento, que pode não ser programador. Explique em português, sem jargão de programação desnecessário, e mostre o que muda antes de mudar.

## O desenho proposto (o ciclo)

1. **Detectar** pivôs nas imagens de satélite, de tempos em tempos. *Ainda não existe.* Hoje os pivôs vêm do mapa público da SEMAD (`pivos_2020_2023_final`, feito à mão com imagens de 2020 a 2023).
2. **Cruzar** os pivôs com as outorgas de irrigação. *Versão aproximada em `codigo/demo_reconciliacao.py`.*
3. **Montar uma fila** com os casos sem outorga por perto, com imagens. *`codigo/aux_gerar_fila.py`, `aux_imagens_fila.py`, `aux_outorgas_proximas.py`.*
4. **Inspeção humana** de cada caso. *Página `docs/triagem/index.html`, gerada por `codigo/aux_gerar_interface.py`.*
5. **Relatório estruturado** com as marcações. *Gerado pela própria página (Markdown e CSV).*

Princípio: o computador faz a parte repetitiva; a pessoa decide. Cada marcação vira um exemplo conferido, que falta hoje para treinar um detector.

## Mapa do repositório

| Caminho | O que é |
|---|---|
| `README.md` | Visão geral para pessoas |
| `documentacao/01..07-*.md` | Documentação completa, em ordem de leitura |
| `codigo/LEIA-ME.md` | O que cada script faz e a ordem para rodar |
| `codigo/demo_reconciliacao.py` | Cruzamento pivô × outorga, com níveis A/B/C |
| `codigo/aux_*.py` | Fila de triagem, testes de detecção, diagnósticos, mapa |
| `codigo/figuras/` | Figuras da apresentação e a comparação 2016 × 2023 |
| `codigo/saida/` | Resultados (CSV, JSON, SVG, recortes de imagem) |
| `codigo/.cache/` | Camadas baixadas (não vai para o Git; os scripts baixam de novo) |
| `apresentacao/slides/*.html`, `deck.json` | Slides de 1920×1080 com estilos em linha (sem as notas do apresentador); `montar.py` gera o site e o PDF; `captura_triagem.py` tira a imagem da tela de triagem |
| `docs/` | Site do GitHub Pages: `index.html`, `apresentacao/`, `triagem/` |

## Dados (todos públicos, sem login)

- **WFS da SEMAD-GO:** `https://siga.meioambiente.go.gov.br/geoserver/ows` (prefixo das camadas: `geonode:`).
  - `pivos_2020_2023_final`: 5.586 pivôs. Sem data por pivô. Colunas `id_2`, `cod_ibge`, `municipio`, `area_ha`. A soma de `area_ha` (~305 mil ha) não bate com a área dos polígonos (~373 mil ha).
  - `Pivos_2016` (3.565), `Area_Irrigada_Bacia_Sao_Marcos` (1.663, **812 fora de Goiás**), `pivos_alto_sao_marcos` (713, Planet 2026), `pivos_araguaia_go_2025` (não usada ainda), `areas_irrigadas_alto_meia_ponte` (196), `area_irrigada_2019`/`2020` (MapBiomas).
  - `vw_usos_outorgados_publico`: 47.856 atos; filtro de irrigação `fin_tfn_ds LIKE '%IRRIGA%'` → 6.121. Campos: `int_nu_ato`, `int_latitude`, `int_longitude`, `int_ds` (tipo de captação), `int_sit_uso`, `situacao_ato`, `sir_ar_irrigada` (só 10% preenchido), `bho_cobacia`, `bho_dedominial`, `municipio`. **Também traz `requerente` e `cpf_cnpj`: nunca leve essas colunas para saídas, figuras, páginas ou para uma IA na nuvem.**
  - `bho_goias` (trechos de rio da BHO), `municipio2022`, `limite_estadual`, `bacias_criticas` (8).
- **Sentinel-2 L2A** no Microsoft Planetary Computer: STAC `https://planetarycomputer.microsoft.com/api/stac/v1`, coleção `sentinel-2-l2a`; token da coleção em `https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a`.

Detalhes: `documentacao/02-dados-publicos.md`.

## Armadilhas já encontradas (não repita)

1. **Acréscimo de 1000 no Sentinel-2.** Imagens com `s2:processing_baseline` ≥ 04.00 (desde jan/2022) precisam de `valor − 1000` antes do NDVI. Sem isso, o NDVI sai baixo e pivôs verdes parecem secos. `aux_imagens_fila.py` e `figuras/figura_satelite.py` fazem certo; `aux_deteccao_temporal.py` e `demo_reconciliacao.py` (etapa de NDVI) **ainda não**.
2. **Pivôs fora de Goiás.** A camada de São Marcos inclui Minas Gerais e DF, onde a outorga é de outro órgão. Filtre pelo limite estadual.
3. **Camadas sobrepostas.** As quatro camadas de pivôs descrevem muitas vezes os mesmos pivôs. Junte por sobreposição real de polígonos, não por coordenada.
4. **"Qualquer outorga rio acima"** mede a posição do pivô no rio, não a documentação. Não use.
5. **Mesma sub-bacia é rígido demais**: 41% dos casos sem outorga localizada têm uma outorga a até 2 km em outra sub-bacia.
6. **Nome do campo do ato:** é `int_nu_ato` (havia um `int_num_ato` errado na fila; corrigido).
7. **Assinar arquivo por arquivo no Planetary Computer** esbarra no limite de pedidos (até ~27 s por pedido). Use o token da coleção.
8. **Uma data não basta para detectar** (AUC 0,44). Use a série da estação seca.
9. **Polígonos incompletos.** Alguns pivôs do mapa de 2023 são só o contorno (um anel fino) ou um pedaço do círculo. `aux_imagens_fila.py` trata isso e avisa na página.
10. **Explicações plausíveis para números errados.** Antes de explicar um número estranho, confira se o dado está certo (foi assim que os pivôs fora de Goiás apareceram).

## Regras para mexer aqui

- **Escreva em português**, em tom de teste exploratório: sem afirmar mais do que os dados mostram, sem chamar casos de "irregulares" ou "infratores". "Nível C" é "nenhuma outorga localizada pela regra", nunca "sem outorga".
- **Confira nos dados** qualquer número antes de escrevê-lo. Se não conferiu, diga que não conferiu.
- **Sem dados pessoais**: nada de `requerente` ou `cpf_cnpj` em saídas, páginas, figuras ou mensagens.
- **Não cite lei, norma ou artigo sem ter lido a fonte.**
- Mantenha a página de triagem como **um arquivo HTML só, sem servidor nem bibliotecas externas**, que funciona offline.
- Depois de mudar código que gera saídas, rode o script e confira a saída, não só a leitura do código.

## Como rodar

```bash
cd codigo
pip install -r requirements.txt
python aux_baixar_bho_stream.py       # BHO em streaming (rodar uma vez, antes do cruzamento; ~15 MB no cache)
python demo_reconciliacao.py          # cruzamento; baixa as camadas para .cache/ (NDVI_N=0 pula a etapa de imagem)
python aux_gerar_fila.py              # fila de triagem (18 casos de nível C)
python aux_imagens_fila.py            # recortes 2022/2025 e série de NDVI (rede; ~10 min com PARALELO=4)
python aux_outorgas_proximas.py       # outorgas a até 5 km de cada caso
python aux_gerar_interface.py         # gera docs/triagem/index.html
cd ../apresentacao && python montar.py --pdf   # site e PDF da apresentação
```

## Resultados principais (para citar com as ressalvas)

| Medida | Valor | Onde |
|---|---|---|
| Pivôs sem nenhuma outorga a até 2 km (cruzamento ingênuo) | ~2.550 pivôs, ~139 mil ha | documentacao/03 |
| Áreas únicas após juntar as camadas (só Goiás) | 5.817 | documentacao/02 |
| Níveis A / B / C (mesma sub-bacia) | 1.571 / 3 / 4.243 | documentacao/03 |
| Nível C com outorga a até 2 km em outra sub-bacia | 41% (amostra de 2.373) | documentacao/03 |
| AUC: NDVI de uma data × desvio-padrão da série | 0,44 × 0,84 (preliminar) | documentacao/04 |
| Pivôs de 2016 ainda no mapa de 2023 | 93% | documentacao/02 |
| Pivôs novos de 2016 a 2023 | ~2.435, ~143 mil ha | documentacao/02 |
| Cobertura do MapBiomas 2020 sobre os pivôs de 2023 | 67% da área | documentacao/02 |

## Perguntas em aberto

- Os sistemas internos de outorga têm o polígono da área irrigada, o número do CAR ou do processo ligado ao pivô? (Resolveria o cruzamento.)
- Como a SEMAD faz hoje a descoberta de área irrigada sem outorga, e que documento sai no fim? (O relatório da triagem deveria seguir esse formato.)
- Quanto tempo as atualizações manuais do mapa (Araguaia 2025, Alto São Marcos 2026) levaram?
- Que ferramentas e que IA podem ser usadas no trabalho, e com que regras?

## Próximos passos possíveis

Ver `documentacao/07-proximos-passos-e-cuidados.md`. Em resumo: usar a triagem numa bacia crítica; descobrir o código de ligação pivô × outorga; testar um detector pela série temporal treinado com os casos marcados; procurar pivôs novos (MapBiomas, série de imagens, camada do Araguaia 2025); só então pensar num piloto em servidor da SEMAD.
