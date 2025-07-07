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

def normalizar_placa(placa):
    return str(placa).upper().replace('-', '').replace(' ', '').strip()

def remover_placas_invalidas(df):
    if 'PLACA' in df.columns:
        df['PLACA'] = df['PLACA'].apply(normalizar_placa)
        df = df[df['PLACA'].notna() & (df['PLACA'] != '')]
    return df

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

    # Padronizar colunas
    for df in [df_ext, df_int, df_val]:
        df.columns = df.columns.str.strip().str.upper()

    df_ext = remover_placas_invalidas(df_ext)
    df_int = remover_placas_invalidas(df_int)
    df_val = remover_placas_invalidas(df_val)

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')

    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    data_val_col = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    df_val['DATA'] = pd.to_datetime(df_val[data_val_col], dayfirst=True, errors='coerce')
    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Selecione o Período:', min_value=ini_min, max_value=fim_max,
                         value=(ini_min, fim_max), format='DD/MM/YYYY')

    # Filtro de datas
    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    # Filtro de combustível
    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    tipos_combustivel = []
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())

    with st.sidebar:
        st.header("Filtros Gerais")
        filtro_combustivel = st.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel) if tipos_combustivel else 'Todos'

        placas = pd.concat([df_ext['PLACA'], df_int['PLACA']])
        placas = placas.dropna().apply(normalizar_placa)
        placas = placas[~placas.isin(['-', 'CORREÇÃO'])]
        placas = sorted(placas.unique().tolist())
        filtro_placa = st.selectbox('🚗 Placa:', ['Todas'] + placas)

    # Aplicar filtros globais
    if filtro_combustivel != 'Todos':
        df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]
    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
        df_val = df_val[df_val['PLACA'] == filtro_placa] if 'PLACA' in df_val.columns else df_val

    # Preço médio por litro - Interno (placa '-')
    df_entrada = df_int[df_int['PLACA'] == '-'].copy()
    df_entrada_total = df_entrada.groupby('DATA')['QUANTIDADE DE LITROS'].sum().reset_index(name='litros_entrada')
    df_val_total = df_val.groupby('DATA')['VALOR_TOTAL'].sum().reset_index(name='valor_total')
    df_entrada_merge = pd.merge(df_entrada_total, df_val_total, on='DATA', how='inner')
    df_entrada_merge['PRECO_MEDIO_LITRO_INTERNO'] = df_entrada_merge.apply(
        lambda row: row['valor_total'] / row['litros_entrada'] if row['litros_entrada'] > 0 else 0, axis=1
    )

    # Preço médio externo
    df_ext_valid = df_ext[df_ext['LITROS'] > 0].copy()
    df_ext_valid['PRECO_LITRO'] = df_ext_valid['CUSTO TOTAL'] / df_ext_valid['LITROS']
    preco_medio_litro_externo = df_ext_valid['PRECO_LITRO'].mean()

    # KPIs
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int[df_int['PLACA'] != '-']['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR_TOTAL'].sum()
    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    tab1, tab2, tab3, tab4, tab5 = st.tabs(['📊 Resumo Geral', '🚚 Top 10 Veículos', '⚙️ Consumo Médio', '📈 Tendências', '💰 Preço Médio'])

    with tab1:
        st.markdown(f"### 📆 Período: `{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f} %')
        c2.metric('💸 Custo (Externo)', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros (Interno)', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f} %')
        c4.metric('💸 Custo (Interno)', f'R$ {valor_int:,.2f}')

    with tab2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int[df_int['PLACA'] != '-'].groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()
        col1, col2 = st.columns(2)
        col1.plotly_chart(px.bar(top_ext, y='PLACA', x='LITROS', orientation='h', title='🔹 Top 10 Externo'), use_container_width=True)
        col2.plotly_chart(px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h', title='🟢 Top 10 Interno'), use_container_width=True)

    with tab3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int[df_int['PLACA'] != '-'][['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
        ])
        df_comb = df_comb.dropna(subset=['placa', 'data', 'km_atual', 'litros']).sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']
        consumo_medio = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo': 'Km/L'})
        consumo_medio['Classificação'] = consumo_medio['Km/L'].apply(lambda x: 'Econômico' if x >= 6 else 'Normal' if x >= 3.5 else 'Ineficiente')
        st.dataframe(consumo_medio.sort_values('Km/L', ascending=False).style.format({'Km/L': '{:.2f}'}))

    with tab4:
        st.markdown("### 📈 Tendências Temporais")
        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS': 'sum', 'CUSTO TOTAL': 'sum'}).reset_index()
        df_int_agg = df_int[df_int['PLACA'] != '-'].groupby('DATA')['QUANTIDADE DE LITROS'].sum().reset_index()
        df_val_agg = df_val.groupby('DATA')['VALOR_TOTAL'].sum().reset_index()
        st.plotly_chart(px.line(df_ext_agg, x='DATA', y='LITROS', title='Litros Externos'), use_container_width=True)
        st.plotly_chart(px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', title='Custo Total Externo'), use_container_width=True)
        st.plotly_chart(px.line(df_int_agg, x='DATA', y='QUANTIDADE DE LITROS', title='Litros Internos'), use_container_width=True)
        st.plotly_chart(px.line(df_val_agg, x='DATA', y='VALOR_TOTAL', title='Custo Total Interno'), use_container_width=True)

    with tab5:
        st.markdown("### 💰 Preço Médio Pago por Litro")
        preco_medio_interno = df_entrada_merge['PRECO_MEDIO_LITRO_INTERNO'].mean()
        st.metric('🛢️ Interno (Diesel no Tanque)', f'R$ {preco_medio_interno:.2f}')
        st.metric('⛽ Externo (Postos)', f'R$ {preco_medio_litro_externo:.2f}')
        st.plotly_chart(px.line(df_entrada_merge, x='DATA', y='PRECO_MEDIO_LITRO_INTERNO', title='Preço Médio Interno'), use_container_width=True)
        st.plotly_chart(px.line(df_ext_valid, x='DATA', y='PRECO_LITRO', title='Preço Médio Externo'), use_container_width=True)

if __name__ == '__main__':
    main()
