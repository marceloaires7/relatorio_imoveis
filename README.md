# Painel de Consulta de Imóveis (Streamlit)

Aplicação web para o grupo consultar os 125 imóveis da carteira consolidada
(base cartográfica + triagem PPR + histórico TB55 + base LUOS revisada, unidos
pela chave `CD_IMOVEL`) e montar a Justificativa Técnica Preliminar do PPR 2026.

## Conteúdo

| Arquivo | Função |
|---|---|
| `app.py` | Interface: 5 abas |
| `nucleo.py` | Paleta institucional, carga de dados e campos derivados |
| `relatorio.py` | Montagem da Justificativa Técnica e exportação em Word/Markdown |
| `Imoveis_consolidado.xlsx` | Carteira (6 abas; regras de junção na aba Leia-me) |
| `LUOS_base_revisada.xlsx` | Parâmetros urbanísticos revisados e log da revisão |
| `REVISAO.md` | O que foi auditado e corrigido em julho/2026 — **leia antes de usar** |
| `requirements.txt` | Dependências Python |
| `.streamlit/config.toml` | Tema institucional Terracap |

## As cinco abas

1. **Visão geral** — panorama da seleção, com área de terreno e potencial
   construtivo separados, e um bloco de cobertura e qualidade dos dados.
2. **Explorar dados** — tabela dinâmica por conjuntos de colunas, com download
   em CSV e Excel.
3. **Ficha do imóvel** — dossiê completo: base cartográfica, triagem PPR, quadro
   urbanístico aplicável, registro cartorial, linha do tempo e alienações.
4. **Relatório PPR** — monta a Justificativa Técnica Preliminar nas 11 seções do
   modelo aprovado e exporta em Word.
5. **Base LUOS** — consulta às 910 faixas de parâmetros, enquadramento de lote
   por área e log das 826 revisões da base.

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
Como os dados envolvem processos e avaliações, mantenha o acesso restrito à
rede/VPN interna.

**Opção 2 — Streamlit Community Cloud (nuvem, gratuito).** Publique esta pasta em
um repositório no GitHub e conecte em https://share.streamlit.io. Use repositório
**privado** e restrinja os visualizadores do app aos e-mails do grupo; em
repositório público os dados ficariam expostos na internet.

## Como atualizar os dados

Substitua `Imoveis_consolidado.xlsx` ou `LUOS_base_revisada.xlsx` pela nova
versão, mantendo o mesmo nome e as mesmas abas. O painel detecta a troca
automaticamente na próxima interação — não é preciso reiniciar o app.

## Estrutura esperada dos arquivos

`Imoveis_consolidado.xlsx`: abas `Consolidado` (1 linha por imóvel),
`LUOS_Vinculacao`, `TB55_Observacoes`, `TB55_Processos`, `TB55_Alienacoes` e
`Leia-me`.

`LUOS_base_revisada.xlsx`: abas `Consolidado LUOS` e `Log de alterações`.

Se nomes de abas ou colunas mudarem, ajuste `nucleo.py` — a carga de dados está
concentrada lá.

## Atenção ao ler os dados

`AREA_MAX` é a **área máxima de construção**, não a área do lote. A área do
terreno é `Shape__Are`, e `AREA_CALCU` é o **coeficiente de aproveitamento**.
O painel já trabalha com nomes corrigidos (`AREA_TERRENO`, `POT_CONSTRUTIVO`,
`CA_BASE`), mas quem for consultar a planilha diretamente precisa saber disso.
Detalhes e verificação em `REVISAO.md`.
