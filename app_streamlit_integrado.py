import os
import io
from typing import List, Dict, Any
import streamlit as st
import pandas as pd

# =========================
#  ⚙️ CONFIG GERAL
# =========================
AI_MODEL = os.getenv("CBIZ_MODEL", "gpt-4o-mini")
LIMITE_CONTEXTO = 14_000

# =========================
#  🔐 OPENAI CLIENT (Chat Completions estável)
# =========================
def _get_api_key() -> str:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")

def _get_openai_client():
    key = _get_api_key()
    if not key:
        return None, "OPENAI_API_KEY não definida em st.secrets ou variável de ambiente."
    try:
        from openai import OpenAI
        return OpenAI(api_key=key), ""
    except Exception as e:
        return None, f"Biblioteca openai não disponível. Faz: pip install openai  [{e}]"

def chamar_ia_base(user: str, extra_system: str = "") -> str:
    """
    Usa apenas Chat Completions (messages) para evitar erros de 'fluxo de mensagens'.
    """
    client, err = _get_openai_client()
    if not client:
        return f"[IA inativa] {err}"

    system = (
        "És um assistente que escreve conteúdo técnico e claro para formulários de projetos de investimento "
        "e candidaturas a programas de financiamento. Utilizas sempre fontes oficiais e fidedignas de informação, atualizadas.\n"
        "Responde em Português de Portugal, estruturado, conciso e acionável.\n"
        "Se houver dados no contexto, usa-os rigorosamente; caso faltem, assume comedidamente e sinaliza suposições.\n"
    )
    if extra_system:
        system += "\n" + extra_system

    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"[ERRO AO CHAMAR OPENAI (chat.completions)]: {e}"

def chamar_ia_para_campo(label: str, instrucao: str, contexto: str) -> str:
    user = (
        f"# Tarefa\nPreenche o campo: **{label}**.\n\n"
        f"# Instrução específica\n{instrucao}\n\n"
        f"# Estilo\n- Português de Portugal\n- Tom profissional, direto; usar listas quando útil.\n\n"
        f"# Contexto\n{contexto}\n"
    )
    return chamar_ia_base(user)

# =========================
#  🧰 HELPERS (uploads/extração)
# =========================
def truncate(txt: str, limit: int = LIMITE_CONTEXTO) -> str:
    return txt if len(txt) <= limit else txt[:limit] + "\n\n[Contexto truncado…]"

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        return "\n".join(pages)
    except Exception as e:
        return f"[ERRO a ler PDF: {e}]"

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[ERRO a ler DOCX: {e}]"

def extract_text_from_xlsx(file_bytes: bytes) -> str:
    try:
        with io.BytesIO(file_bytes) as f:
            dfs = pd.read_excel(f, sheet_name=None)
        parts = []
        for name, df in dfs.items():
            parts.append(f"\n### Folha: {name}\n")
            parts.append(df.to_csv(index=False, sep=";", line_terminator="\n"))
        return "\n".join(parts)
    except Exception as e:
        return f"[ERRO a ler XLSX: {e}]"

def extract_text_from_upload(files) -> str:
    texts = []
    for uf in files or []:
        name = uf.name.lower()
        content = uf.read()
        if name.endswith(".pdf"):
            txt = extract_text_from_pdf(content)
        elif name.endswith(".docx"):
            txt = extract_text_from_docx(content)
        elif name.endswith(".xlsx"):
            txt = extract_text_from_xlsx(content)
        else:
            try:
                txt = content.decode("utf-8", errors="ignore")
            except Exception:
                txt = "[Formato não suportado]"
        texts.append(f"\n---\nFicheiro: {uf.name}\n{txt}")
    return "\n".join(texts).strip()

def build_context_from_fields(state: Dict[str, Any]) -> str:
    campos = {
        "Empresa": state.get("empresa_nome", ""),
        "Promotor": state.get("promotor_nome", ""),
        "Setor": state.get("setor", ""),
        "Localização": state.get("localizacao", ""),
        "Público-alvo": state.get("publico_alvo", ""),
        "Proposta de valor": state.get("proposta_valor", ""),
        "Resumo": state.get("resumo_geral", ""),
    }
    linhas = [f"- {k}: {v}" for k, v in campos.items() if str(v).strip()]
    return "Contexto (campos base):\n" + "\n".join(linhas) if linhas else ""

def build_context(modo_fontes: str, session: Dict[str, Any], uploaded_files) -> str:
    partes = []
    if modo_fontes in ("Campos anteriores", "Ambos"):
        app_ctx = build_context_from_fields(session)
        if app_ctx: partes.append(app_ctx)
    if modo_fontes in ("Documentos", "Ambos"):
        doc_txt = extract_text_from_upload(uploaded_files)
        if doc_txt: partes.append("Contexto (documentos):\n" + doc_txt)
    ctx = "\n\n".join(partes)
    return truncate(ctx, LIMITE_CONTEXTO)

