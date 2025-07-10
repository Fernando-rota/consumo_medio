import streamlit as st
import pandas as pd
import plotly.express as px

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Helper Functions ---

def padroniza_colunas(df):
    """Standardizes DataFrame column names by stripping whitespace and converting to uppercase."""
    df.columns = df.columns.str.strip().str.upper()
    return df

def para_float(valor):
    """Converts a value to float, handling various string formats (comma as decimal, R$, spaces) and NaNs."""
    if pd.isna(valor):
        return None
    valor_str = str(valor).replace(",", ".").replace("R$", "").replace(" ", "").strip()
    try:
        return float(valor_str)
    except ValueError:
        return None

@st.cache_data # Cache data loading to improve performance on subsequent runs
def load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int):
    """
    Loads, preprocesses, and validates the uploaded CSV files.
    """
    df_comb, df_ext, df_int = None, None, None
    errors = []

    # --- Load DataFrames with error handling ---
    try:
        # ATENÇÃO AQUI: Mude sep=";" para sep=","
        df_comb = padroniza_colunas(pd.read_csv(uploaded_comb, sep=",", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo 'Combustível (Financeiro)': {e}")

    try:
        # ATENÇÃO AQUI: Mude sep=";" para sep=","
        df_ext = padroniza_colunas(pd.read_csv(uploaded_ext, sep=",", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo 'Abastecimento Externo': {e}")

    try:
        # ATENÇÃO AQUI: Mude sep=";" para sep=","
        df_int = padroniza_colunas(pd.read_csv(uploaded_int, sep=",", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo 'Abastecimento Interno': {e}")

    if errors:
        for error in errors:
            st.error(f"❌ {error}")
        return None, None, None, None, None

    # --- Validate Required Columns ---
    required_cols_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA"}
    required_cols_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA"}

    missing_ext = required_cols_ext - set(df_ext.columns)
    missing_int = required_cols_int - set(df_int.columns)

    if missing_ext:
        st.error(f"❌ O arquivo 'Abastecimento Externo' está faltando colunas essenciais: {', '.join(missing_ext)}. Por favor, verifique o cabeçalho do CSV.")
        return None, None, None, None, None
    if missing_int:
        st.error(f"❌ O arquivo 'Abastecimento Interno' está faltando colunas essenciais: {', '.join(missing_int)}. Por favor, verifique o cabeçalho do CSV.")
        return None, None, None, None, None

    # --- Data Type Conversions and Cleaning ---
    df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
    df_int["PLACA"] = df_int["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")

    df_ext["DATA"] = pd.to_datetime(df_ext["DATA"], dayfirst=True, errors="coerce")
    df_int["DATA"] = pd.to_datetime(df_int["DATA"], dayfirst=True, errors="coerce")

    df_ext["CONSUMO"] = df_ext["CONSUMO"].apply(para_float)
    df_ext["CUSTO TOTAL"] = df_ext["CUSTO TOTAL"].apply(para_float)
    df_ext["KM RODADOS"] = df_ext.get("KM RODADOS", pd.Series([None]*len(df_ext))).apply(para_float)
    df_ext["KM/LITRO"] = df_ext.get("KM/LITRO", pd.Series([None]*len(df_ext))).apply(para_float)

    df_int["QUANTIDADE DE LITROS"] = df_int["QUANTIDADE DE LITROS"].apply(para_float)

    if "PAGAMENTO" in df_comb.columns:
        df_comb["PAGAMENTO"] = pd.to_datetime(df_comb["PAGAMENTO"], dayfirst=True, errors="coerce")
    if "VENCIMENTO" in df_comb.columns:
        df_comb["VENCIMENTO"] = pd.to_datetime(df_comb["VENCIMENTO"], dayfirst=True, errors="coerce")

    placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO", "NAN", "", "NONE"})
    combustiveis = []
    if "DESCRIÇÃO DO ABASTECIMENTO" in df_ext.columns:
        combustiveis = df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique()
        combustiveis = sorted([c.strip() for c in combustiveis])

    return df_comb, df_ext, df_int, placas_validas, combustiveis

def calculate_kpis_and_combine_data(df_ext_filtered, df_int_filtered):
    """
    Calculates key performance indicators and combines external and internal fueling data.
    """
    consumo_ext = df_ext_filtered["CONSUMO"].sum()
    custo_ext = df_ext_filtered["CUSTO TOTAL"].sum()
    consumo_int = df_int_filtered["QUANTIDADE DE LITROS"].sum()

    avg_price_per_liter_ext = 0
    valid_ext_for_price = df_ext_filtered.dropna(subset=["CUSTO TOTAL", "CONSUMO"])
    if not valid_ext_for_price.empty and valid_ext_for_price["CONSUMO"].sum() > 0:
        avg_price_per_liter_ext = valid_ext_for_price["CUSTO TOTAL"].sum() / valid_ext_for_price["CONSUMO"].sum()

    custo_int_estimated = 0
    if avg_price_per_liter_ext > 0 and consumo_int > 0:
        custo_int_estimated = consumo_int * avg_price_per_liter_ext

    df_ext_processed = df_ext_filtered.copy()
    df_ext_processed["FONTE"] = "Externo"
    df_ext_processed["LITROS"] = df_ext_processed["CONSUMO"]
    df_ext_processed["CUSTO"] = df_ext_processed["CUSTO TOTAL"]

    df_int_processed = df_int_filtered.copy()
    df_int_processed["FONTE"] = "Interno"
    df_int_processed["LITROS"] = df_int_processed["QUANTIDADE DE LITROS"]
    df_int_processed["CUSTO"] = df_int_processed["LITROS"] * custo_int_estimated # Corrigido para usar a variável calculada

    common_cols = ["DATA", "PLACA", "LITROS", "CUSTO", "FONTE"]
    if "KM RODADOS" in df_ext_processed.columns:
        common_cols.append("KM RODADOS")
    if "KM/LITRO" in df_ext_processed.columns:
        common_cols.append("KM/LITRO")

    for col in common_cols:
        if col not in df_ext_processed.columns:
            df_ext_processed[col] = pd.Series([None] * len(df_ext_processed))
        if col not in df_int_processed.columns:
            df_int_processed[col] = pd.Series([None] * len(df_int_processed))

    df_all = pd.concat([
        df_ext_processed[common_cols],
        df_int_processed[common_cols]
    ], ignore_index=True)

    df_efficiency = df_ext_processed.dropna(subset=["KM RODADOS", "LITROS"]).copy()
    if not df_efficiency.empty:
        df_efficiency = df_efficiency[df_efficiency["LITROS"] > 0]
        if not df_efficiency.empty:
            df_efficiency["KM/LITRO CALC"] = df_efficiency["KM RODADOS"] / df_efficiency["LITROS"]
        else:
            df_efficiency["KM/LITRO CALC"] = None
    else:
        df_efficiency["KM/LITRO CALC"] = None

    return consumo_ext, custo_ext, consumo_int, custo_int_estimated, df_all, df_efficiency, avg_price_per_liter_ext

# --- Streamlit Sidebar: File Uploads ---
st.sidebar.header("📁 Enviar arquivos .csv")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

# --- Main Dashboard Logic ---
if uploaded_comb and uploaded_ext and uploaded_int:
    df_comb, df_ext, df_int, placas_validas, combustiveis = load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int)

    if df_comb is not None:
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Filtros")

        col1_filter, col2_filter = st.columns(2)
        with col1_filter:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2_filter:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível (Apenas Externo)", ["Todos"] + combustiveis)

        st.sidebar.subheader("📅 Filtrar por Período")

        all_dates_series = pd.Series(dtype='datetime64[ns]')
        if df_ext is not None and 'DATA' in df_ext.columns:
            all_dates_series = pd.concat([all_dates_series, df_ext['DATA'].dropna()])
        if df_int is not None and 'DATA' in df_int.columns:
            all_dates_series = pd.concat([all_dates_series, df_int['DATA'].dropna()])

        global_min_date = all_dates_series.min() if not all_dates_series.empty else None
        global_max_date = all_dates_series.max() if not all_dates_series.empty else None

        start_date_filter, end_date_filter = None, None

        if global_min_date and global_max_date:
            date_range_selection = st.sidebar.date_input(
                "Selecione o intervalo de datas",
                value=(global_min_date, global_max_date),
                min_value=global_min_date,
                max_value=global_max_date
            )
            if len(date_range_selection) == 2:
                start_date_filter, end_date_filter = date_range_selection
            elif len(date_range_selection) == 1:
                st.sidebar.info("Selecione um intervalo de duas datas para aplicar o filtro.")
                start_date_filter, end_date_filter = global_min_date, global_max_date
        else:
            st.sidebar.info("Não há dados de data válidos para o filtro de período.")
            start_date_filter, end_date_filter = None, None

        df_ext_filtered_by_date = df_ext.copy()
        df_int_filtered_by_date = df_int.copy()

        if start_date_filter and end_date_filter:
            df_ext_filtered_by_date = df_ext_filtered_by_date[
                (df_ext_filtered_by_date['DATA'].notna()) &
                (df_ext_filtered_by_date["DATA"] >= pd.Timestamp(start_date_filter)) &
                (df_ext_filtered_by_date["DATA"] <= pd.Timestamp(end_date_filter))
            ]
            df_int_filtered_by_date = df_int_filtered_by_date[
                (df_int_filtered_by_date['DATA'].notna()) &
                (df_int_filtered_by_date["DATA"] >= pd.Timestamp(start_date_filter)) &
                (df_int_filtered_by_date["DATA"] <= pd.Timestamp(end_date_filter))
            ]

        df_ext_final_filtered = df_ext_filtered_by_date[df_ext_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_ext_filtered_by_date
        df_int_final_filtered = df_int_filtered_by_date[df_int_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_int_filtered_by_date

        if tipo_comb != "Todos" and "DESCRIÇÃO DO ABASTECIMENTO" in df_ext_final_filtered.columns:
            df_ext_final_filtered = df_ext_final_filtered[df_ext_final_filtered["DESCRIÇÃO DO ABASTECIMENTO"] == tipo_comb]

        if df_ext_final_filtered.empty and df_int_final_filtered.empty:
            st.warning("Não há dados para os filtros selecionados. Por favor, ajuste as opções de filtro.")
        else:
            consumo_ext, custo_ext, consumo_int, custo_int_estimated, df_all, df_efficiency, avg_price_per_liter_ext = \
                calculate_kpis_and_combine_data(df_ext_final_filtered, df_int_final_filtered)

            abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

            with abas[0]:
                st.markdown("## 📊 Indicadores Resumidos")
                col1_metric, col2_metric, col3_metric, col4_metric = st.columns(4)

                col1_metric.metric("Total Externo (L)", f"{consumo_ext:,.1f}")
                col2_metric.metric("Total Interno (L)", f"{consumo_int:,.1f}")
                col3_metric.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
                col4_metric.metric("Custo Total Interno (Estimado)", f"R$ {custo_int_estimated:,.2f}")

                if avg_price_per_liter_ext > 0:
                    st.info(f"💡 O custo total interno é uma estimativa baseada no preço médio por litro do abastecimento externo (R$ {avg_price_per_liter_ext:,.2f}/L).")
                else:
                    st.warning("Não foi possível estimar o custo interno, pois não há dados de custo válidos para abastecimento externo.")

            with abas[1]:
                st.markdown("## 📈 Abastecimento por Placa")
                if not df_all.empty and 'LITROS' in df_all.columns:
                    graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                    fig_placa = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True,
                                       title="Volume de Combustível Abastecido por Placa")
                    st.plotly_chart(fig_placa, use_container_width=True)
                else:
                    st.info("Não há dados para exibir o gráfico de Abastecimento por Placa com os filtros selecionados.")

                st.markdown("---")
                st.markdown("## 📆 Tendência por Data")
                if not df_all.empty and 'DATA' in df_all.columns and 'FONTE' in df_all.columns:
                    graf_tempo = df_all.dropna(subset=['DATA']).groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
                    if not graf_tempo.empty:
                        fig_tempo = px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True,
                                            title="Volume de Abastecimento ao Longo do Tempo (Interno vs. Externo)")
                        st.plotly_chart(fig_tempo, use_container_width=True)
                    else:
                        st.info("Não há dados válidos com data para exibir a Tendência por Data.")
                else:
                    st.info("Não há dados para exibir o gráfico de Tendência por Data com os filtros selecionados.")

                st.markdown("---")
                st.markdown("## ⚙️ Eficiência (km/l) - Abastecimento Externo")
                if not df_efficiency.empty and "KM/LITRO CALC" in df_efficiency.columns and df_efficiency["KM/LITRO CALC"].sum() > 0:
                    df_eff_media = df_efficiency.groupby("PLACA")["KM/LITRO CALC"].mean().reset_index().sort_values("KM/LITRO CALC", ascending=False)
                    fig_eff = px.bar(df_eff_media, x="PLACA", y="KM/LITRO CALC", text_auto=".2f", color="PLACA",
                                     title="Média de KM por Litro (Abastecimento Externo)")
                    fig_eff.update_layout(yaxis_title="KM por Litro (média)")
                    st.plotly_chart(fig_eff, use_container_width=True)
                else:
                    st.info("Não há dados suficientes ou válidos para calcular a eficiência (km/l) para o abastecimento externo com os filtros selecionados. Certifique-se de que as colunas 'KM RODADOS' e 'CONSUMO' estejam preenchidas no arquivo de Abastecimento Externo.")

                st.markdown("---")
                st.markdown("## 🏅 Ranking de Veículos por Consumo Total")
                if not df_all.empty and 'LITROS' in df_all.columns:
                    ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                    st.dataframe(ranking, use_container_width=True, hide_index=True)
                else:
                    st.info("Não há dados para exibir o Ranking de Veículos com os filtros selecionados.")

                st.markdown("---")
                st.markdown("## ⚖️ Comparativo: Interno x Externo")
                if not df_all.empty and 'LITROS' in df_all.columns and 'CUSTO' in df_all.columns:
                    comparativo = df_all.groupby("FONTE").agg(
                        LITROS=("LITROS", "sum"),
                        CUSTO=("CUSTO", "sum")
                    ).reset_index()
                    col_pie1, col_pie2 = st.columns(2)
                    with col_pie1:
                        fig_vol = px.pie(comparativo, values="LITROS", names="FONTE", title="Volume Abastecido por Fonte")
                        st.plotly_chart(fig_vol, use_container_width=True)
                    with col_pie2:
                        fig_cost = px.pie(comparativo, values="CUSTO", names="FONTE", title="Custo Total por Fonte (Custo Interno Estimado)")
                        st.plotly_chart(fig_cost, use_container_width=True)
                else:
                    st.info("Não há dados para exibir o Comparativo: Interno x Externo com os filtros selecionados.")

            with abas[2]:
                st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
                if df_comb is not None and not df_comb.empty:
                    st.dataframe(df_comb, use_container_width=True, hide_index=True)
                else:
                    st.info("Não há dados na planilha financeira ou o arquivo não foi carregado corretamente.")

    else:
        st.error("Houve um problema ao carregar ou validar um dos arquivos. Por favor, verifique as mensagens de erro acima e tente novamente.")

else:
    st.warning("⬅️ Por favor, envie os 3 arquivos `.csv` na barra lateral esquerda para visualizar o dashboard completo.")
