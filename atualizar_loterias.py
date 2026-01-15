import requests
import pandas as pd
from datetime import datetime
import os
import time

BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
DATA_DIR = "data"

LOTERIAS_CONFIG = {
    "megasena": {"arquivo": "mega_sena_sorteio.xlsx", "num_bolas": 6},
    "lotofacil": {"arquivo": "loto_facil_sorteio.xlsx", "num_bolas": 15},
    "quina": {"arquivo": "quina_sorteio.xlsx", "num_bolas": 5},
    "lotomania": {"arquivo": "loto_mania_sorteio.xlsx", "num_bolas": 20},
}


def buscar_resultado_concurso(loteria, concurso):
    """Busca resultado de um concurso específico"""
    try:
        response = requests.get(f"{BASE_URL}/{loteria}/{concurso}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Erro ao buscar concurso {concurso}: {e}")
        return None


def buscar_ultimo_resultado(loteria, max_tentativas=3):
    """Busca o último resultado com retry"""
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = requests.get(f"{BASE_URL}/{loteria}/latest", timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Tentativa {tentativa}/{max_tentativas} falhou: {e}")
            if tentativa < max_tentativas:
                print(f"   ⏳ Aguardando 30s antes de tentar novamente...")
                time.sleep(30)
            else:
                print(f"   ❌ Todas as tentativas falharam para {loteria}")
                return None
    return None


def criar_linha_dados(dados_api, num_bolas):
    """Converte dados da API para formato do Excel (ordem de sorteio)"""

    dezenas_sorteio = dados_api["dezenasOrdemSorteio"]

    linha = {"Concurso": dados_api["concurso"], "Data": dados_api["data"]}

    for i in range(num_bolas):
        if i < len(dezenas_sorteio):
            linha[f"bola {i+1}"] = int(dezenas_sorteio[i])
        else:
            linha[f"bola {i+1}"] = None

    return linha


def atualizar_excel(loteria, arquivo_nome, num_bolas):
    """Atualiza o Excel de uma loteria específica, preenchendo lacunas se necessário"""

    # 1. Verifica se o arquivo existe
    arquivo_excel = os.path.join(DATA_DIR, arquivo_nome)
    if not os.path.exists(arquivo_excel):
        print(f"❌ Arquivo {arquivo_excel} não encontrado!")
        return False

    # 2. Busca o último resultado disponível na API
    ultimo_api = buscar_ultimo_resultado(loteria)
    if not ultimo_api:
        return False

    concurso_mais_recente_api = ultimo_api["concurso"]

    # 3. Lê o Excel existente
    df_existente = pd.read_excel(arquivo_excel)

    # 4. Identifica o concurso mais recente no Excel
    if len(df_existente) == 0:
        concurso_mais_recente_excel = 0
    else:
        concurso_mais_recente_excel = df_existente["Concurso"].max()

    # 5. Verifica se já está atualizado
    if concurso_mais_recente_excel >= concurso_mais_recente_api:
        print(
            f"→ {loteria} já está atualizado (concurso {concurso_mais_recente_excel})"
        )
        return False

    # 6. Calcula quantos concursos estão faltando
    concursos_faltantes = list(
        range(concurso_mais_recente_excel + 1, concurso_mais_recente_api + 1)
    )
    num_faltantes = len(concursos_faltantes)

    if num_faltantes > 1:
        print(f"   ⚠️  Detectados {num_faltantes} concursos faltando!")
        print(
            f"   📋 Buscando concursos: {concursos_faltantes[0]} até {concursos_faltantes[-1]}"
        )

    # 7. Busca todos os concursos faltantes
    novas_linhas = []
    for concurso in concursos_faltantes:
        print(f"   🔍 Buscando concurso {concurso}...")

        dados_api = buscar_resultado_concurso(loteria, concurso)
        if dados_api:
            nova_linha = criar_linha_dados(dados_api, num_bolas)
            novas_linhas.append(nova_linha)
            print(f"   ✓ Concurso {concurso} encontrado")
        else:
            print(
                f"   ✗ Concurso {concurso} não encontrado (pode não ter sido sorteado ainda)"
            )

        # Pausa para não sobrecarregar a API
        time.sleep(0.5)

    # 8. Se não encontrou nenhum concurso novo, retorna
    if len(novas_linhas) == 0:
        print(f"→ Nenhum concurso novo disponível para {loteria}")
        return False

    # 9. Adiciona as novas linhas NO TOPO (ordem reversa para manter mais recente primeiro)
    df_novas_linhas = pd.DataFrame(novas_linhas)
    df_novas_linhas = df_novas_linhas.sort_values(
        "Concurso", ascending=False
    )  # Mais recente primeiro
    df_atualizado = pd.concat([df_novas_linhas, df_existente], ignore_index=True)

    # 10. Salva o Excel atualizado
    df_atualizado.to_excel(arquivo_excel, index=False, engine="openpyxl")
    print(f"✅ {loteria}: {len(novas_linhas)} concurso(s) adicionado(s) no topo!")

    return True


def atualizar_todas_loterias():
    """Atualiza todos os Excels"""
    print(f"\n{'='*60}")
    print(f"🎲 Atualização iniciada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")

    if not os.path.exists(DATA_DIR):
        print(f"❌ Pasta '{DATA_DIR}/' não encontrada!")
        return

    atualizacoes = 0
    for loteria, config in LOTERIAS_CONFIG.items():
        print(f"🎰 Processando {loteria.upper()}...")
        if atualizar_excel(loteria, config["arquivo"], config["num_bolas"]):
            atualizacoes += 1
        print()

    print(f"{'='*60}")
    print(f"✔️  Concluído! {atualizacoes} loteria(s) atualizada(s)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    atualizar_todas_loterias()
