
Parece que o trecho de código que você forneceu está quase completo, mas falta um pouco para que o dashboard de indicadores de combustível funcione totalmente. Vamos finalizar o código, garantindo que ele compute e visualize os indicadores desejados.
Aqui está a versão finalizada do seu código Streamlit para gerar indicadores de combustível:
python
import streamlit as st
import pandas as pd
import plotly.express as px
st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')
@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
try:
if file.name.lower().endswith('.csv'):
df = pd.read_csv(file, sep=None, engine='python')
else:
import openpyxl
df = pd.read_excel(file, engine='openpyxl')
df.columns = df.columns.str.strip()
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
def main():
st.markdown(" style='text-align:center;'>⛽ Abastecimento Interno vs Externo", unsafe_allow_html=True)
st.markdown("
Análise comparativa de consumo, custo e eficiência por veículo", unsafe_allow_html=True)
with st.expander('📁 Carregar bases de dados'):
c1, c2, c3 = st.columns(3)
up_ext = c1.file_uploader('Base Externa', type=['csv', 'xlsx'])
up_int = c2.file_uploader('Base Interna', type=['csv', 'xlsx'])
up_val = c3.file_uploader('Base Combustível (Valores)', type=['csv', 'xlsx'])
if not (up_ext and up_int and up_val):
st.info('⚠️ Envie as três bases antes de prosseguir.')
return
df_ext = carregar_base(up_ext, 'Base Externa')
df_int = carregar_base(up_int, 'Base Interna')
df_val = carregar_base(up_val, 'Base Combustível (Valores)')
if df_ext is None or df_int is None or df_val is None:
return
for df in [df_ext, df_int, df_val]:
df.columns = df.columns.str.strip().str.upper()
Validação de colunas obrigatórias
if 'CONSUMO' not in df_ext.columns or 'DATA' not in df_ext.columns:
st.error("A base externa deve conter as colunas 'CONSUMO' e 'DATA'.")
return
df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
if 'DATA' not in df_int.columns:
st.error("A base interna deve conter a coluna 'DATA'.")
return
df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
if 'EMISSÃO' not in df_val.columns or 'VALOR' not in df_val.columns:
st.error("A base de valores deve conter as colunas 'EMISSÃO' e 'VALOR'.")
return
df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)
Filtro de data interativo
min_data = max(pd.Timestamp('2023-01-01'),
min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['EMISSÃO'].min()))
max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['EMISSÃO'].max())
data_selecao = st.sidebar.slider(
'📅 Selecione o intervalo de datas',
min_value=min_data.date(),
max_value=max_data.date(),
value=(min_data.date(), max_data.date()),
format='DD/MM/YYYY'
)
df_ext = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & (df_ext['DATA'].dt.date <= data_selecao[1])]
df_int = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & (df_int['DATA'].dt.date <= data_selecao[1])]
df_val = df_val[(df_val['EMISSÃO'].dt.date >= data_selecao[0]) & (df_val['EMISSÃO'].dt.date <= data_selecao[1])]
Filtros
st.sidebar.header("Filtros Gerais")
placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
filtro_placa = st.sidebar.selectbox('🚗 Placa:', ['Todas'] + placas)
Aplicar filtros
if filtro_placa != 'Todas':
df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
df_int = df_int[df_int['PLACA'] == filtro_placa]
Cálculo de indicadores
total_litros = df_ext['LITROS'].sum()
custo_total = df_val['VALOR'].sum()
media_consumo = total_litros / len(df_ext) if len(df_ext) > 0 else 0
