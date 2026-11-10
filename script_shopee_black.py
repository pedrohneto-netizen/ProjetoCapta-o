from datetime import datetime, timedelta
import glob
import os
from pathlib import Path
import re
import zipfile
import pandas as pd

# ==========================================
# 1. CONFIGURAÇÕES E PARÂMETROS
# ==========================================
DIRETORIO_PROJETO = Path(r'C:\Users\SPXBR30056\Desktop\Projeto Captação Churn')

PATH_BASE_DRIVERS = (
    DIRETORIO_PROJETO / 'br_own_fleet_driver_2026-11-10_11_15_15.csv'
)
PASTA_ZIP_ROTAS = DIRETORIO_PROJETO
PATH_SAIDA_CSV = DIRETORIO_PROJETO / 'relatorio_todos_drivers_churn.csv'
PATH_SAIDA_HTML = DIRETORIO_PROJETO / 'dashboard_shopee_black.html'

HOJE = datetime(2026, 11, 10)  # Data de referência


def limpar_id(val):
  """Padroniza e limpa IDs removendo decimais e espaços."""
  if pd.isna(val):
    return ''
  val_str = str(val).strip()
  if val_str.endswith('.0'):
    val_str = val_str[:-2]
  return val_str


def formatar_whatsapp(val):
  """Limpa e formata número de telefone para link direto do WhatsApp (wa.me)."""
  if pd.isna(val):
    return ''
  num = re.sub(r'\D', '', str(val))
  if not num:
    return ''
  if not num.startswith('55') and len(num) in [10, 11]:
    num = '55' + num
  return num


# ==========================================
# 2. CARREGAR BASE COMPLETA DE MOTORISTAS
# ==========================================
print('1/4 - Carregando base de motoristas...')
try:
  df_drivers = pd.read_csv(
      PATH_BASE_DRIVERS, dtype=str, sep=None, engine='python'
  )
except Exception:
  df_drivers = pd.read_csv(
      PATH_BASE_DRIVERS, dtype=str, sep=';', encoding='latin1'
  )

# Identificar colunas principais
col_status = next(
    (c for c in df_drivers.columns if 'status' in c.lower()), 'SPX Status'
)
col_driver_id = next(
    (
        c
        for c in df_drivers.columns
        if 'driver' in c.lower() and 'id' in c.lower()
    ),
    'Driver ID',
)
if col_driver_id not in df_drivers.columns:
  col_driver_id = next(
      (c for c in df_drivers.columns if 'driver' in c.lower()),
      df_drivers.columns[0],
  )

col_phone = next(
    (
        c
        for c in df_drivers.columns
        if any(
            k in c.lower()
            for k in [
                'phone',
                'mobile',
                'celular',
                'whatsapp',
                'contato',
                'telefone',
            ]
        )
    ),
    None,
)

# Filtrar motoristas ativos e limpar IDs
df_drivers_ativos = df_drivers[df_drivers[col_status] == 'Active'].copy()
df_drivers_ativos[col_driver_id] = df_drivers_ativos[col_driver_id].apply(
    limpar_id
)

# ==========================================
# 3. EXTRAIR ÚLTIMA ROTA DO HISTÓRICO ZIP
# ==========================================
print('2/4 - Mapeando últimas rotas no histórico ZIP...')
dict_ultima_rota = {}
arquivos_zip = glob.glob(os.path.join(PASTA_ZIP_ROTAS, '*.zip'))

for zip_path in arquivos_zip:
  print(f'   -> Processando: {os.path.basename(zip_path)}')
  with zipfile.ZipFile(zip_path, 'r') as z:
    for filename in z.namelist():
      if filename.endswith('.csv'):
        with z.open(filename) as f:
          sample = pd.read_csv(f, nrows=5)
          cols = sample.columns.tolist()

          d_col = next(
              (
                  c
                  for c in cols
                  if any(
                      k in c.lower()
                      for k in ['driver id', 'driver_id', 'driver', 'motorista']
                  )
              ),
              None,
          )
          dt_col = next(
              (
                  c
                  for c in cols
                  if any(
                      k in c.lower()
                      for k in ['route date', 'date', 'created', 'task date']
                  )
              ),
              None,
          )

          if not d_col or not dt_col:
            continue

          f.seek(0)
          for chunk in pd.read_csv(
              f,
              chunksize=100000,
              usecols=[d_col, dt_col],
              dtype={d_col: str},
              on_bad_lines='skip',
          ):

            chunk[d_col] = chunk[d_col].apply(limpar_id)
            chunk[dt_col] = pd.to_datetime(chunk[dt_col], errors='coerce')
            chunk = chunk.dropna(subset=[d_col, dt_col])

            max_dates = chunk.groupby(d_col)[dt_col].max()
            for driver_id, dt in max_dates.items():
              if (
                  driver_id not in dict_ultima_rota
                  or dt > dict_ultima_rota[driver_id]
              ):
                dict_ultima_rota[driver_id] = dt

