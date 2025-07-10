import streamlit as st
import pandas as pd
import plotly.express as px
import io # Importar io para lidar com arquivos em memória

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Helper Functions ---

def padroniza_colunas(df):
    """Standardizes DataFrame column names by stripping whitespace and converting to uppercase."""
    # Garante que as colunas sejam strings antes de aplicar str.strip().str.upper()
    df.columns = [str(col).strip().upper() for col in df.columns]
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

# Função para tentar ler CSVs com diferentes delimitadores
def try_read_csv(uploaded_file):
    """
    Tries to read a CSV file with common delimiters, using 'on_bad_lines="skip"'
    and the 'python' engine for better error handling.
    """
    # Rewind the file pointer to the beginning for multiple read attempts
    uploaded_file.seek(0)
    
    # Try comma
    try:
        df = pd.read_csv(uploaded_file, sep=",", encoding="utf-8", on_bad_lines='skip', engine='python')
        if not df.empty and len(df.columns) > 1: # Basic check if comma worked
            return df
    except Exception:
        pass # Ignore error and try next delimiter

    uploaded_file.seek(0) # Rewind for next attempt
    # Try semicolon
    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8", on_bad_lines='skip', engine='python')
        if not df.empty and len(df.columns) > 1: # Basic check if semicolon worked
            return df
    except Exception:
        pass # Ignore error and try next delimiter

    uploaded_file.seek(0) # Rewind for next attempt
    # Fallback: Try with no specified separator, letting pandas infer (less reliable but can work)
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8", on_bad_lines='skip', engine='python')
        if not df.empty and len(df.columns) > 1:
            return df
    except Exception:
        pass

    uploaded_file.seek(0) # Rewind for next attempt
    # Try with Latin-1 encoding as a last resort for CSVs
    try:
        df = pd.read_csv(uploaded_file, encoding="latin-1", on_bad_lines='skip', engine='python')
        if not df.empty and len(df.columns) > 1:
            return df
    except Exception:
        pass

    return None # Return None if no method worked


