import ast
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="hnos | Gestão de restaurante",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="auto",
)

# Reaproveita os cálculos, as integrações e os formulários do sistema
# original sem executar a montagem das telas antigas.
arquivo_original = Path(__file__).with_name("sistema_original.py")
if not arquivo_original.is_file():
    st.error("Salve o código original como sistema_original.py, ao lado deste app.py.")
    st.stop()

funcoes = {
    "agora", "card", "titulo", "comanda", "minutos", "formatar", "brl",
    "ler_arquivo", "padronizar_data", "para_excel", "perguntar_ia",
    "perguntar_ia_stream", "carregar_usuarios", "conferir_login",
    "contexto_geral", "montar_prompt", "chat_ia", "ler_aba", "ler_horario",
    "preparar_ponto", "escala_do_cadastro", "calcular_saldos", "texto_periodo",
    "pagina_rh", "pagina_financeiro", "modelo_compras", "escolher_fornecedor",
    "calcular_compras", "montar_mensagem", "pagina_compras", "iniciais",
    "equipe_cadastro", "escalados_hoje", "cumprimento",
}
constantes = {"AGENTES", "CFG", "MODELOS_IA", "SUGESTOES", "AVATAR"}

codigo_original = ast.parse(
    arquivo_original.read_text(encoding="utf-8-sig"), filename=str(arquivo_original)
)
componentes = []
for item in codigo_original.body:
    if isinstance(item, (ast.Import, ast.ImportFrom)):
        componentes.append(item)
    elif isinstance(item, ast.FunctionDef) and item.name in funcoes:
        componentes.append(item)
    elif isinstance(item, ast.Assign) and any(
        isinstance(alvo, ast.Name) and alvo.id in constantes
        for alvo in item.targets
    ):
        componentes.append(item)

sistema = {"__file__": str(arquivo_original), "__name__": "sistema_original"}
exec(
    compile(ast.Module(body=componentes, type_ignores=[]), str(arquivo_original), "exec"),
    sistema,
)

st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

