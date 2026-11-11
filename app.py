from datetime import datetime
import base64
import os
from pathlib import Path
import re
import tempfile
import zipfile
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from modulo_reengajamento import renderizar_modulo_reengajamento, registrar_acionamento_massa
except ImportError:
    renderizar_modulo_reengajamento = None
    registrar_acionamento_massa = None

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (AMBIENTE DEV)
# ==========================================
st.set_page_config(
    page_title="[DEV] SPX - Control Tower Churn",
    page_icon="🧪",
    layout="wide",
)

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
        height: 75px;
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

# ==========================================
# CACHE DE IMAGENS (LOGO OFICIAL FORMULA 1_2_2.JPG)
# ==========================================
@st.cache_data(show_spinner=False, max_entries=10, ttl=3600)
def get_base64_image_cached(image_path_str):
    if os.path.exists(image_path_str):
        ext = os.path.splitext(image_path_str)[1].lower().replace('.', '')
        mime = 'gif' if ext == 'gif' else ('png' if ext == 'png' else 'jpeg')
        with open(image_path_str, 'rb') as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/{mime};base64,{encoded}"
    return ''

PATH_PROJECT = Path(r'C:\Users\SPXBR30056\Desktop\Projeto Captação Churn')

# Logo Oficial do Projeto
img_logo_oficial = get_base64_image_cached(str(PATH_PROJECT / 'Formula 1_2_2.jpg'))
if not img_logo_oficial:
    img_logo_oficial = get_base64_image_cached(str(PATH_PROJECT / 'Formula 1_2.jpg'))

img_shopito_entregador = get_base64_image_cached(str(PATH_PROJECT / 'GIF-21-entregador.jpg'))

# Menu Lateral LED Neon com a Logo Oficial
sidebar_img_html = f'<img src="{img_logo_oficial}" class="sidebar-logo" alt="Logo SPX">' if img_logo_oficial else ''

st.sidebar.markdown(f"""
<div class="sidebar-neon-card">
    {sidebar_img_html}
    <div class="sidebar-title">🏎️ SPX FLEET CONTROL</div>
    <div class="sidebar-badge">🧪 AMBIENTE DEV / STAGING</div>
</div>
""", unsafe_allow_html=True)

opcao_menu = st.sidebar.radio(
    "Navegação do Sistema:",
    ["📊 Control Tower Churn", "📅 Reengajamento & Reuniões"],
    index=0
)

st.sidebar.divider()
st.sidebar.caption("SPX Logistics - Fleet LSP93\nAutor: Pedro Heleno")

if opcao_menu == "📅 Reengajamento & Reuniões":
    if renderizar_modulo_reengajamento:
        renderizar_modulo_reengajamento()
    else:
        st.error("Módulo 'modulo_reengajamento.py' não encontrado.")
    st.stop()

# ==========================================
# CÓDIGO DO DASHBOARD PRINCIPAL
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

