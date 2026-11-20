import hmac
import io
import time
from datetime import datetime
import pandas as pd
import streamlit as st
from google import genai

st.set_page_config(page_title="hnos system A", page_icon="🤖", layout="wide")


# ---------- os agentes ----------
ROBOS = {
    "rh": (
        '<line x1="32" y1="8" x2="32" y2="14"/><circle cx="32" cy="6" r="3" fill="currentColor"/>'
        '<rect x="14" y="14" width="36" height="28" rx="14"/>'
        '<circle cx="25" cy="27" r="3" fill="currentColor"/><circle cx="39" cy="27" r="3" fill="currentColor"/>'
        '<path d="M26 34 q6 5 12 0"/>'
        '<path d="M32 59 l-7-7 a4 4 0 0 1 7-5 a4 4 0 0 1 7 5z" fill="currentColor"/>'
    ),
    "financeiro": (
        '<rect x="14" y="10" width="36" height="30" rx="6"/>'
        '<line x1="9" y1="25" x2="14" y2="25"/><line x1="50" y1="25" x2="55" y2="25"/>'
        '<rect x="22" y="19" width="6" height="6" rx="1" fill="currentColor"/>'
        '<rect x="36" y="19" width="6" height="6" rx="1" fill="currentColor"/>'
        '<line x1="25" y1="32" x2="39" y2="32"/>'
        '<circle cx="32" cy="52" r="9"/>'
        '<path d="M35.5 48.5 q-3.5-2-7 0 q-2 2.2 1.5 3.5 l4 1 q3 1.5 1 3.6 q-3.5 2-7 0 M32 44.5 v15"/>'
    ),
    "compras": (
        '<path d="M21 8 l4 7 M43 8 l-4 7"/>'
        '<rect x="16" y="15" width="32" height="24" rx="10"/>'
        '<rect x="22" y="22" width="20" height="7" rx="3.5" fill="currentColor"/>'
        '<path d="M10 43 h6 l5 11 h22 l5-9 H18"/>'
        '<circle cx="25" cy="59" r="2.6" fill="currentColor"/><circle cx="39" cy="59" r="2.6" fill="currentColor"/>'
    ),
    "marketing": (
        '<line x1="24" y1="7" x2="24" y2="14"/><circle cx="24" cy="5" r="3" fill="currentColor"/>'
        '<rect x="9" y="14" width="30" height="28" rx="12"/>'
        '<circle cx="19" cy="26" r="3" fill="currentColor"/><circle cx="30" cy="26" r="3" fill="currentColor"/>'
        '<circle cx="24.5" cy="34" r="2.6"/>'
        '<path d="M42 23 l12-8 v24 l-12-8z"/><path d="M58 21 q3 6 0 12"/>'
        '<path d="M16 42 v10 M32 42 v10 M12 56 h24"/>'
    ),
}

AGENTES = {
    "rh": {
        "nome": "RH", "cor": "#5B5BD6", "tinta": "#EEEEFC", "ativo": True,
        "serve": "calcular o saldo de horas da sua equipe e dizer quem fez hora extra e quem precisa compensar",
        "contexto": (
            "**O que eu faço:** comparo a escala com o ponto de cada funcionário e calculo o saldo de horas da semana.\n\n"
            "**O que eu preciso:** uma planilha .xlsx com as abas *escala* e *ponto*.\n\n"
            "**O que você recebe:** o saldo de cada pessoa, um relatório pronto para ler e um arquivo Excel para guardar."
        ),
    },
    "financeiro": {
        "nome": "Financeiro", "cor": "#178A5A", "tinta": "#E6F5EE", "ativo": True,
        "serve": "conferir se o que você vendeu no cartão e no PIX caiu certo no banco",
        "contexto": (
            "**O que eu faço:** cruzo as vendas do sistema com o extrato do banco, desconto a taxa do cartão "
            "e aponto cada pagamento que não bateu.\n\n"
            "**O que eu preciso:** as vendas do sistema e o extrato do banco, em .csv ou .xlsx.\n\n"
            "**O que você recebe:** as divergências com o valor, as contas pagas no período e um relatório pronto."
        ),
    },
    "compras": {
        "nome": "Compras", "cor": "#C77A0A", "tinta": "#FCF1DF", "ativo": False,
        "serve": "montar a lista de compras a partir do estoque e dos pedidos",
        "contexto": (
            "**Em produção.** Em breve vou olhar o estoque e os pedidos da semana e montar a lista do que comprar."
        ),
    },
    "marketing": {
        "nome": "Marketing", "cor": "#D6336C", "tinta": "#FCE8EF", "ativo": False,
        "serve": "criar e agendar os posts do seu Instagram",
        "contexto": (
            "**Em produção.** Em breve vou buscar os assuntos do dia, criar os posts e agendar no Instagram "
            "depois da sua aprovação."
        ),
    },
}


