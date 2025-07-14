import streamlit as st
import pandas as pd
import unicodedata

# Funções auxiliares
def remove_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFKD', txt) if not unicodedata.combining(c))

def normaliza_colunas(df):
    df.columns = [remove_acentos(col).lower().strip().replace(' ', '_') for col in df.columns]
    return df

def normaliza_placa(placa):
    if pd.isna(placa):
        return ''
    return ''.join(c for c in placa.upper().strip() if c.isalnum())

def verificar_colunas_obrigatorias(df, obrigatorias, nome_base):
    faltando = [col for col in obrigatorias if col not in df.columns]
    if faltando:
        st.error(f"🛑 Colunas obrigatórias ausentes na base '{nome_base}': {faltando}")
        st.warning(f"Colunas encontradas: {df.columns.tolist()}")
        return False
    return True

# Função principal de carregamento
@st.cache_data
def carregar_planilhas(arquivo_combustivel, arquivo_externo, arquivo_interno):
    combustivel = pd.read_excel(arquivo_combustivel)
    externo = pd.read_excel(arquivo_externo)
    interno = pd.read_excel(arquivo_interno)

    # Normaliza colunas
    combustivel = normaliza_colunas(combustivel)
    externo = normaliza_colunas(externo)
    interno = normaliza_colunas(interno)

    # Verifica colunas obrigatórias
    ok1 = verificar_colunas_obrigatorias(combustivel, ['fornecedor', 'emissao'], 'Combustível')
    ok2 = verificar_colunas_obrigatorias(externo, ['data', 'placa', 'posto', 'km_atual', 'descricao_do_abastecimento', 'consumo', 'custo_total'], 'Externo')
    ok3 = verificar_colunas_obrigatorias(interno, ['data', 'tipo', 'placa', 'km_atual', 'quantidade_de_litros'], 'Interno')

    if not (ok1 and ok2 and ok3):
        return None, None, None

    # Normaliza placas
    externo['placa'] = externo['placa'].apply(normaliza_placa)
    interno['placa'] = interno['placa'].apply(normaliza_placa)

    # Converte datas
    combustivel['emissao'] = pd.to_datetime(combustivel['emissao'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')

    return combustivel, externo, interno

# App Streamlit
def main():
    st.title("📊 BI de Abastecimento - Diagnóstico de Planilhas")

    st.sidebar.header("🔼 Upload das planilhas")
    arquivo_combustivel = st.sidebar.file_uploader("Planilha Combustível", type=['xls', 'xlsx'])
    arquivo_externo = st.sidebar.file_uploader("Planilha Abastecimento Externo", type=['xls', 'xlsx'])
    arquivo_interno = st.sidebar.file_uploader("Planilha Abastecimento Interno", type=['xls', 'xlsx'])

    if arquivo_combustivel and arquivo_externo and arquivo_interno:
        combustivel, externo, interno = carregar_planilhas(arquivo_combustivel, arquivo_externo, arquivo_interno)

        if combustivel is not None:
            st.success("✅ Todas as planilhas foram carregadas corretamente.")
            st.subheader("🟢 Visualização rápida dos dados")
            st.markdown("### Planilha Combustível")
            st.dataframe(combustivel.head())

            st.markdown("### Planilha Abastecimento Externo")
            st.dataframe(externo.head())

            st.markdown("### Planilha Abastecimento Interno")
            st.dataframe(interno.head())
        else:
            st.warning("⚠️ Corrija as colunas das planilhas conforme informado acima para continuar.")
    else:
        st.info("🔁 Faça upload das **três planilhas** para iniciar.")

if __name__ == '__main__':
    main()
