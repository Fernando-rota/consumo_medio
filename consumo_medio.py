import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

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

    if 'EMISSÃO' not in df_val.columns or 'VALOR' not in df_val.columns or 'TIPO' not in df_val.columns or 'QUANTIDADE DE LITROS' not in df_val.columns:
        st.error("A base de valores deve conter as colunas 'EMISSÃO', 'VALOR', 'TIPO' e 'QUANTIDADE DE LITROS'.")
        return

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)
    # Ensure 'QUANTIDADE DE LITROS' is numeric and handle NaNs
    df_val['QUANTIDADE DE LITROS'] = pd.to_numeric(df_val['QUANTIDADE DE LITROS'], errors='coerce').fillna(0.0)
    df_val['TIPO'] = df_val['TIPO'].astype(str).str.upper().str.strip() # Normalize 'TIPO' column

    df_ext.dropna(subset=['DATA'], inplace=True)
    df_int.dropna(subset=['DATA'], inplace=True)
    df_val.dropna(subset=['DATA'], inplace=True)

    st.sidebar.header('📅 Filtro de Data')

    all_dates = pd.concat([df_ext['DATA'], df_int['DATA'], df_val['DATA']]).dropna()
    min_data_available = all_dates.min().date() if not all_dates.empty else datetime.date(2023, 1, 1)
    max_data_available = all_dates.max().date() if not all_dates.empty else datetime.date.today()

    default_start_date = min_data_available
    default_end_date = max_data_available

    opcoes_periodo = [
        'Intervalo Personalizado',
        'Hoje',
        'Ontem',
        'Últimos 7 Dias',
        'Últimos 30 Dias',
        'Este Mês',
        'Mês Passado',
        'Este Ano'
    ]

    periodo_selecionado = st.sidebar.selectbox('Período Rápido:', opcoes_periodo, index=0)

    today = datetime.date.today()
    start_date_filter = min_data_available
    end_date_filter = max_data_available

    if periodo_selecionado == 'Hoje':
        start_date_filter = today
        end_date_filter = today
    elif periodo_selecionado == 'Ontem':
        start_date_filter = today - datetime.timedelta(days=1)
        end_date_filter = today - datetime.timedelta(days=1)
    elif periodo_selecionado == 'Últimos 7 Dias':
        start_date_filter = today - datetime.timedelta(days=6)
        end_date_filter = today
    elif periodo_selecionado == 'Últimos 30 Dias':
        start_date_filter = today - datetime.timedelta(days=29)
        end_date_filter = today
    elif periodo_selecionado == 'Este Mês':
        start_date_filter = today.replace(day=1)
        end_date_filter = today
    elif periodo_selecionado == 'Mês Passado':
        first_day_prev_month = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        last_day_prev_month = today.replace(day=1) - datetime.timedelta(days=1)
        start_date_filter = first_day_prev_month
        end_date_filter = last_day_prev_month
    elif periodo_selecionado == 'Este Ano':
        start_date_filter = today.replace(month=1, day=1)
        end_date_filter = today

    if periodo_selecionado == 'Intervalo Personalizado':
        st.sidebar.markdown(
            "**Dica:** Para anos distantes, **digite a data** (ex: 01/01/2018) no campo abaixo."
        )
        data_selecao_manual = st.sidebar.date_input(
            'Ou selecione as datas manualmente:',
            value=(default_start_date, default_end_date),
            min_value=min_data_available,
            max_value=max_data_available
        )
        if len(data_selecao_manual) == 2:
            start_date_filter = data_selecao_manual[0]
            end_date_filter = data_selecao_manual[1]
        elif len(data_selecao_manual) == 1:
            start_date_filter = data_selecao_manual[0]
            end_date_filter = data_selecao_manual[0]
        else:
            pass

    start_date_filter = max(start_date_filter, min_data_available)
    end_date_filter = min(end_date_filter, max_data_available)

    df_ext = df_ext[(df_ext['DATA'].dt.date >= start_date_filter) & (df_ext['DATA'].dt.date <= end_date_filter)]
    df_int = df_int[(df_int['DATA'].dt.date >= start_date_filter) & (df_int['DATA'].dt.date <= end_date_filter)]
    df_val = df_val[(df_val['DATA'].dt.date >= start_date_filter) & (df_val['DATA'].dt.date <= end_date_filter)]


    # --- INÍCIO DAS ALTERAÇÕES PARA FILTRO DE PLACA E DUPLICATAS ---

    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]

    st.sidebar.header("Filtros Gerais")

    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        filtro_combustivel = st.sidebar.selectbox('🛢️ Tipo de Combustível:', ['Todos'] + tipos_combustivel)
    else:
        filtro_combustivel = 'Todos'

    # Correção: Remover duplicatas na lista de placas
    placas_ext = df_ext['PLACA'].dropna().unique()
    placas_int = df_int['PLACA'].dropna().unique()
    # Concatena e remove duplicatas para a lista de seleção
    todas_placas = pd.Series(list(placas_ext) + list(placas_int)).astype(str).str.upper().str.strip().drop_duplicates().sort_values().tolist()

    filtro_placa = st.sidebar.selectbox('🚗 Placa:', ['Todas'] + todas_placas)

    if filtro_combustivel != 'Todos' and combustivel_col:
        df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]

    # Aplica o filtro de placa apenas em df_ext e df_int
    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
    # --- FIM DAS ALTERAÇÕES PARA FILTRO DE PLACA E DUPLICATAS ---


    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    # --- Calculation for External Fuel ---
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()

    # --- Calculation for Internal Fuel (using 'TIPO' and 'QUANTIDADE DE LITROS' from df_val) ---
    # Filter df_val for 'entrada' transactions
    df_val_entrada = df_val[df_val['TIPO'] == 'ENTRADA'].copy()

    # Sum 'VALOR' and 'QUANTIDADE DE LITROS' only for 'entrada' transactions
    valor_int = df_val_entrada['VALOR'].sum()
    litros_int_bomba = df_val_entrada['QUANTIDADE DE LITROS'].sum() # Liters that entered the pump

    # Calculate internal average price based on pump entry
    preco_medio_int = valor_int / litros_int_bomba if litros_int_bomba > 0 else 0

    # For the "Litros (Interno)" KPI, it's still more relevant to show what was dispensed to vehicles
    # unless you explicitly want to show total pump entry here.
    # I'll keep it as dispensed to vehicles for clarity, but you can change it if preferred.
    litros_int_dispensado = df_int['QUANTIDADE DE LITROS'].sum()


    total_litros = litros_ext + litros_int_dispensado # Use dispensed liters for overall percentage
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int_dispensado / total_litros * 100) if total_litros > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs([
        '📊 Resumo Geral',
        '🚚 Top 10 Veículos',
        '⚙️ Consumo Médio',
        '📈 Tendências Temporais'
    ])

    with tab1:
        st.markdown(f"### 📆 Período Selecionado: "
                            f"`{start_date_filter.strftime('%d/%m/%Y')} a {end_date_filter.strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f} %')
        c2.metric('💸 Custo (Externo)', f'R$ {valor_ext:,.2f}')
        c3.metric('💲 Preço Médio (Externo)', f'R$ {preco_medio_ext:,.2f}/L')
        c4.metric('⛽ Litros (Interno - Abastecido)', f'{litros_int_dispensado:,.2f} L', delta=f'{perc_int:.1f} %') # Label updated
        c5.metric('💸 Custo (Interno - Total Compra)', f'R$ {valor_int:,.2f}') # Label updated
        c6.metric('💲 Preço Médio (Interno - Bomba)', f'R$ {preco_medio_int:,.2f}/L') # Label updated

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros (Externo)', 'Custo (Externo)', 'Litros (Interno - Abastecido)', 'Custo (Interno - Total Compra)'],
            'Valor': [litros_ext, valor_ext, litros_int_dispensado, valor_int]
        })
        fig = px.bar(
            df_kpi, x='Métrica', y='Valor',
            text=df_kpi.apply(lambda r: f"R$ {r['Valor']:,.2f}" if 'Custo' in r['Métrica'] else f"{r['Valor']:,.2f} L", axis=1),
            color='Métrica', # Use Métrica for color differentiation
            color_discrete_map={
                'Litros (Externo)': '#1f77b4', 'Custo (Externo)': '#1f77b4',
                'Litros (Interno - Abastecido)': '#2ca02c', 'Custo (Interno - Total Compra)': '#2ca02c'
            },
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
        st.markdown("### 📈 Tendência de Consumo, Custo e Preço Médio ao longo do Tempo")

        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS':'sum', 'CUSTO TOTAL':'sum'}).reset_index()

        # Aggregate 'entrada' transactions from df_val for internal pump liters and cost
        df_val_entrada_agg = df_val_entrada.groupby('DATA').agg({
            'VALOR':'sum',
            'QUANTIDADE DE LITROS':'sum'
        }).reset_index().rename(columns={'QUANTIDADE DE LITROS': 'QTDE_LITROS_BOMBA'})

        # Calculate internal average price temporal for 'entrada'
        if not df_val_entrada_agg.empty:
