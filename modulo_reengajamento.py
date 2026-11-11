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
    return pd.DataFrame(columns=["Driver ID", "Nome", "Veiculo", "Data Acionamento", "Data Reunião", "Horario", "Status", "Observacao"])

def salvar_historico(df):
    df.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def renderizar_modulo_reengajamento():
    st.markdown("""
        <h2 style='color: #EE4D2D; font-weight: 800; margin-bottom: 5px;'>
            📅 Gestão de Reengajamento & Agendamento de Reuniões
        </h2>
        <p style='color: #AAA; font-size: 0.95rem; margin-bottom: 25px;'>
            Ferramenta de controle de disparos em massa, agendamento e acompanhamento de reuniões com motoristas dormentes.
        </p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Configurar Convite & Pauta")
        data_reuniao = st.date_input("Data da Reunião", value=datetime.now())
        hora_reuniao = st.time_input("Horário da Reunião", value=datetime.now().time())
        pauta = st.selectbox("Pauta da Reunião", ["Reintegração de Base Dormente", "Alinhamento de Rotas/Galpão", "Aumento de Capacidade / Migração"])
        link_reuniao = st.text_input("Link da Reunião (Meet / Teams / Zoom)", "https://meet.google.com/spx-fleet-lsp93")

    with col2:
        st.subheader("2. Template da Mensagem")
        msg_template = f"""Olá! Notamos que você está sem rotas atribuídas recentemente no galpão SPX Logistics.

Gostaríamos de convidar você para uma reunião rápida de alinhamento e retorno às atividades!

📌 *Pauta:* {pauta}
📅 *Data:* {data_reuniao.strftime('%d/%m/%Y')} às {hora_reuniao.strftime('%H:%M')}
🔗 *Link de Acesso:* {link_reuniao}

Por favor, responda esta mensagem confirmando sua presença!
Equipe Fleet - SPX Logistics"""

        st.text_area("Pré-visualização do texto para envio:", value=msg_template, height=180)
        
        if st.button("📋 Copiar Mensagem Padrão"):
            st.toast("Mensagem copiada com sucesso!", icon="✅")

    st.divider()

    st.subheader("3. Histórico e Status de Reintegração dos Drivers")
    
    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum acionamento registrado ainda. Utilize o dashboard para selecionar os motoristas e iniciar os agendamentos.")
    else:
        st.caption("Altere o status diretamente na tabela abaixo para acompanhar a evolução:")
        df_editado = st.data_editor(
            df_hist,
            column_config={
                "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
                "Nome": st.column_config.TextColumn("Nome do Motorista", disabled=True),
                "Status": st.column_config.SelectboxColumn(
                    "Status da Reintegração",
                    options=["Aguardando Reunião", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"],
                    required=True
                ),
                "Observacao": st.column_config.TextColumn("Observações / Anotações")
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("💾 Salvar Alterações de Status"):
            salvar_historico(df_editado)
            st.success("Histórico atualizado com sucesso!")
