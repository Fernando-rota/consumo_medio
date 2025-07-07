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

    # Filtros globais
    min_data = max(pd.Timestamp('2023-01-01'), min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
    data_range = st.sidebar.slider('📆 Período:', min_data.date(), max_data.date(), (min_data.date(), max_data.date()))

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_range[0]) & (df_ext['DATA'].dt.date <= data_range[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_range[0]) & (df_int['DATA'].dt.date <= data_range[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_range[0]) & (df_val['DATA'].dt.date <= data_range[1])]

    # Tipo de combustível
    combustivel_col = next((c for c in df_ext.columns if 'DESCRI' in c), None)
    if combustivel_col:
        tipos = sorted(df_ext[combustivel_col].dropna().astype(str).str.strip().unique())
        tipo_sel = st.sidebar.selectbox('🛢 Combustível:', ['Todos'] + tipos)
        if tipo_sel != 'Todos':
            df_ext = df_ext[df_ext[combustivel_col] == tipo_sel]

    # Filtro por placa
    placas = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique()))
    placa_sel = st.sidebar.selectbox('🚗 Veículo:', ['Todas'] + sorted(placas))
    if placa_sel != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == placa_sel]
        df_int = df_int[df_int['PLACA'] == placa_sel]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == placa_sel]

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumo Geral', '🚚 Top 10', '⚙️ Consumo', '📈 Tendência'])

    with tab1:
        st.subheader('Resumo Geral do Período')
        litros_ext = df_ext['LITROS'].sum()
        valor_ext = df_ext['CUSTO TOTAL'].sum()
        litros_int = df_int['QUANTIDADE DE LITROS'].sum()
        valor_int = df_val['VALOR'].sum()
        total_litros = litros_ext + litros_int
        perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
        perc_int = (litros_int / total_litros * 100) if total_litros else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Litros Externo', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('Custo Externo', f'R$ {valor_ext:,.2f}')
        c3.metric('Litros Interno', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        c4.metric('Custo Interno', f'R$ {valor_int:,.2f}')

    with tab2:
        st.subheader('Top 10 Veículos por Consumo')
        col1, col2 = st.columns(2)
        with col1:
            top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
            fig = px.bar(top_ext, x='LITROS', y='PLACA', orientation='h', title='Top 10 Externo')
            fig.update_layout(yaxis=dict(categoryorder='total ascending'))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()
            fig = px.bar(top_int, x='QUANTIDADE DE LITROS', y='PLACA', orientation='h', title='Top 10 Interno')
            fig.update_layout(yaxis=dict(categoryorder='total ascending'))
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader('Consumo Médio por Veículo (Km/L)')
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={
                'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={
                'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km', 'QUANTIDADE DE LITROS': 'litros'})
        ])
        df_comb = df_comb.dropna().sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']

        resumo = df_comb.groupby('placa')['consumo'].mean().reset_index(name='Km/L')
        resumo['Classificação'] = resumo['Km/L'].apply(lambda x: 'Econômico' if x >= 6 else 'Normal' if x >= 3.5 else 'Ineficiente')
        resumo = resumo.sort_values('Km/L', ascending=False)

        st.dataframe(resumo.style.format({'Km/L': '{:.2f}'}))
        fig = px.bar(resumo, x='Km/L', y='placa', orientation='h', color='Classificação', text='Km/L')
        fig.update_layout(yaxis=dict(categoryorder='total descending'))
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader('Tendência ao longo do tempo')
        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS':'sum','CUSTO TOTAL':'sum'}).reset_index()
        df_int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS':'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR':'sum'}).reset_index()

        df_preco = pd.merge(df_val_agg, df_int_agg, on='DATA', how='inner')
        df_preco['PRECO_MEDIO'] = df_preco.apply(lambda row: row['VALOR']/row['QUANTIDADE DE LITROS'] if row['QUANTIDADE DE LITROS'] > 0 else 0, axis=1)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.line(df_ext_agg, x='DATA', y='LITROS', title='Litros Externos'), use_container_width=True)
            st.plotly_chart(px.line(df_int_agg, x='DATA', y='QUANTIDADE DE LITROS', title='Litros Internos'), use_container_width=True)
        with col2:
            st.plotly_chart(px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', title='Custo Externo'), use_container_width=True)
            st.plotly_chart(px.line(df_val_agg, x='DATA', y='VALOR', title='Custo Interno'), use_container_width=True)
            st.plotly_chart(px.line(df_preco, x='DATA', y='PRECO_MEDIO', title='Preço Médio Interno'), use_container_width=True)

if __name__ == '__main__':
    main()
