# 6. Como o teste foi feito

Este é também um exemplo de **como usar IA generativa no trabalho**, que era o tema do encontro. Por isso vale registrar como foi, inclusive os erros.

## As ferramentas

| Ferramenta | Papel |
|---|---|
| **opencode** | Primeira resposta ao pedido. Foi para o lado de redes neurais e treinamento de modelos: correto em tese, mas longe do que dava para fazer com os dados disponíveis |
| **MiniMax** (pelo opencode) | Escreveu e rodou a maior parte do código do cruzamento (`demo_reconciliacao.py`, várias versões) e o teste de detecção pela série temporal |
| **Claude** (Anthropic) | Conferiu cada afirmação das outras IAs nos dados, refez contas, fez as figuras, a apresentação e este repositório |
| **DeepSeek** | Montou a primeira versão da página de triagem, a partir da ideia do ciclo detectar → cruzar → inspecionar → relatório |

O Victor fazia as perguntas, levava a resposta de uma IA para a outra e decidia o que seguir. Em nenhum momento uma IA trabalhou sozinha do começo ao fim.

## A sequência, resumida

1. **Primeira resposta (opencode):** um plano com rede neural, rótulos e treinamento. Útil como visão geral, mas sem olhar os dados que existem.
2. **Os dados existem e são públicos:** achado o servidor de mapas da SEMAD, com pivôs e outorgas. O primeiro cruzamento (pivô sem outorga a até 2 km) saiu em minutos: ~2.550 pivôs.
3. **Rodadas de correção:** cada versão do script era conferida nos dados. Apareceram os pivôs fora de Goiás, as camadas duplicadas, a regra "rio acima" que media a posição no rio, e a regra por sub-bacia que ficou rígida demais. Ver [cruzamento](03-cruzamento-pivo-outorga.md#correções-feitas-no-caminho).
4. **A correção do satélite:** os scripts calculavam o NDVI sem descontar o acréscimo de 1000 das imagens recentes. Pego ao conferir os valores de NDVI com a documentação das imagens.
5. **A detecção é o gargalo:** a própria IA, perguntada se aquilo respondia ao pedido, concluiu que o cruzamento não detecta irrigação nova, e mediu que a série temporal separa os pivôs muito melhor que uma data.
6. **O encontro:** apresentação com o pedido, os dados, o que funcionou, os ajustes e as perguntas.
7. **Depois do encontro:** a ideia do ciclo com inspeção humana, o protótipo de triagem, a comparação 2016 × 2023 e este repositório.

## O que funcionou bem

- Achar e ler dados públicos que nem sempre são conhecidos.
- Escrever código de geoprocessamento em minutos, inclusive para quem não programa.
- Uma IA conferindo a outra: os erros de uma eram pegos pela outra, desde que alguém pedisse para conferir **nos dados**.
- Explorar várias ideias rápido e descartar as que não funcionam.

## O que exigiu cuidado

- **Explicações plausíveis para números errados.** Pivôs a 22 km da outorga mais próxima ganharam uma explicação técnica convincente; na verdade, estavam em Minas Gerais.
- **Afirmações sem conferência.** Uma IA citou uma lei com data de sanção no futuro. Outra disse que o teste de detecção era em Cristalina, mas o recorte estava em Campo Alegre de Goiás e Catalão.
- **Números que mudam a conclusão.** Uma IA retirou a afirmação de que faltam dezenas de milhares de hectares no mapa porque o teste dela não achou pivô novo; a comparação 2016 × 2023 mostra que a ordem de grandeza era plausível.
- **Texto em excesso.** As IAs tendem a escrever mais do que o necessário e a soar mais definitivas do que os dados permitem.

## A lição

Em poucas horas, a IA chegou longe. Cada ajuste veio de alguém **conferindo o dado** e perguntando "o que este número está medindo?". Com o conhecimento de quem trabalha com esses dados e mais tempo, o resultado tende a ser bem melhor do que este primeiro teste.
