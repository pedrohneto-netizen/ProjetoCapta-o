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

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (STREAMLIT)
# ==========================================
st.set_page_config(
    page_title="Shopee SPX - Control Tower Churn",
    page_icon="🚚",
    layout="wide",
)

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

img_kart_src = ''
possible_kart_files = [
    'Formula 1_2.jpg', 'Formula 1_2.png', 'Formula 1_2.jpeg',
    'Formula 1.jpg', 'Formula 1.png', 'Formula 1.jpeg',
    'Shopito Kart.jpg', 'Shopito Kart.png'
]

for fn in possible_kart_files:
    img_kart_src = get_base64_image_cached(str(PATH_PROJECT / fn))
    if img_kart_src:
        break

img_shopito_entregador = get_base64_image_cached(str(PATH_PROJECT / 'GIF-21-entregador.jpg'))

# ==========================================
# 2. ESTILIZAÇÃO CSS & LAYOUT SHOPEE BLACK
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    
    :root {
        --shopee-orange: #EE4D2D;
        --shopee-orange-hover: #FF5722;
        --shopee-dark-bg: #121212;
        --shopee-card-bg: #1E1E1E;
        --shopee-border: #2D2D2D;
    }

    body, .main, .stApp {
        background-color: var(--shopee-dark-bg) !important;
        color: #EEEEEE !important;
        font-family: 'Poppins', sans-serif;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .shopee-header-container {
        background: linear-gradient(135deg, #1A1A1A 0%, #2A0800 60%, #EE4D2D 100%);
        border-bottom: 3px solid var(--shopee-orange);
        padding: 18px 30px;
        border-radius: 16px;
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 25px rgba(238, 77, 45, 0.25);
        animation: fadeIn 0.5s ease-in-out;
    }

    .shopee-title {
        color: #FFFFFF !important;
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
    }

    .shopee-subtitle {
        color: #DDDDDD;
        font-size: 0.95rem;
        margin-top: 4px;
    }

    .header-kart-img {
        height: 90px;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.5));
        transition: transform 0.3s ease;
    }

    .header-kart-img:hover {
        transform: scale(1.05);
    }

    .stButton>button {
        background: linear-gradient(90deg, #EE4D2D 0%, #FF5722 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 12px 28px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(238, 77, 45, 0.3) !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px) scale(1.005) !important;
        box-shadow: 0 6px 20px rgba(255, 87, 34, 0.5) !important;
    }

    .watermark-footer {
        margin-top: 45px;
        padding: 18px 25px;
        background: linear-gradient(135deg, rgba(30,30,30,0.8) 0%, rgba(20,20,20,0.9) 100%);
        border: 1px solid rgba(238, 77, 45, 0.3);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
        pointer-events: none;
    }

    .watermark-text {
        color: #AAAAAA;
        font-size: 0.95rem;
        letter-spacing: 0.5px;
        text-align: center;
        line-height: 1.4;
    }

    .watermark-text strong {
        color: #EE4D2D;
        font-weight: 700;
    }

    .watermark-img {
        height: 55px;
        filter: drop-shadow(0 2px 5px rgba(0,0,0,0.4));
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNÇÕES DE TRATAMENTO DE DADOS
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

# ==========================================
# 4. CABEÇALHO PERSONALIZADO COM SHOPITO KART
# ==========================================
if img_kart_src:
    header_img_html = f'<img src="{img_kart_src}" class="header-kart-img" alt="Shopito Kart">'
else:
    header_img_html = '<div style="font-size: 3rem;">🏎️</div>'

header_html = f'''<div class="shopee-header-container"><div><div class="shopee-title">SPX LOGISTICS - CONTROL TOWER CHURN</div><div class="shopee-subtitle">Painel Inteligente de Monitoramento e Reengajamento de Motoristas de Fleet</div></div><div>{header_img_html}</div></div>'''
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# 5. UPLOAD DE ARQUIVOS
# ==========================================
col_up1, col_up2 = st.columns(2)

with col_up1:
    st.subheader('1. Base de Motoristas')
    arquivo_drivers = st.file_uploader('Faça o upload do CSV de motoristas do Galpão', type=['csv'])

with col_up2:
    st.subheader('2. Histórico de Rotas (ZIP ou CSV)')
    arquivos_rotas = st.file_uploader('Faça o upload dos arquivos ZIP ou CSV com o histórico de rotas', type=['zip', 'csv'], accept_multiple_files=True)

data_ref = st.date_input('Data de Referência da Análise', value=datetime(2026, 11, 10))
data_ref = datetime.combine(data_ref, datetime.min.time())

st.divider()

# ==========================================
# 6. PROCESSAMENTO E EXIBIÇÃO DENTRO DO HTML INTERATIVO
# ==========================================
if st.button('🚀 GERAR ANÁLISE E DASHBOARD'):
    if not arquivo_drivers or not arquivos_rotas:
        st.error('Por favor, faça o upload da base de motoristas (.csv) e do histórico de rotas (.zip ou .csv).')
    else:
        with st.spinner('Processando dados e preparando o painel gerencial...'):
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

            # Garantir extração exata do tipo de veículo da coluna oficial
            col_veh_name = next((c for c in df_drivers.columns if c.lower() in ['vehicle type', 'tipo de veiculo', 'tipo veiculo', 'veiculo']), 'Vehicle Type')
            veiculos_unicos = sorted(list(set(df_analise[col_veh_name].dropna().astype(str).unique()))) if col_veh_name in df_analise.columns else []
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
                d_veh = str(r.get(col_veh_name, 'N/I')).replace("'", "").replace('"', '')
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
                <tr data-status="{d_status}" data-dias="{d_dias_num}" data-veh="{d_veh}" data-id="{d_id}" data-name="{d_name}" style="border-bottom: 1px solid #2D2D2D;">
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
                    
                    .header-bar {{
                        display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;
                    }}
                    .section-title {{
                        color: #EE4D2D; font-size: 1.15rem; font-weight: 700; display: flex; align-items: center; gap: 8px; margin: 0;
                    }}

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

            <!-- KPIS CLICÁVEIS -->
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

            <!-- CONTAINER DA TABELA -->
            <div class="table-container">
                
                <!-- CABEÇALHO DO BLOCO COM TÍTULO E CAMPO DE BUSCA -->
                <div class="header-bar">
                    <div class="section-title">📋 Detalhamento da Base de Motoristas</div>
                    <input type="text" id="searchInput" class="search-input" onkeyup="aplicarFiltros()" placeholder="Buscar por ID, Nome ou Veículo..." style="width: 280px;">
                </div>

                <!-- BARRA DE FILTROS E AÇÕES DE CÓPIA -->
                <div class="filter-toolbar">
                    <div class="toolbar-group">
                        <button onclick="aplicarFiltros()" class="action-btn primary">
                            🔎 Pesquisar
                        </button>

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

                        <button onclick="limparFiltros()" class="action-btn" title="Restaurar visualização original">
                            🔄 Limpar Filtros
                        </button>
                    </div>

                    <div class="toolbar-group">
                        <button onclick="copiarVisiveis('id')" class="action-btn primary" title="Copiar apenas os IDs visíveis">
                            📋 Copiar IDs (Visíveis)
                        </button>
                        <button onclick="copiarVisiveis('name')" class="action-btn" title="Copiar apenas os Nomes visíveis">
                            📋 Copiar Nomes (Visíveis)
                        </button>
                        <button onclick="copiarSelecionados()" class="action-btn" title="Copiar itens marcados pelas caixas de seleção">
                            ✅ Copiar Selecionados <span id="lblSelecionados" class="badge-selected">0</span>
                        </button>
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
                    let vehVal = document.getElementById('veiculoFilter').value;
                    let rows = document.querySelectorAll('#driversTable tbody tr');

                    rows.forEach(row => {{
                        let rowStatus = row.getAttribute('data-status');
                        let rowDias = parseInt(row.getAttribute('data-dias'));
                        let rowVeh = row.getAttribute('data-veh');
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

                function copiarParaClipboard(texto) {{
                    if (navigator.clipboard && window.isSecureContext) {{
                        return navigator.clipboard.writeText(texto).catch(err => {{
                            return fallbackCopiar(texto);
                        }});
                    }} else {{
                        return fallbackCopiar(texto);
                    }}
                }}

                function fallbackCopiar(texto) {{
                    return new Promise((resolve, reject) => {{
                        let textArea = document.createElement("textarea");
                        textArea.value = texto;
                        textArea.style.position = "fixed";
                        textArea.style.left = "-999999px";
                        textArea.style.top = "-999999px";
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        try {{
                            let successful = document.execCommand('copy');
                            document.body.removeChild(textArea);
                            if (successful) resolve(); else reject(new Error('Copy failed'));
                        }} catch (err) {{
                            document.body.removeChild(textArea);
                            reject(err);
                        }}
                    }});
                }}

                function copiarTexto(texto, btnElement) {{
                    copiarParaClipboard(texto).then(() => {{
                        let originalText = btnElement.innerHTML;
                        btnElement.innerHTML = '✅ Copiado!';
                        btnElement.style.background = '#00C853';
                        btnElement.style.color = '#FFF';

                        setTimeout(() => {{
                            btnElement.innerHTML = originalText;
                            btnElement.style.background = '';
                            btnElement.style.color = '';
                        }}, 1500);
                    }}).catch(err => alert('Copie manualmente: ' + texto));
                }}

                function copiarVisiveis(tipo) {{
                    let rows = document.querySelectorAll('#driversTable tbody tr');
                    let lista = [];

                    rows.forEach(row => {{
                        if (row.style.display !== 'none') {{
                            let val = row.getAttribute('data-' + tipo);
                            if (val && val !== 'null' && val !== 'undefined') lista.push(val);
                        }}
                    }});

                    if (lista.length === 0) {{
                        alert('Nenhum motorista visível para copiar!');
                        return;
                    }}

                    let textoFinal = lista.join('\n');
                    copiarParaClipboard(textoFinal).then(() => {{
                        alert('✅ ' + lista.length + ' ' + (tipo === 'id' ? 'IDs' : 'Nomes') + ' copiados para a área de transferência!');
                    }}).catch(err => alert('Erro ao copiar lista!'));
                }}

                function copiarSelecionados() {{
                    let rows = document.querySelectorAll('#driversTable tbody tr');
                    let lista = [];

                    rows.forEach(row => {{
                        let cb = row.querySelector('.driver-checkbox');
                        if (cb && cb.checked) {{
                            let id = row.getAttribute('data-id');
                            let name = row.getAttribute('data-name');
                            lista.push(id + ' - ' + name);
                        }}
                    }});

                    if (lista.length === 0) {{
                        alert('Selecione pelo menos um motorista usando as caixas de seleção!');
                        return;
                    }}

                    let textoFinal = lista.join('\n');
                    copiarParaClipboard(textoFinal).then(() => {{
                        alert('✅ ' + lista.length + ' motoristas selecionados copiados para a área de transferência!');
                    }}).catch(err => alert('Erro ao copiar selecionados!'));
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

# ==========================================
# 7. RODAPÉ MARCA D'ÁGUA LIMPA
# ==========================================
img_footer_html = f'<img src="{img_shopito_entregador}" class="watermark-img">' if img_shopito_entregador else ''
footer_html = f'''<div class="watermark-footer">{img_footer_html}<div class="watermark-text">Created by <strong>Pedro Heleno</strong><br>Fleet - LSP93</div></div>'''
st.markdown(footer_html, unsafe_allow_html=True)
