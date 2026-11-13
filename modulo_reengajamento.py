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
            return df[COLUNAS_HISTORICO].fillna("")
        except Exception:
            pass
    return pd.DataFrame(columns=COLUNAS_HISTORICO)


def salvar_historico(df: pd.DataFrame):
    for col in COLUNAS_HISTORICO:
        if col not in df.columns:
            df[col] = ""
    df[COLUNAS_HISTORICO].to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")


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
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Histórico de Acionamentos, Tratativas & Relatórios</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Consulte os acionamentos realizados pela equipe, atualize o retorno do motorista (com data/hora automática) e extraia relatórios.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum acionamento registrado ainda. Vá até a aba **📊 Control Tower Churn** e clique para acionar um motorista!")
        return

    # ==========================================
    # 1. KPIs DO HISTÓRICO DA EQUIPE
    # ==========================================
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Acionados", len(df_hist))
    m2.metric("Aguardando Retorno", len(df_hist[df_hist["Status"] == "Driver Acionado"]))
    m3.metric("Confirmados / Reintegrados", len(df_hist[df_hist["Status"].isin(["Confirmado", "Reintegrado"])]))
    m4.metric("Sem Resposta / Recusa", len(df_hist[df_hist["Status"].isin(["Sem Resposta", "Sem Interesse", "Número Inválido"])]))

    st.divider()

    # ==========================================
    # 2. FILTROS POR ANALISTA E STATUS
    # ==========================================
    st.subheader("📝 1. Atualizar Situação e Retorno do Motorista")
    st.caption("Altere a coluna **Status** ou **Observação / Tratativa** e clique em **Salvar**. O sistema gravará automaticamente a **Data/Hora da atualização**!")

    f1, f2 = st.columns(2)
    with f1:
        analistas_unicos = ["TODOS"] + sorted(list(set(df_hist["Analista Responsável"].replace("", "Não Informado").unique())))
        analista_filtro = st.selectbox("Filtrar por Analista Responsável:", analistas_unicos)
    with f2:
        status_filtro = st.multiselect(
            "Filtrar por Status:",
            options=["Driver Acionado", "Aguardando Reunião", "Sem Resposta", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse", "Número Inválido"],
            default=[]
        )

    df_view = df_hist.copy()
    if analista_filtro != "TODOS":
        df_view = df_view[df_view["Analista Responsável"].replace("", "Não Informado") == analista_filtro]
    if status_filtro:
        df_view = df_view[df_view["Status"].isin(status_filtro)]

    df_editado = st.data_editor(
        df_view,
        column_config={
            "ID Registro": None,  # Oculta ID técnico
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome do Motorista", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Veiculo": st.column_config.TextColumn("Veículo", disabled=True),
            "Analista Responsável": st.column_config.TextColumn("Analista", disabled=True),
            "Tipo de Acionamento": st.column_config.TextColumn("Tipo Acionamento", disabled=True),
            "Data/Hora Acionamento": st.column_config.TextColumn("Data/Hora Inicial", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status Atual",
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
            "Última Atualização": st.column_config.TextColumn("Data/Hora Atualização", disabled=True),
            "Observação / Tratativa": st.column_config.TextColumn("Observação / Retorno", width="large"),
            "Data Reunião": st.column_config.TextColumn("Data Reunião"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Endereço HUB": st.column_config.TextColumn("Endereço HUB")
        },
        hide_index=True,
        use_container_width=True,
        key="editor_historico_equipe"
    )

    if st.button("💾 SALVAR ATUALIZAÇÕES (GRAVA DATA/HORA AUTOMATICAMENTE)", type="primary"):
        agora_upd = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        alteracoes = 0

        for idx, row_ed in df_editado.iterrows():
            id_reg = row_ed["ID Registro"]
            mask = df_hist["ID Registro"] == id_reg
            if mask.any():
                idx_orig = df_hist[mask].index[0]
                status_antigo = df_hist.loc[idx_orig, "Status"]
                obs_antiga = df_hist.loc[idx_orig, "Observação / Tratativa"]

                # Se mudou status ou observação, atualiza automaticamente data e hora
                if (
                    row_ed["Status"] != status_antigo
                    or row_ed["Observação / Tratativa"] != obs_antiga
                    or row_ed["Data Reunião"] != df_hist.loc[idx_orig, "Data Reunião"]
                    or row_ed["Horário"] != df_hist.loc[idx_orig, "Horário"]
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
        else:
            st.toast("Nenhuma alteração pendente detectada.", icon="ℹ️")
        st.rerun()

    st.divider()

    # ==========================================
    # 3. EXPORTAÇÃO PARA EXTENSÃO & RELATÓRIO EXCEL
    # ==========================================
    st.subheader("📊 2. Exportação em Massa & Relatório Gerencial")

    col_b1, col_b2, col_b3 = st.columns(3)

    # CSV para Extensão Chrome
    lista_ext = []
    for _, r in df_hist[df_hist["Status"].isin(["Driver Acionado", "Aguardando Reunião"])].iterrows():
        ph = str(r["Telefone"]).strip()
        if ph and len(ph) >= 10:
            msg = f"Olá {r['Nome']}! Aqui é {r['Analista Responsável']} da equipe SPX Logistics (LSP93). Entramos em contato sobre: {r['Tipo de Acionamento']}. Podemos conversar?"
            lista_ext.append(f"{ph};{msg}")
    csv_ext = "Phone;Message\n" + "\n".join(lista_ext)

    with col_b1:
        st.download_button(
            label=f"📲 Baixar CSV p/ Extensão Whats ({len(lista_ext)})",
            data=csv_ext,
            file_name=f"extensao_whats_spx_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Relatório Completo Excel
    df_relatorio = df_hist.drop(columns=["ID Registro"], errors="ignore")
    csv_rel = df_relatorio.to_csv(index=False, sep=";", encoding="utf-8-sig")

    with col_b2:
        st.download_button(
            label="📥 EXTRAIR RELATÓRIO COMPLETO (.CSV / EXCEL)",
            data=csv_rel,
            file_name=f"Relatorio_Acionamentos_LSP93_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

    with col_b3:
        if st.button("🗑️ Zerar Histórico", use_container_width=True):
            if os.path.exists(ARQUIVO_HISTORICO):
                os.remove(ARQUIVO_HISTORICO)
            st.toast("Histórico limpo.", icon="🗑️")
            st.rerun()
