import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

# --- Leitura dos arquivos CSV enviados ---
@st.cache_data
def load_data():
    df_comb = pd.read_csv("abastecimento/combustivel.csv", sep=";", encoding="utf-8")
    df_ext = pd.read_csv("abastecimento/abastecimento_externo.csv", sep=";", encoding="utf-8")
    df_int = pd.read_csv("abastecimento/abastecimento_interno.csv", sep=";", encoding="utf-8")
    return df_comb, df_ext, df_int

df_comb, df_ext, df_int = load_data()

st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Normalização das colunas
df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.replace(" ", "").str.upper()
df_int["Placa"] = df_int["Placa"].astype(str).str.replace(" ", "").str.upper()

# --- Filtros Globais
placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["Placa"]) - {"-", "CORREÇÃO"})
combustiveis = df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique()

col1, col2 = st.columns(2)
with col1:
    placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
with col2:
    tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + list(combustiveis))

# --- Filtrar dados
def aplicar_filtros(df, placa_col, tipo_combustivel_col):
    if placa_selecionada != "Todas":
        df = df[df[placa_col] == placa_selecionada]
    if tipo_comb != "Todos" and tipo_combustivel_col in df.columns:
        df = df[df[tipo_combustivel_col] == tipo_comb]
    return df

df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRIÇÃO DO ABASTECIMENTO")
df_int_filt = aplicar_filtros(df_int, "Placa", None)

# --- Indicadores Principais
st.markdown("## 📊 Indicadores Resumidos")

col1, col2, col3 = st.columns(3)

# Consumo total externo
consumo_ext = df_ext_filt["CONSUMO"].fillna(0).astype(float).sum()
custo_ext = df_ext_filt["CUSTO TOTAL"].replace("R$", "", regex=True).str.replace(",", ".").astype(float).sum()

# Consumo total interno
consumo_int = df_int_filt["Quantidade de litros"].fillna(0).astype(float).sum()

col1.metric("Total Abastecido - Externo (L)", f"{consumo_ext:.1f} L")
col2.metric("Total Abastecido - Interno (L)", f"{consumo_int:.1f} L")
col3.metric("Custo Total Abastecimento Externo", f"R$ {custo_ext:,.2f}")

# --- Tabela Consolidada
st.markdown("## 📄 Tabela Consolidada por Tipo")
df_ext_copy = df_ext_filt.copy()
df_ext_copy["Fonte"] = "Externo"
df_ext_copy["Data"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
df_ext_copy["Litros"] = df_ext_copy["CONSUMO"].astype(float)

df_int_copy = df_int_filt.copy()
df_int_copy["Fonte"] = "Interno"
df_int_copy["Data"] = pd.to_datetime(df_int_copy["Data"], dayfirst=True, errors="coerce")
df_int_copy["Litros"] = df_int_copy["Quantidade de litros"].astype(float)

# Unificar colunas
df_ext_copy = df_ext_copy[["Data", "PLACA", "Litros", "Fonte", "CUSTO TOTAL"]].rename(columns={"PLACA": "Placa"})
df_int_copy = df_int_copy[["Data", "Placa", "Litros", "Fonte"]]
df_int_copy["CUSTO TOTAL"] = None

df_all = pd.concat([df_ext_copy, df_int_copy], ignore_index=True)
st.dataframe(df_all.sort_values("Data", ascending=False), use_container_width=True)

# --- Gráfico: Abastecimento por Placa
st.markdown("## 📈 Gráfico de Abastecimento por Veículo")

graf_placa = df_all.groupby("Placa")["Litros"].sum().reset_index().sort_values("Litros", ascending=False)
fig = px.bar(graf_placa, x="Placa", y="Litros", color="Placa", text_auto=True)
st.plotly_chart(fig, use_container_width=True)

# --- Gráfico de Tendência Temporal
st.markdown("## 📆 Tendência de Abastecimento ao Longo do Tempo")

graf_tempo = df_all.groupby(["Data", "Fonte"])["Litros"].sum().reset_index()
fig2 = px.line(graf_tempo, x="Data", y="Litros", color="Fonte", markers=True)
st.plotly_chart(fig2, use_container_width=True)

# --- Planilha de Combustível (faturas pagas)
with st.expander("🧾 Visualizar Faturas de Combustível (Planilha Financeira)"):
    df_comb["Pagamento"] = pd.to_datetime(df_comb["Pagamento"], dayfirst=True, errors="coerce")
    st.dataframe(df_comb[["Documento", "Fornecedor - Nome", "Pagamento", "Valor Pago", "Centro de Custo"]], use_container_width=True)
