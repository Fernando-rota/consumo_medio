import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🚛 Consumo Médio da Frota - Simples")

uploaded_file = st.file_uploader("Envie o arquivo Excel (.xlsx) com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=["xlsx"])

def carregar_e_processar(arquivo):
    interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    # Padronizar colunas e tipos, usando só a coluna 'Data' para datas
    for df in [interno, externo]:
        df['Placa'] = df['Placa'].astype(str).str.strip().str.upper()
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
        df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')

    # Filtrar só saídas no interno
    interno = interno[interno['Tipo'].str.lower() == 'saída']

    # Adicionar coluna para tipo de abastecimento
    interno['TipoAbastecimento'] = 'Interno'
    externo['TipoAbastecimento'] = 'Externo'

    # Concatenar as abas
    df = pd.concat([interno, externo], ignore_index=True)

    # Ordenar usando só a coluna 'Data'
    df = df.sort_values(['Placa', 'Data'])

    # Calcular diferença de KM pela ordem temporal para cada placa
    df['km_diff'] = df.groupby('Placa')['KM Atual'].diff()

    # Calcular consumo (litros / km rodado)
    df['consumo'] = df['Quantidade de litros'] / df['km_diff']

    # Filtrar registros com dados válidos e km_diff > 10 km para evitar distorções
    df = df.dropna(subset=['km_diff', 'consumo'])
    df = df[df['km_diff'] > 10]

    return df

if uploaded_file:
    df = carregar_e_processar(uploaded_file)

    st.subheader("Dados Processados")
    st.dataframe(df.head())

    # Consumo médio geral
    consumo_geral = df['Quantidade de litros'].sum() / df['km_diff'].sum()
    km_por_litro_geral = 1 / consumo_geral
    st.metric("Consumo Médio Geral", f"{km_por_litro_geral:.2f} km/L")

    # Consumo médio por veículo
    consumo_veiculos = df.groupby('Placa').apply(
        lambda x: 1 / (x['Quantidade de litros'].sum() / x['km_diff'].sum())
    ).reset_index(name='Km por Litro')
    consumo_veiculos = consumo_veiculos.sort_values('Km por Litro', ascending=False)

    st.subheader("Consumo Médio por Veículo")
    st.dataframe(consumo_veiculos)

    # Gráfico barras consumo por veículo
    fig = px.bar(consumo_veiculos, x='Placa', y='Km por Litro', title='Consumo Médio (Km/L) por Veículo')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Faça upload do arquivo Excel para começar.")
