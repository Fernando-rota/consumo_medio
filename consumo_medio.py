import streamlit as st
import pandas as pd

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='wide')

# Utilitário para tratar valores em reais
def tratar_valor(valor_str):
    try:
        valor = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(valor)
    except:
        return None

# Carregar e tratar base externa
def calcular_externo(df):
    # Corrigir vírgulas e converter consumo
    if 'CONSUMO' in df.columns:
        litros = df['CONSUMO'].astype(str).str.replace(',', '.').str.replace(' ', '')
        litros = pd.to_numeric(litros, errors='coerce')
    else:
        litros = pd.Series([0] * len(df))

    # Tratar valores
    if 'C/ DESC' in df.columns:
        valor = df['C/ DESC'].apply(tratar_valor)
    elif 'CUSTO TOTAL' in df.columns:
        valor = df['CUSTO TOTAL'].apply(tratar_valor)
    else:
        valor = pd.Series([0] * len(df))

    df['litros'] = litros
    df['valor'] = valor
    return df

# Carregar e tratar base interna
def calcular_interno(df):
    df = df.rename(columns=lambda x: x.strip())
    if 'Quantidade de litros' in df.columns:
        df['litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    else:
        df['litros'] = 0
    return df

# Calcular consumo médio por veículo
def calcular_consumo_medio(df_combined):
    df_combined = df_combined.dropna(subset=['placa', 'data', 'km_atual', 'litros'])
    df_combined = df_combined.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
    df_combined['km_diff'] = df_combined.groupby('placa')['km_atual'].diff()
    df_combined['consumo_por_km'] = df_combined['litros'] / df_combined['km_diff']
    df_clean = df_combined[(df_combined['km_diff'] > 0) & (df_combined['consumo_por_km'].notna())]
    resultado = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
    resultado['km_por_litro'] = 1 / resultado['consumo_por_km']
    return resultado.sort_values('km_por_litro', ascending=False)

# Função principal
def main():
    st.title('⛽ Relatório de Abastecimento Interno x Externo')
    st.markdown("Envie as duas bases (.csv ou .xlsx) para comparar abastecimentos e calcular consumo médio.")

    uploaded_externo = st.file_uploader("📂 Base Externa (com coluna CONSUMO)", type=['csv', 'xlsx'])
    uploaded_interno = st.file_uploader("📂 Base Interna (com coluna Quantidade de litros)", type=['csv', 'xlsx'])

    if uploaded_externo and uploaded_interno:
        try:
            # Detecta formato
            if uploaded_externo.name.endswith('.csv'):
                base_ext = pd.read_csv(uploaded_externo)
            else:
                base_ext = pd.read_excel(uploaded_externo, engine='openpyxl')

            if uploaded_interno.name.endswith('.csv'):
                base_int = pd.read_csv(uploaded_interno)
            else:
                base_int = pd.read_excel(uploaded_interno, engine='openpyxl')

            # Tratar bases
            base_ext = calcular_externo(base_ext)
            base_int = calcular_interno(base_int)

            # Padronizar datas e placas
            base_ext['data'] = pd.to_datetime(base_ext['DATA'], dayfirst=True, errors='coerce')
            base_ext['placa'] = base_ext['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base_ext['km_atual'] = pd.to_numeric(base_ext['KM ATUAL'], errors='coerce')

            base_int['data'] = pd.to_datetime(base_int['Data'], dayfirst=True, errors='coerce')
            base_int['placa'] = base_int['Placa'].astype(str).str.replace(' ', '').str.upper()
            base_int['km_atual'] = pd.to_numeric(base_int['KM Atual'], errors='coerce')

            # Filtro por ano
            ano_disponiveis = sorted(set(base_ext['data'].dt.year.dropna().unique()) |
                                     set(base_int['data'].dt.year.dropna().unique()))
            ano = st.selectbox("📅 Filtrar por ano", ano_disponiveis, index=len(ano_disponiveis) - 1)

            base_ext_ano = base_ext[base_ext['data'].dt.year == ano]
            base_int_ano = base_int[base_int['data'].dt.year == ano]

            # Totais
            litros_ext = base_ext_ano['litros'].sum()
            valor_ext = base_ext_ano['valor'].sum()
            litros_int = base_int_ano['litros'].sum()
            total_litros = litros_ext + litros_int

            perc_ext = (litros_ext / total_litros) * 100 if total_litros > 0 else 0
            perc_int = (litros_int / total_litros) * 100 if total_litros > 0 else 0

            st.subheader(f'📊 Resumo do Abastecimento - Ano {ano}')
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🚛 Litros abastecidos externamente", f"{litros_ext:,.2f} L")
                st.metric("💰 Valor gasto com externo", f"R$ {valor_ext:,.2f}")
                st.metric("🔴 % abastecimento externo", f"{perc_ext:.1f}%")
            with col2:
                st.metric("🏭 Litros abastecidos internamente", f"{litros_int:,.2f} L")
                st.metric("🟢 % abastecimento interno", f"{perc_int:.1f}%")

            # Consumo médio
            st.subheader('📈 Consumo Médio por Veículo (Km por Litro)')
            df_combined = pd.concat([
                base_ext_ano[['placa', 'data', 'km_atual', 'litros']],
                base_int_ano[['placa', 'data', 'km_atual', 'litros']]
            ], ignore_index=True)

            consumo_medio = calcular_consumo_medio(df_combined)
            st.dataframe(consumo_medio[['placa', 'km_por_litro']].style.format({'km_por_litro': '{:.2f}'}))

        except Exception as e:
            st.error(f"Erro ao processar os dados: {e}")
    else:
        st.info("⬆️ Envie as duas bases para continuar.")

if __name__ == "__main__":
    main()
