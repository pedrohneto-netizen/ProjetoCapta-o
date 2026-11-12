import os
import pandas as pd
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"


def analisar_dados_tempo_real() -> str:
    """Lê os dados atuais da sessão e do CSV para gerar diagnósticos instantâneos."""
    linhas = []

    if "df_analise_cache" in st.session_state:
        df = st.session_state["df_analise_cache"]
        col_veh = st.session_state.get("col_veh_name", "Vehicle Type")

        total = len(df)
        ativos = len(df[df["Status_Inatividade"] == "Ativo"])
        alerta = len(df[df["Status_Inatividade"] == "Alerta"])
        churn = len(df[df["Status_Inatividade"] == "Churn"])
        sem_rotas = len(df[df["Status_Inatividade"] == "Sem Rotas"])

        taxa_churn = (churn / total * 100) if total > 0 else 0

        linhas.append("### 📊 Diagnóstico da Base Carregada Hoje")
        linhas.append(f"- **Total de Motoristas Ativos na Base:** {total:,}")
        linhas.append(f"- **Operacionais (0 a 7 dias):** {ativos:,} ({ativos/total*100:.1f}%)" if total else "- Operacionais: 0")
        linhas.append(f"- **Em Alerta (8 a 20 dias):** {alerta:,} *(Prioridade preventiva)*")
        linhas.append(f"- **Inativos / Churn (>20 dias):** {churn:,} (**{taxa_churn:.1f}%** da frota)")
        linhas.append(f"- **Sem Histórico de Rotas:** {sem_rotas:,}")

        if col_veh in df.columns:
            criticos = df[df["Status_Inatividade"].isin(["Alerta", "Churn"])]
            if not criticos.empty:
                top_veh = criticos[col_veh].value_counts().head(3).to_dict()
                resumo_veh = ", ".join([f"**{k}** ({v})" for k, v in top_veh.items()])
                linhas.append(f"- **Veículos mais afetados (Alerta + Churn):** {resumo_veh}")
    else:
        linhas.append("### 📊 Diagnóstico da Base")
        linhas.append("⚠️ Nenhuma base foi carregada ainda na aba **Control Tower Churn**. Faça o upload dos arquivos CSV/ZIP para eu analisar os números do dia!")

    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            df_h = pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
            if not df_h.empty:
                contagem = df_h["Status"].value_counts().to_dict()
                linhas.append("\n### 📅 Status da Fila de Reengajamento")
                for st_nome, qtd in contagem.items():
                    linhas.append(f"- **{st_nome}:** {qtd} motorista(s)")
        except Exception:
            pass

    return "\n".join(linhas)


def gerar_scripts_whatsapp(hub_endereco: str = "HUB Santo André - Av. dos Estados, 7328") -> str:
    """Gera modelos prontos de abordagem para diferentes perfis de inatividade."""
    return f"""### 📲 Modelos Prontos para Disparo no WhatsApp

**Opção 1 — Motoristas em Churn (>20 dias inativos) | Foco em Retorno:**
> Olá! Tudo bem? Aqui é da equipe de Frota da **SPX Logistics (LSP93)**. Notamos que faz um tempo desde a sua última rota conosco e gostaríamos de te convidar para um alinhamento presencial rápido no nosso galpão para liberar novas oportunidades de carregamento!
> 📍 **Local:** {hub_endereco}
> Responda **SIM** para confirmarmos seu horário!

---

**Opção 2 — Motoristas em Alerta (8 a 20 dias) | Prevenção de Abandono:**
> Fala, parceiro(a)! Tudo certo? A equipe **SPX Logistics** sentiu sua falta nas rotas desta semana. Estamos com alta demanda de pacotes na região e queremos alinhar seu retorno no HUB.
> 📍 **Endereço:** {hub_endereco}
> Podemos contar com você nos próximos dias?

---

**Opção 3 — Lembrete de Treinamento Presencial Agendado:**
> Olá! Passando para lembrar do seu **Treinamento Presencial SPX Logistics**.
> 📍 **Local:** {hub_endereco}
> Por favor, chegue com 10 minutos de antecedência e traga documento com foto e CNH. Te esperamos lá!"""


