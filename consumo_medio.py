import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl  # certifique que está instalado
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato de arquivo não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None
        st.success(f'{tipo_base} carregada com sucesso! Linhas: {len(df)}')
        return df
    except Exception as e:
        st.error(f'Erro ao carregar {tipo_base}: {e}')
        return None

def tratar_valor(valor_str):
    try:
        valor = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(valor)
    except:
        return 0.0

def tratar_litros(valor_str):
    try:
        val = str(valor_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return 0.0

def main():
    st.title('Relatório de Abastecimento Interno x Externo com Consumo Médio')

    uploaded_base1 = st.file_uploader('Base 1 – Abastecimento Externo (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base2 = st.file_uploader('Base 2 – Abastecimento Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])
    uploaded_base_combustivel = st.file_uploader('Base 3 – Valor Gasto Combustível Interno (.csv ou .xlsx)', type=['csv', 'xlsx'])

    if uploaded_base1 and uploaded_base2 and uploaded_base_combustivel:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')
        base_combustivel = carregar_base(uploaded_base_combustivel, 'Base 3 (Combustível Interno)')

        if base1 is not None and base2 is not None and base_combustivel is not None:
            # Datas
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')
            base_combustivel['data'] = pd.to_datetime(base_combustivel['Data'], dayfirst=True, errors='coerce')

            # Padronizar placas
            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()
            base_combustivel['placa'] = base_combustivel['Placa'].astype(str).str.replace(' ', '').str.upper()

            # Tratar litros e KM
            base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')

            base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            base_combustivel['valor'] = base_combustivel['Valor Pago'].apply(tratar_valor)

            # Filtros de data e combustível
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                start_date = pd.to_datetime(st.date_input('Data inicial', value=pd.to_datetime('2025-01-01')))
            with col2:
                end_date = pd.to_datetime(st.date_input('Data final', value=pd.to_datetime('2025-12-31')))
            with col3:
                descricao_abastecimento = []
                if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns:
                    descricao_abastecimento = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique().tolist()
                filtro_descricao = None
                if descricao_abastecimento:
                    filtro_descricao = st.selectbox(
                        "Tipo de Combustível (Externo)",
                        ["Todos"] + sorted(descricao_abastecimento),
                        key="combustivel"
                    )
                    if filtro_descricao and filtro_descricao != "Todos":
                        base1 = base1[base1['DESCRIÇÃO DO ABASTECIMENTO'] == filtro_descricao]

            if start_date > end_date:
                st.error("Data inicial deve ser menor ou igual à data final.")
                return

            # Aplicar filtros de datas
            base1 = base1[(base1['data'] >= start_date) & (base1['data'] <= end_date)]
            base2 = base2[(base2['data'] >= start_date) & (base2['data'] <= end_date)]
            base_combustivel = base_combustivel[(base_combustivel['data'] >= start_date) & (base_combustivel['data'] <= end_date)]

            litros_ext = base1['litros'].sum()
            litros_int = base2['litros'].sum()
            total_litros = litros_ext + litros_int
            perc_ext = (litros_ext / total_litros) * 100 if total_litros > 0 else 0
            perc_int = (litros_int / total_litros) * 100 if total_litros > 0 else 0

            valor_ext = 0
            if 'CUSTO TOTAL' in base1.columns:
                valor_ext = base1['CUSTO TOTAL'].apply(tratar_valor).sum()

            valor_combustivel_int = base_combustivel['valor'].sum()

            abas = st.tabs(["📊 Resumo Geral", "🚛 Top 10 Abastecimentos", "⛽ Consumo Médio"])

            # ABA 1 - RESUMO GERAL
            with abas[0]:
                st.subheader(f'Período: {start_date.strftime("%d/%m/%Y")} a {end_date.strftime("%d/%m/%Y")}')
                c1, c2, c3, c4 = st.columns(4)

                with c1:
                    st.markdown("### Litros Externo")
                    st.markdown(f"<h2 style='color:#0072B2'>{litros_ext:,.2f} L</h2>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:gray'>% Externo: {perc_ext:.1f}%</span>", unsafe_allow_html=True)

                with c2:
                    st.markdown("### Valor Gasto Ext.")
                    st.markdown(f"<h2 style='color:#D55E00'>R$ {valor_ext:,.2f}</h2>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                with c3:
                    st.markdown("### Litros Interno")
                    st.markdown(f"<h2 style='color:#009E73'>{litros_int:,.2f} L</h2>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:gray'>% Interno: {perc_int:.1f}%</span>", unsafe_allow_html=True)

                with c4:
                    st.markdown("### Valor Gasto Combustível Int.")
                    st.markdown(f"<h2 style='color:#CC79A7'>R$ {valor_combustivel_int:,.2f}</h2>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                # Gráfico pizza
                fig_pizza = go.Figure(data=[go.Pie(
                    labels=["Abastecimento Externo", "Abastecimento Interno"],
                    values=[litros_ext, litros_int],
                    hole=0.4,
                    marker=dict(colors=['#0072B2', '#009E73']),
                    hoverinfo='label+percent',
                    textinfo='value'
                )])
                fig_pizza.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=350,
                    showlegend=True
                )
                st.plotly_chart(fig_pizza, use_container_width=True)

            # ABA 2 - TOP 10 ABASTECIMENTOS
            with abas[1]:
                st.subheader('Top 10 veículos com mais litros abastecidos')

                top_ext = base1.groupby('placa')['litros'].sum().sort_values(ascending=False).head(10).reset_index()
                top_ext.columns = ['Placa', 'Litros']
                fig_ext = px.bar(top_ext, x='Placa', y='Litros', title='Top 10 Abastecimentos Externos',
                                 labels={'Placa': 'Placa', 'Litros': 'Litros'}, color='Litros', color_continuous_scale='Blues')
                st.plotly_chart(fig_ext, use_container_width=True)
                st.dataframe(top_ext.style.format({'Litros': '{:,.2f}'}))

                top_int = base2.groupby('placa')['litros'].sum().sort_values(ascending=False).head(10).reset_index()
                top_int.columns = ['Placa', 'Litros']
                fig_int = px.bar(top_int, x='Placa', y='Litros', title='Top 10 Abastecimentos Internos',
                                 labels={'Placa': 'Placa', 'Litros': 'Litros'}, color='Litros', color_continuous_scale='Greens')
                st.plotly_chart(fig_int, use_container_width=True)
                st.dataframe(top_int.style.format({'Litros': '{:,.2f}'}))

            # ABA 3 - CONSUMO MÉDIO
            with abas[2]:
                df_combined = pd.concat([
                    base1[['placa', 'data', 'km_atual', 'litros']],
                    base2[['placa', 'data', 'km_atual', 'litros']]
                ], ignore_index=True)

                df_combined = df_combined.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
                df_combined['km_diff'] = df_combined.groupby('placa')['km_atual'].diff()
                df_combined['consumo_por_km'] = df_combined['litros'] / df_combined['km_diff']

                df_clean = df_combined.dropna(subset=['km_diff', 'consumo_por_km'])
                df_clean = df_clean[df_clean['km_diff'] > 0]

                consumo_medio = df_clean.groupby('placa')['consumo_por_km'].mean().reset_index()
                consumo_medio['km_por_litro'] = 1 / consumo_medio['consumo_por_km']
                consumo_medio = consumo_medio[['placa', 'km_por_litro']].sort_values('km_por_litro', ascending=False)

                st.subheader('Consumo Médio por Veículo (Km/L)')
                fig_consumo = px.bar(
                    consumo_medio,
                    x='placa',
                    y='km_por_litro',
                    title='Consumo Médio por Veículo (Km/L)',
                    labels={'placa': 'Placa', 'km_por_litro': 'Km/L'},
                    color='km_por_litro',
                    color_continuous_scale='Purples'
                )
                st.plotly_chart(fig_consumo, use_container_width=True)
                st.dataframe(consumo_medio.style.format({'km_por_litro': '{:.2f}'}))

        else:
            st.warning('Não foi possível processar uma das bases. Verifique os dados.')

    else:
        st.info('Envie as três bases (.csv ou .xlsx) para gerar o relatório.')

if __name__ == '__main__':
    main()
