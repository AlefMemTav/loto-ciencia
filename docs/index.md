# Documentação Técnica e Científica — LotoCiencia

Esta documentação reúne a especificação arquitetural, a pipeline metodológica e o catálogo completo de algoritmos estatísticos, combinatórios e de aprendizado de máquina do ecossistema **LotoCiencia**.

---

## 1. Visão Geral e Princípios Científicos

### 1.1 O Problema Fundamental das Loterias
Em qualquer loteria honesta onde são sorteadas $k$ bolas dentre $N$ disponíveis sem reposição, o espaço amostral total possui tamanho dado pelo coeficiente binomial:

\[\Omega = \binom{N}{k} = \frac{N!}{k!(N - k)!}\]

Cada bilhete individual possui exatamente a mesma probabilidade matemática de acerto do prêmio principal ($P = 1 / \Omega$). Portanto, **não existe algoritmo capaz de prever o próximo sorteio com certeza**. No entanto, um sistema de engenharia estatística consegue otimizar três dimensões reais:

1. **Plausibilidade Estrutural (Onde a Massa Probabilística Vive)**: Embora a combinação `[01, 02, 03, 04, 05, 06]` tenha a mesma chance individual que `[04, 17, 23, 38, 45, 56]`, a quantidade de combinações com soma central, paridade equilibrada e alta entropia de espaçamentos corresponde a cerca de $90\%$ de todo o espaço $\binom{N}{k}$. Jogar dentro da região de alta densidade combinatória alinha o apostador ao comportamento típico da urna.
2. **Proteção contra Divisão de Prêmio (Valor Esperado Líquido)**: Apostadores humanos são péssimos geradores de números aleatórios. Eles escolhem datas de aniversário ($\le 31$), linhas retas ou diagonais no volante, progressões aritméticas e números da sorte. Sob um volume $N_{\text{apostas}}$ de bilhetes concorrentes onde o número de co-ganhadores na combinação $x$ segue $\text{Poisson}(\lambda(x))$ com $\lambda(x) = N_{\text{apostas}} \cdot P_{\text{acerto}} \cdot r(x)$ ($r(x)$ = razão de popularidade medida), o retorno condicional esperado no prêmio principal de valor $V$ é:
   \[E[\text{Retorno}(x) \mid x \text{ sorteado}] = V \cdot E\left[\frac{1}{1 + W(x)}\right] = V \cdot \frac{1 - e^{-\lambda(x)}}{\lambda(x)}\]
   Evitar combinações populares ($r(x) \le 0{,}75\text{--}0{,}80$) não altera a probabilidade individual $P(x \text{ sorteado}) = 1/\Omega$, mas **multiplica a retenção esperada do prêmio** ao reduzir a probabilidade de divisão com a multidão.
3. **Eficiência de Cobertura de Portfólio (Pacote de Jogos)**: Quando se aposta mais de um jogo, os bilhetes não devem competir entre si. Controlar a exposição máxima por dezena, distribuir os cartões entre arquétipos estruturais e proibir repetições excessivas de pares, trincas e quadras maximiza a área coberta do espaço combinatório.

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
| **Lotomania** | `loto_mania_sorteio` | $100$ | $20$ | $50$ | $10 \times 10$ | $0.50$ ($50\%$) | $1$ em $11.372.635{,}9$ |

### 3.2 Geometria do Volante (`BoardLayout` em `models.py`)
Mapeia qualquer dezena $n \in \{1, \dots, N\}$ para coordenadas bidimensionais zero-based $(r, c)$:

\[r = \lfloor (n - 1) / C \rfloor, \quad c = (n - 1) \bmod C\]

A partir de $(r, c)$, o sistema extrai automaticamente subconjuntos geométricos do volante:

* **Moldura (Borda)**: $\{n \mid r \in \{0, R - 1\} \lor c \in \{0, C - 1\}\}$.
* **Miolo (Centro)**: Complementar da moldura no universo $\{1, \dots, N\}$.
* **Cantos**: Os 4 vértices extremos $(0, 0), (0, C-1), (R-1, 0), (R-1, C-1)$.
* **Cruz**: Linha(s) e coluna(s) centrais (1 linha/coluna se ímpar, 2 se par).
* **Xis (Diagonais)**: Diagonal principal ($r = c$ com $r < \min(R, C)$) e diagonal secundária ($r + c = C - 1$).
* **Quadrantes ($Q_1, Q_2, Q_3, Q_4$)**: Divisão do volante ao meio em $R/2$ e $C/2$.
* **Xadrez**: Partição em casas brancas ($(r + c) \bmod 2 = 0$) e casas pretas ($(r + c) \bmod 2 = 1$).
* **Anéis Concêntricos (Distância de Manhattan)**: Mede a distância ao centro simétrico zero-based $(r_c, c_c) = \left(\frac{R - 1}{2}, \frac{C - 1}{2}\right)$:
  \(d_{\text{Manhattan}}(n) = |r - r_c| + |c - c_c|\)
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

\[\alpha_{\text{Bonferroni}} = \frac{\alpha_{\text{family}}}{15} = \frac{0.05}{15} \approx 0.00333\]

Isso redefine os limiares críticos de Z-score (`compute_zscore` em `basic.py`, dado por $Z = \frac{x - \mu}{\sigma + 10^{-9}}$):

* `ZSCORE_EXTREME` $= 2.97$ (evento de $\sim 0.3\%$ após correção; penalidade peso $3.0$).
* `ZSCORE_VERY_RARE` $= 2.39$ (evento de $\sim 1.7\%$; penalidade peso $2.0$).
* `ZSCORE_RARE` $= 1.64$ (evento de $\sim 10\%$; penalidade peso $1.0$).

Além disso, a função `ajustar_threshold_por_densidade(valor_base, densidade)` relaxa limiares **superiores** em $+50\%$ para jogos com $d \ge 0.50$ e em $+20\%$ para $0.30 \le d < 0.50$; inversamente, `ajustar_threshold_inferior_por_densidade(valor_base, densidade)` relaxa limiares **inferiores** (dividindo por $1.5$ ou $1.2$) para métricas como entropia, `cv_gaps` e `span_relativo`, onde jogos densos possuem naturalmente valores menores.

### 4.2 Tabela de Inteligência (`get_tabela_inteligencia` em `basic.py`)
Para cada dezena $n \in \{1, \dots, N\}$, consolida:
1. **Frequência ($F_n$)**: Total de aparições históricas e seu respectivo $Z_{\text{Freq}}$.
2. **Atraso Atual ($G_n$)**: Quantidade de concursos desde a última aparição (`calcular_atrasos`) e seu respectivo $Z_{\text{Gap}}$.
3. **Peso Composto Base**:
   \(P_n = 0.40 \cdot Z_{\text{Freq}}(n) + 0.60 \cdot Z_{\text{Gap}}(n)\)
4. **Peso de Geração Normalizado**: Escalonado para $[0.01, 1.01]$ via Min-Max scaling, além dos percentis empíricos `Percentil_Freq` e `Percentil_Gap`. No gerador padrão, esses sinais permanecem **desligados** (amostragem uniforme); a tabela tem caráter exploratório/descritivo.

### 4.3 Testes de Honestidade e Distribuições (`distributions.py`)

* **Teste Qui-Quadrado ($\chi^2$) sem reposição e Kolmogorov-Smirnov discreto (`calcular_chi_quadrado`)**: Compara a frequência observada $O_n$ de cada bola com a frequência uniforme esperada $E_n = \frac{T \cdot k}{N}$, corrigindo a estatística pelo fator de população finita $\frac{N - 1}{N - k}$:
  \(\chi^2_{\text{hiper}} = \left(\frac{N - 1}{N - k}\right) \sum_{n=1}^{N} \frac{(O_n - E_n)^2}{E_n}\)
  O $p$-valor de Kolmogorov-Smirnov é obtido para a distribuição **discreta** em $\{1, \dots, N\}$ comparando a FDA empírica com $2.000$ simulações multinomiais escalonadas por $\sqrt{(N - k)/(N - 1)}$. Se $p_{\chi^2} > 0.05$ e $p_{\text{KS}} > 0.05$, classifica o sorteio como **Honesto (Aleatório)**.

* **Análise dos Dígitos Finais sem Reposição com Holm-Bonferroni (`analise_poisson`)**: Verifica se os terminais $0 \dots 9$ (cada um com $M_d$ dezenas no universo $N$) aderem à esperança $E_d = T \cdot k \cdot \frac{M_d}{N}$ utilizando a **variância hipergeométrica exata sem reposição**:
  \(\text{Var}(C_d) = T \cdot k \cdot \frac{M_d}{N} \cdot \left(1 - \frac{M_d}{N}\right) \cdot \frac{N - k}{N - 1}\)
  Os $10$ $p$-valores bilaterais (`p_value_bruto`) são ajustados por **Holm-Bonferroni** (`p_value`) para controlar o erro familiar global.
