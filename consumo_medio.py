import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title='⛽️ Dashboard de Abastecimento', layout='wide')

@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python')
        else:
            import openpyxl
            df = pd.read_excel(file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False)]
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

def exportar_csv(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    st.download_button("🔹 Baixar CSV", data=buffer.getvalue(), file_name="dados_exportados.csv", mime="text/csv")

def main():
    st.title('⛽️ Dashboard de Abastecimento Profissional')

    with st.expander('📁 Carregar bases de dados'):
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Base Externa', type=['csv', 'xlsx'])
        up_int = c2.file_uploader('Base Interna', type=['csv', 'xlsx'])
        up_val = c3.file_uploader('Base Combustível (Valores)', type=['csv', 'xlsx'])

    if not (up_ext and up_int and up_val):
        st.warning('⚠️ Envie as três bases para continuar.')
        return

    df_ext = carregar_base(up_ext, 'Base Externa')
    df_int = carregar_base(up_int, 'Base Interna')
    df_val = carregar_base(up_val, 'Base Combustível (Valores)')

    if df_ext is None or df_int is None or df_val is None:
        return

    # Padronizar colunas
    for df in [df_ext, df_int, df_val]:
        df.columns = df.columns.str.strip().str.upper()

    df_ext.rename(columns={'CONSUMO': 'LITROS', 'DESCRIÇÃO DO ABASTECIMENTO': 'COMBUSTIVEL'}, inplace=True)
    df_int.rename(columns={'KM ATUAL': 'KM ATUAL', 'QUANTIDADE DE LITROS': 'QUANTIDADE DE LITROS'}, inplace=True)
    df_val.rename(columns={'EMISSÃO': 'DATA'}, inplace=True)

    # Datas e valores
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True, errors='coerce')

    df_ext['LITROS'] = df_ext['LITROS'].apply(tratar_litros)
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int['KM ATUAL'], errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int['QUANTIDADE DE LITROS'], errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtros globais
    with st.sidebar:
        st.markdown('### 🔍 Filtros')
        min_data = max(pd.Timestamp('2023-01-01'), min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
        max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
        data_range = st.slider('Período:', min_value=min_data.date(), max_value=max_data.date(), value=(min_data.date(), max_data.date()), format="DD/MM/YYYY")

        tipos = sorted(df_ext['COMBUSTIVEL'].dropna().unique())
        tipo_sel = st.selectbox('💥 Combustível:', ['Todos'] + tipos)

        placas = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique()))
        placa_sel = st.multiselect('🚗 Veículo(s):', placas, default=placas)

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_range[0]) & (df_ext['DATA'].dt.date <= data_range[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_range[0]) & (df_int['DATA'].dt.date <= data_range[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_range[0]) & (df_val['DATA'].dt.date <= data_range[1])]

    if tipo_sel != 'Todos':
        df_ext = df_ext[df_ext['COMBUSTIVEL'] == tipo_sel]

    df_ext = df_ext[df_ext['PLACA'].isin(placa_sel)]
    df_int = df_int[df_int['PLACA'].isin(placa_sel)]
    df_val = df_val[df_val['PLACA'].isin(placa_sel) if 'PLACA' in df_val.columns else df_val.index]

    # Abas
    tabs = st.tabs(['📊 Resumo Geral', '⚙️ Consumo', '📈 Tendência', '📊 Indicadores Profissionais'])

    with tabs[0]:
        from resumo import exibir_resumo
        exibir_resumo(df_ext, df_int, df_val)

    with tabs[1]:
        from consumo import exibir_consumo
        exibir_consumo(df_int)

    with tabs[2]:
        from tendencia import exibir_tendencia
        exibir_tendencia(df_ext, df_int)

    with tabs[3]:
        from profissionais import exibir_profissionais
        exibir_profissionais(df_ext, df_int, df_val)

if __name__ == '__main__':
    main()
