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

def main():
    st.title('📊 Relatório Abastecimento Externo x Interno')

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

    df_ext.columns = df_ext.columns.str.strip().str.upper()
    df_int.columns = df_int.columns.str.strip().str.upper()
    df_val.columns = df_val.columns.str.strip().str.upper()

    if 'CONSUMO' in df_ext.columns:
        df_ext.rename(columns={'CONSUMO': 'litros'}, inplace=True)
        df_ext['litros'] = pd.to_numeric(df_ext['litros'], errors='coerce').fillna(0.0)
    else:
        st.error("Coluna 'CONSUMO' não encontrada na base externa.")
        return

    col_data_ext = next((c for c in df_ext.columns if 'DATA' in c), None)
    if not col_data_ext:
        st.error("Coluna de data não encontrada na base Externa.")
        return
    df_ext['DATA'] = pd.to_datetime(df_ext[col_data_ext], dayfirst=True, errors='coerce')

    col_data_int = next((c for c in df_int.columns if 'DATA' in c), None)
    if not col_data_int:
        st.error("Coluna de data não encontrada na base Interna.")
        return
    df_int['DATA'] = pd.to_datetime(df_int[col_data_int], dayfirst=True, errors='coerce')

    col_data_val = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    if not col_data_val:
        st.error("Coluna de data não encontrada na base de valores.")
        return
    df_val['DATA'] = pd.to_datetime(df_val[col_data_val], dayfirst=True, errors='coerce')

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']

    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()

    ini, fim = st.slider('Período', min_value=ini_min, max_value=fim_max, value=(ini_min, fim_max), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        tipos_disponiveis = sorted(df_ext[combustivel_col].dropna().unique())
        with st.expander('🔍 Tipo de Combustível (Externo)', expanded=False):
            combustiveis_escolhidos = st.multiselect('Tipo de Combustível:', options=tipos_disponiveis, default=tipos_disponiveis)
        df_ext = df_ext[df_ext[combustivel_col].isin(combustiveis_escolhidos)]

        tipo_combustivel_int = next((col for col in df_int.columns if 'TIPO' in col or 'DESCRI' in col), None)
        if tipo_combustivel_int:
            df_int[tipo_combustivel_int] = df_int[tipo_combustivel_int].astype(str).str.strip().str.upper()
            df_int = df_int[df_int[tipo_combustivel_int].isin([t.upper() for t in combustiveis_escolhidos])]
    else:
        st.warning('⚠️ Coluna de descrição de combustível não encontrada.')

    df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['placa'] = df_int['PLACA'].astype(str).str.upper().str.strip()

    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['valor_ext'] = pd.to_numeric(df_ext.get('CUSTO TOTAL'), errors='coerce').fillna(0.0)

    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['litros'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    val_col = next((col for col in df_val.columns if 'VALOR' in col), None)
    df_val['valor_int'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['valor_ext'].sum()
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor_int'].sum()
    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros) * 100 if total_litros > 0 else 0
    perc_int = (litros_int / total_litros) * 100 if total_litros > 0 else 0

    tab1, tab2, tab3 = st.tabs(['✔️ Resumo', '🔝 Top 10', '🔍 Consumo Médio'])

    with tab1:
        st.subheader(f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")})
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

        fig = px.bar(df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group', text_auto='.2s',
                     color_discrete_map={'Externo': '#636EFA', 'Interno': '#EF553B'})
        fig.update_traces(marker_line_width=1.5, marker_line_color='white', textfont_size=14)
        fig.update_layout(title='Comparativo Externo vs Interno', title_font_size=20, 
                          plot_bgcolor='#f9f9f9', paper_bgcolor='white', 
                          font=dict(size=14), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('🔝 Top 10 Veículos por Litros')
        top_ext = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(top_ext, y='placa', x='litros', orientation='h', title='Externo',
                          color='litros', color_continuous_scale='Blues', text_auto='.2s')
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(top_int, y='placa', x='litros', orientation='h', title='Interno',
                          color='litros', color_continuous_scale='Greens', text_auto='.2s')
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('🔍 Consumo Médio (Km/L)')
        df_comb = pd.concat([
            df_ext[['placa', 'DATA', 'KM ATUAL', 'litros']].rename(columns={'DATA': 'data', 'KM ATUAL': 'km_atual'}),
            df_int[['placa', 'DATA', 'KM ATUAL', 'litros']].rename(columns={'DATA': 'data', 'KM ATUAL': 'km_atual'})
        ]).dropna()

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
