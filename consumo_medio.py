import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title='⛽ Dashboard de Abastecimento',
    layout='wide',
    page_icon='⛽'
)

# Funções auxiliares
@st.cache_data(show_spinner=False)
def carregar_base(file, nome):
    """Carrega arquivos CSV ou Excel com tratamento de erros"""
    try:
        if file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file, sep=';', engine='python', encoding='utf-8')
        else:
            import openpyxl
            df = pd.read_excel(file, engine='openpyxl')
        
        df.columns = df.columns.str.strip().str.upper()
        registros_invalidos = df.isna().sum().sum()
        
        if registros_invalidos > 0:
            st.warning(f"⚠️ {registros_invalidos} registros inválidos foram ignorados em {nome}.")
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao carregar {nome}: {str(e)}")
        return None

def formatar_moeda(valor):
    """Formata valores monetários"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def validar_placa(placa):
    """Valida o formato de placas de veículo"""
    placa = str(placa).strip().upper()
    padrao_antigo = re.compile(r'^[A-Z]{3}\d{4}$')  # ABC1234
    padrao_mercosul = re.compile(r'^[A-Z]{3}\d[A-Z]\d{2}$')  # ABC1D23
    return bool(padrao_antigo.match(placa)) or bool(padrao_mercosul.match(placa))

def classificar_consumo(km_l):
    """Classifica o consumo de combustível"""
    if km_l <= 0 or km_l > 20:  # Intervalo plausível
        return 'Outlier'
    elif km_l >= 6:
        return 'Econômico'
    elif km_l >= 3.5:
        return 'Normal'
    else:
        return 'Ineficiente'

def main():
    # Cabeçalho
    st.markdown("<h1 style='text-align:center;'>⛽ Abastecimento Interno vs Externo</h1>", 
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Análise comparativa de consumo, custo e eficiência</p>", 
                unsafe_allow_html=True)
    
    # Upload de arquivos
    with st.expander('📁 Carregar bases de dados (Clique para instruções)'):
        st.markdown("""
        **📝 Formato esperado:**  
        - **Base Externa**: Deve conter colunas: DATA, PLACA, LITROS, CUSTO TOTAL  
        - **Base Interna**: Deve conter colunas: DATA, PLACA, QUANTIDADE DE LITROS  
        - **Base Valores**: Deve conter colunas: EMISSÃO, VALOR  
        """)
        
        c1, c2, c3 = st.columns(3)
        up_ext = c1.file_uploader('Base Externa', type=['csv', 'xlsx'])
        up_int = c2.file_uploader('Base Interna', type=['csv', 'xlsx'])
        up_val = c3.file_uploader('Base Combustível (Valores)', type=['csv', 'xlsx'])

    if not (up_ext and up_int and up_val):
        st.info('⚠️ Envie as três bases antes de prosseguir.')
        return

    # Carregamento e validação dos dados
    df_ext = carregar_base(up_ext, 'Base Externa')
    df_int = carregar_base(up_int, 'Base Interna')
    df_val = carregar_base(up_val, 'Base Combustível (Valores)')
    
    if df_ext is None or df_int is None or df_val is None:
        return

    # Verificação de colunas obrigatórias
    colunas_obrigatorias = {
        'Base Externa': ['DATA', 'PLACA', 'LITROS', 'CUSTO TOTAL'],
        'Base Interna': ['DATA', 'PLACA', 'QUANTIDADE DE LITROS'],
        'Base Combustível': ['EMISSÃO', 'VALOR']
    }
    
    for df, nome in zip([df_ext, df_int, df_val], colunas_obrigatorias.keys()):
        colunas_faltantes = [col for col in colunas_obrigatorias[nome] if col not in df.columns]
        if colunas_faltantes:
            st.error(f"Colunas obrigatórias faltantes em {nome}: {', '.join(colunas_faltantes)}")
            return

    # Pré-processamento dos dados
    def preprocessar_dados(df_ext, df_int, df_val):
        # Converter tipos de dados
        df_ext['DATA'] = pd.to_datetime(df_ext['DATA'], dayfirst=True, errors='coerce')
        df_ext['LITROS'] = pd.to_numeric(df_ext['LITROS'].str.replace(',', '.'), errors='coerce').fillna(0)
        df_ext['CUSTO TOTAL'] = pd.to_numeric(
            df_ext['CUSTO TOTAL'].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.'), 
            errors='coerce'
        ).fillna(0)
        
        df_int['DATA'] = pd.to_datetime(df_int['DATA'], dayfirst=True, errors='coerce')
        df_int['QUANTIDADE DE LITROS'] = pd.to_numeric(
            df_int['QUANTIDADE DE LITROS'].str.replace(',', '.'), 
            errors='coerce'
        ).fillna(0)
        
        df_val['DATA'] = pd.to_datetime(df_val['EMISSÃO'], dayfirst=True, errors='coerce')
        df_val['VALOR'] = pd.to_numeric(
            df_val['VALOR'].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.'), 
            errors='coerce'
        ).fillna(0)
        
        # Validar placas
        df_ext = df_ext[df_ext['PLACA'].apply(validar_placa)]
        df_int = df_int[df_int['PLACA'].apply(validar_placa)]
        
        return df_ext, df_int, df_val

    df_ext, df_int, df_val = preprocessar_dados(df_ext, df_int, df_val)

    # Filtros interativos
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por data
    min_data = max(
        pd.Timestamp('2023-01-01'),
        min(df_ext['DATA'].min(), df_int['DATA'].min(), df_val['DATA'].min())
    )
    max_data = max(df_ext['DATA'].max(), df_int['DATA'].max(), df_val['DATA'].max())
    
    data_selecao = st.sidebar.slider(
        '📅 Período de análise',
        min_value=min_data.date(),
        max_value=max_data.date(),
        value=(min_data.date(), max_data.date()),
        format='DD/MM/YYYY'
    )
    
    # Aplicar filtro de data
    df_ext = df_ext[(df_ext['DATA'].dt.date >= data_selecao[0]) & 
                    (df_ext['DATA'].dt.date <= data_selecao[1])]
    df_int = df_int[(df_int['DATA'].dt.date >= data_selecao[0]) & 
                    (df_int['DATA'].dt.date <= data_selecao[1])]
    df_val = df_val[(df_val['DATA'].dt.date >= data_selecao[0]) & 
                    (df_val['DATA'].dt.date <= data_selecao[1])]

    # Filtro por tipo de combustível (se existir)
    combustivel_col = next((col for col in df_ext.columns if 'COMBUST' in col or 'DESCRI' in col), None)
    if combustivel_col:
        tipos_combustivel = sorted(df_ext[combustivel_col].dropna().unique())
        filtro_combustivel = st.sidebar.selectbox(
            '🛢️ Tipo de combustível:', 
            ['Todos'] + tipos_combustivel
        )
        if filtro_combustivel != 'Todos':
            df_ext = df_ext[df_ext[combustivel_col] == filtro_combustivel]

    # Filtro por placa
    placas = sorted(pd.concat([df_ext['PLACA'], df_int['PLACA']]).dropna().unique())
    filtro_placa = st.sidebar.selectbox('🚗 Placa do veículo:', ['Todas'] + placas)
    
    if filtro_placa != 'Todas':
        df_ext = df_ext[df_ext['PLACA'] == filtro_placa]
        df_int = df_int[df_int['PLACA'] == filtro_placa]
        if 'PLACA' in df_val.columns:
            df_val = df_val[df_val['PLACA'] == filtro_placa]

    # Cálculo de métricas principais
    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()
    
    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros > 0 else 0
    perc_int = (litros_int / total_litros * 100) if total_litros > 0 else 0
    
    # Cálculo de economia potencial
    custo_por_litro_ext = valor_ext / litros_ext if litros_ext > 0 else 0
    custo_por_litro_int = valor_int / litros_int if litros_int > 0 else 0
    economia = (custo_por_litro_ext - custo_por_litro_int) * litros_ext

    # Layout das abas
    tab1, tab2, tab3, tab4 = st.tabs([
        '📊 Resumo Geral', 
        '🚗 Veículos', 
        '⚙️ Eficiência', 
        '📈 Tendências'
    ])

    with tab1:
        st.markdown(f"### 📆 Período: `{data_selecao[0].strftime('%d/%m/%Y')} a {data_selecao[1].strftime('%d/%m/%Y')}`")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('⛽ Litros (Externo)', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
        col2.metric('💵 Custo (Externo)', formatar_moeda(valor_ext))
        col3.metric('⛽ Litros (Interno)', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
        col4.metric('💵 Custo (Interno)', formatar_moeda(valor_int))
        
        # Comparativo de custo por litro
        st.markdown("### 💰 Comparativo de Custo por Litro")
        col5, col6, col7 = st.columns(3)
        col5.metric('🏪 Custo/L (Externo)', formatar_moeda(custo_por_litro_ext))
        col6.metric('🏭 Custo/L (Interno)', formatar_moeda(custo_por_litro_int))
        col7.metric('💸 Economia potencial', 
                   formatar_moeda(economia), 
                   delta=f"{(economia/valor_ext*100 if valor_ext > 0 else 0):.1f}%")
        
        # Gráfico comparativo
        df_comparativo = pd.DataFrame({
            'Tipo': ['Externo', 'Interno'],
            'Litros': [litros_ext, litros_int],
            'Custo': [valor_ext, valor_int]
        })
        
        fig = px.bar(
            df_comparativo.melt(id_vars='Tipo'), 
            x='Tipo', y='value', color='variable', barmode='group',
            labels={'value': '', 'variable': 'Métrica'},
            text=[f"{x:,.2f} L" if var == 'Litros' else formatar_moeda(x) 
                  for var, x in zip(df_comparativo.melt(id_vars='Tipo')['variable'], 
                                    df_comparativo.melt(id_vars='Tipo')['value'])],
            title='🔍 Comparativo de Consumo e Custo'
        )
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 🚙 Top 10 Veículos por Consumo")
        
        # Top 10 externo
        top_ext = df_ext.groupby('PLACA').agg({
            'LITROS': 'sum',
            'CUSTO TOTAL': 'sum'
        }).nlargest(10, 'LITROS').reset_index()
        
        # Top 10 interno
        top_int = df_int.groupby('PLACA').agg({
            'QUANTIDADE DE LITROS': 'sum'
        }).nlargest(10, 'QUANTIDADE DE LITROS').reset_index()
        
        # Layout em colunas
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏪 Abastecimento Externo")
            fig1 = px.bar(
                top_ext, y='PLACA', x='LITROS', orientation='h',
                color='LITROS', color_continuous_scale='Blues',
                labels={'LITROS': 'Litros consumidos', 'PLACA': 'Placa'},
                text=[f"{x:,.1f} L" for x in top_ext['LITROS']]
            )
            fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig1, use_container_width=True)
            
        with col2:
            st.markdown("#### 🏭 Abastecimento Interno")
            fig2 = px.bar(
                top_int, y='PLACA', x='QUANTIDADE DE LITROS', orientation='h',
                color='QUANTIDADE DE LITROS', color_continuous_scale='Greens',
                labels={'QUANTIDADE DE LITROS': 'Litros consumidos', 'PLACA': 'Placa'},
                text=[f"{x:,.1f} L" for x in top_int['QUANTIDADE DE LITROS']]
            )
            fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("### ⚡ Eficiência dos Veículos (km/L)")
        
        # Cálculo do consumo médio
        df_consumo = pd.concat([
            df_ext[['PLACA', 'DATA', 'KM ATUAL', 'LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'LITROS': 'litros'}),
            df_int[['PLACA', 'DATA', 'KM ATUAL', 'QUANTIDADE DE LITROS']].rename(
                columns={'PLACA': 'placa', 'DATA': 'data', 'KM ATUAL': 'km_atual', 'QUANTIDADE DE LITROS': 'litros'})
        ])
        
        df_consumo = df_consumo.dropna().sort_values(['placa', 'data'])
        df_consumo['km_diff'] = df_consumo.groupby('placa')['km_atual'].diff()
        df_consumo = df_consumo[df_consumo['km_diff'] > 0]
        df_consumo['consumo'] = df_consumo['km_diff'] / df_consumo['litros']
        
        consumo_medio = df_consumo.groupby('placa').agg({
            'consumo': 'mean',
            'litros': 'sum'
        }).reset_index().rename(columns={'consumo': 'km_l', 'litros': 'total_litros'})
        
        consumo_medio['classificacao'] = consumo_medio['km_l'].apply(classificar_consumo)
        consumo_medio = consumo_medio.sort_values('km_l', ascending=False)
        
        # Detectar outliers
        outliers = consumo_medio[consumo_medio['classificacao'] == 'Outlier']
        if not outliers.empty:
            st.warning(f"⚠️ {len(outliers)} veículos com consumo anormal (verifique os dados):")
            st.dataframe(outliers)
        
        # Visualização
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.dataframe(
                consumo_medio.style.format({'km_l': '{:.2f}', 'total_litros': '{:.1f}'})
                .background_gradient(subset=['km_l'], cmap='RdYlGn')
                .set_properties(**{'text-align': 'center'})
            )
        
        with col2:
            fig = px.bar(
                consumo_medio, x='km_l', y='placa', orientation='h',
                color='km_l', color_continuous_scale='RdYlGn',
                labels={'km_l': 'Consumo (km/L)', 'placa': 'Placa'},
                title='Eficiência por Veículo'
            )
            fig.update_layout(yaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.markdown("### 📊 Tendências Temporais")
        
        # Agregação por data
        df_ext_agg = df_ext.groupby('DATA').agg({
            'LITROS': 'sum',
            'CUSTO TOTAL': 'sum'
        }).reset_index()
        
        df_int_agg = df_int.groupby('DATA').agg({
            'QUANTIDADE DE LITROS': 'sum'
        }).reset_index().rename(columns={'QUANTIDADE DE LITROS': 'LITROS'})
        
        df_val_agg = df_val.groupby('DATA').agg({
            'VALOR': 'sum'
        }).reset_index()
        
        # Preço médio (interno)
        df_preco_medio = pd.merge(
            df_int_agg, df_val_agg, on='DATA', how='inner'
        )
        df_preco_medio['PRECO_MEDIO'] = df_preco_medio.apply(
            lambda x: x['VALOR'] / x['LITROS'] if x['LITROS'] > 0 else 0, axis=1
        )
        
        # Gráficos
        st.markdown("#### ⛽ Consumo por Data")
        fig1 = px.line(
            pd.concat([
                df_ext_agg.assign(Tipo='Externo'),
                df_int_agg.assign(Tipo='Interno')
            ]),
            x='DATA', y='LITROS', color='Tipo',
            labels={'LITROS': 'Litros consumidos', 'DATA': 'Data'},
            markers=True
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        st.markdown("#### 💵 Custo por Data")
        fig2 = px.line(
            pd.concat([
                df_ext_agg.assign(Tipo='Externo'),
                df_val_agg.assign(Tipo='Interno')
            ]),
            x='DATA', y='VALOR', color='Tipo',
            labels={'VALOR': 'Custo (R$)', 'DATA': 'Data'},
            markers=True
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("#### 📉 Preço Médio (Interno)")
        fig3 = px.line(
            df_preco_medio, x='DATA', y='PRECO_MEDIO',
            labels={'PRECO_MEDIO': 'Preço (R$/L)', 'DATA': 'Data'},
            markers=True
        )
        st.plotly_chart(fig3, use_container_width=True)

if __name__ == '__main__':
    main()
