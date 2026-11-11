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
    return pd.DataFrame(columns=["Driver ID", "Nome", "Telefone", "Veiculo", "Data Acionamento", "Data Reunião", "Horário", "Status", "Endereço HUB / Pauta"])

def salvar_historico(df):
    df.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def registrar_ou_atualizar_driver(driver_id, nome, telefone, veiculo, data_reuniao_str, hora_reuniao_str, endereco_pauta, novo_status="Driver Acionado"):
    df_hist = carregar_historico()
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Se já existir o registro para este motorista na mesma data de reunião, atualiza o status
    idx = df_hist[(df_hist["Driver ID"] == str(driver_id)) & (df_hist["Data Reunião"] == data_reuniao_str)].index
    
    if not idx.empty:
        df_hist.loc[idx, "Status"] = novo_status
        df_hist.loc[idx, "Data Acionamento"] = agora_str
    else:
        novo = pd.DataFrame([{
            "Driver ID": str(driver_id),
            "Nome": str(nome),
            "Telefone": str(telefone),
            "Veiculo": str(veiculo),
            "Data Acionamento": agora_str,
            "Data Reunião": data_reuniao_str,
            "Horário": hora_reuniao_str,
            "Status": novo_status,
            "Endereço HUB / Pauta": str(endereco_pauta)
        }])
        df_hist = pd.concat([novo, df_hist], ignore_index=True)

    salvar_historico(df_hist)

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Central de Agendamentos & Fila de Treinamento Presencial</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Gerenciamento de status, alteração de horários e envio de convites com endereço presencial do HUB.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum histórico registrado até o momento. Utilize a aba Control Tower Churn para disparar convites ou agendar reuniões.")
        return

    # 1. ALTERAÇÃO DE STATUS EM MASSA
    st.subheader("⚡ Atualização de Status em Massa")
    st.caption("Selecione múltiplos motoristas abaixo para alterar o status da reintegração simultaneamente:")

    col_m1, col_m2, col_m3 = st.columns([3, 2, 1.5])
    
    lista_drivers_opcoes = [f"{r['Driver ID']} - {r['Nome']} (Atual: {r['Status']})" for _, r in df_hist.iterrows()]
    
    with col_m1:
        drivers_selecionados_massa = st.multiselect("Selecione os motoristas:", options=lista_drivers_opcoes)
    with col_m2:
        novo_status_massa = st.selectbox(
            "Novo Status para a seleção:",
            ["Aguardando Reunião", "Driver Acionado", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"]
        )
    with col_m3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("✅ Aplicar em Massa", type="primary", use_container_width=True):
            if not drivers_selecionados_massa:
                st.warning("Selecione ao menos um motorista!")
            else:
                ids_para_alterar = [item.split(" - ")[0] for item in drivers_selecionados_massa]
                df_hist.loc[df_hist["Driver ID"].isin(ids_para_alterar), "Status"] = novo_status_massa
                salvar_historico(df_hist)
                st.success(f"Status de {len(ids_para_alterar)} motorista(s) alterado para '{novo_status_massa}'!")
                st.rerun()

    st.divider()

    # 2. DISPARO RÁPIDO & MUDANÇA DE STATUS AUTOMÁTICA
    st.subheader("📲 Disparos Rápidos no WhatsApp (Muda automaticamente para 'Driver Acionado')")
    
    for idx, row in df_hist.head(10).iterrows():
        c1, c2, c3, c4 = st.columns([1.5, 2.5, 2.5, 1.5])
        with c1:
            st.markdown(f"**ID:** `{row['Driver ID']}`")
        with c2:
            st.markdown(f"**{row['Nome']}** ({row['Veiculo']})")
        with c3:
            st.caption(f"📅 Reunião: {row['Data Reunião']} às {row['Horário']}\n📍 {row['Endereço HUB / Pauta']}")
        with c4:
            phone = str(row['Telefone'])
            if phone and len(phone) >= 10:
                msg_txt = f"Olá {row['Nome']}! Confirmamos seu Treinamento Presencial da SPX para o dia {row['Data Reunião']} às {row['Horário']}.\n📍 Endereço: {row['Endereço HUB / Pauta']}."
                texto_enc = urllib.parse.quote(msg_txt)
                url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={texto_enc}"
                
                # Botão com link do Whats que executa callback para mudar o status
                if st.button(f"📲 Acionar Whats", key=f"btn_wa_{row['Driver ID']}_{idx}"):
                    registrar_ou_atualizar_driver(
                        row['Driver ID'], row['Nome'], row['Telefone'], row['Veiculo'],
                        row['Data Reunião'], row['Horário'], row['Endereço HUB / Pauta'],
                        novo_status="Driver Acionado"
                    )
                    st.markdown(f'<script>window.open("{url_wa}", "_blank");</script>', unsafe_allow_html=True)
                    st.toast(f"Status do driver {row['Driver ID']} alterado para 'Driver Acionado'!", icon="📲")
                    st.rerun()
            else:
                st.caption("Sem WhatsApp")

    st.divider()

    # 3. TABELA EDITÁVEL INDIVIDUAL DE STATUS E INFORMAÇÕES
    st.subheader("📊 Histórico Geral de Reintegração (Edição Individual)")
    st.caption("Você pode alterar manualmente qualquer célula (Status, Data da Reunião, Horário ou Endereço) diretamente abaixo:")

    df_editado = st.data_editor(
        df_hist,
        column_config={
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Data Reunião": st.column_config.TextColumn("Data da Reunião Presencial"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Endereço HUB / Pauta": st.column_config.TextColumn("Endereço do HUB / Informações"),
            "Status": st.column_config.SelectboxColumn(
                "Status da Reintegração",
                options=["Aguardando Reunião", "Driver Acionado", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"],
                required=True
            ),
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Salvar Alterações Tabela", type="primary"):
        salvar_historico(df_editado)
        st.toast("Todas as alterações salvas com sucesso!", icon="✅")
