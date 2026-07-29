# -*- coding: utf-8 -*-
"""
Painel de Consulta de Imóveis — carteira consolidada (base 125 + PPR + TB55 + LUOS).

Fontes: Imoveis_consolidado.xlsx e LUOS_base_revisada.xlsx.
Execução: streamlit run app.py
"""
import html
import io
import re

import pandas as pd
import plotly.express as px
import streamlit as st

import relatorio as rel
from nucleo import (
    AZUL,
    AZUL_CLARO,
    CINZA,
    COR_SITUACAO,
    DOURADO,
    DOURADO_CLARO,
    GRAFITE,
    SEQUENCIA,
    VERDE,
    VERDE_CLARO,
    br_data,
    br_num,
    carregar_dados,
    carregar_luos,
    parametros_do_imovel,
    selo,
    tabela_html,
    titulo_secao,
    txt,
    versao_arquivos,
)

st.set_page_config(
    page_title="Consulta de Imóveis · Terracap",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ajustes finos sobre o tema: as abas ganham a linha institucional e as métricas
# perdem o peso excessivo do padrão, que competia com os títulos.
st.markdown(
    f"""
    <style>
      .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid #D8DEE3; }}
      .stTabs [data-baseweb="tab"] {{ padding: 8px 16px; font-weight: 600; }}
      .stTabs [aria-selected="true"] {{ color: {VERDE}; border-bottom: 3px solid {VERDE}; }}
      div[data-testid="stMetricValue"] {{ font-size: 1.5rem; color: {GRAFITE}; }}
      div[data-testid="stMetricLabel"] {{ color: {CINZA}; }}
      h1, h2, h3 {{ color: {GRAFITE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

v_cons, v_luos = versao_arquivos()
cons, obs, proc, ali, vinc = carregar_dados(v_cons)
luos, luos_log = carregar_luos(v_luos)

ESSENCIAIS = ["CD_IMOVEL", "ENDERECO", "REGADMIN", "AREA_MAX", "Shape__Are", "SITUACAO",
              "EM_PPR", "EM_TB55", "PPR_Situação", "PPR_Responsável",
              "TB55_VL_AVALIACAO_RECENTE", "TB55_QT_ALIENACOES"]
faltando = [c for c in ESSENCIAIS if c not in cons.columns]
if faltando:
    st.error(
        "O arquivo Imoveis_consolidado.xlsx carregado não tem as colunas: "
        + ", ".join(faltando)
        + ". Substitua-o pela versão mais recente gerada pela rotina de consolidação."
    )
    st.stop()

# ----------------------------------------------------------------------------
# Barra lateral — filtros
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"<div style='border-left:5px solid {VERDE};padding-left:12px'>"
        f"<h2 style='color:{VERDE};margin:0;font-size:1.25rem'>Consulta de Imóveis</h2>"
        f"<p style='margin:2px 0 0;color:{CINZA};font-size:0.82rem'>Terracap · carteira PPR 2026</p></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    busca = st.text_input(
        "Buscar por código, endereço ou processo",
        placeholder="Ex.: 841600, POLO LOGÍSTICO ou 00111-",
        help="Procura no código, nos endereços da base e da triagem PPR e nos números de processo da TB55.",
    )

    f_ra = st.multiselect("Região administrativa", sorted(cons["REGADMIN"].dropna().unique()))
    f_sit = st.multiselect(
        "Situação do lote",
        sorted(cons["SITUACAO_VIGENTE"].dropna().unique()),
        help="Prioriza a situação apurada na triagem PPR; sem triagem, vale a base cartográfica.",
    )
    f_resp = st.multiselect("Responsável (triagem PPR)", sorted(cons["PPR_Responsável"].dropna().unique()))
    f_norma = st.multiselect("Norma de uso e ocupação", sorted(cons["PLANTA_DEC"].dropna().unique()))

    f_dados = st.radio(
        "Cobertura de dados",
        ["Todos os imóveis", "Com triagem PPR e histórico TB55", "Sem correspondência (somente base)"],
        help="17 dos 125 imóveis constam apenas na lista base, sem triagem PPR nem histórico TB55.",
    )

    a_max = float(cons["AREA_TERRENO"].max())
    f_area = st.slider(
        "Área do terreno (m²)",
        min_value=0.0, max_value=a_max, value=(0.0, a_max), step=500.0, format="%.0f",
        help="Área do polígono cadastral (Shape__Are). Não confundir com o potencial construtivo.",
    )
    f_so_aval = st.checkbox("Somente imóveis com laudo de avaliação", value=False)

    st.divider()
    st.caption(
        "Base cartográfica · triagem PPR · TB55 (09/07/2026) · LUOS revisada. "
        "Junção pela chave CD_IMOVEL."
    )

# Aplicação dos filtros -------------------------------------------------------
df = cons.copy()

if busca.strip():
    b = busca.strip().lower()
    achou = (
        df["CD_IMOVEL"].astype(str).str.contains(b, na=False, regex=False)
        | df["ENDERECO"].astype(str).str.lower().str.contains(b, na=False, regex=False)
        | df["PPR_Endereço"].astype(str).str.lower().str.contains(b, na=False, regex=False)
    )
    # Números de processo são comparados só pelos dígitos, para que
    # "00111-00009290/2019-63" e "0011100009290201963" achem o mesmo imóvel.
    b_dig = re.sub(r"\D", "", b)
    if len(b_dig) >= 4:
        achou = achou | df["BUSCA_PROC"].str.contains(b_dig, na=False, regex=False)
    df = df[achou]
if f_ra:
    df = df[df["REGADMIN"].isin(f_ra)]
if f_sit:
    df = df[df["SITUACAO_VIGENTE"].isin(f_sit)]
if f_resp:
    df = df[df["PPR_Responsável"].isin(f_resp)]
if f_norma:
    df = df[df["PLANTA_DEC"].isin(f_norma)]
if f_dados == "Com triagem PPR e histórico TB55":
    df = df[df["EM_PPR"] == "Sim"]
elif f_dados == "Sem correspondência (somente base)":
    df = df[df["EM_PPR"] == "Não"]
if f_so_aval:
    df = df[df["TEM_AVALIACAO"]]
df = df[df["AREA_TERRENO"].between(f_area[0], f_area[1]) | df["AREA_TERRENO"].isna()]


def grafico(fig, altura=420):
    fig.update_layout(
        template="plotly_white",
        height=altura,
        margin=dict(l=10, r=10, t=54, b=10),
        font=dict(family="Source Sans Pro, Segoe UI, sans-serif", size=12, color=GRAFITE),
        title_font=dict(size=14, color=GRAFITE),
        xaxis_title="", yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")


ABAS = st.tabs([
    "Visão geral", "Explorar dados", "Ficha do imóvel",
    "Relatório PPR", "Base LUOS",
])
tab_geral, tab_tabela, tab_ficha, tab_relatorio, tab_luos = ABAS

# ============================================================================
# 1. Visão geral
# ============================================================================
with tab_geral:
    if df.empty:
        st.info("Nenhum imóvel atende aos filtros atuais. Ajuste os filtros na barra lateral.")
    else:
        titulo_secao(
            "Panorama da seleção",
            "Área de terreno e potencial construtivo são grandezas distintas e aparecem separadas.",
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Imóveis selecionados", br_num(len(df)), delta=f"de {len(cons)} na carteira",
                  delta_color="off")
        c2.metric("Área de terreno (m²)", br_num(df["AREA_TERRENO"].sum()))
        c3.metric("Potencial construtivo (m²)", br_num(df["POT_CONSTRUTIVO"].sum()))
        n_aval = int(df["TEM_AVALIACAO"].sum())
        c4.metric(
            "Avaliação registrada (R$)",
            br_num(df["TB55_VL_AVALIACAO_RECENTE"].sum()),
            delta=f"{n_aval} de {len(df)} imóveis com laudo",
            delta_color="off",
        )
        st.caption(
            "Potencial construtivo é a área máxima de construção (coluna AREA_MAX da base), "
            "resultado da área do terreno multiplicada pelo coeficiente de aproveitamento. "
            "A avaliação soma apenas os imóveis com laudo na TB55."
        )

        e1, e2 = st.columns(2)
        with e1:
            por_ra = df.groupby("REGADMIN").agg(
                Imóveis=("CD_IMOVEL", "size"), Área=("AREA_TERRENO", "sum")
            ).sort_values("Imóveis").reset_index()
            fig = px.bar(
                por_ra, x="Imóveis", y="REGADMIN", orientation="h",
                title="Imóveis por região administrativa", text="Imóveis",
                custom_data=["Área"], color_discrete_sequence=[VERDE],
            )
            fig.update_traces(
                hovertemplate="%{y}<br>%{x} imóveis<br>%{customdata[0]:,.0f} m² de terreno<extra></extra>"
            )
            grafico(fig, 460)
        with e2:
            por_sit = df["SITUACAO_VIGENTE"].value_counts().reset_index()
            por_sit.columns = ["Situação", "Imóveis"]
            fig = px.bar(
                por_sit, x="Situação", y="Imóveis", title="Situação dos lotes", text="Imóveis",
                color="Situação", color_discrete_map=COR_SITUACAO,
            )
            grafico(fig, 460)
            st.caption(
                "Verde: lote livre. Dourado: exige providência antes da destinação. "
                "Azul: uso de terceiro identificado."
            )

        e3, e4 = st.columns(2)
        with e3:
            top = df.dropna(subset=["TB55_VL_AVALIACAO_RECENTE"]).nlargest(10, "TB55_VL_AVALIACAO_RECENTE")
            if top.empty:
                st.info("Nenhum imóvel da seleção possui laudo de avaliação na TB55.")
            else:
                top = top.assign(rotulo=top["CD_IMOVEL"].astype(str) + " · " + top["REGADMIN"].fillna(""))
                fig = px.bar(
                    top.sort_values("TB55_VL_AVALIACAO_RECENTE"),
                    x="TB55_VL_AVALIACAO_RECENTE", y="rotulo", orientation="h",
                    title="Dez maiores avaliações (R$)", color_discrete_sequence=[AZUL],
                )
                grafico(fig, 460)
        with e4:
            base = df[df["AREA_TERRENO"] > 0]
            fig = px.scatter(
                base, x="AREA_TERRENO", y="POT_CONSTRUTIVO",
                color="SITUACAO_VIGENTE", color_discrete_map=COR_SITUACAO,
                hover_name="ENDERECO", custom_data=["CD_IMOVEL", "CA_BASE"],
                title="Terreno × potencial construtivo (m²)",
            )
            fig.update_traces(
                marker=dict(size=9, line=dict(width=0.5, color="white")),
                hovertemplate="%{hovertext}<br>Cadastro %{customdata[0]}<br>"
                              "Terreno %{x:,.0f} m²<br>Potencial %{y:,.0f} m²"
                              "<br>CA %{customdata[1]}<extra></extra>",
            )
            fig.update_layout(showlegend=True, legend_title_text="")
            grafico(fig, 460)
            st.caption("A inclinação de cada ponto em relação à origem é o coeficiente de aproveitamento.")

        titulo_secao("Cobertura e qualidade dos dados", "O que precisa de complemento antes da análise.")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Sem triagem PPR", br_num((df["EM_PPR"] == "Não").sum()))
        q2.metric("Sem laudo de avaliação", br_num((~df["TEM_AVALIACAO"]).sum()))
        q3.metric("Sem coeficiente na base", br_num(df["SEM_POTENCIAL"].sum()),
                  help="Coeficiente de aproveitamento zerado ou ausente: o potencial construtivo não pode ser calculado.")
        q4.metric("Situação divergente", br_num(df["SITUACAO_DIVERGE"].sum()),
                  help="A vistoria da triagem PPR encontrou situação diferente da registrada na base cartográfica.")

        if df["SITUACAO_DIVERGE"].any():
            with st.expander(
                f"Ver os {int(df['SITUACAO_DIVERGE'].sum())} lotes com divergência entre base e vistoria"
            ):
                st.dataframe(
                    df.loc[df["SITUACAO_DIVERGE"],
                           ["CD_IMOVEL", "ENDERECO", "REGADMIN", "SITUACAO", "PPR_Situação", "PPR_Responsável"]]
                    .rename(columns={"SITUACAO": "Base cartográfica", "PPR_Situação": "Vistoria PPR"}),
                    width="stretch", hide_index=True,
                    column_config={"CD_IMOVEL": st.column_config.NumberColumn("Cadastro", format="%d")},
                )

# ============================================================================
# 2. Explorar dados
# ============================================================================
with tab_tabela:
    titulo_secao("Tabela dinâmica", "Escolha um conjunto de colunas, ajuste e baixe a seleção.")
    CONJUNTOS = {
        "Visão essencial": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "AREA_TERRENO", "CA_BASE", "POT_CONSTRUTIVO",
            "SITUACAO_VIGENTE", "SITUACAO_FONTE", "PPR_Responsável",
            "TB55_VL_AVALIACAO_RECENTE", "TB55_QT_ALIENACOES",
        ],
        "Urbanístico": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "AREA_TERRENO", "CA_BASE", "POT_CONSTRUTIVO",
            "TX_OCUP_BASE", "PROJECAO_MAX", "PLANTA_DEC", "IMU_PLAN_L", "PPR_Destinacao",
            "FORMA_DESC", "POSICAO",
        ],
        "Base cartográfica": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "UNIDADE", "AREA_TERRENO", "CA_BASE",
            "POT_CONSTRUTIVO", "TX_OCUP_BASE", "FORMA_DESC", "POSICAO",
            "CONDICAO", "DESTINACAO", "IMU_PLAN_L", "PLANTA_DEC", "SITUACAO", "STATUS",
        ],
        "Triagem PPR": [
            "CD_IMOVEL", "PPR_Endereço", "PPR_Nome RA", "PPR_Area_imovel", "PPR_CA",
            "PPR_a_ser_const", "PPR_Ocupação_max", "PPR_Destinacao", "PPR_Proj_URB",
            "PPR__Legis_Norma_", "PPR_Situação", "PPR_obs:", "PPR_Responsável",
        ],
        "Cartório e histórico (TB55)": [
            "CD_IMOVEL", "ENDERECO", "TB55_VL_AVALIACAO_RECENTE", "TB55_CARTORIO",
            "TB55_DT_REGISTRO", "TB55_QT_OBSERVACOES", "TB55_DT_ULT_OBSERVACAO",
            "TB55_ULT_OBSERVACAO", "TB55_QT_PROCESSOS", "TB55_PROCESSOS",
            "TB55_QT_ALIENACOES", "TB55_ULT_ALIENACAO_MODALIDADE", "TB55_ULT_ALIENACAO_SITUACAO",
        ],
        "Parâmetros LUOS": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "LUOS_MATCH_STATUS", "LUOS_CODIGO",
            "LUOS_UOS_DETALHE", "LUOS_CFA_BASICO", "LUOS_CFA_MAXIMO", "LUOS_TX_OCUP",
            "LUOS_TX_PERM", "LUOS_ALT_MAX", "LUOS_AREA_LOTE_M2", "LUOS_CANDIDATOS",
        ],
        "Todas as colunas": list(cons.columns),
    }
    CONJUNTOS = {k: [c for c in v if c in cons.columns] for k, v in CONJUNTOS.items()}
    CONJUNTOS = {k: v for k, v in CONJUNTOS.items() if len(v) > 3}

    esc1, esc2 = st.columns([1, 2])
    conjunto = esc1.selectbox("Conjunto de colunas", list(CONJUNTOS.keys()))
    extras = esc2.multiselect(
        "Adicionar colunas ao conjunto",
        [c for c in cons.columns if c not in CONJUNTOS[conjunto]],
    )
    colunas = CONJUNTOS[conjunto] + extras

    ROTULOS = {
        "CD_IMOVEL": st.column_config.NumberColumn("Cadastro", format="%d"),
        "AREA_TERRENO": st.column_config.NumberColumn("Terreno (m²)", format="localized"),
        "POT_CONSTRUTIVO": st.column_config.NumberColumn("Potencial constr. (m²)", format="localized"),
        "PROJECAO_MAX": st.column_config.NumberColumn("Projeção máx. (m²)", format="localized"),
        "CA_BASE": st.column_config.NumberColumn("Coef. aproveitamento", format="%.2f"),
        "TX_OCUP_BASE": st.column_config.NumberColumn("Taxa de ocupação (%)", format="%.0f"),
        "FORMA_DESC": st.column_config.TextColumn("Forma do lote"),
        "SITUACAO_VIGENTE": st.column_config.TextColumn("Situação vigente"),
        "SITUACAO_FONTE": st.column_config.TextColumn("Fonte da situação"),
        "TB55_VL_AVALIACAO_RECENTE": st.column_config.NumberColumn("Avaliação (R$)", format="localized"),
        "TB55_DT_REGISTRO": st.column_config.DateColumn("Registro", format="DD/MM/YYYY"),
        "TB55_DT_ULT_OBSERVACAO": st.column_config.DateColumn("Últ. observação", format="DD/MM/YYYY"),
        "TB55_DT_ULT_ALIENACAO": st.column_config.DateColumn("Últ. alienação", format="DD/MM/YYYY"),
    }
    st.dataframe(
        df[colunas], width="stretch", height=520, hide_index=True,
        column_config={k: v for k, v in ROTULOS.items() if k in colunas},
    )
    st.caption(f"{len(df)} de {len(cons)} imóveis exibidos, conforme os filtros da barra lateral.")

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(
        "Baixar seleção (CSV)",
        df[colunas].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="imoveis_selecao.csv", mime="text/csv", width="stretch",
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df[colunas].to_excel(w, index=False, sheet_name="Selecao")
    d2.download_button(
        "Baixar seleção (Excel)", buf.getvalue(), file_name="imoveis_selecao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
    )

# ============================================================================
# 3. Ficha do imóvel
# ============================================================================
with tab_ficha:
    if df.empty:
        st.info("Nenhum imóvel atende aos filtros atuais. Ajuste os filtros na barra lateral.")
    else:
        opcoes = df.sort_values("CD_IMOVEL")
        rotulos = {int(r.CD_IMOVEL): f"{int(r.CD_IMOVEL)} — {txt(r.ENDERECO)}" for r in opcoes.itertuples()}
        anterior = st.session_state.get("imovel_atual")
        indice = list(rotulos).index(anterior) if anterior in rotulos else 0
        cod = st.selectbox(
            "Escolha o imóvel (a lista respeita os filtros da barra lateral)",
            options=list(rotulos.keys()), index=indice, format_func=lambda k: rotulos[k],
            key="sel_ficha",
        )
        st.session_state["imovel_atual"] = cod
        im = cons.loc[cons["CD_IMOVEL"] == cod].iloc[0]
        par = parametros_do_imovel(im, luos)

        selos = [selo(txt(im["SITUACAO_VIGENTE"]),
                      COR_SITUACAO.get(im["SITUACAO_VIGENTE"], CINZA), "#F1F4F6")]
        selos.append(selo(txt(im["CD_DS_COND"]), AZUL, AZUL_CLARO))
        selos.append(selo(txt(im["PLANTA_DEC"]), VERDE, VERDE_CLARO))
        if im["SITUACAO_DIVERGE"]:
            selos.append(selo("Situação divergente", "#8A6800", DOURADO_CLARO))
        if not im["TEM_AVALIACAO"]:
            selos.append(selo("Sem laudo de avaliação", "#8A6800", DOURADO_CLARO))

        st.markdown(
            f"<h3 style='color:{VERDE};margin-bottom:0'>{html.escape(txt(im['ENDERECO']))}</h3>"
            f"<p style='margin:2px 0 8px;color:{CINZA}'>{html.escape(txt(im['REGADMIN']))} · "
            f"Cadastro {int(im['CD_IMOVEL'])}</p>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px'>{''.join(selos)}</div>",
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Área do terreno (m²)", br_num(im["AREA_TERRENO"], 2))
        m2.metric("Potencial construtivo (m²)", br_num(im["POT_CONSTRUTIVO"], 2),
                  delta=f"CA {br_num(im['CA_BASE'], 2)}", delta_color="off")
        m3.metric("Avaliação recente (R$)", br_num(im["TB55_VL_AVALIACAO_RECENTE"], 2))
        m4.metric("Alienações no histórico", br_num(im["TB55_QT_ALIENACOES"]))

        if im["EM_PPR"] == "Não":
            st.warning("Este imóvel consta apenas na lista base: não há triagem PPR nem histórico TB55 vinculados.")
        if im["SITUACAO_DIVERGE"]:
            st.warning(
                f"A base cartográfica registra **{txt(im['SITUACAO'])}** e a vistoria da triagem PPR "
                f"apurou **{txt(im['PPR_Situação'])}**. Prevalece a informação de campo."
            )

        b1, b2 = st.columns(2)
        with b1:
            with st.container(border=True):
                st.markdown("**Base cartográfica**")
                st.markdown(tabela_html([
                    ("Condição", txt(im["CD_DS_COND"])),
                    ("Status do cadastro", txt(im["STATUS"])),
                    ("Situação na base", txt(im["SITUACAO"])),
                    ("Área do terreno", br_num(im["AREA_TERRENO"], 2, sufixo=" m²")),
                    ("Coeficiente de aproveitamento", br_num(im["CA_BASE"], 2)),
                    ("Taxa máxima de ocupação", br_num(im["TX_OCUP_BASE"], 0, sufixo="%")),
                    ("Forma · posição", f"{txt(im['FORMA_DESC'])} · {txt(im['POSICAO'])}"),
                    ("Projeto · norma", f"{txt(im['IMU_PLAN_L'])} · {txt(im['PLANTA_DEC'])}"),
                    ("Norma de uso", txt(im["DESTINACAO"], 240)),
                ]), unsafe_allow_html=True)
        with b2:
            with st.container(border=True):
                st.markdown("**Triagem PPR**")
                if im["EM_PPR"] == "Sim":
                    st.markdown(tabela_html([
                        ("Responsável", txt(im["PPR_Responsável"])),
                        ("Área do imóvel", br_num(im["PPR_Area_imovel"], 2, sufixo=" m²")),
                        ("Coeficiente de aproveitamento", br_num(im["PPR_CA"], 2)),
                        ("Potencial construtivo", br_num(im["PPR_a_ser_const"], 2, sufixo=" m²")),
                        ("Ocupação máxima", br_num(im["PPR_Ocupação_max"], 0, sufixo="%")),
                        ("Destinação", txt(im["PPR_Destinacao"])),
                        ("Projeto · norma", f"{txt(im['PPR_Proj_URB'])} · {txt(im['PPR__Legis_Norma_'])}"),
                        ("Situação na vistoria", txt(im["PPR_Situação"])),
                        ("Observação da vistoria", txt(im["PPR_obs:"])),
                    ]), unsafe_allow_html=True)
                else:
                    st.write("Sem registro na planilha de triagem PPR.")

        with st.container(border=True):
            st.markdown("**Quadro urbanístico aplicável**")
            pct = lambda v: br_num(v * 100, 0, sufixo="%") if v is not None and pd.notna(v) else "—"
            st.markdown(tabela_html([
                ("Coeficiente básico", br_num(par["cfa_basico"], 2)),
                ("Coeficiente máximo", br_num(par["cfa_maximo"], 2)),
                ("Área máxima de construção", br_num(par["area_maxima"], 2, sufixo=" m²")),
                ("Taxa máxima de ocupação", pct(par["tx_ocup"])),
                ("Projeção máxima das edificações", br_num(par["projecao_maxima"], 2, sufixo=" m²")),
                ("Permeabilidade mínima", pct(par["tx_perm"])),
                ("Altura máxima", br_num(par["alt_max"], 2, sufixo=" m")),
                ("Fonte dos parâmetros", par["fonte"]),
            ]), unsafe_allow_html=True)
            if not par["vinculado_luos"]:
                st.caption(
                    f"Vinculação à base LUOS: {txt(im['LUOS_MATCH_STATUS'])}. "
                    "Permeabilidade e altura máxima não constam da base cartográfica."
                )

        with st.container(border=True):
            st.markdown("**Registro cartorial e processos (TB55)**")
            if im["EM_TB55"] == "Sim":
                st.markdown(tabela_html([
                    ("Cartório", txt(im["TB55_CARTORIO"])),
                    ("Data do registro", br_data(im["TB55_DT_REGISTRO"])),
                    ("Averbação · folha · livro",
                     f"{txt(im['TB55_REG_AVERBACAO'])} · {txt(im['TB55_REG_FOLHA'])} · {txt(im['TB55_REG_LIVRO'])}"),
                    (f"Processos ({br_num(im['TB55_QT_PROCESSOS'])})", txt(im["TB55_PROCESSOS"])),
                    ("Processos administrativos", txt(im["TB55_PROCESSOS_ADM"])),
                    ("Anotações", txt(im["TB55_ANOTACOES_PROCESSO"], 600)),
                ]), unsafe_allow_html=True)
            else:
                st.write("Sem registro na TB55.")

        h1, h2 = st.columns([3, 2])
        with h1:
            with st.container(border=True):
                o = obs[obs["CD_IMOVEL"] == cod].sort_values("DT_OBSERVACAO", ascending=False)
                st.markdown(f"**Linha do tempo de observações** ({len(o)})")
                if o.empty:
                    st.write("Nenhuma observação registrada para este imóvel.")
                for r in o.itertuples():
                    st.markdown(
                        f"<div style='border-left:3px solid {VERDE};padding:2px 10px;margin:6px 0'>"
                        f"<b style='color:{AZUL}'>{br_data(r.DT_OBSERVACAO)}</b><br>"
                        f"{html.escape(txt(r.OBSERVACAO))}</div>",
                        unsafe_allow_html=True,
                    )
        with h2:
            with st.container(border=True):
                a = ali[ali["CD_IMOVEL"] == cod].sort_values("DT_OPERACAO", ascending=False)
                st.markdown(f"**Alienações** ({len(a)})")
                if a.empty:
                    st.write("Nenhuma alienação registrada para este imóvel.")
                else:
                    st.dataframe(
                        a[["ALIENACAO_CD", "DT_OPERACAO", "MODALIDADE", "SITUACAO"]],
                        hide_index=True, width="stretch",
                        column_config={
                            "ALIENACAO_CD": st.column_config.NumberColumn("Código", format="%d"),
                            "DT_OPERACAO": st.column_config.DateColumn("Operação", format="DD/MM/YYYY"),
                            "MODALIDADE": "Modalidade", "SITUACAO": "Situação",
                        },
                    )
        st.info(
            "Para transformar esta ficha em Justificativa Técnica, abra a aba **Relatório PPR** — "
            "o imóvel selecionado aqui já vai carregado."
        )

# ============================================================================
# 4. Relatório PPR
# ============================================================================
with tab_relatorio:
    if df.empty:
        st.info("Nenhum imóvel atende aos filtros atuais. Ajuste os filtros na barra lateral.")
    else:
        titulo_secao(
            "Justificativa Técnica Preliminar",
            "Estrutura de 11 seções do modelo PPR 2026. Os quadros vêm da carteira; "
            "os textos são rascunhos para você confirmar ou reescrever.",
        )
        opcoes = df.sort_values("CD_IMOVEL")
        rotulos = {int(r.CD_IMOVEL): f"{int(r.CD_IMOVEL)} — {txt(r.ENDERECO)}" for r in opcoes.itertuples()}
        atual = st.session_state.get("imovel_atual")
        indice = list(rotulos).index(atual) if atual in rotulos else 0

        cab1, cab2 = st.columns([3, 2])
        cod = cab1.selectbox(
            "Imóvel", options=list(rotulos.keys()), index=indice,
            format_func=lambda k: rotulos[k], key="sel_relatorio",
        )
        autor = cab2.text_input("Responsável pela análise", value="", placeholder="Nome de quem assina")
        st.session_state["imovel_atual"] = cod

        im = cons.loc[cons["CD_IMOVEL"] == cod].iloc[0]
        par = parametros_do_imovel(im, luos)
        auto = rel.rascunhos(im, cons, obs, ali, par)
        viz, criterio = rel.vizinhos(im, cons)

        quadros = {
            "identificacao": rel.tabela_identificacao(im),
            "uso": rel.tabela_parametros(par),
            "mercado": rel.tabela_vizinhos(viz),
            "avaliacao": [],
            "encaminhamentos": [],
        }
        quadros = {k: v for k, v in quadros.items() if v}

        chaves = [s[0] for s in rel.SECOES]
        for c in chaves:
            st.session_state.setdefault(f"rel_{cod}_{c}", auto.get(c, ""))

        acao1, acao2 = st.columns([1, 4])
        if acao1.button("Restaurar rascunhos", width="stretch",
                        help="Descarta as edições deste imóvel e recarrega o texto gerado a partir dos dados."):
            for c in chaves:
                st.session_state[f"rel_{cod}_{c}"] = auto.get(c, "")
            st.rerun()
        acao2.caption(
            "As edições ficam guardadas por imóvel enquanto a aba do navegador estiver aberta. "
            "Baixe o documento para preservá-las."
        )

        sugeridos = rel.encaminhamentos_sugeridos(im, par)
        marcados = []

        for chave, num, titulo, tem_quadro, ajuda in rel.SECOES:
            with st.expander(f"{num}. {titulo}", expanded=chave in ("identificacao", "uso")):
                if tem_quadro and chave in quadros:
                    q = quadros[chave]
                    if isinstance(q[0], list) and len(q[0]) > 2:
                        st.dataframe(pd.DataFrame(q[1:], columns=q[0]), hide_index=True, width="stretch")
                        st.caption(f"Comparáveis da carteira selecionados por {criterio}.")
                    else:
                        st.markdown(tabela_html(q), unsafe_allow_html=True)
                if chave == "encaminhamentos":
                    st.markdown("**Encaminhamentos propostos**")
                    for i, e in enumerate(sugeridos):
                        if st.checkbox(e, value=True, key=f"enc_{cod}_{i}"):
                            marcados.append(e)
                st.text_area(
                    ajuda, key=f"rel_{cod}_{chave}", height=200, label_visibility="visible",
                )

        textos = {c: st.session_state.get(f"rel_{cod}_{c}", "") for c in chaves}
        md = rel.montar_markdown(im, textos, quadros, marcados, autor)

        st.divider()
        st.markdown("**Gerar documento**")
        g1, g2, g3 = st.columns([1, 1, 3])
        nome = f"PPR_2026_{int(im['CD_IMOVEL'])}"
        try:
            docx = rel.montar_docx(im, textos, quadros, marcados, autor)
            g1.download_button(
                "Baixar em Word (.docx)", docx, file_name=f"{nome}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch", type="primary",
            )
        except ImportError:
            g1.warning("Instale python-docx para exportar em Word: pip install python-docx")
        g2.download_button(
            "Baixar em Markdown (.md)", md.encode("utf-8"), file_name=f"{nome}.md",
            mime="text/markdown", width="stretch",
        )
        g3.caption(
            "O documento sai com a estrutura, a numeração e a identidade visual do modelo aprovado. "
            "Confira os campos automáticos antes de tramitar."
        )
        with st.expander("Pré-visualizar o documento"):
            st.markdown(md)

# ============================================================================
# 5. Base LUOS
# ============================================================================
with tab_luos:
    titulo_secao(
        "Base LUOS revisada",
        f"{len(luos)} faixas de parâmetros urbanísticos em {luos['RA'].nunique()} regiões administrativas, "
        f"com o registro das {len(luos_log)} correções da revisão.",
    )
    sub_consulta, sub_simulador, sub_log = st.tabs(
        ["Consulta de parâmetros", "Enquadrar um lote", "Log da revisão"]
    )

    # --- 5.1 Consulta ------------------------------------------------------
    with sub_consulta:
        f1, f2, f3 = st.columns(3)
        l_ra = f1.multiselect("Região administrativa", sorted(luos["RA"].dropna().unique()), key="luos_ra")
        l_grupo = f2.multiselect("Grupo de uso", sorted(luos["Grupo de Uso"].dropna().unique()), key="luos_gr")
        l_cat = f3.multiselect("Categoria UOS", sorted(luos["Categoria UOS"].dropna().unique()), key="luos_cat")
        f4, f5 = st.columns(2)
        ordem = ["≤10m", "10–15m", "15–20m", "20–30m", ">30m"]
        l_alt = f4.multiselect(
            "Faixa de altura", [o for o in ordem if o in set(luos["Faixa de Altura"].dropna())], key="luos_alt"
        )
        cfa_max = float(luos["CFA Máximo"].max())
        l_cfa = f5.slider("Coeficiente máximo de aproveitamento", 0.0, cfa_max, (0.0, cfa_max), 0.1)

        lf = luos.copy()
        if l_ra:
            lf = lf[lf["RA"].isin(l_ra)]
        if l_grupo:
            lf = lf[lf["Grupo de Uso"].isin(l_grupo)]
        if l_cat:
            lf = lf[lf["Categoria UOS"].isin(l_cat)]
        if l_alt:
            lf = lf[lf["Faixa de Altura"].isin(l_alt)]
        lf = lf[lf["CFA Máximo"].between(l_cfa[0], l_cfa[1])]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Faixas na seleção", br_num(len(lf)))
        k2.metric("Regiões administrativas", br_num(lf["RA"].nunique()))
        k3.metric("Coef. máximo mediano", br_num(lf["CFA Máximo"].median(), 2))
        k4.metric("Altura máxima mediana", br_num(lf["ALT MAX"].median(), 1, sufixo=" m"))

        COLS = ["CÓDIGO", "RA", "UOS", "FAIXA_TEXTO", "CFA Básico", "CFA Máximo", "TX_OCUP_TXT",
                "TX_PERM_TXT", "ALT MAX", "Nº PAV", "Afastamento Frente", "Afastamento Fundo",
                "Afastamento Lateral", "MARQUISE", "GALERIA", "COTA SOLEIRA", "SUBSOLO",
                "Grupo de Uso", "Notas"]
        st.dataframe(
            lf[COLS], width="stretch", height=430, hide_index=True,
            column_config={
                "CÓDIGO": st.column_config.NumberColumn("Código", format="%d"),
                "FAIXA_TEXTO": st.column_config.TextColumn("Faixa de área do lote"),
                "CFA Básico": st.column_config.NumberColumn("CFA básico", format="%.2f"),
                "CFA Máximo": st.column_config.NumberColumn("CFA máximo", format="%.2f"),
                "TX_OCUP_TXT": st.column_config.TextColumn("Taxa de ocupação"),
                "TX_PERM_TXT": st.column_config.TextColumn("Permeabilidade mínima"),
                "ALT MAX": st.column_config.NumberColumn("Altura máx. (m)", format="%.1f"),
                "Nº PAV": st.column_config.NumberColumn("Pavimentos", format="%.0f"),
                "Notas": st.column_config.TextColumn("Notas", width="medium"),
            },
        )
        st.caption(
            "As taxas da fonte vêm em fração (0,60 = 60%) e a permeabilidade mistura número com "
            "texto; ambas são exibidas aqui já convertidas."
        )
        st.download_button(
            "Baixar seleção (CSV)",
            lf[COLS].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="luos_selecao.csv", mime="text/csv",
        )

        g1, g2 = st.columns(2)
        with g1:
            por_grupo = lf["Grupo de Uso"].value_counts().reset_index()
            por_grupo.columns = ["Grupo", "Faixas"]
            fig = px.bar(
                por_grupo.sort_values("Faixas"), x="Faixas", y="Grupo", orientation="h",
                title="Faixas por grupo de uso", text="Faixas",
                color="Grupo", color_discrete_sequence=SEQUENCIA,
            )
            grafico(fig, 400)
        with g2:
            base_alt = lf.dropna(subset=["Faixa de Altura"])
            if base_alt.empty:
                st.info("Sem dados de altura na seleção.")
            else:
                por_alt = base_alt.groupby(["Faixa de Altura", "Ordem Faixa"]).size().reset_index(name="Faixas")
                fig = px.bar(
                    por_alt.sort_values("Ordem Faixa"), x="Faixa de Altura", y="Faixas",
                    title="Distribuição por faixa de altura", text="Faixas",
                    color_discrete_sequence=[AZUL],
                )
                grafico(fig, 400)

        with st.expander("Comparar o coeficiente máximo entre regiões administrativas"):
            comp = (
                lf.groupby("RA")["CFA Máximo"].agg(["median", "max", "size"])
                .reset_index().sort_values("median")
            )
            comp.columns = ["RA", "Mediana", "Máximo", "Faixas"]
            fig = px.bar(
                comp, x="Mediana", y="RA", orientation="h", title="Coeficiente máximo mediano por RA",
                custom_data=["Máximo", "Faixas"], color_discrete_sequence=[VERDE],
            )
            fig.update_traces(
                hovertemplate="%{y}<br>Mediana %{x:.2f}<br>Máximo %{customdata[0]:.2f}"
                              "<br>%{customdata[1]} faixas<extra></extra>"
            )
            grafico(fig, max(340, 22 * len(comp)))

    # --- 5.2 Enquadramento -------------------------------------------------
    with sub_simulador:
        st.markdown(
            "Informe a região, a unidade de uso e a área do terreno para localizar a faixa "
            "aplicável e calcular o quadro urbanístico do lote."
        )
        origem = st.radio(
            "Ponto de partida", ["Informar manualmente", "Usar um imóvel da carteira"],
            horizontal=True, key="luos_origem",
        )

        area_lote, ra_sel, uos_sel = 5000.0, None, None
        if origem == "Usar um imóvel da carteira" and not df.empty:
            rot = {int(r.CD_IMOVEL): f"{int(r.CD_IMOVEL)} — {txt(r.ENDERECO)}"
                   for r in df.sort_values("CD_IMOVEL").itertuples()}
            escolha = st.selectbox("Imóvel", list(rot.keys()), format_func=lambda k: rot[k], key="luos_imovel")
            imv = cons.loc[cons["CD_IMOVEL"] == escolha].iloc[0]
            area_lote = float(imv["AREA_TERRENO"] or 0)
            # A RA da carteira vem com sufixo ("CEILANDIA/RA-IX"); a LUOS usa o nome simples.
            nome_ra = str(imv["REGADMIN"]).split("/")[0].strip().lower()
            for r in sorted(luos["RA"].dropna().unique()):
                if r.lower().replace("ã", "a").replace("â", "a").replace("á", "a") == \
                   nome_ra.replace("ã", "a").replace("â", "a").replace("á", "a"):
                    ra_sel = r
                    break
            uos_bruto = str(imv.get("PPR_Destinacao") or "").replace("UOS", "").strip()
            uos_sel = uos_bruto or None
            st.caption(
                f"Terreno de {br_num(area_lote, 2)} m² · RA {txt(imv['REGADMIN'])} · "
                f"destinação {txt(imv.get('PPR_Destinacao'))} · norma {txt(imv['PLANTA_DEC'])}"
            )
            if str(imv["PLANTA_DEC"]) != "LUOS":
                st.warning(
                    f"A norma vigente deste lote é {txt(imv['PLANTA_DEC'])}, não a LUOS. "
                    "O enquadramento abaixo serve como referência comparativa, não como parâmetro aplicável."
                )

        s1, s2, s3 = st.columns([2, 2, 1])
        ras = sorted(luos["RA"].dropna().unique())
        ra = s1.selectbox("Região administrativa", ras,
                          index=ras.index(ra_sel) if ra_sel in ras else 0, key="sim_ra")
        cats = sorted(luos.loc[luos["RA"] == ra, "Categoria UOS"].dropna().unique())
        idx_cat = 0
        if uos_sel:
            for i, c in enumerate(cats):
                if c.upper() == uos_sel.upper():
                    idx_cat = i
                    break
        cat = s2.selectbox("Categoria de uso e ocupação", cats, index=idx_cat, key="sim_cat")
        area = s3.number_input("Área do terreno (m²)", min_value=0.0, value=float(area_lote),
                               step=100.0, format="%.2f", key="sim_area")

        cand = luos[(luos["RA"] == ra) & (luos["Categoria UOS"] == cat)].sort_values("FAIXA ÁREA mínima")
        dentro = cand[(cand["FAIXA ÁREA mínima"] <= area) & (cand["FAIXA ÁREA máxima"] >= area)]

        if cand.empty:
            st.info("Não há faixas cadastradas para essa combinação de região e categoria.")
        elif dentro.empty:
            st.warning(
                f"A área de {br_num(area, 2)} m² está fora das faixas cadastradas para "
                f"{cat} em {ra}. Faixas disponíveis: "
                + "; ".join(cand["FAIXA_TEXTO"].tolist())
                + ". Nesses casos a base registra o lote como 'área fora das faixas' e o "
                "enquadramento precisa de decisão manual."
            )
        else:
            if len(dentro) > 1:
                st.warning(
                    f"{len(dentro)} faixas atendem a essa área — a fonte tem sobreposição nesse trecho. "
                    "Escolha a linha aplicável."
                )
                escolha_cod = st.selectbox(
                    "Código aplicável", dentro["CÓDIGO"].tolist(),
                    format_func=lambda c: f"{c} — {dentro.loc[dentro['CÓDIGO'] == c, 'UOS'].iloc[0]}",
                    key="sim_cod",
                )
                linha = dentro[dentro["CÓDIGO"] == escolha_cod].iloc[0]
            else:
                linha = dentro.iloc[0]

            cfa_b, cfa_m = linha["CFA Básico"], linha["CFA Máximo"]
            tx_ocup, tx_perm = linha["TX OCUP (%)"], linha["TX PERM num"]
            calc = lambda f: area * float(f) if pd.notna(f) else None
            pct = lambda v: br_num(v * 100, 0, sufixo="%") if pd.notna(v) else "—"

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Área básica de construção", br_num(calc(cfa_b), 2),
                      delta=f"CFA {br_num(cfa_b, 2)}", delta_color="off")
            r2.metric("Área máxima de construção", br_num(calc(cfa_m), 2),
                      delta=f"CFA {br_num(cfa_m, 2)}", delta_color="off")
            r3.metric("Projeção máxima", br_num(calc(tx_ocup), 2),
                      delta=f"Ocupação {pct(tx_ocup)}", delta_color="off")
            r4.metric("Área permeável mínima", br_num(calc(tx_perm), 2),
                      delta=f"Permeabilidade {pct(tx_perm)}", delta_color="off")

            q1, q2 = st.columns([3, 2])
            with q1:
                with st.container(border=True):
                    st.markdown(f"**Faixa aplicável — código {int(linha['CÓDIGO'])}**")
                    st.markdown(tabela_html([
                        ("Unidade de uso e ocupação", txt(linha["UOS"])),
                        ("Grupo de uso", txt(linha["Grupo de Uso"])),
                        ("Faixa de área do lote", txt(linha["FAIXA_TEXTO"])),
                        ("Altura máxima", br_num(linha["ALT MAX"], 2, sufixo=" m")),
                        ("Número de pavimentos", txt(linha["Nº PAV"])),
                        ("Afastamentos (frente · fundo · lateral)",
                         f"{txt(linha['Afastamento Frente'])} · {txt(linha['Afastamento Fundo'])} · "
                         f"{txt(linha['Afastamento Lateral'])}"),
                        ("Marquise · galeria", f"{txt(linha['MARQUISE'])} · {txt(linha['GALERIA'])}"),
                        ("Cota de soleira", txt(linha["COTA SOLEIRA"])),
                        ("Subsolo", txt(linha["SUBSOLO"])),
                    ]), unsafe_allow_html=True)
            with q2:
                with st.container(border=True):
                    st.markdown("**Notas do quadro**")
                    st.write(txt(linha["Notas"]) if pd.notna(linha["Notas"]) else
                             "Sem notas registradas para esta faixa.")
                if not luos_log.empty:
                    alt_linha = luos_log[luos_log["CÓDIGO"] == linha["CÓDIGO"]]
                    if not alt_linha.empty:
                        with st.container(border=True):
                            st.markdown(f"**Revisões deste código** ({len(alt_linha)})")
                            st.dataframe(
                                alt_linha[["Coluna", "Antes", "Depois", "Motivo"]],
                                hide_index=True, width="stretch", height=180,
                            )

    # --- 5.3 Log -----------------------------------------------------------
    with sub_log:
        if luos_log.empty:
            st.info("O arquivo carregado não traz a aba 'Log de alterações'.")
        else:
            n_pend = int(luos_log["PENDENCIA"].sum())
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Alterações registradas", br_num(len(luos_log)))
            t2.metric("Códigos afetados", br_num(luos_log["CÓDIGO"].nunique()))
            t3.metric("Colunas corrigidas", br_num(luos_log["Coluna"].nunique()))
            t4.metric("Pendências de conferência", br_num(n_pend),
                      help="Notas do quadro que não foram localizadas no texto da norma.")

            if n_pend:
                st.markdown(
                    f"<div style='background:{DOURADO_CLARO};border-left:4px solid {DOURADO};"
                    f"padding:10px 14px;border-radius:4px'>"
                    f"<b>{n_pend} linhas seguem pendentes de conferência manual.</b> "
                    f"São notas citadas no quadro da norma que não foram localizadas no texto. "
                    f"Filtre por “conferir” no motivo para tratá-las.</div>",
                    unsafe_allow_html=True,
                )
                st.write("")

            lg1, lg2, lg3 = st.columns(3)
            g_ra = lg1.multiselect("Região administrativa", sorted(luos_log["RA"].dropna().unique()), key="log_ra")
            g_col = lg2.multiselect("Coluna alterada", sorted(luos_log["Coluna"].dropna().unique()), key="log_col")
            g_mot = lg3.multiselect("Motivo", sorted(luos_log["Motivo"].dropna().unique()), key="log_mot")
            so_pend = st.checkbox("Mostrar apenas as pendências de conferência", value=False)

            lg = luos_log.copy()
            if g_ra:
                lg = lg[lg["RA"].isin(g_ra)]
            if g_col:
                lg = lg[lg["Coluna"].isin(g_col)]
            if g_mot:
                lg = lg[lg["Motivo"].isin(g_mot)]
            if so_pend:
                lg = lg[lg["PENDENCIA"]]

            st.dataframe(
                lg[["RA", "CÓDIGO", "Coluna", "Antes", "Depois", "Motivo"]],
                width="stretch", height=380, hide_index=True,
                column_config={"CÓDIGO": st.column_config.NumberColumn("Código", format="%d")},
            )
            st.caption(f"{len(lg)} de {len(luos_log)} alterações exibidas.")

            c1, c2 = st.columns(2)
            with c1:
                por_col = lg["Coluna"].value_counts().reset_index()
                por_col.columns = ["Coluna", "Alterações"]
                fig = px.bar(
                    por_col.sort_values("Alterações"), x="Alterações", y="Coluna", orientation="h",
                    title="Alterações por coluna", text="Alterações", color_discrete_sequence=[VERDE],
                )
                grafico(fig, 420)
            with c2:
                por_mot = lg["Motivo"].value_counts().head(8).reset_index()
                por_mot.columns = ["Motivo", "Alterações"]
                por_mot["Motivo"] = por_mot["Motivo"].str.slice(0, 44)
                fig = px.bar(
                    por_mot.sort_values("Alterações"), x="Alterações", y="Motivo", orientation="h",
                    title="Alterações por motivo", text="Alterações", color_discrete_sequence=[AZUL],
                )
                grafico(fig, 420)

st.divider()
st.caption(
    "Painel de consulta interna · Terracap · consolidação pela chave CD_IMOVEL · "
    "regras de junção documentadas na aba Leia-me do arquivo Imoveis_consolidado.xlsx."
)
