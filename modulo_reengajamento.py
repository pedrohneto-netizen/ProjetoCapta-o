from datetime import datetime
import os
import pandas as pd
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            return pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
        except Exception:
            pass
    return pd.DataFrame(columns=["Driver ID", "Nome", "Telefone", "Veiculo", "Data Acionamento", "Data Reunião", "Horário", "Status", "Endereço HUB / Pauta"])

def salvar_historico(df):
    df.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Central de Agendamentos & Fila de Envio (Opção A: Extensão)</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Gere o lote formatado para disparo automático via extensão do Chrome e gerencie os status de reintegração.</p>
        </div>
    """, unsafe_allow_html=True)

    drivers_importados = st.session_state.get("drivers_para_agendar", [])
    if drivers_importados:
        st.success(f"📥 **{len(drivers_importados)} motorista(s)** importado(s) do Dashboard com sucesso!")

    df_hist = carregar_historico()

    # ==========================================
    # 1. PARÂMETROS DO TREINAMENTO PRESENCIAL
    # ==========================================
    st.subheader("📍 1. Configuração do Convite Presencial")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        end_hub = st.text_input("📍 Endereço do HUB / Local do Treinamento", "Av. dos Estados, 7328 - Parque Jaçatuba - Santo André / SP")
    with col_c2:
        dt_treino = st.date_input("Data do Treinamento", value=datetime.now())
    with col_c3:
        hr_treino = st.time_input("Horário", value=datetime.now().time())

    pauta_txt = st.selectbox("Pauta Principal", ["Reintegração & Capacitação Presencial", "Alinhamento de Rotas/Galpão", "Aumento de Carga / Migração"])

    st.divider()

    # ==========================================
    # 2. DISPARO EM MASSA VIA EXTENSÃO CHROME
    # ==========================================
    st.subheader("⚡ 2. Exportação de Fila para Extensão WhatsApp")

    if df_hist.empty:
        st.info("Nenhum histórico gravado. Selecione motoristas na aba Control Tower Churn primeiro.")
        return

    # Prepara mensagens formatadas para exportação
    lista_export = []
    for _, r in df_hist.iterrows():
        phone = str(r["Telefone"])
        if phone and len(phone) >= 10:
            msg = f"Olá {r['Nome']}! Confirmamos seu Treinamento Presencial da SPX Logistics para {r['Data Reunião']} às {r['Horário']}. 📍 Endereço: {r['Endereço HUB / Pauta']} ({pauta_txt}). Favor confirmar presença!"
            lista_export.append(f"{phone};{msg}")

    csv_extensao = "Phone;Message\n" + "\n".join(lista_export)

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.download_button(
            label="📥 Baixar Arquivo de Envio para a Extensão (.CSV)",
            data=csv_extensao,
            file_name=f"disparo_whatsapp_spx_{datetime.now().strftime('%d%m%Y_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
        st.caption("💡 Importe este arquivo na sua extensão (ex: WAPlus ou WA Web Plus) no WhatsApp Web para disparar 100% automático.")

    with col_exp2:
        if st.button("✅ Marcar Fila Exportada como 'Driver Acionado'", use_container_width=True):
            df_hist["Status"] = "Driver Acionado"
            df_hist["Data Acionamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            salvar_historico(df_hist)
            st.toast("Status da fila atualizado para 'Driver Acionado'!", icon="✅")
            st.rerun()

    st.divider()

    # ==========================================
    # 3. CONTROLE DE STATUS E EDIÇÃO MANUAL
    # ==========================================
    st.subheader("📊 3. Histórico Geral & Atualização de Status")
    st.caption("Altere manualmente o status, horários ou endereços de qualquer motorista na tabela abaixo:")

    df_editado = st.data_editor(
        df_hist,
        column_config={
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Data Reunião": st.column_config.TextColumn("Data Reunião"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Endereço HUB / Pauta": st.column_config.TextColumn("Local HUB / Pauta"),
            "Status": st.column_config.SelectboxColumn(
                "Status da Reintegração",
                options=["Aguardando Reunião", "Driver Acionado", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"],
                required=True
            )
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Salvar Alterações Manuais", type="secondary"):
        salvar_historico(df_editado)
        st.toast("Tabela atualizada com sucesso!", icon="💾")
