# Documentação Técnica e Científica — LotoCiencia

Esta documentação reúne a especificação arquitetural, a pipeline metodológica e o catálogo completo de algoritmos estatísticos, combinatórios e de aprendizado de máquina do ecossistema **LotoCiencia**.

---

## 1. Visão Geral e Princípios Científicos

### 1.1 O Problema Fundamental das Loterias
Em qualquer loteria honesta onde são sorteadas $k$ bolas dentre $N$ disponíveis sem reposição, o espaço amostral total possui tamanho dado pelo coeficiente binomial:

$$\Omega = \binom{N}{k} = \frac{N!}{k!(N - k)!}$$

Cada bilhete individual possui exatamente a mesma probabilidade matemática de acerto do prêmio principal ($P = 1 / \Omega$). Portanto, **não existe algoritmo capaz de prever o próximo sorteio com certeza**. No entanto, um sistema de engenharia estatística consegue otimizar três dimensões reais:

1. **Plausibilidade Estrutural (Onde a Massa Probabilística Vive)**: Embora a combinação `[01, 02, 03, 04, 05, 06]` tenha a mesma chance individual que `[04, 17, 23, 38, 45, 56]`, a quantidade de combinações com soma central, paridade equilibrada e alta entropia de espaçamentos corresponde a cerca de $90\%$ de todo o espaço $\binom{N}{k}$. Jogar dentro da região de alta densidade combinatória alinha o apostador ao comportamento típico da urna.
2. **Proteção contra Divisão de Prêmio (Valor Esperado Líquido)**: Apostadores humanos são péssimos geradores de números aleatórios. Eles escolhem datas de aniversário ($\le 31$), linhas retas ou diagonais no volante, progressões aritméticas e números da sorte. Evitar combinações populares não aumenta a probabilidade de acertar, mas **multiplica o prêmio líquido esperado** ao reduzir drasticamente o número de co-ganhadores.
3. **Eficiência de Cobertura de Portfólio (Pacote de Jogos)**: Quando se aposta mais de um jogo, os bilhetes não devem competir entre si. Controlar a exposição máxima por dezena e proibir repetições excessivas de pares, trincas e quadras maximiza a área coberta do espaço combinatório.

### 1.2 Desacoplamento pela Lei de Goodhart
> *"Quando uma métrica se torna um objetivo, ela deixa de ser uma boa métrica."* — Lei de Goodhart.

Uma decisão arquitetural central do **LotoCiencia** é a separação estrita entre:
* **Objetivo do Gerador (`generator_objective.py`)**: Avalia milhões de candidatos de forma contínua usando percentis do Modelo Nulo Combinatório, calibração estrutural suave, sinais históricos limitados (clipped) e modelo empírico de popularidade.
* **Validador Independente (`validator.py`)**: Atua como um auditor externo de 13 etapas que aplica testes com correção de Bonferroni e detectores geométricos rigorosos. O gerador **nunca** chama o `validator.py` para otimizar o score de tela, evitando *overfitting* artificial.
* **Score Composto de Backtest (`strategy_matrix.py`)**: É puramente diagnóstico para comparar relatórios históricos e jamais realimenta os geradores.

---

## 2. Arquitetura e Pipeline Operacional (5 Estágios)

O diagrama abaixo resume o fluxo de ponta a ponta desde a ingestão das planilhas até a emissão do pacote final auditado:

```
[Estágio 1: Contexto e Auditoria]
   ├── Histórico de Sorteios (D1..Dk) ──> Auditoria (Chi², KS, VMR, Runs, Ordem de Saída)
   ├── Sinais Temporais ────────────────> Tabela Z_Freq/Z_Gap, Pesos Dinâmicos, Markov, Ciclo, Co-ocorrência
   └── Modelos de Referência ───────────> Modelo Nulo (50k), Calibração Estrutural, Popularidade Medida (Ridge)
                 │
                 ▼
[Estágio 2: Roteamento por Densidade (k / N)]
   ├── Jogos Esparsos (d < 0.20: Mega-Sena, Quina) ──> Estratégia Cauda Convexa / Controlada (Foco em cobertura)
   └── Jogos Densos   (d > 0.40: Lotofácil, Mania) ──> Estratégia Balanceada / Agressiva ou Matrizes de Fechamento
                 │
                 ▼
[Estágio 3: Geração Oficial via Torneio (real_game_mode.py)]
   ├── Amostragem Gumbel-Max + Softmax (generator_fast.py) ou Evolução (generator_genetic.py)
   ├── Avaliação Vetorial Independente (score_plausibility_batch)
   ├── Torneio Fechado de Pacotes (Maximiza cobertura de pares/trincas e penaliza superexposição)
   └── Benchmark contra até 5.000 pacotes Monte Carlo equivalentes
                 │
                 ▼
[Estágio 4: Auditoria de Transparência e Risco (validator.py & cluster_profile.py)]
   ├── Checagem de Histórico O(1) e Distância de Hamming
   ├── Detector de Padrões Humanos (PAs, Diagonais, Bordas, Simetria, Datas, Lost, Sortudos)
   ├── Validação Dupla de Soma (IC Histórico + Bootstrap IC 95%)
   └── Classificação de Perfil via K-Means / DBSCAN
                 │
                 ▼
[Estágio 5: Evolução Contínua na Bancada Científica (backtest.py & strategy_matrix.py)]
   └── Walk-Forward Temporal + Simulação Financeira (ROI) + Alertas de Estabilidade entre Seeds
```

---

## 3. Modelagem de Domínio e Geometria do Volante

**Arquivos**: `app/core/lottery/catalog.py` e `app/core/lottery/models.py`

### 3.1 Catálogo de Modalidades (`catalog.py`)
O registro `GAMES_REGISTRY` centraliza as quatro loterias suportadas e seus parâmetros operacionais:

