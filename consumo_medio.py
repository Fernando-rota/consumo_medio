import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

@st.cache_data
def carregar_dados(uploaded_file):
    try:
        interno = pd.read_excel(uploaded_file, sheet_name='Abastecimento Interno')
        externo = pd.read_excel(uploaded_file, sheet_name='Abastecimento Externo')

        interno = interno.rename(columns={
            'Data': 'data',
            'Placa': 'placa',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual',
            'Tipo': 'tipo'
        })
        interno['data'] = pd.to_datetime(interno['data'], dayfirst=True, errors='coerce')
        interno['placa'] = interno['placa'].astype(str).str.strip().str.upper()
        interno['litros'] = pd.to_numeric(interno['litros'], errors='coerce')
        interno['km_atual'] = pd.to_numeric(interno['km_atual'], errors='coerce')
        interno['tipo'] = interno['tipo'].astype(str).str.lower()
        interno = interno[interno['tipo'] == 'saída']

        externo = externo.rename(columns={
            'Data': 'data',
            'Placa': 'placa',
            'Quantidade de litros': 'litros',
            'KM Atual': 'km_atual'
        })
        externo['data'] = pd.to_datetime(externo['data'], dayfirst=True, errors='coerce')
        externo['placa'] = externo['placa'].astype(str).str.strip().str.upper()
        externo['litros'] = pd.to_numeric(externo['litros'], errors='coerce')
        externo['km_atual'] = pd.to_numeric(externo['km_atual'], errors='coerce')
        externo['tipo'] = 'externo'

        interno['tipo'] = 'interno'

        df = pd.concat([interno, externo], ignore_index=True)
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()
        df['consumo_por_km'] = df['litros'] / df['km_diff']
        df['km_por_litro'] = 1 / df['consumo_por_km']
        df = df.dropna(subset=['km_diff', 'consumo_por_km'])
        df = df[df['km_diff'] > 10]  # filtra trechos menores que 10 km para evitar ruído
        return df
    except Exception as e:
        st.error(f'Erro ao carregar/processar os dados: {e}')
        return pd.DataFrame()

def calcular_metricas(df):
    total_abastecimentos = df.shape[0]
    total_litros = df['litros'].sum()
    km_rodados = df['km_diff'].sum()
    consumo_medio_geral = (total_litros / km_rodados) if km_rodados > 0 else np.nan

    consumo_interno = df[df['tipo'] == 'interno']
    consumo_externo = df[df['tipo'] == 'externo']

    consumo_medio_interno = (consumo_interno['litros'].sum() / consumo_interno['km_diff'].sum()) if consumo_interno['km_diff'].sum() > 0 else np.nan
    consumo_medio_externo = (consumo_externo['litros'].sum() / consumo_externo['km_diff'].sum()) if consumo_externo['km_diff'].sum() > 0 else np.nan

    return {
        'total_abastecimentos': total_abastecimentos,
        'total_litros': total_litros,
        'km_rodados': km_rodados,
        'consumo_medio_geral': consumo_medio_geral,
        'consumo_medio_interno': consumo_medio_interno,
        'consumo_medio_externo': consumo_medio_externo
    }

def consumo_medio_por_veiculo(df):
    df_agg = df.groupby('placa').agg({
        'litros': 'sum',
        'km_diff': 'sum'
    }).reset_index()
    df_agg['consumo_medio'] = df_agg['litros'] / df_agg['km_diff']
    df_agg['km_por_litro'] = 1 / df_agg['consumo_medio']
    return df_agg.sort_values('km_por_litro', ascending=False)

def grafico_tendencia(df, placa):
    df_veiculo = df[df['placa'] == placa].copy()
    if df_veiculo.empty:
        return None

    df_veiculo['mes'] = df_veiculo['data'].dt.to_period('M').dt.to_timestamp()
    df_mes = df_veiculo.groupby('mes').agg({'litros': 'sum', 'km_diff': 'sum'}).reset_index()
    df_mes['consumo'] = df_mes['litros'] / df_mes['km_diff']
    df_mes['km_por_litro'] = 1 / df_mes['consumo']

    fig = px.line(df_mes, x='mes', y='km_por_litro', markers=True,
                  title=f'Tendência de Consumo (Km/L) - Veículo {placa}')
    fig.update_layout(yaxis_title='Km por Litro', xaxis_title='Mês')
    return fig

def validar_consumo(df, consumo_esperado_por_veiculo, tolerancia=0.3):
    resultados = []
    for placa, esperado in consumo_esperado_por_veiculo.items():
        df_veiculo = df[df['placa'] == placa]
        litros = df_veiculo['litros'].sum()
        km = df_veiculo['km_diff'].sum()
        if km == 0 or litros == 0:
            resultados.append((placa, np.nan, 'Sem dados suficientes'))
            continue
        consumo_calc = litros / km  # litros por km
        desvio = abs(consumo_calc - esperado) / esperado
        status = 'OK' if desvio <= tolerancia else 'Fora da margem'
        resultados.append((placa, consumo_calc, status))
    df_result = pd.DataFrame(resultados, columns=['placa', 'consumo_calculado_L_km', 'status'])
    df_result['km_por_litro'] = 1 / df_result['consumo_calculado_L_km']
    return df_result

