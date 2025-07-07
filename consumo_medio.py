import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

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
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def normalizar_placa(placa):
    return str(placa).upper().replace('-', '').replace(' ', '').strip()

def remover_placas_invalidas(df):
    if 'PLACA' in df.columns:
        df['PLACA'] = df['PLACA'].apply(normalizar_placa)
        df = df[df['PLACA'].notna() & (df['PLACA'] != '') & (df['PLACA'] != '-') & (df['PLACA'] != 'CORRECAO')]
    return df

def remover_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def encontrar_coluna_emissao(cols):
    for col in cols:
        col_sem_acento = remover_acentos(col).upper()
        if 'EMISSAO' in col_sem_acento:
            return col
    return None

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

    df_ext = remover_placas_invalidas(df_ext)
    df_int = remover_placas_invalidas(df_int)
    df_val = remover_placas_invalidas(df_val)

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
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)
    df_int['TIPO'] = df_int['TIPO'].astype(str).str.upper()

    col_emissao = encontrar_coluna_emissao(df_val.columns)
    if col_emissao:
        df_val['DATA'] = pd.to_datetime(df_val[col_emissao], dayfirst=True, errors='coerce')
    else:
        st.error("Coluna de data com 'Emissão' não encontrada na base de valores.")
        return

    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    if not val_col:
        st.error("Coluna de valor não encontrada na base de valores.")
        return
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor)

    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Selecione o Período:', min_value=ini_min, max_value=fim_max,
                        value=(ini_min, fim_max), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    df_int_entrada = df_int[df_int['TIPO'] == 'ENTRADA']

    litros_entrada = df_int_entrada['QUANTIDADE DE LITROS'].sum()
    valor_pago = df_val['VALOR_TOTAL'].sum()
    preco_medio_int = valor_pago / litros_entrada if litros_entrada > 0 else 0

    st.subheader('💡 Preço Médio do Diesel (Interno)')
    col1, col2, col3 = st.columns(3)
    col1.metric('🔸 Litros de Entrada', f'{litros_entrada:,.2f} L')
    col2.metric('💰 Valor Total Pago', f'R$ {valor_pago:,.2f}')
    col3.metric('📊 Preço Médio por Litro', f'R$ {preco_medio_int:.3f}')

if __name__ == '__main__':
    main()
