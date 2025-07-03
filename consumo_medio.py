import streamlit as st
import pandas as pd

st.set_page_config(page_title='Relatório de Abastecimento com Filtro de Ano', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato de arquivo não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None
        return df
    except Exception as e:
        st.error(f'Erro ao carregar {tipo_base}: {e}')
        return None

def tratar_valor(valor_str):
    try:
        valor = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(valor)
    except:
        return None

def detectar_coluna_data(df):
    for col in df.columns:
        if 'data' in col.lower():
            return col
    return None

def aplicar_filtro_ano(df, ano):
    col_data = detectar_coluna_data(df)
    if col_data:
        df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        return df[df[col_data].dt.year == ano]
    else:
        return pd.DataFrame()  # retorna vazio se não achar coluna de data

def calcular_externo(df):
    litros = pd.to_numeric(df.get('CONSUMO', None), errors='coerce')
    if 'C/ DESC' in df.columns:
        valor = df['C/ DESC'].apply(tratar_valor)
    elif 'CUSTO TOTAL' in df.columns:
        valor = df['CUSTO TOTAL'].apply(tratar_valor)
    else:
        valor = pd.Series([0]*len(df))
    return litros.sum(), valor.sum()

def calcular_interno(df):
    if 'Quantidade de litros' in df.columns:
        return pd.to_numeric(df['Quantidade de litros'], errors='coerce').sum()
    return 0

def calcular_consumo_medio(base1, base2):
    df1 = base1.rename(columns={
        'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'CONSUMO': 'litros'
    })
    df2 = base2.rename(columns={
        'Placa': 'placa', 'Data': 'data', 'KM Atual': 'km_atual', 'Quantidade de litros': 'litros'
    })

    for df in [df1, df2]:
        df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
        df['placa'] = df['placa'].astype(str).str.replace(' ', '').str.upper()
        df['km_atual'] = pd.to_numeric(df['km_atual'], errors='coerce')
        df['litros'] = pd.to_numeric(df['litros'], errors='coerce')

    df_comb = pd.concat([df1[['placa', 'data', 'km_atual', 'litros']], df2[['placa', 'data', 'km_atual', 'litros']]])
    df_comb = df_comb.dropna()
    df_comb = df_comb.sort_values(['placa', 'data', 'km_atual'])

    df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
    df_comb['consumo_por_km'] = df_comb['litros'] / df_comb['km_diff']
    df_valid = df_comb[(df_comb['km_diff'] > 0) & (df_comb['consumo_por_km'].notnull())]

    consumo_medio = df_valid.groupby('placa')['consumo_por_km'].mean().reset_index()
    consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']
    return consumo_medio[['placa', 'km_por_litro']].sort_values(by='km_por_litro', ascending=False)

def main():
    st.title('⛽ Relatório de Abastecimento com Filtro de Ano')

    uploaded_base1 = st.file_uploader('📂 Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('📂 Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')

        if base1 is not None and base2 is not None:
            # Detectar anos disponíveis
            col_data1 = detectar_coluna_data(base1)
            col_data2 = detectar_coluna_data(base2)
            anos1 = pd.to_datetime(base1[col_data1], dayfirst=True, errors='coerce').dt.year.dropna().unique()
            anos2 = pd.to_datetime(base2[col_data2], dayfirst=True, errors='coerce').dt.year.dropna().unique()
            anos_disponiveis = sorted(set(anos1).union(set(anos2)))

            ano = st.selectbox("📅 Escolha o ano para análise:", anos_disponiveis, index=len(anos_disponiveis)-1)

            base1_ano = aplicar_filtro_ano(base1, ano)
            base2_ano = aplicar_filtro_ano(base2, ano)

            st.markdown(f"**Linhas externas para {ano}:** {len(base1_ano)}")
            st.markdown(f"**Linhas internas para {ano}:** {len(base2_ano)}")

            litros_ext, valor_ext = calcular_externo(base1_ano)
            litros_int = calcular_interno(base2_ano)

            total_geral = litros_ext + litros_int
            perc_ext = (litros_ext / total_geral) * 100 if total_geral > 0 else 0
            perc_int = (litros_int / total_geral) * 100 if total_geral > 0 else 0

            st.markdown(f"### 🔍 Comparativo Interno x Externo – {ano}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric('🚛 Litros externos', f'{litros_ext:,.2f} L')
                st.metric('💰 Valor gasto', f'R$ {valor_ext:,.2f}')
                st.metric('🔴 % externo', f'{perc_ext:.1f}%')
            with col2:
                st.metric('🏭 Litros internos', f'{litros_int:,.2f} L')
                st.metric('🟢 % interno', f'{perc_int:.1f}%')

            st.divider()
            st.markdown(f"### 📈 Consumo Médio por Veículo – {ano}")
            consumo_medio = calcular_consumo_medio(base1_ano, base2_ano)
            st.dataframe(consumo_medio.style.format({'km_por_litro': '{:.2f}'}), height=400)

        else:
            st.warning('❌ Falha ao processar uma das bases.')
    else:
        st.info('⬆️ Faça upload das duas bases para visualizar o relatório.')

if __name__ == '__main__':
    main()

