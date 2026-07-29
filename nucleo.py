# -*- coding: utf-8 -*-
"""
Núcleo do painel: paleta institucional, carga de dados e campos derivados.

Concentra aqui tudo o que app.py e relatorio.py precisam compartilhar, para que
a correção de uma regra de negócio valha para todas as abas de uma vez só.
"""
from __future__ import annotations

import html
import os
import re

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Paleta institucional Terracap (design.txt)
# ----------------------------------------------------------------------------
VERDE = "#006D33"        # Pantone 356C — cor principal
DOURADO = "#E7B000"      # Pantone 110C — atenção / pendência
AZUL = "#00416D"         # Pantone 294C — bloqueio / dado cartorial

VERDE_CLARO = "#E5F0E9"
AZUL_CLARO = "#E5EBF0"
DOURADO_CLARO = "#FBF2DA"
GRAFITE = "#243239"
CINZA = "#5A6B7B"
CINZA_CLARO = "#D8DEE3"

# Sequência categórica: institucional primeiro, tons derivados depois.
SEQUENCIA = [VERDE, AZUL, DOURADO, "#4C9A6F", "#3E7096", "#C4941F", "#8FBFA4", "#7D9BB5"]

# Situação do lote codificada por leitura de negócio, não por estética:
# verde = disponível, dourado = exige providência, azul = uso de terceiro.
COR_SITUACAO = {
    "VAGO": VERDE,
    "CERCADO": DOURADO,
    "CERCADO E VAGO": DOURADO,
    "OBSTRUIDO": "#C4941F",
    "OCUPADO": AZUL,
    "CONSTRUIDO": "#3E7096",
    "SEM INFORMAÇÃO": CINZA_CLARO,
}

ARQUIVO = "Imoveis_consolidado.xlsx"
ARQUIVO_LUOS = "LUOS_base_revisada.xlsx"

# Decodificação dos códigos da base cartográfica (confirmada contra a triagem PPR).
FORMA_IMOVEL = {1: "Regular", 2: "Semirregular", 3: "Irregular"}


# ----------------------------------------------------------------------------
# Formatação
# ----------------------------------------------------------------------------
def br_num(v, dec=0, prefixo="", sufixo=""):
    """Número no padrão brasileiro (1.234.567,89). Vazio vira travessão."""
    if v is None or pd.isna(v):
        return "—"
    s = f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefixo}{s}{sufixo}"


def br_data(v):
    if v is None or pd.isna(v):
        return "—"
    return pd.to_datetime(v).strftime("%d/%m/%Y")


def txt(v, limite=None):
    if v is None or pd.isna(v) or str(v).strip() == "":
        return "—"
    s = " ".join(str(v).split())
    if limite and len(s) > limite:
        s = s[: limite - 1].rstrip() + "…"
    return s


def tabela_html(pares, largura_rotulo="38%"):
    """Tabela de duas colunas à prova de conteúdo.

    A versão anterior do painel montava estas tabelas em Markdown por f-string.
    Como 'Anotações' e 'Observação' da TB55 contêm quebras de linha e o caractere
    '|', a tabela quebrava no meio e o texto vazava para fora da célula. Aqui o
    conteúdo é escapado e as quebras viram <br>, então qualquer texto renderiza.
    """
    linhas = []
    for rotulo, valor in pares:
        v = "—" if valor is None else str(valor)
        v = html.escape(v).replace("\n", "<br>")
        linhas.append(
            f"<tr><th style='text-align:left;vertical-align:top;padding:6px 10px;"
            f"width:{largura_rotulo};color:{CINZA};font-weight:600;"
            f"border-bottom:1px solid {CINZA_CLARO}'>{html.escape(str(rotulo))}</th>"
            f"<td style='vertical-align:top;padding:6px 10px;"
            f"border-bottom:1px solid {CINZA_CLARO}'>{v}</td></tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"
        + "".join(linhas)
        + "</table>"
    )


def selo(texto, cor=VERDE, fundo=VERDE_CLARO):
    return (
        f"<span style='background:{fundo};color:{cor};padding:2px 9px;"
        f"border-radius:10px;font-size:0.78rem;font-weight:600;"
        f"white-space:nowrap'>{html.escape(str(texto))}</span>"
    )


