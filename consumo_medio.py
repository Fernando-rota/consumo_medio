# Adicionar após a seção de consumo médio (tab3)

with tab4:
    # Novo gráfico de comparação direta
    st.markdown("### 🔄 Comparação Direta: Interno vs Externo")
    
    # Preparar dados comparativos
    df_comparativo = pd.DataFrame({
        'Tipo': ['Externo', 'Interno'],
        'Litros': [litros_ext, litros_int],
        'Custo': [valor_ext, valor_int],
        'Custo por Litro': [valor_ext/litros_ext if litros_ext > 0 else 0, 
                           valor_int/litros_int if litros_int > 0 else 0]
    })
    
    col1, col2 = st.columns(2)
    with col1:
        fig_comp_litros = px.pie(df_comparativo, values='Litros', names='Tipo',
                                title='Distribuição de Litros Consumidos',
                                color='Tipo', color_discrete_map={'Externo':'#1f77b4', 'Interno':'#2ca02c'})
        st.plotly_chart(fig_comp_litros, use_container_width=True)
    
    with col2:
        fig_comp_custo = px.bar(df_comparativo, x='Tipo', y='Custo por Litro',
                               title='Custo Médio por Litro (R$/L)',
                               color='Tipo', color_discrete_map={'Externo':'#1f77b4', 'Interno':'#2ca02c'},
                               text=df_comparativo['Custo por Litro'].apply(lambda x: f"R$ {x:.2f}"))
        st.plotly_chart(fig_comp_custo, use_container_width=True)

    # Análise de custo por km
    st.markdown("### 📉 Custo por Quilômetro Rodado")
    
    # Calcular km total por veículo (assumindo que o último registro tem a km atual)
    km_total = pd.concat([
        df_ext.groupby('PLACA')['KM ATUAL'].last(),
        df_int.groupby('PLACA')['KM ATUAL'].last()
    ]).groupby(level=0).sum().reset_index()
    
    if not km_total.empty:
        km_total.columns = ['PLACA', 'KM_TOTAL']
        
        # Calcular custo total por veículo
        custo_veiculo = pd.concat([
            df_ext.groupby('PLACA')['CUSTO TOTAL'].sum(),
            df_int.groupby('PLACA').apply(lambda x: df_val[df_val['PLACA'].isin(x['PLACA'])]['VALOR'].sum())
        ]).groupby(level=0).sum().reset_index()
        
        custo_veiculo.columns = ['PLACA', 'CUSTO_TOTAL']
        
        df_custo_km = pd.merge(km_total, custo_veiculo, on='PLACA')
        df_custo_km['CUSTO_KM'] = df_custo_km['CUSTO_TOTAL'] / df_custo_km['KM_TOTAL']
        df_custo_km = df_custo_km[df_custo_km['KM_TOTAL'] > 0].sort_values('CUSTO_KM')
        
        fig_custo_km = px.bar(df_custo_km, x='PLACA', y='CUSTO_KM',
                             title='Custo por Quilômetro (R$/km)',
                             labels={'CUSTO_KM': 'Custo por km (R$)', 'PLACA': 'Placa do Veículo'},
                             text=df_custo_km['CUSTO_KM'].apply(lambda x: f"R$ {x:.2f}"))
        st.plotly_chart(fig_custo_km, use_container_width=True)

# Adicionar nova aba para análises avançadas
tab5 = st.tabs(['🔍 Análises Avançadas'])[0]

with tab5:
    st.markdown("### 📅 Análise de Sazonalidade")
    
    # Agrupar por mês
    df_ext_mes = df_ext.groupby(df_ext['DATA'].dt.to_period('M')).agg({'LITROS':'sum', 'CUSTO TOTAL':'sum'}).reset_index()
    df_int_mes = df_int.groupby(df_int['DATA'].dt.to_period('M')).agg({'QUANTIDADE DE LITROS':'sum'}).reset_index()
    df_val_mes = df_val.groupby(df_val['DATA'].dt.to_period('M')).agg({'VALOR':'sum'}).reset_index()
    
    fig_sazonal = px.line(title='Consumo Mensal de Combustível')
    fig_sazonal.add_scatter(x=df_ext_mes['DATA'].astype(str), y=df_ext_mes['LITROS'], name='Externo')
    fig_sazonal.add_scatter(x=df_int_mes['DATA'].astype(str), y=df_int_mes['QUANTIDADE DE LITROS'], name='Interno')
    fig_sazonal.update_layout(xaxis_title='Mês', yaxis_title='Litros Consumidos')
    st.plotly_chart(fig_sazonal, use_container_width=True)
    
    st.markdown("### 🔎 Identificação de Outliers")
    
    # Boxplot de consumo por veículo
    fig_outliers = px.box(df_comb, x='placa', y='consumo', 
                         title='Distribuição de Consumo por Veículo (Km/L)',
                         labels={'placa': 'Placa', 'consumo': 'Km/L'})
    st.plotly_chart(fig_outliers, use_container_width=True)
