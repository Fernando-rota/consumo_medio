import streamlit as st
import pandas as pd
import plotly.express as px

# Título e contexto
st.set_page_config(page_title='Abastecimento Externo x Interno', layout='wide')
st.title('📊 Relatório Abastecimento Externo x Interno')
st.markdown('''
Este dashboard apresenta o volume de litros e o custo de abastecimentos externos e internos
para análise gerencial. Selecione o período e carregue suas bases de dados.
''')

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

# Upload dentro de expander para liberar espaço
with st.expander('🔽 Carregar bases de dados'):  
    c1, c2, c3 = st.columns(3)
    up_ext = c1.file_uploader('Externo', type=['csv','xlsx'])
    up_int = c2.file_uploader('Interno', type=['csv','xlsx'])
    up_val = c3.file_uploader('Valor Comb. Int.', type=['csv','xlsx'])

if not (up_ext and up_int and up_val):
    st.stop()

# Carregar DataFrames
df_ext = carregar_base(up_ext, 'Externo')
df_int = carregar_base(up_int, 'Interno')
df_val = carregar_base(up_val, 'Valor Comb. Int.')
if None in (df_ext, df_int, df_val):
    st.stop()

# Seleção de período com slider de datas
ini, fim = st.slider(
    'Selecione o Período',
    value=(pd.to_datetime('2025-01-01'), pd.to_datetime('2025-12-31')),
    format='DD/MM/YYYY'
)
ini = ini.date(); fim = fim.date()

# Converter e filtrar datas
for df, col in [(df_ext, 'DATA'), (df_int, 'Data')]:
    df['data'] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.date
col_dt = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
if col_dt:
    df_val['data'] = pd.to_datetime(df_val[col_dt], dayfirst=True, errors='coerce').dt.date
else:
    st.error('Data não encontrada em Valor Comb. Int.'); st.stop()

# Aplicar filtro de período
mask = (df_ext['data'] >= ini) & (df_ext['data'] <= fim)
df_ext = df_ext[mask]
mask = (df_int['data'] >= ini) & (df_int['data'] <= fim)
df_int = df_int[mask]
mask = (df_val['data'] >= ini) & (df_val['data'] <= fim)
df_val = df_val[mask]

# Criação da coluna placa
for df, col in [(df_ext, 'PLACA'), (df_int, 'Placa')]:
    df['placa'] = df[col].astype(str).str.upper().str.strip()

# Tratar valores
df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
df_val['valor'] = df_val['Valor Total'].apply(tratar_valor)

# Cálculos principais
litros_ext = df_ext['litros'].sum()
valor_ext = df_ext['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in df_ext.columns else 0
litros_int = df_int['litros'].sum()
valor_int = df_val['valor'].sum()

# Modularização das renderizações
def render_resumo():
    st.subheader(f'Resumo de {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
    # KPIs destacados
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Litros Externo', f'{litros_ext:,.2f} L')
    k2.metric('Valor Externo', f'R$ {valor_ext:,.2f}')
    k3.metric('Litros Interno', f'{litros_int:,.2f} L')
    k4.metric('Valor Interno', f'R$ {valor_int:,.2f}')
    # Gráfico comparativo
    df_kpi = pd.DataFrame({
        'Métrica': ['Litros', 'Valor'],
        'Externo': [litros_ext, valor_ext],
        'Interno': [litros_int, valor_int]
    }).set_index('Métrica')
    fig = px.bar(
        df_kpi,
        barmode='group',
        color_discrete_map={'Externo': '#1f77b4','Interno': '#2ca02c'},
        text_auto=True
    )
    fig.update_layout(title_text='Comparativo Externo x Interno', title_font_size=18)
    st.plotly_chart(fig, use_container_width=True)


def render_top10():
    st.subheader('Top 10 Litros')
    fig1 = px.bar(
        df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index(),
        x='litros', y='placa', orientation='h',
        title='Externo', color='litros', color_continuous_scale='Blues'
    )
    fig1.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)
    fig2 = px.bar(
        df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index(),
        x='litros', y='placa', orientation='h',
        title='Interno', color='litros', color_continuous_scale='Greens'
    )
    fig2.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig2, use_container_width=True)


def render_consumo():
    st.subheader('Consumo Médio (Km/L)')
    df_comb = pd.concat([df_ext[['placa','data','km_atual']], df_int[['placa','data','km_atual']]]).dropna()
    df_comb = df_comb.sort_values(['placa','data','km_atual']).reset_index(drop=True)
    df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
    df_comb = df_comb[df_comb['km_diff']>0]
    df_comb = df_comb.merge(
        pd.concat([df_ext[['placa','data','litros']], df_int[['placa','data','litros']]]), on=['placa','data']
    )
    df_comb['consumo'] = df_comb['litros'] / df_comb['km_diff']
    cm = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo':'Km/L'})
    fig = px.bar(cm, x='Km/L', y='placa', orientation='h', title='Eficiência de Combustível', color='Km/L', color_continuous_scale='Purples')
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

# Renderizar abas
tab1, tab2, tab3 = st.tabs(['Resumo','Top10','Consumo'])
with tab1: render_resumo()
with tab2: render_top10()
with tab3: render_consumo()

if __name__=='__main__':
    main()