* **Estatísticas de Ordem (`calcular_order_statistics`)**: Para um bilhete ordenado $x_{(1)} < x_{(2)} < \dots < x_{(k)}$, a posição esperada da $i$-ésima menor dezena em um sorteio uniforme é:
  \(E[X_{(i)}] = i \cdot \frac{N + 1}{k + 1}\)
  O algoritmo calcula o desvio médio relativo normalizado por $(N/k)$ para detectar números excessivamente deslocados para o início ou fim do volante.

* **Distribuição Discreta de Gaps Internos (`testar_distribuicao_gaps_bilhete` e `detectar_motifs_gaps`)**: Avalia os intervalos $g_i = x_{(i+1)} - x_{(i)}$ e seu coeficiente de variação $\text{CV}_{\text{gaps}} = \sigma_g / \mu_g$ contra quantis discretos calibrados do modelo nulo (`_GAPS_CV_NULL_CACHE`, evitando falsos positivos do teste KS contínuo em jogos densos como Lotofácil/Lotomania), além de buscar *motifs* periódicos como $[a, a, \dots]$, alternâncias $[a, b, a, b]$ ou subsequências repetidas.

### 4.4 Auditoria Forense da Ordem de Saída das Bolas (`ordem_saida.py`)
Analisa as colunas `D1..Dk` na ordem exata em que foram sorteadas do globo:
1. **Filtro de Dados Antigos Ordenados (`mascara_ordem_de_saida`)**: Algumas bases históricas antigas (ex.: Quina) registravam os primeiros concursos em ordem crescente em vez da ordem de sorteio. Como a chance de uma linha real sair estritamente crescente por acaso é $1 / k!$, o algoritmo encontra o ponto de corte ótimo $c^*$ que minimiza o custo de incoerência:
   \(\text{custo}(c) = \sum_{t=0}^{c-1} (1 - I_{\text{crescente}}(t)) + \sum_{t=c}^{T-1} I_{\text{crescente}}(t)\)
   Descartando automaticamente o bloco corrompido $[0, c^*)$.
2. **Teste Posicional com Correção FDR (Benjamini-Hochberg)**: Normaliza a ordem de saída em $[0, 1]$ ($0 =$ primeira bola, $1 =$ última bola). Sob $H_0$, a posição média esperada de cada dezena é $0.50$, com variância teórica:
   \(\text{Var}(P) = \frac{k + 1}{12(k - 1)}\)
   Calcula o Z-score por dezena e controla a Taxa de Falsas Descobertas (*False Discovery Rate* — FDR a $5\%$) pelo procedimento step-up de **Benjamini-Hochberg** (`benjamini_hochberg` em `multiple_testing.py`), além de testar a uniformidade da primeira e da última bola via $\chi^2$.
3. **Auditoria Forense Espectral (FFT + Teste $g$ de Fisher) e Sample Entropy (`_teste_espectral_fisher_fft`, `_sample_entropy`)**: Aplica a Transformada Rápida de Fourier (FFT) sobre a sequência temporal padronizada da 1ª bola sorteada (`D1`) e testa o maior pico do periodograma pela estatística exata $g$ de Fisher (`fft_d1_g`, `fft_d1_p_fisher`), em conjunto com a **Sample Entropy (`sampen_d1`, $m=2, r=0{,}2\sigma$)** para medir previsibilidade sequencial residual.

### 4.5 Bootstrap Vetorizado, Intervalo de Predição e Matrizes Binárias (`monte_carlo.py`, `bootstrap_integration.py` e `basic.py`)

* **Bootstrap Vetorizado da Média vs. Intervalo de Predição de Bilhete Único (`bootstrap_ic_soma`)**: Realiza $B = 5.000$ (ou $10.000$) reamostragens com reposição das somas históricas em blocos matriciais (`chunk_size = 500`), separando explicitamente dois intervalos estatísticos distintos:
  1. **IC Bootstrap $95\%$ da Média Histórica** (`ic_media_lower`, `ic_media_upper`): mede a incerteza da média populacional das somas ($\sim \pm 1{,}5$ pontos após milhares de sorteios).
  2. **Intervalo de Predição $95\%$ de um Bilhete Único** (`pred_lower`, `pred_upper`): faixa $P_{2{,}5}\text{--}P_{97{,}5}$ onde caem $95\%$ dos bilhetes individuais. Quando $k_{\text{bet}} \ne k$ (Lotomania: aposta $m = 50$ vs. sorteio $k = 20$), utiliza a distribuição hipergeométrica exata da soma ($\mu = m\frac{N+1}{2}$, $\sigma = \sqrt{m\frac{N^2 - 1}{12}\frac{N - m}{N - 1}}$) para evitar o colapso de escala.
* **Validação Cruzada de Soma (`avaliar_soma_com_bootstrap`)**: Valida a soma do bilhete contra o **Intervalo de Predição $95\%$** (`pred_lower`–`pred_upper`), preservando o IC da média histórica como metadado informativo.
* **Indexação Binária de Sorteios (`build_draws_binary_matrix`)**: Pré-computa a matriz booleana $B_{\text{hist}} \in \{0, 1\}^{T \times N}$ em `GameContext.draws_bin`, permitindo que `verificar_historico` e `calcular_distribuicao_hamming` calculem acertos e distâncias de Hamming contra todo o histórico por produto matricial $B_{\text{hist}} \cdot v$ sem iterar linha a linha sobre o `DataFrame`.

---

### 4.6 Auditoria de Independência entre Sorteios (`auditoria_independencia.py`)
`auditar_independencia` roda uma bateria de oito testes que perguntam se o histórico mostra alguma dependência que valha explorar. Sob $H_0$ os sorteios são independentes e as bolas saem em ordem uniforme:

* **Soma jogo a jogo**: autocorrelação lag 1 e tamanho médio de $|\Delta \text{soma}|$ (ambos por permutação da ordem dos sorteios), Ljung-Box em 10 lags, transição entre tercis da soma (qui-quadrado $3 \times 3$) e runs da soma acima/abaixo da mediana (Wald-Wolfowitz).
* **Repetição do sorteio anterior**: distribuição de quantos números repetem, contra a hipergeométrica $\text{Hip}(N, k, k)$ (qui-quadrado com classes agrupadas até esperado $\ge 5$).
* **Ordem de saída** (só nas linhas na ordem real, via `mascara_ordem_de_saida`): correlação de Spearman média entre posição de saída e valor da bola (com $\text{Var}(\rho) = 1/(k-1)$ por sorteio) e uniformidade da posição em que sai o menor número.

Os p-valores são ajustados por **Holm-Bonferroni** (`multiple_testing.py`), que não supõe nenhuma estrutura de dependência entre os testes. Simulações com sorteios independentes mostram que cada teste rejeita em cerca de $5\%$ dos conjuntos e que a bateria inteira rejeita algo em $2$ a $7\%$ deles. Nos históricos reais das quatro modalidades, nenhum dos oito testes rejeita após o ajuste (menores p ajustados: $0{,}53$ na Lotomania e $0{,}58$ na Mega-Sena; $1{,}0$ na Quina e na Lotofácil).

Ausência de rejeição não prova independência, e uma rejeição isolada não é sinal explorável: antes de usá-la em geração, deve ser confirmada fora da amostra pelo backtest walk-forward (seção 9.1).

## 5. Sinais Avançados, Séries Temporais e Machine Learning

**Arquivos**: `advanced.py`, `temporal.py`, `similarity.py`, `geometry.py`, `clustering.py`, `cluster_profile.py`, `popularidade_medida.py`

### 5.1 Matriz de Co-ocorrência Normalizada (`advanced.py`)
Mede a afinidade histórica entre pares de dezenas $(i, j)$ normalizada pela esperança hipergeométrica sob independência:

\[P_{\text{esperada}}(i \land j) = \frac{\binom{N - 2}{k - 2}}{\binom{N}{k}} = \frac{k(k - 1)}{N(N - 1)}\]

\[M_{\text{cooc}}[i, j] = \frac{\text{Ocorrências}(i, j)}{T \cdot P_{\text{esperada}}(i \land j) + 10^{-9}}\]

Valores $M_{\text{cooc}}[i, j] > 1.0$ indicam pares que saíram juntos acima do esperado (`get_pares_mais_frequentes`), enquanto valores próximos de $0$ identificam pares que historicamente "se repelem" (`get_pares_que_se_repelem`).

