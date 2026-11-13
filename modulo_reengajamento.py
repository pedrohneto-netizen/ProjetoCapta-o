from datetime import datetime
import os
import pandas as pd
import streamlit as st

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


def renderizar_modulo_reengajamento():
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
        key="tabela_edicao_historico_modular"
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

    # 5. EXPORTAÇÃO DE RELATÓRIO & EXTENSÃO WHATSAPP
    st.subheader("📥 Exportação de Relatórios & Fila WhatsApp")

    c_exp1, c_exp2, c_exp3 = st.columns(3)

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
