import streamlit as st
import pandas as pd

st.title('Relatório de Consumo Médio por Veículo')

uploaded_file = st.file_uploader('Faça upload do arquivo "Abastecimento - Planilhas" (.xlsx)', type=['xlsx'])

if uploaded_file:
    try:
        # Ler as duas abas do Excel
        externo = pd.read_excel(uploaded_file, sheet_name='Abastecimento Externo')
        interno = pd.read_excel(uploaded_file, sheet_name='Abastecimento Interno')

        st.write('### Preview - Abastecimento Externo')
        st.dataframe(externo.head())

        st.write('### Preview - Abastecimento Interno')
        st.dataframe(interno.head())

        # Padronizar colunas do Externo
        externo = externo.rename(columns={
            'PLACA': 'placa',
            'DATA': 'data',
            'KM ATUAL': 'km_atual',
            'CONSUMO': 'litros'
        })
        externo['data'] = pd.to_datetime(externo['data'], dayfirst=True, errors='coerce')
        externo['placa'] = externo['placa'].astype(str).str.replace(' ', '').str.upper()
        externo['km_atual'] = pd.to_numeric(externo['km_atual'], errors='coerce')
        externo['litros'] = pd.to_numeric(externo['litros'], errors='coerce')

        # Padronizar colunas do Interno
        interno = interno.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'KM Atual': 'km_atual',
            'Quantidade de litros': 'litros'
        })
        interno['data'] = pd.to_datetime(interno['data'], dayfirst=True, errors='coerce')
        interno['placa'] = interno['placa'].astype(str).str.replace(' ', '').str.upper()
        interno['km_atual'] = pd.to_numeric(interno['km_atual'], errors='coerce')
        interno['litros'] = pd.to_numeric(interno['litros'], errors='coerce')

        # Concatenar as duas bases
        df = pd.concat([
            externo[['placa', 'data', 'km_atual', 'litros']],
            interno[['placa', 'data', 'km_atual', 'litros']]
        ], ignore_index=True)

        # Ordenar
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)

        # Calcular diferença de km para cada placa
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()

        # Calcular consumo por km
        df['consumo_por_km'] = df['litros'] / df['km_diff']

        # Filtrar dados válidos
        df_clean = df.dropna(subset=['km_diff', 'consumo_por_km'])
        df_clean = df_clean[df_clean['km_diff'] > 0]

        # Consumo médio por veículo
        consumo_medio = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
        consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']

        st.write('### Consumo Médio por Veículo (Km por Litro)')
        st.dataframe(consumo_medio[['placa', 'km_por_litro']].sort_values('km_por_litro', ascending=False))

    except Exception as e:
        st.error(f'Erro ao processar o arquivo: {e}')
else:
    st.info('Por favor, faça upload do arquivo Excel com as abas "Abastecimento Externo" e "Abastecimento Interno".')