header_img_html = f'<img src="{img_logo_oficial}" style="height: 90px; filter: drop-shadow(0 0 10px rgba(238,77,45,0.6));" alt="Logo Oficial SPX">' if img_logo_oficial else '🏎️'

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
                d_id = str(r[col_driver_id]).replace("'", "").replace('', '')
                d_name = str(r.get('Driver Name', 'N/I')).replace("'", "").replace('', '')
                d_veh = str(r.get(col_veh_name, 'N/I')).replace("'", "").replace('', '').strip()
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

                if d_phone_clean:
                    copy_phone_btn = f'''
                    <button onclick="copiarTexto('{d_phone_clean}', this)" style="background: #2D2D2D; color: #EE4D2D; border: 1px solid #EE4D2D; border-radius: 6px; padding: 3px 8px; cursor: pointer; font-size: 0.75rem; font-weight: 700; transition: all 0.2s;">
                        📋 Copiar
                    </button>
                    '''
                else:
                    copy_phone_btn = '<span style="color: #777; font-size: 0.75rem;">Sem Whats</span>'

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
                    <td style="padding: 10px; text-align: center;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 6px;">
                            <span style="font-size: 0.82rem;">{d_phone}</span>
                            {copy_phone_btn}
                        </div>
                    </td>
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
                    .kpi-card {{
                        background: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 12px; padding: 16px; cursor: pointer;
                        transition: all 0.25s ease; position: relative; overflow: hidden;
                    }}
                    .kpi-card:hover {{ transform: translateY(-3px); border-color: #EE4D2D; box-shadow: 0 6px 15px rgba(238, 77, 45, 0.2); }}
                    .kpi-card.active {{ border-color: #EE4D2D; background: #261614; box-shadow: 0 0 15px rgba(238, 77, 45, 0.4); }}
                    .kpi-title {{ font-size: 0.75rem; text-transform: uppercase; color: #888888; font-weight: 700; letter-spacing: 0.5px; }}
                    .kpi-num {{ font-size: 1.8rem; font-weight: 800; color: #FFF; margin-top: 5px; }}
                    
                    .table-container {{ background: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 12px; padding: 20px; }}
                    .header-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }}
                    .section-title {{ color: #EE4D2D; font-size: 1.15rem; font-weight: 700; display: flex; align-items: center; gap: 8px; margin: 0; }}

                    .filter-toolbar {{
                        display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between;
                        background: #161616; padding: 12px 14px; border-radius: 10px; border: 1px solid #2A2A2A; margin-bottom: 15px;
                    }}

                    .toolbar-group {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}

                    .action-btn {{
                        background: #252525; color: #FFF; border: 1px solid #444; border-radius: 8px; padding: 7px 14px;
                        font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px;
                    }}
                    .action-btn:hover {{ background: #333; border-color: #EE4D2D; color: #EE4D2D; }}

                    .action-btn.primary {{
                        background: linear-gradient(90deg, #EE4D2D 0%, #FF5722 100%); border: none; color: white;
                    }}
                    .action-btn.primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}

                    .search-input, .select-input {{
                        background: #121212; border: 1px solid #333; color: #FFF; padding: 8px 12px; border-radius: 8px;
                        font-size: 0.85rem; outline: none;
                    }}
                    .search-input:focus, .select-input:focus {{ border-color: #EE4D2D; }}

                    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem; }}
                    th {{ background: #181818; color: #EE4D2D; font-weight: 700; text-transform: uppercase; padding: 12px 10px; border-bottom: 2px solid #EE4D2D; font-size: 0.78rem; }}
                    tr:hover {{ background-color: #242424; }}
                    
                    .badge-selected {{
                        background: rgba(238, 77, 45, 0.2); color: #EE4D2D; font-size: 0.78rem; font-weight: 700;
                        padding: 3px 8px; border-radius: 6px; border: 1px solid #EE4D2D;
                    }}
                </style>
            </head>
            <body>

            <div class="kpi-grid">
                <div class="kpi-card active" onclick="filtrarStatus('TODOS', this)">
                    <div class="kpi-title">🔍 Todos os Drivers</div>
                    <div class="kpi-num">{total:,}</div>
                </div>
                <div class="kpi-card" onclick="filtrarStatus('Ativo', this)">
                    <div class="kpi-title" style="color: #00E676;">🟢 Operacionais (0 a 7d)</div>
                    <div class="kpi-num" style="color: #00E676;">{c_op:,}</div>
                </div>
                <div class="kpi-card" onclick="filtrarStatus('Alerta', this)">
                    <div class="kpi-title" style="color: #FFD600;">🟡 Em Alerta (8 a 20d)</div>
                    <div class="kpi-num" style="color: #FFD600;">{c_alt:,}</div>
                </div>
                <div class="kpi-card" onclick="filtrarStatus('Churn', this)">
                    <div class="kpi-title" style="color: #FF5252;">🔴 Inativos (>20d)</div>
                    <div class="kpi-num" style="color: #FF5252;">{c_churn:,}</div>
                </div>
                <div class="kpi-card" onclick="filtrarStatus('Sem Rotas', this)">
                    <div class="kpi-title" style="color: #B0BEC5;">⚪ Sem Histórico AT</div>
                    <div class="kpi-num" style="color: #B0BEC5;">{c_sem:,}</div>
                </div>
            </div>

            <div class="table-container">
                <div class="header-bar">
                    <div class="section-title">📋 Detalhamento da Base de Motoristas</div>
                    <input type="text" id="searchInput" class="search-input" onkeyup="aplicarFiltros()" placeholder="Buscar por ID, Nome ou Veículo..." style="width: 280px;">
                </div>

                <div class="filter-toolbar">
                    <div class="toolbar-group">
                        <button onclick="aplicarFiltros()" class="action-btn primary">🔎 Pesquisar</button>

                        <select id="diasFilter" class="select-input" onchange="aplicarFiltros()">
                            <option value="TODOS">⏱️ Dias sem AT: Todos</option>
                            <option value="0-7">🟢 0 a 7 dias sem AT</option>
                            <option value="8-15">🟡 8 a 15 dias sem AT</option>
                            <option value="16-20">🟧 16 a 20 dias sem AT</option>
                            <option value="21+">🔴 Mais de 20 dias (Churn)</option>
                            <option value="SEM">⚪ Sem Histórico de Rotas</option>
                        </select>

                        <select id="veiculoFilter" class="select-input" onchange="aplicarFiltros()">
                            {veiculos_options_html}
                        </select>

                        <button onclick="limparFiltros()" class="action-btn">🔄 Limpar Filtros</button>
                    </div>

                    <div class="toolbar-group">
                        <button onclick="acionarMassaWhatsApp()" class="action-btn primary" style="background: #00E676; color: #121212; border: none; font-weight: 800;">
                            📲 Acionar Selecionados no WhatsApp <span id="lblSelecionados" class="badge-selected" style="background: #121212; color: #00E676; border-color: #00E676;">0</span>
                        </button>
                        <button onclick="copiarVisiveis('id')" class="action-btn">📋 Copiar IDs</button>
                        <button onclick="copiarVisiveis('name')" class="action-btn">📋 Copiar Nomes</button>
                    </div>
                </div>

                <div style="overflow-x: auto; max-height: 520px; overflow-y: auto;">
                    <table id="driversTable">
                        <thead>
                            <tr>
                                <th style="text-align: center; width: 40px;"><input type="checkbox" id="selectAll" onclick="toggleSelectAll(this)"></th>
                                <th>DRIVER ID</th>
                                <th>NOME DO MOTORISTA</th>
                                <th>VEÍCULO</th>
                                <th>DIAS SEM HISTÓRICO DE AT</th>
                                <th>STATUS INATIVIDADE</th>
                                <th style="text-align: center;">CONTATO / WHATSAPP</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <script>
                let currentCardStatus = 'TODOS';

                function filtrarStatus(status, cardElement) {{
                    currentCardStatus = status;
                    let cards = document.querySelectorAll('.kpi-card');
                    cards.forEach(c => c.classList.remove('active'));
                    cardElement.classList.add('active');
                    aplicarFiltros();
                }}

                function aplicarFiltros() {{
                    let searchText = document.getElementById('searchInput').value.toLowerCase().trim();
                    let diasVal = document.getElementById('diasFilter').value;
                    let vehVal = document.getElementById('veiculoFilter').value.toUpperCase().trim();
                    let rows = document.querySelectorAll('#driversTable tbody tr');

                    rows.forEach(row => {{
                        let rowStatus = row.getAttribute('data-status');
                        let rowDias = parseInt(row.getAttribute('data-dias'));
                        let rowVeh = (row.getAttribute('data-veh') || '').toUpperCase().trim();
                        let rowText = row.textContent.toLowerCase();

                        let matchCard = (currentCardStatus === 'TODOS') || (rowStatus === currentCardStatus);
                        let matchText = (searchText === '') || rowText.includes(searchText);

                        let matchDias = true;
                        if (diasVal === '0-7') matchDias = (rowDias >= 0 && rowDias <= 7);
                        else if (diasVal === '8-15') matchDias = (rowDias >= 8 && rowDias <= 15);
                        else if (diasVal === '16-20') matchDias = (rowDias >= 16 && rowDias <= 20);
                        else if (diasVal === '21+') matchDias = (rowDias > 20 && rowDias < 9999);
                        else if (diasVal === 'SEM') matchDias = (rowDias === 9999);

                        let matchVeh = (vehVal === 'TODOS') || (rowVeh === vehVal);

                        if (matchCard && matchText && matchDias && matchVeh) {{
                            row.style.display = '';
                        }} else {{
                            row.style.display = 'none';
                        }}
                    }});
                }}

                function limparFiltros() {{
                    document.getElementById('searchInput').value = '';
                    document.getElementById('diasFilter').value = 'TODOS';
                    document.getElementById('veiculoFilter').value = 'TODOS';
                    currentCardStatus = 'TODOS';
                    
                    let cards = document.querySelectorAll('.kpi-card');
                    cards.forEach(c => c.classList.remove('active'));
                    if(cards.length > 0) cards[0].classList.add('active');

                    let checkboxes = document.querySelectorAll('.driver-checkbox');
                    checkboxes.forEach(cb => cb.checked = false);
                    document.getElementById('selectAll').checked = false;
                    atualizarContadorSelecao();

                    aplicarFiltros();
                }}

                function toggleSelectAll(masterCb) {{
                    let rows = document.querySelectorAll('#driversTable tbody tr');
                    rows.forEach(row => {{
                        if (row.style.display !== 'none') {{
                            let cb = row.querySelector('.driver-checkbox');
                            if(cb) cb.checked = masterCb.checked;
                        }}
                    }});
                    atualizarContadorSelecao();
                }}

                function atualizarContadorSelecao() {{
                    let checked = document.querySelectorAll('.driver-checkbox:checked').length;
                    document.getElementById('lblSelecionados').textContent = checked;
                }}

                function acionarMassaWhatsApp() {{
                    let rows = document.querySelectorAll('#driversTable tbody tr');
                    let selecionados = [];

                    rows.forEach(row => {{
                        let cb = row.querySelector('.driver-checkbox');
                        if (cb && cb.checked) {{
                            let phone = row.getAttribute('data-phone');
                            let name = row.getAttribute('data-name');
                            if (phone && phone.length >= 10) {{
                                selecionados.push({{ name: name, phone: phone }});
                            }}
                        }}
                    }});

                    if (selecionados.length === 0) {{
                        alert('Selecione pelo menos um motorista com telefone válido para acionar via WhatsApp!');
                        return;
                    }}

                    let msgBase = encodeURIComponent("Olá! Notamos que você está inativo recentemente no galpão SPX. Gostamos de agendar uma reunião rápida de retorno às atividades!");
                    
                    selecionados.forEach(d => {{
                        let url = "https://api.whatsapp.com/send?phone=" + d.phone + "&text=" + msgBase;
                        window.open(url, '_blank');
                    }});
                }}

                function copiarTexto(texto, btnElement) {{
                    navigator.clipboard.writeText(texto).then(() => {{
                        let orig = btnElement.innerHTML;
                        btnElement.innerHTML = '✅ Copiado!';
                        btnElement.style.background = '#00C853';
                        setTimeout(() => {{ btnElement.innerHTML = orig; btnElement.style.background = ''; }}, 1500);
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

                    if (lista.length === 0) return alert('Nenhum motorista visível!');
                    navigator.clipboard.writeText(lista.join('\\n')).then(() => alert('✅ ' + lista.length + ' itens copiados!'));
                }}
            </script>
            </body>
            </html>
            '''

            components.html(html_component, height=730, scrolling=True)

            csv_data = df_analise.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label='📥 BAIXAR RELATÓRIO COMPLETO (CSV)',
                data=csv_data,
                file_name='relatorio_churn_galpao.csv',
                mime='text/csv'
            )

img_footer_html = f'<img src="{img_shopito_entregador}" style="height: 55px;">' if img_shopito_entregador else ''
footer_html = f'''
<div style="margin-top: 45px; padding: 18px 25px; background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%); border: 1px solid rgba(238, 77, 45, 0.3); border-radius: 14px; display: flex; align-items: center; justify-content: center; gap: 15px;">
    {img_footer_html}
    <div style="color: #AAA; font-size: 0.95rem; text-align: center;">Created by <strong style="color: #EE4D2D;">Pedro Heleno</strong><br>Fleet - LSP93</div>
</div>
'''
st.markdown(footer_html, unsafe_allow_html=True)
