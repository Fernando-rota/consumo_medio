import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Configurações da página
st.set_page_config(
    page_title='⛽ Dashboard de Abastecimento - Análise Completa',
    layout='wide',
    page_icon='⛽'
)

# Constantes
DATE_FORMAT = "DD/MM/YYYY"
BR_CURRENCY = "R$ {:,.2f}"
BR_LITERS = "{:,.2f} L"

@st.cache_data(show_spinner="Carregando dados...", ttl=3600)
def carregar_base(file, nome: str) -> pd.DataFrame:
    """Carrega arquivos CSV ou Excel com tratamento robusto de erros."""
    try:
        if file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file, sep=';', engine='python', encoding='latin1')
        else:
            df = pd.read_excel(file, engine='openpyxl')
        
        df.columns = df.columns.str.strip().str.upper()
        return df
    
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {str(e)}")
        st.info("Verifique se o arquivo está no formato correto e com as colunas necessárias.")
        return None

def formatar_brl(valor: float) -> str:
    """Formata valores monetários no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def tratar_valores_br(valor) -> float:
    """Converte valores no formato brasileiro para float."""
    if pd.isna(valor):
        return 0.0
    try:
        if isinstance(valor, str):
            return float(valor.replace('R$', '')
                          .replace('.', '')
                          .replace(',', '.')
                          .strip())
        return float(valor)
    except:
        return 0.0

def tratar_litros_br(valor) -> float:
    """Converte litros no formato brasileiro para float."""
    if pd.isna(valor):
        return 0.0
    try:
        if isinstance(valor, str):
            return float(valor.replace('.', '').replace(',', '.'))
        return float(valor)
    except:
        return 0.0

def verificar_colunas(df: pd.DataFrame, colunas_necessarias: list, nome_base: str) -> bool:
    """Verifica se as colunas necessárias estão presentes no DataFrame."""
    colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
    if colunas_faltantes:
        st.error(f"Base {nome_base} está faltando colunas: {', '.join(colunas_faltantes)}")
        return False
    return True

def calcular_eficiencia(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a eficiência em km/litro com tratamento de dados."""
    if 'KM ATUAL' not in df.columns or 'QUANTIDADE DE LITROS' not in df.columns:
        return None
    
    df = df.sort_values('DATA').copy()
    df['KM RODADOS'] = df['KM ATUAL'].diff()
    df['KM/L'] = df['KM RODADOS'] / df['QUANTIDADE DE LITROS']
    
    # Filtra valores plausíveis (entre 1 e 20 km/l)
    df_eficiencia = df[df['KM/L'].between(1, 20)]
    
    return df_eficiencia if not df_eficiencia.empty else None

def criar_grafico_consumo_temporal(df_ext: pd.DataFrame, df_int: pd.DataFrame) -> go.Figure:
    """Cria gráfico de série temporal comparando consumos interno e externo."""
    df_ext_daily = df_ext.groupby(pd.Grouper(key='DATA', freq='D'))['LITROS'].sum().reset_index()
    df_int_daily = df_int.groupby(pd.Grouper(key='DATA', freq='D'))['QUANTIDADE DE LITROS'].sum().reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_ext_daily['DATA'], y=df_ext_daily['LITROS'],
        name='Abastecimento Externo',
        line=dict(color='#1f77b4', width=2),
        mode='lines+markers'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_int_daily['DATA'], y=df_int_daily['QUANTIDADE DE LITROS'],
        name='Abastecimento Interno',
        line=dict(color='#ff7f0e', width=2),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        title='Consumo Diário de Combustível',
        xaxis_title='Data',
        yaxis_title='Litros',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def criar_grafico_comparativo_mensal(df_ext: pd.DataFrame, df_int: pd.DataFrame) -> go.Figure:
    """Cria gráfico de barras comparando consumo mensal interno e externo."""
    df_ext_mensal = df_ext.groupby(pd.Grouper(key='DATA', freq='M'))['LITROS'].sum().reset_index()
    df_int_mensal = df_int.groupby(pd.Grouper(key='DATA', freq='M'))['QUANTIDADE DE LITROS'].sum().reset_index()
    
    df_ext_mensal['MES_ANO'] = df_ext_mensal['DATA'].dt.strftime('%b/%Y')
    df_int_mensal['MES_ANO'] = df_int_mensal['DATA'].dt.strftime('%b/%Y')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_ext_mensal['MES_ANO'], y=df_ext_mensal['LITROS'],
        name='Externo',
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        x=df_int_mensal['MES_ANO'], y=df_int_mensal['QUANTIDADE DE LITROS'],
        name='Interno',
        marker_color='#ff7f0e'
    ))
    
    fig.update_layout(
        title='Comparativo Mensal de Consumo',
        xaxis_title='Mês/Ano',
        yaxis_title='Litros',
        barmode='group',
        hovermode='x unified'
    )
    
    return fig

