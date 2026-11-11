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
    return pd.DataFrame(columns=["Driver ID", "Nome", "Telefone", "Veiculo", "Data Acionamento", "Data Reunião", "Horário", "Status", "Observação"])

def salvar_historico(df):
    df.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def registrar_acionamento_massa(drivers_list, data_reuniao, hora_reuniao, pauta):
    df = carregar_historico()
    novos = []
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    for d in drivers_list:
        novos.append({
            "Driver ID": d.get("id", ""),
            "Nome": d.get("nome", ""),
            "Telefone": d.get("phone", ""),
            "Veiculo": d.get("veiculo", ""),
            "Data Acionamento": agora_str,
            "Data Reunião": data_reuniao.strftime("%d/%m/%Y"),
            "Horário": hora_reuniao.strftime("%H:%M"),
            "Status": "Aguardando Reunião",
            "Observação": f"Pauta: {pauta}"
        })
    
    if novos:
        df_novos = pd.DataFrame(novos)
        df_final = pd.concat([df_novos, df], ignore_index=True).drop_duplicates(subset=["Driver ID", "Data Reunião"], keep="first")
        salvar_historico(df_final)

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Gestão de Reengajamento & CRM de Reuniões</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Acompanhamento de disparos em massa, presenças e status de reintegração dos motoristas dormentes.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Configurar Pauta da Reunião")
        data_reuniao = st.date_input("Data da Reunião", value=datetime.now())
        hora_reuniao = st.time_input("Horário da Reunião", value=datetime.now().time())
        pauta = st.selectbox("Pauta Principal", ["Reintegração de Base Dormente", "Alinhamento de Rotas/Galpão", "Aumento de Carga / Migração"])
        link_reuniao = st.text_input("Link da Reunião (Meet/Teams)", "https://meet.google.com/spx-fleet-lsp93")

    with col2:
        st.subheader("2. Modelo do Mensagem Padrão")
        msg_template = f"""Olá! Notamos que você está sem rotas atribuídas recentemente no galpão SPX Logistics.

Gostaríamos de convidar você para uma reunião de alinhamento e retorno às atividades!

📌 *Pauta:* {pauta}
📅 *Data:* {data_reuniao.strftime('%d/%m/%Y')} às {hora_reuniao.strftime('%H:%M')}
🔗 *Link:* {link_reuniao}

Por favor, responda confirmando sua participação!
Equipe Fleet - SPX Logistics"""

        st.text_area("Pré-visualização do texto:", value=msg_template, height=170)

    st.divider()

    st.subheader("3. Histórico e Controle de Reintegração")
    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum acionamento em massa registrado ainda. Utilize a aba Control Tower Churn para selecionar os motoristas e realizar o disparo.")
    else:
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
                "Observação": st.column_config.TextColumn("Anotações")
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("💾 Salvar Alterações de Status"):
            salvar_historico(df_editado)
            st.success("Status atualizados com sucesso!")
