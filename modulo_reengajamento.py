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
    
    idx = df_hist[(df_hist["Driver ID"] == str(driver_id)) & (df_hist["Data Reunião"] == str(data_reuniao_str))].index
    
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
            "Data Reunião": str(data_reuniao_str),
            "Horário": str(hora_reuniao_str),
            "Status": novo_status,
            "Endereço HUB / Pauta": str(endereco_pauta)
        }])
        df_hist = pd.concat([novo, df_hist], ignore_index=True)

    salvar_historico(df_hist)

def renderizar_modulo_reengajamento():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.3); padding: 20px; border-radius: 12px; margin-bottom: 25px;">
            <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>📅 Central de Agendamentos & Fila de Treinamento Presencial</h2>
            <p style='color: #AAA; font-size: 0.9rem; margin-top: 5px;'>Gerenciamento de status, disparo em massa no WhatsApp e envio de convites para treinamento presencial.</p>
        </div>
    """, unsafe_allow_html=True)

    df_hist = carregar_historico()

    if df_hist.empty:
        st.info("Nenhum histórico registrado até o momento. Utilize a aba Control Tower Churn para selecionar motoristas!")
        return

    # ==========================================
    # 1. DISPARO EM MASSA & ATUALIZAÇÃO DE STATUS
    # ==========================================
    st.subheader("⚡ Disparo em Massa & Atualização de Status")
    st.caption("Selecione os motoristas abaixo para enviar as mensagens de WhatsApp e mudar o status automaticamente:")

    lista_drivers_opcoes = [f"{r['Driver ID']} - {r['Nome']} ({r['Veiculo']}) | Status: {r['Status']}" for _, r in df_hist.iterrows()]

    col_m1, col_m2 = st.columns([3, 1.5])
    with col_m1:
        drivers_selecionados_massa = st.multiselect(
            "Selecione os motoristas para o disparo:",
            options=lista_drivers_opcoes,
            default=lista_drivers_opcoes # Por padrão já vem todos selecionados para facilidade de acionamento
        )
    with col_m2:
        novo_status_massa = st.selectbox(
            "Novo Status após o disparo:",
            ["Driver Acionado", "Aguardando Reunião", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"]
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📲 DISPARAR WHATSAPP EM MASSA (E MUDAR STATUS)", type="primary", use_container_width=True):
            if not drivers_selecionados_massa:
                st.warning("Selecione pelo menos um motorista!")
            else:
                ids_selecionados = [item.split(" - ")[0] for item in drivers_selecionados_massa]
                links_abrir = []

                # Atualiza os status no DataFrame
                for _, r in df_hist[df_hist["Driver ID"].isin(ids_selecionados)].iterrows():
                    phone = str(r["Telefone"])
                    if phone and len(phone) >= 10:
                        msg_txt = f"Olá {r['Nome']}! Confirmamos seu Treinamento Presencial da SPX para o dia {r['Data Reunião']} às {r['Horário']}.\n📍 Endereço: {r['Endereço HUB / Pauta']}."
                        texto_enc = urllib.parse.quote(msg_txt)
                        url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={texto_enc}"
                        links_abrir.append(url_wa)

                # Atualiza o arquivo CSV para "Driver Acionado" ou o status escolhido
                df_hist.loc[df_hist["Driver ID"].isin(ids_selecionados), "Status"] = novo_status_massa
                df_hist.loc[df_hist["Driver ID"].isin(ids_selecionados), "Data Acionamento"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                salvar_historico(df_hist)

                # Gera script JS para abrir todas as abas do WhatsApp
                js_code = "".join([f'window.open("{link}", "_blank");' for link in links_abrir])
                st.markdown(f"<script>{js_code}</script>", unsafe_allow_html=True)

                st.success(f"✅ {len(ids_selecionados)} motorista(s) acionado(s) e atualizados para '{novo_status_massa}'!")
                st.rerun()

    with col_btn2:
        if st.button("📝 Apenas Atualizar Status em Lote (Sem Abrir WhatsApp)", use_container_width=True):
            if not drivers_selecionados_massa:
                st.warning("Selecione pelo menos um motorista!")
            else:
                ids_selecionados = [item.split(" - ")[0] for item in drivers_selecionados_massa]
                df_hist.loc[df_hist["Driver ID"].isin(ids_selecionados), "Status"] = novo_status_massa
                salvar_historico(df_hist)
                st.success(f"Status atualizado para '{novo_status_massa}'!")
                st.rerun()

    st.divider()

    # ==========================================
    # 2. LISTA DE DISPAROS INDIVIDUAIS
    # ==========================================
    st.subheader("⚡ Disparos Rápidos Individuais no WhatsApp")
    st.caption("Ao clicar no botão verde de cada motorista, o chat será aberto e o status mudará automaticamente para 'Driver Acionado':")

    for idx, row in df_hist.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1.2, 2.3, 2.5, 1.5, 1.5])
        with c1:
            st.markdown(f"**ID:** `{row['Driver ID']}`")
        with c2:
            st.markdown(f"**{row['Nome']}** ({row['Veiculo']})")
        with c3:
            st.caption(f"📅 Reunião: {row['Data Reunião']} às {row['Horário']}\n📍 {row['Endereço HUB / Pauta']}")
        with c4:
            st.markdown(f"**Status:** `{row['Status']}`")
        with c5:
            phone = str(row['Telefone'])
            if phone and len(phone) >= 10:
                msg_txt = f"Olá {row['Nome']}! Confirmamos seu Treinamento Presencial da SPX para o dia {row['Data Reunião']} às {row['Horário']}.\n📍 Endereço: {row['Endereço HUB / Pauta']}."
                texto_enc = urllib.parse.quote(msg_txt)
                url_wa = f"https://api.whatsapp.com/send?phone={phone}&text={texto_enc}"
                
                # HTML Nativo com clique direto e atualização de estado no backend
                if st.button(f"📲 Acionar Whats", key=f"btn_indiv_{row['Driver ID']}_{idx}"):
                    registrar_ou_atualizar_driver(
                        row['Driver ID'], row['Nome'], row['Telefone'], row['Veiculo'],
                        row['Data Reunião'], row['Horário'], row['Endereço HUB / Pauta'],
                        novo_status="Driver Acionado"
                    )
                    st.markdown(f'<script>window.open("{url_wa}", "_blank");</script>', unsafe_allow_html=True)
                    st.toast(f"Status de {row['Nome']} alterado para 'Driver Acionado'!", icon="📲")
                    st.rerun()
            else:
                st.caption("Sem WhatsApp")

    st.divider()

    # ==========================================
    # 3. EDICÃO INDIVIDUAL GERAL DE DADOS E STATUS
    # ==========================================
    st.subheader("📊 Histórico Geral & Edição Manual de Informações")
    st.caption("Você pode alterar qualquer dado (Status, Endereço do HUB, Data ou Horário) diretamente na tabela abaixo:")

    df_editado = st.data_editor(
        df_hist,
        column_config={
            "Driver ID": st.column_config.TextColumn("Driver ID", disabled=True),
            "Nome": st.column_config.TextColumn("Nome", disabled=True),
            "Telefone": st.column_config.TextColumn("Telefone", disabled=True),
            "Data Reunião": st.column_config.TextColumn("Data da Reunião"),
            "Horário": st.column_config.TextColumn("Horário"),
            "Endereço HUB / Pauta": st.column_config.TextColumn("Endereço do HUB / Observação"),
            "Status": st.column_config.SelectboxColumn(
                "Status da Reintegração",
                options=["Aguardando Reunião", "Driver Acionado", "Confirmado", "Reintegrado", "Faltou", "Sem Interesse"],
                required=True
            ),
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Salvar Alterações Manuais", type="primary"):
        salvar_historico(df_editado)
        st.toast("Tabela de histórico atualizada com sucesso!", icon="✅")
