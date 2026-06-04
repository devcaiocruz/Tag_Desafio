"""
leitura_dados.py
----------------
Responsável por toda a etapa de leitura e validação da planilha.
Separa claramente dois tipos de problema:
  1. Erros estruturais  → coluna faltando, arquivo não encontrado (levanta exceção)
  2. Dados inconsistentes → campo nulo, valor fora do intervalo (registra aviso e continua)

Dessa forma um cliente com dados ruins não impede o processamento dos demais.
"""

import math
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Colunas que DEVEM existir na planilha (em minúsculo)
COLUNAS_ESPERADAS = [
    "nome",
    "idade",
    "patrimonio_total",
    "perc_renda_variavel",
    "perc_renda_fixa",
    "perc_cripto",
    "objetivo",
]

# Valores aceitos para o campo "objetivo"
OBJETIVOS_VALIDOS = {"aposentadoria", "crescimento", "preservacao"}


def carregar_planilha(caminho: str) -> pd.DataFrame:
    """
    Lê o arquivo Excel e retorna um DataFrame do pandas.

    Levanta:
        FileNotFoundError — se o arquivo não existir no caminho informado.
        ValueError         — se o arquivo não for um Excel válido.
    """
    try:
        df = pd.read_excel(caminho)
        logger.info(f"Planilha carregada com sucesso: {len(df)} linhas encontradas.")
        return df

    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: '{caminho}'")
        raise

    except Exception as e:
        logger.error(f"Erro inesperado ao ler a planilha: {e}")
        raise ValueError(f"Não foi possível ler '{caminho}': {e}") from e


def validar_colunas(df: pd.DataFrame) -> None:
    """
    Verifica se todas as colunas obrigatórias estão presentes.
    Também padroniza os nomes para minúsculo (ex.: 'Nome' → 'nome').

    Levanta:
        ValueError — se alguma coluna obrigatória estiver ausente.
    """
    # Padroniza para minúsculo e remove espaços acidentais nos nomes
    df.columns = df.columns.str.strip().str.lower()

    colunas_presentes = set(df.columns)
    colunas_faltando = [col for col in COLUNAS_ESPERADAS if col not in colunas_presentes]

    if colunas_faltando:
        raise ValueError(
            f"A planilha está faltando as seguintes colunas obrigatórias: {colunas_faltando}\n"
            f"Colunas encontradas: {list(colunas_presentes)}"
        )

    logger.info("Estrutura da planilha validada com sucesso.")


def _parse_percentual(row: pd.Series, campo: str, avisos: list) -> float:
    """
    Tenta converter um campo percentual para float.
    - Se o valor estiver vazio (NaN), registra aviso e retorna 0.0
    - Se o valor estiver fora de 0–100, registra aviso e retorna 0.0

    Função auxiliar usada apenas dentro deste módulo (prefixo _).
    """
    try:
        valor = float(row[campo])
        # float(NaN) não levanta exceção — precisamos checar explicitamente
        # Um campo vazio no Excel vira float('nan') no pandas
        if math.isnan(valor):
            raise ValueError("valor é NaN")
        if valor < 0 or valor > 100:
            avisos.append(f"'{campo}' com valor fora do intervalo 0–100 ({valor}) → tratado como 0%")
            return 0.0
        return valor

    except (ValueError, TypeError):
        # Valor era NaN ou não numérico
        avisos.append(f"'{campo}' ausente ou inválido → tratado como 0%")
        return 0.0


def limpar_e_validar(df: pd.DataFrame) -> list[dict]:
    """
    Percorre todas as linhas do DataFrame e normaliza os dados de cada cliente.

    Para cada campo problemático, o código:
      - Decide um valor padrão seguro (ex.: campo nulo → None ou 0)
      - Registra o problema em 'avisos_dados' para constar no relatório final

    Retorna uma lista de dicionários, um por cliente.
    """
    clientes = []

    for idx, row in df.iterrows():
        # Lista de avisos sobre qualidade dos dados deste cliente
        avisos: list[str] = []

        # ------------------------------------------------------------------ #
        # NOME
        # ------------------------------------------------------------------ #
        nome = str(row.get("nome", "")).strip()
        if not nome or nome.lower() == "nan":
            nome = f"Cliente #{idx + 1} (nome não informado)"
            avisos.append("nome ausente")

        # ------------------------------------------------------------------ #
        # IDADE
        # ------------------------------------------------------------------ #
        try:
            idade = int(row["idade"])
            if idade < 0 or idade > 120:
                avisos.append(f"idade fora do intervalo válido ({idade}) → ignorada")
                idade = None
        except (ValueError, TypeError):
            avisos.append("idade ausente ou não numérica")
            idade = None

        # ------------------------------------------------------------------ #
        # PATRIMÔNIO TOTAL
        # ------------------------------------------------------------------ #
        try:
            patrimonio = float(row["patrimonio_total"])
            # float(NaN) não levanta exceção — precisamos checar explicitamente
            if math.isnan(patrimonio):
                raise ValueError("valor é NaN")
            if patrimonio <= 0:
                avisos.append(f"patrimônio inválido ({patrimonio}) → ignorado")
                patrimonio = None
        except (ValueError, TypeError):
            avisos.append("patrimônio ausente ou não numérico")
            patrimonio = None

        # ------------------------------------------------------------------ #
        # PERCENTUAIS DE ALOCAÇÃO
        # Cada um é tratado individualmente via função auxiliar
        # ------------------------------------------------------------------ #
        perc_rv  = _parse_percentual(row, "perc_renda_variavel", avisos)
        perc_rf  = _parse_percentual(row, "perc_renda_fixa",     avisos)
        perc_cri = _parse_percentual(row, "perc_cripto",         avisos)

        # Verifica se os três percentuais somam ~100%
        # Uma tolerância de 5pp é razoável para arredondamentos
        soma = perc_rv + perc_rf + perc_cri
        if abs(soma - 100) > 5:
            avisos.append(
                f"soma dos percentuais = {soma:.1f}% (esperado ~100%) → possível dado incompleto"
            )

        # ------------------------------------------------------------------ #
        # OBJETIVO
        # ------------------------------------------------------------------ #
        objetivo = str(row.get("objetivo", "")).strip().lower()
        if objetivo not in OBJETIVOS_VALIDOS:
            avisos.append(
                f"objetivo '{objetivo}' não reconhecido "
                f"(esperado: {OBJETIVOS_VALIDOS}) → marcado como 'desconhecido'"
            )
            objetivo = "desconhecido"

        # ------------------------------------------------------------------ #
        # Monta o dicionário final do cliente
        # ------------------------------------------------------------------ #
        clientes.append({
            "nome":                 nome,
            "idade":                idade,
            "patrimonio_total":     patrimonio,
            "perc_renda_variavel":  perc_rv,
            "perc_renda_fixa":      perc_rf,
            "perc_cripto":          perc_cri,
            "objetivo":             objetivo,
            "avisos_dados":         avisos,   # acumulado acima
        })

        # Log rápido no terminal caso haja problemas
        if avisos:
            logger.warning(f"Cliente '{nome}' — {len(avisos)} aviso(s): {avisos}")

    logger.info(f"{len(clientes)} clientes processados.")
    return clientes
