import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento de Veículos")

# --- Funções ---

def padroniza_colunas(df):
    df.columns = df.columns.str.strip()
    return df

def renomear_colunas(df, tipo):
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

def calcula_eficiencia(df, posto, lim_ef, lim_norm):
    df = df.dropna(subset=["KM RODADOS", "LITROS"])
    if df.empty:
        return pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"])
    df_grouped = df.groupby("PLACA").apply(
        lambda x: (x["KM RODADOS"].sum() / x["LITROS"].sum()) if x["LITROS"].sum() > 0 else 0
    ).reset_index(name="KM/LITRO")
    df_grouped["CLASSIFICAÇÃO"] = df_grouped["KM/LITRO"].apply(lambda x: classifica_eficiencia(x, lim_ef, lim_norm))
    df_grouped["POSTO"] = posto
    return df_grouped

# --- Uploads ---
uploaded_comb = st.sidebar.file_uploader("📄 Combustível (Financeiro)", type="csv")
uploaded_ext = st.sidebar.file_uploader("⛽ Abastecimento Externo", type="csv")
uploaded_int = st.sidebar.file_uploader("🛢️ Abastecimento Interno", type="csv")

st.sidebar.markdown("### ⚙️ Configuração Classificação de Eficiência (km/l)")
limite_eficiente = st.sidebar.slider("Limite para 'Eficiente' (km/l)", 1.0, 10.0, 3.0, 0.1)
limite_normal = st.sidebar.slider("Limite para 'Normal' (km/l)", 0.5, limite_eficiente, 2.0, 0.1)

