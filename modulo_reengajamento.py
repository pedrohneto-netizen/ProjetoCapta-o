from datetime import datetime
import os
import urllib.parse
import pandas as pd
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            return pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
        except Exception:
            pass
    return pd.DataFrame(columns=["Driver ID", "Nome", "Telefone", "Veiculo", "Data Acionamento", "Data Reunião", "Horário", "Status", "Observação"])

def salvar_historico(df):
    df.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Gestão de Reengajamento & Histórico de Agendamentos</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Controle de motoristas acionados em massa, status das reuniões e reintegração da base.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum acionamento registrado no histórico ainda. Faça a seleção dos motoristas no Dashboard para registrar!")
        return

    # Mensagem padrão para envio rápido no WhatsApp
    st.subheader("1. Fila de Disparo no WhatsApp (Acionamentos Recentes)")
    st.caption("Clique no botão do WhatsApp de cada motorista para abrir o chat pré-configurado:")

    for idx, row in df_hist.head(10).iterrows():
        c1, c2, c3, c4 = st.columns([1.5, 2.5, 2, 1.5])
        with c1:
            st.markdown(f"**ID:** `{row['Driver ID']}`")
        with c2:
            st.markdown(f"**{row['Nome']}** ({row['Veiculo']})")
        with c3:
            st.caption(f"📅 Reunião: {row['Data Reunião']} às {row['Horário']}")
        with c4:
            phone = str(row['Telefone'])
            if phone and len(phone) >= 10:
                texto_enc = urllib.parse.quote(f"Olá {row['Nome']}! Confirmando sua reunião de alinhamento SPX para {row['Data Reunião']} às {row['Horário']}. Pauta: {row['Observação']}.")
                url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={texto_enc}"
                st.markdown(f'<a href="{url_wa}" target="_blank" style="background-color: #25D366; color: white; padding: 5px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.8rem;">📲 Abrir Whats</a>', unsafe_allow_html=True)
            else:
                st.caption("Sem WhatsApp")

    st.divider()

    st.subheader("2. Central de Status & Controle de Reintegração")
    df_editado = st.data_editor(
        df_hist,
        column_config={
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status da Reintegração",
                options=["Aguardando Reunião", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"],
                required=True
            ),
            "Observação": st.column_config.TextColumn("Anotações / Pauta")
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Salvar Histórico e Atualizações"):
        salvar_historico(df_editado)
        st.toast("Histórico salvo com sucesso!", icon="✅")