def robo(chave, tamanho=64):
    return (
        f'<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 64 64" fill="none" stroke="currentColor" '
        f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{ROBOS[chave]}</svg>'
    )


# ---------- estilo ----------
ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Instrument+Sans:wght@400;500;600&family=Courier+Prime:wght@400;700&display=swap');

:root {
    --fundo: #F7F8FA; --cartao: #FFFFFF; --linha: #E3E6EC;
    --texto: #1C1E24; --mudo: #646B78; --acento: #1C1E24;
    --curva: cubic-bezier(0.22, 1, 0.36, 1);
}
.stApp { background: var(--fundo); color: var(--texto); }
.stApp, .stApp p, .stApp label, .stApp li, .stMarkdown, button, input, textarea {
    font-family: 'Instrument Sans', sans-serif;
}
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1120px; }
h1, h2, h3 { font-family: 'Bricolage Grotesque', sans-serif !important; color: var(--texto); }

/* ---------- abertura (fade in) ---------- */
@keyframes surgir { from { opacity: 0; } to { opacity: 1; } }
@keyframes surgir-subindo { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
.abertura { text-align: center; padding: 22vh 0 2.4rem 0; }
.abertura .marca {
    font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; color: var(--texto);
    font-size: clamp(3rem, 9vw, 6.5rem); letter-spacing: -.035em; line-height: 1;
    animation: surgir 1.6s ease-out both;
}
.abertura .marca span { color: #5B5BD6; }
.abertura .robos {
    display: flex; justify-content: center; gap: 18px; margin-top: 2rem;
    animation: surgir-subindo 1.2s var(--curva) .7s both;
}
.abertura .robos div { width: 44px; height: 44px; }
.st-key-btn_ok { width: 100% !important; animation: surgir 1s ease-out 1.3s both; }
.st-key-btn_ok .stButton, .st-key-btn_ok .stButton > div { display: block !important; width: 100% !important; }
.st-key-btn_ok button { width: 200px !important; margin: 0 auto !important; display: flex !important; padding: .8rem 0 !important; }
.st-key-btn_ok button p { font-size: 1.1rem; letter-spacing: .02em; }
[class*="st-key-caixa_pedido"] .titulo-secao { margin-top: 0; }
[class*="st-key-caixa_pedido"] [data-testid="stForm"] { padding: 0; }
.saudacao svg { flex: 0 0 auto; }

/* ---------- login ---------- */
.st-key-caixa_login {
    max-width: 420px; margin: 12vh auto 0 auto; background: var(--cartao);
    border: 1px solid var(--linha); border-radius: 22px; padding: 30px 30px 18px 30px;
    box-shadow: 0 20px 50px -30px rgba(28, 30, 36, .35);
    animation: surgir .8s ease-out both;
}
.login-titulo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.9rem; margin: 0; }
.login-sub { color: var(--mudo); margin: .3rem 0 1.2rem 0; }
.dica { color: var(--mudo); font-size: .9rem; margin-top: .4rem; }

/* ---------- cabeçalho fixo ---------- */
.marca-topo { line-height: 1.05; }
.marca-topo .nome {
    font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.7rem;
    letter-spacing: -.03em; color: var(--texto);
}
.marca-topo .nome span { color: var(--acento); }
.marca-topo .com { color: var(--mudo); font-size: 1rem; padding-left: 2px; }
.marca-topo .com strong { color: var(--texto); font-weight: 600; }
.st-key-topo { border-bottom: 1px solid var(--linha); padding-bottom: 14px; margin-bottom: 1.6rem; }
.st-key-topo [data-testid="stHorizontalBlock"] { align-items: center; }

/* ---------- cartões dos agentes ---------- */
.st-key-card_rh { --cor: #5B5BD6; }
.st-key-card_financeiro { --cor: #178A5A; }
.st-key-card_compras { --cor: #C77A0A; }
.st-key-card_marketing { --cor: #D6336C; }
[class*="st-key-card_"] {
    position: relative; background: var(--cartao); border: 2px solid var(--cor);
    border-radius: 24px; padding: 22px 20px; min-height: 196px;
    box-shadow: 7px 7px 0 var(--cor);
    transition: transform .18s var(--curva), box-shadow .18s var(--curva);
}
[class*="st-key-card_"]:hover { transform: translate(-2px, -2px); box-shadow: 9px 9px 0 var(--cor); }
[class*="st-key-card_"]:active { transform: translate(4px, 4px); box-shadow: 3px 3px 0 var(--cor); }
[class*="st-key-card_"]:has(button:focus-visible) { outline: 3px solid var(--texto); outline-offset: 4px; }
.cartao-robo { color: var(--cor); }
.cartao-nome {
    font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.55rem;
    color: var(--texto); margin-top: .7rem;
}
.cartao-serve { color: var(--mudo); font-size: .92rem; line-height: 1.4; margin-top: .2rem; }
[class*="st-key-abrir_"] { position: absolute !important; inset: 0; z-index: 3; margin: 0 !important; }
[class*="st-key-abrir_"] div, [class*="st-key-abrir_"] button {
    width: 100% !important; height: 100% !important; min-height: 100% !important;
}
[class*="st-key-abrir_"] button { opacity: 0; cursor: pointer; }
.st-key-card_compras, .st-key-card_marketing { background: #FBFBFC; }
.st-key-card_compras:hover, .st-key-card_marketing:hover { transform: none; box-shadow: 7px 7px 0 var(--cor); }
.st-key-card_compras .cartao-robo, .st-key-card_marketing .cartao-robo { opacity: .55; }
.selo-producao {
    display: inline-block; margin-top: .7rem; font-size: .78rem; font-weight: 600;
    color: var(--cor); background: color-mix(in srgb, var(--cor) 12%, white);
    padding: .18rem .6rem; border-radius: 999px;
}
[data-testid="stPopover"] { margin-top: 18px; }
[data-testid="stPopover"] button { border-radius: 999px; border: 1px solid var(--linha); background: var(--cartao); }

/* ---------- pedido ---------- */
[class*="st-key-caixa_pedido"] {
    background: var(--cartao); border: 1px solid var(--linha); border-radius: 22px;
    padding: 22px 24px; margin-top: 2.6rem;
}
[class*="st-key-caixa_pedido"] textarea { border-radius: 14px; }
.resposta {
    display: flex; gap: 14px; align-items: flex-start; margin-top: 1rem;
    background: color-mix(in srgb, var(--cor) 7%, white); border-radius: 18px; padding: 16px 18px;
}
.resposta .cartao-robo { flex: 0 0 auto; }

/* ---------- botões ---------- */
.stButton > button, [data-testid="stDownloadButton"] > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 999px; padding: .6rem 1.4rem; border: 1px solid var(--linha); background: var(--cartao);
    transition: transform .15s var(--curva), background-color .15s var(--curva);
}
.stButton > button:active, [data-testid="stFormSubmitButton"] > button:active { transform: scale(.97); }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: var(--acento); border-color: var(--acento); color: #fff;
}
button[data-testid="stBaseButton-primary"] p, button[data-testid="stBaseButton-primaryFormSubmit"] p { color: #fff; font-weight: 600; }
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: color-mix(in srgb, var(--acento) 85%, black); border-color: transparent; color: #fff;
}
button:focus-visible { outline: 3px solid var(--acento) !important; outline-offset: 3px; }

/* ---------- seção do agente ---------- */
.saudacao {
    display: flex; gap: 18px; align-items: center; background: var(--cartao);
    border: 2px solid var(--acento); border-radius: 24px; padding: 20px 24px;
    box-shadow: 7px 7px 0 var(--acento); margin: .4rem 0 1.4rem 0; color: var(--acento);
    animation: surgir .6s ease-out both;
}
.saudacao p { color: var(--texto); font-size: 1.15rem; line-height: 1.5; margin: 0; }
.saudacao strong { font-family: 'Bricolage Grotesque', sans-serif; }
.titulo-secao {
    font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.35rem;
    color: var(--texto); margin: 2.2rem 0 .8rem 0;
}
.titulo-secao small {
    display: block; font-family: 'Instrument Sans', sans-serif; font-weight: 400;
    font-size: .92rem; color: var(--mudo); margin-top: .2rem;
}
[data-testid="stFileUploader"] section {
    border: 1.5px dashed color-mix(in srgb, var(--acento) 45%, white); border-radius: 16px; background: var(--cartao);
}
[data-testid="stMetric"] {
    background: var(--cartao); border-radius: 18px; padding: 16px 18px;
    border: 1px solid var(--linha); border-top: 4px solid var(--acento);
}
[data-testid="stMetricLabel"] p { color: var(--mudo); }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    font-family: 'Bricolage Grotesque', sans-serif !important; font-weight: 700; color: var(--texto);
}
[data-testid="stExpander"] details { border: 1px solid var(--linha); border-radius: 16px; background: var(--cartao); }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* ---------- comanda (relatório da IA) ---------- */
@keyframes imprimir {
    from { clip-path: inset(0 0 100% 0); transform: translateY(-14px); }
    to { clip-path: inset(0 0 -20px 0); transform: none; }
}
[class*="st-key-ticket_"] {
    position: relative; max-width: 620px; margin: 2.4rem 0 2.2rem 0;
    background: #FFFEFA; color: var(--texto); padding: 26px 30px 34px 30px;
    border-top: 5px solid var(--acento);
    box-shadow: 0 18px 40px -22px rgba(28, 30, 36, .45);
    animation: imprimir 1.1s var(--curva) both;
}
[class*="st-key-ticket_"]::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: -10px; height: 10px;
    background:
        linear-gradient(135deg, #FFFEFA 5px, transparent 0) 0 0 / 14px 10px repeat-x,
        linear-gradient(225deg, #FFFEFA 5px, transparent 0) 0 0 / 14px 10px repeat-x;
}
[class*="st-key-ticket_"] p, [class*="st-key-ticket_"] li,
[class*="st-key-ticket_"] strong, [class*="st-key-ticket_"] span {
    font-family: 'Courier Prime', monospace; color: var(--texto); font-size: .98rem; line-height: 1.6;
}
[class*="st-key-ticket_"] h1, [class*="st-key-ticket_"] h2, [class*="st-key-ticket_"] h3, [class*="st-key-ticket_"] h4 {
    font-family: 'Courier Prime', monospace !important; font-size: 1.05rem; padding: .6rem 0 .2rem 0;
}
.ticket-topo {
    display: flex; justify-content: space-between; align-items: baseline; gap: 16px;
    border-bottom: 2px dashed #CFCAB9; padding-bottom: 12px; margin-bottom: 6px;
}
.ticket-topo strong { font-size: 1.15rem !important; }

/* ---------- avisos ---------- */
.aviso { margin: 1.2rem 0; padding: 12px 16px; border-radius: 14px; font-weight: 600; }
.aviso.alerta { color: #9B2C1F; background: #FDECEA; }
.aviso.ok { color: #15603F; background: #E6F5EE; }

@media (max-width: 720px) {
    .abertura { padding-top: 16vh; }
    [class*="st-key-card_"] { min-height: 0; }
}
@media (prefers-reduced-motion: reduce) {
    .abertura .marca, .abertura .robos, .st-key-btn_ok, .st-key-caixa_login, .saudacao,
    [class*="st-key-ticket_"] { animation: none; }
    [class*="st-key-card_"], .stButton > button { transition: none; }
    [class*="st-key-card_"]:hover, [class*="st-key-card_"]:active { transform: none; }
}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

CFG = {
    "funcionario": "Funcionário", "saldo": "Saldo", "situacao": "Situação",
    "data": "Data", "entrada": "Entrada", "saida": "Saída",
    "forma": "Forma", "status": "Status", "descricao": "Descrição",
    "esperado": st.column_config.NumberColumn("Esperado", format="R$ %.2f"),
    "recebido": st.column_config.NumberColumn("Recebido", format="R$ %.2f"),
    "diferenca": st.column_config.NumberColumn("Diferença", format="R$ %.2f"),
    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
}


# ---------- funções comuns ----------
def ir(tela, agente=None):
    st.session_state["tela"] = tela
    st.session_state["agente"] = agente
    st.rerun()


def titulo(texto, detalhe=""):
    extra = f"<small>{detalhe}</small>" if detalhe else ""
    st.markdown(f'<div class="titulo-secao">{texto}{extra}</div>', unsafe_allow_html=True)


def comanda(nome, relatorio):
    st.markdown(
        f'<div class="ticket-topo"><strong>{nome}</strong>'
        f'<span>{datetime.now():%d/%m/%Y %H:%M}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(relatorio)


def minutos(hora):
    h, m = str(hora).split(":")[:2]
    return int(h) * 60 + int(m)


def formatar(min_total):
    sinal = "+" if min_total >= 0 else "-"
    h, m = divmod(abs(int(min_total)), 60)
    return f"{sinal}{h}h{m:02d}"


def brl(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ler_arquivo(arquivo):
    if arquivo.name.lower().endswith(".csv"):
        return pd.read_csv(arquivo)
    return pd.read_excel(arquivo)


def padronizar_data(df):
    df["data"] = pd.to_datetime(df["data"]).dt.strftime("%Y-%m-%d")
    return df


def para_excel(abas):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as w:
        for nome, df in abas.items():
            df.to_excel(w, sheet_name=nome, index=False)
    return buffer.getvalue()


def perguntar_ia(pedido):
    try:
        cliente = genai.Client()
    except Exception as erro:
        return f"Chave da IA não encontrada: {erro}"
    for modelo in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]:
        try:
            return cliente.models.generate_content(model=modelo, contents=pedido).text
        except Exception:
            time.sleep(3)
    return "A IA não respondeu. Tente de novo mais tarde."


# ---------- login ----------
def carregar_usuarios():
    try:
        return {k: dict(v) for k, v in st.secrets["usuarios"].items()}
    except Exception:
        return {}


def conferir_login(usuario, senha):
    usuarios = carregar_usuarios()
    if not usuarios:
        usuarios = {"demo": {"senha": "demo", "nome": "Ronaldo"}}
    dados = usuarios.get(usuario.strip().lower())
    if dados and hmac.compare_digest(str(dados.get("senha", "")), senha):
        return dados.get("nome", usuario)
    return None


# ---------- pedido livre para um agente ----------
def dados_do_agente(chave):
    if chave == "rh" and "resultado_rh" in st.session_state:
        total = st.session_state["resultado_rh"]["total"]
        return "Saldo de horas da última planilha:\n" + total[["funcionario", "saldo", "situacao"]].to_string(index=False)
    if chave == "financeiro" and "resultado_fin" in st.session_state:
        r = st.session_state["resultado_fin"]
        div = r["divergentes"].to_string(index=False) if len(r["divergentes"]) else "nenhuma"
        return (
            f"Última conferência: {len(r['conc'])} vendas conferidas.\nDivergências:\n{div}\n\n"
            f"Contas pagas:\n{r['contas'].to_string(index=False)}"
        )
    return "Ainda não há planilha enviada nesta sessão."


def pedir_ao_agente(chave, pedido, nome_usuario):
    ag = AGENTES[chave]
    prompt = (
        f"Você é o agente de {ag['nome']} do sistema hnos system A, usado por um restaurante. "
        f"Você serve para {ag['serve']}. Responda em português, de forma curta e prática, "
        f"falando com {nome_usuario}.\n\n"
        f"O que você sabe fazer:\n{ag['contexto']}\n\n"
        f"Dados disponíveis agora:\n{dados_do_agente(chave)}\n\n"
        "Use apenas esses dados, sem inventar números. Se o pedido precisar de uma planilha que ainda "
        f"não foi enviada, diga qual planilha enviar na seção de {ag['nome']}. Se o pedido estiver fora "
        "do que você faz, diga isso com educação.\n\n"
        f"Pedido: {pedido}"
    )
    return perguntar_ia(prompt)


def caixa_de_pedido(nome_usuario, fixo=None):
    ativos = [k for k, a in AGENTES.items() if a["ativo"]]
    with st.container(key=f"caixa_pedido_{fixo or 'painel'}"):
        if fixo:
            titulo(f"Peça algo ao agente de {AGENTES[fixo]['nome']}")
            chave = fixo
        else:
            titulo("Peça algo", "Escreva o que precisa e marque o agente que vai fazer. Compras e Marketing chegam em breve.")
        with st.form(key=f"form_pedido_{fixo or 'painel'}", clear_on_submit=False, border=False):
            pedido = st.text_area(
                "Seu pedido",
                placeholder=(
                    "Ex.: quanto deixou de cair no banco esta semana?" if fixo == "financeiro"
                    else "Ex.: quem precisa compensar horas esta semana?"
                ),
                key=f"texto_pedido_{fixo or 'painel'}",
            )
            if not fixo:
                chave = st.radio(
                    "Agente", ativos, horizontal=True,
                    format_func=lambda k: AGENTES[k]["nome"], key="agente_pedido",
                )
            enviar = st.form_submit_button("Pedir ao agente", type="primary")
        if enviar:
            if not pedido.strip():
                st.warning("Escreva o pedido antes de enviar.")
            else:
                with st.spinner(f"O agente de {AGENTES[chave]['nome']} está trabalhando..."):
                    resposta = pedir_ao_agente(chave, pedido, nome_usuario)
                st.session_state[f"resposta_{fixo or 'painel'}"] = (chave, resposta)
        if f"resposta_{fixo or 'painel'}" in st.session_state:
            chave_r, resposta = st.session_state[f"resposta_{fixo or 'painel'}"]
            cor = AGENTES[chave_r]["cor"]
            st.markdown(
                f'<div class="resposta" style="--cor:{cor}"><div class="cartao-robo" style="color:{cor}">'
                f'{robo(chave_r, 40)}</div><div><strong>Agente de {AGENTES[chave_r]["nome"]}</strong></div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(resposta)


# ---------- página do RH ----------
def pagina_rh():
    titulo("Envie a planilha do RH", "Um arquivo .xlsx com as abas escala e ponto.")
    arq = st.file_uploader("Planilha do RH (.xlsx)", type=["xlsx"], key="upload_rh")
    calcular = bool(arq) and st.button("Calcular horas", type="primary", key="btn_rh")

    if calcular:
        escala = padronizar_data(pd.read_excel(arq, sheet_name="escala"))
        ponto = padronizar_data(pd.read_excel(arq, sheet_name="ponto"))
        dados = escala.merge(ponto, on=["funcionario", "data"])

        previsto = dados["saida_prevista"].apply(minutos) - dados["entrada_prevista"].apply(minutos)
        trabalhado = dados["saida"].apply(minutos) - dados["entrada"].apply(minutos)
        dados["saldo_min"] = trabalhado - previsto
        dados["saldo"] = dados["saldo_min"].apply(formatar)

        total = dados.groupby("funcionario")["saldo_min"].sum().reset_index()
        total["saldo"] = total["saldo_min"].apply(formatar)
        total["situacao"] = total["saldo_min"].apply(
            lambda m: "hora extra" if m > 0 else ("compensar" if m < 0 else "zerado")
        )

        resumo = total[["funcionario", "saldo", "situacao"]].to_string(index=False)
        pedido = (
            "Você é assistente de RH de um restaurante. Com base no saldo semanal de horas "
            "abaixo, escreva um relatório curto em português para o gerente: quem tem mais "
            "hora extra e quem precisa compensar. Só diga que alguém precisa compensar se a "
            "situação dele for 'compensar'. Use apenas os números fornecidos, sem calcular "
            "nada.\n\n" + resumo
        )
        with st.spinner("Escrevendo o relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_rh"] = {
            "dados": dados, "total": total, "relatorio": relatorio,
        }

    if "resultado_rh" in st.session_state:
        r = st.session_state["resultado_rh"]
        topo = r["total"].sort_values("saldo_min", ascending=False).iloc[0]
        extras = r["total"][r["total"]["saldo_min"] > 0]["saldo_min"].sum()

        titulo("Resumo da semana")
        c1, c2, c3 = st.columns(3)
        c1.metric("Funcionários", len(r["total"]))
        c2.metric("Horas extras no total", formatar(extras))
        c3.metric("Maior saldo", topo["funcionario"], topo["saldo"], delta_color="off")

        with st.container(key="ticket_rh"):
            comanda("Relatório do RH", r["relatorio"])

        titulo("Saldo por funcionário")
        st.dataframe(
            r["total"][["funcionario", "saldo", "situacao"]],
            hide_index=True, column_config=CFG,
        )

        titulo("Detalhes e exportação")
        with st.expander("Ver o saldo de cada dia"):
            st.dataframe(
                r["dados"][["funcionario", "data", "entrada", "saida", "saldo"]],
                hide_index=True, column_config=CFG,
            )
        st.download_button(
            "Baixar relatório (.xlsx)",
            para_excel({
                "por_dia": r["dados"][["funcionario", "data", "entrada", "saida", "saldo"]],
                "total": r["total"][["funcionario", "saldo", "situacao"]],
            }),
            file_name="relatorio_rh.xlsx",
        )


# ---------- página do Financeiro ----------
def pagina_financeiro():
    titulo("Envie as vendas e o extrato", "Arquivos .csv ou .xlsx do sistema de vendas e do banco.")
    col1, col2 = st.columns(2)
    f_vendas = col1.file_uploader("Vendas do sistema", type=["csv", "xlsx"], key="upload_vendas")
    f_extrato = col2.file_uploader("Extrato do banco", type=["csv", "xlsx"], key="upload_extrato")
    taxa = st.number_input("Taxa do cartão (%)", value=2.0, step=0.1) / 100
    conciliar = bool(f_vendas and f_extrato) and st.button(
        "Conferir pagamentos", type="primary", key="btn_fin"
    )

    if conciliar:
        vendas = padronizar_data(ler_arquivo(f_vendas))
        extrato = padronizar_data(ler_arquivo(f_extrato))

        vendas = vendas[vendas["forma"] != "dinheiro"].copy()
        vendas["esperado"] = vendas.apply(
            lambda l: l["valor"] * (1 - taxa) if l["forma"] == "cartao" else l["valor"],
            axis=1,
        )
        vendas["descricao"] = vendas["forma"].map(
            {"pix": "PIX recebido", "cartao": "Maquininha cartão"}
        )

        entradas = extrato[extrato["valor"] > 0]
        conc = vendas.merge(
            entradas, on=["data", "descricao"], how="left", suffixes=("_venda", "_banco")
        ).rename(columns={"valor_banco": "recebido"})
        conc["diferenca"] = (conc["recebido"] - conc["esperado"]).round(2)
        conc["status"] = conc["diferenca"].apply(
            lambda d: "OK" if abs(d) < 0.01 else "DIVERGENTE"
        )

        colunas = ["data", "forma", "esperado", "recebido", "diferenca", "status"]
        divergentes = conc[conc["status"] == "DIVERGENTE"][colunas]
        contas = extrato[extrato["valor"] < 0][["data", "descricao", "valor"]]

        resumo = (
            f"Linhas conciliadas: {len(conc)}\n"
            f"Divergências:\n{divergentes.to_string(index=False) if len(divergentes) else 'nenhuma'}\n\n"
            f"Contas pagas no período:\n{contas.to_string(index=False)}"
        )
        pedido = (
            "Você é assistente financeiro de um restaurante. Com base na conciliação "
            "abaixo, escreva um relatório curto em português para o gerente: destaque "
            "as divergências (e o valor) e liste as contas pagas. Use apenas os números "
            "fornecidos, sem calcular nada e sem inventar causas.\n\n" + resumo
        )
        with st.spinner("Escrevendo o relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_fin"] = {
            "conc": conc[colunas], "divergentes": divergentes,
            "contas": contas, "relatorio": relatorio,
        }

    if "resultado_fin" in st.session_state:
        r = st.session_state["resultado_fin"]
        n = len(r["divergentes"])

        titulo("Resumo do período")
        c1, c2, c3 = st.columns(3)
        c1.metric("Vendas conferidas", len(r["conc"]))
        c2.metric("Divergências", n)
        c3.metric("Contas pagas", brl(abs(r["contas"]["valor"].sum())))
        if n:
            texto = "1 pagamento não bateu com o banco" if n == 1 else f"{n} pagamentos não bateram com o banco"
            st.markdown(f'<div class="aviso alerta">{texto}. Veja quais abaixo.</div>', unsafe_allow_html=True)
            st.dataframe(r["divergentes"], hide_index=True, column_config=CFG)
        else:
            st.markdown(
                '<div class="aviso ok">Todos os pagamentos bateram com o banco.</div>',
                unsafe_allow_html=True,
            )

        with st.container(key="ticket_fin"):
            comanda("Relatório financeiro", r["relatorio"])

        titulo("Detalhes e exportação")
        with st.expander("Ver a conferência completa"):
            st.dataframe(r["conc"], hide_index=True, column_config=CFG)
        with st.expander("Ver as contas pagas no período"):
            st.dataframe(r["contas"], hide_index=True, column_config=CFG)
        st.download_button(
            "Baixar relatório (.xlsx)",
            para_excel({
                "conciliacao": r["conc"],
                "divergencias": r["divergentes"],
                "contas_pagas": r["contas"],
            }),
            file_name="relatorio_financeiro.xlsx",
        )


# ---------- telas ----------
def tela_abertura():
    robos = "".join(f'<div style="color:{a["cor"]}">{robo(k, 44)}</div>' for k, a in AGENTES.items())
    st.markdown(
        f'<div class="abertura"><div class="marca">hnos system <span>A</span></div>'
        f'<div class="robos">{robos}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("OK", type="primary", key="btn_ok"):
        ir("login")


def tela_login():
    with st.container(key="caixa_login"):
        st.markdown(
            '<p class="login-titulo">Entrar</p><p class="login-sub">Use o usuário e a senha do seu restaurante.</p>',
            unsafe_allow_html=True,
        )
        with st.form("form_login", border=False):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if entrar:
            nome = conferir_login(usuario, senha)
            if nome:
                st.session_state["usuario"] = nome
                ir("painel")
            else:
                st.error("Usuário ou senha incorretos. Confira e tente de novo.")
        if not carregar_usuarios():
            st.markdown(
                '<p class="dica">Modo demonstração: usuário <strong>demo</strong>, senha <strong>demo</strong>.</p>',
                unsafe_allow_html=True,
            )


def cabecalho(nome_usuario, cor=None):
    if cor:
        st.markdown(f"<style>:root {{ --acento: {cor}; }}</style>", unsafe_allow_html=True)
    with st.container(key="topo"):
        c1, c2 = st.columns([5, 1])
        c1.markdown(
            f'<div class="marca-topo"><div class="nome">hnos system <span>A</span></div>'
            f'<div class="com">with <strong>{nome_usuario.lower()}</strong></div></div>',
            unsafe_allow_html=True,
        )
        if c2.button("Sair", key="btn_sair"):
            st.session_state.clear()
            st.session_state["tela"] = "login"
            st.rerun()


def tela_painel(nome_usuario):
    cabecalho(nome_usuario, "#5B5BD6")
    colunas = st.columns(4, gap="large")
    for col, (chave, ag) in zip(colunas, AGENTES.items()):
        with col:
            with st.container(key=f"card_{chave}"):
                selo = "" if ag["ativo"] else '<span class="selo-producao">em produção</span>'
                st.markdown(
                    f'<div class="cartao-robo">{robo(chave, 58)}</div>'
                    f'<div class="cartao-nome">{ag["nome"]}</div>{selo}',
                    unsafe_allow_html=True,
                )
                if ag["ativo"] and st.button(f"Abrir {ag['nome']}", key=f"abrir_{chave}"):
                    ir("agente", chave)
            with st.popover("Contexto"):
                st.markdown(f"**Agente de {ag['nome']}**")
                st.markdown(ag["contexto"])
    caixa_de_pedido(nome_usuario)


def tela_agente(nome_usuario, chave):
    ag = AGENTES[chave]
    cabecalho(nome_usuario, ag["cor"])
    st.markdown(
        f"<style>.stApp {{ background: linear-gradient(180deg, {ag['tinta']} 0, var(--fundo) 520px); }}</style>",
        unsafe_allow_html=True,
    )
    if st.button("Voltar ao painel", key="btn_voltar"):
        ir("painel")
    st.markdown(
        f'<div class="saudacao">{robo(chave, 64)}<p>Olá, eu sou seu <strong>agente de {ag["nome"]}</strong>. '
        f'Sirvo para {ag["serve"]}. Do que você precisa hoje, {nome_usuario}?</p></div>',
        unsafe_allow_html=True,
    )
    if chave == "rh":
        pagina_rh()
    elif chave == "financeiro":
        pagina_financeiro()
    caixa_de_pedido(nome_usuario, fixo=chave)


# ---------- montagem ----------
tela = st.session_state.get("tela", "abertura")
usuario = st.session_state.get("usuario")

if tela in ("painel", "agente") and not usuario:
    tela = "login"

if tela == "abertura":
    tela_abertura()
elif tela == "login":
    tela_login()
elif tela == "agente" and AGENTES.get(st.session_state.get("agente"), {}).get("ativo"):
    tela_agente(usuario, st.session_state["agente"])
else:
    tela_painel(usuario)
