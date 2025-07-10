import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard de Combustível", layout="wide")

# --- Upload dos arquivos ---
st.sidebar.header("📁 Upload das Planilhas")
file_combustivel = st.sidebar.file_uploader("Planilha Combustível", type=["csv", "xlsx"])
file_ext = st.sidebar.file_uploader("Planilha Abastecimento Externo", type=["csv", "xlsx"])
file_int = st.sidebar.file_uploader("Planilha Abastecimento Interno", type=["csv", "xlsx"])

if file_combustivel and file_ext and file_int:
    # Leitura dos dados
    df_comb = pd.read_excel(file_combustivel) if file_combustivel.name.endswith("xlsx") else pd.read_csv(file_combustivel, delimiter=";")
    df_ext = pd.read_excel(file_ext) if file_ext.name.endswith("xlsx") else pd.read_csv(file_ext, delimiter=";")
    df_int = pd.read_excel(file_int) if file_int.name.endswith("xlsx") else pd.read_csv(file_int, delimiter=";")

    st.title("📊 Dashboard de Combustível")

    st.subheader("🔎 Visualização das Planilhas")
    with st.expander("➡️ Planilha Combustível"):
        st.dataframe(df_comb)

    with st.expander("➡️ Planilha Abastecimento Externo"):
        st.dataframe(df_ext)

    with st.expander("➡️ Planilha Abastecimento Interno"):
        st.dataframe(df_int)

    st.subheader("📌 Junção por Placa (para análise cruzada)")
    # Padronizar colunas de placa
    df_ext["PLACA"] = df_ext["PLACA"].str.replace(" ", "").str.upper()
    df_int["Placa"] = df_int["Placa"].str.replace(" ", "").str.upper()

    # Exemplo de merge: Combinar abastecimento interno e externo por placa
    placas_validas = set(df_ext["PLACA"]).intersection(set(df_int["Placa"]))
    df_ext_filtrado = df_ext[df_ext["PLACA"].isin(placas_validas)]
    df_int_filtrado = df_int[df_int["Placa"].isin(placas_validas)]

    st.write("📌 Placas em comum:", list(placas_validas))

    # Exemplo de concatenação para relatório consolidado
    df_ext_filtrado = df_ext_filtrado.rename(columns={"PLACA": "Placa", "DATA": "Data"})
    df_ext_filtrado["Tipo"] = "Externo"
    df_int_filtrado["Tipo"] = "Interno"

    df_ext_simple = df_ext_filtrado[["Data", "Placa", "CONSUMO", "VALOR UNIT", "CUSTO TOTAL", "Tipo"]]
    df_int_simple = df_int_filtrado[["Data", "Placa", "Quantidade de litros", "KM Atual", "Tipo"]]
    df_int_simple = df_int_simple.rename(columns={
        "Quantidade de litros": "CONSUMO",
        "KM Atual": "KM_ATUAL",
    })

    df_consolidado = pd.concat([df_ext_simple, df_int_simple], ignore_index=True)
    st.dataframe(df_consolidado)

else:
    st.warning("⚠️ Por favor, envie os três arquivos (Combustível, Externo e Interno) para continuar.")
