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

# Conversão

def tratar_litros(x):
    try: return float(str(x).replace('.', '').replace(',', '.'))
    except: return 0.0

def tratar_valor(x):
    try: return float(str(x).replace('R$', '').replace('.', '').replace(',', '.'))
    except: return 0.0

# App

def main():
    st.title('Abastecimento Externo x Interno')

    # uploads inline
    c1,c2,c3 = st.columns(3)
    up_ext = c1.file_uploader('Externo', type=['csv','xlsx'])
    up_int = c2.file_uploader('Interno', type=['csv','xlsx'])
    up_val = c3.file_uploader('Valor Int.', type=['csv','xlsx'])
    if not (up_ext and up_int and up_val):
        st.info('Envie as 3 bases antes de prosseguir.')
        return

    df_ext = carregar_base(up_ext,'Externo')
    df_int = carregar_base(up_int,'Interno')
    df_val = carregar_base(up_val,'Valor Int.')
    if None in (df_ext, df_int, df_val): return

    # datas em formato brasileiro
    from datetime import date
    f1,f2 = st.columns(2)
    with f1:
        ini = st.date_input('Data inicial', value=date(2025,1,1))
    with f2:
        fim = st.date_input('Data final', value=date(2025,12,31))
    
    # converter datas
    df_ext['data'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce').dt.date
    df_int['data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce').dt.date
    col_dt = next((c for c in df_val.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if not col_dt:
        st.error('Coluna de data não encontrada em Valor Int.')
        return
    df_val['data'] = pd.to_datetime(df_val[col_dt], dayfirst=True, errors='coerce').dt.date

    # filtrar
    df_ext = df_ext[(df_ext['data']>=ini)&(df_ext['data']<=fim)]
    df_int = df_int[(df_int['data']>=ini)&(df_int['data']<=fim)]
    df_val = df_val[(df_val['data']>=ini)&(df_val['data']<=fim)]

    # tratar valores
    df_ext['litros'] = df_ext['CONSUMO'].apply(tratar_litros)
    df_int['litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
    df_val['valor'] = df_val['Valor Total'].apply(tratar_valor)

    # cálculos resumo
    litros_ext = df_ext['litros'].sum()
    litros_int = df_int['litros'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in df_ext.columns else 0
    valor_int = df_val['valor'].sum()

    tabs = st.tabs(['Resumo','Top10','Consumo'])

    # aba Resumo: um KPI externo, um interno empilhados
    with tabs[0]:
        st.subheader(f'Resumo {ini.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}')
        st.metric('✦ Externo (L)', f'{litros_ext:,.2f}', delta=None)
        st.metric('✦ Externo (R$)', f'{valor_ext:,.2f}', delta=None)
        st.metric('✦ Interno (L)', f'{litros_int:,.2f}', delta=None)
        st.metric('✦ Interno (R$)', f'{valor_int:,.2f}', delta=None)

    # Top10
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
        df['prev_litros'] = df.groupby('placa')['litros'].shift(1)
        df['consumo'] = df['litros'] / df['prev_litros']
        cm = df.groupby('placa')['consumo'].mean().reset_index().rename(columns={'consumo':'média'})
        st.plotly_chart(px.bar(cm, x='placa', y='média', title='Consumo Médio'), use_container_width=True)

if __name__=='__main__':
    main()
