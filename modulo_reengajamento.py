from datetime import datetime
import os
import pandas as pd
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

COLUNAS_HISTORICO = [
    "Driver ID",
    "Nome",
    "Telefone",
    "Veiculo",
    "Data Acionamento",
    "Data Reunião",
    "Horário",
    "Status",
    "Observação / Tratativa",
    "Endereço HUB / Pauta"
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


def registrar_acionamentos_lote(registros: list):
    """Adiciona ou atualiza acionamentos preservando todo o histórico anterior."""
    df_atual = carregar_historico()
    df_novos = pd.DataFrame(registros)
    df_combinado = pd.concat([df_novos, df_atual], ignore_index=True)
    salvar_historico(df_combinado)


def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Histórico de Acionamentos, Tratativas & Relatórios</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Registro permanente de situações, disparo em massa via extensão e extração de relatórios gerenciais.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum acionamento registrado ainda. Vá até a aba **📊 Control Tower Churn**, selecione os motoristas e registre o acionamento.")
        return

    # ==========================================
    # 1. MÉTRICAS RÁPIDAS DO HISTÓRICO
    # ==========================================
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Registros", len(df_hist))
    m2.metric("Drivers Acionados", len(df_hist[df_hist["Status"] == "Driver Acionado"]))
    m3.metric("Confirmados / Reintegrados", len(df_hist[df_hist["Status"].isin(["Confirmado", "Reintegrado"])]))
    m4.metric("Sem Resposta / Recusa", len(df_hist[df_hist["Status"].isin(["Sem Resposta", "Sem Interesse", "Número Inválido"])]))

    st.divider()

    # ==========================================
    # 2. EXPORTAÇÃO PARA EXTENSÃO WHATSAPP (OPÇÃO A)
    # ==========================================
    st.subheader("⚡ 1. Disparo em Massa via Extensão Chrome (Opção A)")
    
    lista_export = []
    for _, r in df_hist[df_hist["Status"].isin(["Aguardando Reunião", "Driver Acionado"])].iterrows():
        phone = str(r["Telefone"]).strip()
        if phone and len(phone) >= 10:
            msg = f"Olá {r['Nome']}! Aqui é da equipe SPX Logistics (LSP93). Confirmamos seu Treinamento Presencial para {r['Data Reunião']} às {r['Horário']}. Local: {r['Endereço HUB / Pauta']}. Responda para confirmar!"
            lista_export.append(f"{phone};{msg}")

    csv_extensao = "Phone;Message\n" + "\n".join(lista_export)

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label=f"📥 Baixar CSV para Extensão WhatsApp ({len(lista_export)} contatos)",
            data=csv_extensao,
            file_name=f"fila_extensao_spx_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    with col_exp2:
        if st.button("✅ Marcar 'Aguardando Reunião' como 'Driver Acionado'", use_container_width=True):
            mask = df_hist["Status"] == "Aguardando Reunião"
            df_hist.loc[mask, "Status"] = "Driver Acionado"
            df_hist.loc[mask, "Data Acionamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            salvar_historico(df_hist)
            st.toast("Status atualizados para 'Driver Acionado'!", icon="✅")
            st.rerun()

    st.divider()

    # ==========================================
    # 3. REGISTRO DE SITUAÇÃO & HISTÓRICO EDITÁVEL
    # ==========================================
    st.subheader("📝 2. Histórico Completo & Atualização da Situação do Acionamento")
    st.caption("Dê um duplo clique nas colunas **Status** ou **Observação / Tratativa** para registrar o retorno de cada motorista:")

    filtro_status_hist = st.multiselect(
        "Filtrar histórico por situação:",
        options=["Aguardando Reunião", "Driver Acionado", "Sem Resposta", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse", "Número Inválido"],
        default=[]
    )

    df_para_editar = df_hist.copy()
    if filtro_status_hist:
        df_para_editar = df_para_editar[df_para_editar["Status"].isin(filtro_status_hist)]

    df_editado = st.data_editor(
        df_para_editar,
        column_config={
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome do Motorista", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Veiculo": st.column_config.TextColumn("Veículo", disabled=True),
            "Data Acionamento": st.column_config.TextColumn("Data/Hora Acionamento", disabled=True),
            "Data Reunião": st.column_config.TextColumn("Data Reunião"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Status": st.column_config.SelectboxColumn(
                "Situação do Acionamento",
                options=[
                    "Aguardando Reunião",
                    "Driver Acionado",
                    "Sem Resposta",
                    "Confirmado",
                    "Reintegrado",
                    "Faltou",
                    "Sem Interesse",
                    "Número Inválido"
                ],
                required=True
            ),
            "Observação / Tratativa": st.column_config.TextColumn("Observação / Retorno do Driver", width="large"),
            "Endereço HUB / Pauta": st.column_config.TextColumn("Local HUB / Pauta")
        },
        hide_index=True,
        use_container_width=True,
        key="editor_historico_completo"
    )

    if st.button("💾 SALVAR SITUAÇÕES E TRATATIVAS NO HISTÓRICO", type="primary"):
        df_hist.update(df_editado)
        salvar_historico(df_hist)
        st.toast("Histórico salvo com sucesso!", icon="💾")
        st.rerun()

    st.divider()

    # ==========================================
    # 4. EXTRAÇÃO DE RELATÓRIO GERENCIAL (EXCEL / CSV)
    # ==========================================
    st.subheader("📊 3. Extrair Relatório Gerencial de Acionamentos")
    st.caption("Exporte o histórico completo com todas as situações e observações prontas para abrir no Excel:")

    csv_relatorio_excel = df_hist.to_csv(index=False, sep=";", encoding="utf-8-sig")

    col_rel1, col_rel2 = st.columns([2, 1])
    with col_rel1:
        st.download_button(
            label="📥 EXTRAIR RELATÓRIO COMPLETO (.CSV / EXCEL)",
            data=csv_relatorio_excel,
            file_name=f"Relatorio_Acionamentos_Churn_LSP93_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    with col_rel2:
        if st.button("🗑️ Limpar Todo o Histórico", use_container_width=True):
            if os.path.exists(ARQUIVO_HISTORICO):
                os.remove(ARQUIVO_HISTORICO)
            st.toast("Histórico zerado.", icon="🗑️")
            st.rerun()