| Modalidade | Slug | Universo ($N$) | Sorteio ($k$) | Aposta ($k_{\text{bet}}$) | Volante ($R \times C$) | Densidade ($d$) | Probabilidade Base |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Mega-Sena** | `mega_sena_sorteio` | $60$ | $6$ | $6$ | $6 \times 10$ | $0.10$ ($10\%$) | $1$ em $50.063.860$ |
| **Quina** | `quina_sorteio` | $80$ | $5$ | $5$ | $8 \times 10$ | $0.0625$ ($6.25\%$) | $1$ em $24.040.016$ |
| **Lotofácil** | `loto_facil_sorteio` | $25$ | $15$ | $15$ | $5 \times 5$ | $0.60$ ($60\%$) | $1$ em $3.268.760$ |
| **Lotomania** | `loto_mania_sorteio` | $100$ | $20$ | $50$ | $10 \times 10$ | $0.50$ ($50\%$) | $1$ em $11.372.635$ |

### 3.2 Geometria do Volante (`BoardLayout` em `models.py`)
Mapeia qualquer dezena $n \in \{1, \dots, N\}$ para coordenadas bidimensionais zero-based $(r, c)$:

$$r = \lfloor (n - 1) / C \rfloor, \quad c = (n - 1) \bmod C$$

A partir de $(r, c)$, o sistema extrai automaticamente subconjuntos geométricos do volante:
* **Moldura (Borda)**: $\{n \mid r \in \{0, R - 1\} \lor c \in \{0, C - 1\}\}$.
* **Miolo (Centro)**: Complementar da moldura no universo $\{1, \dots, N\}$.
* **Cantos**: Os 4 vértices extremos $(0, 0), (0, C-1), (R-1, 0), (R-1, C-1)$.
* **Cruz**: Linha(s) e coluna(s) centrais (1 linha/coluna se ímpar, 2 se par).
* **Xis (Diagonais)**: Diagonal principal ($r = c$ com $r < \min(R, C)$) e diagonal secundária ($r + c = C - 1$).
* **Quadrantes ($Q_1, Q_2, Q_3, Q_4$)**: Divisão do volante ao meio em $R/2$ e $C/2$.
* **Xadrez**: Partição em casas brancas ($(r + c) \bmod 2 = 0$) e casas pretas ($(r + c) \bmod 2 = 1$).
* **Anéis Concêntricos (Distância de Manhattan)**: Mede a distância ao centro $(r_c, c_c) = (R/2, C/2)$:
  $$d_{\text{Manhattan}}(n) = |r - r_c| + |c - c_c|$$
  Classifica em anel **Externo** ($\ge 66\%$ da distância máxima), **Médio** ($33\%$ a $66\%$) e **Interno** ($< 33\%$).

### 3.3 Regras de Densidade e Limite de Overlap (`GameConfig` em `models.py`)
A densidade do jogo é definida por $d = k_{\text{bet}} / N$:
* `is_sparse`: $d < 0.20$ (Mega-Sena, Quina).
* `is_dense`: $d > 0.40$ (Lotofácil, Lotomania).

O método `get_overlap_limit()` define o máximo de dezenas repetidas permitidas entre dois bilhetes do mesmo pacote:
* Se $d < 0.20$: $\lfloor 0.50 \times k_{\text{bet}} \rfloor$ (ex.: máx. $3$ dezenas comuns na Mega-Sena).
* Se $0.20 \le d < 0.45$: $\lfloor 0.70 \times k_{\text{bet}} \rfloor$.
* Se $d \ge 0.45$: $\lfloor 0.85 \times k_{\text{bet}} \rfloor$ (ex.: máx. $12$ dezenas comuns na Lotofácil).

Já `get_recommended_weights()` protege jogos esparsos contra a **Falácia do Apostador**, forçando no mínimo $70\%$ de peso em frequência ($w_{\text{freq}} \ge 0.70$) e no máximo $30\%$ em atraso ($w_{\text{gap}} \le 0.30$).

---

## 4. Estatística Descritiva, Inferencial e Auditoria

**Arquivos**: `constants.py`, `basic.py`, `distributions.py`, `ordem_saida.py`, `monte_carlo.py`, `bootstrap_integration.py`

### 4.1 Correção de Bonferroni para Múltiplos Testes (`constants.py`)
Ao avaliar um bilhete simultaneamente em $15$ dimensões estatísticas ($5$ geométricas + $4$ quadrantes + $6$ básicas), testar cada dimensão com $\alpha = 0.05$ geraria uma taxa de falsos positivos acumulada de $1 - (1 - 0.05)^{15} \approx 53.7\%$.

Para manter o erro familiar global em $\alpha_{\text{family}} = 0.05$, aplica-se a **Correção de Bonferroni**:

$$\alpha_{\text{Bonferroni}} = \frac{\alpha_{\text{family}}}{15} = \frac{0.05}{15} \approx 0.00333$$

Isso redefine os limiares críticos de Z-score (`compute_zscore` em `basic.py`, dado por $Z = \frac{x - \mu}{\sigma + 10^{-9}}$):
* `ZSCORE_EXTREME` $= 2.97$ (evento de $\sim 0.3\%$ após correção; penalidade peso $3.0$).
* `ZSCORE_VERY_RARE` $= 2.39$ (evento de $\sim 1.7\%$; penalidade peso $2.0$).
* `ZSCORE_RARE` $= 1.64$ (evento de $\sim 10\%$; penalidade peso $1.0$).

Além disso, a função `ajustar_threshold_por_densidade(valor_base, densidade)` relaxa os limiares em $+50\%$ para jogos com $d \ge 0.50$ e em $+20\%$ para jogos com $0.30 \le d < 0.50$.

### 4.2 Tabela de Inteligência (`get_tabela_inteligencia` em `basic.py`)
Para cada dezena $n \in \{1, \dots, N\}$, consolida:
1. **Frequência ($F_n$)**: Total de aparições históricas e seu respectivo $Z_{\text{Freq}}$.
2. **Atraso Atual ($G_n$)**: Quantidade de concursos desde a última aparição (`calcular_atrasos`) e seu respectivo $Z_{\text{Gap}}$.
3. **Peso Composto Base**:
   $$P_n = 0.40 \cdot Z_{\text{Freq}}(n) + 0.60 \cdot Z_{\text{Gap}}(n)$$