df_ultimas_rotas = (
    pd.DataFrame(
        list(dict_ultima_rota.items()),
        columns=[col_driver_id, 'Ultima_Rota'],
    )
    .drop_duplicates(subset=[col_driver_id])
    .reset_index(drop=True)
)

# ==========================================
# 4. DIAGNÓSTICO E CATEGORIZAÇÃO DE TODOS OS DRIVERS
# ==========================================
print('3/4 - Calculando inatividade e categorizando todos os motoristas...')
df_analise = df_drivers_ativos.merge(
    df_ultimas_rotas, on=col_driver_id, how='left'
)
df_analise['Dias_Sem_Rota'] = (HOJE - df_analise['Ultima_Rota']).dt.days


# Classificação em 4 Faixas Dinâmicas
def classificar_status(row):
  if pd.isna(row['Ultima_Rota']):
    return 'Sem Rotas Registradas'
  dias = row['Dias_Sem_Rota']
  if dias <= 7:
    return 'Ativo (0 a 7 dias)'
  elif dias <= 20:
    return 'Alerta (8 a 20 dias)'
  else:
    return 'Inativo / Churn (> 20 dias)'


df_analise['Status_Inatividade'] = df_analise.apply(classificar_status, axis=1)

# Ordenar por maior tempo de inatividade
df_analise = df_analise.sort_values(
    by='Dias_Sem_Rota', ascending=False, na_position='first'
)

# Exportar base completa consolidada
df_analise.to_csv(PATH_SAIDA_CSV, index=False, encoding='utf-8-sig')

# ==========================================
# 5. GERAR DASHBOARD SHOPEE BLACK EDITION (HTML)
# ==========================================
print('4/4 - Gerando Dashboard Shopee Black Edition em HTML...')

total_ativos = len(df_analise)
count_operacionais = len(
    df_analise[df_analise['Status_Inatividade'] == 'Ativo (0 a 7 dias)']
)
count_alerta = len(
    df_analise[df_analise['Status_Inatividade'] == 'Alerta (8 a 20 dias)']
)
count_churn_20d = len(
    df_analise[df_analise['Status_Inatividade'] == 'Inativo / Churn (> 20 dias)']
)
count_sem_rota = len(
    df_analise[df_analise['Status_Inatividade'] == 'Sem Rotas Registradas']
)

pct_churn = (count_churn_20d / total_ativos * 100) if total_ativos > 0 else 0

