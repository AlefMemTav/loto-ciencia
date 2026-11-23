<h1 align="center">LotoCiencia</h1>

<p align="center">
  <strong>Não é sorte. É ciência aplicada aos dados.</strong><br>
  Plataforma de análise estatística, validação e geração de apostas para loterias brasileiras.
</p>

<p align="center">
  <a href="https://alefmemtav.github.io/loto-ciencia/">Documentação</a> ·
  <a href="#-funcionalidades">Funcionalidades</a> ·
  <a href="#-instalação">Instalação</a> ·
  <a href="#-uso">Uso</a> ·
  <a href="#-contribuição">Contribuição</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white" alt="Python 3.13 ou superior">
  <img src="https://img.shields.io/badge/Streamlit-1.52%2B-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/github/license/AlefMemTav/loto-ciencia?color=2ea44f" alt="Licença MIT">
  <img src="https://img.shields.io/github/actions/workflow/status/AlefMemTav/loto-ciencia/deploy-mkdocs.yml?label=docs" alt="Build da documentação">
</p>

> **Aviso:** o LotoCiencia não aumenta a probabilidade matemática de acertar uma loteria.
> Todos os números têm a mesma chance teórica de serem sorteados. A ferramenta organiza
> dados históricos, avalia padrões e ajuda a montar apostas de forma mais consciente.
> Loteria é jogo de azar: jogue com responsabilidade.

## Documentação