4. **Peso de Geração Normalizado**: Escalonado para $[0.01, 1.01]$ via Min-Max scaling, além dos percentis empíricos `Percentil_Freq` e `Percentil_Gap`.

### 4.3 Testes de Honestidade e Distribuições (`distributions.py`)
* **Teste Qui-Quadrado ($\chi^2$) e Kolmogorov-Smirnov (`calcular_chi_quadrado`)**: Compara a frequência observada $O_n$ de cada bola com a frequência uniforme esperada $E_n = \frac{T \cdot k}{N}$, onde $T$ é o total de sorteios:
  $$\chi^2 = \sum_{n=1}^{N} \frac{(O_n - E_n)^2}{E_n}$$
  Se $p_{\chi^2} > 0.05$ e $p_{\text{KS}} > 0.05$, classifica o sorteio como **Honesto (Aleatório)**.
* **Análise de Poisson nos Dígitos Finais (`analise_poisson`)**: Verifica se os terminais $0 \dots 9$ seguem a distribuição de Poisson $\text{Poisson}(\lambda_d)$, onde $\lambda_d = T \cdot k \cdot P_{\text{teórica}}(d)$, apontando déficits ou excessos bilaterais com $p < \alpha$.
* **Estatísticas de Ordem (`calcular_order_statistics`)**: Para um bilhete ordenado $x_{(1)} < x_{(2)} < \dots < x_{(k)}$, a posição esperada da $i$-ésima menor dezena em um sorteio uniforme é:
  $$E[X_{(i)}] = i \cdot \frac{N + 1}{k + 1}$$
  O algoritmo calcula o desvio médio relativo normalizado por $(N/k)$ para detectar números excessivamente deslocados para o início ou fim do volante.
* **Distribuição de Gaps Internos (`testar_distribuicao_gaps_bilhete` e `detectar_motifs_gaps`)**: Testa os intervalos $g_i = x_{(i+1)} - x_{(i)}$ contra uma distribuição Exponencial via teste KS, calcula o coeficiente de variação $\text{CV}_{\text{gaps}} = \sigma_g / \mu_g$ e busca *motifs* periódicos como $[a, a, \dots]$, alternâncias $[a, b, a, b]$ ou subsequências repetidas.

### 4.4 Auditoria da Ordem de Saída das Bolas (`ordem_saida.py`)
Analisa as colunas `D1..Dk` na ordem exata em que foram sorteadas do globo:
1. **Filtro de Dados Antigos Ordenados (`mascara_ordem_de_saida`)**: Algumas bases históricas antigas (ex.: Quina) registravam os primeiros concursos em ordem crescente em vez da ordem de sorteio. Como a chance de uma linha real sair estritamente crescente por acaso é $1 / k!$, o algoritmo encontra o ponto de corte ótimo $c^*$ que minimiza o custo de incoerência:
   $$\text{custo}(c) = \sum_{t=0}^{c-1} (1 - I_{\text{crescente}}(t)) + \sum_{t=c}^{T-1} I_{\text{crescente}}(t)$$
   Descartando automaticamente o bloco corrompido $[0, c^*)$.
2. **Teste Posicional com Correção FDR (Benjamini-Hochberg)**: Normaliza a ordem de saída em $[0, 1]$ ($0 =$ primeira bola, $1 =$ última bola). Sob $H_0$, a posição média esperada de cada dezena é $0.50$, com variância teórica:
   $$\text{Var}(P) = \frac{k + 1}{12(k - 1)}$$
   Calcula o Z-score por dezena e controla a Taxa de Falsas Descobertas (*False Discovery Rate* — FDR a $5\%$) pelo procedimento step-up de **Benjamini-Hochberg** (`_benjamini_hochberg`), além de testar a uniformidade da primeira e da última bola via $\chi^2$.

### 4.5 Bootstrap e Monte Carlo (`monte_carlo.py` e `bootstrap_integration.py`)
* **Intervalo de Confiança Bootstrap da Soma (`bootstrap_ic_soma`)**: Realiza $B = 5.000$ (ou $10.000$) reamostragens com reposição das somas históricas para estimar a distribuição empírica da média e seus percentis de $95\%$.
* **Validação Cruzada de Soma (`avaliar_soma_com_bootstrap`)**: Compara o IC Histórico ($P_{10}\text{--}P_{90}$ e $P_{2.5}\text{--}P_{97.5}$) com o IC Bootstrap, gerando diagnósticos de convergência ou divergência para o validador.

---

## 5. Sinais Avançados, Séries Temporais e Machine Learning

**Arquivos**: `advanced.py`, `temporal.py`, `similarity.py`, `geometry.py`, `clustering.py`, `cluster_profile.py`, `popularidade_medida.py`

### 5.1 Matriz de Co-ocorrência Normalizada (`advanced.py`)
Mede a afinidade histórica entre pares de dezenas $(i, j)$ normalizada pela esperança hipergeométrica sob independência:

$$P_{\text{esperada}}(i \land j) = \frac{\binom{N - 2}{k - 2}}{\binom{N}{k}} = \frac{k(k - 1)}{N(N - 1)}$$

$$M_{\text{cooc}}[i, j] = \frac{\text{Ocorrências}(i, j)}{T \cdot P_{\text{esperada}}(i \land j) + 10^{-9}}$$

Valores $M_{\text{cooc}}[i, j] > 1.0$ indicam pares que saíram juntos acima do esperado (`get_pares_mais_frequentes`), enquanto valores próximos de $0$ identificam pares que historicamente "se repelem" (`get_pares_que_se_repelem`).

### 5.2 Cadeias de Markov de 1ª Ordem (`advanced.py`)
Constrói a matriz de transição estocástica $M_{\text{trans}}[i, j] = P(j \in \text{Sorteio}_{t+1} \mid i \in \text{Sorteio}_t)$, normalizada por linha. A função `analisar_transicoes_anomalas` avalia desvios em relação à contagem esperada $E_{ij} = (T - 1) \cdot k \cdot (k / N)$ via aproximação de Poisson ($\sigma = \sqrt{E_{ij}}$), sinalizando transições com $|Z| \ge 2.5$.

