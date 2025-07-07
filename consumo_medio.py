import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

# --- Funções de Apoio ---
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
        
        df.columns = df.columns.str.strip().str.upper()
        registros_invalidos = df.isna().sum().sum()
        if registros_invalidos > 0:
            st.warning(f"⚠️ {registros_invalidos} registros inválidos foram ignorados em {nome}.")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

def tratar_valor(x):
    try:
        valor = float(str(x).replace('R$', '').replace('.', '').replace(',', '.').strip())
        return valor if valor >= 0 else 0.0
    except:
        return 0.0

def tratar_litros(x):
    try:
        valor = float(str(x).replace('.', '').replace(',', '.'))
        return valor if valor >= 0 else 0.0
    except:
        return 0.0

def validar_placa(placa):
    placa = str(placa).strip().upper()
    padrao_antigo = re.compile(r'^[A-Z]{3}\d{4}$')  # Ex: ABC1234
    padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')  # Ex: ABC1D23
    return bool(padrao_antigo.match(placa)) or bool(padrao_mercosul.match(placa))

def classificar_consumo(km_l):
    if km_l <= 0 or km_l > 20:  # Intervalo plausível
        return 'Outlier'
    elif km_l >= 6:
        return 'Econômico'
    elif km_l >= 3.5:
        return 'Normal'
    else:
        return 'Ineficiente'

# --- Main ---
def main():
    st.markdown("<h1 style='text-align:center;'>⛽ Abastecimento Interno vs Externo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Análise comparativa de consumo, custo e eficiência por veículo</p>", unsafe_allow_html=True)

    with st.expander('📁 Carregar bases de dados'):
        st.tooltip("""
        - **Base Externa**: CSV/Excel com colunas 'DATA', 'PLACA', 'LITROS', 'CUSTO TOTAL'.
        - **Base Interna**: CSV/Excel com colunas 'DATA', 'PLACA', 'QUANTIDADE DE LITROS'.
        - **Base Combustível**: CSV/Excel com colunas 'EMISSÃO', 'VALOR'.
        """)
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

    # --- Validação de Colunas Obrigatórias ---
    colunas_obrigatorias = {
        'Base Externa': ['DATA', 'PLACA', 'LITROS', 'CUSTO TOTAL'],
        'Base Interna': ['DATA', 'PLACA', 'QUANTIDADE DE LITROS'],
        'Base Combustível': ['EMISSÃO', 'VALOR']
    }
    
    for df, nome in zip([df_ext, df_int, df_val], colunas_obrigatorias.keys()):
        colunas_faltantes = [col for col in colunas_obrigatorias[nome] if col not in df.columns]
        if colunas_faltantes:
            st.error(f"Colunas obrigatórias faltantes em {nome}: {', '.join(colunas_faltantes)}")
            return

    # --- Pré-processamento ---
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].astype(str).apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_ext = df_ext[df_ext['PLACA'].apply(validar_placa)]

    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int['QUANTIDADE DE LITROS'].astype(str).apply(tratar_litros), errors='coerce').fillna(0.0)
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_int = df_int[df_int['PLACA'].apply(validar_placa)]

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # --- Filtros Interativos ---
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

    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & (df_ext['DATA'].dt.date <= data_selecao[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & (df_int['DATA'].dt.date <= data_selecao[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_selecao[0]) & (df_val['DATA'].dt.date <= data_selecao[1])]

    st.sidebar.header("Filtros Gerais")
    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        filtro_combustivel = st.sidebar.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel)
    else:
        filtro_combustivel = 'Todos'

    placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
    filtro_placa = st.sidebar.selectbox('🚗 Placa:', ['Todas'] + placas)

    if filtro_combustivel != 'Todos' and combustivel_col:
        df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]
    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == filtro_placa]

    # --- Métricas Principais ---
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    # --- Abas de Análise ---
    tab1, tab2, tab3, tab4 = st.tabs([
        '📊 Resumo Geral',
        '🚚 Top 10 Veículos',
        '⚙️ Consumo Médio',
        '📈 Tendências Temporais'
    ])

    with tab1:
        st.markdown(f"### 📆 Período Selecionado: `{data_selecao[0].strftime('%d/%m/%Y')} a {data_selecao[1].strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('💸 Custo (Externo)', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros (Interno)', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
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
        consumo_medio['Classificação'] = consumo_medio['Km/L'].apply(classificar_consumo)
        consumo_medio = consumo_medio.sort_values('Km/L', ascending=False)

        st.markdown('### ⚙️ Consumo Médio por Veículo')
        outliers = consumo_medio[consumo_medio['Classificação'] == 'Outlier']
        if not outliers.empty:
            st.warning(f"⚠️ {len(outliers)} veículos com consumo anormal (verifique os dados):")
            st.dataframe(outliers)

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
        df_int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS':'sum'}).reset_index().rename(columns={'QUANTIDADE DE LITROS': 'QTDE_LITROS'})
        df_val_agg = df_val.groupby('DATA').agg({'VALOR':'sum'}).reset_index()

        fig_ext_litros = px.line(df_ext_agg, x='DATA', y='LITROS', markers=True,
                                 title='Litros Consumidos (Externo)', labels={'LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_ext_litros, use_container_width=True)

        fig_int_litros = px.line(df_int_agg, x='DATA', y='QTDE_LITROS', markers=True,
                                 title='Litros Consumidos (Interno)', labels={'QTDE_LITROS':'Litros', 'DATA':'Data'})
        st.plotly_chart(fig_int_litros, use_container_width=True)

if __name__ == '__main__':
    main()
