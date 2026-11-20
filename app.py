import io
import time
from datetime import datetime
import pandas as pd
import streamlit as st
from google import genai

st.set_page_config(page_title="Painel do Restaurante", page_icon="🍽️", layout="wide")

ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Young+Serif&family=Instrument+Sans:wght@400;500;600&family=Courier+Prime:wght@400;700&display=swap');

:root {
    --garrafa: #17322A; --garrafa-clara: #1F4136; --linha: #2E5446;
    --papel: #F6F3EA; --mudo: #A9BBB1; --tinta: #22251F;
    --tomate: #C8432B; --tomate-claro: #D8553C; --mostarda: #E8B04A; --manjericao: #7FBF8E;
    --curva: cubic-bezier(0.22, 1, 0.36, 1);
}

.stApp { background: var(--garrafa); color: var(--papel); }
.stApp, .stApp p, .stApp label, .stApp li, .stMarkdown, button, input, textarea {
    font-family: 'Instrument Sans', sans-serif;
}
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1120px; }

/* ---------- cabeçalho ---------- */
.cabecalho {
    display: grid; grid-template-columns: 1fr auto; gap: 48px; align-items: end;
    padding: 1rem 0 2.4rem 0; margin-bottom: 1.6rem; border-bottom: 1px solid var(--linha);
}
.cabecalho h1 {
    font-family: 'Young Serif', serif; font-weight: 400; color: var(--papel);
    font-size: clamp(2.6rem, 5.6vw, 4.6rem); line-height: 1.02; letter-spacing: -.01em;
    margin: 0; padding: 0;
}
.cabecalho .intro {
    color: var(--mudo); font-size: 1.05rem; line-height: 1.55; max-width: 46ch;
    margin: 1.1rem 0 0 0;
}
.equipe { min-width: 250px; }
.equipe h2 {
    font-family: 'Young Serif', serif; font-weight: 400; font-size: 1.05rem;
    color: var(--papel); margin: 0 0 .6rem 0; padding: 0;
}
.equipe ul { list-style: none; margin: 0; padding: 0; }
.equipe li {
    display: flex; justify-content: space-between; align-items: center; gap: 24px;
    padding: .5rem 0; border-top: 1px solid var(--linha); margin: 0;
    font-size: .98rem; color: var(--papel);
}
.selo {
    font-size: .8rem; padding: .15rem .6rem; border-radius: 999px; white-space: nowrap;
}
.selo.pronto { color: var(--manjericao); background: rgba(127, 191, 142, .12); }
.selo.producao { color: var(--mostarda); background: rgba(232, 176, 74, .12); }
.equipe li.desligado { color: var(--mudo); }
@media (max-width: 720px) {
    .cabecalho { grid-template-columns: 1fr; gap: 28px; }
    .cabecalho h1 { font-size: 2.5rem; }
    .stTabs [role="tablist"] { gap: 22px; }
}

/* ---------- títulos de seção ---------- */
.titulo-secao {
    font-family: 'Young Serif', serif; font-weight: 400; font-size: 1.45rem;
    color: var(--papel); margin: 2.4rem 0 .9rem 0;
}
.titulo-secao small {
    display: block; font-family: 'Instrument Sans', sans-serif; font-size: .92rem;
    color: var(--mudo); margin-top: .25rem;
}

/* ---------- abas ---------- */
.stTabs [role="tablist"] { gap: 36px; border-bottom: 1px solid var(--linha); }
.stTabs [data-testid="stTab"] { background: transparent; height: auto; padding: 0 0 12px 0; }
.stTabs [data-testid="stTab"] p {
    font-family: 'Young Serif', serif; font-size: 1.2rem; color: var(--mudo);
}
.stTabs [data-testid="stTab"]:hover p { color: var(--papel); }
.stTabs [data-testid="stTab"][aria-selected="true"] p { color: var(--papel); }
.stTabs .react-aria-SelectionIndicator { background: var(--tomate-claro) !important; height: 3px !important; }
.stTabs [data-testid="stTab"]:nth-of-type(n+3) { pointer-events: none; cursor: default; }
.stTabs [data-testid="stTab"]:nth-of-type(n+3) p { color: #6F8A7E; }
.stTabs [data-testid="stTab"]:nth-of-type(n+3) p::after {
    content: "em produção"; margin-left: .6rem; vertical-align: middle;
    font-family: 'Instrument Sans', sans-serif; font-size: .72rem;
    color: var(--mostarda); background: rgba(232, 176, 74, .12);
    padding: .12rem .5rem; border-radius: 999px;
}

/* ---------- números ---------- */
[data-testid="stMetric"] {
    border-left: 3px solid var(--mostarda); padding: 2px 0 2px 16px;
}
[data-testid="stMetricLabel"] p { font-size: .95rem; color: var(--mudo); }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    font-family: 'Young Serif', serif !important; font-size: 2.2rem; color: var(--papel);
}
[data-testid="stMetricDelta"] { color: var(--mudo); }

/* ---------- botões (resposta ao clique) ---------- */
.stButton > button, [data-testid="stDownloadButton"] > button {
    border-radius: 8px; border: 1px solid var(--papel); background: transparent;
    padding: .7rem 1.4rem;
    transition: transform .2s var(--curva), background-color .2s var(--curva), border-color .2s var(--curva);
}
.stButton > button p, [data-testid="stDownloadButton"] > button p {
    font-size: 1rem; font-weight: 600; color: var(--papel);
}
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
    background: rgba(246, 243, 234, .08); border-color: var(--papel);
}
.stButton > button:active, [data-testid="stDownloadButton"] > button:active { transform: scale(.98); }
button[data-testid="stBaseButton-primary"] { background: var(--tomate); border-color: var(--tomate); }
button[data-testid="stBaseButton-primary"]:hover { background: var(--tomate-claro); border-color: var(--tomate-claro); }
button:focus-visible { outline: 2px solid var(--mostarda) !important; outline-offset: 3px; }

