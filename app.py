import io
import time
import pandas as pd
import streamlit as st
from google import genai

st.set_page_config(page_title="Agentes do Restaurante", page_icon="🍽️", layout="wide")


# ---------- funções comuns ----------
def minutos(hora):
    h, m = str(hora).split(":")[:2]
    return int(h) * 60 + int(m)


def formatar(min_total):
    sinal = "+" if min_total >= 0 else "-"
    h, m = divmod(abs(int(min_total)), 60)
    return f"{sinal}{h}h{m:02d}"


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
    st.header("👥 RH: horas extras e compensação")
    st.caption("Envie a planilha com as abas 'escala' e 'ponto'.")
    arq = st.file_uploader("Planilha do RH (.xlsx)", type=["xlsx"], key="upload_rh")

    if arq and st.button("Calcular horas", type="primary", key="btn_rh"):
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
        with st.spinner("A IA está escrevendo o relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_rh"] = {
            "dados": dados, "total": total, "relatorio": relatorio,
        }

    if "resultado_rh" in st.session_state:
        r = st.session_state["resultado_rh"]
        st.subheader("Saldo por funcionário")
        st.dataframe(r["total"][["funcionario", "saldo", "situacao"]])
        st.subheader("Relatório da IA")
        st.write(r["relatorio"])
        with st.expander("Ver detalhe por dia"):
            st.dataframe(r["dados"][["funcionario", "data", "entrada", "saida", "saldo"]])
        st.download_button(
            "⬇️ Baixar relatório em Excel",
            para_excel({
                "por_dia": r["dados"][["funcionario", "data", "entrada", "saida", "saldo"]],
                "total": r["total"][["funcionario", "saldo", "situacao"]],
            }),
            file_name="relatorio_rh.xlsx",
        )


# ---------- página do Financeiro ----------
def pagina_financeiro():
    st.header("💰 Financeiro: conciliação")
    col1, col2 = st.columns(2)
    f_vendas = col1.file_uploader("Vendas do sistema", type=["csv", "xlsx"], key="upload_vendas")
    f_extrato = col2.file_uploader("Extrato do banco", type=["csv", "xlsx"], key="upload_extrato")
    taxa = st.number_input("Taxa do cartão (%)", value=2.0, step=0.1) / 100

    if f_vendas and f_extrato and st.button("Conciliar", type="primary", key="btn_fin"):
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
        with st.spinner("A IA está escrevendo o relatório..."):
            relatorio = perguntar_ia(pedido)

        st.session_state["resultado_fin"] = {
            "conc": conc[colunas], "divergentes": divergentes,
            "contas": contas, "relatorio": relatorio,
        }

    if "resultado_fin" in st.session_state:
        r = st.session_state["resultado_fin"]
        if len(r["divergentes"]):
            st.error(f"{len(r['divergentes'])} divergência(s) encontrada(s)")
            st.dataframe(r["divergentes"])
        else:
            st.success("Tudo conferido: nenhuma divergência!")
        st.subheader("Relatório da IA")
        st.write(r["relatorio"])
        with st.expander("Ver conciliação completa"):
            st.dataframe(r["conc"])
        with st.expander("Contas pagas no período"):
            st.dataframe(r["contas"])
        st.download_button(
            "⬇️ Baixar relatório em Excel",
            para_excel({
                "conciliacao": r["conc"],
                "divergencias": r["divergentes"],
                "contas_pagas": r["contas"],
            }),
            file_name="relatorio_financeiro.xlsx",
        )


# ---------- montagem do site ----------
st.title("🍽️ Agentes do Restaurante")
aba_rh, aba_fin = st.tabs(["👥 RH", "💰 Financeiro"])
with aba_rh:
    pagina_rh()
with aba_fin:
    pagina_financeiro()