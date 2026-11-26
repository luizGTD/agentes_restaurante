import hmac
import io
import math
import re
import time
from datetime import datetime
from html import escape
from urllib.parse import quote

import pandas as pd
import streamlit as st
from google import genai

st.set_page_config(page_title="hnos system A", page_icon="🤖", layout="wide")

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
          "sexta-feira", "sábado", "domingo"]
PALETA = ["#7aa7ff", "#5fe3b0", "#ffc46b", "#ff8cc6", "#b69cff", "#6fd6ff"]


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
        "nome": "RH", "cor": "#8fa8ff", "ativo": True,
        "serve": "calcular o saldo de horas da sua equipe e dizer quem fez hora extra e quem precisa compensar",
        "contexto": (
            "**O que eu faço:** comparo a escala com o ponto de cada funcionário e calculo o saldo de horas.\n\n"
            "**O que eu preciso:** o relatório de ponto (.xlsx) ou uma planilha com as abas *escala* e *ponto*.\n\n"
            "**O que você recebe:** o saldo de cada pessoa, um relatório pronto para ler e um arquivo Excel para guardar."
        ),
    },
    "financeiro": {
        "nome": "Financeiro", "cor": "#5fe3b0", "ativo": True,
        "serve": "conferir se o que você vendeu no cartão e no PIX caiu certo no banco",
        "contexto": (
            "**O que eu faço:** cruzo as vendas do sistema com o extrato do banco, desconto a taxa do cartão "
            "e aponto cada pagamento que não bateu.\n\n"
            "**O que eu preciso:** as vendas do sistema e o extrato do banco, em .csv ou .xlsx.\n\n"
            "**O que você recebe:** as divergências com o valor, as contas pagas no período e um relatório pronto."
        ),
    },
    "compras": {
        "nome": "Compras", "cor": "#ffc46b", "ativo": True,
        "serve": "montar a lista de compras a partir do estoque e das cotações dos fornecedores",
        "contexto": (
            "**O que eu faço:** analiso o estoque, comparo cotações e monto pedidos por fornecedor.\n\n"
            "**O que eu preciso:** uma planilha .xlsx com as abas estoque, cotacoes e fornecedores.\n\n"
            "**O que você recebe:** lista de compras, custos, economia, relatório e mensagens para revisar e "
            "enviar pelo WhatsApp."
        ),
    },
    "marketing": {
        "nome": "Marketing", "cor": "#ff8cc6", "ativo": False,
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


# ---------- estilo (vidro fosco) ----------
BOTOES = ",".join(f'[data-testid="{t}"]' for t in (
    "stBaseButton-secondary", "stBaseButton-primary",
    "stBaseButton-secondaryFormSubmit", "stBaseButton-primaryFormSubmit",
    "stBaseLinkButton-secondary", "stBaseLinkButton-primary",
))
PRIMARIOS = ",".join(f'[data-testid="{t}"]' for t in (
    "stBaseButton-primary", "stBaseButton-primaryFormSubmit", "stBaseLinkButton-primary",
))

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#101216; --texto:#f2f4f8; --mudo:rgba(242,244,248,.62); --fraco:rgba(242,244,248,.38);
  --borda:rgba(255,255,255,.1); --borda-forte:rgba(255,255,255,.24);
  --azul:#3b9dff; --verde:#4fe0a8; --ambar:#ffc46b; --vermelho:#ff7b7b;
  --mola:cubic-bezier(.34,1.3,.5,1); --suave:cubic-bezier(.22,1,.36,1);
}
.stApp{
  font-family:'Plus Jakarta Sans',system-ui,sans-serif; color:var(--texto);
  background:
    radial-gradient(60vmax 40vmax at 85% -10%,rgba(59,157,255,.16),transparent 60%),
    radial-gradient(50vmax 40vmax at -5% 105%,rgba(79,224,168,.09),transparent 60%),
    var(--bg);
  background-attachment:fixed;
}
.stApp p,.stApp label,.stApp li,.stApp h1,.stApp h2,.stApp h3,.stApp button,.stApp input,.stApp textarea,
.stApp a,[data-testid="stMarkdownContainer"],[data-testid="stMetricValue"],[data-testid="stMetricLabel"]{
  font-family:'Plus Jakarta Sans',system-ui,sans-serif;
}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{letter-spacing:-.03em;font-weight:700;color:var(--texto)}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:10px}
/* não deixa a tela piscar enquanto o Streamlit recarrega */
[data-stale="true"]{opacity:1!important;transition:none!important}

[data-testid="stMainBlockContainer"],.block-container{
  width:min(1180px,100%)!important; max-width:none!important; margin:0 auto!important;
  padding:22px 24px 56px!important; background:none; border:none; box-shadow:none;
}
[data-testid="stVerticalBlock"]{gap:1rem}