### 5.2 Cadeias de Markov de 1ª Ordem (`advanced.py`)
Constrói a matriz de transição estocástica $M_{\text{trans}}[i, j] = P(j \in \text{Sorteio}_{t+1} \mid i \in \text{Sorteio}_t)$, normalizada por linha. A função `analisar_transicoes_anomalas` compara a contagem observada de cada transição com a obtida ao **embaralhar a ordem dos sorteios** (500 permutações por padrão), o que preserva a frequência de cada dezena e destrói qualquer dependência entre sorteios consecutivos. Cada célula é padronizada pela média e pelo desvio dessas permutações (incluindo o histórico real, para que ele e as permutações sejam tratados de forma simétrica) e só é sinalizada se $|Z| \ge 2.5$ **e** o p-valor ajustado pelo método *max-T* de Westfall-Young ficar abaixo de $5\%$.

A fórmula fechada $E_{ij} = (T - 1) \cdot (k / N)^2$ (contagem $\text{Binomial}(T - 1, p^2)$ com $p = k / N$) é a esperança correta sob independência, mas não é usada como referência: as células da diagonal ($i \to i$) têm variância $1 + 2p/(1+p)$ vezes maior que a binomial ($1{,}75\times$ na Lotofácil), e as demais são dependentes entre si porque cada sorteio tem exatamente $k$ números. Em simulações com sorteios independentes, a versão binomial reportava ao menos uma transição falsa em $11\%$ dos conjuntos de Lotofácil; a versão por permutação, em $2$ a $6\%$ (Lotofácil, Mega-Sena e Quina).

### 5.3 Teste de Runs de Wald-Wolfowitz e Índice VMR sem Reposição (`advanced.py`)

* **Teste de Runs (`teste_runs_numero`)**: Converte o histórico de cada dezena em uma sequência binária de presenças ($n_1$) e ausências ($n_0$). Conta o número de *runs* (sequências contínuas de $1$s ou $0$s) e compara com a esperança e variância exatas sob aleatoriedade:
  \(\mu_R = \frac{2 n_1 n_0}{n_1 + n_0} + 1, \quad \sigma_R^2 = \frac{2 n_1 n_0 (2 n_1 n_0 - n_1 - n_0)}{(n_1 + n_0)^2 (n_1 + n_0 - 1)}\)
* **Índice de Dispersão VMR com Correção de População Finita (`indice_dispersao`)**: Calcula a razão variância-média das frequências ($\text{VMR} = s^2 / \bar{x}$). Como cada concurso sorteia $k$ bolas **sem reposição** dentre $N$, a razão esperada sob uniformidade é $f_{\text{FPC}} = \left(1 - \frac{k}{N}\right)\frac{N}{N - 1}$ (ex.: $0{,}4167$ na Lotofácil, e não $1{,}0$!). O índice é reescalonado por $\text{VMR}_{\text{corrigido}} = \text{VMR} / f_{\text{FPC}}$, de modo que $(N - 1)\cdot \text{VMR}_{\text{corrigido}} \sim \chi^2_{N-1}$.

### 5.4 Calibração Dinâmica de Pesos — "Autópsia dos Vencedores" (`advanced.py`)
A função `calibrar_pesos_dinamicos` substitui escolhas arbitrárias entre números quentes e atrasados por uma fusão Bayesiana empírica:
1. Seleciona uma janela recente adaptada à densidade ($100$ sorteios para jogos densos, $300$ para esparsos).
2. Extrai de forma vetorizada todos os intervalos reais ($\Delta t$) entre aparições consecutivas de cada dezena na janela.
3. Compara cada intervalo real com o **Gap Teórico** $\mu_{\text{gap}} = N / k$:
   * Retorno rápido ($\Delta t \le N / k$): ponto para **Frequência** ($p_{\text{freq}}$).
   * Retorno lento ($\Delta t > N / k$): ponto para **Atraso/Gap** ($p_{\text{gap}}$).
4. **Fusão Bayesiana**: Combina a evidência recente (confiança de $75\%$) com a distribuição *prior* da natureza do jogo ($P_{\text{prior}} = 0.70$ para densos, $0.30$ para esparsos):
   \(w_{\text{freq}} = 0.75 \cdot p_{\text{freq}} + 0.25 \cdot P_{\text{prior}}, \quad w_{\text{gap}} = 1.0 - w_{\text{freq}}\)
### 5.5 Ciclos, Eletrocardiograma de Somas e Regressão à Média (`temporal.py` e `similarity.py`)

* **Ciclo das Dezenas (`calcular_ciclo_atual`)**: Monitora o *Coupon Collector's Problem*, identificando exatamente quais dezenas ainda faltam sair para fechar o ciclo atual de $1$ a $N$.
* **Eletrocardiograma das Somas (`analise_temporal_somas`)**: Calcula a média teórica da soma e seu desvio padrão exato com fator de correção para população finita:
  \(\mu_{\text{soma}} = k \frac{N + 1}{2}, \quad \sigma_{\text{soma}} = \sqrt{k \left(\frac{N^2 - 1}{12}\right) \left(\frac{N - k}{N - 1}\right)}\)
  Define a banda de normalidade em $[\mu_{\text{soma}} - 2\sigma_{\text{soma}}, \mu_{\text{soma}} + 2\sigma_{\text{soma}}]$.

* **Autocorrelação de Frequências (`calcular_autocorrelacao_frequencias`)**: Divide o histórico em janelas de $w$ sorteios, conta quantas vezes cada dezena saiu em cada janela e calcula, para cada dezena, a autocorrelação dessa série de contagens, tirando a média entre as $N$ dezenas. O estimador com média removida tem viés $-(W - k)/(W(W-1))$ sob ruído branco ($W$ = nº de janelas, $k$ = lag), que é subtraído. Sob independência a média tem desvio $\approx 1/\sqrt{W \cdot N}$, e o limite de significância usa correção de Bonferroni sobre os lags testados (sem ela, com 50 lags, a chance de algum passar por acaso é de $\approx 92\%$).

* **Validação de Regressão à Média e Aderência Discreta à Geométrica (`calcular_taxa_regressao` e `analisar_gaps_geometricos` em `similarity.py`)**: Mede a correlação de Spearman ($\rho$) entre o atraso passado e a frequência futura na janela seguinte. Para os intervalos de espera $\Delta t \ge 1$ de cada dezena, extrai as aparições de forma vetorizada e avalia a aderência à distribuição $\text{Geom}(p = k/N)$ usando a estatística supremum discreta $D_{\text{disc}} = \max_{g \ge 1} |F_n(g) - F_{\text{Geom}}(g)|$ (evitando o artefato de salto $F_n(g^-)$ do teste KS contínuo em variáveis discretas) em conjunto com o teste Qui-Quadrado agrupado (`_chi2_geometric_gof` com contagem esperada $\ge 5$ por classe).

### 5.6 Clusterização sem Colinearidade e Distância de Mahalanobis (`clustering.py` e `cluster_profile.py`)
Cada jogo gera um vetor completo de $9$ métricas (`extrair_features_jogo` / `extrair_features_jogos_batch`):
`[soma, media, prop_pares, prop_baixos, gap_medio, gap_std, sequencias, prop_finais_unicos, amplitude_relativa]`.

* **Eliminação de Colinearidade Exata (`INDEPENDENT_FEATURE_INDICES`)**: Como `media = soma / k` e `gap_medio = amplitude / (k - 1)` são combinações lineares exatas de `soma` e `amplitude_relativa` (o que tornava a matriz de covariância singular e distorcia a distância Euclidiana), tanto o K-Means quanto o DBSCAN e a distância de Mahalanobis operam estritamente sobre as **$7$ dimensões linearmente independentes** `(0, 2, 3, 5, 6, 7, 8)`.
* **K-Means + Distância de Mahalanobis Descritiva (`clusterizar_jogos_kmeans`, `calcular_referencia_mahalanobis`)**: Padroniza as $7$ features com `StandardScaler`, estima a covariância regularizada $\Sigma + \epsilon I$ e persiste $\Sigma^{-1}$ e os quantis empíricos de $D_M(x) = \sqrt{(x - \mu)^\top \Sigma^{-1}(x - \mu)}$ (`mahal_p95`, `mahal_p99`).
* **Calibração Nula para $k_{\text{bet}} \ne k$ (Lotomania)**: Em `analisar_perfil_cluster`, quando o tamanho do bilhete difere do sorteio ($50$ dezenas vs. $20$ sorteadas na Lotomania), a referência de Mahalanobis e o limiar de outlier são calibrados sobre o próprio modelo nulo de $k_{\text{bet}} = 50$ dezenas (`_get_null_mahalanobis_ref`), eliminando o falso-positivo de $100\%$ de outliers causado pela comparação direta de somas de $50$ dezenas contra centróides de $20$.
* **DBSCAN (`clusterizar_jogos_dbscan`)**: Agrupamento baseado em densidade no espaço $7\text{D}$ padronizado que isola combinações extremas como ruído (`label = -1`).

