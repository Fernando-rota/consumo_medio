import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="⛽ BI - Abastecimento", layout="wide")

@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    try:
        if file.name.lower().endswith(".csv"):
            try:
                df = pd.read_csv(file, sep=None, engine="python")
            except:
                df = pd.read_csv(file, sep=";", engine="python")
        else:
            df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

def tratar_valor(x):
    try:
        return float(str(x).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except:
        return 0.0

def tratar_litros(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

def main():
    st.title("⛽ Dashboard de Abastecimento Interno vs Externo")

    with st.expander("📥 Enviar arquivos"):
        col1, col2, col3 = st.columns(3)
        file_comb = col1.file_uploader("🧾 Planilha COMBUSTÍVEL (entrada de diesel)", type=["xlsx", "csv"])
        file_ext = col2.file_uploader("📄 Planilha ABASTECIMENTO EXTERNO", type=["xlsx", "csv"])
        file_int = col3.file_uploader("📄 Planilha ABASTECIMENTO INTERNO", type=["xlsx", "csv"])

    if not file_comb or not file_ext or not file_int:
        st.info("Carregue as três planilhas para visualizar o dashboard.")
        return

    df_comb = carregar_base(file_comb, "Combustível")
    df_ext = carregar_base(file_ext, "Externo")
    df_int = carregar_base(file_int, "Interno")

    if df_comb is None or df_ext is None or df_int is None:
        return

    df_comb["emissao"] = pd.to_datetime(df_comb["emissao"], errors="coerce")
    df_comb["valor_pago"] = df_comb["valor"].apply(tratar_valor)

    df_ext = df_ext.rename(columns={
        "descrição do abastecimento": "combustivel",
        "km atual": "km_atual",
        "custo total": "valor_pago",
        "consumo": "litros"
    })
    df_ext["data"] = pd.to_datetime(df_ext["data"], errors="coerce")
    df_ext["valor_pago"] = df_ext["valor_pago"].apply(tratar_valor)
    df_ext["litros"] = df_ext["litros"].apply(tratar_litros)
    df_ext["placa"] = df_ext["placa"].astype(str).str.upper().str.strip()

    df_int = df_int.rename(columns={
        "km atual": "km_atual",
        "quantidade de litros": "litros"
    })
    df_int["data"] = pd.to_datetime(df_int["data"], errors="coerce")
    df_int["litros"] = df_int["litros"].apply(tratar_litros)
    df_int["placa"] = df_int["placa"].astype(str).str.upper().str.strip()

    diesel_total = df_comb["valor_pago"].sum()
    litros_entrada = df_comb.shape[0]
    total_litros_int = df_int[df_int["tipo"].str.lower() == "saida de diesel"]["litros"].sum()
    media_preco_interno = diesel_total / total_litros_int if total_litros_int > 0 else 0

    total_litros_ext = df_ext["litros"].sum()
    total_valor_ext = df_ext["valor_pago"].sum()
    media_preco_externo = total_valor_ext / total_litros_ext if total_litros_ext > 0 else 0

    st.subheader("📊 Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("💸 Preço Médio Interno (R$/L)", f"{media_preco_interno:.2f}")
    col2.metric("💸 Preço Médio Externo (R$/L)", f"{media_preco_externo:.2f}")
    col3.metric("📈 Diferença", f"{(media_preco_externo - media_preco_interno):.2f}", delta_color="inverse")

    st.subheader("🔍 Evolução dos Abastecimentos")
    df_ext_group = df_ext.groupby("data")["litros"].sum().reset_index(name="litros_externo")
    df_int_group = df_int[df_int["tipo"].str.lower() == "saida de diesel"].groupby("data")["litros"].sum().reset_index(name="litros_interno")
    df_merged = pd.merge(df_ext_group, df_int_group, on="data", how="outer").sort_values("data")

    fig = px.line(df_merged, x="data", y=["litros_externo", "litros_interno"],
                  labels={"value": "Litros", "variable": "Tipo"},
                  title="Evolução Diária de Abastecimento")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🚚 Consumo por Veículo (Externo vs Interno)")
    veiculos_ext = df_ext.groupby("placa")["litros"].sum().reset_index(name="litros_ext")
    veiculos_int = df_int[df_int["tipo"].str.lower() == "saida de diesel"].groupby("placa")["litros"].sum().reset_index(name="litros_int")
    df_veiculos = pd.merge(veiculos_ext, veiculos_int, on="placa", how="outer").fillna(0)

    fig_bar = px.bar(df_veiculos.melt(id_vars="placa", value_vars=["litros_ext", "litros_int"],
                                      var_name="tipo", value_name="litros"),
                     x="placa", y="litros", color="tipo", barmode="group",
                     title="Litros por Veículo")
    st.plotly_chart(fig_bar, use_container_width=True)

if __name__ == "__main__":
    main()