### 5.3 Teste de Runs de Wald-Wolfowitz e Índice VMR (`advanced.py`)
* **Teste de Runs (`teste_runs_numero`)**: Converte o histórico de cada dezena em uma sequência binária de presenças ($n_1$) e ausências ($n_0$). Conta o número de *runs* (sequências contínuas de $1$s ou $0$s) e compara com a esperança e variância exatas sob aleatoriedade:
  $$\mu_R = \frac{2 n_1 n_0}{n_1 + n_0} + 1, \quad \sigma_R^2 = \frac{2 n_1 n_0 (2 n_1 n_0 - n_1 - n_0)}{(n_1 + n_0)^2 (n_1 + n_0 - 1)}$$
* **Índice de Dispersão VMR (`indice_dispersao`)**: Calcula a razão variância-média das frequências ($\text{VMR} = s^2 / \bar{x}$). Sob uma distribuição de Poisson, $\text{VMR} \approx 1.0$ e a estatística $(N - 1) \cdot \text{VMR} \sim \chi^2_{N-1}$.

### 5.4 Calibração Dinâmica de Pesos — "Autópsia dos Vencedores" (`advanced.py`)
A função `calibrar_pesos_dinamicos` substitui escolhas arbitrárias entre números quentes e atrasados por uma fusão Bayesiana empírica:
1. Seleciona uma janela recente adaptada à densidade ($100$ sorteios para jogos densos, $300$ para esparsos).
2. Extrai de forma vetorizada todos os intervalos reais ($\Delta t$) entre aparições consecutivas de cada dezena na janela.
3. Compara cada intervalo real com o **Gap Teórico** $\mu_{\text{gap}} = N / k$:
   * Retorno rápido ($\Delta t \le N / k$): ponto para **Frequência** ($p_{\text{freq}}$).
   * Retorno lento ($\Delta t > N / k$): ponto para **Atraso/Gap** ($p_{\text{gap}}$).
4. **Fusão Bayesiana**: Combina a evidência recente (confiança de $75\%$) com a distribuição *prior* da natureza do jogo ($P_{\text{prior}} = 0.70$ para densos, $0.30$ para esparsos):
   $$w_{\text{freq}} = 0.75 \cdot p_{\text{freq}} + 0.25 \cdot P_{\text{prior}}, \quad w_{\text{gap}} = 1.0 - w_{\text{freq}}$$

### 5.5 Ciclos, Eletrocardiograma de Somas e Regressão à Média (`temporal.py` e `similarity.py`)
* **Ciclo das Dezenas (`calcular_ciclo_atual`)**: Monitora o *Coupon Collector's Problem*, identificando exatamente quais dezenas ainda faltam sair para fechar o ciclo atual de $1$ a $N$.
* **Eletrocardiograma das Somas (`analise_temporal_somas`)**: Calcula a média teórica da soma e seu desvio padrão exato com fator de correção para população finita:
  $$\mu_{\text{soma}} = k \frac{N + 1}{2}, \quad \sigma_{\text{soma}} = \sqrt{k \left(\frac{N^2 - 1}{12}\right) \left(\frac{N - k}{N - 1}\right)}$$
  Define a banda de normalidade em $[\mu_{\text{soma}} - 2\sigma_{\text{soma}}, \mu_{\text{soma}} + 2\sigma_{\text{soma}}]$.
* **Validação de Regressão à Média (`calcular_taxa_regressao` e `analisar_gaps_geometricos` em `similarity.py`)**: Mede a correlação de Spearman ($\rho$) entre o atraso passado e a frequência futura na janela seguinte, além de testar se os intervalos entre aparições de cada bola seguem a distribuição Geométrica teórica $\text{Geom}(p = k/N)$.

### 5.6 Clusterização de Padrões com K-Means e DBSCAN (`clustering.py` e `cluster_profile.py`)
Todo jogo é transformado em um vetor de $9$ features (`extrair_features_jogo`):
`[soma, media, prop_pares, prop_baixos, gap_medio, gap_std, sequencias, prop_finais_unicos, amplitude_relativa]`.
* **K-Means (`clusterizar_jogos_kmeans`)**: Padroniza com `StandardScaler`, encontra o número ótimo de clusters maximizando o *Silhouette Score* (`encontrar_numero_otimo_clusters`) e rotula os grupos dinamicamente em `cluster_profile.py`:
  * 🔵 **Compacto-Inicial** (Soma baixa + Gap concentrado)
  * 🔴 **Expansivo-Final** (Soma alta + Gap espalhado)
  * 🟢 **Equilibrado (Típico)** (Soma média + Gap padrão)
  * 🟠 **Compacto-Final** (Soma alta + Gap concentrado)
  * ⚪ **Perfil Misto** (Combinações híbridas)
* **DBSCAN (`clusterizar_jogos_dbscan`)**: Agrupamento baseado em densidade que isola automaticamente jogos aberrantes como ruído (`label = -1`).

### 5.7 Modelo Econométrico de Popularidade Medida (`popularidade_medida.py`)
Em vez de depender apenas de regras fixas sobre o que os apostadores jogam, este módulo estima a popularidade real de cada dezena a partir dos dados de rateio da Caixa (`data/detalhes/<loteria>_detalhes.csv`):
1. **Seleção de Faixa (`_escolher_faixa`)**: Escolhe a faixa de premiação com mediana de ganhadores $\ge 300$ (ex.: Quadra da Mega-Sena), onde a lei dos grandes números reduz o ruído de Poisson.
2. **Especificação Econométrica (Regressão Ridge)**: Como as dezenas sorteadas são independentes do volume arrecadado, modela-se a taxa logarítmica de ganhadores por milhão arrecadado:
   $$y_t = \log\left(\frac{\text{Ganhadores}_t + 0.5}{\text{Arrecadado}_t} \times 10^6\right) = \beta_0 + \sum_{n=1}^{N} \beta_n X_{t,n} + \gamma_1 \widetilde{\log(\text{Arrecadado}_t)} + \gamma_2 \tilde{t} + \varepsilon_t$$
   Onde $X_{t,n} \in \{0, 1\}$ indica se a dezena $n$ foi sorteada no concurso $t$. A penalização Ridge ($\lambda \in \{1, 10, 100, 1000\}$) incide apenas sobre os pesos das dezenas $\beta_1 \dots \beta_N$, deixando o intercepto e os controles livres.
