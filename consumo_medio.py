import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# Upload arquivos
st.sidebar.header("📁 Enviar arquivos .csv")
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

# Parâmetros para classificação de eficiência via sliders
st.sidebar.markdown("### ⚙️ Configuração Classificação de Eficiência (km/l)")
limite_eficiente = st.sidebar.slider("Limite para 'Eficiente' (km/l)", 1.0, 10.0, 3.0, 0.1)
limite_normal = st.sidebar.slider("Limite para 'Normal' (km/l)", 0.5, limite_eficiente, 2.0, 0.1)

def padroniza_colunas(df):
    # Remove espaços extras das colunas
    df.columns = df.columns.str.strip()
    return df

def renomear_colunas(df, tipo):
    # Mapeia várias variações de nomes para nomes padrão em maiúsculo
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
        "EMISSAO": ["EMISSAO", "Emissao", "Emissão", "EMISSÃO", "emissao"]
    }

    mapeamento = {}
    cols_upper = [c.upper() for c in df.columns]
    for alvo, variações in renomeios_comuns.items():
        for v in variações:
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

def para_float(valor):
    if pd.isna(valor):
        return None
    valor_str = str(valor).replace(",", ".").replace("R$", "").replace(" ", "").strip()
    try:
        return float(valor_str)
    except:
        return None

def classifica_eficiencia(km_litro, lim_ef, lim_norm):
    if km_litro >= lim_ef:
        return "Eficiente"
    elif km_litro >= lim_norm:
        return "Normal"
    else:
        return "Ineficiente"

def calcula_km_rodado_interno(df):
    df = df.copy()
    # Converte KM ATUAL para numérico, NaN onde inválido
    df["KM ATUAL"] = pd.to_numeric(df["KM ATUAL"], errors="coerce")
    res = []
    for placa, grupo in df.sort_values("DATA").groupby("PLACA"):
        grupo = grupo.reset_index(drop=True)
        grupo["KM RODADOS"] = grupo["KM ATUAL"].diff().fillna(0)
        grupo.loc[grupo["KM RODADOS"] < 0, "KM RODADOS"] = 0  # Evita valores negativos por reset
        res.append(grupo)
    return pd.concat(res)

def calcula_eficiencia(df, fonte, lim_ef, lim_norm):
    df = df.dropna(subset=["KM RODADOS", "LITROS"])
    if df.empty:
        return pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "FONTE"])
    df_grouped = df.groupby("PLACA").apply(
        lambda x: (x["KM RODADOS"].sum() / x["LITROS"].sum()) if x["LITROS"].sum() > 0 else 0
    ).reset_index(name="KM/LITRO")
    df_grouped["CLASSIFICAÇÃO"] = df_grouped["KM/LITRO"].apply(lambda x: classifica_eficiencia(x, lim_ef, lim_norm))
    df_grouped["FONTE"] = fonte
    return df_grouped

