# app/core/generator_genetic.py
"""
Motor de Geração Genética (Algoritmo Evolutivo).
Versão 2.2: OTIMIZAÇÕES DE PERFORMANCE
- Penalidades proporcionais (reduz de 20/15 para 5/3)
- Co-ocorrência vetorizada (elimina loop Python)
"""

import numpy as np
from typing import List, Optional
from app.core.generator_objective import score_plausibility_batch
from app.core.strategies import normalizar_estrategia


class GeneticMiner:
    def __init__(
        self,
        ctx,
        estrategia: str = "balanceada",
        seed: Optional[int] = None,
        objective_options: dict | None = None,
    ):
        self.rng = np.random.default_rng(seed)
        self.ctx = ctx
        self.config = ctx.config
        estrategia = normalizar_estrategia(estrategia)
        self.estrategia = estrategia
        self.objective_options = dict(objective_options or {})

        self.bet_k = self.config.bet_size
        self.n_numbers = self.config.n_numbers
        self.modo_pura = estrategia == "pura"

    def _fitness(
        self, populacao: np.ndarray, fixos: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Fitness própria do gerador.

        Mede plausibilidade estatística e intenção de acerto responsável sem
        chamar o validador nem tentar maximizar o score exibido ao usuário.
        """
        if len(populacao) == 0:
            return np.array([], dtype=float)

        if fixos:
            fixos_arr = np.tile(np.array(sorted(fixos), dtype=int), (len(populacao), 1))
            completos = np.hstack([populacao, fixos_arr])
            completos.sort(axis=1)
        else:
            completos = populacao.copy()
            completos.sort(axis=1)

        return score_plausibility_batch(
            completos,
            self.ctx,
            estrategia=self.estrategia,
            **self.objective_options,
        )

    def _crossover_set(
        self, pai1: np.ndarray, pai2: np.ndarray, pool_livre: np.ndarray
    ) -> np.ndarray:
        k_game = len(pai1)
        genes_uniao = np.union1d(pai1, pai2)

        if len(genes_uniao) >= k_game:
            filho = self.rng.choice(genes_uniao, k_game, replace=False)
        else:
            faltam = k_game - len(genes_uniao)
            candidatos_extra = np.setdiff1d(pool_livre, genes_uniao)
            if len(candidatos_extra) < faltam:
                filho = pai1.copy()
            else:
                extra = self.rng.choice(candidatos_extra, faltam, replace=False)
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
        evitados: Optional[List[int]] = None,
    ) -> List[List[int]]:

        n_numbers = self.n_numbers
        k = self.bet_k

        fixos = sorted(set(int(x) for x in (fixos or [])))
        evitados = sorted(set(int(x) for x in (evitados or [])) - set(fixos))
        n_fixos = len(fixos)
        k_livre = k - n_fixos

        if k_livre <= 0:
            return [fixos[:k]] * qtd_final

        pool = np.arange(1, n_numbers + 1, dtype=int)
        bloqueados = sorted(set(fixos + evitados))
        pool_livre = np.setdiff1d(pool, bloqueados) if bloqueados else pool
        if len(pool_livre) < k_livre:
            raise ValueError("Restrições de fixos/evitados impossibilitam preencher o jogo.")

        # Gênese
        populacao = np.array(
            [
                self.rng.choice(pool_livre, k_livre, replace=False)
                for _ in range(tamanho_populacao)
            ],
            dtype=int,
        )

        # Loop evolutivo
        for _ in range(geracoes):
            scores = self._fitness(populacao, fixos=fixos)
            ranking = np.argsort(scores)[::-1]
            populacao = populacao[ranking]

            n_elite = max(2, int(tamanho_populacao * 0.10))
            elite = populacao[:n_elite]

            filhos = []
            pool_livre_arr = np.array(pool_livre, dtype=int)

            while len(filhos) < (tamanho_populacao - n_elite):
                pai1 = populacao[int(self.rng.integers(0, n_elite))]
                pai2 = populacao[int(self.rng.integers(0, tamanho_populacao))]
                filho = self._crossover_set(pai1, pai2, pool_livre_arr)
                filhos.append(filho)

            populacao_nova = np.vstack([elite, np.array(filhos, dtype=int)])

            # Mutação
            mask_mutacao = self.rng.random(tamanho_populacao) < 0.20
            mask_mutacao[:3] = False

            if len(pool_livre) > k_livre:
                indices_mutar = np.where(mask_mutacao)[0]
                for idx in indices_mutar:
                    genes_troca = 2 if self.rng.random() > 0.5 else 1
                    for _ in range(genes_troca):
                        disponiveis_mut = np.setdiff1d(pool_livre, populacao_nova[idx])
                        if len(disponiveis_mut) == 0:
                            break
                        gene_idx = int(self.rng.integers(0, k_livre))
                        novo_gene = int(self.rng.choice(disponiveis_mut))
                        populacao_nova[idx, gene_idx] = novo_gene
                    populacao_nova[idx].sort()

            populacao = populacao_nova

        # Seleção final
        populacao.sort(axis=1)
        scores_finais = self._fitness(populacao, fixos=fixos)
        ranking_final = np.argsort(scores_finais)[::-1]

        best_score = float(scores_finais[ranking_final[0]])
        populacao_ordenada = populacao[ranking_final]
        scores_ordenados = scores_finais[ranking_final]

        jogos_unicos_livres: List[np.ndarray] = []
        hashes_vistos = set()

        fator_overlap = self.config.get_overlap_limit() / self.config.bet_size
        limite_comum = int(k_livre * fator_overlap)

        for jogo_arr, sc in zip(populacao_ordenada, scores_ordenados):
            if float(sc) <= -1e8:
                continue
            t = tuple(jogo_arr.tolist())
            if t in hashes_vistos:
                continue

            if self._passa_overlap(
                jogo_arr, jogos_unicos_livres, limite_comum=limite_comum
            ):
                hashes_vistos.add(t)
                jogos_unicos_livres.append(jogo_arr.copy())

            if len(jogos_unicos_livres) >= qtd_final:
                break

        # Fallback
        tentativas = 0
        max_tentativas = 500

        while len(jogos_unicos_livres) < qtd_final and tentativas < max_tentativas:
            tentativas += 1

            if jogos_unicos_livres and len(pool_livre) > k_livre:
                base = jogos_unicos_livres[0].tolist()
                idx_rem = int(self.rng.integers(0, len(base)))
                base.pop(idx_rem)

                cands_livres = [int(x) for x in pool_livre if int(x) not in base]
                if cands_livres:
                    cand = int(self.rng.choice(cands_livres))
                    base.append(cand)
                    base.sort()

                    arr = np.array(base, dtype=int)
                    t = tuple(arr.tolist())

                    if t not in hashes_vistos:
                        min_score = -9999 if self.modo_pura else (best_score - 40)
                        score_arr = self._fitness(np.array([arr], dtype=int), fixos=fixos)
                        if float(score_arr[0]) > max(min_score, -1e8):
                            if self._passa_overlap(
                                arr, jogos_unicos_livres, limite_comum=limite_comum
                            ):
                                hashes_vistos.add(t)
                                jogos_unicos_livres.append(arr)
                                continue

            novo_random = self.rng.choice(pool_livre, k_livre, replace=False)
            novo_random.sort()
            t_rand = tuple(novo_random.tolist())

            if t_rand not in hashes_vistos:
                if self._passa_overlap(
                    novo_random, jogos_unicos_livres, limite_comum=limite_comum
                ):
                    hashes_vistos.add(t_rand)
                    jogos_unicos_livres.append(novo_random)

        if len(jogos_unicos_livres) < qtd_final:
            for jogo_arr in populacao_ordenada:
                t = tuple(jogo_arr.tolist())
                if t not in hashes_vistos:
                    hashes_vistos.add(t)
                    jogos_unicos_livres.append(jogo_arr.copy())
                if len(jogos_unicos_livres) >= qtd_final:
                    break

        # Montagem final com fixos
        resultado_final: List[List[int]] = []
        for jogo_livre in jogos_unicos_livres[:qtd_final]:
            if n_fixos > 0:
                completo = np.concatenate([jogo_livre, np.array(fixos, dtype=int)])
                completo.sort()
                resultado_final.append(completo.tolist())
            else:
                resultado_final.append(jogo_livre.tolist())

        return resultado_final


def gerar_jogos_geneticos(
    ctx,
    quantidade=10,
    estrategia="balanceada",
    fixos=None,
    evitados=None,
    numeros_evitados=None,
    seed=None,
    objective_options: dict | None = None,
):
    miner = GeneticMiner(
        ctx,
        estrategia=estrategia,
        seed=seed,
        objective_options=objective_options,
    )
    n_gens = 60 if ctx.config.n_numbers >= 60 else 30
    evitados_final = evitados if evitados is not None else numeros_evitados
    return miner.evoluir(
        tamanho_populacao=300,
        geracoes=n_gens,
        qtd_final=quantidade,
        fixos=fixos,
        evitados=evitados_final,
    )