### 5.7 Modelo Econométrico de Popularidade Medida (`popularidade_medida.py`)
Estima a popularidade empírica de cada combinação diretamente a partir dos rateios reais da Caixa (`data/detalhes/<loteria>_detalhes.csv`):
1. **Filtro Causal de Integridade de Arrecadação (`filtrar_arrecadacao_valida_causal`)**: Descarta automaticamente registros corrompidos de arrecadação na API da Caixa (ex.: concurso `994` da Mega-Sena com `valorArrecadado = R$ 158,15` frente a $\sim\text{R\$ } 30\text{M}$, que criava um resíduo aberrante de $+12{,}4$ em escala log e degradava o $R^2_{\text{CV}}$ da Mega-Sena de $0{,}719$ para $0{,}378$). O filtro é estritamente causal: usa apenas a mediana móvel passada (`[0.05x, 20x]` da mediana anterior).
2. **Seleção de Faixa (`_escolher_faixa`)**: Escolhe a faixa de maior prêmio com mediana de ganhadores $\ge 300$ (Quadra da Mega-Sena, Terno da Quina, $14$ pontos da Lotofácil, $17$ pontos da Lotomania).
3. **Normalização Causal contra Mudanças de Regime (`_causal_rolling_median`)**: Centra a variável dependente $y_t = \log\left(\frac{\text{Ganhadores}_t + 0.5}{\text{Arrecadado}_t} \times 10^6\right)$ pela mediana móvel estritamente causal dos últimos $50$ concursos anteriores para absorver reajustes discretos no preço das apostas sem vazamento temporal.
4. **Regressão Huber-IRLS Ridge + Kernel de Interações de Pares de 2ª Ordem + WLS Exponencial**:
   * **Huber-IRLS (`_ridge_huber`)**: Substitui o ajuste quadrático puro por M-estimação robusta de Huber ($\delta = 1{,}35 \cdot \text{MAD}$), protegendo os coeficientes contra sorteios atípicos.
   * **Kernel Dual de Interações de Pares ($\gamma_{ij}$)**: Modela interações de 2ª ordem entre pares de dezenas co-apostadas por humanos (ex.: combinações de aniversário, colunas/linhas do volante) em forma fechada dual (`_fit_pair_kernel_alpha` via fatoração de Cholesky `cho_factor`/`cho_solve` sobre janela recente de até $2.200$ concursos), selecionado exclusivamente por validação cruzada temporal quando eleva $R^2_{\text{CV}}$.
   * **Calibração de Inclinação Out-of-Sample (`cal_slope`), Intervalo Conformal $90\%$ (`conformal_q90_log`) e Monitor de Drift (`diagnostico_modelo`)**: Ajusta a calibração linear fora da amostra nos folds da CV temporal, estima o quantil split-conformal $q_{90}$ dos resíduos em escala log (`razao_ic90_low` / `razao_ic90_high`) e monitora continuamente o $R^2$ dos últimos $250$ concursos (`r2_recente`, `drift_alerta`).
5. **Desempenho Medido Fora da Amostra (CV Temporal em $6$ Blocos Expansivos)**:
   * **Mega-Sena**: **$R^2_{\text{CV}} = 0{,}7185$** ($R^2_{\text{recente}} = 0{,}7664$, Huber + pares $\lambda_{\text{par}} = 100$, $1$ outlier filtrado).
   * **Quina**: **$R^2_{\text{CV}} = 0{,}7886$** ($R^2_{\text{recente}} = 0{,}8501$, Huber + pares $\lambda_{\text{par}} = 30$).
   * **Lotofácil**: **$R^2_{\text{CV}} = 0{,}6007$** ($R^2_{\text{recente}} = 0{,}6196$, Huber).
   * **Lotomania**: **$R^2_{\text{CV}} = 0{,}3891$** ($R^2_{\text{recente}} = 0{,}4104$, Huber).
6. **Reescalonamento Hipergeométrico e Proteção-Espelho Dual na Lotomania (`_log_score_batch`)**: Para $m = 50 \ne k = 20$, reescalona os pesos individuais por $k / m = 0{,}40$, padroniza as features estruturais contra o modelo nulo de $50$ dezenas e combina o risco das faixas principais ($97{,}5\%$) com o bilhete-espelho $J^c$ para a faixa de $0$ acerto ($2{,}5\%$):
   \[S_{\text{Lotomania}}(J) = 0{,}975 \cdot S(J) + 0{,}025 \cdot S(J^c)\]

---

## 6. Modelo Nulo Combinatório e Calibração Estrutural

**Arquivos**: `ticket_features.py`, `null_model.py`, `feature_percentiles.py`, `score_calibration.py`

### 6.1 Extração Vetorizada de Features (`ticket_features.py`)
A função `extract_ticket_features_batch` processa dezenas de milhares de candidatos simultaneamente em NumPy puro (sem loops por linha, via contagem por `np.bincount`, máscaras geométricas pré-computadas do `BoardLayout` e detecção vetorizada de sequências/gaps), extraindo **$28$ métricas objetivas**:
`soma`, `pares`, `span`, `min_gap`, `max_gap`, `gap_medio`, `gap_variety`, `gap_regularidade`, `entropia_gaps`, `max_sequencia`, `max_final_repetido`, `finais_unicos`, `superior`, `inferior`, `max_dezena_repetida`, `max_linha`, `std_linhas`, `max_coluna`, `max_quadrante`, `moldura`, `cruz`, `xis`, `cantos`, `diag_principal`, `diag_secundaria`, `multiplos_5`, `simetria_reflexao` e o índice contínuo `compressibilidade_simples` $\in [0, 1]$:

\[\text{Compressibilidade} = \text{clip}\left(0.55 \cdot \hat{H}_{\text{norm}}(\text{gaps}) + 0.35 \cdot \text{VarGaps} - 0.20 \cdot \text{Pen}_{\text{seq}} - 0.10 \cdot \text{Pen}_{\text{final}}, \, 0, \, 1\right)\]

### 6.2 Modelo Nulo Combinatório (`null_model.py` e `feature_percentiles.py`)
Para saber se uma métrica é "rara" ou "comum" sem usar limiares arbitrários:
1. `build_null_model` (versão `null-model-v2`) sorteia $M = 50.000$ jogos uniformemente distribuídos no espaço $\binom{N}{k_{\text{bet}}}$ usando partição rápida de matrizes aleatórias (`np.argpartition`).
2. Ordena e armazena em cache o vetor de cada uma das $28$ métricas (das quais $22$ entram diretamente na avaliação de percentis do gerador).
3. `batch_feature_percentiles` converte qualquer métrica bruta de um bilhete em seu **percentil combinatório exato** ($0$ a $100$) em tempo $O(\log M)$ via busca binária vetorizada (`np.searchsorted`).

### 6.3 Calibração de Score Estrutural (`score_calibration.py`)
Impede que o gerador produza apenas bilhetes "artificialmente perfeitos" (concentrados na faixa $70\text{--}100$), forçando a distribuição do pacote gerado a imitar a distribuição real da natureza:
1. Calcula um score estrutural independente do validador (`score_structural_from_percentiles`, versão `score-cal-v3`), combinando métricas centrais (ótimo em torno do percentil $50$, incluindo `moldura`, `cruz`, `std_linhas`), métricas onde valores altos são ruins (incluindo `diag_principal`, `diag_secundaria`, `simetria_reflexao`, `gap_regularidade`) e métricas onde valores baixos são ruins (`min_gap`, `compressibilidade_simples`, `finais_unicos`). As penalidades de cauda extrema em `max_sequencia` e `max_final_repetido` usam o **percentil $99$ do modelo nulo** da própria modalidade (com piso $3$).
2. Divide o score em $5$ *buckets*: `0-39`, `40-54`, `55-69`, `70-84`, `85-100`.
3. Quando $k_{\text{bet}} = k$, avalia os sorteios históricos diretamente (`modo_historico = "exato"`) e define a distribuição alvo como:
   \(P_{\text{alvo}}(b) = 0.70 \cdot P_{\text{histórico}}(b) + 0.30 \cdot P_{\text{modelo\_nulo}}(b)\)
   Quando $k_{\text{bet}} \ne k$ (Lotomania, onde o sorteio tem $k=20$ bolas e a aposta tem $k_{\text{bet}}=50$), avalia o histórico na escala do sorteio (`replace(config, bet_k=None)`, `modo_historico = "escala_sorteio_k"`) e combina $50\%$ histórico em escala de sorteio + $50\%$ modelo nulo da aposta.
