result = process_uploaded_files(uploaded_comb, uploaded_ext, uploaded_int, lim_ef=limite_eficiente, lim_norm=limite_normal)

if result is None:
    st.stop()

# Exemplo de uso
st.metric("Custo Total Interno", f"R$ {result['custo_int']:.2f}")
st.metric("Custo Total Externo", f"R$ {result['custo_ext']:.2f}")
st.dataframe(result["df_eff_final"])
