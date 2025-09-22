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
# ---------------- Parte 2 ---------------- #
else:
    st.title("📘 Parte 2 — Plano de Negócio")
    sec_list = [
        ("1. Apresentação da empresa", 800, "Apresenta a empresa e o âmbito de atividade."),
        ("1.1. Historial e apresentação do promotor", 600, "Experiência, formação, resultados relevantes."),
        ("1.2. Historial e apresentação do promotor (equipa)", 600, "Restantes promotores/equipa e complementaridade."),
        ("1.3. Missão, visão e valores da empresa", 500, "Missão, visão a 3-5 anos e valores orientadores."),
        ("1.4. Objetivos do projeto", 800, "Metas SMART, prazos e indicadores."),
        ("1.5. O projeto, o serviço e a ideia", 900, "Descrição do serviço, proposta de valor e benefício para o cliente."),
        ("2.1. Contextualização da área geográfica envolvente", 700, "Localização, acesso, dados demográficos relevantes."),
        ("2.2. Concorrência", 700, "Principais concorrentes, comparação de preço/serviço, diferenciação."),
        ("2.3. Clientes potenciais", 700, "Segmentos-alvo, necessidades, sizing aproximado."),
        ("2.4. O preço", 400, "Estratégia de preço, descontos, política promocional."),
        ("2.5. Fornecedores", 500, "Principais fornecedores, prazos e condições."),
        ("2.6. Contexto económico, tecnológico e de inovação", 700, "Tendências, inovação aplicável e riscos macro."),
        ("2.7. Contexto político legal", 500, "Licenças, regulamentação, conformidade."),
        ("2.8. Contexto ambiental e ecológico", 500, "Sustentabilidade e impacto ambiental."),
        ("2.9. Posicionamento face à análise setorial", 600, "Síntese SWOT setorial e posicionamento."),
        ("3.1. Instalações", 500, "Local, área, adequação e custos fixos associados."),
        ("3.2. Equipamentos", 400, "Lista de principais equipamentos e capacidade."),
        ("3.3. Licenciamento", 400, "Licenças, prazos e entidades competentes."),
        ("3.4. Estratégia comercial e promoção", 700, "Canais, marketing digital, parcerias, cronograma de ações."),
        ("4.1. Recursos humanos", 600, "Organograma, funções e necessidades de contratação."),
        ("4.2. Formação", 400, "Plano de formação inicial e contínua."),
        ("4.3. Política de remunerações", 400, "Estrutura salarial e incentivos."),
        ("4.4. SHST", 400, "Procedimentos de Segurança, Higiene e Saúde no Trabalho."),
        ("4.5. Horário", 300, "Horário de funcionamento e turnos."),
        ("5. Análise SWOT do projeto", 600, "Forças, fraquezas, oportunidades e ameaças."),
        ("6.10. Viabilidade económica", 700, "Síntese da viabilidade com base nas tabelas."),
    ]

    usar_ia_p2 = st.checkbox("Ativar IA (botões por secção)", value=False)
    textos = {}
    for titulo, limite, instr in sec_list:
        colT, colB = st.columns([3,1])
        with colT:
            val = st.text_area(titulo, height=140, key=f"ta_{titulo}")
        with colB:
            if st.button("Gerar com IA", key=f"btn_{titulo}"):
                if usar_ia_p2 and ia_ok_bp():
                    try:
                        txt = ia_text_bp(titulo, instr, {"tema": titulo})
                        textos[titulo] = cortar(txt, limite)
                        st.session_state[f"ta_{titulo}"] = textos[titulo]
                        val = textos[titulo]
                    except Exception as e:
                        import traceback
                        st.error("Erro ao gerar texto com IA.")
                        st.code(traceback.format_exc())
                else:
                    st.warning("Ativa IA e define OPENAI_API_KEY nos Secrets.")
        textos[titulo] = st.session_state.get(f"ta_{titulo}", "")

    st.markdown("---")
    st.subheader("Pressupostos (alimentam as tabelas)")
    col1, col2, col3 = st.columns(3)
    with col1:
        anos = st.multiselect("Anos", [2025,2026,2027,2028], default=[2025,2026,2027], key="anos_p2")
        crescimento = st.number_input("Crescimento receitas (0-1)", 0.0, 1.0, 0.08, step=0.01, key="cres_p2")
        margem = st.number_input("Margem bruta alvo (0-1)", 0.0, 1.0, 0.55, step=0.01, key="margem_p2")
        fse = st.number_input("FSE % receitas (0-1)", 0.0, 1.0, 0.12, step=0.01, key="fse_p2")
    with col2:
        encargos = st.number_input("Encargos sociais (0-1)", 0.0, 1.0, 0.2375, step=0.0025, format="%.4f", key="enc_p2")
        aumento_sal = st.number_input("Aumento salarial (0-1)", 0.0, 1.0, 0.03, step=0.01, key="aum_p2")
        cap_proprios = st.number_input("Capitais próprios iniciais (€)", 0.0, 1e9, 8000.0, step=500.0, key="cap_p2")
    with col3:
        emp_mont = st.number_input("Empréstimo: montante (€)", 0.0, 1e9, 12000.0, step=500.0, key="mont_p2")
        emp_taxa = st.number_input("Empréstimo: taxa (0-1)", 0.0, 1.0, 0.06, step=0.005, format="%.3f", key="taxa_p2")
        emp_anos = st.number_input("Empréstimo: anos amortização", 1, 15, 3, step=1, key="anos_am_p2")

    st.markdown("Vida útil por tipo de ativo (anos)")
    colA, colB, colC, colD, colE = st.columns(5)
    with colA: dep_eq = st.number_input("Equipamento", 1, 15, 5, key="dep_eq")
    with colB: dep_inf = st.number_input("Informática", 1, 15, 3, key="dep_inf")
    with colC: dep_veh = st.number_input("Veículos", 1, 15, 4, key="dep_veh")
    with colD: dep_int = st.number_input("Intangíveis", 1, 15, 3, key="dep_int")
    with colE: dep_out = st.number_input("Outros", 1, 15, 4, key="dep_out")

    assum = {
        "crescimento_receitas": crescimento,
        "margem_bruta_target": margem,
        "fse_pct_receitas": fse,
        "encargos_sociais_pct": encargos,
        "aumento_salarios_pct": aumento_sal,
        "capitais_proprios_iniciais": cap_proprios,
        "dep_equipamento_anos": dep_eq,
        "dep_informatica_anos": dep_inf,
        "dep_veiculos_anos": dep_veh,
        "dep_intangiveis_anos": dep_int,
        "dep_outros_anos": dep_out,
        "emprestimo_montante": emp_mont,
        "emprestimo_taxa": emp_taxa,
        "emprestimo_anos": emp_anos,
    }

    st.session_state["anos"] = anos
    st.session_state["assum"] = assum

    st.markdown("---")
    st.subheader("Bases (podes ajustar)")
    vendas_df = st.data_editor(pd.DataFrame([
        {"designacao":"Serviço Base","preco":45.0,"qtd_mensal":120,"meses_y1":10},
    ], columns=["designacao","preco","qtd_mensal","meses_y1"]), num_rows="dynamic", key="vendas_bp")

    pessoal_df = st.data_editor(pd.DataFrame([
        {"funcao":"Técnico(a)","n":1,"venc_mensal":1100,"meses":12},
    ], columns=["funcao","n","venc_mensal","meses"]), num_rows="dynamic", key="pessoal_bp")

    investimento_df = st.data_editor(pd.DataFrame([
        {"tipo":"equipamento","descricao":"Equipamentos iniciais","valor":14000},
        {"tipo":"informatica","descricao":"Portátil e POS","valor":2000},
        {"tipo":"intangiveis","descricao":"Website e branding","valor":1500},
    ], columns=["tipo","descricao","valor"]), num_rows="dynamic", key="inv_bp")

    try:
        tabs_fin = calc_p2(anos, assum, vendas_df, pessoal_df, investimento_df)
    except Exception as e:
        import traceback
        st.error("Erro nos cálculos da Parte 2.")
        st.code(traceback.format_exc())
        st.stop()

    st.markdown("---")
    st.subheader("Resultados")
    for nome, df in tabs_fin.items():
        st.markdown(f"**{nome.upper()}**")
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Exportar DOCX + Excel")
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as w:
        for nome, df in tabs_fin.items():
            df.to_excel(w, index=False, sheet_name=nome[:31])
    xlsx_buf.seek(0)

    docx_buf = io.BytesIO()
    tmp_path = Path("tmp_p2.docx")
    try:
        build_docx_p2({}, tabs_fin, {k.replace("ta_",""):v for k,v in st.session_state.items() if k.startswith("ta_")}, tmp_path)
        docx_buf.write(tmp_path.read_bytes()); docx_buf.seek(0)
    finally:
        tmp_path.unlink(missing_ok=True)

    colD, colE = st.columns(2)
    with colD:
        st.download_button("⬇️ DOCX (Parte 2)", data=docx_buf, file_name="parte2_plano_negocio.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with colE:
        st.download_button("⬇️ Excel (Parte 2)", data=xlsx_buf, file_name="parte2_mapas.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