3. **Validação Cruzada Temporal Estrita (`treinar_modelo_popularidade`)**: Divide o histórico em $6$ blocos expansivos (sem vazamento de dados futuros). O modelo só é ativado se superar o modelo nulo (apenas controles) em mais da metade dos *folds* e atingir ganho fora da amostra $R^2_{\text{CV}} \ge 0.02$.
4. **Razão de Divisão de Prêmio (`avaliar`)**: Para qualquer bilhete candidato, $\exp\left(\sum_{n \in \text{jogo}} \hat{\beta}_n\right)$ estima o multiplicador esperado de ganhadores caso aquele jogo seja sorteado.

---

## 6. Modelo Nulo Combinatório e Calibração Estrutural

**Arquivos**: `ticket_features.py`, `null_model.py`, `feature_percentiles.py`, `score_calibration.py`

### 6.1 Extração Vetorizada de Features (`ticket_features.py`)
A função `extract_ticket_features_batch` processa dezenas de milhares de candidatos simultaneamente em NumPy, extraindo $17$ métricas objetivas:
`soma`, `pares`, `span`, `min_gap`, `max_gap`, `gap_medio`, `gap_variety`, `entropia_gaps`, `max_sequencia`, `max_final_repetido`, `superior`, `inferior`, `max_dezena_repetida`, `max_linha`, `max_coluna`, `max_quadrante` e o índice contínuo `compressibilidade_simples` $\in [0, 1]$:

$$\text{Compressibilidade} = \text{clip}\left(0.55 \cdot \hat{H}(\text{gaps}) + 0.35 \cdot \text{VarGaps} - 0.20 \cdot \text{Pen}_{\text{seq}} - 0.10 \cdot \text{Pen}_{\text{final}}, \, 0, \, 1\right)$$

### 6.2 Modelo Nulo Combinatório (`null_model.py` e `feature_percentiles.py`)
Para saber se uma métrica é "rara" ou "comum" sem usar limiares arbitrários:
1. `build_null_model` sorteia $M = 50.000$ jogos uniformemente distribuídos no espaço $\binom{N}{k_{\text{bet}}}$ usando partição rápida de matrizes aleatórias (`np.argpartition`).
2. Ordena e armazena em cache o vetor de cada uma das métricas.
3. `batch_feature_percentiles` converte qualquer métrica bruta de um bilhete em seu **percentil combinatório exato** ($0$ a $100$) em tempo $O(\log M)$ via busca binária vetorizada (`np.searchsorted`).

### 6.3 Calibração de Score Estrutural (`score_calibration.py`)
Impede que o gerador produza apenas bilhetes "artificialmente perfeitos" (concentrados na faixa $85\text{--}100$), forçando a distribuição do pacote gerado a imitar a distribuição real da natureza:
1. Calcula um score estrutural independente do validador (`score_structural_from_percentiles`), combinando métricas centrais (ótimo em torno do percentil $50$), métricas onde valores altos são ruins (ex.: `max_sequencia`, `max_final_repetido`) e métricas onde valores baixos são ruins (`min_gap`, `compressibilidade_simples`).
2. Divide o score em $5$ *buckets*: `0-39`, `40-54`, `55-69`, `70-84`, `85-100`.
3. Define a distribuição alvo como uma mistura convexa:
   $$P_{\text{alvo}}(b) = 0.70 \cdot P_{\text{histórico}}(b) + 0.30 \cdot P_{\text{modelo\_nulo}}(b)$$
4. Calcula o *log-prior* de calibração para cada candidato no bucket $b$:
   $$\text{Prior}(b) = \text{clip}\left(\ln\left(\frac{P_{\text{alvo}}(b)}{0.20}\right), \, -1.5, \, 1.5\right)$$
5. Audita a fidelidade do pacote gerado medindo a **Divergência de Jensen-Shannon ($D_{\text{JS}}$)** entre a distribuição gerada $P$ e a distribuição alvo $Q$ (onde $M = \frac{1}{2}(P + Q)$):
   $$D_{\text{JS}}(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M)$$

---

## 7. Motores de Geração, Função Objetivo e Fechamentos

**Arquivos**: `generator_objective.py`, `generator_fast.py`, `generator_genetic.py`, `real_game_mode.py`, `matrices.py`

### 7.1 Função Objetivo Própria do Gerador (`generator_objective.py`)
A função `score_plausibility_batch` pontua lotes massivos de candidatos combinando $7$ camadas independentes:
1. **Aderência Central e Penalidade de Caudas Combinatórias**: Premia candidatos próximos à mediana combinatória ($\text{percentil} = 50$) e penaliza violações fora da janela $[\text{percentil\_min}, \text{percentil\_max}]$ (padrão $[5\%, 95\%]$, expandido para $[3\%, 97\%]$ ou $[4\%, 96\%]$ nas estratégias de cauda).
2. **Prior de Calibração Estrutural**: Soma $0.35 \times \text{calibration\_strength} \times \text{Prior}(b)$.
3. **Penalidade Anti-Números da Sorte**: Desconta $1.5$ ponto se o bilhete contiver excesso de números culturais $\{3, 7, 9, 11, 13, 21, 27, 33\}$.
4. **Sinais Históricos Controlados (Clipped)**: Incorpora as médias de $Z_{\text{Freq}}$ (peso $0.30$) e $Z_{\text{Gap}}$ (peso $0.22$) truncadas em $[-2.0, 2.0]$ para evitar que uma única bola domine o bilhete.
5. **Co-ocorrência com Controle de Cauda**: Calcula o Z-score da soma de co-ocorrências do bilhete (`cooc_z`) via indexação triangular superior (`np.triu_indices`). Nas estratégias `cauda_controlada`, `cauda_convexa` e `cauda_agressiva`, premia sinergia moderada, mas **penaliza excesso de co-ocorrência** acima de $2.0\sigma\text{--}2.5\sigma$ para evitar sobreposição em cliques viciados.
6. **Penalidade de Popularidade Medida e Ordem de Saída**: Desconta até $2.0 \times \text{força}$ para jogos com percentil de popularidade real acima de $60\%$ e aplica leve correção contra extremos posicionais ($< 5\%$ ou $> 95\%$).
7. **Eliminação de Jogos Já Sorteados**: Qualquer combinação presente em `ctx.historico_set` recebe score $-\infty$.