.stApp {
  --texto: #211934;
  --suave: #625a73;
  --borda: #e6e0ef;
  --fundo: #f7f6fb;
  --roxo: #5736bf;
  color: var(--texto);
  background: var(--fundo);
}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .marca, .topo, .status {
  font-family: Manrope, system-ui, sans-serif;
}
.stApp h1, .stApp h2, .stApp h3 { color: var(--texto); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] {
  max-width: 1390px;
  padding: 3.2rem clamp(1rem, 4vw, 3.1rem);
}
[data-testid="stSidebar"] {
  background: #fff;
  border-right: 1px solid var(--borda);
}
[data-testid="stSidebar"] button {
  justify-content: flex-start;
  border-radius: 10px;
  min-height: 44px;
}
[data-testid="stSidebar"] button[kind="primary"] {
  background: #eee8ff;
  color: #452597;
  border-color: #eee8ff;
}
.marca {
  font-weight: 800;
  font-size: 2.35rem;
  letter-spacing: -.09em;
  line-height: 1;
  margin: .35rem 0 1.5rem;
}
.marca span { color: var(--roxo); }
.marca small {
  display: block;
  margin-top: .65rem;
  color: var(--suave);
  font-size: .68rem;
  font-weight: 800;
  letter-spacing: .12em;
}
.topo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
  color: var(--suave);
  font-size: .9rem;
}
.data, .status {
  background: #f3effb;
  border: 1px solid var(--borda);
  color: #514064;
  border-radius: 999px;
  padding: .35rem .7rem;
  font-size: .78rem;
  font-weight: 800;
}
.hero {
  border-radius: 20px;
  padding: clamp(1.6rem, 5vw, 3.5rem);
  min-height: 240px;
  color: #fff;
  background:
    linear-gradient(95deg, #21163f 3%, #281b4ce8 48%, #281b4c68 100%),
    #21163f url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1250&q=82') center 52% / cover;
}
.hero h1 {
  color: #fff;
  font-size: clamp(2rem, 4.5vw, 3.5rem);
  letter-spacing: -.065em;
  line-height: 1.1;
  margin: 0;
  padding: 0;
  font-weight: 800;
}
.hero p {
  margin: .8rem 0 0;
  max-width: 32rem;
  color: #f5efff;
  font-size: 1rem;
  line-height: 1.6;
}
[class*="st-key-vc_"], [class*="st-key-area_"], .st-key-acesso {
  min-width: 0;
  padding: 1.2rem;
  border-radius: 16px;
  border: 1px solid var(--borda);
  background: #fff;
  box-shadow: 0 8px 20px #29164b08;
}
[class*="st-key-area_"] { height: 100%; }
.st-key-acesso {
  max-width: 550px;
  margin: 5vh auto 0;
  padding: clamp(1.3rem, 5vw, 3rem);
}
.area-topo {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: .55rem;
  margin-bottom: .8rem;
}
.icone-area {
  display: grid;
  place-items: center;
  width: 43px;
  height: 43px;
  border-radius: 12px;
  background: #eee8ff;
  color: #4b2ea2;
}
.financeiro .icone-area { background: #e0f4eb; color: #155d4a; }
.compras .icone-area { background: #ffedd8; color: #884804; }
.icone-area span { font: 500 23px/1 "Material Symbols Rounded"; }
.area h3 { font-size: 1.12rem; margin: 0; padding: 0; font-weight: 800; }
.area p, .titulo-secao small, .ticket-topo span { color: var(--suave); }
.area p { font-size: .9rem; margin: .35rem 0 0; }
.valor { font-size: 1.35rem; font-weight: 800; margin-top: .9rem; }
.titulo-secao { font-size: 1.15rem; font-weight: 800; }
.titulo-secao small { display: block; font-size: .86rem; font-weight: 500; margin-top: .3rem; }
.ticket-topo {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: .5rem;
  padding-bottom: .65rem;
  border-bottom: 1px solid var(--borda);
}
.aviso { padding: .8rem 1rem; border-radius: 10px; }
.aviso.alerta { background: #fff0dd; color: #703805; }
.aviso.ok { background: #dff4e9; color: #145742; }
.vazio {
  padding: 1.15rem;
  border: 1px dashed #d8cbea;
  border-radius: 12px;
  background: #faf8ff;
  color: var(--suave);
  text-align: center;
}
[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed #d4c4f0;
  border-radius: 12px;
  background: #faf7ff;
}
[data-testid="stMetric"] {
  background: #f6f2fc;
  border-radius: 12px;
  padding: .8rem;
}
.stApp :is(button, a, input, textarea):focus-visible {
  outline: 2px solid var(--roxo);
  outline-offset: 3px;
}
@media (max-width: 700px) {
  [data-testid="stHorizontalBlock"]:has([class*="st-key-area_"]),
  [data-testid="stHorizontalBlock"]:has(.st-key-vc_escala_hoje) {
    flex-wrap: wrap;
  }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-area_"]) > [data-testid="stColumn"],
  [data-testid="stHorizontalBlock"]:has(.st-key-vc_escala_hoje) > [data-testid="stColumn"] {
    flex: 1 1 100%;
    width: 100%;
    min-width: 0;
  }
}

/* Paleta dos botões */
.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"],
  [data-testid="stLinkButton"],
  [data-testid="stPopover"]
) :is(button, a) {
  --botao-fundo: #f0ebff;
  --botao-texto: #442589;
  --botao-borda: #ded2fa;
  --botao-hover: #e6dcff;

  background: var(--botao-fundo);
  color: var(--botao-texto);
  border: 1px solid var(--botao-borda);
  border-radius: 10px;
  min-height: 42px;
  font-weight: 700;
}

/* Faz o texto e o ícone acompanharem a cor do botão */
.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"],
  [data-testid="stLinkButton"],
  [data-testid="stPopover"]
) :is(button, a) :is(p, span, svg) {
  color: inherit;
}

.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"],
  [data-testid="stLinkButton"],
  [data-testid="stPopover"]
) :is(button, a):hover:not(:disabled) {
  background: var(--botao-hover);
  color: var(--botao-texto);
  border-color: var(--botao-borda);
}

/* Ações principais, como Entrar e Calcular horas */
.stApp :is(
  [data-testid="stButton"],
  [data-testid="stFormSubmitButton"]
) button[kind="primary"] {
  --botao-fundo: #5736bf;
  --botao-texto: #ffffff;
  --botao-borda: #5736bf;
  --botao-hover: #452597;
}

/* Botões dos cartões */
.stApp .st-key-area_financeiro [data-testid="stButton"] button {
  --botao-fundo: #e4f5ed;
  --botao-texto: #145b44;
  --botao-borda: #c4e6d7;
  --botao-hover: #d3eee1;
}

.stApp .st-key-area_compras [data-testid="stButton"] button {
  --botao-fundo: #fff0dc;
  --botao-texto: #783d06;
  --botao-borda: #f0d7b5;
  --botao-hover: #fae4c6;
}

/* Navegação lateral */
.stApp [data-testid="stSidebar"] [data-testid="stButton"] button {
  --botao-fundo: #ffffff;
  --botao-texto: #40374f;
  --botao-borda: #e9e3f0;
  --botao-hover: #f6f2fc;
}

.stApp [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
  --botao-fundo: #eee8ff;
  --botao-texto: #452597;
  --botao-borda: #ddd0fa;
  --botao-hover: #e6dcff;
}

.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"]
) button:disabled {
  --botao-fundo: #f2eff6;
  --botao-texto: #6d647c;
  --botao-borda: #e5dfed;
  opacity: 1;
  cursor: not-allowed;
}

/* Superfícies e texto */
.stApp {
  --texto: #f2eff8;
  --suave: #bdb5cc;
  --borda: #393148;
  --fundo: #111018;
  --roxo: #b79bff;
  --painel: #1c1928;
  --menu: #16131f;
  color: var(--texto);
  background: var(--fundo);
}

.stApp [data-testid="stAppViewContainer"] {
  background: var(--fundo);
}

.stApp [data-testid="stSidebar"] {
  background: var(--menu);
  border-color: var(--borda);
}

.stApp :is(
  [class*="st-key-vc_"],
  [class*="st-key-area_"],
  .st-key-acesso
) {
  background: var(--painel);
  border-color: var(--borda);
  box-shadow: 0 8px 24px #0003;
}

.stApp :is(.marca, .valor, .titulo-secao, .ticket-topo strong) {
  color: var(--texto);
}

.stApp :is(.data, .status) {
  background: #2b233d;
  color: #e0d2ff;
  border-color: #4b3c65;
}

.stApp :is(.vazio, [data-testid="stFileUploaderDropzone"]) {
  background: #181522;
  border-color: #55466d;
  color: var(--suave);
}

.stApp [data-testid="stMetric"] {
  background: #252033;
}

.stApp .aviso.alerta {
  background: #3a2919;
  color: #ffd8a3;
}

.stApp .aviso.ok {
  background: #15352d;
  color: #b1efda;
}

/* Cartões da mesma altura e botões alinhados */
.stApp [data-testid="stHorizontalBlock"]:has(
  > [data-testid="stColumn"] [class*="st-key-area_"]
) {
  align-items: stretch;
}

.stApp [data-testid="stColumn"]:has([class*="st-key-area_"]),
.stApp [data-testid="stColumn"] :has([class*="st-key-area_"]),
.stApp [class*="st-key-area_"] {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
}

.stApp [class*="st-key-area_"] {
  box-sizing: border-box;
  min-height: 282px;
}

.stApp [class*="st-key-area_"] > :last-child {
  margin-top: auto;
}

/* Botões no tema escuro */
.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"],
  [data-testid="stLinkButton"],
  [data-testid="stPopover"]
) :is(button, a) {
  --botao-fundo: #302449;
  --botao-texto: #eadfff;
  --botao-borda: #51406e;
  --botao-hover: #40305e;
}

