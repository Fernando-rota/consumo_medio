import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# Configuração da página
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Classes de Processamento ---
class DataProcessor:
    @staticmethod
    def padroniza_colunas(df):
        """Padroniza nomes das colunas removendo espaços extras"""
        df.columns = df.columns.str.strip()
        return df

    @staticmethod
    def renomear_colunas(df, tipo):
        """Padroniza os nomes das colunas conforme dicionário de mapeamento"""
        renomeios_comuns = {
            "DATA": ["DATA", "Data", " data"],
            "PLACA": ["PLACA", "Placa", " placa"],
            "TIPO": ["TIPO", "Tipo"],
            "QUANTIDADE DE LITROS": ["QUANTIDADE DE LITROS", "quantidade de litros", "Qtd Litros"],
            "CONSUMO": ["CONSUMO", "Consumo"],
            "CUSTO TOTAL": ["CUSTO TOTAL", "VALOR PAGO", "valor pago", "valor total"],
            "DESCRIÇÃO DO ABASTECIMENTO": ["DESCRIÇÃO DO ABASTECIMENTO", "TIPO DE COMBUSTIVEL", "COMBUSTÍVEL"],
            "KM ATUAL": ["KM ATUAL", "Km Atual", "KM_ATUAL"],
            "KM RODADOS": ["KM RODADOS", "Km Rodados", "KM_RODADOS"],
            "EMISSAO": ["EMISSAO", "Emissao", "Emissão", "EMISSÃO", "emissao"],
            "POSTO": ["POSTO", "Posto"]
        }
        
        mapeamento = {}
        cols_upper = [c.upper() for c in df.columns]
        
        for alvo, variacoes in renomeios_comuns.items():
            for v in variacoes:
                if v.upper() in cols_upper:
                    real_col = df.columns[cols_upper.index(v.upper())]
                    mapeamento[real_col] = alvo
                    break
                    
        df.rename(columns=mapeamento, inplace=True)
        
        if tipo == "int" and "TIPO" in df.columns:
            df["TIPO"] = df["TIPO"].str.upper().str.strip()
            
        if "PLACA" in df.columns:
            df["PLACA"] = df["PLACA"].astype(str).str.upper().str.strip().str.replace(" ", "")
            
        return df

    @staticmethod
    def para_float(valor):
        """Converte valores para float, tratando diferentes formatos"""
        if pd.isna(valor):
            return None
        valor_str = str(valor).replace(",", ".").replace("R$", "").replace(" ", "").strip()
        try:
            return float(valor_str)
        except:
            return None

    @staticmethod
    def classifica_eficiencia(km_litro, lim_ef, lim_norm):
        """Classifica a eficiência com base nos limites"""
        if km_litro >= lim_ef:
            return "Eficiente"
        elif km_litro >= lim_norm:
            return "Normal"
        else:
            return "Ineficiente"

    @staticmethod
    def calcula_km_rodado_interno(df):
        """Calcula a quilometragem rodada entre abastecimentos"""
        df = df.copy()
        
        # Validação básica
        if not DataValidator.validate_km_calculation(df):
            df["KM RODADOS"] = None
            return df

        # Processamento otimizado
        df["KM ATUAL"] = pd.to_numeric(df["KM ATUAL"], errors="coerce")
        df = df.sort_values(["PLACA", "DATA"])
        
        # Cálculo vetorizado
        df["KM RODADOS"] = df.groupby("PLACA")["KM ATUAL"].diff().fillna(0)
        df.loc[df["KM RODADOS"] < 0, "KM RODADOS"] = 0
        
        st.write(f"Cálculo de km rodado interno para {len(df)} registros concluído.")
        return df

    @staticmethod
    def calcula_eficiencia(df, posto, lim_ef, lim_norm):
        """Calcula a eficiência de consumo por veículo"""
        df = df.dropna(subset=["KM RODADOS", "LITROS"])
        
        if df.empty:
            return pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"])
            
        # Cálculo otimizado
        df_grouped = df.groupby("PLACA").agg(
            KM_LITRO=("KM RODADOS", "sum"),
            LITROS=("LITROS", "sum")
        ).reset_index()
        
        df_grouped["KM/LITRO"] = df_grouped["KM_LITRO"] / df_grouped["LITROS"]
        df_grouped["CLASSIFICAÇÃO"] = df_grouped["KM/LITRO"].apply(
            lambda x: DataProcessor.classifica_eficiencia(x, lim_ef, lim_norm))
        df_grouped["POSTO"] = posto
        
        return df_grouped[["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"]]

