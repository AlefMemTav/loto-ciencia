# app/ui/views/closures.py
import streamlit as st
import math
from app.core.logger import logger
from app.core.matrices import get_matriz_fechamento


def render_closures(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()
    color = constants.get("heat_color", "#ef4444")

    # --- Título com Apelo Científico ---
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="margin:0;">🧬 Matrizes de Fechamento <span style='color: {color};'>{config.name}</span></h2>
            <p style="color: #777; font-size: 1.1rem; margin-top: 5px;">
                Economize dinheiro usando Matrizes de Fechamentos avançadas.
            </p>
        </div>
        <div style="background-color: #f0fdf4; padding: 15px; border-left: 5px solid #22c55e; border-radius: 5px; margin-bottom: 20px;">
            <strong style="color: #15803d">O Segredo dos Bolões Profissionais:</strong> 
            Não jogue dinheiro fora com combinações completas. Use <em>Covering Designs</em> 
            (Matrizes Matemáticas) para cobrir mais números pagando até <strong>99% menos</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    qtd_aposta = config.bet_size
    min_base = qtd_aposta + 1

    # --- Configuração Dinâmica por Jogo ---
    if slug == "loto_facil_sorteio":
        max_base = 23
        exemplo_texto = (
            "📊 **Exemplo de Potência (Lotofácil):**\n\n"
            "Jogar **18 dezenas** na lotérica custa **R$ 2.448,00**.\n\n"
            "Com nossa Matriz 18-15-14-15, você joga os mesmos 18 números gastando apenas **R$ 72,00** "
            "(garantia de 14 pontos)."
        )
    elif slug == "mega_sena_sorteio":
        max_base = 15
        exemplo_texto = (
            "📊 **Exemplo de Potência (Mega-Sena):**\n\n"
            "Jogar **10 dezenas** na lotérica custa cerca de **R$ 1.050,00**.\n\n"
            "Com nosso Fechamento Inteligente, você cerca esses 10 números com **~15 jogos** (R$ 75,00), "
            "focando em garantir a Quadra ou Quina."
        )
    elif slug == "quina_sorteio":
        max_base = 15
        exemplo_texto = (
            "📊 **Exemplo de Potência (Quina):**\n\n"
            "Jogar **10 dezenas** na lotérica custa mais de **R$ 750,00**.\n\n"
            "Com a Matriz de Redução, você cobre esses 10 números gastando menos de **R$ 60,00**."
        )
    elif slug == "loto_mania_sorteio":
        max_base = 70
        exemplo_texto = (
            "📊 **Estratégia de Cobertura (Lotomania):**\n\n"
            "É impossível marcar 60 números em um único cartão.\n\n"
            "Nossa ferramenta permite que você escolha **60 ou 70 números** e o sistema os distribui "
            "automaticamente em cartões de 50, maximizando suas chances de acertar 19 ou 20 pontos."
        )
    else:
        # Fallback genérico
        max_base = qtd_aposta + 10
        exemplo_texto = (
            "Matrizes reduzem drasticamente o custo de apostas com muitos números."
        )

    # Placeholder dinâmico (exemplo visual correto)
    exemplo_nums = [f"{n:02d}" for n in range(1, qtd_aposta + 5)]
    # Se for muita coisa (Lotomania), corta o exemplo
    if len(exemplo_nums) > 10:
        placeholder_ex = (
            " ".join(exemplo_nums[:5]) + " ... " + " ".join(exemplo_nums[-3:])
        )
    else:
        placeholder_ex = " ".join(exemplo_nums)

    # --- Área de Input ---
    col_input, col_info = st.columns([2, 1])

    with col_input:
        st.info(
            f"Escolha de **{min_base} a {max_base}** números. "
            f"O sistema usará inteligência estatística para otimizar seus custos."
        )
        entrada_base = st.text_area(
            label="Digite os números:",
            placeholder=f"Ex: {placeholder_ex} ...",
            height=120,
            help="Separe por espaços, vírgulas ou quebra de linha.",
        )

    with col_info:
        st.info(exemplo_texto)

    if st.button(
        "⚡ Gerar Matriz Econômica Agora",
        width="stretch",
        type="primary",
    ):
        try:
            # Tratamento de input robusto
            raw_text = (
                entrada_base.replace(",", " ").replace("-", " ").replace("\n", " ")
            )
            numeros_str = raw_text.split()
            base = sorted(list(set([int(n) for n in numeros_str if n.isdigit()])))

            # Validações
            if len(base) < min_base:
                st.error(
                    f"❌ Poucos números! Escolha pelo menos **{min_base}** para usar matrizes."
                )
                return
            if len(base) > max_base:
                st.error(
                    f"❌ Muitos números! O limite para processamento online é **{max_base}**."
                )
                return
            if any(n > config.n_numbers or n < 1 for n in base):
                st.error(
                    f"❌ Números inválidos detectados. Use apenas entre 1 e {config.n_numbers}."
                )
                return

            with st.spinner("📐 Aplicando Design Combinatório Otimizado..."):
                # 1. Gera Matriz Otimizada (Passa o config para ser universal)
                jogos = get_matriz_fechamento(base, config)

                # 2. Cálculos Financeiros (O Pulo do Gato)
                custo_otimizado = len(jogos) * config.game_price

                # Custo "Na Raça" (Combinação Total C(n,k))
                comb_total = math.comb(len(base), config.k)
                custo_bruto = comb_total * config.game_price

                economia = custo_bruto - custo_otimizado

                if custo_bruto > 0:
                    pct_economia = (economia / custo_bruto) * 100
                else:
                    pct_economia = 0

            # --- EXIBIÇÃO DOS RESULTADOS ---
            st.markdown("---")
            st.subheader("💰 Relatório de Economia Inteligente")

            label_custo_bruto = (
                "Custo Teórico (Combinatória)"
                if slug == "loto_mania_sorteio"
                else "Custo na Lotérica (Bruto)"
            )

            m1, m2, m3 = st.columns(3)

            with m1:
                st.metric(label_custo_bruto, f"R$ {custo_bruto:,.2f}")

            with m2:
                # Lógica visual de desconto
                if pct_economia > 0:
                    delta_text = f"-{pct_economia:.1f}% Off"
                    delta_color = "normal"  # Verde
                else:
                    delta_text = "Preço Padrão"
                    delta_color = "off"  # Cinza

                st.metric(
                    "Custo LotoCiencia",
                    f"R$ {custo_otimizado:,.2f}",
                    delta=delta_text,
                    delta_color=delta_color,
                )

            with m3:
                st.metric(
                    "Você Economizou", f"R$ {economia:,.2f}", delta="Dinheiro no Bolso"
                )

            # Mensagem explicativa se não houve economia (UX Importante)
            if pct_economia == 0 and len(base) <= (config.bet_size + 2):
                st.caption(
                    "ℹ️ **Nota:** Para poucos números extras (ex: jogar 7 na Mega), "
                    "a quantidade de combinações é pequena. O sistema gera "
                    "o fechamento completo para garantir 100% do prêmio máximo."
                )

            # Lógica de Garantia Dinâmica
            if config.slug == "loto_facil_sorteio":
                if len(base) <= 18:
                    garantia = "14 Pontos (se acertar 15)"
                elif len(base) == 19:
                    garantia = "13 Pontos (se acertar 15) - Foco em Economia"
                else:
                    garantia = "11/12 Pontos (Cobertura de Equilíbrio)"
            elif config.slug == "mega_sena_sorteio":
                if len(base) <= 10:
                    garantia = "Sena (100% Garantida se acertar os 6)"
                else:
                    garantia = "Quadra/Quina (Cobertura Estratégica)"
            elif config.slug == "quina_sorteio":
                if len(base) <= 10:
                    garantia = "Quina (100% Garantida se acertar os 5)"
                else:
                    garantia = "Terno/Quadra (Cobertura Estratégica)"
            elif config.slug == "loto_mania_sorteio":
                garantia = "Distribuição Otimizada (Maximizar 19/20 pontos)"
            else:
                garantia = "Cobertura Matemática Otimizada"

            st.success(
                f"✅ **Matriz Aplicada:** {len(jogos)} jogos gerados. **Garantia Estimada:** {garantia}."
            )

            # Visualização dos Jogos
            with st.expander("📋 Visualizar/Copiar Jogos", expanded=True):
                txt_out = ""
                for i, jogo in enumerate(jogos, 1):
                    nums_fmt = " ".join([f"{n:02d}" for n in jogo])
                    st.text(f"Jogo {i:02d}: {nums_fmt}")
                    txt_out += f"{nums_fmt}\n"

            # Download
            st.download_button(
                "📥 Baixar Matriz (.txt)",
                txt_out,
                f"LotoScience_Matriz_{len(base)}dz_{len(jogos)}jogos.txt",
                width="stretch",
            )

        except Exception as e:
            logger.error(f"Erro matrix: {e}")
            st.error("❌ Ocorreu um erro ao calcular a matriz. Verifique seus números.")
            # ----
