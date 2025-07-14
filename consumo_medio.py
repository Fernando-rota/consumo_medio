import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento - Interno e Externo")

# Upload dos arquivos
st.sidebar.header("🔼 Enviar Planilhas")
externo_file = st.sidebar.file_uploader("Abastecimento Externo (.xlsx)", type="xlsx")
interno_file = st.sidebar.file_uploader("Abastecimento Interno (.xlsx)", type="xlsx")
fornecedor_file = st.sidebar.file_uploader("Compras de Diesel (.xlsx)", type="xlsx")

# Processamento
if externo_file and interno_file and fornecedor_file:
    externo = pd.read_excel(externo_file)
    interno = pd.read_excel(interno_file)
    fornecedor = pd.read_excel(fornecedor_file)

    # --- EXTERNO ---
    externo.columns = externo.columns.str.lower().str.strip()
    externo = externo.rename(columns={
        "km atual": "km_atual",
        "consumo": "litros",
        "valor pago": "valor_pago",
        "placa": "placa"
    })
    externo["data"] = pd.to_datetime(externo["data"], errors="coerce")
    externo = externo[~externo["placa"].isin(["-", "correção"])]
    externo = externo.sort_values(by=["placa", "data"])
    externo["km_rodado"] = externo.groupby("placa")["km_atual"].diff()
    externo["km_litro"] = externo["km_rodado"] / externo["litros"]

    # --- INTERNO ---
    interno.columns = interno.columns.str.lower().str.strip()
    interno = interno[interno["tipo"].str.lower() == "saida"]
    interno = interno[~interno["placa"].isin(["-", "correção"])]
    interno["data"] = pd.to_datetime(interno["data"], errors="coerce")
    interno = interno.rename(columns={"quantidade de litro": "litros"})

    # --- FORNECEDOR ---
    fornecedor.columns = fornecedor.columns.str.lower().str.strip()
    fornecedor["emissão"] = pd.to_datetime(fornecedor["emissão"], errors="coerce")
    total_pago = fornecedor["valor pago"].sum()
    total_litros_internos = interno["litros"].sum()
    preco_medio_interno = total_pago / total_litros_internos if total_litros_internos > 0 else np.nan

    preco_medio_externo = (externo["valor_pago"] / externo["litros"]).mean()

    # --- KPIs ---
    st.markdown("### 🧾 Indicadores Gerais")
    col1, col2 = st.columns(2)
    col1.metric("💰 Preço Médio Diesel Interno", f"R$ {preco_medio_interno:.2f}")
    col2.metric("⛽ Preço Médio Diesel Externo", f"R$ {preco_medio_externo:.2f}")

    # --- Eficiência ---
    st.markdown("### ⚙️ Eficiência Média por Veículo (Externo)")
    km_l_por_placa = externo.groupby("placa")["km_litro"].mean().sort_values(ascending=False)
    st.bar_chart(km_l_por_placa)

    # --- Consumo total por veículo ---
    st.markdown("### ⛽ Consumo Total por Veículo (Litros)")
    consumo_por_placa = externo.groupby("placa")["litros"].sum().sort_values(ascending=False)
    st.bar_chart(consumo_por_placa)

    # --- Tabela de Compras ---
    st.markdown("### 🧾 Compras de Diesel (Fornecedor)")
    st.dataframe(fornecedor[["emissão", "fornecedor - nome", "valor pago"]])

else:
    st.info("👈 Envie as três planilhas na barra lateral para visualizar os dados.")
