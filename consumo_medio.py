import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Relatório Abastecimento Interno x Externo', layout='wide')

# Função para tratar valores monetários
def tratar_valor(valor_str):
    try:
        valor = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(valor)
    except:
        return 0.0

# Função para tratar quantidade de litros
def tratar_litros(valor_str):
    try:
        val = str(valor_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return 0.0

# Função para carregar planilhas
def carregar_base(uploaded_file):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                return pd.read_csv(uploaded_file, sep=';', engine='python')
            except:
                return pd.read_csv(uploaded_file, sep=',', engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl
            return pd.read_excel(uploaded_file, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None

# Função principal
def main():
    st.markdown("<h2 style='text-align: center;'>Relatório Abastecimento Interno x Externo</h2>", unsafe_allow_html=True)

    with st.expander("Envio das Bases", expanded=True):
        col_up1, col_up2, col_up3 = st.columns(3)
        with col_up1:
            uploaded_ext = st.file_uploader("Base Externa", type=['csv', 'xlsx'])
        with col_up2:
            uploaded_int = st.file_uploader("Base Interna", type=['csv', 'xlsx'])
        with col_up3:
            uploaded_comb = st.file_uploader("Custo Combustível Interno", type=['csv', 'xlsx'])

    if uploaded_ext and uploaded_int and uploaded_comb:
        df_ext = carregar_base(uploaded_ext)
        df_int = carregar_base(uploaded_int)
        df_val = carregar_base(uploaded_comb)

        if None in (df_ext, df_int, df_val):
            st.error("Erro ao carregar uma ou mais bases.")
            return

        # Padronização da externa
        df_ext['data'] = pd.to_datetime(df_ext.get('DATA'), dayfirst=True, errors='coerce')
        df_ext['placa'] = df_ext.get('PLACA', '').astype(str).str.replace(' ', '').str.upper()
        df_ext['litros'] = df_ext.get('CONSUMO', 0).apply(tratar_litros)
        df_ext['km_atual'] = pd.to_numeric(df_ext.get('KM ATUAL'), errors='coerce')

        # Padronização da interna
        if 'Placa' in df_int.columns:
            df_int = df_int[df_int['Placa'].str.upper().ne('ENTRADA POSTO INTERNO')]
            df_int['placa'] = df_int['Placa'].astype(str).str.replace(' ', '').str.upper()
        else:
            df_int['placa'] = ''

        df_int['data'] = pd.to_datetime(df_int.get('Data'), dayfirst=True, errors='coerce')
        df_int['litros'] = pd.to_numeric(df_int.get('Quantidade de litros'), errors='coerce')
        df_int['km_atual'] = pd.to_numeric(df_int.get('KM Atual'), errors='coerce')

        # Padronização da base de custo
        for col in ['Data', 'DATA', 'data']:
            if col in df_val.columns:
                df_val['data'] = pd.to_datetime(df_val[col], dayfirst=True, errors='coerce')
                break
        else:
            df_val['data'] = pd.NaT

        if 'Placa' in df_val.columns:
            df_val['placa'] = df_val['Placa'].astype(str).str.replace(' ', '').str.upper()
        else:
            df_val['placa'] = ''

        col_val_list = [c for c in df_val.columns if 'valor' in c.lower()]
        if col_val_list:
            col_val = col_val_list[0]
            df_val['valor_pago'] = df_val[col_val].apply(tratar_valor)
        else:
            st.warning("Coluna de valor não encontrada na base de custo do combustível.")
            df_val['valor_pago'] = 0.0

        # Filtros por data
        colf1, colf2 = st.columns(2)
        with colf1:
            data_ini = st.date_input("Data Inicial", value=df_ext['data'].min())
        with colf2:
            data_fim = st.date_input("Data Final", value=df_ext['data'].max())

        df_ext = df_ext[(df_ext['data'] >= pd.Timestamp(data_ini)) & (df_ext['data'] <= pd.Timestamp(data_fim))]
        df_int = df_int[(df_int['data'] >= pd.Timestamp(data_ini)) & (df_int['data'] <= pd.Timestamp(data_fim))]
        df_val = df_val[(df_val['data'] >= pd.Timestamp(data_ini)) & (df_val['data'] <= pd.Timestamp(data_fim))]

        # KPIs
        litros_ext = df_ext['litros'].sum()
        litros_int = df_int['litros'].sum()

        col_custo_ext = [c for c in df_ext.columns if 'custo total' in c.lower()]
        if col_custo_ext:
            valor_ext = df_ext[col_custo_ext[0]].apply(tratar_valor).sum()
        else:
            st.warning("Coluna 'CUSTO TOTAL' não encontrada na base externa.")
            valor_ext = 0.0

        valor_int = df_val['valor_pago'].sum()

        total_litros = litros_ext + litros_int
        perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 and pd.notna(litros_ext) else 0
        perc_int = (litros_int / total_litros * 100) if total_litros > 0 and pd.notna(litros_int) else 0

        st.markdown(f"<h4 style='margin-top:10px;'>Período: {data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}</h4>", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Litros Ext.", f"{litros_ext:,.2f} L", delta=f"{perc_ext:.1f}%")
        with k2:
            st.metric("Custo Ext.", f"R$ {valor_ext:,.2f}")
        with k3:
            st.metric("Litros Int.", f"{litros_int:,.2f} L", delta=f"{perc_int:.1f}%")
        with k4:
            st.metric("Custo Int.", f"R$ {valor_int:,.2f}")

        # Gráfico comparativo
        df_bar = pd.DataFrame({
            'Tipo': ['Externo', 'Interno'],
            'Litros': [litros_ext, litros_int],
            'Custo': [valor_ext, valor_int]
        })

        df_plot = df_bar.melt(id_vars='Tipo', value_vars=['Litros', 'Custo'], var_name='Metrica', value_name='Valor')

        fig = px.bar(df_plot, x='Metrica', y='Valor', color='Tipo', barmode='group', text_auto='.2s')
        fig.update_layout(font=dict(size=16), title_font=dict(size=22))
        st.plotly_chart(fig, use_container_width=True)

        # Aba consumo médio
        st.markdown("### Consumo Médio por Veículo (Km/L)")

        df_comb = pd.concat([
            df_ext[['placa', 'data', 'km_atual', 'litros']],
            df_int[['placa', 'data', 'km_atual', 'litros']]
        ], ignore_index=True).dropna(subset=['placa', 'data', 'km_atual', 'litros'])

        df_comb = df_comb.sort_values(['placa', 'data'])
        df_comb['km_diff'] = df_comb.groupby('placa')['km_atual'].diff()
        df_comb['consumo_km_l'] = df_comb['km_diff'] / df_comb['litros']

        df_clean = df_comb[df_comb['km_diff'] > 0].dropna(subset=['consumo_km_l'])
        consumo_medio = df_clean.groupby('placa')['consumo_km_l'].mean().reset_index().sort_values('consumo_km_l', ascending=False)

        fig2 = px.bar(consumo_medio, x='placa', y='consumo_km_l', text_auto='.2f',
                      labels={'placa': 'Veículo', 'consumo_km_l': 'Km/L'}, color='consumo_km_l', color_continuous_scale='Plasma')
        fig2.update_layout(font=dict(size=16))
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(consumo_medio.style.format({'consumo_km_l': '{:.2f}'}))

if __name__ == '__main__':
    main()
