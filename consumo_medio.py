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

    # Renomear colunas
    df_ext.rename(columns={'CONSUMO': 'LITROS', 'DESCRIÇÃO DO ABASTECIMENTO': 'COMBUSTIVEL'}, inplace=True)
    df_int.rename(columns={'KM ATUAL': 'KM ATUAL', 'QUANTIDADE DE LITROS': 'QUANTIDADE DE LITROS'}, inplace=True)
    df_val.rename(columns={'EMISSÃO': 'DATA'}, inplace=True)

    # Limpar e converter datas
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True, errors='coerce')

    # Conversão de valores
    df_ext['LITROS'] = df_ext['LITROS'].apply(tratar_litros)
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int['KM ATUAL'], errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int['QUANTIDADE DE LITROS'], errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtros globais
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

    # Combustível
    tipos = sorted(df_ext['COMBUSTIVEL'].dropna().astype(str).unique())
    tipo_sel = st.sidebar.selectbox('🛢 Combustível:', ['Todos'] + tipos)
    if tipo_sel != 'Todos':
        df_ext = df_ext[df_ext['COMBUSTIVEL'] == tipo_sel]

    # Filtro por placa
    placas = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique()))
    placa_sel = st.sidebar.selectbox('🚗 Veículo:', ['Todas'] + sorted(placas))
    if placa_sel != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == placa_sel]
        df_int = df_int[df_int['PLACA'] == placa_sel]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == placa_sel]

    # Abas
    tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumo Geral', '⚙️ Consumo Médio', '📈 Tendência', '📆 Comparativo'])

    with tab1:
        st.subheader('Resumo Geral do Período')
        litros_ext = df_ext['LITROS'].sum()
        valor_ext = df_ext['CUSTO TOTAL'].sum()
        litros_int = df_int['QUANTIDADE DE LITROS'].sum()
        valor_int = df_val['VALOR'].sum()
        preco_medio_ponderado = valor_int / litros_int if litros_int > 0 else 0
        total_litros = litros_ext + litros_int
        perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
        perc_int = (litros_int / total_litros * 100) if total_litros else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('Litros Externo', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('Custo Externo', f'R$ {valor_ext:,.2f}')
        c3.metric('Litros Interno', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        c4.metric('Custo Interno', f'R$ {valor_int:,.2f}')
        c5.metric('💰 Preço Médio Interno', f'R$ {preco_medio_ponderado:.2f}')

    with tab2:
        st.subheader('⚙️ Consumo Médio por Veículo')
        df_int_filtrado = df_int.dropna(subset=['PLACA', 'KM ATUAL', 'DATA'])
        df_int_filtrado = df_int_filtrado.sort_values(['PLACA', 'DATA'])
        df_int_filtrado['KM RODADO'] = df_int_filtrado.groupby('PLACA')['KM ATUAL'].diff()
        df_int_filtrado['KM/L'] = df_int_filtrado['KM RODADO'] / df_int_filtrado['QUANTIDADE DE LITROS']
        df_int_filtrado['EFICIÊNCIA'] = pd.cut(df_int_filtrado['KM/L'],
                                               bins=[0, 3, 6, float('inf')],
                                               labels=['🛑 Ineficiente', '⚖️ Regular', '🚀 Econômico'])

        resumo = df_int_filtrado.groupby('PLACA').agg({
            'KM RODADO': 'sum',
            'QUANTIDADE DE LITROS': 'sum',
            'KM/L': 'mean',
            'EFICIÊNCIA': lambda x: x.value_counts().idxmax() if not x.empty else None
        }).reset_index()

        resumo.columns = ['PLACA', 'Total KM', 'Total Litros', 'Consumo Médio (km/L)', 'Eficiência']
        st.dataframe(resumo.style.format({
            'Total KM': '{:,.0f}',
            'Total Litros': '{:,.2f}',
            'Consumo Médio (km/L)': '{:,.2f}'
        }), use_container_width=True)

        fig_bar = px.bar(resumo.sort_values('Consumo Médio (km/L)', ascending=False),
                         x='PLACA', y='Consumo Médio (km/L)',
                         color='Eficiência', title='Consumo Médio por Veículo (km/L)',
                         color_discrete_map={
                             '🚀 Econômico': 'green',
                             '⚖️ Regular': 'orange',
                             '🛑 Ineficiente': 'red'
                         })
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.subheader('📈 Tendência de Consumo Mensal')
        df_ext['MÊS'] = df_ext['DATA'].dt.to_period('M').dt.to_timestamp()
        df_int['MÊS'] = df_int['DATA'].dt.to_period('M').dt.to_timestamp()

        litros_mensal = (
            df_ext.groupby('MÊS')['LITROS'].sum().rename('Externo')
            .to_frame()
            .join(df_int.groupby('MÊS')['QUANTIDADE DE LITROS'].sum().rename('Interno'), how='outer')
            .fillna(0)
            .reset_index()
        )
        litros_mensal['Total'] = litros_mensal['Externo'] + litros_mensal['Interno']

        fig = px.line(litros_mensal, x='MÊS', y=['Externo', 'Interno', 'Total'],
                      title='Tendência Mensal de Abastecimento',
                      labels={'value': 'Litros', 'MÊS': 'Mês', 'variable': 'Origem'},
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.info("📊 Em breve: Comparativo detalhado mensal com custo/litro.")

if __name__ == '__main__':
    main()
