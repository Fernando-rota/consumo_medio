# [IMPORTAÇÕES E CONFIGURACOES INICIAIS]
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

# ========== FUNÇÕES ==========
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

def classificar_eficiencia(km_l):
    if km_l >= 6:
        return 'Econômico'
    elif km_l >= 3.5:
        return 'Normal'
    else:
        return 'Ineficiente'

# ========== APP PRINCIPAL ==========
def main():
    st.markdown("<h1 style='text-align:center;'>⛽ Abastecimento Interno vs Externo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Análise comparativa, consumo e eficiência</p>", unsafe_allow_html=True)

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

    df_ext.rename(columns={'CONSUMO': 'LITROS'}, inplace=True)
    df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')

    df_int = df_int[df_int['PLACA'].astype(str).str.strip() != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')

    data_val_col = next((c for c in df_val.columns if 'DATA' in c or 'DT.' in c), None)
    df_val['DATA'] = pd.to_datetime(df_val[data_val_col], dayfirst=True, errors='coerce')

    ini_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    fim_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    ini, fim = st.slider('📅 Período:', min_value=ini_min, max_value=fim_max, value=(ini_min, fim_max), format='DD/MM/YYYY')

    df_ext = df_ext[(df_ext['DATA'].dt.date >= ini) & (df_ext['DATA'].dt.date <= fim)]
    df_int = df_int[(df_int['DATA'].dt.date >= ini) & (df_int['DATA'].dt.date <= fim)]
    df_val = df_val[(df_val['DATA'].dt.date >= ini) & (df_val['DATA'].dt.date <= fim)]

    combustivel_col = next((col for col in df_ext.columns if 'DESCRIÇÃO' in col or 'DESCRI' in col), None)
    if combustivel_col:
        df_ext[combustivel_col] = df_ext[combustivel_col].astype(str).str.strip()
        df_ext = df_ext[~df_ext[combustivel_col].isin(['', 'nan', 'NaN'])]
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        combustivel_escolhido = st.radio('🛢️ Tipo de Combustível (Externo):', options=tipos_combustivel, horizontal=True)
        df_ext = df_ext[df_ext[combustivel_col] == combustivel_escolhido]

    # Normalizar placas: remover espaços internos e externos, deixar maiúsculas
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.replace(' ', '').str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.replace(' ', '').str.strip()
    df_val['PLACA'] = df_val['PLACA'].astype(str).str.upper().str.replace(' ', '').str.strip()

    df_ext['KM ATUAL'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_int['KM ATUAL'] = pd.to_numeric(df_int.get('KM ATUAL'), errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int.get('QUANTIDADE DE LITROS'), errors='coerce').fillna(0.0)

    val_col = next((c for c in df_val.columns if 'VALOR' in c), None)
    df_val['VALOR_TOTAL'] = df_val[val_col].apply(tratar_valor) if val_col else 0.0

    placas = sorted(set(df_ext['PLACA'].unique()).union(df_int['PLACA'].unique()))
    placa_filtro = st.selectbox('🚗 Filtrar por Veículo (opcional):', options=['Todos'] + placas)
    if placa_filtro != 'Todos':
        df_ext = df_ext[df_ext['PLACA'] == placa_filtro]
        df_int = df_int[df_int['PLACA'] == placa_filtro]

    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR_TOTAL'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumo', '🚚 Top 10', '⚙️ Consumo Médio', '📅 Tendências'])

    with tab1:
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

        fig_resumo = px.bar(
            df_kpi,
            x='Métrica',
            y='Valor',
            color='Tipo',
            barmode='group',
            text_auto='.2s',
            title='🔎 Comparativo Geral Externo vs Interno'
        )
        fig_resumo.update_layout(yaxis_title='', xaxis_title='')
        st.plotly_chart(fig_resumo, use_container_width=True)

    with tab2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()
        col1, col2 = st.columns(2)
        fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h', title='🔹 Top 10 Externo', text_auto='.2f')
        fig1.update_layout(yaxis_title='', xaxis_title='Litros', yaxis=dict(categoryorder='total ascending'))
        fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h', title='🟢 Top 10 Interno', text_auto='.2f')
        fig2.update_layout(yaxis_title='', xaxis_title='Litros', yaxis=dict(categoryorder='total ascending'))
        col1.plotly_chart(fig1, use_container_width=True)
        col2.plotly_chart(fig2, use_container_width=True)

    with tab3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
        ])
        df_comb = df_comb.dropna(subset=['placa', 'data', 'km_atual', 'litros']).sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff'] > 0]
        df_comb['consumo'] = df_comb['km_diff'] / df_comb['litros']

        consumo_medio = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo': 'Km/L'})
        consumo_medio['Classificação'] = consumo_medio['Km/L'].apply(classificar_eficiencia)
        consumo_medio = consumo_medio.sort_values(by='Km/L', ascending=False)
        st.dataframe(consumo_medio, use_container_width=True)

    with tab4:
        df_ext['MÊS'] = df_ext['DATA'].dt.to_period('M').astype(str)
        df_int['MÊS'] = df_int['DATA'].dt.to_period('M').astype(str)
        df_val['MÊS'] = df_val['DATA'].dt.to_period('M').astype(str)

        resumo_mes = pd.DataFrame({
            'Mês': sorted(set(df_ext['MÊS']).union(df_int['MÊS']).union(df_val['MÊS']))
        })
        resumo_mes['Litros Externo'] = resumo_mes['Mês'].map(df_ext.groupby('MÊS')['LITROS'].sum())
        resumo_mes['Litros Interno'] = resumo_mes['Mês'].map(df_int.groupby('MÊS')['QUANTIDADE DE LITROS'].sum())
        resumo_mes['Custo Interno Diesel'] = resumo_mes['Mês'].map(df_val.groupby('MÊS')['VALOR_TOTAL'].sum())

        fig4 = px.line(resumo_mes, x='Mês', y=['Litros Externo', 'Litros Interno'],
                       markers=True, title='📈 Tendência Mensal de Abastecimento')
        st.plotly_chart(fig4, use_container_width=True)

        fig5 = px.line(resumo_mes, x='Mês', y='Custo Interno Diesel', markers=True, title='💰 Custo Total Mensal (Diesel Interno)')
        st.plotly_chart(fig5, use_container_width=True)

        df_ext['R$/L'] = df_ext['CUSTO TOTAL'] / df_ext['LITROS']
        custo_mensal = df_ext.groupby('MÊS')['R$/L'].mean().reset_index()
        fig6 = px.line(custo_mensal, x='MÊS', y='R$/L', markers=True, title='💰 Custo Médio por Litro (Externo)')
        st.plotly_chart(fig6, use_container_width=True)

if __name__ == '__main__':
    main()
