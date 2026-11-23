# app/ui/views/closures.py
import math

import numpy as np
import streamlit as st

from app.core.logger import logger
from app.core.matrices import (
    gerar_fechamento_detalhado,
    opcoes_fechamento_para_jogo,
    sugerir_base_antipopular,
)


def _brl(valor: float) -> str:
    """Formata em reais no padrão brasileiro: R$ 2.856,00."""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_base_numbers(texto: str, slug: str) -> list[int]:
    """Lê dezenas separadas por espaço/vírgula/hífen/quebra, normalizando 00 -> 100 na Lotomania."""
    raw_text = (
        texto.replace(",", " ")
        .replace("-", " ")
        .replace(";", " ")
        .replace("\n", " ")
    )
    nums: set[int] = set()
    for token in raw_text.split():
        tk = token.strip()
        if not tk.isdigit():
            continue
        val = int(tk)
        if slug == "loto_mania_sorteio" and val == 0:
            val = 100
        nums.add(val)
    return sorted(nums)


def render_closures(ctx, svc):
    config = ctx.config
    slug = config.slug
    constants = config.as_constants_dict()
    color = constants.get("heat_color", "#ef4444")
    preco = float(config.game_price)

    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="margin:0;">🧬 Matrizes de Fechamento <span style='color: {color};'>{config.name}</span></h2>
            <p style="color: #777; font-size: 1.1rem; margin-top: 5px;">
                Covering Designs com garantia matemática verificada e base menos popular.
            </p>
        </div>
        <div style="background-color: #f0fdf4; padding: 15px; border-left: 5px solid #22c55e; border-radius: 5px; margin-bottom: 20px;">
            <strong style="color: #15803d">Nota Matemática Honesta:</strong>
            Fechamentos não alteram a média de acertos por real apostado, mas reorganizam a
            distribuição dos bilhetes para garantir um piso exato de acertos (<em>Covering Design</em>)
            pagando uma fração do desdobramento completo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    qtd_aposta = config.bet_size
    min_base = qtd_aposta + 1

    # --- Configuração Dinâmica por Jogo (usando preço oficial atual de config.game_price) ---
    if slug == "loto_facil_sorteio":
        max_base = 23
        qtd_sugestao_default = 18
        exemplo_texto = (
            "📊 **Exemplo Real (Lotofácil):**\n\n"
            f"Desdobrar **18 dezenas** completo custa **{_brl(math.comb(18, 15) * preco)}** (816 jogos).\n\n"
            f"Com a matriz de Turán **18-15-14-15 (24 jogos)**, você gasta **{_brl(24 * preco)}** "
            "(97,1% menos) com garantia verificada de >= 14 pontos se os 15 sorteados estiverem na base.\n\n"
            f"Para **19 ou 20 dezenas**, o fechamento **13-se-15** gera 15 ou 45 jogos verificados."
        )
    elif slug == "mega_sena_sorteio":
        max_base = 15
        qtd_sugestao_default = 10
        exemplo_texto = (
            "📊 **Exemplo Real (Mega-Sena):**\n\n"
            f"Desdobrar **10 dezenas** completo custa **{_brl(math.comb(10, 6) * preco)}** (210 jogos).\n\n"
            f"• **Quina se 6:** 15 jogos ({_brl(15 * preco)} · -92,9%)\n"
            f"• **Quadra se 4 (Covering Design):** 23 jogos ({_brl(23 * preco)} · -89,0%)\n"
            f"• **Quadra se 6:** 3 jogos ({_brl(3 * preco)} · -98,6%)"
        )
    elif slug == "quina_sorteio":
        max_base = 15
        qtd_sugestao_default = 10
        exemplo_texto = (
            "📊 **Exemplo Real (Quina):**\n\n"
            f"Desdobrar **10 dezenas** completo custa **{_brl(math.comb(10, 5) * preco)}** (252 jogos).\n\n"
            f"• **Quadra se 5:** 19 jogos ({_brl(19 * preco)} · -92,5%)\n"
            f"• **Terno se 3 (Covering Design):** 19 jogos ({_brl(19 * preco)} · -92,5%)\n"
            f"• **Terno se 5:** 2 jogos ({_brl(2 * preco)} · -99,2%)"
        )
    elif slug == "loto_mania_sorteio":
        max_base = 70
        qtd_sugestao_default = 60
        exemplo_texto = (
            "📊 **Cobertura Balanceada (Lotomania):**\n\n"
            "Escolha **51 a 70 dezenas** (aceita `00` ou `100`) e o sistema distribui em cartões "
            "de 50 maximizando pares inéditos e equilibrando a exposição entre todas as dezenas da base."
        )
    else:
        max_base = qtd_aposta + 10
        qtd_sugestao_default = min(max_base, min_base + 3)
        exemplo_texto = "Matrizes reduzem drasticamente o custo de apostas com muitos números."

    # Estado da caixa de texto por jogo (para suportar botão de sugestão anti-popular)
    input_key = f"closures_base_input_{slug}"
    if input_key not in st.session_state:
        st.session_state[input_key] = ""

    exemplo_nums = [f"{n:02d}" for n in range(1, min(qtd_aposta + 5, config.n_numbers + 1))]
    if len(exemplo_nums) > 10:
        placeholder_ex = " ".join(exemplo_nums[:5]) + " ... " + " ".join(exemplo_nums[-3:])
    else:
        placeholder_ex = " ".join(exemplo_nums)

    # --- Sugestão de base menos popular (anti-rateio) ---
    col_sug_n, col_sug_btn = st.columns([1, 2])
    with col_sug_n:
        qtd_sug = st.number_input(
            "Qtd. dezenas para sugestão anti-rateio",
            min_value=min_base,
            max_value=max_base,
            value=min(max_base, max(min_base, qtd_sugestao_default)),
            step=1,
            key=f"closures_qtd_sug_{slug}",
        )
    with col_sug_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button(
            "🎯 Sugerir base menos popular (anti-rateio)",
            key=f"btn_sug_base_{slug}",
            width="stretch",
        ):
            sugestao = sugerir_base_antipopular(
                config,
                int(qtd_sug),
                modelo_popularidade=getattr(ctx, "modelo_popularidade", None),
            )
            st.session_state[input_key] = " ".join(
                "00" if (slug == "loto_mania_sorteio" and n == 100) else f"{n:02d}"
                for n in sugestao
            )
            st.rerun()

    # --- Área de Input ---
    col_input, col_info = st.columns([2, 1])

    with col_input:
        st.info(
            f"Escolha de **{min_base} a {max_base}** números."
            + (" (Na Lotomania, `00` equivale a `100`.)" if slug == "loto_mania_sorteio" else "")
        )
        entrada_base = st.text_area(
            label="Digite os números da base:",
            placeholder=f"Ex: {placeholder_ex} ...",
            height=120,
            key=input_key,
            help="Separe por espaços, vírgulas ou quebra de linha.",
        )

    with col_info:
        st.info(exemplo_texto)

    base_preview = _parse_base_numbers(entrada_base, slug)
    n_preview = len(base_preview)

    # Seletor dinâmico de modo/garantia com base na quantidade digitada
    modo_selecionado = None
    qtd_jogos_parcial = 20
    if min_base <= n_preview <= max_base:
        opcoes = opcoes_fechamento_para_jogo(config, n_preview)
        labels = [op["label"] for op in opcoes]
        escolha_label = st.selectbox(
            "Tipo de Fechamento / Garantia:",
            labels,
            index=0,
            key=f"closures_modo_{slug}_{n_preview}",
        )
        modo_selecionado = next(op for op in opcoes if op["label"] == escolha_label)
        if modo_selecionado["id"] == "parcial":
            qtd_jogos_parcial = int(
                st.slider(
                    "Quantidade de jogos na cobertura balanceada:",
                    min_value=5,
                    max_value=100,
                    value=20,
                    step=5,
                    key=f"closures_qtd_parcial_{slug}",
                )
            )

    if st.button(
        "⚡ Gerar Matriz Econômica Agora",
        width="stretch",
        type="primary",
    ):
        try:
            base = _parse_base_numbers(entrada_base, slug)

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

            with st.spinner("📐 Construindo Covering Design verificado..."):
                if modo_selecionado is None:
                    opcoes = opcoes_fechamento_para_jogo(config, len(base))
                    modo_selecionado = opcoes[0]

                is_completo = modo_selecionado["id"] == "completo"
                is_parcial = modo_selecionado["id"] == "parcial"
                res = gerar_fechamento_detalhado(
                    base,
                    config,
                    garantia_t=modo_selecionado.get("t"),
                    condicao_m=modo_selecionado.get("m"),
                    completo=is_completo,
                    max_jogos=qtd_jogos_parcial if is_parcial else None,
                )
                jogos = res["jogos"]
                custo_otimizado = len(jogos) * preco
                comb_total = math.comb(len(base), config.bet_size)

            st.markdown("---")
            st.subheader("💰 Relatório da Matriz")

            if slug == "loto_mania_sorteio":
                # Não exibe "economia" fictícia de quatrilhões sobre C(70,50)
                exposicao = [sum(1 for j in jogos if n in j) for n in base]
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Jogos Gerados", f"{len(jogos)}")
                with m2:
                    st.metric("Custo Total do Pacote", _brl(custo_otimizado))
                with m3:
                    st.metric(
                        "Exposição por Dezena",
                        f"{min(exposicao)}–{max(exposicao)}x",
                        delta=f"Média {np.mean(exposicao):.1f}x",
                        delta_color="off",
                    )
            else:
                custo_bruto = comb_total * preco
                economia = max(0.0, custo_bruto - custo_otimizado)
                pct_economia = (economia / custo_bruto) * 100 if custo_bruto > 0 else 0.0

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric(
                        f"Desdobramento Completo ({comb_total:,} jogos)",
                        _brl(custo_bruto),
                    )
                with m2:
                    delta_text = f"-{pct_economia:.1f}% Off" if pct_economia > 0 else "Completo"
                    st.metric(
                        f"Matriz ({len(jogos)} jogos)",
                        _brl(custo_otimizado),
                        delta=delta_text,
                        delta_color="normal" if pct_economia > 0 else "off",
                    )
                with m3:
                    st.metric(
                        "Economia Real",
                        _brl(economia),
                        delta="vs. completo" if economia > 0 else "0%",
                        delta_color="normal" if economia > 0 else "off",
                    )

            # Métrica de popularidade média do pacote (se modelo disponível)
            modelo_pop = getattr(ctx, "modelo_popularidade", None)
            if modelo_pop is not None and jogos:
                razoes = modelo_pop.razao_ganhadores_batch(np.asarray(jogos, dtype=int))
                st.caption(
                    f"📊 **Risco de divisão medido:** razão média de ganhadores do fechamento = "
                    f"**{float(np.mean(razoes)):.2f}x** (1,00x = jogo aleatório médio; menor = divide menos o prêmio)."
                )

            if res["garantia_verificada"]:
                st.success(
                    f"✅ **Matriz Aplicada:** {len(jogos)} jogo(s). **Garantia:** {res['descricao_garantia']}."
                )
            else:
                st.info(
                    f"ℹ️ **Cobertura Aplicada:** {len(jogos)} jogo(s). **Tipo:** {res['descricao_garantia']}."
                )

            # Visualização leve em bloco único (evita milhares de st.text)
            linhas_fmt = []
            txt_lines = []
            for i, jogo in enumerate(jogos, 1):
                nums_fmt = " ".join(
                    "00" if (slug == "loto_mania_sorteio" and n == 100) else f"{n:02d}"
                    for n in jogo
                )
                linhas_fmt.append(f"Jogo {i:03d}: {nums_fmt}")
                txt_lines.append(nums_fmt)
            txt_out = "\n".join(txt_lines) + "\n"

            with st.expander(f"📋 Visualizar/Copiar Jogos ({len(jogos)})", expanded=len(jogos) <= 50):
                st.code("\n".join(linhas_fmt), language="text")

            st.download_button(
                "📥 Baixar Matriz (.txt)",
                txt_out,
                f"LotoCiencia_Matriz_{len(base)}dz_{len(jogos)}jogos.txt",
                width="stretch",
            )

        except Exception as e:
            logger.error(f"Erro matrix: {e}")
            st.error("❌ Ocorreu um erro ao calcular a matriz. Verifique seus números.")
