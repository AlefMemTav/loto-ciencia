import streamlit as st
import pandas as pd
import numpy as np
import random
from scipy.stats import poisson
import matplotlib.pyplot as plt
from itertools import combinations

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="LotoScience Virada", page_icon="🎱", layout="wide")

# CSS Customizado
st.markdown(
    """
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .success-box { padding:15px; background-color:#d4edda; color:#155724; border-radius:10px; }
    .warning-box { padding:15px; background-color:#fff3cd; color:#856404; border-radius:10px; }
    .error-box { padding:15px; background-color:#f8d7da; color:#721c24; border-radius:10px; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 1. MOTOR DE DADOS E ESTATÍSTICA ---


@st.cache_data
def carregar_dados_reais():
    try:
        # Carrega o Excel
        df = pd.read_excel("data/mega_sena_asloterias_ate_concurso_2954_sorteio.xlsx")

        # Ajuste conforme as colunas do seu Excel
        df_limpo = df.iloc[:, 2:8].copy()
        df_limpo.columns = ["D1", "D2", "D3", "D4", "D5", "D6"]

        for col in df_limpo.columns:
            df_limpo[col] = pd.to_numeric(df_limpo[col], errors="coerce")

        df_limpo = df_limpo.dropna()
        return df_limpo

    except FileNotFoundError:
        st.error("Erro: Arquivo Excel não encontrado na pasta data/.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return pd.DataFrame()


@st.cache_data
def get_numeros_quentes_frios(df):
    if df.empty:
        return pd.Series()
    todos_numeros = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    freq = pd.Series(todos_numeros).value_counts().sort_values(ascending=False)

    # Quentes: Top 15 mais frequentes nos últimos 50 jogos
    # Frios: 15 menos frequentes
    # Neutros: O resto
    return freq


@st.cache_data
def analise_poisson(df):
    if df.empty:
        return []
    # Analisa o dígito final (unidade) de todos os números
    todos_numeros = df[["D1", "D2", "D3", "D4", "D5", "D6"]].values.flatten()
    finais = [n % 10 for n in todos_numeros]
    contagem = pd.Series(finais).value_counts().sort_index()

    # Atraso teórico (simplificado para MVP)
    # Se um final saiu muito menos que 10% das vezes, ele é candidato Poisson
    total = len(finais)
    esperado = total * 0.10  # 10% para cada digito 0-9

    atrasados = []
    for digito in range(10):
        real = contagem.get(digito, 0)
        if real < esperado * 0.9:  # 10% abaixo do esperado
            atrasados.append(digito)

    return atrasados


# def verificar_quadrantes(numeros):
#    # Inicializa contadores para Q1, Q2, Q3, Q4
#    q_counts = [0, 0, 0, 0]
#
#    for n in numeros:
#        if n == 0: continue # Segurança
#
#        # Ajusta para índice 0-59 para facilitar a matemática
#        idx = n - 1
#
#        # Calcula linha (0-5) e coluna (0-9)
#        linha = idx // 10
#        coluna = idx % 10
#
#        # Lógica Geométrica:
#        # Linhas 0, 1, 2 são Superior. Linhas 3, 4, 5 são Inferior.
#        # Colunas 0, 1, 2, 3, 4 são Esquerda. Colunas 5, 6, 7, 8, 9 são Direita.
#
#        if linha < 3: # Parte Superior
#            if coluna < 5:
#                q_counts[0] += 1 # Q1 (Superior Esquerdo)
#            else:
#                q_counts[1] += 1 # Q2 (Superior Direito)
#        else: # Parte Inferior
#            if coluna < 5:
#                q_counts[2] += 1 # Q3 (Inferior Esquerdo)
#            else:
#                q_counts[3] += 1 # Q4 (Inferior Direito)
#
#    return q_counts


def verificar_quadrantes(numeros):
    q1 = [
        n
        for n in numeros
        if n in [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]
    ]
    q2 = [
        n
        for n in numeros
        if n in [6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30]
    ]
    q3 = [
        n
        for n in numeros
        if n in [31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55]
    ]
    q4 = [
        n
        for n in numeros
        if n in [36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60]
    ]
    return [len(q1), len(q2), len(q3), len(q4)]


# --- 2. O TERMÔMETRO (VALIDADOR) ---


def validar_jogo(numeros):
    report = {"score": 100, "msgs": [], "status": "Excelente"}

    # Regra 1: Soma (Gauss)
    soma = sum(numeros)
    if not (140 <= soma <= 240):
        report["score"] -= 25
        report["msgs"].append(
            f"❌ Soma ({soma}) fora da Curva de Gauss (Ideal: 140-240)."
        )
    else:
        report["msgs"].append(f"✅ Soma ({soma}) dentro da Zona de Ouro.")

    # Regra 2: Pares e Ímpares
    pares = len([n for n in numeros if n % 2 == 0])
    if pares == 6 or pares == 0:
        report["score"] -= 30
        report["msgs"].append("❌ Desequilíbrio Total de Par/Ímpar (6/0).")
    elif pares not in [2, 3, 4]:
        report["score"] -= 10
        report["msgs"].append(f"⚠️ Distribuição Par/Ímpar arriscada ({pares} pares).")
    else:
        report["msgs"].append(f"✅ Distribuição Par/Ímpar equilibrada ({pares} pares).")

    # Regra 3: Quadrantes
    quads = verificar_quadrantes(numeros)
    zeros = quads.count(0)
    if zeros >= 2:
        report["score"] -= 20
        report["msgs"].append("❌ Jogo concentrado. Dois ou mais quadrantes vazios.")
    else:
        report["msgs"].append("✅ Jogo bem distribuído no volante.")

    # Regra 4: Divisão de Prêmio (Anti-Popularidade)
    seqs = sum(1 for i in range(len(numeros) - 1) if numeros[i + 1] == numeros[i] + 1)
    datas = len([n for n in numeros if n <= 31])

    if seqs > 1:
        report["score"] -= 15
        report["msgs"].append("⚠️ Cuidado: Muitas sequências numéricas (Ex: 10,11).")
    if datas >= 5:
        report["score"] -= 10  # Não penaliza tanto a "vitória", mas avisa da divisão
        report["msgs"].append(
            "⚠️ ALERTA FINANCEIRO: Muitos números de data (1-31). Chance alta de dividir prêmio."
        )

    # Define Status Final
    if report["score"] >= 80:
        report["status"] = "💎 Excelente (Científico)"
    elif report["score"] >= 50:
        report["status"] = "⚠️ Razoável"
    else:
        report["status"] = "🗑️ Estatisticamente Fraco"

    return report


# --- 3. O GERADOR (IA ESTATÍSTICA) ---


def gerar_jogo_perfeito(freq_series, finais_poisson):
    # Separa os conjuntos
    top_quentes = freq_series.head(15).index.tolist()
    top_frios = freq_series.tail(15).index.tolist()
    # Neutros são os que não estão nem no top nem no bottom
    neutros = [n for n in range(1, 61) if n not in top_quentes and n not in top_frios]

    tentativas = 0
    while tentativas < 5000:
        tentativas += 1

        # Estratégia Híbrida: 3 Quentes + 2 Frios + 1 Neutro (ou variação)
        # Adiciona viés de Poisson (se houver finais atrasados, tenta incluir)

        try:
            jogo = []
            jogo += random.sample(top_quentes, 3)
            jogo += random.sample(top_frios, 2)
            jogo += random.sample(neutros, 1)

            # Força Poisson (opcional): Substitui o último por um número com final atrasado se necessário
            if finais_poisson and random.random() < 0.5:
                final_desejado = random.choice(finais_poisson)
                candidatos_final = [
                    n
                    for n in range(1, 61)
                    if n % 10 == final_desejado and n not in jogo
                ]
                if candidatos_final:
                    jogo.pop()
                    jogo.append(random.choice(candidatos_final))

            jogo = sorted(jogo)

            # Passa no Validador Rigoroso
            val = validar_jogo(jogo)
            if val["score"] >= 90:  # Só aceita jogos Nota A
                return jogo
        except ValueError:
            continue  # Caso falte números nas listas (edge case)

    return sorted(random.sample(range(1, 61), 6))  # Fallback se falhar


def gerar_fechamento(numeros_base):
    # Gera todas as combinações de 6 números baseadas na entrada
    # Ex: Se entrar 7 números, gera 7 jogos. Se entrar 8, gera 28 jogos.
    if len(numeros_base) < 6:
        return []
    comb = list(combinations(numeros_base, 6))
    return [sorted(list(c)) for c in comb]


# --- 4. VERIFICADOR DE HISTÓRICO ---
def verificar_historico(numeros, df):
    # Transforma os números do usuário em um conjunto (set) para comparação rápida
    meus_nums = set(numeros)
    ja_saiu_sena = []
    ja_saiu_quina = []
    ja_saiu_quadra = []

    # Itera sobre cada linha do histórico (Concursos reais)
    # iterrows é lento para big data, mas para 2600 linhas é instantâneo
    for index, row in df.iterrows():
        # Pega as bolas do sorteio atual
        sorteio = set(row[["D1", "D2", "D3", "D4", "D5", "D6"]].values)

        # Vê quantos números coincidem (Intersecção)
        acertos = len(meus_nums.intersection(sorteio))

        concurso_info = f"Conc. {row.name if row.name else index} ({row.iloc[1] if len(row) > 1 else 'Data N/A'})"  # Tenta pegar data se existir

        if acertos == 6:
            ja_saiu_sena.append(concurso_info)
        elif acertos == 5:
            ja_saiu_quina.append(concurso_info)
        elif acertos == 4:
            ja_saiu_quadra.append(concurso_info)

    return ja_saiu_sena, ja_saiu_quina, ja_saiu_quadra


# --- INTERFACE VISUAL ---
def main():
    df = carregar_dados_reais()

    if df.empty:
        st.warning("Aguardando dados... Verifique o arquivo Excel.")
        st.stop()  # Para a execução se não tiver dados

    freq = get_numeros_quentes_frios(df)
    poisson_finais = analise_poisson(df)

    st.title("🏆 MegaScience Pro: A Estratégia da Virada")
    st.write("Não é Sorte 🍀🙅‍♂️, é Ciência 🤓")
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Dashboard de Tendências",
            "🧪 Validador de Jogos",
            "🤖 Gerador Híbrido",
            "📦 Gerador de Fechamentos",
            "👥 Análise de Bolão",
        ]
    )

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Números Mais Quentes")
            st.caption("Frequência nos últimos jogos")
            st.bar_chart(freq.head(10))
        with col2:
            st.subheader("❄️ Números Mais Frios")
            st.caption("Estão atrasados (Teoria do Retorno)")
            st.bar_chart(freq.tail(10))

        st.info(
            f"🧬 **Análise de Poisson:** Os finais de dezena **{poisson_finais}** estão matematicamente atrasados."
        )

    with tab2:
        st.subheader("Teste sua intuição")
        entrada = st.text_input(
            "Digite seus 6 números (separados por vírgula, traços ou espaço):", ""
        )

        if st.button("Analisar Aposta"):
            try:
                texto_limpo = entrada.replace(",", " ").replace("-", " ")
                nums = sorted(
                    list(
                        set(
                            [int(n) for n in texto_limpo.split() if n.strip().isdigit()]
                        )
                    )
                )

                if len(nums) != 6:
                    st.error("Digite exatamente 6 números entre 1 e 60.")
                else:
                    relatorio = validar_jogo(nums)

                    # Exibe Score
                    st.metric(
                        "Score Estatístico",
                        f"{relatorio['score']}/100",
                        relatorio["status"],
                    )

                    # --- BACKTESTING ---
                    st.write("---")
                    st.subheader("📜 Raio-X Histórico")
                    senas, quinas, quadras = verificar_historico(nums, df)

                    col_hist1, col_hist2, col_hist3 = st.columns(3)
                    col_hist1.metric("Já deu Sena (6)?", f"{len(senas)} vezes")
                    if len(senas) > 0:
                        col_hist1.warning(f"Já saiu em: {senas[0]}")
                    col_hist2.metric("Já deu Quina (5)?", f"{len(quinas)} vezes")
                    col_hist3.metric("Já deu Quadra (4)?", f"{len(quadras)} vezes")

                    if len(senas) == 0:
                        st.caption(
                            "✅ **Inédito:** Essa combinação completa de 6 números nunca foi sorteada na história."
                        )
                    else:
                        st.error(
                            "⚠️ **Atenção:** Esses números exatos já saíram! Estatisticamente, repetir a mesma sena é raríssimo."
                        )

                    # Exibe Detalhes
                    if relatorio["score"] > 70:
                        st.markdown(
                            f'<div class="success-box">{"<br>".join(relatorio["msgs"])}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'<div class="error-box">{"<br>".join(relatorio["msgs"])}</div>',
                            unsafe_allow_html=True,
                        )

                    # Volante
                    st.write("---")
                    st.write("📍 **Visualização no Volante:**")
                    fig, ax = plt.subplots(figsize=(6, 3))
                    ax.set_xlim(0, 11)
                    ax.set_ylim(0, 7)

                    # Desenha o grid (6 linhas x 10 colunas)
                    for n in range(1, 61):
                        row = (n - 1) // 10
                        col = (n - 1) % 10
                        # Inverte row para 1 ficar em cima
                        y_pos = 6 - row - 0.5
                        x_pos = col + 0.5

                        color = "green" if n in nums else "lightgray"
                        weight = "bold" if n in nums else "normal"
                        size = 14 if n in nums else 10

                        ax.text(
                            x_pos,
                            y_pos,
                            str(n),
                            ha="center",
                            va="center",
                            color="white" if n in nums else "black",
                            bbox=dict(boxstyle="circle,pad=0.3", fc=color, ec="none"),
                        )
                    ax.axis("off")
                    st.pyplot(fig)
            except:
                st.error("Formato inválido.")

    with tab3:
        st.subheader("Gerador de Alta Performance")
        st.write(
            "Cria jogos combinando: **3 Quentes + 2 Frios + 1 Neutro** + Ajuste de Gauss + Poisson."
        )
        qtd_jogos = st.slider("Quantos jogos deseja gerar?", 1, 10, 3)

        if st.button("💎 Gerar Jogos Otimizados"):
            jogos_gerados = []
            progress = st.progress(0)
            for i in range(qtd_jogos):
                jogo = gerar_jogo_perfeito(freq, poisson_finais)
                jogos_gerados.append(jogo)
                progress.progress((i + 1) / qtd_jogos)

            st.success("Jogos Calculados com Sucesso!")
            texto_jogos = "LotoScience - Seus Jogos Otimizados\n\n"

            for i, jogo in enumerate(jogos_gerados):
                st.markdown(f"**Jogo {i+1}:** `{' - '.join(map(str, jogo))}`")
                val = validar_jogo(jogo)
                st.caption(f"Score: {val['score']} | {val['status']}")
                st.divider()
                texto_jogos += f"Jogo {i+1}: {jogo} \n"

            st.download_button(
                label="📥 Baixar Jogos (.txt)",
                data=texto_jogos,
                file_name="meus_jogos_lotoscience.txt",
                mime="text/plain",
            )

    with tab4:
        st.subheader("📦 Gerador de Fechamentos (Combinatória)")
        st.write(
            "Escolha de 7 a 12 números para cercar o prêmio. O sistema gera TODOS os jogos possíveis para garantir o prêmio matemático."
        )

        entrada_base = st.text_input(
            "Digite seus números base (Ex: 8 números):",
            placeholder="01 02 03 04 05 06 07 08",
        )

        if st.button("Gerar Fechamento"):
            try:
                base = sorted(
                    list(set([int(n) for n in entrada_base.replace(",", " ").split()]))
                )
                if len(base) < 7 or len(base) > 12:
                    st.warning("Escolha entre 7 e 12 números.")
                else:
                    jogos_fechamento = gerar_fechamento(base)
                    custo = len(jogos_fechamento) * 5.00
                    st.success(
                        f"Gerados {len(jogos_fechamento)} jogos. Custo real: R$ {custo:,.2f}"
                    )

                    # Mostra os jogos
                    txt_fech = ""
                    for j in jogos_fechamento:
                        st.text(str(j))
                        txt_fech += f"{j}\n"
                    st.download_button(
                        "📥 Baixar Fechamento Completo", txt_fech, "fechamento.txt"
                    )
            except:
                st.error("Erro nos números. Verifique a digitação.")
    with tab5:
        st.subheader("👥 Auditoria de Bolão")
        st.write(
            "Cole todos os jogos do seu bolão aqui. Vamos analisar a qualidade do grupo e se há erros (jogos repetidos ou mal distribuídos)."
        )

        # Área de texto grande para colar vários jogos
        texto_bolao = st.text_area(
            "Cole os jogos (um por linha):",
            placeholder="01 02 03 04 05 06\n10 12 14 16 18 20\n...",
        )

        if st.button("🔍 Auditar Bolão"):
            jogos_validos = []
            jogos_invalidos = []
            todos_numeros_jogados = []

            # 1. Processamento e Limpeza
            linhas = texto_bolao.strip().split("\n")

            for linha in linhas:
                if not linha.strip():
                    continue  # Pula linhas vazias

                # Limpeza inteligente (mesma lógica das outras abas)
                limpa = linha.replace(",", " ").replace("-", " ").replace(";", " ")
                try:
                    nums = sorted(
                        list(
                            set([int(n) for n in limpa.split() if n.strip().isdigit()])
                        )
                    )
                    if len(nums) == 6 and all(1 <= n <= 60 for n in nums):
                        jogos_validos.append(nums)
                        todos_numeros_jogados.extend(nums)
                    else:
                        jogos_invalidos.append(linha)
                except:
                    jogos_invalidos.append(linha)

            # Se não tiver jogos válidos, para
            if not jogos_validos:
                st.warning("Nenhum jogo válido identificado. Verifique a formatação.")
                st.stop()

            # 2. Estatísticas do Grupo
            qtd_jogos = len(jogos_validos)
            custo_total = qtd_jogos * 6.00

            # Verifica Duplicatas (Erro Clássico de Bolão)
            # Transforma em tupla para poder comparar
            jogos_tuple = [tuple(j) for j in jogos_validos]
            tem_duplicata = len(jogos_tuple) != len(set(jogos_tuple))

            # Cobertura (Quantos números únicos do volante estamos cobrindo?)
            numeros_unicos = len(set(todos_numeros_jogados))
            cobertura_perc = (numeros_unicos / 60) * 100

            # 3. Exibição dos Cards
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total de Jogos", qtd_jogos)
            k2.metric("Custo Total", f"R$ {custo_total:,.2f}")
            k3.metric(
                "Cobertura do Volante", f"{numeros_unicos}/60 ({cobertura_perc:.0f}%)"
            )

            if tem_duplicata:
                k4.metric("Duplicatas?", "SIM ⚠️", delta="Erro", delta_color="inverse")
                st.error(
                    "⚠️ **ATENÇÃO:** Existem jogos idênticos repetidos na lista! Você está pagando duas vezes pelo mesmo bilhete."
                )
            else:
                k4.metric("Duplicatas?", "Não", delta="Ok")

            st.divider()

            # 4. Análise de Qualidade Média
            scores = []
            for j in jogos_validos:
                scores.append(validar_jogo(j)["score"])

            media_score = sum(scores) / len(scores)

            col_graph1, col_graph2 = st.columns([2, 1])
            with col_graph1:
                st.markdown("##### 🔥 Mapa de Calor do Bolão")
                st.caption(
                    "Quais números seu grupo está jogando mais? (Mais escuro = Mais apostado)"
                )

                # Gráfico de Frequência no Bolão
                contagem_bolao = (
                    pd.Series(todos_numeros_jogados).value_counts().sort_index()
                )

                # Visualização do Volante (Heatmap)
                fig, ax = plt.subplots(figsize=(6, 3.5))
                for n in range(1, 61):
                    qtd_vezes = contagem_bolao.get(n, 0)
                    # Cor baseada na frequência (Branco se 0, Verde claro a Escuro se > 0)
                    if qtd_vezes == 0:
                        color = "#f0f0f0"  # Cinza claro
                        alpha = 1
                    else:
                        color = "green"
                        # Calcula opacidade baseada no máximo de vezes que um número saiu
                        max_freq = contagem_bolao.max()
                        alpha = 0.2 + (
                            0.8 * (qtd_vezes / max_freq)
                        )  # Mínimo 0.2, Máximo 1.0

                    circle = plt.Circle(
                        ((n - 1) % 10, 5 - ((n - 1) // 10)),
                        0.4,
                        color=color,
                        alpha=alpha,
                    )
                    ax.add_patch(circle)

                    # Texto (Número)
                    ax.text(
                        (n - 1) % 10,
                        5 - ((n - 1) // 10),
                        str(n),
                        ha="center",
                        va="center",
                        fontsize=6,
                    )

                    # Texto Pequeno (Qtd de vezes que foi jogado)
                    if qtd_vezes > 0:
                        ax.text(
                            (n - 1) % 10,
                            5 - ((n - 1) // 10) - 0.25,
                            f"x{qtd_vezes}",
                            ha="center",
                            va="center",
                            fontsize=4,
                            color="black",
                        )

                ax.set_xlim(-0.5, 9.5)
                ax.set_ylim(-0.5, 5.5)
                ax.axis("off")
                st.pyplot(fig)

            with col_graph2:
                st.markdown("##### 🌡️ Qualidade Técnica")
                st.metric("Score Médio do Grupo", f"{media_score:.0f}/100")
                if media_score < 60:
                    st.warning("Seu bolão tem muitos jogos 'ruins' estatisticamente.")
                else:
                    st.success("O bolão está bem equilibrado.")

                st.markdown("**Números Esquecidos:**")
                esquecidos = [
                    str(n) for n in range(1, 61) if n not in todos_numeros_jogados
                ]
                if len(esquecidos) > 0:
                    st.caption(f"Vocês não jogaram: {', '.join(esquecidos)}")
                else:
                    st.success("Parabéns! Vocês cercaram todos os 60 números.")

            # 5. Lista Detalhada com Análise Individual
            with st.expander("📋 Ver Lista Detalhada dos Jogos"):
                for i, jogo in enumerate(jogos_validos):
                    val = validar_jogo(jogo)
                    cor_icone = (
                        "🟢"
                        if val["score"] >= 80
                        else "🟡" if val["score"] >= 50 else "🔴"
                    )
                    st.write(
                        f"**Jogo {i+1}:** {jogo} {cor_icone} (Score: {val['score']})"
                    )

            if jogos_invalidos:
                st.error(
                    f"Ignoramos {len(jogos_invalidos)} linhas que não pareciam jogos válidos."
                )
            # 6. Lista Detalhada com Análise Individual
            st.write("---")
            st.subheader("📋 Detalhes Jogo a Jogo")
            st.caption(
                "Clique no jogo para ver a análise individual completa (Gauss, Quadrantes, Alertas)."
            )

            for i, jogo in enumerate(jogos_validos):
                # Roda o motor da Tab 2 para este jogo específico
                val = validar_jogo(jogo)

                # Define cor do ícone
                if val["score"] >= 80:
                    icone = "🟢"
                    label_score = "Excelente"
                elif val["score"] >= 50:
                    icone = "🟡"
                    label_score = "Razoável"
                else:
                    icone = "🔴"
                    label_score = "Fraco"

                # Cria um Expander para cada jogo
                # O título mostra o resumo, o conteúdo mostra os detalhes
                with st.expander(
                    f"{icone} Jogo {i+1}: {jogo} — Score: {val['score']} ({label_score})"
                ):

                    # Mostra todas as mensagens da Tab 2
                    for msg in val["msgs"]:
                        if "✅" in msg:
                            st.caption(
                                msg
                            )  # Usa caption para os acertos (menos visual)
                        elif "⚠️" in msg:
                            st.warning(msg)  # Amarelo para alertas
                        elif "❌" in msg:
                            st.error(msg)  # Vermelho para erros graves

                    # Mostra a análise de Gauss/Soma específica deste jogo
                    soma = sum(jogo)
                    st.text(
                        f"📊 Soma: {soma} | Pares: {len([n for n in jogo if n%2==0])}"
                    )


if __name__ == "__main__":
    main()
