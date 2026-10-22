# 1. O pedido e o contexto

## De onde veio

Em outubro de 2026, um servidor da área de recursos hídricos da SEMAD-GO (Secretaria de Estado de Meio Ambiente e Desenvolvimento Sustentável de Goiás) pediu um encontro de tutoria sobre como usar inteligência artificial no trabalho. No formulário, ele descreveu o problema assim:

> **Contexto.** "Minha intenção é dar início em projeto que visa utilizar inteligência artificial e sensoriamento remoto para identificar áreas irrigadas que não possuem autorização (outorga) para tanto."
>
> **Tarefa e dificuldade.** "Atualmente a identificação de áreas irrigadas, principalmente pivôs, é feita manualmente através de observações de imagens de satélite. […] são feitos apenas quando surge uma demanda específica. A ideia aqui seria automatizar essa análise e rodá-la em períodos estratégicos como por exemplo a época de seca no estado de Goiás. […] o foco inicial seria em bacias que apresentam criticidade hídrica."
>
> **Resultado esperado.** "Relatórios padronizados que seriam cruzados com o banco de dados das outorgas."

Para preparar o encontro, Victor Amaral (LAPIG/UFG) fez um teste exploratório com IAs generativas, usando só dados públicos. Este repositório reúne o que saiu desse teste e do encontro.

## O problema, em três partes

O pedido tem três partes, e cada uma tem uma dificuldade diferente:

| Parte | Hoje | Dificuldade |
|---|---|---|
| **Detectar** áreas irrigadas | Feito à mão, olhando imagens, quando surge uma demanda | É o gargalo. Exige imagens de várias datas e um critério que funcione na paisagem de Goiás |
| **Cruzar** com as outorgas | Feito à mão, caso a caso | A base de pivôs e a de outorgas não têm um código que as ligue (ver [cruzamento](03-cruzamento-pivo-outorga.md)) |
| **Relatar** o resultado | Sem formato padronizado | Precisa servir ao processo administrativo, sem concluir irregularidade antes da hora |

## Alguns termos

| Termo | O que é |
|---|---|
| **Outorga** | Autorização do Estado para usar água (captar de um rio, de um poço, fazer um barramento). Em Goiás, em rios de domínio estadual, quem emite é a SEMAD. Em rios federais, a ANA |
| **Pivô central** | Sistema de irrigação que gira em torno de um ponto e desenha um círculo no campo. Aparece muito bem em imagem de satélite |
| **Ponto de captação** | Onde a água é retirada. É o que a outorga registra no mapa, e não a área irrigada |
| **BHO / ottobacia** | Base Hidrográfica Ottocodificada da ANA. Divide os rios em trechos e sub-bacias com um código hierárquico (`cobacia`) |
| **NDVI** | Índice de vegetação calculado com as bandas vermelha e infravermelha. Vai de −1 a 1; vegetação ativa fica acima de 0,6 e solo seco perto de 0,2 |
| **Sentinel-2** | Satélites europeus (programa Copernicus) com imagens gratuitas de 10 m, a cada ~5 dias |
| **AUC** | Medida de quanto um número separa dois grupos. 0,5 = não separa (como sortear); 1 = separa tudo |
| **Nível A/B/C** | Classificação usada no cruzamento: A = outorga compatível perto; B = outorga possível; C = nenhuma outorga localizada pela regra |

## O que este teste é, e o que não é

- É um **teste exploratório**, feito em algumas horas, com IAs escrevendo o código e uma pessoa conferindo cada passo.
- **Não** usa os sistemas internos da SEMAD nem o conhecimento de campo de quem trabalha com esses dados. Com isso, os resultados tendem a ser bem melhores do que os daqui.
- Os números são **preliminares**. Servem para explorar o caminho, não como resultado oficial.
- Nenhum resultado aqui indica que uma área seja irregular. Ver [cuidados](07-proximos-passos-e-cuidados.md#cuidados).
