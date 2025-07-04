import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title='Relatório Abastecimento', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            except:
                df = pd.read_csv(uploaded_file, sep=';', engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato não suportado para {tipo_base}.")
            return None
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {tipo_base}: {e}")
        return None


def tratar_valor(v):
    try:
        return float(str(v).replace('R$', '').replace('.', '').replace(',', '.'))
    except:
        return 0.0


def tratar_litros(v):
    try:
        return float(str(v).replace('.', '').replace(',', '.'))
    except:
        return 0.0


def main():
    st.title('Abastecimento Externo x Interno')

    # Uploads compactos em linha
    u1, u2, u3 = st.columns(3)
    up1 = u1.file_uploader('Externo', type=['csv','xlsx'], key='e')
    up2 = u2.file_uploader('Interno', type=['csv','xlsx'], key='i')
    up3 = u3.file_uploader('Valor Int.', type=['csv','xlsx'], key='v')
    if not (up1 and up2 and up3):
        st.info('Envie as 3 bases.')
        return

    base1 = carregar_base(up1,'Externo')
    base2 = carregar_base(up2,'Interno')
    base3 = carregar_base(up3,'Valor Int.')
    if None in (base1,base2,base3): return

    # Datas
    base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
    base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')
    coluna3 = next((c for c in base3.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if not coluna3:
        st.error('Data não encontrada em Valor Int.')
        return
    base3['data'] = pd.to_datetime(base3[coluna3], dayfirst=True, errors='coerce')

    # Padronizar e tratar
    base1['placa']=base1['PLACA'].astype(str).str.upper()
    base2['placa']=base2['Placa'].astype(str).str.upper()
    base3['valor']=base3['Valor Total'].apply(tratar_valor)
    base1['litros']=base1['CONSUMO'].apply(tratar_litros)
    base2['litros']=pd.to_numeric(base2['Quantidade de litros'],errors='coerce')

    # Filtros em linha
    f1,f2,f3 = st.columns([1,1,2])
    with f1: sd=st.date_input('De',value=pd.to_datetime('2025-01-01'))
    with f2: ed=st.date_input('Até',value=pd.to_datetime('2025-12-31'))
    with f3:
        tipos = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique().tolist() if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns else []
        filt = st.selectbox('Tipo (Ext)',['Todos']+sorted(tipos))

    if sd>ed:
        st.error('Data inválida')
        return
    # aplicar filtros data
    m1=(base1['data'].dt.date>=sd)&(base1['data'].dt.date<=ed)
    m2=(base2['data'].dt.date>=sd)&(base2['data'].dt.date<=ed)
    m3=(base3['data'].dt.date>=sd)&(base3['data'].dt.date<=ed)
    base1,base2,base3=base1[m1],base2[m2],base3[m3]
    if filt!='Todos': base1=base1[base1['DESCRIÇÃO DO ABASTECIMENTO']==filt]

    # cálculos
    le=base1['litros'].sum()
    li=base2['litros'].sum()
    tot=le+li
    pe=le/tot*100 if tot>0 else 0
    pi=li/tot*100 if tot>0 else 0
    ve=base1['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in base1.columns else 0
    vi=base3['valor'].sum()

    tabs=st.tabs(['Resumo','Top10','Consumo'])
    with tabs[0]:
        st.subheader(f'{sd.strftime('%d/%m/%Y')} a {ed.strftime('%d/%m/%Y')}')
        c1,c2,c3,c4=st.columns(4)
        c1.metric('LExt',f'{le:,.0f}L',f'{pe:.1f}%')
        c2.metric('VExt',f'R${ve:,.0f}')
        c3.metric('LInt',f'{li:,.0f}L',f'{pi:.1f}%')
        c4.metric('VInt',f'R${vi:,.0f}')
    with tabs[1]:
        st.subheader('Top 10')
        te=base1.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        ti=base2.groupby('placa')['litros'].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(te,x='placa',y='litros',title='Ext'),use_container_width=True)
        st.plotly_chart(px.bar(ti,x='placa',y='litros',title='Int'),use_container_width=True)
    with tabs[2]:
        df=pd.concat([base1[['placa','data','litros']],base2[['placa','data','litros']]])
        df['diff']=df.groupby('placa')['litros'].diff()
        cm=df.groupby('placa')['diff'].mean().reset_index().rename(columns={'diff':'km/L'})
        st.plotly_chart(px.bar(cm,x='placa',y='km/L'),use_container_width=True)

if __name__=='__main__': main()