def responder_duvida_inteligente(pergunta: str) -> str:
    """Motor de resposta baseado em intenção e dados reais da sessão."""
    p = pergunta.lower().strip()

    if any(k in p for k in ["resumo", "dado", "numero", "número", "churn", "analise", "análise", "status", "hoje", "frota", "veiculo", "veículo"]):
        return analisar_dados_tempo_real()

    if any(k in p for k in ["mensagem", "script", "texto", "whatsapp", "whats", "convite", "abordagem"]):
        return gerar_scripts_whatsapp()

    if any(k in p for k in ["massa", "extensao", "extensão", "disparar", "enviar", "csv", "wa web", "waplus"]):
        return """### ⚡ Como Disparar Mensagens em Massa (Passo a Passo)

1. Na aba **Control Tower Churn**, marque a caixa **Acionar em Massa** ao lado dos motoristas desejados.
2. Preencha o **Endereço do HUB**, **Data** e **Horário** do treinamento presencial logo abaixo da tabela e clique em **Direcionar para o Agendamento**.
3. Na aba **Reengajamento & Reuniões**, clique em **📥 Baixar Arquivo de Envio para a Extensão (.CSV)**.
4. Abra o **WhatsApp Web** no Chrome, ative sua extensão (**WA Web Plus** ou **WAPlus**), importe o CSV baixado (colunas `Phone` e `Message`) e inicie o envio com intervalo de 3 a 5 segundos.
5. Volte ao painel e clique em **✅ Marcar Fila Exportada como 'Driver Acionado'** para atualizar o histórico."""

    if any(k in p for k in ["regra", "classifica", "alerta", "ativo", "sem rota", "dias", "significa"]):
        return """### 📏 Regras de Classificação de Inatividade (LSP93)

O sistema cruza a base de motoristas com status **Active** contra a data mais recente de rota encontrada nos arquivos de histórico:

- 🟢 **Operacional / Ativo (0 a 7 dias):** Motorista rodando regularmente.
- 🟡 **Em Alerta (8 a 20 dias):** Início de afastamento; ideal para contato preventivo antes que migre para outro aplicativo.
- 🔴 **Churn (> 20 dias):** Motorista inativo; foco principal das convocações de treinamento presencial e reintegração.
- ⚪ **Sem Histórico:** Motorista ativo no cadastro, mas sem nenhuma rota registrada nos arquivos importados."""

    if any(k in p for k in ["alterar", "mudar", "editar", "endereco", "endereço", "hub", "horario", "horário", "presencial"]):
        return """### 🛠️ Como Editar Status, Horários e Endereço do HUB

- **No momento do agendamento:** Na aba **Control Tower Churn**, antes de enviar a fila, digite o endereço completo do HUB no campo **📍 Endereço do HUB / Local do Treinamento**.
- **Edição posterior (Individual):** Na aba **Reengajamento & Reuniões**, vá até a tabela **📊 Histórico Geral & Atualização de Status** e dê um duplo clique em qualquer célula (*Status*, *Data Reunião*, *Horário* ou *Local HUB*) para editar. Depois clique em **💾 Salvar Alterações Manuais**.
- **Atualização em lote:** Use o botão **✅ Marcar Fila Exportada como 'Driver Acionado'** para atualizar todos os registros da fila de uma só vez."""

    return """Não identifiquei um comando específico, mas posso te ajudar imediatamente com:

1. **📊 Análise em Tempo Real:** Pergunte *"Qual o resumo dos dados de hoje?"* para ver a taxa de churn e os veículos mais afetados.
2. **📲 Scripts de WhatsApp:** Peça *"Crie mensagens de WhatsApp"* para gerar convites prontos.
3. **⚡ Guia de Disparo em Massa:** Pergunte *"Como disparar em massa pela extensão?"*.
4. **📏 Regras do Painel:** Pergunte *"Quais são as regras de classificação?"* ou *"Como editar status e endereço do HUB?"*."""


def renderizar_modulo_ia():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.35); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>🤖 SPX Copilot — Assistente Operacional Interno</h2>
                    <p style='color: #CCC; font-size: 0.9rem; margin-top: 5px; margin-bottom: 0;'>100% Nativo • Sem necessidade de API externa • Leitura em tempo real da base LSP93.</p>
                </div>
                <span style="background: #00E676; color: #121212; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem;">⚡ OFFLINE / NATIVO</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if "mensagens_ia_spx" not in st.session_state:
        st.session_state["mensagens_ia_spx"] = [
            {
                "role": "assistant",
                "content": "Fala, equipe **LSP93**! 👋 Sou o **SPX Copilot** integrado ao painel. Já estou pronto para analisar os dados carregados hoje, tirar dúvidas do sistema ou gerar scripts de WhatsApp. Use os botões rápidos abaixo ou digite sua dúvida!"
            }
        ]

    st.caption("⚡ **Consultas Rápidas (1 Clique):**")
    c1, c2, c3, c4 = st.columns(4)
    prompt_selecionado = None

    with c1:
        if st.button("📊 Resumo dos Dados Hoje", use_container_width=True):
            prompt_selecionado = "Resumo dos dados de hoje"
    with c2:
        if st.button("📲 Scripts WhatsApp", use_container_width=True):
            prompt_selecionado = "Gerar scripts de WhatsApp"
    with c3:
        if st.button("⚡ Guia Disparo em Massa", use_container_width=True):
            prompt_selecionado = "Como disparar em massa?"
    with c4:
        if st.button("📏 Regras & Edição HUB", use_container_width=True):
            prompt_selecionado = "Quais são as regras de classificação?"

    st.divider()

    for msg in st.session_state["mensagens_ia_spx"]:
        avatar = "🏎️" if msg["role"] == "assistant" else "🧑‍💻"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    user_input = st.chat_input("Digite sua dúvida sobre o sistema, peça o resumo do churn ou scripts...")
    pergunta_final = prompt_selecionado if prompt_selecionado else user_input

    if pergunta_final:
        st.session_state["mensagens_ia_spx"].append({"role": "user", "content": pergunta_final})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(pergunta_final)

        resposta = responder_duvida_inteligente(pergunta_final)

        st.session_state["mensagens_ia_spx"].append({"role": "assistant", "content": resposta})
        with st.chat_message("assistant", avatar="🏎️"):
            st.markdown(resposta)
