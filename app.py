from datetime import datetime
import base64
import io
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import zipfile
import pandas as pd
import requests
import streamlit as st

try:
    from modulo_assistente_ia import renderizar_modulo_ia
except ImportError:
    renderizar_modulo_ia = None

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA & PERSISTÊNCIA POR HUB
# ==========================================
st.set_page_config(
    page_title="SPX - Control Tower Churn (Multi-HUB)",
    page_icon="🏎️",
    layout="wide",
)

HUBS_PREDEFINIDOS = [
    "LSP-93",
    "LSP-133",
    "LSP-01",
    "LSP-10",
    "LSP-50",
    "Outro HUB (Digitar Código)"
]

ENDERECOS_HUB = {
    "LSP-93": "Av. dos Estados, 7328 - Parque Jaçatuba - Santo André / SP",
    "LSP-133": "HUB SPX Logistics - LSP-133",
}

COLUNAS_HISTORICO = [
    "ID Registro",
    "HUB",
    "Driver ID",
    "Nome",
    "Telefone",
    "Veiculo",
    "Analista Responsável",
    "Tipo de Acionamento",
    "Data/Hora Acionamento",
    "Status",
    "Última Atualização",
    "Observação / Tratativa",
    "Data Reunião",
    "Horário",
    "Endereço HUB"
]


def sanitizar_hub(hub_code: str) -> str:
    limpo = re.sub(r"[^A-Za-z0-9\-]", "", str(hub_code).upper().strip())
    return limpo if limpo else "LSP-93"


def get_caminhos_hub(hub_code: str):
    h = sanitizar_hub(hub_code)
    pasta_local = Path("dados_hubs") / h
    pasta_local.mkdir(parents=True, exist_ok=True)
    return {
        "hub": h,
        "local_hist": str(pasta_local / f"historico_{h}.csv"),
        "local_base": str(pasta_local / f"base_drivers_{h}.csv.gz"),
        "repo_hist": f"dados_hubs/{h}/historico_{h}.csv",
        "repo_base": f"dados_hubs/{h}/base_drivers_{h}.csv.gz",
    }


# ==========================================
# MOTOR DE MEMÓRIA PERMANENTE (GITHUB SYNC + LOCAL)
# ==========================================
def github_config():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        return token, repo, branch
    except Exception:
        return "", "", "main"


def ler_arquivo_github(repo_path: str) -> bytes | None:
    token, repo, branch = github_config()
    if not token or not repo:
        return None
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}?ref={branch}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "content" in data:
                return base64.b64decode(data["content"])
    except Exception:
        pass
    return None


def gravar_arquivo_github(repo_path: str, content_bytes: bytes, commit_msg: str) -> bool:
    token, repo, branch = github_config()
    if not token or not repo:
        return False
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        sha = None
        get_resp = requests.get(f"{url}?ref={branch}", headers=headers, timeout=10)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")

        payload = {
            "message": commit_msg,
            "content": base64.b64encode(content_bytes).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=headers, json=payload, timeout=15)
        return put_resp.status_code in [200, 201]
    except Exception:
        return False


def carregar_historico_hub(hub_code: str) -> pd.DataFrame:
    caminhos = get_caminhos_hub(hub_code)
    cache_key = f"historico_cache_{caminhos['hub']}"

    # 1. Tenta buscar do GitHub (Memória Permanente) na primeira leitura da sessão
    if f"sync_hist_done_{caminhos['hub']}" not in st.session_state:
        bytes_gh = ler_arquivo_github(caminhos["repo_hist"])
        if bytes_gh:
            with open(caminhos["local_hist"], "wb") as f:
                f.write(bytes_gh)
        st.session_state[f"sync_hist_done_{caminhos['hub']}"] = True

    # 2. Lê do arquivo local sincronizado
    if os.path.exists(caminhos["local_hist"]):
        try:
            df = pd.read_csv(caminhos["local_hist"], dtype=str)
            for col in COLUNAS_HISTORICO:
                if col not in df.columns:
                    df[col] = caminhos["hub"] if col == "HUB" else ""
            df = df[COLUNAS_HISTORICO].fillna("")
            st.session_state[cache_key] = df
            return df
        except Exception:
            pass

    if cache_key in st.session_state:
        return st.session_state[cache_key]
    return pd.DataFrame(columns=COLUNAS_HISTORICO)


def salvar_historico_hub(hub_code: str, df: pd.DataFrame):
    caminhos = get_caminhos_hub(hub_code)
    for col in COLUNAS_HISTORICO:
        if col not in df.columns:
            df[col] = caminhos["hub"] if col == "HUB" else ""
    df_limpo = df[COLUNAS_HISTORICO].fillna("")
    csv_bytes = df_limpo.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    with open(caminhos["local_hist"], "wb") as f:
        f.write(csv_bytes)

    st.session_state[f"historico_cache_{caminhos['hub']}"] = df_limpo
    gravar_arquivo_github(
        caminhos["repo_hist"],
        csv_bytes,
        f"Atualiza historico HUB {caminhos['hub']} ({datetime.now().strftime('%d/%m/%Y %H:%M')})"
    )


def carregar_base_salva_hub(hub_code: str) -> pd.DataFrame | None:
    caminhos = get_caminhos_hub(hub_code)
    if f"sync_base_done_{caminhos['hub']}" not in st.session_state:
        bytes_gh = ler_arquivo_github(caminhos["repo_base"])
        if bytes_gh:
            with open(caminhos["local_base"], "wb") as f:
                f.write(bytes_gh)
        st.session_state[f"sync_base_done_{caminhos['hub']}"] = True

    if os.path.exists(caminhos["local_base"]):
        try:
            return pd.read_csv(caminhos["local_base"], compression="gzip", dtype=str)
        except Exception:
            pass
    return None


def salvar_base_hub(hub_code: str, df_analise: pd.DataFrame):
    caminhos = get_caminhos_hub(hub_code)
    buf = io.BytesIO()
    df_analise.to_csv(buf, index=False, compression="gzip", encoding="utf-8")
    gz_bytes = buf.getvalue()

    with open(caminhos["local_base"], "wb") as f:
        f.write(gz_bytes)

    gravar_arquivo_github(
        caminhos["repo_base"],
        gz_bytes,
        f"Salva base de drivers HUB {caminhos['hub']} ({datetime.now().strftime('%d/%m/%Y %H:%M')})"
    )


