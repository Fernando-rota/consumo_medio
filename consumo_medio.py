import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Dashboard de Abastecimento Veicular", layout="wide")

def tratar_valor(valor_str):
    try:
        valor = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(valor)
    except:
        return 0.0

def tratar_litros(valor_str):
    try:
        val = str(valor_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return 0.0

@st.cache_data
def carregar_base(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext == 'csv':
        return pd.read_csv(uploaded_file, sep=None, engine='python')
    elif ext in ['xls', 'xlsx']:
        return pd.read_excel(uploaded_file)
    else:
        return None

def main():
    st.title("⛽ Dashboard de Abastecimento Veicular")

    uploaded_base1 = st.file_uploader("📁 Base 1 – Abastecimento Externo (.csv ou .xlsx)", type=["csv", "xlsx"])
    uploaded_base2 = st.file_uploader("📁 Base 2 – Abastecimento Interno (.csv ou .xlsx)", type=["csv", "xlsx"])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1)
        base2 = carregar_base(uploaded_base2)

        if base1 is not None and base2 is not None:
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')

            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()

            base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')

            base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            min_date = min(base1['data'].min(), base2['data'].min())
            max_date = max(base1['data'].max(), base2['data'].max())
            start_date = st.sidebar.date_input("Data inicial", min_date)
            end_date = st.sidebar.date_input("Data final", max_date)

            if start_date > end_date:
                st.sidebar.error("Data inicial deve ser anterior à data final.")
                return

            base1 = base1[(base1['data'] >= pd.to_datetime(start_date)) & (base1['data'] <= pd.to_datetime(end_date))]
            base2 = base2[(base2['data'] >= pd.to_datetime(start_date)) & (base2['data'] <= pd.to_datetime(end_date))]

            descricao_list = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique() if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns else []
            filtro_tipo = st.sidebar.selectbox("Tipo de Combustível (Base Externa)", ["Todos"] + sorted(descricao_list))
            if filtro_tipo != "Todos":
                base1 = base1[base1['DESCRIÇÃO DO ABASTECIMENTO'] == filtro_tipo]

            aba1, aba2, aba3, aba4 = st.tabs(["Resumo", "Top Veículos", "Consumo Médio", "Dados Completos"])

            with aba1:
                litros_ext = base1['litros'].sum()
                litros_int = base2['litros'].sum()
                total_litros = litros_ext + litros_int

                perc_ext = (litros_ext / total_litros) * 100 if total_litros else 0
                perc_int = (litros_int / total_litros) * 100 if total_litros else 0

                valor_ext = base1['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in base1.columns else 0

                st.markdown(f"### 📊 KPIs Gerais ({start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("🔴 Abastecimento Externo (litros)", f"{litros_ext:,.2f} L")
                    st.metric("💰 Custo Externo", f"R$ {valor_ext:,.2f}")
                    st.metric("📉 % Externo", f"{perc_ext:.1f}%")

                with col2:
                    st.metric("🟢 Abastecimento Interno (litros)", f"{litros_int:,.2f} L")
                    st.metric("📈 % Interno", f"{perc_int:.1f}%")

            with aba2:
                st.markdown("### 🚚 Top 10 Veículos – Abastecimento Externo (Litros)")
                top_ext = base1.groupby("placa")["litros"].sum().sort_values(ascending=False).head(10)
                st.bar_chart(top_ext.to_frame("Litros"))
                st.dataframe(top_ext.reset_index().rename(columns={"placa": "Placa", "litros": "Litros"}))

            with aba3:
                st.markdown("### ⛽ Consumo Médio por Veículo (Km/L)")

                df_comb = pd.concat([
                    base1[["placa", "data", "km_atual", "litros"]],
                    base2[["placa", "data", "km_atual", "litros"]]
                ], ignore_index=True)

                df_comb = df_comb.sort_values(by=["placa", "data", "km_atual"])
                df_comb["km_diff"] = df_comb.groupby("placa")["km_atual"].diff()
                df_comb["consumo_por_km"] = df_comb["litros"] / df_comb["km_diff"]

                df_clean = df_comb.dropna()
                df_clean = df_clean[df_clean["km_diff"] > 0]

                consumo = df_clean.groupby("placa")["consumo_por_km"].mean().reset_index()
                consumo["km_por_litro"] = 1 / consumo["consumo_por_km"]
                consumo_final = consumo[["placa", "km_por_litro"]].sort_values(by="km_por_litro", ascending=False)

                st.bar_chart(consumo_final.set_index("placa"))
                st.dataframe(consumo_final.rename(columns={"placa": "Placa", "km_por_litro": "Km/L"}).style.format({"Km/L": "{:.2f}"}))

            with aba4:
                st.markdown("### 📑 Bases Completas")
                st.subheader("Base Externa")
                st.dataframe(base1)
                st.subheader("Base Interna")
                st.dataframe(base2)
        else:
            st.warning("Erro ao processar um dos arquivos. Verifique o formato e os dados.")
    else:
        st.info("Por favor, envie as duas bases para continuar.")

if __name__ == "__main__":
    main()
