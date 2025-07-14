import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file, sep=None, engine='python')
            except:
                df = pd.read_csv(file, sep=';', engine='python')
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

def padronizar_placa(placa):
    return str(placa).upper().replace('-', '').strip()

def main():
    st.markdown("<h1 style='text-align:center;'>⛽ Abastecimento Interno vs Externo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Análise comparativa de consumo, custo e eficiência por veículo</p>", unsafe_allow_html=True)

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

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    df_ext['PLACA'] = df_ext['PLACA'].apply(padronizar_placa)
    df_int['PLACA'] = df_int['PLACA'].apply(padronizar_placa)
    if 'PLACA' in df_val.columns:
        df_val['PLACA'] = df_val['PLACA'].apply(padronizar_placa)

    min_data = max(pd.Timestamp('2023-01-01'), min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())

    data_selecao = st.sidebar.slider('📅 Selecione o intervalo de datas', min_value=min_data.date(), max_value=max_data.date(), value=(min_data.date(), max_data.date()), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & (df_ext['DATA'].dt.date <= data_selecao[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & (df_int['DATA'].dt.date <= data_selecao[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_selecao[0]) & (df_val['DATA'].dt.date <= data_selecao[1])]

    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]

    st.sidebar.header("Filtros Gerais")

    placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
    todas_opcoes = ['Selecionar tudo'] + placas
    placas_selecionadas = st.sidebar.multiselect("🚚 Filtrar Placa(s)", options=todas_opcoes, default=todas_opcoes)
    if 'Selecionar tudo' in placas_selecionadas:
        placas_selecionadas = placas
    df_ext = df_ext[df_ext['PLACA'].isin(placas_selecionadas)]
    df_int = df_int[df_int['PLACA'].isin(placas_selecionadas)]
    if 'PLACA' in df_val.columns:
        df_val = df_val[df_val['PLACA'].isin(placas_selecionadas)]

    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        filtro_combustivel = st.sidebar.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel)
        if filtro_combustivel != 'Todos':
            df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]

    # ... (continua com os KPIs e as abas)

if __name__ == '__main__':
    main()
