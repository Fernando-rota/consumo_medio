import streamlit as st
import pandas as pd
import numpy as np

# Função para carregar e pré-processar os dados
@st.cache_data
def carregar_dados(uploaded_file):
    try:
        interno = pd.read_excel(uploaded_file, sheet_name='Abastecimento Interno')
        externo = pd.read_excel(uploaded_file, sheet_name='Abastecimento Externo')

        # Padronização interno
        interno = interno.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual',
            'Tipo': 'tipo'
        })
        interno['data'] = pd.to_datetime(interno['data'], dayfirst=True, errors='coerce')
        interno['placa'] = interno['placa'].astype(str).str.strip().str.upper()
        interno['km_atual'] = pd.to_numeric(interno['km_atual'], errors='coerce')
        interno['litros'] = pd.to_numeric(interno['litros'], errors='coerce')
        # Considerar apenas saídas
        interno = interno[interno['tipo'].str.lower() == 'saída']

        # Padronização externo
        externo = externo.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual'
        })
        externo['data'] = pd.to_datetime(externo['data'], dayfirst=True, errors='coerce')
        externo['placa'] = externo['placa'].astype(str).str.strip().str.upper()
        externo['km_atual'] = pd.to_numeric(externo['km_atual'], errors='coerce')
        externo['litros'] = pd.to_numeric(externo['litros'], errors='coerce')

        # Concatenar dados
        df = pd.concat([
            interno[['placa', 'data', 'km_atual', 'litros']],
            externo[['placa', 'data', 'km_atual', 'litros']]
        ], ignore_index=True)

        # Ordenar e calcular diferença de km
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()
        df['consumo_por_km'] = df['litros'] / df['km_diff']

        # Filtrar dados válidos
        df_clean = df.dropna(subset=['km_diff', 'consumo_por_km'])
        df_clean = df_clean[df_clean['km_diff'] > 0]

        return df_clean

    except Exception as e:
        st.error(f'Erro ao carregar ou processar dados: {e}')
        return pd.DataFrame()  # Retorna df vazio em caso de erro

# Função para cálculo do consumo médio por veículo
def calcular_consumo_medio(df):
    consumo_medio = df.groupby('placa')['consumo_por_km'].mean().reset_index()
    consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']
    consumo_medio = consumo_medio.sort_values('km_por_litro', ascending=False).reset_index(drop=True)
    return consumo_medio

# Layout do app
def main():
    st.set_page_config(page_title='Relatório de Consumo Médio por Veículo', layout='wide')

    st.title('📊 Relatório de Consumo Médio por Veículo')

    uploaded_file = st.file_uploader(
        'Faça upload do arquivo Excel com as abas "Abastecimento Interno" e "Abastecimento Externo"', 
        type=['xlsx']
    )

    if not uploaded_file:
        st.info('Aguardando upload do arquivo Excel...')
        return

    df = carregar_dados(uploaded_file)
    if df.empty:
        st.warning('Nenhum dado válido encontrado após o processamento.')
        return

    # Filtros laterais
    with st.sidebar:
        st.header('Filtros')

        placas_disponiveis = df['placa'].unique()
        placa_selecionada = st.multiselect('Selecione uma ou mais placas:', options=placas_disponiveis, default=placas_disponiveis)

        df_filtrado = df[df['placa'].isin(placa_selecionada)]

        data_min, data_max = df_filtrado['data'].min(), df_filtrado['data'].max()
        periodo = st.date_input('Período:', [data_min, data_max], min_value=data_min, max_value=data_max)

        df_filtrado = df_filtrado[(df_filtrado['data'] >= pd.to_datetime(periodo[0])) & (df_filtrado['data'] <= pd.to_datetime(periodo[1]))]

    # Cálculo consumo médio com filtro
    consumo_medio = calcular_consumo_medio(df_filtrado)

    # Layout principal com abas
    abas = st.tabs(['📋 Dados Detalhados', '📈 Consumo Médio', '🔍 Análise por Placa'])

    with abas[0]:
        st.subheader('Dados Detalhados de Abastecimento')
        st.dataframe(df_filtrado.reset_index(drop=True))

    with abas[1]:
        st.subheader('Consumo Médio por Veículo (Km por Litro)')
        st.dataframe(consumo_medio[['placa', 'km_por_litro']].style.format({'km_por_litro': '{:.2f}'}))

        # Métricas principais
        melhor_veiculo = consumo_medio.loc[consumo_medio['km_por_litro'].idxmax()]
        pior_veiculo = consumo_medio.loc[consumo_medio['km_por_litro'].idxmin()]

        col1, col2 = st.columns(2)
        col1.metric('Melhor Consumo', f"{melhor_veiculo['placa']}", f"{melhor_veiculo['km_por_litro']:.2f} km/l")
        col2.metric('Pior Consumo', f"{pior_veiculo['placa']}", f"{pior_veiculo['km_por_litro']:.2f} km/l")

    with abas[2]:
        st.subheader('Análise por Veículo')

        placa_analise = st.selectbox('Selecione a placa para análise detalhada:', options=placas_disponiveis)
        df_placa = df[df['placa'] == placa_analise].sort_values('data')

        if not df_placa.empty:
            st.line_chart(
                df_placa.set_index('data')['consumo_por_km'].apply(lambda x: 1/x)
            )
            st.write(f"Detalhes do veículo {placa_analise}:")
            st.dataframe(df_placa.reset_index(drop=True))
        else:
            st.warning('Sem dados para esta placa.')

if __name__ == '__main__':
    main()
