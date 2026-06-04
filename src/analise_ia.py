"""
analise_ia.py
-------------
Responsável pela comunicação com a API da OpenAI.
Gera resumos em linguagem natural a partir dos dados de cada cliente,
usando o modelo gpt-4o-mini como motor de análise.

Separar esta camada em módulo próprio facilita trocar o provedor de IA
(ex.: OpenAI → Gemini) sem tocar nos demais módulos do pipeline.
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def configurar_openai() -> OpenAI:
    """
    Lê a chave de API da variável de ambiente e retorna um cliente OpenAI pronto para uso.

    Levanta:
        EnvironmentError — se OPENAI_API_KEY não estiver definida no ambiente.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Variável de ambiente OPENAI_API_KEY não encontrada.\n"
            "Adicione ao .env: OPENAI_API_KEY=sua_chave_aqui"
        )
    client = OpenAI(api_key=api_key)
    logger.info("Cliente OpenAI configurado com sucesso.")
    return client


def _montar_prompt(cliente: dict, perfil: str, alertas: list[str]) -> str:
    """
    Monta o prompt enviado ao modelo com os dados do cliente,
    o perfil classificado e os alertas identificados.
    """
    patrimonio_fmt = (
        f"R$ {cliente['patrimonio_total']:,.0f}"
        if cliente["patrimonio_total"] is not None
        else "não informado"
    )
    idade_fmt = cliente["idade"] if cliente["idade"] is not None else "não informada"
    alertas_fmt = (
        "\n".join(f"  - {a}" for a in alertas)
        if alertas else "  Nenhum alerta identificado."
    )
    return f"""Você é um analista sênior de carteiras de uma gestora de patrimônio familiar.
Analise o cliente abaixo e escreva um parágrafo de até 4 linhas em português,
explicando se a carteira está adequada ao perfil e objetivo declarado.
Use linguagem profissional, direta e sem marcadores ou listas.

Dados do cliente:
- Nome: {cliente['nome']}
- Idade: {idade_fmt}
- Patrimônio total: {patrimonio_fmt}
- Renda variável: {cliente['perc_renda_variavel']:.0f}%
- Renda fixa: {cliente['perc_renda_fixa']:.0f}%
- Cripto: {cliente['perc_cripto']:.0f}%
- Objetivo declarado: {cliente['objetivo']}
- Perfil de risco classificado: {perfil}

Alertas identificados:
{alertas_fmt}

Escreva apenas o parágrafo de análise.""".strip()


def gerar_resumo_ia(client: OpenAI, cliente: dict, perfil: str, alertas: list[str]) -> str:
    """
    Envia os dados do cliente à API da OpenAI e retorna o resumo gerado.

    Em caso de falha na chamada (timeout, cota excedida, etc.), retorna uma
    mensagem de fallback em vez de propagar a exceção — o pipeline continua.
    """
    prompt = _montar_prompt(cliente, perfil, alertas)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        resumo = response.choices[0].message.content.strip()
        logger.debug(f"Resumo gerado para '{cliente['nome']}' ({len(resumo)} chars).")
        return resumo
    except Exception as e:
        logger.warning(f"Falha ao gerar resumo para '{cliente['nome']}': {type(e).__name__}: {e}")
        return (
            f"[Resumo indisponível — erro na chamada à API da OpenAI: {type(e).__name__}. "
            f"Verifique a chave e os limites de uso.]"
        )
