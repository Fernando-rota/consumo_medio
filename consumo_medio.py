import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# Configurações da página
st.set_page_config(
    page_title="⛽ Dashboard de Abastecimento Profissional",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para criar gradiente de cores sem matplotlib
def color_gradient(value, min_val, max_val):
    """Retorna uma cor em formato RGB baseada em um gradiente vermelho-verde"""
    if pd.isna(value) or min_val == max_val:
        return "rgb(200, 200, 200)"  # Cinza para valores inválidos
    
    # Normaliza o valor entre 0 e 1
    normalized = (value - min_val) / (max_val - min_val)
    
    # Calcula componentes RGB (vermelho -> amarelo -> verde)
    red = int(255 * (1 - normalized))
    green = int(255 * normalized)
    blue = 0
    
    return f"rgb({red}, {green}, {blue})"

# Função para aplicar estilo às tabelas
def style_dataframe(df, numeric_columns):
    """Aplica formatação condicional ao DataFrame"""
    styles = []
    for col in df.columns:
        if col in numeric_columns:
            min_val = df[col].min()
            max_val = df[col].max()
            col_styles = []
            for val in df[col]:
                col_styles.append(f"background-color: {color_gradient(val, min_val, max_val)};")
            styles.append(col_styles)
        else:
            styles.append([""] * len(df))
    return styles

# Função principal de carregamento de dados
@st.cache_data(show_spinner="Processando dados...")
def carregar_dados(uploaded_ext, uploaded_int, uploaded_val):
    try:
        # Função auxiliar para padronizar colunas
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

        # Carregar base externa
        if uploaded_ext.name.endswith('.csv'):
            df_ext = pd.read_csv(uploaded_ext, sep=';', encoding='utf-8', decimal=',')
        else:
            df_ext = pd.read_excel(uploaded_ext, engine='openpyxl')
        
        df_ext = padronizar_colunas(df_ext)
        df_ext = df_ext.rename(columns={
            'CONSUMO': 'LITROS',
            'CUSTO_TOTAL': 'VALOR',
            'KM_ATUAL': 'KM_ATUAL'
        })
        
        # Converter tipos de dados
        df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True)
        df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce')
        df_ext['VALOR'] = pd.to_numeric(df_ext['VALOR'].astype(str).str.replace('R\$', '').str.replace('.', '').str.replace(',', '.'), errors='coerce')
        df_ext['TIPO'] = 'EXTERNO'

        # Carregar base interna
        if uploaded_int.name.endswith('.csv'):
            df_int = pd.read_csv(uploaded_int, sep=';', encoding='utf-8', decimal=',')
        else:
            df_int = pd.read_excel(uploaded_int, engine='openpyxl')
        
        df_int = padronizar_colunas(df_int)
        df_int = df_int.rename(columns={
            'QUANTIDADE_DE_LITROS': 'LITROS',
            'KM_ATUAL': 'KM_ATUAL'
        })
        
        df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True)
        df_int['LITROS'] = pd.to_numeric(df_int['LITROS'].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce')
        df_int['TIPO'] = 'INTERNO'

        # Carregar base de valores
        if uploaded_val.name.endswith('.csv'):
            df_val = pd.read_csv(uploaded_val, sep=';', encoding='utf-8', decimal=',')
        else:
            df_val = pd.read_excel(uploaded_val, engine='openpyxl')
        
        df_val = padronizar_colunas(df_val)
        df_val = df_val.rename(columns={
            'EMISSÃO': 'DATA',
            'VALOR_PAGO': 'VALOR'
        })
        
        df_val['DATA'] = pd.to_datetime(df_val['DATA'], dayfirst=True)
        df_val['VALOR'] = pd.to_numeric(df_val['VALOR'].astype(str).str.replace('R\$', '').str.replace('.', '').str.replace(',', '.'), errors='coerce')

        return df_ext, df_int, df_val

    except Exception as e:
        st.error(f"Erro crítico ao processar os dados: {str(e)}")
        st.stop()

# Função principal
def main():
    st.title("⛽ Dashboard de Abastecimento Profissional")
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
            uploaded_ext = st.file_uploader("Abastecimento Externo (Postos)", type=['csv', 'xlsx'])
        with col2:
            uploaded_int = st.file_uploader("Abastecimento Interno (Frota)", type=['csv', 'xlsx'])
        with col3:
            uploaded_val = st.file_uploader("Pagamentos (Financeiro)", type=['csv', 'xlsx'])

    if not all([uploaded_ext, uploaded_int, uploaded_val]):
        st.warning("Por favor, carregue todos os três arquivos para continuar.")
        return

    # Carregar dados
    with st.spinner('Processando bases de dados...'):
        df_ext, df_int, df_val = carregar_dados(uploaded_ext, uploaded_int, uploaded_val)

    # Verificar dados carregados
    if df_ext is None or df_int is None or df_val is None:
        st.error("Falha ao carregar um ou mais arquivos. Verifique os formatos.")
        return

    # Sidebar - Filtros
    st.sidebar.header("🔍 FILTROS AVANÇADOS")

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
        "Selecione o período",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Filtro de veículos
    veiculos = sorted(set(
        list(df_ext['PLACA'].dropna().unique()) + 
        list(df_int['PLACA'].dropna().unique())
    ))
    veiculo_selecionado = st.sidebar.selectbox(
        "Filtrar por veículo",
        ["Todos"] + veiculos
    )

    # Filtro de tipo de combustível (se existir)
    combustivel_col = next((col for col in df_ext.columns if 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = ["Todos"] + sorted(df_ext[combustivel_col].dropna().unique())
        combustivel_selecionado = st.sidebar.selectbox(
            "Filtrar por combustível",
            tipos_combustivel
        )

    # Aplicar filtros
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    
    df_ext_filtrado = df_ext[
        (df_ext['DATA'] >= start_date) & 
        (df_ext['DATA'] <= end_date)
    ].copy()
    
    df_int_filtrado = df_int[
        (df_int['DATA'] >= start_date) & 
        (df_int['DATA'] <= end_date)
    ].copy()
    
    df_val_filtrado = df_val[
        (df_val['DATA'] >= start_date) & 
        (df_val['DATA'] <= end_date)
    ].copy()

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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 VISÃO GERAL", 
        "🚙 ANÁLISE POR VEÍCULO", 
        "⚡ EFICIÊNCIA", 
        "📈 TENDÊNCIAS"
    ])

    with tab1:
        st.subheader("Visão Consolidada")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Litros Externos", f"{total_ext:,.1f} L")
        with col2:
            st.metric("Total Gasto Externo", f"R$ {valor_ext:,.2f}")
        with col3:
            st.metric("Total Litros Internos", f"{total_int:,.1f} L")
        with col4:
            st.metric("Total Gasto Interno", f"R$ {valor_int:,.2f}")

        # Gráfico de distribuição
        fig_dist = px.pie(
            names=['Externo', 'Interno'],
            values=[total_ext, total_int],
            title='Distribuição do Consumo',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with tab2:
        st.subheader("Desempenho por Veículo")
        
        # Consumo por veículo (externo)
        consumo_ext = df_ext_filtrado.groupby('PLACA').agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        consumo_ext['TIPO'] = 'EXTERNO'

        # Consumo por veículo (interno)
        consumo_int = df_int_filtrado.groupby('PLACA').agg({
            'LITROS': 'sum'
        }).reset_index()
        
        # Combinar com valores internos
        if 'PLACA' in df_val_filtrado.columns:
            valores_int = df_val_filtrado.groupby('PLACA')['VALOR'].sum().reset_index()
            consumo_int = pd.merge(consumo_int, valores_int, on='PLACA', how='left')
        else:
            consumo_int['VALOR'] = valor_int / len(consumo_int) if len(consumo_int) > 0 else 0
        
        consumo_int['TIPO'] = 'INTERNO'

        # Combinar dados
        df_consumo = pd.concat([consumo_ext, consumo_int])
        
        # Tabela detalhada
        st.dataframe(
            df_consumo.style
                .format({
                    'LITROS': '{:,.1f} L',
                    'VALOR': 'R$ {:,.2f}'
                })
                .apply(lambda x: style_dataframe(pd.DataFrame(x), ['LITROS', 'VALOR']), axis=None),
            height=500,
            use_container_width=True
        )

    with tab3:
        st.subheader("Análise de Eficiência")
        
        # Calcular consumo médio (km/l)
        def calcular_consumo(df):
            df = df.sort_values(['PLACA', 'DATA'])
            df['KM_RODADOS'] = df.groupby('PLACA')['KM_ATUAL'].diff()
            df['CONSUMO_KM_L'] = np.where(
                (df['LITROS'] > 0) & (df['KM_RODADOS'] > 0),
                df['KM_RODADOS'] / df['LITROS'],
                np.nan
            )
            return df

        df_ext_eff = calcular_consumo(df_ext_filtrado)
        df_int_eff = calcular_consumo(df_int_filtrado)
        
        # Combinar resultados
        df_eficiencia = pd.concat([
            df_ext_eff[['PLACA', 'CONSUMO_KM_L']],
            df_int_eff[['PLACA', 'CONSUMO_KM_L']]
        ]).dropna()
        
        consumo_medio = df_eficiencia.groupby('PLACA')['CONSUMO_KM_L'].mean().reset_index()
        consumo_medio = consumo_medio.sort_values('CONSUMO_KM_L', ascending=False)
        
        # Classificação de eficiência
        def classificar_eficiencia(km_l):
            if km_l > 8: return '⭐ Excelente'
            elif km_l > 6: return '👍 Bom'
            elif km_l > 4: return '➖ Regular'
            else: return '👎 Ruim'
        
        consumo_medio['CLASSIFICACAO'] = consumo_medio['CONSUMO_KM_L'].apply(classificar_eficiencia)
        
        # Exibir resultados
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(
                consumo_medio.style
                    .format({'CONSUMO_KM_L': '{:.2f} km/L'})
                    .apply(lambda x: style_dataframe(pd.DataFrame(x), ['CONSUMO_KM_L']), axis=None),
                height=500
            )
        
        with col2:
            fig = px.bar(
                consumo_medio,
                x='CONSUMO_KM_L',
                y='PLACA',
                orientation='h',
                color='CLASSIFICACAO',
                title='Desempenho dos Veículos',
                color_discrete_map={
                    '⭐ Excelente': '#2ecc71',
                    '👍 Bom': '#3498db',
                    '➖ Regular': '#f39c12',
                    '👎 Ruim': '#e74c3c'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Análise Temporal")
        
        # Configuração de período
        periodo = st.selectbox(
            "Agrupar dados por",
            ["Diário", "Semanal", "Mensal"],
            key="periodo_agrupamento"
        )
        
        freq = {
            "Diário": "D",
            "Semanal": "W-MON",
            "Mensal": "ME"
        }[periodo]
        
        # Preparar dados externos
        df_ext_trend = df_ext_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum',
            'VALOR': 'sum'
        }).reset_index()
        df_ext_trend['PRECO_MEDIO'] = df_ext_trend['VALOR'] / df_ext_trend['LITROS']
        df_ext_trend['TIPO'] = 'EXTERNO'
        
        # Preparar dados internos
        df_int_trend = df_int_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'LITROS': 'sum'
        }).reset_index()
        
        df_val_trend = df_val_filtrado.groupby(pd.Grouper(key='DATA', freq=freq)).agg({
            'VALOR': 'sum'
        }).reset_index()
        
        df_int_full = pd.merge(df_int_trend, df_val_trend, on='DATA')
        df_int_full['PRECO_MEDIO'] = df_int_full['VALOR'] / df_int_full['LITROS']
        df_int_full['TIPO'] = 'INTERNO'
        
        # Gráficos
        fig1 = px.line(
            df_ext_trend,
            x='DATA',
            y='LITROS',
            title='Consumo Externo ao Longo do Tempo',
            labels={'LITROS': 'Litros consumidos', 'DATA': 'Data'}
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.line(
            pd.concat([df_ext_trend, df_int_trend]),
            x='DATA',
            y='LITROS',
            color='TIPO',
            title='Comparativo de Consumo',
            labels={'LITROS': 'Litros consumidos', 'DATA': 'Data'}
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = px.line(
            pd.concat([df_ext_trend, df_int_full]),
            x='DATA',
            y='PRECO_MEDIO',
            color='TIPO',
            title='Evolução do Preço Médio (R$/L)',
            labels={'PRECO_MEDIO': 'Preço por litro (R$)', 'DATA': 'Data'}
        )
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
