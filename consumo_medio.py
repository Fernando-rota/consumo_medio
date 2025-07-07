import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

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

def padronizar_colunas(df):
    df.columns = df.columns.str.upper().str.replace(' ', '_')
    return df

def calcular_metricas(df_ext, df_int, df_val, data_inicio, data_fim):
    df_ext_filtrado = df_ext[(df_ext['DATA'].dt.date >= data_inicio) & (df_ext['DATA'].dt.date <= data_fim)]
    df_int_filtrado = df_int[(df_int['DATA'].dt.date >= data_inicio) & (df_int['DATA'].dt.date <= data_fim)]
    df_val_filtrado = df_val[(df_val['DATA'].dt.date >= data_inicio) & (df_val['DATA'].dt.date <= data_fim)]

    litros_ext = df_ext_filtrado['LITROS'].sum()
    valor_ext = df_ext_filtrado['CUSTO_TOTAL'].sum()
    litros_int = df_int_filtrado['LITROS_INTERNO'].sum()
    valor_int = df_val_filtrado['VALOR'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    return litros_ext, valor_ext, litros_int, valor_int, perc_ext, perc_int

def criar_grafico_comparativo(df_comparativo):
    fig = px.bar(
        df_comparativo, x='MÉTRICA', y='VALOR', color='TIPO', barmode='group',
        text=df_comparativo.apply(lambda r: f"R$ {r['VALOR']:,.2f}" if r['MÉTRICA'] == 'CUSTO' else f"{r['VALOR']:,.2f} L", axis=1),
        color_discrete_map={'EXTERNO': '#1f77b4', 'INTERNO': '#2ca02c'},
        title='🔍 COMPARATIVO DE CONSUMO E CUSTO'
    )
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True, gridcolor='lightgray'))
    return fig