@st.cache_data # Cache data loading to improve performance on subsequent runs
def load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int):
    """
    Loads, preprocesses, and validates the uploaded CSV/XLSX files.

    Args:
        uploaded_comb: Uploaded file object for financial data.
        uploaded_ext: Uploaded file object for external fueling data.
        uploaded_int: Uploaded file object for internal fueling data.

    Returns:
        tuple: (df_comb, df_ext, df_int, placas_validas, combustiveis) or (None, None, None, None, None) if errors occur.
    """
    df_comb, df_ext, df_int = None, None, None
    errors = []

    # Helper to load either CSV or XLSX
    def load_file(uploaded_file_obj, file_type_name):
        df_loaded = None
        file_extension = uploaded_file_obj.name.split('.')[-1].lower()

        try:
            if file_extension == 'csv':
                # Pass the BytesIO object to try_read_csv
                df_loaded = try_read_csv(io.BytesIO(uploaded_file_obj.getvalue()))
                if df_loaded is None:
                    raise ValueError(f"Não foi possível carregar o arquivo CSV '{file_type_name}'. Verifique o formato e o delimitador.")
            elif file_extension == 'xlsx':
                df_loaded = pd.read_excel(uploaded_file_obj)
            else:
                raise ValueError(f"Formato de arquivo não suportado para '{file_type_name}'. Por favor, use .csv ou .xlsx.")

            return padroniza_colunas(df_loaded) # Standardize columns after loading
        except Exception as e:
            errors.append(f"Erro ao carregar arquivo '{file_type_name}': {e}")
            return None

    # Load each file
    df_comb = load_file(uploaded_comb, 'Combustível (Financeiro)')
    df_ext = load_file(uploaded_ext, 'Abastecimento Externo')
    df_int = load_file(uploaded_int, 'Abastecimento Interno')

    if errors: # Check for errors immediately after trying to load all files
        for error in errors:
            st.error(f"❌ {error}")
        return None, None, None, None, None

    # --- Validate Required Columns (UPDATED for 'DATA HORA' in internal sheet) ---
    required_cols_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA"}
    # Expect 'DATA HORA' in internal CSV/XLSX. Padroniza_colunas ensures it's 'DATA HORA' (uppercase)
    required_cols_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA HORA"} 

    missing_ext = required_cols_ext - set(df_ext.columns)
    missing_int = required_cols_int - set(df_int.columns)

    if missing_ext:
        st.error(f"❌ O arquivo 'Abastecimento Externo' está faltando colunas essenciais: {', '.join(missing_ext)}. Por favor, verifique o cabeçalho do arquivo.")
        return None, None, None, None, None
    if missing_int:
        st.error(f"❌ O arquivo 'Abastecimento Interno' está faltando colunas essenciais: {', '.join(missing_int)}. Por favor, verifique o cabeçalho do arquivo.")
        return None, None, None, None, None

    # --- Data Type Conversions and Cleaning ---
    df_ext["PLACA"] = df_ext["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
    df_int["PLACA"] = df_int["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")

    # Convert 'DATA' columns to datetime, coercing errors to NaT (Not a Time)
    df_ext["DATA"] = pd.to_datetime(df_ext["DATA"], dayfirst=True, errors="coerce")

    # Rename 'DATA HORA' to 'DATA' in df_int for consistency, then convert to datetime
    # The padroniza_colunas already made it 'DATA HORA' (uppercase)
    if 'DATA HORA' in df_int.columns:
        df_int.rename(columns={'DATA HORA': 'DATA'}, inplace=True)
    df_int["DATA"] = pd.to_datetime(df_int["DATA"], dayfirst=True, errors="coerce")

    # Apply para_float to numerical columns, including optional ones using .get()
    df_ext["CONSUMO"] = df_ext["CONSUMO"].apply(para_float)
    df_ext["CUSTO TOTAL"] = df_ext["CUSTO TOTAL"].apply(para_float)
    df_ext["KM RODADOS"] = df_ext.get("KM RODADOS", pd.Series([None]*len(df_ext), index=df_ext.index)).apply(para_float)
    df_ext["KM/LITRO"] = df_ext.get("KM/LITRO", pd.Series([None]*len(df_ext), index=df_ext.index)).apply(para_float)

    df_int["QUANTIDADE DE LITROS"] = df_int["QUANTIDADE DE LITROS"].apply(para_float)

    # Clean financial data dates
    if "PAGAMENTO" in df_comb.columns:
        df_comb["PAGAMENTO"] = pd.to_datetime(df_comb["PAGAMENTO"], dayfirst=True, errors="coerce")
    if "VENCIMENTO" in df_comb.columns:
        df_comb["VENCIMENTO"] = pd.to_datetime(df_comb["VENCIMENTO"], dayfirst=True, errors="coerce")

    # Determine unique valid plates and fuel types for filters
    placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO", "NAN", "", "NONE"})
    combustiveis = []
    if "DESCRIÇÃO DO ABASTECIMENTO" in df_ext.columns:
        combustiveis = df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique()
        combustiveis = sorted([c.strip() for c in combustiveis])

    return df_comb, df_ext, df_int, placas_validas, combustiveis

def calculate_kpis_and_combine_data(df_ext_filtered, df_int_filtered):
    """
    Calculates key performance indicators and combines external and internal fueling data.

    Args:
        df_ext_filtered (pd.DataFrame): Filtered external fueling data.
        df_int_filtered (pd.DataFrame): Filtered internal fueling data.

    Returns:
        tuple: (consumo_ext, custo_ext, consumo_int, custo_int_estimated, df_all, df_efficiency, avg_price_per_liter_ext)
    """
    # Calculate external consumption and cost
    consumo_ext = df_ext_filtered["CONSUMO"].sum()
    custo_ext = df_ext_filtered["CUSTO TOTAL"].sum()

    # Calculate internal consumption
    consumo_int = df_int_filtered["QUANTIDADE DE LITROS"].sum()

    # --- Internal Fueling Cost (Estimated) ---
    # Estimate internal cost based on the average price per liter from external fueling.
    # This assumes external prices are a reasonable proxy for internal fuel cost.
    avg_price_per_liter_ext = 0
    valid_ext_for_price = df_ext_filtered.dropna(subset=["CUSTO TOTAL", "CONSUMO"])
    # Ensure no division by zero and there's actual consumption data
    if not valid_ext_for_price.empty and valid_ext_for_price["CONSUMO"].sum() > 0:
        avg_price_per_liter_ext = valid_ext_for_price["CUSTO TOTAL"].sum() / valid_ext_for_price["CONSUMO"].sum()

    custo_int_estimated = 0
    if avg_price_per_liter_ext > 0 and consumo_int > 0:
        custo_int_estimated = consumo_int * avg_price_per_liter_ext

    # --- Prepare DataFrames for Concatenation ---
    df_ext_processed = df_ext_filtered.copy()
    df_ext_processed["FONTE"] = "Externo"
    df_ext_processed["LITROS"] = df_ext_processed["CONSUMO"]
    df_ext_processed["CUSTO"] = df_ext_processed["CUSTO TOTAL"]

    df_int_processed = df_int_filtered.copy()
    df_int_processed["FONTE"] = "Interno"
    df_int_processed["LITROS"] = df_int_processed["QUANTIDADE DE LITROS"]
    # Assign estimated cost for internal fueling based on calculated average price
    df_int_processed["CUSTO"] = df_int_processed["LITROS"] * avg_price_per_liter_ext

    # Define common columns to ensure consistent structure before concatenation
    # Add KM RODADOS and KM/LITRO if they exist in the external data
    common_cols = ["DATA", "PLACA", "LITROS", "CUSTO", "FONTE"]
    if "KM RODADOS" in df_ext_processed.columns:
        common_cols.append("KM RODADOS")
    if "KM/LITRO" in df_ext_processed.columns:
        common_cols.append("KM/LITRO")

    # Ensure all common columns are present in both DFs before concat, fill with None if not
    for col in common_cols:
        if col not in df_ext_processed.columns:
            df_ext_processed[col] = pd.Series([None] * len(df_ext_processed), index=df_ext_processed.index)
        if col not in df_int_processed.columns:
            df_int_processed[col] = pd.Series([None] * len(df_int_processed), index=df_int_processed.index)

    # Concatenate data for combined analysis
    df_all = pd.concat([
        df_ext_processed[common_cols],
        df_int_processed[common_cols]
    ], ignore_index=True)

    # Calculate KM/L for external fueling.
    df_efficiency = df_ext_processed.dropna(subset=["KM RODADOS", "LITROS"]).copy()
    if not df_efficiency.empty:
        # Avoid division by zero for KM/L calculation
        df_efficiency = df_efficiency[df_efficiency["LITROS"] > 0]
        if not df_efficiency.empty:
            df_efficiency["KM/LITRO CALC"] = df_efficiency["KM RODADOS"] / df_efficiency["LITROS"]
        else:
            df_efficiency["KM/LITRO CALC"] = None # No valid data after filtering zero liters
    else:
        df_efficiency["KM/LITRO CALC"] = None # Ensure column exists even if empty

    return consumo_ext, custo_ext, consumo_int, custo_int_estimated, df_all, df_efficiency, avg_price_per_liter_ext

# --- Streamlit Sidebar: File Uploads ---
st.sidebar.header("📁 Enviar arquivos (.csv ou .xlsx)")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type=["csv", "xlsx"])
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type=["csv", "xlsx"])
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type=["csv", "xlsx"])

