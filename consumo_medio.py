import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações iniciais
st.set_page_config(page_title='Abastecimento Externo x Interno', layout='wide')

@st.cache_data
# Carrega e limpa dados
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

# Converte strings

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
    Dashboard de análise de volume (litros) e custo (R$) de abastecimentos externos e internos.
    ''')

    # Uploads
    with st.expander('📥 Carregar bases'):  
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Externo', type=['csv','xlsx'])
        up_int = c2.file_uploader('Interno', type=['csv','xlsx'])
        up_val = c3.file_uploader('Valor Int.', type=['csv','xlsx'])
    if not (up_ext and up_int and up_val): st.stop()

    df_ext = carregar_base(up_ext, 'Externo')
    df_int = carregar_base(up_int, 'Interno')
    df_val = carregar_base(up_val, 'Valor Int.')
    if df_ext is None or df_int is None or df_val is None: st.stop()

    # Determina período baseado nos dados
    min_ext = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').min().date()
    min_int = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').min().date()
    max_ext = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').max().date()
    max_int = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').max().date()
    min_dt = min(min_ext, min_int)
    max_dt = max(max_ext, max_int)

    # Slider de período
    ini, fim = st.slider('Período', min_value=min_dt, max_value=max_dt, value=(min_dt, max_dt), format='DD/MM/YYYY')

    # DataFrames: converte datas e filtra
    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').dt.date
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').dt.date
    col_dt = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if not col_dt: st.error('Coluna de data não encontrada em Valor Int.'); st.stop()
    df_val['data'] = pd.to_datetime(df_val[col_dt], dayfirst=True, errors='coerce').dt.date

    df_ext = df_ext[(df_ext['data']>=ini)&(df_ext['data']<=fim)]
    df_int = df_int[(df_int['data']>=ini)&(df_int['data']<=fim)]
    df_val = df_val[(df_val['data']>=ini)&(df_val['data']<=fim)]

    # Cria colunas essenciais
    df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['placa'] = df_int['Placa'].astype(str).str.upper().str.strip()
    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
    df_ext['valor'] = df_ext.get('CUSTO TOTAL', pd.Series()).apply(tratar_valor)
    df_val['valor_int'] = df_val['Valor Total'].apply(tratar_valor)

    # Calcula KPIs
    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['valor'].sum()
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor_int'].sum()

    # Abas
    tab1, tab2, tab3 = st.tabs(['✔️ Resumo','🔝 Top10','🔍 Consumo'])

    with tab1:
        st.subheader(f'Período: {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        # KPIs em linha
        k1,k2,k3,k4 = st.columns(4)
        k1.metric('Litros Ext.', f'{litros_ext:,.2f} L')
        k2.metric('Custo Ext.', f'R$ {valor_ext:,.2f}')
        k3.metric('Litros Int.', f'{litros_int:,.2f} L')
        k4.metric('Custo Int.', f'R$ {valor_int:,.2f}')
        # Gráfico comparativo
        df_kpi = pd.DataFrame({
            'Métrica':['Litros','Custo'],
            'Externo':[litros_ext, valor_ext],
            'Interno':[litros_int, valor_int]
        }).melt(id_vars='Métrica', var_name='Tipo', value_name='Valor')
        fig = px.bar(df_kpi, x='Métrica', y='Valor', color='Tipo', barmode='group',
                     color_discrete_map={'Externo':'#1f77b4','Interno':'#2ca02c'}, text='Valor')
        fig.update_layout(title='Comparativo Externo vs Interno', title_font_size=18)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader('Top 10 Litros')
        te = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        fig1 = px.bar(te, y='placa', x='litros', orientation='h', color='litros',
                     title='Externo', color_continuous_scale='Blues')
        fig1.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)
        fig2 = px.bar(ti, y='placa', x='litros', orientation='h', color='litros',
                     title='Interno', color_continuous_scale='Greens')
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader('Consumo Médio (Km/L)')
        # Verifica km_atual existe
        for df in (df_ext, df_int):
            if 'km_atual' not in df.columns:
                st.warning('Coluna km_atual ausente; consumo não calculado.')
                return
        df_comb = pd.concat([
            df_ext[['placa','data','km_atual','litros']],
            df_int[['placa','data','km_atual','litros']]
        ]).dropna()
        df_comb = df_comb.sort_values(['placa','data','km_atual']).reset_index(drop=True)
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb = df_comb[df_comb['km_diff']>0]
        df_comb['consumo'] = df_comb['litros']/df_comb['km_diff']
        cm = df_comb.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo':'Km/L'})
        fig3 = px.bar(cm, x='Km/L', y='placa', orientation='h', color='Km/L',
                      title='Eficiência de Combustível', color_continuous_scale='Purples')
        fig3.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig3, use_container_width=True)

if __name__=='__main__': main()
