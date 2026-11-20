import io
import time
import pandas as pd
import streamlit as st
from google import genai

st.set_page_config(page_title="Agentes do Restaurante", page_icon="■", layout="wide")

ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #0A0B0D; --painel: #111215; --linha: #23262B;
    --texto: #E9E9E6; --mudo: #8A8F98; --acento: #D4FF3A; --alerta: #FF5A36;
    --curva: cubic-bezier(0.22, 1, 0.36, 1);
}

.stApp { background: var(--bg); color: var(--texto); }
.stApp, .stApp p, .stApp label, .stMarkdown, button, input, textarea {
    font-family: 'Space Grotesk', sans-serif;
}
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }

/* ---------- entradas (opacidade + subida suave) ---------- */
@keyframes entrada {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: none; }
}
@keyframes entrada-mob {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
}
.hero-grupo { animation: entrada .8s var(--curva) both; }
[class*="st-key-rev_"] { animation: entrada 1s var(--curva) .1s both; }
@media (max-width: 640px) {
    .hero-grupo { animation-name: entrada-mob; }
    [class*="st-key-rev_"] { animation-name: entrada-mob; }
}

/* ---------- topo ---------- */
.topbar {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 24px; border-bottom: 1px solid var(--linha);
    padding: 1rem 0 28px 0;
}
.marca {
    font-size: clamp(2.8rem, 6.2vw, 5.4rem); font-weight: 500;
    letter-spacing: -.045em; line-height: .98; color: var(--texto);
}
.marca em { font-style: normal; color: var(--acento); }
.status {
    display: inline-flex; align-items: center; white-space: nowrap; margin-top: .7rem;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    letter-spacing: .14em; text-transform: uppercase; color: var(--mudo);
}
.dot {
    display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    background: var(--acento); margin-right: 8px; animation: pulso 2s infinite;
}
@keyframes pulso { 50% { opacity: .2; } }
.sub {
    font-family: 'JetBrains Mono', monospace; font-size: .82rem;
    color: var(--mudo); max-width: 560px; line-height: 1.6; margin: 1.4rem 0 2rem 0;
}
@media (max-width: 640px) {
    .topbar { flex-direction: column; }
    .marca { font-size: 2.6rem; }
}

/* ---------- rótulo de seção ---------- */
.rotulo {
    display: flex; gap: 14px; border-top: 1px solid var(--linha);
    padding-top: 10px; margin: 2.2rem 0 1rem 0;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    letter-spacing: .14em; text-transform: uppercase; color: var(--mudo);
}
.rotulo span { color: var(--acento); }

/* ---------- abas ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 30px; border-bottom: 1px solid var(--linha); }
.stTabs [data-baseweb="tab"] { background: transparent; height: auto; padding: 0 0 12px 0; }
.stTabs [data-baseweb="tab"] p {
    font-family: 'JetBrains Mono', monospace; font-size: .8rem;
    letter-spacing: .14em; text-transform: uppercase; color: var(--mudo);
}
.stTabs [aria-selected="true"] p { color: var(--acento); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--acento); height: 2px; }
.stTabs [data-baseweb="tab-border"] { background: var(--linha); }

/* ---------- números ---------- */
[data-testid="stMetric"] {
    background: var(--painel); border: 1px solid var(--linha);
    border-radius: 2px; padding: 18px 20px;
}
[data-testid="stMetricLabel"] p {
    font-family: 'JetBrains Mono', monospace; font-size: .7rem;
    letter-spacing: .14em; text-transform: uppercase; color: var(--mudo);
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace; font-weight: 500;
    font-size: 1.9rem; letter-spacing: -.03em;
}
[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace; color: var(--mudo); }

