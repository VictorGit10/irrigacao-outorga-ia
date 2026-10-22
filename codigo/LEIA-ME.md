# Código

Scripts em Python que fazem o cruzamento pivô × outorga, os testes de detecção, a fila de triagem e as figuras. Foram escritos por IAs (MiniMax, DeepSeek e Claude) e conferidos nos dados; são código de teste, não de produção.

## Instalar

```bash
pip install -r requirements.txt
```

Python 3.10 ou mais novo. No Windows, se o `rasterio` não instalar pelo pip, use o conda (`conda install -c conda-forge rasterio shapely pyproj`).

## Ordem para rodar

| # | Script | O que faz | Precisa de rede | Tempo |
|---|---|---|---|---|
| 1 | `aux_baixar_bho_stream.py` | Baixa os trechos de rio da BHO (237 mil) em streaming e guarda só o necessário em `.cache/bho_trechos.pkl` | sim | alguns minutos, uma vez |
| 2 | `demo_reconciliacao.py` | Baixa as camadas da SEMAD, junta as camadas de pivôs, cruza com as outorgas (níveis A/B/C), agrega por município e, se `NDVI_N` > 0, mede o NDVI de alguns pivôs | sim na 1ª vez | ~1–3 min com cache |
| 3 | `aux_gerar_fila.py` | Monta a fila de triagem: 18 pivôs de nível C, um por município, e faz os primeiros recortes de imagem | sim | alguns minutos |
| 4 | `aux_imagens_fila.py` | Refaz os recortes 2022/2025 escolhendo a imagem sem nuvem sobre o pivô e calcula a série de NDVI (abr–out/2025) dentro e em volta de cada pivô | sim | ~10 min (`PARALELO=4`) |
| 5 | `aux_outorgas_proximas.py` | Acrescenta a cada caso as outorgas de irrigação a até 5 km, em qualquer sub-bacia | não | segundos |
| 6 | `aux_gerar_interface.py` | Gera a página de triagem: `../docs/triagem/index.html` e `saida/revisao_pivos.html` | não | segundos |

## Testes e diagnósticos

| Script | O que mede |
|---|---|
| `aux_deteccao_temporal.py` | Se o NDVI de uma data ou a série da seca separa pivôs de áreas vizinhas (AUC). Preliminar: conta por pixel e **sem** o desconto de 1000 do Sentinel-2 |
| `aux_teste_mudanca.py` | Se a diferença de NDVI entre a seca de 2022 e a de 2025 acha pivôs novos. Não achou; ver `documentacao/04` |
| `aux_dedup_sobreposicao.py` | Quanto as quatro camadas de pivôs se sobrepõem |
| `aux_indicador_cobertura.py` | Atos de outorga por área irrigada mapeada, por município |
| `aux_mapa.py` | Mapa SVG do estado com pivôs e pontos de captação |
| `aux_verificar_texto.py` | Procura caracteres estranhos (chinês, cirílico…) que IAs às vezes deixam no meio do texto |

## Figuras (`figuras/`)

| Script | Gera |
|---|---|
| `dados.py` | Função `camada(nome)` que lê do cache ou baixa do WFS da SEMAD |
| `figuras_apresentacao.py` | Mapas de Goiás, São Marcos e o esquema da regra "rio acima" |
| `figura_cristalina.py` | Recorte de Cristalina com pivôs e captações |
| `figura_satelite.py` | Sentinel-2 em cor natural e NDVI (1º/8/2025) |
| `comparar_2016_2023.py` | Comparação dos mapas de pivôs de 2016 e 2023 e com o MapBiomas 2020 |

As figuras vão para `../docs/apresentacao/img/`.

## Saídas (`saida/`)

| Arquivo | Conteúdo |
|---|---|
| `municipios_por_nivel.csv` | Por município: áreas mapeadas, atos de irrigação e áreas por nível A/B/C |
| `municipios_indice_cobertura.csv` | Por município: atos de outorga por área irrigada mapeada |
| `amostra_para_teste.csv` | 2.373 áreas de 20 municípios com o nível de cada uma. É uma amostra para testar a regra, **não uma lista de irregulares**. Sem nomes nem CPF/CNPJ |
| `fila_revisao.json` | Os 18 casos da triagem, com recortes, série de NDVI e outorgas próximas |
| `chips/` | Recortes Sentinel-2 em cor natural (2022 e 2025) de cada caso |
| `mapa_reconciliacao.svg` | Mapa do estado |
| `revisao_pivos.html` | Cópia local da página de triagem (abre com dois cliques) |

O resultado de `demo_reconciliacao.py` foi gerado em 21/10/2026, antes de algumas correções (por exemplo, o desconto do Sentinel-2 na etapa de NDVI). Rodar de novo pode dar números um pouco diferentes.

## Cache (`.cache/`)

As camadas baixadas ficam em `.cache/` e **não vão para o Git** (~180 MB, e a camada de outorgas traz nomes e CPF/CNPJ). Os scripts baixam de novo quando a pasta não existe.
