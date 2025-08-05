import streamlit as st
from data import carregar_dados
from filters import aplicar_filtros
from plots import plot_visao_geral, plot_consumo_veiculos, plot_tendencia
from metrics import calcular_metricas, validar_consumo
from export import gerar_link_excel

st.set_page_config(page_title="Dashboard Consumo Médio", layout="wide")

st.title("🚛 Dashboard de Consumo Médio da Frota")

uploaded_file = st.sidebar.file_uploader("📤 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = carregar_dados(uploaded_file)
    if df.empty:
        st.error("Nenhum dado válido após processamento.")
        st.stop()

    # Filtros na sidebar
    filtros = aplicar_filtros(df)
    df_filtrado = filtros["df_filtrado"]

    metricas = calcular_metricas(df_filtrado)
    df_validacao = validar_consumo(df_filtrado, consumo_esperado_por_veiculo={}, tolerancia=0.3)

    tabs = st.tabs([
        "📊 Visão Geral",
        "🚗 Consumo por Veículo",
        "📈 Tendência",
        "🔍 Validação Consumo",
        "⬇️ Exportar Dados"
    ])

    with tabs[0]:
        plot_visao_geral(metricas)

    with tabs[1]:
        plot_consumo_veiculos(df_filtrado)

    with tabs[2]:
        veiculo = st.selectbox("Selecione veículo para análise de tendência", sorted(df_filtrado['placa'].unique()))
        plot_tendencia(df_filtrado, veiculo)

    with tabs[3]:
        st.markdown("### Validação do Consumo Médio")
        st.dataframe(df_validacao.style.applymap(
            lambda v: 'background-color: #ff9999' if v == 'Fora da margem' else ''
        , subset=['status']))

    with tabs[4]:
        st.download_button(
            label="📥 Baixar dados filtrados (Excel)",
            data=gerar_link_excel(df_filtrado),
            file_name="dados_consumo_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Envie o arquivo Excel no menu lateral para começar.")
