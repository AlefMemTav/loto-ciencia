# 🎱 LotoScience Pro

> **Not Luck, It’s Science.** > A statistical engineering tool for analysis, validation, and generation of lottery plays (Mega-Sena).

> ⚠️ The system does not increase the chance of winning; it only improves statistical quality, distribution, and financial efficiency of bets.

![LotoScience](/assets/images/lotoscience.png)

---

## About the Project

**LotoScience Pro** is an interactive dashboard built in Python that uses data science to make betting more intelligent. It processes the official Caixa history, applies mathematical filters (Gaussian Curve, Quadrants, Poisson) and generates insights for individual bettors or syndicates.


![Bet Validator](/assets/gifs/validador.gif)

![Combinatorics](/assets/gifs/gerador_fechamento.gif)

![Syndicate Audit](/assets/gifs/analise_bolao.gif)

### Main Features

1.  **📊 Trends Dashboard:** Real-time charts of Hot (frequent) and Cold (overdue) numbers and Poisson analysis (tens endings).
2.  **🧪 Bet Validator:** Enter your numbers and receive a "Score" from 0 to 100 based on the mathematical quality of the bet.
3.  **🤖 Hybrid Generator:** Algorithm combining statistics (Hot/Cold) with controlled randomness to create balanced plays.
4.  **📦 Combinatorics (Wheelings):** Tool to generate all mathematical combinations from a group of numbers (7 to 12 numbers).
5.  **👥 Syndicate Audit:** Paste a list of plays and get a group x-ray (total cost, coverage, duplicate/error detection).

### 🧠 How the Algorithm (Score) Works

The system assigns a score from 0 to 100 for each play based on 4 pillars:

    Gaussian Sum: The sum of the 6 numbers should be between 140 and 240 (where the highest statistical probability occurs).

    Parity: Plays with 3 even and 3 odd numbers (or 4/2) are prioritized. 6/0 plays are penalized.

    Quadrants: The play slip is divided into 4 areas. Plays that leave 2 or more areas empty lose points.

    Anti-Popularity: The system warns (but does not forbid) plays with many sequences or date-like numbers, which tend to split the prize.

---

### System Architecture (ARCHITECTURE.md)

```
┌────────────────────────┐
│        Interface       │
│   (Streamlit Tabs)     │
└──────────▲─────────────┘
           │
┌──────────┴─────────────┐
│     Statistical Engine │
│ validar_jogo()         │
│ gerar_jogo_perfeito()  │
│ verificar_historico()  │
└──────────▲─────────────┘
           │
┌──────────┴─────────────┐
│   Preprocessed Data    │
│ freq / poisson / df    │
└──────────▲─────────────┘
           │
┌──────────┴─────────────┐
│     Data Source        │
│   Historical Excel     │
└────────────────────────┘
```
---

## Installation and Setup

### Prerequisites
* Python 3.10+
* Caixa Excel data file (`data/mega_sena_asloterias_ate_concurso_2954_sorteio.xlsx`)

### Step by Step

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/loto-science.git](https://github.com/your-username/loto-science.git)
    cd loto-science
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare the data:**
    Make sure the Excel file downloaded from Caixa is in the `data/` folder.

5.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

---

## File Structure
```
loto-science/
│
├── .venv/                   # Seu ambiente virtual
│
├── .streamlit/              # Configuration folder
│   └── config.toml          # Defines colors and theme (Dark/Light)
│
├── data/
│   └── mega_sena*.xlsx      # Caixa data file
│
├── src/                     # Código Fonte
│   ├── __init__.py
│   ├── data_loader.py       # (Model) Carregamento e limpeza de dados
│   ├── statistics.py        # (Model) Cálculos pesados (Frequência, Poisson, etc.)
│   ├── validator.py         # (Controller) Regras de validação (Gauss, Pares, Score)
│   ├── generator.py         # (Controller) Algoritmos de geração de jogos
│   ├── constants.py         # Constantes (Listas de Primos, Moldura, etc.)
│   └── utils.py             # Funções auxiliares genéricas
│
├── components/              # (View) Componentes visuais reutilizáveis
│   ├── __init__.py
│   ├── dashboard.py         # Conteúdo da Tab 1
│   ├── validator_ui.py      # Conteúdo da Tab 2
│   ├── generator_ui.py      # Conteúdo da Tab 3
│   ├── closures_ui.py       # Conteúdo da Tab 4
│   └── bolao_ui.py          # Conteúdo da Tab 5
│
├── app.py                   # Application (Main)
├── requirements.txt         # Libraries to install
├── ARCHITECTURE.md          # System architecture
└── README.md                # Instructions on how to use the project
```

## Statistical Note

All numbers have the same theoretical probability of being drawn.
The analyses presented here are intended only for organization, statistical distribution, and reduction of common patterns—not to predict outcomes.
This software is an analytical tool. It does not guarantee wins. Lottery is gambling and the mathematical probabilities are fixed. Play responsibly.
