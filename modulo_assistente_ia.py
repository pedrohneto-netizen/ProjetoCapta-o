import os
import re
import unicodedata
import pandas as pd
import streamlit as st

ARQUIVO_HISTORICO = "historico_reengajamento.csv"


def normalizar_texto(texto: str) -> str:
    """Remove acentos, pontuação e converte para minúsculas para interpretação flexível."""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    texto = re.sub(r"[^\w\s]", " ", texto.lower())
    return " ".join(texto.split())


BASE_CONHECIMENTO_SISTEMA = [
    {
        "tema": "Inserção e Upload de Bases (CSV / ZIP)",
        "tags": ["inserir", "base", "bases", "upload", "carregar", "subir", "arquivo", "csv", "zip", "importar", "planilha", "rotas", "motoristas", "comecar", "iniciar"],
        "resposta": """### 📂 Como Inserir e Processar as Bases no Sistema

Para alimentar o **Control Tower Churn**, siga estes 4 passos na aba **📊 Control Tower Churn**:

1. **1. Base de Motoristas (CSV):** Clique em *Upload CSV motoristas* e selecione o arquivo exportado do sistema SPX. O sistema filtra automaticamente apenas os motoristas com status **`Active`**.
2. **2. Histórico de Rotas (ZIP ou CSV):** Clique em *Upload histórico rotas*. Você pode subir **um ou vários arquivos** simultaneamente (`.zip` ou `.csv`).
3. **Data de Referência:** Confirme ou ajuste a data base de corte no campo *Data de Referência*.
4. **Gerar Painel:** Clique no botão laranja **🚀 GERAR ANÁLISE E TRAVAR PAINEL NA SESSÃO**. As bases ficarão fixas na tela até você clicar em **🗑️ Limpar / Trocar Bases Importadas**."""
    },
    {
        "tema": "Regras de Classificação de Inatividade (Ativo, Alerta, Churn)",
        "tags": ["regra", "regras", "classificacao", "classificar", "ativo", "alerta", "churn", "sem rotas", "dias", "criterio", "inatividade", "significa"],
        "resposta": """### 📏 Regras de Classificação de Inatividade (LSP93)

O sistema calcula a diferença em dias entre a **Data de Referência** e a **Última Rota (AT)** de cada motorista ativo:

- 🟢 **Operacional / Ativo (0 a 7 dias):** Motorista operando regularmente na semana.
- 🟡 **Em Alerta (8 a 20 dias):** Sinal amarelo de afastamento. Momento ideal para contato preventivo.
- 🔴 **Inativo / Churn (> 20 dias):** Motorista afastado há mais de 20 dias. Foco prioritário para resgate e treinamento presencial.
- ⚪ **Sem Histórico de AT:** Motorista com cadastro `Active`, mas sem nenhuma rota registrada nos arquivos importados."""
    },
    {
        "tema": "Filtros, KPIs e Busca na Tabela Gerencial",
        "tags": ["filtrar", "filtro", "buscar", "busca", "pesquisar", "kpi", "card", "veiculo", "fiorino", "moto", "passeio", "van", "tabela", "encontrar"],
        "resposta": """### 🔍 Como Filtrar e Localizar Motoristas no Painel

1. **Cards KPI no Topo:** Clique nos botões abaixo dos números (*Filtrar Todos*, *Filtrar Ativos*, *Filtrar Alerta*, *Filtrar Churn* ou *Filtrar Sem Rotas*) para isolar cada grupo.
2. **Busca Rápida:** Digite qualquer parte do **Nome** ou do **Driver ID** no campo *🔍 Busca Rápida*.
3. **Filtro por Tipo de Veículo:** Use o seletor *🚗 Tipo de Veículo* para filtrar apenas *MOTO*, *FIORINO*, *PASSEIO*, *VAN*, etc.
4. **Limpar:** Clique em **🔄 Resetar Filtros** para voltar à visão completa."""
    },
    {
        "tema": "Acionamento via WhatsApp e Janela Pop-up de Registro",
        "tags": ["acionar", "whatsapp", "whats", "contato", "chamar", "popup", "janela", "analista", "tipo"],
        "resposta": """### 📲 Como Acionar Motoristas no WhatsApp (Passo a Passo)

1. Preencha seu nome no campo **👤 Analista Responsável** no menu lateral esquerdo.
2. Na aba **📊 Control Tower Churn**, escolha o motorista na lista **Acionar Motorista no WhatsApp** e clique em **📲 CHAMAR NO WHATS (REGISTRAR)**.
3. Na janela que abrir, confirme o **Analista**, escolha o **Tipo de Acionamento**, ajuste data/horário/HUB se necessário e clique em **✅ GRAVAR NO HISTÓRICO E LIBERAR WHATSAPP**.
4. Clique em **🚀 ABRIR CONVERSA NO WHATSAPP AGORA** para enviar a mensagem pronta."""
    },
    {
        "tema": "Dashboard de Reengajamento, Atualização de Status e Relatórios",
        "tags": ["status", "reintegracao", "reintegrado", "confirmado", "faltou", "sem interesse", "driver acionado", "aguardando", "atualizar", "historico", "relatorio", "exportar", "excel"],
        "resposta": """### 🔄 Histórico, Atualização de Retornos e Relatórios

Na aba **📅 Reengajamento & Histórico**, você visualiza todos os motoristas acionados pela equipe:

- **Editar Retorno:** Dê um duplo clique nas colunas **Status (Editar)** ou **Observação / Retorno (Editar)** e clique em **💾 SALVAR ALTERAÇÕES** — o sistema carimba automaticamente a **Data e Hora** da atualização.
- **Extrair Relatório:** Use os botões na parte inferior da página para baixar a **Visão Filtrada** ou o **Histórico Completo** em formato pronto para Excel."""
    }
]


