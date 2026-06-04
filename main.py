"""
main.py
-------
Ponto de entrada do projeto. Orquestra todas as etapas do pipeline na sequência:

  1. Leitura e validação da planilha (src/leitura_dados.py)
  2. Configuração da API de IA         (src/analise_ia.py)
  3. Classificação de perfil e alertas (src/classificador.py)
  4. Geração do resumo via OpenAI      (src/analise_ia.py)
  5. Geração dos relatórios finais     (src/relatorio.py)

Para rodar:
    python main.py

Requisitos:
    - Arquivo .env com OPENAI_API_KEY definida
    - Planilha em data/clientes_TAG.xlsx
    - Dependências instaladas: pip install -r requirements.txt
"""

import os
import logging
from dotenv import load_dotenv

# ── Importa cada módulo com responsabilidade separada ─────────────────────────
from src.leitura_dados  import carregar_planilha, validar_colunas, limpar_e_validar
from src.classificador  import classificar_perfil, gerar_alertas
from src.analise_ia     import configurar_openai, gerar_resumo_ia
from src.relatorio      import montar_entrada_cliente, salvar_relatorio_json, salvar_relatorio_txt


# ── Configuração de logging ────────────────────────────────────────────────────
# INFO → mostra progresso geral; WARNING → mostra problemas nos dados
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


# ── Carrega as variáveis de ambiente do arquivo .env ──────────────────────────
# Deve ser chamado antes de qualquer leitura de os.getenv()
load_dotenv()


# ── Caminhos — altere aqui se necessário ──────────────────────────────────────
CAMINHO_PLANILHA     = "data/clientes_TAG.xlsx"
CAMINHO_SAIDA_JSON   = "output/relatorio.json"
CAMINHO_SAIDA_TXT    = "output/relatorio.txt"


def main() -> None:
    """
    Função principal que executa o pipeline completo.
    Cada etapa está claramente identificada nos logs do terminal.
    """
    print("\n" + "=" * 55)
    print("  TAG Investimentos — Análise de Carteiras de Clientes")
    print("=" * 55 + "\n")

    # ── ETAPA 1: Leitura e validação da planilha ──────────────────────────────
    logger.info("ETAPA 1 — Lendo e validando a planilha...")

    # carregar_planilha levanta exceção se o arquivo não existir
    df = carregar_planilha(CAMINHO_PLANILHA)

    # validar_colunas levanta exceção se faltar coluna obrigatória
    # e normaliza os nomes para minúsculo
    validar_colunas(df)

    # limpar_e_validar percorre linha a linha e trata dados problemáticos
    clientes = limpar_e_validar(df)

    # ── ETAPA 2: Configuração da API de IA ───────────────────────────────────
    logger.info("ETAPA 2 — Conectando à API da OpenAI...")

    # configurar_openai levanta EnvironmentError se a chave não estiver no .env
    client = configurar_openai()

    # ── ETAPA 3 e 4: Análise de cada cliente ─────────────────────────────────
    logger.info("ETAPA 3/4 — Classificando perfis e gerando resumos com IA...")

    resultados = []

    for i, cliente in enumerate(clientes, start=1):
        logger.info(f"  [{i:02d}/{len(clientes)}] Processando: {cliente['nome']}")

        # Classifica o perfil de risco com base em regras determinísticas
        perfil = classificar_perfil(cliente)

        # Gera lista de alertas sobre inconsistências na carteira
        alertas = gerar_alertas(cliente, perfil)

        # Chama a OpenAI para gerar o resumo em linguagem natural
        # Em caso de falha na API, retorna mensagem de fallback (não para o loop)
        resumo = gerar_resumo_ia(client, cliente, perfil, alertas)

        # Consolida tudo em um dicionário pronto para o relatório
        entrada = montar_entrada_cliente(cliente, perfil, alertas, resumo)
        resultados.append(entrada)

    # ── ETAPA 5: Geração dos relatórios ──────────────────────────────────────
    logger.info("ETAPA 5 — Gerando relatórios...")

    # Cria o diretório de saída se não existir
    os.makedirs("output", exist_ok=True)

    salvar_relatorio_json(resultados, CAMINHO_SAIDA_JSON)
    salvar_relatorio_txt(resultados,  CAMINHO_SAIDA_TXT)

    # ── Sumário final no terminal ─────────────────────────────────────────────
    total_alertas = sum(1 for r in resultados if r["alertas"])
    print(f"\n{'=' * 55}")
    print(f"  ✔ Pipeline concluído com sucesso!")
    print(f"  Clientes analisados : {len(resultados)}")
    print(f"  Clientes com alertas: {total_alertas}")
    print(f"  Saída JSON : {CAMINHO_SAIDA_JSON}")
    print(f"  Saída TXT  : {CAMINHO_SAIDA_TXT}")
    print(f"{'=' * 55}\n")


# Garante que main() só rode quando o arquivo é executado diretamente
# (não quando importado por outro módulo, ex.: durante testes)
if __name__ == "__main__":
    main()
