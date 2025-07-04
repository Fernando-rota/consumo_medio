import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Abastecimento Externo x Interno', layout='wide')

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
    st.title('📊 Relatório Abastecimento Externo x Interno')

    with st.expander('📥 Carregar bases'):
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Base Externa', type=['csv', 'xlsx'])
        up_int = c2.file_uploader('Base Interna', type=['csv', 'xlsx'])
        up_val = c3.file_uploader('Base Combustível (Valores)', type=['csv', 'xlsx'])

    if not (up_ext and up_int and up_val):
        st.info('Envie as três bases antes de prosseguir.')
        return

    df_ext = carregar_base(up_ext, 'Base Externa')
    df_int = carregar_base(up_int, 'Base Interna')
    df_val = carregar_base(up_val, 'Base Combustível (Valores)')

    if df_ext is None or df_int is None or df_val is None:
        return

    # Padronizar colunas
    df_ext.columns = df_ext.columns.str.strip().str.upper()
    df_int.columns = df_int.columns.str.strip().str.upper()
    df_val.columns = df_val.columns.str.strip().str.upper()

    # Renomear 'CONSUMO' para 'LITROS' na base externa e converter para float
    if 'CONSUMO' in df_ext.columns:
        df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
        df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    else:
        st.error("Coluna 'CONSUMO' não encontrada na base externa.")
        return

    # Converter datas para datetime
    if 'DATA' not in df_ext.columns:
        st.error("Coluna 'DATA' não encontrada na base externa.")
        return
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')

    if 'DATA' not in df_int.columns:
        st.error("Coluna 'DATA' não encontrada na base interna.")
        return
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')

    # Na base de valores, coluna data pode ser 'DT. VENCIMENTO'
    data_val_col = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    if not data_val_col:
        st.error("Coluna de data não encontrada na base de valores.")
        return
    df_val['DATA'] = pd.to_datetime(df_val[data_val_col], dayfirst=True, errors='coerce')

    # Filtrar base interna, remover placa '-'
    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']

    # Selecionar período disponível
    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()

    ini, fim = st.slider('Período', min_value=ini_min, max_value=fim_max, value=(ini_min, fim_max), format='DD/MM/YYYY')

    # Filtrar por período
    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    # Filtro por tipo de combustível (base externa)
    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        combustiveis_selecionados = st.multiselect(
            '🔍 Filtrar por Tipo de Combustível (Externo)',
            options=tipos_combustivel,
            default=tipos_combustivel
        )
        df_ext = df_ext[df_ext[combustivel_col].isin(combustiveis_selecionados)]
    else:
        st.warning('Coluna de descrição do combustível não encontrada na base externa.')

    # Normalizar colunas
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()

    # Converter colunas numéricas
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    # Coluna valor total da base combustível
    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    if val_col:
        df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor)
    else:
        st.warning("Coluna 'Valor Total' não encontrada na base de valores.")
        df_val['VALOR_TOTAL'] = 0.0

    # Somar KPIs
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR_TOTAL'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    # Tabs para visualização
    tab1, tab2, tab3 = st.tabs(['✔️ Resumo', '🔝 Top 10', '🔍 Consumo Médio'])

    with tab1:
        st.subheader(f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ Litros Ext.', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        c2.metric('💰 Custo Ext.', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros Int.', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        c4.metric('💰 Custo Int.', f'R$ {valor_int:,.2f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        fig = px.bar(df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group', text_auto='.2s')
        fig.update_traces(marker_line_width=1.5, marker_line_color='white', textfont_size=14)
        fig.update_layout(title='Comparativo Externo vs Interno', title_font_size=20)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('🔝 Top 10 Veículos por Litros Abastecidos')

        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h', title='Externo',
                          color='LITROS', color_continuous_scale='Blues', text_auto='.2s')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h', title='Interno',
                          color='QUANTIDADE DE LITROS', color_continuous_scale='Greens', text_auto='.2s')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('🔍 Consumo Médio (Km/L)')

        # Preparar dados para consumo médio
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
        ]).dropna(subset=['placa', 'data', 'km_atual', 'litros'])

        df_comb = df_comb.sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']

        consumo_medio = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo': 'Km/L'})

        fig3 = px.bar(consumo_medio, x='Km/L', y='placa', orientation='h', color='Km/L',
                      color_continuous_scale='Viridis', text_auto='.2f', title='Eficiência por Veículo')
        fig3.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
