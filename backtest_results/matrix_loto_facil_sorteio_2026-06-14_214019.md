# Bancada Cientifica de Estrategias

- Jogo: `loto_facil_sorteio`
- Estrategias: `cauda_convexa, cauda_controlada, pura, balanceada`
- Seeds: `7, 21, 42, 77, 101`
- Janelas: `24`
- Jogos por janela: `1`
- Monte Carlo por janela: `500`

## Ranking Geral

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cauda_convexa | Vetorial | 31.566 | 0.800 | 0.035668 | -0.752857 | 0.247143 | 0.952 | 1.000 | 3 |
| 2 | cauda_controlada | Vetorial | 30.484 | 0.400 | 0.074835 | -0.764286 | 0.235714 | 0.551 | 1.000 | 3 |
| 3 | cauda_convexa | Genetico | 24.992 | 0.200 | 0.025668 | -0.760000 | 0.240000 | 0.702 | 1.000 | 3 |
| 4 | balanceada | Vetorial | 23.599 | 0.000 | 0.046501 | -0.767143 | 0.232857 | 0.452 | 1.000 | 3 |
| 5 | cauda_controlada | Genetico | 19.884 | 0.800 | -0.025165 | -0.764286 | 0.235714 | 0.551 | 1.000 | 3 |
| 6 | balanceada | Genetico | 18.778 | 0.200 | -0.010998 | -0.804286 | 0.195714 | -0.849 | 1.000 | 3 |
| 7 | pura | Genetico | 18.703 | 1.000 | -0.062665 | -0.780000 | 0.220000 | 0.002 | 1.000 | 4 |
| 8 | pura | Vetorial | 8.631 | 0.000 | -0.055998 | -0.805714 | 0.194286 | -0.898 | 1.000 | 3 |

## Ranking Genetico

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | cauda_convexa | Genetico | 24.992 | 0.200 | 0.025668 | -0.760000 | 0.240000 | 0.702 | 1.000 | 3 |
| 5 | cauda_controlada | Genetico | 19.884 | 0.800 | -0.025165 | -0.764286 | 0.235714 | 0.551 | 1.000 | 3 |
| 6 | balanceada | Genetico | 18.778 | 0.200 | -0.010998 | -0.804286 | 0.195714 | -0.849 | 1.000 | 3 |
| 7 | pura | Genetico | 18.703 | 1.000 | -0.062665 | -0.780000 | 0.220000 | 0.002 | 1.000 | 4 |

## Ranking Vetorial

| Rank | Estrategia | Motor | Score | Quadras | Delta acertos | ROI | Retorno | Delta receita | Max exp | Alertas |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | cauda_convexa | Vetorial | 31.566 | 0.800 | 0.035668 | -0.752857 | 0.247143 | 0.952 | 1.000 | 3 |
| 2 | cauda_controlada | Vetorial | 30.484 | 0.400 | 0.074835 | -0.764286 | 0.235714 | 0.551 | 1.000 | 3 |
| 4 | balanceada | Vetorial | 23.599 | 0.000 | 0.046501 | -0.767143 | 0.232857 | 0.452 | 1.000 | 3 |
| 8 | pura | Vetorial | 8.631 | 0.000 | -0.055998 | -0.805714 | 0.194286 | -0.898 | 1.000 | 3 |

## Alertas

| Estrategia | Motor | Severidade | Tipo | Mensagem |
|---|---|---|---|---|
| balanceada | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| balanceada | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.572). |
| balanceada | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.804). |
| balanceada | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| balanceada | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.622). |
| balanceada | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.767). |
| cauda_controlada | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_controlada | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.561). |
| cauda_controlada | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.764). |
| cauda_controlada | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_controlada | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.395). |
| cauda_controlada | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.764). |
| cauda_convexa | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_convexa | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.564). |
| cauda_convexa | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.760). |
| cauda_convexa | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| cauda_convexa | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.395). |
| cauda_convexa | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.753). |
| pura | Genetico | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| pura | Genetico | media | dependencia_seed | Quadras variam muito entre seeds; resultado pode ser instavel. |
| pura | Genetico | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.530). |
| pura | Genetico | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.780). |
| pura | Vetorial | alta | ic_cruza_zero | IC95 medio do delta de acertos cruza ou toca zero. |
| pura | Vetorial | media | calibracao_artificial | Distribuicao de score estrutural distante do alvo (JS 0.572). |
| pura | Vetorial | baixa | roi_negativo | ROI medio negativo no modelo de premios configurado (-0.806). |

## Recomendacao Experimental

Geral: `cauda_convexa` com motor `Vetorial` (score `31.565943`).
- Genetico: `cauda_convexa` (score `24.992488`)
- Vetorial: `cauda_convexa` (score `31.565943`)

> O score composto e diagnostico; ele nao deve alimentar o gerador.