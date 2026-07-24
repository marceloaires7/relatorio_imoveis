# -*- coding: utf-8 -*-
"""
Painel de Consulta de Imóveis — carteira consolidada (Base 125 + PPR + TB55).
Fonte de dados: Imoveis_consolidado.xlsx (gerado pela rotina de consolidação).
Execução: streamlit run app.py
"""
import io
import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Configuração geral
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consulta de Imóveis",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

COR = "#1F4E79"          # cor institucional (mesma do relatório Excel)
ARQUIVO = "Imoveis_consolidado.xlsx"


def br_num(v, dec=0, prefixo=""):
    """Formata número no padrão brasileiro (1.234.567,89). Vazio -> travessão."""
    if v is None or pd.isna(v):
        return "—"
    s = f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefixo}{s}"


def br_data(v):
    if v is None or pd.isna(v):
        return "—"
    return pd.to_datetime(v).strftime("%d/%m/%Y")


def txt(v):
    if v is None or pd.isna(v) or str(v).strip() == "":
        return "—"
    return str(v).strip()


@st.cache_data(show_spinner="Carregando dados...")
def carregar_dados(_versao_arquivo):
    """O parâmetro _versao_arquivo (data de modificação do xlsx) faz o cache
    ser renovado automaticamente quando a planilha for substituída."""
    cons = pd.read_excel(ARQUIVO, sheet_name="Consolidado")
    obs = pd.read_excel(ARQUIVO, sheet_name="TB55_Observacoes")
    proc = pd.read_excel(ARQUIVO, sheet_name="TB55_Processos")
    ali = pd.read_excel(ARQUIVO, sheet_name="TB55_Alienacoes")

    cons["AREA_MAX"] = pd.to_numeric(cons["AREA_MAX"], errors="coerce")
    for c in ("TB55_DT_REGISTRO", "TB55_DT_ULT_OBSERVACAO", "TB55_DT_ULT_ALIENACAO"):
        cons[c] = pd.to_datetime(cons[c], errors="coerce")
    obs["DT_OBSERVACAO"] = pd.to_datetime(obs["DT_OBSERVACAO"], errors="coerce")
    ali["DT_OPERACAO"] = pd.to_datetime(ali["DT_OPERACAO"], errors="coerce")
    return cons, obs, proc, ali


cons, obs, proc, ali = carregar_dados(os.path.getmtime(ARQUIVO))

# ----------------------------------------------------------------------------
# Barra lateral — filtros
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"<h2 style='color:{COR};margin-bottom:0'>Consulta de Imóveis</h2>", unsafe_allow_html=True)
    st.caption("Carteira consolidada · 125 lotes em estoque")
    st.divider()

    busca = st.text_input(
        "Buscar por código ou endereço",
        placeholder="Ex.: 14770 ou SAI/N",
        help="Procura no código do imóvel e nos endereços da base e da triagem PPR.",
    )

    f_ra = st.multiselect("Região administrativa", sorted(cons["REGADMIN"].dropna().unique()))
    f_sit = st.multiselect(
        "Situação do lote",
        sorted(cons["SITUACAO_VIGENTE"].dropna().unique()),
        help="Prioriza a situação apurada na triagem PPR; sem triagem, vale a base cartográfica.",
    )
    f_resp = st.multiselect("Responsável (triagem PPR)", sorted(cons["PPR_Responsável"].dropna().unique()))

    f_dados = st.radio(
        "Cobertura de dados",
        ["Todos os imóveis", "Com triagem PPR e histórico TB55", "Sem correspondência (somente base)"],
        help="17 dos 125 imóveis constam apenas na lista base, sem triagem PPR nem histórico TB55.",
    )

    a_min, a_max = float(cons["AREA_MAX"].min()), float(cons["AREA_MAX"].max())
    f_area = st.slider(
        "Área máxima do lote (m²)",
        min_value=0.0, max_value=a_max, value=(0.0, a_max), step=500.0, format="%.0f",
    )

    st.divider()
    st.caption("Dados: Lista base 125 · Triagem PPR · TB55 (09/07/2026). Junção pela chave CD_IMOVEL.")

