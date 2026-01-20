# app/core/generator_genetic.py
import numpy as np
import random
from typing import List, Optional
from app.core.logger import logger
from scipy import stats


class GeneticMiner:
    def __init__(self, ctx, estrategia: str = "balanceada"):
        self.ctx = ctx
        self.config = ctx.config

        # 1) Blindagem de Configuração
        self.bet_k = self.config.bet_size
        self.n_numbers = self.config.n_numbers

        # 2) Pesos + Estratégia
        raw_pesos = (
            getattr(ctx, "pesos_dinamicos", None)
            if hasattr(ctx, "pesos_dinamicos")
            else None
        )
        if not raw_pesos:
            raw_pesos = {"w_freq": 0.5, "w_gap": 0.5}

        if estrategia == "agressiva":
            w_freq_temp, w_gap_temp = 0.2, 0.8
        elif estrategia == "conservadora":
            w_freq_temp, w_gap_temp = 0.8, 0.2
        elif estrategia == "pura":
            w_freq_temp, w_gap_temp = 0.5, 0.5
        else:
            densidade = self.config.density
            if densidade < 0.15:  # Mega/Quina: evita vício em gap
                w_freq_temp = max(float(raw_pesos.get("w_freq", 0.5)), 0.7)
                w_gap_temp = min(float(raw_pesos.get("w_gap", 0.5)), 0.3)
            else:
                w_freq_temp = float(raw_pesos.get("w_freq", 0.5))
                w_gap_temp = float(raw_pesos.get("w_gap", 0.5))

        total_w = w_freq_temp + w_gap_temp
        if not np.isfinite(total_w) or total_w <= 0:
            total_w = 1.0
            w_freq_temp, w_gap_temp = 0.5, 0.5

        self.pesos = {"w_freq": w_freq_temp / total_w, "w_gap": w_gap_temp / total_w}

        # Modo pura: fitness caótico + penalidades atenuadas
        self.modo_pura = estrategia == "pura"

        # 3) Intervalo de Confiança (robusto: ctx.ic_info pode ser None)
        icinfo = getattr(self.ctx, "ic_info", None) or {}
        ic95 = icinfo.get("ic_95")
        if not ic95 or len(ic95) != 2:
            logger.warning(
                "[GA] 'ic_95' ausente/ inválido no contexto; penalidade de soma desativada."
            )
            self.ic_min, self.ic_max = 0, 999999
        else:
            self.ic_min, self.ic_max = float(ic95[0]), float(ic95[1])
            bet_size = self.config.bet_size

            k_sorteio = self.config.k

            if bet_size != k_sorteio:
                fator = bet_size / k_sorteio
                self.ic_min, self.ic_max = self.ic_min * fator, self.ic_max * fator
            else:
                self.ic_min, self.ic_max = self.ic_min, self.ic_max

            # ---
        # 4) Blindagem de Alinhamento (Scatter)
        self.z_freq_aligned = np.zeros(self.n_numbers, dtype=np.float64)
        self.z_gap_aligned = np.zeros(self.n_numbers, dtype=np.float64)

        df_raw = ctx.tabela.copy()

        if "Numero" in df_raw.columns:
            bolas_indices = df_raw["Numero"].values.astype(int)
        elif "numero" in df_raw.columns:
            bolas_indices = df_raw["numero"].values.astype(int)
        else:
            bolas_indices = df_raw.index.values.astype(int)

        if self.n_numbers >= 100:
            bolas_indices = np.where(bolas_indices == 0, self.n_numbers, bolas_indices)

        vals_freq = df_raw["Z_Freq"].values
        vals_gap = df_raw["Z_Gap"].values

        mask_safe = (bolas_indices >= 1) & (bolas_indices <= self.n_numbers)
        dest_indices = bolas_indices[mask_safe] - 1

        self.z_freq_aligned[dest_indices] = vals_freq[mask_safe]
        self.z_gap_aligned[dest_indices] = vals_gap[mask_safe]

        # [NOVO] Pré-cálculo de vetores Markov e Ciclo para performance
        self.z_markov = np.zeros(self.n_numbers, dtype=np.float64)
        self.z_ciclo = np.zeros(self.n_numbers, dtype=np.float64)

        # Prepara Markov
        if hasattr(ctx, "matriz_transicao") and ctx.matriz_transicao is not None:
            last_draw = ctx.df.iloc[-1][self.config.draw_cols].values
            for num_ant in last_draw:
                if 1 <= num_ant <= self.n_numbers:
                    self.z_markov += ctx.matriz_transicao[num_ant - 1]
            if self.z_markov.max() > 0:
                self.z_markov /= self.z_markov.max()  # Normaliza 0-1

        # Prepara Ciclo
        if hasattr(ctx, "ciclo_atual") and ctx.ciclo_atual:
            faltam = ctx.ciclo_atual.get("faltam_sair", [])
            if faltam:
                peso = 2.0 if self.config.is_dense else 0.5
                indices = np.array(faltam) - 1
                validos = indices[(indices >= 0) & (indices < self.n_numbers)]
                self.z_ciclo[validos] = peso

    def _fitness(self, populacao: np.ndarray) -> np.ndarray:
        """
        Fitness v2.0: Híbrido (Linear + Estrutural + Padrões)
        """
        # 1. Score Linear Base (Frequência e Gap) - O "arroz com feijão"
        indices = populacao - 1
        score_freq = self.z_freq_aligned[indices].sum(axis=1)
        score_gap = self.z_gap_aligned[indices].sum(axis=1)

        linear_score = (score_freq * self.pesos["w_freq"]) + (
            score_gap * self.pesos["w_gap"]
        )
        # [NOVO] Scores Temporais (Markov e Ciclo)
        # Como pré-calculamos no __init__, aqui é só indexar e somar (muito rápido)
        score_markov = self.z_markov[indices].sum(axis=1)
        score_ciclo = self.z_ciclo[indices].sum(axis=1)

        # Score Linear Combinado
        linear_score = (
            (score_freq * self.pesos["w_freq"])
            + (score_gap * self.pesos["w_gap"])
            + (score_markov * 0.3)  # Peso do Markov
            + score_ciclo  # Peso do Ciclo já está embutido no vetor
        )
        # 2. Score Estrutural (Co-ocorrência) - O "Molho Secreto"
        # Recompensa jogos cujos números costumam sair juntos (Clusterização natural)
        cooc_score = np.zeros(len(populacao))

        if hasattr(self.ctx, "matriz_coocorrencia"):
            matriz = self.ctx.matriz_coocorrencia
            for i, jogo in enumerate(indices):
                # Soma a força de conexão entre todos os pares do jogo
                # Pega a submatriz apenas dos números do jogo e soma a metade superior
                sub_matriz = matriz[np.ix_(jogo, jogo)]
                # A matriz é normalizada em 1.0. Valores > 1.0 são bons.
                # Subtraímos 1.0 para penalizar combinações que se repelem (<1.0)
                cooc_score[i] = np.sum(np.triu(sub_matriz, k=1))

        # 3. Penalidades de Validação (Soma e Paridade)
        somas = populacao.sum(axis=1)
        n_pares = (populacao % 2 == 0).sum(axis=1)

        penalties = np.zeros(len(populacao))

        # Penalidade Soma (Suave)
        mask_bad_soma = (somas < self.ic_min) | (somas > self.ic_max)
        penalties[mask_bad_soma] += 20.0

        # Penalidade Paridade
        mask_bad_parity = (n_pares < self.bet_k * 0.3) | (n_pares > self.bet_k * 0.7)
        penalties[mask_bad_parity] += 15.0

        # --- FÓRMULA FINAL ---
        # Equilibramos o peso linear com o peso estrutural.
        # Jogos com alta co-ocorrência têm maior probabilidade estatística real.

        raw_fitness = (linear_score * 0.4) + (cooc_score * 0.6) - penalties

        return raw_fitness

    def _crossover_set(
        self, pai1: np.ndarray, pai2: np.ndarray, pool_livre: np.ndarray
    ) -> np.ndarray:
        k_game = len(pai1)
        genes_uniao = np.union1d(pai1, pai2)

        if len(genes_uniao) >= k_game:
            filho = np.random.choice(genes_uniao, k_game, replace=False)
        else:
            faltam = k_game - len(genes_uniao)
            candidatos_extra = np.setdiff1d(pool_livre, genes_uniao)
            if len(candidatos_extra) < faltam:
                filho = pai1.copy()
            else:
                extra = np.random.choice(candidatos_extra, faltam, replace=False)
                filho = np.concatenate([genes_uniao, extra])

        filho.sort()
        return filho

    def _passa_overlap(
        self, jogo_arr: np.ndarray, escolhidos: List[np.ndarray], limite_comum: int
    ) -> bool:
        s = set(jogo_arr.tolist())
        for e in escolhidos:
            if len(s.intersection(set(e.tolist()))) > limite_comum:
                return False
        return True

    def evoluir(
        self,
        tamanho_populacao: int = 200,
        geracoes: int = 50,
        qtd_final: int = 5,
        fixos: Optional[List[int]] = None,
    ) -> List[List[int]]:

        n_numbers = self.n_numbers
        k = self.bet_k

        fixos = sorted(fixos) if fixos else []
        n_fixos = len(fixos)
        k_livre = k - n_fixos

        if k_livre <= 0:
            return [fixos] * qtd_final

        pool = np.arange(1, n_numbers + 1)
        pool_livre = np.setdiff1d(pool, fixos) if fixos else pool

        # 1) gênese
        populacao = np.array(
            [
                np.random.choice(pool_livre, k_livre, replace=False)
                for _ in range(tamanho_populacao)
            ],
            dtype=int,
        )

        # 2) loop evolutivo
        for _ in range(geracoes):
            scores = self._fitness(populacao)
            ranking = np.argsort(scores)[::-1]
            populacao = populacao[ranking]

            #  elite mínima
            n_elite = max(2, int(tamanho_populacao * 0.10))
            elite = populacao[:n_elite]

            filhos = []
            pool_livre_arr = np.array(pool_livre, dtype=int)

            while len(filhos) < (tamanho_populacao - n_elite):
                pai1 = populacao[np.random.randint(0, n_elite)]
                pai2 = populacao[np.random.randint(0, tamanho_populacao)]
                filho = self._crossover_set(pai1, pai2, pool_livre_arr)
                filhos.append(filho)

            populacao_nova = np.vstack([elite, np.array(filhos, dtype=int)])

            # mutação
            mask_mutacao = np.random.rand(tamanho_populacao) < 0.20
            mask_mutacao[:3] = False

            indices_mutar = np.where(mask_mutacao)[0]
            for idx in indices_mutar:
                genes_troca = 2 if np.random.random() > 0.5 else 1
                for _ in range(genes_troca):
                    gene_idx = np.random.randint(0, k_livre)
                    novo_gene = np.random.choice(pool_livre)
                    while novo_gene in populacao_nova[idx]:
                        novo_gene = np.random.choice(pool_livre)
                    populacao_nova[idx, gene_idx] = novo_gene
                populacao_nova[idx].sort()

            populacao = populacao_nova

        # 3) seleção final: dedup + overlap adaptativo
        populacao.sort(axis=1)
        scores_finais = self._fitness(populacao)
        ranking_final = np.argsort(scores_finais)[::-1]

        best_score = float(scores_finais[ranking_final[0]])
        populacao_ordenada = populacao[ranking_final]

        jogos_unicos_livres: List[np.ndarray] = []
        hashes_vistos = set()

        fator_overlap = self.config.get_overlap_limit() / self.config.bet_size
        limite_comum = int(k_livre * fator_overlap)

        for jogo_arr in populacao_ordenada:
            #  dedup exato primeiro
            t = tuple(jogo_arr.tolist())
            if t in hashes_vistos:
                continue

            #  depois diversidade
            if self._passa_overlap(
                jogo_arr, jogos_unicos_livres, limite_comum=limite_comum
            ):
                hashes_vistos.add(t)
                jogos_unicos_livres.append(jogo_arr.copy())

            if len(jogos_unicos_livres) >= qtd_final:
                break

        # 4) fallback: mutações + aleatório
        tentativas = 0
        max_tentativas = 500
        pool_lista = pool_livre.tolist()

        while len(jogos_unicos_livres) < qtd_final and tentativas < max_tentativas:
            tentativas += 1

            if jogos_unicos_livres:
                base = jogos_unicos_livres[0].tolist()
                idx_rem = random.randint(0, len(base) - 1)
                base.pop(idx_rem)

                cand = random.choice(pool_lista)
                while cand in base:
                    cand = random.choice(pool_lista)
                base.append(cand)
                base.sort()

                arr = np.array(base, dtype=int)
                t = tuple(arr.tolist())

                if t not in hashes_vistos:
                    min_score = -9999 if self.modo_pura else (best_score - 40)
                    if float(self._fitness(np.array([arr], dtype=int))[0]) > min_score:
                        if self._passa_overlap(
                            arr, jogos_unicos_livres, limite_comum=limite_comum
                        ):
                            hashes_vistos.add(t)
                            jogos_unicos_livres.append(arr)
                            continue

            novo_random = np.random.choice(pool_livre, k_livre, replace=False)
            novo_random.sort()
            t_rand = tuple(novo_random.tolist())

            if t_rand not in hashes_vistos:
                if self._passa_overlap(
                    novo_random, jogos_unicos_livres, limite_comum=limite_comum
                ):
                    hashes_vistos.add(t_rand)
                    jogos_unicos_livres.append(novo_random)

        # 5) montagem final com fixos
        resultado_final: List[List[int]] = []
        for jogo_livre in jogos_unicos_livres[:qtd_final]:
            if n_fixos > 0:
                completo = np.concatenate([jogo_livre, np.array(fixos, dtype=int)])
                completo.sort()
                resultado_final.append(completo.tolist())
            else:
                resultado_final.append(jogo_livre.tolist())

        return resultado_final


def gerar_jogos_geneticos(ctx, quantidade=10, estrategia="balanceada", fixos=None):
    miner = GeneticMiner(ctx, estrategia=estrategia)
    n_gens = 60 if ctx.config.n_numbers >= 60 else 30
    return miner.evoluir(
        tamanho_populacao=300,
        geracoes=n_gens,
        qtd_final=quantidade,
        fixos=fixos,
    )
