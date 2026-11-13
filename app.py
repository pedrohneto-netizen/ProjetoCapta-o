from datetime import datetime
import base64
import os
from pathlib import Path
import re
import tempfile
import zipfile
import pandas as pd
import streamlit as st

try:
    from modulo_reengajamento import (
        renderizar_modulo_reengajamento,
        carregar_historico,
        registrar_acionamentos_lote
    )
except ImportError:
    renderizar_modulo_reengajamento = None
    carregar_historico = None
    registrar_acionamentos_lote = None

try:
    from modulo_assistente_ia import renderizar_modulo_ia
except ImportError:
    renderizar_modulo_ia = None

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (AMBIENTE DEV)
# ==========================================
st.set_page_config(
    page_title="[DEV] SPX - Control Tower Churn",
    page_icon="🧪",
    layout="wide",
)

if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "📊 Control Tower Churn"

if "filtro_kpi_status" not in st.session_state:
    st.session_state["filtro_kpi_status"] = "TODOS"

if "selecionar_todos_flag" not in st.session_state:
    st.session_state["selecionar_todos_flag"] = False

if "base_travada" not in st.session_state:
    st.session_state["base_travada"] = False

# Estilização Neon Fluorescente do Menu Lateral
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
        margin-bottom: 20px;
        box-shadow: 0 0 12px rgba(238, 77, 45, 0.35);
        text-align: center;
    }

    .sidebar-logo {
        max-height: 80px;
        width: auto;
        margin-bottom: 8px;
        filter: drop-shadow(0 0 8px rgba(238, 77, 45, 0.5));
    }

    .sidebar-title {
        color: #FFFFFF;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
    }

    .sidebar-badge {
        background: linear-gradient(90deg, #EE4D2D 0%, #FF5722 100%);
        color: white;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 4px;
        box-shadow: 0 0 8px #EE4D2D;
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

    .stRadio > label {
        color: #FFF !important;
        font-weight: 700 !important;
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

# MENU LATERAL LED NEON
sidebar_img_html = f'<img src="{img_logo_oficial}" class="sidebar-logo" alt="Logo SPX">' if img_logo_oficial else '🏎️'

st.sidebar.markdown(f"""
<div class="sidebar-neon-card">
    <div style="text-align: center; margin-bottom: 8px;">{sidebar_img_html}</div>
    <div class="sidebar-title">🏎️ SPX FLEET CONTROL</div>
    <div class="sidebar-badge">🧪 AMBIENTE DEV / STAGING</div>
</div>
""", unsafe_allow_html=True)

opcoes_menu = [
    "📊 Control Tower Churn",
    "📅 Reengajamento & Reuniões",
    "🤖 Assistente IA (SPX Copilot)"
]

if st.session_state["pagina_atual"] not in opcoes_menu:
    st.session_state["pagina_atual"] = opcoes_menu[0]

opcao_menu = st.sidebar.radio(
    "Navegação do Sistema:",
    opcoes_menu,
    index=opcoes_menu.index(st.session_state["pagina_atual"])
)

st.session_state["pagina_atual"] = opcao_menu

# Indicador de Base Travada na Sidebar + Comando Manual de Reset
st.sidebar.divider()
if st.session_state.get("base_travada") and "df_analise_cache" in st.session_state:
    st.sidebar.success(f"🔒 Base Carregada ({len(st.session_state['df_analise_cache'])} drivers)")
    if st.sidebar.button("🗑️ Limpar / Trocar Bases Importadas", use_container_width=True):
        for chave in ["df_analise_cache", "base_travada", "col_driver_id_name", "col_driver_name_col", "col_veh_name"]:
            st.session_state.pop(chave, None)
        st.session_state["selecionar_todos_flag"] = False
        st.toast("Bases removidas. Você já pode importar novos arquivos.", icon="🗑️")
        st.rerun()
else:
    st.sidebar.info("📂 Aguardando importação das bases")

st.sidebar.divider()
st.sidebar.caption("SPX Logistics - Fleet LSP93\nAutor: Pedro Heleno")

# ROTEAMENTO DAS PÁGINAS SECUNDÁRIAS
if st.session_state["pagina_atual"] == "📅 Reengajamento & Reuniões":
    if renderizar_modulo_reengajamento:
        renderizar_modulo_reengajamento()
    else:
        st.error("Módulo 'modulo_reengajamento.py' não encontrado.")
    st.stop()

if st.session_state["pagina_atual"] == "🤖 Assistente IA (SPX Copilot)":
    if renderizar_modulo_ia:
        renderizar_modulo_ia()
    else:
        st.error("Módulo 'modulo_assistente_ia.py' não encontrado.")
    st.stop()

# ==========================================
# FUNÇÕES DE APOIO E IMPORTAÇÃO
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

# ==========================================
# ÁREA DE IMPORTAÇÃO (EXIBE APENAS SE NÃO ESTIVER TRAVADA)
# ==========================================
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
                st.session_state["selecionar_todos_flag"] = False
                st.rerun()

# ==========================================
# EXIBIÇÃO DO PAINEL GERENCIAL (PERSISTENTE)
# ==========================================
if st.session_state.get("base_travada") and "df_analise_cache" in st.session_state:
    df_analise = st.session_state["df_analise_cache"]
    col_driver_id = st.session_state["col_driver_id_name"]
    col_driver_name = st.session_state.get("col_driver_name_col", "Driver Name")
    col_veh_name = st.session_state["col_veh_name"]

    # Barra de status da base travada com comando explícito de limpeza
    col_info_base, col_reset_base = st.columns([4, 1.3])
    with col_info_base:
        st.info("🔒 **Base ativa na sessão.** Os dados permanecerão carregados mesmo ao navegar entre abas ou registrar acionamentos.")
    with col_reset_base:
        if st.button("🗑️ Limpar / Trocar Bases", key="btn_reset_topo", use_container_width=True):
            for chave in ["df_analise_cache", "base_travada", "col_driver_id_name", "col_driver_name_col", "col_veh_name"]:
                st.session_state.pop(chave, None)
            st.session_state["selecionar_todos_flag"] = False
            st.rerun()

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
            st.session_state["selecionar_todos_flag"] = False
            st.rerun()

    with k2:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#00E676; font-size:0.8rem; font-weight:700;">🟢 OPERACIONAIS</div><div class="metric-num" style="color:#00E676;">{c_op:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Ativos", key="f_op", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Ativo"
            st.session_state["selecionar_todos_flag"] = False
            st.rerun()

    with k3:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#FFD600; font-size:0.8rem; font-weight:700;">🟡 EM ALERTA</div><div class="metric-num" style="color:#FFD600;">{c_alt:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Alerta", key="f_alt", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Alerta"
            st.session_state["selecionar_todos_flag"] = False
            st.rerun()

    with k4:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#FF5252; font-size:0.8rem; font-weight:700;">🔴 INATIVOS (CHURN)</div><div class="metric-num" style="color:#FF5252;">{c_churn:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Churn", key="f_churn", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Churn"
            st.session_state["selecionar_todos_flag"] = False
            st.rerun()

    with k5:
        st.markdown(f'<div class="metric-card-gerencial"><div style="color:#B0BEC5; font-size:0.8rem; font-weight:700;">⚪ SEM HISTÓRICO</div><div class="metric-num" style="color:#B0BEC5;">{c_sem:,}</div></div>', unsafe_allow_html=True)
        if st.button("Filtrar Sem Rotas", key="f_sem", use_container_width=True):
            st.session_state["filtro_kpi_status"] = "Sem Rotas"
            st.session_state["selecionar_todos_flag"] = False
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
            st.session_state["selecionar_todos_flag"] = False
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

    # Consulta histórico salvo para mostrar na tabela se o driver já tem situação registrada
    mapa_status_historico = {}
    if carregar_historico:
        df_hist_atual = carregar_historico()
        if not df_hist_atual.empty:
            for _, rh in df_hist_atual.iterrows():
                d_id_h = str(rh["Driver ID"]).strip()
                if d_id_h not in mapa_status_historico:
                    obs_txt = f" ({rh['Observação / Tratativa']})" if rh.get("Observação / Tratativa") else ""
                    mapa_status_historico[d_id_h] = f"{rh['Status']}{obs_txt}"

    col_title, col_sel_all = st.columns([3, 1.2])
    with col_title:
        st.markdown(f"### 📋 Tabela Gerencial (`{len(df_exibir)} motoristas`)")
    with col_sel_all:
        if st.button("☑️ Marcar / Desmarcar Todos", use_container_width=True):
            st.session_state["selecionar_todos_flag"] = not st.session_state["selecionar_todos_flag"]
            st.rerun()

    df_tabela = pd.DataFrame()
    df_tabela["Selecionar"] = st.session_state["selecionar_todos_flag"]
    df_tabela["Driver ID"] = df_exibir[col_driver_id].astype(str)
    df_tabela["Nome do Motorista"] = df_exibir[col_driver_name].astype(str)
    df_tabela["Veículo"] = df_exibir[col_veh_name].astype(str) if col_veh_name in df_exibir.columns else "N/I"
    df_tabela["Inatividade"] = df_exibir["Dias_Sem_AT_Fmt"]
    df_tabela["Situação Registrada"] = df_tabela["Driver ID"].apply(lambda x: mapa_status_historico.get(str(x).strip(), "Não Acionado"))
    df_tabela["Telefone"] = df_exibir["Telefone_Limpo"]
    df_tabela["WhatsApp"] = df_exibir["Telefone_Limpo"].apply(
        lambda p: f"https://api.whatsapp.com/send?phone={p}" if p else ""
    )

    editor_key = f"tabela_gerencial_{st.session_state['selecionar_todos_flag']}_{st.session_state['filtro_kpi_status']}_{veh_selecionado}"

    df_editado_tabela = st.data_editor(
        df_tabela,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Selecionar", default=False),
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome do Motorista": st.column_config.TextColumn("Nome do Motorista", disabled=True),
            "Veículo": st.column_config.TextColumn("Veículo", disabled=True),
            "Inatividade": st.column_config.TextColumn("Dias Sem AT", disabled=True),
            "Situação Registrada": st.column_config.TextColumn("Último Registro / Situação", disabled=True),
            "Telefone": st.column_config.TextColumn("Contato Tel", disabled=True),
            "WhatsApp": st.column_config.LinkColumn("📲 Abrir Whats", display_text="Chamar no Whats")
        },
        hide_index=True,
        use_container_width=True,
        key=editor_key
    )

    drivers_marcados = df_editado_tabela[df_editado_tabela["Selecionar"] == True]

    # ==========================================
    # PAINEL DE REGISTRO DE SITUAÇÃO DO ACIONAMENTO
    # ==========================================
    st.markdown("---")
    st.markdown(f"### 📝 Registrar Situação do Acionamento ({len(drivers_marcados)} selecionado(s))")
    st.caption("Selecione 1 ou mais motoristas na tabela acima, defina em que situação está o acionamento e grave no histórico:")

    c_reg1, c_reg2, c_reg3 = st.columns([1.5, 2.5, 1.5])
    with c_reg1:
        situacao_acionamento = st.selectbox(
            "Situação Atual do Acionamento:",
            [
                "Driver Acionado",
                "Aguardando Reunião",
                "Sem Resposta",
                "Confirmado",
                "Reintegrado",
                "Faltou",
                "Sem Interesse",
                "Número Inválido"
            ]
        )
    with c_reg2:
        obs_tratativa = st.text_input(
            "Observação / Retorno do Motorista (Opcional):",
            placeholder="Ex: Confirmou presença para amanhã às 11h / Pediu vaga para segunda..."
        )
    with c_reg3:
        endereco_hub_input = st.text_input(
            "📍 Endereço do HUB / Local:",
            "Av. dos Estados, 7328 - Santo André / SP"
        )

    c_dt1, c_dt2, c_btn_reg = st.columns([1, 1, 2])
    with c_dt1:
        dt_ag = st.date_input("Data da Reunião / Contato", value=datetime.now())
    with c_dt2:
        hr_ag = st.time_input("Horário", value=datetime.now().time())
    with c_btn_reg:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button(f"💾 REGISTRAR SITUAÇÃO DE {len(drivers_marcados)} DRIVER(S) NO HISTÓRICO", type="primary", use_container_width=True):
            if drivers_marcados.empty:
                st.warning("Marque pelo menos 1 motorista na coluna 'Selecionar' da tabela acima!")
            else:
                novos_registros = []
                agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

                for _, r in drivers_marcados.iterrows():
                    novos_registros.append({
                        "Driver ID": str(r["Driver ID"]),
                        "Nome": str(r["Nome do Motorista"]),
                        "Telefone": str(r["Telefone"]),
                        "Veiculo": str(r["Veículo"]),
                        "Data Acionamento": agora_str,
                        "Data Reunião": dt_ag.strftime("%d/%m/%Y"),
                        "Horário": hr_ag.strftime("%H:%M"),
                        "Status": situacao_acionamento,
                        "Observação / Tratativa": obs_tratativa,
                        "Endereço HUB / Pauta": endereco_hub_input
                    })

                if registrar_acionamentos_lote:
                    registrar_acionamentos_lote(novos_registros)
                    st.session_state["selecionar_todos_flag"] = False
                    st.toast(f"✅ {len(novos_registros)} registro(s) salvos como '{situacao_acionamento}'!", icon="💾")
                    st.rerun()

img_footer_html = f'<img src="{img_shopito_entregador}" style="height: 55px;">' if img_shopito_entregador else ''
footer_html = f'''
<div style="margin-top: 45px; padding: 18px 25px; background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%); border: 1px solid rgba(238, 77, 45, 0.3); border-radius: 14px; display: flex; align-items: center; justify-content: space-between;">
    <div style="display:flex; align-items:center; gap: 12px;">{img_footer_html} <span style="color:#FFF; font-weight:700;">SPX Logistics</span></div>
    <div style="color: #AAA; font-size: 0.95rem; text-align: center;">Created by <strong style="color: #EE4D2D;">Pedro Heleno</strong><br>Fleet - LSP93</div>
</div>
'''
st.markdown(footer_html, unsafe_allow_html=True)
