from datetime import datetime
import base64
import os
from pathlib import Path
import re
import tempfile
import zipfile
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from modulo_reengajamento import renderizar_modulo_reengajamento, salvar_historico, carregar_historico
except ImportError:
    renderizar_modulo_reengajamento = None
    salvar_historico = None
    carregar_historico = None

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

    /* BARRA LATERAL ESTILO LED NEON */
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

    .stRadio > label {
        color: #FFF !important;
        font-weight: 700 !important;
    }

    .stRadio div[role="radiogroup"] > label:hover {
        color: var(--shopee-orange) !important;
    }
</style>
""", unsafe_allow_html=True)

# Cache de Imagens
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

opcoes_menu = ["📊 Control Tower Churn", "📅 Reengajamento & Reuniões"]

opcao_menu = st.sidebar.radio(
    "Navegação do Sistema:",
    opcoes_menu,
    index=opcoes_menu.index(st.session_state["pagina_atual"])
)

st.session_state["pagina_atual"] = opcao_menu

st.sidebar.divider()
st.sidebar.caption("SPX Logistics - Fleet LSP93\nAutor: Pedro Heleno")

if st.session_state["pagina_atual"] == "📅 Reengajamento & Reuniões":
    if renderizar_modulo_reengajamento:
        renderizar_modulo_reengajamento()
    else:
        st.error("Módulo 'modulo_reengajamento.py' não encontrado.")
    st.stop()

# ==========================================
# DASHBOARD PRINCIPAL
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
        <div style="color: #DDD; font-size: 0.95rem; margin-top: 4px;">Painel de Monitoramento e Disparo de Reagendamentos (LSP93)</div>
    </div>
    <div>{header_img_html}</div>
</div>
'''
st.markdown(header_html, unsafe_allow_html=True)

col_up1, col_up2 = st.columns(2)
with col_up1:
    st.subheader('1. Base de Motoristas')
    arquivo_drivers = st.file_uploader('Upload CSV motoristas', type=['csv'])

with col_up2:
    st.subheader('2. Histórico de Rotas (ZIP ou CSV)')
    arquivos_rotas = st.file_uploader('Upload histórico rotas', type=['zip', 'csv'], accept_multiple_files=True)

data_ref = st.date_input('Data de Referência', value=datetime(2026, 11, 10))
data_ref = datetime.combine(data_ref, datetime.min.time())

st.divider()

if st.button('🚀 GERAR ANÁLISE E DASHBOARD'):
    if not arquivo_drivers or not arquivos_rotas:
        st.error('Por favor, faça o upload das bases.')
    else:
        with st.spinner('Processando dados...'):
            try:
                df_drivers = pd.read_csv(arquivo_drivers, sep=';', dtype=str, encoding='utf-8')
            except Exception:
                arquivo_drivers.seek(0)
                df_drivers = pd.read_csv(arquivo_drivers, sep=None, dtype=str, engine='python')

            col_status = next((c for c in df_drivers.columns if 'status' in c.lower()), 'SPX Status')
            col_driver_id, _ = encontrar_colunas(df_drivers.columns.tolist())
            if not col_driver_id:
                col_driver_id = df_drivers.columns[0]

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

            veiculos_unicos = sorted(list(set(df_analise[col_veh_name].dropna().astype(str).str.strip().unique()))) if col_veh_name in df_analise.columns else []
            veiculos_options_html = '<option value="TODOS">🚗 Veículo: Todos</option>' + "".join([f'<option value="{v}">{v}</option>' for v in veiculos_unicos if v and v.lower() != 'nan'])

            total = len(df_analise)
            c_op = len(df_analise[df_analise['Status_Inatividade'] == 'Ativo'])
            c_alt = len(df_analise[df_analise['Status_Inatividade'] == 'Alerta'])
            c_churn = len(df_analise[df_analise['Status_Inatividade'] == 'Churn'])
            c_sem = len(df_analise[df_analise['Status_Inatividade'] == 'Sem Rotas'])

            rows_list = []
            for _, r in df_analise.iterrows():
                d_id = str(r[col_driver_id]).replace("'", "").replace('"', '')
                d_name = str(r.get('Driver Name', 'N/I')).replace("'", "").replace('"', '')
                d_veh = str(r.get(col_veh_name, 'N/I')).replace("'", "").replace('"', '').strip()
                d_dias_num = int(r['Dias_Sem_Rota']) if pd.notna(r['Dias_Sem_Rota']) else 9999
                d_dias_at = r['Dias_Sem_AT_Fmt']
                d_status = r['Status_Inatividade']
                d_phone = r.get(col_phone, '') if col_phone else 'Não informado'
                d_phone_clean = r['Telefone_Limpo']

                if d_status == 'Ativo':
                    badge = '<span style="background: rgba(0, 200, 83, 0.2); color: #00E676; border: 1px solid #00E676; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem;">Ativo (0 a 7d)</span>'
                elif d_status == 'Alerta':
                    badge = '<span style="background: rgba(255, 171, 0, 0.2); color: #FFD600; border: 1px solid #FFD600; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem;">Alerta (8 a 20d)</span>'
                elif d_status == 'Churn':
                    badge = '<span style="background: rgba(255, 61, 0, 0.2); color: #FF5252; border: 1px solid #FF5252; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem;">Churn (>20d)</span>'
                else:
                    badge = '<span style="background: rgba(158, 158, 158, 0.2); color: #B0BEC5; border: 1px solid #B0BEC5; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8rem;">Sem Histórico</span>'

                # Ações Individuais (WhatsApp + Cópias)
                if d_phone_clean:
                    url_wa_indiv = f"https://api.whatsapp.com/send?phone={d_phone_clean}"
                    actions_cell = f'''
                    <div style="display: flex; gap: 6px; align-items: center; justify-content: center;">
                        <a href="{url_wa_indiv}" target="_blank" style="background: #25D366; color: #FFF; text-decoration: none; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 0.75rem;">📲 Whats</a>
                        <button onclick="copiarTexto('{d_phone_clean}', this)" style="background: #2D2D2D; color: #EE4D2D; border: 1px solid #EE4D2D; border-radius: 6px; padding: 3px 8px; cursor: pointer; font-size: 0.75rem; font-weight: 700;">📋 Tel</button>
                    </div>
                    '''
                else:
                    actions_cell = '<span style="color: #777; font-size: 0.75rem;">Sem Telefone</span>'

                row_html = f'''
                <tr data-status="{d_status}" data-dias="{d_dias_num}" data-veh="{d_veh}" data-id="{d_id}" data-name="{d_name}" data-phone="{d_phone_clean}" style="border-bottom: 1px solid #2D2D2D;">
                    <td style="padding: 10px; text-align: center;"><input type="checkbox" class="driver-checkbox" onclick="atualizarContadorSelecao()"></td>
                    <td style="padding: 10px; color: #EE4D2D; font-weight: 700;">
                        {d_id}
                        <button onclick="copiarTexto('{d_id}', this)" title="Copiar ID" style="background: transparent; border: none; color: #AAA; cursor: pointer; font-size: 0.8rem; margin-left: 4px;">📋</button>
                    </td>
                    <td style="padding: 10px;">
                        {d_name}
                        <button onclick="copiarTexto('{d_name}', this)" title="Copiar Nome" style="background: transparent; border: none; color: #AAA; cursor: pointer; font-size: 0.8rem; margin-left: 4px;">📋</button>
                    </td>
                    <td style="padding: 10px;"><span style="background: #252525; border: 1px solid #3A3A3A; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">{d_veh}</span></td>
                    <td style="padding: 10px; font-weight: 600; color: #FFF;">{d_dias_at}</td>
                    <td style="padding: 10px;">{badge}</td>
                    <td style="padding: 10px; text-align: center;">{actions_cell}</td>
                </tr>
                '''
                rows_list.append(row_html)

            table_rows = "".join(rows_list)

            html_component = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ background-color: #121212; color: #EEEEEE; font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 10px; }}
                    .kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }}
                    .kpi-card {{ background: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.25s ease; }}
                    .kpi-card:hover {{ border-color: #EE4D2D; }}
                    .kpi-card.active {{ border-color: #EE4D2D; background: #261614; box-shadow: 0 0 15px rgba(238, 77, 45, 0.4); }}
                    .kpi-title {{ font-size: 0.75rem; text-transform: uppercase; color: #888888; font-weight: 700; }}
                    .kpi-num {{ font-size: 1.8rem; font-weight: 800; color: #FFF; margin-top: 5px; }}
                    .table-container {{ background: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 12px; padding: 20px; }}
                    .filter-toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; background: #161616; padding: 12px 14px; border-radius: 10px; border: 1px solid #2A2A2A; margin-bottom: 15px; }}
                    .action-btn {{ background: #252525; color: #FFF; border: 1px solid #444; border-radius: 8px; padding: 7px 14px; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
                    .action-btn:hover {{ border-color: #EE4D2D; color: #EE4D2D; }}
                    .action-btn.primary {{ background: linear-gradient(90deg, #EE4D2D 0%, #FF5722 100%); border: none; color: white; font-weight: 800; }}
                    .search-input, .select-input {{ background: #121212; border: 1px solid #333; color: #FFF; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; outline: none; }}
                    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem; }}
                    th {{ background: #181818; color: #EE4D2D; font-weight: 700; padding: 12px 10px; border-bottom: 2px solid #EE4D2D; font-size: 0.78rem; }}
                    tr:hover {{ background-color: #242424; }}
                    .badge-selected {{ background: rgba(238, 77, 45, 0.2); color: #EE4D2D; font-size: 0.78rem; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid #EE4D2D; }}
                </style>
            </head>
            <body>

            <div class="kpi-grid">
                <div class="kpi-card active" onclick="filtrarStatus('TODOS', this)">
                    <div class="kpi-title">🔍 Todos os Drivers</div>
                    <div class="kpi-num">{total:,}</div>
                </div>
                <div class="kpi-card" onclick="filtrarStatus('Ativo', this)"><div class="kpi-title" style="color:#00E676;">🟢 Operacionais</div><div class="kpi-num" style="color:#00E676;">{c_op:,}</div></div>
                <div class="kpi-card" onclick="filtrarStatus('Alerta', this)"><div class="kpi-title" style="color:#FFD600;">🟡 Em Alerta</div><div class="kpi-num" style="color:#FFD600;">{c_alt:,}</div></div>
                <div class="kpi-card" onclick="filtrarStatus('Churn', this)"><div class="kpi-title" style="color:#FF5252;">🔴 Inativos (>20d)</div><div class="kpi-num" style="color:#FF5252;">{c_churn:,}</div></div>
                <div class="kpi-card" onclick="filtrarStatus('Sem Rotas', this)"><div class="kpi-title" style="color:#B0BEC5;">⚪ Sem Histórico AT</div><div class="kpi-num" style="color:#B0BEC5;">{c_sem:,}</div></div>
            </div>

            <div class="table-container">
                <div class="filter-toolbar">
                    <div style="display:flex; gap:8px; align-items: center; flex-wrap: wrap;">
                        <input type="text" id="searchInput" class="search-input" onkeyup="aplicarFiltros()" placeholder="Buscar por ID, Nome ou Veículo..." style="width: 240px;">
                        <select id="diasFilter" class="select-input" onchange="aplicarFiltros()">
                            <option value="TODOS">⏱️ Dias: Todos</option>
                            <option value="0-7">🟢 0 a 7 dias</option>
                            <option value="8-15">🟡 8 a 15 dias</option>
                            <option value="16-20">🟧 16 a 20 dias</option>
                            <option value="21+">🔴 >20 dias (Churn)</option>
                            <option value="SEM">⚪ Sem Histórico</option>
                        </select>
                        <select id="veiculoFilter" class="select-input" onchange="aplicarFiltros()">{veiculos_options_html}</select>
                        <button onclick="limparFiltros()" class="action-btn">🔄 Limpar</button>
                    </div>

                    <div style="display:flex; gap:8px;">
                        <button onclick="copiarVisiveis('id')" class="action-btn">📋 Copiar IDs</button>
                        <button onclick="copiarVisiveis('name')" class="action-btn">📋 Copiar Nomes</button>
                    </div>
                </div>

                <div style="overflow-x: auto; max-height: 500px;">
                    <table id="driversTable">
                        <thead>
                            <tr>
                                <th style="text-align: center; width: 40px;"><input type="checkbox" id="selectAll" onclick="toggleSelectAll(this)"></th>
                                <th>DRIVER ID</th>
                                <th>NOME DO MOTORISTA</th>
                                <th>VEÍCULO</th>
                                <th>DIAS SEM HISTÓRICO DE AT</th>
                                <th>STATUS INATIVIDADE</th>
                                <th style="text-align: center;">AÇÕES INDIVIDUAIS</th>
                            </tr>
                        </thead>
                        <tbody>{table_rows}</tbody>
                    </table>
                </div>
            </div>

            <script>
                let currentCardStatus = 'TODOS';

                function filtrarStatus(status, el) {{
                    currentCardStatus = status;
                    document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('active'));
                    el.classList.add('active');
                    aplicarFiltros();
                }}

                function aplicarFiltros() {{
                    let search = document.getElementById('searchInput').value.toLowerCase().trim();
                    let diasVal = document.getElementById('diasFilter').value;
                    let vehVal = document.getElementById('veiculoFilter').value.toUpperCase().trim();
                    let rows = document.querySelectorAll('#driversTable tbody tr');

                    rows.forEach(row => {{
                        let rowStatus = row.getAttribute('data-status');
                        let rowDias = parseInt(row.getAttribute('data-dias'));
                        let rowVeh = (row.getAttribute('data-veh') || '').toUpperCase().trim();
                        let rowText = row.textContent.toLowerCase();

                        let mCard = (currentCardStatus === 'TODOS') || (rowStatus === currentCardStatus);
                        let mText = (search === '') || rowText.includes(search);
                        let mVeh = (vehVal === 'TODOS') || (rowVeh === vehVal);

                        let mDias = true;
                        if (diasVal === '0-7') mDias = (rowDias >= 0 && rowDias <= 7);
                        else if (diasVal === '8-15') mDias = (rowDias >= 8 && rowDias <= 15);
                        else if (diasVal === '16-20') mDias = (rowDias >= 16 && rowDias <= 20);
                        else if (diasVal === '21+') mDias = (rowDias > 20 && rowDias < 9999);
                        else if (diasVal === 'SEM') mDias = (rowDias === 9999);

                        row.style.display = (mCard && mText && mVeh && mDias) ? '' : 'none';
                    }});
                }}

                function limparFiltros() {{
                    document.getElementById('searchInput').value = '';
                    document.getElementById('diasFilter').value = 'TODOS';
                    document.getElementById('veiculoFilter').value = 'TODOS';
                    currentCardStatus = 'TODOS';
                    document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('active'));
                    document.querySelectorAll('.kpi-card')[0].classList.add('active');
                    document.querySelectorAll('.driver-checkbox').forEach(cb => cb.checked = false);
                    document.getElementById('selectAll').checked = false;
                    atualizarContadorSelecao();
                    aplicarFiltros();
                }}

                function toggleSelectAll(masterCb) {{
                    document.querySelectorAll('#driversTable tbody tr').forEach(row => {{
                        if (row.style.display !== 'none') {{
                            let cb = row.querySelector('.driver-checkbox');
                            if(cb) cb.checked = masterCb.checked;
                        }}
                    }});
                    atualizarContadorSelecao();
                }}

                function atualizarContadorSelecao() {{
                    let checked = document.querySelectorAll('.driver-checkbox:checked').length;
                    let btn = window.parent.document.querySelector('button[key="btn_massa_trigger"]');
                }}

                function copiarTexto(texto, btnElement) {{
                    navigator.clipboard.writeText(texto).then(() => {{
                        let orig = btnElement.innerHTML;
                        btnElement.innerHTML = '✅ Copiado!';
                        btnElement.style.background = '#00C853';
                        setTimeout(() => {{ btnElement.innerHTML = orig; btnElement.style.background = ''; }}, 1400);
                    }});
                }}

                function copiarVisiveis(tipo) {{
                    let rows = document.querySelectorAll('#driversTable tbody tr');
                    let lista = [];
                    rows.forEach(row => {{
                        if (row.style.display !== 'none') {{
                            let val = row.getAttribute('data-' + tipo);
                            if (val) lista.push(val);
                        }}
                    }});
                    if (lista.length === 0) return alert('Nenhum item visível!');
                    navigator.clipboard.writeText(lista.join('\\n')).then(() => alert('✅ ' + lista.length + ' itens copiados!'));
                }}
            </script>
            </body>
            </html>
            '''

            components.html(html_component, height=710, scrolling=True)

            # ==========================================
            # PAINEL DE DISPARO EM MASSA / REUNIÃO (STREAMLIT NATIVO)
            # ==========================================
            st.markdown("### 📲 Acionamento & Agendamento de Reunião em Massa")
            st.caption("Selecione os motoristas desejados na tabela acima para agendar o disparo coletivo:")

            # Seleção direta no Streamlit para garantir estabilidade do botão de envio
            drivers_opcoes = [f"{r[col_driver_id]} - {r.get('Driver Name', 'Motorista')} ({r['Telefone_Limpo']})" for _, r in df_analise.iterrows() if r['Telefone_Limpo']]
            
            selecionados_massa = st.multiselect(
                "Motoristas selecionados para o disparo em massa:",
                options=drivers_opcoes,
                default=drivers_opcoes[:5] if len(drivers_opcoes) >= 5 else drivers_opcoes
            )

            c_box1, c_box2 = st.columns(2)
            with c_box1:
                dt_reuniao = st.date_input("Data Agendada para Reunião", value=datetime.now())
                hr_reuniao = st.time_input("Horário da Reunião", value=datetime.now().time())
            with c_box2:
                pauta_reuniao = st.selectbox("Pauta Principal", ["Reintegração de Base Dormente", "Alinhamento de Rotas/Galpão", "Aumento de Carga / Migração"])
                link_reuniao = st.text_input("Link da Reunião (Meet/Teams)", "https://meet.google.com/spx-fleet-lsp93")

            if st.button("🚀 REGISTRAR AGENDAMENTO E IR PARA GERENCIADOR DE ENVIOS", type="primary"):
                if not selecionados_massa:
                    st.warning("Selecione pelo menos 1 motorista na caixa acima.")
                else:
                    novos = []
                    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    for item in selecionados_massa:
                        partes = item.split(" - ")
                        d_id = partes[0]
                        sub_partes = partes[1].split(" (")
                        d_name = sub_partes[0]
                        d_phone = sub_partes[1].replace(")", "")
                        
                        novos.append({
                            "Driver ID": d_id,
                            "Nome": d_name,
                            "Telefone": d_phone,
                            "Veiculo": "N/I",
                            "Data Acionamento": agora_str,
                            "Data Reunião": dt_reuniao.strftime("%d/%m/%Y"),
                            "Horário": hr_reuniao.strftime("%H:%M"),
                            "Status": "Aguardando Reunião",
                            "Observação": f"Pauta: {pauta_reuniao} | Link: {link_reuniao}"
                        })
                    
                    if novos and salvar_historico and carregar_historico:
                        df_h = carregar_historico()
                        df_f = pd.concat([pd.DataFrame(novos), df_h], ignore_index=True).drop_duplicates(subset=["Driver ID", "Data Reunião"], keep="first")
                        salvar_historico(df_f)
                        
                        st.session_state["pagina_atual"] = "📅 Reengajamento & Reuniões"
                        st.toast("✅ Reuniões registradas no histórico!", icon="🚀")
                        st.rerun()

img_footer_html = f'<img src="{img_shopito_entregador}" style="height: 55px;">' if img_shopito_entregador else ''
footer_html = f'''
<div style="margin-top: 45px; padding: 18px 25px; background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%); border: 1px solid rgba(238, 77, 45, 0.3); border-radius: 14px; display: flex; align-items: center; justify-content: center; gap: 15px;">
    {img_footer_html}
    <div style="color: #AAA; font-size: 0.95rem; text-align: center;">Created by <strong style="color: #EE4D2D;">Pedro Heleno</strong><br>Fleet - LSP93</div>
</div>
'''
st.markdown(footer_html, unsafe_allow_html=True)
