"""Agente de Marketing: o que está em alta no nicho, criação de post ou carrossel e foto (própria ou com IA).

Sem a API do Metricool por enquanto: o dono baixa as imagens, copia a legenda e posta.
"""
import io
import json
import zipfile
from html import escape

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

MODELOS_TEXTO = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
MODELOS_IMAGEM = ["gemini-3-pro-image-preview", "gemini-2.5-flash-image"]
LARGURA, ALTURA = 1080, 1350  # formato 4:5 do feed do Instagram

REGRAS_TEXTO = """
Regras de escrita (do squad de marketing da HNOS, adaptadas para restaurante):
- Uma ideia por slide: título forte de até 6 palavras e texto de apoio de 12 a 30 palavras.
- Comece pela vontade ou pela situação do cliente (fome, almoço corrido, fim de semana), nunca por "O restaurante oferece".
- Seja concreto: prato, dia, horário, preço. Use só os fatos que o dono informou; nunca invente preço, prazo ou promoção.
- Fale como gente: "a gente", "você", frases curtas.
- Nunca use: "Descubra", "Confira", "Imperdível", "No mundo de hoje", "experiência única", "explosão de sabores".
- Sem emoji nos slides. Na legenda, no máximo 3 emojis.
- Termine com um pedido claro: chamar no WhatsApp, marcar um amigo, salvar o post ou vir hoje.
"""


# ---------- IA ----------
def _cliente():
    return genai.Client()


def _texto(prompt, config=None):
    cliente = _cliente()
    ultimo = None
    for modelo in MODELOS_TEXTO:
        try:
            return cliente.models.generate_content(model=modelo, contents=prompt, config=config)
        except Exception as erro:  # tenta o próximo modelo
            ultimo = erro
    raise RuntimeError(f"A IA não respondeu: {ultimo}")


def pesquisar_em_alta(nicho, cidade):
    prompt = (
        f"Você é o agente de marketing de um restaurante do nicho '{nicho}' em {cidade or 'Brasil'}. "
        "Pesquise no Google o que está em alta AGORA (últimos 30 dias) nesse nicho: pratos, tendências, datas "
        "comemorativas próximas, formatos de post que estão funcionando no Instagram e assuntos que o público comenta. "
        "Responda em português, em tópicos curtos, com no máximo 6 tendências. Para cada uma: o que é, por que está em alta "
        "e uma ideia de post que esse restaurante pode fazer. Não invente números; se não tiver certeza, diga."
    )
    cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
    resp = _texto(prompt, cfg)
    fontes = []
    try:
        for ch in resp.candidates[0].grounding_metadata.grounding_chunks or []:
            if ch.web and ch.web.uri:
                fontes.append((ch.web.title or ch.web.uri, ch.web.uri))
    except (AttributeError, IndexError, TypeError):
        pass
    return resp.text, fontes


def criar_post(nicho, assunto, fatos, formato, qtd):
    n = 1 if formato == "Post único" else qtd
    prompt = (
        f"Você é o agente de marketing de um restaurante do nicho '{nicho}'. Crie um "
        f"{'post de imagem única' if n == 1 else f'carrossel de {n} slides'} para o Instagram.\n"
        f"Assunto: {assunto}\nFatos informados pelo dono (use só estes): {fatos or 'nenhum'}\n"
        f"{REGRAS_TEXTO}\n"
        "Para cada slide, escreva também 'prompt_foto': o prompt ideal, em português, para uma IA gerar a foto "
        "desse slide. Descreva o prato ou a cena, o ângulo da câmera, a luz, o fundo e o clima. Peça foto realista, "
        "como tirada no próprio restaurante, sem nenhum texto, letra ou logo na imagem, e com espaço livre na parte "
        "de baixo para o texto do post.\n"
        f"Devolva exatamente {n} slide(s) neste JSON: "
        '{"legenda": "...", "hashtags": ["#..."], "slides": [{"titulo": "...", "texto": "...", "prompt_foto": "..."}]}'
    )
    cfg = types.GenerateContentConfig(response_mime_type="application/json")
    dados = json.loads(_texto(prompt, cfg).text)
    dados["slides"] = dados.get("slides", [])[:n]
    return dados