if uploaded_comb and uploaded_ext and uploaded_int:
    # Leitura e padronização
    df_comb = padroniza_colunas(pd.read_csv(uploaded_comb, sep=";", encoding="utf-8"))
    df_ext = padroniza_colunas(pd.read_csv(uploaded_ext, sep=";", encoding="utf-8"))
    df_int = padroniza_colunas(pd.read_csv(uploaded_int, sep=";", encoding="utf-8"))

    df_comb = renomear_colunas(df_comb, "comb")
    df_ext = renomear_colunas(df_ext, "ext")
    df_int = renomear_colunas(df_int, "int")

    # Debug: exibir colunas carregadas
    st.sidebar.write("Colunas Combustível:", df_comb.columns.tolist())
    st.sidebar.write("Colunas Externo:", df_ext.columns.tolist())
    st.sidebar.write("Colunas Interno:", df_int.columns.tolist())

    # Validar colunas essenciais
    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA", "DESCRIÇÃO DO ABASTECIMENTO"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO"}

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}")
    else:
        # Preparar filtros
        placas_validas = sorted(set(df_ext["PLACA"]).union(df_int["PLACA"]) - {"-", "CORREÇÃO", ""})
        combustiveis = sorted(df_ext["DESCRIÇÃO DO ABASTECIMENTO"].dropna().unique())

        col1, col2 = st.columns(2)
        with col1:
            placa_selecionada = st.selectbox("🔎 Filtrar por Placa", ["Todas"] + placas_validas)
        with col2:
            tipo_comb = st.selectbox("⛽ Tipo de Combustível", ["Todos"] + combustiveis)

        def aplicar_filtros(df, placa_col, tipo_comb_col=None):
            if placa_selecionada != "Todas":
                df = df[df[placa_col] == placa_selecionada]
            if tipo_comb != "Todos" and tipo_comb_col and tipo_comb_col in df.columns:
                df = df[df[tipo_comb_col] == tipo_comb]
            return df

        df_ext_filt = aplicar_filtros(df_ext, "PLACA", "DESCRIÇÃO DO ABASTECIMENTO")
        df_int_filt = aplicar_filtros(df_int, "PLACA")

        # Somatórios
        consumo_ext = df_ext_filt["CONSUMO"].apply(para_float).sum()
        custo_ext = df_ext_filt["CUSTO TOTAL"].apply(para_float).sum()

        # Apenas saída de diesel para consumo interno
        consumo_int = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"]["QUANTIDADE DE LITROS"].apply(para_float).sum()

        # Data emissão no financeiro
        if "EMISSAO" in df_comb.columns:
            df_comb["EMISSAO"] = pd.to_datetime(df_comb["EMISSAO"], dayfirst=True, errors="coerce")
        else:
            st.warning("⚠️ Coluna 'EMISSAO' não encontrada no arquivo Combustível (Financeiro).")

        # Cálculo custo médio litro interno baseado nas entradas de diesel e financeiro
        entradas = df_int[df_int["TIPO"] == "ENTRADA DE DIESEL"].copy()
        entradas["QUANTIDADE DE LITROS"] = entradas["QUANTIDADE DE LITROS"].apply(para_float)

        entradas = entradas.merge(df_comb, left_on="DATA", right_on="EMISSAO", how="left")
        entradas["CUSTO TOTAL"] = entradas["CUSTO TOTAL"].apply(para_float)
        valor_total_entrada = entradas["CUSTO TOTAL"].sum()
        litros_entrada = entradas["QUANTIDADE DE LITROS"].sum()
        preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada else 0

        saidas = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"].copy()
        saidas["QUANTIDADE DE LITROS"] = saidas["QUANTIDADE DE LITROS"].apply(para_float)
        saidas["CUSTO"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro
        custo_int = saidas["CUSTO"].sum()

        # Prepara dataframe externo
        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
        df_ext_copy["FONTE"] = "Externo"
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(para_float)
        df_ext_copy["CUSTO"] = df_ext_copy["CUSTO TOTAL"].apply(para_float)
        df_ext_copy["KM RODADOS"] = df_ext_copy["KM RODADOS"].apply(para_float) if "KM RODADOS" in df_ext_copy.columns else None

        # Prepara dataframe interno só com saídas (abastecimentos)
        saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
        saidas["FONTE"] = "Interno"
        saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"]
        saidas["KM RODADOS"] = None  # Depois calcularemos

        # Calcula km rodados internos (delta km)
        if "KM ATUAL" in df_int_filt.columns:
            df_int_eff = calcula_km_rodado_interno(df_int_filt.copy())
        else:
            df_int_eff = df_int_filt.copy()
            df_int_eff["KM RODADOS"] = None

        df_int_eff["LITROS"] = df_int_eff["QUANTIDADE DE LITROS"].apply(para_float)
        df_int_eff = df_int_eff[df_int_eff["TIPO"] == "SAÍDA DE DIESEL"]

        df_all = pd.concat([
            df_ext_copy[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS"]],
            df_int_eff[["DATA", "PLACA", "LITROS", "CUSTO", "FONTE", "KM RODADOS"]],
        ], ignore_index=True)

        # Filtro por período
        st.sidebar.markdown("### 🗓️ Filtro por Data")
        min_data = df_all["DATA"].min()
        max_data = df_all["DATA"].max()
        data_inicio = st.sidebar.date_input("Data Inicial", min_data)
        data_fim = st.sidebar.date_input("Data Final", max_data)
        df_all = df_all[(df_all["DATA"] >= pd.to_datetime(data_inicio)) & (df_all["DATA"] <= pd.to_datetime(data_fim))]

        # Abas para separar visualizações
        abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:
            st.markdown("## 📊 Indicadores Resumidos")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Estimado Interno", f"R$ {custo_int:,.2f}")

            # Classificação de eficiência para externo
            ext_eff = calcula_eficiencia(df_ext_copy.dropna(subset=["KM RODADOS", "LITROS"]), "Externo", limite_eficiente, limite_normal)
            # Classificação de eficiência para interno
            int_eff = calcula_eficiencia(df_int_eff.dropna(subset=["KM RODADOS", "LITROS"]), "Interno", limite_eficiente, limite_normal)

            df_eff_final = pd.concat([ext_eff, int_eff], ignore_index=True)

            st.markdown("### ⚙️ Classificação de Eficiência por Veículo")
            st.dataframe(df_eff_final.sort_values("KM/LITRO", ascending=False), use_container_width=True)

            # Mostrar Top 5 mais econômicos
            top_5 = df_eff_final.sort_values("KM/LITRO", ascending=False).head(5)
            st.markdown("### 🏆 Top 5 Veículos Mais Econômicos")
            st.table(top_5[["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "FONTE"]])

        with abas[1]:
            st.markdown("## 📈 Abastecimento por Placa (Litros)")
            graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            fig = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("## 📆 Tendência de Abastecimento por Data")
            graf_tempo = df_all.groupby(["DATA", "FONTE"])["LITROS"].sum().reset_index()
            fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="FONTE", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("## ⚙️ Eficiência (km/l) por Fonte")
            fig_eff = px.bar(df_eff_final, x="PLACA", y="KM/LITRO", color="CLASSIFICAÇÃO", text_auto=".2f",
                             title="Eficiência média por veículo")
            fig_eff.update_layout(yaxis_title="Km por Litro (média)")
            st.plotly_chart(fig_eff, use_container_width=True)

            st.markdown("## 🏅 Ranking de Veículos por Consumo Total (Litros)")
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

        with abas[2]:
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            st.dataframe(df_comb, use_container_width=True)

            # Opção para exportar tabela consolidada
            def to_excel(df):
                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                df.to_excel(writer, index=False, sheet_name='Resumo')
                writer.save()
                processed_data = output.getvalue()
                return processed_data

            st.markdown("### 📥 Exportar dados consolidados")
            df_export = df_all.sort_values("DATA", ascending=False)
            excel_data = to_excel(df_export)
            st.download_button(label='Exportar Excel', data=excel_data, file_name='dados_abastecimento.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

else:
    st.warning("⬅️ Envie os 3 arquivos `.csv` na barra lateral para visualizar o dashboard.")