A documentação técnica e científica está disponível em
**[alefmemtav.github.io/loto-ciencia](https://alefmemtav.github.io/loto-ciencia/)**.
Ela descreve a arquitetura, os modelos estatísticos, o pipeline de geração e os
procedimentos de backtest.

## Funcionalidades

- **Dashboard de tendências:** frequências, atrasos (descritivos, sem falácia do apostador), distribuições geométricas discretas exatas (KS discreto + $\chi^2$ agrupado), testes de uniformidade com correção de população finita e intervalos de predição/confiança via Bootstrap vetorizado.
- **Validador de apostas (15 sinais):** score de 0 a 100, percentis exatos no Modelo Nulo Combinatório (28 métricas vetorizadas), tipicidade em Espaço-Z sem colinearidade (7 dimensões independentes + distância de Mahalanobis descritiva), lookup histórico matricial $O(1)$, geometria 2D calibrada por cauda hipergeométrica exata e modelo econométrico de popularidade medida (Huber-IRLS Ridge + kernel de interações de pares + WLS exponencial + filtro causal de anomalias de arrecadação + quantil conformal 90% + monitor de drift, com $R^2_{\text{CV}}$ de **$0{,}389$ na Lotomania**, **$0{,}601$ na Lotofácil**, **$0{,}719$ na Mega-Sena** e **$0{,}789$ na Quina**).
- **Gerador inteligente, Gatekeeper de EV Ex-Ante e Modo Jogo Real:** torneio fechado de carteiras com calibração estrutural por Cotas de Hamilton ($D_{\text{JS}} \le 0{,}07$), refinamento local 1-opt preservador de buckets, bloqueio anti-divisão de prêmio (incluindo proteção-espelho de 0 acerto na Lotomania), diagnóstico causal de EV Ex-Ante com regime de concursos especiais, limites conformais 90%, Kelly fracionado e comparativo cruzado entre modalidades (`--comparar-modalidades`).
- **Auditoria diária prospectiva e sequencial (`game_day.py`, `conferir.py`, `auditoria_registro.py`):** geração pré-sorteio determinística, conferência automatizada com variância hipergeométrica exata, controle pareado de Rao-Blackwell, rastreamento de rateio realizado contra `data/detalhes/*.csv` e auditoria sequencial *anytime-valid* via e-values/martingale de Ville + calculadora de poder amostral (`python -m app.cli.conferir --auditar`).
- **Fechamentos combinatórios verificados (`matrices.py`):** desenhos de cobertura $C(v,k,t)$ / $L(v,k,t,m)$ exaustivamente verificados para Mega-Sena, Quina e Lotofácil, com seleção de base anti-popular e transparência para Lotomania.
- **Auditoria de bolões (`bolao.py`):** validação em lote, normalização `00 → 100` na Lotomania, duplicidades, cobertura, métricas de portfólio, razão média de rateio e simulador interativo de ágio de 0% a 35% sobre o EV.
- **Dados atualizados:** resultados e detalhes de premiação obtidos dos dados oficiais da Caixa Econômica Federal.

## Jogos suportados

| Jogo | Universo | Aposta padrão | Densidade |
| --- | ---: | ---: | ---: |
| Mega-Sena | 1–60 | 6 números | 10% |
| Lotofácil | 1–25 | 15 números | 60% |
| Quina | 1–80 | 5 números | 6,25% |
| Lotomania | 1–100 | 50 números (sorteio de 20) | 50% |

> **Densidade** é a proporção entre números escolhidos e números disponíveis. Os
> thresholds de análise, a calibração histórica e a proteção anti-divisão (incluindo o reescalonamento hipergeométrico $k/m = 20/50$ e o bilhete-espelho $J^c$ para a faixa de 0 acerto na Lotomania) são ajustados automaticamente para cada modalidade.

## Como o score funciona

O sistema separa estritamente a **função objetivo do gerador** (contínua, calibrada sob o Modelo Nulo Combinatório e o modelo econométrico de popularidade medida com modulação pela elasticidade de Poisson do EV ex-ante) do **validador independente** (auditor de 13 etapas e 15 sinais com correção de Bonferroni). Entre os critérios estão soma (IC Histórico + faixa de predição 95% para bilhete único), paridade, quadrantes, linhas, colunas, moldura, cruz, diagonais, simetria de reflexão, terminações, entropia relativa e regularidade dos intervalos, distância de Hamming, tipicidade de cluster + distância de Mahalanobis e risco empírico de divisão de prêmio com intervalo conformal 90%.

| Score | Classificação | Interpretação |
| ---: | --- | --- |
| 85–100 | Excelente | Distribuição estruturalmente bem equilibrada |
| 70–84 | Muito Bom | Aposta bem alinhada aos padrões típicos |
| 55–69 | Bom | Aposta válida com pequenos desvios estruturais |
| 40–54 | Razoável | Concentração ou padrão popular moderado |
| 0–39 | Fraco | Muitos padrões concentrados ou populares |

O score mede o equilíbrio estrutural e o risco de divisão da combinação; na geração de carteiras, as **Cotas de Hamilton** distribuem os jogos entre as faixas na mesma proporção observada nos sorteios reais.

## Instalação

### Pré-requisitos

- Python 3.13 ou superior
- Git

```bash
git clone https://github.com/AlefMemTav/loto-ciencia.git
cd loto-ciencia

python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Uso

Para iniciar a interface:

```bash
streamlit run main.py
```

A aplicação estará disponível em <http://localhost:8501>.

Para atualizar os resultados e os detalhes de premiação:

```bash
python atualizar_loterias.py
```

Para comparar o EV ex-ante (com IC conformal 90% e Kelly fracionado) entre todas as modalidades ou auditar o histórico do `registro`:

```bash
python -m app.cli.game_day --comparar-modalidades --agio 0.0 --banca 500
python -m app.cli.conferir --registro registro --auditar
```

O processo diário é executado automaticamente pelo GitHub Actions. Os resultados são
salvos em `data/*.xlsx` e os detalhes por faixa em `data/detalhes/*.csv`.

### Exemplo de validação

```python
from app.core.lottery.catalog import MEGASENA
from app.core.validator import validar_jogo

numeros = [5, 17, 28, 35, 48, 59]
relatorio = validar_jogo(numeros, MEGASENA)

print(f"Score: {relatorio['score']}")
print(f"Risco de divisão: {relatorio['risco_divisao']}")
```

## Arquitetura

```text
Streamlit UI (pages/, app/ui/)
        ↓
Serviços e orquestração (app/services/)
        ↓
Núcleo estatístico e geradores (app/core/)
        ↓
Dados históricos (data/*.xlsx, data/detalhes/*.csv)
```

O projeto separa apresentação, serviços, regras de negócio e dados. O núcleo prioriza
funções puras, injeção de dependências e análises ajustadas à densidade de cada jogo.

## Testes

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Contribuição

Contribuições são bem-vindas:

1. Faça um fork do projeto.
2. Crie uma branch para sua alteração.
3. Adicione ou atualize os testes correspondentes.
4. Abra um Pull Request descrevendo a mudança.

## Licença

Este projeto está sob a licença MIT.

## Autor

**AlefMemTav**

- GitHub: [@AlefMemTav](https://github.com/AlefMemTav)

## Agradecimentos

- [Caixa Econômica Federal](https://loterias.caixa.gov.br/) — Dados históricos oficiais
- [Streamlit](https://streamlit.io/) — Framework de UI

<p align="center">
  <strong>Se este projeto foi útil, considere dar uma estrela.</strong>
</p>

<p align="center">
  Made with Statistics
</p>
