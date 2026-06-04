# TAG Investimentos — Desafio Técnico: Automação com Python e IA

Script Python que processa uma planilha de carteiras de clientes, classifica perfis de risco e gera análises automatizadas usando a API da **OpenAI**.

---

## Estrutura do projeto

```
tag_desafio/
├── main.py                  # Ponto de entrada — orquestra todas as etapas
├── requirements.txt         # Dependências do projeto
├── .env.example             # Modelo do arquivo de variáveis de ambiente
├── .gitignore               # Arquivos que não vão para o repositório
│
├── src/
│   ├── __init__.py          # Torna src um pacote Python
│   ├── leitura_dados.py     # Leitura e validação da planilha
│   ├── classificador.py     # Classificação de perfil de risco por regras
│   ├── analise_ia.py        # Comunicação com a API da OpenAI
│   └── relatorio.py         # Geração dos arquivos de saída (.json e .txt)
│
├── data/                    # (não versionado) coloque a planilha aqui
│   └── clientes_TAG.xlsx    ← arquivo esperado
│
└── output/                  # (não versionado) relatórios gerados aqui
    ├── relatorio.json
    └── relatorio.txt
```

---

## Pré-requisitos

- Python 3.10 ou superior
- Conta na OpenAI (platform.openai.com) para obter a chave de API

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/tag-desafio.git
cd tag-desafio

# 2. (Recomendado) Crie um ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure a chave de API
cp .env.example .env
# Edite o arquivo .env e preencha: OPENAI_API_KEY=sua_chave_aqui

# 5. Coloque a planilha de clientes na pasta data/
# Copie o arquivo clientes_TAG.xlsx para data/clientes_TAG.xlsx
```

---

## Como rodar

```bash
python main.py
```

O script exibe o progresso no terminal e salva os resultados em `output/`.

---

## O que o script faz (passo a passo)

| Etapa | Módulo | O que acontece |
|-------|--------|----------------|
| 1 | `leitura_dados.py` | Lê o `.xlsx`, valida colunas obrigatórias, trata campos nulos e valores fora do esperado |
| 2 | `analise_ia.py` | Configura o cliente OpenAI com a chave do `.env` |
| 3 | `classificador.py` | Classifica o perfil de risco (conservador / moderado / arrojado) por regras e gera alertas |
| 4 | `analise_ia.py` | Envia os dados de cada cliente à API da OpenAI e recebe um resumo em linguagem natural |
| 5 | `relatorio.py` | Salva os resultados em `output/relatorio.json` e `output/relatorio.txt` |

---

## Dados inconsistentes — decisões tomadas

A planilha foi entregue com problemas propositais. Abaixo estão os casos identificados e como foram tratados:

| Cliente | Problema | Tratamento |
|---------|----------|------------|
| Isabela Prado | `perc_cripto` ausente | Tratado como 0% e registrado em `avisos_dados` |
| Thiago Azevedo | `patrimonio_total` ausente | Exibido como "N/A" no relatório |
| Eduardo Fontes | `idade` ausente | Exibido como "N/A"; regras de faixa etária são ignoradas |
| Fernanda Queiroz | 80% em cripto + objetivo preservação | Perfil arrojado + alerta crítico gerado |
| Sônia Brandão | 69 anos, aposentadoria, 75% RV + 10% cripto | Perfil arrojado + alertas de faixa etária e objetivo |
| Carlos Uchoa | 90% RV com objetivo aposentadoria | Perfil arrojado + alerta de inconsistência de objetivo |
| Lucas Evangelista | 27 anos, crescimento, só 5% RV | Alerta de carteira conservadora demais para o perfil |

**Princípio adotado:** nenhum cliente é descartado por dados ruins. O problema é registrado em `avisos_dados` e o processamento continua. Isso garante que o gestor veja todos os clientes no relatório, inclusive os com dados incompletos.

---

## Formato da saída

### JSON (`output/relatorio.json`)
```json
{
  "gerado_em": "2025-01-15 14:32:00",
  "total_clientes": 20,
  "clientes": [
    {
      "nome": "Ana Luiza Ferreira",
      "idade": 62,
      "patrimonio_total": 4500000,
      "alocacao": { "renda_variavel_pct": 10, "renda_fixa_pct": 88, "cripto_pct": 2 },
      "objetivo": "aposentadoria",
      "perfil_risco": "conservador",
      "resumo_ia": "Ana Luiza apresenta uma carteira...",
      "alertas": []
    }
  ]
}
```

### TXT (`output/relatorio.txt`)
Formato legível por humanos, com bloco separado por cliente, contendo dados, análise e alertas.

---

## Segurança

- A chave de API **nunca** é escrita no código — é lida de uma variável de ambiente
- O arquivo `.env` está no `.gitignore` e não vai para o repositório
- A planilha de clientes e os relatórios gerados também estão no `.gitignore`

---

## Decisões técnicas

**Por que separar em módulos?**
Cada arquivo tem uma única responsabilidade. Se precisar trocar o provedor de IA (ex.: OpenAI → Gemini), basta editar `analise_ia.py` sem tocar em nada mais.

**Por que classificar por regras E usar IA?**
As regras garantem consistência (mesma entrada → mesmo perfil). A IA gera o texto narrativo, que é onde o valor real está. As duas camadas se complementam.

**Por que `try/except` em cada cliente?**
Se a API falhar para um cliente específico (ex.: timeout), o loop continua. O cliente recebe uma mensagem de fallback e o relatório não fica incompleto.

**Por que constantes para os limiares?**
Centralizar os valores em constantes nomeadas (ex.: `LIMIAR_RV_APOSENTADORIA = 40`) evita números mágicos espalhados pelo código e facilita ajustes futuros sem risco de inconsistência entre classificação e alertas.
