import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Helper Functions ---
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

# --- Data Loading and Preprocessing ---
@st.cache_data # Cache data to avoid reloading on every interaction
def load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int):
    df_comb = None
    df_ext = None
    df_int = None
    errors = []

    try:
        df_comb = padroniza_colunas(pd.read_csv(uploaded_comb, sep=";", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo de Combustível (Financeiro): {e}")

    try:
        df_ext = padroniza_colunas(pd.read_csv(uploaded_ext, sep=";", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo de Abastecimento Externo: {e}")

    try:
        df_int = padroniza_colunas(pd.read_csv(uploaded_int, sep=";", encoding="utf-8"))
    except Exception as e:
        errors.append(f"Erro ao carregar arquivo de Abastecimento Interno: {e}")

    if errors:
        for error in errors:
            st.error(f"❌ {error}")
        return None, None, None, None

    # Column validation
    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA"}
    # The image shows 'KM FINAL' which might be the actual odometer reading.
    # If 'KM RODADOS' is a calculated difference, it's fine. If not, needs re-calculation.
    # Assuming 'KM RODADOS' exists and is the actual distance for now.

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}. Por favor, verifique se as colunas estão corretas no CSV.")
        return None, None, None, None
    if faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}. Por favor, verifique se as colunas estão corretas no CSV.")
        return None, None, None, None

    # Data Type Conversions and Cleaning
    df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
    df_int["PLACA"] = df_int["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")

    df_ext["DATA"] = pd.to_datetime(df_ext["DATA"], dayfirst=True, errors="coerce")
    df_int["DATA"] = pd.to_datetime(df_int["DATA"], dayfirst=True, errors="coerce")

    # Apply para_float early for numerical columns that will be used in calculations
    df_ext["CONSUMO"] = df_ext["CONSUMO"].apply(para_float)
    df_ext["CUSTO TOTAL"] = df_ext["CUSTO TOTAL"].apply(para_float)
    df_ext["KM RODADOS"] = df_ext.get("KM RODADOS", pd.Series([None]*len(df_ext))).apply(para_float) # .get handles missing col
    df_ext["KM/LITRO"] = df_ext.get("KM/LITRO", pd.Series([None]*len(df_ext))).apply(para_float)

    df_int["QUANTIDADE DE LITROS"] = df_int["QUANTIDADE DE LITROS"].apply(para_float)

    # Clean financial data dates
    if "PAGAMENTO" in df_comb.columns:
        df_comb["PAGAMENTO"] = pd.to_datetime(df_comb["PAGAMENTO"], dayfirst=True, errors="coerce")
    if "VENCIMENTO" in df_comb.columns:
        df_comb["VENCIMENTO"] = pd.to_datetime(df_comb["VENCIMENTO"], dayfirst=True, errors="coerce")

    # Determine unique valid plates and fuels
    placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO", "NAN"})
    combustiveis = []
    if "DESCRIÇÃO DO ABASTECIMENTO" in df_ext.columns:
        combustiveis = df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique()
        combustiveis = sorted([c.strip() for c in combustiveis])

    return df_comb, df_ext, df_int, placas_validas, combustiveis

# --- KPI Calculation Function ---
def calculate_kpis(df_ext_filt, df_int_filt, df_comb_filt):
    # Calculate external consumption and cost
    consumo_ext = df_ext_filt["CONSUMO"].sum()
    custo_ext = df_ext_filt["CUSTO TOTAL"].sum()

    # Calculate internal consumption
    consumo_int = df_int_filt["QUANTIDADE DE LITROS"].sum()

    # --- Internal Fueling Cost (Improved Calculation) ---
    # Option 2: Approximate internal cost based on average external price
    # Get average price per liter from external fueling if available
    avg_price_per_liter_ext = 0
    valid_ext_for_price = df_ext_filt.dropna(subset=["CUSTO TOTAL", "CONSUMO"])
    if not valid_ext_for_price.empty and valid_ext_for_price["CONSUMO"].sum() > 0:
        avg_price_per_liter_ext = valid_ext_for_price["CUSTO TOTAL"].sum() / valid_ext_for_price["CONSUMO"].sum()

    custo_int = 0
    if avg_price_per_liter_ext > 0 and consumo_int > 0:
        custo_int = consumo_int * avg_price_per_liter_ext
    # Else, if no external data to base price on, custo_int remains 0 or can be None

    # Create combined dataframe for general analysis and charting
    df_ext_processed = df_ext_filt.copy()
    df_ext_processed["FONTE"] = "Externo"
    df_ext_processed["LITROS"] = df_ext_processed["CONSUMO"]
    df_ext_processed["CUSTO"] = df_ext_processed["CUSTO TOTAL"]

    df_int_processed = df_int_filt.copy()
    df_int_processed["FONTE"] = "Interno"
    df_int_processed["LITROS"] = df_int_processed["QUANTIDADE DE LITROS"]
    df_int_processed["CUSTO"] = df_int_processed["LITROS"] * avg_price_per_liter_ext # Use calculated internal cost

    # Select common columns for concatenation
    common_cols = ["DATA", "PLACA", "LITROS", "CUSTO", "FONTE"]
    if "KM RODADOS" in df_ext_processed.columns: # Add KM RODADOS for external data if available
        common_cols.append("KM RODADOS")
    if "KM/LITRO" in df_ext_processed.columns: # Add KM/LITRO for external data if available
        common_cols.append("KM/LITRO")

    # Ensure all columns are present in both DFs before concat, fill with None if not
    for col in common_cols:
        if col not in df_ext_processed.columns:
            df_ext_processed[col] = None
        if col not in df_int_processed.columns:
            df_int_processed[col] = None

    df_all = pd.concat([
        df_ext_processed[common_cols],
        df_int_processed[common_cols]
    ], ignore_index=True)

    # Calculate KM/L for external fueling (if 'KM RODADOS' is the actual distance driven)
    df_eff = df_ext_processed.dropna(subset=["KM RODADOS", "LITROS"]).copy()
    if not df_eff.empty:
        df_eff["KM/LITRO CALC"] = df_eff["KM RODADOS"] / df_eff["LITROS"]
    else:
        df_eff["KM/LITRO CALC"] = None # Ensure column exists even if empty

    return consumo_ext, custo_ext, consumo_int, custo_int, df_all, df_eff, avg_price_per_liter_ext

# --- Streamlit UI ---
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

if uploaded_comb and uploaded_ext and uploaded_int:
    df_comb, df_ext, df_int, placas_validas, combustiveis = load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int)

    if df_comb is not None: # Check if data loading was successful
        col1, col2 = st.columns(2)
        with col1:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível (Apenas Externo)", ["Todos"] + combustiveis)

        # Date Filter - Added for more control
        st.sidebar.subheader("📅 Filtrar por Período")
        min_date = df_all['DATA'].min() if not df_all.empty else None
        max_date = df_all['DATA'].max() if not df_all.empty else None

        if min_date and max_date:
            date_range = st.sidebar.date_input(
                "Selecione o intervalo de datas",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
                # Apply date filter to original dataframes before specific filters
                df_ext_filtered_by_date = df_ext[(df_ext["DATA"] >= pd.Timestamp(start_date)) & (df_ext["DATA"] <= pd.Timestamp(end_date))]
                df_int_filtered_by_date = df_int[(df_int["DATA"] >= pd.Timestamp(start_date)) & (df_int["DATA"] <= pd.Timestamp(end_date))]
            else: # Handle case where only one date is selected (e.g., initial state)
                st.sidebar.info("Selecione um intervalo de duas datas para aplicar o filtro.")
                df_ext_filtered_by_date = df_ext
                df_int_filtered_by_date = df_int
        else:
            df_ext_filtered_by_date = df_ext
            df_int_filtered_by_date = df_int
            st.sidebar.info("Dados de data insuficientes para o filtro de período.")


        # Apply Placa and Tipo Combustível filters
        df_ext_filt = df_ext_filtered_by_date[df_ext_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_ext_filtered_by_date
        df_int_filt = df_int_filtered_by_date[df_int_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_int_filtered_by_date

        if tipo_comb != "Todos" and "DESCRIÇÃO DO ABASTECIMENTO" in df_ext_filt.columns:
            df_ext_filt = df_ext_filt[df_ext_filt["DESCRIÇÃO DO ABASTECIMENTO"] == tipo_comb]
            # Note: Internal fueling typically doesn't have a fuel type column in this setup.

        # Check if filtered data is empty
        if df_ext_filt.empty and df_int_filt.empty:
            st.warning("Não há dados para os filtros selecionados. Tente ajustar os filtros.")
        else:
            consumo_ext, custo_ext, consumo_int, custo_int, df_all, df_eff, avg_price_per_liter_ext = calculate_kpis(df_ext_filt, df_int_filt, df_comb)

            abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

            with abas[0]:
                st.markdown("## 📊 Indicadores Resumidos")
                col1, col2, col3, col4 = st.columns(4)

                col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
                col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
                col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
                col4.metric("Custo Total Interno (Estimado)", f"R$ {custo_int:,.2f}")
                st.info(f"O custo total interno é uma estimativa baseada no preço médio por litro do abastecimento externo (R$ {avg_price_per_liter_ext:,.2f}/L).")


            with abas[1]:
                st.markdown("## 📈 Abastecimento por Placa")
                if not df_all.empty:
                    graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                    fig = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True, title="Volume Abastecido por Placa")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há dados para o gráfico de Abastecimento por Placa.")


                st.markdown("## 📆 Tendência por Data")
                if not df_all.empty:
                    graf_tempo = df_all.groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
                    fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True, title="Volume de Abastecimento ao Longo do Tempo")
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Não há dados para o gráfico de Tendência por Data.")


                st.markdown("## ⚙️ Eficiência (km/l) - Externo")
                if not df_eff.empty and "KM/LITRO CALC" in df_eff.columns and df_eff["KM/LITRO CALC"].sum() > 0:
                    df_eff_media = df_eff.groupby("PLACA")["KM/LITRO CALC"].mean().reset_index().sort_values("KM/LITRO CALC", ascending=False)
                    fig_eff = px.bar(df_eff_media, x="PLACA", y="KM/LITRO CALC", text_auto=".2f", color="PLACA", title="Média de KM por Litro (Abastecimento Externo)")
                    fig_eff.update_layout(yaxis_title="KM por Litro (média)")
                    st.plotly_chart(fig_eff, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para calcular eficiência (km/l) para o abastecimento externo ou 'KM RODADOS' está ausente/vazio. Verifique a coluna 'KM RODADOS' no arquivo de Abastecimento Externo. Se ela for a leitura do odômetro, a lógica de cálculo precisa ser ajustada para diferenças entre abastecimentos.")

                st.markdown("## 🏅 Ranking de Veículos por Consumo Total")
                if not df_all.empty:
                    ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                    st.dataframe(ranking, use_container_width=True, hide_index=True)
                else:
                    st.info("Não há dados para o Ranking de Veículos.")

                st.markdown("## ⚖️ Comparativo: Interno x Externo")
                if not df_all.empty:
                    comparativo = df_all.groupby("FONTE").agg(
                        LITROS=("LITROS", "sum"),
                        CUSTO=("CUSTO", "sum")
                    ).reset_index()
                    col1, col2 = st.columns(2)
                    with col1:
                        fig3 = px.pie(comparativo, values="LITROS", names="FONTE", title="Volume Abastecido por Fonte")
                        st.plotly_chart(fig3, use_container_width=True)
                    with col2:
                        fig4 = px.pie(comparativo, values="CUSTO", names="FONTE", title="Custo Total por Fonte (Custo Interno Estimado)")
                        st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.info("Não há dados para o Comparativo: Interno x Externo.")

            with abas[2]:
                st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
                if not df_comb.empty:
                    st.dataframe(df_comb, use_container_width=True, hide_index=True)
                else:
                    st.info("Não há dados na planilha financeira.")

else:
    st.warning("⬅️ Envie os 3 arquivos `.csv` na barra lateral para visualizar o dashboard.")
