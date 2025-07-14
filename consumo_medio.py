import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='⛽ Dashboard de Abastecimento', layout='wide')

@st.cache_data
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith('.csv'):
            # tenta detectar separador automaticamente
            try:
                df = pd.read_csv(file, sep=None, engine='python')
            except:
                df = pd.read_csv(file, sep=';', engine='python')
        else:
            df = pd.read_excel(file)
        # Padroniza colunas: minúsculas e sem espaços
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

def tratar_valor(x):
    try:
        # Remove símbolos e converte para float
        return float(str(x).replace('r$', '').replace('.', '').replace(',', '.').strip())
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def main():
    st.title("⛽ Dashboard de Abastecimento Interno vs Externo")

    # Upload dos arquivos
    uploaded_ext = st.file_uploader("📁 Base Abastecimento Externo (CSV ou XLSX)", type=['csv', 'xlsx'])
    uploaded_int = st.file_uploader("📁 Base Abastecimento Interno (CSV ou XLSX)", type=['csv', 'xlsx'])
    uploaded_comb = st.file_uploader("📁 Base Combustível (Valores) (CSV ou XLSX)", type=['csv', 'xlsx'])

    if not uploaded_ext or not uploaded_int or not uploaded_comb:
        st.info("⚠️ Faça upload dos três arquivos para continuar")
        return

    # Carregar bases com padronização de colunas
    df_ext = carregar_base(uploaded_ext, "Abastecimento Externo")
    df_int = carregar_base(uploaded_int, "Abastecimento Interno")
    df_comb = carregar_base(uploaded_comb, "Combustível (Valores)")

    if df_ext is None or df_int is None or df_comb is None:
        return

    # Verificar colunas essenciais
    col_essenciais_ext = ['data', 'placa', 'consumo', 'custo total', 'descriçao do abastecimento']
    col_essenciais_int = ['data', 'tipo', 'placa', 'quantidade de litros']
    col_essenciais_comb = ['emissao', 'valor']

    for col in col_essenciais_ext:
        if col not in df_ext.columns:
            st.error(f"Coluna obrigatória '{col}' não encontrada na base externa.")
            return
    for col in col_essenciais_int:
        if col not in df_int.columns:
            st.error(f"Coluna obrigatória '{col}' não encontrada na base interna.")
            return
    for col in col_essenciais_comb:
        if col not in df_comb.columns:
            st.error(f"Coluna obrigatória '{col}' não encontrada na base de valores.")
            return

    # Converter datas
    df_ext['data'] = pd.to_datetime(df_ext['data'], dayfirst=True, errors='coerce')
    df_int['data'] = pd.to_datetime(df_int['data'], dayfirst=True, errors='coerce')
    df_comb['emissao'] = pd.to_datetime(df_comb['emissao'], dayfirst=True, errors='coerce')

    # Tratar colunas numéricas
    df_ext['consumo'] = df_ext['consumo'].apply(tratar_litros)
    df_ext['custo total'] = df_ext['custo total'].apply(tratar_valor)
    df_int['quantidade de litros'] = df_int['quantidade de litros'].apply(tratar_litros)
    df_comb['valor'] = df_comb['valor'].apply(tratar_valor)

    # Padronizar placas: maiúsculas, sem espaços
    df_ext['placa'] = df_ext['placa'].astype(str).str.upper().str.strip()
    df_int['placa'] = df_int['placa'].astype(str).str.upper().str.strip()

    # Filtros na barra lateral
    st.sidebar.header("Filtros")

    # Filtro placa (concatena todas as placas para o filtro)
    placas_ext = set(df_ext['placa'].unique())
    placas_int = set(df_int['placa'].unique())
    placas_all = sorted(placas_ext.union(placas_int))
    placa_selec = st.sidebar.multiselect("Placa(s)", options=placas_all, default=placas_all)
    if placa_selec:
        df_ext = df_ext[df_ext['placa'].isin(placa_selec)]
        df_int = df_int[df_int['placa'].isin(placa_selec)]

    # Filtro combustível externo (descriçao do abastecimento)
    combustiveis_ext = df_ext['descriçao do abastecimento'].dropna().unique()
    combust_selec = st.sidebar.multiselect("Tipo Combustível (Externo)", options=combustiveis_ext, default=combustiveis_ext)
    if combust_selec:
        df_ext = df_ext[df_ext['descriçao do abastecimento'].isin(combust_selec)]

    # Filtro data (intervalo comum entre as bases)
    min_data = max(df_ext['data'].min(), df_int['data'].min(), df_comb['emissao'].min())
    max_data = min(df_ext['data'].max(), df_int['data'].max(), df_comb['emissao'].max())
    data_selec = st.sidebar.date_input("Período", [min_data.date(), max_data.date()])
    if len(data_selec) == 2:
        start_date, end_date = pd.to_datetime(data_selec[0]), pd.to_datetime(data_selec[1])
        df_ext = df_ext[(df_ext['data'] >= start_date) & (df_ext['data'] <= end_date)]
        df_int = df_int[(df_int['data'] >= start_date) & (df_int['data'] <= end_date)]
        df_comb = df_comb[(df_comb['emissao'] >= start_date) & (df_comb['emissao'] <= end_date)]

    # Calcular médias e indicadores

    # Média valor por litro interno (usar apenas entradas)
    df_int_entrada = df_int[df_int['tipo'].str.lower() == 'entrada de diesel']
    litros_totais_int = df_int_entrada['quantidade de litros'].sum()
    valor_total_int = df_comb['valor'].sum()
    preco_medio_litro_int = valor_total_int / litros_totais_int if litros_totais_int > 0 else 0

    # Somar litros e custo externo
    litros_ext = df_ext['consumo'].sum()
    custo_ext = df_ext['custo total'].sum()

    # Somar litros interno
    litros_int = df_int['quantidade de litros'].sum()

    # Consumo médio Km/L
    # Para cálculo de consumo médio, precisamos do km atual e litros em sequência por veículo
    # Certifique-se que 'km atual' esteja em df_ext e df_int para cálculo, se não tiver, ignorar consumo médio
    def calcula_consumo_medio(df):
        if 'km atual' not in df.columns:
            return pd.DataFrame(columns=['placa', 'km_l_med'])
        df = df.copy()
        df['km atual'] = pd.to_numeric(df['km atual'], errors='coerce')
        df = df.dropna(subset=['placa', 'data', 'km atual'])
        df = df.sort_values(['placa', 'data'])
        # Calcula km rodado entre registros
        df['km_diff'] = df.groupby('placa')['km atual'].diff()
        df = df[df['km_diff'] > 0]
        df['km_l'] = df['km_diff'] / df['consumo'].replace(0, pd.NA)
        return df.groupby('placa')['km_l'].mean().reset_index().rename(columns={'km_l': 'Km/L médio'})

    # Para interno, o campo 'consumo' não existe, usamos 'quantidade de litros'
    def calcula_consumo_medio_interno(df):
        if 'km atual' not in df.columns:
            return pd.DataFrame(columns=['placa', 'km_l_med'])
        df = df.copy()
        df['km atual'] = pd.to_numeric(df['km atual'], errors='coerce')
        df = df.dropna(subset=['placa', 'data', 'km atual'])
        df = df.sort_values(['placa', 'data'])
        df['km_diff'] = df.groupby('placa')['km atual'].diff()
        df = df[df['km_diff'] > 0]
        df['km_l'] = df['km_diff'] / df['quantidade de litros'].replace(0, pd.NA)
        return df.groupby('placa')['km_l'].mean().reset_index().rename(columns={'km_l': 'Km/L médio'})

    consumo_medio_ext = calcula_consumo_medio(df_ext)
    consumo_medio_int = calcula_consumo_medio_interno(df_int)

    # Mostrar indicadores
    st.subheader("📊 Indicadores Gerais")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Litros Consumidos (Externo)", f"{litros_ext:.2f} L")
    col2.metric("Custo Total (Externo)", f"R$ {custo_ext:.2f}")
    col3.metric("Litros Consumidos (Interno)", f"{litros_int:.2f} L")
    col4.metric("Preço Médio Litro Interno", f"R$ {preco_medio_litro_int:.3f}")
    # Média consumo Km/L (externo e interno) — média geral
    km_l_ext = consumo_medio_ext['Km/L médio'].mean() if not consumo_medio_ext.empty else 0
    km_l_int = consumo_medio_int['Km/L médio'].mean() if not consumo_medio_int.empty else 0
    col5.metric("Consumo Médio Km/L (Ext / Int)", f"{km_l_ext:.2f} / {km_l_int:.2f}")

    # Gráfico litros externos e internos por placa
    st.subheader("🚗 Litros Consumidos por Veículo")
    litros_ext_placa = df_ext.groupby('placa')['consumo'].sum().reset_index()
    litros_int_placa = df_int.groupby('placa')['quantidade de litros'].sum().reset_index()

    fig_litros = px.bar(
        pd.merge(litros_ext_placa, litros_int_placa, on='placa', how='outer').fillna(0).melt(id_vars='placa'),
        x='placa', y='value', color='variable',
        labels={'value': 'Litros', 'placa': 'Placa', 'variable': 'Origem'},
        title='Litros Consumidos - Externo (consumo) vs Interno (quantidade de litros)'
    )
    st.plotly_chart(fig_litros, use_container_width=True)

    # Gráfico Consumo médio Km/L por veículo (externo)
    st.subheader("⛽ Consumo Médio Km/L por Veículo (Externo)")
    if not consumo_medio_ext.empty:
        fig_kml_ext = px.bar(
            consumo_medio_ext.sort_values('Km/L médio', ascending=False),
            x='Km/L médio', y='placa', orientation='h',
            color='Km/L médio', color_continuous_scale='Viridis',
            labels={'Km/L médio': 'Km/L', 'placa': 'Placa'},
            title='Consumo Médio Externo'
        )
        st.plotly_chart(fig_kml_ext, use_container_width=True)
    else:
        st.write("Dados insuficientes para cálculo de consumo médio externo.")

    # Gráfico Consumo médio Km/L por veículo (interno)
    st.subheader("⛽ Consumo Médio Km/L por Veículo (Interno)")
    if not consumo_medio_int.empty:
        fig_kml_int = px.bar(
            consumo_medio_int.sort_values('Km/L médio', ascending=False),
            x='Km/L médio', y='placa', orientation='h',
            color='Km/L médio', color_continuous_scale='Viridis',
            labels={'Km/L médio': 'Km/L', 'placa': 'Placa'},
            title='Consumo Médio Interno'
        )
        st.plotly_chart(fig_kml_int, use_container_width=True)
    else:
        st.write("Dados insuficientes para cálculo de consumo médio interno.")

if __name__ == "__main__":
    main()
