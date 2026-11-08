import json
import requests
import pandas as pd
from datetime import datetime
import os
import time

BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"
DATA_DIR = "data"
DETALHES_DIR = os.path.join(DATA_DIR, "detalhes")
# Quantos concursos antigos (sem detalhes) buscar por execução, por loteria.
# O histórico é preenchido aos poucos para caber no tempo do workflow.
LIMITE_BACKFILL = int(os.getenv("LIMITE_BACKFILL", "100"))
MAX_FALHAS_SEGUIDAS = 5

COLUNAS_FIXAS_DETALHES = [
    "Concurso",
    "Data",
    "acumulou",
    "valorArrecadado",
    "valorAcumuladoProximoConcurso",
    "valorEstimadoProximoConcurso",
    "valorAcumuladoConcursoEspecial",
    "concursoEspecial",
    "local",
]

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


def _numero(valor):
    """Converte para float; devolve None se vier vazio ou inválido."""
    if valor is None or isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def criar_linha_detalhes(dados_api):
    """Extrai da resposta da API os campos que não existem no Excel:
    ganhadores e prêmio por faixa, arrecadação, acumulado e local dos ganhadores.
    Tolerante a concursos antigos, em que alguns campos podem faltar."""

    linha = {
        "Concurso": dados_api["concurso"],
        "Data": dados_api.get("data"),
        "acumulou": dados_api.get("acumulou"),
        "valorArrecadado": _numero(dados_api.get("valorArrecadado")),
        "valorAcumuladoProximoConcurso": _numero(
            dados_api.get("valorAcumuladoProximoConcurso")
        ),
        "valorEstimadoProximoConcurso": _numero(
            dados_api.get("valorEstimadoProximoConcurso")
        ),
        "valorAcumuladoConcursoEspecial": _numero(
            dados_api.get("valorAcumuladoConcursoEspecial")
        ),
        "concursoEspecial": dados_api.get("concursoEspecial"),
        "local": dados_api.get("local"),
    }

    for premio in dados_api.get("premiacoes") or []:
        faixa = premio.get("faixa")
        if faixa is None:
            continue
        linha[f"faixa{int(faixa)}_ganhadores"] = premio.get("ganhadores")
        linha[f"faixa{int(faixa)}_premio"] = _numero(premio.get("valorPremio"))

    linha["localGanhadores"] = json.dumps(
        dados_api.get("localGanhadores") or [], ensure_ascii=False
    )
    return linha


def _ordenar_colunas(df):
    faixas = sorted(
        (c for c in df.columns if c.startswith("faixa")),
        key=lambda c: (int(c[5 : c.index("_")]), c),
    )
    ordem = [c for c in COLUNAS_FIXAS_DETALHES if c in df.columns] + faixas
    if "localGanhadores" in df.columns:
        ordem.append("localGanhadores")
    return df[ordem]


def caminho_detalhes(loteria):
    return os.path.join(DETALHES_DIR, f"{loteria}_detalhes.csv")


def ler_detalhes(loteria):
    caminho = caminho_detalhes(loteria)
    if os.path.exists(caminho):
        return pd.read_csv(caminho)
    return pd.DataFrame(columns=COLUNAS_FIXAS_DETALHES)


def salvar_detalhes(loteria, df_existente, novas_linhas):
    """Junta as linhas novas ao CSV (mais recente primeiro, sem duplicar concurso)."""
    if not novas_linhas:
        return 0
    os.makedirs(DETALHES_DIR, exist_ok=True)
    df_novas = pd.DataFrame(novas_linhas)
    df = pd.concat([df_novas, df_existente], ignore_index=True)
    df = df.drop_duplicates(subset="Concurso", keep="first")
    df = df.sort_values("Concurso", ascending=False)
    _ordenar_colunas(df).to_csv(caminho_detalhes(loteria), index=False)
    return len(df_novas)


def atualizar_detalhes(loteria, arquivo_nome, detalhes_novos):
    """Grava os detalhes dos concursos que acabaram de entrar no Excel e
    completa, aos poucos, os concursos antigos que ainda não têm detalhes."""

    df_detalhes = ler_detalhes(loteria)
    conhecidos = set(df_detalhes["Concurso"].astype(int))
    conhecidos.update(int(l["Concurso"]) for l in detalhes_novos)

    linhas = list(detalhes_novos)

    arquivo_excel = os.path.join(DATA_DIR, arquivo_nome)
    concursos_excel = set(pd.read_excel(arquivo_excel)["Concurso"].astype(int))
    pendentes = sorted(concursos_excel - conhecidos, reverse=True)[:LIMITE_BACKFILL]

    falhas_seguidas = 0
    for concurso in pendentes:
        dados_api = buscar_resultado_concurso(loteria, concurso)
        if dados_api:
            linhas.append(criar_linha_detalhes(dados_api))
            falhas_seguidas = 0
        else:
            falhas_seguidas += 1
            if falhas_seguidas >= MAX_FALHAS_SEGUIDAS:
                print("   ⚠️  Muitas falhas seguidas; o resto fica para a próxima execução")
                break
        time.sleep(0.3)

    gravados = salvar_detalhes(loteria, df_detalhes, linhas)
    salvos = set(ler_detalhes(loteria)["Concurso"].astype(int))
    restantes = len(concursos_excel - salvos)
    print(
        f"📊 {loteria}: {gravados} detalhe(s) gravado(s); "
        f"faltam {restantes} concurso(s) antigo(s)"
    )
    return gravados


def atualizar_excel(loteria, arquivo_nome, num_bolas, detalhes_novos=None):
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
            if detalhes_novos is not None:
                detalhes_novos.append(criar_linha_detalhes(dados_api))
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
        detalhes_novos = []
        if atualizar_excel(
            loteria, config["arquivo"], config["num_bolas"], detalhes_novos
        ):
            atualizacoes += 1
        try:
            atualizar_detalhes(loteria, config["arquivo"], detalhes_novos)
        except Exception as e:  # os detalhes nunca devem derrubar a atualização
            print(f"   ⚠️  Detalhes de {loteria} não atualizados: {e}")
        print()

    print(f"{'='*60}")
    print(f"✔️  Concluído! {atualizacoes} loteria(s) atualizada(s)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    atualizar_todas_loterias()