/* cartões */
[class*="st-key-vc_"]{
  position:relative; border-radius:26px; padding:22px;
  background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.04));
  border:1px solid var(--borda);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.1),0 18px 40px rgba(0,0,0,.22);
  backdrop-filter:blur(18px) saturate(130%); -webkit-backdrop-filter:blur(18px) saturate(130%);
  animation:entra .5s var(--suave) both;
}
@keyframes entra{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

.titulo-secao{font-size:19px;font-weight:700;letter-spacing:-.025em;margin:2px 0 10px}
.titulo-secao small{display:block;color:var(--mudo);font-size:13px;font-weight:400;letter-spacing:0;margin-top:4px}
.rot{font-size:15px;font-weight:600}
.rot small{display:block;color:var(--mudo);font-size:12.5px;font-weight:400;margin-top:2px}
.aviso{padding:13px 16px;border-radius:16px;margin:10px 0;font-size:14px;line-height:1.5;
  border:1px solid var(--borda);background:rgba(255,255,255,.06)}
.aviso.ok{background:rgba(79,224,168,.12);border-color:rgba(79,224,168,.35);color:#b9f6dd}
.aviso.alerta{background:rgba(255,123,123,.12);border-color:rgba(255,123,123,.38);color:#ffd2d2}

/* topo */
.st-key-topo{margin-bottom:12px}
.st-key-topo [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;align-items:center}
.st-key-topo [data-testid="stColumn"]{min-width:0!important}
.marca-topo{display:flex;align-items:center;gap:12px}
.logo-chip{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;flex:none;
  background:linear-gradient(145deg,rgba(59,157,255,.35),rgba(59,157,255,.08));border:1px solid rgba(59,157,255,.45)}
.marca-topo .nome{font-weight:800;font-size:18px;letter-spacing:-.04em;line-height:1.1}
.marca-topo .nome span{color:var(--azul)}
.marca-topo .com{font-size:12px;color:var(--mudo);margin-top:2px}
.chip-usuario{display:flex;justify-content:flex-end}
.chip-usuario div{display:flex;align-items:center;gap:10px;padding:5px 16px 5px 5px;border-radius:999px;
  background:rgba(255,255,255,.07);border:1px solid var(--borda);font-size:13px;font-weight:600;white-space:nowrap}
.chip-usuario i{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-style:normal;
  background:var(--azul);color:#fff;font-weight:700;font-size:12px}
.st-key-btn_sair{display:flex;justify-content:flex-end}
.st-key-btn_sair button{width:44px;height:44px;min-height:44px!important;padding:0!important;border-radius:50%!important}
.st-key-btn_sair button p{display:none}

/* botões */
:is(@BTN@){
  border-radius:999px!important; min-height:44px; padding:.5rem 1.3rem;
  background:rgba(255,255,255,.08)!important; border:1px solid var(--borda)!important;
  color:var(--texto)!important; font-weight:600;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.14)!important;
  transition:transform .3s var(--mola),background .2s,border-color .2s,box-shadow .2s;
}
:is(@BTN@) p{color:inherit!important;font-weight:600}
:is(@BTN@):hover{background:rgba(255,255,255,.14)!important;border-color:var(--borda-forte)!important}
:is(@BTN@):active{transform:scale(.96)}
:is(@BTN@):focus-visible{outline:2px solid var(--azul);outline-offset:3px}
:is(@PRI@){
  background:linear-gradient(180deg,#4aa8ff,#2f8ef0)!important; border-color:rgba(255,255,255,.3)!important;
  color:#fff!important; box-shadow:inset 0 1px 0 rgba(255,255,255,.4),0 8px 24px rgba(47,142,240,.35)!important;
}
:is(@PRI@):hover{filter:brightness(1.08)}

/* menu: pílula de vidro com marcador que desliza */
.st-key-nav{
  --i:0; position:relative; width:min(600px,100%); margin:6px auto 26px; padding:5px;
  border-radius:999px; background:rgba(255,255,255,.06); border:1px solid var(--borda);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 16px 36px rgba(0,0,0,.3);
  backdrop-filter:blur(22px) saturate(150%); -webkit-backdrop-filter:blur(22px) saturate(150%);
}
.st-key-nav [data-testid="stHorizontalBlock"]{position:relative;z-index:2;gap:0!important;flex-wrap:nowrap!important}
.st-key-nav [data-testid="stColumn"]{flex:1 1 0!important;width:auto!important;min-width:0!important}
.st-key-nav::before{
  content:""; position:absolute; z-index:1; pointer-events:none;
  top:5px; bottom:5px; left:5px; width:calc((100% - 10px)/4); border-radius:999px;
  background:linear-gradient(180deg,rgba(255,255,255,.24),rgba(255,255,255,.1));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.45),0 6px 18px rgba(0,0,0,.3),0 0 0 1px rgba(255,255,255,.14);
  transform:translateX(calc(var(--i) * 100%));
  transition:transform .55s var(--mola);
}
.st-key-nav:has(.st-key-nav_rh button[data-testid*="rimary" i]){--i:1}
.st-key-nav:has(.st-key-nav_financeiro button[data-testid*="rimary" i]){--i:2}
.st-key-nav:has(.st-key-nav_compras button[data-testid*="rimary" i]){--i:3}
.st-key-nav:has(.st-key-nav_home button:active){--i:0}
.st-key-nav:has(.st-key-nav_rh button:active){--i:1}
.st-key-nav:has(.st-key-nav_financeiro button:active){--i:2}
.st-key-nav:has(.st-key-nav_compras button:active){--i:3}
.st-key-nav :is(@BTN@){
  background:transparent!important; border:none!important; box-shadow:none!important; transform:none!important;
  border-radius:999px!important; min-height:52px; padding:6px 4px; color:var(--mudo)!important;
  transition:color .25s;
}
.st-key-nav :is(@BTN@) p{font-size:13px;margin:0}
.st-key-nav :is(@BTN@):hover{color:var(--texto)!important;background:transparent!important}
.st-key-nav :is(@PRI@){color:#fff!important;background:transparent!important;filter:none}
.st-key-nav [data-testid="stIconMaterial"]{font-size:20px}

/* saudação */
.ola{margin:4px 0 22px}
.ola h1{font-size:clamp(28px,4.4vw,42px);line-height:1.1;margin:0;padding:0}
.ola p{color:var(--mudo);margin:8px 0 0;font-size:15px}

/* cartões de agentes na tela inicial */
[class*="st-key-vc_ag_"]{min-height:210px;cursor:pointer;
  transition:transform .35s var(--mola),border-color .2s,background .2s}
[class*="st-key-vc_ag_"]:hover{transform:translateY(-4px);border-color:var(--borda-forte)}
[class*="st-key-vc_ag_"]:has(button:active){transform:scale(.97)}
[class*="st-key-vc_ag_"]:has(button:focus-visible){outline:2px solid var(--azul);outline-offset:3px}
[class*="st-key-vc_ag_"]:has(button:disabled){cursor:not-allowed;opacity:.6}
[class*="st-key-vc_ag_"]:has(button:disabled):hover{transform:none}
[class*="st-key-abrir_"]{position:absolute!important;inset:0;z-index:4;margin:0!important}
[class*="st-key-abrir_"] [data-testid="stButton"]{height:100%}
[class*="st-key-abrir_"] button{width:100%!important;height:100%;opacity:0;border-radius:26px!important}
.ag-ico{display:inline-grid;place-items:center;width:58px;height:58px;border-radius:18px;
  background:rgba(255,255,255,.07);border:1px solid var(--borda)}
.ag-nome{font-size:18px;font-weight:700;letter-spacing:-.02em;margin-top:18px}
.ag-val{font-size:24px;font-weight:600;letter-spacing:-.03em;margin-top:4px;line-height:1.15}
.ag-sub{color:var(--mudo);font-size:13px;margin-top:4px;min-height:18px}
.pilula{display:inline-flex;align-items:center;gap:8px;margin-top:12px;padding:5px 12px;border-radius:999px;
  background:rgba(255,255,255,.09);font-size:12px;font-weight:600}
.pilula::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--fraco)}
.pilula.ok::before{background:var(--verde)}
.pilula.atencao::before{background:var(--ambar)}

.cab-agente{display:flex;align-items:center;gap:18px}
.cab-agente h2{margin:0;font-size:26px;padding:0}
.cab-agente p{margin:6px 0 0;color:var(--mudo);font-size:14px;line-height:1.5;max-width:640px}

/* hoje */
.dia-grande{font-size:54px;font-weight:500;letter-spacing:-.05em;line-height:1;margin-top:14px}
.dia-sub{color:var(--mudo);font-size:13px;margin-top:6px}
.escala-hoje{margin-top:14px;border-top:1px solid var(--borda)}
.linha-escala{display:flex;justify-content:space-between;gap:10px;padding:10px 0;
  border-bottom:1px solid rgba(255,255,255,.07);font-size:14px}
.linha-escala:last-child{border-bottom:none}
.linha-escala span{color:var(--mudo);font-variant-numeric:tabular-nums}
.vazio{color:var(--mudo);font-size:14px;line-height:1.5;margin-top:14px}
.avs{display:flex;align-items:center;margin:14px 0 2px}
.av{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;color:#14161a;
  font-size:12px;font-weight:800;border:2px solid #23262c;margin-left:-9px}
.av:first-child{margin-left:0}
.av.mais{background:rgba(255,255,255,.14);color:var(--texto)}

/* barras */
.barras{position:relative;display:flex;gap:12px;margin-top:18px}
.bcol{flex:1;min-width:0;text-align:center}
.trilho{position:relative;height:150px}
.bcol>span{display:block;margin-top:10px;font-size:12px;color:var(--mudo);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{position:absolute;left:16%;right:16%;border-radius:10px;background:rgba(255,255,255,.2)}
.bar.neg{background:rgba(255,160,120,.5)}
.bar.hi{background:var(--azul)}
.bar em{position:absolute;left:50%;bottom:calc(100% + 8px);transform:translateX(-50%);font-style:normal;
  font-size:12px;font-weight:700;padding:4px 9px;border-radius:999px;background:rgba(255,255,255,.92);
  color:#14161a;white-space:nowrap}
.bar.neg em{bottom:auto;top:calc(100% + 8px)}
.zero{position:absolute;left:0;right:0;top:75px;border-top:1px dashed rgba(255,255,255,.2)}
.barras.fantasma .bar{background:rgba(255,255,255,.08)}

[data-testid="stMetric"]{background:rgba(255,255,255,.05);border:1px solid var(--borda);border-radius:18px;padding:16px 18px}
[data-testid="stMetricLabel"] p{color:var(--mudo);font-size:13px;font-weight:500}
[data-testid="stMetricValue"]{font-weight:600;letter-spacing:-.03em}
[data-testid="stMetricDelta"]{color:var(--mudo)!important}
[class*="st-key-vc_ticket"]{border-left:3px solid var(--azul)}
.ticket-topo{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--borda);padding-bottom:12px;margin-bottom:12px}
.ticket-topo span{color:var(--mudo);font-size:12px}

[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  background:rgba(255,255,255,.06)!important;border-color:rgba(255,255,255,.14)!important;
  border-radius:14px!important;color:var(--texto)!important}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--azul)!important}
input,textarea{color:var(--texto)!important}
[data-testid="stFileUploaderDropzone"],[data-testid="stFileUploader"] section{
  background:rgba(255,255,255,.04);border:1.5px dashed rgba(255,255,255,.22);border-radius:18px}
[data-testid="stExpander"] details{background:rgba(255,255,255,.04);border:1px solid var(--borda);border-radius:16px}
[data-testid="stDataFrame"]{border:1px solid var(--borda);border-radius:16px;overflow:hidden}
[data-testid="stCode"] pre{background:rgba(0,0,0,.28)!important;border-radius:14px}
[data-testid="stAlert"]{border-radius:16px}
[data-testid="stPopoverBody"]{background:#23262c;border:1px solid var(--borda);border-radius:18px}

[data-testid="stChatMessage"]{background:rgba(255,255,255,.05);border:1px solid var(--borda);border-radius:20px;padding:14px 18px}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:rgba(59,157,255,.13);border-color:rgba(59,157,255,.3)}
[data-testid="stChatInput"]{background:rgba(255,255,255,.07);border:1px solid var(--borda-forte);border-radius:999px}
[data-testid="stChatInput"] textarea{background:transparent!important}
[data-testid="stChatInputSubmitButton"]{background:var(--azul)!important;color:#fff!important;border-radius:50%!important}
[class*="st-key-sug_"] button{min-height:38px!important;font-size:13px;padding:.3rem 1rem!important}

/* abertura */
.abertura{display:flex;flex-direction:column;align-items:center;text-align:center;padding:9vh 0 22px}
.orb{position:relative;width:190px;height:190px;margin-bottom:34px}
.orb::before{content:"";position:absolute;inset:-26px;border-radius:50%;
  background:conic-gradient(from 0deg,#3b9dff,#4fe0a8,#b69cff,#ff8cc6,#3b9dff);
  filter:blur(34px);opacity:.5;animation:gira 10s linear infinite}
.orb .anel-gira{position:absolute;inset:0;border-radius:50%;
  background:conic-gradient(from 0deg,#3b9dff,#4fe0a8,#ffc46b,#ff8cc6,#b69cff,#3b9dff);
  -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));
  mask:radial-gradient(farthest-side,transparent calc(100% - 5px),#000 calc(100% - 4px));
  animation:gira 6s linear infinite}
.orb .miolo{position:absolute;inset:12px;border-radius:50%;display:grid;place-items:center;
  background:radial-gradient(circle at 30% 25%,rgba(255,255,255,.22),rgba(255,255,255,.05) 55%,rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.16);box-shadow:inset 0 1px 0 rgba(255,255,255,.3);
  backdrop-filter:blur(8px);animation:respira 4.5s ease-in-out infinite}
.orb .miolo svg{filter:drop-shadow(0 6px 18px rgba(59,157,255,.5))}
@keyframes gira{to{transform:rotate(360deg)}}
@keyframes respira{50%{transform:scale(.965)}}
.marca-grande{font-size:clamp(40px,8vw,76px);font-weight:800;letter-spacing:-.06em;line-height:1}
.marca-grande span{color:var(--azul)}
.abertura .sub{color:var(--mudo);margin-top:14px;font-size:16px;max-width:420px;line-height:1.5}
.st-key-entrar{width:min(300px,100%);margin:6px auto 0}
.st-key-entrar button{min-height:54px;font-size:16px}
.robos{display:flex;justify-content:center;gap:12px;margin:34px 0 0;flex-wrap:wrap}
.chip-robo{width:58px;height:58px;border-radius:18px;display:grid;place-items:center;
  background:rgba(255,255,255,.06);border:1px solid var(--borda)}
.st-key-vc_login{max-width:440px;margin:8vh auto 0;padding:30px!important}
.login-titulo{font-size:28px;font-weight:700;letter-spacing:-.03em}
.login-sub,.dica{color:var(--mudo)!important;font-size:13px}

@media(max-width:700px){
  [data-testid="stMainBlockContainer"],.block-container{padding:14px 14px 40px!important}
  .chip-usuario div b{display:none}.chip-usuario div{padding:5px}
  .marca-topo .com{display:none}
}
@media(max-width:560px){.st-key-nav :is(@BTN@) p{display:none}.st-key-nav :is(@BTN@){min-height:48px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
@media(prefers-reduced-transparency:reduce){
  [class*="st-key-vc_"],.st-key-nav{backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
  [class*="st-key-vc_"]{background:#23262c}
}
"""


def _minificar(css):
    css = css.replace("@BTN@", BOTOES).replace("@PRI@", PRIMARIOS)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"\s+", " ", css).strip()


st.markdown(f"<style>{_minificar(CSS)}</style>", unsafe_allow_html=True)

CFG = {
    "funcionario": "Funcionário", "saldo": "Saldo", "situacao": "Situação",
    "data": "Data", "entrada": "Entrada", "saida": "Saída",
    "forma": "Forma", "status": "Status", "descricao": "Descrição",
    "esperado": st.column_config.NumberColumn("Esperado", format="R$ %.2f"),
    "recebido": st.column_config.NumberColumn("Recebido", format="R$ %.2f"),
    "diferenca": st.column_config.NumberColumn("Diferença", format="R$ %.2f"),
    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
    "item": "Item", "unidade": "Unidade", "quantidade": "Quantidade",
    "fornecedor": "Fornecedor", "prazo_dias": "Prazo (dias)", "motivo": "Critério",
    "preco_unitario": st.column_config.NumberColumn("Preço unit.", format="R$ %.2f"),
    "total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
}


# ---------- funções comuns ----------
def agora():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


def ir(tela, agente=None):
    st.session_state["tela"] = tela
    st.session_state["agente"] = agente
    st.rerun()


def card(nome):
    return st.container(key=f"vc_{nome}")


def titulo(texto, detalhe=""):
    extra = f"<small>{detalhe}</small>" if detalhe else ""
    st.markdown(f'<div class="titulo-secao">{texto}{extra}</div>', unsafe_allow_html=True)


def comanda(nome, relatorio):
    st.markdown(
        f'<div class="ticket-topo"><strong>{nome}</strong>'
        f'<span>{agora():%d/%m/%Y %H:%M}</span></div>',
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


# ---------- IA ----------
MODELOS_IA = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]


def perguntar_ia(pedido):
    try:
        cliente = genai.Client()
    except Exception as erro:
        return f"Chave da IA não encontrada: {erro}"
    for modelo in MODELOS_IA:
        try:
            return cliente.models.generate_content(model=modelo, contents=pedido).text
        except Exception:
            time.sleep(3)
    return "A IA não respondeu. Tente de novo mais tarde."


def perguntar_ia_stream(prompt):
    try:
        cliente = genai.Client()
    except Exception as erro:
        yield f"Chave da IA não encontrada: {erro}"
        return
    for modelo in MODELOS_IA:
        enviou = False
        try:
            for parte in cliente.models.generate_content_stream(model=modelo, contents=prompt):
                if parte.text:
                    enviou = True
                    yield parte.text
            return
        except Exception:
            if enviou:
                return
            time.sleep(2)
    yield "A IA não respondeu. Tente de novo mais tarde."


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


# ---------- chat com a IA ----------
SUGESTOES = {
    None: ["O que preciso resolver esta semana?", "Resuma tudo em 5 linhas", "Tem algo fora do normal?"],
    "rh": ["Quem precisa compensar horas?", "Quantas horas de equipe tenho por semana?", "Escreva um aviso sobre a escala"],
    "financeiro": ["Quais pagamentos não bateram?", "Quanto deixou de cair no banco?", "Resuma as contas pagas"],
    "compras": ["O que preciso comprar?", "Qual o total e a economia?", "Qual fornecedor tem o maior pedido?"],
}
AVATAR = {"user": ":material/person:", "assistant": ":material/smart_toy:"}


def contexto_geral():
    partes = []
    try:
        from rh_ponto import resumo_para_ia
        partes.append("EQUIPE CADASTRADA:\n" + resumo_para_ia())
    except Exception:
        pass
    ss = st.session_state
    if "resultado_rh" in ss:
        r = ss["resultado_rh"]
        partes.append(
            f"SALDO DE HORAS (período {r.get('periodo', 'não informado')}, "
            f"{r.get('n_dias', '?')} dia(s) com registro):\n"
            + r["total"][["funcionario", "saldo", "situacao"]].to_string(index=False)
        )
    if "resultado_fin" in ss:
        r = ss["resultado_fin"]
        div = r["divergentes"].to_string(index=False) if len(r["divergentes"]) else "nenhuma"
        partes.append(
            f"FINANCEIRO (última conferência): {len(r['conc'])} vendas conferidas.\n"
            f"Divergências:\n{div}\nContas pagas:\n{r['contas'].to_string(index=False)}"
        )
    if "resultado_cmp" in ss:
        r = ss["resultado_cmp"]
        p = r["pedidos"]
        if p.empty:
            txt = "Nenhum pedido gerado."
        else:
            cols = ["item", "quantidade", "unidade", "fornecedor", "preco_unitario", "prazo_dias", "total"]
            txt = (
                p[cols].to_string(index=False)
                + f"\nTotal: {brl(p['total'].sum())} | Economia: {brl(p['economia'].sum())}"
            )
        partes.append(
            f"COMPRAS (última análise):\n{txt}\n"
            f"Itens sem cotação: {', '.join(r['sem_cotacao']) or 'nenhum'}"
        )
    return "\n\n".join(partes) or "Nenhum dado foi enviado ainda nesta sessão."


def montar_prompt(nome_usuario, escopo, historico, pergunta):
    if escopo:
        ag = AGENTES[escopo]
        foco = f"Você está na seção do agente de {ag['nome']}, que serve para {ag['serve']}.\n{ag['contexto']}"
    else:
        foco = "Você conhece os agentes de RH, Financeiro e Compras e pode cruzar informações entre eles."
    conversa = "\n".join(
        f"{'Usuário' if m['papel'] == 'user' else 'Assistente'}: {m['texto']}" for m in historico[-8:]
    )
    return (
        "Você é o assistente do sistema hnos system A, usado para gerir um restaurante. "
        f"Fale com {nome_usuario}, em português, de forma direta e curta (no máximo 6 linhas, "
        f"a menos que peçam mais).\n{foco}\n\n"
        "REGRAS:\n"
        "- Use somente os dados abaixo. Nunca invente números, nomes ou datas.\n"
        "- Sempre diga o período que os dados cobrem. Nunca chame de 'semana' um período com menos de 7 dias.\n"
        "- Se os registros parecerem incompletos (turnos de poucos minutos, por exemplo), avise que o saldo "
        "pode estar distorcido antes de recomendar qualquer ação.\n"
        "- Se faltar dado, diga qual planilha ou cadastro enviar e em qual agente.\n"
        "- Você não paga contas, não envia pedidos e não altera nada: só analisa e sugere. "
        "Quando ajudar, escreva o texto da mensagem para a pessoa copiar e enviar.\n"
        "- Prefira os totais já calculados nos dados.\n\n"
        f"DADOS DISPONÍVEIS:\n{contexto_geral()}\n\n"
        f"CONVERSA ATÉ AGORA:\n{conversa or '(início)'}\n\n"
        f"Pergunta atual: {pergunta}"
    )


def chat_ia(nome_usuario, escopo=None):
    chave = f"chat_{escopo or 'painel'}"
    historico = st.session_state.setdefault(chave, [])

    with card(f"chat_{escopo or 'painel'}"):
        if escopo:
            titulo(
                f"Converse com o agente de {AGENTES[escopo]['nome']}",
                "Pergunte sobre os dados que você já enviou. Ele analisa e sugere, mas não paga nem envia nada.",
            )
        else:
            titulo(
                "Converse com o assistente",
                "Ele conhece todos os agentes. Analisa e sugere, mas não paga nem envia nada.",
            )

        sugestoes = SUGESTOES.get(escopo, SUGESTOES[None])
        for i, (col, texto) in enumerate(zip(st.columns(len(sugestoes)), sugestoes)):
            if col.button(texto, key=f"sug_{chave}_{i}", use_container_width=True):
                st.session_state[f"pend_{chave}"] = texto

        for m in historico:
            with st.chat_message(m["papel"], avatar=AVATAR[m["papel"]]):
                st.markdown(m["texto"])

        if historico and st.button("Limpar conversa", key=f"limpar_{chave}"):
            st.session_state[chave] = []
            st.rerun()

        pergunta = st.chat_input("Escreva sua pergunta...", key=f"in_{chave}")
        if not pergunta:
            pergunta = st.session_state.pop(f"pend_{chave}", None)

        if pergunta:
            with st.chat_message("user", avatar=AVATAR["user"]):
                st.markdown(pergunta)
            with st.chat_message("assistant", avatar=AVATAR["assistant"]):
                resposta = st.write_stream(
                    perguntar_ia_stream(montar_prompt(nome_usuario, escopo, historico, pergunta))
                )
            historico.append({"papel": "user", "texto": pergunta})
            historico.append({"papel": "assistant", "texto": resposta})


# ---------- RH ----------
def ler_aba(arq, nome):
    abas = pd.ExcelFile(arq).sheet_names
    achada = next((a for a in abas if a.strip().lower() == nome), None)
    if achada is None:
        raise ValueError(
            f'A planilha não tem a aba "{nome}". Abas encontradas: {", ".join(abas)}.'
        )
    return pd.read_excel(arq, sheet_name=achada)


def ler_horario(serie):
    try:
        t = pd.to_datetime(serie, errors="coerce")
        if t.dtype == object:
            raise ValueError("fusos misturados")
    except ValueError:
        t = pd.to_datetime(serie, errors="coerce", utc=True)
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    return t


def preparar_ponto(ponto):
    p = ponto.copy()
    p.columns = [str(c).strip().lower() for c in p.columns]
    for c in ("funcionario", "entrada", "saida"):
        if c not in p.columns:
            raise KeyError(c)
    p = p.dropna(subset=["funcionario", "entrada", "saida"]).copy()
    if "intervalo" in p.columns:
        p["intervalo"] = pd.to_numeric(p["intervalo"], errors="coerce").fillna(0)
    else:
        p["intervalo"] = 0

    if "data" in p.columns:  # planilha da semana: horários em HH:MM
        p = padronizar_data(p)
        bruto = p["saida"].apply(minutos) - p["entrada"].apply(minutos)
        bruto = bruto.where(bruto > 0, bruto + 1440)
        p["entrada"] = p["entrada"].astype(str).str[:5]
        p["saida"] = p["saida"].astype(str).str[:5]
    else:  # relatório do painel de ponto: data e hora juntas
        ent = ler_horario(p["entrada"])
        sai = ler_horario(p["saida"])
        if ent.isna().any() or sai.isna().any():
            raise ValueError("Não consegui ler alguns horários de entrada ou saída da aba ponto.")
        bruto = (sai - ent).dt.total_seconds() / 60
        p["data"] = ent.dt.strftime("%Y-%m-%d")
        p["entrada"] = ent.dt.strftime("%H:%M")
        p["saida"] = sai.dt.strftime("%H:%M")

    p["trabalhado"] = (bruto - p["intervalo"]).round().astype(int)
    if "jornada" in p.columns:
        p["previsto"] = pd.to_numeric(p["jornada"], errors="coerce")
    else:
        p["previsto"] = float("nan")
    return p.reset_index(drop=True)


def escala_do_cadastro(ponto):
    try:
        from rh_ponto import carregar, limpar_equipe, DIAS
    except ImportError:
        raise ValueError("A planilha não tem a aba escala e não há cadastro de equipe para usar no lugar.")
    equipe = limpar_equipe(carregar())
    if equipe.empty:
        raise ValueError("A planilha não tem a aba escala e o cadastro da equipe está vazio.")
    datas = sorted(pd.to_datetime(ponto["data"]).dt.normalize().unique())
    linhas = []
    for _, f in equipe.iterrows():
        for dia in datas:
            dia = pd.Timestamp(dia)
            if f[DIAS[dia.weekday()]]:
                linhas.append({
                    "funcionario": f["nome"], "data": dia.strftime("%Y-%m-%d"),
                    "entrada_prevista": f["entrada"], "saida_prevista": f["saida"],
                })
    return pd.DataFrame(
        linhas, columns=["funcionario", "data", "entrada_prevista", "saida_prevista"]
    )


def calcular_saldos(arq):
    ponto = preparar_ponto(ler_aba(arq, "ponto"))
    if ponto["previsto"].isna().any():  # sem jornada no arquivo: usa a escala
        try:
            escala = padronizar_data(ler_aba(arq, "escala"))
        except ValueError:
            escala = escala_do_cadastro(ponto)
        prev = escala["saida_prevista"].apply(minutos) - escala["entrada_prevista"].apply(minutos)
        escala["prev_esc"] = prev.where(prev > 0, prev + 1440)
        escala["_k"] = escala["funcionario"].astype(str).str.strip().str.lower()
        ponto["_k"] = ponto["funcionario"].astype(str).str.strip().str.lower()
        ponto = ponto.merge(escala[["_k", "data", "prev_esc"]], on=["_k", "data"], how="left")
        ponto["previsto"] = ponto["previsto"].fillna(ponto["prev_esc"])

    dados = ponto.dropna(subset=["previsto"]).copy()
    ignorados = len(ponto) - len(dados)
    if dados.empty:
        raise ValueError(
            "Nenhum registro do ponto bateu com a escala. Confira se os nomes e as datas estão certos."
        )
    dados["saldo_min"] = (dados["trabalhado"] - dados["previsto"]).round().astype(int)
    dados["saldo"] = dados["saldo_min"].apply(formatar)

    total = dados.groupby("funcionario")["saldo_min"].sum().reset_index()
    total["saldo"] = total["saldo_min"].apply(formatar)
    total["situacao"] = total["saldo_min"].apply(
        lambda m: "hora extra" if m > 0 else ("compensar" if m < 0 else "zerado")
    )
    return dados, total, ignorados


def texto_periodo(dados):
    dias = sorted(dados["data"].unique())

    def f(s):
        return f"{s[8:10]}/{s[5:7]}"

    return (f(dias[0]) if len(dias) == 1 else f"{f(dias[0])} a {f(dias[-1])}"), len(dias)


def pagina_rh():
    with card("cadastro"):
        try:
            from rh_ponto import painel
            painel()
        except ImportError:
            titulo("Equipe", "O arquivo rh_ponto.py não foi encontrado, então o cadastro não aparece.")

    with card("rh_envio"):
        titulo(
            "Envie a planilha do RH",
            "Aceita o relatório baixado do painel de ponto ou a planilha da semana (abas escala e ponto).",
        )
        arq = st.file_uploader("Planilha do RH (.xlsx)", type=["xlsx"], key="upload_rh")
        calcular = bool(arq) and st.button("Calcular horas", type="primary", key="btn_rh")

    if calcular:
        try:
            dados, total, ignorados = calcular_saldos(arq)
        except KeyError as erro:
            st.markdown(
                f'<div class="aviso alerta">Falta a coluna {escape(str(erro))} na aba ponto.</div>',
                unsafe_allow_html=True,
            )
        except (ValueError, AttributeError, TypeError) as erro:
            st.markdown(
                f'<div class="aviso alerta">{escape(str(erro))}</div>', unsafe_allow_html=True
            )
        else:
            periodo, n_dias = texto_periodo(dados)
            resumo = total[["funcionario", "saldo", "situacao"]].to_string(index=False)
            pedido = (
                "Você é assistente de RH de um restaurante. Com base no saldo de horas abaixo, "
                "escreva um relatório curto em português para o gerente: quem tem mais hora extra "
                "e quem precisa compensar. Só diga que alguém precisa compensar se a situação dele "
                "for 'compensar'. Cite o período dos dados e nunca chame de 'semana' um período "
                "com menos de 7 dias. Use apenas os números fornecidos, sem calcular nada.\n\n"
                f"Período dos dados: {periodo} ({n_dias} dia(s) com registro).\n{resumo}"
            )
            with st.spinner("Escrevendo o relatório..."):
                relatorio = perguntar_ia(pedido)
            st.session_state["resultado_rh"] = {
                "dados": dados, "total": total, "relatorio": relatorio,
                "ignorados": ignorados, "periodo": periodo, "n_dias": n_dias,
            }

    if "resultado_rh" in st.session_state:
        r = st.session_state["resultado_rh"]
        topo = r["total"].sort_values("saldo_min", ascending=False).iloc[0]
        extras = r["total"][r["total"]["saldo_min"] > 0]["saldo_min"].sum()

        with card("rh_resumo"):
            titulo("Resumo do período", f"Dados de {r['periodo']} · {r['n_dias']} dia(s) com registro")
            c1, c2, c3 = st.columns(3)
            c1.metric("Funcionários", len(r["total"]))
            c2.metric("Horas extras no total", formatar(extras))
            c3.metric("Maior saldo", topo["funcionario"], topo["saldo"], delta_color="off")
            if r.get("ignorados"):
                st.markdown(
                    f'<div class="aviso alerta">{r["ignorados"]} registro(s) do ponto ficaram de fora '
                    "porque não têm escala para essa pessoa e dia.</div>",
                    unsafe_allow_html=True,
                )

        with card("ticket_rh"):
            comanda("Relatório do RH", r["relatorio"])

        with card("rh_tabela"):
            titulo("Saldo por funcionário")
            st.dataframe(
                r["total"][["funcionario", "saldo", "situacao"]],
                hide_index=True, column_config=CFG,
            )
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


# ---------- Financeiro ----------
def pagina_financeiro():
    with card("fin_envio"):
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

        with card("fin_resumo"):
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

        with card("ticket_fin"):
            comanda("Relatório financeiro", r["relatorio"])

        with card("fin_detalhes"):
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


# ---------- Compras ----------
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


def pagina_compras():
    with card("cmp_envio"):
        titulo(
            "Envie a planilha de compras",
            "Um arquivo .xlsx com as abas estoque, cotacoes e fornecedores.",
        )
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
                '<div class="aviso alerta">A planilha está fora do padrão. Baixe a planilha modelo e use as mesmas abas e colunas.</div>',
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
                with st.spinner("Escrevendo o relatório..."):
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
        st.markdown(
            f'<div class="aviso alerta">Sem cotação para: {escape(", ".join(r["sem_cotacao"]))}. '
            "Adicione esses itens na aba cotacoes.</div>",
            unsafe_allow_html=True,
        )
    if pedidos.empty:
        if not r["sem_cotacao"]:
            st.markdown(
                '<div class="aviso ok">Estoque em dia. Nada para comprar agora.</div>',
                unsafe_allow_html=True,
            )
        return

    with card("cmp_resumo"):
        titulo("Resumo do pedido")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Itens a comprar", len(pedidos))
        c2.metric("Fornecedores", pedidos["fornecedor"].nunique())
        c3.metric("Total do pedido", brl(pedidos["total"].sum()))
        c4.metric("Economia", brl(pedidos["economia"].sum()))

    with card("cmp_lista"):
        titulo("Melhor opção por item")
        st.dataframe(
            pedidos[["item", "quantidade", "unidade", "fornecedor",
                     "preco_unitario", "prazo_dias", "total", "motivo"]],
            hide_index=True, column_config=CFG,
        )

    with card("ticket_cmp"):
        comanda("Relatório de compras", r["relatorio"])

    with card("cmp_envio_forn"):
        titulo("Pedidos por fornecedor", "Revise cada mensagem antes de enviar.")
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

        por_fornecedor = pedidos.groupby("fornecedor")["total"].sum().reset_index()
        st.download_button(
            "Baixar pedidos (.xlsx)",
            para_excel({
                "pedidos": pedidos.drop(columns=["economia"]),
                "por_fornecedor": por_fornecedor,
            }),
            file_name="pedidos_compras.xlsx",
        )


# ---------- peças visuais da tela inicial ----------
def iniciais(nome):
    partes = [p for p in str(nome).split() if p]
    if not partes:
        return "?"
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


def avatares(nomes, limite=5):
    saida = []
    for i, n in enumerate(nomes[:limite]):
        saida.append(
            f'<span class="av" style="background:{PALETA[i % len(PALETA)]}" '
            f'title="{escape(str(n))}">{escape(iniciais(n))}</span>'
        )
    if len(nomes) > limite:
        saida.append(f'<span class="av mais">+{len(nomes) - limite}</span>')
    return '<div class="avs">' + "".join(saida) + "</div>"


def anel(valor, total, grande, pequeno):
    r, c0 = 74, 95
    circ = 2 * math.pi * r
    f = 0 if total == 0 else min(max(valor / total, 0), 1)
    ang = -math.pi / 2 + 2 * math.pi * f
    kx, ky = c0 + r * math.cos(ang), c0 + r * math.sin(ang)
    return (
        '<div class="anel"><svg viewBox="0 0 190 190" width="190" height="190" aria-hidden="true">'
        f'<circle cx="{c0}" cy="{c0}" r="{r}" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="16"/>'
        f'<circle cx="{c0}" cy="{c0}" r="{r}" fill="none" stroke="#2f9bff" stroke-width="16" '
        f'stroke-linecap="round" stroke-dasharray="{circ * f:.1f} {circ:.1f}" transform="rotate(-90 {c0} {c0})"/>'
        f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="9" fill="#e9eef7" stroke="rgba(0,0,0,.25)"/>'
        f'</svg><div class="anel-centro"><b>{grande}</b><span>{pequeno}</span></div></div>'
    )


def barras(rotulos, valores, fmt, destaque=None, fantasma=False):
    if not valores:
        return ""
    m = max(abs(v) for v in valores) or 1
    neg = any(v < 0 for v in valores)
    colunas = []
    for i, (rot, v) in enumerate(zip(rotulos, valores)):
        h = max(abs(v) / m * (46 if neg else 92), 3)
        pos = "top:50%;" if v < 0 else ("bottom:50%;" if neg else "bottom:0;")
        cls = "bar" + (" hi" if i == destaque else "") + (" neg" if v < 0 else "")
        dica = f"<em>{escape(fmt(v))}</em>" if i == destaque else ""
        colunas.append(
            f'<div class="bcol"><div class="trilho"><div class="{cls}" style="{pos}height:{h:.1f}%">{dica}</div></div>'
            f'<span>{escape(str(rot))}</span></div>'
        )
    zero = '<div class="zero"></div>' if neg else ""
    extra = " fantasma" if fantasma else ""
    return f'<div class="barras{extra}">{zero}{"".join(colunas)}</div>'


def equipe_cadastro():
    try:
        from rh_ponto import carregar, limpar_equipe
        return limpar_equipe(carregar())
    except Exception:
        return pd.DataFrame()


def escalados_hoje(equipe):
    if equipe is None or equipe.empty:
        return []
    try:
        from rh_ponto import DIAS
        dia = DIAS[agora().weekday()]
        return [(r["nome"], r["entrada"], r["saida"]) for _, r in equipe.iterrows() if r.get(dia)]
    except Exception:
        return []


def cumprimento():
    h = agora().hour
    return "Bom dia" if h < 12 else ("Boa tarde" if h < 18 else "Boa noite")


# ---------- telas ----------
def tela_abertura():
    chips = "".join(
        f'<div class="chip-robo" style="color:{a["cor"]}">{robo(k, 32)}</div>' for k, a in AGENTES.items()
    )
    st.markdown(
        '<div class="abertura">'
        '<div class="orb" aria-hidden="true"><div class="anel-gira"></div><div class="miolo">'
        '<svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.4" '
        'stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>'
        '<circle cx="12" cy="12" r="1.6" fill="#3b9dff" stroke="none"/></svg></div></div>'
        '<div class="marca-grande">hnos system <span>A</span></div>'
        '<div class="sub">RH, financeiro e compras do restaurante em um só lugar.</div></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="entrar"):
        if st.button("Entrar no sistema", type="primary", key="btn_ok", use_container_width=True):
            ir("login")
    st.markdown(f'<div class="robos">{chips}</div>', unsafe_allow_html=True)


def tela_login():
    st.markdown('<div class="tela-solta"></div>', unsafe_allow_html=True)
    with card("login"):
        st.markdown(
            '<div class="login-titulo">Entrar</div>'
            '<p class="login-sub">Use o usuário e a senha do seu restaurante.</p>',
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


def cabecalho(nome_usuario):
    with st.container(key="topo"):
        c1, c2, c3 = st.columns([7, 2.6, 0.9], vertical_alignment="center")
        c1.markdown(
            '<div class="marca-topo"><div class="logo-chip">'
            '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" '
            'aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.2" fill="#2f9bff" '
            'stroke="none"/></svg></div>'
            '<div><div class="nome">hnos system <span>A</span></div>'
            f'<div class="com">with <strong>{escape(nome_usuario.lower())}</strong></div></div></div>',
            unsafe_allow_html=True,
        )
        c2.markdown(
            f'<div class="chip-usuario"><div><i>{escape(iniciais(nome_usuario))}</i>'
            f'<b>{escape(nome_usuario)}</b></div></div>',
            unsafe_allow_html=True,
        )
        if c3.button("Sair", key="btn_sair", icon=":material/power_settings_new:", help="Sair do sistema"):
            st.session_state.clear()
            st.session_state["tela"] = "login"
            st.rerun()


ITENS_NAV = [
    ("home", None, "Visão geral", ":material/dashboard:"),
    ("rh", "rh", "RH", ":material/groups:"),
    ("financeiro", "financeiro", "Financeiro", ":material/payments:"),
    ("compras", "compras", "Compras", ":material/shopping_cart:"),
]


def navegacao(atual=None):
    with st.container(key="nav"):
        cols = st.columns(4)
        for col, (chave, destino, nome, icone) in zip(cols, ITENS_NAV):
            if col.button(
                nome, key=f"nav_{chave}", icon=icone,
                type="primary" if atual == destino else "secondary",
                use_container_width=True,
            ):
                ir("painel" if destino is None else "agente", destino)


def status_agente(chave):
    ss = st.session_state
    vazio = ("Sem dados", "Envie o arquivo para começar.", "", "Aguardando")
    if chave == "rh":
        if "resultado_rh" not in ss:
            return vazio
        r = ss["resultado_rh"]
        n = int((r["total"]["saldo_min"] < 0).sum())
        if n:
            return (f"{n} para compensar", f"Período {r['periodo']}", "atencao", "Revisar")
        return ("Horas em dia", f"Período {r['periodo']}", "ok", "Conferido")
    if chave == "financeiro":
        if "resultado_fin" not in ss:
            return vazio
        n = len(ss["resultado_fin"]["divergentes"])
        if n == 0:
            return ("Tudo certo", "Vendas e banco conferem.", "ok", "Conferido")
        return (f"{n} divergência" + ("s" if n > 1 else ""), "Pagamentos que não bateram.", "atencao", "Revisar")
    if chave == "compras":
        if "resultado_cmp" not in ss:
            return vazio
        p = ss["resultado_cmp"]["pedidos"]
        if p.empty:
            return ("Em dia", "Nada para comprar.", "ok", "Estoque ok")
        return (brl(p["total"].sum()), f"{len(p)} itens a comprar.", "atencao", "Revisar pedidos")
    return ("Em breve", "Posts do Instagram.", "", "Em produção")


def tela_painel(nome_usuario):
    cabecalho(nome_usuario)
    navegacao(None)

    equipe = equipe_cadastro()
    escalados = escalados_hoje(equipe)
    ss = st.session_state

    st.markdown(
        f'<div class="ola"><h1>{cumprimento()}, {escape(nome_usuario)}</h1>'
        "<p>Escolha um agente para começar.</p></div>",
        unsafe_allow_html=True,
    )

    for col, (chave, ag) in zip(st.columns(4, gap="medium"), AGENTES.items()):
        with col:
            with st.container(key=f"vc_ag_{chave}"):
                val, sub, est, pil = status_agente(chave)
                st.markdown(
                    f'<span class="ag-ico" style="color:{ag["cor"]}">{robo(chave, 36)}</span>'
                    f'<div class="ag-nome">{ag["nome"]}</div><div class="ag-val">{val}</div>'
                    f'<div class="ag-sub">{sub}</div><span class="pilula {est}">{pil}</span>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Abrir {ag['nome']}", key=f"abrir_{chave}", disabled=not ag["ativo"]):
                    ir("agente", chave)

    esq, dir_ = st.columns([1, 1.2], gap="medium")
    with esq:
        with card("hoje"):
            d = agora()
            linhas = "".join(
                f'<div class="linha-escala"><b style="font-weight:600">{escape(str(n))}</b>'
                f"<span>{escape(str(e))} às {escape(str(s))}</span></div>"
                for n, e, s in escalados[:5]
            )
            bloco = (
                f'<div class="escala-hoje">{linhas}</div>' if linhas else
                '<div class="vazio">Ninguém na escala hoje, ou a equipe ainda não foi cadastrada na aba RH.</div>'
            )
            st.markdown(
                f'<div class="rot">Hoje<small>{len(escalados)} na escala · {len(equipe)} cadastrado(s)</small></div>'
                f'<div class="dia-grande">{d.day}</div>'
                f'<div class="dia-sub">{SEMANA[d.weekday()]}, {MESES[d.month - 1]} · {d:%H:%M}</div>'
                + (avatares(list(equipe["nome"])) if len(equipe) else "") + bloco,
                unsafe_allow_html=True,
            )
    with dir_:
        with card("barras"):
            if "resultado_rh" in ss:
                t = ss["resultado_rh"]["total"].reset_index(drop=True)
                vals = [m / 60 for m in t["saldo_min"]]
                nomes = [str(n).split()[0] for n in t["funcionario"]]
                alto = max(range(len(vals)), key=lambda i: abs(vals[i]))
                st.markdown(
                    f'<div class="rot">Saldo de horas<small>Período {ss["resultado_rh"].get("periodo", "")}</small></div>'
                    + barras(nomes, vals, lambda v: f"{v:+.1f} h", alto),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="rot">Saldo de horas<small>Por funcionário</small></div>'
                    + barras(["", "", "", "", ""], [4, 7, 5, 9, 6], str, None, fantasma=True)
                    + '<div class="vazio">Envie o ponto na aba RH para ver o saldo de cada pessoa.</div>',
                    unsafe_allow_html=True,
                )

    chat_ia(nome_usuario)


def tela_agente(nome_usuario, chave):
    ag = AGENTES[chave]
    cabecalho(nome_usuario)
    navegacao(chave)

    with card("cab"):
        st.markdown(
            f'<div class="cab-agente"><span class="ag-ico" style="color:{ag["cor"]}">{robo(chave, 44)}</span>'
            f'<div><h2>Agente de {ag["nome"]}</h2><p>Serve para {ag["serve"]}.</p></div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Como funciona", icon=":material/info:"):
            st.markdown(ag["contexto"])

    if chave == "rh":
        pagina_rh()
    elif chave == "financeiro":
        pagina_financeiro()
    elif chave == "compras":
        pagina_compras()
    chat_ia(nome_usuario, chave)


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