4. Calcula o *log-prior* de calibração para cada candidato no bucket $b$:
   \(\text{Prior}(b) = \text{clip}\left(\ln\left(\frac{P_{\text{alvo}}(b)}{0.20}\right), \, -1.5, \, 1.5\right)\)
5. Audita a fidelidade do pacote gerado medindo a **Divergência de Jensen-Shannon ($D_{\text{JS}}$)** entre a distribuição gerada $P$ e a distribuição alvo $Q$ (onde $M = \frac{1}{2}(P + Q)$):
   \(D_{\text{JS}}(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M)\)
---

## 7. Motores de Geração, Função Objetivo e Fechamentos

**Arquivos**: `generator_objective.py`, `generator_fast.py`, `generator_genetic.py`, `real_game_mode.py`, `matrices.py`

### 7.1 Função Objetivo Própria do Gerador (`generator_objective.py`)
A função `score_plausibility_batch` pontua lotes massivos de candidatos combinando $7$ camadas independentes:
1. **Aderência Central e Penalidade de Caudas Combinatórias**: Premia candidatos próximos à mediana combinatória ($\text{percentil} = 50$) nas $22$ features estruturais/geométricas e penaliza violações fora da janela $[\text{percentil\_min}, \text{percentil\_max}]$ (padrão $[5\%, 95\%]$, expandido para $[4\%, 96\%]$ em `cauda_controlada`).
2. **Prior de Calibração Estrutural**: Soma $0.35 \times \text{calibration\_strength} \times \text{Prior}(b)$.
3. **Penalidade Anti-Números da Sorte**: Desconta $1.5$ ponto se o bilhete contiver excesso de números culturais $\{3, 7, 9, 11, 13, 21, 27, 33\}$.
4. **Sinais Históricos Controlados (Clipped)** — *desligados por padrão*: em walk-forward (2.700 a 6.800 sorteios por jogo) quentes, atrasados, Markov, ciclo e co-ocorrência não se separaram do acaso após correção para múltiplos testes (co-ocorrência: nulo em 3 jogos; Lotofácil z = +2,69, abaixo do corte de 28 testes). Quando ligados, incorpora as médias de $Z_{\text{Freq}}$ (peso $0.30$) e $Z_{\text{Gap}}$ (peso $0.22$) truncadas em $[-2.0, 2.0]$ para evitar que uma única bola domine o bilhete.
5. **Co-ocorrência com Controle de Cauda** — *desligada por padrão (`usar_coocorrencia=False`)*: quando habilitada, calcula o Z-score da soma de co-ocorrências do bilhete (`cooc_z`) via indexação triangular superior (`np.triu_indices`). Na estratégia `cauda_controlada`, premia sinergia moderada e penaliza excesso acima de $2.0\sigma\text{--}2.5\sigma$.
6. **Popularidade Medida, Modulação por Elasticidade de Poisson, Corte e Ordem de Saída**: Desconta até $2.0 \times \text{força}$ para jogos com percentil de popularidade real acima de $60\%$ (incluindo a Lotomania com escala $k/m$ e proteção-espelho de $0$ acerto) e aplica leve correção contra extremos posicionais ($< 5\%$ ou $> 95\%$). A força anti-popular é modulada dinamicamente pela **elasticidade do prêmio esperado à diluição de Poisson** (`ctx.elasticidade_antipopular`, calculada em `prize_model.py`), intensificando a proteção anti-multidão em concursos acumulados ou especiais onde a probabilidade de haver co-ganhadores é alta. Na **Mega-Sena** ($R^2_{\text{CV}} \approx 0{,}719$), na **Quina** ($R^2_{\text{CV}} \approx 0{,}789$) e na **Lotofácil** ($R^2_{\text{CV}} \approx 0{,}601$), há ainda um **corte**: jogos com razão de ganhadores prevista acima de $0{,}75$ (Mega-Sena e Lotofácil) ou $0{,}80$ (Quina) levam penalidade de $100$ pontos (`PENALIDADE_CORTE_POPULARIDADE`) e só entram no pacote se faltarem alternativas (`LIMIAR_RAZAO_GANHADORES`, `usar_corte_popularidade`).
7. **Eliminação de Jogos Já Sorteados e Quase-Clones Recentes**: Qualquer combinação presente em `ctx.historico_set` é filtrada (`scores <= -1e8`) antes da padronização `score_z` do portfólio, e candidatos a distância de Hamming $\le 1$ dos últimos $10$ sorteios recebem penalidade anti-clone recente.

### 7.2 Seleção de Portfólio, Calibração por Cotas de Hamilton e Refinamento 1-opt de Cobertura (`select_diverse_portfolio`)
O módulo suporta $3$ estratégias (`balanceada`, `cauda_controlada` e `pura`), mantendo `agressiva`/`conservadora` como apelidos de `balanceada` e `cauda_agressiva`/`cauda_convexa` como apelidos de `cauda_controlada` (`app/core/strategies.py`).

* **Padronização Limpa (`score_z`)**: Em `cauda_controlada` e no torneio do `real_game_mode.py`, a média e o desvio-padrão usados para padronizar `score_z` são calculados exclusivamente sobre candidatos que passaram pelo corte de popularidade (`scores > -50.0`), garantindo que bilhetes penalizados pelo corte permaneçam mais de $20\sigma$ abaixo do pool válido.
* **Cotas de Bucket de Hamilton e Diversidade de Arquétipos**: Tanto `balanceada` quanto `cauda_controlada` alocam cotas inteiras de maior resto ($Q_b = \lfloor P_{\text{alvo}}(b) \cdot Q \rfloor$) nos $5$ *buckets* do `score_calibration.py` e distribuem os bilhetes entre os arquétipos estruturais do espaço Z (`assign_clusters_batch`), mantendo a divergência $D_{\text{JS}} < 0.05$ e alta entropia de arquétipos (`entropia_arquetipos`, `arquetipos_unicos` em `portfolio_diagnostics`).
* **Seleção Marginal de Conjunto (`_select_tail_controlled_portfolio`)**: Usada por `cauda_controlada`. Em cada passo, escolhe o bilhete que maximiza a **utilidade marginal do pacote**, combinando `score_z`, ganho marginal de calibração, ganho de diversidade de arquétipo e tetos absolutos (*hard caps*) de exposição por dezena e repetição de pares.
* **Separação de Regime (Faixas Fixas vs. Rateadas) e Busca Local Preservadora de Buckets (`_refine_coverage_preserving_buckets`)**: Em modalidades densas com forte peso de faixas fixas (Lotofácil, onde $11$, $12$ e $13$ pontos representam $\sim 60\%$ do retorno esperado e independem de quantos outros apostadores acertaram), o teto de exposição individual é mais estrito ($1{,}25\times$ a exposição uniforme esperada) e a busca local 1-opt pós-seleção minimiza a norma de Frobenius da matriz de sobreposição e a variância de exposição das dezenas (`w_exp = 0.45`, `w_ov = 0.55`) realizando trocas **estritamente dentro do mesmo bucket de Hamilton** e respeitando o teto de exposição máxima (`max_exposure_cap`), reduzindo a variância do retorno sem degradar $D_{\text{JS}}$ nem violar o corte de popularidade.
* **Padrão por densidade** (`estrategia_padrao`): `cauda_controlada` em jogos esparsos (Mega-Sena, Quina) e `balanceada` em jogos densos (Lotofácil, Lotomania). `pura` é o controle sem sinais históricos.

### 7.3 Motor 1: Geração Vetorial com Truque Gumbel-Max (`generator_fast.py`)
O motor `gerar_jogos_vetorizado` realiza amostragem ponderada sem reposição em alta velocidade:
1. Alinha explicitamente a tabela estatística ao índice $1 \dots N$ (`reindex(range(1, N + 1))`) e, se habilitados (`usar_quentes`, `usar_atrasados`, `usar_markov`, `usar_ciclo`, `usar_coocorrencia`; **todos desligados por padrão**), combina $Z_{\text{Freq}}$, $Z_{\text{Gap}}$, probabilidades de transição de Markov do último sorteio ($+0.15$) e bônus de gravidade do Ciclo das Dezenas ($+0.80$ para densos, $+0.25$ para esparsos). Com tudo desligado, a amostragem de candidatos é uniforme e a escolha fica por conta dos filtros estruturais, da popularidade e da diversidade do pacote.
2. Aplica **Softmax com Temperatura** ($\tau \in [1.15, 2.0]$ conforme a estratégia):
   \(p_i = \frac{\exp(s_i / \tau)}{\sum_{j=1}^{N} \exp(s_j / \tau)}\)
