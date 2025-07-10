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

    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA"}

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}")
    else:
        df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
        df_int["PLACA"] = df_int["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")

        placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO"})

        if "DESCRIÇÃO DO ABASTECIMENTO" in df_ext.columns:
            combustiveis = df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique()
            combustiveis = sorted([c.strip() for c in combustiveis])
        else:
            combustiveis = []

        col1, col2 = st.columns(2)
        with col1:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + combustiveis)

        def aplicar_filtros(df, placa_col, tipo_combustivel_col=None):
            if placa_selecionada != "Todas":
                df = df[df[placa_col] == placa_selecionada]
            if tipo_comb != "Todos" and tipo_combustivel_col is not None and tipo_combustivel_col in df.columns:
                df = df[df[tipo_combustivel_col] == tipo_comb]
            return df

        df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRIÇÃO DO ABASTECIMENTO")
        df_int_filt = aplicar_filtros(df_int, "PLACA")

        consumo_ext = df_ext_filt["CONSUMO"].apply(para_float).sum()
        custo_ext = df_ext_filt["CUSTO TOTAL"].apply(para_float).sum()
        consumo_int = df_int_filt["QUANTIDADE DE LITROS"].apply(para_float).sum()

        # Se tiver custo no abastecimento interno, somar também aqui (se não, será zero)
        # Vou colocar como zero, pois seu dataset interno não tem coluna custo
        custo_int = 0.0

        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["FONTE"] = "Externo"
        df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(para_float)
        df_ext_copy["CUSTO"] = df_ext_copy["CUSTO TOTAL"].apply(para_float)
        if "KM RODADOS" in df_ext_copy.columns:
            df_ext_copy["KM RODADOS"] = df_ext_copy["KM RODADOS"].apply(para_float)
        else:
            df_ext_copy["KM RODADOS"] = None
        if "KM/LITRO" in df_ext_copy.columns:
            df_ext_copy["KM/LITRO"] = df_ext_copy["KM/LITRO"].apply(para_float)
        else:
            df_ext_copy["KM/LITRO"] = None

        df_int_copy = df_int_filt.copy()
        df_int_copy["FONTE"] = "Interno"
        df_int_copy["DATA"] = pd.to_datetime(df_int_copy["DATA"], dayfirst=True, errors="coerce")
        df_int_copy["LITROS"] = df_int_copy["QUANTIDADE DE LITROS"].apply(para_float)
        df_int_copy["CUSTO"] = custo_int  # zero aqui
        df_int_copy["KM RODADOS"] = None
        df_int_copy["KM/LITRO"] = None

        df_all = pd.concat([
            df_ext_copy[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS", "KM/LITRO"]],
            df_int_copy[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS", "KM/LITRO"]]
        ], ignore_index=True)

        # Criar abas
        abas = st.tabs(["📊 Indicadores", "📄 Tabela Consolidada", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:  # Indicadores
            st.markdown("## 📊 Indicadores Resumidos")
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Total Interno", f"R$ {custo_int:,.2f}")

        with abas[1]:  # Tabela
            st.markdown("## 📄 Tabela Consolidada")
            st.dataframe(df_all.sort_values("DATA", ascending=False), use_container_width=True)

        with abas[2]:  # Gráficos & Rankings
            st.markdown("## 📈 Abastecimento por Placa")
            graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            fig = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("## 📆 Tendência por Data")
            graf_tempo = df_all.groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
            fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("## ⚙️ Eficiência (km/l) - Externo")
            df_eff = df_ext_copy.dropna(subset=["KM RODADOS", "LITROS"]).copy()
            if not df_eff.empty:
                df_eff["KM/LITRO CALC"] = df_eff["KM RODADOS"] / df_eff["LITROS"]
                df_eff_media = df_eff.groupby("PLACA")["KM/LITRO CALC"].mean().reset_index().sort_values("KM/LITRO CALC", ascending=False)
                fig_eff = px.bar(df_eff_media, x="PLACA", y="KM/LITRO CALC", text_auto=".2f", color="PLACA")
                fig_eff.update_layout(yaxis_title="KM por Litro (média)")
                st.plotly_chart(fig_eff, use_container_width=True)
            else:
                st.info("Não há dados suficientes para calcular eficiência (km/l)")

            st.markdown("## 🏅 Ranking de Veículos por Consumo Total")
            ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            st.dataframe(ranking, use_container_width=True)

            st.markdown("## ⚖️ Comparativo: Interno x Externo")
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

        with abas[3]:  # Financeiro
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            if "PAGAMENTO" in df_comb.columns:
                df_comb["PAGAMENTO"] = pd.to_datetime(df_comb["PAGAMENTO"], dayfirst=True, errors="coerce")
            st.dataframe(df_comb, use_container_width=True)

else:
    st.warning("⬅️ Envie os 3 arquivos `.csv` na barra lateral para visualizar o dashboard.")