.stApp :is(
  [data-testid="stButton"],
  [data-testid="stFormSubmitButton"]
) button[kind^="primary"] {
  --botao-fundo: #b79bff;
  --botao-texto: #1e1039;
  --botao-borda: #b79bff;
  --botao-hover: #c9b4ff;
}

.stApp .st-key-area_financeiro [data-testid="stButton"] button {
  --botao-fundo: #19372f;
  --botao-texto: #b8f1db;
  --botao-borda: #315b4d;
  --botao-hover: #234b3e;
}

.stApp .st-key-area_compras [data-testid="stButton"] button {
  --botao-fundo: #3b2b1c;
  --botao-texto: #ffdbad;
  --botao-borda: #654b31;
  --botao-hover: #523b26;
}

.stApp .icone-area { background: #352651; color: #dbc7ff; }
.stApp .financeiro .icone-area { background: #19372f; color: #b8f1db; }
.stApp .compras .icone-area { background: #3b2b1c; color: #ffdbad; }

.stApp [data-testid="stSidebar"] [data-testid="stButton"] button {
  --botao-fundo: #211c2d;
  --botao-texto: #e9e2f3;
  --botao-borda: #393148;
  --botao-hover: #2e253d;
}

.stApp [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
  --botao-fundo: #392953;
  --botao-texto: #eddfff;
  --botao-borda: #654e8a;
  --botao-hover: #48346a;
}

.stApp :is(
  [data-testid="stButton"],
  [data-testid="stDownloadButton"],
  [data-testid="stFormSubmitButton"]
) button:disabled {
  --botao-fundo: #282431;
  --botao-texto: #a69db4;
  --botao-borda: #393148;
}

@media (max-width: 700px) {
  .stApp [data-testid="stHorizontalBlock"]:has(
    > [data-testid="stColumn"] [class*="st-key-area_"]
  ) > [data-testid="stColumn"] {
    flex: 1 1 100%;
    width: 100%;
  }
}
</style>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded" rel="stylesheet">
""")

PAGINAS = {
    "painel": ("Visão geral", "space_dashboard"),
    "rh": ("RH", "groups"),
    "financeiro": ("Financeiro", "account_balance_wallet"),
    "compras": ("Compras", "shopping_bag"),
    "assistente": ("Assistente IA", "auto_awesome"),
}
DESCRICOES = {
    "rh": "Confira a escala e calcule horas extras e compensações.",
    "financeiro": "Concilie vendas, repasses e contas pagas.",
    "compras": "Compare cotações e organize pedidos por fornecedor.",
}
RESULTADOS = {
    "rh": "resultado_rh",
    "financeiro": "resultado_fin",
    "compras": "resultado_cmp",
}
MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
    "agosto", "setembro", "outubro", "novembro", "dezembro",
)
MARCA = '<div class="marca">hnos<span>.</span><small>GESTÃO DE RESTAURANTE</small></div>'


def abrir(pagina):
    st.session_state["pagina"] = pagina


def autenticar(usuario, senha):
    import hmac

    usuarios = sistema["carregar_usuarios"]()
    if not usuarios:
        usuarios = {"demo": {"senha": "demo", "nome": "Ronaldo"}}
    cadastro = usuarios.get(usuario.strip().lower())
    if cadastro and hmac.compare_digest(
        str(cadastro.get("senha", "")).encode("utf-8"), senha.encode("utf-8")
    ):
        st.session_state["usuario"] = cadastro.get("nome") or usuario
        abrir("painel")
        st.rerun()
    st.error("Usuário ou senha incorretos.")


def login():
    with st.container(key="acesso"):
        st.html(MARCA)
        st.title("Entre na sua operação")
        st.write("Acesse o painel de gestão do seu restaurante.")
        with st.form("acesso_hnos", border=False):
            usuario = st.text_input("Usuário", placeholder="Seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if enviar:
            autenticar(usuario, senha)
        if not sistema["carregar_usuarios"]():
            if st.button("Explorar demonstração", width="stretch"):
                autenticar("demo", "demo")


def menu(nome, atual):
    with st.sidebar:
        st.html(MARCA)
        for chave, (rotulo, icone) in PAGINAS.items():
            st.button(
                rotulo,
                key=f"menu_{chave}",
                icon=f":material/{icone}:",
                width="stretch",
                type="primary" if chave == atual else "secondary",
                on_click=abrir,
                args=(chave,),
            )
        st.divider()
        st.text(nome)
        if st.button("Sair", icon=":material/logout:", width="stretch"):
            st.session_state.clear()
            st.rerun()


def resumo(chave):
    resultado = st.session_state.get(RESULTADOS[chave])
    if resultado is None:
        return "Sem importação", "Aguardando dados"
    if chave == "rh":
        return "Ponto analisado", f'{len(resultado["total"])} pessoas na análise'
    if chave == "financeiro":
        total = len(resultado["divergentes"])
        return "Conciliação concluída", f"{total} divergência{'s' if total != 1 else ''}"
    pedidos = resultado["pedidos"]
    quantidade = len(pedidos)
    sem_cotacao = len(resultado.get("sem_cotacao", []))
    if sem_cotacao:
        return "Cotações pendentes", f"{sem_cotacao} itens sem cotação"
    return "Estoque analisado", f"{quantidade} itens a comprar"


def painel(nome):
    saudacao = escape(sistema["cumprimento"]())
    st.html(
        f'<section class="hero"><h1>{saudacao}, {escape(nome)}.</h1>'
        '<p>Acompanhe a equipe, confira recebimentos e organize as próximas compras.</p>'
        '</section>'
    )

    st.subheader("Áreas de trabalho")
    for coluna, chave in zip(st.columns(3), DESCRICOES):
        rotulo, icone = PAGINAS[chave]
        status, valor = resumo(chave)
        with coluna, st.container(key=f"area_{chave}"):
            st.html(
                f'<div class="area {chave}"><div class="area-topo">'
                f'<div class="icone-area" aria-hidden="true"><span>{icone}</span></div>'
                f'<span class="status">{escape(status)}</span></div>'
                f'<h3>{escape(rotulo)}</h3><p>{escape(DESCRICOES[chave])}</p>'
                f'<div class="valor">{escape(valor)}</div></div>'
            )
            st.button(
                f"Abrir {rotulo}", key=f"abrir_{chave}", width="stretch",
                on_click=abrir, args=(chave,),
            )

    esquerda, direita = st.columns([1, 1.45])
    with esquerda, st.container(key="vc_escala_hoje"):
        st.subheader("Escala de hoje")
        equipe = sistema["equipe_cadastro"]()
        turnos = sistema["escalados_hoje"](equipe)
        if turnos:
            for pessoa, entrada, saida in turnos:
                st.text(f"{pessoa} · {entrada}–{saida}")
        else:
            st.html('<div class="vazio">Nenhum turno disponível para hoje.</div>')
        st.button("Ver equipe", on_click=abrir, args=("rh",), width="stretch")
    with direita, st.container(key="vc_banco_horas"):
        st.subheader("Banco de horas")
        resultado = st.session_state.get("resultado_rh")
        if resultado is not None and not resultado["total"].empty:
            tabela = resultado["total"][["funcionario", "saldo_min"]].copy()
            tabela["Horas"] = tabela.pop("saldo_min").div(60)
            tabela.rename(columns={"funcionario": "Funcionário"}, inplace=True)
            st.bar_chart(tabela, x="Funcionário", y="Horas", color="#704bdd")
        else:
            st.html('<div class="vazio">Importe o ponto para visualizar os saldos.</div>')
            st.button("Importar ponto", on_click=abrir, args=("rh",), width="stretch")


def modulo(nome, pagina):
    rotulo, icone = PAGINAS[pagina]
    st.title(rotulo)
    st.write(DESCRICOES[pagina])
    with st.popover("Como funciona", icon=":material/help:"):
        st.markdown(sistema["AGENTES"][pagina]["contexto"])

    operacao, assistente = st.tabs(["Operação", "Assistente do módulo"])
    with operacao:
        try:
            sistema[f"pagina_{pagina}"]()
        except (KeyError, ValueError, TypeError, OSError) as erro:
            st.error(f"Confira o formato da planilha enviada. Detalhe: {erro}")
    with assistente:
        sistema["chat_ia"](nome, pagina)


def main():
    nome = st.session_state.get("usuario")
    if not nome:
        login()
        return

    pagina = st.session_state.get("pagina", "painel")
    menu(nome, pagina)
    hoje: datetime = sistema["agora"]()
    data = f"{hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}"
    st.html(
        f'<div class="topo"><div>Operação / <strong>{PAGINAS[pagina][0]}</strong></div>'
        f'<span class="data">{data}</span></div>'
    )
    if pagina == "painel":
        painel(nome)
    elif pagina == "assistente":
        st.title("Assistente da operação")
        sistema["chat_ia"](nome)
    else:
        modulo(nome, pagina)


main()