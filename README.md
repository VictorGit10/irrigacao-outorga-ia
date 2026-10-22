# Irrigação sem outorga: um primeiro teste com IA

Teste exploratório de como identificar **áreas irrigadas sem outorga de uso da água em Goiás**, usando dados públicos, imagens de satélite e IA generativa. Feito em outubro de 2026 para um encontro de tutoria com um servidor da SEMAD-GO sobre o uso de IA no trabalho.

**Site:** https://victorgit10.github.io/irrigacao-outorga-ia/

| | |
|---|---|
| 🖥️ [Apresentação](https://victorgit10.github.io/irrigacao-outorga-ia/apresentacao/) | os 21 slides do encontro ([PDF](docs/apresentacao/apresentacao.pdf)) |
| 🛰️ [Protótipo de triagem](https://victorgit10.github.io/irrigacao-outorga-ia/triagem/) | página para inspecionar casos e gerar o relatório |
| 📄 [Documentação](documentacao/) | o que foi feito, com os números e as ressalvas |

> **É um teste, não um sistema oficial.** Foi feito em algumas horas, só com dados públicos, sem os sistemas internos da SEMAD e sem o conhecimento de campo de quem trabalha com esses dados. Os números são preliminares, e nenhum resultado aqui indica que uma área seja irregular.

## A ideia em uma figura

```
 1. Detectar          2. Cruzar            3. Fila              4. Inspecionar        5. Relatório
 pivôs nas imagens ─► com as outorgas ──► casos sem outorga ─► uma pessoa olha ───► tabela e texto
 de satélite          por perto            por perto, com       cada caso e marca     prontos para o
 (a cada seca)                             imagens              o que vê              encaminhamento
                                                                (a decisão é humana)
```

O computador faz a parte repetitiva; a pessoa faz a parte que exige julgamento. Cada caso marcado vira também um exemplo para treinar um detector melhor no futuro. É o mesmo princípio do DETER, do INPE: alerta automático, verificação humana e só então o laudo.

**Neste teste:** as etapas 2 a 5 funcionam com dados públicos, numa versão simples. A etapa 1 (detecção) ainda não existe: os pivôs vêm do mapa público da SEMAD, feito à mão com imagens de 2020 a 2023. Foram feitas medições para orientar a detecção.

## O que se aprendeu

| | |
|---|---|
| **Os dados existem e são públicos** | O servidor de mapas da SEMAD tem 5.586 pivôs mapeados e 6.121 outorgas de irrigação, sem login |
| **As duas bases não conversam** | O pivô é uma área; a outorga é um ponto de captação. Nenhum código liga um ao outro, então todo cruzamento automático é aproximado |
| **O primeiro número engana** | ~2.550 pivôs sem outorga a até 2 km, mas parte está fora de Goiás, contada duas vezes, em rio federal ou com captação distante |
| **Uma regra rígida também erra** | Exigir a outorga na mesma sub-bacia deixa 73% sem outorga localizada, mas 41% desses têm uma outorga a até 2 km |
| **Uma imagem não basta** | Numa data de agosto, o NDVI não separa pivô da vegetação vizinha (AUC 0,44); a variação ao longo da seca separa bem melhor (0,84) |
| **O mapa de pivôs é estável** | 93% dos pivôs de 2016 seguem no mesmo lugar em 2023; o que muda é o aparecimento de ~2.400 pivôs novos em sete anos |
| **A detecção é o gargalo** | Para treinar um detector, faltam exemplos conferidos. É isso que a triagem produz |

Detalhes, ressalvas e como cada número foi obtido: [documentação](documentacao/).

## O que tem aqui

```
README.md            este arquivo
CLAUDE.md            contexto completo para assistentes de IA (Claude, ChatGPT, Copilot…)
documentacao/        o pedido, os dados, o cruzamento, a detecção, a triagem, como foi feito e próximos passos
codigo/              scripts em Python (cruzamento, testes de detecção, fila de triagem, figuras)
  saida/             resultados: tabelas por município, amostra, fila de triagem e imagens
apresentacao/        os slides em HTML e o script que monta a versão do site
docs/                o site publicado no GitHub Pages (apresentação e triagem)
```

## Como rodar

Precisa de Python 3.10 ou mais novo.

```bash
cd codigo
pip install -r requirements.txt
python demo_reconciliacao.py      # baixa as camadas da SEMAD e faz o cruzamento (alguns minutos na 1ª vez)
```

A ordem completa dos scripts e o que cada um faz estão em [codigo/LEIA-ME.md](codigo/LEIA-ME.md).

## Usar este repositório com uma IA

Cole o link do repositório no seu assistente de IA (Claude, ChatGPT ou outro) e peça para ele ler o `README.md` e o [`CLAUDE.md`](CLAUDE.md) antes de qualquer coisa. O `CLAUDE.md` traz o contexto completo: o problema, as fontes de dados com os nomes dos campos, a ordem dos scripts, os erros já encontrados e os cuidados. Exemplos de pedidos:

- "Adapte a fila de triagem para a bacia do Meia Ponte."
- "Refaça o teste de detecção pela série temporal contando por pivô e com a correção do Sentinel-2."
- "Inclua a camada `pivos_araguaia_go_2025` no cruzamento e me diga o que muda."

## Fontes e créditos

- Pivôs, outorgas, bacias e limites: servidor público de mapas da SEMAD-GO (SIGA).
- Imagens: Sentinel-2 L2A, programa Copernicus (ESA/Comissão Europeia), via Microsoft Planetary Computer.
- Área irrigada 2020: MapBiomas, pela camada publicada no SIGA.
- Código escrito por IAs (MiniMax, DeepSeek e Claude) com orientação e conferência de Victor Amaral (LAPIG/UFG). Ver [como o teste foi feito](documentacao/06-como-o-teste-foi-feito.md).

O código está sob a licença MIT (ver [LICENSE](LICENSE)). Os dados pertencem às suas fontes.
