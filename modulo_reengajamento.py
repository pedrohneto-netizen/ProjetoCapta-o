from datetime import datetime
import os
import time
import pandas as pd
import requests
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

# ==========================================
# CONFIGURAÇÃO DA Z-API (SUBSTITUA PELOS SEUS DADOS)
# ==========================================
ZAPI_INSTANCE_ID = st.secrets.get("ZAPI_INSTANCE_ID", "SUA_INSTANCIA_AQUI")
ZAPI_TOKEN = st.secrets.get("ZAPI_TOKEN", "SEU_TOKEN_AQUI")
ZAPI_CLIENT_TOKEN = st.secrets.get("ZAPI_CLIENT_TOKEN", "SEU_CLIENT_TOKEN_AQUI")

def enviar_mensagem_zapi(telefone: str, mensagem: str) -> bool:
    """Envia uma mensagem de texto via Z-API."""
    if not ZAPI_INSTANCE_ID or ZAPI_INSTANCE_ID == "SUA_INSTANCIA_AQUI":
        st.error("⚠️ Insira as credenciais da Z-API no arquivo modulo_reengajamento.py!")
        return False

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": telefone,
        "message": mensagem
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Erro ao enviar para {telefone}: {e}")
        return False

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
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>🤖 Central de Agendamentos & Bot de Disparo API</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Envio 100% automático de convites via API para WhatsApp com atualização imediata de status.</p>
        </div>
    """, unsafe_allow_html=True)

    drivers_importados = st.session_state.get("drivers_para_agendar", [])
    if drivers_importados:
        st.success(f"📥 **{len(drivers_importados)} motorista(s)** prontos para acionamento!")

    df_hist = carregar_historico()

    # 1. PARÂMETROS DO ACIONAMENTO
    st.subheader("⚡ 1. Parâmetros da Mensagem")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        end_hub = st.text_input("📍 Endereço do HUB / Local do Treinamento Presencial", "Av. dos Estados, 7328 - Parque Jaçatuba - Santo André / SP")
    with col_c2:
        dt_treino = st.date_input("Data do Treinamento", value=datetime.now())
    with col_c3:
        hr_treino = st.time_input("Horário", value=datetime.now().time())

    pauta_txt = st.selectbox("Pauta / Assunto", ["Reintegração & Capacitação Presencial", "Alinhamento de Rotas/Galpão", "Aumento de Carga / Migração"])

    st.divider()

    # 2. SELEÇÃO DA FILA E DISPARO VIA BOT API
    st.subheader("🤖 2. Disparo Automático via API (100% Sem Mão)")

    if df_hist.empty:
        st.info("Nenhum histórico gravado. Selecione motoristas na tela Control Tower Churn primeiro.")
        return

    # Opção de Selecionar Quem Disparar
    lista_opcoes = [f"{r['Driver ID']} - {r['Nome']} ({r['Telefone']}) | Status: {r['Status']}" for _, r in df_hist.iterrows()]
    
    drivers_para_disparar = st.multiselect(
        "Selecione os motoristas que receberão o disparo via WhatsApp:",
        options=lista_opcoes,
        default=lista_opcoes # Por padrão já seleciona todos
    )

    if st.button("🚀 DISPARAR MENSAGENS EM MASSA VIA API", type="primary", use_container_width=True):
        if not drivers_para_disparar:
            st.warning("Selecione pelo menos 1 motorista para disparar!")
        else:
            ids_alvo = [item.split(" - ")[0] for item in drivers_para_disparar]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            sucessos = 0
            falhas = 0
            total_items = len(ids_alvo)

            for index, driver_id in enumerate(ids_alvo):
                # Busca registro no DataFrame
                idx_df = df_hist[df_hist["Driver ID"] == str(driver_id)].index
                if idx_df.empty:
                    continue

                row = df_hist.loc[idx_df[0]]
                nome = row["Nome"]
                telefone = str(row["Telefone"])

                status_text.text(f"⏳ Enviando mensagem para: {nome} ({telefone})... [{index+1}/{total_items}]")

                mensagem_envio = f"""Olá *{nome}*! 👋

Gostaríamos de confirmar seu *Treinamento Presencial da SPX Logistics*:

📅 *Data:* {dt_treino.strftime('%d/%m/%Y')} às {hr_treino.strftime('%H:%M')}
📍 *Local:* {end_hub}
📌 *Pauta:* {pauta_txt}

Por favor, responda a esta mensagem confirmando sua presença!
*Equipe Fleet - SPX Logistics*"""

                if telefone and len(telefone) >= 10:
                    enviado = enviar_mensagem_zapi(telefone, mensagem_envio)
                    if enviado:
                        df_hist.loc[idx_df[0], "Status"] = "Driver Acionado"
                        df_hist.loc[idx_df[0], "Data Acionamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        sucessos += 1
                    else:
                        falhas += 1
                else:
                    falhas += 1

                # Atualiza barra de progresso
                progress_bar.progress((index + 1) / total_items)
                time.sleep(1) # Delay de 1s de segurança entre disparos para evitar bloqueios da operadora

            # Salva o arquivo CSV atualizado com os novos status "Driver Acionado"
            salvar_historico(df_hist)
            status_text.empty()
            st.success(f"🎉 Processo concluído! {sucessos} mensagens enviadas com sucesso e status atualizados para 'Driver Acionado'. ({falhas} falhas)")
            st.rerun()

    st.divider()

    # 3. GESTÃO E EDIÇÃO MANUAL DE STATUS
    st.subheader("📊 3. Histórico e Controle Gerencial de Status")
    
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

    if st.button("💾 Salvar Alterações Manuais no Histórico", type="secondary"):
        salvar_historico(df_editado)
        st.toast("Histórico atualizado com sucesso!", icon="💾")
