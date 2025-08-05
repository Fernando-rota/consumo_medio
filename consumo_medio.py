import streamlit as st
import pandas as pd

st.set_page_config(page_title="Painel de Abastecimento", layout="wide")
st.title("📊 Painel de Indicadores - Abastecimento de Frota")

uploaded_file = st.file_uploader("📂 Envie a planilha de abastecimento (.xlsx)", type=["xlsx"])

@st.cache_data
def get_sheet_names(file):
    return pd.ExcelFile(file).sheet_names

@st.cache_data
def process_data(file, aba_interno, aba_externo):
    interno = pd.read_excel(file, sheet_name=aba_interno)
    externo = pd.read_excel(file, sheet_name=aba_externo)

    interno["Fonte"] = "Interno"
    externo["Fonte"] = "Externo"

    df = pd.concat([interno, externo], ignore_index=True)

    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors='coerce')
    df["Valor Unitario"] = df["Valor Unitario"].replace("R\$ ", "", regex=True).str.replace(",", ".").astype(float)
    df["Valor Total"] = df["Valor Total"].replace("R\$ ", "", regex=True).str.replace(",", ".").astype(float)
    df["Quantidade de litros"] = df["Quantidade de litros"].astype(str).str.replace(",", ".").astype(float)

    return df

if uploaded_file:
    abas = get_sheet_names(uploaded_file)

    with st.sidebar:
        st.subheader("🗂 Selecione as abas da planilha")
        aba_interno = st.selectbox("Aba de Abastecimento Interno", abas, index=abas.index("abastecimento interno") if "abastecimento interno" in abas else 0)
        aba_externo = st.selectbox("Aba de Abastecimento Externo", abas, index=abas.index("abastecimento externo") if "abastecimento externo" in abas else 1)

    df = process_data(uploaded_file, aba_interno, aba_externo)

    with st.sidebar:
        st.header("Filtros")
        placas = st.multiselect("Placas", df["Placa"].dropna().unique())
        tipo = st.multiselect("Descrição Despesa", df["Descrição Despesa"].dropna().unique())
        fonte = st.multiselect("Fonte", df["Fonte"].unique(), default=["Interno", "Externo"])

    df_filtrado = df.copy()
    if placas:
        df_filtrado = df_filtrado[df_filtrado["Placa"].isin(placas)]
    if tipo:
        df_filtrado = df_filtrado[df_filtrado["Descrição Despesa"].isin(tipo)]
    if fonte:
        df_filtrado = df_filtrado[df_filtrado["Fonte"].isin(fonte)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔋 Total Abastecido (L)", f'{df_filtrado["Quantidade de litros"].sum():,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("💰 Valor Total (R$)", f'R$ {df_filtrado["Valor Total"].sum():,.2f}'.replace(",", "X").replace(".", ",").replace("X", "."))
    preco_medio = df_filtrado["Valor Total"].sum() / df_filtrado["Quantidade de litros"].sum() if df_filtrado["Quantidade de litros"].sum() > 0 else 0
    col3.metric("⛽ Preço Médio por Litro", f'R$ {preco_medio:.2f}')
    col4.metric("🚗 Média KM Atual", f'{df_filtrado["KM Atual"].mean():,.0f}' if not df_filtrado["KM Atual"].isna().all() else "N/A")

    st.subheader("Distribuição de Litros por Tipo de Despesa")
    litros_por_tipo = df_filtrado.groupby("Descrição Despesa")["Quantidade de litros"].sum().sort_values(ascending=False)
    st.bar_chart(litros_por_tipo)

    st.subheader("Top Veículos por Litros Abastecidos")
    top_veiculos = df_filtrado.groupby("Placa")["Quantidade de litros"].sum().sort_values(ascending=False).head(10)
    st.bar_chart(top_veiculos)

    st.subheader("📄 Tabela Detalhada")
    st.dataframe(df_filtrado)

else:
    st.info("Envie uma planilha do Excel com abas 'abastecimento interno' e 'abastecimento externo'.")
