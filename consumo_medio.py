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
    st.markdown("<p style='text-align:center;'>Análise comparativa e consumo médio por veículo</p>", unsafe_allow_html=True)

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

    # Validações mínimas
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

    # Importante: manter o veículo '-' na base interna para considerar entrada no tanque
    # Filtrar no df_int somente as placas válidas, exceto '-'
    # Porém, para cálculo de preço interno, vamos usar '-' depois no gráfico
    # Então aqui não removemos '-', mantemos

    data_val_col = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    if not data_val_col:
        st.error("Coluna de data não encontrada na base de valores.")
        return
    df_val['DATA'] = pd.to_datetime(df_val[data_val_col], dayfirst=True, errors='coerce')

    # === FILTROS NA SIDEBAR ===
    st.sidebar.header("Filtros Gerais")

    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        # Retirar valores 'nan', '', 'none' do filtro
        tipos_combustivel = sorted(df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])][combustivel_col].unique())
        filtro_combustivel = st.sidebar.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel)
    else:
        st.sidebar.warning('⚠️ Coluna de tipo de combustível não encontrada na base externa.')
        filtro_combustivel = 'Todos'

    # Unificar placas das 3 bases para filtro, limpando e padronizando
    placas_ext = df_ext['PLACA'].dropna().astype(str).str.upper().str.strip()
    placas_int = df_int['PLACA'].dropna().astype(str).str.upper().str.strip()
    placas_val = df_val['PLACA'].dropna().astype(str).str.upper().str.strip() if 'PLACA' in df_val.columns else pd.Series(dtype=str)

    placas_unificadas = pd.concat([placas_ext, placas_int, placas_val]).drop_duplicates().sort_values()
    filtro_placa = st.sidebar.selectbox('🚗 Placa:', ['Todas'] + placas_unificadas.tolist())

    # === FILTRAR BASES CONFORME FILTROS ===
    if filtro_combustivel != 'Todos':
        df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]

    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'].str.upper().str.strip() == filtro_placa]

    # Filtrar por período
    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Selecione o Período:', min_value=ini_min, max_value=fim_max, value=(ini_min, fim_max), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    # Normalização e conversões numéricas
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    # === CÁLCULO DE KPIs ===
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR_TOTAL'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumo Geral', '🚚 Top 10 Veículos', '⚙️ Consumo Médio', '📈 Tendências'])

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
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=60))
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                          title='🟢 Top 10 Interno', color='QUANTIDADE DE LITROS', color_continuous_scale='Greens', text_auto='.2s')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=60))
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

        # Classificação por economia
        def classifica_eficiencia(km_l):
            if km_l >= 6:
                return 'Alta Eficiência'
            elif km_l >= 4:
                return 'Média Eficiência'
            else:
                return 'Baixa Eficiência'

        consumo_medio['Eficiência'] = consumo_medio['Km/L'].apply(classifica_eficiencia)
        consumo_medio = consumo_medio.sort_values('Km/L', ascending=False)

        st.dataframe(consumo_medio.style.format({'Km/L': '{:.2f}'}), use_container_width=True)

    with tab4:
        st.markdown("### 📈 Tendência Preço Médio por Litro")

        # Preparar dados para tendência preço médio litro
        # Para interno, considerar veículo '-' como entrada no tanque
        df_int_precos = df_int.copy()
        df_int_precos.loc[df_int_precos['PLACA'] == '-', 'PLACA'] = 'INTERNAL'  # Marcamos pra agrupar internamente

        df_val_precos = df_val.copy()
        if 'PLACA' in df_val_precos.columns:
            df_val_precos['PLACA'] = df_val_precos['PLACA'].astype(str).str.upper().str.strip()
        else:
            df_val_precos['PLACA'] = 'INTERNAL'

        # Agrupar valores diários preço médio externo e interno
        preco_ext = df_ext.groupby('DATA').apply(
            lambda d: (d['CUSTO TOTAL'].sum() / d['LITROS'].sum()) if d['LITROS'].sum() > 0 else 0
        ).reset_index(name='Preço Médio')

        # Preço médio interno considerando valor total / litros (incluindo '-')
        litros_int_total = df_int_precos['QUANTIDADE DE LITROS'].sum()
        valor_int_total = df_val_precos['VALOR_TOTAL'].sum()
        preco_int_medio = valor_int_total / litros_int_total if litros_int_total > 0 else 0

        # Preço médio interno diário (se quiser por dia, pode agregar também)
        preco_int = df_int_precos.groupby('DATA').apply(
            lambda d: (df_val_precos[df_val_precos['DATA'] == d.name]['VALOR_TOTAL'].sum() / d['QUANTIDADE DE LITROS'].sum()) if d['QUANTIDADE DE LITROS'].sum() > 0 else 0
        ).reset_index(name='Preço Médio')

        # Criar df para gráfico
        df_tendencia = pd.DataFrame({
            'DATA': pd.concat([preco_ext['DATA'], preco_int['DATA']]),
            'Preço Médio': pd.concat([preco_ext['Preço Médio'], preco_int['Preço Médio']]),
            'Tipo': ['Externo'] * len(preco_ext) + ['Interno'] * len(preco_int)
        })

        df_tendencia = df_tendencia.dropna().sort_values('DATA')

        fig_tend = px.line(df_tendencia, x='DATA', y='Preço Médio', color='Tipo', markers=True,
                           title='Preço Médio por Litro - Interno x Externo')
        fig_tend.update_layout(
            xaxis_title='Data',
            yaxis_title='Preço Médio (R$)',
            legend_title='Tipo',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(showgrid=True, gridcolor='lightgray'),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig_tend, use_container_width=True)


if __name__ == '__main__':
    main()
