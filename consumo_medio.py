import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Funções Auxiliares ---

def padroniza_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove espaços em branco do início/fim dos nomes das colunas de um DataFrame.
    Args:
        df (pd.DataFrame): O DataFrame cujas colunas serão padronizadas.
    Returns:
        pd.DataFrame: O DataFrame com as colunas padronizadas.
    """
    df.columns = df.columns.str.strip()
    return df

def renomear_colunas(df: pd.DataFrame, file_type: str) -> pd.DataFrame:
    """
    Renomeia colunas comuns para um padrão unificado, facilitando a manipulação posterior.
    Args:
        df (pd.DataFrame): DataFrame a ser renomeado.
        file_type (str): Tipo de arquivo ('comb', 'ext', 'int') para renomeios específicos.
    Returns:
        pd.DataFrame: DataFrame com colunas renomeadas.
    """
    # Dicionário de mapeamento de nomes de colunas comuns e suas variações
    renomeios_comuns = {
        "DATA": ["DATA", "Data", " data"],
        "PLACA": ["PLACA", "Placa", " placa"],
        "TIPO": ["TIPO", "Tipo"],
        "QUANTIDADE DE LITROS": ["QUANTIDADE DE LITROS", "quantidade de litros", "Qtd Litros", "LITROS"],
        "CONSUMO": ["CONSUMO", "Consumo"],
        "CUSTO TOTAL": ["CUSTO TOTAL", "VALOR PAGO", "valor pago", "valor total"],
        "DESCRICAO DO ABASTECIMENTO": ["DESCRICAO DO ABASTECIMENTO", "TIPO DE COMBUSTIVEL", "COMBUSTIVEL"],
        "KM ATUAL": ["KM ATUAL", "Km Atual", "KM_ATUAL"],
        "KM RODADOS": ["KM RODADOS", "Km Rodados", "KM_RODADOS"],
        "EMISSAO": ["EMISSAO", "Emissao", "Emissão", "EMISSÃO", "emissao"],
        "POSTO": ["POSTO", "Posto"],
        "PAGAMENTO": ["PAGAMENTO", "Pagamento"]
    }
    mapeamento = {}
    cols_upper = [c.upper() for c in df.columns] # Converte nomes das colunas para maiúsculas para comparação

    for alvo, variacoes in renomeios_comuns.items():
        for v in variacoes:
            if v.upper() in cols_upper:
                real_col = df.columns[cols_upper.index(v.upper())]
                mapeamento[real_col] = alvo
                break # Encontrou uma variação, passa para a próxima coluna alvo
    df.rename(columns=mapeamento, inplace=True)

    # Padronizações específicas de dados após o renomeio das colunas
    if "TIPO" in df.columns and file_type == "int":
        df["TIPO"] = df["TIPO"].astype(str).str.upper().str.strip()
    if "PLACA" in df.columns:
        df["PLACA"] = df["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
    return df

def clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    Limpa e converte uma série (coluna) para o tipo numérico, tratando vírgulas, pontos e símbolos de moeda.
    Args:
        series (pd.Series): A série a ser limpa e convertida.
    Returns:
        pd.Series: A série convertida para tipo numérico.
    """
    if series.dtype == 'object': # Se a série for de strings
        # Remove "R$", espaços em branco, pontos (separador de milhar) e substitui vírgula por ponto (separador decimal)
        cleaned_series = series.astype(str).str.replace("R$", "", regex=False).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.strip()
        return pd.to_numeric(cleaned_series, errors="coerce") # Converte para numérico, valores inválidos viram NaN
    return pd.to_numeric(series, errors="coerce") # Se já não for string, tenta converter diretamente