# Montar Tabela HTML
tabela_rows = ''
for _, row in df_analise.iterrows():
  dt_str = (
      row['Ultima_Rota'].strftime('%d/%m/%Y')
      if pd.notna(row['Ultima_Rota'])
      else 'Nunca realizou'
  )
  dias_val = row['Dias_Sem_Rota']

  if pd.notna(dias_val):
    dias_num = int(dias_val)
    dias_str = f'{dias_num} dias'
  else:
    dias_num = 9999
    dias_str = 'N/A'

  driver_name = row.get('Driver Name', row.get('Name', row[col_driver_id]))
  vehicle_type = row.get('Vehicle Type', 'N/I')

  # WhatsApp
  raw_phone = row.get(col_phone, '') if col_phone else ''
  phone_num = formatar_whatsapp(raw_phone)

  if phone_num:
    msg_wa = f'Olá {driver_name}, tudo bem? Notamos que você está a {dias_str} sem rodar na SPX. Gostaria de verificar como podemos te ajudar a retornar às rotas!'
    msg_encoded = pd.Series([msg_wa]).str.replace(' ', '%20')[0]
    wa_button = f'<a href="https://wa.me/{phone_num}?text={msg_encoded}" target="_blank" class="btn btn-wa"><i class="bi bi-whatsapp"></i> {raw_phone if raw_phone else "Chamar"}</a>'
  else:
    wa_button = (
        '<span class="text-muted" style="font-size:0.8rem;">Não informado</span>'
    )

  # Badge de Status
  st = row['Status_Inatividade']
  if st == 'Ativo (0 a 7 dias)':
    badge_class = 'bg-success-shopee'
  elif st == 'Alerta (8 a 20 dias)':
    badge_class = 'bg-warning-shopee'
  elif st == 'Inativo / Churn (> 20 dias)':
    badge_class = 'bg-danger-shopee'
  else:
    badge_class = 'bg-secondary-shopee'

  tabela_rows += f"""
    <tr data-status="{st}" data-vehicle="{vehicle_type}">
        <td><strong class="text-orange">{row[col_driver_id]}</strong></td>
        <td>{driver_name}</td>
        <td><span class="vehicle-tag">{vehicle_type}</span></td>
        <td>{dt_str}</td>
        <td data-order="{dias_num}"><span class="badge {badge_class}">{dias_str}</span></td>
        <td><span class="badge {badge_class}">{st}</span></td>
        <td class="text-center">{wa_button}</td>
    </tr>
    """

