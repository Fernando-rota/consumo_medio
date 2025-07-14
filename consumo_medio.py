import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

# Funções auxiliares
@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python')
        else:
            df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

def tratar_valor(x):
    try:
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.').strip())
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def main():
    st.title("⛽ Dashboard de Abastecimento Interno vs Externo")
    st.markdown("Comparativo de consumo, custo e eficiência por veículo")

    with st.sidebar:
        st.subheader("📁 Upload das Bases")
        up_comb = st.file_uploader("Base Combustível (compras)", type=['xlsx', 'csv'])
        up_ext = st.file_uploader("Base Abastecimento Externo", type=['xlsx', 'csv'])
        up_int = st.file_uploader("Base Abastecimento Interno", type=['xlsx', 'csv'])

    if not (up_comb and up_ext and up_int):
        st.info("⚠️ Envie as três bases para continuar.")
        return

    df_comb = carregar_base(up_comb, 'Combustível')
    df_ext = carregar_base(up_ext, 'Externo')
    df_int = carregar_base(up_int, 'Interno')

    if None in [df_comb, df_ext, df_int]:
        return

    # Padroniza colunas
    df_comb.rename(columns={'emissao': 'data', 'valor': 'valor'}, inplace=True)
    df_ext.rename(columns={'consumo': 'litros', 'custo total': 'custo'}, inplace=True)
    df_int.rename(columns={'quantidade de litros': 'litros'}, inplace=True)

    df_comb['data'] = pd.to_datetime(df_comb['data'], errors='coerce')
    df_ext['data'] = pd.to_datetime(df_ext['data'], errors='coerce')
    df_int['data'] = pd.to_datetime(df_int['data'], errors='coerce')

    df_comb['valor'] = df_comb['valor'].apply(tratar_valor)
    df_ext['litros'] = df_ext['litros'].apply(tratar_litros)
    df_ext['custo'] = df_ext['custo'].apply(tratar_valor)
    df_int['litros'] = df_int['litros'].apply(tratar_litros)

    # Filtro de data
    min_data = min(df_comb['data'].min(), df_ext['data'].min(), df_int['data'].min())
    max_data = max(df_comb['data'].max(), df_ext['data'].max(), df_int['data'].max())
    data_ini, data_fim = st.sidebar.date_input("Período", [min_data.date(), max_data.date()])

    df_comb = df_comb[(df_comb['data'].dt.date >= data_ini) & (df_comb['data'].dt.date <= data_fim)]
    df_ext = df_ext[(df_ext['data'].dt.date >= data_ini) & (df_ext['data'].dt.date <= data_fim)]
    df_int = df_int[(df_int['data'].dt.date >= data_ini) & (df_int['data'].dt.date <= data_fim)]

    # Filtros
    placas = sorted(set(df_ext['placa'].dropna().unique()) | set(df_int['placa'].dropna().unique()))
    placa_filtro = st.sidebar.multiselect("Placas", options=placas, default=placas)

    df_ext = df_ext[df_ext['placa'].isin(placa_filtro)]
    df_int = df_int[df_int['placa'].isin(placa_filtro)]

    # KPIs principais
    litros_ext = df_ext['litros'].sum()
    custo_ext = df_ext['custo'].sum()

    df_int_saida = df_int[df_int['tipo'].str.lower().str.contains("saida")]
    litros_int = df_int_saida['litros'].sum()

    custo_int = df_comb['valor'].sum()
    total_litros = litros_ext + litros_int

    perc_ext = litros_ext / total_litros * 100 if total_litros > 0 else 0
    perc_int = litros_int / total_litros * 100 if total_litros > 0 else 0

    st.subheader("🔢 Indicadores Gerais")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⛽ Litros (Externo)", f"{litros_ext:.2f} L", delta=f"{perc_ext:.1f}%")
    c2.metric("💰 Custo (Externo)", f"R$ {custo_ext:.2f}")
    c3.metric("⛽ Litros (Interno)", f"{litros_int:.2f} L", delta=f"{perc_int:.1f}%")
    c4.metric("💰 Custo (Interno)", f"R$ {custo_int:.2f}")

    st.subheader("📊 Comparativo Visual")
    df_kpi = pd.DataFrame({
        'Origem': ['Interno', 'Externo'],
        'Litros': [litros_int, litros_ext],
        'Custo': [custo_int, custo_ext]
    })

    fig = px.bar(df_kpi.melt(id_vars='Origem'),
                 x='Origem', y='value', color='variable', barmode='group',
                 text_auto='.2s', labels={'value': 'Valor', 'variable': 'Métrica'})
    st.plotly_chart(fig, use_container_width=True)

if __name__ == '__main__':
    main()
