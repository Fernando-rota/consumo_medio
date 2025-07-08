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
    st.markdown("<h1 style='text-align:center;'>⛽ Abastecimento Interno vs Externo</h1>", unsafe_allow_html=True)

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

    if 'CONSUMO' not in df_ext.columns or 'DATA' not in df_ext.columns:
        st.error("A base externa deve conter as colunas 'CONSUMO' e 'DATA'.")
        return

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)

    if 'DATA' not in df_int.columns:
        st.error("A base interna deve conter a coluna 'DATA'.")
        return

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    if 'EMISSÃO' not in df_val.columns or 'VALOR' not in df_val.columns:
        st.error("A base de valores deve conter as colunas 'EMISSÃO' e 'VALOR'.")
        return

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtros globais
    min_data = max(pd.Timestamp('2023-01-01'),
                   min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())

    data_selecao = st.sidebar.slider(
        '📅 Período',
        min_value=min_data.date(),
        max_value=max_data.date(),
        value=(min_data.date(), max_data.date()),
        format='DD/MM/YYYY'
    )

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & (df_ext['DATA'].dt.date <= data_selecao[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & (df_int['DATA'].dt.date <= data_selecao[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_selecao[0]) & (df_val['DATA'].dt.date <= data_selecao[1])]

    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]

    st.sidebar.header("🔍 Filtros")

    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        tipo_sel = st.sidebar.selectbox('🛢️ Tipo de Combustível', ['Todos'] + tipos_combustivel)
        if tipo_sel != 'Todos':
            df_ext = df_ext[df_ext[combustivel_col] == tipo_sel]

    placas = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique()))
    placa_sel = st.sidebar.selectbox('🚗 Veículo (Placa)', ['Todas'] + placas)
    if placa_sel != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == placa_sel]
        df_int = df_int[df_int['PLACA'] == placa_sel]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == placa_sel]

    # KPIs
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    preco_medio_ext = valor_ext / litros_ext if litros_ext > 0 else 0

    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()
    preco_medio_int = valor_int / litros_int if litros_int > 0 else 0

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
    perc_int = (litros_int / total_litros * 100) if total_litros else 0

    tabs = st.tabs(['📊 Resumo Geral', '🚚 Top 10', '⚙️ Consumo Médio', '📈 Tendências'])

    with tabs[0]:
        st.markdown(f"### Período: `{data_selecao[0].strftime('%d/%m/%Y')} a {data_selecao[1].strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric('Litros Ext.', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('Custo Ext.', f'R$ {valor_ext:,.2f}')
        c3.metric('R$/L Ext.', f'R$ {preco_medio_ext:.2f}')
        c4.metric('Litros Int.', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        c5.metric('Custo Int.', f'R$ {valor_int:,.2f}')
        c6.metric('R$/L Int.', f'R$ {preco_medio_int:.2f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        fig = px.bar(df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group',
                     text=df_kpi.apply(lambda r: f"R$ {r['Valor']:,.2f}" if r['Métrica'] == 'Custo' else f"{r['Valor']:,.2f} L", axis=1),
                     title='🔍 Comparativo de Consumo e Custo')
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔹 Top 10 - Externo")
            fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h',
                          color='LITROS', color_continuous_scale='Blues', text_auto='.2s')
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.subheader("🟢 Top 10 - Interno")
            fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                          color='QUANTIDADE DE LITROS', color_continuous_scale='Greens', text_auto='.2s')
            st.plotly_chart(fig2, use_container_width=True)

    with tabs[2]:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km', 'QUANTIDADE DE LITROS': 'litros'})
        ])

        df_comb = df_comb.dropna().sort_values(['placa', 'data'])
        df_comb['km_rodado'] = df_comb.groupby('placa')['km'].diff()
        df_comb = df_comb[df_comb['km_rodado'] > 0]
        df_comb['km_litro'] = df_comb['km_rodado'] / df_comb['litros']
        consumo_medio = df_comb.groupby('placa')['km_litro'].mean().reset_index().rename(columns={'km_litro': 'Km/L'})

        def classificar(kml):
            if kml >= 6: return 'Econômico'
            elif kml >= 3.5: return 'Normal'
            return 'Ineficiente'

        consumo_medio['Classificação'] = consumo_medio['Km/L'].apply(classificar)
        st.dataframe(consumo_medio.sort_values('Km/L', ascending=False), use_container_width=True)

    with tabs[3]:
        st.subheader("📈 Tendência de Consumo e Preço Médio")
        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS': 'sum', 'CUSTO TOTAL': 'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR': 'sum'}).reset_index()
        df_int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS': 'sum'}).reset_index()

        df_preco_ext = df_ext_agg.copy()
        df_preco_ext['PRECO_MEDIO'] = df_preco_ext['CUSTO TOTAL'] / df_preco_ext['LITROS']
        df_preco_ext['ORIGEM'] = 'Externo'

        df_preco_int = pd.merge(df_val_agg, df_int_agg, on='DATA', how='inner')
        df_preco_int['PRECO_MEDIO'] = df_preco_int['VALOR'] / df_preco_int['QUANTIDADE DE LITROS']
        df_preco_int['ORIGEM'] = 'Interno'

        df_comparativo = pd.concat([
            df_preco_ext[['DATA', 'PRECO_MEDIO', 'ORIGEM']],
            df_preco_int[['DATA', 'PRECO_MEDIO', 'ORIGEM']]
        ])

        fig = px.line(df_comparativo, x='DATA', y='PRECO_MEDIO', color='ORIGEM', markers=True,
                      title='Preço Médio por Origem (R$/L)')
        fig.update_layout(yaxis_tickprefix='R$ ')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == '__main__':
    main()