### 7.2 Seleção de Portfólio e Estratégias de Cauda (`select_diverse_portfolio`)
O módulo suporta $6$ estratégias (`conservadora`, `balanceada`, `agressiva`, `cauda_controlada`, `cauda_agressiva`, `cauda_convexa` e `pura`):
* **Seleção Padrão**: Ordena candidatos com ruído Gumbel proporcional à estratégia e aplica limites rígidos de exposição por dezena, chave de diversidade no espaço de features (`soma // 15`, `pares`, `span // 8`, `gap_medio // 3`) e limite de overlap de Hamming.
* **Seleção Marginal de Conjunto (`_select_tail_controlled_portfolio`)**: Usada por `cauda_controlada`, `cauda_agressiva` e `cauda_convexa`. Em cada passo, escolhe o bilhete que maximiza a **utilidade marginal do pacote**:
  * Impõe tetos absolutos (*hard caps*) de exposição por dezena e repetição de pares.
  * Na estratégia **`cauda_convexa`** em jogos esparsos (ex.: Mega-Sena), trava o overlap máximo em $2$ dezenas e **proíbe qualquer repetição de trincas ($\text{cap} = 1$) e quadras ($\text{cap} = 1$)** em todo o pacote.
  * Balanceia dinamicamente os *buckets* de calibração estrutural para minimizar a divergência $D_{\text{JS}}$ do pacote.

### 7.3 Motor 1: Geração Vetorial com Truque Gumbel-Max (`generator_fast.py`)
O motor `gerar_jogos_vetorizado` realiza amostragem ponderada sem reposição em alta velocidade:
1. Combina $Z_{\text{Freq}}$, $Z_{\text{Gap}}$, probabilidades de transição de Markov do último sorteio ($+0.15$) e bônus de gravidade do Ciclo das Dezenas ($+0.80$ para densos, $+0.25$ para esparsos).
2. Aplica **Softmax com Temperatura** ($\tau \in [1.15, 2.0]$ conforme a estratégia):
   $$p_i = \frac{\exp(s_i / \tau)}{\sum_{j=1}^{N} \exp(s_j / \tau)}$$
3. **Truque Gumbel-Max**: Para gerar dezenas de milhares de jogos sem reposição sem usar loops lentos em Python, soma ruído Gumbel padrão $G_{b,i} = -\ln(-\ln(U_{b,i}))$ aos log-probabilidades:
   $$W_{b,i} = \ln(p_i + 10^{-10}) - \ln(-\ln(U_{b,i} + 10^{-10}))$$
   Selecionar os $k$ maiores valores de $W_{b,i}$ por linha via `np.argpartition` produz matematicamente uma amostra exata sem reposição da distribuição multinomial ponderada.

### 7.4 Motor 2: Minerador Genético Evolutivo (`generator_genetic.py`)
A classe `GeneticMiner` implementa um algoritmo evolucionário sobre conjuntos:
* **População**: $300$ indivíduos evoluídos por $30$ (jogos pequenos) a $60$ gerações (Mega-Sena/Quina/Lotomania).
* **Fitness**: Avaliado diretamente por `score_plausibility_batch`.
* **Elitismo e Crossover de Conjunto (`_crossover_set`)**: Preserva os top $10\%$ como elite. O cruzamento une os genes dos pais ($P_1 \cup P_2$) e amostra $k$ dezenas únicas dessa união.
* **Mutação**: Taxa de $20\%$ (preservando o top $3$ intacto), trocando $1$ ou $2$ genes por dezenas livres do universo.

### 7.5 Modo Jogo Real — Torneio Fechado de Pacotes (`real_game_mode.py`)
Projetado para o momento da aposta real, evitando que o usuário rode o gerador várias vezes até escolher um resultado por viés visual:
1. **Seed Determinística Auditável (`_default_seed`)**: Gera uma *seed* SHA-256 única combinando a data do dia, o slug do jogo, a quantidade de bilhetes, o perfil de esforço (`rapido`, `forte` ou `maximo`), o tamanho do histórico e as dezenas do último sorteio.
2. **Torneio de Pacotes (`_package_score`)**: Gera um pool de candidatos e monta até $800$ pacotes concorrentes (no perfil `maximo`). Cada pacote é avaliado pela função de utilidade global:
   $$\text{Score}_{\text{pacote}} = \bar{S} + 0.12 \cdot S_{\max} + 0.80 \cdot \text{Cob}_{\text{pares}} + 0.55 \cdot \text{Cob}_{\text{trincas}} - 0.80 \cdot \text{Excesso}_{\text{exp}} - 0.80 \cdot \text{Excesso}_{\text{overlap}} - 0.60 \cdot \text{Excesso}_{\text{pares}}$$
3. **Comparação contra Monte Carlo**: Gera até $5.000$ pacotes puramente aleatórios sob as mesmas restrições e informa o percentil exato e o $p$-valor empírico do pacote campeão.

