# resumo.py
import streamlit as st
import pandas as pd

def exibir_resumo(df_ext, df_int, df_val):
    st.subheader('📊 Resumo Geral do Período')

    litros_ext = df_ext['LITROS'].sum()
    valor_ext = df_ext['CUSTO TOTAL'].sum()
    preco_medio_ext = valor_ext / litros_ext if litros_ext > 0 else 0

    litros_int = df_int['QUANTIDADE DE LITROS'].sum()
    valor_int = df_val['VALOR'].sum()
    preco_medio_int = valor_int / litros_int if litros_int > 0 else 0

    total_litros = litros_ext + litros_int
    perc_ext = (litros_ext / total_litros * 100) if total_litros else 0
    perc_int = (litros_int / total_litros * 100) if total_litros else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('Litros Externo', f'{litros_ext:,.2f} L', delta=f'{perc_ext:.1f}%')
    c2.metric('Custo Externo', f'R$ {valor_ext:,.2f}')
    c3.metric('💵 Preço Médio Ext', f'R$ {preco_medio_ext:.2f}')
    c4.metric('Litros Interno', f'{litros_int:,.2f} L', delta=f'{perc_int:.1f}%')
    c5.metric('Custo Interno', f'R$ {valor_int:,.2f}')
    c6.metric('💰 Preço Médio Int', f'R$ {preco_medio_int:.2f}')

    with st.expander('📋 Detalhamento'): 
        col1, col2, col3 = st.columns(3)
        col1.metric('Abastecimentos Externos', f'{len(df_ext):,}')
        col2.metric('Abastecimentos Internos', f'{len(df_int):,}')
        col3.metric('Veículos Atendidos', f"{df_ext['PLACA'].nunique() + df_int['PLACA'].nunique()}")