3. **Truque Gumbel-Max**: Para gerar dezenas de milhares de jogos sem reposição sem usar loops lentos em Python, soma ruído Gumbel padrão $G_{b,i} = -\ln(-\ln(U_{b,i}))$ aos log-probabilidades:
   \(W_{b,i} = \ln(p_i + 10^{-10}) - \ln(-\ln(U_{b,i} + 10^{-10}))\)
   Selecionar os $k$ maiores valores de $W_{b,i}$ por linha via `np.argpartition` produz matematicamente uma amostra exata sem reposição da distribuição multinomial ponderada.

### 7.4 Motor 2: Minerador Genético Evolutivo (`generator_genetic.py`)
A classe `GeneticMiner` implementa um algoritmo evolucionário sobre conjuntos com gerador pseudoaleatório isolado (`self.rng = np.random.default_rng(seed)`), sem poluir a semente global do processo:

* **População e Restrições**: $300$ indivíduos evoluídos por $30$ (jogos pequenos) a $60$ gerações (Mega-Sena/Quina/Lotomania), respeitando estritamente `numeros_fixos`, `numeros_evitados`, o limite de sobreposição ajustado pelo número de fixos (`limite_comum = max(0, overlap_total - n_fixos)`) e a guarda anti-histórico (`score > -1e8`) inclusive no fallback aleatório.
* **Fitness**: Avaliado diretamente por `score_plausibility_batch`.
* **Elitismo e Crossover de Conjunto (`_crossover_set`)**: Preserva os top $10\%$ como elite. O cruzamento une os genes dos pais ($P_1 \cup P_2$) e amostra $k$ dezenas únicas dessa união.
* **Mutação**: Taxa de $20\%$ (preservando o top $3$ intacto), trocando $1$ ou $2$ genes por dezenas livres do universo permitido.

### 7.5 Modo Jogo Real — Torneio Fechado de Pacotes (`real_game_mode.py`)
Projetado para o momento da aposta real, evitando que o usuário rode o gerador várias vezes até escolher um resultado por viés visual:
1. **Seed Determinística Auditável (`_default_seed`)**: Gera uma *seed* SHA-256 única combinando a data do dia, o slug do jogo, a quantidade de bilhetes, o perfil de esforço (`rapido`, `forte` ou `maximo`), o tamanho do histórico e as dezenas do último sorteio.
2. **Torneio de Pacotes (`_package_score`) e Refinamento 1-opt (`_refine_package_1opt`)**: Gera um pool de candidatos, monta até $800$ pacotes concorrentes (no perfil `maximo`) e aplica busca local 1-opt sobre o pacote vencedor avaliando a função de utilidade global (com peso de dispersão de exposição $w_{\sigma} = 0{,}40$ em jogos densos e $0{,}15$ em jogos esparsos):
   \(\text{Score}_{\text{pacote}} = \bar{S} + 0.12 \cdot S_{\max} + 1.40 \cdot \text{NãoRed}_{\text{pares}} + 0.90 \cdot \text{NãoRed}_{\text{trincas}} + 1.20 \cdot \text{Cob}_{\text{univ}} + 0.25 \cdot \hat{H}_{\text{arq}} - w_{\sigma} \cdot \sigma_{\text{exp}} - 1.20 \cdot \text{Exc}_{\text{exp}} - 1.50 \cdot \text{Exc}_{\text{overlap}} - 0.90 \cdot \text{Exc}_{\text{pares}} - 2.50 \cdot D_{\text{JS}}\)
3. **Comparação contra Monte Carlo e Diagnósticos Pós-Seleção Neutros**: Gera até $5.000$ pacotes puramente aleatórios sob as mesmas restrições e informa o percentil exato e o $p$-valor empírico do pacote campeão, além de emitir três relatórios puramente pós-seleção (que não entram no `_package_score` para evitar *overfitting*):
   * `diagnostico_cobertura_historica`: confronta o pacote selecionado contra todos os concursos históricos em `ctx.draws_bin` e compara os acertos por faixa com a expectativa hipergeométrica exata sob $H_0$.
   * `diagnostico_antidivisao`: reporta a razão média/mínima/máxima de co-ganhadores (`razao_ganhadores_media`), a conformidade com o limiar de corte e o multiplicador esperado de retenção de prêmio (`multiplicador_retencao_premio_medio`).
   * `diagnostico_ev_ex_ante`: calcula o retorno esperado líquido ex-ante por R\$ $1{,}00$ apostado para um bilhete aleatório (`ev_por_real_aleatorio`) e para o pacote anti-popular selecionado (`ev_por_real_ajustado`), com **intervalo split-conformal $90\%$** (`ev_por_real_ic90_low`–`ev_por_real_ic90_high`), detecção de **concurso especial** (`concurso_especial_detectado`) e recomendação operacional (`PULAR_CONCURSO`, `APOSTAR_SELETIVO_TOP20`, `APOSTAR_ACUMULADO_TOP10` ou `APOSTAR_EV_POSITIVO`).

### 7.6 Desenhos de Cobertura Verificados — Fechamentos (`matrices.py`)
Quando o apostador seleciona $v > k_{\text{bet}}$ dezenas base, o sistema aplica **desenhos de cobertura combinatórios $L(v, k, t, m)$** (construídos por `construir_covering_design` via bitmasks com busca gulosa + poda de redundâncias e auditados exaustivamente sobre todos os $\binom{v}{m}$ cenários por `verificar_garantia_fechamento`):

* **Lotofácil (`MatrixCatalog` + `opcoes_fechamento_para_jogo`)**:
  * $16$ dezenas $\to 1$ jogo ($14\text{-se-}15$ ótimo, pois qualquer subconjunto de $15$ dezenas em $16$ tem ao menos $14$ em comum) ou $16$ jogos (desdobramento completo $15\text{-se-}15$).
  * $17$ dezenas $\to 8$ jogos ($14\text{-se-}15$ verificado $100\%$).
  * $18$ dezenas $\to 24$ jogos ($14\text{-se-}15$ verificado $100\%$).
  * $19$–$20$ dezenas $\to$ matrizes verificadas $13\text{-se-}15$.
* **Mega-Sena e Quina (Fechamentos Reais Verificados)**:
  * **Mega-Sena**: $7\text{..}10$ dezenas com garantias verificadas `Quina-se-6` ($t=5, m=6$), `Quadra-se-6` ($t=4, m=6$) e `Quadra-se-4` ($t=4, m=4$).
  * **Quina**: $6\text{..}10$ dezenas com garantias verificadas `Quadra-se-5` ($t=4, m=5$), `Terno-se-5` ($t=3, m=5$) e `Terno-se-3` ($t=3, m=3$).
* **Seleção de Base Anti-Popular (`sugerir_base_antipopular`)**: Sugere $v$ dezenas base que minimizam o risco empírico de divisão de prêmio segundo `ctx.modelo_popularidade` (substituindo a heurística anterior de frequência/atraso).
* **Fechamento Dinâmico e Transparência na Lotomania (`_gerar_fechamento_dinamico`, `gerar_fechamento_detalhado`)**: Para conjuntos sem matriz exata (como Lotomania $v > 50$, onde $\binom{v}{50}$ é astronômico), o algoritmo gera pacotes gulosos balanceados reportando explicitamente que se trata de cobertura aproximada por pares (sem falsa garantia matemática).

---

## 8. Sistema de Validação e Detecção de Padrões

**Arquivos**: `validator.py` e `patterns.py`

A função `validar_jogo` (alimentada em `LotteryService.validate` com todos os $15$ sinais cacheados do `GameContext`, incluindo `bootstrap_ic`, `taxa_regressao`, `atrasos`, `pares_repelentes`, `pares_populares`, `draws_bin` e `clusters_historicos`) parte de um score inicial de $100$ pontos e executa uma bateria de **13 etapas de auditoria**:

1. **Verificação de Histórico O(1)**: Consulta se a tupla ordenada já saiu no passado (`ja_saiu = True` zera o score imediatamente).
2. **Análise Técnica Básica (`_analise_tecnica`)**:
   * Soma dentro do $\text{IC}_{80\%}$ ($0$ pen), no $\text{IC}_{95\%}$ ($-10$ pts) ou fora do $\text{IC}_{95\%}$ ($-25$ pts), utilizando o desvio-padrão hipergeométrico exato no fallback.
   * Equilíbrio Par/Ímpar na faixa proporcional $[\lfloor 0.35 \cdot k_{\text{bet}} \rfloor, \lceil 0.65 \cdot k_{\text{bet}} \rceil]$ ($-10$ a $-25$ pts se extremo).
   * Concentração vertical de linhas vazias ($-5$ pts) e equilíbrio entre metade superior e inferior ($-10$ a $-20$ pts).
   * Repetição excessiva de dígitos finais ($-5$ a $-15$ pts).
