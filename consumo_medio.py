import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

st.title("⛽ Dashboard de Abastecimento - Interno vs Externo")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload da planilha (.xlsx) com abas 'abastecimento interno' e 'abastecimento externo'", type=["xlsx"])

if uploaded_file:
    # Leitura das abas com os nomes exatos
    try:
        df_interno = pd.read_excel(uploaded_file, sheet_name="abastecimento interno")
        df_externo = pd.read_excel(uploaded_file, sheet_name="abastecimento externo")
    except Exception as e:
        st.error("Erro ao ler as planilhas. Verifique se há abas chamadas 'abastecimento interno' e 'abastecimento externo'.")
        st.stop()

    # Normalização das colunas
    colunas = ['Data', 'Placa', 'Codigo Despesa', 'Descrição Despesa', 'CNPJ Fornecedor',
               'Quantidade de litros', 'Valor Unitario', 'Valor Total', 'KM Atual', 'Observações']

    df_interno = df_interno[colunas].copy()
    df_externo = df_externo[colunas].copy()

    df_interno['Fonte'] = 'Interno'
    df_externo['Fonte'] = 'Externo'

    # Combina os dois DataFrames
    df = pd.concat([df_interno, df_externo], ignore_index=True)

    # Conversões
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'].astype(str).str.replace('R$', '').str.replace(',', '.'), errors='coerce')
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'].astype(str).str.replace('R$', '').str.replace(',', '.'), errors='coerce')

    # Filtros
    st.sidebar.header("🔍 Filtros")
    placas = st.sidebar.multiselect("Filtrar por placa:", df["Placa"].dropna().unique())
    combustiveis = st.sidebar.multiselect("Filtrar por combustível:", df["Descrição Despesa"].dropna().unique())
    fontes = st.sidebar.multiselect("Filtrar por origem:", df["Fonte"].unique(), default=["Interno", "Externo"])

    df_filtrado = df.copy()

    if placas:
        df_filtrado = df_filtrado[df_filtrado["Placa"].isin(placas)]
    if combustiveis:
        df_filtrado = df_filtrado[df_filtrado["Descrição Despesa"].isin(combustiveis)]
    if fontes:
        df_filtrado = df_filtrado[df_filtrado["Fonte"].isin(fontes)]

    st.subheader("📈 Indicadores Gerais")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Litros Abastecidos", f"{df_filtrado['Quantidade de litros'].sum():,.2f} L")
    col2.metric("Valor Total", f"R$ {df_filtrado['Valor Total'].sum():,.2f}")
    preco_medio_geral = df_filtrado['Valor Total'].sum() / df_filtrado['Quantidade de litros'].sum()
    col3.metric("Preço Médio (Geral)", f"R$ {preco_medio_geral:.2f}")

    st.divider()
    st.subheader("📊 Indicadores por Tipo de Combustível e Fonte")

    combustiveis = df_filtrado["Descrição Despesa"].dropna().unique()
    fontes = df_filtrado["Fonte"].dropna().unique()

    for combustivel in combustiveis:
        st.markdown(f"### ⛽ {combustivel}")
        cols = st.columns(len(fontes))
        for i, fonte in enumerate(fontes):
            temp = df_filtrado[(df_filtrado["Descrição Despesa"] == combustivel) & (df_filtrado["Fonte"] == fonte)]
            litros = temp["Quantidade de litros"].sum()
            valor = temp["Valor Total"].sum()
            preco_medio = valor / litros if litros > 0 else 0
            with cols[i]:
                st.metric(f"{fonte}", f"{litros:,.2f} L", help=f"Total abastecido via {fonte}")
                st.metric(f"Valor Total", f"R$ {valor:,.2f}")
                st.metric(f"Preço Médio", f"R$ {preco_medio:.2f}")
