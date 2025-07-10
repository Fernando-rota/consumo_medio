import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# Upload dos arquivos
st.sidebar.header("📁 Enviar arquivos .csv")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

# Padronizar colunas
def padroniza_colunas(df):
    df.columns = df.columns.str.strip().str.upper()
    return df

# Renomear colunas comuns
def renomear_colunas(df, tipo):
    renomeios_comuns = {
        "DATA": ["DATA", "Data", " data"],
        "PLACA": ["PLACA", "Placa", " placa"],
        "TIPO": ["TIPO", "Tipo"],
        "QUANTIDADE DE LITROS": ["QUANTIDADE DE LITROS", "quantidade de litros", "Qtd Litros"],
        "CONSUMO": ["CONSUMO", "Consumo"],
        "CUSTO TOTAL": ["CUSTO TOTAL", "VALOR PAGO", "valor total"],
        "DESCRIÇÃO DO ABASTECIMENTO": ["DESCRIÇÃO DO ABASTECIMENTO", "TIPO DE COMBUSTIVEL", "COMBUSTÍVEL"]
    }

    mapeamento = {}
    for alvo, variações in renomeios_comuns.items():
        for v in variações:
            if v.upper() in df.columns:
                mapeamento[v.upper()] = alvo
                break

    df.rename(columns=mapeamento, inplace=True)

    if tipo == "int" and "TIPO" in df.columns:
        df["TIPO"] = df["TIPO"].str.upper().str.strip()
    if "PLACA" in df.columns:
        df["PLACA"] = df["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
    return df

# Converter strings para float
def para_float(valor):
    if pd.isna(valor):
        return None
    valor_str = str(valor).replace(",", ".").replace("R$", "").replace(" ", "").strip()
    try:
        return float(valor_str)
    except:
        return None

if uploaded_comb and uploaded_ext and uploaded_int:
    df_comb = padroniza_colunas(pd.read_csv(uploaded_comb, sep=";", encoding="utf-8"))
    df_ext = padroniza_colunas(pd.read_csv(uploaded_ext, sep=";", encoding="utf-8"))
    df_int = padroniza_colunas(pd.read_csv(uploaded_int, sep=";", encoding="utf-8"))

    df_ext = renomear_colunas(df_ext, "ext")
    df_int = renomear_colunas(df_int, "int")
    df_comb = renomear_colunas(df_comb, "comb")

    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA", "DESCRIÇÃO DO ABASTECIMENTO"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO"}

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}")
    else:
        placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO"})
        combustiveis = sorted(df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique())

        col1, col2 = st.columns(2)
        with col1:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + combustiveis)

        def aplicar_filtros(df, placa_col, tipo_combustivel_col=None):
            if placa_selecionada != "Todas":
                df = df[df[placa_col] == placa_selecionada]
            if tipo_comb != "Todos" and tipo_combustivel_col and tipo_combustivel_col in df.columns:
                df = df[df[tipo_combustivel_col] == tipo_comb]
            return df

        df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRIÇÃO DO ABASTECIMENTO")
        df_int_filt = aplicar_filtros(df_int, "PLACA")

        consumo_ext = df_ext_filt["CONSUMO"].apply(para_float).sum()
        custo_ext = df_ext_filt["CUSTO TOTAL"].apply(para_float).sum()
        consumo_int = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"]["QUANTIDADE DE LITROS"].apply(para_float).sum()

        # Cálculo do valor médio do litro interno
        entradas = df_int[df_int["TIPO"] == "ENTRADA DE DIESEL"].copy()
        entradas["QUANTIDADE DE LITROS"] = entradas["QUANTIDADE DE LITROS"].apply(para_float)
        entradas = entradas.merge(df_comb, left_on="DATA", right_on="EMISSAO", how="left")
        entradas["CUSTO TOTAL"] = entradas["CUSTO TOTAL"].apply(para_float)
        valor_total_entrada = entradas["CUSTO TOTAL"].sum()
        litros_entrada = entradas["QUANTIDADE DE LITROS"].sum()
        preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada else 0

        # Custo das saídas
        saidas = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"].copy()
        saidas["QUANTIDADE DE LITROS"] = saidas["QUANTIDADE DE LITROS"].apply(para_float)
        saidas["CUSTO"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro
        custo_int = saidas["CUSTO"].sum()

        # Preparar DataFrame consolidado
        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
        df_ext_copy["FONTE"] = "Externo"
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(para_float)
        df_ext_copy["CUSTO"] = df_ext_copy["CUSTO TOTAL"].apply(para_float)

        saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
        saidas["FONTE"] = "Interno"
        saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"]
        saidas["KM RODADOS"] = None
        saidas["KM/LITRO"] = None

        df_all = pd.concat([
            df_ext_copy[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE"]],
            saidas[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE"]]
        ], ignore_index=True)

        # Filtro por período
        st.sidebar.markdown("### 🗓️ Filtro por Data")
        min_data = df_all["DATA"].min()
        max_data = df_all["DATA"].max()
        data_inicio = st.sidebar.date_input("Data Inicial", min_data)
        data_fim = st.sidebar.date_input("Data Final", max_data)
        df_all = df_all[(df_all["DATA"] >= pd.to_datetime(data_inicio)) & (df_all["DATA"] <= pd.to_datetime(data_fim))]

        # Abas
        abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:
            st.markdown("## 📊 Indicadores Resumidos")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Total Interno", f"R$ {custo_int:,.2f}")
            st.metric("💰 Valor Médio Litro Interno", f"R$ {preco_medio_litro:.2f}")

            with st.expander("📤 Exportar Dados Consolidados"):
                buffer = BytesIO()
                df_all.to_excel(buffer, index=False, engine='openpyxl')
                st.download_button(
                    label="📥 Baixar tabela como Excel",
                    data=buffer.getvalue(),
                    file_name="abastecimento_consolidado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        with abas[1]:
            st.markdown("## 📈 Abastecimento por Placa")
            graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            st.plotly_chart(px.bar(graf_placa, x="PLACA", y="LITROS", text_auto=True, color="PLACA"), use_container_width=True)

            st.markdown("## 📆 Tendência por Data")
            graf_tempo = df_all.groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
            st.plotly_chart(px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True), use_container_width=True)

            st.markdown("## 🏅 Ranking por Consumo")
            ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            st.dataframe(ranking, use_container_width=True)

            st.markdown("## ⚖️ Comparativo Interno x Externo")
            comparativo = df_all.groupby("FONTE").agg(LITROS=("LITROS", "sum"), CUSTO=("CUSTO", "sum")).reset_index()
            col1, col2 = st.columns(2)
            col1.plotly_chart(px.pie(comparativo, values="LITROS", names="FONTE", title="Volume Abastecido"), use_container_width=True)
            col2.plotly_chart(px.pie(comparativo, values="CUSTO", names="FONTE", title="Custo Total"), use_container_width=True)

        with abas[2]:
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            if "EMISSAO" in df_comb.columns:
                df_comb["EMISSAO"] = pd.to_datetime(df_comb["EMISSAO"], dayfirst=True, errors="coerce")
            st.dataframe(df_comb, use_container_width=True)

else:
    st.warning("⬅️ Envie os 3 arquivos `.csv` na barra lateral para visualizar o dashboard.")