/* ---------- upload, tabelas, expanders ---------- */
[data-testid="stFileUploader"] section {
    border: 1.5px dashed #5C7D70; border-radius: 10px; background: var(--garrafa-clara);
}
[data-testid="stFileUploader"] section:hover { border-color: var(--papel); }
[data-testid="stFileUploader"] label p, [data-testid="stNumberInput"] label p {
    font-size: .98rem; color: var(--papel);
}
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
[data-testid="stExpander"] details {
    border: 1px solid var(--linha); border-radius: 10px; background: var(--garrafa-clara);
}
[data-testid="stExpander"] summary p { font-size: 1rem; font-weight: 600; }

/* ---------- a comanda: relatório da IA impresso ---------- */
@keyframes imprimir {
    from { clip-path: inset(0 0 100% 0); transform: translateY(-14px); }
    to { clip-path: inset(0 0 -20px 0); transform: none; }
}
[class*="st-key-ticket_"] {
    position: relative; max-width: 620px; margin: 2.6rem 0 2.2rem 0;
    background: var(--papel); color: var(--tinta);
    padding: 26px 30px 34px 30px; border-radius: 2px 2px 0 0;
    box-shadow: 0 18px 40px -18px rgba(0, 0, 0, .55);
    animation: imprimir 1.1s var(--curva) both;
}
[class*="st-key-ticket_"]::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: -10px; height: 10px;
    background:
        linear-gradient(135deg, var(--papel) 5px, transparent 0) 0 0 / 14px 10px repeat-x,
        linear-gradient(225deg, var(--papel) 5px, transparent 0) 0 0 / 14px 10px repeat-x;
}
[class*="st-key-ticket_"] p, [class*="st-key-ticket_"] li,
[class*="st-key-ticket_"] strong, [class*="st-key-ticket_"] span {
    font-family: 'Courier Prime', monospace; color: var(--tinta); font-size: .98rem; line-height: 1.6;
}
[class*="st-key-ticket_"] h1, [class*="st-key-ticket_"] h2,
[class*="st-key-ticket_"] h3, [class*="st-key-ticket_"] h4 {
    font-family: 'Courier Prime', monospace; font-weight: 700; color: var(--tinta);
    font-size: 1.05rem; padding: .6rem 0 .2rem 0;
}
.ticket-topo {
    display: flex; justify-content: space-between; align-items: baseline; gap: 16px;
    border-bottom: 2px dashed #B9B3A3; padding-bottom: 12px; margin-bottom: 6px;
}
.ticket-topo strong { font-size: 1.15rem !important; }

/* ---------- avisos ---------- */
.aviso {
    margin: 1.2rem 0; padding: 12px 16px; border-radius: 8px; font-size: 1rem; font-weight: 600;
}
.aviso.alerta { color: #FFD9CF; background: rgba(200, 67, 43, .28); border-left: 4px solid var(--tomate-claro); }
.aviso.ok { color: #D3F0DA; background: rgba(127, 191, 142, .16); border-left: 4px solid var(--manjericao); }

/* ---------- em produção ---------- */
.em-producao {
    max-width: 52ch; margin: 2rem 0; padding: 22px 24px; border-radius: 10px;
    background: var(--garrafa-clara); border: 1px dashed var(--mostarda);
}
.em-producao h3 { font-family: 'Young Serif', serif; font-weight: 400; color: var(--papel); padding: 0; margin: 0 0 .4rem 0; }
.em-producao p { color: var(--mudo); margin: 0; }

/* ---------- movimento reduzido ---------- */
@media (prefers-reduced-motion: reduce) {
    [class*="st-key-ticket_"] { animation: none; }
    .stButton > button, [data-testid="stDownloadButton"] > button { transition: none; }
    .stButton > button:active, [data-testid="stDownloadButton"] > button:active { transform: none; }
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


def em_producao(nome, descricao):
    st.markdown(
        f'<div class="em-producao"><h3>{nome} está em produção</h3><p>{descricao}</p></div>',
        unsafe_allow_html=True,
    )


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


# ---------- montagem do site ----------
st.markdown(
    '<div class="cabecalho">'
    '<div>'
    '<h1>O que vamos<br>resolver hoje?</h1>'
    '<p class="intro">Envie a planilha e o painel faz as contas e escreve o '
    'relatório para você.</p>'
    '</div>'
    '<div class="equipe"><h2>Sua equipe</h2><ul>'
    '<li>RH <span class="selo pronto">pronto</span></li>'
    '<li>Financeiro <span class="selo pronto">pronto</span></li>'
    '<li class="desligado">Compras <span class="selo producao">em produção</span></li>'
    '<li class="desligado">Marketing <span class="selo producao">em produção</span></li>'
    '</ul></div>'
    '</div>',
    unsafe_allow_html=True,
)

aba_rh, aba_fin, aba_compras, aba_mkt = st.tabs(["RH", "Financeiro", "Compras", "Marketing"])
with aba_rh:
    pagina_rh()
with aba_fin:
    pagina_financeiro()
with aba_compras:
    em_producao("Compras", "Em breve o painel vai montar a lista de compras a partir do estoque e dos pedidos.")
with aba_mkt:
    em_producao("Marketing", "Em breve o painel vai buscar as notícias do dia, criar os posts e agendar no Instagram.")
