import streamlit as st
import pandas as pd

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='centered')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            try:
                import openpyxl
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            except ImportError:
                st.warning(f"Arquivo {tipo_base} está em Excel (.xlsx), mas o pacote `openpyxl` não está disponível. Converta para CSV.")
                return None
        else:
            st.warning(f"Formato de arquivo não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None

        st.success(f'{tipo_base} carregada com sucesso! Linhas: {len(df)}')
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

def tratar_litros(litros_str):
    try:
        litros = str(litros_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(litros)
    except:
        return None

def calcular_externo(df):
    # Tratamento da coluna CONSUMO (litros)
    if 'CONSUMO' in df.columns:
        litros = df['CONSUMO'].apply(tratar_litros)
    else:
        litros = pd.Series([0] * len(df))

    # Tratamento coluna valor preferencial
    if 'C/ DESC' in df.columns:
        valor = df['C/ DESC'].apply(tratar_valor)
    elif 'CUSTO TOTAL' in df.columns:
        valor = df['CUSTO TOTAL'].apply(tratar_valor)
    else:
        valor = pd.Series([0] * len(df))

    df['litros'] = litros
    df['valor'] = valor
    return df

def calcular_interno(df):
    df = df.rename(columns=lambda x: x.strip())
    if 'Quantidade de litros' in df.columns:
        df['litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    else:
        df['litros'] = 0
    return df

def calcular_consumo_medio(df_combined):
    df_combined = df_combined.dropna(subset=['placa', 'data', 'km_atual', 'litros'])
    df_combined = df_combined.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
    df_combined['km_diff'] = df_combined.groupby('placa')['km_atual'].diff()
    df_combined['consumo_por_km'] = df_combined['litros'] / df_combined['km_diff']
    df_clean = df_combined[(df_combined['km_diff'] > 0) & (df_combined['consumo_por_km'].notna())]
    resultado = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
    resultado['km_por_litro'] = 1 / resultado['consumo_por_km']
    return resultado.sort_values('km_por_litro', ascending=False)

def main():
    st.title('⛽ Relatório de Abastecimento Interno x Externo')

    uploaded_base1 = st.file_uploader('📂 Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('📂 Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')

        if base1 is not None and base2 is not None:
            # Tratar bases
            base1 = calcular_externo(base1)
            base2 = calcular_interno(base2)

            # Padronizar colunas para filtro e consumo médio
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')

            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            # Filtro intervalo de datas
            data_min = min(base1['data'].min(), base2['data'].min())
            data_max = max(base1['data'].max(), base2['data'].max())

            start_date = st.date_input('Data inicial', value=data_min)
            end_date = st.date_input('Data final', value=data_max)

            if start_date > end_date:
                st.error("Data inicial deve ser menor ou igual à data final.")
                return

            base1_filtrada = base1[(base1['data'] >= pd.to_datetime(start_date)) & (base1['data'] <= pd.to_datetime(end_date))]
            base2_filtrada = base2[(base2['data'] >= pd.to_datetime(start_date)) & (base2['data'] <= pd.to_datetime(end_date))]

            # Totais
            litros_ext = base1_filtrada['litros'].sum()
            valor_ext = base1_filtrada['valor'].sum()
            litros_int = base2_filtrada['litros'].sum()
            total_geral = litros_ext + litros_int

            perc_ext = (litros_ext / total_geral) * 100 if total_geral > 0 else 0
            perc_int = (litros_int / total_geral) * 100 if total_geral > 0 else 0

            st.subheader(f'🔍 Resumo do Abastecimento (de {start_date} a {end_date})')
            col1, col2 = st.columns(2)

            with col1:
                st.metric('🚛 Litros abastecidos externamente', f'{litros_ext:,.2f} L')
                st.metric('💰 Valor gasto externo', f'R$ {valor_ext:,.2f}')
                st.metric('🔴 % abastecimento externo', f'{perc_ext:.1f}%')

            with col2:
                st.metric('🏭 Litros abastecidos internamente', f'{litros_int:,.2f} L')
                st.metric('🟢 % abastecimento interno', f'{perc_int:.1f}%')

            # Consumo médio por veículo
            st.subheader('📈 Consumo Médio por Veículo (Km por Litro)')

            df_combined = pd.concat([
                base1_filtrada[['placa', 'data', 'km_atual', 'litros']],
                base2_filtrada[['placa', 'data', 'km_atual', 'litros']]
            ], ignore_index=True)

            consumo_medio = calcular_consumo_medio(df_combined)
            st.dataframe(consumo_medio[['placa', 'km_por_litro']].style.format({'km_por_litro': '{:.2f}'}))

        else:
            st.warning('❌ Não foi possível processar uma das bases. Verifique os dados.')

    else:
        st.info('⬆️ Envie as duas bases para calcular o comparativo.')

if __name__ == '__main__':
    main()
