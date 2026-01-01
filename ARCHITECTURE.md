# System Architecture - LotoScience Pro

## Overview
The project follows a **Modular Monolithic** script-based architecture, using the **Streamlit** framework for frontend rendering and **Pandas/NumPy** for analytical backend.

## Data Flow

1.  **Ingestion (Data Layer):**
    * The raw Excel file is loaded via `pandas`.
    * Data cleaning: column selection by index (`iloc`), conversion to numeric and removal of `NaN`.
    * **Optimization:** Use of `@st.cache_data` to keep the DataFrame in memory and avoid repeated I/O.

2.  **Statistical Processing (Service Layer):**
    * **Frequency:** Calculation via `value_counts()` to determine hot/cold numbers. (Cached)
    * **Poisson:** Statistical analysis of the distribution of final digits (0-9). (Cached)
    * **Validation:** The `validar_jogo()` function acts as a rule engine, applying penalties to an initial score of 100.

3.  **Presentation (UI Layer):**
    * Interface built with native Streamlit components (`st.tabs`, `st.metric`).
    * Data visualization with `matplotlib` (ticket rendering and heatmaps).

## Main Modules (`app.py`)

### `carregar_dados_reais()`
* Responsible for reading the Excel file.
* Handles `FileNotFound` errors.
* Returns a cleaned DataFrame containing only the six number columns.

### `validar_jogo(numeros)`
* Accepts a list of 6 integers.
* Applies 4 business rules:
    1.  Sum Range Check (Gauss).
    2.  Parity Check.
    3.  Geometric Distribution (Quadrants).
    4.  Popularity Heuristic (Sequences and Dates).
* Returns a dictionary with `score`, `status`, and a list of `msgs`.

### `gerar_jogo_perfeito()`
* Uses weighted sampling.
* Splits the number universe into 3 clusters: Hot, Cold, and Neutral.
* Trial-and-error loop: generates random combinations and submits them to `validar_jogo()`. Returns only if the score is > 90.

## Performance Optimizations

* **Cache:** Heavy statistical functions (`get_numeros_quentes_frios`, `analise_poisson`) are decorated with `@st.cache_data`. This prevents interface reloads (user interactions) from triggering unnecessary recalculations.