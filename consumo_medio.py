import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento - Interno e Externo")

# Upload de arquivos
st.sidebar.header("🔼 Enviar Planilhas")
externo_file = st.sidebar.file_uploader("Abastecimento Externo (.csv)", type="csv")
interno_file = st.sidebar.file_uploader("Abastecimento Interno (.csv)", type="csv")
fornecedor_file = st.sidebar.file_uploader("Compras de Diesel (.csv)", type="csv")

# Função de mapeamento inteligente de colunas
def mapear_colunas(df, mapa):
    df = df.copy()
    renomear = {}
    for nome_padrao, opcoes in mapa.items():
        for opcao in opcoes:
            col_match = next((col for col in df.columns if opcao.lower() in col.lower()), None)
            if col_match:
                renomear[col_match] = nome_padrao
                break
    return df.rename(columns=renomear)

# Funções de validação e padronização de placa
def validar_placa_tradicional(placa: str) -> bool:
    return bool(re.fullmatch(r'[A-Z]{3}[0-9]{4}', placa))

def validar_placa_mercosul(placa: str) -> bool:
    return bool(re.fullmatch(r'[A-Z]{3}[0-9][A-Z][0-9]{2}', placa))

def padronizar_placa(placa: str) -> str:
    if not isinstance(placa, str):
        return ""
    placa = placa.strip().upper().replace(" ", "")
    placa = re.sub(r'[^A-Z0-9]', '', placa)
    if validar_placa_tradicional(placa) or validar_placa_mercosul(placa):
        return placa
    return ""

if externo_file and interno_file and fornecedor_file:
    try:
        # Leitura dos arquivos CSV
        externo = pd.read_csv(externo_file)
        interno = pd.read_csv(interno_file)
        fornecedor = pd.read_csv(fornecedor_file)

        # Mapeamento de colunas possíveis
        mapa_externo = {
            "data": ["data", "data do abastecimento"],
            "placa": ["placa", "veículo"],
            "km_atual": ["km atual", "odômetro", "km"],
            "litros": ["consumo", "qtd abastecida", "litros", "quantidade de litros"],
            "valor_pago": ["valor pago", "custo total", "valor"]
        }

        mapa_interno = {
            "data": ["data"],
            "placa": ["placa"],
            "tipo": ["tipo"],
            "litros": ["quantidade de litros", "litros"]
        }

        mapa_fornecedor = {
            "emissão": ["emissão"],
            "valor_pago": ["valor pago", "valor"]
        }

        externo.columns = externo.columns.str.strip()
        interno.columns = interno.columns.str.strip()
        fornecedor.columns = fornecedor.columns.str.strip()

        externo = mapear_colunas(externo, mapa_externo)
        interno = mapear_colunas(interno, mapa_interno)
        fornecedor = mapear_colunas(fornecedor, mapa_fornecedor)

        # Padronizar e validar placas
        externo["placa"] = externo["placa"].apply(padronizar_placa)
        interno["placa"] = interno["placa"].apply(padronizar_placa)

        # Remover placas inválidas ou vazias
        externo = externo[externo["placa"] != ""]
        interno = interno[interno["placa"] != ""]

        # Validação de colunas essenciais para externo
        colunas_essenciais = ["data", "placa", "km_atual", "litros"]
        colunas_faltantes = [col for col in colunas_essenciais if col not in externo.columns]
        if colunas_faltantes:
            st.error(f"❌ As seguintes colunas estão faltando na planilha de abastecimento externo: {colunas_faltantes}")
            st.write("📄 Colunas encontradas no arquivo:", list(externo.columns))
            st.stop()

        # Tratamento externo
        externo["data"] = pd.to_datetime(externo["data"], errors="coerce")
        externo = externo.dropna(subset=["data", "placa", "km_atual", "litros"])
        externo = externo[~externo["placa"].isin(["-", "correção"])]
        externo = externo.sort_values(by=["placa", "data"])
        externo["km_rodado"] = externo.groupby("placa")["km_atual"].diff()
        externo["km_litro"] = externo["km_rodado"] / externo["litros"]

        # Tratamento interno
        interno["data"] = pd.to_datetime(interno["data"], errors="coerce")
        interno = interno[interno["tipo"].str.lower() == "saida"]
        interno = interno[~interno["placa"].isin(["-", "correção"])]

        # Tratamento fornecedor
        fornecedor["emissão"] = pd.to_datetime(fornecedor["emissão"], errors="coerce")
        total_pago = fornecedor["valor_pago"].sum()
        total_litros_internos = interno["litros"].sum()
        preco_medio_interno = total_pago / total_litros_internos if total_litros_internos > 0 else np.nan
        preco_medio_externo = (externo["valor_pago"] / externo["litros"]).mean()

        # KPIs
        st.subheader("📈 Indicadores de Preço Médio")
        col1, col2 = st.columns(2)
        col1.metric("💰 Preço Médio Diesel Interno", f"R$ {preco_medio_interno:.2f}")
        col2.metric("⛽ Preço Médio Diesel Externo", f"R$ {preco_medio_externo:.2f}")

        # Gráfico: Eficiência Externa
        st.subheader("⚙️ Eficiência Média por Veículo (KM/L)")
        eficiencia = externo.groupby("placa")["km_litro"].mean().sort_values(ascending=False)
        st.bar_chart(eficiencia)

        # Gráfico: Consumo total
        st.subheader("⛽ Consumo Total por Veículo (litros)")
        consumo = externo.groupby("placa")["litros"].sum().sort_values(ascending=False)
        st.bar_chart(consumo)

        # Tabela: Compras do Fornecedor
        st.subheader("📦 Compras de Diesel - Fornecedor")
        st.dataframe(fornecedor[["emissão", "valor_pago"]].sort_values(by="emissão", ascending=False))

    except Exception as e:
        st.error(f"⚠️ Erro ao processar os dados: {str(e)}")

else:
    st.info("👈 Envie as três planilhas na barra lateral para visualizar o dashboard.")
