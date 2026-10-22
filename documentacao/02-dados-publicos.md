# 2. Os dados públicos usados

Tudo aqui vem de fontes públicas, sem login e sem custo. Consultas feitas entre 21 e 22/10/2026; os números podem mudar quando as fontes forem atualizadas.

## Servidor de mapas da SEMAD-GO (SIGA)

- Endereço WFS: `https://siga.meioambiente.go.gov.br/geoserver/ows`
- Lista de camadas: `?service=WFS&version=2.0.0&request=GetCapabilities` (137 camadas em out/2026)
- Baixar uma camada em GeoJSON: `?service=WFS&version=2.0.0&request=GetFeature&typeNames=geonode:<camada>&outputFormat=application/json&srsName=EPSG:4326`

### Camadas de áreas irrigadas

| Camada | O que é | Feições | Observações |
|---|---|---|---|
| `pivos_2020_2023_final` | "Pivôs Centrais 2023 – SEMAD": pivôs mapeados por inspeção visual em imagens PlanetScope (4,7 m) | 5.586 | Principal camada usada. Não tem data por pivô; a data-base é 2020–2023. A soma da coluna `area_ha` dá ~305 mil ha, mas a área dos polígonos dá ~373 mil ha: alguns pivôs estão com a área faltando ou diferente na tabela. Alguns polígonos são só o contorno do pivô ou um pedaço dele (2 dos 18 casos da triagem) |
| `Pivos_2016` | Pivôs instalados em Goiás e no DF até 2016 (Informe Técnico nº 24/2017) | 3.565 | Usada para medir quanto o mapa muda com o tempo |
| `Area_Irrigada_Bacia_Sao_Marcos` | Áreas irrigadas da alta bacia do São Marcos | 1.663 | **812 estão fora de Goiás** (Minas Gerais e DF) |
| `pivos_alto_sao_marcos` | Pivôs do Alto São Marcos: base ANA 2024, atualizada com Planet 2026 | 713 | Tem a cultura de cada pivô |
| `pivos_araguaia_go_2025` | Pivôs da bacia do Araguaia, atualizados com Planet 2025 | — | Achada depois do teste; **ainda não usada** |
| `areas_irrigadas_alto_meia_ponte` | Áreas irrigadas do Alto Meia Ponte | 196 | |
| `area_irrigada_2019`, `area_irrigada_2020` | Área irrigada do MapBiomas para Goiás | 3.484 (2020) | Só o polígono, sem classe |

As quatro primeiras camadas de pivôs se sobrepõem: muitas descrevem os mesmos pivôs com desenhos um pouco diferentes. Juntando por sobreposição real de polígonos, 7.340 polígonos viram 5.817 áreas únicas.

### Outorgas

| Camada | O que é | Feições |
|---|---|---|
| `vw_usos_outorgados_publico` | Atos de outorga e registros de uso da água, com o ponto de captação | 47.856 no total; **6.121 de irrigação** |

Campos úteis (nomes reais da camada): `int_nu_ato` (número do ato), `int_latitude`/`int_longitude` (ponto de captação), `int_ds` (tipo de captação: superficial, em barragem, subterrânea, barramento), `int_sit_uso` (instalado / não instalado), `situacao_ato`, `fin_tfn_ds` (finalidade), `sir_ar_irrigada` (área irrigada declarada), `bho_cobacia` (sub-bacia da BHO), `bho_dedominial` (domínio do rio: estadual ou federal), `municipio`.

O que os dados de outorga mostram sozinhos:

- Só **585 dos 6.121** atos de irrigação (10%) têm a área irrigada preenchida. Por isso não dá para comparar, na maior parte dos casos, a área vista no satélite com a área autorizada.
- **3.569** estão marcados como instalados e **2.518** como não instalados.
- Só **42** estão em rio federal: as outorgas da ANA não estão nessa base.

> **Atenção:** a camada traz o nome do requerente e o CPF/CNPJ (o CPF vem mascarado; o CNPJ, completo). Os scripts deste repositório **não** levam essas colunas para nenhuma saída. Se for usar a camada com uma IA na nuvem, retire essas colunas antes.

### Outras camadas usadas

| Camada | Para quê |
|---|---|
| `bho_goias` | Trechos de rio da BHO (237 mil), para achar a sub-bacia de cada pivô |
| `municipio2022` | Limites municipais |
| `limite_estadual` | Limite de Goiás |
| `bacias_criticas` | As 8 bacias com criticidade hídrica |

## Imagens Sentinel-2

- Coleção `sentinel-2-l2a` no **Microsoft Planetary Computer**: busca STAC em `https://planetarycomputer.microsoft.com/api/stac/v1` e token público de leitura em `https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a`.
- Resolução de 10 m (bandas B02, B03, B04, B08) e 20 m (banda SCL, que classifica nuvem e sombra).
- **Cuidado importante:** desde o início de 2022 (processing baseline 04.00), os valores vêm com um acréscimo fixo de 1000. Sem descontar, o NDVI sai baixo demais. Num recorte de 79 pivôs em Cristalina (13/8/2025), a conta sem o desconto apontava 74 pivôs secos; com o desconto, 50. Os scripts novos (`aux_imagens_fila.py`) já descontam; o `aux_deteccao_temporal.py` ainda não.
- Pedir um token para cada arquivo esbarra no limite de pedidos do serviço (cada pedido chegou a levar 27 s). Usar o token da coleção, que vale para todos os arquivos.

## Comparações entre mapas

Medidas feitas com `codigo/figuras/comparar_2016_2023.py`, só dentro de Goiás:

| Comparação | Resultado |
|---|---|
| Pivôs de 2016 que continuam no mapa de 2023 | 3.107 de 3.326 (93%) |
| Deslocamento do centro entre os dois mapas | mediana de 50 m (diferença de desenho, não de lugar) |
| Pivôs de 2023 que não existiam em 2016 | 2.435, cerca de 143 mil ha (~20 mil ha por ano) |
| Área dos pivôs de 2023 coberta pelo MapBiomas 2020 | 67% |
| Área irrigada do MapBiomas 2020 fora dos pivôs de 2023 | 5% |

O que isso indica: **pivô quase não muda de lugar**. O mapa funciona como um cadastro estável, e a mudança de um ano para outro é o aparecimento de pivôs novos. O MapBiomas raramente marca como irrigado algo que não é pivô no mapa da SEMAD, mas deixa de fora uma parte deles (em parte porque o mapa de 2023 inclui pivôs abertos entre 2021 e 2023).
