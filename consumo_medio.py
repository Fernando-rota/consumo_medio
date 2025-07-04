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
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

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

    if 'CONSUMO' not in df_ext.columns or 'DATA' not in df_ext.columns:
        st.error("A base externa deve conter as colunas 'CONSUMO' e 'DATA'.")
        return

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')

    if 'DATA' not in df_int.columns:
        st.error("A base interna deve conter a coluna 'DATA'.")
        return

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')

    data_val_col = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    if not data_val_col:
        st.error("Coluna de data não encontrada na base de valores.")
        return
    df_val['DATA'] = pd.to_datetime(df_val[data_val_col], dayfirst=True, errors='coerce')

    # --- Período mínimo e máximo para filtro
    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Selecione o Período:', min_value=ini_min, max_value=fim_max,
                        value=(ini_min, fim_max), format='DD/MM/YYYY')

    # --- Aplicar filtro de período
    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    # --- Filtro Tipo Combustível (base externa)
    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())

        combustivel_escolhido = st.radio(
            '🛢️ Tipo de Combustível (Base Externa):',
            options=tipos_combustivel,
            index=0,
            horizontal=True
        )
        df_ext = df_ext[df_ext[combustivel_col] == combustivel_escolhido]
    else:
        st.warning('⚠️ Coluna de tipo de combustível não encontrada na base externa.')

    # --- Filtros avançados (posto e motorista), se disponíveis
    posto_col = next((col for col in df_ext.columns if 'POSTO' in col or 'POSTO' in col.upper()), None)
    motorista_col = next((col for col in df_int.columns if 'MOTORISTA' in col or 'RESPONSÁVEL' in col), None)

    if posto_col:
        postos = sorted(df_ext[posto_col].dropna().unique())
        posto_selecionado = st.selectbox('⛽ Filtrar por Posto (Base Externa):', options=['Todos'] + postos)
        if posto_selecionado != 'Todos':
            df_ext = df_ext[df_ext[posto_col] == posto_selecionado]

    if motorista_col:
        motoristas = sorted(df_int[motorista_col].dropna().unique())
        motorista_selecionado = st.selectbox('🚛 Filtrar por Motorista (Base Interna):', options=['Todos'] + motoristas)
        if motorista_selecionado != 'Todos':
            df_int = df_int[df_int[motorista_col] == motorista_selecionado]

    # --- Normalizações básicas
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    # --- KPIs
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR_TOTAL'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    # --- Tabs do dashboard incluindo Tendências
    tab1, tab2, tab3, tab4 = st.tabs([
        '📊 Resumo Geral',
        '🚚 Top 10 Veículos',
        '⚙️ Consumo Médio',
        '📈 Tendências Temporais'
    ])

    with tab1:
        st.markdown(f"### 📆 Período Selecionado: `{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}`")
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

        fig = px.bar(
            df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group',
            text=df_kpi.apply(lambda r: f"R$ {r['Valor']:,.2f}" if r['Métrica'] == 'Custo' else f"{r['Valor']:,.2f} L", axis=1),
            color_discrete_map={'Externo': '#1f77b4', 'Interno': '#2ca02c'},
            title='🔍 Comparativo de Consumo e Custo'
        )
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True, gridcolor='lightgray'))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h',
                          title='🔹 Top 10 Externo', color='LITROS', color_continuous_scale='Blues', text_auto='.2s')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                          title='🟢 Top 10 Interno', color='QUANTIDADE DE LITROS', color_continuous_scale='Greens', text_auto='.2s')
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
        st.markdown("### 📈 Tendência de Consumo e Custo ao longo do Tempo")

        # Série temporal base externa
        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS':'sum', 'CUSTO TOTAL':'sum'}).reset_index()
        # Série temporal base interna
        df_int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS':'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR_TOTAL':'sum'}).reset_index()

        # Gráfico consumo externo
        fig_ext_litros = px.line(df_ext_agg, x='DATA', y='LITROS', markers=True,
                                 title='Litros Consumidos (Base Externa)', labels={'LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_ext_litros, use_container_width=True)

        # Gráfico custo externo
        fig_ext_custo = px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', markers=True,
                                title='Custo Total (Base Externa)', labels={'CUSTO TOTAL':'R$', 'DATA':'Data'})
        st.plotly_chart(fig_ext_custo, use_container_width=True)

        # Gráfico consumo interno
        fig_int_litros = px.line(df_int_agg, x='DATA', y='QUANTIDADE DE LITROS', markers=True,
                                 title='Litros Consumidos (Base Interna)', labels={'QUANTIDADE_DE_LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_int_litros, use_container_width=True)

        # Gráfico custo interno (base valores)
        fig_int_custo = px.line(df_val_agg, x='DATA', y='VALOR_TOTAL', markers=True,
                                title='Custo Total (Base Interna)', labels={'VALOR_TOTAL':'R$', 'DATA':'Data'})
        st.plotly_chart(fig_int_custo, use_container_width=True)

if __name__ == '__main__':
    main()
