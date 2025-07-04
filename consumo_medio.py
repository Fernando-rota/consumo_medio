import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações iniciais
st.set_page_config(page_title='Abastecimento Externo x Interno', layout='wide')

@st.cache_data
# Função de carregamento com cache
def carregar_base(uploaded_file, nome):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            except:
                df = pd.read_csv(uploaded_file, sep=';', engine='python')
        else:
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

# Conversão de valores

def tratar_litros(x):
    try: return float(str(x).replace('.', '').replace(',', '.'))
    except: return 0.0

def tratar_valor(x):
    try: return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except: return 0.0

# Função principal

def main():
    st.title('📊 Relatório Abastecimento Externo x Interno')
    st.markdown('''
    Este dashboard apresenta o volume de litros e o custo de abastecimentos externos e internos
    para análise gerencial.
    ''')

    # Upload dentro de expander
    with st.expander('🔽 Carregar bases de dados'):
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Externo', type=['csv','xlsx'])
        up_int = c2.file_uploader('Interno', type=['csv','xlsx'])
        up_val = c3.file_uploader('Valor Comb. Int.', type=['csv','xlsx'])
    if not (up_ext and up_int and up_val):
        st.info('Envie as três bases antes de prosseguir.')
        return

    # Carregar DataFrames
    df_ext = carregar_base(up_ext, 'Externo')
    df_int = carregar_base(up_int, 'Interno')
    df_val = carregar_base(up_val, 'Valor Comb. Int.')
    if df_ext is None or df_int is None or df_val is None:
        return

    # Definir período usando slider com domínio
    min_date = min(
        pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').min(),
        pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').min()
    )
    max_date = max(
        pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').max(),
        pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').max()
    )
    ini, fim = st.slider(
        'Selecione o Período',
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=(min_date.date(), max_date.date()),
        format='DD/MM/YYYY'
    )

    # Converter e filtrar datas
    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').dt.date
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').dt.date
    col_dt = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if not col_dt:
        st.error('Coluna de data não encontrada em Valor Comb. Int.')
        return
    df_val['data'] = pd.to_datetime(df_val[col_dt], dayfirst=True, errors='coerce').dt.date

    df_ext = df_ext[(df_ext['data'] >= ini) & (df_ext['data'] <= fim)]
    df_int = df_int[(df_int['data'] >= ini) & (df_int['data'] <= fim)]
    df_val = df_val[(df_val['data'] >= ini) & (df_val['data'] <= fim)]

    # Criar coluna placa
    if 'PLACA' in df_ext.columns:
        df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    if 'Placa' in df_int.columns:
        df_int['placa'] = df_int['Placa'].astype(str).str.upper().str.strip()

    # Tratar valores e litros
    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
    df_val['valor'] = df_val['Valor Total'].apply(tratar_valor)

    # Cálculos principais
    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in df_ext.columns else 0
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor'].sum()

    # Renderizar abas
    tab1, tab2, tab3 = st.tabs(['Resumo','Top10','Consumo'])

    with tab1:
        st.subheader(f'Resumo de {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric('Litros Externo', f'{litros_ext:,.2f} L')
        k2.metric('Valor Externo', f'R$ {valor_ext:,.2f}')
        k3.metric('Litros Interno', f'{litros_int:,.2f} L')
        k4.metric('Valor Interno', f'R$ {valor_int:,.2f}')
        # Gráfico comparativo
        df_kpi = pd.DataFrame({
            'Métrica': ['Litros','Valor'],
            'Externo': [litros_ext, valor_ext],
            'Interno': [litros_int, valor_int]
        }).set_index('Métrica')
        fig = px.bar(
            df_kpi,
            barmode='group',
            labels={'value':'Quantidade','variable':'Tipo'},
            color_discrete_map={'Externo':'#1f77b4','Interno':'#2ca02c'},
            text_auto=True
        )
        fig.update_layout(title_text='Comparativo Externo x Interno', title_font_size=18)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('Top 10 Litros')
        te = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        fig1 = px.bar(te, x='litros', y='placa', orientation='h', title='Externo', color='litros', color_continuous_scale='Blues')
        fig1.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)
        fig2 = px.bar(ti, x='litros', y='placa', orientation='h', title='Interno', color='litros', color_continuous_scale='Greens')
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('Consumo Médio (Km/L)')
        df_comb = pd.concat([
            df_ext[['placa','data','km_atual']],
            df_int[['placa','data','km_atual']]
        ]).dropna()
        df_comb = df_comb.sort_values(['placa','data','km_atual']).reset_index(drop=True)
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff']>0]
        litros = pd.concat([
            df_ext[['placa','data','litros']],
            df_int[['placa','data','litros']]
        ])
        df_comb = df_comb.merge(litros, on=['placa','data'])
        df_comb['consumo'] = df_comb['litros']/df_comb['km_diff']
        cm = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo':'Km/L'})
        fig3 = px.bar(cm, x='Km/L', y='placa', orientation='h', title='Eficiência de Combustível', color='Km/L', color_continuous_scale='Purples')
        fig3.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

if __name__=='__main__':
    main()