### 7.6 Matrizes de Fechamento Combinatório (`matrices.py`)
Quando o apostador seleciona $n > k$ dezenas base:
* **Catálogo Otimizado Lotofácil (`MatrixCatalog`)**:
  * $16$ dezenas $\to 3$ jogos.
  * $17$ dezenas $\to 8$ jogos.
  * $18$ dezenas $\to 24$ jogos (Matriz $18\text{-}15\text{-}14\text{-}15$: garante matematicamente pelo menos $14$ acertos se as $15$ dezenas sorteadas estiverem entre as $18$ escolhidas).
* **Fechamento Dinâmico Universal (`_gerar_fechamento_dinamico`)**: Se $\binom{n}{k} \le 5.000$, gera o desdobramento completo exato; caso contrário, aplica uma redução por **Janela Deslizante Circular** com passo $\lfloor i \cdot k / 2 \rfloor \bmod n$.

---

## 8. Sistema de Validação e Detecção de Padrões

**Arquivos**: `validator.py` e `patterns.py`

A função `validar_jogo` parte de um score inicial de $100$ pontos e executa uma bateria de **13 etapas de auditoria**:

1. **Verificação de Histórico O(1)**: Consulta se a tupla ordenada já saiu no passado (`ja_saiu = True` zera o score imediatamente).
2. **Análise Técnica Básica (`_analise_tecnica`)**:
   * Soma dentro do $\text{IC}_{80\%}$ ($0$ pen), no $\text{IC}_{95\%}$ ($-10$ pts) ou fora do $\text{IC}_{95\%}$ ($-25$ pts).
   * Equilíbrio Par/Ímpar ajustado por densidade ($-10$ a $-25$ pts se extremo).
   * Concentração vertical de linhas vazias ($-5$ pts) e equilíbrio entre metade superior e inferior ($-10$ a $-20$ pts).
   * Repetição excessiva de dígitos finais ($-5$ a $-15$ pts).
3. **Entropia de Shannon dos Gaps (`_analise_entropia`)**:
   $$H(\text{gaps}) = -\sum_{g} p(g) \log_2 p(g)$$
   Penaliza padrões regulares com baixa entropia ($-25$ pts e risco de divisão `ALTO`) e concede bônus ($+5$ pts) para alta entropia.
4. **Heurísticas de Popularidade Humana (`_analise_popularidade` e `_analise_numeros_sortudos`)**: Detecta excesso de datas ($\le 31$), presença da combinação famosa da série *Lost* ($\{4, 8, 15, 16, 23, 42\}$), excesso de sequências consecutivas e concentração de números sortudos culturais.
5. **Distribuição Espacial pelo Coeficiente de Gini (`_calcular_coeficiente_gini`)**:
   $$G = \frac{2 \sum_{i=1}^{k} i \cdot y_{(i)}}{k \sum_{i=1}^{k} y_{(i)}} - \frac{k + 1}{k}, \quad y_i = \frac{x_i - 1}{N - 1}$$
   Premia $G < 0.15$ ($+5$ pts) e penaliza alta concentração espacial $G > 0.50$ ($-10$ pts).
6. **Geometria Empírica com Correção de Bonferroni (`_analise_geometrica`)**: Avalia Moldura, Miolo, Cruz, Xis, Cantos, Colunas, Xadrez e Metades contra a distribuição histórica real.
7. **Propriedades Matemáticas (`_analise_primos`, `_analise_multiplos`, `_analise_quase_reta`)**: Audita quantidade de números primos, concentração de múltiplos de $d \in \{2, 3, 5, 10\}$ e formação de linhas ou colunas quase completas no volante.
8. **Similaridade de Hamming, Quadrantes e Regressão (`_analises_avancadas`)**: Calcula a menor distância de Hamming $d_H(A, B) = |A \triangle B|$ contra os últimos $100$ sorteios (penalizando $-30$ pts se $d_H = 1$ e $-20$ pts se $d_H = 2$), avalia os $4$ quadrantes e concede bônus ($+5$ pts) se o jogo aproveitar números atrasados quando a regressão à média histórica for estatisticamente significativa ($\rho > 0.30, p < 0.05$).
9. **Co-ocorrência Rara e Pares Populares**: Alerta sobre pares que nunca saíram juntos ou pares excessivamente batidos.
10. **Ordem de Saída e Popularidade Medida**: Integra os percentis de `ordem_saida.py` e `popularidade_medida.py`.
11. **Análise Estrutural, Motifs, Simetria de Reflexão e Padrões Avançados (`patterns.py`)**:
    * **Simetria de Reflexão (`calcular_simetria_reflexao`)**: Conta quantos pares espelhados $(n, N + 1 - n)$ existem no bilhete.
    * **Progressão Aritmética Geral (`detectar_progressao_aritmetica_geral`)**: Detecta PAs completas de qualquer razão, múltiplos de bases altas via Máximo Divisor Comum ($\text{MDC}(x_1, \dots, x_k) > 1$) e PAs parciais ($\ge 70\%$ de gaps idênticos).
    * **Sequências Longas, Diagonais e Bordas Extremas**: Penaliza sequências consecutivas $\ge 4$ (ou $\ge 6$ em jogos densos), alinhamentos nas diagonais do volante e concentração nos primeiros ou últimos $20\%$ do universo.
12. **Raridade Conjunta (`_aplicar_raridade_conjunta`)**: Se $2$ ou $3+$ alertas estruturais graves ocorrerem simultaneamente no mesmo bilhete, aplica penalidade composta adicional de $-8$ a $-15$ pontos.
13. **Índice de Compressibilidade (`calcular_indice_compressibilidade`)**: Sintetiza todas as flags estruturais em um índice de $0$ a $100$ (`Excelente`, `Bom`, `Regular`, `Compressível`, `Ultra-compressível`).

---

## 9. Backtest Walk-Forward, Modelo Financeiro e Matriz de Estratégias

**Arquivos**: `backtest.py`, `prize_model.py`, `strategy_matrix.py`

