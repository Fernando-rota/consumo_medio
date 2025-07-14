# dashboard_abastecimento.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="⛽ Dashboard de Abastecimento", layout="wide")

@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python')
        else:
            df = pd.read_excel(file, engine='openpyxl')
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

def tratar_valor(x):
    try:
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.').strip())
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

# 🎯 Interface principal
def main():
    st.title("⛽ Dashboard de Abastecimento Veicular")
    st.markdown("### 💡 Análise comparativa de consumo, custo e eficiência por veículo")

    with st.expander("📁 Upload das Bases de Dados", expanded=True):
        col1, col2, col3 = st.columns(3)
        ext_file = col1.file_uploader("Abastecimento Externo", type=["csv", "xlsx"])
        int_file = col2.file_uploader("Abastecimento Interno", type=["csv", "xlsx"])
        val_file = col3.file_uploader("Valores de Combustível (Entrada no Tanque)", type=["csv", "xlsx"])

    if not (ext_file and int_file and val_file):
        st.info("⚠️ Por favor, envie as três planilhas para continuar.")
        return

    df_ext = carregar_base(ext_file, "Externo")
    df_int = carregar_base(int_file, "Interno")
    df_val = carregar_base(val_file, "Valores")

    # ✅ Verificações mínimas
    if any(df is None for df in [df_ext, df_int, df_val]):
        return

    # ✅ Padronização
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['LITROS'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext['KM ATUAL'], errors='coerce')
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['KM ATUAL'] = pd.to_numeric(df_int['KM ATUAL'], errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int['QUANTIDADE DE LITROS'], errors='coerce')
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # 📅 Filtro de data
    data_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min())
    data_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
    data_ini, data_fim = st.sidebar.date_input("📅 Período", (data_min.date(), data_max.date()), format="DD/MM/YYYY")

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_ini) & (df_ext['DATA'].dt.date <= data_fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= data_ini) & (df_int['DATA'].dt.date <= data_fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= data_ini) & (df_val['DATA'].dt.date <= data_fim)]

    # 🔍 Filtros adicionais
    placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
    placa_sel = st.sidebar.multiselect("🚚 Filtrar Placa(s)", options=placas, default=placas)

    df_ext = df_ext[df_ext['PLACA'].isin(placa_sel)]
    df_int = df_int[df_int['PLACA'].isin(placa_sel)]

    # 📊 Abas
    aba1, aba2, aba3, aba4 = st.tabs([
        "📊 Resumo Geral", "🚚 Top 10 Veículos", "⚙️ Consumo Médio", "📈 Tendência Mensal"
    ])

    with aba1:
        litros_ext = df_ext['LITROS'].sum()
        valor_ext = df_ext['CUSTO TOTAL'].sum()
        litros_int = df_int['QUANTIDADE DE LITROS'].sum()
        valor_int = df_val['VALOR'].sum()
        total_litros = litros_ext + litros_int
        perc_ext = (litros_ext / total_litros) * 100 if total_litros else 0
        perc_int = (litros_int / total_litros) * 100 if total_litros else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⛽ Externo (Litros)", f"{litros_ext:,.1f}", f"{perc_ext:.1f}%")
        c2.metric("💰 Externo (R$)", f"{valor_ext:,.2f}")
        c3.metric("⛽ Interno (Litros)", f"{litros_int:,.1f}", f"{perc_int:.1f}%")
        c4.metric("💰 Interno (R$)", f"{valor_int:,.2f}")

        df_comp = pd.DataFrame({
            "Tipo": ["Externo", "Interno"],
            "Litros": [litros_ext, litros_int],
            "Custo": [valor_ext, valor_int]
        }).melt(id_vars="Tipo", var_name="Métrica", value_name="Valor")

        fig = px.bar(df_comp, x="Métrica", y="Valor", color="Tipo", barmode="group",
                     text_auto='.2s', color_discrete_map={"Externo": "red", "Interno": "green"})
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        top_ext = df_ext.groupby("PLACA")["LITROS"].sum().nlargest(10).reset_index()
        top_int = df_int.groupby("PLACA")["QUANTIDADE DE LITROS"].sum().nlargest(10).reset_index()

        c1, c2 = st.columns(2)
        fig1 = px.bar(top_ext, x="LITROS", y="PLACA", orientation="h", title="🔺 Top 10 Externo", color="LITROS", color_continuous_scale="Reds")
        c1.plotly_chart(fig1, use_container_width=True)
        fig2 = px.bar(top_int, x="QUANTIDADE DE LITROS", y="PLACA", orientation="h", title="🟢 Top 10 Interno", color="QUANTIDADE DE LITROS", color_continuous_scale="Greens")
        c2.plotly_chart(fig2, use_container_width=True)

    with aba3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'LITROS': 'LITROS_COMB'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'QUANTIDADE DE LITROS': 'LITROS_COMB'})
        ])
        df_comb = df_comb.dropna().sort_values(['PLACA', 'DATA'])
        df_comb['KM_RODADOS'] = df_comb.groupby('PLACA')['KM ATUAL'].diff()
        df_comb = df_comb[df_comb['KM_RODADOS'] > 0]
        df_comb['CONSUMO'] = df_comb['KM_RODADOS'] / df_comb['LITROS_COMB']

        resumo = df_comb.groupby("PLACA")["CONSUMO"].mean().reset_index().rename(columns={"CONSUMO": "Km/L"}).sort_values(by="Km/L", ascending=False)

        def classificar(val):
            if val >= 6:
                return "Econômico"
            elif val >= 3.5:
                return "Normal"
            else:
                return "Ineficiente"

        resumo["Classificação"] = resumo["Km/L"].apply(classificar)

        col1, col2 = st.columns([1, 2])
        col1.dataframe(resumo.style.format({"Km/L": "{:.2f}"}))
        fig3 = px.bar(resumo, x="Km/L", y="PLACA", orientation="h", color="Km/L", color_continuous_scale="Viridis", title="Eficiência por Veículo")
        col2.plotly_chart(fig3, use_container_width=True)

    with aba4:
        df_ext_agg = df_ext.groupby(df_ext['DATA'].dt.to_period('M')).agg({'LITROS': 'sum', 'CUSTO TOTAL': 'sum'}).reset_index()
        df_ext_agg['DATA'] = df_ext_agg['DATA'].astype(str)

        fig_litros = px.line(df_ext_agg, x='DATA', y='LITROS', markers=True, title='📈 Consumo Externo Mensal')
        fig_custo = px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', markers=True, title='📉 Custo Externo Mensal')

        st.plotly_chart(fig_litros, use_container_width=True)
        st.plotly_chart(fig_custo, use_container_width=True)

if __name__ == "__main__":
    main()
