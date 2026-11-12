import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

ARQUIVO_HISTORICO = "historico_reengajamento.csv"

def obter_resumo_contexto_operacional() -> str:
    """Lê os dados atuais da sessão e do histórico para dar visão gerencial à IA."""
    contexto = []

    # 1. Dados do Dashboard (se já tiverem sido processados na sessão)
    if "df_analise_cache" in st.session_state:
        df = st.session_state["df_analise_cache"]
        total = len(df)
        ativos = len(df[df["Status_Inatividade"] == "Ativo"])
        alerta = len(df[df["Status_Inatividade"] == "Alerta"])
        churn = len(df[df["Status_Inatividade"] == "Churn"])
        sem_rotas = len(df[df["Status_Inatividade"] == "Sem Rotas"])

        contexto.append(
            f"DADOS DA BASE CARREGADA HOJE NO DASHBOARD:\n"
            f"- Total de motoristas ativos na base: {total}\n"
            f"- Operacionais (0 a 7 dias sem rota): {ativos}\n"
            f"- Em Alerta (8 a 20 dias sem rota): {alerta}\n"
            f"- Inativos / Churn (>20 dias sem rota): {churn}\n"
            f"- Sem Histórico de Rotas: {sem_rotas}"
        )

        # Quebra por veículo nos grupos críticos (Alerta + Churn)
        col_veh = st.session_state.get("col_veh_name", "Vehicle Type")
        if col_veh in df.columns:
            criticos = df[df["Status_Inatividade"].isin(["Alerta", "Churn"])]
            if not criticos.empty:
                contagem_veh = criticos[col_veh].value_counts().to_dict()
                contexto.append(f"- Distribuição de veículos em Alerta/Churn: {contagem_veh}")
    else:
        contexto.append("DADOS DO DASHBOARD: Nenhuma base CSV/ZIP foi carregada ainda nesta sessão.")

    # 2. Dados do Histórico de Agendamentos
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            df_h = pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
            if not df_h.empty:
                status_counts = df_h["Status"].value_counts().to_dict()
                contexto.append(
                    f"\nDADOS DO HISTÓRICO DE AGENDAMENTOS E REUNIÕES:\n"
                    f"- Total de registros no histórico: {len(df_h)}\n"
                    f"- Contagem por status de reintegração: {status_counts}"
                )
        except Exception:
            pass

    return "\n".join(contexto)


SYSTEM_PROMPT_SPX = """
Você é o **SPX Copilot (Especialista de Operações & Churn - Fleet LSP93)**, uma inteligência artificial integrada ao sistema "SPX Control Tower Churn".
Seu objetivo é orientar os analistas na utilização do sistema, interpretar os indicadores da frota e redigir mensagens estratégicas para motoristas.

### MANUAL DO SISTEMA QUE VOCÊ DOMINA:
1. **Aba Control Tower Churn:**
   - Faz o upload da Base de Motoristas (CSV) e Histórico de Rotas (ZIP ou CSV).
   - Classifica os motoristas por dias sem AT (rota):
     * **Ativo (0 a 7 dias):** Operacional normal.
     * **Alerta (8 a 20 dias):** Risco de abandono; requer contato preventivo.
     * **Churn (>20 dias):** Inativo; foco principal de reengajamento.
     * **Sem Rotas:** Nunca rodou ou sem histórico recente.
   - Permite selecionar motoristas via checkbox na tabela, preencher o **Endereço do HUB**, **Data** e **Horário** do treinamento presencial e enviá-los para a fila de agendamento.
2. **Aba Reengajamento & Reuniões:**
   - Gera o arquivo `.CSV` formatado (`Phone;Message`) para disparo 100% automático usando extensões do Chrome no WhatsApp Web (como **WA Web Plus** ou **WAPlus**).
   - Permite marcar toda a fila como **"Driver Acionado"** com um clique ou editar individualmente status (*Aguardando Reunião*, *Driver Acionado*, *Confirmado*, *Reintegrado*, *Faltou*, *Sem Interesse*).

### REGRAS DE CONDUTA:
- Responda sempre em português, de forma direta, prática, cordial e com tom de parceiro de operação logística.
- Use bullet points e negrito para facilitar a leitura rápida no galpão.
- Quando pedirem modelos de mensagem para WhatsApp, crie textos curtos, engajadores, claros e prontos para copiar e colar.
- Utilize os dados em tempo real fornecidos abaixo para responder perguntas sobre os números atuais da operação.
"""


