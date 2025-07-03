import streamlit as st
import pandas as pd

st.title('Relatório de Consumo Médio por Veículo')

# Upload das duas bases
uploaded_base1 = st.file_uploader('Faça upload da Base 1 (cupons de abastecimento)', type=['csv', 'xlsx'])
uploaded_base2 = st.file_uploader('Faça upload da Base 2 (controle de saída)', type=['csv', 'xlsx'])

if uploaded_base1 and uploaded_base2:
    # Carregar Base 1
    if uploaded_base1.name.endswith('.csv'):
        base1 = pd.read_csv(uploaded_base1, sep=None, engine='python')  # tenta detectar separador
    else:
        base1 = pd.read_excel(uploaded_base1)
        
    # Carregar Base 2
    if uploaded_base2.name.endswith('.csv'):
        base2 = pd.read_csv(uploaded_base2, sep=None, engine='python')
    else:
        base2 = pd.read_excel(uploaded_base2)
    
    st.write('### Preview Base 1')
    st.dataframe(base1.head())
    st.write('### Preview Base 2')
    st.dataframe(base2.head())
    
    try:
        # Padronizar base1
        base1 = base1.rename(columns={
            'PLACA': 'placa',
            'DATA': 'data',
            'KM ATUAL': 'km_atual',
            'CONSUMO': 'litros'
        })
        base1['data'] = pd.to_datetime(base1['data'], dayfirst=True, errors='coerce')
        base1['placa'] = base1['placa'].astype(str).str.replace(' ', '').str.upper()
        base1['km_atual'] = pd.to_numeric(base1['km_atual'], errors='coerce')
        base1['litros'] = pd.to_numeric(base1['litros'], errors='coerce')
        
        # Padronizar base2
        base2 = base2.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'KM Atual': 'km_atual',
            'Quantidade de litros': 'litros'
        })
        base2['data'] = pd.to_datetime(base2['data'], dayfirst=True, errors='coerce')
        base2['placa'] = base2['placa'].astype(str).str.replace(' ', '').str.upper()
        base2['km_atual'] = pd.to_numeric(base2['km_atual'], errors='coerce')
        base2['litros'] = pd.to_numeric(base2['litros'], errors='coerce')
        
        # Concatenar bases
        df = pd.concat([base1[['placa', 'data', 'km_atual', 'litros']],
                        base2[['placa', 'data', 'km_atual', 'litros']]],
                       ignore_index=True)
        
        # Ordenar
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
        
        # Calcular diferença de km
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()
        
        # Calcular consumo por km
        df['consumo_por_km'] = df['litros'] / df['km_diff']
        
        # Limpar dados inválidos
        df_clean = df.dropna(subset=['km_diff', 'consumo_por_km'])
        df_clean = df_clean[df_clean['km_diff'] > 0]
        
        # Consumo médio por veículo
        consumo_medio = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
        consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']
        
        st.write('### Consumo Médio por Veículo (Km por Litro)')
        st.dataframe(consumo_medio[['placa', 'km_por_litro']].sort_values('km_por_litro', ascending=False))
        
    except Exception as e:
        st.error(f'Erro no processamento dos dados: {e}')
else:
    st.info('Por favor, faça upload das duas bases para gerar o relatório.')