html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopee SPX - Control Tower Driver Churn</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --shopee-orange: #EE4D2D;
            --shopee-orange-hover: #FF5722;
            --shopee-dark-bg: #121212;
            --shopee-card-bg: #1E1E1E;
            --shopee-border: #2D2D2D;
            --shopee-text-primary: #EEEEEE;
            --shopee-text-muted: #AAAAAA;
        }}
        body {{
            background-color: var(--shopee-dark-bg);
            color: var(--shopee-text-primary);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            padding-bottom: 50px;
        }}
        .header-shopee {{
            background: linear-gradient(135deg, #1A1A1A 0%, #2A0800 50%, #EE4D2D 100%);
            border-bottom: 2px solid var(--shopee-orange);
            padding: 25px 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(238, 77, 45, 0.2);
        }}
        .brand-logo {{
            font-weight: 900;
            font-size: 1.8rem;
            letter-spacing: 1px;
            color: var(--shopee-orange);
            text-transform: uppercase;
        }}
        .card-shopee {{
            background-color: var(--shopee-card-bg);
            border: 1px solid var(--shopee-border);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }}
        .card-shopee:hover {{
            border-color: var(--shopee-orange);
            transform: translateY(-3px);
        }}
        .kpi-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--shopee-text-muted);
            font-weight: 700;
        }}
        .kpi-value {{
            font-size: 2.2rem;
            font-weight: 800;
            color: #FFFFFF;
        }}
        .text-orange {{ color: var(--shopee-orange) !important; }}
        .bg-orange-subtle {{ background-color: rgba(238, 77, 45, 0.15) !important; }}
        
        /* Badges Customizadas */
        .bg-success-shopee {{ background-color: #00c853 !important; color: #fff; }}
        .bg-warning-shopee {{ background-color: #ffab00 !important; color: #000; font-weight: 600; }}
        .bg-danger-shopee {{ background-color: #ff3d00 !important; color: #fff; }}
        .bg-secondary-shopee {{ background-color: #616161 !important; color: #fff; }}

        .vehicle-tag {{
            background-color: #2A2A2A;
            border: 1px solid #3A3A3A;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.85rem;
            color: #DDD;
        }}

        /* Tabela Styling */
        .table-shopee {{
            color: var(--shopee-text-primary);
            background-color: var(--shopee-card-bg);
        }}
        .table-shopee thead {{
            background-color: #252525;
            border-bottom: 2px solid var(--shopee-orange);
            color: var(--shopee-orange);
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        .table-shopee tbody tr {{
            border-bottom: 1px solid var(--shopee-border);
            transition: background 0.2s;
        }}
        .table-shopee tbody tr:hover {{
            background-color: #2A2A2A !important;
        }}
        
        /* Botão WhatsApp */
        .btn-wa {{
            background-color: #25D366;
            color: white;
            font-weight: 600;
            font-size: 0.82rem;
            border-radius: 20px;
            padding: 4px 12px;
            border: none;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .btn-wa:hover {{
            background-color: #1EBE5D;
            color: white;
            box-shadow: 0 0 10px rgba(37, 211, 102, 0.4);
            transform: scale(1.03);
        }}

        /* Controles de Busca e Filtro */
        .form-control-shopee, .form-select-shopee {{
            background-color: #181818;
            border: 1px solid var(--shopee-border);
            color: #FFF;
            border-radius: 8px;
        }}
        .form-control-shopee:focus, .form-select-shopee:focus {{
            background-color: #181818;
            border-color: var(--shopee-orange);
            color: #FFF;
            box-shadow: 0 0 8px rgba(238, 77, 45, 0.4);
        }}
    </style>
</head>
<body>

<div class="header-shopee">
    <div class="container-fluid px-4 d-flex justify-content-between align-items-center">
        <div>
            <div class="brand-logo"><i class="bi bi-truck-flatbed"></i> SPX LOGISTICS</div>
            <p class="mb-0 text-muted">Painel de Monitoramento de Atividade & Inatividade de Motoristas (Data Ref: {HOJE.strftime('%d/%m/%Y')})</p>
        </div>
        <div>
            <span class="badge bg-orange-subtle text-orange border border-warning px-3 py-2">
                <i class="bi bi-person-check-fill"></i> Total Ativos: <strong>{total_ativos:,}</strong>
            </span>
        </div>
    </div>
</div>

<div class="container-fluid px-4">
    <!-- CARDS DE KPIS -->
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="card card-shopee p-3 border-start border-success border-4">
                <div class="kpi-title"><i class="bi bi-check-circle-fill text-success"></i> Operacionais (0 a 7d)</div>
                <div class="kpi-value text-success">{count_operacionais:,}</div>
                <small class="text-muted">Rodaram recentemente</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-shopee p-3 border-start border-warning border-4">
                <div class="kpi-title"><i class="bi bi-exclamation-triangle-fill text-warning"></i> Em Alerta (8 a 20d)</div>
                <div class="kpi-value text-warning">{count_alerta:,}</div>
                <small class="text-muted">Atenção para reengajamento</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-shopee p-3 border-start border-danger border-4">
                <div class="kpi-title"><i class="bi bi-slash-circle-fill text-danger"></i> Churn / Crítico (>20d)</div>
                <div class="kpi-value text-danger">{count_churn_20d:,}</div>
                <small class="text-muted">{pct_churn:.1f}% do total de ativos</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-shopee p-3 border-start border-secondary border-4">
                <div class="kpi-title"><i class="bi bi-question-circle-fill text-secondary"></i> Sem Rotas Registradas</div>
                <div class="kpi-value text-secondary">{count_sem_rota:,}</div>
                <small class="text-muted">Sem dados no histórico ZIP</small>
            </div>
        </div>
    </div>

    <!-- GRÁFICOS -->
    <div class="row g-3 mb-4">
        <div class="col-md-8">
            <div class="card card-shopee p-3">
                <h6 class="fw-bold text-orange mb-3"><i class="bi bi-bar-chart-fill"></i> Visão Geral de Inatividade por Faixas</h6>
                <canvas id="chartFaixas" height="110"></canvas>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card card-shopee p-3">
                <h6 class="fw-bold text-orange mb-3"><i class="bi bi-pie-chart-fill"></i> Distribuição Operacional</h6>
                <canvas id="chartProporcao" height="180"></canvas>
            </div>
        </div>
    </div>

    <!-- TABELA DETALHADA COM FILTROS -->
    <div class="card card-shopee p-4 mb-5">
        <div class="row g-3 align-items-center mb-3">
            <div class="col-md-4">
                <h5 class="fw-bold text-orange mb-0"><i class="bi bi-people-fill"></i> Base Completa de Motoristas Ativos</h5>
            </div>
            <div class="col-md-3">
                <select id="selectStatus" class="form-select form-select-shopee">
                    <option value="TODOS">Todos os Status</option>
                    <option value="Ativo (0 a 7 dias)">Ativos (0 a 7 dias)</option>
                    <option value="Alerta (8 a 20 dias)">Alerta (8 a 20 dias)</option>
                    <option value="Inativo / Churn (> 20 dias)">Churn / Inativo (>20 dias)</option>
                    <option value="Sem Rotas Registradas">Sem Rotas Registradas</option>
                </select>
            </div>
            <div class="col-md-5">
                <div class="input-group">
                    <span class="input-group-text bg-dark text-orange border-secondary"><i class="bi bi-search"></i></span>
                    <input type="text" id="searchInput" class="form-control form-control-shopee" placeholder="Buscar por ID, Nome, Veículo ou Telefone...">
                </div>
            </div>
        </div>

        <div class="table-responsive">
            <table class="table table-shopee align-middle" id="driversTable">
                <thead>
                    <tr>
                        <th>Driver ID</th>
                        <th>Nome do Motorista</th>
                        <th>Veículo</th>
                        <th>Última Rota</th>
                        <th>Dias Sem Rota</th>
                        <th>Status</th>
                        <th class="text-center">Contato WhatsApp</th>
                    </tr>
                </thead>
                <tbody>
                    {tabela_rows}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    Chart.defaults.color = '#AAAAAA';
    Chart.defaults.borderColor = '#2D2D2D';

    const ctxFaixas = document.getElementById('chartFaixas').getContext('2d');
    new Chart(ctxFaixas, {{
        type: 'bar',
        data: {{
            labels: ['0 a 7 Dias (OK)', '8 a 20 Dias (Alerta)', '> 20 Dias (Churn)', 'Sem Histórico'],
            datasets: [{{
                label: 'Quantidade de Motoristas',
                data: [{count_operacionais}, {count_alerta}, {count_churn_20d}, {count_sem_rota}],
                backgroundColor: ['#00c853', '#ffab00', '#ff3d00', '#616161'],
                borderRadius: 6
            }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
    }});

    const ctxProp = document.getElementById('chartProporcao').getContext('2d');
    new Chart(ctxProp, {{
        type: 'doughnut',
        data: {{
            labels: ['Operacionais', 'Alerta', 'Churn (>20d)', 'Sem Rota'],
            datasets: [{{
                data: [{count_operacionais}, {count_alerta}, {count_churn_20d}, {count_sem_rota}],
                backgroundColor: ['#00c853', '#ffab00', '#ff3d00', '#616161'],
                borderWidth: 2,
                borderColor: '#1E1E1E'
            }}]
        }},
        options: {{ responsive: true, cutout: '70%' }}
    }});

    function aplicarFiltros() {{
        let textFilter = document.getElementById('searchInput').value.toLowerCase();
        let statusFilter = document.getElementById('selectStatus').value;
        
        let rows = document.querySelectorAll('#driversTable tbody tr');
        rows.forEach(row => {{
            let textMatch = row.textContent.toLowerCase().includes(textFilter);
            let statusMatch = (statusFilter === 'TODOS') || (row.getAttribute('data-status') === statusFilter);
            
            if (textMatch && statusMatch) {{
                row.style.display = '';
            }} else {{
                row.style.display = 'none';
            }}
        }});
    }}

    document.getElementById('searchInput').addEventListener('keyup', aplicarFiltros);
    document.getElementById('selectStatus').addEventListener('change', aplicarFiltros);
</script>
</body>
</html>
"""

with open(PATH_SAIDA_HTML, 'w', encoding='utf-8') as f:
  f.write(html_template)

msg_final = f"""
==================================================
 DASHBOARD SHOPEE BLACK EDITION GERADO COM SUCESSO!
==================================================
Relatório CSV Completo: {PATH_SAIDA_CSV}
Dashboard HTML:         {PATH_SAIDA_HTML}

 Resumo Executivo:
 - Total Base Ativa:           {total_ativos}
 - Operacionais (0 a 7d):      {count_operacionais}
 - Em Alerta (8 a 20d):        {count_alerta}
 - Churn / Crítico (> 20d):    {count_churn_20d} ({pct_churn:.1f}%)
 - Sem Rotas Registradas:      {count_sem_rota}
==================================================
"""
print(msg_final)