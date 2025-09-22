import io
from pathlib import Path
import streamlit as st
import pandas as pd
import yaml

from autofill_core import (
    calcular_tabelas as calc_p1,
    build_docx as build_docx_p1,
    ia_disponivel as ia_ok,
    gerar_texto_ia as ia_text,
)
from autofill_core_bp import (
    calcular_financeiros as calc_p2,
    build_docx_bp as build_docx_p2,
    gerar_texto_ia as ia_text_bp,
    ia_disponivel as ia_ok_bp,
    cortar,
)

st.set_page_config(page_title="IEFP — App Integrada", page_icon="🧩", layout="wide")
st.sidebar.title("🧩 IEFP — App Integrada")
page = st.sidebar.radio("Escolhe a área", ["Parte 1 — Formulário IEFP", "Parte 2 — Plano de Negócio"])

# ---------------- Parte 1 ---------------- #
if page.startswith("Parte 1"):
    st.title("📝 Parte 1 — Formulário IEFP (Autofill)")
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Identificação")
        titulo_proj   = st.text_input("Título do Projeto", "")
        designacao    = st.text_input("Designação Social", "")
        nif           = st.text_input("NIF (9 dígitos)", "")
        promotor      = st.text_input("Promotor", "")
        forma         = st.text_input("Forma Jurídica", "ENI")
        morada        = st.text_input("Morada", "")
        email         = st.text_input("Email", "")
        telefone      = st.text_input("Telefone", "")
        cae           = st.text_input("CAE", "")
    with colB:
        st.subheader("Configuração")
        anos = st.multiselect("Anos a considerar", [2025,2026,2027,2028], default=[2025,2026,2027])
        usar_ia = st.checkbox("Ativar IA para textos", value=False)

    st.markdown("---")
    st.subheader("Textos")
    col1, col2, col3 = st.columns(3)
    with col1:
        objetivos = st.text_area("Objetivos do Projeto", height=160, key="ta_obj")
        if st.button("Gerar com IA (Objetivos)"):
            if usar_ia and ia_ok():
                txt = ia_text("Objetivos do Projeto", "Inclui metas e KPIs.", {"identificacao":{"designacao_social":designacao}})
                st.session_state["ta_obj"] = txt
            else:
                st.warning("Ativa IA e define OPENAI_API_KEY nos Secrets.")
    with col2:
        mercado = st.text_area("Mercado", height=160, key="ta_mer")
        if st.button("Gerar com IA (Mercado)"):
            if usar_ia and ia_ok():
                txt = ia_text("Mercado", "Segmentos, necessidades, concorrência.", {"identificacao":{"designacao_social":designacao}})
                st.session_state["ta_mer"] = txt
            else:
                st.warning("Ativa IA e define OPENAI_API_KEY nos Secrets.")
    with col3:
        instalacoes = st.text_area("Instalações", height=160, key="ta_ins")
        if st.button("Gerar com IA (Instalações)"):
            if usar_ia and ia_ok():
                txt = ia_text("Instalações", "Localização, meios técnicos e equipa.", {"identificacao":{"designacao_social":designacao}})
                st.session_state["ta_ins"] = txt
            else:
                st.warning("Ativa IA e define OPENAI_API_KEY nos Secrets.")

    st.markdown("---")
    st.subheader("Vendas / Serviços")
    vendas_df = st.data_editor(pd.DataFrame([
        {"designacao":"Serviço A", "preco":50.0, "qtd_mensal":100, "meses_y1":10},
    ], columns=["designacao","preco","qtd_mensal","meses_y1"]), num_rows="dynamic", key="vendas_p1")

    st.subheader("Pessoal")
    pessoal_df = st.data_editor(pd.DataFrame([
        {"funcao":"Técnico(a)", "n":1, "venc_mensal":1100, "meses":12},
    ], columns=["funcao","n","venc_mensal","meses"]), num_rows="dynamic", key="pessoal_p1")

    st.subheader("Investimento")
    inv_df = st.data_editor(pd.DataFrame([
        {"tipo":"equipamento", "descricao":"Equipamentos", "valor":12000},
    ], columns=["tipo","descricao","valor"]), num_rows="dynamic", key="inv_p1")

    st.subheader("Financiamento")
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        emp_mont = st.number_input("Empréstimo: montante (€)", 0.0, 1e9, 12000.0, step=500.0)
    with colf2:
        emp_taxa = st.number_input("Taxa de juro (ano)", 0.0, 1.0, 0.06, step=0.005, format="%.3f")
    with colf3:
        emp_anos = st.number_input("Anos de amortização", 1, 15, 3, step=1)
    cap_proprios = st.number_input("Capitais próprios iniciais (€)", 0.0, 1e9, 8000.0, step=500.0)

    st.markdown("---")
    uploaded_yaml = st.file_uploader("Carregar YAML", type=["yaml","yml"])
    if uploaded_yaml is not None:
        try:
            data_loaded = yaml.safe_load(uploaded_yaml.read().decode("utf-8"))
            st.session_state["form_data_loaded_p1"] = data_loaded
            st.success("YAML carregado.")
        except Exception as e:
            import traceback
            st.error("Erro a ler YAML.")
            st.code(traceback.format_exc())
            st.stop()

    if st.button("Gerar (Parte 1)"):
        if "form_data_loaded_p1" in st.session_state:
            cfg = st.session_state["form_data_loaded_p1"]
        else:
            cfg = {
                "identificacao": {
                    "titulo_projeto": titulo_proj, "designacao_social": designacao, "nif": nif,
                    "promotor": promotor, "forma_juridica": forma, "morada": morada,
                    "email": email, "telefone": telefone, "cae": cae
                },
                "textos": {"objetivos_projeto": st.session_state.get("ta_obj", objetivos),
                           "mercado": st.session_state.get("ta_mer", mercado),
                           "instalacoes": st.session_state.get("ta_ins", instalacoes)},
                "limites_caracteres": {"objetivos_projeto": 2000, "mercado":1200, "instalacoes":1000},
                "anos": anos,
                "vendas": vendas_df.fillna(0).to_dict(orient="records"),
                "pessoal": pessoal_df.fillna(0).to_dict(orient="records"),
                "investimento": inv_df.fillna(0).to_dict(orient="records"),
                "capitais_proprios_iniciais": cap_proprios,
                "emprestimo": {"montante": emp_mont, "taxa_juros": emp_taxa, "amortizacao_anos": int(emp_anos)},
            }
        try:
            tabs = calc_p1(cfg)
        except Exception as e:
            import traceback
            st.error("Erro nos cálculos da Parte 1.")
            st.code(traceback.format_exc())
            st.stop()

        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as w:
            for nome, df in tabs.items():
                df.to_excel(w, index=False, sheet_name=nome[:31])
        xlsx_buf.seek(0)

        docx_buf = io.BytesIO()
        tmp_path = Path("tmp_p1.docx")
        try:
            build_docx_p1(cfg, tabs, tmp_path)
            docx_buf.write(tmp_path.read_bytes()); docx_buf.seek(0)
        finally:
            tmp_path.unlink(missing_ok=True)

        colD, colE = st.columns(2)
        with colD:
            st.download_button("⬇️ DOCX (Parte 1)", data=docx_buf, file_name="parte1_formulario.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with colE:
            st.download_button("⬇️ Excel (Parte 1)", data=xlsx_buf, file_name="parte1_mapas.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
