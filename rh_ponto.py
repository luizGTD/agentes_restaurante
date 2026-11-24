import os, sqlite3, smtplib, ssl, io
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from email.message import EmailMessage
import pandas as pd

TZ = ZoneInfo('America/Sao_Paulo')
@contextmanager
def db():
    c = sqlite3.connect(os.getenv('HNOS_DB', 'hnos_rh.sqlite3'), timeout=30)
    try:
        c.executescript('''CREATE TABLE IF NOT EXISTS funcionarios(id INTEGER PRIMARY KEY, nome TEXT UNIQUE NOT NULL, jornada INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS ponto(id INTEGER PRIMARY KEY, funcionario INTEGER NOT NULL, entrada TEXT NOT NULL, saida TEXT, jornada INTEGER NOT NULL, intervalo INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(funcionario) REFERENCES funcionarios(id));
        CREATE UNIQUE INDEX IF NOT EXISTS ponto_aberto ON ponto(funcionario) WHERE saida IS NULL;
        CREATE TABLE IF NOT EXISTS envios(periodo TEXT PRIMARY KEY);''')
        c.execute('PRAGMA foreign_keys=ON')
        yield c
        c.commit()
    finally: c.close()

def relatorio(inicio, fim):
    with db() as c:
        d = pd.read_sql_query('SELECT f.nome AS funcionario,p.entrada,p.saida,p.jornada,p.intervalo FROM ponto p JOIN funcionarios f ON f.id=p.funcionario WHERE substr(p.entrada,1,10) BETWEEN ? AND ? ORDER BY p.entrada', c, params=(str(inicio),str(fim)))
    d['trabalhado_min'] = [
    int((pd.to_datetime(s) - pd.to_datetime(e)).total_seconds() // 60)
    - (int(i) if pd.notna(i) else 0)
    if pd.notna(s) and pd.notna(e) and s != "" and e != ""
    else None
    for e, s, i in zip(d.entrada, d.saida, d.intervalo)
    ]
    d['saldo_min'] = d.trabalhado_min-d.jornada
    t = d[d.saida.notna()].groupby('funcionario',as_index=False)[['trabalhado_min','saldo_min']].sum()
    return d,t

def excel(d,t):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine='openpyxl') as w:
        d.to_excel(w,sheet_name='Ponto',index=False); t.to_excel(w,sheet_name='Resumo',index=False)
    return b.getvalue()

def enviar(inicio,fim):
    d,t=relatorio(inicio,fim)
    msg=EmailMessage(); msg['Subject']=f'HNOS RH | {inicio} a {fim}'; msg['From']=os.environ['SMTP_USER']; msg['To']=os.environ['RH_EMAIL']
    msg.set_content('Relatório de ponto em anexo. Registros sem saída não entram no saldo.\n\n'+t.to_string(index=False))
    msg.add_attachment(excel(d,t),maintype='application',subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='relatorio_rh.xlsx')
    with smtplib.SMTP_SSL(os.getenv('SMTP_HOST','smtp.gmail.com'),int(os.getenv('SMTP_PORT','465')),context=ssl.create_default_context(),timeout=30) as s:
        s.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']); s.send_message(msg)

def rotina():
    hoje=datetime.now(TZ).date(); periodos=[]
    if hoje.weekday()==0: periodos.append(('semanal',hoje-timedelta(days=7),hoje-timedelta(days=1)))
    if hoje.day==1:
        fim=hoje-timedelta(days=1); periodos.append(('mensal',fim.replace(day=1),fim))
    for tipo,a,b in periodos:
        chave=f'{tipo}:{a}:{b}'
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM envios WHERE periodo=?',(chave,)).fetchone(): continue
            # Read using same database before marking delivery.
            enviar(a,b); c.execute('INSERT INTO envios VALUES (?)',(chave,))

def painel():
    import streamlit as st
    st.subheader('Ponto digital e banco de horas')
    with st.expander('Cadastrar funcionário'):
        with st.form('rh_cadastro'):
            nome=st.text_input('Nome'); horas=st.number_input('Jornada líquida diária (horas)',0.5,16.0,8.0,0.5)
            if st.form_submit_button('Cadastrar'):
                if not nome.strip(): st.error('Informe o nome.')
                else:
                    try:
                        with db() as c: c.execute('INSERT INTO funcionarios(nome,jornada) VALUES (?,?)',(nome.strip(),round(horas*60)))
                        st.success('Funcionário cadastrado.')
                    except sqlite3.IntegrityError: st.error('Nome já cadastrado.')
    with db() as c: pessoas=c.execute('SELECT id,nome,jornada FROM funcionarios ORDER BY nome').fetchall()
    if pessoas:
        p=st.selectbox('Funcionário',pessoas,format_func=lambda x:x[1]); agora=datetime.now(TZ)
        with db() as c: aberto=c.execute('SELECT id,entrada FROM ponto WHERE funcionario=? AND saida IS NULL',(p[0],)).fetchone()
        with st.form('rh_batida'):
            dia=st.date_input('Data do registro',agora.date()); hora=st.time_input('Horário',agora.time().replace(second=0,microsecond=0)); intervalo=st.number_input('Intervalo não trabalhado (minutos)',0,480,0,disabled=not bool(aberto))
            if st.form_submit_button('Registrar saída' if aberto else 'Registrar entrada'):
                instante=datetime.combine(dia,hora,TZ); stamp=instante.isoformat()
                try:
                    with db() as c:
                        if instante>datetime.now(TZ): raise ValueError('Horário futuro não permitido.')
                        if aberto:
                            dur=(instante-datetime.fromisoformat(aberto[1])).total_seconds()/60
                            if dur<=0 or intervalo>=dur: raise ValueError('Saída ou intervalo inválido.')
                            c.execute('UPDATE ponto SET saida=?,intervalo=? WHERE id=? AND saida IS NULL',(stamp,intervalo,aberto[0]))
                        else:
                            if c.execute('SELECT 1 FROM ponto WHERE funcionario=? AND (saida IS NULL OR saida>?)',(p[0],stamp)).fetchone(): raise ValueError('Registro sobreposto ou anterior ao último turno.')
                            c.execute('INSERT INTO ponto(funcionario,entrada,jornada) VALUES (?,?,?)',(p[0],stamp,p[2]))
                    st.rerun()
                except (ValueError,sqlite3.IntegrityError) as e: st.error(str(e))
        if aberto: st.info('Entrada em aberto: '+aberto[1])
    hoje=datetime.now(TZ).date(); tipo=st.radio('Período',['Semana','Mês','Personalizado'],horizontal=True)
    a=hoje-timedelta(days=hoje.weekday()) if tipo=='Semana' else hoje.replace(day=1)
    b=hoje
    if tipo=='Personalizado':
        a=st.date_input('Início',a); b=st.date_input('Fim',b)
    if a>b: st.error('Período inválido.'); return
    d,t=relatorio(a,b)
    st.dataframe(t,hide_index=True); st.dataframe(d,hide_index=True)
    st.caption('Saldo em minutos por turno encerrado; não inclui faltas, feriados ou regras de convenção coletiva.')
    st.download_button('Baixar relatório de ponto',excel(d,t),'ponto_rh.xlsx',key='rh_ponto_download')
    if st.button('Enviar relatório por e-mail agora'):
        try: enviar(a,b); st.success('Relatório enviado.')
        except Exception: st.error('Falha no envio. Confira a configuração SMTP no servidor.')

if __name__=='__main__': rotina()
