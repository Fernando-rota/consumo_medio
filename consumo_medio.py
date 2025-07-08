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

def main():
    st.title('⛽ Dashboard de Abastecimento Interativo')

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

    # Validar colunas essenciais
    if 'CONSUMO' not in df_ext.columns or 'DATA' not in df_ext.columns:
        st.error("Base externa deve conter 'CONSUMO' e 'DATA'")
        return
    if 'DATA' not in df_int.columns or 'EMISSÃO' not in df_val.columns or 'VALOR' not in df_val.columns:
        st.error("Base interna precisa de 'DATA'. Base de valores precisa de 'EMISSÃO' e 'VALOR'")
        return

    # Normalizar dados externos
    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = df_ext['LITROS'].apply(tratar_litros)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor) if 'CUSTO TOTAL' in df_ext.columns else 0

    # Normalizar dados internos
    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce')

    # Normalizar base de valores
    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtros globais com formato brasileiro
    min_data = max(pd.Timestamp('2023-01-01'), min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
    data_range = st.sidebar.slider('📆 Período:',
                                   min_value=min_data.date(),
                                   max_value=max_data.date(),
                                   value=(min_data.date(), max_data.date()),
                                   format="DD/MM/YYYY")

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_range[0]) & (df_ext['DATA'].dt.date <= data_range[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_range[0]) & (df_int['DATA'].dt.date <= data_range[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_range[0]) & (df_val['DATA'].dt.date <= data_range[1])]

    combustivel_col = next((c for c in df_ext.columns if 'DESCRI' in c), None)
    if combustivel_col:
        tipos = sorted(df_ext[combustivel_col].dropna().astype(str).str.strip().unique())
        tipo_sel = st.sidebar.selectbox('🛢 Combustível:', ['Todos'] + tipos)
        if tipo_sel != 'Todos':
            df_ext = df_ext[df_ext[combustivel_col] == tipo_sel]

    placas = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique()))
    placa_sel = st.sidebar.selectbox('🚗 Veículo:', ['Todas'] + sorted(placas))
    if placa_sel != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == placa_sel]
        df_int = df_int[df_int['PLACA'] == placa_sel]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == placa_sel]

    tab1, tab2, tab3, tab4, tab5 = st.tabs(['📊 Resumo Geral', '🚚 Top 10', '⚙️ Consumo', '📈 Tendência', '📆 Comparativo Mensal'])

    with tab1:
        st.subheader('Resumo Geral do Período')
        litros_ext = df_ext['LITROS'].sum()
        valor_ext = df_ext['CUSTO TOTAL'].sum()
        litros_int = df_int['QUANTIDADE DE LITROS'].sum()

        # Calcular custo interno com base na média ponderada
        total_valor_int = df_val['VALOR'].sum()
        valor_int = total_valor_int
        preco_medio_ponderado = total_valor_int / litros_int if litros_int > 0 else 0

        total_litros = litros_ext + litros_int
        perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
        perc_int = (litros_int / total_litros * 100) if total_litros else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('Litros Externo', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('Custo Externo', f'R$ {valor_ext:,.2f}')
        c3.metric('Litros Interno', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        c4.metric('Custo Interno', f'R$ {valor_int:,.2f}')
        c5.metric('💰 Preço Médio Interno', f'R$ {preco_medio_ponderado:.2f}')

if __name__ == '__main__':
    main()
