"""
relatorio.py
------------
Responsável pela geração dos arquivos de saída do pipeline.

Gera dois formatos:
  - JSON  →  estruturado, ideal para integrar com outros sistemas ou APIs
  - TXT   →  legível por humanos, ideal para revisão rápida pelos gestores

Separar a geração de relatório em módulo próprio facilita:
  - Adicionar novos formatos (ex.: PDF, CSV) sem tocar em outros módulos
  - Testar a formatação de forma independente
"""

import json
import os
from datetime import datetime


def montar_entrada_cliente(
    cliente: dict,
    perfil: str,
    alertas: list[str],
    resumo_ia: str,
) -> dict:
    """
    Combina os dados brutos do cliente com os resultados da análise em
    um único dicionário organizado para o relatório.

    Estrutura do dicionário retornado:
        nome, idade, patrimonio_total
        alocacao      → sub-dict com os três percentuais
        objetivo
        perfil_risco  → resultado do classificador
        resumo_ia     → texto gerado pela OpenAI
        alertas       → lista de alertas (pode ser vazia)
    """
    return {
        "nome":            cliente["nome"],
        "idade":           cliente["idade"],
        "patrimonio_total": cliente["patrimonio_total"],
        "alocacao": {
            "renda_variavel_pct": cliente["perc_renda_variavel"],
            "renda_fixa_pct":    cliente["perc_renda_fixa"],
            "cripto_pct":        cliente["perc_cripto"],
        },
        "objetivo":      cliente["objetivo"],
        "perfil_risco":  perfil,
        "resumo_ia":     resumo_ia,
        "alertas":       alertas,
    }


def salvar_relatorio_json(dados: list[dict], caminho: str) -> None:
    """
    Salva a lista completa de análises em formato JSON.

    O arquivo inclui metadados (data de geração, total de clientes) que
    facilitam rastrear quando a análise foi executada.

    Args:
        dados   — lista de dicionários retornados por montar_entrada_cliente()
        caminho — caminho onde o arquivo .json será salvo
    """
    # Garante que o diretório de saída existe
    os.makedirs(os.path.dirname(caminho), exist_ok=True)

    relatorio = {
        "gerado_em":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_clientes":  len(dados),
        "clientes":        dados,
    }

    with open(caminho, "w", encoding="utf-8") as f:
        # indent=2 → arquivo legível; ensure_ascii=False → acentos corretos
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    print(f"✔ Relatório JSON salvo em: {caminho}")


def salvar_relatorio_txt(dados: list[dict], caminho: str) -> None:
    """
    Salva o relatório em formato texto plano, um bloco por cliente.

    Cada bloco contém:
      - Dados cadastrais e de alocação
      - Perfil de risco classificado
      - Resumo gerado pela IA
      - Lista de alertas (se houver)

    Args:
        dados   — lista de dicionários retornados por montar_entrada_cliente()
        caminho — caminho onde o arquivo .txt será salvo
    """
    os.makedirs(os.path.dirname(caminho), exist_ok=True)

    linhas = [
        "=" * 65,
        "  RELATÓRIO DE ANÁLISE DE CARTEIRAS — TAG INVESTIMENTOS",
        f"  Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
        f"  Total de clientes analisados: {len(dados)}",
        "=" * 65,
        "",
    ]

    for c in dados:
        # Formata patrimônio ou exibe N/A se ausente
        patrimonio_fmt = (
            f"R$ {c['patrimonio_total']:,.0f}"
            if c["patrimonio_total"] is not None
            else "N/A"
        )

        idade_fmt = str(c["idade"]) if c["idade"] is not None else "N/A"

        linhas += [
            f"  Cliente : {c['nome']}",
            f"  Idade   : {idade_fmt} anos    |    Patrimônio: {patrimonio_fmt}",
            f"  Alocação: {c['alocacao']['renda_variavel_pct']:.0f}% Renda Variável  |  "
            f"{c['alocacao']['renda_fixa_pct']:.0f}% Renda Fixa  |  "
            f"{c['alocacao']['cripto_pct']:.0f}% Cripto",
            f"  Objetivo: {c['objetivo'].capitalize()}    |    "
            f"Perfil de Risco: {c['perfil_risco'].upper()}",
            "",
            "  Análise (IA OpenAI):",
        ]

        # Adiciona o resumo com recuo para ficar visualmente separado
        for linha in c["resumo_ia"].split("\n"):
            linhas.append(f"    {linha}")

        linhas.append("")

        # Alertas — só exibe o bloco se houver pelo menos um
        if c["alertas"]:
            linhas.append("  ⚠  Alertas:")
            for alerta in c["alertas"]:
                linhas.append(f"      • {alerta}")
            linhas.append("")

        linhas += ["-" * 65, ""]

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"✔ Relatório TXT salvo em: {caminho}")
