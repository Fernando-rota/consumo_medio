import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

# Configuração da página
st.set_page_config(
    page_title='⛽ Dashboard de Abastecimento',
    layout='wide',
    page_icon='⛽'
)

# Funções de apoio
@st.cache_data(show_spinner="Carregando dados...")
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file, sep=';', engine='python', encoding='utf-8')
        else:
            df = pd.read_excel(file, engine='openpyxl')
        
        # Padronização de colunas
        df.columns = (
            df.columns.str.upper()
            .str.replace(' ', '_')
            .str.replace('Ç', 'C')
            .str.replace('Ã', 'A')
            .str.replace('Õ', 'O')
            .str.strip()
        )
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {str(e)}")
        return None

def tratar_valor(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.').strip())
    except:
        return 0.0

def tratar_litros(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_consumo_medio(df):
    df = df.sort_values(['PLACA', 'DATA'])
    df['KM_RODADOS'] = df.groupby('PLACA')['KM_ATUAL'].diff()
    df['CONSUMO_KM_L'] = np.where(
        (df['LITROS'] > 0) & (df['KM_RODADOS'] > 0),
        df['KM_RODADOS'] / df['LITROS'],
        np.nan
    )
    return df

# Interface principal
def main():
    st.title('⛽ Dashboard de Abastecimento')
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    # Upload de arquivos
    with st.expander("📤 Upload de Arquivos", expanded=True):
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

    # Carregar e tratar dados
    df_ext = carregar_base(uploaded_ext, "Abastecimento Externo")
    df_int = carregar_base(uploaded_int, "Abastecimento Interno")
    df_val = carregar_base(uploaded_val, "Valores de Combustível")

    if df_ext is None or df_int is None or df_val is None:
        return

    # Tratamento específico para cada base
    try:
        # Base Externa
        df_ext = df_ext.rename(columns={
            'CONSUMO': 'LITROS',
            'CUSTO_TOTAL': 'VALOR',
            'KM_ATUAL': 'KM_ATUAL'
        })
        df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
        df_ext['LITROS'] = df_ext['LITROS'].apply(tratar_litros)
        df_ext['VALOR'] = df_ext['VALOR'].apply(tratar_valor)
        df_ext['TIPO'] = 'EXTERNO'
        
        # Base Interna
        df_int = df_int.rename(columns={
            'QUANTIDADE_DE_LITROS': 'LITROS',
            'KM_ATUAL': 'KM_ATUAL'
        })
        df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
        df_int['LITROS'] = df_int['LITROS'].apply(tratar_litros)
        df_int['TIPO'] = 'INTERNO'
        
        # Base de Valores
        df_val = df_val.rename(columns={
            'EMISSAO': 'DATA',
            'VALOR_PAGO': 'VALOR'
        })
        df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True, errors='coerce')
        df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)
        
    except Exception as e:
        st.error(f"Erro no processamento dos dados: {str(e)}")
        return

    # Filtros
    st.sidebar.header("🔍 Filtros")
    
    # Filtro de data
    min_date = min(
        df_ext['DATA'].min(), 
        df_int['DATA'].min(), 
        df_val['DATA'].min()
    ).date()
    max_date = max(
        df_ext['DATA'].max(), 
        df_int['DATA'].max(), 
        df_val['DATA'].max()
    ).date()
    
    date_range = st.sidebar.date_input(
        "Período de Análise",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtro de veículos
    veiculos = sorted(set(df_ext['PLACA'].dropna().unique()) | set(df_int['PLACA'].dropna().unique())
    veiculo_selecionado = st.sidebar.selectbox(
        "Selecione o Veículo",
        ["Todos"] + veiculos
    )
    
    # Filtro de tipo de combustível (se disponível)
    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = ["Todos"] + sorted(df_ext[combustivel_col].dropna().unique())
        combustivel_selecionado = st.sidebar.selectbox(
            "Tipo de Combustível",
            tipos_combustivel
        )
    
    # Aplicar filtros
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    
    df_ext = df_ext[(df_ext['DATA'] >= start_date) & (df_ext['DATA'] <= end_date)]
    df_int = df_int[(df_int['DATA'] >= start_date) & (df_int['DATA'] <= end_date)]
    df_val = df_val[(df_val['DATA'] >= start_date) & (df_val['DATA'] <= end_date)]
    
    if veiculo_selecionado != "Todos":
        df_ext = df_ext[df_ext['PLACA'] == veiculo_selecionado]
        df_int = df_int[df_int['PLACA'] == veiculo_selecionado]
    
    if combustivel_col and 'combustivel_selecionado' in locals() and combustivel_selecionado != "Todos":
        df_ext = df_ext[df_ext[combustivel_col] == combustivel_selecionado]
    
    # Cálculos principais
    total_ext = df_ext['LITROS'].sum()
    total_int = df_int['LITROS'].sum()
    valor_ext = df_ext['VALOR'].sum()
    valor_int = df_val['VALOR'].sum()
    
    # Layout do dashboard
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral", 
        "🚗 Análise por Veículo", 
        "⛽ Eficiência", 
        "📈 Tendências"
    ])
    
    with tab1:
        st.subheader("Visão Geral do Abastecimento")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Litros Externos", f"{total_ext:,.1f} L")
        with col2:
            st.metric("Valor Externo", formatar_moeda(valor_ext))
        with col3:
            st.metric("Litros Internos", f"{total_int:,.1f} L")
        with col4:
            st.metric("Valor Interno", formatar_moeda(valor_int))
        
        # Gráfico comparativo
        fig = px.pie(
            names=['Externo', 'Interno'],
            values=[total_ext, total_int],
            title='Distribuição de Litros Consumidos'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Análise por Veículo")
        
        # Consumo por veículo (externo + interno)
        df_veiculos_ext = df_ext.groupby('PLACA').agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        
        df_veiculos_int = df_int.groupby('PLACA').agg({
            'LITROS': 'sum'
        }).reset_index()
        
        df_veiculos = pd.merge(
            df_veiculos_ext, 
            df_veiculos_int, 
            on='PLACA', 
            how='outer', 
            suffixes=('_EXT', '_INT')
        ).fillna(0)
        
        df_veiculos['TOTAL_LITROS'] = df_veiculos['LITROS_EXT'] + df_veiculos['LITROS_INT']
        df_veiculos = df_veiculos.sort_values('TOTAL_LITROS', ascending=False)
        
        st.dataframe(
            df_veiculos.style.format({
                'LITROS_EXT': '{:,.1f} L',
                'VALOR': formatar_moeda,
                'LITROS_INT': '{:,.1f} L',
                'TOTAL_LITROS': '{:,.1f} L'
            }),
            height=400,
            use_container_width=True
        )
    
    with tab3:
        st.subheader("Eficiência dos Veículos")
        
        # Calcular consumo médio
        df_ext_eff = calcular_consumo_medio(df_ext)
        df_int_eff = calcular_consumo_medio(df_int)
        
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
                consumo_medio.style.format({'CONSUMO_KM_L': '{:.2f} km/L'})
                .background_gradient(subset=['CONSUMO_KM_L'], cmap='RdYlGn'),
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
                labels={'CONSUMO_KM_L': 'Consumo (km/L)', 'PLACA': 'Veículo'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("Tendências Temporais")
        
        # Agrupar por período (semanal/mensal)
        periodo = st.selectbox("Agrupar por:", ["Diário", "Semanal", "Mensal"])
        
        freq = {
            "Diário": "D",
            "Semanal": "W",
            "Mensal": "M"
        }[periodo]
        
        # Dados externos
        df_ext_trend = df_ext.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        df_ext_trend['TIPO'] = 'EXTERNO'
        
        # Dados internos
        df_int_trend = df_int.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum'
        }).reset_index()
        df_int_trend['TIPO'] = 'INTERNO'
        
        # Valores internos
        df_val_trend = df_val.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'VALOR': 'sum'
        }).reset_index()
        df_val_trend['TIPO'] = 'INTERNO'
        
        # Gráficos
        fig1 = px.line(
            df_ext_trend, 
            x='DATA', 
            y='LITROS',
            title='Consumo Externo ao Longo do Tempo'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.line(
            pd.concat([df_ext_trend, df_int_trend]),
            x='DATA',
            y='LITROS',
            color='TIPO',
            title='Comparativo de Consumo Interno vs Externo'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = px.line(
            pd.concat([df_ext_trend, df_val_trend]),
            x='DATA',
            y='VALOR',
            color='TIPO',
            title='Comparativo de Custos'
        )
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