3. **Entropia de Shannon dos Gaps (`_analise_entropia`)**:
   \(H(\text{gaps}) = -\sum_{g} p(g) \log_2 p(g)\)
   Penaliza padrões regulares com baixa entropia ($-25$ pts e risco de divisão `ALTO`, com limiar inferior ajustado por `ajustar_threshold_inferior_por_densidade`) e concede bônus ($+5$ pts) para alta entropia. Na interface, a entropia é exibida de forma relativa ao máximo teórico $\log_2(k_{\text{bet}} - 1)$ de cada modalidade.
4. **Heurísticas de Popularidade Humana (`_analise_popularidade` e `_analise_numeros_sortudos`)**: Detecta excesso de datas ($\le 31$), presença da combinação cultural *Lost* ($\{4, 8, 15, 16, 23, 42\}$), excesso de sequências consecutivas e números culturalmente "sortudos", rotulando explicitamente esses alertas como heurísticas comportamentais/culturais em `metricas["popularidade_heuristica"]` para diferenciá-los da popularidade medida empiricamente nos rateios (`popularidade_medida_*`).
5. **Distribuição Espacial pelo Coeficiente de Gini (`_calcular_coeficiente_gini`)**:
   \(G = \frac{2 \sum_{i=1}^{k} i \cdot y_{(i)}}{k \sum_{i=1}^{k} y_{(i)}} - \frac{k + 1}{k}, \quad y_i = \frac{x_i - 1}{N - 1}\)
   Premia $G < 0.15$ ($+5$ pts) e penaliza alta concentração espacial $G > 0.50$ ($-10$ pts).
6. **Geometria Empírica com Correção de Bonferroni (`_analise_geometrica`)**: Avalia Moldura, Miolo, Cruz, Xis, Cantos, Colunas, Xadrez e Metades contra a distribuição histórica real, projetando média e desvio-padrão com o fator hipergeométrico exato $\sqrt{(k_{\text{bet}}/k)\cdot(N - k_{\text{bet}})/(N - k)}$ quando $k_{\text{bet}} \ne k$.
7. **Propriedades Matemáticas (`_analise_primos`, `_analise_multiplos`, `_analise_quase_reta`)**: Audita quantidade de números primos (com expectativa hipergeométrica exata $k_{\text{bet}} \cdot M / N$ e tolerância mínima de $2\sigma_{\text{hiper}}$), concentração de múltiplos de $d \in \{2, 3, 5, 10\}$ e formação de linhas ou colunas anômalas calibradas por cauda hipergeométrica ($p \cdot n_{\text{grupos}} < 0{,}015$).
8. **Similaridade de Hamming, Quadrantes e Regressão (`_analises_avancadas`)**: Calcula a menor distância de Hamming $d_H(A, B) = |A \triangle B|$ contra todo o histórico e os últimos $100$ sorteios (`penalizar_por_similaridade`: $-25$ pts em jogos esparsos / $-12$ pts em densos se $d_H = 1$ nos últimos $100$; $-8$ pts / $-5$ pts se $d_H = 1$ em concurso antigo; $-8$ pts / $-3$ pts em jogos esparsos se $d_H = 2$ nos últimos $100$), avalia os $4$ quadrantes (com escala hipergeométrica exata para $k_{\text{bet}} \ne k$) e registra a regressão à média de forma estritamente informativa (sem bônus de score).
9. **Co-ocorrência Rara e Pares Populares**: Alerta sobre pares que nunca saíram juntos ou pares excessivamente batidos.
10. **Ordem de Saída e Popularidade Medida**: Integra os percentis de `ordem_saida.py` e `popularidade_medida.py` (incluindo o intervalo conformal $90\%$ `popularidade_medida_ic90`).
11. **Análise Estrutural, Motifs, Simetria de Reflexão e Padrões Avançados (`patterns.py`)**:
    * **Simetria de Reflexão (`calcular_simetria_reflexao`)**: Conta quantos pares espelhados $(n, N + 1 - n)$ existem no bilhete, com limiar calibrado ao esperado hipergeométrico do jogo.
    * **Progressão Aritmética Geral (`detectar_progressao_aritmetica_geral`)**: Detecta **sempre** PAs completas de qualquer razão em todas as modalidades (inclusive `[1..15]` na Lotofácil e `[1..50]` na Lotomania), múltiplos via $\text{MDC}(x_1, \dots, x_k) > 1$ e PAs parciais ($\ge 70\%$ de gaps idênticos, ajustado para $\ge 85\%$ em jogos densos com passo $1$–$2$).
    * **Sequências Longas, Diagonais e Bordas Extremas**: Penaliza sequências consecutivas longas, diagonais/Xis e bordas extremas com limiares calibrados pela cauda hipergeométrica exata ($p < 0{,}015$).
12. **Raridade Conjunta (`_aplicar_raridade_conjunta`)**: Se $2$ ou $3+$ alertas estruturais graves ocorrerem simultaneamente no mesmo bilhete (usando limiares hipergeométricos para simetria e `ajustar_threshold_inferior_por_densidade` para `cv_gaps`, `span_relativo` e `entropia`), aplica penalidade composta adicional de $-8$ a $-15$ pontos.
13. **Índice de Compressibilidade (`calcular_indice_compressibilidade`)**: Sintetiza todas as flags estruturais (calibradas por modalidade/densidade) em um índice de $0$ a $100$ (`Excelente`, `Bom`, `Regular`, `Compressível`, `Ultra-compressível`).

---

## 9. Backtest Walk-Forward, Modelo Financeiro e Matriz de Estratégias

**Arquivos**: `backtest.py`, `prize_model.py`, `strategy_matrix.py`, `auditoria_registro.py`

### 9.1 Validação Temporal Walk-Forward (`executar_backtest_temporal` em `backtest.py`)
Para testar se uma estratégia realmente agrega valor sem *data leakage* (olhar o futuro):
1. Define múltiplos pontos de corte cronológicos $c_1, c_2, \dots, c_W$ espaçados por `step` sorteios, com semente determinística por janela (`seed_janela`) propagada a ambos os motores para reprodutibilidade exata.
2. Em cada janela $w$:
   * Constrói o contexto `ctx_janela` **exclusivamente** com o passado `df_completo.iloc[:corte]`.
   * Gera $Q$ jogos com o motor **Genético** e $Q$ jogos com o motor **Vetorial** (com `usar_coocorrencia=False` por padrão também nos scripts CLI).
   * Confronta os pacotes gerados com os próximos `tamanho_teste` sorteios reais (`df_futuro`), mapeando corretamente os $0$ acertos da Lotomania na faixa de prêmio máximo (`hit_6`).
   * Executa $M$ simulações de **Monte Carlo** (ex.: $500$ pacotes aleatórios) enfrentando exatamente o mesmo `df_futuro`.
3. **Métricas Estatísticas Rigorosas**:
   * **Delta contra o Acaso**: $\Delta_w = \text{Score}_{\text{motor}, w} - \overline{\text{Score}}_{\text{MC}, w}$.
   * **$p$-valor Empírico Unilateral**: \(\displaystyle p_{\text{emp}, w} = \frac{\sum_{m=1}^{M} \mathbb{I}(\text{Score}_{\text{MC}, m} \ge \text{Score}_{\text{motor}, w}) + 1}{M + 1}\).
   * **Intervalo de Confiança Bootstrap $95\%$**: Reamostra os deltas das janelas ($B = 2.000$) para verificar se o ganho médio sustenta-se acima de zero.