/* ---------- botões (feedback: hover 1.01, clique 0.99) ---------- */
.stButton > button, [data-testid="stDownloadButton"] > button {
    border-radius: 2px; border: 1px solid var(--texto); background: transparent;
    padding: .75rem 1.5rem;
    transition: transform .25s var(--curva), border-color .25s var(--curva), background-color .25s var(--curva);
}
.stButton > button p, [data-testid="stDownloadButton"] > button p {
    font-family: 'JetBrains Mono', monospace; font-size: .78rem;
    letter-spacing: .1em; text-transform: uppercase; color: var(--texto);
}
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
    transform: scale(1.01); border-color: var(--acento);
}
.stButton > button:hover p, [data-testid="stDownloadButton"] > button:hover p { color: var(--acento); }
.stButton > button:active, [data-testid="stDownloadButton"] > button:active {
    transform: scale(.99); transition-duration: .1s;
}
button[data-testid="stBaseButton-primary"] { background: var(--acento); border: 1px solid var(--acento); }
button[data-testid="stBaseButton-primary"] p { color: #0A0B0D; font-weight: 700; }
button[data-testid="stBaseButton-primary"]:hover { background: #E6FF7A; border-color: #E6FF7A; }
button[data-testid="stBaseButton-primary"]:hover p { color: #0A0B0D; }

/* ---------- upload, tabelas, expanders ---------- */
[data-testid="stFileUploader"] section {
    border: 1px dashed #3A3E46; border-radius: 2px; background: var(--painel);
}
[data-testid="stFileUploader"] section:hover { border-color: var(--acento); }
[data-testid="stFileUploader"] label p, [data-testid="stNumberInput"] label p {
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    letter-spacing: .12em; text-transform: uppercase; color: var(--mudo);
}
[data-testid="stDataFrame"] { border: 1px solid var(--linha); border-radius: 2px; }
[data-testid="stExpander"] {
    border: 1px solid var(--linha); border-radius: 2px; background: var(--painel);
}
[data-testid="stExpander"] summary p {
    font-family: 'JetBrains Mono', monospace; font-size: .76rem;
    letter-spacing: .1em; text-transform: uppercase;
}
[data-baseweb="input"], [data-baseweb="base-input"] { border-radius: 2px; }

/* ---------- relatório da IA (painel) ---------- */
[class*="st-key-rev_"][class*="_relatorio"] {
    background: var(--painel); border: 1px solid var(--linha);
    border-left: 2px solid var(--acento); border-radius: 2px; padding: 22px 26px;
    margin-top: 2.2rem;
}
[class*="st-key-rev_"][class*="_relatorio"] .rotulo {
    border-top: none; padding-top: 0; margin: 0 0 .4rem 0;
}

/* ---------- avisos ---------- */
.aviso {
    display: flex; align-items: center; gap: 12px; margin: 1rem 0;
    padding: 12px 16px; border: 1px solid; border-radius: 2px;
    font-family: 'JetBrains Mono', monospace; font-size: .78rem; letter-spacing: .12em;
}
.aviso::before { content: ""; width: 8px; height: 8px; background: currentColor; }
.aviso.alerta { color: var(--alerta); border-color: var(--alerta); }
.aviso.ok { color: var(--acento); border-color: var(--acento); }

/* ---------- movimento reduzido: sem subida, sem escala, sem pulso ---------- */
@media (prefers-reduced-motion: reduce) {
    .hero-grupo, [class*="st-key-rev_"] { animation: none; }
    .dot { animation: none; }
    .stButton > button, [data-testid="stDownloadButton"] > button { transition: none; }
    .stButton > button:hover, [data-testid="stDownloadButton"] > button:hover,
    .stButton > button:active, [data-testid="stDownloadButton"] > button:active { transform: none; }
}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

CFG = {
    "funcionario": "FUNCIONÁRIO", "saldo": "SALDO", "situacao": "SITUAÇÃO",
    "data": "DATA", "entrada": "ENTRADA", "saida": "SAÍDA",
    "forma": "FORMA", "status": "STATUS", "descricao": "DESCRIÇÃO",
    "esperado": st.column_config.NumberColumn("ESPERADO", format="R$ %.2f"),
    "recebido": st.column_config.NumberColumn("RECEBIDO", format="R$ %.2f"),
    "diferenca": st.column_config.NumberColumn("DIFERENÇA", format="R$ %.2f"),
    "valor": st.column_config.NumberColumn("VALOR", format="R$ %.2f"),
}


# ---------- funções comuns ----------
def rotulo(numero, texto):
    st.markdown(
        f'<div class="rotulo"><span>{numero}</span>{texto}</div>',
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
    with st.container(key="rev_rh_entrada"):
        rotulo("01", "Entrada de dados · planilha com as abas escala e ponto")
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
        with st.spinner("Processando relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_rh"] = {
            "dados": dados, "total": total, "relatorio": relatorio,
        }

    if "resultado_rh" in st.session_state:
        r = st.session_state["resultado_rh"]
        topo = r["total"].sort_values("saldo_min", ascending=False).iloc[0]
        extras = r["total"][r["total"]["saldo_min"] > 0]["saldo_min"].sum()

        with st.container(key="rev_rh_resumo"):
            rotulo("02", "Resumo")
            c1, c2, c3 = st.columns(3)
            c1.metric("Funcionários", len(r["total"]))
            c2.metric("Horas extras no total", formatar(extras))
            c3.metric("Maior saldo", topo["funcionario"], topo["saldo"], delta_color="off")

        with st.container(key="rev_rh_tabela"):
            rotulo("03", "Saldo por funcionário")
            st.dataframe(
                r["total"][["funcionario", "saldo", "situacao"]],
                hide_index=True, column_config=CFG,
            )

        with st.container(key="rev_rh_relatorio"):
            rotulo("04", "Relatório · IA")
            st.markdown(r["relatorio"])

        with st.container(key="rev_rh_export"):
            rotulo("05", "Detalhes e exportação")
            with st.expander("Detalhe por dia"):
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
    with st.container(key="rev_fin_entrada"):
        rotulo("01", "Entrada de dados · vendas do sistema e extrato do banco")
        col1, col2 = st.columns(2)
        f_vendas = col1.file_uploader("Vendas do sistema", type=["csv", "xlsx"], key="upload_vendas")
        f_extrato = col2.file_uploader("Extrato do banco", type=["csv", "xlsx"], key="upload_extrato")
        taxa = st.number_input("Taxa do cartão (%)", value=2.0, step=0.1) / 100
        conciliar = bool(f_vendas and f_extrato) and st.button(
            "Conciliar", type="primary", key="btn_fin"
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
        with st.spinner("Processando relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_fin"] = {
            "conc": conc[colunas], "divergentes": divergentes,
            "contas": contas, "relatorio": relatorio,
        }

    if "resultado_fin" in st.session_state:
        r = st.session_state["resultado_fin"]
        n = len(r["divergentes"])

        with st.container(key="rev_fin_resumo"):
            rotulo("02", "Resumo")
            c1, c2, c3 = st.columns(3)
            c1.metric("Vendas conciliadas", len(r["conc"]))
            c2.metric("Divergências", n)
            c3.metric("Contas pagas", brl(abs(r["contas"]["valor"].sum())))
            if n:
                plural = "S" if n > 1 else ""
                st.markdown(
                    f'<div class="aviso alerta">{n} DIVERGÊNCIA{plural} ENCONTRADA{plural}</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(r["divergentes"], hide_index=True, column_config=CFG)
            else:
                st.markdown(
                    '<div class="aviso ok">TUDO CONFERIDO · NENHUMA DIVERGÊNCIA</div>',
                    unsafe_allow_html=True,
                )

        with st.container(key="rev_fin_relatorio"):
            rotulo("03", "Relatório · IA")
            st.markdown(r["relatorio"])

        with st.container(key="rev_fin_export"):
            rotulo("04", "Detalhes e exportação")
            with st.expander("Conciliação completa"):
                st.dataframe(r["conc"], hide_index=True, column_config=CFG)
            with st.expander("Contas pagas no período"):
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
    '<div class="hero-grupo">'
    '<div class="topbar">'
    '<div class="marca">Painel operacional<br><em>de agentes</em></div>'
    '<span class="status"><i class="dot"></i>2 AGENTES ATIVOS</span>'
    '</div>'
    '<div class="sub">RH e financeiro em um só lugar. Envie as planilhas, '
    'receba o cálculo e o relatório.</div>'
    '</div>',
    unsafe_allow_html=True,
)

aba_rh, aba_fin = st.tabs(["RH", "Financeiro"])
with aba_rh:
    pagina_rh()
with aba_fin:
    pagina_financeiro()