def load_and_preprocess_dataframe(uploaded_file, file_type: str):
    """
    Carrega um arquivo CSV, padroniza as colunas, renomeia e converte os tipos de dados.
    Args:
        uploaded_file: Objeto de arquivo enviado pelo Streamlit.
        file_type (str): Tipo de arquivo ('comb', 'ext', 'int') para renomeios e conversões específicas.
    Returns:
        tuple: (pd.DataFrame, str) - DataFrame processado e mensagem de erro (None se sucesso).
    """
    if uploaded_file is None:
        return None, f"Arquivo não enviado."

    try:
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")
        if df.empty:
            return None, f"O arquivo '{uploaded_file.name}' está vazio."

        df = padroniza_colunas(df)
        df = renomear_colunas(df, file_type)

        # Mapeamento de colunas de data e numéricas para cada tipo de arquivo
        date_cols_map = {
            "comb": ["EMISSAO", "PAGAMENTO"],
            "ext": ["DATA"],
            "int": ["DATA"]
        }
        numeric_cols_map = {
            "comb": ["CUSTO TOTAL"],
            "ext": ["CONSUMO", "CUSTO TOTAL", "KM ATUAL", "KM RODADOS"],
            "int": ["QUANTIDADE DE LITROS", "KM ATUAL"]
        }

        # Conversão de colunas de data
        for col in date_cols_map.get(file_type, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
                if df[col].isnull().any():
                    st.warning(f"Valores inválidos encontrados na coluna de data '{col}' do arquivo '{uploaded_file.name}'. Linhas com datas inválidas podem ser afetadas.")

        # Conversão de colunas numéricas
        for col in numeric_cols_map.get(file_type, []):
            if col in df.columns:
                df[col] = clean_numeric_column(df[col])
                if df[col].isnull().any():
                    st.warning(f"Valores não numéricos encontrados na coluna '{col}' do arquivo '{uploaded_file.name}'. Eles foram convertidos para NaN.")

        return df, None
    except pd.errors.EmptyDataError:
        return None, f"O arquivo '{uploaded_file.name}' está vazio ou não contém dados."
    except Exception as e:
        return None, f"Erro ao ler o arquivo '{uploaded_file.name}': {e}. Verifique o formato e o separador."

def calcula_km_rodado_interno(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o KM rodado interno com base nos dados de quilometragem por placa e data.
    Args:
        df (pd.DataFrame): DataFrame contendo as colunas 'PLACA', 'DATA' e 'KM ATUAL'.
    Returns:
        pd.DataFrame: O DataFrame original com uma nova coluna 'KM RODADOS'.
    """
    if df.empty:
        st.warning("DataFrame de entrada vazio no cálculo de KM rodado interno. Retornando DataFrame vazio.")
        return pd.DataFrame(columns=df.columns.tolist() + ["KM RODADOS"])

    # Verifica se as colunas obrigatórias estão presentes
    required_cols = ["PLACA", "DATA", "KM ATUAL"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Colunas obrigatórias não encontradas para cálculo de KM rodado interno: {', '.join(missing_cols)}. Verifique o arquivo de entrada.")
        df["KM RODADOS"] = None
        return df

    df_copy = df.copy() # Trabalha em uma cópia para evitar SettingWithCopyWarning

    # Garante que 'KM ATUAL' seja numérico e 'DATA' seja datetime
    df_copy["KM ATUAL"] = pd.to_numeric(df_copy["KM ATUAL"], errors="coerce")
    df_copy["DATA"] = pd.to_datetime(df_copy["DATA"], dayfirst=True, errors="coerce")

    # Remove linhas com valores inválidos em colunas chave para o cálculo
    df_copy.dropna(subset=["KM ATUAL", "DATA", "PLACA"], inplace=True)
    if df_copy.empty:
        st.warning("Após a limpeza de valores inválidos em 'KM ATUAL', 'DATA' ou 'PLACA', o DataFrame ficou vazio. Não é possível calcular KM rodado.")
        df["KM RODADOS"] = None
        return df

    result_df_list = []
    # Agrupa por PLACA e ordena por DATA para calcular a diferença de KM corretamente
    for placa, grupo in df_copy.sort_values(by="DATA").groupby("PLACA"):
        grupo = grupo.copy() # Evita SettingWithCopyWarning ao modificar o grupo
        grupo["KM RODADOS"] = grupo["KM ATUAL"].diff().fillna(0) # Calcula a diferença entre KMs
        grupo.loc[grupo["KM RODADOS"] < 0, "KM RODADOS"] = 0 # Garante que KM_RODADOS não seja negativo
        result_df_list.append(grupo)

    if result_df_list:
        final_df = pd.concat(result_df_list)
        st.success(f"Cálculo de KM rodado interno para {len(final_df)} registros concluído com sucesso.")
        return final_df
    else:
        st.warning("Nenhum registro processado para cálculo de KM rodado após agrupamento por PLACA.")
        df["KM RODADOS"] = None
        return df

def classifica_eficiencia(km_litro: float, lim_ef: float, lim_norm: float) -> str:
    """
    Classifica a eficiência de um veículo com base no KM/Litro.
    Args:
        km_litro (float): Quilômetros por litro.
        lim_ef (float): Limite inferior para ser considerado "Eficiente".
        lim_norm (float): Limite inferior para ser considerado "Normal".
    Returns:
        str: Classificação da eficiência ("Eficiente", "Normal", "Ineficiente").
    """
    if km_litro >= lim_ef:
        return "Eficiente"
    elif km_litro >= lim_norm:
        return "Normal"
    else:
        return "Ineficiente"

def calcula_eficiencia(df: pd.DataFrame, posto: str, lim_ef: float, lim_norm: float) -> pd.DataFrame:
    """
    Calcula a eficiência (KM/Litro) por veículo e classifica.
    Args:
        df (pd.DataFrame): DataFrame com as colunas 'KM RODADOS' e 'LITROS'.
        posto (str): Nome do posto (e.g., "Interno", "Externo").
        lim_ef (float): Limite para classificação "Eficiente".
        lim_norm (float): Limite para classificação "Normal".
    Returns:
        pd.DataFrame: DataFrame com 'PLACA', 'KM/LITRO', 'CLASSIFICACAO', 'POSTO'.
    """
    df_filtered = df.dropna(subset=["KM RODADOS", "LITROS"]).copy()
    if df_filtered.empty:
        st.info(f"Nenhum dado válido para calcular eficiência para o posto '{posto}'.")
        return pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICACAO", "POSTO"])

    # Garante que LITROS e KM RODADOS são numéricos antes de somar
    df_filtered["LITROS"] = pd.to_numeric(df_filtered["LITROS"], errors="coerce")
    df_filtered["KM RODADOS"] = pd.to_numeric(df_filtered["KM RODADOS"], errors="coerce")
    df_filtered.dropna(subset=["KM RODADOS", "LITROS"], inplace=True) # Remove NaNs após a conversão

    if df_filtered.empty:
        st.info(f"Nenhum dado válido após conversão numérica para calcular eficiência para o posto '{posto}'.")
        return pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICACAO", "POSTO"])

    # Agrupa por PLACA e calcula KM/LITRO
    df_grouped = df_filtered.groupby("PLACA").apply(
        lambda x: (x["KM RODADOS"].sum() / x["LITROS"].sum()) if x["LITROS"].sum() > 0 else 0
    ).reset_index(name="KM/LITRO")

    df_grouped["CLASSIFICACAO"] = df_grouped["KM/LITRO"].apply(lambda x: classifica_eficiencia(x, lim_ef, lim_norm))
    df_grouped["POSTO"] = posto
    return df_grouped

# --- Inicialização do Session State ---
# O session_state é usado para persistir dados entre as interações do usuário,
# evitando que os arquivos sejam recarregados e processados a cada mudança de filtro.
if 'df_comb' not in st.session_state:
    st.session_state.df_comb = None
if 'df_ext' not in st.session_state:
    st.session_state.df_ext = None
if 'df_int' not in st.session_state:
    st.session_state.df_int = None
if 'processed_data_ready' not in st.session_state:
    st.session_state.processed_data_ready = False

# --- Upload de Arquivos na Barra Lateral ---
st.sidebar.header("Upload de Arquivos")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv", key="comb_file")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv", key="ext_file")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv", key="int_file")

st.sidebar.markdown("### ⚙️ Configuração Classificação de Eficiência (km/l)")
limite_eficiente = st.sidebar.slider("Limite para 'Eficiente' (km/l)", 1.0, 10.0, 3.0, 0.1)
limite_normal = st.sidebar.slider("Limite para 'Normal' (km/l)", 0.5, limite_eficiente, 2.0, 0.1)

# Botão para processar os arquivos após o upload
if st.sidebar.button("Processar Arquivos"):
    # Carrega e pré-processa cada arquivo, armazenando no session_state
    st.session_state.df_comb, err_comb = load_and_preprocess_dataframe(uploaded_comb, "comb")
    if err_comb: st.sidebar.error(f"Erro Combustível: {err_comb}")
    else: st.sidebar.success("Combustível: Carregado e processado com sucesso.")

    st.session_state.df_ext, err_ext = load_and_preprocess_dataframe(uploaded_ext, "ext")
    if err_ext: st.sidebar.error(f"Erro Abastecimento Externo: {err_ext}")
    else: st.sidebar.success("Abastecimento Externo: Carregado e processado com sucesso.")

    st.session_state.df_int, err_int = load_and_preprocess_dataframe(uploaded_int, "int")
    if err_int: st.sidebar.error(f"Erro Abastecimento Interno: {err_int}")
    else: st.sidebar.success("Abastecimento Interno: Carregado e processado com sucesso.")

    # Define a flag processed_data_ready se todos os arquivos essenciais foram carregados
    if (st.session_state.df_comb is not None and
        st.session_state.df_ext is not None and
        st.session_state.df_int is not None):
        st.session_state.processed_data_ready = True
    else:
        st.session_state.processed_data_ready = False
        st.error("Por favor, corrija os erros de upload para continuar com a análise.")

# --- Lógica Principal do Dashboard ---
# Esta seção só é executada se os dados foram processados com sucesso
if st.session_state.processed_data_ready:
    df_comb = st.session_state.df_comb
    df_ext = st.session_state.df_ext
    df_int = st.session_state.df_int

    # Verificação de colunas obrigatórias após o pré-processamento
    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA", "DESCRICAO DO ABASTECIMENTO", "POSTO", "KM RODADOS"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO", "KM ATUAL"}
    colunas_necessarias_comb = {"EMISSAO", "CUSTO TOTAL"} # PAGAMENTO é opcional para algumas análises

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)
    faltando_comb = colunas_necessarias_comb - set(df_comb.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas essenciais: {', '.join(faltando_ext)}. Por favor, verifique o arquivo e reenvie.")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas essenciais: {', '.join(faltando_int)}. Por favor, verifique o arquivo e reenvie.")
    else:
        if faltando_comb:
            st.warning(f"⚠️ Combustível (Financeiro) está faltando colunas: {', '.join(faltando_comb)}. Algumas análises financeiras podem ser limitadas.")

        # Preparar dados para filtro de Placa
        placas_validas_ext = df_ext["PLACA"].dropna().unique()
        placas_validas_int = df_int["PLACA"].dropna().unique()
        # Remove placas inválidas (e.g., '-', 'CORREÇÃO', vazias)
        placas_validas = sorted(set(placas_validas_ext).union(placas_validas_int) - {"-", "CORREÇÃO", ""})

        # Preparar dados para filtro de Tipo de Combustível
        combustiveis = sorted(df_ext["DESCRICAO DO ABASTECIMENTO"].dropna().unique())

        # Filtros na interface principal
        col1, col2 = st.columns(2)
        with col1:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + combustiveis)

        def aplicar_filtros(df: pd.DataFrame, placa_col: str, tipo_comb_col: str = None) -> pd.DataFrame:
            """Aplica filtros de placa e tipo de combustível ao DataFrame."""
            df_filtered = df.copy()
            if placa_selecionada != "Todas":
                df_filtered = df_filtered[df_filtered[placa_col] == placa_selecionada]
            if tipo_comb != "Todos" and tipo_comb_col and tipo_comb_col in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[tipo_comb_col] == tipo_comb]
            return df_filtered

        # Aplica os filtros aos DataFrames de abastecimento
        df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRICAO DO ABASTECIMENTO")
        df_int_filt = aplicar_filtros(df_int, "PLACA")

        # --- Cálculos de Consumo e Custo ---
        consumo_ext = df_ext_filt["CONSUMO"].sum() if "CONSUMO" in df_ext_filt.columns else 0
        custo_ext = df_ext_filt["CUSTO TOTAL"].sum() if "CUSTO TOTAL" in df_ext_filt.columns else 0

        # Entradas de diesel interno (para cálculo de preço médio)
        entradas = df_int_filt[df_int_filt["TIPO"] == "ENTRADA DE DIESEL"].copy()
        entradas["QUANTIDADE DE LITROS"] = pd.to_numeric(entradas["QUANTIDADE DE LITROS"], errors="coerce")

        # Merge com df_comb para obter o custo das entradas de diesel
        # Nota: Um merge por data exata pode ser limitante. Para cenários reais,
        # pode ser necessário um merge por faixa de data ou lógica de estoque.
        entradas_com_custo = entradas.merge(df_comb[["EMISSAO", "CUSTO TOTAL"]].dropna(),
                                            left_on="DATA", right_on="EMISSAO", how="left", suffixes=('_int', '_comb'))
        entradas_com_custo["CUSTO TOTAL_comb"] = entradas_com_custo["CUSTO TOTAL_comb"].fillna(0)

        valor_total_entrada = entradas_com_custo["CUSTO TOTAL_comb"].sum()
        litros_entrada = entradas_com_custo["QUANTIDADE DE LITROS"].sum()
        preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada > 0 else 0

        # Saídas de diesel interno (para cálculo de custo e KM rodado)
        saidas = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"].copy()
        saidas["QUANTIDADE DE LITROS"] = pd.to_numeric(saidas["QUANTIDADE DE LITROS"], errors="coerce")
        saidas["CUSTO TOTAL"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro
        saidas["POSTO"] = "Interno"
        saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"] # Renomeia para consistência com df_ext

        # Calcula KM rodado interno
        saidas_com_km = calcula_km_rodado_interno(saidas)

        # Preparar df_ext para concatenação com df_all
        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["POSTO"] = df_ext_copy["POSTO"].fillna("Externo")
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"] # 'CONSUMO' já é numérico do load_data
        # Garante que 'KM RODADOS' exista no df_ext_copy
        if "KM RODADOS" not in df_ext_copy.columns:
            df_ext_copy["KM RODADOS"] = None # Ou pode ser calculado se houver 'KM ATUAL'

        # Unificar colunas para concatenação de df_ext_copy e saidas_com_km
        colunas_necessarias_all = ["DATA", "PLACA", "LITROS", "CUSTO TOTAL", "POSTO", "KM RODADOS"]

        # Reindexar e preencher colunas ausentes para ambos os DataFrames antes de concatenar
        for col in colunas_necessarias_all:
            if col not in df_ext_copy.columns:
                df_ext_copy[col] = None
            if col not in saidas_com_km.columns:
                saidas_com_km[col] = None

        df_ext_copy = df_ext_copy.reindex(columns=colunas_necessarias_all)
        saidas_com_km = saidas_com_km.reindex(columns=colunas_necessarias_all)

        # Concatena todos os dados de abastecimento (externo e interno)
        df_all = pd.concat([df_ext_copy, saidas_com_km], ignore_index=True)

        # Filtro por data na barra lateral
        st.sidebar.markdown("### 🗓️ Filtro por Data")
        if not df_all["DATA"].empty:
            min_data_df = df_all["DATA"].min()
            max_data_df = df_all["DATA"].max()
            data_inicio = st.sidebar.date_input("Data Inicial", min_data_df)
            data_fim = st.sidebar.date_input("Data Final", max_data_df)
            # Aplica o filtro de data
            df_all = df_all[(df_all["DATA"] >= pd.to_datetime(data_inicio)) & (df_all["DATA"] <= pd.to_datetime(data_fim))]
        else:
            st.warning("Nenhum dado disponível para aplicar filtro de data. Verifique se os arquivos foram carregados corretamente.")

        # --- Abas do Dashboard ---
        abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:
            st.markdown("## 📊 Indicadores Resumidos")
            # Exibe métricas chave em colunas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{saidas_com_km['LITROS'].sum():.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Estimado Interno", f"R$ {saidas_com_km['CUSTO TOTAL'].sum():,.2f}")

            # Calcula e exibe a eficiência por veículo
            ext_eff = calcula_eficiencia(df_ext_copy, "Externo", limite_eficiente, limite_normal)
            int_eff = calcula_eficiencia(saidas_com_km, "Interno", limite_eficiente, limite_normal)

            dfs_para_concat = []
            if not ext_eff.empty:
                dfs_para_concat.append(ext_eff)
            if not int_eff.empty:
                dfs_para_concat.append(int_eff)

            if dfs_para_concat:
                df_eff_final = pd.concat(dfs_para_concat, ignore_index=True)
            else:
                df_eff_final = pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICACAO", "POSTO"])
                st.info("Não há dados suficientes para calcular a eficiência de veículos após os filtros.")

            st.markdown("### ⚙️ Classificação de Eficiência por Veículo")
            st.dataframe(df_eff_final.sort_values("KM/LITRO", ascending=False), use_container_width=True)

            # Exibe o Top 5 veículos mais econômicos
            if not df_eff_final.empty:
                top_5 = df_eff_final.sort_values("KM/LITRO", ascending=False).head(5)
                st.markdown("### 🏆 Top 5 Veículos Mais Econômicos")
                st.table(top_5[["PLACA", "KM/LITRO", "CLASSIFICACAO", "POSTO"]])
            else:
                st.info("Não há dados para exibir o Top 5 de veículos mais econômicos.")

        with abas[1]:
            st.markdown("## 📈 Gráficos & Rankings")

            if not df_all.empty:
                # Gráfico de barras: Abastecimento por Placa
                st.markdown("### Abastecimento por Placa (Litros)")
                graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                fig_placa = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True,
                                   title="Volume Total Abastecido por Placa")
                st.plotly_chart(fig_placa, use_container_width=True)

                # Gráfico de linha: Tendência de Abastecimento por Data
                st.markdown("### Tendência de Abastecimento por Data")
                graf_tempo = df_all.groupby(["DATA", "POSTO"])["LITROS"].sum().reset_index()
                fig_tempo = px.line(graf_tempo, x="DATA", y="LITROS", color="POSTO", markers=True,
                                    title="Volume Abastecido ao Longo do Tempo por Posto")
                st.plotly_chart(fig_tempo, use_container_width=True)

                # Gráfico de barras: Eficiência (km/l) por Fonte
                st.markdown("### Eficiência (km/l) por Fonte")
                if not df_eff_final.empty:
                    fig_eff = px.bar(df_eff_final, x="PLACA", y="KM/LITRO", color="CLASSIFICACAO", text_auto=".2f",
                                     title="Eficiência Média por Veículo",
                                     color_discrete_map={"Eficiente": "green", "Normal": "blue", "Ineficiente": "red"})
                    fig_eff.update_layout(yaxis_title="Km por Litro (média)")
                    st.plotly_chart(fig_eff, use_container_width=True)
                else:
                    st.info("Não há dados de eficiência para gerar o gráfico.")

                # Ranking de Veículos por Consumo Total
                st.markdown("### Ranking de Veículos por Consumo Total (Litros)")
                ranking = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                st.dataframe(ranking, use_container_width=True)

                # Comparativo: Interno x Externo (Gráficos de Pizza)
                st.markdown("### Comparativo: Interno x Externo")
                comparativo = df_all.groupby("POSTO").agg(
                    LITROS=("LITROS", "sum"),
                    **{"CUSTO TOTAL": ("CUSTO TOTAL", "sum")}
                ).reset_index()

                col1, col2 = st.columns(2)
                with col1:
                    fig_litros = px.pie(comparativo, values="LITROS", names="POSTO", title="Volume Abastecido por Posto")
                    st.plotly_chart(fig_litros, use_container_width=True)
                with col2:
                    fig_custo = px.pie(comparativo, values="CUSTO TOTAL", names="POSTO", title="Custo Total por Posto")
                    st.plotly_chart(fig_custo, use_container_width=True)
            else:
                st.info("Não há dados para gerar gráficos e rankings após os filtros. Verifique os uploads e filtros.")

        with abas[2]:
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            # Exibe o DataFrame de combustível financeiro e oferece opção de download
            if "PAGAMENTO" in df_comb.columns and not df_comb.empty:
                st.dataframe(df_comb.sort_values("EMISSAO", ascending=False), use_container_width=True)
                st.download_button(
                    label="Download Detalhes Financeiros (CSV)",
                    data=df_comb.to_csv(index=False).encode('utf-8'),
                    file_name="combustivel_financeiro_detalhes.csv",
                    mime="text/csv",
                )
            else:
                st.info("Arquivo Combustível não possui a coluna 'PAGAMENTO' ou está vazio para exibir detalhes financeiros. Verifique o arquivo.")

else:
    st.info("📥 Por favor, envie os três arquivos CSV nas opções da barra lateral e clique em 'Processar Arquivos' para iniciar a análise.")