class DataValidator:
    @staticmethod
    def validate_dataframe(df, required_columns, context=""):
        """Valida se o DataFrame contém as colunas necessárias"""
        if df.empty:
            st.warning(f"DataFrame vazio {context}")
            return False
            
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            st.error(f"Colunas faltantes {context}: {', '.join(missing_cols)}")
            return False
            
        return True

    @staticmethod
    def validate_km_calculation(df):
        """Valida se o DataFrame tem os requisitos para cálculo de KM"""
        if df.empty:
            st.warning("DataFrame vazio no cálculo de km rodado interno.")
            return False
            
        if "KM ATUAL" not in df.columns:
            st.error("Coluna 'KM ATUAL' não encontrada no DataFrame.")
            return False
            
        if "PLACA" not in df.columns or "DATA" not in df.columns:
            st.error("Colunas 'PLACA' e/ou 'DATA' não encontradas no DataFrame.")
            return False
            
        return True

class DashboardRenderer:
    @staticmethod
    def show_help_section():
        """Exibe a seção de ajuda do dashboard"""
        with st.expander("ℹ️ Como usar este dashboard"):
            st.markdown("""
            - **Upload de Arquivos**: Faça upload dos 3 arquivos necessários na barra lateral
            - **Filtros**: Use os filtros para selecionar veículos específicos e períodos
            - **Navegação**: Navegue entre as abas para ver diferentes visualizações
            - **Configurações**: Ajuste os limites de eficiência na barra lateral
            """)

    @staticmethod
    def render_indicators(data):
        """Renderiza os indicadores principais"""
        st.markdown("## 📊 Indicadores Resumidos")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Externo (L)", f"{data['consumo_ext']:.1f}")
        col2.metric("Total Interno (L)", f"{data['consumo_int']:.1f}")
        col3.metric("Custo Total Externo", f"R$ {data['custo_ext']:,.2f}")
        col4.metric("Custo Estimado Interno", f"R$ {data['custo_int']:,.2f}")

    @staticmethod
    def render_efficiency_table(df_eff_final):
        """Renderiza a tabela de eficiência"""
        st.markdown("### ⚙️ Classificação de Eficiência por Veículo")
        st.dataframe(df_eff_final.sort_values("KM/LITRO", ascending=False), 
                    height=400,
                    use_container_width=True)

    @staticmethod
    def render_top_vehicles(df_eff_final):
        """Renderiza o ranking dos veículos mais econômicos"""
        st.markdown("### 🏆 Top 5 Veículos Mais Econômicos")
        top_5 = df_eff_final.sort_values("KM/LITRO", ascending=False).head(5)
        st.table(top_5[["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"]])

    @staticmethod
    def render_consumption_charts(df_all):
        """Renderiza os gráficos de consumo"""
        st.markdown("## 📈 Abastecimento por Placa (Litros)")
        graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
        fig = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("## 📆 Tendência de Abastecimento por Data")
        graf_tempo = df_all.groupby(["DATA", "POSTO"])["LITROS"].sum().reset_index()
        fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="POSTO", markers=True)
        st.plotly_chart(fig2, use_container_width=True)

    @staticmethod
    def render_efficiency_chart(df_eff_final):
        """Renderiza o gráfico de eficiência"""
        st.markdown("## ⚙️ Eficiência (km/l) por Fonte")
        fig_eff = px.bar(df_eff_final, x="PLACA", y="KM/LITRO", color="CLASSIFICAÇÃO", 
                         text_auto=".2f", title="Eficiência média por veículo")
        fig_eff.update_layout(yaxis_title="Km por Litro (média)")
        st.plotly_chart(fig_eff, use_container_width=True)

    @staticmethod
    def render_comparison_charts(df_all):
        """Renderiza os gráficos comparativos"""
        st.markdown("## ⚖️ Comparativo: Interno x Externo")
        comparativo = df_all.groupby("POSTO").agg(
            LITROS=("LITROS", "sum"),
            CUSTO_TOTAL=("CUSTO TOTAL", "sum")
        ).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig3 = px.pie(comparativo, values="LITROS", names="POSTO", 
                          title="Volume Abastecido", hole=0.4)
            st.plotly_chart(fig3, use_container_width=True)
        with col2:
            fig4 = px.pie(comparativo, values="CUSTO_TOTAL", names="POSTO", 
                          title="Custo Total", hole=0.4)
            st.plotly_chart(fig4, use_container_width=True)

