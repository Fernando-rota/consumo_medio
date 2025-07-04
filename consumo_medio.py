import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Relatório Abastecimento Interno x Externo', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            try:
                import openpyxl
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            except ImportError:
                st.warning(f"Arquivo {tipo_base} é Excel, mas falta o pacote openpyxl. Use CSV.")
                return None
        else:
            st.warning(f"Formato não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None

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
    st.title('Relatório Abastecimento Interno x Externo')

    uploaded_base1 = st.file_uploader('Base 1 – Externo (.csv ou .xlsx)', type=['csv', 'xlsx'], key="up1")
    uploaded_base2 = st.file_uploader('Base 2 – Interno (.csv ou .xlsx)', type=['csv', 'xlsx'], key="up2")

    if uploaded_base1 and uploaded_base2:
        base1 = carregar_base(uploaded_base1, 'Base 1 (Externo)')
        base2 = carregar_base(uploaded_base2, 'Base 2 (Interno)')

        if base1 is not None and base2 is not None:

            # Trocar placa '-' no interno para texto descritivo
            base2['Placa'] = base2['Placa'].astype(str).str.strip()
            base2.loc[base2['Placa'] == '-', 'Placa'] = 'Entrada Posto Interno'

            # Data
            base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
            base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')

            # Placa
            base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
            base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()

            base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
            base1['km_atual'] = pd.to_numeric(base1['KM ATUAL'], errors='coerce')

            base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
            base2['km_atual'] = pd.to_numeric(base2['KM Atual'], errors='coerce')

            # Mostrar apenas uma vez as infos base carregadas (compacto, lado a lado)
            col1, col2 = st.columns([1,1])
            with col1:
                st.markdown(f"**Base 1 (Externo):** {len(base1):,} linhas")
            with col2:
                st.markdown(f"**Base 2 (Interno):** {len(base2):,} linhas")

            # Filtros na mesma linha
            fcol1, fcol2, fcol3 = st.columns([1,1,2])
            with fcol1:
                start_date = st.date_input('Data inicial', value=pd.to_datetime('2025-01-01'))
            with fcol2:
                end_date = st.date_input('Data final', value=pd.to_datetime('2025-12-31'))
            with fcol3:
                filtro_combustivel = None
                if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns:
                    combustiveis = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique().tolist()
                    filtro_combustivel = st.selectbox("Tipo Combustível (Externo)", ["Todos"] + sorted(combustiveis))

            if start_date > end_date:
                st.error("Data inicial deve ser menor ou igual à final.")
                return

            base1 = base1[(base1['data'] >= pd.Timestamp(start_date)) & (base1['data'] <= pd.Timestamp(end_date))]
            base2 = base2[(base2['data'] >= pd.Timestamp(start_date)) & (base2['data'] <= pd.Timestamp(end_date))]

            if filtro_combustivel and filtro_combustivel != "Todos":
                base1 = base1[base1['DESCRIÇÃO DO ABASTECIMENTO'] == filtro_combustivel]

            litros_ext = base1['litros'].sum()
            litros_int = base2['litros'].sum()
            total_litros = litros_ext + litros_int
            perc_ext = (litros_ext / total_litros) * 100 if total_litros > 0 else 0
            perc_int = (litros_int / total_litros) * 100 if total_litros > 0 else 0

            valor_ext = 0
            if 'CUSTO TOTAL' in base1.columns:
                valor_ext = base1['CUSTO TOTAL'].apply(tratar_valor).sum()

            abas = st.tabs(["Resumo", "Top 10", "Consumo Médio"])

            with abas[0]:
                st.subheader(f'Período: {start_date.strftime("%d/%m/%Y")} a {end_date.strftime("%d/%m/%Y")}')
                c1, c2 = st.columns(2)
                with c1:
                    st.metric('Litros Externo', f'{litros_ext:,.2f} L')
                    st.metric('Valor Gasto Ext.', f'R$ {valor_ext:,.2f}')
                    st.metric('% Externo', f'{perc_ext:.1f}%')
                with c2:
                    st.metric('Litros Interno', f'{litros_int:,.2f} L')
                    st.metric('% Interno', f'{perc_int:.1f}%')

            with abas[1]:
                st.subheader('Top 10 Abastecimentos')

                top_ext = base1.groupby('placa')['litros'].sum().sort_values(ascending=False).head(10).reset_index()
                top_ext.columns = ['Veículo', 'Litros']
                fig_ext = px.bar(top_ext, x='Veículo', y='Litros', color='Litros', 
                                 color_continuous_scale='Blues', title='Externo')
                st.plotly_chart(fig_ext, use_container_width=True)
                st.dataframe(top_ext.style.format({'Litros': '{:,.2f}'}))

                top_int = base2.groupby('placa')['litros'].sum().sort_values(ascending=False).head(10).reset_index()
                top_int.columns = ['Veículo', 'Litros']
                fig_int = px.bar(top_int, x='Veículo', y='Litros', color='Litros',
                                 color_continuous_scale='Greens', title='Interno')
                st.plotly_chart(fig_int, use_container_width=True)
                st.dataframe(top_int.style.format({'Litros': '{:,.2f}'}))

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

                st.subheader('Consumo Médio (Km/L)')
                fig_consumo = px.bar(consumo_medio, x='placa', y='km_por_litro', color='km_por_litro',
                                    color_continuous_scale='Purples', labels={'placa': 'Veículo', 'km_por_litro': 'Km/L'})
                st.plotly_chart(fig_consumo, use_container_width=True)
                st.dataframe(consumo_medio.style.format({'km_por_litro': '{:.2f}'}))

        else:
            st.warning('Não foi possível processar as bases. Verifique os dados.')

    else:
        st.info('Envie as duas bases (.csv ou .xlsx) para gerar o relatório.')

if __name__ == '__main__':
    main()