# =========================
#  🧩 CAMPOS
# =========================
FIELDS_PART1: List[Dict[str, str]] = [
    {"label": "Nome da empresa", "key": "empresa_nome", "prompt": "Indica o nome oficial da entidade promotora."},
    {"label": "Nome do promotor", "key": "promotor_nome", "prompt": "Identifica o(s) promotor(es) do projeto e função."},
    {"label": "Setor de atividade", "key": "setor", "prompt": "Resume o setor de atividade (CAE) e especialização."},
    {"label": "Localização", "key": "localizacao", "prompt": "Indica a localização do projeto (concelho, região)."},
    {"label": "Público-alvo", "key": "publico_alvo", "prompt": "Define o público-alvo e segmentos relevantes."},
    {"label": "Proposta de valor", "key": "proposta_valor", "prompt": "Explica a proposta de valor e diferenciação."},
    {"label": "Resumo geral do projeto", "key": "resumo_geral", "prompt": "Apresenta um resumo executivo claro do projeto."},
]

FIELDS_PART2: List[Dict[str, str]] = [
    {"label": "1.1. Historial e apresentação do promotor", "key": "historial", "prompt": "Elabora o historial e a apresentação do promotor, incluindo experiência e resultados relevantes."},
    {"label": "1.3. Missão, visão e valores da empresa", "key": "missao", "prompt": "Define missão, visão e valores, alinhados com o projeto e o setor."},
    {"label": "1.4. Objetivos do projeto", "key": "objetivos", "prompt": "Estabelece objetivos específicos, mensuráveis, alcançáveis, relevantes e temporizados (SMART)."},
    {"label": "1.5. O projeto, o serviço e a ideia", "key": "projeto_servico", "prompt": "Descreve o projeto e os serviços/produtos, destacando a proposta de valor e inovação."},
    {"label": "2.1. Contextualização da área geográfica envolvente", "key": "area_geo", "prompt": "Caracteriza a área geográfica, dados demográficos e especificidades locais/regionais."},
    {"label": "2.2. Concorrência", "key": "concorrencia", "prompt": "Analisa concorrentes diretos e indiretos, posicionamento e barreiras à entrada."},
    {"label": "2.3. Clientes potenciais", "key": "clientes", "prompt": "Segmenta clientes potenciais, necessidades e critérios de decisão."},
    {"label": "2.4. O preço", "key": "preco", "prompt": "Define a estratégia de preços (cost-plus, benchmark, valor percebido) e política comercial."},
    {"label": "2.5. Fornecedores", "key": "fornecedores", "prompt": "Identifica fornecedores-chave, condições de fornecimento e riscos associados."},
    {"label": "2.6. Contexto económico, tecnológico e de inovação", "key": "contexto_eco", "prompt": "Apresenta tendências económicas, tecnológicas e de inovação relevantes."},
    {"label": "2.7. Contexto político legal", "key": "contexto_politico", "prompt": "Resume o enquadramento político-legal e regulamentar aplicável."},
    {"label": "2.8. Contexto ambiental e ecológico", "key": "contexto_amb", "prompt": "Avalia impactos ambientais, requisitos e práticas de sustentabilidade."},
    {"label": "2.9. Posicionamento face à análise setorial", "key": "posicionamento", "prompt": "Define o posicionamento competitivo com base na análise setorial."},
    {"label": "3.1. Instalações", "key": "instalacoes", "prompt": "Descreve instalações (local, área, adequação) e necessidades futuras."},
    {"label": "3.2. Equipamentos", "key": "equipamentos", "prompt": "Lista equipamentos essenciais, capacidades e justificações."},
    {"label": "3.3. Licenciamento", "key": "licenciamento", "prompt": "Indica licenças/autorização necessárias e estado do processo."},
    {"label": "3.4. Estratégia comercial e promoção", "key": "estrategia_comercial", "prompt": "Explica canais de venda, marketing, comunicação e métricas de sucesso."},
    {"label": "4.1. Recursos humanos", "key": "rh", "prompt": "Apresenta organograma, perfis e afetações por função/atividade."},
    {"label": "4.2. Formação", "key": "formacao", "prompt": "Identifica necessidades de formação e plano de capacitação."},
    {"label": "4.3. Política de remunerações", "key": "remuneracoes", "prompt": "Explica a política remuneratória e incentivos (fixo/variável)."},
    {"label": "4.4. SHST", "key": "shst", "prompt": "Indica medidas de Segurança, Higiene e Saúde no Trabalho."},
    {"label": "4.5. Horário", "key": "horario", "prompt": "Descreve o horário de funcionamento e escalas relevantes."},
    {"label": "Análise SWOT do projeto", "key": "swot", "prompt": "Elabora SWOT (forças, fraquezas, oportunidades, ameaças) com bullets claros."},
    {"label": "6.10. Viabilidade económica", "key": "viabilidade", "prompt": "Apresenta análise de viabilidade económica com pressupostos e indicadores-chave."},
]

