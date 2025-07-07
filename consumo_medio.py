import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# Configurações da página
st.set_page_config(
    page_title="⛽ Dashboard de Abastecimento",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Funções de tratamento de dados
@st.cache_data(show_spinner="Processando dados...")
def carregar_dados(uploaded_ext, uploaded_int, uploaded_val):
    # Função para padronizar nomes de colunas
    def padronizar_colunas(df):
        df.columns = (
            df.columns.str.upper()
            .str.replace(' ', '_')
            .str.replace('Ç', 'C')
            .str.replace('Ã', 'A')
            .str.replace('Õ', 'O')
            .str.strip()
        )
        return df

    # Carregar e tratar cada base
    try:
        # Base Externa
        if uploaded_ext.name.endswith('.csv'):
            df_ext = pd.read_csv(uploaded_ext, sep=None, engine='python', encoding='utf-8')
        else:
            df_ext = pd.read_excel(uploaded_ext, engine='openpyxl')
        df_ext = padronizar_colunas(df_ext)
        df_ext = df_ext.rename(columns={
            'CONSUMO': 'LITROS',
            'CUSTO_TOTAL': 'VALOR',
            'KM_ATUAL': 'KM_ATUAL'
        })
        df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
        df_ext['LITROS'] = df_ext['LITROS'].apply(lambda x: float(str(x).replace('.', '').replace(',', '.')) if isinstance(x, str) else float(x))
        df_ext['VALOR'] = df_ext['VALOR'].apply(lambda x: float(str(x).replace('R$', '').replace('.', '').replace(',', '.')) if isinstance(x, str) else float(x))
        df_ext['TIPO'] = 'EXTERNO'

        # Base Interna
        if uploaded_int.name.endswith('.csv'):
            df_int = pd.read_csv(uploaded_int, sep=None, engine='python', encoding='utf-8')
        else:
            df_int = pd.read_excel(uploaded_int, engine='openpyxl')
        df_int = padronizar_colunas(df_int)
        df_int = df_int.rename(columns={
            'QUANTIDADE_DE_LITROS': 'LITROS',
            'KM_ATUAL': 'KM_ATUAL'
        })
        df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
        df_int['LITROS'] = df_int['LITROS'].apply(lambda x: float(str(x).replace('.', '').replace(',', '.')) if isinstance(x, str) else float(x))
        df_int['TIPO'] = 'INTERNO'

        # Base de Valores
        if uploaded_val.name.endswith('.csv'):
            df_val = pd.read_csv(uploaded_val, sep=None, engine='python', encoding='utf-8')
        else:
            df_val = pd.read_excel(uploaded_val, engine='openpyxl')
        df_val = padronizar_colunas(df_val)
        df_val = df_val.rename(columns={
            'EMISSAO': 'DATA',
            'VALOR_PAGO': 'VALOR'
        })
        df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True, errors='coerce')
        df_val['VALOR'] = df_val['VALOR'].apply(lambda x: float(str(x).replace('R$', '').replace('.', '').replace(',', '.')) if isinstance(x, str) else float(x))

        return df_ext, df_int, df_val

    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {str(e)}")
        return None, None, None

# Função para calcular eficiência
def calcular_eficiencia(df):
    df = df.sort_values(['PLACA', 'DATA'])
    df['KM_RODADOS'] = df.groupby('PLACA')['KM_ATUAL'].diff()
    df['CONSUMO_KM_L'] = np.where(
        (df['LITROS'] > 0) & (df['KM_RODADOS'] > 0),
        df['KM_RODADOS'] / df['LITROS'],
        np.nan
    )
    return df

