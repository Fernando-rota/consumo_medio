import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title='Relatório de Abastecimento Interno x Externo', layout='wide')

def carregar_base(uploaded_file, tipo_base):
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            # Leitura CSV com detecção de separador
            try:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
            except Exception:
                df = pd.read_csv(uploaded_file, sep=';', engine='python')
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            import openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            st.warning(f"Formato não suportado para {tipo_base}. Use .csv ou .xlsx.")
            return None
        # Limpar nomes de colunas
        df.columns = df.columns.str.strip()
        st.success(f"{tipo_base} carregada: {len(df):,} linhas")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {tipo_base}: {e}")
        return None

def tratar_valor(valor_str):
    try:
        v = str(valor_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(v)
    except:
        return 0.0


def tratar_litros(litro_str):
    try:
        v = str(litro_str).replace(' ', '').replace('.', '').replace(',', '.')
        return float(v)
    except:
        return 0.0


def main():
    st.title('Relatório de Abastecimento Interno x Externo')

    up1 = st.file_uploader('Base Externo', type=['csv', 'xlsx'])
    up2 = st.file_uploader('Base Interno', type=['csv', 'xlsx'])
    up3 = st.file_uploader('Base Valor Combustível Interno', type=['csv', 'xlsx'])

    if not (up1 and up2 and up3):
        st.info('Envie as três bases (.csv ou .xlsx).')
        return

    base1 = carregar_base(up1, 'Externo')
    base2 = carregar_base(up2, 'Interno')
    base3 = carregar_base(up3, 'Valor Combustível Interno')
    if base1 is None or base2 is None or base3 is None:
        return

    # Tratar datas
    base1['data'] = pd.to_datetime(base1['DATA'], dayfirst=True, errors='coerce')
    base2['data'] = pd.to_datetime(base2['Data'], dayfirst=True, errors='coerce')
    date_col3 = next((c for c in base3.columns if 'dt' in c.lower() or 'data' in c.lower()), None)
    if not date_col3:
        st.error('Coluna de data não encontrada na base de combustível.')
        return
    base3['data'] = pd.to_datetime(base3[date_col3], dayfirst=True, errors='coerce')

    # Padronizar placas
    base1['placa'] = base1['PLACA'].astype(str).str.replace(' ', '').str.upper()
    base2['placa'] = base2['Placa'].astype(str).str.replace(' ', '').str.upper()
    base3['placa'] = base3['Placa'].astype(str).str.replace(' ', '').str.upper() if 'Placa' in base3.columns else None

    # Tratar litros e valor
    base1['litros'] = base1['CONSUMO'].apply(tratar_litros)
    base2['litros'] = pd.to_numeric(base2['Quantidade de litros'], errors='coerce')
    base3['valor_total'] = base3['Valor Total'].apply(tratar_valor)

    # Filtros linha única
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        start = st.date_input('Data inicial', value=pd.to_datetime('2025-01-01'))
    with c2:
        end = st.date_input('Data final', value=pd.to_datetime('2025-12-31'))
    with c3:
        tipos = base1['DESCRIÇÃO DO ABASTECIMENTO'].dropna().unique().tolist() if 'DESCRIÇÃO DO ABASTECIMENTO' in base1.columns else []
        filtro = st.selectbox('Tipo Combustível (Externo)', ['Todos'] + sorted(tipos))

    if start > end:
        st.error('Data inicial deve ser <= data final.')
        return

    # aplicar filtros usando comparação de datas sem hora
    mask1 = (base1['data'].dt.date >= start) & (base1['data'].dt.date <= end)
    mask2 = (base2['data'].dt.date >= start) & (base2['data'].dt.date <= end)
    mask3 = (base3['data'].dt.date >= start) & (base3['data'].dt.date <= end)
    base1 = base1[mask1]
    base2 = base2[mask2]
    base3 = base3[mask3]
    if filtro != 'Todos':
        base1 = base1[base1['DESCRIÇÃO DO ABASTECIMENTO'] == filtro]

    # Cálculos
    litros_ext = base1['litros'].sum()
    litros_int = base2['litros'].sum()
    total = litros_ext + litros_int
    pct_ext = litros_ext / total * 100 if total > 0 else 0
    pct_int = litros_int / total * 100 if total > 0 else 0
    valor_ext = base1['CUSTO TOTAL'].apply(tratar_valor).sum() if 'CUSTO TOTAL' in base1.columns else 0
    valor_int = base3['valor_total'].sum()

    abas = st.tabs(['📊 Resumo', '🚛 Top10', '⛽ Consumo'])

    with abas[0]:
        st.subheader(f'Período: {start.strftime("%d/%m/%Y")} a {end.strftime("%d/%m/%Y")}')
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
        c1.metric('Litros Ext.', f'{litros_ext:,.2f} L', f'{pct_ext:.1f}%')
        c2.metric('Valor Ext.', f'R$ {valor_ext:,.2f}')
        c3.metric('Litros Int.', f'{litros_int:,.2f} L', f'{pct_int:.1f}%')
        c4.metric('Gasto Int.', f'R$ {valor_int:,.2f}')
        # pizza
        fig = go.Figure(go.Pie(
            labels=['Ext.', 'Int.'],
            values=[litros_ext, litros_int],
            hole=0.4,
            marker=dict(colors=['#0072B2', '#009E73']),
            hoverinfo='label+percent'
        ))
        fig.update_layout(margin=dict(t=0, b=0), height=300)
        c5.plotly_chart(fig, use_container_width=True)

    with abas[1]:
        st.subheader('Top 10 Abastecimentos')
        te = base1.groupby('placa')['litros'].sum().nlargest(10).reset_index().rename(columns={'placa': 'Placa', 'litros': 'Litros'})
        ti = base2.groupby('placa')['litros'].sum().nlargest(10).reset_index().rename(columns={'placa': 'Placa', 'litros': 'Litros'})
        fig1 = px.bar(te, x='Placa', y='Litros', color='Litros', color_continuous_scale='Blues', title='Externo')
        fig2 = px.bar(ti, x='Placa', y='Litros', color='Litros', color_continuous_scale='Greens', title='Interno')
        st.plotly_chart(fig1, use_container_width=True)
        st.dataframe(te.style.format({'Litros': '{:,.2f}'}))
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(ti.style.format({'Litros': '{:,.2f}'}))

    with abas[2]:
        df = pd.concat([
            base1[['placa', 'data', 'km_atual', 'litros']],
            base2[['placa', 'data', 'km_atual', 'litros']]
        ])
        df = df.sort_values(['placa', 'data', 'km_atual']).reset_index(drop=True)
        df['km_diff'] = df.groupby('placa')['km_atual'].diff()
        df['cons_km'] = df['litros'] / df['km_diff']
        df = df.dropna(subset=['cons_km'])
        cm = df.groupby('placa')['cons_km'].mean().reset_index().rename(columns={'cons_km': 'km_por_litro'})
        cm = cm.sort_values('km_por_litro', ascending=False)
        fig3 = px.bar(cm, x='placa', y='km_por_litro', color='km_por_litro', color_continuous_scale='Purples', labels={'placa':'Placa','km_por_litro':'Km/L'})
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(cm.style.format({'km_por_litro': '{:.2f}'}))

if __name__ == '__main__':
    main()
