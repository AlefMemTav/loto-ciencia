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

- **Dashboard de tendências:** frequências, atrasos, distribuições, testes de uniformidade
  e intervalos de confiança.
- **Validador de apostas:** score de 0 a 100, paridade, soma, distribuição espacial,
  similaridade histórica, geometria e padrões populares.
- **Gerador inteligente:** estatísticas históricas, aleatoriedade criptográfica,
  filtros de qualidade e geração em lote.
- **Fechamentos combinatórios:** cobertura de grupos de 7 a 12 números e estimativa de custo.
- **Auditoria de bolões:** validação em lote, duplicidades, cobertura e relatório de custos.
- **Dados atualizados:** resultados e detalhes de premiação obtidos dos dados oficiais da
  Caixa Econômica Federal.

## Jogos suportados

| Jogo | Universo | Aposta padrão | Densidade |
| --- | ---: | ---: | ---: |
| Mega-Sena | 1–60 | 6 números | 10% |
| Lotofácil | 1–25 | 15 números | 60% |
| Quina | 1–80 | 5 números | 6,25% |
| Lotomania | 1–100 | 50 números | 50% |

> **Densidade** é a proporção entre números escolhidos e números disponíveis. Os
> thresholds de análise são ajustados para cada modalidade.

## Como o score funciona

O score combina critérios técnicos e sinais de popularidade. Entre eles estão soma,
paridade, quadrantes, linhas e colunas, terminações, entropia dos intervalos, distância
de Hamming, geometria do volante, coocorrência, simetria e progressões.

| Score | Classificação | Interpretação |
| ---: | --- | --- |
| 90–100 | Excelente | Distribuição estatisticamente bem equilibrada |
| 70–89 | Bom | Aposta válida |
| 50–69 | Regular | Considere revisar alguns critérios |
| 0–49 | Baixo | Muitos padrões concentrados |

O score mede a qualidade estrutural da combinação; ele **não prevê o resultado** nem
altera a chance de acerto.

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

O mesmo processo é executado automaticamente pelo GitHub Actions. Os resultados são
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