def main():
    st.set_page_config(page_title='Dashboard Consumo Médio - Frota', layout='wide')
    st.title('🚛 Dashboard de Consumo Médio da Frota')

    uploaded_file = st.file_uploader('Faça upload do arquivo Excel com abas "Abastecimento Interno" e "Abastecimento Externo"', type=['xlsx'])
    if not uploaded_file:
        st.info('Aguardando upload do arquivo...')
        return

    df = carregar_dados(uploaded_file)
    if df.empty:
        st.warning('Nenhum dado válido após o processamento.')
        return

    st.sidebar.header('Filtros')
    placas = sorted(df['placa'].unique())
    placas_selecionadas = st.sidebar.multiselect('Selecione veículos:', placas, default=placas)

    data_min = df['data'].min()
    data_max = df['data'].max()
    periodo = st.sidebar.date_input('Período:', [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtrado = df[
        (df['placa'].isin(placas_selecionadas)) &
        (df['data'] >= pd.to_datetime(periodo[0])) &
        (df['data'] <= pd.to_datetime(periodo[1]))
    ]

    metricas = calcular_metricas(df_filtrado)
    df_consumo = consumo_medio_por_veiculo(df_filtrado)

    # Exemplo: defina seus consumos esperados em L/km para cada placa abaixo
    consumo_esperado_por_veiculo = {
        # 'ABC1234': 0.20, # 5 km/l
        # 'XYZ5678': 0.15, # 6.66 km/l
        # Coloque aqui as placas reais da frota e seus valores de consumo esperado
    }

    df_validacao = validar_consumo(df_filtrado, consumo_esperado_por_veiculo, tolerancia=0.3)

    aba_geral, aba_veiculos, aba_tendencias, aba_validacao = st.tabs([
        '📊 Visão Geral', '🚗 Detalhes por Veículo', '📈 Tendências', '🔍 Validação Consumo'
    ])

    with aba_geral:
        st.header('Visão Geral da Frota')
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Abastecimentos', f"{metricas['total_abastecimentos']}")
        col2.metric('Litros Totais', f"{metricas['total_litros']:.2f} L")
        col3.metric('KM Rodados', f"{metricas['km_rodados']:.0f} km")
        col4.metric('Consumo Médio Geral', f"{(1/metricas['consumo_medio_geral']):.2f} km/L" if not np.isnan(metricas['consumo_medio_geral']) else 'N/A')

        col5, col6 = st.columns(2)
        col5.metric('Consumo Médio Interno', f"{(1/metricas['consumo_medio_interno']):.2f} km/L" if not np.isnan(metricas['consumo_medio_interno']) else 'N/A')
        col6.metric('Consumo Médio Externo', f"{(1/metricas['consumo_medio_externo']):.2f} km/L" if not np.isnan(metricas['consumo_medio_externo']) else 'N/A')

        st.markdown('---')
        st.markdown('### Distribuição do Consumo Médio por Veículo')
        fig_bar = px.bar(df_consumo, x='placa', y='km_por_litro',
                         labels={'placa': 'Veículo', 'km_por_litro': 'Km por Litro'},
                         title='Consumo Médio (Km/L) por Veículo',
                         color='km_por_litro', color_continuous_scale='Viridis')
        st.plotly_chart(fig_bar, use_container_width=True)

    with aba_veiculos:
        st.header('Detalhes por Veículo')

        st.markdown('### Ranking de Consumo')
        melhores = df_consumo.head(5)
        piores = df_consumo.tail(5)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**Melhores Consumidores (Km/L)**')
            st.table(melhores[['placa', 'km_por_litro']].rename(columns={'placa': 'Veículo', 'km_por_litro': 'Km por Litro'}).style.format({'Km por Litro': '{:.2f}'}))
        with col2:
            st.markdown('**Piores Consumidores (Km/L)**')
            st.table(piores[['placa', 'km_por_litro']].rename(columns={'placa': 'Veículo', 'km_por_litro': 'Km por Litro'}).style.format({'Km por Litro': '{:.2f}'}))

        st.markdown('---')
        st.markdown('### Tabela Completa')
        st.dataframe(df_consumo.rename(columns={'placa': 'Veículo', 'km_por_litro': 'Km por Litro'}).style.format({'Km por Litro': '{:.2f}'}))

    with aba_tendencias:
        st.header('Tendência de Consumo ao Longo do Tempo')
        veiculo_analise = st.selectbox('Selecione o veículo:', placas_selecionadas)
        fig = grafico_tendencia(df_filtrado, veiculo_analise)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Sem dados suficientes para gerar gráfico.')

    with aba_validacao:
        st.header('🔍 Validação do Consumo Médio por Veículo')
        st.markdown('Veículos classificados como "Fora da margem" estão com consumo calculado fora do intervalo aceitável ±30% do esperado.')

        if df_validacao.empty:
            st.info('Nenhum consumo esperado configurado para validação. Atualize o dicionário `consumo_esperado_por_veiculo` no código.')
        else:
            fora_margem = df_validacao[df_validacao['status'] == 'Fora da margem']
            ok = df_validacao[df_validacao['status'] == 'OK']

            st.write(f'Veículos com consumo fora da margem: {fora_margem.shape[0]}')
            st.write(f'Veículos dentro da margem: {ok.shape[0]}')

            def color_row(row):
                if row.status == 'Fora da margem':
                    return ['background-color: #ff9999']*len(row)
                else:
                    return ['background-color: #b6fcd5']*len(row)

            st.dataframe(df_validacao.style.apply(color_row, axis=1).format({
                'consumo_calculado_L_km': '{:.3f}',
                'km_por_litro': '{:.2f}'
            }))

if __name__ == '__main__':
    main()
