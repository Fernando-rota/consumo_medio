import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- Função para carregar e processar dados ---
@st.cache_data
def carregar_dados(uploaded_file):
    try:
        interno = pd.read_excel(uploaded_file, sheet_name='Abastecimento Interno')
        externo = pd.read_excel(uploaded_file, sheet_name='Abastecimento Externo')

        # Padronização interno
        interno = interno.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual',
            'Tipo': 'tipo'
        })
        interno['data'] = pd.to_datetime(interno['data'], dayfirst=True, errors='coerce')
        interno['placa'] = interno['placa'].astype(str).str.strip().str.upper()
        interno['km_atual'] = pd.to_numeric(interno['km_atual'], errors='coerce')
        interno['litros'] = pd.to_numeric(interno['litros'], errors='coerce')
        interno['tipo'] = interno['tipo'].astype(str).str.lower()

        # Filtrar apenas saídas (abastecimentos)
        interno = interno[interno['tipo'] == 'saída']

        # Padronização externo
        externo = externo.rename(columns={
            'Placa': 'placa',
            'Data': 'data',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual'
        })
        externo['data'] = pd.to_datetime(externo['data'], dayfirst=True, errors='coerce')
        externo['placa'] = externo['placa'].astype(str).str.strip().str.upper()
        externo['km_atual'] = pd.to_numeric(externo['km_atual'], errors='coerce')
        externo['litros'] = pd.to_numeric(externo['litros'], errors='coerce')
        externo['tipo'] = 'externo'

        # Marcar tipo para interno
        interno['tipo'] = 'interno'

        # Concatenar
        df = pd.concat([interno, externo], ignore_index=True)

        # Ordenar e calcular diferença de km
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()
        df['consumo_por_km'] = df['litros'] / df['km_diff']
        df['km_por_litro'] = 1 / df['consumo_por_km']

        # Limpar dados inválidos
        df = df.dropna(subset=['km_diff', 'consumo_por_km'])
        df = df[df['km_diff'] > 0]

        return df

    except Exception as e:
        st.error(f'Erro ao carregar/processar os dados: {e}')
        return pd.DataFrame()

# --- Função para métricas principais ---
def calcular_metricas(df):
    total_abastecimentos = df.shape[0]
    total_litros = df['litros'].sum()
    km_rodados = df['km_diff'].sum()
    consumo_medio_geral = (total_litros / km_rodados) if km_rodados > 0 else np.nan

    # Consumo médio por tipo (interno x externo)
    consumo_tipo = df.groupby('tipo').apply(
        lambda x: (x['litros'].sum() / x['km_diff'].sum()) if x['km_diff'].sum() > 0 else np.nan
    ).to_dict()

    return {
        'total_abastecimentos': total_abastecimentos,
        'total_litros': total_litros,
        'km_rodados': km_rodados,
        'consumo_medio_geral': consumo_medio_geral,
        'consumo_medio_interno': consumo_tipo.get('interno', np.nan),
        'consumo_medio_externo': consumo_tipo.get('externo', np.nan)
    }

# --- Função para calcular consumo médio por veículo ---
def consumo_medio_por_veiculo(df):
    df_agg = df.groupby(['placa', 'tipo']).agg({
        'litros':'sum',
        'km_diff':'sum'
    }).reset_index()
    df_agg['consumo_medio'] = df_agg['litros'] / df_agg['km_diff']
    df_agg['km_por_litro'] = 1 / df_agg['consumo_medio']
    return df_agg

# --- Função para gráfico de tendência ---
def grafico_tendencia(df, placa_selecionada):
    df_placa = df[df['placa'] == placa_selecionada].copy()
    if df_placa.empty:
        return None

    # Agrupar por mês
    df_placa['mes'] = df_placa['data'].dt.to_period('M')
    df_mes = df_placa.groupby(['mes', 'tipo']).agg({
        'litros': 'sum',
        'km_diff': 'sum'
    }).reset_index()
    df_mes['consumo_medio'] = df_mes['litros'] / df_mes['km_diff']
    df_mes['km_por_litro'] = 1 / df_mes['consumo_medio']
    df_mes['mes'] = df_mes['mes'].dt.to_timestamp()

    fig = px.line(df_mes, x='mes', y='km_por_litro', color='tipo',
                  markers=True,
                  title=f'Tendência de Consumo (Km/L) - Veículo {placa_selecionada}')
    fig.update_layout(yaxis_title='Km por Litro', xaxis_title='Mês')
    return fig

