<p align="center">
  <img src="assets/images/logo.png" alt="LotoScience Pro" width="200" />
</p>

<h1 align="center">🎱 LotoScience Pro</h1>

<p align="center">
  <strong>Não é Sorte, é Ciência.</strong><br>
  Plataforma de engenharia estatística para análise, validação e geração de apostas em loterias brasileiras.
</p>

<p align="center">
  <a href="#-funcionalidades">Funcionalidades</a> •
  <a href="#-jogos-suportados">Jogos</a> •
  <a href="#-instalação">Instalação</a> •
  <a href="#-uso">Uso</a> •
  <a href="#-arquitetura">Arquitetura</a> •
  <a href="#-api">API</a> •
  <a href="#-contribuição">Contribuição</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/streamlit-1.40+-red.svg" alt="Streamlit" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT" />
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status Active" />
</p>

---

## ⚠️ Aviso Importante

> **Este sistema NÃO aumenta a probabilidade de ganhar na loteria.**
> 
> Todos os números têm a mesma chance teórica de serem sorteados. O LotoScience Pro é uma ferramenta de **análise estatística** que melhora a qualidade da distribuição, detecta padrões populares (risco de divisão de prêmio) e organiza apostas de forma inteligente.
> 
> **Loteria é jogo de azar. Jogue com responsabilidade.**

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Jogos Suportados](#-jogos-suportados)
- [Como Funciona o Score](#-como-funciona-o-score)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Arquitetura](#-arquitetura)
- [API REST](#-api-rest)
- [Tecnologias](#-tecnologias)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

---

## ✨ Funcionalidades

### 📊 Dashboard de Tendências
Visualização em tempo real com gráficos interativos:
- **Números Quentes**: Dezenas mais frequentes nos últimos sorteios
- **Números Frios**: Dezenas com maior atraso estatístico
- **Análise de Poisson**: Distribuição de terminações (finais)
- **Teste Chi-Quadrado**: Validação de uniformidade estatística
- **Intervalos de Confiança**: IC80% e IC95% para soma dos números

### 🧪 Validador de Apostas
Análise completa de qualquer jogo com score de 0 a 100:
- Validação de soma (Curva Gaussiana)
- Equilíbrio par/ímpar
- Distribuição por quadrantes e linhas
- Detecção de padrões populares (risco de divisão)
- Análise de similaridade com sorteios anteriores (Distância de Hamming)
- Análise geométrica (moldura, miolo, cruz, diagonais)
- Detecção de progressões aritméticas e simetrias

### 🤖 Gerador Inteligente
Algoritmo híbrido que combina:
- Estatísticas históricas (frequência, atrasos)
- Aleatoriedade controlada (cryptographic random)
- Filtros de qualidade automáticos
- Geração em lote com score mínimo configurável

### 📦 Fechamentos (Wheelings)
Combinatória matemática para grupos:
- Geração de todas as combinações possíveis
- Suporte de 7 a 12 números base
- Cálculo automático de custo total
- Análise de cobertura estatística

### 👥 Auditoria de Bolões
Ferramenta para grupos e apostadores:
- Validação em lote de múltiplos jogos
- Detecção de duplicatas
- Análise de cobertura do grupo
- Relatório de custo total
- Identificação de jogos com erros

---

## 🎰 Jogos Suportados

| Jogo | Números | Escolha | Densidade | Status |
|------|---------|---------|-----------|--------|
| **Mega-Sena** | 1-60 | 6 | 10% | ✅ Completo |
| **Lotofácil** | 1-25 | 15 | 60% | ✅ Completo |
| **Quina** | 1-80 | 5 | 6.25% | ✅ Completo |
| **Lotomania** | 1-100 | 50 | 50% | ✅ Completo |

> **Densidade** = Proporção de números escolhidos vs disponíveis. O sistema ajusta automaticamente os thresholds de análise baseado na densidade de cada jogo.

---

## 🧠 Como Funciona o Score

O sistema atribui um score de **0 a 100** para cada aposta baseado em múltiplos pilares estatísticos:

### Análises Técnicas

| Critério | Descrição | Penalidade Máxima |
|----------|-----------|-------------------|
| **Soma Gaussiana** | Soma deve estar no intervalo de confiança histórico | -25 pts |
| **Paridade** | Equilíbrio entre números pares e ímpares | -25 pts |
| **Quadrantes** | Distribuição espacial no volante | -20 pts |
| **Linhas/Colunas** | Cobertura vertical e horizontal | -10 pts |
| **Finais** | Terminações dos números (0-9) | -15 pts |

### Análises Avançadas

| Critério | Descrição | Penalidade Máxima |
|----------|-----------|-------------------|
| **Entropia Shannon** | Aleatoriedade dos gaps entre números | -25 pts |
| **Hamming Distance** | Similaridade com sorteios passados | -20 pts |
| **Geometria** | Padrões no volante (moldura, cruz, X) | -15 pts |
| **Co-ocorrência** | Pares que raramente saem juntos | -15 pts |
| **Simetria** | Pares simétricos no volante | -10 pts |
| **Motifs** | Progressões aritméticas detectadas | -20 pts |

### Análise de Popularidade

| Critério | Descrição | Efeito |
|----------|-----------|--------|
| **Sequências** | Muitos números consecutivos | ⚠️ Risco divisão |
| **Datas** | Concentração em 1-31 | ⚠️ Risco divisão |
| **Lost Numbers** | Padrão 4-8-15-16-23-42 | ⚠️ Risco divisão |
| **Pares Populares** | Combinações muito frequentes | ⚠️ Risco divisão |

### Classificação Final

| Score | Classificação | Recomendação |
|-------|---------------|--------------|
| 90-100 | 🏆 Excelente | Aposta de alta qualidade |
| 70-89 | ✅ Bom | Aposta válida |
| 50-69 | ⚠️ Regular | Considere ajustes |
| 0-49 | ❌ Ruim | Não recomendado |

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- pip (gerenciador de pacotes)
- Git

### Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/AlefMemTav/loto-science.git
cd loto-science

# 2. Crie um ambiente virtual
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute a aplicação
streamlit run main.py
```

### Atualização dos resultados e detalhes de premiação

`python atualizar_loterias.py` (também roda no GitHub Actions) atualiza os `.xlsx` com os
novos sorteios e grava, em `data/detalhes/<loteria>_detalhes.csv`, os dados que o Excel não
tem: ganhadores e prêmio por faixa, valor arrecadado, acumulado, estimativa do próximo
concurso e local dos ganhadores. Concursos antigos são completados aos poucos
(`LIMITE_BACKFILL`, padrão 100 por loteria a cada execução).

### Usando Docker

```bash
# Build da imagem
docker build -t lotoscience .

# Executar container
docker run -p 8501:8501 lotoscience
```

---

## 💻 Uso

### Interface Web (Streamlit)

```bash
streamlit run main.py
```

Acesse: `http://localhost:8501`

### API REST (FastAPI)

```bash
python run_api.py
```

Acesse: `http://localhost:8000/docs` (Swagger UI)

### Exemplos de Uso

#### Validar um Jogo (Python)

```python
from app.core.lottery.catalog import MEGASENA
from app.core.validator import validar_jogo

numeros = [5, 17, 28, 35, 48, 59]
report = validar_jogo(numeros, MEGASENA)

print(f"Score: {report['score']}")
print(f"Risco de Divisão: {report['risco_divisao']}")
```

#### Validar via API

```bash
curl -X POST "http://localhost:8000/games/mega_sena/validate" \
  -H "Content-Type: application/json" \
  -d '{"numeros": [5, 17, 28, 35, 48, 59]}'
```

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                      │
├─────────────────────────────┬───────────────────────────────┤
│      Streamlit UI           │         FastAPI REST          │
│    (pages/, app/ui/)        │        (app/api/)             │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                          │
│                   (app/services/)                            │
│              LotteryService (cache + orchestration)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        CORE LAYER                            │
├─────────────────────────────┬───────────────────────────────┤
│      app/core/              │    app/core/statistics/       │
│  • validator.py             │  • basic.py                   │
│  • generator.py             │  • distributions.py           │
│  • lottery/                 │  • geometry.py                │
│    - models.py              │  • similarity.py              │
│    - catalog.py             │  • temporal.py                │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                            │
│                      (data/*.xlsx)                           │
│            Historical lottery results from Caixa             │
└─────────────────────────────────────────────────────────────┘
```

### Princípios de Design

- **Separation of Concerns**: UI, serviços e core são independentes
- **Dependency Injection**: Serviços injetados nas camadas superiores
- **Pure Functions**: Core estatístico sem side effects
- **Density-Aware Analysis**: Thresholds ajustados automaticamente por jogo

---

## 🔌 API REST

### Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/games` | Lista todos os jogos disponíveis |
| `GET` | `/games/{slug}/config` | Configuração de um jogo |
| `GET` | `/games/{slug}/stats` | Estatísticas do jogo |
| `POST` | `/games/{slug}/validate` | Valida uma aposta |
| `POST` | `/games/{slug}/generate` | Gera apostas |
| `POST` | `/games/{slug}/closures` | Gera fechamentos |

### Exemplo de Response (Validação)

```json
{
  "score": 85,
  "status": "Bom",
  "risco_divisao": "Baixo",
  "msgs": [
    "✅ Soma (192) equilibrada",
    "✅ Distribuição Par/Ímpar equilibrada",
    "✅ Finais bem distribuídos",
    "🛡️ Aposta Blindada: Padrão único"
  ],
  "metricas": {
    "soma": 192,
    "pares": 3,
    "impares": 3,
    "span": 54
  }
}
```

---

## 🛠️ Tecnologias

### Core
- **Python 3.10+** - Linguagem principal
- **Pandas** - Manipulação de dados
- **NumPy** - Computação numérica
- **SciPy** - Análises estatísticas

### Frontend
- **Streamlit** - Interface web interativa
- **Plotly** - Gráficos interativos
- **Altair** - Visualizações declarativas

### Backend
- **FastAPI** - API REST de alta performance
- **Pydantic** - Validação de dados

### DevOps
- **Docker** - Containerização
- **pytest** - Testes automatizados

---

## 📁 Estrutura do Projeto

```
loto-science/
├── app/
│   ├── api/                    # FastAPI endpoints
│   │   ├── routers/            # Rotas por domínio
│   │   └── schemas/            # DTOs Pydantic
│   ├── core/                   # Lógica de negócio
│   │   ├── lottery/            # Modelos e catálogo de jogos
│   │   ├── statistics/         # Módulos estatísticos
│   │   ├── validator.py        # Validação de apostas
│   │   └── generator.py        # Geração de apostas
│   ├── services/               # Camada de serviços
│   └── ui/                     # Componentes Streamlit
├── pages/                      # Páginas Streamlit
├── data/                       # Dados históricos (Excel)
├── tests/                      # Testes automatizados
├── assets/                     # Imagens e recursos
├── main.py                     # Entry point Streamlit
├── run_api.py                  # Entry point FastAPI
├── requirements.txt            # Dependências
├── Dockerfile                  # Container config
└── README.md                   # Documentação
```

---

## 🧪 Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-cov

# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=app --cov-report=html
```

---

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor, siga os passos:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add: AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Guidelines

- Siga o padrão PEP 8
- Adicione testes para novas funcionalidades
- Documente funções com docstrings
- Atualize o README se necessário

---

## 📊 Estatísticas do Projeto

- **Linguagem**: Python 100%
- **Jogos Suportados**: 4 (Mega-Sena, Lotofácil, Quina, Lotomania)
- **Métricas de Análise**: 15+
- **Testes**: Em desenvolvimento

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

**AlefMemTav**

- GitHub: [@AlefMemTav](https://github.com/AlefMemTav)

---

## 🙏 Agradecimentos

- [Caixa Econômica Federal](https://loterias.caixa.gov.br/) - Dados históricos oficiais
- [Streamlit](https://streamlit.io/) - Framework de UI
- [FastAPI](https://fastapi.tiangolo.com/) - Framework de API

---

<p align="center">
  <strong>⭐ Se este projeto foi útil, considere dar uma estrela!</strong>
</p>

<p align="center">
  Made with ❤️ and 📊 Statistics
</p>
