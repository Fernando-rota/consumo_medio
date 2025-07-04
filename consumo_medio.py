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
    st.markdown('Dashboard com dados comparativos entre abastecimentos externos e internos.')

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

    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce')
    col_dt_val = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    df_val['data'] = pd.to_datetime(df_val[col_dt_val], dayfirst=True, errors='coerce') if col_dt_val else pd.NaT

    df_int = df_int[df_int['Placa'].astype(str).str.strip() != '-']

    ini_min = min(df_ext['data'].min(), df_int['data'].min(), df_val['data'].min()).date()
    fim_max = max(df_ext['data'].max(), df_int['data'].max(), df_val['data'].max()).date()

    ini, fim = st.slider(
        'Período',
        min_value=ini_min,
        max_value=fim_max,
        value=(ini_min, fim_max),
        format='DD/MM/YYYY'
    )

    df_ext = df_ext[(df_ext['data'].dt.date >= ini) & (df_ext['data'].dt.date <= fim)]
    df_int = df_int[(df_int['data'].dt.date >= ini) & (df_int['data'].dt.date <= fim)]
    df_val = df_val[(df_val['data'].dt.date >= ini) & (df_val['data'].dt.date <= fim)]

    # Filtro por tipo de combustível (Externo)
    combustivel_col = next((col for col in df_ext.columns if 'descri' in col.lower()), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        tipos_disponiveis = sorted(df_ext[combustivel_col].dropna().unique())

        combustiveis_selecionados = st.multiselect(
            '🔍 Filtrar por Tipo de Combustível (Externo)',
            options=tipos_disponiveis,
            default=tipos_disponiveis
        )

        df_ext = df_ext[df_ext[combustivel_col].isin(combustiveis_selecionados)]
    else:
        st.warning('⚠️ Coluna com descrição do abastecimento não encontrada para filtro de combustível.')

    # Normalização
    df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['placa'] = df_int['Placa'].astype(str).str.upper().str.strip()

    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce').fillna(0)
    df_ext['km_atual'] = pd.to_numeric(df_ext.get('KM ATUAL', pd.Series()), errors='coerce')
    df_int['km_atual'] = pd.to_numeric(df_int.get('KM Atual', pd.Series()), errors='coerce')
    df_ext['valor_ext'] = df_ext.get('CUSTO TOTAL', pd.Series()).apply(tratar_valor)

    val_cols = [c for c in df_val.columns if 'valor' in c.lower()]
    df_val['valor_int'] = df_val[val_cols[0]].apply(tratar_valor) if val_cols else 0.0

    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['valor_ext'].sum()
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor_int'].sum()

    tab1, tab2, tab3 = st.tabs(['✔️ Resumo', '🔝 Top 10', '🔍 Consumo Médio'])

    with tab1:
        st.subheader(f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('⛽ Litros Ext.', f'{litros_ext:,.2f} L')
        c2.metric('💰 Custo Ext.', f'R$ {valor_ext:,.2f}')
        c3.metric('⛽ Litros Int.', f'{litros_int:,.2f} L')
        c4.metric('💰 Custo Int.', f'R$ {valor_int:,.2f}')

        df_kpi = pd.DataFrame({
            'Métrica': ['Litros', 'Custo'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')

        fig = px.bar(
            df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group',
            text_auto='.2s', color_discrete_map={'Externo': '#4C78A8', 'Interno': '#72B7B2'}
        )
        fig.update_traces(marker_line_width=1.5, marker_line_color='white', textfont_size=14)
        fig.update_layout(
            title='Comparativo Externo vs Interno',
            title_font_size=20,
            plot_bgcolor='rgba(240,240,240,0.5)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis_tickformat=',.2f',
            margin=dict(l=40, r=40, t=50, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('🔝 Top 10 Veículos por Litros')
        te = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(te, y='placa', x='litros', orientation='h', color='litros',
                          title='Externo', color_continuous_scale='Blues', text_auto='.2s')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(ti, y='placa', x='litros', orientation='h', color='litros',
                          title='Interno', color_continuous_scale='Greens', text_auto='.2s')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('🔍 Consumo Médio (Km/L)')
        df_comb = pd.concat([
            df_ext[['placa', 'data', 'km_atual', 'litros']],
            df_int[['placa', 'data', 'km_atual', 'litros']]
        ]).dropna()

        df_comb = df_comb.sort_values(['placa', 'data']).reset_index(drop=True)
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['km_l'] = df_comb['km_diff'] / df_comb['litros']
        consumo_medio = df_comb.groupby('placa')['km_l'].mean().reset_index().rename(columns={'km_l': 'Km/L'})

        fig3 = px.bar(consumo_medio, x='Km/L', y='placa', orientation='h', color='Km/L',
                      color_continuous_scale='Viridis', text_auto='.2f',
                      title='Eficiência Média por Veículo')
        fig3.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

        with st.expander("🔎 Tabela detalhada"):
            st.dataframe(consumo_medio.style.format({'Km/L': '{:.2f}'}), use_container_width=True)

if __name__ == '__main__':
    main()