if uploaded_comb and uploaded_ext and uploaded_int:
    # Leitura dos CSVs
    df_comb = padroniza_colunas(pd.read_csv(uploaded_comb, sep=";", encoding="utf-8"))
    df_ext = padroniza_colunas(pd.read_csv(uploaded_ext, sep=";", encoding="utf-8"))
    df_int = padroniza_colunas(pd.read_csv(uploaded_int, sep=";", encoding="utf-8"))

    # Renomear colunas
    df_comb = renomear_colunas(df_comb, "comb")
    df_ext = renomear_colunas(df_ext, "ext")
    df_int = renomear_colunas(df_int, "int")

    # Verificação colunas obrigatórias
    colunas_necessarias_ext = {"PLACA", "CONSUMO", "CUSTO TOTAL", "DATA", "DESCRIÇÃO DO ABASTECIMENTO", "POSTO"}
    colunas_necessarias_int = {"PLACA", "QUANTIDADE DE LITROS", "DATA", "TIPO"}

    faltando_ext = colunas_necessarias_ext - set(df_ext.columns)
    faltando_int = colunas_necessarias_int - set(df_int.columns)

    if faltando_ext:
        st.error(f"❌ Abastecimento Externo está faltando colunas: {faltando_ext}")
    elif faltando_int:
        st.error(f"❌ Abastecimento Interno está faltando colunas: {faltando_int}")
    else:
        # Preparar dados para filtro
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

        consumo_ext = df_ext_filt["CONSUMO"].apply(para_float).sum()
        custo_ext = df_ext_filt["CUSTO TOTAL"].apply(para_float).sum()
        consumo_int = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"]["QUANTIDADE DE LITROS"].apply(para_float).sum()

        # Processar df_comb para datas
        if "EMISSAO" in df_comb.columns:
            df_comb["EMISSAO"] = pd.to_datetime(df_comb["EMISSAO"], dayfirst=True, errors="coerce")
        else:
            st.warning("⚠️ Coluna 'EMISSAO' não encontrada no arquivo Combustível (Financeiro).")

        # Entradas diesel interno
        entradas = df_int[df_int["TIPO"] == "ENTRADA DE DIESEL"].copy()
        entradas["QUANTIDADE DE LITROS"] = entradas["QUANTIDADE DE LITROS"].apply(para_float)

        # Merge para obter custo nas entradas
        entradas = entradas.merge(df_comb, left_on="DATA", right_on="EMISSAO", how="left")
        entradas["CUSTO TOTAL"] = entradas["CUSTO TOTAL"].apply(para_float)

        valor_total_entrada = entradas["CUSTO TOTAL"].sum()
        litros_entrada = entradas["QUANTIDADE DE LITROS"].sum()
        preco_medio_litro = valor_total_entrada / litros_entrada if litros_entrada else 0

        # Saídas diesel interno
        saidas = df_int_filt[df_int_filt["TIPO"] == "SAÍDA DE DIESEL"].copy()
        saidas["QUANTIDADE DE LITROS"] = saidas["QUANTIDADE DE LITROS"].apply(para_float)
        saidas["CUSTO TOTAL"] = saidas["QUANTIDADE DE LITROS"] * preco_medio_litro

        saidas["DATA"] = pd.to_datetime(saidas["DATA"], dayfirst=True, errors="coerce")
        saidas["POSTO"] = "Interno"
        saidas["LITROS"] = saidas["QUANTIDADE DE LITROS"]

        # Calcula km rodado interno com proteção
        if saidas.empty:
            st.warning("O DataFrame 'saidas' está vazio. Não será possível calcular km rodado interno.")
            saidas["KM RODADOS"] = None
        elif ("PLACA" not in saidas.columns) or ("DATA" not in saidas.columns):
            st.error("Colunas 'PLACA' e/ou 'DATA' não estão presentes no DataFrame 'saidas'.")
            saidas["KM RODADOS"] = None
        else:
            saidas = calcula_km_rodado_interno(saidas)

        # Preparar df_ext para concat
        df_ext_copy = df_ext_filt.copy()
        df_ext_copy["DATA"] = pd.to_datetime(df_ext_copy["DATA"], dayfirst=True, errors="coerce")
        df_ext_copy["POSTO"] = df_ext_copy["POSTO"].fillna("Externo")
        df_ext_copy["LITROS"] = df_ext_copy["CONSUMO"].apply(para_float)
        df_ext_copy["KM RODADOS"] = df_ext_copy["KM RODADOS"].apply(para_float) if "KM RODADOS" in df_ext_copy.columns else None

        colunas_necessarias = ["DATA", "PLACA", "LITROS", "CUSTO TOTAL", "POSTO", "KM RODADOS"]
        for col in colunas_necessarias:
            if col not in df_ext_copy.columns:
                df_ext_copy[col] = None
            if col not in saidas.columns:
                saidas[col] = None

        df_ext_copy = df_ext_copy.reindex(columns=colunas_necessarias)
        saidas = saidas.reindex(columns=colunas_necessarias)

        df_all = pd.concat([df_ext_copy, saidas], ignore_index=True)

        # Filtro por data
        st.sidebar.markdown("### 🗓️ Filtro por Data")
        min_data = df_all["DATA"].min()
        max_data = df_all["DATA"].max()
        data_inicio = st.sidebar.date_input("Data Inicial", min_data)
        data_fim = st.sidebar.date_input("Data Final", max_data)
        df_all = df_all[(df_all["DATA"] >= pd.to_datetime(data_inicio)) & (df_all["DATA"] <= pd.to_datetime(data_fim))]

        abas = st.tabs(["📊 Indicadores", "📈 Gráficos & Rankings", "🧾 Financeiro"])

        with abas[0]:
            st.markdown("## 📊 Indicadores Resumidos")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Externo (L)", f"{consumo_ext:.1f}")
            col2.metric("Total Interno (L)", f"{consumo_int:.1f}")
            col3.metric("Custo Total Externo", f"R$ {custo_ext:,.2f}")
            col4.metric("Custo Estimado Interno", f"R$ {saidas['CUSTO TOTAL'].sum():,.2f}")

            ext_eff = calcula_eficiencia(df_ext_copy.dropna(subset=["KM RODADOS", "LITROS"]), "Externo", limite_eficiente, limite_normal)
            int_eff = calcula_eficiencia(saidas.dropna(subset=["KM RODADOS", "LITROS"]), "Interno", limite_eficiente, limite_normal)

            dfs_para_concat = []
            if not ext_eff.empty:
                dfs_para_concat.append(ext_eff)
            if not int_eff.empty:
                dfs_para_concat.append(int_eff)

            if dfs_para_concat:
                df_eff_final = pd.concat(dfs_para_concat, ignore_index=True)
            else:
                df_eff_final = pd.DataFrame(columns=["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"])

            st.markdown("### ⚙️ Classificação de Eficiência por Veículo")
            st.dataframe(df_eff_final.sort_values("KM/LITRO", ascending=False), use_container_width=True)

            top_5 = df_eff_final.sort_values("KM/LITRO", ascending=False).head(5)
            st.markdown("### 🏆 Top 5 Veículos Mais Econômicos")
            st.table(top_5[["PLACA", "KM/LITRO", "CLASSIFICAÇÃO", "POSTO"]])

        with abas[1]:
            st.markdown("## 📈 Abastecimento por Placa (Litros)")
            graf_placa = df_all.groupby("PLACA")["LITROS"].sum().reset_index().sort_values("LITROS", ascending=False)
            fig = px.bar(graf_placa, x="PLACA", y="LITROS", color="PLACA", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("## 📆 Tendência de Abastecimento por Data")
            graf_tempo = df_all.groupby(["DATA", "POSTO"])["LITROS"].sum().reset_index()
            fig2 = px.line(graf_tempo, x="DATA", y="LITROS", color="POSTO", markers=True)
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
            comparativo = df_all.groupby("POSTO").agg(
                LITROS=("LITROS", "sum"),
                **{"CUSTO TOTAL": ("CUSTO TOTAL", "sum")}
            ).reset_index()

            col1, col2 = st.columns(2)
            with col1:
                fig3 = px.pie(comparativo, values="LITROS", names="POSTO", title="Volume Abastecido")
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                fig4 = px.pie(comparativo, values="CUSTO TOTAL", names="POSTO", title="Custo Total")
                st.plotly_chart(fig4, use_container_width=True)

        with abas[2]:
            st.markdown("## 🧾 Faturas de Combustível (Financeiro)")
            if "PAGAMENTO" in df_comb.columns:
                df_comb["PAGAMENTO"] = pd.to_datetime(df_comb["PAGAMENTO"], dayfirst=True, errors="coerce")
                st.dataframe(df_comb.sort_values("EMISSAO", ascending=False), use_container_width=True)
            else:
                st.info("Arquivo Combustível não possui a coluna 'PAGAMENTO' para exibir.")

else:
    st.info("📥 Por favor, envie os três arquivos CSV nas opções da barra lateral para iniciar a análise.")