def consultar_dados_reais(pergunta_norm: str) -> str | None:
    tem_base = "df_analise_cache" in st.session_state
    tem_hist = os.path.exists(ARQUIVO_HISTORICO)

    if any(k in pergunta_norm for k in ["resumo", "numero", "numeros", "indicador", "kpi", "taxa", "quanto", "quantos", "total", "hoje", "panorama", "situacao"]):
        blocos = []
        if tem_base:
            df = st.session_state["df_analise_cache"]
            col_veh = st.session_state.get("col_veh_name", "Vehicle Type")
            total = len(df)
            ativos = len(df[df["Status_Inatividade"] == "Ativo"])
            alerta = len(df[df["Status_Inatividade"] == "Alerta"])
            churn = len(df[df["Status_Inatividade"] == "Churn"])
            sem_rotas = len(df[df["Status_Inatividade"] == "Sem Rotas"])
            taxa_churn = (churn / total * 100) if total > 0 else 0

            blocos.append("### 📊 Panorama Atual da Base Carregada")
            blocos.append(f"- **Total de Motoristas Ativos:** {total:,}")
            blocos.append(f"- 🟢 **Operacionais (0-7d):** {ativos:,} ({ativos/total*100:.1f}%)" if total else "- Operacionais: 0")
            blocos.append(f"- 🟡 **Em Alerta (8-20d):** {alerta:,}")
            blocos.append(f"- 🔴 **Inativos / Churn (>20d):** {churn:,} (**{taxa_churn:.1f}%** da base)")
            blocos.append(f"- ⚪ **Sem Histórico de AT:** {sem_rotas:,}")

            if col_veh in df.columns:
                criticos = df[df["Status_Inatividade"].isin(["Alerta", "Churn"])]
                if not criticos.empty:
                    top_veh = criticos[col_veh].value_counts().to_dict()
                    detalhe_veh = ", ".join([f"**{k}**: {v}" for k, v in top_veh.items()])
                    blocos.append(f"- 🚗 **Críticos (Alerta + Churn) por Veículo:** {detalhe_veh}")
        else:
            blocos.append("⚠️ **Base principal não carregada:** Faça o upload dos arquivos na aba **Control Tower Churn** para que eu leia os números da frota.")

        if tem_hist:
            try:
                df_h = pd.read_csv(ARQUIVO_HISTORICO, dtype=str)
                if not df_h.empty:
                    cont = df_h["Status"].value_counts().to_dict()
                    blocos.append("\n### 📅 Histórico de Acionamentos da Equipe")
                    for st_nome, qtd in cont.items():
                        blocos.append(f"- **{st_nome}:** {qtd} motorista(s)")
            except Exception:
                pass

        return "\n".join(blocos)

    if any(k in pergunta_norm for k in ["listar", "lista", "quais motoristas", "quem esta", "prioridade", "criticos"]):
        if not tem_base:
            return "⚠️ Carregue a base de motoristas e rotas na aba **Control Tower Churn** primeiro para que eu possa listar os motoristas prioritários."
        df = st.session_state["df_analise_cache"]
        col_id = st.session_state.get("col_driver_id_name", "Driver ID")
        col_name = st.session_state.get("col_driver_name_col", "Driver Name")
        col_veh = st.session_state.get("col_veh_name", "Vehicle Type")
        criticos = df[df["Status_Inatividade"].isin(["Churn", "Alerta"])].head(10)
        if criticos.empty:
            return "🟢 Excelente! Não há motoristas em status **Churn** ou **Alerta** na base carregada."
        linhas = ["### 🎯 Top 10 Motoristas Prioritários para Acionamento (Maior Inatividade)\n"]
        for _, r in criticos.iterrows():
            linhas.append(f"- **{r.get(col_name, 'N/I')}** (`ID: {r[col_id]}`) — {r.get(col_veh, 'N/I')} | **{r['Dias_Sem_AT_Fmt']}** ({r['Status_Inatividade']})")
        return "\n".join(linhas)

    return None


