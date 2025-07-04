import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='Abastecimento Externo x Interno', layout='wide')

def carregar_base(uploaded_file, nome):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            except:
                df = pd.read_csv(uploaded_file, sep=';', engine='python')
        elif uploaded_file.name.lower().endswith(('.xls','xlsx')):
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato não suportado em {nome}.")
            return None
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {e}")
        return None

# Conversão de valores

def tratar_litros(x):
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except:
        return 0.0

def tratar_valor(x):
    try:
        return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0

# App

def main():
    st.title('Abastecimento Externo x Interno')

    # Uploads em linha
    u_ext, u_int, u_val = st.columns(3)
    up_ext = u_ext.file_uploader('Externo', type=['csv','xlsx'])
    up_int = u_int.file_uploader('Interno', type=['csv','xlsx'])
    up_val = u_val.file_uploader('Valor Comb. Int.', type=['csv','xlsx'])
    if up_ext is None or up_int is None or up_val is None:
        st.info('Envie as três bases antes de prosseguir.')
        return

    df_ext = carregar_base(up_ext, 'Externo')
    df_int = carregar_base(up_int, 'Interno')
    df_val = carregar_base(up_val, 'Valor Int.')
    if df_ext is None or df_int is None or df_val is None:
        return

    # Período interativo
    inicio, fim = st.date_input('Selecione o período', value=(pd.to_datetime('2025-01-01'), pd.to_datetime('2025-12-31')))
    inicio = pd.to_datetime(inicio).date()
    fim = pd.to_datetime(fim).date()

    # Converter e filtrar datas
    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').dt.date
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').dt.date
    col_dt = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if col_dt is None:
        st.error('Coluna de data não encontrada em Valor Int.')
        return
    df_val['data'] = pd.to_datetime(df_val[col_dt], dayfirst=True, errors='coerce').dt.date

    df_ext = df_ext[(df_ext['data'] >= inicio) & (df_ext['data'] <= fim)]
    df_int = df_int[(df_int['data'] >= inicio) & (df_int['data'] <= fim)]
    df_val = df_val[(df_val['data'] >= inicio) & (df_val['data'] <= fim)]

    # Criar coluna placa
    if 'PLACA' in df_ext.columns:
        df_ext['placa'] = df_ext['PLACA'].astype(str).str.upper().str.strip()
    else:
        st.error('Coluna PLACA não encontrada em Externo.')
        return
    if 'Placa' in df_int.columns:
        df_int['placa'] = df_int['Placa'].astype(str).str.upper().str.strip()
    else:
        st.error('Coluna Placa não encontrada em Interno.')
        return

    # Tratar valores e litros
    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
    df_val['valor'] = df_val['Valor Total'].apply(tratar_valor)

    # Cálculos resumo
    litros_ext = df_ext['litros'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in df_ext.columns else 0
    litros_int = df_int['litros'].sum()
    valor_int = df_val['valor'].sum()

    tabs = st.tabs(['Resumo', 'Top10', 'Consumo'])

    # Aba Resumo: gráfico comparativo
    with tabs[0]:
        st.subheader(f'Resumo de {inicio.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        df_kpi = pd.DataFrame({
            'Tipo': ['Externo', 'Interno'],
            'Litros': [litros_ext, litros_int],
            'Valor (R$)': [valor_ext, valor_int]
        })
        fig_kpi = px.bar(df_kpi, x='Tipo', y=['Litros', 'Valor (R$)'], barmode='group', text_auto=True,
                         labels={'value': 'Quantidade', 'variable': 'Métrica'})
        st.plotly_chart(fig_kpi, use_container_width=True)

    # Top10 Litros
    with tabs[1]:
        st.subheader('Top 10 Litros')
        te = df_ext.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti = df_int.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(te, x='placa', y='litros', title='Externo'), use_container_width=True)
        st.plotly_chart(px.bar(ti, x='placa', y='litros', title='Interno'), use_container_width=True)

    # Consumo médio
    with tabs[2]:
        df = pd.concat([df_ext[['placa','data','litros']], df_int[['placa','data','litros']]])
        df = df.sort_values(['placa','data']).reset_index(drop=True)
        df['prev'] = df.groupby('placa')['litros'].shift(1)
        df['consumo'] = df['litros'] / df['prev']
        cm = df.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo':'Média Km/L'})
        st.plotly_chart(px.bar(cm, x='placa', y='Média Km/L', title='Consumo Médio'), use_container_width=True)

if __name__=='__main__':
    main()