# --- Main Dashboard Logic ---
if uploaded_comb and uploaded_ext and uploaded_int:
    # Attempt to load and preprocess data
    df_comb, df_ext, df_int, placas_validas, combustiveis = load_and_preprocess_data(uploaded_comb, uploaded_ext, uploaded_int)

    # Proceed only if all files were loaded and validated successfully (df_comb is not None)
    if df_comb is not None and df_ext is not None and df_int is not None: # Check all DFs are not None
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Filtros")

        # Placa and Fuel Type Filters
        col1_filter, col2_filter = st.columns(2)
        with col1_filter:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2_filter:
            # Note: Fuel type filter primarily applies to external fueling data as internal data often lacks this detail
            tipo_comb = st.selectbox("⛽ Tipo de Combustível (Apenas Externo)", ["Todos"] + combustiveis)

        # Date Range Filter (applies to both external and internal fueling data)
        st.sidebar.subheader("📅 Filtrar por Período")

        # Determine the overall min/max dates from the initially loaded (raw) dataframes
        # This ensures the date picker always shows the full range available in the dataset,
        # even if specific filters (like plate) result in an empty subset.
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
                value=(global_min_date, global_max_date), # Default to the full date range
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

        # --- Apply Filters in Order: Date -> Placa -> Combustível ---
        df_ext_filtered_by_date = df_ext.copy()
        df_int_filtered_by_date = df_int.copy()

        if start_date_filter and end_date_filter:
            # Filter by date, handling potential NaT values
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

        # Apply Placa filter
        df_ext_final_filtered = df_ext_filtered_by_date[df_ext_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_ext_filtered_by_date
        df_int_final_filtered = df_int_filtered_by_date[df_int_filtered_by_date["PLACA"] == placa_selecionada] if placa_selecionada != "Todas" else df_int_filtered_by_date

        # Apply Tipo de Combustível filter (only for external data)
        if tipo_comb != "Todos" and "DESCRIÇÃO DO ABASTECIMENTO" in df_ext_final_filtered.columns:
            df_ext_final_filtered = df_ext_final_filtered[df_ext_final_filtered["DESCRIÇÃO DO ABASTECIMENTO"] == tipo_comb]

        # Check if filtered data is empty before calculating KPIs and generating plots
        if df_ext_final_filtered.empty and df_int_final_filtered.empty:
            st.warning("Não há dados para os filtros selecionados. Por favor, ajuste as opções de filtro.")
        else:
            # Calculate KPIs and prepare combined DataFrame
            consumo_ext, custo_ext, consumo_int, custo_int_estimated, df_all, df_efficiency, avg_price_per_liter_ext = \
                calculate_kpis_and_combine_data(df_ext_final_filtered, df_int_final_filtered)

            # --- Dashboard Tabs ---
            abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

            with abas[0]: # Indicadores Tab
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


            with abas[1]: # Gráficos & Rankings Tab
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
                    # Drop rows where 'DATA' might be NaT after conversion/filtering for plotting
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

            with abas[2]: # Financeiro Tab
                st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
                if df_comb is not None and not df_comb.empty:
                    st.dataframe(df_comb, use_container_width=True, hide_index=True)
                else:
                    st.info("Não há dados na planilha financeira ou o arquivo não foi carregado corretamente.")

    else: # This block executes if load_and_preprocess_data returned None due to an error
        st.error("Houve um problema ao carregar ou validar um dos arquivos. Por favor, verifique as mensagens de erro acima e tente novamente.")

else: # This block executes if not all 3 files are uploaded
    st.warning("⬅️ Por favor, envie os 3 arquivos (`.csv` ou `.xlsx`) na barra lateral esquerda para visualizar o dashboard completo.")