def gerar_scripts_whatsapp() -> str:
    return """### 📲 Templates Prontos de WhatsApp (Copie e Use)

**1. Convocação para Treinamento Presencial (Churn >20 dias):**
> Olá! Tudo bem? Aqui é da equipe de Frota da **SPX Logistics (LSP93)**. Notamos que você está há alguns dias sem rodar conosco e queremos te convidar para um treinamento presencial rápido de reintegração no nosso HUB para liberar novas rotas!
> 📍 **Local:** Av. dos Estados, 7328 - Parque Jaçatuba - Santo André / SP
> Responda **SIM** para confirmarmos sua vaga!

---

**2. Abordagem Preventiva (Motoristas em Alerta 8 a 20 dias):**
> Fala, parceiro(a)! Tudo certo? A equipe **SPX Logistics** sentiu sua falta nas rotas desta semana. Estamos com volume alto de pacotes na região e queremos alinhar seu retorno no galpão. Podemos contar com você nos próximos dias?

---

**3. Confirmação de Presença (Dia anterior ao Treinamento):**
> Olá! Passando para confirmar seu **Treinamento Presencial SPX Logistics** amanhã. Lembre-se de levar documento original com foto e CNH válida, chegando 10 minutos antes. Te esperamos no HUB!"""


def responder_duvida_inteligente(pergunta: str) -> str:
    p_norm = normalizar_texto(pergunta)
    palavras_usuario = set(p_norm.split())

    if any(k in p_norm for k in ["script", "mensagem", "mensagens", "modelo", "texto", "template", "convite", "abordagem"]):
        return gerar_scripts_whatsapp()

    resp_dados = consultar_dados_reais(p_norm)
    if resp_dados:
        return resp_dados

    melhor_item = None
    maior_pontuacao = 0

    for item in BASE_CONHECIMENTO_SISTEMA:
        tags = set(item["tags"])
        matches = palavras_usuario.intersection(tags)
        pontuacao = len(matches)

        for tag in tags:
            if " " in tag and tag in p_norm:
                pontuacao += 2

        if pontuacao > maior_pontuacao:
            maior_pontuacao = pontuacao
            melhor_item = item

    if melhor_item and maior_pontuacao >= 1:
        return melhor_item["resposta"]

    temas_disponiveis = "\n".join([f"- **{item['tema']}**" for item in BASE_CONHECIMENTO_SISTEMA])
    return f"""Não encontrei uma correspondência exata para *"{pergunta}"*, mas como especialista do **SPX Control Tower Churn**, posso te orientar sobre qualquer um destes tópicos:

{temas_disponiveis}
- **Análise dos Números de Hoje & Lista de Prioritários**
- **Modelos de Mensagens para WhatsApp**"""


def renderizar_modulo_ia():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E1E1E 0%, #2A0800 100%); border: 1px solid #EE4D2D; box-shadow: 0 0 15px rgba(238, 77, 45, 0.35); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h2 style='color: #EE4D2D; font-weight: 800; margin: 0;'>🤖 SPX Copilot — Especialista do Sistema (LSP93)</h2>
                    <p style='color: #CCC; font-size: 0.9rem; margin-top: 5px; margin-bottom: 0;'>Base de Conhecimento Completa • Leitura em Tempo Real dos Dados • 100% Nativo.</p>
                </div>
                <span style="background: #00E676; color: #121212; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem;">⚡ ATIVO</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if "mensagens_ia_spx" not in st.session_state:
        st.session_state["mensagens_ia_spx"] = [
            {
                "role": "assistant",
                "content": "Olá, equipe **LSP93**! 👋 Sou o **SPX Copilot**, treinado com toda a documentação e regras do **Control Tower Churn**.\n\nVocê pode me perguntar **qualquer dúvida sobre o funcionamento do sistema** (upload de bases, filtros, acionamentos, histórico e relatórios) ou pedir o **resumo dos dados carregados hoje**!"
            }
        ]

    st.caption("⚡ **Perguntas Frequentes (1 Clique):**")
    c1, c2, c3, c4, c5 = st.columns(5)
    prompt_selecionado = None

    with c1:
        if st.button("📂 Como inserir bases?", use_container_width=True):
            prompt_selecionado = "Como inserir as bases?"
    with c2:
        if st.button("📊 Resumo de Hoje", use_container_width=True):
            prompt_selecionado = "Qual o resumo dos dados de hoje?"
    with c3:
        if st.button("🎯 Top 10 Críticos", use_container_width=True):
            prompt_selecionado = "Listar motoristas prioritários"
    with c4:
        if st.button("📲 Como acionar driver?", use_container_width=True):
            prompt_selecionado = "Como acionar motoristas no WhatsApp?"
    with c5:
        if st.button("📝 Scripts WhatsApp", use_container_width=True):
            prompt_selecionado = "Gerar scripts de WhatsApp"

    st.divider()

    for msg in st.session_state["mensagens_ia_spx"]:
        avatar = "🏎️" if msg["role"] == "assistant" else "🧑‍💻"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    user_input = st.chat_input("Pergunte qualquer coisa sobre o sistema (ex: como inserir bases, regras de churn, histórico...)")
    pergunta_final = prompt_selecionado if prompt_selecionado else user_input

    if pergunta_final:
        st.session_state["mensagens_ia_spx"].append({"role": "user", "content": pergunta_final})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(pergunta_final)

        resposta = responder_duvida_inteligente(pergunta_final)

        st.session_state["mensagens_ia_spx"].append({"role": "assistant", "content": resposta})
        with st.chat_message("assistant", avatar="🏎️"):
            st.markdown(resposta)
