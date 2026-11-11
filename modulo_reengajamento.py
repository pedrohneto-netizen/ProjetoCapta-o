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

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Central de Agendamentos & Fila de Disparo</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Configure a pauta da reunião e confirme o acionamento dos motoristas pendentes.</p>
        </div>
    """, unsafe_allow_html=True)

    # 1. VERIFICA SE HÁ MOTORISTAS ENVIADOS DO DASHBOARD
    drivers_pendentes = st.session_state.get("drivers_para_agendar", [])

    if drivers_pendentes:
        st.success(f"📥 **{len(drivers_pendentes)} motorista(s)** importado(s) do Dashboard com sucesso!")
    else:
        st.info("💡 Nenhum motorista selecionado recentemente no Dashboard. Você pode visualizar o histórico abaixo ou voltar ao Dashboard para selecionar.")

    # 2. CONFIGURAÇÃO DA REUNIÃO / DISPARO
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Detalhes da Reunião")
        data_reuniao = st.date_input("Data da Reunião", value=datetime.now())
        hora_reuniao = st.time_input("Horário da Reunião", value=datetime.now().time())
        pauta = st.selectbox("Pauta da Reunião", [
            "Reintegração de Base Dormente", 
            "Alinhamento de Rotas/Galpão", 
            "Aumento de Capacidade / Migração"
        ])
        link_reuniao = st.text_input("Link da Reunião (Meet / Teams / Zoom)", "https://meet.google.com/spx-fleet-lsp93")

    with col2:
        st.subheader("2. Modelo de Mensagem Gerado")
        msg_template = f"""Olá! Notamos que você está sem rotas atribuídas recentemente no galpão SPX Logistics.

Gostaríamos de convidar você para uma reunião rápida de alinhamento e retorno às atividades!

📌 *Pauta:* {pauta}
📅 *Data:* {data_reuniao.strftime('%d/%m/%Y')} às {hora_reuniao.strftime('%H:%M')}
🔗 *Link de Acesso:* {link_reuniao}

Por favor, responda esta mensagem confirmando sua presença!
Equipe Fleet - SPX Logistics"""

        st.text_area("Pré-visualização do texto para envio:", value=msg_template, height=175)

    # 3. CONFIRMAÇÃO DA FILA DE DISPARO
    if drivers_pendentes:
        st.divider()
        st.subheader(f"3. Fila de Confirmação ({len(drivers_pendentes)} motoristas selecionados)")
        
        df_pendentes = pd.DataFrame(drivers_pendentes)
        st.dataframe(df_pendentes[["id", "nome", "veh", "phone"]].rename(columns={
            "id": "Driver ID", "nome": "Nome", "veh": "Veículo", "phone": "WhatsApp"
        }), hide_index=True, use_container_width=True)

        if st.button("✅ REGISTRAR E GERAR FILA DE ENVIOS NO WHATSAPP", type="primary"):
            df_hist = carregar_historico()
            novos_registros = []
            agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

            for d in drivers_pendentes:
                novos_registros.append({
                    "Driver ID": str(d.get("id", "")),
                    "Nome": str(d.get("nome", "")),
                    "Telefone": str(d.get("phone", "")),
                    "Veiculo": str(d.get("veh", "")),
                    "Data Acionamento": agora_str,
                    "Data Reunião": data_reuniao.strftime("%d/%m/%Y"),
                    "Horário": hora_reuniao.strftime("%H:%M"),
                    "Status": "Aguardando Reunião",
                    "Observação": f"Pauta: {pauta}"
                })

            if novos_registros:
                df_novos = pd.DataFrame(novos_registros)
                df_final = pd.concat([df_novos, df_hist], ignore_index=True).drop_duplicates(subset=["Driver ID", "Data Reunião"], keep="first")
                salvar_historico(df_final)
                
                # Limpa a sessão após confirmar
                st.session_state["drivers_para_agendar"] = []
                st.success("✅ Motoristas registrados na Central de Agendamentos! Veja a fila atualizada abaixo.")
                st.rerun()

    st.divider()

    # 4. GESTÃO E DISPARO INDIVIDUAL
    st.subheader("📊 Histórico & Controle de Reintegração")
    df_hist = carregar_historico()

    if df_hist.empty:
        st.caption("Nenhum histórico gravado.")
    else:
        st.caption("Acompanhe o status e envie as mensagens diretamente pelo WhatsApp abaixo:")
        
        # Exibe os motoristas com botão direto de disparo individual para não ser bloqueado por pop-ups
        for idx, row in df_hist.head(15).iterrows():
            col_d1, col_d2, col_d3, col_d4 = st.columns([1.5, 2.5, 2, 1.5])
            with col_d1:
                st.markdown(f"**ID:** {row['Driver ID']}")
            with col_d2:
                st.markdown(f"**{row['Nome']}** ({row['Veiculo']})")
            with col_d3:
                st.caption(f"📅 Reunião: {row['Data Reunião']} às {row['Horário']}")
            with col_d4:
                phone = str(row['Telefone'])
                if phone and len(phone) >= 10:
                    import urllib.parse
                    texto_enc = urllib.parse.quote(msg_template)
                    url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={texto_enc}"
                    st.markdown(f'<a href="{url_wa}" target="_blank" style="background-color: #25D366; color: white; padding: 5px 12px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 0.8rem;">📲 Enviar Whats</a>', unsafe_allow_html=True)
                else:
                    st.caption("Sem número")

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabela editável de status
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
            st.toast("Histórico atualizado com sucesso!", icon="✅")