def registrar_novo_acionamento(
    hub_code: str,
    driver_id: str,
    nome: str,
    telefone: str,
    veiculo: str,
    analista: str,
    tipo_acionamento: str,
    status: str = "Driver Acionado",
    observacao: str = "",
    data_reuniao: str = "",
    horario: str = "",
    endereco_hub: str = ""
):
    hub_limpo = sanitizar_hub(hub_code)
    df_atual = carregar_historico_hub(hub_limpo)
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    id_reg = f"AC-{hub_limpo}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{driver_id}"

    novo = pd.DataFrame([{
        "ID Registro": id_reg,
        "HUB": hub_limpo,
        "Driver ID": str(driver_id),
        "Nome": str(nome),
        "Telefone": str(telefone),
        "Veiculo": str(veiculo),
        "Analista Responsável": str(analista),
        "Tipo de Acionamento": str(tipo_acionamento),
        "Data/Hora Acionamento": agora_str,
        "Status": str(status),
        "Última Atualização": agora_str,
        "Observação / Tratativa": str(observacao),
        "Data Reunião": str(data_reuniao),
        "Horário": str(horario),
        "Endereço HUB": str(endereco_hub)
    }])

    df_combinado = pd.concat([novo, df_atual], ignore_index=True)
    salvar_historico_hub(hub_limpo, df_combinado)


