# Bancada Cientifica de Estrategias

- Jogo: `loto_facil_sorteio`
- Estrategias: `cauda_convexa, cauda_controlada, agressiva, balanceada, pura`
- Seeds: `7, 21, 42`
- Janelas: `12`
- Jogos por janela: `5`
- Monte Carlo por janela: `200`

## Ranking Geral

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | pura | Vetorial | 29.123 | 1.000 | 0.002869 | -0.769524 | 0.230476 | 1.843 | 0.000 | 4 |
| 2 | cauda_convexa | Vetorial | 27.800 | 0.667 | 0.000092 | -0.760000 | 0.240000 | 3.510 | 0.000 | 2 |
| 3 | agressiva | Genetico | 27.297 | 1.333 | -0.039353 | -0.776190 | 0.223810 | 0.677 | 0.000 | 3 |
| 4 | balanceada | Vetorial | 25.288 | 2.000 | -0.077131 | -0.788572 | 0.211428 | -1.490 | 0.000 | 3 |
| 5 | cauda_controlada | Vetorial | 24.143 | 0.000 | 0.022592 | -0.761147 | 0.238853 | 1.510 | 0.000 | 2 |
| 6 | cauda_controlada | Genetico | 22.232 | 0.333 | 0.004536 | -0.780953 | 0.219047 | -0.157 | 0.000 | 3 |
| 7 | pura | Genetico | 19.383 | 0.667 | -0.051575 | -0.806667 | 0.193333 | -4.657 | 0.000 | 3 |
| 8 | balanceada | Genetico | 14.750 | 0.333 | -0.071575 | -0.795238 | 0.204762 | -2.657 | 0.000 | 3 |
| 9 | cauda_convexa | Genetico | 14.574 | 0.000 | -0.044353 | -0.797143 | 0.202857 | -2.990 | 0.000 | 3 |
| 10 | agressiva | Vetorial | 13.645 | 0.333 | -0.073242 | -0.798095 | 0.201905 | -3.157 | 0.000 | 3 |

## Ranking Genetico

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | agressiva | Genetico | 27.297 | 1.333 | -0.039353 | -0.776190 | 0.223810 | 0.677 | 0.000 | 3 |
| 6 | cauda_controlada | Genetico | 22.232 | 0.333 | 0.004536 | -0.780953 | 0.219047 | -0.157 | 0.000 | 3 |
| 7 | pura | Genetico | 19.383 | 0.667 | -0.051575 | -0.806667 | 0.193333 | -4.657 | 0.000 | 3 |
| 8 | balanceada | Genetico | 14.750 | 0.333 | -0.071575 | -0.795238 | 0.204762 | -2.657 | 0.000 | 3 |
| 9 | cauda_convexa | Genetico | 14.574 | 0.000 | -0.044353 | -0.797143 | 0.202857 | -2.990 | 0.000 | 3 |

## Ranking Vetorial

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | pura | Vetorial | 29.123 | 1.000 | 0.002869 | -0.769524 | 0.230476 | 1.843 | 0.000 | 4 |
| 2 | cauda_convexa | Vetorial | 27.800 | 0.667 | 0.000092 | -0.760000 | 0.240000 | 3.510 | 0.000 | 2 |
| 4 | balanceada | Vetorial | 25.288 | 2.000 | -0.077131 | -0.788572 | 0.211428 | -1.490 | 0.000 | 3 |
| 5 | cauda_controlada | Vetorial | 24.143 | 0.000 | 0.022592 | -0.761147 | 0.238853 | 1.510 | 0.000 | 2 |
| 10 | agressiva | Vetorial | 13.645 | 0.333 | -0.073242 | -0.798095 | 0.201905 | -3.157 | 0.000 | 3 |

## Alertas

| Estrategia | Motor | Severidade | Tipo | Mensagem |
|---|---|---|---|---|
| agressiva | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| agressiva | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.339). |
| agressiva | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.776). |
| agressiva | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| agressiva | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.248). |
| agressiva | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.798). |
| balanceada | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| balanceada | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.356). |
| balanceada | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.795). |
| balanceada | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| balanceada | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.304). |
| balanceada | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.789). |
| cauda_controlada | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_controlada | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.357). |
| cauda_controlada | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.781). |
| cauda_controlada | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_controlada | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.761). |
| cauda_convexa | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_convexa | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.326). |
| cauda_convexa | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.797). |
| cauda_convexa | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_convexa | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.760). |
| pura | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| pura | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.272). |
| pura | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.807). |
| pura | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| pura | Vetorial | media | dependencia_seed | Quadras variam muito entre seeds; resultado pode ser instavel. |
| pura | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.261). |
| pura | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.770). |

## Recomendacao Experimental

Geral: `pura` com motor `Vetorial` (score `29.123453`).
- Genetico: `agressiva` (score `27.297298`)
- Vetorial: `pura` (score `29.123453`)

> O score composto e diagnostico; ele nao deve alimentar o gerador.