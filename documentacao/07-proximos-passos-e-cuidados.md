# 7. Próximos passos, perguntas e cuidados

## Possíveis próximos passos

Em ordem sugerida, mas a decisão é de quem vai tocar o trabalho:

1. **Usar a triagem com casos reais de uma bacia crítica.** Revisar algumas dezenas de casos e ver se o relatório serve ao trabalho. Anotar quanto tempo leva cada caso.
2. **Descobrir o código que liga pivô e outorga** nos sistemas internos (polígono da área irrigada, número do CAR, número do processo). Isso resolve a maior fonte de erro do cruzamento.
3. **Testar a detecção numa bacia crítica:** série de imagens da seca e um classificador simples, treinado com os casos marcados na triagem e com os mapas feitos à mão pela SEMAD.
4. **Achar pivôs novos:** comparar o mapa público com o MapBiomas Irrigação e com a série de imagens dos anos recentes. Incluir a camada `pivos_araguaia_go_2025`, que ainda não foi usada.
5. **Piloto:** se os passos anteriores funcionarem, levar a triagem para um servidor da SEMAD, com login, banco de dados e histórico.

| Fase | O que é | Sinal de que funcionou |
|---|---|---|
| 1. Triagem | uma bacia, uma estação seca, sem instalar nada | dezenas de casos revisados e um relatório útil |
| 2. Piloto | fila periódica, banco, login, auditoria | algumas centenas de casos marcados; taxa de acerto do cruzamento medida |
| 3. Detector | série temporal e classificador treinado com as marcações | acerto medido contra os casos conferidos e contra o mapa feito à mão |

Uma parte desse caminho (a detecção, por exemplo) pode virar tema de pesquisa de pós-graduação.

## Perguntas em aberto

- Como uma área irrigada sem outorga é descoberta hoje? Que documento sai no fim?
- As atualizações do mapa de pivôs de 2025 (Araguaia) e 2026 (Alto São Marcos) foram feitas à mão? Quanto tempo levaram?
- O sistema de outorga tem o polígono da área irrigada ou o número do CAR?
- Que ferramentas estão disponíveis no trabalho (QGIS, Python, Google Earth Engine)? Que IA pode ser usada, e com que regras?
- Nas bacias críticas, a captação é mais superficial ou por poço? Quanto está em rio federal?
- A soma da coluna de área do mapa de 2023 dá ~305 mil ha, mas a área dos polígonos dá ~373 mil ha. Qual número a SEMAD usa?
- Quem conferiria os casos apontados, e quanto tempo essa pessoa tem?

## Cuidados

- **Não é lista de infratores.** A automação aponta casos para conferir. Quem verifica, decide e autua é o órgão, no processo, com contraditório.
- **Verde não prova irrigação.** A safrinha pode estar verde em agosto. Comparar com o entorno e olhar várias datas.
- **Sem outorga localizada não é sem outorga.** Pode ser outorga da ANA, captação distante, poço ou barramento compartilhado.
- **Dados pessoais fora de IA pública.** A camada de outorgas (e o CAR) traz nomes e CNPJ. Trabalhar com tabelas sem essas colunas quando usar IA na nuvem.
- **Conferir antes de citar.** Lei, norma, número ou artigo vindo de IA só entra num documento depois de lido na fonte.