def titulo_secao(texto, descricao=None):
    d = (
        f"<p style='margin:2px 0 0;color:{CINZA};font-size:0.86rem'>{html.escape(descricao)}</p>"
        if descricao
        else ""
    )
    st.markdown(
        f"<div style='border-left:4px solid {VERDE};padding-left:12px;margin:6px 0 14px'>"
        f"<h3 style='margin:0;color:{GRAFITE};font-size:1.12rem'>{html.escape(texto)}</h3>{d}</div>",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Carga
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando a carteira...")
def carregar_dados(_versao_arquivo):
    """_versao_arquivo (mtime do xlsx) renova o cache quando a planilha é trocada."""
    # Números de processo são identificadores, não grandezas: sem dtype=str o
    # pandas os converte para float64 e destrói zeros à esquerda e dígitos finais.
    cons = pd.read_excel(
        ARQUIVO,
        sheet_name="Consolidado",
        dtype={"TB55_PROCESSOS": str, "TB55_PROCESSOS_ADM": str, "TB55_PROCESSO_CD": str},
    )
    obs = pd.read_excel(ARQUIVO, sheet_name="TB55_Observacoes")
    proc = pd.read_excel(
        ARQUIVO,
        sheet_name="TB55_Processos",
        dtype={"NUM_PROCESSO": str, "NUM_PROCESSO_ADM": str},
    )
    ali = pd.read_excel(ARQUIVO, sheet_name="TB55_Alienacoes")
    try:
        vinc = pd.read_excel(ARQUIVO, sheet_name="LUOS_Vinculacao")
    except ValueError:
        vinc = pd.DataFrame()

    cons = derivar(cons)
    for c in ("TB55_DT_REGISTRO", "TB55_DT_ULT_OBSERVACAO", "TB55_DT_ULT_ALIENACAO"):
        cons[c] = pd.to_datetime(cons[c], errors="coerce")
    obs["DT_OBSERVACAO"] = pd.to_datetime(obs["DT_OBSERVACAO"], errors="coerce")
    ali["DT_OPERACAO"] = pd.to_datetime(ali["DT_OPERACAO"], errors="coerce")
    return cons, obs, proc, ali, vinc


def derivar(cons: pd.DataFrame) -> pd.DataFrame:
    """Campos derivados e renomeação semântica dos campos da base cartográfica.

    Auditoria de julho/2026 sobre a base (conferida contra a triagem PPR e contra
    a Justificativa Técnica do imóvel 841600) mostrou que três colunas da base
    cartográfica não significam o que o nome sugere:

      AREA_MAX   -> área máxima de CONSTRUÇÃO (potencial construtivo), não a área
                    do terreno. Para o 841600 vale 122.663,805 m², exatamente o
                    valor do quadro urbanístico da Justificativa Técnica.
      AREA_CALCU -> coeficiente de aproveitamento. É idêntico a PPR_CA nos 108
                    imóveis vistoriados e satisfaz Shape__Are x CA = AREA_MAX.
      OCUPACAO   -> taxa máxima de ocupação em %, não a situação de ocupação.
      PERCENTUAL -> repetição de AREA_MAX, não um percentual.

    A área de terreno de fato é Shape__Are (polígono do GIS), como já registrava
    a aba Leia-me ao descrever a vinculação com a LUOS.
    """
    c = cons.copy()
    c["AREA_TERRENO"] = pd.to_numeric(c["Shape__Are"], errors="coerce")
    c["POT_CONSTRUTIVO"] = pd.to_numeric(c["AREA_MAX"], errors="coerce")
    c["CA_BASE"] = pd.to_numeric(c["AREA_CALCU"], errors="coerce")
    c["TX_OCUP_BASE"] = pd.to_numeric(c["OCUPACAO"], errors="coerce")
    c["PROJECAO_MAX"] = c["AREA_TERRENO"] * c["TX_OCUP_BASE"] / 100.0
    c["FORMA_DESC"] = c["FORMA_IMOV"].map(FORMA_IMOVEL)

    # Afastamentos misturam número e texto ("5,00 (bilateral)"); como texto a
    # tabela serializa sem aviso e o conteúdo original é preservado.
    for col in ("LUOS_AFAST_FRENTE", "LUOS_AFAST_FUNDO", "LUOS_AFAST_LATERAL"):
        if col in c.columns:
            c[col] = c[col].astype("string").str.strip()

    # Índice de busca por processo. Os números convivem em três formatos na
    # fonte — CNJ sem pontuação (07007102620188070018), SEI com pontuação
    # (111.3345/1987) e citações de SEI no meio das anotações
    # ("lançado no SEI 00111-00009290/2019-63"). Guardar tudo reduzido a
    # dígitos faz a busca funcionar com ou sem a pontuação digitada.
    partes = []
    for col in ("TB55_PROCESSOS", "TB55_PROCESSOS_ADM", "TB55_PROCESSO_CD"):
        if col in c.columns:
            partes.append(c[col].astype("string").fillna(""))
    anot = c["TB55_ANOTACOES_PROCESSO"].astype("string").fillna("") if \
        "TB55_ANOTACOES_PROCESSO" in c.columns else pd.Series("", index=c.index)
    # Das anotações interessam apenas as sequências com cara de processo.
    partes.append(anot.map(lambda t: " ".join(re.findall(r"\d[\d.\-/]{5,}\d", str(t)))))
    bruto = partes[0]
    for p in partes[1:]:
        bruto = bruto + " " + p
    c["BUSCA_PROC"] = bruto.map(lambda t: re.sub(r"\D", "", str(t)))

    # Situação vigente (compatibilidade com planilhas antigas sem a coluna).
    if "SITUACAO_VIGENTE" not in c.columns:
        ppr = c["PPR_Situação"].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
        base = c["SITUACAO"].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
        c["SITUACAO_VIGENTE"] = ppr.fillna(base)
        fonte = pd.Series("Sem informação", index=c.index)
        fonte[base.notna()] = "Base cartográfica"
        fonte[ppr.notna()] = "Triagem PPR"
        c["SITUACAO_FONTE"] = fonte
    c["SITUACAO_VIGENTE"] = (
        c["SITUACAO_VIGENTE"].astype("string").str.strip().fillna("SEM INFORMAÇÃO")
    )

    # Divergência entre a vistoria em campo e a base cartográfica: quando existe,
    # a ficha e o relatório precisam mostrar as duas leituras, não só a vigente.
    b = c["SITUACAO"].astype("string").str.strip()
    p = c["PPR_Situação"].astype("string").str.strip()
    c["SITUACAO_DIVERGE"] = (b.notna() & p.notna() & (b != p)).fillna(False)

    # Sinalizadores de qualidade usados na aba Visão geral.
    c["SEM_AREA"] = c["AREA_TERRENO"].isna() | (c["AREA_TERRENO"] <= 0)
    c["SEM_POTENCIAL"] = c["POT_CONSTRUTIVO"].isna() | (c["POT_CONSTRUTIVO"] <= 0)
    c["TEM_AVALIACAO"] = c["TB55_VL_AVALIACAO_RECENTE"].notna()
    return c


@st.cache_data(show_spinner="Carregando a base LUOS...")
def carregar_luos(_versao_arquivo):
    """Base de parâmetros urbanísticos revisada (910 linhas) e o log da revisão."""
    par = pd.read_excel(ARQUIVO_LUOS, sheet_name="Consolidado LUOS")
    try:
        log = pd.read_excel(ARQUIVO_LUOS, sheet_name="Log de alterações")
    except ValueError:
        log = pd.DataFrame()

    par = par.rename(columns={"Região Administrativa": "RA"})
    par["TX PERM num"] = pd.to_numeric(par["TX PERM num"], errors="coerce")
    par["TX OCUP (%)"] = pd.to_numeric(par["TX OCUP (%)"], errors="coerce")
    par["FAIXA_TEXTO"] = par.apply(
        lambda r: f"{br_num(r['FAIXA ÁREA mínima'])} a {br_num(r['FAIXA ÁREA máxima'])} m²", axis=1
    )
    # As taxas vêm como fração (0,6 = 60%) apesar do "%" no nome da coluna, e a
    # permeabilidade mistura número com texto ("Não exigido"). Colunas próprias
    # de exibição evitam a leitura errada de "0,60%" na tela.
    par["TX_OCUP_TXT"] = par["TX OCUP (%)"].map(
        lambda v: br_num(v * 100, 0, sufixo="%") if pd.notna(v) else "—"
    )
    par["TX_PERM_TXT"] = [
        br_num(n * 100, 0, sufixo="%") if pd.notna(n) else (str(b).strip() if pd.notna(b) else "—")
        for n, b in zip(par["TX PERM num"], par["TX PERM (%)"])
    ]
    # Colunas de tipo misto (número + texto) travam a serialização em Arrow;
    # padronizar como texto elimina o aviso e mantém o conteúdo original.
    for col in ("TX PERM (%)", "Afastamento Frente", "Afastamento Fundo", "Afastamento Lateral",
                "MARQUISE", "GALERIA", "COTA SOLEIRA", "SUBSOLO", "Notas", "UOS"):
        if col in par.columns:
            par[col] = par[col].astype("string").str.strip()
    # Marquise/galeria vêm com e sem acento na fonte; unifica para poder filtrar.
    for col in ("MARQUISE", "GALERIA"):
        par[col] = par[col].replace({"Obrigatoria": "Obrigatória"})

    if not log.empty:
        log["PENDENCIA"] = log["Motivo"].astype(str).str.startswith("conferir")
        for col in ("Antes", "Depois", "Coluna", "Motivo", "RA"):
            log[col] = log[col].astype("string").str.strip()
    return par, log


def versao_arquivos():
    """mtime dos dois arquivos, para invalidar o cache quando forem substituídos."""
    v1 = os.path.getmtime(ARQUIVO) if os.path.exists(ARQUIVO) else 0
    v2 = os.path.getmtime(ARQUIVO_LUOS) if os.path.exists(ARQUIVO_LUOS) else 0
    return v1, v2


def parametros_do_imovel(im, luos):
    """Quadro urbanístico do imóvel e a fonte de onde cada número veio.

    Prioriza a linha da LUOS quando a vinculação foi confirmada; caso contrário
    usa o coeficiente e a taxa de ocupação registrados na base cartográfica, que
    é a norma efetivamente aplicável aos lotes regidos por NGB/PPCUB/PR.
    """
    area = im.get("AREA_TERRENO")
    vinculado = str(im.get("LUOS_MATCH_STATUS", "")) == "Vinculado"

    if vinculado:
        cfa_b = im.get("LUOS_CFA_BASICO")
        cfa_m = im.get("LUOS_CFA_MAXIMO")
        tx_ocup = im.get("LUOS_TX_OCUP")
        tx_perm = im.get("LUOS_TX_PERM")
        alt = im.get("LUOS_ALT_MAX")
        fonte = f"Base LUOS revisada — código {txt(im.get('LUOS_CODIGO'))}"
    else:
        cfa_b = None
        cfa_m = im.get("CA_BASE")
        tx_ocup = (im.get("TX_OCUP_BASE") or 0) / 100.0 if pd.notna(im.get("TX_OCUP_BASE")) else None
        tx_perm = None
        alt = None
        fonte = f"Base cartográfica — norma {txt(im.get('PLANTA_DEC'))}"

    def mult(fator):
        if area is None or pd.isna(area) or fator is None or pd.isna(fator):
            return None
        return float(area) * float(fator)

    return {
        "fonte": fonte,
        "vinculado_luos": vinculado,
        "area_terreno": area,
        "cfa_basico": cfa_b,
        "cfa_maximo": cfa_m,
        "tx_ocup": tx_ocup,
        "tx_perm": tx_perm,
        "alt_max": alt,
        "area_basica": mult(cfa_b),
        "area_maxima": im.get("POT_CONSTRUTIVO") if not vinculado else mult(cfa_m),
        "projecao_maxima": mult(tx_ocup),
        "permeavel_minima": mult(tx_perm),
    }
