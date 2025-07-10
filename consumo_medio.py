import streamlit as st
import pandas as pd

# Função corrigida para cálculo de km rodado interno
def calcula_km_rodado_interno(df):
    df = df.copy()
    if df.empty:
        st.warning("DataFrame vazio no cálculo de km rodado interno.")
        return df
    if "KM ATUAL" not in df.columns:
        st.error("Coluna 'KM ATUAL' não encontrada no DataFrame.")
        df["KM RODADOS"] = None
        return df
    if "PLACA" not in df.columns or "DATA" not in df.columns:
        st.error("Colunas 'PLACA' e/ou 'DATA' não encontradas no DataFrame.")
        df["KM RODADOS"] = None
        return df

    df["KM ATUAL"] = pd.to_numeric(df["KM ATUAL"], errors="coerce")

    res = []
    grouped = df.sort_values("DATA").groupby("PLACA")
    if grouped.ngroups == 0:
        st.warning("Nenhum grupo encontrado para 'PLACA' ao calcular km rodado interno.")
        df["KM RODADOS"] = None
        return df

    for placa, grupo in grouped:
        grupo = grupo.reset_index(drop=True)
        grupo["KM RODADOS"] = grupo["KM ATUAL"].diff().fillna(0)
        grupo.loc[grupo["KM RODADOS"] < 0, "KM RODADOS"] = 0
        res.append(grupo)

    if res:
        resultado = pd.concat(res)
        st.write(f"Cálculo de km rodado interno para {len(resultado)} registros concluído.")
        return resultado
    else:
        st.warning("Nenhum resultado após agrupamento no cálculo de km rodado interno.")
        df["KM RODADOS"] = None
        return df


# Upload dos arquivos
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

if uploaded_comb and uploaded_ext and uploaded_int:
    # Leitura básica para teste (adicione seus tratamentos de colunas aqui)
    df_int = pd.read_csv(uploaded_int, sep=";", encoding="utf-8")
    
    # Filtra saídas diesel para exemplo
    saidas = df_int[df_int["TIPO"].str.upper().str.strip() == "SAÍDA DE DIESEL"].copy()
    
    # Converte datas
    saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
    
    # Verificações e cálculo
    if saidas.empty:
        st.warning("O DataFrame 'saidas' está vazio. Não será possível calcular km rodado interno.")
    else:
        if ("PLACA" not in saidas.columns) or ("DATA" not in saidas.columns):
            st.error("Colunas 'PLACA' e/ou 'DATA' não estão presentes no DataFrame 'saidas'.")
            saidas["KM RODADOS"] = None
        else:
            saidas = calcula_km_rodado_interno(saidas)
            st.dataframe(saidas.head())
else:
    st.info("📥 Por favor, envie os três arquivos CSV na barra lateral para iniciar a análise.")