### 9.2 Diagnóstico Financeiro Vetorizado, Regime de Especiais, Conformal EV e Kelly (`prize_model.py`)
1. **Confronto Financeiro Vetorizado (`financial_diagnostics`)**: Calcula o cruzamento exato de acertos entre os $m$ bilhetes do pacote e os $T$ sorteios de teste via multiplicação matricial binária $B_{\text{jogos}} B_{\text{sorteios}}^\top \in \mathbb{Z}^{m \times T}$, computando Custo Total ($C$), Receita Bruta ($R$), Lucro Líquido ($L = R - C$), ROI ($L / C$) e Fator de Retorno ($R / C$) com a tabela oficial vigente de prêmios fixos da Lotofácil ($11 \mapsto \text{R\$ } 7{,}00$, $12 \mapsto \text{R\$ } 14{,}00$, $13 \mapsto \text{R\$ } 35{,}00$) e sobrescritas via CLI.
2. **Gatekeeper Causal de Valor Esperado Ex-Ante (`estimar_ev_concurso_ex_ante`)**: A partir do último concurso fechado em `data/detalhes/<loteria>_detalhes.csv` (com filtro causal contra anomalias de arrecadação):
   \[\text{EV}(r) = \frac{1}{\text{Preço}\cdot(1 + \tau_{\text{bolão}})} \left[\sum_{f \in \text{Fixas}} p_f V_f + \sum_{f \in \text{Rateadas}} p_f \, \widehat{\text{Pool}}_{f,t} \, \frac{1 - e^{-\hat{\Lambda}_{f,t}\cdot r}}{\hat{\Lambda}_{f,t}\cdot r}\right]\]
   * **Detector Ex-Ante de Concursos Especiais (`_detectar_concurso_especial_ex_ante`)**: Identifica Mega da Virada, Quina de São João e Lotofácil da Independência usando apenas campos conhecidos *antes* do sorteio (`valorAcumuladoProximoConcurso ≈ valorAcumuladoConcursoEspecial`, salto $\ge 1{,}45\times$ da estimativa oficial sobre o acumulado e $\ge 2{,}5\times$ a mediana de arrecadação) e aplica o multiplicador causal dos últimos $4$ concursos especiais (`razao_est_arr_especial`), eliminando falsos alertas de `APOSTAR_EV_POSITIVO` em sorteios especiais.
   * **Intervalos Split-Conformal $90\%$**: Propaga o quantil conformal $q_{90}$ dos erros passados de previsão de arrecadação e do modelo de popularidade (`conformal_q90_log_pop`) para emitir `ev_por_real_ic90_low`, `ev_por_real_ic90_high` e `ev_positivo_conformal`.
   * **Kelly Fracionado (`calcular_kelly_fracionado`)**: Calcula o tamanho conservador da aposta ($25\%$ do Kelly ajustado à variância da faixa 1, limitado a $5\%$ da banca), retornando **zero** sempre que $\text{EV} \le 1{,}00$.
   * **Comparador Cruzado entre Modalidades (`comparar_ev_modalidades`)**: Ranqueia simultaneamente Mega-Sena, Quina, Lotofácil e Lotomania considerando ágio do bolão e banca (acessível via `python -m app.cli.game_day --comparar-modalidades`).

### 9.3 Bancada Científica Multi-Seed (`strategy_matrix.py`)
O módulo `strategy_matrix.py` cruza todas as estratégias (`balanceada`, `cauda_controlada`, `pura`) contra múltiplas *seeds* padrão (`[7, 21, 42, 77, 101]`) e contra ambos os motores (`Vetorial` e `Genetico`):

* Calcula estatísticas agregadas (média, mediana, desvio padrão populacional, mínimo e máximo) para todas as métricas de acerto, portfólio, calibração e ROI.
* Aplica o `_score_composto` diagnóstico adaptado à densidade da modalidade (respeitando limites próprios de overlap/exposição para jogos densos vs. esparsos) que recompensa acertos reais (`hit_4`, `hit_5`, `hit_6`), delta positivo contra Monte Carlo e ROI, enquanto penaliza instabilidade entre seeds, superexposição, overlap excessivo, trincas/quadras repetidas em jogos esparsos e divergência $D_{\text{JS}}$.
* **Sistema Automático de Alertas (`_gerar_alertas_agregado`)**: Emite alertas classificados por severidade (`baixa`, `media`, `alta`) para `ic_cruza_zero`, `dependencia_seed`, `concentracao_excessiva`, `overlap_excessivo`, `trincas_repetidas`, `quadras_repetidas` e `calibracao_artificial`.

### 9.4 Auditoria Diária Prospectiva, Rateio Realizado e E-Values Anytime-Valid (`game_day.py`, `conferir.py`, `auditoria_registro.py`)
Os *workflows* automatizados (`game-day.yml` e `conferir.yml`) operam um experimento prospectivo contínuo na branch `registro`:
1. **Geração Pré-Sorteio (`app/cli/game_day.py`)**: Nos dias de sorteio de cada modalidade, gera o pacote real com semente determinística, audita os cartões via `validar_jogo`, calcula o EV ex-ante com limites conformais $90\%$, detecção de concurso especial, monitor de drift de popularidade e razão esperada de co-ganhadores (`razao_ganhadores`), gravando `package.json` e `report.md` antes do sorteio.
2. **Conferência com Rao-Blackwell e Rastreamento de Rateio (`app/cli/conferir.py`)**: Quando o resultado oficial entra na planilha (normalizando `00 → 100` na Lotomania):
   * Verifica que o pacote foi gerado estritamente antes do concurso (`ultimo_concurso_conhecido < concurso`).
   * Calcula a **variância hipergeométrica exata da média de acertos condicional à exposição $E$** (`variancia_media_acertos_exata`) e o **controle aleatório pareado Rao-Blackwellizado** (`avaliar_controle_pareado_condicional`).
   * Cruza automaticamente os acertos com `data/detalhes/*_detalhes.csv` para gravar `resultado.json["auditoria_rateio"]` (prêmio bruto realizado da Caixa, custo do pacote, retorno líquido, razão observada de ganhadores no sorteio e fator esperado de retenção), preservando o esquema original de `historico.csv`.
3. **Auditoria Sequencial Anytime-Valid e Poder Amostral (`auditoria_registro.py` / `conferir.py --auditar`)**:
   * **E-Values / Martingale de Teste Exato (`calcular_e_valor_sequencial`)**: Usa mistura de martingales de apostas limitados sobre incrementos padronizados de acertos e de taxa de premiação pareada, produzindo $p_{\text{anytime}} = \min(1, 1/\max_{t} M_t)$ válido em **qualquer regra de parada** pela desigualdade de Ville (sem viés de *optional stopping* ao auditar o registro diariamente).
   * **Calculadora de Poder Estatístico (`calcular_tamanho_amostra_auditoria`)**: Informa exatamente quantos eventos rateados e quantos pacotes conferidos são necessários para atingir $80\%$ de poder ($\alpha = 0{,}05$) na detecção de $+10\%$ ou $+20\%$ de retenção de prêmio.
   * **Detecção de Censura Amostral**: Alerta automaticamente caso existam pacotes `reprovados` sem conferência no diretório auditado.

---

## 10. Guia Prático de Operação para Apostas Reais

Para utilizar toda essa infraestrutura com disciplina científica, siga o protocolo abaixo para cada tipo de jogo:

### 10.1 Critério Prévio: Decisão de Quando e Onde Jogar
1. Execute `python -m app.cli.game_day --comparar-modalidades --agio 0.0` (informando `--agio` caso participe de bolão com tarifa de lotérica).
2. Priorize concursos sinalizados como `APOSTAR_ACUMULADO_TOP10`, `APOSTAR_SELETIVO_TOP20` ou `APOSTAR_EV_POSITIVO` (verificando o IC conformal $90\%$ e se o ágio do bolão não anulou o ganho anti-popular).

### 10.2 Receita para Mega-Sena e Quina (Jogos Esparsos)
1. **Abordagem A — Pacote Diversificado (`real_game_mode.py`)**: Use `estrategia_base="cauda_controlada"` com `perfil_esforco="forte"` ou `"maximo"`. Verifique `max_repeticao_par <= 3`, `overlap_max <= get_overlap_limit()`, `ja_saiu: False` e `risco_divisao: "Baixo"`.
2. **Abordagem B — Fechamento Verificado (`matrices.py`)**: Escolha $7\text{..}10$ dezenas com `sugerir_base_antipopular(config, n, ctx.modelo_popularidade)` e aplique `gerar_fechamento_detalhado(..., garantia_t, condicao_m)` para garantias exaustivamente verificadas de Quadra/Quina (Mega-Sena) ou Terno/Quadra (Quina).

### 10.3 Receita para Lotofácil e Lotomania (Jogos Densos)
1. **Abordagem A — Pacote Diversificado (`real_game_mode.py`)**: Use `estrategia_base="balanceada"` (que aplica busca local 1-opt preservadora de buckets para maximizar cobertura uniforme nas faixas fixas e proteção-espelho de $0$ acerto na Lotomania).
2. **Abordagem B — Fechamento Verificado na Lotofácil (`matrices.py`)**: Use `sugerir_base_antipopular(config, n, ctx.modelo_popularidade)` para selecionar $16$ ($1$ jogo $14\text{-se-}15$), $17$ ($8$ jogos $14\text{-se-}15$), $18$ ($24$ jogos $14\text{-se-}15$) ou $19\text{--}20$ dezenas ($13\text{-se-}15$) e valide os cartões gerados em `validator.py`. Na Lotomania ($50$ dezenas por bilhete), prefira o Modo Jogo Real em vez de fechamentos parciais sem garantia matemática.