# --- Funções Principais ---
@st.cache_data(ttl=3600, show_spinner="Processando dados...")
def process_uploaded_files(uploaded_comb, uploaded_ext, uploaded_int):
    """Processa todos os arquivos enviados e retorna dados consolidados"""
    processor = DataProcessor()
    validator = DataValidator()
    
    # Dicionário para armazenar resultados
    result = {
        'df_comb': None,
        'df_ext': None,
        'df_int': None,
        'saidas': None,
        'df_all': None,
        'df_eff_final': None,
        'consumo_ext': 0,
        'consumo_int': 0,
        'custo_ext': 0,
        'custo_int': 0
    }
    
    # Processar cada arquivo
    steps = {
        'comb': "Processando arquivo de combustível...",
        'ext': "Processando abastecimento externo...",
        'int': "Processando abastecimento interno..."
    }
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (key, message) in enumerate(steps.items()):
        status_text.text(message)
        progress_bar.progress((i + 1) / len(steps))
        
        uploaded_file = uploaded_comb if key == 'comb' else uploaded_ext if key == 'ext' else uploaded_int
        df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")
        df = processor.padroniza_colunas(df)
        df = processor.renomear_colunas(df, key)
        
        if key == 'comb':
            result['df_comb'] = df
        elif key == 'ext':
            result['df_ext'] = df
        elif key == 'int':
            result['df_int'] = df
    
    # Validação das colunas necessárias
    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA", "DESCRIÇÃO DO ABASTECIMENTO", "POSTO"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO"}
    
    if not validator.validate_dataframe(result['df_ext'], colunas_necessarias_ext, "no abastecimento externo"):
        return None
    if not validator.validate_dataframe(result['df_int'], colunas_necessarias_int, "no abastecimento interno"):
        return None
    
    # Processamento adicional
    status_text.text("Calculando métricas de consumo...")
    
    # Consumo externo
    result['consumo_ext'] = result['df_ext']["CONSUMO"].apply(processor.para_float).sum()
    result['custo_ext'] = result['df_ext']["CUSTO TOTAL"].apply(processor.para_float).sum()
    
    # Consumo interno
    result['consumo_int'] = result['df_int'][result['df_int']["TIPO"] == "SAÍDA DE DIESEL"]["QUANTIDADE DE LITROS"].apply(processor.para_float).sum()
    
    # Processar entradas diesel interno
    entradas = result['df_int'][result['df_int']["TIPO"] == "ENTRADA DE DIESEL"].copy()
    entradas["QUANTIDADE DE LITROS"] = entradas["QUANTIDADE DE LITROS"].apply(processor.para_float)
    
    # Merge para obter custo nas entradas
    if "EMISSAO" in result['df_comb'].columns:
        result['df_comb']["EMISSAO"] = pd.to_datetime(result['df_comb']["EMISSAO"], dayfirst=True, errors="coerce")
        entradas = entradas.merge(result['df_comb'], left_on="DATA", right_on="EMISSAO", how="left")
        entradas["CUSTO TOTAL"] = entradas["CUSTO TOTAL"].apply(processor.para_float)
    
    valor_total_entrada = entradas["CUSTO TOTAL"].sum()
    litros_entrada = entradas["QUANTIDADE DE LITROS"].sum()
    preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada else 0
    
    # Processar saídas diesel interno
    saidas = result['df_int'][result['df_int']["TIPO"] == "SAÍDA DE DIESEL"].copy()
    saidas["QUANTIDADE DE LITROS"] = saidas["QUANTIDADE DE LITROS"].apply(processor.para_float)
    saidas["CUSTO TOTAL"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro
    saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
    saidas["POSTO"] = "Interno"
    saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"]
    
    # Calcular km rodado interno
    saidas = processor.calcula_km_rodado_interno(saidas)
    result['saidas'] = saidas
    result['custo_int'] = saidas["CUSTO TOTAL"].sum()
    
    # Preparar df_ext para concat
    df_ext_copy = result['df_ext'].copy()
    df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
    df_ext_copy["POSTO"] = df_ext_copy["POSTO"].fillna("Externo")
    df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(processor.para_float)
    
    if "KM RODADOS" in df_ext_copy.columns:
        df_ext_copy["KM RODADOS"] = df_ext_copy["KM RODADOS"].apply(processor.para_float)
    
    # Colunas necessárias para unificação
    colunas_necessarias = ["DATA", "PLACA", "LITROS", "CUSTO TOTAL", "POSTO", "KM RODADOS"]
    
    for col in colunas_necessarias:
        if col not in df_ext_copy.columns:
            df_ext_copy[col] = None
        if col not in saidas.columns:
            saidas[col] = None
    
    # Unificar dados
    result['df_all'] = pd.concat([df_ext_copy[colunas_necessarias], 
                                saidas[colunas_necessarias]], 
                                ignore_index=True)
    
    # Calcular eficiência
    ext_eff = processor.calcula_eficiencia(
        df_ext_copy.dropna(subset=["KM RODADOS", "LITROS"]), 
        "Externo", 
        st.session_state.get('limite_eficiente', 3.0),
        st.session_state.get('limite_normal', 2.0)
    )
    
    int_eff = processor.calcula_eficiencia(
        saidas.dropna(subset=["KM RODADOS", "LITROS"]), 
        "Interno", 
        st.session_state.get('limite_eficiente', 3.0),
        st.session_state.get('limite_normal', 2.0)
    )
    
    dfs_para_concat = []
    if not ext_eff.empty:
        dfs_para_concat.append(ext_eff)
    if not int_eff.empty:
        dfs_para_concat.append(int_eff)
    
    result['df_eff_final'] = pd.concat(dfs_para_concat, ignore_index=True) if dfs_para_concat else pd.DataFrame(
        columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"])
    
    status_text.text("Processamento concluído!")
    progress_bar.empty()
    
    return result

def main():
    # Mostrar seção de ajuda
    DashboardRenderer.show_help_section()
    
    # Upload de arquivos na sidebar
    with st.sidebar:
        st.header("📤 Upload de Arquivos")
        uploaded_comb = st.file_uploader("Combustível (Financeiro)", type="csv")
        uploaded_ext = st.file_uploader("Abastecimento Externo", type="csv")
        uploaded_int = st.file_uploader("Abastecimento Interno", type="csv")
        
        st.markdown("### ⚙️ Configuração")
        limite_eficiente = st.slider("Limite para 'Eficiente' (km/l)", 1.0, 10.0, 3.0, 0.1)
        limite_normal = st.slider("Limite para 'Normal' (km/l)", 0.5, limite_eficiente, 2.0, 0.1)
        
        # Armazenar limites na sessão
        st.session_state['limite_eficiente'] = limite_eficiente
        st.session_state['limite_normal'] = limite_normal
    
    # Processamento principal
    if uploaded_comb and uploaded_ext and uploaded_int:
        try:
            processed_data = process_uploaded_files(uploaded_comb, uploaded_ext, uploaded_int)
            
            if processed_data is None:
                st.error("Erro no processamento dos dados. Verifique os arquivos enviados.")
                return
            
            # Filtro por data
            st.sidebar.markdown("### 🗓️ Filtro por Data")
            min_data = processed_data['df_all']["DATA"].min()
            max_data = processed_data['df_all']["DATA"].max()
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                data_inicio = st.date_input("Data Inicial", min_data)
            with col2:
                data_fim = st.date_input("Data Final", max_data)
            
            # Aplicar filtro de data
            processed_data['df_all'] = processed_data['df_all'][
                (processed_data['df_all']["DATA"] >= pd.to_datetime(data_inicio)) & 
                (processed_data['df_all']["DATA"] <= pd.to_datetime(data_fim))]
            
            # Filtro por placa e tipo de combustível
            placas_validas = sorted(set(processed_data['df_ext']["PLACA"]).union(
                processed_data['df_int']["PLACA"]) - {"-", "CORREÇÃO", ""})
            
            combustiveis = sorted(processed_data['df_ext']["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique())
            
            col1, col2 = st.columns(2)
            with col1:
                placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
            with col2:
                tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + combustiveis)
            
            # Aplicar filtros
            if placa_selecionada != "Todas":
                processed_data['df_all'] = processed_data['df_all'][
                    processed_data['df_all']["PLACA"] == placa_selecionada]
            
            if tipo_comb != "Todos":
                processed_data['df_all'] = processed_data['df_all'][
                    processed_data['df_all']["DESCRIÇÃO DO ABASTECIMENTO"] == tipo_comb]
            
            # Atualizar eficiência com os novos limites
            ext_eff = DataProcessor.calcula_eficiencia(
                processed_data['df_all'][processed_data['df_all']["POSTO"] == "Externo"]
                    .dropna(subset=["KM RODADOS", "LITROS"]), 
                "Externo", 
                limite_eficiente,
                limite_normal
            )
            
            int_eff = DataProcessor.calcula_eficiencia(
                processed_data['df_all'][processed_data['df_all']["POSTO"] == "Interno"]
                    .dropna(subset=["KM RODADOS", "LITROS"]), 
                "Interno", 
                limite_eficiente,
                limite_normal
            )
            
            dfs_para_concat = []
            if not ext_eff.empty:
                dfs_para_concat.append(ext_eff)
            if not int_eff.empty:
                dfs_para_concat.append(int_eff)
            
            processed_data['df_eff_final'] = pd.concat(dfs_para_concat, ignore_index=True) if dfs_para_concat else pd.DataFrame(
                columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"])
            
            # Exibir abas
            abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])
            
            with abas[0]:
                DashboardRenderer.render_indicators(processed_data)
                DashboardRenderer.render_efficiency_table(processed_data['df_eff_final'])
                DashboardRenderer.render_top_vehicles(processed_data['df_eff_final'])
            
            with abas[1]:
                DashboardRenderer.render_consumption_charts(processed_data['df_all'])
                DashboardRenderer.render_efficiency_chart(processed_data['df_eff_final'])
                
                st.markdown("## 🏅 Ranking de Veículos por Consumo Total (Litros)")
                ranking = processed_data['df_all'].groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
                st.dataframe(ranking, use_container_width=True)
                
                DashboardRenderer.render_comparison_charts(processed_data['df_all'])
            
            with abas[2]:
                st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
                if "PAGAMENTO" in processed_data['df_comb'].columns:
                    processed_data['df_comb']["PAGAMENTO"] = pd.to_datetime(
                        processed_data['df_comb']["PAGAMENTO"], dayfirst=True, errors="coerce")
                    st.dataframe(processed_data['df_comb'].sort_values("EMISSAO", ascending=False), 
                               height=400,
                               use_container_width=True)
                else:
                    st.info("Arquivo Combustível não possui a coluna 'PAGAMENTO' para exibir.")
        
        except Exception as e:
            st.error(f"Erro durante o processamento: {str(e)}")
            st.stop()
    else:
        st.info("📥 Por favor, envie os três arquivos CSV nas opções da barra lateral para iniciar a análise.")

if __name__ == "__main__":
    main()