# --- App principal ---
def main():
    st.set_page_config(page_title='Dashboard Consumo Médio por Veículo', layout='wide')

    st.title('🚛 Dashboard de Consumo Médio por Veículo')

    uploaded_file = st.file_uploader(
        'Faça upload do arquivo Excel com abas "Abastecimento Interno" e "Abastecimento Externo"',
        type=['xlsx']
    )

    if not uploaded_file:
        st.info('Aguardando upload do arquivo Excel...')
        return

    df = carregar_dados(uploaded_file)
    if df.empty:
        st.warning('Nenhum dado válido encontrado.')
        return

    # Sidebar filtros
    st.sidebar.header('Filtros')
    placas_disponiveis = sorted(df['placa'].unique())
    placa_selecionada = st.sidebar.multiselect('Selecione uma ou mais placas:', placas_disponiveis, default=placas_disponiveis)

    periodo_min = df['data'].min()
    periodo_max = df['data'].max()
    periodo = st.sidebar.date_input('Período:', [periodo_min, periodo_max], min_value=periodo_min, max_value=periodo_max)

    df_filtrado = df[
        (df['placa'].isin(placa_selecionada)) &
        (df['data'] >= pd.to_datetime(periodo[0])) &
        (df['data'] <= pd.to_datetime(periodo[1]))
    ]

    # Mostrar métricas gerais
    metricas = calcular_metricas(df_filtrado)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Abastecimentos', f"{metricas['total_abastecimentos']}")
    col2.metric('Litros Totais', f"{metricas['total_litros']:.2f} L")
    col3.metric('KM Rodados', f"{metricas['km_rodados']:.0f} km")
    if metricas['consumo_medio_geral'] and not np.isnan(metricas['consumo_medio_geral']):
        col4.metric('Consumo Médio Geral', f"{1/metricas['consumo_medio_geral']:.2f} km/L")
    else:
        col4.metric('Consumo Médio Geral', 'N/A')

    col5, col6 = st.columns(2)
    if metricas['consumo_medio_interno'] and not np.isnan(metricas['consumo_medio_interno']):
        col5.metric('Consumo Médio Interno', f"{1/metricas['consumo_medio_interno']:.2f} km/L")
    else:
        col5.metric('Consumo Médio Interno', 'N/A')

    if metricas['consumo_medio_externo'] and not np.isnan(metricas['consumo_medio_externo']):
        col6.metric('Consumo Médio Externo', f"{1/metricas['consumo_medio_externo']:.2f} km/L")
    else:
        col6.metric('Consumo Médio Externo', 'N/A')

    st.markdown('---')

    # Consumo médio por veículo e tipo
    st.subheader('Consumo Médio por Veículo e Tipo de Abastecimento')
    df_consumo_veiculo = consumo_medio_por_veiculo(df_filtrado)
    st.dataframe(
        df_consumo_veiculo[['placa', 'tipo', 'km_por_litro']].sort_values(['placa', 'tipo']),
        use_container_width=True
    )

    st.markdown('---')

    # Análise detalhada por veículo
    st.subheader('Análise Detalhada por Veículo')
    veiculo_analise = st.selectbox('Selecione o veículo para análise detalhada:', placas_disponiveis)

    fig_tendencia = grafico_tendencia(df_filtrado, veiculo_analise)
    if fig_tendencia:
        st.plotly_chart(fig_tendencia, use_container_width=True)
    else:
        st.warning('Sem dados para este veículo no período selecionado.')

    # Tabela detalhada para o veículo
    df_veiculo = df_filtrado[df_filtrado['placa'] == veiculo_analise].sort_values('data')
    st.write(f"Registros detalhados do veículo **{veiculo_analise}**:")
    st.dataframe(df_veiculo[['data', 'tipo', 'km_atual', 'km_diff', 'litros', 'km_por_litro']])

if __name__ == '__main__':
    main()