def mostrar_metricas_principais(df_ext: pd.DataFrame, df_int: pd.DataFrame, df_val: pd.DataFrame) -> None:
    """Exibe as métricas principais no dashboard."""
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum() if 'CUSTO TOTAL' in df_ext.columns else 0
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()
    
    preco_medio = valor_int / litros_int if litros_int > 0 else 0
    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
    perc_int = (litros_int / total_litros * 100) if total_litros else 0
    
    cols = st.columns(5)
    cols[0].metric('Litros Externo', BR_LITERS.format(litros_ext), f"{perc_ext:.1f}%")
    cols[1].metric('Custo Externo', formatar_brl(valor_ext))
    cols[2].metric('Litros Interno', BR_LITERS.format(litros_int), f"{perc_int:.1f}%")
    cols[3].metric('Custo Interno', formatar_brl(valor_int))
    cols[4].metric('Preço Médio Interno', formatar_brl(preco_medio))

def main():
    st.title('⛽ Dashboard de Abastecimento - Análise Completa')
    st.markdown("""
    **Dashboard interativo** para análise de consumo e custos de combustível da frota.
    """)
    
    with st.expander('📁 CARREGAR BASES DE DADOS', expanded=True):
        cols = st.columns(3)
        up_ext = cols[0].file_uploader('Base Externa (Abastecimentos)', 
                                      type=['csv', 'xlsx'],
                                      help="Deve conter: DATA, PLACA, LITROS")
        up_int = cols[1].file_uploader('Base Interna (Abastecimentos)',
                                     type=['csv', 'xlsx'],
                                     help="Deve conter: DATA, PLACA, QUANTIDADE DE LITROS, KM ATUAL")
        up_val = cols[2].file_uploader('Base de Valores (Custos)',
                                     type=['csv', 'xlsx'],
                                     help="Deve conter: DATA, VALOR")
    
    if not (up_ext and up_int and up_val):
        st.info("ℹ️ Por favor, carregue todas as três bases de dados para iniciar a análise.")
        return
    
    with st.spinner('Processando dados...'):
        # Carregar e validar dados
        df_ext = carregar_base(up_ext, 'Externa')
        df_int = carregar_base(up_int, 'Interna')
        df_val = carregar_base(up_val, 'de Valores')
        
        if df_ext is None or df_int is None or df_val is None:
            return
        
        # Verificar colunas essenciais
        if not verificar_colunas(df_ext, ['DATA', 'PLACA', 'LITROS'], 'Externa'):
            return
        if not verificar_colunas(df_int, ['DATA', 'PLACA', 'QUANTIDADE DE LITROS'], 'Interna'):
            return
        if not verificar_colunas(df_val, ['DATA', 'VALOR'], 'de Valores'):
            return
        
        # Processar dados
        df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
        df_ext['LITROS'] = df_ext['LITROS'].apply(tratar_litros_br)
        if 'CUSTO TOTAL' in df_ext.columns:
            df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valores_br)
        
        df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
        df_int['QUANTIDADE DE LITROS'] = df_int['QUANTIDADE DE LITROS'].apply(tratar_litros_br)
        if 'KM ATUAL' in df_int.columns:
            df_int['KM ATUAL'] = pd.to_numeric(df_int['KM ATUAL'], errors='coerce')
        
        df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True, errors='coerce')
        df_val['VALOR'] = df_val['VALOR'].apply(tratar_valores_br)
    
    # Filtros na sidebar
    st.sidebar.header('🔍 FILTROS')
    
    min_date = max(
        pd.Timestamp('2023-01-01'),
        min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min())
    )
    max_date = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
    
    date_range = st.sidebar.date_input(
        '📆 Período de Análise',
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
        format=DATE_FORMAT
    )
    
    # Aplicar filtro de data
    df_ext = df_ext[(df_ext['DATA'].dt.date >= date_range[0]) & (df_ext['DATA'].dt.date <= date_range[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= date_range[0]) & (df_int['DATA'].dt.date <= date_range[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= date_range[0]) & (df_val['DATA'].dt.date <= date_range[1])]
    
    # Filtro por veículo
    all_vehicles = sorted(set(
        df_ext['PLACA'].dropna().unique().tolist() + 
        df_int['PLACA'].dropna().unique().tolist()
    ))
    selected_vehicle = st.sidebar.selectbox('🚗 Veículo', ['Todos'] + all_vehicles)
    
    if selected_vehicle != 'Todos':
        df_ext = df_ext[df_ext['PLACA'] == selected_vehicle]
        df_int = df_int[df_int['PLACA'] == selected_vehicle]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == selected_vehicle]
    
    # Filtro por tipo de combustível (se disponível)
    fuel_col = next((c for c in df_ext.columns if 'COMBUST' in c or 'DESCRI' in c), None)
    if fuel_col:
        fuel_types = sorted(df_ext[fuel_col].dropna().astype(str).str.strip().unique())
        selected_fuel = st.sidebar.selectbox('🛢 Tipo de Combustível', ['Todos'] + fuel_types)
        if selected_fuel != 'Todos':
            df_ext = df_ext[df_ext[fuel_col] == selected_fuel]
    
    # Abas de análise
    tab1, tab2, tab3, tab4 = st.tabs([
        '📊 VISÃO GERAL', 
        '⏳ TENDÊNCIA TEMPORAL', 
        '📈 COMPARATIVO MENSAL', 
        '🚙 EFICIÊNCIA'
    ])
    
    with tab1:
        st.header("Visão Geral do Período")
        mostrar_metricas_principais(df_ext, df_int, df_val)
        
        st.subheader("Top 10 Veículos por Consumo")
        top_veiculos = pd.concat([
            df_ext.groupby('PLACA')['LITROS'].sum(),
            df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum()
        ], axis=1).sum(axis=1).nlargest(10).reset_index()
        
        if not top_veiculos.empty:
            fig = px.bar(
                top_veiculos, x='PLACA', y=0,
                labels={'PLACA': 'Veículo', '0': 'Litros Consumidos'},
                color=0,
                color_continuous_scale='Bluered'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Tendência Temporal de Consumo")
        fig = criar_grafico_consumo_temporal(df_ext, df_int)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("Comparativo Mensal")
        fig = criar_grafico_comparativo_mensal(df_ext, df_int)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Análise de Eficiência")
        
        if 'KM ATUAL' in df_int.columns:
            df_eficiencia = calcular_eficiencia(df_int)
            
            if df_eficiencia is not None:
                avg_eff = df_eficiencia['KM/L'].mean()
                best_eff = df_eficiencia['KM/L'].max()
                
                cols = st.columns(2)
                cols[0].metric('Eficiência Média', f"{avg_eff:.1f} km/L")
                cols[1].metric('Melhor Desempenho', f"{best_eff:.1f} km/L")
                
                fig = px.line(
                    df_eficiencia, x='DATA', y='KM/L',
                    title='Evolução da Eficiência (km/litro)',
                    labels={'KM/L': 'Quilômetros por litro', 'DATA': 'Data'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados insuficientes para calcular eficiência.")
        else:
            st.info("A base interna não contém dados de quilometragem para cálculo de eficiência.")

if __name__ == '__main__':
    main()
