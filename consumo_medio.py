import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# Upload dos arquivos
st.sidebar.header("📁 Enviar arquivos .csv")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

def padroniza_colunas(df):
    df.columns = df.columns.str.strip().str.upper()
    return df

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

    colunas_necessarias_ext = {"PLACA", "CONSUMO", "VALOR PAGO", "DATA", "DESCRIÇÃO DO ABASTECIMENTO"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO"}

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}")
    else:
        df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
        df_int["PLACA"] = df_int["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
        df_int["TIPO"] = df_int["TIPO"].str.upper().str.strip()

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
        custo_ext = df_ext_filt["VALOR PAGO"].apply(para_float).sum()
        consumo_int = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"]["QUANTIDADE DE LITROS"].apply(para_float).sum()

        # CALCULAR MÉDIA DE VALOR POR LITRO INTERNO (ENTRADAS)
        entradas = df_int[df_int["TIPO"] == "ENTRADA DE DIESEL"].copy()
        entradas["QUANTIDADE DE LITROS"] = entradas["QUANTIDADE DE LITROS"].apply(para_float)
        entradas = entradas.merge(df_comb, left_on="DATA", right_on="EMISSAO", how="left")

        if "VALOR PAGO" in df_comb.columns:
            entradas["VALOR PAGO"] = entradas["VALOR PAGO"].apply(para_float)
            valor_total_entrada = entradas["VALOR PAGO"].sum()
            litros_entrada = entradas["QUANTIDADE DE LITROS"].sum()
            preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada else 0
        else:
            preco_medio_litro = 0

        # CALCULAR CUSTO TOTAL DAS SAÍDAS INTERNAS
        saidas = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"].copy()
        saidas["QUANTIDADE DE LITROS"] = saidas["QUANTIDADE DE LITROS"].apply(para_float)
        saidas["CUSTO"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro
        custo_int = saidas["CUSTO"].sum()

        # Preparar DataFrame unificado para gráficos
        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
        df_ext_copy["FONTE"] = "Externo"
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(para_float)
        df_ext_copy["CUSTO"] = df_ext_copy["VALOR PAGO"].apply(para_float)
        df_ext_copy["KM RODADOS"] = df_ext_copy.get("KM RODADOS", None).apply(para_float) if "KM RODADOS" in df_ext_copy else None
        df_ext_copy["KM/LITRO"] = df_ext_copy.get("KM/LITRO", None).apply(para_float) if "KM/LITRO" in df_ext_copy else None

        saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
        saidas["FONTE"] = "Interno"
        saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"]
        saidas["KM RODADOS"] = None
        saidas["KM/LITRO"] = None

        df_all = pd.concat([
            df_ext_copy[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS", "KM/LITRO"]],
            saidas[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS", "KM/LITRO"]]
        ], ignore_index=True)

        # ABAS
        abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:
            st.markdown("## 📊 Indicadores Resumidos")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Total Interno", f"R$ {custo_int:,.2f}")

        with abas[1]:
            st.markdown("## 📈 Abastecimento por Placa")
            graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            fig1 = px.bar(graf_placa, x="PLACA", y="LITROS", text_auto=True, color="PLACA")
            st.plotly_chart(fig1, use_container_width=True)

            st.markdown("## 📆 Tendência por Data")
            graf_tempo = df_all.groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
            fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("## ⚙️ Eficiência (km/l) - Externo")
            df_eff = df_ext_copy.dropna(subset=["KM RODADOS", "LITROS"])
            if not df_eff.empty:
                df_eff["KM/LITRO CALC"] = df_eff["KM RODADOS"] / df_eff["LITROS"]
                df_eff_media = df_eff.groupby("PLACA")["KM/LITRO CALC"].mean().reset_index().sort_values("KM/LITRO CALC", ascending=False)
                fig_eff = px.bar(df_eff_media, x="PLACA", y="KM/LITRO CALC", text_auto=".2f", color="PLACA")
                fig_eff.update_layout(yaxis_title="KM por Litro (média)")
                st.plotly_chart(fig_eff, use_container_width=True)
            else:
                st.info("Sem dados suficientes para calcular eficiência.")

            st.markdown("## 🏅 Ranking por Consumo")
            ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            st.dataframe(ranking, use_container_width=True)

            st.markdown("## ⚖️ Comparativo Interno x Externo")
            comparativo = df_all.groupby("FONTE").agg(
                LITROS=("LITROS", "sum"),
                CUSTO=("CUSTO", "sum")
            ).reset_index()
            col1, col2 = st.columns(2)
            with col1:
                fig3 = px.pie(comparativo, values="LITROS", names="FONTE", title="Volume Abastecido")
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                fig4 = px.pie(comparativo, values="CUSTO", names="FONTE", title="Custo Total")
                st.plotly_chart(fig4, use_container_width=True)

        with abas[2]:
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            if "EMISSAO" in df_comb.columns:
                df_comb["EMISSAO"] = pd.to_datetime(df_comb["EMISSAO"], dayfirst=True, errors="coerce")
            st.dataframe(df_comb, use_container_width=True)

else:
    st.warning("⬅️ Envie os 3 arquivos `.csv` na barra lateral para visualizar o dashboard.")
