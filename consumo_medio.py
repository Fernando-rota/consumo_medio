import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python')
        else:
            df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.upper()
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
    st.title("⛽ Dashboard de Abastecimento - Interno vs Externo")

    with st.expander("📁 Carregar Arquivos"):
        col1, col2, col3 = st.columns(3)
        up_ext = col1.file_uploader("📄 Abastecimento Externo", type=["csv", "xlsx"])
        up_int = col2.file_uploader("📄 Abastecimento Interno", type=["csv", "xlsx"])
        up_val = col3.file_uploader("📄 Valores de Diesel", type=["csv", "xlsx"])

    if not (up_ext and up_int and up_val):
        st.warning("🔄 Por favor, envie os três arquivos para prosseguir.")
        return

    df_ext = carregar_base(up_ext, "Externo")
    df_int = carregar_base(up_int, "Interno")
    df_val = carregar_base(up_val, "Combustível")

    if df_ext is None or df_int is None or df_val is None:
        return

    # Padroniza colunas
    df_ext['PLACA'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    df_int['PLACA'] = df_int['PLACA'].astype(str).str.upper().str.strip()
    df_val['PLACA'] = df_val.get('PLACA', pd.Series([""] * len(df_val))).astype(str).str.upper().str.strip()

    df_ext['LITROS'] = pd.to_numeric(df_ext['CONSUMO'].apply(tratar_litros), errors='coerce').fillna(0.0)
    df_ext['CUSTO TOTAL'] = df_ext['CUSTO TOTAL'].apply(tratar_valor)
    df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
    df_ext['KM ATUAL'] = pd.to_numeric(df_ext['KM ATUAL'], errors='coerce')

    df_int = df_int[df_int['PLACA'] != '-']
    df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
    df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(df_int['QUANTIDADE DE LITROS'], errors='coerce').fillna(0.0)
    df_int['KM ATUAL'] = pd.to_numeric(df_int['KM ATUAL'], errors='coerce')

    df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
    df_val['VALOR'] = df_val['VALOR'].apply(tratar_valor)

    # Filtros globais
    placas_disponiveis = sorted(set(df_ext['PLACA'].unique()) | set(df_int['PLACA'].unique()))
    tipos_combustivel = sorted(df_ext['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique())

    st.sidebar.header("🔎 Filtros Globais")
    placa_sel = st.sidebar.multiselect("🚗 Placas", options=placas_disponiveis, default=placas_disponiveis)
    tipo_sel = st.sidebar.multiselect("🛢️ Tipo de Combustível", options=tipos_combustivel, default=tipos_combustivel)

    data_min = min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min())
    data_max = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())

    data_ini, data_fim = st.sidebar.date_input("📅 Intervalo de Datas", [data_min, data_max])
    if data_ini > data_fim:
        st.sidebar.error("Data inicial não pode ser maior que a final.")
        return

    # Aplicar filtros
    df_ext = df_ext[
        (df_ext['PLACA'].isin(placa_sel)) &
        (df_ext['DESCRIÇÃO DO ABASTECIMENTO'].isin(tipo_sel)) &
        (df_ext['DATA'].dt.date.between(data_ini, data_fim))
    ]
    df_int = df_int[
        (df_int['PLACA'].isin(placa_sel)) &
        (df_int['DATA'].dt.date.between(data_ini, data_fim))
    ]
    df_val = df_val[df_val['DATA'].dt.date.between(data_ini, data_fim)]

    # KPIs
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()

    total_litros = litros_ext + litros_int
    perc_ext = litros_ext / total_litros * 100 if total_litros else 0
    perc_int = litros_int / total_litros * 100 if total_litros else 0

    st.markdown(f"### 📊 Período Selecionado: `{data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}`")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⛽ Litros Externo", f"{litros_ext:,.2f} L", delta=f"{perc_ext:.1f} %")
    col2.metric("💸 Valor Externo", f"R$ {valor_ext:,.2f}")
    col3.metric("⛽ Litros Interno", f"{litros_int:,.2f} L", delta=f"{perc_int:.1f} %")
    col4.metric("💸 Valor Interno", f"R$ {valor_int:,.2f}")

    st.divider()

    aba1, aba2, aba3, aba4 = st.tabs([
        "📈 Evolução Temporal",
        "🚚 Top 10 Veículos",
        "⚙️ Consumo Médio",
        "📑 Detalhamento por Data"
    ])

    with aba1:
        st.subheader("🔁 Consumo e Custo ao Longo do Tempo")
        ext_agg = df_ext.groupby('DATA').agg({'LITROS': 'sum', 'CUSTO TOTAL': 'sum'}).reset_index()
        int_agg = df_int.groupby('DATA').agg({'QUANTIDADE DE LITROS': 'sum'}).reset_index()
        val_agg = df_val.groupby('DATA').agg({'VALOR': 'sum'}).reset_index()

        preco_agg = pd.merge(val_agg, int_agg, on='DATA', how='inner')
        preco_agg['PREÇO MÉDIO'] = preco_agg.apply(
            lambda r: r['VALOR'] / r['QUANTIDADE DE LITROS'] if r['QUANTIDADE DE LITROS'] > 0 else 0, axis=1
        )

        st.plotly_chart(px.line(ext_agg, x='DATA', y='LITROS', title='⛽ Consumo Externo (L)'), use_container_width=True)
        st.plotly_chart(px.line(ext_agg, x='DATA', y='CUSTO TOTAL', title='💰 Custo Externo (R$)'), use_container_width=True)
        st.plotly_chart(px.line(int_agg, x='DATA', y='QUANTIDADE DE LITROS', title='⛽ Consumo Interno (L)'), use_container_width=True)
        st.plotly_chart(px.line(val_agg, x='DATA', y='VALOR', title='💰 Valor Pago Internamente (R$)'), use_container_width=True)
        st.plotly_chart(px.line(preco_agg, x='DATA', y='PREÇO MÉDIO', title='📊 Preço Médio Interno (R$/L)'), use_container_width=True)

    with aba2:
        top_ext = df_ext.groupby('PLACA')['LITROS'].sum().nlargest(10).reset_index()
        top_int = df_int.groupby('PLACA')['QUANTIDADE DE LITROS'].sum().nlargest(10).reset_index()

        col1, col2 = st.columns(2)
        fig1 = px.bar(top_ext, y='PLACA', x='LITROS', orientation='h', title='🔹 Top 10 Externo', color='LITROS')
        fig2 = px.bar(top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h', title='🟢 Top 10 Interno', color='QUANTIDADE DE LITROS')
        col1.plotly_chart(fig1, use_container_width=True)
        col2.plotly_chart(fig2, use_container_width=True)

    with aba3:
        df_comb = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(columns={'LITROS': 'LITROS_CONSUMO'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(columns={'QUANTIDADE DE LITROS': 'LITROS_CONSUMO'})
        ])
        df_comb = df_comb.dropna(subset=['PLACA', 'DATA', 'KM ATUAL', 'LITROS_CONSUMO']).sort_values(['PLACA', 'DATA'])
        df_comb['KM DIF'] = df_comb.groupby('PLACA')['KM ATUAL'].diff()
        df_comb = df_comb[df_comb['KM DIF'] > 0]
        df_comb['KM/L'] = df_comb['KM DIF'] / df_comb['LITROS_CONSUMO']

        resumo = df_comb.groupby('PLACA')['KM/L'].mean().reset_index().sort_values('KM/L', ascending=False)
        resumo['Classificação'] = resumo['KM/L'].apply(lambda x: 'Econômico' if x >= 6 else 'Normal' if x >= 3.5 else 'Ineficiente')

        col1, col2 = st.columns([1, 2])
        col1.dataframe(resumo.style.format({'KM/L': '{:.2f}'}), use_container_width=True)
        col2.plotly_chart(px.bar(resumo, y='PLACA', x='KM/L', color='Classificação', orientation='h', title='⚙️ Eficiência por Veículo (Km/L)'), use_container_width=True)

    with aba4:
        st.dataframe(df_comb.dropna(subset=['KM/L']).sort_values(['DATA', 'PLACA']))

if __name__ == '__main__':
    main()
