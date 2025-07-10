import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

# --- Leitura dos arquivos CSV ---
@st.cache_data
def load_data():
    df_comb = pd.read_csv("abastecimento/combustivel.csv", sep=";", encoding="utf-8")
    df_ext = pd.read_csv("abastecimento/abastecimento_externo.csv", sep=";", encoding="utf-8")
    df_int = pd.read_csv("abastecimento/abastecimento_interno.csv", sep=";", encoding="utf-8")
    return df_comb, df_ext, df_int

df_comb, df_ext, df_int = load_data()

# --- Normalização
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

def aplicar_filtros(df, placa_col, tipo_combustivel_col):
    if placa_selecionada != "Todas":
        df = df[df[placa_col] == placa_selecionada]
    if tipo_comb != "Todos" and tipo_combustivel_col in df.columns:
        df = df[df[tipo_combustivel_col] == tipo_comb]
    return df

df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRIÇÃO DO ABASTECIMENTO")
df_int_filt = aplicar_filtros(df_int, "Placa", None)

# --- Indicadores
st.markdown("## 📊 Indicadores Resumidos")

col1, col2, col3 = st.columns(3)

consumo_ext = df_ext_filt["CONSUMO"].fillna(0).astype(float).sum()
custo_ext = df_ext_filt["CUSTO TOTAL"].replace("R$", "", regex=True).replace(",", ".", regex=True)
custo_ext = pd.to_numeric(custo_ext, errors="coerce").fillna(0).sum()
consumo_int = df_int_filt["Quantidade de litros"].fillna(0).astype(float).sum()

col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")

# --- Preparar Tabela Consolidada
df_ext_copy = df_ext_filt.copy()
df_ext_copy["Fonte"] = "Externo"
df_ext_copy["Data"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
df_ext_copy["Litros"] = df_ext_copy["CONSUMO"].astype(float)
df_ext_copy["Custo"] = df_ext_copy["CUSTO TOTAL"].replace("R$", "", regex=True).str.replace(",", ".")
df_ext_copy["Custo"] = pd.to_numeric(df_ext_copy["Custo"], errors="coerce")
df_ext_copy["KM Rodados"] = pd.to_numeric(df_ext_copy["KM Rodados"], errors="coerce")
df_ext_copy["KM/Litro"] = pd.to_numeric(df_ext_copy["KM/Litro"], errors="coerce")
df_ext_copy = df_ext_copy.rename(columns={"PLACA": "Placa"})

df_int_copy = df_int_filt.copy()
df_int_copy["Fonte"] = "Interno"
df_int_copy["Data"] = pd.to_datetime(df_int_copy["Data"], dayfirst=True, errors="coerce")
df_int_copy["Litros"] = pd.to_numeric(df_int_copy["Quantidade de litros"], errors="coerce")
df_int_copy["Custo"] = 0
df_int_copy["KM Rodados"] = None
df_int_copy["KM/Litro"] = None

df_all = pd.concat([
    df_ext_copy[["Data", "Placa", "Litros", "Custo", "Fonte", "KM Rodados", "KM/Litro"]],
    df_int_copy[["Data", "Placa", "Litros", "Custo", "Fonte", "KM Rodados", "KM/Litro"]]
], ignore_index=True)

# --- Tabela completa
st.markdown("## 📄 Tabela Consolidada")
st.dataframe(df_all.sort_values("Data", ascending=False), use_container_width=True)

# --- Gráficos por Placa e Fonte
st.markdown("## 📈 Abastecimento por Placa")
graf_placa = df_all.groupby("Placa")["Litros"].sum().reset_index().sort_values("Litros", ascending=False)
fig = px.bar(graf_placa, x="Placa", y="Litros", color="Placa", text_auto=True)
st.plotly_chart(fig, use_container_width=True)

# --- Gráfico temporal
st.markdown("## 📆 Tendência por Data")
graf_tempo = df_all.groupby(["Data", "Fonte"])["Litros"].sum().reset_index()
fig2 = px.line(graf_tempo, x="Data", y="Litros", color="Fonte", markers=True)
st.plotly_chart(fig2, use_container_width=True)

# --- 📌 Eficiência (km/l)
st.markdown("## ⚙️ Eficiência (km por litro) - Externo")
df_eff = df_ext_copy[["Placa", "KM Rodados", "Litros"]].dropna()
df_eff["KM/Litro Calc"] = df_eff["KM Rodados"] / df_eff["Litros"]
df_eff_media = df_eff.groupby("Placa")["KM/Litro Calc"].mean().reset_index().sort_values("KM/Litro Calc", ascending=False)

fig_eff = px.bar(df_eff_media, x="Placa", y="KM/Litro Calc", text_auto=".2f", color="Placa")
fig_eff.update_layout(yaxis_title="KM por Litro (média)")
st.plotly_chart(fig_eff, use_container_width=True)

# --- 🏅 Ranking de Consumo
st.markdown("## 🏅 Ranking de Veículos por Consumo Total")
ranking = df_all.groupby("Placa")["Litros"].sum().reset_index().sort_values("Litros", ascending=False)
st.dataframe(ranking, use_container_width=True)

# --- ⚖️ Comparativo Interno vs Externo
st.markdown("## ⚖️ Comparativo: Interno x Externo")

comparativo = df_all.groupby("Fonte").agg(
    Litros=("Litros", "sum"),
    Custo=("Custo", "sum")
).reset_index()

col1, col2 = st.columns(2)
with col1:
    fig3 = px.pie(comparativo, values="Litros", names="Fonte", title="Volume Abastecido")
    st.plotly_chart(fig3, use_container_width=True)
with col2:
    fig4 = px.pie(comparativo, values="Custo", names="Fonte", title="Custo Total")
    st.plotly_chart(fig4, use_container_width=True)

# --- Planilha Financeira
with st.expander("🧾 Faturas de Combustível (Financeiro)"):
    df_comb["Pagamento"] = pd.to_datetime(df_comb["Pagamento"], dayfirst=True, errors="coerce")
    st.dataframe(df_comb[["Documento", "Fornecedor - Nome", "Pagamento", "Valor Pago", "Centro de Custo"]], use_container_width=True)