# Aplicação dos filtros -------------------------------------------------------
df = cons.copy()

if busca.strip():
    b = busca.strip().lower()
    df = df[
        df["CD_IMOVEL"].astype(str).str.contains(b, na=False)
        | df["ENDERECO"].astype(str).str.lower().str.contains(b, na=False)
        | df["PPR_Endereço"].astype(str).str.lower().str.contains(b, na=False)
    ]
if f_ra:
    df = df[df["REGADMIN"].isin(f_ra)]
if f_sit:
    df = df[df["SITUACAO_VIGENTE"].isin(f_sit)]
if f_resp:
    df = df[df["PPR_Responsável"].isin(f_resp)]
if f_dados == "Com triagem PPR e histórico TB55":
    df = df[df["EM_PPR"] == "Sim"]
elif f_dados == "Sem correspondência (somente base)":
    df = df[df["EM_PPR"] == "Não"]
df = df[df["AREA_MAX"].between(f_area[0], f_area[1]) | df["AREA_MAX"].isna()]

# ----------------------------------------------------------------------------
# Abas
# ----------------------------------------------------------------------------
tab_geral, tab_tabela, tab_ficha = st.tabs(["Visão geral", "Explorar dados", "Ficha do imóvel"])

# --------------------------- 1. Visão geral ---------------------------------
with tab_geral:
    if df.empty:
        st.info("Nenhum imóvel atende aos filtros atuais. Ajuste os filtros na barra lateral.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Imóveis selecionados", br_num(len(df)))
        c2.metric("Área total (m²)", br_num(df["AREA_MAX"].sum()))
        c3.metric("Avaliação recente (R$)", br_num(df["TB55_VL_AVALIACAO_RECENTE"].sum(), prefixo="R$ "))
        c4.metric("Com histórico de alienação", br_num((df["TB55_QT_ALIENACOES"] > 0).sum()))
        st.caption(
            "A soma de avaliação considera apenas os imóveis com laudo na TB55; "
            "os demais entram como zero."
        )

        e1, e2 = st.columns(2)
        with e1:
            por_ra = (
                df.groupby("REGADMIN").size().sort_values().reset_index(name="Imóveis")
            )
            fig = px.bar(
                por_ra, x="Imóveis", y="REGADMIN", orientation="h",
                title="Imóveis por região administrativa", text="Imóveis",
                color_discrete_sequence=[COR], template="plotly_white",
            )
            fig.update_layout(yaxis_title="", xaxis_title="", height=460, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")
        with e2:
            por_sit = df["SITUACAO_VIGENTE"].fillna("NÃO INFORMADA").value_counts().reset_index()
            por_sit.columns = ["Situação", "Imóveis"]
            fig = px.bar(
                por_sit, x="Situação", y="Imóveis",
                title="Situação dos lotes", text="Imóveis",
                color_discrete_sequence=[COR], template="plotly_white",
            )
            fig.update_layout(xaxis_title="", yaxis_title="", height=460, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

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
                    title="Dez maiores avaliações (R$)",
                    color_discrete_sequence=[COR], template="plotly_white",
                )
                fig.update_layout(yaxis_title="", xaxis_title="", height=460, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, width="stretch")
        with e4:
            fig = px.histogram(
                df.dropna(subset=["AREA_MAX"]), x="AREA_MAX", nbins=30,
                title="Distribuição da área dos lotes (m²)",
                color_discrete_sequence=[COR], template="plotly_white",
            )
            fig.update_layout(xaxis_title="Área (m²)", yaxis_title="Imóveis", height=460, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

# --------------------------- 2. Explorar dados ------------------------------
with tab_tabela:
    CONJUNTOS = {
        "Visão essencial": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "AREA_MAX", "SITUACAO_VIGENTE", "SITUACAO_FONTE", "STATUS",
            "EM_PPR", "PPR_Responsável", "TB55_VL_AVALIACAO_RECENTE",
            "TB55_QT_ALIENACOES", "TB55_DT_ULT_OBSERVACAO",
        ],
        "Base cartográfica": [
            "CD_IMOVEL", "ENDERECO", "REGADMIN", "UNIDADE", "AREA_CALCU", "AREA_MAX",
            "Shape__Are", "FORMA_IMOV", "POSICAO", "OCUPACAO", "PERCENTUAL",
            "CONDICAO", "DESTINACAO", "IMU_PLAN_L", "PLANTA_DEC", "SITUACAO", "STATUS",
        ],
        "Triagem PPR": [
            "CD_IMOVEL", "PPR_Endereço", "PPR_Nome RA", "PPR_Area_imovel", "PPR_CA",
            "PPR_a_ser_const", "PPR_Area_max_construção", "PPR_Ocupação_max",
            "PPR_Destinacao", "PPR_Proj_URB", "PPR__Legis_Norma_", "PPR_Situação",
            "PPR_obs:", "PPR_Responsável",
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
    esc1, esc2 = st.columns([1, 2])
    conjunto = esc1.selectbox("Conjunto de colunas", list(CONJUNTOS.keys()))
    extras = esc2.multiselect(
        "Adicionar colunas ao conjunto",
        [c for c in cons.columns if c not in CONJUNTOS[conjunto]],
    )
    colunas = CONJUNTOS[conjunto] + extras

    st.dataframe(
        df[colunas],
        width="stretch",
        height=520,
        hide_index=True,
        column_config={
            "CD_IMOVEL": st.column_config.NumberColumn("CD_IMOVEL", format="%d"),
            "AREA_MAX": st.column_config.NumberColumn("Área máx. (m²)", format="localized"),
            "TB55_VL_AVALIACAO_RECENTE": st.column_config.NumberColumn("Avaliação (R$)", format="localized"),
            "TB55_DT_REGISTRO": st.column_config.DateColumn("Registro", format="DD/MM/YYYY"),
            "TB55_DT_ULT_OBSERVACAO": st.column_config.DateColumn("Últ. observação", format="DD/MM/YYYY"),
            "TB55_DT_ULT_ALIENACAO": st.column_config.DateColumn("Últ. alienação", format="DD/MM/YYYY"),
        },
    )
    st.caption(f"{len(df)} de {len(cons)} imóveis exibidos, conforme os filtros da barra lateral.")

    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(
        "Baixar seleção (CSV)",
        df[colunas].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="imoveis_selecao.csv",
        mime="text/csv",
        width="stretch",
    )
    buf = io.BytesIO()
    df[colunas].to_excel(buf, index=False, sheet_name="Selecao")
    d2.download_button(
        "Baixar seleção (Excel)",
        buf.getvalue(),
        file_name="imoveis_selecao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

# --------------------------- 3. Ficha do imóvel -----------------------------
with tab_ficha:
    if df.empty:
        st.info("Nenhum imóvel atende aos filtros atuais. Ajuste os filtros na barra lateral.")
    else:
        opcoes = df.sort_values("CD_IMOVEL")
        rotulos = {
            int(r.CD_IMOVEL): f"{int(r.CD_IMOVEL)} — {txt(r.ENDERECO)}" for r in opcoes.itertuples()
        }
        cod = st.selectbox(
            "Escolha o imóvel (a lista respeita os filtros da barra lateral)",
            options=list(rotulos.keys()),
            format_func=lambda k: rotulos[k],
        )
        im = cons.loc[cons["CD_IMOVEL"] == cod].iloc[0]

        st.markdown(
            f"<h3 style='color:{COR};margin-bottom:0'>{txt(im['ENDERECO'])}</h3>"
            f"<p style='margin-top:2px;color:#5A6B7B'>{txt(im['REGADMIN'])} · Código {int(im['CD_IMOVEL'])}</p>",
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Área máxima (m²)", br_num(im["AREA_MAX"]))
        m2.metric("Avaliação recente (R$)", br_num(im["TB55_VL_AVALIACAO_RECENTE"]))
        m3.metric("Situação (vigente)", txt(im["SITUACAO_VIGENTE"]))
        m4.metric("Alienações no histórico", br_num(im["TB55_QT_ALIENACOES"]))

        if im["EM_PPR"] == "Não":
            st.warning(
                "Este imóvel consta apenas na lista base: não há triagem PPR nem histórico TB55 vinculados."
            )

        b1, b2 = st.columns(2)
        with b1:
            with st.container(border=True):
                st.markdown(f"**Dados da base cartográfica**")
                st.markdown(
                    f"""
| | |
|---|---|
| Condição | {txt(im['CD_DS_COND'])} |
| Status | {txt(im['STATUS'])} |
| Situação na base | {txt(im['SITUACAO'])} |
| Ocupação · % | {txt(im['OCUPACAO'])} · {br_num(im['PERCENTUAL'])}% |
| Forma · posição | {txt(im['FORMA_IMOV'])} · {txt(im['POSICAO'])} |
| Projeto / planta | {txt(im['IMU_PLAN_L'])} · dec. {txt(im['PLANTA_DEC'])} |
| Norma de uso | {txt(im['DESTINACAO'])[:220]} |
"""
                )
        with b2:
            with st.container(border=True):
                st.markdown(f"**Triagem PPR**")
                if im["EM_PPR"] == "Sim":
                    st.markdown(
                        f"""
| | |
|---|---|
| Responsável | {txt(im['PPR_Responsável'])} |
| Área do imóvel (m²) | {br_num(im['PPR_Area_imovel'], 2)} |
| CA · a construir (m²) | {br_num(im['PPR_CA'], 2)} · {br_num(im['PPR_a_ser_const'], 2)} |
| Área máx. construção (m²) | {br_num(im['PPR_Area_max_construção'], 2)} |
| Projeto / norma | {txt(im['PPR_Proj_URB'])} · {txt(im['PPR__Legis_Norma_'])} |
| Situação na vistoria | {txt(im['PPR_Situação'])} |
| Observação da triagem | {txt(im['PPR_obs:'])} |
"""
                    )
                else:
                    st.write("Sem registro na planilha de triagem PPR.")

        with st.container(border=True):
            st.markdown("**Registro cartorial e processos (TB55)**")
            if im["EM_TB55"] == "Sim":
                st.markdown(
                    f"""
| | |
|---|---|
| Cartório | {txt(im['TB55_CARTORIO'])} |
| Data do registro | {br_data(im['TB55_DT_REGISTRO'])} |
| Averbação · folha · livro | {txt(im['TB55_REG_AVERBACAO'])} · {txt(im['TB55_REG_FOLHA'])} · {txt(im['TB55_REG_LIVRO'])} |
| Processos ({br_num(im['TB55_QT_PROCESSOS'])}) | {txt(im['TB55_PROCESSOS'])} |
| Processos administrativos | {txt(im['TB55_PROCESSOS_ADM'])} |
| Anotações | {txt(im['TB55_ANOTACOES_PROCESSO'])[:400]} |
"""
                )
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
                        f"<div style='border-left:3px solid {COR};padding:2px 10px;margin:6px 0'>"
                        f"<b>{br_data(r.DT_OBSERVACAO)}</b><br>{txt(r.OBSERVACAO)}</div>",
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
                            "MODALIDADE": "Modalidade",
                            "SITUACAO": "Situação",
                        },
                    )

st.divider()
st.caption(
    "Painel de consulta interna · consolidação pela chave CD_IMOVEL · "
    "regras de junção documentadas na aba Leia-me do arquivo Imoveis_consolidado.xlsx."
)
