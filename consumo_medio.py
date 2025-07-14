import streamlit as st
import pandas as pd
import unicodedata

# Função para normalizar texto (colunas e placas)
def remove_acentos(txt):
    return ''.join(c for c in unicodedata.normalize('NFKD', txt) if not unicodedata.combining(c))

def normaliza_colunas(df):
    df.columns = [remove_acentos(col).lower().strip().replace(' ', '_') for col in df.columns]
    return df

def normaliza_placa(placa):
    if pd.isna(placa):
        return ''
    placa = placa.upper().strip()
    placa = ''.join(c for c in placa if c.isalnum())  # remove espaços e caracteres especiais
    return placa

@st.cache_data
def carregar_planilhas(arquivo_combustivel, arquivo_externo, arquivo_interno):
    # Leitura
    combustivel = pd.read_excel(arquivo_combustivel)
    externo = pd.read_excel(arquivo_externo)
    interno = pd.read_excel(arquivo_interno)

    # Normaliza colunas
    combustivel = normaliza_colunas(combustivel)
    externo = normaliza_colunas(externo)
    interno = normaliza_colunas(interno)

    # Normaliza placas
    externo['placa'] = externo['placa'].apply(normaliza_placa)
    interno['placa'] = interno['placa'].apply(normaliza_placa)

    # Converte datas
    combustivel['emissao'] = pd.to_datetime(combustivel['emissao'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')

    return combustivel, externo, interno

def main():
    st.title("BI de Abastecimento - Streamlit")

    st.sidebar.header("Upload das planilhas")
    arquivo_combustivel = st.sidebar.file_uploader("Planilha Combustível", type=['xls', 'xlsx'])
    arquivo_externo = st.sidebar.file_uploader("Planilha Abastecimento Externo", type=['xls', 'xlsx'])
    arquivo_interno = st.sidebar.file_uploader("Planilha Abastecimento Interno", type=['xls', 'xlsx'])

    if arquivo_combustivel and arquivo_externo and arquivo_interno:
        combustivel, externo, interno = carregar_planilhas(arquivo_combustivel, arquivo_externo, arquivo_interno)

        st.subheader("Dados Carregados")

        st.markdown("**Planilha Combustível**")
        st.dataframe(combustivel.head())

        st.markdown("**Planilha Abastecimento Externo**")
        st.dataframe(externo.head())

        st.markdown("**Planilha Abastecimento Interno**")
        st.dataframe(interno.head())

        # Exemplos de indicadores básicos
        st.subheader("Indicadores Básicos")

        # Total litros abastecidos externo
        total_litros_externo = externo['consumo'].sum()
        st.metric("Total Litros Abastecidos (Externo)", f"{total_litros_externo:,.2f}")

        # Total litros abastecidos interno (só entradas)
        litros_entrada_interno = interno.loc[interno['tipo'].str.lower() == 'entrada de diesel', 'quantidade_de_litros'].sum()
        st.metric("Total Litros Abastecidos (Interno - entrada)", f"{litros_entrada_interno:,.2f}")

        # Total custo abastecimento externo
        total_custo_externo = externo['custo_total'].sum()
        st.metric("Total Custo Abastecimento Externo (R$)", f"R$ {total_custo_externo:,.2f}")

        # Filtros e gráficos simples
        st.subheader("Análise por Veículo")

        lista_placas = sorted(externo['placa'].dropna().unique())
        placa_selecionada = st.selectbox("Selecione a placa", options=lista_placas)

        # Filtra abastecimento externo e interno pela placa selecionada
        externo_placa = externo[externo['placa'] == placa_selecionada]
        interno_placa = interno[interno['placa'] == placa_selecionada]

        st.markdown(f"### Abastecimento Externo - {placa_selecionada}")
        st.dataframe(externo_placa)

        st.markdown(f"### Abastecimento Interno - {placa_selecionada}")
        st.dataframe(interno_placa)

        # Consumo médio externo por veículo
        km_inicial = externo_placa['km_atual'].min()
        km_final = externo_placa['km_atual'].max()
        litros_totais = externo_placa['consumo'].sum()
        km_rodados = km_final - km_inicial if pd.notna(km_final) and pd.notna(km_inicial) else None
        consumo_medio = (km_rodados / litros_totais) if litros_totais > 0 and km_rodados and km_rodados > 0 else None

        if consumo_medio:
            st.metric("Consumo Médio (km/l) - Externo", f"{consumo_medio:.2f}")
        else:
            st.info("Dados insuficientes para calcular consumo médio.")

    else:
        st.info("Faça upload das 3 planilhas para começar.")

if __name__ == '__main__':
    main()