def main():
    st.markdown("<h1 style='text-align:center;'>⛽ ABASTECIMENTO INTERNO VS EXTERNO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Análise comparativa de consumo, custo e eficiência por veículo</p>", unsafe_allow_html=True)

    with st.expander('📁 CARREGAR BASES DE DADOS'):
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
    df_ext = padronizar_colunas(df_ext)
    df_int = padronizar_colunas(df_int)
    df_val = padronizar_colunas(df_val)

    # Renomear colunas críticas
    df_ext = df_ext.rename(columns={'CONSUMO': 'LITROS'})
    df_int = df_int.rename(columns={
        'QUANTIDADE_DE_LITROS': 'LITROS_INTERNO',
        'QUANTIDADE_LITROS': 'LITROS_INTERNO',
        'LITROS': 'LITROS_INTERNO'
    })

    # Tratamento da base externa
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['CUSTO_TOTAL'] = df_ext['CUSTO_TOTAL'].apply(tratar_valor)

    # Tratamento da base interna
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['LITROS_INTERNO'] = pd.to_numeric(df_int['LITROS_INTERNO'], errors='coerce').fillna(0.0)

    # Tratamento da base de valores
    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtro de data com calendário
    st.sidebar.header("FILTROS DE PERÍODO")
    min_data = max(pd.Timestamp('2023-01-01'),
                   min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()))
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())

    col1, col2 = st.sidebar.columns(2)
    with col1:
        data_inicio = st.date_input(
            "Data Início",
            min_data.date(),
            min_value=min_data.date(),
            max_value=max_data.date()
        )
    with col2:
        data_fim = st.date_input(
            "Data Fim",
            max_data.date(),
            min_value=min_data.date(),
            max_value=max_data.date()
        )

    # Filtros adicionais
    st.sidebar.header("FILTROS GERAIS")
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
    df_ext['KM_ATUAL'] = pd.to_numeric(df_ext.get('KM_ATUAL'), errors='coerce')
    df_int['KM_ATUAL'] = pd.to_numeric(df_int.get('KM_ATUAL'), errors='coerce')

    # Cálculo de métricas
    litros_ext, valor_ext, litros_int, valor_int, perc_ext, perc_int = calcular_metricas(df_ext, df_int, df_val, data_inicio, data_fim)

    # Criação das abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '📊 RESUMO GERAL',
        '🚚 CONSUMO POR VEÍCULO',
        '⚙️ EFICIÊNCIA',
        '📈 TENDÊNCIAS',
        '🔍 ANÁLISES AVANÇADAS'
    ])

    with tab1:
        st.markdown(f"### 📆 PERÍODO SELECIONADO: `{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}`")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ LITROS (EXTERNO)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f} %')
        c2.metric('💸 CUSTO (EXTERNO)', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ LITROS (INTERNO)', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f} %')
        c4.metric('💸 CUSTO (INTERNO)', f'R$ {valor_int:,.2f}')

        df_kpi = pd.DataFrame({
            'MÉTRICA': ['LITROS', 'CUSTO'],
            'EXTERNO': [litros_ext, valor_ext],
            'INTERNO': [litros_int, valor_int]
        }).melt(id_vars='MÉTRICA', var_name='TIPO', value_name='VALOR')

        st.plotly_chart(criar_grafico_comparativo(df_kpi), use_container_width=True)

    with tab2:
        st.markdown("### 🚗 CONSUMO TOTAL POR VEÍCULO")
        
        consumo_ext = df_ext.groupby('PLACA').agg({
            'LITROS': 'sum',
            'CUSTO_TOTAL': 'sum'
        }).reset_index().rename(columns={'LITROS': 'LITROS_EXTERNO', 'CUSTO_TOTAL': 'CUSTO_EXTERNO'})
        
        consumo_int = df_int.groupby('PLACA').agg({
            'LITROS_INTERNO': 'sum'
        }).reset_index()
        
        if 'PLACA' in df_val.columns:
            custo_int = df_val.groupby('PLACA')['VALOR'].sum().reset_index().rename(columns={'VALOR': 'CUSTO_INTERNO'})
            consumo_int = pd.merge(consumo_int, custo_int, on='PLACA', how='left')
        else:
            consumo_int['CUSTO_INTERNO'] = valor_int / len(consumo_int) if len(consumo_int) > 0 else 0
        
        df_consumo = pd.merge(consumo_ext, consumo_int, on='PLACA', how='outer').fillna(0)
        df_consumo['TOTAL_LITROS'] = df_consumo['LITROS_EXTERNO'] + df_consumo['LITROS_INTERNO']
        df_consumo['TOTAL_CUSTO'] = df_consumo['CUSTO_EXTERNO'] + df_consumo['CUSTO_INTERNO']
        df_consumo = df_consumo.sort_values('TOTAL_LITROS', ascending=False)
        
        st.dataframe(
            df_consumo.style.format({
                'LITROS_EXTERNO': '{:,.2f} L',
                'CUSTO_EXTERNO': 'R$ {:,.2f}',
                'LITROS_INTERNO': '{:,.2f} L',
                'CUSTO_INTERNO': 'R$ {:,.2f}',
                'TOTAL_LITROS': '{:,.2f} L',
                'TOTAL_CUSTO': 'R$ {:,.2f}'
            }),
            height=500,
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(df_consumo, x='PLACA', y='TOTAL_LITROS',
                         title='TOTAL DE LITROS POR VEÍCULO',
                         labels={'TOTAL_LITROS': 'LITROS', 'PLACA': 'PLACA'},
                         text=df_consumo['TOTAL_LITROS'].apply(lambda x: f"{x:,.1f} L"))
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.bar(df_consumo, x='PLACA', y='TOTAL_CUSTO',
                         title='CUSTO TOTAL POR VEÍCULO',
                         labels={'TOTAL_CUSTO': 'R$', 'PLACA': 'PLACA'},
                         text=df_consumo['TOTAL_CUSTO'].apply(lambda x: f"R$ {x:,.2f}"))
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("### ⚙️ EFICIÊNCIA DOS VEÍCULOS")
        
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM_ATUAL', 'LITROS']].rename(
                columns={'PLACA': 'PLACA', 'DATA': 'DATA', 'KM_ATUAL': 'KM_ATUAL', 'LITROS': 'LITROS'}),
            df_int[['PLACA', 'DATA', 'KM_ATUAL', 'LITROS_INTERNO']].rename(
                columns={'PLACA': 'PLACA', 'DATA': 'DATA', 'KM_ATUAL': 'KM_ATUAL', 'LITROS_INTERNO': 'LITROS'})
        ])
        
        df_comb = df_comb.dropna(subset=['PLACA', 'DATA', 'KM_ATUAL', 'LITROS']).sort_values(['PLACA', 'DATA'])
        df_comb['KM_DIFF'] = df_comb.groupby('PLACA')['KM_ATUAL'].diff()
        df_comb = df_comb[df_comb['KM_DIFF'] > 0]
        df_comb['CONSUMO'] = df_comb['KM_DIFF'] / df_comb['LITROS']
        
        consumo_medio = df_comb.groupby('PLACA')['CONSUMO'].mean().reset_index().rename(columns={'CONSUMO': 'KM/L'})
        consumo_medio = consumo_medio.sort_values('KM/L', ascending=False)
        
        def classificar(km_l):
            if km_l >= 6:
                return 'ECONÔMICO'
            elif km_l >= 3.5:
                return 'NORMAL'
            else:
                return 'INEFICIENTE'

        consumo_medio['CLASSIFICAÇÃO'] = consumo_medio['KM/L'].apply(classificar)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(
                consumo_medio.style.format({'KM/L': '{:.2f}'})
                .background_gradient(subset=['KM/L'], cmap='RdYlGn')
                .set_properties(**{'text-align': 'center'}),
                height=500
            )
        
        with col2:
            fig3 = px.bar(consumo_medio, x='KM/L', y='PLACA', orientation='h',
                         color='CLASSIFICAÇÃO', 
                         color_discrete_map={'ECONÔMICO': 'green', 'NORMAL': 'orange', 'INEFICIENTE': 'red'},
                         title='EFICIÊNCIA POR VEÍCULO (KM/L)',
                         labels={'PLACA': 'PLACA', 'KM/L': 'KM POR LITRO'})
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.markdown("### 📈 TENDÊNCIAS TEMPORAIS")
        
        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS':'sum', 'CUSTO_TOTAL':'sum'}).reset_index()
        df_int_agg = df_int.groupby('DATA').agg({'LITROS_INTERNO':'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR':'sum'}).reset_index()

        df_preco_medio_int = pd.merge(df_val_agg, df_int_agg, on='DATA', how='inner')
        df_preco_medio_int['PRECO_MEDIO'] = df_preco_medio_int.apply(
            lambda row: row['VALOR'] / row['LITROS_INTERNO'] if row['LITROS_INTERNO'] > 0 else 0, axis=1)
        
        fig1 = px.line(df_ext_agg, x='DATA', y='LITROS', markers=True,
                      title='LITROS CONSUMIDOS (EXTERNO) POR DIA',
                      labels={'LITROS':'LITROS', 'DATA':'DATA'})
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.line(df_int_agg, x='DATA', y='LITROS_INTERNO', markers=True,
                      title='LITROS CONSUMIDOS (INTERNO) POR DIA',
                      labels={'LITROS_INTERNO':'LITROS', 'DATA':'DATA'})
        st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = px.line(df_preco_medio_int, x='DATA', y='PRECO_MEDIO', markers=True,
                      title='PREÇO MÉDIO (INTERNO) [R$/LITRO]',
                      labels={'PRECO_MEDIO':'R$/LITRO', 'DATA':'DATA'})
        st.plotly_chart(fig3, use_container_width=True)

    with tab5:
        st.markdown("### 🔍 ANÁLISES AVANÇADAS")
        
        st.markdown("#### 🔄 COMPARAÇÃO DIRETA")
        df_comparativo = pd.DataFrame({
            'TIPO': ['EXTERNO', 'INTERNO'],
            'LITROS': [litros_ext, litros_int],
            'CUSTO': [valor_ext, valor_int],
            'CUSTO_POR_LITRO': [
                valor_ext/litros_ext if litros_ext > 0 else 0,
                valor_int/litros_int if litros_int > 0 else 0
            ]
        })
        
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(df_comparativo, values='LITROS', names='TIPO',
                         title='DISTRIBUIÇÃO DE LITROS CONSUMIDOS',
                         color='TIPO', color_discrete_map={'EXTERNO':'#1f77b4', 'INTERNO':'#2ca02c'})
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.bar(df_comparativo, x='TIPO', y='CUSTO_POR_LITRO',
                         title='CUSTO MÉDIO POR LITRO (R$/L)',
                         color='TIPO', color_discrete_map={'EXTERNO':'#1f77b4', 'INTERNO':'#2ca02c'},
                         text=df_comparativo['CUSTO_POR_LITRO'].apply(lambda x: f"R$ {x:.2f}"))
            st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("#### 📅 ANÁLISE MENSAL")
        df_ext_mes = df_ext.groupby(df_ext['DATA'].dt.to_period('M')).agg({
            'LITROS': 'sum',
            'CUSTO_TOTAL': 'sum'
        }).reset_index()
        df_ext_mes['DATA'] = df_ext_mes['DATA'].astype(str)
        
        df_int_mes = df_int.groupby(df_int['DATA'].dt.to_period('M')).agg({
            'LITROS_INTERNO': 'sum'
        }).reset_index()
        df_int_mes['DATA'] = df_int_mes['DATA'].astype(str)
        
        fig3 = px.line(title='CONSUMO MENSAL DE COMBUSTÍVEL')
        fig3.add_scatter(x=df_ext_mes['DATA'], y=df_ext_mes['LITROS'], name='EXTERNO')
        fig3.add_scatter(x=df_int_mes['DATA'], y=df_int_mes['LITROS_INTERNO'], name='INTERNO')
        fig3.update_layout(xaxis_title='MÊS', yaxis_title='LITROS CONSUMIDOS')
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