def gerar_foto(prompt):
    cliente = _cliente()
    ultimo = None
    for modelo in MODELOS_IMAGEM:
        for cfg in (
            {"response_modalities": ["IMAGE"], "image_config": {"aspect_ratio": "4:5"}},
            {"response_modalities": ["IMAGE", "TEXT"]},
        ):
            try:
                resp = cliente.models.generate_content(
                    model=modelo, contents=prompt, config=types.GenerateContentConfig(**cfg)
                )
                for parte in resp.candidates[0].content.parts:
                    if getattr(parte, "inline_data", None) and parte.inline_data.data:
                        return parte.inline_data.data
                ultimo = "a IA não devolveu imagem"
            except Exception as erro:
                ultimo = erro
    raise RuntimeError(f"Não consegui gerar a foto: {ultimo}")


# ---------- montagem da imagem final ----------
def _fonte(tamanho):
    for nome in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanho)


def _quebrar(draw, texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def montar_slide(foto_bytes, titulo, texto, numero=None, total=None):
    foto = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
    # corta no centro para 4:5
    escala = max(LARGURA / foto.width, ALTURA / foto.height)
    foto = foto.resize((round(foto.width * escala), round(foto.height * escala)))
    x, y = (foto.width - LARGURA) // 2, (foto.height - ALTURA) // 2
    img = foto.crop((x, y, x + LARGURA, y + ALTURA))

    # degradê escuro embaixo para o texto ficar legível
    sombra = Image.new("L", (1, ALTURA))
    for i in range(ALTURA):
        sombra.putpixel((0, i), max(0, min(235, int((i - ALTURA * 0.35) / (ALTURA * 0.5) * 235))))
    preto = Image.new("RGB", (LARGURA, ALTURA), (0, 0, 0))
    img = Image.composite(preto, img, sombra.resize((LARGURA, ALTURA)))

    draw = ImageDraw.Draw(img)
    margem, largura = 80, LARGURA - 160
    f_titulo, f_texto = _fonte(72), _fonte(40)
    l_titulo = _quebrar(draw, titulo.upper(), f_titulo, largura)
    l_texto = _quebrar(draw, texto, f_texto, largura)
    altura_bloco = len(l_titulo) * 84 + 24 + len(l_texto) * 54
    y = ALTURA - 90 - altura_bloco
    for linha in l_titulo:
        draw.text((margem, y), linha, font=f_titulo, fill=(255, 255, 255))
        y += 84
    y += 24
    for linha in l_texto:
        draw.text((margem, y), linha, font=f_texto, fill=(235, 235, 235))
        y += 54
    if numero and total and total > 1:
        draw.text((LARGURA - margem - 90, 60), f"{numero}/{total}", font=_fonte(36), fill=(255, 255, 255))

    saida = io.BytesIO()
    img.save(saida, format="JPEG", quality=92)
    return saida.getvalue()


def _zip(imagens):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for i, dados in enumerate(imagens, start=1):
            z.writestr(f"slide-{i:02d}.jpg", dados)
    return buffer.getvalue()


# ---------- tela ----------
def _post():
    return st.session_state.get("mkt_post")


def _mostrar_erro(erro):
    st.markdown(f'<div class="aviso alerta">{escape(str(erro))}</div>', unsafe_allow_html=True)


def secao_em_alta(titulo):
    with st.container(key="mkt_alta"):
        titulo("01 · O que está em alta no seu nicho", "O Gemini pesquisa no Google agora e sugere ideias de post.")
        c1, c2 = st.columns(2)
        st.session_state.setdefault("mkt_nicho", "hamburgueria")
        st.session_state.setdefault("mkt_cidade", "São Paulo")
        nicho = c1.text_input("Nicho do restaurante", key="mkt_nicho")
        cidade = c2.text_input("Cidade", key="mkt_cidade")
        if st.button("Ver o que está em alta", type="primary", key="btn_mkt_alta"):
            with st.spinner("Pesquisando as tendências..."):
                try:
                    st.session_state["mkt_tendencias"] = pesquisar_em_alta(nicho, cidade)
                except Exception as erro:
                    _mostrar_erro(erro)
        if "mkt_tendencias" in st.session_state:
            texto, fontes = st.session_state["mkt_tendencias"]
            st.markdown(texto)
            if fontes:
                with st.expander("Fontes da pesquisa"):
                    for nome, url in fontes[:8]:
                        st.markdown(f"- [{nome}]({url})")
    return nicho


def secao_criar(titulo, nicho):
    with st.container(key="mkt_criar"):
        titulo("02 · Criar o post", "Diga o assunto e os fatos (prato, dia, preço). O agente escreve o texto e o prompt da foto.")
        assunto = st.text_input("Assunto do post", placeholder="Ex.: smash duplo de sábado", key="mkt_assunto")
        fatos = st.text_area("Fatos que podem entrar no post", placeholder="Ex.: R$ 34,90, só sábado, das 18h às 23h, pedido pelo WhatsApp", key="mkt_fatos")
        c1, c2 = st.columns(2)
        formato = c1.radio("Formato", ["Post único", "Carrossel"], horizontal=True, key="mkt_formato")
        qtd = c2.slider("Slides do carrossel", 3, 7, 5, key="mkt_qtd", disabled=formato == "Post único")
        if st.button("Criar post", type="primary", key="btn_mkt_criar"):
            if not assunto.strip():
                st.warning("Escreva o assunto do post.")
            else:
                with st.spinner("Escrevendo o post..."):
                    try:
                        dados = criar_post(nicho, assunto, fatos, formato, qtd)
                        for s in dados["slides"]:
                            s.update({"foto": None, "foto_ia": None, "final": None})
                        # limpa os campos do post anterior
                        for k in [k for k in st.session_state if k.startswith(("mkt_tit_", "mkt_txt_", "mkt_pf_", "mkt_origem_", "mkt_up_"))]:
                            del st.session_state[k]
                        st.session_state["mkt_post"] = dados
                        st.session_state["mkt_atual"] = 0
                    except Exception as erro:
                        _mostrar_erro(erro)


def secao_slides(titulo):
    post = _post()
    if not post or not post["slides"]:
        return
    slides = post["slides"]
    total = len(slides)
    atual = min(st.session_state.get("mkt_atual", 0), total - 1)

    with st.container(key="mkt_slides"):
        titulo("03 · Foto de cada slide", "Adicione sua foto ou use a foto com IA. Aprove para montar o slide.")
        # sequência do carrossel
        cols = st.columns(total)
        for i, (col, s) in enumerate(zip(cols, slides)):
            marca = "✓ " if s["final"] else ""
            if col.button(f"{marca}{i + 1}", key=f"mkt_ir_{i}", width="stretch",
                          type="primary" if i == atual else "secondary"):
                st.session_state["mkt_atual"] = i
                st.rerun()

        s = slides[atual]
        for campo, chave in (("titulo", "mkt_tit"), ("texto", "mkt_txt"), ("prompt_foto", "mkt_pf")):
            st.session_state.setdefault(f"{chave}_{atual}", s.get(campo, ""))
        st.markdown(f"**Slide {atual + 1} de {total}**")
        s["titulo"] = st.text_input("Título do slide", key=f"mkt_tit_{atual}")
        s["texto"] = st.text_area("Texto do slide", key=f"mkt_txt_{atual}")

        origem = st.radio("Foto", ["Adicionar sua foto", "Foto com IA"], horizontal=True, key=f"mkt_origem_{atual}")
        if origem == "Adicionar sua foto":
            arq = st.file_uploader("Sua foto (.jpg ou .png)", type=["jpg", "jpeg", "png"], key=f"mkt_up_{atual}")
            if arq:
                s["foto"] = arq.getvalue()
                if st.button("Usar esta foto", type="primary", key=f"mkt_usar_{atual}"):
                    s["final"] = montar_slide(s["foto"], s["titulo"], s["texto"], atual + 1, total)
                    st.rerun()
        else:
            if st.button("Gerar o prompt ideal", key=f"mkt_prompt_{atual}"):
                with st.spinner("Montando o prompt da foto..."):
                    try:
                        r = _texto(
                            "Escreva só o prompt, em português, para uma IA gerar uma foto realista de restaurante "
                            f"para este slide do Instagram. Título: {s['titulo']}. Texto: {s['texto']}. "
                            "Descreva prato ou cena, ângulo, luz, fundo e clima. Sem texto, letra ou logo na imagem, "
                            "com espaço livre embaixo para o texto do post."
                        )
                        s["prompt_foto"] = r.text.strip()
                        st.session_state[f"mkt_pf_{atual}"] = s["prompt_foto"]
                    except Exception as erro:
                        _mostrar_erro(erro)
            st.markdown("**Foto com IA**")
            s["prompt_foto"] = st.text_area("Prompt da foto (pode ajustar)", key=f"mkt_pf_{atual}", height=130)
            st.caption("Cada foto gerada usa alguns centavos de crédito do Gemini.")
            rotulo_gerar = "Gerar novamente" if s.get("foto_ia") else "Gerar foto"
            if st.button(rotulo_gerar, key=f"mkt_gerar_{atual}"):
                with st.spinner("Gerando a foto..."):
                    try:
                        s["foto_ia"] = gerar_foto(s["prompt_foto"])
                        s["final"] = None
                    except Exception as erro:
                        _mostrar_erro(erro)
            if s.get("foto_ia"):
                st.image(s["foto_ia"], caption="Foto gerada", width=360)
                if st.button("Aprovar esta foto", type="primary", key=f"mkt_aprovar_{atual}"):
                    s["final"] = montar_slide(s["foto_ia"], s["titulo"], s["texto"], atual + 1, total)
                    if atual + 1 < total:
                        st.session_state["mkt_atual"] = atual + 1
                    st.rerun()

        if s["final"]:
            st.image(s["final"], caption=f"Slide {atual + 1} pronto", width=360)


def secao_final(titulo):
    post = _post()
    if not post or not post["slides"]:
        return
    prontos = [s["final"] for s in post["slides"] if s["final"]]
    total = len(post["slides"])
    with st.container(key="mkt_final"):
        titulo("04 · Post pronto", f"{len(prontos)} de {total} slide(s) aprovado(s).")
        if prontos:
            cols = st.columns(min(len(prontos), 4))
            for i, img in enumerate(prontos):
                cols[i % len(cols)].image(img, caption=f"{i + 1}", width="stretch")
        legenda = post.get("legenda", "") + "\n\n" + " ".join(post.get("hashtags", []))
        st.markdown("**Legenda para copiar**")
        st.code(legenda.strip(), language=None)
        if len(prontos) == total:
            st.download_button("Baixar as imagens do post", _zip(prontos), file_name="post-instagram.zip",
                               type="primary", key="mkt_baixar")
            st.caption("Por enquanto você posta no Instagram. O agendamento automático entra com o Metricool.")


def pagina_marketing(titulo):
    nicho = secao_em_alta(titulo)
    secao_criar(titulo, nicho)
    secao_slides(titulo)
    secao_final(titulo)


def resumo_para_ia():
    partes = []
    if "mkt_tendencias" in st.session_state:
        partes.append("Tendências pesquisadas:\n" + st.session_state["mkt_tendencias"][0][:2500])
    post = _post()
    if post:
        partes.append("Post em criação:\n" + "\n".join(f"- {s['titulo']}: {s['texto']}" for s in post["slides"]))
        partes.append("Legenda: " + post.get("legenda", ""))
    return "\n\n".join(partes)
