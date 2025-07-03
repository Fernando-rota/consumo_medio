import streamlit as st
import pandas as pd

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='centered')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None
        return df
    except Exception as e:
        st.error(f'Erro ao carregar {tipo_base}: {e}')
        return None

def tratar_valor(valor_str):
    try:
        return float(str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

def tratar_litros(valor_str):
    try:
        return float(str(valor_str).replace(' ', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

def main():
    st.title('Relatório de Abastecimento Interno x Externo com Consumo Médio')

    uploaded_base1 = st.file_uploader('Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')

        if base1 is not None and base2 is not None:
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')

            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()

            base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')
            base1['valor_total'] = base1['CUSTO TOTAL'].apply(tratar_valor)

            base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            st.sidebar.header("🔎 Filtros")
            start_date = st.sidebar.date_input('Data inicial', value=pd.to_datetime('2025-01-01'))
            end_date = st.sidebar.date_input('Data final', value=pd.to_datetime('2025-12-31'))

            if start_date > end_date:
                st.error("Data inicial deve ser menor ou igual à data final.")
                return

            base1_filt = base1[(base1['data'] >= start_date) & (base1['data'] <= end_date)]
            base2_filt = base2[(base2['data'] >= start_date) & (base2['data'] <= end_date)]

            litros_ext = base1_filt['litros'].sum()
            litros_int = base2_filt['litros'].sum()
            total_litros = litros_ext + litros_int

            perc_ext = (litros_ext / total_litros) * 100 if total_litros > 0 else 0
            perc_int = (litros_int / total_litros) * 100 if total_litros > 0 else 0
            valor_ext = base1_filt['valor_total'].sum()

            st.subheader(f'📌 Resumo Geral ({start_date} a {end_date})')
            c1, c2 = st.columns(2)
            with c1:
                st.metric('Litros Externos', f'{litros_ext:,.2f} L')
                st.metric('Valor Gasto Externo', f'R$ {valor_ext:,.2f}')
                st.metric('% Externo', f'{perc_ext:.1f}%')
            with c2:
                st.metric('Litros Internos', f'{litros_int:,.2f} L')
                st.metric('% Interno', f'{perc_int:.1f}%')

            st.divider()

            # Top 10 veículos que mais abasteceram externamente
            top_veiculos = base1_filt.groupby('placa')['litros'].sum().reset_index().sort_values(by='litros', ascending=False).head(10)
            st.subheader('🚚 Top 10 veículos com maior abastecimento externo')
            st.dataframe(top_veiculos.style.format({'litros': '{:,.2f}'}))

            # Consumo médio
            df_comb = pd.concat([
                base1_filt[['placa', 'data', 'km_atual', 'litros']],
                base2_filt[['placa', 'data', 'km_atual', 'litros']]
            ], ignore_index=True)

            df_comb = df_comb.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
            df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
            df_comb['consumo_por_km'] = df_comb['litros'] / df_comb['km_diff']

            df_clean = df_comb.dropna(subset=['km_diff', 'consumo_por_km'])
            df_clean = df_clean[df_clean['km_diff'] > 0]

            consumo_medio = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
            consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']

            st.subheader('📊 Consumo Médio por Veículo (Km/L)')
            st.dataframe(consumo_medio[['placa', 'km_por_litro']].sort_values('km_por_litro', ascending=False).style.format({'km_por_litro': '{:.2f}'}))

            # Gráfico com st.bar_chart()
            st.subheader('Gráfico de Consumo Médio (Km/L)')
            top_grafico = consumo_medio[['placa', 'km_por_litro']].sort_values('km_por_litro', ascending=False).set_index('placa')
            st.bar_chart(top_grafico)

        else:
            st.warning('Não foi possível processar uma das bases. Verifique os dados.')

    else:
        st.info('Envie as duas bases para visualizar o relatório.')

if __name__ == '__main__':
    main()