### 9.1 Validação Temporal Walk-Forward (`executar_backtest_temporal` em `backtest.py`)
Para testar se uma estratégia realmente agrega valor sem *data leakage* (olhar o futuro):
1. Define múltiplos pontos de corte cronológicos $c_1, c_2, \dots, c_W$ espaçados por `step` sorteios.
2. Em cada janela $w$:
   * Constrói o contexto `ctx_janela` **exclusivamente** com o passado `df_completo.iloc[:corte]`.
   * Gera $Q$ jogos com o motor **Genético** e $Q$ jogos com o motor **Vetorial**.
   * Confronta os pacotes gerados com os próximos `tamanho_teste` sorteios reais (`df_futuro`).
   * Executa $M$ simulações de **Monte Carlo** (ex.: $500$ pacotes aleatórios) enfrentando exatamente o mesmo `df_futuro`.
3. **Métricas Estatísticas Rigorosas**:
   * **Delta contra o Acaso**: $\Delta_w = \text{Score}_{\text{motor}, w} - \overline{\text{Score}}_{\text{MC}, w}$.
   * **$p$-valor Empírico Unilateral**:
     $$p_{\text{emp}, w} = \frac{\sum_{m=1}^{M} \mathbb{I}(\text{Score}_{\text{MC}, m} \ge \text{Score}_{\text{motor}, w}) + 1}{M + 1}$$
   * **Intervalo de Confiança Bootstrap $95\%$**: Reamostra os deltas das janelas ($B = 2.000$) para verificar se o ganho médio sustenta-se acima de zero.

### 9.2 Diagnóstico Financeiro (`prize_model.py`)
Calcula o desempenho monetário explícito do pacote frente aos sorteios futuros:
* **Custo Total**: $C = Q \times T_{\text{teste}} \times \text{Preço}_{\text{aposta}}$.
* **Receita Bruta ($R$)**, **Lucro Líquido ($L = R - C$)**, **ROI ($L / C$)** e **Fator de Retorno ($R / C$)**, permitindo tabelas de prêmios fixas (como $11, 12, 13$ pontos da Lotofácil) e sobrescritas via CLI para faixas variáveis (`14=1500`, `15=1500000`).

### 9.3 Bancada Científica Multi-Seed (`strategy_matrix.py`)
O módulo `strategy_matrix.py` cruza todas as estratégias (`agressiva`, `cauda_agressiva`, `cauda_convexa`, `cauda_controlada`, `balanceada`, `pura`) contra múltiplas *seeds* padrão (`[7, 21, 42, 77, 101]`) e contra ambos os motores (`Vetorial` e `Genetico`):
* Calcula estatísticas agregadas (média, mediana, desvio padrão populacional, mínimo e máximo) para todas as métricas de acerto, portfólio, calibração e ROI.
* Aplica o `_score_composto` diagnóstico que recompensa acertos reais (`hit_4`, `hit_5`, `hit_6`), delta positivo de acertos contra Monte Carlo e ROI, enquanto **penaliza severamente** instabilidade entre seeds, superexposição de dezenas, overlap alto, trincas/quadras repetidas e divergência de calibração $D_{\text{JS}}$.
* **Sistema Automático de Alertas (`_gerar_alertas_agregado`)**: Emite alertas classificados por severidade (`baixa`, `media`, `alta`) para:
  * `ic_cruza_zero`: $\text{IC}_{95\%}$ inferior do delta de acertos $\le 0$.
  * `dependencia_seed`: Coeficiente de variação de quadras entre seeds $> 0.75$.
  * `concentracao_excessiva`: Exposição máxima média acima do limite ($> 6$ em esparsos, $> 15$ em densos).
  * `overlap_excessivo`: Overlap máximo médio acima do limite ($> 3$ em esparsos, $> 12$ em densos).
  * `trincas_repetidas` e `quadras_repetidas`: Presença de subgrupos repetidos no pacote.
  * `calibracao_artificial`: Divergência de Jensen-Shannon $D_{\text{JS}} > 0.15$.

---

## 10. Guia Prático de Operação para Apostas Reais

Para utilizar toda essa infraestrutura com disciplina científica, siga o protocolo abaixo para cada tipo de jogo:

### 10.1 Receita para Mega-Sena e Quina (Jogos Esparsos)
1. **Estratégia recomendada**: `cauda_convexa` (para pacotes de $5$ a $30$ jogos) ou `cauda_controlada`.
2. **Como gerar**: Utilize sempre a função `generate_real_game_package` (`real_game_mode.py`) com `perfil_esforco="forte"` ou `"maximo"` e `estrategia_base="cauda_convexa"`.
3. **O que verificar no relatório gerado**:
   * `trincas_repetidas` e `quadras_repetidas` em `diagnostico_portfolio` devem ser **iguais a zero** ($0$).
   * `overlap_max` deve ser no máximo $2$ dezenas entre quaisquer dois jogos do pacote.
   * `percentil_vs_monte_carlo` deve estar acima de $80\%$.
   * Ao passar pelo `validar_jogo`, todos os bilhetes devem exibir `ja_saiu: False` e `risco_divisao: "Baixo"`.

### 10.2 Receita para Lotofácil e Lotomania (Jogos Densos)
1. **Abordagem A — Pacote Diversificado (`real_game_mode.py`)**:
   * Use `estrategia_base="balanceada"` ou `"agressiva"` com `usar_ciclo=True` e `usar_markov=True`.
   * Como o ciclo da Lotofácil fecha rápido, o bônus de ciclo ($+0.80$) garante presença das dezenas pendentes sem viciar a geometria do cartão.
2. **Abordagem B — Fechamento Matemático com Garantia (`matrices.py` — Exclusivo Lotofácil)**:
   * Ordene as $25$ dezenas pelo `Peso_Geracao` da Tabela de Inteligência (`get_tabela_inteligencia` em `basic.py`).
   * Escolha as top $17$ dezenas (para gerar $8$ jogos) ou top $18$ dezenas (para gerar $24$ jogos) — cuidando para manter equilíbrio entre pares/ímpares e moldura/miolo no grupo base.
   * Aplique `get_matriz_fechamento(numeros_base, LOTOFACIL)` e valide os cartões gerados no `validator.py`.