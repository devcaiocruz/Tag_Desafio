"""
classificador.py
----------------
Classifica o perfil de risco de cada cliente usando regras determinísticas
(sem IA), baseadas em três variáveis principais:
  - objetivo declarado (aposentadoria / preservação / crescimento)
  - percentual em renda variável (ações, FIIs, etc.)
  - percentual em cripto

Por que regras e não só IA?
  - Garante consistência: o mesmo perfil sempre gera o mesmo resultado
  - Serve de âncora para a IA: o resumo gerado parte de uma classificação confiável
  - Facilita testes unitários
"""

# ─────────────────────────────────────────────────────────────────────────────
# Limiares usados nas regras de classificação
# Centralizados aqui para facilitar ajuste sem mexer na lógica
# ─────────────────────────────────────────────────────────────────────────────
LIMIAR_RV_ARROJADO        = 60   # % renda variável acima disso → arrojado
LIMIAR_RV_CONSERVADOR     = 30   # % renda variável abaixo disso → conservador
LIMIAR_RV_APOSENTADORIA   = 40   # % renda variável máximo recomendado para objetivos defensivos
LIMIAR_CRIPTO_ARROJADO    = 15   # % cripto acima disso → arrojado independente de tudo
LIMIAR_CRIPTO_CONSERVADOR = 5    # % cripto acima disso invalida conservador puro

IDADE_SENIOR      = 60   # A partir desta idade, exposição alta vira alerta
IDADE_JOVEM       = 35   # Abaixo desta idade, carteira ultra-conservadora para crescimento vira alerta
LIMIAR_RV_JOVEM   = 20   # % renda variável abaixo disso é conservador demais para jovem com crescimento
LIMIAR_RV_SENIOR  = 50   # % renda variável acima disso é arriscado demais para idoso


def classificar_perfil(cliente: dict) -> str:
    """
    Retorna o perfil de risco do cliente: 'conservador', 'moderado' ou 'arrojado'.

    Lógica aplicada (ordem importa — primeira regra satisfeita vence):
    1. Cripto > 15%  →  arrojado (exposição especulativa dominante)
    2. RV >= 60%     →  arrojado
    3. Objetivo em (preservação/aposentadoria) E RV <= 30% E cripto <= 5%  →  conservador
    4. Idade >= 60 E RV <= 30%  →  conservador (sênior com carteira defensiva)
    5. Demais casos  →  moderado
    """
    objetivo    = cliente["objetivo"]
    perc_rv     = cliente["perc_renda_variavel"]
    perc_cripto = cliente["perc_cripto"]
    idade       = cliente["idade"] or 0  # None → 0 para evitar erros de comparação

    # Regra 1: Cripto elevada = postura especulativa
    if perc_cripto > LIMIAR_CRIPTO_ARROJADO:
        return "arrojado"

    # Regra 2: Renda variável dominante
    if perc_rv >= LIMIAR_RV_ARROJADO:
        return "arrojado"

    # Regra 3: Objetivo defensivo + alocação defensiva
    objetivo_defensivo = objetivo in ("preservacao", "aposentadoria")
    if objetivo_defensivo and perc_rv <= LIMIAR_RV_CONSERVADOR and perc_cripto <= LIMIAR_CRIPTO_CONSERVADOR:
        return "conservador"

    # Regra 4: Sênior com carteira defensiva (mesmo que objetivo não seja declarado)
    if idade >= IDADE_SENIOR and perc_rv <= LIMIAR_RV_CONSERVADOR:
        return "conservador"

    # Regra 5: Tudo que não se encaixa acima é moderado
    return "moderado"


def gerar_alertas(cliente: dict, perfil: str) -> list[str]:
    """
    Verifica se a carteira do cliente apresenta inconsistências em relação
    ao seu objetivo declarado e perfil de risco.

    Cada alerta descreve UM problema específico, com os valores exatos,
    para que o gestor possa agir sem precisar abrir a planilha.

    Também repassa os avisos de qualidade de dados (ex.: campo nulo)
    identificados na etapa de leitura.
    """
    alertas: list[str] = []

    objetivo    = cliente["objetivo"]
    perc_rv     = cliente["perc_renda_variavel"]
    perc_cripto = cliente["perc_cripto"]
    perc_rf     = cliente["perc_renda_fixa"]
    idade       = cliente["idade"] or 0

    # ── 1. Objetivo conservador/preservação com RV excessiva ────────────────
    if objetivo in ("preservacao", "aposentadoria") and perc_rv > LIMIAR_RV_APOSENTADORIA:
        alertas.append(
            f"[ALOCAÇÃO] Objetivo '{objetivo}' porém {perc_rv:.0f}% em renda variável "
            f"— recomendado ≤ {LIMIAR_RV_APOSENTADORIA}% para este perfil."
        )

    # ── 2. Cripto elevada para perfil defensivo ──────────────────────────────
    if objetivo in ("preservacao", "aposentadoria") and perc_cripto > LIMIAR_CRIPTO_CONSERVADOR:
        alertas.append(
            f"[ALOCAÇÃO] Objetivo '{objetivo}' com {perc_cripto:.0f}% em cripto "
            f"— recomendado ≤ {LIMIAR_CRIPTO_CONSERVADOR}% para este perfil."
        )

    # ── 3. Cripto excessiva mesmo para crescimento ───────────────────────────
    if objetivo == "crescimento" and perc_cripto > 20:
        alertas.append(
            f"[ALOCAÇÃO] {perc_cripto:.0f}% em cripto é alta concentração de risco "
            f"mesmo para objetivo de crescimento."
        )

    # ── 4. Idoso com carteira agressiva ─────────────────────────────────────
    if idade >= IDADE_SENIOR and perc_rv > LIMIAR_RV_SENIOR:
        alertas.append(
            f"[FAIXA ETÁRIA] Cliente com {idade} anos e {perc_rv:.0f}% em renda variável "
            f"— exposição elevada para a fase de vida."
        )

    # ── 5. Jovem com crescimento e carteira ultra-conservadora ───────────────
    # Um cliente de 27 anos com objetivo crescimento e 90% em renda fixa
    # está deixando potencial de retorno de longo prazo na mesa
    if idade and idade < IDADE_JOVEM and objetivo == "crescimento" and perc_rv < LIMIAR_RV_JOVEM:
        alertas.append(
            f"[FAIXA ETÁRIA] Cliente jovem ({idade} anos) com objetivo crescimento "
            f"mas apenas {perc_rv:.0f}% em renda variável — perfil conservador demais para o objetivo."
        )

    # ── 6. Percentuais que não fecham em ~100% ───────────────────────────────
    soma = perc_rv + perc_rf + perc_cripto
    if abs(soma - 100) > 5:
        alertas.append(
            f"[DADOS] Soma dos percentuais de alocação = {soma:.1f}% "
            f"— possível dado incompleto (esperado ~100%)."
        )

    # ── 7. Repassa avisos de qualidade de dados da etapa de leitura ──────────
    for aviso in cliente.get("avisos_dados", []):
        alertas.append(f"[DADO AUSENTE/INVÁLIDO] {aviso}")

    return alertas
