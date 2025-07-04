import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='wide')

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
        return 0.0

def tratar_litros(valor_str):
    try:
        val = str(valor_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return 0.0

def main():
    st.title('Relatório de Abastecimento Interno x Externo com Consumo Médio')

    uploaded_base1 = st.file_uploader('Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_combustivel = st.file_uploader('Base 3 – Valor Combustível Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2 and uploaded_combustivel:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')
        base_combustivel = carregar_base(uploaded_combustivel, 'Base 3 (Combustível Interno)')

        if base1 is not None and base2 is not None and base_combustivel is not None:
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')

            # Verifica a coluna de data da base de combustível
            coluna_data_combustivel = None
            for col in base_combustivel.columns:
                if 'data' in col.lower():
                    coluna_data_combustivel = col
                    break

            if coluna_data_combustivel:
                base_combustivel['data'] = pd.to_datetime(base_combustivel[coluna_data_combustivel], dayfirst=True, errors='coerce')
            else:
                st.error("Não foi possível encontrar uma coluna de data na base de combustível.")
                return

            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()

            base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')

            base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                start_date = pd.to_datetime(st.date_input('Data inicial', value=pd.to_datetime('2025-01-01')))
            with col2:
                end_date = pd.to_datetime(st.date_input('Data final', value=pd.to_datetime('2025-12-31')))
            with col3:
                descricao_abastecimento = []
                if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns:
                    descricao_abastecimento = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique().tolist()

                filtro_descricao = None
                if descricao_abastecimento:
                    filtro_descricao = st.selectbox(
                        "Tipo de Combustível (Externo)",
                        ["Todos"] + sorted(descricao_abastecimento),
                        key="combustivel"
                    )
                    if filtro_descricao and filtro_descricao != "Todos":
                        base1 = base1[base1['DESCRIÇÃO DO ABASTECIMENTO'] == filtro_descricao]

            if start_date > end_date:
                st.error("Data inicial deve ser menor ou igual à data final.")
                return

            base1 = base1[(base1['data'] >= start_date) & (base1['data'] <= end_date)]
            base2 = base2[(base2['data'] >= start_date) & (base2['data'] <= end_date)]
            base_combustivel = base_combustivel[(base_combustivel['data'] >= start_date) & (base_combustivel['data'] <= end_date)]

            # Resto da lógica (KPIs, gráficos, consumo médio etc.)...

        else:
            st.warning('Não foi possível processar uma das bases. Verifique os dados.')

    else:
        st.info('Envie as três bases (.csv ou .xlsx) para gerar o relatório.')

if __name__ == '__main__':
    main()
