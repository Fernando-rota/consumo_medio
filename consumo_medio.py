import streamlit as st
import pandas as pd

st.set_page_config(page_title='Relatório de Consumo Médio', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            try:
                import openpyxl  # tentativa de forçar erro mais cedo, se não estiver disponível
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

def padronizar_base1(df):
    cols_map = {
        'PLACA': 'placa',
        'DATA': 'data',
        'KM ATUAL': 'km_atual',
        'CONSUMO': 'litros'
    }
    df = df.rename(columns=cols_map)
    df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
    df['placa'] = df['placa'].astype(str).str.replace(' ', '').str.upper()
    df['km_atual'] = pd.to_numeric(df['km_atual'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    return df[['placa', 'data', 'km_atual', 'litros']]

def padronizar_base2(df):
    cols_map = {
        'Placa': 'placa',
        'Data': 'data',
        'KM Atual': 'km_atual',
        'Quantidade de litros': 'litros'
    }
    df = df.rename(columns=cols_map)
    df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
    df['placa'] = df['placa'].astype(str).str.replace(' ', '').str.upper()
    df['km_atual'] = pd.to_numeric(df['km_atual'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    return df[['placa', 'data', 'km_atual', 'litros']]

def calcular_consumo_medio(df):
    df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
    df['km_diff'] = df.groupby('placa')['km_atual'].diff()
    df['consumo_por_km'] = df['litros'] / df['km_diff']
    df_clean = df.dropna(subset=['km_diff', 'consumo_por_km'])
    df_clean = df_clean[df_clean['km_diff'] > 0]
    consumo_medio = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
    consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']
    return consumo_medio.sort_values('km_por_litro', ascending=False)

def main():
    st.title('📊 Relatório de Consumo Médio por Veículo')
    st.markdown("""
    Faça upload das duas bases para calcular o consumo médio por veículo (km por litro).

    - **Base 1**: Cupons de abastecimento (`.csv` recomendado)
    - **Base 2**: Controle de saída (`.csv` recomendado)

    ⚠️ Para evitar erros de leitura, prefira arquivos `.csv`. Se usar `.xlsx`, certifique-se de que `openpyxl` está instalado no ambiente.
    """)

    uploaded_base1 = st.file_uploader('📂 Base 1 (cupons de abastecimento)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('📂 Base 2 (controle de saída)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1')
        base2 = carregar_base(uploaded_base2, 'Base 2')

        if base1 is not None and base2 is not None:
            try:
                df1 = padronizar_base1(base1)
                df2 = padronizar_base2(base2)
                df = pd.concat([df1, df2], ignore_index=True)
                consumo_medio = calcular_consumo_medio(df)

                st.write('### 🔍 Visualização dos Dados Combinados')
                st.dataframe(df.head(10))

                st.write('### ✅ Consumo Médio por Veículo (Km por Litro)')
                st.dataframe(consumo_medio[['placa', 'km_por_litro']].style.format({'km_por_litro': '{:.2f}'}))

            except Exception as e:
                st.error(f'Erro no processamento dos dados: {e}')
        else:
            st.warning('⚠️ Erro ao carregar uma das bases. Verifique o tipo do arquivo e tente novamente.')
    else:
        st.info('⬆️ Por favor, envie as duas bases acima para gerar o relatório.')

if __name__ == '__main__':
    main()