# Função principal
def main():
    st.title("⛽ Dashboard de Abastecimento")
    st.markdown("""
    <style>
    .css-18e3th9 {padding: 2rem 1rem 10rem;}
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    # Upload de arquivos
    with st.expander("📤 CARREGAR ARQUIVOS", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_ext = st.file_uploader("Abastecimento Externo", type=['csv', 'xlsx'])
        with col2:
            uploaded_int = st.file_uploader("Abastecimento Interno", type=['csv', 'xlsx'])
        with col3:
            uploaded_val = st.file_uploader("Valores de Combustível", type=['csv', 'xlsx'])

    if not (uploaded_ext and uploaded_int and uploaded_val):
        st.warning("Por favor, carregue todos os arquivos para continuar.")
        return

    # Carregar dados
    df_ext, df_int, df_val = carregar_dados(uploaded_ext, uploaded_int, uploaded_val)
    if df_ext is None or df_int is None or df_val is None:
        return

    # Filtros na sidebar
    st.sidebar.header("🔍 FILTROS")

    # Filtro de data
    min_date = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min()).date()
    max_date = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max()).date()
    date_range = st.sidebar.date_input(
        "Selecione o período",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Filtro de veículos
    veiculos = sorted(set(df_ext['PLACA'].dropna().unique()).union(set(df_int['PLACA'].dropna().unique())))
    veiculo_selecionado = st.sidebar.selectbox("Selecione o veículo", ["Todos"] + veiculos)

    # Filtro de combustível (se existir na base externa)
    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = ["Todos"] + sorted(df_ext[combustivel_col].dropna().unique())
        combustivel_selecionado = st.sidebar.selectbox("Tipo de combustível", tipos_combustivel)

    # Aplicar filtros
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    
    df_ext_filtrado = df_ext[(df_ext['DATA'] >= start_date) & (df_ext['DATA'] <= end_date)]
    df_int_filtrado = df_int[(df_int['DATA'] >= start_date) & (df_int['DATA'] <= end_date)]
    df_val_filtrado = df_val[(df_val['DATA'] >= start_date) & (df_val['DATA'] <= end_date)]

    if veiculo_selecionado != "Todos":
        df_ext_filtrado = df_ext_filtrado[df_ext_filtrado['PLACA'] == veiculo_selecionado]
        df_int_filtrado = df_int_filtrado[df_int_filtrado['PLACA'] == veiculo_selecionado]

    if combustivel_col and 'combustivel_selecionado' in locals() and combustivel_selecionado != "Todos":
        df_ext_filtrado = df_ext_filtrado[df_ext_filtrado[combustivel_col] == combustivel_selecionado]

    # Cálculos principais
    total_ext = df_ext_filtrado['LITROS'].sum()
    total_int = df_int_filtrado['LITROS'].sum()
    valor_ext = df_ext_filtrado['VALOR'].sum()
    valor_int = df_val_filtrado['VALOR'].sum()

    # Layout das abas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 RESUMO", "🚙 VEÍCULOS", "⚙️ EFICIÊNCIA", "📈 TENDÊNCIAS"])

    with tab1:
        st.subheader("Visão Geral do Abastecimento")
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Litros Externos", f"{total_ext:,.1f} L")
        with col2:
            st.metric("Valor Externo", f"R$ {valor_ext:,.2f}")
        with col3:
            st.metric("Litros Internos", f"{total_int:,.1f} L")
        with col4:
            st.metric("Valor Interno", f"R$ {valor_int:,.2f}")

        # Gráficos comparativos
        fig1 = px.pie(
            names=['Externo', 'Interno'],
            values=[total_ext, total_int],
            title='Distribuição de Litros Consumidos',
            hole=0.4
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Análise por Veículo")
        
        # Consumo por veículo
        consumo_ext = df_ext_filtrado.groupby('PLACA').agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        
        consumo_int = df_int_filtrado.groupby('PLACA').agg({
            'LITROS': 'sum'
        }).reset_index()
        
        df_consumo = pd.merge(
            consumo_ext, 
            consumo_int, 
            on='PLACA', 
            how='outer', 
            suffixes=('_EXT', '_INT')
        ).fillna(0)
        
        df_consumo['TOTAL_LITROS'] = df_consumo['LITROS_EXT'] + df_consumo['LITROS_INT']
        df_consumo = df_consumo.sort_values('TOTAL_LITROS', ascending=False)

        # Estilo condicional para a tabela
        def color_negative_red(val):
            color = 'red' if val < 0 else 'black'
            return f'color: {color}'

        st.dataframe(
            df_consumo.style
                .format({
                    'LITROS_EXT': '{:,.1f} L',
                    'VALOR': 'R$ {:,.2f}',
                    'LITROS_INT': '{:,.1f} L',
                    'TOTAL_LITROS': '{:,.1f} L'
                })
                .applymap(color_negative_red),
            height=400,
            use_container_width=True
        )

    with tab3:
        st.subheader("Eficiência dos Veículos")
        
        # Calcular eficiência
        df_ext_eff = calcular_eficiencia(df_ext_filtrado)
        df_int_eff = calcular_eficiencia(df_int_filtrado)
        
        df_eficiencia = pd.concat([
            df_ext_eff[['PLACA', 'CONSUMO_KM_L']],
            df_int_eff[['PLACA', 'CONSUMO_KM_L']]
        ]).dropna()
        
        consumo_medio = df_eficiencia.groupby('PLACA')['CONSUMO_KM_L'].mean().reset_index()
        consumo_medio = consumo_medio.sort_values('CONSUMO_KM_L', ascending=False)
        
        # Classificação de eficiência
        def classificar_eficiencia(km_l):
            if km_l > 8: return 'Excelente'
            elif km_l > 6: return 'Bom'
            elif km_l > 4: return 'Regular'
            else: return 'Ruim'
        
        consumo_medio['CLASSIFICACAO'] = consumo_medio['CONSUMO_KM_L'].apply(classificar_eficiencia)
        
        # Exibir resultados
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(
                consumo_medio.style
                    .format({'CONSUMO_KM_L': '{:.2f} km/L'})
                    .apply(lambda x: ['background-color: #d4edda' if v == 'Excelente' 
                                    else 'background-color: #c3e6cb' if v == 'Bom'
                                    else 'background-color: #ffeeba' if v == 'Regular'
                                    else 'background-color: #f5c6cb' for v in x],
                          subset=['CLASSIFICACAO']),
                height=500
            )
        
        with col2:
            fig = px.bar(
                consumo_medio,
                x='CONSUMO_KM_L',
                y='PLACA',
                orientation='h',
                color='CLASSIFICACAO',
                title='Eficiência por Veículo (km/L)',
                color_discrete_map={
                    'Excelente': '#28a745',
                    'Bom': '#5cb85c',
                    'Regular': '#ffc107',
                    'Ruim': '#dc3545'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Tendências Temporais")
        
        # Agrupar por período
        periodo = st.selectbox("Agrupar por", ["Diário", "Semanal", "Mensal"])
        freq = {'Diário': 'D', 'Semanal': 'W-MON', 'Mensal': 'M'}[periodo]
        
        # Dados agrupados
        df_ext_trend = df_ext_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        df_ext_trend['TIPO'] = 'EXTERNO'
        df_ext_trend['PRECO_MEDIO'] = df_ext_trend['VALOR'] / df_ext_trend['LITROS']
        
        df_int_trend = df_int_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum'
        }).reset_index()
        df_int_trend['TIPO'] = 'INTERNO'
        
        df_val_trend = df_val_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'VALOR': 'sum'
        }).reset_index()
        df_val_trend['TIPO'] = 'INTERNO'
        
        # Combinar para preço médio interno
        df_int_full = pd.merge(df_int_trend, df_val_trend, on=['DATA', 'TIPO'])
        df_int_full['PRECO_MEDIO'] = df_int_full['VALOR'] / df_int_full['LITROS']
        
        # Gráficos
        fig1 = px.line(
            df_ext_trend,
            x='DATA',
            y='LITROS',
            title='Consumo Externo'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.line(
            pd.concat([df_ext_trend, df_int_trend]),
            x='DATA',
            y='LITROS',
            color='TIPO',
            title='Comparativo de Consumo'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = px.line(
            pd.concat([df_ext_trend, df_int_full]),
            x='DATA',
            y='PRECO_MEDIO',
            color='TIPO',
            title='Preço Médio (R$/L)'
        )
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
