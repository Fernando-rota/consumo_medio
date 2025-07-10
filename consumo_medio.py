import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Abastecimento",
    layout="wide",
    page_icon="⛽"
)
st.title("⛽ Dashboard de Abastecimento de Veículos")

## ----------------------------
## 1. CLASSES DE PROCESSAMENTO
## ----------------------------

class DataProcessor:
    """Classe para processamento e transformação de dados"""
    
    @staticmethod
    def padronizar_colunas(df):
        """Padroniza nomes de colunas removendo espaços extras"""
        df.columns = df.columns.str.strip()
        return df

    @staticmethod
    def converter_tipos(df):
        """Converte colunas para tipos adequados"""
        type_map = {
            'PLACA': 'string',
            'KM ATUAL': 'float32',
            'LITROS': 'float32',
            'CUSTO TOTAL': 'float32'
        }
        
        for col, dtype in type_map.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') if 'float' in dtype else df[col].astype(dtype)
        return df

    @staticmethod
    def tratar_valores(df):
        """Trata valores problemáticos"""
        # Remover linhas com valores essenciais faltantes
        cols_essenciais = ['PLACA', 'DATA', 'TIPO']
        df = df.dropna(subset=[col for col in cols_essenciais if col in df.columns])
        
        # Substituir vírgulas por pontos em números
        num_cols = df.select_dtypes(include=['object']).columns
        for col in num_cols:
            if df[col].str.contains(',').any():
                df[col] = df[col].str.replace(',', '.').astype(float)
                
        return df

    @staticmethod
    def calcular_km_rodado(df):
        """Calcula a quilometragem rodada entre abastecimentos"""
        if not {'PLACA', 'DATA', 'KM ATUAL'}.issubset(df.columns):
            return df.assign(KM_RODADOS=None)
        
        df = df.sort_values(['PLACA', 'DATA'])
        df['KM_RODADOS'] = df.groupby('PLACA')['KM ATUAL'].diff().fillna(0)
        df['KM_RODADOS'] = df['KM_RODADOS'].clip(lower=0)
        return df

    @staticmethod
    def calcular_consumo(df):
        """Calcula consumo em km/litro"""
        if not {'KM_RODADOS', 'LITROS'}.issubset(df.columns):
            return df.assign(CONSUMO=None)
        
        df['CONSUMO'] = df['KM_RODADOS'] / df['LITROS']
        return df.replace([np.inf, -np.inf], np.nan)

## ----------------------------
## 2. GERENCIAMENTO DE ARQUIVOS
## ----------------------------

def carregar_arquivo(uploaded_file, tipo):
    """Carrega e valida um arquivo CSV"""
    if uploaded_file is None:
        return None
    
    try:
        df = pd.read_csv(
            uploaded_file,
            sep=";",
            encoding="utf-8",
            parse_dates=['DATA'],
            dayfirst=True
        )
        
        df = (df.pipe(DataProcessor.padronizar_colunas)
                .pipe(DataProcessor.tratar_valores)
                .pipe(DataProcessor.converter_tipos))
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar arquivo {tipo}: {str(e)}")
        return None

## ----------------------------
## 3. VISUALIZAÇÕES
## ----------------------------

class Visualizacoes:
    """Classe para geração de gráficos e visualizações"""
    
    @staticmethod
    def mostrar_resumo(df):
        """Exibe métricas resumidas"""
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total de Abastecimentos", len(df))
        with cols[1]:
            st.metric("Veículos Únicos", df['PLACA'].nunique())
        with cols[2]:
            st.metric("Litros Consumidos", f"{df['LITROS'].sum():,.1f}")
        with cols[3]:
            st.metric("Custo Total", f"R$ {df['CUSTO TOTAL'].sum():,.2f}")

    @staticmethod
    def plotar_consumo_por_veiculo(df):
        """Gráfico de consumo por veículo"""
        fig = px.bar(
            df.groupby('PLACA', as_index=False).agg({
                'LITROS': 'sum',
                'CUSTO TOTAL': 'sum'
            }).sort_values('LITROS', ascending=False),
            x='PLACA',
            y='LITROS',
            color='PLACA',
            title='Consumo por Veículo (Litros)',
            hover_data=['CUSTO TOTAL']
        )
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def plotar_tendencia_temporal(df):
        """Gráfico de tendência temporal"""
        df_mensal = df.resample('M', on='DATA').agg({
            'LITROS': 'sum',
            'CUSTO TOTAL': 'sum'
        }).reset_index()
        
        fig = px.line(
            df_mensal,
            x='DATA',
            y='LITROS',
            title='Consumo Mensal',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

## ----------------------------
## 4. LÓGICA PRINCIPAL
## ----------------------------

def main():
    # Configuração da barra lateral
    with st.sidebar:
        st.header("📤 Upload de Arquivos")
        arquivo_comb = st.file_uploader("Combustível (Financeiro)", type="csv")
        arquivo_ext = st.file_uploader("Abastecimento Externo", type="csv")
        arquivo_int = st.file_uploader("Abastecimento Interno", type="csv")
        
        st.header("⚙️ Configurações")
        data_inicio = st.date_input("Data Inicial", datetime.now().replace(day=1))
        data_fim = st.date_input("Data Final", datetime.now())

    # Processamento dos dados
    if all([arquivo_comb, arquivo_ext, arquivo_int]):
        with st.spinner("Processando dados..."):
            # Carregar e combinar dados
            df_ext = carregar_arquivo(arquivo_ext, "externo")
            df_int = carregar_arquivo(arquivo_int, "interno")
            
            if df_ext is None or df_int is None:
                st.error("Erro no carregamento dos arquivos")
                return
            
            # Processar dados internos (cálculo de KM rodados)
            df_int = DataProcessor.calcular_km_rodado(df_int)
            
            # Combinar dados externos e internos
            df = pd.concat([df_ext, df_int], ignore_index=True)
            
            # Filtrar por período
            df = df[(df['DATA'] >= pd.to_datetime(data_inicio)) & 
                   (df['DATA'] <= pd.to_datetime(data_fim))]
            
            # Calcular consumo
            df = DataProcessor.calcular_consumo(df)

        # Exibir resultados
        tab1, tab2, tab3 = st.tabs(["📊 Resumo", "📈 Análise", "🧾 Detalhes"])
        
        with tab1:
            Visualizacoes.mostrar_resumo(df)
            
        with tab2:
            Visualizacoes.plotar_consumo_por_veiculo(df)
            Visualizacoes.plotar_tendencia_temporal(df)
            
        with tab3:
            st.dataframe(
                df.sort_values('DATA', ascending=False),
                use_container_width=True,
                height=500
            )
    else:
        st.info("Por favor, faça upload de todos os arquivos para iniciar a análise.")

if __name__ == "__main__":
    main()