# Inicialização de variáveis de sessão
for key, default in [
    ("pagina_atual", "📊 Control Tower Churn"),
    ("filtro_kpi_status", "TODOS"),
    ("base_travada", False),
    ("analista_logado", ""),
    ("hub_autenticado", "")
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==========================================
# 2. ESTILIZAÇÃO VISUAL (SHOPEE FULL DARK NEON)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    
    :root {
        color-scheme: dark !important;
        --shopee-orange: #EE4D2D;
        --shopee-neon: #FF5722;
        --shopee-dark-bg: #121212;
        --shopee-card-bg: #1E1E1E;
    }

    html, body, .main, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--shopee-dark-bg) !important;
        color: #EEEEEE !important;
        font-family: 'Poppins', sans-serif;
    }

    /* Oculta o botão "Manage app" e a barra superior do Streamlit Cloud */
    [data-testid="manage-app-button"],
    .stAppDeployButton,
    button[kind="manageApp"],
    #MainMenu,
    [data-testid="stToolbar"],
    [data-testid="stHeaderActionElements"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Menu Lateral Dark */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161616 0%, #0A0A0A 100%) !important;
        border-right: 2px solid var(--shopee-orange) !important;
        box-shadow: 4px 0 20px rgba(238, 77, 45, 0.25) !important;
    }

    /* Força Full Dark em Inputs, Selectbox, DateInput e Pop-ups (Modais) */
    input, textarea, select,
    [data-baseweb="input"],
    [data-baseweb="base-input"],
    [data-baseweb="select"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stFileUploader"] section {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border-color: #333333 !important;
    }

    /* Menu suspenso (Dropdowns abertos) e Janela Modal (@st.dialog) */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    ul[role="listbox"],
    [data-testid="stDialog"] div[role="dialog"] {
        background-color: #181818 !important;
        color: #FFFFFF !important;
        border: 1px solid #EE4D2D !important;
    }

    li[role="option"]:hover {
        background-color: rgba(238, 77, 45, 0.25) !important;
    }

    /* Botões secundários (Filtros KPI, Reset, Trocar HUB) */
    button[kind="secondary"] {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        border: 1px solid #3A3A3A !important;
    }
    button[kind="secondary"]:hover {
        border-color: #EE4D2D !important;
        color: #EE4D2D !important;
    }

    /* Expanders e Alertas */
    [data-testid="stExpander"] {
        background-color: #1A1A1A !important;
        border: 1px solid #2E2E2E !important;
        border-radius: 10px !important;
    }

    /* Labels e textos */
    label, p, span, h1, h2, h3, h4 {
        color: #EEEEEE !important;
    }

    .sidebar-neon-card {
        background: #1E1E1E;
        border: 1px solid var(--shopee-orange);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
        box-shadow: 0 0 12px rgba(238, 77, 45, 0.35);
        text-align: center;
    }

    .sidebar-title {
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 1.05rem;
    }

    .sidebar-badge-prod {
        background: linear-gradient(90deg, #00C853 0%, #00E676 100%);
        color: #121212 !important;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 3px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 4px;
        box-shadow: 0 0 8px rgba(0, 230, 118, 0.4);
    }

    .metric-card-gerencial {
        background: #1E1E1E;
        border: 1px solid #2D2D2D;
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .metric-num {
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 4px;
    }

    .login-box {
        background: linear-gradient(135deg, #1A1A1A 0%, #260A02 100%);
        border: 2px solid #EE4D2D;
        border-radius: 18px;
        padding: 32px;
        box-shadow: 0 0 30px rgba(238, 77, 45, 0.35);
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)
# ==========================================
# 3. TELA DE LOGIN POR HUB (ISOLAMENTO DE OPERAÇÃO)
# ==========================================
if not st.session_state["hub_autenticado"]:
    _, col_login, _ = st.columns([1, 1.6, 1])
    with col_login:
        logo_login = (
            f'<img src="{img_logo_oficial}" style="width: 110px; height: 110px; object-fit: cover; border-radius: 50%; border: 3px solid #EE4D2D; box-shadow: 0 0 18px rgba(238,77,45,0.6); margin-bottom: 12px;">'
            if img_logo_oficial else '🏎️'
        )
        st.markdown(f"""
        <div class="login-box" style="text-align: center;">
            {logo_login}
            <h2 style="color: #FFF; font-weight: 800; margin: 0;">SPX CONTROL TOWER CHURN</h2>
            <p style="color: #EE4D2D; font-weight: 700; font-size: 0.95rem; margin-top: 4px;">Acesso Operacional Multi-HUB • Fleet Logistics</p>
            <p style="color: #BBB; font-size: 0.85rem;">Selecione seu HUB e informe seu nome para carregar a memória e o histórico exclusivo da sua unidade.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        hub_escolha = st.selectbox("🏢 Selecione o seu HUB:", HUBS_PREDEFINIDOS, index=0)
        if hub_escolha == "Outro HUB (Digitar Código)":
            hub_digitado = st.text_input("Digite o código do HUB:", placeholder="Ex: LSP-145")
            hub_final_login = sanitizar_hub(hub_digitado)
        else:
            hub_final_login = sanitizar_hub(hub_escolha)

        nome_analista_login = st.text_input(
            "👤 Nome do Analista Responsável:",
            value=st.session_state.get("analista_logado", ""),
            placeholder="Ex: Pedro Heleno"
        )

        # Senha opcional por HUB via st.secrets["SENHAS_HUBS"] se desejar restringir
        senhas_hubs = {}
        try:
            senhas_hubs = dict(st.secrets.get("SENHAS_HUBS", {}))
        except Exception:
            senhas_hubs = {}

        senha_digitada = ""
        if hub_final_login in senhas_hubs:
            senha_digitada = st.text_input("🔑 Senha de Acesso do HUB:", type="password")

        if st.button("🚀 ENTRAR NO PAINEL DO HUB", type="primary", use_container_width=True):
            if not hub_final_login:
                st.error("⚠️ Informe um código de HUB válido (ex: LSP-93).")
            elif not nome_analista_login.strip():
                st.error("⚠️ Informe o nome do Analista Responsável para continuar.")
            elif hub_final_login in senhas_hubs and senha_digitada != str(senhas_hubs[hub_final_login]):
                st.error("❌ Senha incorreta para este HUB.")
            else:
                st.session_state["hub_autenticado"] = hub_final_login
                st.session_state["analista_logado"] = nome_analista_login.strip()
                # Carrega automaticamente a última base salva desse HUB na memória permanente
                with st.spinner(f"Carregando memória e histórico do HUB {hub_final_login}..."):
                    df_base_salva = carregar_base_salva_hub(hub_final_login)
                    if df_base_salva is not None and not df_base_salva.empty:
                        st.session_state["df_analise_cache"] = df_base_salva
                        st.session_state["col_driver_id_name"] = "ID_LIMPO" if "ID_LIMPO" in df_base_salva.columns else df_base_salva.columns[0]
                        col_nm = next((c for c in df_base_salva.columns if any(k in c.lower() for k in ['driver name', 'driver_name', 'nome', 'name'])), df_base_salva.columns[1] if len(df_base_salva.columns) > 1 else "ID_LIMPO")
                        col_vh = next((c for c in df_base_salva.columns if c.lower() in ['vehicle type', 'tipo de veiculo', 'tipo veiculo', 'veiculo']), 'Vehicle Type')
                        st.session_state["col_driver_name_col"] = col_nm
                        st.session_state["col_veh_name"] = col_vh
                        st.session_state["base_travada"] = True
                st.rerun()

    st.stop()

# ==========================================
# 4. MENU LATERAL (COM HUB LOGADO & TROCA DE HUB)
# ==========================================
HUB_ATUAL = st.session_state["hub_autenticado"]

sidebar_img_html = (
    f'<img src="{img_logo_oficial}" style="width: 95px; height: 95px; object-fit: cover; border-radius: 50%; border: 2px solid #EE4D2D; box-shadow: 0 0 12px rgba(238,77,45,0.6); margin-bottom: 8px;" alt="Logo SPX">'
    if img_logo_oficial else '🏎️'
)

st.sidebar.markdown(f"""
<div class="sidebar-neon-card">
    <div style="text-align: center; margin-bottom: 6px;">{sidebar_img_html}</div>
    <div class="sidebar-title">🏎️ SPX FLEET CONTROL</div>
    <div class="sidebar-badge-prod">⚡ OFICIAL • {HUB_ATUAL}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"### 🏢 Unidade: **{HUB_ATUAL}**")
if st.sidebar.button("🔄 Trocar de HUB / Sair", use_container_width=True):
    for k in ["hub_autenticado", "df_analise_cache", "base_travada", "col_driver_id_name", "col_driver_name_col", "col_veh_name"]:
        st.session_state.pop(k, None)
    st.session_state["hub_autenticado"] = ""
    st.session_state["base_travada"] = False
    st.rerun()

st.sidebar.markdown("### 👤 Analista Responsável")
analista_input = st.sidebar.text_input(
    "Seu Nome (gravado nos acionamentos):",
    value=st.session_state["analista_logado"],
    placeholder="Ex: Pedro Heleno"
)
st.session_state["analista_logado"] = analista_input.strip()

st.sidebar.divider()

df_hist_sidebar = carregar_historico_hub(HUB_ATUAL)
qtd_hist = len(df_hist_sidebar)

opcoes_menu = [
    "📊 Control Tower Churn",
    f"📅 Reengajamento & Histórico ({qtd_hist})",
    "🤖 Assistente IA (SPX Copilot)"
]

idx_atual = 0
if "Reengajamento" in st.session_state["pagina_atual"]:
    idx_atual = 1
elif "Assistente" in st.session_state["pagina_atual"]:
    idx_atual = 2

opcao_menu = st.sidebar.radio(
    "Navegação do Sistema:",
    opcoes_menu,
    index=idx_atual
)
st.session_state["pagina_atual"] = opcao_menu

st.sidebar.divider()
if st.session_state.get("base_travada") and "df_analise_cache" in st.session_state:
    st.sidebar.success(f"🔒 Memória Ativa {HUB_ATUAL} ({len(st.session_state['df_analise_cache'])} drivers)")
    if st.sidebar.button("🗑️ Atualizar / Substituir Bases do HUB", use_container_width=True):
        for chave in ["df_analise_cache", "base_travada", "col_driver_id_name", "col_driver_name_col", "col_veh_name"]:
            st.session_state.pop(chave, None)
        st.rerun()

token_ok, _, _ = github_config()
if token_ok:
    st.sidebar.caption("☁️ Nuvem Sincronizada (Memória Permanente Ativa)")
else:
    st.sidebar.caption("💾 Modo Sessão Local (Configure GITHUB_TOKEN nos Secrets para backup contínuo)")

st.sidebar.caption(f"SPX Logistics - Fleet {HUB_ATUAL}\nCreated by Pedro Heleno")


# ==========================================
# 5. PÁGINA: DASHBOARD DE REENGAJAMENTO, HISTÓRICO & EXPORTAÇÃO
# ==========================================
def renderizar_pagina_reengajamento_nativa():
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Dashboard de Acionamentos & Histórico — {HUB_ATUAL}</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Histórico exclusivo do HUB <strong>{HUB_ATUAL}</strong>. Atualize retornos com gravação automática de data/hora e exporte relatórios.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico_hub(HUB_ATUAL)

    if df_hist.empty:
        st.warning(f"📭 Nenhum acionamento registrado para o HUB {HUB_ATUAL} até o momento.")
        st.info("👉 Vá até a aba **📊 Control Tower Churn**, selecione um motorista no campo **Acionar Motorista no WhatsApp** e clique em **Chamar no Whats (Registrar)**.")
        return

    # 1. KPIs DO DASHBOARD DE ACIONAMENTOS
    total_ac = len(df_hist)
    aguardando = len(df_hist[df_hist["Status"].isin(["Driver Acionado", "Aguardando Reunião"])])
    confirmados = len(df_hist[df_hist["Status"] == "Confirmado"])
    reintegrados = len(df_hist[df_hist["Status"] == "Reintegrado"])
    sem_retorno = len(df_hist[df_hist["Status"].isin(["Sem Resposta", "Sem Interesse", "Faltou", "Número Inválido"])])

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f'<div class="metric-card-gerencial"><div style="color:#AAA; font-size:0.78rem; font-weight:700;">📋 TOTAL ACIONADOS</div><div class="metric-num" style="color:#FFF;">{total_ac}</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="metric-card-gerencial"><div style="color:#FFD600; font-size:0.78rem; font-weight:700;">⏳ AGUARDANDO RETORNO</div><div class="metric-num" style="color:#FFD600;">{aguardando}</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="metric-card-gerencial"><div style="color:#00B0FF; font-size:0.78rem; font-weight:700;">👍 CONFIRMADOS</div><div class="metric-num" style="color:#00B0FF;">{confirmados}</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="metric-card-gerencial"><div style="color:#00E676; font-size:0.78rem; font-weight:700;">🚀 REINTEGRADOS</div><div class="metric-num" style="color:#00E676;">{reintegrados}</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div class="metric-card-gerencial"><div style="color:#FF5252; font-size:0.78rem; font-weight:700;">❌ SEM RETORNO / RECUSA</div><div class="metric-num" style="color:#FF5252;">{sem_retorno}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. GRÁFICOS GERENCIAIS
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**📊 Distribuição por Situação (Status)**")
        cont_status = df_hist["Status"].value_counts()
        st.bar_chart(cont_status, color="#EE4D2D")
    with g2:
        st.markdown("**👤 Produtividade por Analista Responsável**")
        cont_analista = df_hist["Analista Responsável"].replace("", "Não Informado").value_counts()
        st.bar_chart(cont_analista, color="#00E676")

    st.divider()

    # 3. FILTROS AVANÇADOS DO HISTÓRICO
    st.subheader(f"🔍 Filtrar e Editar Acionamentos ({HUB_ATUAL})")

    f1, f2, f3, f4 = st.columns([1.5, 1.5, 1.5, 1.5])
    with f1:
        busca_hist = st.text_input("Buscar Driver (Nome ou ID):", "")
    with f2:
        lista_analistas = ["TODOS"] + sorted(list(set(df_hist["Analista Responsável"].replace("", "Não Informado").unique())))
        filtro_analista = st.selectbox("Analista Responsável:", lista_analistas)
    with f3:
        lista_tipos = ["TODOS"] + sorted(list(set(df_hist["Tipo de Acionamento"].replace("", "Não Informado").unique())))
        filtro_tipo = st.selectbox("Tipo de Acionamento:", lista_tipos)
    with f4:
        filtro_status = st.multiselect(
            "Status:",
            options=["Driver Acionado", "Aguardando Reunião", "Sem Resposta", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse", "Número Inválido"],
            default=[]
        )

    df_filtrado = df_hist.copy()
    if busca_hist:
        t = busca_hist.lower()
        df_filtrado = df_filtrado[
            df_filtrado["Driver ID"].str.lower().str.contains(t) |
            df_filtrado["Nome"].str.lower().str.contains(t)
        ]
    if filtro_analista != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["Analista Responsável"].replace("", "Não Informado") == filtro_analista]
    if filtro_tipo != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["Tipo de Acionamento"].replace("", "Não Informado") == filtro_tipo]
    if filtro_status:
        df_filtrado = df_filtrado[df_filtrado["Status"].isin(filtro_status)]

    st.caption(f"Exibindo **{len(df_filtrado)}** de **{len(df_hist)}** registros. Dê um duplo clique na coluna **Status** ou **Observação / Tratativa** para editar:")

    df_editado = st.data_editor(
        df_filtrado,
        column_config={
            "ID Registro": None,
            "HUB": st.column_config.TextColumn("HUB", disabled=True),
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Motorista", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Veiculo": st.column_config.TextColumn("Veículo", disabled=True),
            "Analista Responsável": st.column_config.TextColumn("Analista", disabled=True),
            "Tipo de Acionamento": st.column_config.TextColumn("Tipo Acionamento", disabled=True),
            "Data/Hora Acionamento": st.column_config.TextColumn("Data/Hora Inicial", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status (Editar)",
                options=[
                    "Driver Acionado",
                    "Aguardando Reunião",
                    "Sem Resposta",
                    "Confirmado",
                    "Reintegrado",
                    "Faltou",
                    "Sem Interesse",
                    "Número Inválido"
                ],
                required=True
            ),
            "Última Atualização": st.column_config.TextColumn("Última Atualização", disabled=True),
            "Observação / Tratativa": st.column_config.TextColumn("Observação / Retorno (Editar)", width="large"),
            "Data Reunião": st.column_config.TextColumn("Data Reunião"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Endereço HUB": st.column_config.TextColumn("Endereço HUB")
        },
        hide_index=True,
        use_container_width=True,
        key=f"tabela_edicao_historico_{HUB_ATUAL}"
    )

    if st.button("💾 SALVAR ALTERAÇÕES NA MEMÓRIA PERMANENTE", type="primary"):
        agora_upd = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alteracoes = 0

        for _, row_ed in df_editado.iterrows():
            id_reg = row_ed["ID Registro"]
            mask = df_hist["ID Registro"] == id_reg
            if mask.any():
                idx_orig = df_hist[mask].index[0]
                if (
                    row_ed["Status"] != df_hist.loc[idx_orig, "Status"]
                    or row_ed["Observação / Tratativa"] != df_hist.loc[idx_orig, "Observação / Tratativa"]
                    or row_ed["Data Reunião"] != df_hist.loc[idx_orig, "Data Reunião"]
                    or row_ed["Horário"] != df_hist.loc[idx_orig, "Horário"]
                    or row_ed["Endereço HUB"] != df_hist.loc[idx_orig, "Endereço HUB"]
                ):
                    df_hist.loc[idx_orig, "Status"] = row_ed["Status"]
                    df_hist.loc[idx_orig, "Observação / Tratativa"] = row_ed["Observação / Tratativa"]
                    df_hist.loc[idx_orig, "Data Reunião"] = row_ed["Data Reunião"]
                    df_hist.loc[idx_orig, "Horário"] = row_ed["Horário"]
                    df_hist.loc[idx_orig, "Endereço HUB"] = row_ed["Endereço HUB"]
                    df_hist.loc[idx_orig, "Última Atualização"] = agora_upd
                    alteracoes += 1

        salvar_historico_hub(HUB_ATUAL, df_hist)
        if alteracoes > 0:
            st.toast(f"✅ {alteracoes} registro(s) salvos na memória do {HUB_ATUAL} às {agora_upd}!", icon="🕒")
            st.rerun()
        else:
            st.info("Nenhuma alteração foi feita na tabela.")

    st.divider()

    # 5. EXPORTAÇÃO DE RELATÓRIO & EXTENSÃO WHATSAPP
    st.subheader(f"📥 Exportação de Relatórios & Fila WhatsApp ({HUB_ATUAL})")

    c_exp1, c_exp2, c_exp3 = st.columns(3)

    df_rel_filtrado = df_filtrado.drop(columns=["ID Registro"], errors="ignore")
    csv_filtrado = df_rel_filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig")

    with c_exp1:
        st.download_button(
            label=f"📊 Exportar Visão Filtrada ({len(df_rel_filtrado)} reg.)",
            data=csv_filtrado,
            file_name=f"Relatorio_Filtrado_{HUB_ATUAL}_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

    df_rel_completo = df_hist.drop(columns=["ID Registro"], errors="ignore")
    csv_completo = df_rel_completo.to_csv(index=False, sep=";", encoding="utf-8-sig")

    with c_exp2:
        st.download_button(
            label=f"📑 Exportar Histórico Completo ({len(df_rel_completo)} reg.)",
            data=csv_completo,
            file_name=f"Relatorio_Completo_{HUB_ATUAL}_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    lista_ext = []
    for _, r in df_filtrado.iterrows():
        ph = str(r["Telefone"]).strip()
        if ph and len(ph) >= 10:
            msg = f"Olá {r['Nome']}! Aqui é {r['Analista Responsável']} da equipe SPX Logistics ({HUB_ATUAL}). Entramos em contato sobre: {r['Tipo de Acionamento']}. Podemos conversar?"
            lista_ext.append(f"{ph};{msg}")
    csv_ext = "Phone;Message\n" + "\n".join(lista_ext)

    with c_exp3:
        st.download_button(
            label=f"📲 Exportar p/ Extensão WhatsApp ({len(lista_ext)})",
            data=csv_ext,
            file_name=f"Fila_Extensao_Whats_{HUB_ATUAL}_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# Roteamento das abas secundárias
if "Reengajamento" in st.session_state["pagina_atual"]:
    renderizar_pagina_reengajamento_nativa()
    st.stop()

if "Assistente" in st.session_state["pagina_atual"]:
    if renderizar_modulo_ia:
        renderizar_modulo_ia()
    else:
        st.error("Módulo 'modulo_assistente_ia.py' não encontrado.")
    st.stop()


# ==========================================
# 6. JANELA MODAL (POP-UP) DE ACIONAMENTO WHATSAPP
# ==========================================
@st.dialog("📲 Registrar Acionamento & Chamar no WhatsApp")
def modal_acionar_driver(driver_info: dict):
    st.markdown(f"**Unidade:** `{HUB_ATUAL}` | **Motorista:** `{driver_info['Driver ID']}` — **{driver_info['Nome']}**")
    st.markdown(f"**Veículo:** {driver_info['Veiculo']} | **Inatividade:** {driver_info['Inatividade']}")
    st.divider()

    analista_atual = st.text_input(
        "👤 Analista Responsável pelo Acionamento:",
        value=st.session_state.get("analista_logado", ""),
        placeholder="Digite seu nome"
    )

    tipo_acionamento = st.selectbox(
        "📌 Tipo de Acionamento:",
        [
            "Convocação Treinamento Presencial",
            "Contato Preventivo (Motorista em Alerta)",
            "Resgate de Inativo (Churn > 20 dias)",
            "Alinhamento de Rotas / Disponibilidade",
            "Atualização Cadastral / Documentação"
        ]
    )

    endereco_padrao = ENDERECOS_HUB.get(HUB_ATUAL, f"HUB SPX Logistics - {HUB_ATUAL}")
    endereco_hub = st.text_input(
        "📍 Endereço do HUB (se aplicável):",
        value=endereco_padrao
    )

    c_d1, c_d2 = st.columns(2)
    with c_d1:
        dt_reuniao = st.date_input("Data Sugerida / Treinamento", value=datetime.now())
    with c_d2:
        hr_reuniao = st.time_input("Horário", value=datetime.now().time())

    obs_inicial = st.text_input(
        "📝 Observação Inicial (Opcional):",
        placeholder="Ex: Primeiro contato via WhatsApp..."
    )

    phone = str(driver_info["Telefone"]).strip()
    msg_whatsapp = (
        f"Olá {driver_info['Nome']}! Aqui é {analista_atual or 'da equipe'} da SPX Logistics ({HUB_ATUAL}). "
        f"Estamos entrando em contato referente a: *{tipo_acionamento}*.\n"
        f"📅 Data: {dt_reuniao.strftime('%d/%m/%Y')} às {hr_reuniao.strftime('%H:%M')}\n"
        f"📍 Local: {endereco_hub}\n"
        f"Podemos confirmar sua participação?"
    )
    url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg_whatsapp)}" if phone else ""

    if st.button("✅ GRAVAR NO HISTÓRICO E LIBERAR WHATSAPP", type="primary", use_container_width=True):
        if not analista_atual.strip():
            st.error("⚠️ Por favor, informe o nome do Analista Responsável antes de registrar!")
        else:
            st.session_state["analista_logado"] = analista_atual.strip()
            registrar_novo_acionamento(
                hub_code=HUB_ATUAL,
                driver_id=driver_info["Driver ID"],
                nome=driver_info["Nome"],
                telefone=phone,
                veiculo=driver_info["Veiculo"],
                analista=analista_atual.strip(),
                tipo_acionamento=tipo_acionamento,
                status="Driver Acionado",
                observacao=obs_inicial,
                data_reuniao=dt_reuniao.strftime("%d/%m/%Y"),
                horario=hr_reuniao.strftime("%H:%M"),
                endereco_hub=endereco_hub
            )
            st.success(f"Acionamento gravado na memória permanente do {HUB_ATUAL} às {datetime.now().strftime('%H:%M:%S')}!")
            if url_wa:
                st.link_button("🚀 ABRIR CONVERSA NO WHATSAPP AGORA", url_wa, type="primary", use_container_width=True)
            else:
                st.warning("Este motorista não possui número de telefone válido cadastrado.")


# ==========================================
# 7. PÁGINA PRINCIPAL: CONTROL TOWER CHURN
# ==========================================
def converter_id_cientifico(val):
    if pd.isna(val) or val == '' or val is None:
        return ''
    val_str = str(val).strip()
    try:
        val_float = float(val_str)
        val_int = int(round(val_float))
        return str(val_int)
    except Exception:
        return val_str


def formatar_whatsapp(val):
    if pd.isna(val):
        return ''
    num = re.sub(r'\D', '', str(val))
    if not num:
        return ''
    if not num.startswith('55') and len(num) in [10, 11]:
        num = '55' + num
    return num


def encontrar_colunas(cols):
    d_col = next((c for c in cols if any(k in c.lower() for k in ['driver id', 'driver_id', 'id driver'])), None)
    if not d_col:
        d_col = next((c for c in cols if 'driver' in c.lower() and 'name' not in c.lower()), None)
    dt_col = next((c for c in cols if any(k in c.lower() for k in ['delivery date', 'route date', 'task date', 'created', 'date'])), None)
    return d_col, dt_col


header_img_html = (
    f'<img src="{img_logo_oficial}" style="width: 105px; height: 105px; object-fit: cover; border-radius: 16px; border: 2px solid rgba(255,255,255,0.25); box-shadow: 0 0 18px rgba(0,0,0,0.6);" alt="Logo SPX">'
    if img_logo_oficial else '🏎️'
)

header_html = f'''
<div style="background: linear-gradient(135deg, #1A1A1A 0%, #2A0800 60%, #EE4D2D 100%); border-bottom: 3px solid #EE4D2D; padding: 18px 30px; border-radius: 16px; margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 0 20px rgba(238,77,45,0.3);">
    <div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="color: #FFF; font-size: 2.1rem; font-weight: 800; margin: 0;">SPX LOGISTICS - CONTROL TOWER CHURN</div>
            <span style="background: #00E676; color: #121212; font-weight: 800; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">OFICIAL • {HUB_ATUAL}</span>
        </div>
        <div style="color: #DDD; font-size: 0.95rem; margin-top: 4px;">Painel Gerencial de Monitoramento, Acionamento e Histórico — Unidade {HUB_ATUAL}</div>
    </div>
    <div>{header_img_html}</div>
</div>
'''
st.markdown(header_html, unsafe_allow_html=True)

# ÁREA DE IMPORTAÇÃO
if not st.session_state.get("base_travada"):
    st.info(f"📥 Nenhuma base carregada na memória do **{HUB_ATUAL}** no momento (ou você optou por atualizar). Faça o upload abaixo para salvar permanentemente neste HUB:")
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.subheader('1. Base de Motoristas')
        arquivo_drivers = st.file_uploader('Upload CSV motoristas', type=['csv'])

    with col_up2:
        st.subheader('2. Histórico de Rotas (ZIP ou CSV)')
        arquivos_rotas = st.file_uploader('Upload histórico rotas', type=['zip', 'csv'], accept_multiple_files=True)

    data_ref = st.date_input('Data de Referência', value=datetime.now())
    data_ref = datetime.combine(data_ref, datetime.min.time())

    st.divider()

    if st.button(f'🚀 GERAR ANÁLISE E SALVAR NA MEMÓRIA DO {HUB_ATUAL}', type="primary", use_container_width=True):
        if not arquivo_drivers or not arquivos_rotas:
            st.error('Por favor, faça o upload das bases.')
        else:
            with st.spinner(f'Processando e gravando dados na memória permanente do {HUB_ATUAL}...'):
                try:
                    df_drivers = pd.read_csv(arquivo_drivers, sep=';', dtype=str, encoding='utf-8')
                except Exception:
                    arquivo_drivers.seek(0)
                    df_drivers = pd.read_csv(arquivo_drivers, sep=None, dtype=str, engine='python')

                col_status = next((c for c in df_drivers.columns if 'status' in c.lower()), 'SPX Status')
                col_driver_id, _ = encontrar_colunas(df_drivers.columns.tolist())
                if not col_driver_id:
                    col_driver_id = df_drivers.columns[0]

                col_driver_name = next((c for c in df_drivers.columns if any(k in c.lower() for k in ['driver name', 'driver_name', 'nome', 'name'])), df_drivers.columns[1] if len(df_drivers.columns) > 1 else col_driver_id)
                col_phone = next((c for c in df_drivers.columns if any(k in c.lower() for k in ['phone', 'mobile', 'celular', 'whatsapp', 'contato', 'telefone'])), None)
                col_veh_name = next((c for c in df_drivers.columns if c.lower() in ['vehicle type', 'tipo de veiculo', 'tipo veiculo', 'veiculo']), 'Vehicle Type')

                df_ativos = df_drivers[df_drivers[col_status] == 'Active'].copy()
                df_ativos['ID_LIMPO'] = df_ativos[col_driver_id].apply(converter_id_cientifico)

                dict_ultima_rota = {}

                for up_file in arquivos_rotas:
                    if up_file.name.endswith('.zip'):
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                            tmp_file.write(up_file.getvalue())
                            tmp_path = tmp_file.name

                        with zipfile.ZipFile(tmp_path, 'r') as z:
                            for filename in z.namelist():
                                if filename.endswith('.csv'):
                                    with z.open(filename) as f:
                                        sample = pd.read_csv(f, nrows=5, sep=None, engine='python')
                                        d_col, dt_col = encontrar_colunas(sample.columns.tolist())
                                        if not d_col or not dt_col:
                                            continue
                                        f.seek(0)
                                        for chunk in pd.read_csv(f, chunksize=200000, usecols=[d_col, dt_col], dtype={d_col: str}, on_bad_lines='skip', sep=None, engine='python'):
                                            chunk['ID_LIMPO'] = chunk[d_col].apply(converter_id_cientifico)
                                            chunk[dt_col] = pd.to_datetime(chunk[dt_col], dayfirst=True, errors='coerce')
                                            chunk = chunk.dropna(subset=['ID_LIMPO', dt_col])
                                            max_dates = chunk.groupby('ID_LIMPO')[dt_col].max()
                                            for d_id, dt in max_dates.items():
                                                if d_id not in dict_ultima_rota or dt > dict_ultima_rota[d_id]:
                                                    dict_ultima_rota[d_id] = dt
                        os.remove(tmp_path)

                    elif up_file.name.endswith('.csv'):
                        df_chunk = pd.read_csv(up_file, dtype=str, on_bad_lines='skip', sep=None, engine='python')
                        d_col, dt_col = encontrar_colunas(df_chunk.columns.tolist())
                        if d_col and dt_col:
                            df_chunk['ID_LIMPO'] = df_chunk[d_col].apply(converter_id_cientifico)
                            df_chunk[dt_col] = pd.to_datetime(df_chunk[dt_col], dayfirst=True, errors='coerce')
                            df_chunk = df_chunk.dropna(subset=['ID_LIMPO', dt_col])
                            max_dates = df_chunk.groupby('ID_LIMPO')[dt_col].max()
                            for d_id, dt in max_dates.items():
                                if d_id not in dict_ultima_rota or dt > dict_ultima_rota[d_id]:
                                    dict_ultima_rota[d_id] = dt

                df_rotas = pd.DataFrame(list(dict_ultima_rota.items()), columns=['ID_LIMPO', 'Ultima_Rota']).drop_duplicates(subset=['ID_LIMPO']).reset_index(drop=True)

                df_analise = df_ativos.merge(df_rotas, on='ID_LIMPO', how='left')
                df_analise['Dias_Sem_Rota'] = (data_ref - df_analise['Ultima_Rota']).dt.days

                def classificar(row):
                    if pd.isna(row['Ultima_Rota']):
                        return 'Sem Rotas'
                    dias = row['Dias_Sem_Rota']
                    if dias <= 7:
                        return 'Ativo'
                    elif dias <= 20:
                        return 'Alerta'
                    else:
                        return 'Churn'

                df_analise['Status_Inatividade'] = df_analise.apply(classificar, axis=1)
                df_analise['Dias_Sem_AT_Fmt'] = df_analise['Dias_Sem_Rota'].apply(lambda d: f"{int(d)} dias sem AT" if pd.notna(d) else "Sem Histórico de AT")
                df_analise['Telefone_Limpo'] = df_analise[col_phone].apply(formatar_whatsapp) if col_phone else ''
                df_analise = df_analise.sort_values(by='Dias_Sem_Rota', ascending=False, na_position='first')

                # Salva na memória permanente deste HUB
                salvar_base_hub(HUB_ATUAL, df_analise)

                st.session_state["df_analise_cache"] = df_analise
                st.session_state["col_driver_id_name"] = col_driver_id
                st.session_state["col_driver_name_col"] = col_driver_name
                st.session_state["col_veh_name"] = col_veh_name
                st.session_state["base_travada"] = True
                st.rerun()

# EXIBIÇÃO DO PAINEL GERENCIAL
if st.session_state.get("base_travada") and "df_analise_cache" in st.session_state:
    df_analise = st.session_state["df_analise_cache"]
    col_driver_id = st.session_state["col_driver_id_name"]
    col_driver_name = st.session_state.get("col_driver_name_col", "Driver Name")
    col_veh_name = st.session_state["col_veh_name"]

    # CARDS GERENCIAIS KPI
    total = len(df_analise)
    c_op = len(df_analise[df_analise['Status_Inatividade'] == 'Ativo'])
    c_alt = len(df_analise[df_analise['Status_Inatividade'] == 'Alerta'])
    c_churn = len(df_analise[df_analise['Status_Inatividade'] == 'Churn'])
    c_sem = len(df_analise[df_analise['Status_Inatividade'] == 'Sem Rotas'])

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#AAA; font-size:0.8rem; font-weight:700;">🔍 TODOS OS DRIVERS</div><div class="metric-num" style="color:#FFF;">{total:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Todos", key="f_todos", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "TODOS"
            st.rerun()

    with k2:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#00E676; font-size:0.8rem; font-weight:700;">🟢 OPERACIONAIS</div><div class="metric-num" style="color:#00E676;">{c_op:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Ativos", key="f_op", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Ativo"
            st.rerun()

    with k3:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#FFD600; font-size:0.8rem; font-weight:700;">🟡 EM ALERTA</div><div class="metric-num" style="color:#FFD600;">{c_alt:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Alerta", key="f_alt", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Alerta"
            st.rerun()

    with k4:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#FF5252; font-size:0.8rem; font-weight:700;">🔴 INATIVOS (CHURN)</div><div class="metric-num" style="color:#FF5252;">{c_churn:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Churn", key="f_churn", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Churn"
            st.rerun()

    with k5:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#B0BEC5; font-size:0.8rem; font-weight:700;">⚪ SEM HISTÓRICO</div><div class="metric-num" style="color:#B0BEC5;">{c_sem:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Sem Rotas", key="f_sem", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Sem Rotas"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # FILTROS DE BUSCA E TIPO DE VEÍCULO
    f_col1, f_col2, f_col3 = st.columns([2, 1.5, 1])
    with f_col1:
        busca_texto = st.text_input("🔍 Busca Rápida (Nome ou ID)", "")
    with f_col2:
        veiculos_unicos = ["TODOS"] + sorted(list(set(df_analise[col_veh_name].dropna().astype(str).str.strip().unique()))) if col_veh_name in df_analise.columns else ["TODOS"]
        veh_selecionado = st.selectbox("🚗 Tipo de Veículo", veiculos_unicos)
    with f_col3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Resetar Filtros", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "TODOS"
            st.rerun()

    df_exibir = df_analise.copy()
    if st.session_state["filtro_kpi_status"] != "TODOS":
        df_exibir = df_exibir[df_exibir["Status_Inatividade"] == st.session_state["filtro_kpi_status"]]

    if veh_selecionado != "TODOS" and col_veh_name in df_exibir.columns:
        df_exibir = df_exibir[df_exibir[col_veh_name] == veh_selecionado]

    if busca_texto:
        termo = busca_texto.lower()
        df_exibir = df_exibir[
            df_exibir[col_driver_id].astype(str).str.lower().str.contains(termo) |
            df_exibir[col_driver_name].astype(str).str.lower().str.contains(termo)
        ]

    df_hist_atual = carregar_historico_hub(HUB_ATUAL)
    mapa_status_historico = {}
    if not df_hist_atual.empty:
        for _, rh in df_hist_atual.iterrows():
            d_id_h = str(rh["Driver ID"]).strip()
            if d_id_h not in mapa_status_historico:
                mapa_status_historico[d_id_h] = f"{rh['Status']} ({rh['Analista Responsável']} - {rh['Data/Hora Acionamento']})"

    # SELETOR RÁPIDO PARA ABRIR POP-UP DE ACIONAMENTO
    st.markdown(f"### 📲 Acionar Motorista no WhatsApp — {HUB_ATUAL}")
    st.caption("Escolha o motorista abaixo e clique no botão laranja. O acionamento será salvo permanentemente no histórico do seu HUB:")

    opcoes_drivers_popup = [
        f"{r[col_driver_id]} - {r[col_driver_name]} ({r.get(col_veh_name, 'N/I')}) | {r['Dias_Sem_AT_Fmt']}"
        for _, r in df_exibir.head(300).iterrows()
    ]

    col_pop1, col_pop2 = st.columns([3, 1.3])
    with col_pop1:
        driver_escolhido_str = st.selectbox(
            "Selecione o motorista para chamar:",
            options=opcoes_drivers_popup,
            label_visibility="collapsed"
        )
    with col_pop2:
        if st.button("📲 CHAMAR NO WHATS (REGISTRAR)", type="primary", use_container_width=True):
            if driver_escolhido_str:
                id_sel = driver_escolhido_str.split(" - ")[0].strip()
                row_sel = df_exibir[df_exibir[col_driver_id].astype(str).str.strip() == id_sel].iloc[0]
                modal_acionar_driver({
                    "Driver ID": str(row_sel[col_driver_id]),
                    "Nome": str(row_sel[col_driver_name]),
                    "Veiculo": str(row_sel.get(col_veh_name, "N/I")),
                    "Inatividade": str(row_sel["Dias_Sem_AT_Fmt"]),
                    "Telefone": str(row_sel["Telefone_Limpo"])
                })

    if not df_hist_atual.empty:
        with st.expander(f"📋 Últimos Acionamentos Registrados no {HUB_ATUAL} ({len(df_hist_atual)} no total)", expanded=True):
            st.dataframe(
                df_hist_atual[["Driver ID", "Nome", "Analista Responsável", "Tipo de Acionamento", "Status", "Data/Hora Acionamento", "Última Atualização"]].head(5),
                hide_index=True,
                use_container_width=True
            )

    st.divider()

    # TABELA GERENCIAL DE CONSULTA
    st.markdown(f"### 📋 Tabela Gerencial {HUB_ATUAL} (`{len(df_exibir)} motoristas`)")

    df_tabela = pd.DataFrame()
    df_tabela["Driver ID"] = df_exibir[col_driver_id].astype(str)
    df_tabela["Nome do Motorista"] = df_exibir[col_driver_name].astype(str)
    df_tabela["Veículo"] = df_exibir[col_veh_name].astype(str) if col_veh_name in df_exibir.columns else "N/I"
    df_tabela["Inatividade"] = df_exibir["Dias_Sem_AT_Fmt"]
    df_tabela["Status Frota"] = df_exibir["Status_Inatividade"]
    df_tabela["Histórico / Último Acionamento"] = df_tabela["Driver ID"].apply(
        lambda x: mapa_status_historico.get(str(x).strip(), "Não Acionado")
    )
    df_tabela["Telefone"] = df_exibir["Telefone_Limpo"]

    st.dataframe(
        df_tabela,
        hide_index=True,
        use_container_width=True
    )

img_footer_html = f'<img src="{img_shopito_entregador}" style="height: 55px; border-radius: 8px;">' if img_shopito_entregador else ''
footer_html = f'''
<div style="margin-top: 45px; padding: 18px 25px; background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%); border: 1px solid rgba(238, 77, 45, 0.3); border-radius: 14px; display: flex; align-items: center; justify-content: space-between;">
    <div style="display:flex; align-items:center; gap: 12px;">{img_footer_html} <span style="color:#FFF; font-weight:700;">SPX Logistics • {HUB_ATUAL}</span></div>
    <div style="color: #AAA; font-size: 0.95rem; text-align: center;">Created by <strong style="color: #EE4D2D;">Pedro Heleno</strong><br>Fleet - LSP-93</div>
</div>
'''
st.markdown(footer_html, unsafe_allow_html=True)
