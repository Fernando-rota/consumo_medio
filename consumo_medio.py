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
        df = df[df['PLACA'].notna() & (df['PLACA'] != '') & (df['PLACA'] != '-') & (df['PLACA'] != 'CORRECAO')]
    return df

def validar_data_coluna(df, col_prefixes=['EMISSÃO', 'DATA', 'DT']):
    for prefix in col_prefixes:
        for c in df.columns:
            if prefix in c:
                try:
                    df['DATA'] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
                    if df['DATA'].notna().any():
                        return True
                except:
                    pass
    return False

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

    # Padronizar colunas e remover placas inválidas
    for df in [df_ext, df_int, df_val]:
        df.columns = df.columns.str.strip().str.upper()

    df_ext = remover_placas_invalidas(df_ext)
    df_int = remover_placas_invalidas(df_int)
    df_val = remover_placas_invalidas(df_val)

    # Validar colunas mínimas e obrigatórias
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

    # Na base valores, priorizar coluna de data 'EMISSÃO', depois 'DATA'
    col_data_val = None
    for prefix in ['EMISSÃO', 'DATA', 'DT']:
        for c in df_val.columns:
            if prefix in c:
                col_data_val = c
                break
        if col_data_val:
            break
    if not col_data_val:
        st.error("Coluna de data não encontrada na base de valores.")
        return
    df_val['DATA'] = pd.to_datetime(df_val[col_data_val], dayfirst=True, errors='coerce')

    # Remover linhas com DATA inválida
    df_ext = df_ext[df_ext['DATA'].notna()]
    df_int = df_int[df_int['DATA'].notna()]
    df_val = df_val[df_val['DATA'].notna()]

    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Selecione o Período:', min_value=ini_min, max_value=fim_max,
                        value=(ini_min, fim_max), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].str.lower().isin(['nan', '', 'none'])]
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
    else:
        st.warning('⚠️ Coluna de tipo de combustível não encontrada na base externa.')
        tipos_combustivel = []

    with st.sidebar:
        st.header("Filtros Gerais")

        filtro_combustivel = st.multiselect(
            '🛢️ Tipo de Combustível:', options=tipos_combustivel, default=tipos_combustivel)

        placas_raw = pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique()
        placas = sorted([p for p in set(placas_raw) if p not in ('', '-', 'CORRECAO')])

        filtro_placas = st.multiselect('🚗 Placa:', options=placas, default=placas)

        if st.button('🔄 Limpar filtros'):
            filtro_combustivel = tipos_combustivel
            filtro_placas = placas

    # Aplicar filtro combustível múltiplo
    if filtro_combustivel:
        df_ext = df_ext[df_ext[combustivel_col].isin(filtro_combustivel)]
    else:
        # Nenhum combustível selecionado = vazio
        df_ext = df_ext.iloc[0:0]

    # Aplicar filtro placas múltiplo
    if filtro_placas:
        df_ext = df_ext[df_ext['PLACA'].isin(filtro_placas)]
        df_int = df_int[df_int['PLACA'].isin(filtro_placas)]

        if 'PLACA' in df_val.columns:
            df_val['PLACA'] = df_val['PLACA'].apply(normalizar_placa)
            df_val = df_val[df_val['PLACA'].isin(filtro_placas)]
        else:
            st.warning("⚠️ A base de valores não contém a coluna 'PLACA'. Filtro de placa não aplicado nessa base.")
    else:
        # Nenhuma placa selecionada = vazio
        df_ext = df_ext.iloc[0:0]
        df_int = df_int.iloc[0:0]
        df_val = df_val.iloc[0:0]

    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()

    # Base interna: separar entrada (placa '-' ou vazio) e saída
    df_int_entrada = df_int[df_int['PLACA'].isin(['', '-'])]
    df_int_saida = df_int[~df_int.index.isin(df_int_entrada.index)]

    litros_int_entrada = df_int_entrada['QUANTIDADE DE LITROS'].sum()
    litros_int_saida = df_int_saida['QUANTIDADE DE LITROS'].sum()

    valor_int = df_val['VALOR_TOTAL'].sum()

    total_litros = litros_ext + litros_int_saida
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int_saida / total_litros * 100) if total_litros > 0 else 0

    preco_medio_int = valor_int / litros_int_entrada if litros_int_entrada > 0 else 0
    preco_medio_ext = valor_ext / litros_ext if litros_ext > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumo Geral', '🚚 Top 10 Veículos', '⚙️ Consumo Médio', '📈 Tendências Temporais'])

    with tab1:
        st.markdown(f"### 📆 Período Selecionado: `{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}`")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f} %')
        c2.metric('💸 Custo (Externo)', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros Entrada (Interno)', f'{litros_int_entrada:,.2f} L')
        c4.metric('⛽ Litros Saída (Interno)', f'{litros_int_saida:,.2f} L', delta=f'{perc_int:.1f} %')
        c5.metric('💸 Custo (Interno)', f'R$ {valor_int:,.2f}')
        c6.metric('💰 Preço Médio (R$/L)', f'Externo: R$ {preco_medio_ext:.3f}\nInterno: R$ {preco_medio_int:.3f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo', 'Preço Médio (R$/L)'],
            'Externo': [litros_ext, valor_ext, preco_medio_ext],
            'Interno': [litros_int_saida, valor_int, preco_medio_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        # Gráfico agrupado com preços médios em escala secundária por métrica?
        fig = px.bar(df_kpi[df_kpi['Métrica'] != 'Preço Médio (R$/L)'],
                     x='Métrica', y='Valor', color='Tipo', barmode='group',
                     text=df_kpi[df_kpi['Métrica'] != 'Preço Médio (R$/L)']
                     .apply(lambda r: f"R$ {r['Valor']:,.2f}" if r['Métrica'] == 'Custo' else f"{r['Valor']:,.2f} L", axis=1),
                     color_discrete_map={'Externo': '#1f77b4', 'Interno': '#2ca02c'})
        st.plotly_chart(fig, use_container_width=True)

        # Gráfico preço médio externo vs interno
        df_preco = pd.DataFrame({
            'Tipo': ['Externo', 'Interno'],
            'Preço Médio R$/L': [preco_medio_ext, preco_medio_int]
        })
        fig_precos = px.bar(df_preco, x='Tipo', y='Preço Médio R$/L', text='Preço Médio R$/L',
                            color='Tipo', color_discrete_map={'Externo': '#1f77b4', 'Interno': '#2ca02c'},
                            title='💰 Preço Médio do Combustível')
        fig_precos.update_traces(texttemplate='R$ %{text:.3f}', textposition='outside')
        st.plotly_chart(fig_precos, use_container_width=True)

    with tab2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int_saida.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h',
                      title='🔹 Top 10 Externo', color='LITROS', color_continuous_scale='Blues', text_auto='.2s')
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
        col1.plotly_chart(fig1, use_container_width=True)

        fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                      title='🟢 Top 10 Interno', color='QUANTIDADE DE LITROS', color_continuous_scale='Greens', text_auto='.2s')
        fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
        col2.plotly_chart(fig2, use_container_width=True)

    with tab3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int_saida[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
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
        col1.dataframe(consumo_medio.style.format({'Km/L': '{:.2f}'}).set_properties(**{'text-align': 'center'}))

        fig3 = px.bar(consumo_medio, x='Km/L', y='placa', orientation='h',
                      color='Km/L', color_continuous_scale='Viridis', text_auto='.2f',
                      title='Eficiência por Veículo (Km/L)')
        fig3.update_layout(yaxis={'categoryorder': 'total descending'})
        col2.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.markdown("### 📈 Tendência de Consumo, Custo e Preço Médio ao longo do Tempo")

        df_ext_agg = df_ext.groupby('DATA').agg({'LITROS': 'sum', 'CUSTO TOTAL': 'sum'}).reset_index()
        df_int_agg = df_int_saida.groupby('DATA').agg({'QUANTIDADE DE LITROS': 'sum'}).reset_index()
        df_val_agg = df_val.groupby('DATA').agg({'VALOR_TOTAL': 'sum'}).reset_index()

        df_preco_medio_int = pd.merge(df_val_agg, df_int_agg, on='DATA', how='inner')
        df_preco_medio_int['PRECO_MEDIO'] = df_preco_medio_int.apply(
            lambda row: row['VALOR_TOTAL'] / row['QUANTIDADE DE LITROS'] if row['QUANTIDADE DE LITROS'] > 0 else 0, axis=1)

        st.plotly_chart(px.line(df_ext_agg, x='DATA', y='LITROS', markers=True, title='Litros Consumidos (Externo)'), use_container_width=True)
        st.plotly_chart(px.line(df_ext_agg, x='DATA', y='CUSTO TOTAL', markers=True, title='Custo Total (Externo)'), use_container_width=True)
        st.plotly_chart(px.line(df_int_agg, x='DATA', y='QUANTIDADE DE LITROS', markers=True, title='Litros Consumidos (Interno)'), use_container_width=True)
        st.plotly_chart(px.line(df_val_agg, x='DATA', y='VALOR_TOTAL', markers=True, title='Custo Total (Interno)'), use_container_width=True)
        st.plotly_chart(px.line(df_preco_medio_int, x='DATA', y='PRECO_MEDIO', markers=True, title='Preço Médio do Combustível (Interno) [R$/Litro]'), use_container_width=True)

if __name__ == '__main__':
    main()
