
Parece que o trecho de código que você forneceu está incompleto. Vamos reestruturar e completar o código da aplicação Streamlit que você está desenvolvendo, garantindo que ele esteja completo e funcional. O código realizará o carregamento de dados de abastecimento, processamento e visualização.
Aqui está o código reescrito e completo:
python
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
Configuração da página
st.set_page_config(
page_title='⛽ Dashboard de Abastecimento',
layout='wide',
page_icon='⛽'
)
Funções auxiliares
@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
"""Carrega arquivos CSV ou Excel com tratamento de erros"""
try:
if file.name.lower().endswith('.csv'):
df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
else:
df = pd.read_excel(file, engine='openpyxl')
df.columns = df.columns.str.strip().str.upper()
registros_invalidos = df.isna().sum().sum()
if registros_invalidos > 0:
st.warning(f"⚠️ {registros_invalidos} registros inválidos foram ignorados em {nome}.")
return df
except Exception as e:
st.error(f"Erro ao carregar {nome}: {str(e)}")
return None
def formatar_moeda(valor):
"""Formata valores monetários"""
if pd.isna(valor):
return "R$ 0,00"
return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def validar_placa(placa):
"""Valida o formato de placas de veículo"""
if pd.isna(placa):
return False
placa = str(placa).strip().upper()
padrao_antigo = re.compile(r'^[A-Z]{3}\d{4}$')  # ABC1234
padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')  # ABC1D23
return bool(padrao_antigo.match(placa)) or bool(padrao_mercosul.match(placa))
def classificar_consumo(km_l):
"""Classifica o consumo de combustível"""
if pd.isna(km_l) or km_l <= 0 or km_l > 20:  # Intervalo plausível
return 'Outlier'
elif km_l >= 6:
return 'Econômico'
elif km_l >= 3.5:
return 'Normal'
else:
return 'Ineficiente'
def converter_para_float(valor):
"""Converte valores para float, tratando strings com formatação"""
try:
if pd.isna(valor):
return 0.0
if isinstance(valor, str):
return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
return float(valor)
except:
return 0.0
def tratar_litros(valor):
"""Converte valores de litros para float"""
try:
if pd.isna(valor):
return 0.0
if isinstance(valor, str):
return float(valor.replace('.', '').replace(',', '.'))
return float(valor)
except:
return 0.0
def preprocessar_dados(df_ext, df_int, df_val):
"""Pré-processa dados de abastecimento, converte tipos e prepara para análise"""
df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
df_ext['CONSUMO'] = df_ext['CONSUMO'].apply(tratar_litros)
df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(converter_para_float)
df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
df_int['QUANTIDADE DE LITROS'] = df_int['QUANTIDADE DE LITROS'].apply(tratar_litros)
return df_ext, df_int
def main():
Cabeçalho
st.markdown(" style='text-align:center;'>⛽ Abastecimento Interno vs Externo",
unsafe_allow_html=True)
st.markdown("
Análise comparativa de consumo, custo e eficiência",
