import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações iniciais
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

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def tratar_valor(x):
    try:
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

def main():
    st.title('📊 Relatório Abastecimento Externo x Interno')
    st.markdown('Dashboard de análise de volume (litros) e custo (R$) de abastecimentos externos e internos.')

    with st.expander('📥 Carregar bases'):
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Externo', type=['csv', 'xlsx'])
        up_int = c2.file_uploader('Interno', type=['csv', 'xlsx'])
        up_val = c3.file_uploader('Valor Int.', type=['csv', 'xlsx'])

    if not (up_ext and up_int and up_val):
        st.info('Envie as três bases antes de prosseguir.')
        return

    df_ext = carregar_base(up_ext, 'Externo')
    df_int = carregar_base(up_int, 'Interno')
    df_val = carregar_base(up_val, 'Valor Int.')

    if df_ext is None or df_int is None or df_val is None:
        return

    # Datas min/max para slider
    def extrair_data(df, col_names):
        for col in col_names:
            if col in df.columns:
                try:
                    return pd.to_datetime(df[col], dayfirst=True, errors='coerce').dropna()
                except:
                    continue
        return pd.Series(dtype='datetime64[ns]')

    datas_ext = extrair_data(df_ext, ['DATA'])
    datas_int = extrair_data(df_int, ['Data'])
    datas_val = extrair_data(df_val, [c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()])

    if datas_ext.empty or datas_int.empty or datas_val.empty:
        st.error("Erro: Colunas de data não encontradas ou inválidas em uma ou mais bases.")
        return

    ini_min = min(datas_ext.min(), datas_int.min(), datas_val.min()).date()
    fim_max = max(datas_ext.max(), datas_int.max(), datas_val.max()).date()

    ini, fim = st.slider(
        'Período',
        min_value=ini_min,
        max_value=fim_max,
        value=(ini_min, fim_max),
        format='DD/MM/YYYY'
    )

    # Preparar dados e filtrar por data
    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce')
    col_dt_val = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    df_val['data'] = pd.to_datetime(df_val[col_dt_val], dayfirst=True, errors='coerce') if col_dt_val else pd.NaT

    df_ext = df_ext[(df_ext['data'].dt.date >= ini) & (df_ext['data'].dt.date <= fim)]
    df_int = df_int[(df_int['data'].dt.date >= ini) & (df_int['data'].dt.date <= fim)]
    df_val = df_val[(df_val['data'].dt.date >= ini) & (df_val['data'].dt.date <= fim)]

    # Normalizar colunas
    df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['placa'] = df_int['Placa'].astype(str).str.upper().str.strip()

    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce').fillna(0)

    df_ext['km_atual'] = pd.to_numeric(df_ext.get('KM ATUAL', pd.Series(dtype='float')), errors='coerce')
    df_int['km_atual'] = pd.to_numeric(df_int.get('KM Atual', pd.Series(dtype='float')), errors='coerce')

    df_ext['valor_ext'] = df_ext.get('CUSTO TOTAL', pd.Series(dtype='object')).apply(tratar_valor)
    # Detectar coluna valor em df_val (ex: 'Valor Total', 'ValorPago', etc)
    val_cols = [c for c in df_val.columns if 'valor' in c.lower()]
    if val_cols:
        df_val['valor_int'] = df_val[val_cols[0]].apply(tratar_valor)
    else:
        st.warning("Coluna de valor não encontrada em Valor Int.")
        df_val['valor_int'] = 0.0

    # KPIs
    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['valor_ext'].sum()
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor_int'].sum()

    # Abas
    tab1, tab2, tab3 = st.tabs(['✔️ Resumo', '🔝 Top10', '🔍 Consumo'])

    with tab1:
        st.subheader(f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        k1, k2, k3, k4 = st.columns(4)
        k1.metric('⛽ Litros Ext.', f'{litros_ext:,.2f} L')
        k2.metric('💰 Custo Ext.', f'R$ {valor_ext:,.2f}')
        k3.metric('⛽ Litros Int.', f'{litros_int:,.2f} L')
        k4.metric('💰 Custo Int.', f'R$ {valor_int:,.2f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        fig = px.bar(
            df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group',
            color_discrete_map={'Externo': '#1f77b4', 'Interno': '#2ca02c'},
            text_auto='.2s'
        )
        fig.update_traces(textposition='inside')
        fig.update_layout(
            title='Comparativo Externo vs Interno',
            title_font_size=16,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis_tickformat='~s',
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('Top 10 Litros')
        te = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()

        fig1 = px.bar(
            te, y='placa', x='litros', orientation='h', color='litros',
            title='Externo', color_continuous_scale='Blues', text_auto='.2s'
        )
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')

        fig2 = px.bar(
            ti, y='placa', x='litros', orientation='h', color='litros',
            title='Interno', color_continuous_scale='Greens', text_auto='.2s'
        )
        fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('Consumo Médio (Km/L)')

        if df_ext['km_atual'].isna().all() or df_int['km_atual'].isna().all():
            st.warning('Coluna km_atual ausente em algum conjunto; consumo não calculado.')
            return

        df_comb = pd.concat([
            df_ext[['placa', 'data', 'km_atual', 'litros']],
            df_int[['placa', 'data', 'km_atual', 'litros']]
        ]).dropna()

        df_comb = df_comb.sort_values(['placa', 'data']).reset_index(drop=True)
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()

        df_comb = df_comb[df_comb['km_diff'] > 0].copy()
        # Corrigido: consumo = km / litros
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']

        cm = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo': 'Km/L'})

        fig3 = px.bar(
            cm, x='Km/L', y='placa', orientation='h', color='Km/L',
            title='Eficiência de Combustível', color_continuous_scale='Purples', text_auto='.2s'
        )
        fig3.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