def renderizar_modulo_ia():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.35); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>🤖 SPX Copilot — Assistente Inteligente (IA)</h2>
                    <p style='color: #CCC; font-size: 0.9rem; margin-top: 5px; margin-bottom: 0;'>Tire dúvidas sobre o sistema, analise os números da tela em tempo real ou gere scripts de WhatsApp.</p>
                </div>
                <span style="background: #FFD600; color: #121212; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem;">🧪 DEV AI</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Busca a chave API nos Secrets do Streamlit ou permite inserir na tela para teste
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

    if not api_key:
        with st.expander("🔑 Configurar Chave de API do Gemini (Necessário para ativar a IA)", expanded=True):
            st.caption("Obtenha sua chave gratuita no **Google AI Studio** e cole abaixo (ou salve em `.streamlit/secrets.toml` como `GEMINI_API_KEY`).")
            api_key_input = st.text_input("Cole sua GEMINI_API_KEY:", type="password", key="input_gemini_key")
            if api_key_input:
                st.session_state["temp_gemini_key"] = api_key_input
                api_key = api_key_input
            elif "temp_gemini_key" in st.session_state:
                api_key = st.session_state["temp_gemini_key"]

    if not api_key:
        st.warning("⚠️ Aguardando a configuração da `GEMINI_API_KEY` para iniciar o assistente.")
        return

    # Inicializa histórico do chat na sessão
    if "mensagens_ia_spx" not in st.session_state:
        st.session_state["mensagens_ia_spx"] = [
            {
                "role": "assistant",
                "content": "Fala, equipe LSP93! 👋 Sou o **SPX Copilot**. Já estou conectado aos dados do painel. Como posso ajudar você hoje? *(Ex: análise do churn atual, dúvidas de uso ou criação de mensagens de convocação)*"
            }
        ]

    # Atalhos rápidos (Prompts prontos com 1 clique)
    st.caption("⚡ **Ações Rápidas:**")
    c_q1, c_q2, c_q3, c_q4 = st.columns(4)
    prompt_atalho = None

    with c_q1:
        if st.button("📊 Resumir dados atuais", use_container_width=True):
            prompt_atalho = "Faça um resumo gerencial dos números atuais carregados no painel e no histórico de agendamentos, destacando onde devo focar."
    with c_q2:
        if st.button("📲 Script WhatsApp Churn", use_container_width=True):
            prompt_atalho = "Crie 2 opções de mensagens curtas e persuasivas de WhatsApp para convidar motoristas em Churn para um treinamento presencial no HUB."
    with c_q3:
        if st.button("❓ Como disparar em massa?", use_container_width=True):
            prompt_atalho = "Explique o passo a passo rápido de como selecionar os drivers aqui no sistema e disparar as mensagens em massa pela extensão do Chrome."
    with c_q4:
        if st.button("🗑️ Limpar conversa", use_container_width=True):
            st.session_state["mensagens_ia_spx"] = [st.session_state["mensagens_ia_spx"][0]]
            st.rerun()

    st.divider()

    # Renderiza o histórico de mensagens
    for msg in st.session_state["mensagens_ia_spx"]:
        avatar = "🏎️" if msg["role"] == "assistant" else "🧑‍💻"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Entrada de texto do usuário (via input ou botão de atalho)
    user_input = st.chat_input("Pergunte algo sobre o sistema, peça análises ou textos de WhatsApp...")
    prompt_final = prompt_atalho if prompt_atalho else user_input

    if prompt_final:
        st.session_state["mensagens_ia_spx"].append({"role": "user", "content": prompt_final})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt_final)

        with st.chat_message("assistant", avatar="🏎️"):
            with st.spinner("Analisando operação..."):
                try:
                    client = genai.Client(api_key=api_key)
                    contexto_atual = obter_resumo_contexto_operacional()
                    instrucao_completa = f"{SYSTEM_PROMPT_SPX}\n\n### CONTEXTO OPERACIONAL EM TEMPO REAL:\n{contexto_atual}"

                    # Monta histórico recente para manter o fio da conversa
                    historico_api = []
                    for m in st.session_state["mensagens_ia_spx"][-8:]:
                        role_api = "model" if m["role"] == "assistant" else "user"
                        historico_api.append(
                            types.Content(role=role_api, parts=[types.Part.from_text(text=m["content"])])
                        )

                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=historico_api,
                        config=types.GenerateContentConfig(
                            system_instruction=instrucao_completa,
                            temperature=0.4,
                        ),
                    )

                    resposta_texto = response.text
                    st.markdown(resposta_texto)
                    st.session_state["mensagens_ia_spx"].append({"role": "assistant", "content": resposta_texto})

                except Exception as e:
                    st.error(f"Erro ao consultar o Gemini: {e}")