# =========================
#  🧱 AÇÕES IA
# =========================
def gerar_para_campo(key_area: str, label: str, instrucao: str, modo_fontes_key: str, uploads_key: str):
    uploaded_files = st.session_state.get(uploads_key, [])
    contexto = build_context(
        modo_fontes=st.session_state.get(modo_fontes_key, "Campos anteriores"),
        session=st.session_state,
        uploaded_files=uploaded_files
    )
    texto_ia = chamar_ia_para_campo(label=label, instrucao=instrucao, contexto=contexto)
    st.session_state[key_area] = texto_ia
    st.rerun()

def expandir_campo(key_area: str, label: str, instrucao: str, modo_fontes_key: str, uploads_key: str):
    uploaded_files = st.session_state.get(uploads_key, [])
    contexto = build_context(
        modo_fontes=st.session_state.get(modo_fontes_key, "Campos anteriores"),
        session=st.session_state,
        uploaded_files=uploaded_files
    )
    novo = chamar_ia_para_campo(label=label, instrucao=instrucao, contexto=contexto)
    atual = st.session_state.get(key_area, "")
    st.session_state[key_area] = (atual + ("\n\n" if atual else "") + novo).strip()
    st.rerun()

# =========================
#  🧱 RENDERIZADORES
# =========================
def render_field_block(field: Dict[str, str], uploads_key: str, default_mode: str = "Campos anteriores"):
    label = field["label"]
    key_area = field["key"]
    modo_key = f"modo_{key_area}"

    c1, c2, c3 = st.columns([1, 0.55, 0.75])
    with c1:
        st.markdown(f"**{label}**")
    with c2:
        st.selectbox(
            "Fonte de dados",
            ["Campos anteriores", "Documentos", "Ambos"],
            key=modo_key,
            index=["Campos anteriores", "Documentos", "Ambos"].index(st.session_state.get(modo_key, default_mode)),
            label_visibility="collapsed",
        )
    with c3:
        b1, b2 = st.columns(2)
        with b1:
            st.button(
                "Gerar com IA",
                key=f"btn_{key_area}_gerar",
                on_click=gerar_para_campo,
                kwargs={
                    "key_area": key_area,
                    "label": label,
                    "instrucao": field["prompt"],
                    "modo_fontes_key": modo_key,
                    "uploads_key": uploads_key,
                },
                use_container_width=True,
            )
        with b2:
            st.button(
                "Expandir com IA",
                key=f"btn_{key_area}_expandir",
                on_click=expandir_campo,
                kwargs={
                    "key_area": key_area,
                    "label": label,
                    "instrucao": field["prompt"] + " Expande e aprofunda mantendo coerência com o texto existente.",
                    "modo_fontes_key": modo_key,
                    "uploads_key": uploads_key,
                },
                use_container_width=True,
            )

    st.text_area("", key=key_area, height=220, placeholder=f"Escreve ou clica em Gerar/Expandir — {label}")
    st.markdown("---")

# =========================
#  🖥️ UI — PARTE 1 + PARTE 2
# =========================
def render_parte1():
    st.subheader("Parte 1 — Dados Base do Projeto/Promotor")
    with st.expander("Ajuda", expanded=False):
        st.markdown("Estes campos alimentam o **contexto** para geração na Parte 2.")
    for f in FIELDS_PART1:
        st.text_input(f["label"], key=f["key"], placeholder="…")
    st.markdown("---")

def render_parte2():
    st.subheader("Parte 2 — Desenvolvimento do Dossier")
    st.caption("Podes carregar documentos para dar contexto à IA (PDF/DOCX/XLSX/TXT/MD).")

    # ⚠️ Instancia o uploader e **NÃO** escrevas em st.session_state["uploads_sec2"]
    uploads = st.file_uploader(
        "Carrega documentos de suporte",
        type=["pdf", "docx", "xlsx", "txt", "md"],
        accept_multiple_files=True,
        key="uploads_sec2"
    )
    # Se precisares localmente:
    _ = uploads or st.session_state.get("uploads_sec2", [])

    with st.expander("Preferências de geração", expanded=False):
        st.markdown("- **Fonte de dados** por campo: *Campos anteriores*, *Documentos* ou *Ambos*.")
        st.markdown("- **Gerar com IA** preenche o campo; **Expandir com IA** acrescenta ao texto existente.")

    for f in FIELDS_PART2:
        render_field_block(f, uploads_key="uploads_sec2")

# =========================
#  🚀 ENTRADA
# =========================
def main():
    st.set_page_config(page_title="IEFP — Formulário integrado", layout="wide")
    st.title("IEFP — Formulário integrado (CBIZ_DEV)")
    if not _get_api_key():
        st.warning("⚠️ Define a tua **OPENAI_API_KEY** em `.streamlit/secrets.toml` ou como variável de ambiente para ativar os botões de IA.")

    render_parte1()
    render_parte2()
    st.success("Pronto. Parte 2 corrigida: já não há escrita em `st.session_state['uploads_sec2']`.")

if __name__ == "__main__":
    main()
