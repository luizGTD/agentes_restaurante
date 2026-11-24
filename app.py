import hmac
from html import escape
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
        "nome": "Compras", "cor": "#C77A0A", "tinta": "#FCF1DF", "ativo": True,
        "serve": "montar a lista de compras a partir do estoque e dos pedidos",
        "contexto": (
            "**O que eu faço:** analiso o estoque, comparo cotações e monto pedidos por fornecedor.\n\n**O que eu preciso:** uma planilha .xlsx com as abas estoque, cotacoes e fornecedores.\n\n**O que você recebe:** lista de compras, custos, economia, relatório e mensagens para revisar e enviar pelo WhatsApp."
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
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{--fundo:#080b14;--cartao:#111725;--linha:#28334a;--texto:#edf2ff;--mudo:#a3afc5;--acento:#a5a5ff;--curva:cubic-bezier(.2,.8,.2,1)}
.stApp{background:radial-gradient(ellipse at 85% 0%,#25234a 0%,transparent 40%),radial-gradient(ellipse at 0% 40%,#10283a 0%,transparent 38%),#080b14;color:var(--texto)}
.stApp p,.stApp label,.stApp li,.stMarkdown,button,input,textarea{font-family:Manrope,sans-serif;color:var(--texto)}
h1,h2,h3,.marca,.cartao-nome,.titulo-secao,.login-titulo{font-family:'Space Grotesk',sans-serif!important;color:var(--texto)}
#MainMenu,footer{visibility:hidden}[data-testid=stHeader]{background:transparent}.block-container{max-width:1250px;padding-top:2rem;padding-bottom:4rem}
@keyframes enter{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes orbit{to{transform:rotateZ(360deg)}}@keyframes float{50%{transform:translateY(-12px) rotate(-5deg)}}
@keyframes shine{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.st-key-topo{border-bottom:1px solid #ffffff18;padding-bottom:14px;margin-bottom:1rem}.marca-topo .nome{font:700 24px 'Space Grotesk',sans-serif;letter-spacing:-1px}.marca-topo .nome span,.marca span{color:#b4aaff}.marca-topo .com{font-size:12px;color:var(--mudo)}
.hero{position:relative;overflow:hidden;isolation:isolate;min-height:270px;border:1px solid #ffffff20;border-radius:32px;padding:38px;display:flex;align-items:center;background:linear-gradient(115deg,#192239b0,#15182e80);animation:enter .65s both}.hero-copy{position:relative;z-index:2;max-width:65%}.eyebrow{font-size:11px;letter-spacing:.22em;color:#b9b4ff;font-weight:800;text-transform:uppercase}.hero h1{font-size:clamp(32px,5vw,62px);line-height:1.04;letter-spacing:-.055em;margin:14px 0}.hero p{color:var(--mudo);max-width:490px;font-size:15px}.orb-stage{position:absolute;right:5%;top:50%;width:220px;height:220px;transform:translateY(-50%);perspective:650px;pointer-events:none}.orb{position:absolute;inset:36px;border-radius:50%;background:radial-gradient(circle at 32% 25%,#fff 0%,#b8c6ff 12%,#8174e8 34%,#353568 65%,#11142d 83%);box-shadow:inset -14px -18px 30px #080b24,0 0 65px #8878ff66;animation:float 6s ease-in-out infinite}.ring{position:absolute;inset:8px;border:1px solid #c6c9ff90;border-radius:50%;transform:rotateX(65deg) rotateZ(-25deg);box-shadow:0 0 15px #b6aaff44}.ring.r2{transform:rotateY(65deg) rotateZ(40deg)}.ring.r3{inset:0;transform:rotateX(40deg) rotateY(-45deg)}.orbit-dot{position:absolute;inset:0;animation:orbit 12s linear infinite}.orbit-dot:before{content:'';position:absolute;top:5px;left:50%;width:9px;height:9px;border-radius:50%;background:#fff;box-shadow:0 0 18px #a8baff}
.st-key-nav{background:#ffffff08;border:1px solid #ffffff1c;border-radius:22px;padding:10px;backdrop-filter:blur(24px);margin:10px 0 20px}.stButton>button,[data-testid=stFormSubmitButton]>button,[data-testid=stDownloadButton]>button,[data-testid=stLinkButton] a{border:1px solid #ffffff30!important;border-radius:16px!important;background:linear-gradient(145deg,#ffffff20,#ffffff07)!important;box-shadow:inset 0 1px 1px #ffffff38,0 8px 20px #0003!important;backdrop-filter:blur(20px) saturate(160%);color:#edf2ff!important;transition:transform .22s var(--curva),box-shadow .22s,border-color .22s!important;min-height:44px}.stButton>button:hover,[data-testid=stFormSubmitButton]>button:hover,[data-testid=stDownloadButton]>button:hover,[data-testid=stLinkButton] a:hover{transform:translateY(-3px);border-color:#c5baff!important;box-shadow:inset 0 1px 1px #ffffff70,0 8px 30px #a597ff40!important}.stButton>button:active{transform:scale(.97)}button[data-testid*=primary],button[data-testid*=Primary]{background:linear-gradient(135deg,#6654b9,#343b76)!important;border-color:#a69bff!important}button:focus-visible{outline:2px solid #d0c8ff!important;outline-offset:3px}
.st-key-card_rh{--cor:#a89cff}.st-key-card_financeiro{--cor:#69e5b5}.st-key-card_compras{--cor:#ffc37c}.st-key-card_marketing{--cor:#f3a2d4}[class*=st-key-card_]{border:1px solid #ffffff20;border-radius:26px;padding:22px;background:linear-gradient(145deg,#ffffff10,#ffffff03);box-shadow:0 18px 40px #0003,inset 0 1px 0 #ffffff18;transition:transform .3s var(--curva),border-color .3s;animation:enter .7s both;min-height:310px}[class*=st-key-card_]:hover{transform:perspective(900px) rotateX(3deg) translateY(-6px);border-color:var(--cor)}.cartao-robo{display:inline-flex;color:var(--cor);filter:drop-shadow(0 8px 14px var(--cor));padding:10px;border-radius:20px;background:#ffffff0b}.cartao-nome{font-size:25px;font-weight:700;margin:12px 0 4px}.cartao-serve{font-size:13px;color:var(--mudo);min-height:88px}.selo-producao{font-size:11px;color:var(--mudo);letter-spacing:.08em}.st-key-card_marketing{opacity:.85}[class*=st-key-card_] [data-testid=stButton] button:disabled{opacity:.65;cursor:not-allowed;transform:none!important}[class*=st-key-card_] .cartao-serve{height:88px;overflow-wrap:anywhere}@media(max-width:900px){[class*=st-key-card_] .cartao-serve{height:auto;min-height:110px}}@media(max-width:640px){[class*=st-key-card_] .cartao-serve{min-height:88px}}
.abertura{text-align:center;padding:12vh 0 2rem;animation:enter .8s both}.abertura .marca{font-size:clamp(42px,8vw,90px);font-weight:700;letter-spacing:-.07em}.abertura .orb-stage{position:relative;right:auto;top:auto;transform:none;margin:0 auto 30px}.abertura .robos{display:flex;justify-content:center;gap:24px;margin-top:24px}.st-key-btn_ok{max-width:240px;margin:auto}.st-key-caixa_login{max-width:440px;margin:9vh auto;padding:32px;border:1px solid #ffffff25;border-radius:30px;background:#151d30aa;backdrop-filter:blur(24px);animation:enter .6s both}.login-titulo{font-size:32px;font-weight:700}.login-sub,.dica{color:var(--mudo)!important;font-size:13px}
.saudacao{display:flex;align-items:center;gap:22px;padding:26px;border:1px solid #ffffff22;border-radius:26px;background:linear-gradient(135deg,#ffffff12,#ffffff04);color:var(--acento);animation:enter .6s both}.saudacao svg{flex:none;filter:drop-shadow(0 8px 14px var(--acento))}.saudacao p{margin:0}.titulo-secao{font-size:23px;font-weight:700;margin:30px 0 12px;letter-spacing:-.025em}.titulo-secao small{display:block;color:var(--mudo);font:400 13px Manrope,sans-serif;margin-top:5px}[class*=st-key-caixa_pedido],[class*=st-key-rev_cmp_]{background:#ffffff06;border:1px solid #ffffff16;border-radius:24px;padding:22px;margin-top:18px;animation:enter .6s both}[data-testid=stMetric]{border:1px solid #ffffff20;border-radius:20px;padding:18px;background:#ffffff09}[data-testid=stMetricValue]{color:var(--texto);font-family:'Space Grotesk',sans-serif}[data-testid=stFileUploader] section,[data-testid=stExpander] details{background:#141b2b;border:1px solid #ffffff25;border-radius:16px;color:var(--texto)}[data-baseweb=input],[data-baseweb=textarea],[data-baseweb=select]>div{background:#141b2b!important;border-color:#ffffff25!important;color:var(--texto)!important}input,textarea{color:var(--texto)!important}[data-testid=stDataFrame]{border:1px solid #ffffff20;border-radius:14px;overflow:hidden}[class*=st-key-ticket_]{border:1px solid #ffffff20;border-left:3px solid var(--acento);background:#151d30;border-radius:22px;padding:24px;margin:24px 0;animation:enter .7s both}.ticket-topo{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #ffffff20;padding-bottom:12px;margin-bottom:12px}.ticket-topo span{color:var(--mudo);font-size:12px}.resposta{display:flex;align-items:center;gap:14px;padding:16px;background:#ffffff08;border-radius:18px;margin-top:16px}.aviso{padding:14px;border-radius:14px;margin:12px 0}.aviso.alerta{background:#512a35;color:#ffd0d7}.aviso.ok{background:#163c32;color:#a5f4d0}
@media(max-width:700px){.hero{padding:24px;min-height:300px;align-items:flex-start}.hero-copy{max-width:100%}.hero .orb-stage{opacity:.35;right:-40px;top:75%;scale:.75}.block-container{padding-top:1rem}.saudacao{padding:16px}.st-key-nav{padding:5px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
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
    if chave == "compras" and "resultado_cmp" in st.session_state:
        r = st.session_state["resultado_cmp"]
        pedidos = r["pedidos"]
        resumo = pedidos.to_string(index=False) if not pedidos.empty else "Nenhum pedido gerado."
        return (
            f"Última análise de compras:\n{resumo}\n"
            f"Itens sem cotação: {', '.join(r['sem_cotacao']) or 'nenhum'}"
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
            titulo("Peça algo", "Escreva o que precisa e marque o agente que vai fazer. Marketing chega em breve.")
        with st.form(key=f"form_pedido_{fixo or 'painel'}", clear_on_submit=False, border=False):
            pedido = st.text_area(
                "Seu pedido",
                placeholder=(
                    "Ex.: quanto deixou de cair no banco esta semana?" if fixo == "financeiro"
                    else "Ex.: quais itens preciso comprar?" if fixo == "compras"
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
def esfera():
    return '<div class="orb-stage" aria-hidden="true"><div class="orb"></div><div class="ring"></div><div class="ring r2"></div><div class="ring r3"></div><div class="orbit-dot"></div></div>'


def tela_abertura():
    robos = "".join(f'<div style="color:{a["cor"]}">{robo(k, 44)}</div>' for k, a in AGENTES.items())
    st.markdown(
        f'<div class="abertura">{esfera()}<div class="eyebrow">Inteligência operacional</div><div class="marca">hnos system <span>A</span></div>'
        f'<div class="robos">{robos}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Entrar no sistema", type="primary", key="btn_ok"):
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


# ---------- página de Compras ----------
CFG.update({
    "item": "ITEM", "unidade": "UNIDADE", "quantidade": "QUANTIDADE",
    "fornecedor": "FORNECEDOR", "prazo_dias": "PRAZO (DIAS)", "motivo": "CRITÉRIO",
    "preco_unitario": st.column_config.NumberColumn("PREÇO UNIT.", format="R$ %.2f"),
    "total": st.column_config.NumberColumn("TOTAL", format="R$ %.2f"),
})

ESTILO_COMPRAS = ""

def modelo_compras():
    estoque = pd.DataFrame(
        [
            ("Tomate", "kg", 4, 10, 30),
            ("Filé de frango", "kg", 18, 15, 40),
            ("Queijo mussarela", "kg", 6, 8, 25),
            ("Farinha de trigo", "kg", 12, 20, 60),
            ("Óleo de soja", "L", 9, 10, 30),
            ("Cerveja long neck", "un", 120, 100, 400),
            ("Refrigerante lata", "un", 35, 80, 300),
            ("Limão", "kg", 3, 5, 15),
        ],
        columns=["item", "unidade", "qtd_atual", "qtd_minima", "qtd_ideal"],
    )
    cotacoes = pd.DataFrame(
        [
            ("Tomate", "Hortifruti Central", 6.80, 1),
            ("Tomate", "Atacado Sul", 6.20, 4),
            ("Tomate", "Distribuidora Bom Preço", 7.10, 2),
            ("Queijo mussarela", "Hortifruti Central", 41.00, 1),
            ("Queijo mussarela", "Atacado Sul", 38.50, 3),
            ("Queijo mussarela", "Distribuidora Bom Preço", 36.90, 5),
            ("Farinha de trigo", "Hortifruti Central", 5.00, 1),
            ("Farinha de trigo", "Atacado Sul", 4.30, 3),
            ("Farinha de trigo", "Distribuidora Bom Preço", 4.10, 6),
            ("Óleo de soja", "Hortifruti Central", 8.50, 1),
            ("Óleo de soja", "Atacado Sul", 7.90, 3),
            ("Óleo de soja", "Distribuidora Bom Preço", 7.40, 4),
            ("Refrigerante lata", "Bebidas Express", 2.60, 1),
            ("Refrigerante lata", "Atacado Sul", 2.45, 4),
            ("Refrigerante lata", "Distribuidora Bom Preço", 2.35, 7),
            ("Limão", "Hortifruti Central", 5.50, 1),
            ("Limão", "Atacado Sul", 4.80, 4),
            ("Limão", "Distribuidora Bom Preço", 5.20, 2),
            ("Filé de frango", "Atacado Sul", 18.90, 3),
            ("Filé de frango", "Distribuidora Bom Preço", 17.80, 4),
            ("Cerveja long neck", "Bebidas Express", 4.20, 1),
            ("Cerveja long neck", "Atacado Sul", 3.95, 3),
        ],
        columns=["item", "fornecedor", "preco_unitario", "prazo_dias"],
    )
    fornecedores = pd.DataFrame(
        [
            ("Hortifruti Central", "5511900000001"),
            ("Atacado Sul", "5511900000002"),
            ("Distribuidora Bom Preço", "5511900000003"),
            ("Bebidas Express", "5511900000004"),
        ],
        columns=["fornecedor", "whatsapp"],
    )
    return {"estoque": estoque, "cotacoes": cotacoes, "fornecedores": fornecedores}


def escolher_fornecedor(cot, prazo_max):
    dentro = cot[cot["prazo_dias"] <= prazo_max]
    if len(dentro):
        return dentro.sort_values(["preco_unitario", "prazo_dias"]).iloc[0], "menor preço no prazo"
    return cot.sort_values(["prazo_dias", "preco_unitario"]).iloc[0], "ninguém no prazo: mais rápido"


def calcular_compras(estoque, cotacoes, prazo_max):
    precisa = estoque[estoque["qtd_atual"] <= estoque["qtd_minima"]]
    linhas, sem_cotacao = [], []
    for _, it in precisa.iterrows():
        cot = cotacoes[cotacoes["item"] == it["item"]]
        if cot.empty:
            sem_cotacao.append(str(it["item"]))
            continue
        esc, motivo = escolher_fornecedor(cot, prazo_max)
        qtd = float(it["qtd_ideal"] - it["qtd_atual"])
        preco = float(esc["preco_unitario"])
        linhas.append({
            "item": it["item"], "unidade": it["unidade"], "quantidade": qtd,
            "fornecedor": esc["fornecedor"], "preco_unitario": preco,
            "prazo_dias": int(esc["prazo_dias"]),
            "total": round(qtd * preco, 2),
            "economia": round(qtd * (float(cot["preco_unitario"].max()) - preco), 2),
            "motivo": motivo,
        })
    return pd.DataFrame(linhas), sem_cotacao


def montar_mensagem(fornecedor, itens):
    linhas = [
        f"- {l['quantidade']:g} {l['unidade']} de {l['item']} "
        f"({brl(l['preco_unitario'])} por {l['unidade']})"
        for _, l in itens.iterrows()
    ]
    return (
        f"Olá, {fornecedor}! Gostaria de fazer o seguinte pedido:\n\n"
        + "\n".join(linhas)
        + f"\n\nTotal estimado: {brl(itens['total'].sum())}\n"
        + "Pode confirmar disponibilidade e prazo de entrega? Obrigado!"
    )


def rotulo(numero, texto):
    titulo(f"{numero} · {texto}")


def pagina_compras():
    st.markdown(ESTILO_COMPRAS, unsafe_allow_html=True)
    from urllib.parse import quote

    with st.container(key="rev_cmp_entrada"):
        rotulo("01", "Entrada de dados · planilha com as abas estoque, cotacoes e fornecedores")
        st.download_button(
            "Baixar planilha modelo", para_excel(modelo_compras()),
            file_name="modelo_compras.xlsx",
        )
        arq = st.file_uploader("Planilha de compras (.xlsx)", type=["xlsx"], key="upload_compras")
        prazo_max = st.number_input("Prazo máximo de entrega (dias)", value=3, min_value=1, step=1)
        gerar = bool(arq) and st.button("Gerar pedidos", type="primary", key="btn_cmp")

    if gerar:
        try:
            estoque = pd.read_excel(arq, sheet_name="estoque")
            cotacoes = pd.read_excel(arq, sheet_name="cotacoes")
            fornecedores = pd.read_excel(arq, sheet_name="fornecedores")
            pedidos, sem_cotacao = calcular_compras(estoque, cotacoes, prazo_max)
        except (ValueError, KeyError):
            st.session_state.pop("resultado_cmp", None)
            st.markdown(
                '<div class="aviso alerta">PLANILHA FORA DO PADRÃO · BAIXE O MODELO</div>',
                unsafe_allow_html=True,
            )
        else:
            relatorio = ""
            if len(pedidos):
                colunas_ia = ["item", "quantidade", "unidade", "fornecedor",
                              "preco_unitario", "prazo_dias", "total"]
                resumo = (
                    f"Itens a comprar:\n{pedidos[colunas_ia].to_string(index=False)}\n\n"
                    f"Total geral: {brl(pedidos['total'].sum())}\n"
                    f"Economia em relação à cotação mais cara: {brl(pedidos['economia'].sum())}\n"
                    f"Itens sem cotação: {', '.join(sem_cotacao) if sem_cotacao else 'nenhum'}\n"
                    f"Prazo máximo: {prazo_max} dias"
                )
                pedido_ia = (
                    "Você é assistente de compras de um restaurante. Com base nos dados "
                    "abaixo, escreva um relatório curto em português para o gerente: o que "
                    "precisa ser comprado, de quais fornecedores, o total e a economia. "
                    "Use apenas os números fornecidos, sem calcular nada e sem inventar "
                    "nada.\n\n" + resumo
                )
                with st.spinner("Processando relatório..."):
                    relatorio = perguntar_ia(pedido_ia)

            tels = {
                str(f): "".join(c for c in str(w) if c.isdigit())
                for f, w in zip(fornecedores["fornecedor"], fornecedores["whatsapp"])
            }
            st.session_state["resultado_cmp"] = {
                "pedidos": pedidos, "sem_cotacao": sem_cotacao,
                "relatorio": relatorio, "tels": tels,
            }

    if "resultado_cmp" not in st.session_state:
        return

    r = st.session_state["resultado_cmp"]
    pedidos = r["pedidos"]

    if r["sem_cotacao"]:
        nomes = ", ".join(r["sem_cotacao"]).upper()
        st.markdown(
            f'<div class="aviso alerta">SEM COTAÇÃO: {nomes}</div>',
            unsafe_allow_html=True,
        )
    if pedidos.empty:
        if not r["sem_cotacao"]:
            st.markdown(
                '<div class="aviso ok">ESTOQUE EM DIA · NADA PARA COMPRAR</div>',
                unsafe_allow_html=True,
            )
        return

    with st.container(key="rev_cmp_resumo"):
        rotulo("02", "Resumo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Itens a comprar", len(pedidos))
        c2.metric("Fornecedores", pedidos["fornecedor"].nunique())
        c3.metric("Total do pedido", brl(pedidos["total"].sum()))
        c4.metric("Economia", brl(pedidos["economia"].sum()))

    with st.container(key="rev_cmp_lista"):
        rotulo("03", "Melhor opção por item")
        st.dataframe(
            pedidos[["item", "quantidade", "unidade", "fornecedor",
                     "preco_unitario", "prazo_dias", "total", "motivo"]],
            hide_index=True, column_config=CFG,
        )

    with st.container(key="rev_cmp_relatorio"):
        rotulo("04", "Relatório · IA")
        st.markdown(r["relatorio"])

    with st.container(key="rev_cmp_envio"):
        rotulo("05", "Pedidos por fornecedor · revise antes de enviar")
        for forn, itens in pedidos.groupby("fornecedor"):
            with st.expander(f"{forn} · {brl(itens['total'].sum())}", expanded=True):
                st.dataframe(
                    itens[["item", "quantidade", "unidade", "preco_unitario", "prazo_dias", "total"]],
                    hide_index=True, column_config=CFG,
                )
                msg = montar_mensagem(forn, itens)
                st.code(msg, language=None)
                numero = r["tels"].get(str(forn), "")
                if numero:
                    st.link_button(
                        "Abrir no WhatsApp", f"https://wa.me/{numero}?text={quote(msg)}"
                    )
                else:
                    st.caption("Sem WhatsApp cadastrado para este fornecedor.")

    with st.container(key="rev_cmp_export"):
        rotulo("06", "Exportação")
        por_fornecedor = pedidos.groupby("fornecedor")["total"].sum().reset_index()
        st.download_button(
            "Baixar pedidos (.xlsx)",
            para_excel({
                "pedidos": pedidos.drop(columns=["economia"]),
                "por_fornecedor": por_fornecedor,
            }),
            file_name="pedidos_compras.xlsx",
        )



def cabecalho(nome_usuario, cor=None):
    if cor:
        st.markdown(f"<style>:root {{ --acento: {cor}; }}</style>", unsafe_allow_html=True)
    with st.container(key="topo"):
        c1, c2 = st.columns([5, 1])
        c1.markdown(
            f'<div class="marca-topo"><div class="nome">hnos system <span>A</span></div>'
            f'<div class="com">with <strong>{escape(nome_usuario.lower())}</strong></div></div>',
            unsafe_allow_html=True,
        )
        if c2.button("Sair", key="btn_sair"):
            st.session_state.clear()
            st.session_state["tela"] = "login"
            st.rerun()


def navegacao(atual=None):
    with st.container(key="nav"):
        cols = st.columns(4)
        for col, (chave, nome) in zip(cols, [(None, "Visão geral"), ("rh", "RH"), ("financeiro", "Financeiro"), ("compras", "Compras")]):
            if col.button(nome, key=f"nav_{chave}", type="primary" if atual == chave else "secondary", use_container_width=True):
                ir("painel" if chave is None else "agente", chave)


def tela_painel(nome_usuario):
    cabecalho(nome_usuario, "#a5a5ff")
    navegacao()
    st.markdown(f'<div class="hero"><div class="hero-copy"><div class="eyebrow">Workspace / 03 agentes disponíveis</div><h1>Seu restaurante.<br>Uma nova inteligência.</h1><p>Olá, {escape(nome_usuario)}. Gerencie pessoas, pagamentos e compras em um único espaço.</p></div>{esfera()}</div>', unsafe_allow_html=True)
    titulo("Seus agentes", "Escolha uma especialidade para começar.")
    colunas = st.columns(4, gap="large")
    for col, (chave, ag) in zip(colunas, AGENTES.items()):
        with col:
            with st.container(key=f"card_{chave}"):
                st.markdown(
                    f'<div class="cartao-robo">{robo(chave, 58)}</div>'
                    f'<div class="cartao-nome">{ag["nome"]}</div><div class="cartao-serve">{ag["serve"].capitalize()}.</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Abrir {ag['nome']}" if ag["ativo"] else "Em produção", key=f"abrir_{chave}", use_container_width=True, disabled=not ag["ativo"]):
                    ir("agente", chave)
            with st.popover("Contexto"):
                st.markdown(f"**Agente de {ag['nome']}**")
                st.markdown(ag["contexto"])
    caixa_de_pedido(nome_usuario)


def tela_agente(nome_usuario, chave):
    ag = AGENTES[chave]
    cabecalho(nome_usuario, ag["cor"])
    navegacao(chave)
    st.markdown(
        f'<div class="saudacao">{robo(chave, 64)}<p>Olá, eu sou seu <strong>agente de {ag["nome"]}</strong>. '
        f'Sirvo para {ag["serve"]}. Do que você precisa hoje, {escape(nome_usuario)}?</p></div>',
        unsafe_allow_html=True,
    )
    if chave == "rh":
        pagina_rh()
    elif chave == "financeiro":
        pagina_financeiro()
    elif chave == "compras":
        pagina_compras()
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
