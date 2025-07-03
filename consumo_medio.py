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

def calcular_externo(df):
    # Coluna de litros
    litros = pd.to_numeric(df.get('CONSUMO', None), errors='coerce')

    # Coluna de valor preferencial
    if 'C/ DESC' in df.columns:
        valor = df['C/ DESC'].apply(tratar_valor)
    elif 'CUSTO TOTAL' in df.columns:
        valor = df['CUSTO TOTAL'].apply(tratar_valor)
    else:
        valor = pd.Series([0]*len(df))

    total_litros = litros.sum() if litros is not None else 0
    total_valor = valor.sum() if valor is not None else 0
    return total_litros, total_valor

def calcular_interno(df):
    if 'Quantidade de litros' in df.columns:
        litros = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
        return litros.sum()
    return 0

def main():
    st.title('⛽ Relatório de Abastecimento Interno x Externo')

    uploaded_base1 = st.file_uploader('📂 Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('📂 Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')

        if base1 is not None and base2 is not None:
            litros_ext, valor_ext = calcular_externo(base1)
            litros_int = calcular_interno(base2)

            total_geral = litros_ext + litros_int
            perc_int = (litros_int / total_geral) * 100 if total_geral > 0 else 0
            perc_ext = (litros_ext / total_geral) * 100 if total_geral > 0 else 0

            st.subheader('🔍 Resumo do Abastecimento')

            col1, col2 = st.columns(2)

            with col1:
                st.metric('Litros abastecidos **externamente**', f'{litros_ext:,.2f} L')
                st.metric('Valor gasto externo', f'R$ {valor_ext:,.2f}')
                st.metric('% externo', f'{perc_ext:.1f}%')

            with col2:
                st.metric('Litros abastecidos **internamente**', f'{litros_int:,.2f} L')
                st.metric('% interno', f'{perc_int:.1f}%')
        else:
            st.warning('❌ Não foi possível processar uma das bases. Verifique os dados.')

    else:
        st.info('⬆️ Envie as duas bases para calcular o comparativo.')

if __name__ == '__main__':
    main()
