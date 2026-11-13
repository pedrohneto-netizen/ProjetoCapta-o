from datetime import datetime
import base64
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import zipfile
import pandas as pd
import streamlit as st

try:
    from modulo_assistente_ia import renderizar_modulo_ia
except ImportError:
    renderizar_modulo_ia = None

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA & PERSISTÊNCIA
# ==========================================
st.set_page_config(
    page_title="[DEV] SPX - Control Tower Churn",
    page_icon="🧪",
    layout="wide",
)

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

COLUNAS_HISTORICO = [
    "ID Registro",
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


def carregar_historico() -> pd.DataFrame:
    """Lê o CSV de histórico e garante sincronia com o estado da sessão."""
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            df = pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
            for col in COLUNAS_HISTORICO:
                if col not in df.columns:
                    df[col] = ""
            df = df[COLUNAS_HISTORICO].fillna("")
            st.session_state["historico_cache"] = df
            return df
        except Exception:
            pass
    if "historico_cache" in st.session_state:
        return st.session_state["historico_cache"]
    return pd.DataFrame(columns=COLUNAS_HISTORICO)


def salvar_historico(df: pd.DataFrame):
    """Salva o histórico no CSV e atualiza o cache da sessão."""
    for col in COLUNAS_HISTORICO:
        if col not in df.columns:
            df[col] = ""
    df_limpo = df[COLUNAS_HISTORICO].fillna("")
    df_limpo.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")
    st.session_state["historico_cache"] = df_limpo


def registrar_novo_acionamento(
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
    df_atual = carregar_historico()
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    id_reg = f"AC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{driver_id}"

    novo = pd.DataFrame([{
        "ID Registro": id_reg,
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
    salvar_historico(df_combinado)


# Inicialização de variáveis de sessão
for key, default in [
    ("pagina_atual", "📊 Control Tower Churn"),
    ("filtro_kpi_status", "TODOS"),
    ("base_travada", False),
    ("analista_logado", "")
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==========================================
# 2. ESTILIZAÇÃO VISUAL (SHOPEE DARK NEON)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    
    :root {
        --shopee-orange: #EE4D2D;
        --shopee-neon: #FF5722;
        --shopee-dark-bg: #121212;
    }

    body, .main, .stApp {
        background-color: var(--shopee-dark-bg) !important;
        color: #EEEEEE !important;
        font-family: 'Poppins', sans-serif;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161616 0%, #0A0A0A 100%) !important;
        border-right: 2px solid var(--shopee-orange) !important;
        box-shadow: 4px 0 20px rgba(238, 77, 45, 0.25) !important;
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

    .sidebar-logo {
        max-height: 75px;
        width: auto;
        margin-bottom: 6px;
        filter: drop-shadow(0 0 8px rgba(238, 77, 45, 0.5));
    }

    .sidebar-title {
        color: #FFFFFF;
        font-weight: 800;
        font-size: 1.05rem;
    }

    .sidebar-badge {
        background: linear-gradient(90deg, #EE4D2D 0%, #FF5722 100%);
        color: white;
        font-size: 0.7rem;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 4px;
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
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=10, ttl=3600)
def get_base64_image_cached(image_filename):
    possible_paths = [
        Path(image_filename),
        Path(r'C:\Users\SPXBR30056\Desktop\Projeto Captação Churn') / image_filename
    ]
    for path in possible_paths:
        if path.exists():
            ext = path.suffix.lower().replace('.', '')
            mime = 'gif' if ext == 'gif' else ('png' if ext == 'png' else 'jpeg')
            with open(path, 'rb') as img_file:
                encoded = base64.b64encode(img_file.read()).decode('utf-8')
                return f"data:image/{mime};base64,{encoded}"
    return ''


img_logo_oficial = get_base64_image_cached('Formula 1_2_2.jpg') or get_base64_image_cached('Formula 1_2.jpg')
img_shopito_entregador = get_base64_image_cached('GIF-21-entregador.jpg')

# ==========================================
# 3. MENU LATERAL & IDENTIFICAÇÃO DO ANALISTA
# ==========================================
sidebar_img_html = f'<img src="{img_logo_oficial}" class="sidebar-logo" alt="Logo SPX">' if img_logo_oficial else '🏎️'

st.sidebar.markdown(f"""
<div class="sidebar-neon-card">
    <div style="text-align: center; margin-bottom: 6px;">{sidebar_img_html}</div>
    <div class="sidebar-title">🏎️ SPX FLEET CONTROL</div>
    <div class="sidebar-badge">🧪 AMBIENTE DEV / STAGING</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 👤 Analista Responsável")
analista_input = st.sidebar.text_input(
    "Seu Nome (gravado nos acionamentos):",
    value=st.session_state["analista_logado"],
    placeholder="Ex: Pedro Heleno"
)
st.session_state["analista_logado"] = analista_input.strip()

if not st.session_state["analista_logado"]:
    st.sidebar.warning("⚠️ Informe seu nome acima antes de acionar.")

st.sidebar.divider()

df_hist_sidebar = carregar_historico()
qtd_hist = len(df_hist_sidebar)

opcoes_menu = [
    "📊 Control Tower Churn",
    f"📅 Reengajamento & Histórico ({qtd_hist})",
    "🤖 Assistente IA (SPX Copilot)"
]

# Mapeia índice mantendo a seleção mesmo quando o contador entre parênteses muda
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
    st.sidebar.success(f"🔒 Base Carregada ({len(st.session_state['df_analise_cache'])} drivers)")
    if st.sidebar.button("🗑️ Limpar / Trocar Bases Importadas", use_container_width=True):
        for chave in ["df_analise_cache", "base_travada", "col_driver_id_name", "col_driver_name_col", "col_veh_name"]:
            st.session_state.pop(chave, None)
        st.rerun()

st.sidebar.divider()
st.sidebar.caption("SPX Logistics - Fleet LSP93\nAutor: Pedro Heleno")


# ==========================================
# 4. PÁGINA: DASHBOARD DE REENGAJAMENTO, HISTÓRICO & EXPORTAÇÃO
# ==========================================
def renderizar_pagina_reengajamento_nativa():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Dashboard de Acionamentos, Histórico & Exportação</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Acompanhe todos os motoristas acionados, filtre por analista/status, atualize retornos (com data/hora automática) e exporte relatórios.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.warning("📭 Nenhum acionamento registrado até o momento.")
        st.info("👉 Vá até a aba **📊 Control Tower Churn**, selecione um motorista no campo **Acionar Motorista no WhatsApp** e clique em **Chamar no Whats (Registrar)** para criar o primeiro registro.")
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

    # 2. GRÁFICOS GERENCIAIS (POR STATUS E POR ANALISTA)
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
    st.subheader("🔍 Filtrar e Editar Acionamentos Arquivados")

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

    # 4. TABELA EDITÁVEL COM GRAVAÇÃO AUTOMÁTICA DE DATA/HORA
    df_editado = st.data_editor(
        df_filtrado,
        column_config={
            "ID Registro": None,
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
        key="tabela_edicao_historico_nativa"
    )

    if st.button("💾 SALVAR ALTERAÇÕES (CARIMBA DATA/HORA AUTOMATICAMENTE)", type="primary"):
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

        salvar_historico(df_hist)
        if alteracoes > 0:
            st.toast(f"✅ {alteracoes} registro(s) atualizado(s) às {agora_upd}!", icon="🕒")
            st.rerun()
        else:
            st.info("Nenhuma alteração foi feita na tabela.")

    st.divider()

    # 5. EXPORTAÇÃO DE RELATÓRIO (FILTRADO OU COMPLETO) & EXTENSÃO WHATS
    st.subheader("📥 Exportação de Relatórios & Fila WhatsApp")

    c_exp1, c_exp2, c_exp3 = st.columns(3)

    # Relatório dos dados filtrados na tela
    df_rel_filtrado = df_filtrado.drop(columns=["ID Registro"], errors="ignore")
    csv_filtrado = df_rel_filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig")

    with c_exp1:
        st.download_button(
            label=f"📊 Exportar Visão Filtrada ({len(df_rel_filtrado)} reg.)",
            data=csv_filtrado,
            file_name=f"Relatorio_Filtrado_LSP93_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

    # Relatório Completo
    df_rel_completo = df_hist.drop(columns=["ID Registro"], errors="ignore")
    csv_completo = df_rel_completo.to_csv(index=False, sep=";", encoding="utf-8-sig")

    with c_exp2:
        st.download_button(
            label=f"📑 Exportar Histórico Completo ({len(df_rel_completo)} reg.)",
            data=csv_completo,
            file_name=f"Relatorio_Completo_LSP93_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # CSV para Extensão Chrome
    lista_ext = []
    for _, r in df_filtrado.iterrows():
        ph = str(r["Telefone"]).strip()
        if ph and len(ph) >= 10:
            msg = f"Olá {r['Nome']}! Aqui é {r['Analista Responsável']} da equipe SPX Logistics (LSP93). Entramos em contato sobre: {r['Tipo de Acionamento']}. Podemos conversar?"
            lista_ext.append(f"{ph};{msg}")
    csv_ext = "Phone;Message\n" + "\n".join(lista_ext)

    with c_exp3:
        st.download_button(
            label=f"📲 Exportar p/ Extensão WhatsApp ({len(lista_ext)})",
            data=csv_ext,
            file_name=f"Fila_Extensao_Whats_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
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
# 5. JANELA MODAL (POP-UP) DE ACIONAMENTO WHATSAPP
# ==========================================
@st.dialog("📲 Registrar Acionamento & Chamar no WhatsApp")
def modal_acionar_driver(driver_info: dict):
    st.markdown(f"**Motorista:** `{driver_info['Driver ID']}` — **{driver_info['Nome']}**")
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

    endereco_hub = st.text_input(
        "📍 Endereço do HUB (se aplicável):",
        value="Av. dos Estados, 7328 - Parque Jaçatuba - Santo André / SP"
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
        f"Olá {driver_info['Nome']}! Aqui é {analista_atual or 'da equipe'} da SPX Logistics (LSP93). "
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
            st.success(f"Acionamento gravado no histórico às {datetime.now().strftime('%H:%M:%S')}!")
            if url_wa:
                st.link_button("🚀 ABRIR CONVERSA NO WHATSAPP AGORA", url_wa, type="primary", use_container_width=True)
            else:
                st.warning("Este motorista não possui número de telefone válido cadastrado.")


# ==========================================
# 6. PÁGINA PRINCIPAL: CONTROL TOWER CHURN
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


header_img_html = f'<img src="{img_logo_oficial}" style="height: 90px; filter: drop-shadow(0 0 10px rgba(238,77,45,0.6));" alt="Logo SPX">' if img_logo_oficial else '🏎️'

header_html = f'''
<div style="background: linear-gradient(135deg, #1A1A1A 0%, #2A0800 60%, #EE4D2D 100%); border-bottom: 3px solid #EE4D2D; padding: 18px 30px; border-radius: 16px; margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 0 20px rgba(238,77,45,0.3);">
    <div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="color: #FFF; font-size: 2.1rem; font-weight: 800; margin: 0;">SPX LOGISTICS - CONTROL TOWER CHURN</div>
            <span style="background: #FFD600; color: #121212; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem;">🧪 DEV</span>
        </div>
        <div style="color: #DDD; font-size: 0.95rem; margin-top: 4px;">Painel Gerencial de Monitoramento, Acionamento e Histórico (LSP93)</div>
    </div>
    <div>{header_img_html}</div>
</div>
'''
st.markdown(header_html, unsafe_allow_html=True)

# ÁREA DE IMPORTAÇÃO (EXIBE APENAS SE NÃO ESTIVER TRAVADA)
if not st.session_state.get("base_travada"):
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

    if st.button('🚀 GERAR ANÁLISE E TRAVAR PAINEL NA SESSÃO', type="primary", use_container_width=True):
        if not arquivo_drivers or not arquivos_rotas:
            st.error('Por favor, faça o upload das bases.')
        else:
            with st.spinner('Processando inteligência de dados...'):
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

                st.session_state["df_analise_cache"] = df_analise
                st.session_state["col_driver_id_name"] = col_driver_id
                st.session_state["col_driver_name_col"] = col_driver_name
                st.session_state["col_veh_name"] = col_veh_name
                st.session_state["base_travada"] = True
                st.rerun()

# EXIBIÇÃO DO PAINEL GERENCIAL (PERSISTENTE)
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

    # Consulta histórico salvo para exibir situação atual na tabela
    df_hist_atual = carregar_historico()
    mapa_status_historico = {}
    if not df_hist_atual.empty:
        for _, rh in df_hist_atual.iterrows():
            d_id_h = str(rh["Driver ID"]).strip()
            if d_id_h not in mapa_status_historico:
                mapa_status_historico[d_id_h] = f"{rh['Status']} ({rh['Analista Responsável']} - {rh['Data/Hora Acionamento']})"

    # ==========================================
    # SELETOR RÁPIDO PARA ABRIR POP-UP DE ACIONAMENTO
    # ==========================================
    st.markdown("### 📲 Acionar Motorista no WhatsApp (Abre Janela de Registro)")
    st.caption("Escolha o motorista abaixo e clique no botão laranja. Uma janela abrirá para registrar o **Tipo de Acionamento** e o **Analista** antes de abrir o WhatsApp:")

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

    # Mostra os últimos 5 acionamentos registrados logo abaixo para confirmação visual imediata
    if not df_hist_atual.empty:
        with st.expander(f"📋 Últimos Acionamentos Registrados ({len(df_hist_atual)} no total) — Clique para ver ou vá ao menu Reengajamento", expanded=True):
            st.dataframe(
                df_hist_atual[["Driver ID", "Nome", "Analista Responsável", "Tipo de Acionamento", "Status", "Data/Hora Acionamento", "Última Atualização"]].head(5),
                hide_index=True,
                use_container_width=True
            )

    st.divider()

    # ==========================================
    # TABELA GERENCIAL DE CONSULTA
    # ==========================================
    st.markdown(f"### 📋 Tabela Gerencial (`{len(df_exibir)} motoristas`)")

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

img_footer_html = f'<img src="{img_shopito_entregador}" style="height: 55px;">' if img_shopito_entregador else ''
footer_html = f'''
<div style="margin-top: 45px; padding: 18px 25px; background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%); border: 1px solid rgba(238, 77, 45, 0.3); border-radius: 14px; display: flex; align-items: center; justify-content: space-between;">
    <div style="display:flex; align-items:center; gap: 12px;">{img_footer_html} <span style="color:#FFF; font-weight:700;">SPX Logistics</span></div>
    <div style="color: #AAA; font-size: 0.95rem; text-align: center;">Created by <strong style="color: #EE4D2D;">Pedro Heleno</strong><br>Fleet - LSP93</div>
</div>
'''
st.markdown(footer_html, unsafe_allow_html=True)
