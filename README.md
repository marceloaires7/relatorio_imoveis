# Painel de Consulta de Imóveis (Streamlit)

Aplicação web para o grupo consultar, de forma dinâmica, os 125 imóveis da carteira
consolidada (Lista base + Triagem PPR + histórico TB55, unidos pela chave `CD_IMOVEL`).

## Conteúdo

| Arquivo | Função |
|---|---|
| `app.py` | Aplicação Streamlit (3 abas: Visão geral, Explorar dados, Ficha do imóvel) |
| `Imoveis_consolidado.xlsx` | Fonte de dados (5 abas; regras de junção na aba Leia-me) |
| `requirements.txt` | Dependências Python |
| `.streamlit/config.toml` | Tema visual e configuração do servidor |

## Como executar localmente

Requer Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abre em `http://localhost:8501`.

## Como disponibilizar para o grupo

**Opção 1 — Rede interna (mais simples).** Rode em uma máquina que fique ligada
(estação ou servidor do órgão):

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Os colegas acessam `http://IP-DA-MAQUINA:8501` pelo navegador, sem instalar nada.
Como os dados envolvem processos e avaliações, mantenha o acesso restrito à rede/VPN interna.

**Opção 2 — Streamlit Community Cloud (nuvem, gratuito).** Publique esta pasta em um
repositório no GitHub e conecte em https://share.streamlit.io. Use repositório **privado**
e restrinja os visualizadores do app aos e-mails do grupo; em repositório público os
dados ficariam expostos na internet.

## Como atualizar os dados

Substitua o arquivo `Imoveis_consolidado.xlsx` pela nova versão (gerada pela rotina de
consolidação) mantendo o mesmo nome e as mesmas abas. O painel detecta a troca
automaticamente na próxima interação — não é preciso reiniciar o app.

## Estrutura esperada do xlsx

Abas: `Consolidado` (1 linha por imóvel), `TB55_Observacoes`, `TB55_Processos`,
`TB55_Alienacoes` e `Leia-me`. Se nomes de abas ou colunas mudarem, ajuste `app.py`.
