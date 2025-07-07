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

def calcular_metricas(df_ext, df_int, df_val, data_selecao):
    df_ext_filtrado = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & (df_ext['DATA'].dt.date <= data_selecao[1])]
    df_int_filtrado = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & (df_int['DATA'].dt.date <= data_selecao[1])]
    df_val_filtrado = df_val[(df_val['DATA'].dt.date >= data_selecao[0]) & (df_val['DATA'].dt.date <= data_selecao[1])]

    litros_ext = df_ext_filtrado['LITROS'].sum()
    valor_ext = df_ext_filtrado['CUSTO TOTAL'].sum()
    litros_int = df_int_filtrado['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val_filtrado['VALOR'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    return litros_ext, valor_ext, litros_int, valor_int, perc_ext, perc_int

def criar_grafico_comparativo(df_comparativo):
    fig = px.bar(
        df_comparativo, x='Métrica', y='Valor', color='Tipo', barmode='group',
        text=df_comparativo.apply(lambda r: f"R$ {r['Valor']:,.2f}" if r['Métrica'] == 'Custo' else f"{r['Valor']:,.2f} L", axis=1),
        color_discrete_map={'Externo': '#1f77b4', 'Interno': '#2ca02c'},
        title='🔍 Comparativo de Consumo e Custo'
    )
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True, gridcolor='lightgray'))
    return fig

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

    # Padronização de colunas
    for df in [df_ext, df_int, df_val]:
        df.columns = df.columns.str.strip().str.upper()

    # Tratamento da base externa
    if 'CONSUMO' not in df_ext.columns or 'DATA' not in df_ext.columns:
        st.error("A base externa deve conter as colunas 'CONSUMO' e 'DATA'.")
        return

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')

    # Tratamento da base interna
    if 'DATA' not in df_int.columns:
        st.error("A base interna deve conter a coluna 'DATA'.")
        return

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')

    # Tratamento da base de valores
    if 'EMISSÃO' not in df_val.columns or 'VALOR' not in df_val.columns:
        st.error("A base de valores deve conter as colunas 'EMISSÃO' e 'VALOR'.")
        return

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtro de data interativo
    min_data = max(pd.Timestamp('2023-01-01'),
                   min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())

    data_selecao = st.sidebar.slider(
        '📅 Selecione o intervalo de datas',
        min_value=min_data.date(),
        max_value=max_data.date(),
        value=(min_data.date(), max_data.date()),
        format='DD/MM/YYYY'
    )

    # Filtros adicionais
    st.sidebar.header("Filtros Gerais")

    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        filtro_combustivel = st.sidebar.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel)
    else:
        filtro_combustivel = 'Todos'

    placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
    filtro_placa = st.sidebar.selectbox('🚗 Placa:', ['Todas'] + placas)

    # Aplicar filtros
    if filtro_combustivel != 'Todos' and combustivel_col:
        df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]
    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == filtro_placa]

    # Processamento adicional
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    # Cálculo de métricas
    litros_ext, valor_ext, litros_int, valor_int, perc_ext, perc_int = calcular_metricas(df_ext, df_int, df_val, data_selecao)

    # Criação das abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '📊 Resumo Geral',
        '🚚 Top 10 Veículos',
        '⚙️ Consumo Médio',
        '📈 Tendências Temporais',
        '🔍 Análises Avançadas'
    ])

    with tab1:
        st.markdown(f"### 📆 Período Selecionado: `{data_selecao[0].strftime('%d/%m/%Y')} a {data_selecao[1].strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f} %')
        c2.metric('💸 Custo (Externo)', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros (Interno)', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f} %')
        c4.metric('💸 Custo (Interno)', f'R$ {valor_int:,.2f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        st.plotly_chart(criar_grafico_comparativo(df_kpi), use_container_width=True)

    with tab2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h',
                         title='🔹 Top 10 Externo', color='LITROS', 
                         color_continuous_scale='Blues', text_auto='.2s')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                         title='🟢 Top 10 Interno', color='QUANTIDADE DE LITROS', 
                         color_continuous_scale='Greens', text_auto='.2s')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
        ])
        df_comb = df_comb.dropna(subset=['placa', 'data', 'km_atual', 'litros']).sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']
        consumo_medio = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo': 'Km/L'})

        def classificar(km_l):
            if km_l >= 6:
                return 'Econômico'
            elif km_l >= 3.5:
                return 'Normal'
            else:
                return 'Ineficiente'

        consumo_medio['Classificação'] = consumo_medio['Km/L'].apply(classificar)
        consumo_medio = consumo_medio.sort_values('Km/L', ascending=False)

        st.markdown('### ⚙️ Consumo Médio por Veículo')
        col1, col2 = st.columns([1, 2])

        with col1:
            st.dataframe(consumo_medio.style.format({'Km/L': '{:.2f}'}).set_properties(**{'text-align': 'center'}))

        with col2:
            fig3 = px.bar(consumo_medio, x='Km/L', y='placa', orientation='h',
                         color='Km/L', color_continuous_scale='Viridis', text_auto='.2f',
                         title='Eficiência por Veículo (Km/L)')
            fig3.update_layout(yaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.markdown("### 📈 Tendência de Consumo, Custo e Preço Médio ao longo do Tempo")

        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS':'sum', 'CUSTO TOTAL':'sum'}).reset_index()
        df_int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS':'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR':'sum'}).reset_index()

        df_int_agg = df_int_agg.rename(columns={'QUANTIDADE DE LITROS': 'QTDE_LITROS'})

        df_preco_medio_int = pd.merge(df_val_agg, df_int_agg, on='DATA', how='inner')
        df_preco_medio_int['PRECO_MEDIO'] = df_preco_medio_int.apply(
            lambda row: row['VALOR'] / row['QTDE_LITROS'] if row['QTDE_LITROS'] > 0 else 0, axis=1)

        fig_ext_litros = px.line(df_ext_agg, x='DATA', y='LITROS', markers=True,
                                title='Litros Consumidos (Externo)', labels={'LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_ext_litros, use_container_width=True)

        fig_ext_custo = px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', markers=True,
                              title='Custo Total (Externo)', labels={'CUSTO TOTAL':'R$', 'DATA':'Data'})
        st.plotly_chart(fig_ext_custo, use_container_width=True)

        fig_int_litros = px.line(df_int_agg, x='DATA', y='QTDE_LITROS', markers=True,
                                title='Litros Consumidos (Interno)', labels={'QTDE_LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_int_litros, use_container_width=True)

        fig_int_custo = px.line(df_val_agg, x='DATA', y='VALOR', markers=True,
                              title='Custo Total (Interno)', labels={'VALOR':'R$', 'DATA':'Data'})
        st.plotly_chart(fig_int_custo, use_container_width=True)

        fig_preco_medio = px.line(df_preco_medio_int, x='DATA', y='PRECO_MEDIO', markers=True,
                                title='Preço Médio do Combustível (Interno) [R$/Litro]',
                                labels={'PRECO_MEDIO':'R$/Litro', 'DATA':'Data'})
        st.plotly_chart(fig_preco_medio, use_container_width=True)

    with tab5:
        st.markdown("### 🔄 Comparação Direta: Interno vs Externo")
        
        # Preparar dados comparativos
        df_comparativo = pd.DataFrame({
            'Tipo': ['Externo', 'Interno'],
            'Litros': [litros_ext, litros_int],
            'Custo': [valor_ext, valor_int],
            'Custo por Litro': [valor_ext/litros_ext if litros_ext > 0 else 0, 
                               valor_int/litros_int if litros_int > 0 else 0]
        })
        
        col1, col2 = st.columns(2)
        with col1:
            fig_comp_litros = px.pie(df_comparativo, values='Litros', names='Tipo',
                                    title='Distribuição de Litros Consumidos',
                                    color='Tipo', color_discrete_map={'Externo':'#1f77b4', 'Interno':'#2ca02c'})
            st.plotly_chart(fig_comp_litros, use_container_width=True)
        
        with col2:
            fig_comp_custo = px.bar(df_comparativo, x='Tipo', y='Custo por Litro',
                                   title='Custo Médio por Litro (R$/L)',
                                   color='Tipo', color_discrete_map={'Externo':'#1f77b4', 'Interno':'#2ca02c'},
                                   text=df_comparativo['Custo por Litro'].apply(lambda x: f"R$ {x:.2f}"))
            st.plotly_chart(fig_comp_custo, use_container_width=True)

        # Análise de custo por km
        st.markdown("### 📉 Custo por Quilômetro Rodado")
        
        # Calcular km total por veículo (assumindo que o último registro tem a km atual)
        km_total = pd.concat([
            df_ext.groupby('PLACA')['KM ATUAL'].last(),
            df_int.groupby('PLACA')['KM ATUAL'].last()
        ]).groupby(level=0).sum().reset_index()
        
        if not km_total.empty:
            km_total.columns = ['PLACA', 'KM_TOTAL']
            
            # Calcular custo total por veículo
            custo_veiculo = pd.concat([
                df_ext.groupby('PLACA')['CUSTO TOTAL'].sum(),
                df_int.groupby('PLACA').apply(lambda x: df_val[df_val['PLACA'].isin(x['PLACA'])]['VALOR'].sum())
            ]).groupby(level=0).sum().reset_index()
            
            custo_veiculo.columns = ['PLACA', 'CUSTO_TOTAL']
            
            df_custo_km = pd.merge(km_total, custo_veiculo, on='PLACA')
            df_custo_km['CUSTO_KM'] = df_custo_km['CUSTO_TOTAL'] / df_custo_km['KM_TOTAL']
            df_custo_km = df_custo_km[df_custo_km['KM_TOTAL'] > 0].sort_values('CUSTO_KM')
            
            fig_custo_km = px.bar(df_custo_km, x='PLACA', y='CUSTO_KM',
                                 title='Custo por Quilômetro (R$/km)',
                                 labels={'CUSTO_KM': 'Custo por km (R$)', 'PLACA': 'Placa do Veículo'},
                                 text=df_custo_km['CUSTO_KM'].apply(lambda x: f"R$ {x:.2f}"))
            st.plotly_chart(fig_custo_km, use_container_width=True)

        st.markdown("### 📅 Análise de Sazonalidade")
        
        # Agrupar por mês
        df_ext_mes = df_ext.groupby(df_ext['DATA'].dt.to_period('M')).agg({'LITROS':'sum', 'CUSTO TOTAL':'sum'}).reset_index()
        df_int_mes = df_int.groupby(df_int['DATA'].dt.to_period('M')).agg({'QUANTIDADE DE LITROS':'sum'}).reset_index()
        df_val_mes = df_val.groupby(df_val['DATA'].dt.to_period('M')).agg({'VALOR':'sum'}).reset_index()
        
        fig_sazonal = px.line(title='Consumo Mensal de Combustível')
        fig_sazonal.add_scatter(x=df_ext_mes['DATA'].astype(str), y=df_ext_mes['LITROS'], name='Externo')
        fig_sazonal.add_scatter(x=df_int_mes['DATA'].astype(str), y=df_int_mes['QUANTIDADE DE LITROS'], name='Interno')
        fig_sazonal.update_layout(xaxis_title='Mês', yaxis_title='Litros Consumidos')
        st.plotly_chart(fig_sazonal, use_container_width=True)
        
        st.markdown("### 🔎 Identificação de Outliers")
        
        # Boxplot de consumo por veículo
        fig_outliers = px.box(df_comb, x='placa', y='consumo', 
                            title='Distribuição de Consumo por Veículo (Km/L)',
                            labels={'placa': 'Placa', 'consumo': 'Km/L'})
        st.plotly_chart(fig_outliers, use_container_width=True)

if __name__ == '__main__':
    main()
