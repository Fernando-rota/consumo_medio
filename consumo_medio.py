import pandas as pd
import streamlit as st

@st.cache_data
def load_and_clean_data():
    # Carregamento dos dados
    combustivel = pd.read_excel('combustivel.xlsx')
    externo = pd.read_excel('abastecimento_externo.xlsx')
    interno = pd.read_excel('abastecimento_interno.xlsx')

    # Padronizar placas - remove espaços, maiúsculas
    for df in [externo, interno]:
        df['placa'] = df['placa'].str.upper().str.replace(r'\W+', '', regex=True)

    # Conversão de datas
    combustivel['emissao'] = pd.to_datetime(combustivel['emissao'])
    externo['data'] = pd.to_datetime(externo['data'])
    interno['data'] = pd.to_datetime(interno['data'])

    return combustivel, externo, interno
