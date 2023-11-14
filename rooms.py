import datetime, functools
import hashlib

from flask import (Flask, render_template, Blueprint, flash, redirect, request,
                   session, url_for, get_flashed_messages)
from werkzeug.security import check_password_hash, generate_password_hash
import mariadb
import mysql.connector
import sys
import re
from calendar import Calendar, monthrange


def login_required(user):
    """
        função para limitar o acesso as áreas restritas da plataforma (áreas que somente usuários logados podem acessar)
        utilizamos as sessões criadas na função 'fazer login' para validar se o usuário está logado ou não.

        se não estiver logado é redirecionado para a página de login.
    """
    @functools.wraps(user)
    def secure_function(*args, **kwargs):
        if "id_usuario" not in session:
            flash('faça o login para acessar!', 'info')
            return redirect(url_for('login'))
        else:
            return user(*args, **kwargs)
    return secure_function

def valida_email(email):
    # pass the regular expression
    # and the string into the fullmatch() method
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if re.fullmatch(regex, email):
        return True
    else:
        return False


def conecta_bd():

    try:
        conn = mariadb.connect(
            user="admin",
            password="021207",
            host="localhost",
            port=3306,
            database="rooms"

        )

        # conn = mysql.connector.connect(
        #     user="root",
        #     password="nLJmOoF6VM9qBJkpozwa",
        #     host="containers-us-west-151.railway.app",
        #     port=7137,
        #     database="rooms"
        #
        # )

    except mysql.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    return conn


def valida_permissao(usuario, modulo, aplicativo):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    cur.execute('select a.nivelacesso as nivel_user, b.nivelacesso as nivel_perfil from ger_usuario a '
                'inner join ger_perfil b on a.id_perfil = b.id_perfil '
                'where a.id_usuario = %s ', (usuario,))
    usuario = cur.fetchone()

    cur.execute('select a.nivelacesso as nivel_app, b.nivelacesso as nivel_modulo from ger_app a '
                'inner join ger_modulo b on a.id_modulo = b.id_modulo '
                'where a.id_app = %s and a.id_modulo = %s', (aplicativo, modulo,))
    app = cur.fetchone()

    cur.execute('select nivelacesso from ger_modulo where id_modulo = %s', (modulo,))
    mod = cur.fetchone()

    nivel_user = int(usuario['nivel_user'])
    nivel_perfil = int(usuario['nivel_perfil'])
    nivel_app = int(app['nivel_app']) if aplicativo > 0 else aplicativo
    nivel_modulo = int(app['nivel_modulo']) if aplicativo > 0 else int(mod['nivelacesso'])

    acesso = False

    if nivel_user >= nivel_app if aplicativo > 0 else 0 or nivel_user >= nivel_modulo:
        print('liberado')
        acesso = True
    elif nivel_perfil >= nivel_app if aplicativo > 0 else 0 or nivel_perfil >= nivel_modulo:
        print('liberado')
        acesso = True
    else:
        print('acesso negado')
        acesso = False

    return acesso

app = Flask(__name__)

app.secret_key = 'bdb93e1ead22caa2f1d1b330d0300c7c59a1a98c58f994e7088bd7758ef8256d'


def grava_log(descricao, usuario, app):

    conn = conecta_bd()
    cur = conn.cursor()

    cur.execute('INSERT INTO ger_log(descricao, usuariocriacao, datacriacao, id_app) VALUES(%s, %s, %s, %s)',
                (descricao, usuario, datetime.datetime.now(), app))

    conn.commit()

    conn.close()

@app.post('/fazer_login')
def fazer_login():

    usuario = request.form.get('email')
    senha = request.form.get('password')

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    cur.execute('select a.* from ger_usuario a '
                'where a.email = %s ', (usuario,))
    usuario_login = cur.fetchone()

    print('LOGIN AQUI')
    print(str(hashlib.md5(senha.encode('utf-8'))))
    print(usuario_login['senha'])

    if str(hashlib.md5(senha.encode('utf-8')).hexdigest()) == usuario_login['senha']:
        session.clear()
        session['id_usuario'] = usuario_login['id_usuario']
        session['nivel_usuario'] = usuario_login['nivelacesso']
        return redirect(url_for('index'))
    else:
        flash('usuário ou senha incorretos', 'danger')
        return redirect(url_for('login'))


@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/reservas')
@login_required
def reservas():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'], 2, 11)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso', 'info')
        return redirect(url_for('index'))

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin from rsv_reserva a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('A',))
    reservas = cur.fetchall()

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin from rsv_reserva a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('H',))
    reservas_finalizadas = cur.fetchall()

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin from rsv_reserva a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('C',))
    reservas_canceladas = cur.fetchall()

    conn.close()

    return render_template('reservas.html', reservas=reservas, reservas_finalizadas=reservas_finalizadas,
                           reservas_canceladas=reservas_canceladas,)


@app.route('/hospedagens')
@login_required
def hospedagens():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 13)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    cur.execute('select a.id_hospedagem, b.nome, c.nroquarto, a.datacheckin from rsv_hospedagem a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('A',))
    hospedagens = cur.fetchall()

    cur.execute('select a.id_hospedagem, b.nome, c.nroquarto, a.datacheckin from rsv_hospedagem a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('F',))
    hospedagens_finalizadas = cur.fetchall()

    cur.execute('select a.id_hospedagem, b.nome, c.nroquarto, a.datacheckin from rsv_hospedagem a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('P',))
    hospedagens_pagamento = cur.fetchall()

    print(hospedagens_finalizadas)

    conn.close()

    return render_template('hospedagens.html', hospedagens=hospedagens, hospedagens_finalizadas=hospedagens_finalizadas,
                           hospedagens_pagamento=hospedagens_pagamento)

@app.route('/reservas_hospede/<int:id_hospede>')
@login_required
def reservas_hospede(id_hospede):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 11)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    cur.execute('select a.id_hospedagem, b.nome, c.nroquarto, a.datacheckin from rsv_hospedagem a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.id_hospede = %s order by 1 desc', (id_hospede,))
    hospedagens = cur.fetchall()

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin from rsv_reserva a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.id_hospede = %s order by 1 desc', (id_hospede,))
    reservas = cur.fetchall()


    conn.close()

    return render_template('reservas_hospede.html', hospedagens=hospedagens, reservas=reservas)


@app.route('/')
@login_required
def index():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin from rsv_reserva a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('A',))
    reservas = cur.fetchall()

    cur.execute('select a.id_hospedagem, b.nome, c.nroquarto, a.datacheckin from rsv_hospedagem a '
                'inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where a.status = %s order by 1 desc', ('A',))
    hospedagens = cur.fetchall()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('index.html', reservas=reservas, hospedagens=hospedagens,
                           mes_atual=mes_atual, ano_atual=ano_atual)


@app.route('/quartos')
@login_required
def quartos():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 6)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    # lista de tipos de quarto utilizada no cadastro de novo quarto
    cur.execute('SELECT id_tipoquarto, descricao FROM rsv_tipoquarto')
    lista_tipo_quarto = cur.fetchall()

    #lista de quartos
    cur.execute('SELECT id_quarto, nroquarto, case when status = "L" then "livre" '
                'when status = "O" then "ocupado" '
                'when status = "P" then "livre" end as status FROM rsv_quarto')
    lista_quartos = cur.fetchall()
    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('quartos.html', lista_tipo_quarto=lista_tipo_quarto,
                           lista_quartos=lista_quartos, mes_atual=mes_atual, ano_atual=ano_atual)


@app.route('/quarto/<int:id_quarto>')
@login_required
def quarto(id_quarto):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 6)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('quartos'))

    cur.execute('SELECT * FROM rsv_quarto a '
                'where a.id_quarto= %s', (id_quarto,))
    quarto = cur.fetchone()

    cur.execute('select maxhospedes from rsv_tipoquarto where id_tipoquarto = %s', (quarto['id_tipoquarto'],))
    maxhospedes = cur.fetchone()

    capacidade = maxhospedes['maxhospedes'] if maxhospedes['maxhospedes'] else 0

    cur.execute('SELECT id_hospede, nome FROM rsv_hospede a '
                'where a.status = %s', ('A',))
    hospedes = cur.fetchall()

    # lista de tipos de hospede utilizada no cadastro do hospede
    cur.execute('SELECT id_tipoquarto, descricao FROM rsv_tipoquarto')
    lista_tipo_quarto = cur.fetchall()

    cur.execute('SELECT status FROM rsv_hospedagem where id_quarto = %s and '
                'sysdate() between datacheckin and datacheckout and status = %s ',
                (id_quarto, 'A'))

    ocupado = cur.fetchone()
    ocupado = len(ocupado if ocupado != None else '')

    cur.execute('select a.id_hospedagem, b.nome, a.datacheckin from rsv_hospedagem a inner join rsv_hospede b '
                'on a.id_hospede = b.id_hospede where a.id_quarto = %s order by 2 desc',
                (id_quarto, ))

    historico = cur.fetchall()

    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    data_minima_reserva = datetime.datetime.today() + datetime.timedelta(days=1)
    hoje = datetime.datetime.today()
    return render_template('quarto.html', quarto=quarto, lista_tipo_quarto=lista_tipo_quarto,
                           hospedes=hospedes, hoje=hoje, data_minima_reserva=data_minima_reserva,
                           ocupado=ocupado, historico=historico, mes_atual=mes_atual, ano_atual=ano_atual,
                           capacidade=capacidade)


@app.route('/hospedes')
@login_required
def hospedes(**kwargs):
    mensagens = get_flashed_messages(category_filter='danger')
    dados = request.args.to_dict()

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    # lista de hospedes exibida na página
    cur.execute('SELECT distinct * FROM v_rsv_hospedes limit 50')
    lista_hospedes = cur.fetchall()

    # lista de tipos de hospede utilizada no cadastro do hospede
    cur.execute('SELECT id_tipohospede, descricao FROM rsv_tipohospede')
    lista_tipo_hospede = cur.fetchall()
    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    if len(mensagens) > 0:
        return render_template('hospedes.html', lista_hospedes=lista_hospedes,
                               lista_tipo_hospede=lista_tipo_hospede, dados=dados, mes_atual=mes_atual,
                               ano_atual=ano_atual)
    return render_template('hospedes.html', lista_hospedes=lista_hospedes,
                           lista_tipo_hospede=lista_tipo_hospede, dados=dados, mes_atual=mes_atual,
                           ano_atual=ano_atual)


@app.route('/hospede/<int:id_hospede>')
@login_required
def hospede(id_hospede):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    cur.execute('SELECT * FROM rsv_hospede a '
                'inner join rsv_contatohospede b '
                'on a.id_hospede = b.id_hospede '
                'where a.id_hospede = %s', (id_hospede,))
    hospede = cur.fetchone()

    # lista de tipos de hospede utilizada no cadastro do hospede
    cur.execute('SELECT id_tipohospede, descricao FROM rsv_tipohospede')
    lista_tipo_hospede = cur.fetchall()

    cur.execute('SELECT id_quarto, nroquarto, capacidade FROM rsv_quarto WHERE status = "L"')
    quartos = cur.fetchall()

    cur.execute('SELECT id_dependente, nome, ROWNUM() as number FROM rsv_dependente where id_hospede = %s',
                (id_hospede,))
    dependentes = cur.fetchall()

    data_minima_reserva = datetime.datetime.today() + datetime.timedelta(days=1)
    hoje = datetime.datetime.today()

    cur.execute('SELECT status FROM rsv_hospedagem where id_hospede = %s and '
                'sysdate() between datacheckin and datacheckout and status = %s ',
                (id_hospede, 'A'))

    ocupado = cur.fetchone()
    ocupado = len(ocupado if ocupado != None else '')

    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('hospede.html', hospede=hospede, lista_tipo_hospede=lista_tipo_hospede,
                           quartos=quartos, data_minima_reserva=data_minima_reserva, hoje=hoje,
                           ocupado=ocupado, mes_atual=mes_atual, ano_atual=ano_atual, dependentes=dependentes)


@app.route('/dependente/<int:id_dependente>')
@login_required
def dependente(id_dependente):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    acesso = valida_permissao(session['id_usuario'], 2, 10)
    if not acesso:
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    cur.execute('SELECT * FROM rsv_dependente a '
                'where a.id_dependente = %s', (id_dependente,))
    dependente = cur.fetchone()

    # lista de tipos de hospede utilizada no cadastro do hospede
    cur.execute('SELECT id_tipohospede, descricao FROM rsv_tipohospede')
    lista_tipo_hospede = cur.fetchall()

    cur.execute('SELECT id_quarto, nroquarto, capacidade FROM rsv_quarto WHERE status = "L"')
    quartos = cur.fetchall()

    cur.execute('SELECT id_dependente, nome, ROWNUM() as number FROM rsv_dependente where id_dependente = %s',
                (id_dependente,))
    dependentes = cur.fetchall()

    data_minima_reserva = datetime.datetime.today() + datetime.timedelta(days=1)
    hoje = datetime.datetime.today()

    cur.execute('SELECT status FROM rsv_hospedagem a inner join rsv_hospdependente b '
                'on a.id_hospedagem = b.id_hospedagem '
                'where b.id_dependente = %s and '
                'status = %s ',
                (id_dependente, 'A'))

    ocupado = cur.fetchone()
    ocupado = len(ocupado if ocupado != None else '')

    cur.execute('SELECT a.*, b.nroquarto, c.nome FROM rsv_hospedagem a inner join rsv_quarto b on '
                'a.id_quarto = b.id_quarto inner join rsv_hospede c on '
                'a.id_hospede = c.id_hospede where a.id_hospede = %s and a.status = %s',
                (dependente['id_hospede'], 'A'))
    hospedagem_titular = cur.fetchall()

    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('dependente.html', dependente=dependente, lista_tipo_hospede=lista_tipo_hospede,
                           quartos=quartos, data_minima_reserva=data_minima_reserva, hoje=hoje,
                           ocupado=ocupado, mes_atual=mes_atual, ano_atual=ano_atual, dependentes=dependentes,
                           hospedagem_titular=hospedagem_titular)


@app.post('/inclui_dependente_hospedagem')
@login_required
def inclui_dependente_hospedagem():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_hospede = request.form.get('id_hospede')
        id_dependente = request.form.get('id_dependente')
        id_hospedagem = request.form.get('id_hospedagem')
        id_quarto = request.form.get('id_quarto')
        inclui = request.form.get('inclui')

    if inclui == 0:
        return redirect(url_for('dependentes', id_dependente=id_dependente))

    acesso = valida_permissao(session['id_usuario'] , 2 , 10)
    if not acesso:
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospede' , id_hospede=id_hospede))

    # verifica se dependente já está hospedado
    cur.execute('select * from rsv_hospdependente where id_hospedagem = %s and id_dependente = %s',
                (id_hospedagem, id_dependente,))
    dependente_hospedado = cur.fetchone()

    dependente_hospedado = dependente_hospedado if dependente_hospedado else ''
    if len(dependente_hospedado) > 0:
        flash('esse dependente já está vinculado a essa hospedagem!', 'info')
        return redirect(url_for('dependente' , id_dependente=id_dependente))

    # verifica capacidade do quarto
    cur.execute('select count(id_dependente) from rsv_hospdependente where id_hospedagem = %s',
                (id_hospedagem,))
    hospedados = cur.fetchone()
    hospedados = len(hospedados) + 1

    cur.execute('select id_tipoquarto from rsv_quarto where id_quarto = %s', (id_quarto,))
    quarto = cur.fetchone()

    print(quarto)

    cur.execute('select maxhospedes from rsv_tipoquarto where id_tipoquarto = %s', (quarto['id_tipoquarto'],))
    capacidade = cur.fetchone()

    if int(hospedados) >= capacidade['maxhospedes']:
        flash('capacidade do quarto atingida, não é possível hospedar.', 'info')
        return redirect(url_for('dependente', id_dependente=id_dependente))

    cur.execute('insert into rsv_hospdependente(id_hospedagem, id_dependente) values(%s, %s)' ,
                (id_hospedagem , id_dependente ,))

    conn.commit()
    conn.close()
    flash('Dependente vinculado a hospedagem com sucesso')
    return redirect(url_for('dependente', id_dependente=id_dependente))


@app.post('/cadastra_dependente')
@login_required
def cadastra_dependente():
    conn = conecta_bd()
    cur = conn.cursor()

    if request.method == 'POST':
        id_hospede = request.form.get('id_hospede')
        nome = request.form.get('nome')
        datanasc = request.form.get('datanasc')
        parentesco = request.form.get('parentesco')
        isento = request.form.get('isento')
        pertaxa = request.form.get('pertaxa')
        valortaxa = request.form.get('valortaxa')
        datacriacao = datetime.datetime.now()
        usucriacao = 'admin'
        status = 'A'

        # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 10)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospede' , id_hospede=id_hospede))

    cur.execute("insert into rsv_dependente(id_hospede, nome, datanasc, status, parentesco, isento, valortaxa,"
                "pertaxa, datacriacao, usuariocriacao) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s )",
                (id_hospede, nome, datanasc, status, parentesco, isento, valortaxa, pertaxa, datacriacao, usucriacao,))

    conn.commit()
    conn.close()

    grava_log(f'Dependente "{nome}" cadastrado com sucesso! {usucriacao}', usucriacao, 10)

    flash(f'Dependente "{nome}" cadastrado com sucesso!', 'success')

    return redirect(url_for('hospede', id_hospede=id_hospede))


@app.post('/atualiza_dependente')
@login_required
def atualiza_dependente():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    cur.execute('select nome from ger_usuario where id_usuario = %s', (session['id_usuario'],))
    usuario = cur.fetchone()

    if request.method == 'POST':
        id_dependente = request.form.get('id_dependente')
        nome = request.form.get('nome')
        datanasc = request.form.get('datanasc')
        parentesco = request.form.get('parentesco')
        isento = request.form.get('isento')
        pertaxa = request.form.get('pertaxa')
        valortaxa = request.form.get('valortaxa')
        dataalteracao = datetime.datetime.now()
        usualteracao = usuario['nome']
        status = 'A'

        # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 10)
    if not acesso:
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso', 'info')
        return redirect(url_for('dependente' , id_dependente=id_dependente))

    cur.execute("update rsv_dependente set nome = %s, datanasc = %s, status = %s, parentesco = %s, "
                "isento = %s, valortaxa = %s, "
                "pertaxa = %s, dataalteracao = %s, usuarioalteracao = %s where id_dependente = %s",
                (nome, datanasc, status, parentesco, isento, valortaxa, pertaxa, dataalteracao,
                usualteracao, id_dependente,))

    conn.commit()
    conn.close()

    grava_log(f'Dependente "{nome}" alterado com sucesso!' , usualteracao, 10)

    flash(f'Dependente "{nome}" alterado com sucesso!', 'success')

    return redirect(url_for('dependente', id_dependente=id_dependente))


@app.post('/cadastra_hospede')
@login_required
def cadastra_hospede():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        apelido = request.form.get('apelido')
        empresa = request.form.get('empresa')
        tipohospede = request.form.get('tipohospede')
        datanasc = request.form.get('datanasc')
        cargo = request.form.get('cargo')
        datacriacao = datetime.datetime.now()
        usucriacao = 'admin'
        cpf = request.form.get('cpf')
        rg = request.form.get('rg')
        codinterno = request.form.get('codinterno')
        status = 'A'
        tel1 = request.form.get('tel1')
        tel2 = request.form.get('tel2')
        email = request.form.get('email')
        rua = request.form.get('rua')
        numero = request.form.get('numero')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        uf = request.form.get('uf')
        cep = request.form.get('cep')
        complemento = request.form.get('complemento')

        cur.execute("SELECT cpf FROM rsv_hospede WHERE cpf = %s", (cpf,))

        if cur.fetchone():
            flash(f'O CPF {cpf} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': False, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospedes', **dados))

        cur.execute("SELECT rg FROM rsv_hospede WHERE rg = %s", (rg,))

        if cur.fetchone():
            flash(f'O RG {rg} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': False,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospedes', **dados))

        cur.execute("SELECT email FROM rsv_contatohospede WHERE email = %s", (email,))
        if cur.fetchone():
            flash(f'O e-mail {email} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': '',
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }

            print(cidade)

            return redirect(url_for('hospedes', **dados))

        email_valido = valida_email(email)
        if not email_valido:
            flash(f'O e-mail {email} é inválido! Verifique.', 'danger')
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': '',
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospedes', **dados))

        cur.execute("SELECT codinterno FROM rsv_hospede WHERE codinterno = %s", (codinterno,))

        if cur.fetchone():
            flash(f'O Cód. Interno {codinterno} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': False,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospedes', **dados))

        cur.execute("SELECT telefone FROM rsv_contatohospede WHERE telefone = %s", (tel1,))

        if cur.fetchone():
            flash(f'O telefone {tel1} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': '', 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospedes', **dados))

        cur.execute("INSERT INTO rsv_hospede(nome, apelido, id_empresa, id_tipohospede, datanasc, cargo, datacriacao, "
                    "usuariocriacao, dataalteracao, usuarioalteracao, cpf, rg, codinterno, status) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (nome, apelido, empresa, tipohospede, datanasc, cargo, datacriacao, usucriacao, None, None, cpf,
                     rg, codinterno, status))

        cur.execute("INSERT INTO rsv_contatohospede(id_hospede, telefone, telefone2, email, rua, numero, bairro, "
                    "cidade, uf, cep, complemento) "
                    "VALUES(LAST_INSERT_ID(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (tel1, tel2, email, rua, numero, bairro, cidade, uf, cep, complemento))

        conn.commit()
        # with open('produtos.json', 'w') as fout:
        #     json.dump(prds, fout)
        conn.close()

        grava_log(f'hospede {nome} cadastrado pelo usuário {usucriacao}', usucriacao, 8)

        flash(f'O Hospede {nome} foi cadastrado com sucesso!', 'success')

    return redirect(url_for('hospedes'))


@app.post('/cadastra_quarto')
@login_required
def cadastra_quarto():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 6)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('quartos'))

    if request.method == 'POST':
        numero = request.form.get('numero')
        capacidade = request.form.get('capacidade')
        tipoquarto = request.form.get('tipoquarto')
        valor = request.form.get('valor')
        datacriacao = datetime.datetime.now()
        usucriacao = 'admin'
        status = 'L'
        hotel = 1

        cur.execute("SELECT nroquarto FROM rsv_quarto WHERE nroquarto = %s", (numero,))

        if cur.fetchone():
            flash(f'O quarto {numero} já está cadastrado! Verifique.', 'danger')
            conn.close()
            return redirect(url_for('quartos'))

        cur.execute("INSERT INTO rsv_quarto(nroquarto, capacidade, status, valordiaria, id_tipoquarto, "
                    "dataultcheckin, dataultcheckout, usuariocriacao, datacriacao, dataalteracao, "
                    "usuarioalteracao, id_hotel) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (numero, capacidade, status, valor, tipoquarto, None, None, usucriacao,
                     datacriacao, None, None, hotel))

        conn.commit()

        conn.close()

        grava_log(f'usuario {usucriacao} criou o quarto {numero}', usucriacao, 6)

        flash(f'O quarto {numero} foi cadastrado com sucesso!', 'success')

    return redirect(url_for('quartos'))


@app.post('/cadastra_tipoquarto')
@login_required
def cadastra_tipoquarto():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 14)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    if request.method == 'POST':
        tipoquarto = request.form.get('tipoquarto')
        capacidade = request.form.get('capacidade')
        perdesconto = request.form.get('perdesconto') if request.form.get('perdesconto') else 0
        valordesconto = request.form.get('valordesconto') if request.form.get('valordesconto') else 0

        cur.execute("INSERT INTO rsv_tipoquarto(descricao, status, perdesconto, valordesconto, maxhospedes, "
                    "usuariocriacao, datacriacao, dataalteracao, "
                    "usuarioalteracao, id_hotel) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (tipoquarto, 'A', perdesconto, valordesconto, capacidade, 'admin', datetime.datetime.now(),
                     None, None, 1))

        conn.commit()

        conn.close()

        grava_log(f'tipo quarto {tipoquarto} criado', 'admin', 14)

    return redirect(url_for('configuracoes'))


@app.post('/cadastra_tipohospede')
@login_required
def cadastra_tipohospede():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 7)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    if request.method == 'POST':
        tipohospede = request.form.get('tipohospede')
        perdesconto = request.form.get('perdesconto') if request.form.get('perdesconto') else 0
        valordesconto = request.form.get('valordesconto') if request.form.get('valordesconto') else 0

        cur.execute("INSERT INTO rsv_tipohospede(descricao, status, perdesconto, valordesconto, "
                    "usuariocriacao, datacriacao, dataalteracao, "
                    "usuarioalteracao) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                    (tipohospede, 'A', perdesconto, valordesconto, 'admin', datetime.datetime.now(),
                     None, None,))

        conn.commit()

        conn.close()

        grava_log(f'tipo hospede {tipohospede} criado', 'admin', 7)

    return redirect(url_for('configuracoes'))


@app.post('/cadastra_perfil')
@login_required
def cadastra_perfil():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 18)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    if request.method == 'POST':
        perfil = request.form.get('perfil')
        nivelacesso = request.form.get('nivelacesso')

        cur.execute("INSERT INTO ger_perfil(descricao, nivelacesso) "
                    "VALUES(%s, %s)",
                    (perfil, nivelacesso,))

        conn.commit()

        conn.close()

        grava_log(f'Perfil {perfil} criado', 'admin', 18)

    return redirect(url_for('configuracoes'))

@app.post('/cadastra_servico')
@login_required
def cadastra_servico():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 15)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    if request.method == 'POST':
        servico = request.form.get('servico')
        valor = request.form.get('valor')

        cur.execute("INSERT INTO rsv_servico(descricao, valor, id_hotel) "
                    "VALUES(%s, %s, %s)",
                    (servico, valor, 1,))

        conn.commit()

        conn.close()

        grava_log(f'Perfil {servico} criado', 'admin', 15)

    return redirect(url_for('configuracoes'))



@app.post('/cadastra_usuario')
@login_required
def cadastra_usuario():
    conn = conecta_bd()
    cur = conn.cursor()

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 19)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        perfil = request.form.get('id_perfil')
        nivelacesso = request.form.get('nivelacesso')
        email = request.form.get('email')
        senha = request.form.get('senha')

        cur.execute("INSERT INTO ger_usuario(nome, id_perfil, nivelacesso, email, senha) "
                    "VALUES(%s, %s, %s, %s, md5(%s))",
                    (nome, perfil, nivelacesso, email, senha))

        conn.commit()

        conn.close()

        grava_log(f'Usuário {nome} criado', 'admin', 19)

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_quarto')
@login_required
def atualiza_quarto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 6)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('quartos'))

    if request.method == 'POST':
        id_quarto = request.form.get('id_quarto')
        numero = request.form.get('numero')
        #capacidade = request.form.get('capacidade')
        tipoquarto = request.form.get('tipoquarto')
        valor = request.form.get('valor')
        dataalteracao = datetime.datetime.now()
        usuarioalteracao = 'admin'
        status = request.form.get('status')

    cur.execute("SELECT nroquarto FROM rsv_quarto WHERE nroquarto = %s and id_quarto <> %s", (numero, id_quarto,))

    if cur.fetchone():
        flash(f'O quarto {numero} já está cadastrado! Verifique.', 'danger')
        conn.close()
        return redirect(url_for('quarto', id_quarto=id_quarto))

    cur.execute('select * from rsv_quarto where id_quarto = %s', (id_quarto,))
    quarto = cur.fetchone()

    cur.execute('select maxhospedes from rsv_tipoquarto where id_tipoquarto = %s' , (quarto['id_tipoquarto'] ,))
    maxhospedes = cur.fetchone()

    capacidade = maxhospedes['maxhospedes'] if maxhospedes['maxhospedes'] else 0

    lista_alterados = []

    if int(numero) != int(quarto['nroquarto']):
        lista_alterados.append({
            'campo': 'numero',
            'novo': numero,
            'antigo': quarto['nroquarto']
        })
    if int(capacidade) != int(quarto['capacidade']):
        lista_alterados.append({
            'campo': 'capacidade',
            'novo': capacidade,
            'antigo': quarto['capacidade']
        })
    if int(tipoquarto) != int(quarto['id_tipoquarto']):
        lista_alterados.append({
            'campo': 'tipoquarto',
            'novo': tipoquarto,
            'antigo': quarto['id_tipoquarto']
        })
    if float(valor) != float(quarto['valordiaria']):
        lista_alterados.append({
            'campo': 'valordiaria',
            'novo': valor,
            'antigo': quarto['valordiaria']
        })

    cur.execute('update rsv_quarto set nroquarto = %s, capacidade = %s, id_tipoquarto = %s, '
                'valordiaria = %s, status = %s, dataalteracao = %s, usuarioalteracao = %s '
                'where id_quarto= %s',
                (numero, capacidade, tipoquarto, valor, status, dataalteracao,
                 usuarioalteracao, id_quarto))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado campo {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'para o quarto {quarto["nroquarto"]} id: {quarto["id_quarto"]}', 'admin', 6)

    flash(f'O quarto {numero} foi atualizado com sucesso.', 'info')
    conn.close()

    return redirect(url_for('quarto', id_quarto=id_quarto))


@app.post('/atualiza_hospede')
@login_required
def atualiza_hospede():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    if request.method == 'POST':
        id_hospede = request.form.get('id_hospede')
        nome = request.form.get('nome')
        apelido = request.form.get('apelido')
        empresa = request.form.get('empresa')
        tipohospede = request.form.get('tipohospede')
        datanasc = request.form.get('datanasc')
        cargo = request.form.get('cargo')
        cpf = request.form.get('cpf')
        rg = request.form.get('rg')
        codinterno = request.form.get('codinterno')
        status = 'A'
        tel1 = request.form.get('tel1')
        tel2 = request.form.get('tel2')
        email = request.form.get('email')
        rua = request.form.get('rua')
        numero = request.form.get('numero')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')
        uf = request.form.get('uf')
        cep = request.form.get('cep')
        complemento = request.form.get('complemento')

        cur.execute('SELECT * FROM rsv_hospede a '
                    'inner join rsv_contatohospede b '
                    'on a.id_hospede = b.id_hospede '
                    'where a.id_hospede = %s', (id_hospede,))
        hospede = cur.fetchone()

        campos_alterados = []

        if nome != hospede['nome']:
            campos_alterados.append({'campo': 'nome',
                                     'valor_anterior': hospede['nome'],
                                     'valor_novo': nome})
        if apelido != hospede['apelido']:
            campos_alterados.append({'campo': 'apelido',
                                     'valor_anterior': hospede['apelido'],
                                     'valor_novo': apelido})
        if int(empresa if empresa else 0) != int(hospede['id_empresa'] if hospede['id_empresa'] else 0):
            campos_alterados.append({'campo': 'empresa',
                                     'valor_anterior': hospede['id_empresa'],
                                     'valor_novo': empresa})
        if int(tipohospede) != int(hospede['id_tipohospede']):
            campos_alterados.append({'campo': 'tipohospede',
                                     'valor_anterior': hospede['id_tipohospede'],
                                     'valor_novo': tipohospede})
        nasc = datanasc.split('-')
        nasc_bd = str(hospede['datanasc']).split('-')
        print(nasc, nasc_bd)
        if nasc[0] != nasc_bd[0] or  nasc[1] != nasc_bd[1] or nasc[2] != nasc_bd[2]:
            campos_alterados.append({'campo': 'datanasc',
                                     'valor_anterior': hospede['datanasc'],
                                     'valor_novo': datanasc})
        if cargo != hospede['cargo']:
            campos_alterados.append({'campo': 'cargo',
                                     'valor_anterior': hospede['cargo'],
                                     'valor_novo': cargo})
        if cpf != hospede['cpf']:
            campos_alterados.append({'campo': 'cpf',
                                     'valor_anterior': hospede['cpf'],
                                     'valor_novo': cpf})
        if rg != hospede['rg']:
            campos_alterados.append({'campo': 'rg',
                                     'valor_anterior': hospede['rg'],
                                     'valor_novo': rg})
        if codinterno != hospede['codinterno']:
            campos_alterados.append({'campo': 'codinterno',
                                     'valor_anterior': hospede['codinterno'],
                                     'valor_novo': codinterno})
        if status != hospede['status']:
            campos_alterados.append({'campo': 'status',
                                     'valor_anterior': hospede['status'],
                                     'valor_novo': status})
        if tel1 != hospede['telefone']:
            campos_alterados.append({'campo': 'telefone',
                                     'valor_anterior': hospede['telefone'],
                                     'valor_novo': tel1})
        if tel2 != hospede['telefone2']:
            campos_alterados.append({'campo': 'telefone2',
                                     'valor_anterior': hospede['telefone2'],
                                     'valor_novo': tel2})
        if email != hospede['email']:
            campos_alterados.append({'campo': 'email',
                                     'valor_anterior': hospede['email'],
                                     'valor_novo': email})
        if rua != hospede['rua']:
            campos_alterados.append({'campo': 'rua',
                                     'valor_anterior': hospede['rua'],
                                     'valor_novo': rua})
        if int(numero) != int(hospede['numero']):
            campos_alterados.append({'campo': 'numero',
                                     'valor_anterior': hospede['numero'],
                                     'valor_novo': numero})
        if cidade != hospede['cidade']:
            campos_alterados.append({'campo': 'cidade',
                                     'valor_anterior': hospede['cidade'],
                                     'valor_novo': cidade})
        if bairro != hospede['bairro']:
            campos_alterados.append({'campo': 'bairro',
                                     'valor_anterior': hospede['bairro'],
                                     'valor_novo': bairro})
        if uf != hospede['uf']:
            campos_alterados.append({'campo': 'uf',
                                     'valor_anterior': hospede['uf'],
                                     'valor_novo': uf})
        if cep != hospede['cep']:
            campos_alterados.append({'campo': 'cep',
                                     'valor_anterior': hospede['cep'],
                                     'valor_novo': cep})
        if complemento != hospede['complemento']:
            campos_alterados.append({'campo': 'complemento',
                                     'valor_anterior': hospede['complemento'],
                                     'valor_novo': complemento})

        cur.execute("SELECT cpf FROM rsv_hospede WHERE cpf = %s and id_hospede <> %s", (cpf, id_hospede,))

        if cur.fetchone():
            flash(f'O CPF {cpf} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': False, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospede', hospede=id_hospede))

        cur.execute("SELECT rg FROM rsv_hospede WHERE rg = %s and id_hospede <> %s", (rg, id_hospede))

        if cur.fetchone():
            flash(f'O RG {rg} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': False,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospede', hospede=id_hospede))

        cur.execute("SELECT email FROM rsv_contatohospede WHERE email = %s and id_hospede <> %s", (email, id_hospede))
        if cur.fetchone():
            flash(f'O e-mail {email} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': '',
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }

            print(cidade)

            return redirect(url_for('hospede', hospede=id_hospede))

        email_valido = valida_email(email)
        if not email_valido:
            flash(f'O e-mail {email} é inválido! Verifique.', 'danger')
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': '',
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospede', hospede=id_hospede))

        cur.execute("SELECT codinterno FROM rsv_hospede WHERE codinterno = %s  and id_hospede <> %s",
                    (codinterno, id_hospede))

        if cur.fetchone():
            flash(f'O Cód. Interno {codinterno} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': False,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': tel1, 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospede', hospede=id_hospede))

        cur.execute("SELECT telefone FROM rsv_contatohospede WHERE telefone = %s and id_hospede <> %s",
                    (tel1, id_hospede))

        if cur.fetchone():
            flash(f'O telefone {tel1} já está associado a outro hospede! Verifique.', 'danger')
            conn.close()
            dados = {
                'nome': nome,
                'apelido': apelido,
                'empresa': empresa,
                'tipohospede': tipohospede,
                'datanasc': datanasc,
                'codinterno': codinterno,
                'cargo': cargo,
                'cpf': cpf, 'rg': rg,
                'tel1': '', 'tel2': tel2, 'email': email,
                'rua': rua, 'numero': numero, 'bairro': bairro, 'cidade': cidade, 'uf': uf, 'cep': cep,
                'complemento': complemento
            }
            return redirect(url_for('hospede', hospede=id_hospede))

        cur.execute("update rsv_hospede set nome = %s, apelido = %s, id_empresa = %s, id_tipohospede = %s, "
                    "datanasc = %s, cargo = %s, dataalteracao = %s, usuarioalteracao = %s, cpf = %s, rg = %s, "
                    "codinterno = %s, status = %s WHERE id_hospede = %s",
                    (nome, apelido, empresa, tipohospede, datanasc, cargo, datetime.datetime.now(), 'admin', cpf,
                     rg, codinterno, status, id_hospede))

        cur.execute("update rsv_contatohospede set telefone = %s, telefone2 = %s, email = %s, rua = %s, numero = %s, bairro = %s, "
                    "cidade = %s, uf = %s, cep = %s, complemento = %s WHERE id_hospede = %s",
                    (tel1, tel2, email, rua, numero, bairro, cidade, uf, cep, complemento, id_hospede))

        conn.commit()
        # with open('produtos.json', 'w') as fout:
        #     json.dump(prds, fout)
        conn.close()

        for campo in campos_alterados:
            grava_log(f'{campo["campo"]} alterado de {campo["valor_anterior"]} para {campo["valor_novo"]} no cadastro do '
                      f'hospede {nome} id:{id_hospede}', 'admin', 8)

        flash(f'Alterações salvas com sucesso!', 'success')

    return redirect(url_for('hospede', hospede=id_hospede))


@app.post('/inativa_hospede')
@login_required
def inativa_hospede():

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    id_hospede = request.form.get('id_hospede')

    cur.execute('SELECT nome from rsv_hospede where id_hospede = %s', (id_hospede,))
    hospede = cur.fetchone()

    cur.execute('UPDATE rsv_hospede SET status = "I" WHERE id_hospede = %s', (id_hospede,) )

    conn.commit()

    grava_log(f'usuario admin INATIVOU o hospede {hospede["nome"]}, id: {id_hospede}', 'admin', 8)

    flash(f'O hospede {hospede["nome"]} foi inativado', 'info')
    conn.close()

    return redirect(url_for('hospedes'))

@app.post('/ativa_hospede')
@login_required
def ativa_hospede():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    id_hospede = request.form.get('id_hospede')

    cur.execute('SELECT nome from rsv_hospede where id_hospede = %s', (id_hospede,))
    hospede = cur.fetchone()

    cur.execute('UPDATE rsv_hospede SET status = "A" WHERE id_hospede = %s', (id_hospede,))

    conn.commit()

    grava_log(f'usuario admin ATIVOU o hospede {hospede["nome"]}, id: {id_hospede}', 'admin', 8)

    flash(f'O hospede {hospede["nome"]} foi Ativado', 'info')
    conn.close()

    return redirect(url_for('hospedes'))


@app.route('/busca_hospede', methods=['GET','POST'])
@login_required
def busca_hospede():
    dados = request.args.to_dict()
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 8)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('hospedes'))

    nome = request.form.get('nome')
    codinterno = request.form.get('codinterno')
    empresa = request.form.get('empresa') if request.form.get('empresa') else 0
    tipohospede = request.form.get('tipohospede')
    cpf = request.form.get('cpf')
    rg = request.form.get('rg')

    print(f'nome: {nome}, cod: {codinterno}, empresa: {empresa}, tipo: {tipohospede}, '
          f'cpf {cpf}, rg: {rg}')

    cur.execute('select distinct * from v_rsv_buscahospede where (nome like %s or cpf = %s or rg = %s '
                'or codinterno = %s '
                'or empresa = %s) and tipohospede = %s', ('%'+nome+'%' if len(nome) > 0 else 0,
                                                        cpf if len(str(cpf)) > 0 else 0,
                                                        rg if len(str(rg)) > 0 else 0,
                                                        codinterno if len(str(codinterno)) > 0 else 0,
                                                        empresa if len(str(empresa)) > 0 else 0,
                                                        tipohospede if len(str(tipohospede)) > 0 else 0))

    busca = cur.fetchall()

    # lista de tipos de hospede utilizada no cadastro do hospede
    cur.execute('SELECT id_tipohospede, descricao FROM rsv_tipohospede')
    lista_tipo_hospede = cur.fetchall()
    conn.close()

    qtd_busca = len(busca)
    flash(f'a busca retornou {qtd_busca} registros compativeis', 'info')

    return render_template('busca_hospede.html', busca=busca, dados=dados, lista_tipo_hospede=lista_tipo_hospede)


@app.route('/configuracoes')
@login_required
def configuracoes():

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 0)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    print(acesso)

    cur.execute('select * from ger_app')
    apps = cur.fetchall()

    cur.execute('select * from ger_modulo')
    modulos = cur.fetchall()

    cur.execute('select * from ger_parametro')
    parametros = cur.fetchall()

    cur.execute('select valor from ger_parametro where descricao = "USA_PRECO_TIPO_HOSPEDE"')
    precohospede = cur.fetchone()

    cur.execute('select valor from ger_parametro where descricao = "USA_PRECO_TIPO_QUARTO"')
    precoquarto = cur.fetchone()

    print(precohospede)

    cur.execute('select * from ger_perfil')
    perfis = cur.fetchall()

    cur.execute('select * from ger_usuario')
    usuarios = cur.fetchall()

    cur.execute('select * from ger_log order by id_log desc limit 200')
    logs = cur.fetchall()

    cur.execute('select * from rsv_tipohospede')
    tipohospede = cur.fetchall()

    cur.execute('select * from rsv_tipoquarto')
    tipoquarto = cur.fetchall()

    cur.execute('select * from rsv_servico')
    servicos = cur.fetchall()

    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('configuracoes.html', apps=apps, modulos=modulos, parametros=parametros,
                           perfis=perfis, logs=logs, tipohospede=tipohospede, tipoquarto=tipoquarto,
                           usuarios=usuarios, servicos=servicos, mes_atual=mes_atual, ano_atual=ano_atual,
                           precohospede=precohospede, precoquarto=precoquarto)


@app.route('/financeiro')
@login_required
def financeiro():

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 0)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    cur.execute('select * from fin_pagamento order by 1 desc')
    pagamentos = cur.fetchall()

    cur.execute('select * from fin_formapagto')
    formas = cur.fetchall()

    cur.execute('select * from fin_cancelamento order by 1 desc')
    cancelamentos = cur.fetchall()

    cur.execute('select * from fin_condpagto')
    condicoes = cur.fetchall()

    cur.execute('select * from fin_estorno order by 1 desc')
    estornos = cur.fetchall()

    cur.execute('select * from ger_log order by id_log desc limit 200')
    logs = cur.fetchall()

    conn.close()

    hoje = datetime.date.today()

    mes_atual, ano_atual = hoje.month, hoje.year

    return render_template('financeiro.html', estornos=estornos, pagamentos=pagamentos, formas=formas,
                           condicoes=condicoes, cancelamentos=cancelamentos, logs=logs, mes_atual=mes_atual,
                           ano_atual=ano_atual)


@app.post('/atualiza_modulo')
@login_required
def atualiza_modulo():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 21)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_modulo = request.form.get('id_modulo')
    nivelacesso = request.form.get('nivelacesso')

    cur.execute('select * from ger_modulo where id_modulo = %s', (id_modulo,))
    modulo = cur.fetchone()

    cur.execute('update ger_modulo set nivelacesso = %s where id_modulo = %s', (nivelacesso, id_modulo,))

    conn.commit()

    grava_log(f'alteado nivel de acesso do modulo {modulo["descricao"]} de {modulo["nivelacesso"]} para {nivelacesso}',
              'admin', 21)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_perfil')
@login_required
def atualiza_perfil():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 18)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_perfil = request.form.get('id_perfil')
    nivelacesso = request.form.get('nivelacesso')

    cur.execute('select * from ger_perfil where id_perfil = %s', (id_perfil,))
    perfil = cur.fetchone()

    cur.execute('update ger_perfil set nivelacesso = %s where id_perfil = %s', (nivelacesso, id_perfil,))

    conn.commit()

    grava_log(f'alteado nivel de acesso do perfil {perfil["descricao"]} de {perfil["nivelacesso"]} para {nivelacesso}',
              'admin', 18)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_servico')
@login_required
def atualiza_servico():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 15)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_servico = request.form.get('id_servico')
    valor = request.form.get('valor')

    cur.execute('select * from rsv_servico where id_servico = %s', (id_servico,))
    servico = cur.fetchone()

    cur.execute('update rsv_servico set valor = %s where id_servico = %s', (valor, id_servico,))

    conn.commit()

    grava_log(f'alteado valor do serviço {servico["descricao"]} de {servico["valor"]} para {valor}',
              'admin', 15)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_parametro')
@login_required
def atualiza_parametro():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 22)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_parametro = request.form.get('id_parametro')
    valor = request.form.get('valor')

    cur.execute('select * from ger_parametro where id_parametro = %s', (id_parametro,))
    parametro = cur.fetchone()

    cur.execute('update ger_parametro set valor = %s where id_parametro = %s', (valor, id_parametro,))

    conn.commit()

    grava_log(f'alterado parâmetro {parametro["descricao"]} de {parametro["valor"]} para {valor}',
              'admin', 18)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_usuario')
@login_required
def atualiza_usuario():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 19)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_usuario = request.form.get('id_usuario')
    id_perfil = request.form.get('id_perfil')
    nivelacesso = request.form.get('nivelacesso')

    cur.execute('select * from ger_usuario where id_usuario = %s', (id_usuario,))
    usuario = cur.fetchone()

    lista_alterados = []

    if int(id_perfil) != int(usuario['id_perfil']):
        lista_alterados.append({
            'campo': 'id_perfil',
            'novo': id_perfil,
            'antigo': usuario['id_perfil']
        })
    if int(nivelacesso) != int(usuario['nivelacesso']):
        lista_alterados.append({
            'campo': 'nivelacesso',
            'novo': nivelacesso,
            'antigo': usuario['nivelacesso']
        })

    cur.execute('update ger_usuario set id_perfil = %s, nivelacesso = %s where id_usuario = %s',
                (id_perfil, nivelacesso, id_usuario,))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado campo {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'para o usuario {usuario["nome"]} id: {usuario["id_usuario"]}', 'admin', 19)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_app')
@login_required
def atualiza_app():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 1 , 20)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_app = request.form.get('id_app')
    nivelacesso = request.form.get('nivelacesso')

    cur.execute('select * from ger_app where id_app = %s', (id_app,))
    aplicacao = cur.fetchone()


    cur.execute('update ger_app set nivelacesso = %s where id_app = %s', (nivelacesso, id_app,))

    conn.commit()

    grava_log(f'alteado nivel de acesso do app {aplicacao["descricao"]} de {aplicacao["nivelacesso"]} para {nivelacesso}',
              'admin', 20)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_tipohospede')
@login_required
def atualiza_tipohospede():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 7)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_tipohospede = request.form.get('id_tipohospede')
    perdesconto = request.form.get('perdesconto')
    valordesconto = request.form.get('valordesconto')
    valordiaria = request.form.get('valordiaria')
    status = request.form.get('status')

    cur.execute('select * from rsv_tipohospede where id_tipohospede = %s', (id_tipohospede,))
    tipo = cur.fetchone()

    lista_alterados = []

    if float(perdesconto) != float(tipo['perdesconto']):
        lista_alterados.append({
            'campo': '% desconto',
            'novo': perdesconto,
            'antigo': tipo['perdesconto']
        })
    if float(valordesconto) != float(tipo['valordesconto']):
        lista_alterados.append({
            'campo': 'R$ desconto',
            'novo': valordesconto,
            'antigo': tipo['valordesconto']
        })
    if status != tipo['status']:
        lista_alterados.append({
            'campo': 'status',
            'novo': status,
            'antigo': tipo['status']
        })
    if valordiaria != tipo['valordiaria']:
        lista_alterados.append({
            'campo': 'valordiaria',
            'novo': valordiaria,
            'antigo': tipo['valordiaria']
        })

    cur.execute('update rsv_tipohospede set perdesconto = %s, valordesconto = %s, valordiaria = %s, '
                'status = %s where id_tipohospede = %s',
                (perdesconto, valordesconto, valordiaria, status, id_tipohospede,))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado campo {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'para o tipo hospede {tipo["descricao"]} id: {tipo["id_tipohospede"]}', 'admin', 7)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/atualiza_tipoquarto')
@login_required
def atualiza_tipoquarto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 14)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_tipoquarto= request.form.get('id_tipoquarto')
    perdesconto = request.form.get('perdesconto')
    valordesconto = request.form.get('valordesconto')
    valordiaria = request.form.get('valordiaria')
    maxhospedes = request.form.get('maxhospedes')
    status = request.form.get('status')

    cur.execute('select * from rsv_tipoquarto where id_tipoquarto = %s', (id_tipoquarto,))
    tipo = cur.fetchone()

    lista_alterados = []

    if float(perdesconto) != float(tipo['perdesconto']):
        lista_alterados.append({
            'campo': '% desconto',
            'novo': perdesconto,
            'antigo': tipo['perdesconto']
        })
    if float(valordesconto) != float(tipo['valordesconto']):
        lista_alterados.append({
            'campo': 'R$ desconto',
            'novo': valordesconto,
            'antigo': tipo['valordesconto']
        })
    if status != tipo['status']:
        lista_alterados.append({
            'campo': 'status',
            'novo': status,
            'antigo': tipo['status']
        })
    if int(maxhospedes) != int(tipo['maxhospedes']):
        lista_alterados.append({
            'campo': 'maxhospedes',
            'novo': maxhospedes,
            'antigo': tipo['maxhospedes']
        })
    if valordiaria != tipo['valordiaria']:
        lista_alterados.append({
            'campo': 'valordiaria',
            'novo': valordiaria,
            'antigo': tipo['valordiaria']
        })

    cur.execute('update rsv_tipoquarto set perdesconto = %s, valordesconto = %s, valordiaria = %s, '
                'status = %s, maxhospedes = %s where id_tipoquarto = %s',
                (perdesconto, valordesconto, valordiaria, status, maxhospedes, id_tipoquarto,))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado campo {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'para o tipo quarto {tipo["descricao"]} id: {tipo["id_tipoquarto"]}', 'admin', 14)

    conn.close()

    return redirect(url_for('configuracoes'))


@app.post('/cria_reserva')
@login_required
def cria_reserva():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 11)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação para criar reservas. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    id_quarto = request.form.get('id_quarto')
    nroquarto = request.form.get('nroquarto')
    id_hospede = request.form.get('id_hospede')
    datacheckin = request.form.get('datacheckin')
    datacheckout = request.form.get('datacheckout')
    dp1 = int(request.form.get('dependente1') if request.form.get('dependente1') else 0)
    dp2 = int(request.form.get('dependente2') if request.form.get('dependente2') else 0)
    dp3 = int(request.form.get('dependente3') if request.form.get('dependente3') else 0)
    dp4 = int(request.form.get('dependente4') if request.form.get('dependente4') else 0)
    dp5 = int(request.form.get('dependente5') if request.form.get('dependente5') else 0)
    dp6 = int(request.form.get('dependente6') if request.form.get('dependente6') else 0)
    usuariocriacao = 'admin'
    datacriacao = datetime.datetime.now()
    origem_reserva = int(request.form.get('origem'))
    dependentes = []

    if dp1 > 0:
        dependentes.append(dp1)
    if dp2 > 0:
        dependentes.append(dp2)
    if dp3 > 0:
        dependentes.append(dp3)
    if dp4 > 0:
        dependentes.append(dp4)
    if dp5 > 0:
        dependentes.append(dp5)
    if dp6 > 0:
        dependentes.append(dp6)

    if nroquarto is None:
        cur.execute('select nroquarto, capacidade, id_tipoquarto from rsv_quarto where id_quarto = %s', (id_quarto,))
        quarto = cur.fetchone()
        nroquarto = quarto['nroquarto']

    cur.execute('select maxhospedes as capacidade from rsv_tipoquarto where id_tipoquarto = %s',
                (quarto['id_tipoquarto'],))
    diaria_tipoquarto = cur.fetchone()

    cur.execute('select * from rsv_reserva where id_quarto = %s '
                'and ((datacheckin between %s and %s) or (nvl(datacheckoutreal, datacheckout) between %s and %s ))',
                (id_quarto, datacheckin, datacheckout, datacheckin, datacheckout))
    reserva = cur.fetchall()

    if len(reserva) > 0:
        flash('Já existe uma reserva para esse quarto na data selecionada', 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto', id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede', id_hospede=id_hospede))

    cur.execute('select * from rsv_hospedagem where id_quarto = %s and status = %s '
                'and ((%s between datacheckin and datacheckout) or ( %s between datacheckin and datacheckout ))',
                (id_quarto, 'A', datacheckin, datacheckout))
    reserva = cur.fetchall()

    print(f'DEBUG RESERVA: {reserva}, {datacheckin}, {datacheckout}, {id_quarto}')

    if len(reserva) > 0:
        flash('Existe uma Hospedagem me andamento para esse quarto na data selecionada', 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto', id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede', id_hospede=id_hospede))

    cur.execute('select * from rsv_reserva where id_hospede = %s '
                'and ((datacheckin between %s and %s) or (datacheckout between %s and %s ))',
                (id_hospede, datacheckin, datacheckout, datacheckin, datacheckout))
    reserva = cur.fetchall()

    if len(reserva) > 0:
        flash('Já existe uma reserva para esse hospede na data selecionada', 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto', id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede', id_hospede=id_hospede))

    capacidade = int(diaria_tipoquarto['capacidade']) if int(diaria_tipoquarto['capacidade']) > 0 else int(
        quarto['capacidade'])

    if len(dependentes) + 1 > capacidade:
        flash('Não é possível criar a reserva, capacidade do quarto insuficiente' , 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto' , id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede' , id_hospede=id_hospede))

    cur.execute('insert into rsv_reserva(id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, '
                'datacriacao, status, id_hotel) values(%s, %s, %s, %s, %s, %s, %s, %s)',
                (id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, datacriacao,
                 'A', 1))

    cur.execute('select id_reserva from rsv_reserva where id_reserva = LAST_INSERT_ID()')
    novo_id_reserva = cur.fetchone()
    print(novo_id_reserva['id_reserva'])

    for dependente in dependentes:
        cur.execute('insert into rsv_reservadependente(id_reserva, id_dependente) values(%s, %s)',
                    (novo_id_reserva['id_reserva'], dependente,))

    conn.commit()
    cur.execute('select nome from rsv_hospede where id_hospede = %s', (id_hospede,))
    nome_hospede = cur.fetchone()

    conn.close()

    grava_log(f'Reserva criada com sucesso. quarto {nroquarto}, hospede {nome_hospede["nome"]}, '
              f'checkin {datacheckin}, checkout {datacheckout}', 'admin', 11)

    flash(f'reserva criada com sucesso. Quarto {nroquarto}, hospede {nome_hospede["nome"]}', 'info')

    if origem_reserva == 1:
        return redirect(url_for('quarto', id_quarto=id_quarto))
    elif origem_reserva == 2:
        return redirect(url_for('hospede', id_hospede=id_hospede))


@app.post('/cria_hospedagem')
@login_required
def cria_hospedagem():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 13)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    id_quarto = request.form.get('id_quarto')
    nroquarto = request.form.get('nroquarto')
    id_hospede = request.form.get('id_hospede')
    id_reserva = request.form.get('id_reserva')
    datacheckout = request.form.get('datacheckout')
    dp1 = int(request.form.get('dependente1') if request.form.get('dependente1') else 0)
    dp2 = int(request.form.get('dependente2') if request.form.get('dependente2') else 0)
    dp3 = int(request.form.get('dependente3') if request.form.get('dependente3') else 0)
    dp4 = int(request.form.get('dependente4') if request.form.get('dependente4') else 0)
    dp5 = int(request.form.get('dependente5') if request.form.get('dependente5') else 0)
    dp6 = int(request.form.get('dependente6') if request.form.get('dependente6') else 0)
    usuariocriacao = 'admin'
    datacriacao = datetime.datetime.now()
    origem_reserva = int(request.form.get('origem'))
    valordesconto_hospede = 0.0
    perdesconto_hospede = 0.0
    valordesconto_quarto = 0.0
    perdesconto_quarto = 0.0
    datacheckin = datetime.datetime.now()
    datacheckin = datacheckin.strftime('%Y-%m-%d')
    dependentes = []

    if dp1 > 0:
        dependentes.append(dp1)
    if dp2 > 0:
        dependentes.append(dp2)
    if dp3 > 0:
        dependentes.append(dp3)
    if dp4 > 0:
        dependentes.append(dp4)
    if dp5 > 0:
        dependentes.append(dp5)
    if dp6 > 0:
        dependentes.append(dp6)


    if nroquarto is None:
        cur.execute('select nroquarto from rsv_quarto where id_quarto = %s', (id_quarto,))
        quarto = cur.fetchone()
        nroquarto = quarto['nroquarto']

    #verifica reserva
    cur.execute('select * from rsv_reserva where id_reserva = %s and id_quarto = %s and id_hospede = %s and status = %s',
                (id_reserva, id_quarto, id_hospede, 'A'))
    reserva = cur.fetchone()

    if len(reserva if reserva != None else '') > 0:
        cur.execute('update rsv_reserva set status = %s where id_reserva = %s and id_quarto = %s and id_hospede = %s',
                    ('H', id_reserva, id_quarto, id_hospede))

    # busca dados do quarto
    cur.execute('select id_quarto, nroquarto, valordiaria, id_tipoquarto, capacidade '
                'from rsv_quarto where id_quarto = %s', (id_quarto,))
    quarto = cur.fetchone()

    # busca dados do tipo do quarto
    cur.execute('select perdesconto, valordesconto from rsv_tipoquarto where id_tipoquarto = %s',
                (quarto['id_tipoquarto'],))
    tipoquarto = cur.fetchone()

    # busca dados do hospede
    cur.execute('select id_hospede, nome, id_tipohospede from rsv_hospede where id_hospede = %s',
                (id_hospede,))
    hospede = cur.fetchone()

    # busca parametrizacao do tipo hospede
    cur.execute('select perdesconto, valordesconto from rsv_tipohospede where id_tipohospede = %s',
                (hospede['id_tipohospede'],))
    tipohospede = cur.fetchone()

    # busca parametros para o calculo do valor da diaria
    cur.execute('select id_parametro, descricao, valor from ger_parametro '
                'WHERE descricao in (%s, %s)', ('USA_DESCONTO_HOSPEDE', 'USA_DESCONTO_QUARTO',))
    parametros = cur.fetchall()

    for parametro in parametros:
        if parametro['descricao'] == 'USA_DESCONTO_HOSPEDE' and parametro['valor'] == 'S':
            valordesconto_hospede = tipohospede['valordesconto']
            perdesconto_hospede = tipohospede['perdesconto']

        if parametro['descricao'] == 'USA_DESCONTO_QUARTO' and parametro['valor'] == 'S':
            valordesconto_quarto = tipoquarto['valordesconto']
            perdesconto_quarto = tipoquarto['perdesconto']

    d1 = datetime.datetime.strptime(datacheckin, '%Y-%m-%d')
    d2 = datetime.datetime.strptime(datacheckout, '%Y-%m-%d')

    delta = d2 - d1
    diarias = delta.days + datetime.timedelta(days=1).days

    valor_diaria = 0

    cur.execute('select valordiaria, maxhospedes as capacidade from rsv_tipoquarto where id_tipoquarto = %s' ,
                (hospedagem['id_tipoquarto'] ,))
    diaria_tipoquarto = cur.fetchone()

    cur.execute('select valordiaria from rsv_tipohospede where id_tipohospede = %s' ,
                (hospedagem['id_tipohospede'] ,))
    diaria_tipohospede = cur.fetchone()

    cur.execute('select id_parametro, descricao, valor from ger_parametro '
                'WHERE descricao in (%s, %s)' , ('USA_PRECO_TIPO_QUARTO' , 'USA_PRECO_TIPO_HOSPEDE' ,))
    parametros = cur.fetchall()

    diaria_tipohospede = float(diaria_tipohospede['valordiaria']) if diaria_tipohospede['valordiaria'] else 0
    diaria_tipoquarto = float(diaria_tipoquarto['valordiaria']) if diaria_tipoquarto['valordiaria'] else 0

    usa_preco_hospede = 'N'
    usa_preco_quarto = 'N'

    for parametro in parametros:
        if parametro['descricao'] == 'USA_PRECO_TIPO_HOSPEDE':
            usa_preco_hospede = parametro['valor']
        elif parametro['descricao'] == 'USA_PRECO_TIPO_QUARTO':
            usa_preco_quarto = parametro['valor']

    if usa_preco_hospede == 'S' and diaria_tipohospede > 0:
        valor_diaria = diaria_tipohospede
    elif usa_preco_quarto == 'S' and diaria_tipoquarto > 0:
        valor_diaria = diaria_tipoquarto
    else:
        valor_diaria = hospedagem['valor']

    valortotal = diarias * valor_diaria

    valordesconto = 0.0
    if perdesconto_hospede > 0:
        valordesconto = valortotal * (perdesconto_hospede / 100)
        valortotal -= valordesconto
    elif perdesconto_quarto > 0:
        valordesconto = valortotal * (perdesconto_quarto / 100)
        valortotal -= valordesconto
    elif valordesconto_hospede > 0:
        valordesconto = valordesconto_hospede
        valortotal -= valordesconto
        if valortotal < 0:
            valortotal = 0.0
    elif valordesconto_quarto > 0:
        valordesconto = valordesconto_quarto
        valortotal -= valordesconto
        if valortotal < 0:
            valortotal = 0.0

    cur.execute('select * from rsv_reserva where id_quarto = %s and status = %s '
                'and ((datacheckin between %s and %s) or (datacheckout between %s and %s ))',
                (id_quarto, 'A', datacheckin, datacheckout, datacheckin, datacheckout))
    reserva = cur.fetchall()

    print(f'RESERVA: {reserva}')
    print(f'DATAS: {datacheckin} {datacheckout}')

    capacidade = int(diaria_tipoquarto['capacidade']) \
        if int(diaria_tipoquarto['capacidade']) > 0 \
        else int(quarto['capacidade'])

    if len(dependentes) + 1 > capacidade:
        flash('Não é possível hospedar, capacidade do quarto insuficiente' , 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto' , id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede' , id_hospede=id_hospede))

    if len(reserva) > 0:
        flash('Não é possível hospedar, existe uma reserva em espera para esse quarto na data selecionada', 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto', id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede', id_hospede=id_hospede))

    cur.execute('select * from rsv_reserva where id_hospede = %s and status not in (%s, %s) '
                'and ((%s between datacheckin and nvl(datacheckoutreal, datacheckout)) '
                'or (%s between datacheckin and nvl(datacheckoutreal,datacheckout)))',
                (id_hospede, 'C', 'F', datacheckin, datacheckout))
    reserva = cur.fetchall()

    print(reserva)

    if len(reserva) > 0:
        flash('Esse Hospede tem uma reserva pendente entre essas datas, verifique', 'danger')
        conn.close()
        if origem_reserva == 1:
            return redirect(url_for('quarto', id_quarto=id_quarto))
        elif origem_reserva == 2:
            return redirect(url_for('hospede', id_hospede=id_hospede))
    else:
        cur.execute('insert into rsv_reserva(id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, '
                    'datacriacao, status, id_hotel) values(%s, %s, %s, %s, %s, %s, %s, %s)',
                    (id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, datacriacao,
                     'H', 1))

        # conn.commit()

        cur.execute('select id_reserva from rsv_reserva where id_reserva = LAST_INSERT_ID()')
        novo_id_reserva = cur.fetchone()
        print(novo_id_reserva['id_reserva'])
        print(id_reserva)

    cur.execute('insert into rsv_hospedagem(id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, '
                'datacriacao, status, id_hotel, dias, valordiaria, valordesconto, valortotal, ocupacao, id_reserva) '
                'values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (id_quarto, id_hospede, datacheckin, datacheckout, usuariocriacao, datacriacao,
                 'A', 1, diarias, quarto['valordiaria'], valordesconto, valortotal, 1,
                 id_reserva if int(id_reserva) > 0 else novo_id_reserva['id_reserva']))

    cur.execute('select id_hospedagem from rsv_hospedagem where id_hospedagem = LAST_INSERT_ID()')
    novo_id_hospedagem = cur.fetchone()
    print(novo_id_hospedagem['id_hospedagem'])

    cur.execute('update rsv_quarto set status = %s where id_quarto = %s', ('O', id_quarto))

    for dependente in dependentes:
        cur.execute('insert into rsv_hospdependente(id_hospedagem, id_dependente) values(%s, %s)',
                    (novo_id_hospedagem['id_hospedagem'], dependente,))

    conn.commit()
    cur.execute('select nome from rsv_hospede where id_hospede = %s', (id_hospede,))
    nome_hospede = cur.fetchone()

    conn.close()

    grava_log(f'Hospedagem criada com sucesso. quarto {nroquarto}, hospede {nome_hospede["nome"]}, '
              f'checkin {datacheckin}, checkout {datacheckout}', 'admin', 13)

    flash(f'Hospedagem criada com sucesso. Quarto {nroquarto}, hospede {nome_hospede["nome"]}', 'info')

    if origem_reserva == 1:
        return redirect(url_for('quarto', id_quarto=id_quarto))
    elif origem_reserva == 2:
        return redirect(url_for('hospede', id_hospede=id_hospede))


@app.route('/hospedagem/<int:id_hospedagem>')
@login_required
def hospedagem(id_hospedagem):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'], 2, 13)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    cur.execute('select a.*, b.nroquarto, c.nome from rsv_hospedagem a '
                'inner join rsv_quarto b on a.id_quarto = b.id_quarto '
                'inner join rsv_hospede c on a.id_hospede = c.id_hospede '
                'where id_hospedagem = %s', (id_hospedagem,))
    hospedagem = cur.fetchone()

    hoje = datetime.datetime.today()

    cur.execute('select a.id_servicohospedagem, a.descricao, a.quantidade, a.valor as valortotal '
                'from rsv_servicohospedagem a '
                'where a.id_hospedagem = %s',
                (id_hospedagem,))
    servicos = cur.fetchall()

    cur.execute('select * from rsv_servico')
    lista_servico = cur.fetchall()

    cur.execute('select id_reserva from rsv_hospedagem where id_hospedagem = %s', (id_hospedagem,))
    id_reserva = cur.fetchone()

    cur.execute('select id_pagamento from fin_pagamento where id_hospedagem = %s', (id_hospedagem,))
    pagamento = cur.fetchone()

    cur.execute('select a.* from rsv_dependente a inner join rsv_hospdependente b '
                'on a.id_dependente = b.id_dependente inner join rsv_hospedagem c '
                'on c.id_hospedagem = b.id_hospedagem where c.id_hospedagem = %s' , (id_hospedagem,))
    dependentes = cur.fetchall()

    id_reserva = id_reserva['id_reserva']
    if id_reserva == None:
        id_reserva = 0

    conn.close()

    return render_template('hospedagem.html', hospedagem=hospedagem, hoje=hoje, servicos=servicos,
                           lista_servico=lista_servico, id_reserva=id_reserva, pagamento=pagamento, dependentes=dependentes)


@app.route('/reserva/<int:id_reserva>')
@login_required
def reserva(id_reserva):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 11)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    cur.execute('select a.*, b.nroquarto, c.nome, b.valordiaria as valor, b.id_tipoquarto, c.id_tipohospede from rsv_reserva a '
                'inner join rsv_quarto b on a.id_quarto = b.id_quarto '
                'inner join rsv_hospede c on a.id_hospede = c.id_hospede '
                'where id_reserva = %s', (id_reserva,))
    hospedagem = cur.fetchone()

    cur.execute('select id_dependente from rsv_reservadependente where id_reserva = %s',
                (id_reserva,))
    dp_reserva = cur.fetchall()

    if len(dp_reserva) < 6:
        for i in range(0, 6 - len(dp_reserva)):
            dp_reserva.append({'id_dependente': 0})

    hoje = datetime.datetime.today()
    data_minima_reserva = datetime.datetime.today() + datetime.timedelta(days=1)

    d1 = datetime.datetime.strftime(hospedagem['datacheckin'], '%Y-%m-%d')
    d2 = datetime.datetime.strftime(hospedagem['datacheckout'], '%Y-%m-%d')

    dt1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
    dt2 = datetime.datetime.strptime(d2, '%Y-%m-%d')

    cur.execute('select id_hospedagem from rsv_hospedagem where id_reserva = %s', (id_reserva,))
    id_hospedagem = cur.fetchone()

    if id_hospedagem == None:
        id_hospedagem = 0
    else:
        id_hospedagem = id_hospedagem['id_hospedagem']

    print(id_hospedagem)

    status_reserva = ''
    if hospedagem['status'] == 'A':
        status_reserva = 'Agendada'
    elif hospedagem['status'] == 'C':
        status_reserva = 'Cancelada'
    elif hospedagem['status'] == 'H':
        status_reserva = 'Finalizada'

    delta = dt2 - dt1
    diarias = delta.days + datetime.timedelta(days=1).days

    cur.execute('select a.id_servicohospedagem, a.descricao, a.quantidade, a.valor as valortotal '
                'from rsv_servicohospedagem a '
                'where a.id_hospedagem = %s',
                (id_reserva,))
    servicos = cur.fetchall()

    cur.execute('select a.* from rsv_dependente a inner join rsv_reservadependente b '
                'on a.id_dependente = b.id_dependente inner join rsv_reserva c '
                'on c.id_reserva = b.id_reserva where c.id_reserva = %s' , (id_reserva ,))
    dependentes = cur.fetchall()

    cur.execute('select * from rsv_servico')
    lista_servico = cur.fetchall()

    valor_diaria = 0

    cur.execute('select valordiaria from rsv_tipoquarto where id_tipoquarto = %s' ,
                (hospedagem['id_tipoquarto'],))
    diaria_tipoquarto = cur.fetchone()

    cur.execute('select valordiaria from rsv_tipohospede where id_tipohospede = %s' ,
                (hospedagem['id_tipohospede'],))
    diaria_tipohospede = cur.fetchone()

    cur.execute('select id_parametro, descricao, valor from ger_parametro '
                'WHERE descricao in (%s, %s)', ('USA_PRECO_TIPO_QUARTO', 'USA_PRECO_TIPO_HOSPEDE',))
    parametros = cur.fetchall()

    diaria_tipohospede = float(diaria_tipohospede['valordiaria']) if diaria_tipohospede['valordiaria'] else 0
    diaria_tipoquarto = float(diaria_tipoquarto['valordiaria']) if diaria_tipoquarto['valordiaria'] else 0

    usa_preco_hospede = 'N'
    usa_preco_quarto = 'N'

    for parametro in parametros:
        if parametro['descricao'] == 'USA_PRECO_TIPO_HOSPEDE':
            usa_preco_hospede = parametro['valor']
        elif parametro['descricao'] == 'USA_PRECO_TIPO_QUARTO':
            usa_preco_quarto = parametro['valor']

    if usa_preco_hospede == 'S' and diaria_tipohospede > 0:
        valor_diaria = diaria_tipohospede
    elif usa_preco_quarto == 'S' and diaria_tipoquarto > 0:
        valor_diaria = diaria_tipoquarto
    else:
        valor_diaria = hospedagem['valor']

    conn.close()

    return render_template('reserva.html', hospedagem=hospedagem, hoje=hoje, servicos=servicos,
                           lista_servico=lista_servico, diarias=diarias,
                           data_minima_reserva=data_minima_reserva, status_reserva=status_reserva,
                           id_hospedagem=id_hospedagem, dp_reserva=dp_reserva, dependentes=dependentes,
                           valor_diaria=valor_diaria)


@app.post('/add_servico_hospedagem')
@login_required
def add_servico_hospedagem():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 15)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('index'))

    id_hospedagem = request.form.get('id_hospedagem')
    id_servico = request.form.get('id_servico')
    quantidade = request.form.get('quantidade')
    cur.execute('select descricao, valor from rsv_servico where id_servico = %s', (id_servico,))
    servico = cur.fetchone()

    cur.execute('insert into rsv_servicohospedagem(id_hospedagem, id_servico, '
                'quantidade, valor, descricao) '
                'values(%s, %s, %s, %s, %s)', (id_hospedagem, id_servico, quantidade,
                                           int(quantidade) * float(servico['valor']), servico['descricao']))

    conn.commit()

    conn.close()

    grava_log(f'servico {servico["descricao"]} adicionada a hospedagem {id_hospedagem}, qtd: {quantidade}', 'admin', 13)

    return redirect(url_for('hospedagem', id_hospedagem=id_hospedagem))


@app.post('/exclui_servico')
@login_required
def exclui_servico():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 15)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_servicohospedagem = request.form.get('id_servicohospedagem')

    cur.execute('select * from rsv_servicohospedagem where id_servicohospedagem = %s',
                (id_servicohospedagem,))
    servico = cur.fetchone()

    id_hospedagem = servico["id_hospedagem"]

    cur.execute('delete from rsv_servicohospedagem where id_servicohospedagem = %s',
                (id_servicohospedagem,))

    conn.commit()

    conn.close()
    grava_log(f'servico {servico["descricao"]} no valor de R${servico["valor"]} excluída da hospedagem '
              f'{servico["id_hospedagem"]}', 'admin', 15)

    flash(f'servico {servico["descricao"]} no valor de R${servico["valor"]} excluído', 'info')

    return redirect(url_for('hospedagem', id_hospedagem=id_hospedagem))


@app.post('/checkout')
@login_required
def checkout():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 13)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_hospedagem = request.form.get('id_hospedagem')

    cur.execute('select * from rsv_hospedagem where id_hospedagem = %s', (id_hospedagem,))
    hospedagem = cur.fetchone()

    # busca dados do quarto
    cur.execute('select id_quarto, nroquarto, valordiaria, id_tipoquarto '
                'from rsv_quarto where id_quarto = %s', (hospedagem['id_quarto'],))
    quarto = cur.fetchone()

    # busca dados do tipo do quarto
    cur.execute('select perdesconto, valordesconto from rsv_tipoquarto where id_tipoquarto = %s',
                (quarto['id_tipoquarto'],))
    tipoquarto = cur.fetchone()

    # busca dados do hospede
    cur.execute('select id_hospede, nome, id_tipohospede from rsv_hospede where id_hospede = %s',
                (hospedagem['id_hospede'],))
    hospede = cur.fetchone()

    # busca parametrizacao do tipo hospede
    cur.execute('select perdesconto, valordesconto from rsv_tipohospede where id_tipohospede = %s',
                (hospede['id_tipohospede'],))
    tipohospede = cur.fetchone()

    d1 = datetime.datetime.strptime(datetime.datetime.strftime(hospedagem['datacheckin'], '%Y-%m-%d'), '%Y-%m-%d')
    d2 = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')

    delta = d2 - d1
    diarias = delta.days + datetime.timedelta(days=1).days

    cur.execute('select * from rsv_servicohospedagem where id_hospedagem = %s', (id_hospedagem,))
    servicos = cur.fetchall()

    valor_hospedagem = hospedagem['valordiaria'] * diarias
    valordesconto_hospede = 0.00
    perdesconto_hospede = 0.00
    valordesconto_quarto = 0.00
    perdesconto_quarto = 0.00

    # busca parametros para o calculo do valor da diaria
    cur.execute('select id_parametro, valor from ger_parametro WHERE id_parametro in (%s, %s)', (4, 5,))
    parametros = cur.fetchall()

    for parametro in parametros:
        if parametro['id_parametro'] == 4 and parametro['valor'] == 'S':
            valordesconto_hospede = tipohospede['valordesconto']
            perdesconto_hospede = tipohospede['perdesconto']

        if parametro['id_parametro'] == 5 and parametro['valor'] == 'S':
            valordesconto_quarto = tipoquarto['valordesconto']
            perdesconto_quarto = tipoquarto['perdesconto']

    valordesconto = 0.0
    if perdesconto_hospede > 0:
        valordesconto = valor_hospedagem * (perdesconto_hospede / 100)
        valor_hospedagem -= valordesconto
    elif perdesconto_quarto > 0:
        valordesconto = valor_hospedagem * (perdesconto_quarto / 100)
        valor_hospedagem -= valordesconto
    elif valordesconto_hospede > 0:
        valordesconto = valordesconto_hospede
        valor_hospedagem -= valordesconto
        if valor_hospedagem < 0:
            valor_hospedagem = 0.0
    elif valordesconto_quarto > 0:
        valordesconto = valordesconto_quarto
        valor_hospedagem -= valordesconto
        if valor_hospedagem < 0:
            valor_hospedagem = 0.0

    valor_servicos = 0.0
    for servico in servicos:
        valor_servicos += servico['valor']

    cur.execute('insert into fin_pagamento(id_hospedagem, datageracao, status, usuariocriacao, '
                'valortotal, valorservico, valordesconto, valorbruto, valorliquido, id_hotel) '
                'values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (id_hospedagem, datetime.datetime.now(), 'A', 'admin', valor_hospedagem,
                 valor_servicos, valordesconto, float(valor_hospedagem) + float(valor_servicos) + float(valordesconto),
                 float(valor_hospedagem) + float(valor_servicos), 1,))

    cur.execute('update rsv_hospedagem set status = %s, datacheckout = %s, '
                'valordesconto = %s, valortotal = %s where id_hospedagem = %s',
                ('P', datetime.datetime.now(), valordesconto, valor_hospedagem, id_hospedagem,))

    cur.execute('update rsv_quarto set status = %s where id_quarto= %s',
                ('L', hospedagem['id_quarto'],))

    cur.execute('update rsv_reserva set datacheckoutreal = %s, status = %s where id_reserva = %s',
                (datetime.datetime.now(), 'F', hospedagem['id_reserva'],))

    conn.commit()

    grava_log(f'checkout da hospedagem {id_hospedagem} realizado com sucesso, '
              f'dados gerado para pagamento no financeiro', 'admin', 13)

    flash('checkout realizado com sucesso', 'info')

    return redirect(url_for('hospedagem', id_hospedagem=id_hospedagem))


@app.post('/cancela_reserva')
@login_required
def cancela_reserva():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 2 , 12)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('configuracoes'))

    id_reserva = request.form.get('id_reserva')

    cur.execute('select * from rsv_reserva where id_reserva = %s', (id_reserva,))
    reserva = cur.fetchone()

    cur.execute('update rsv_reserva set status = %s where id_reserva = %s',
                ('C', id_reserva,))

    conn.commit()

    grava_log(f'Cancelamento da Reserva {id_reserva} realizado com sucesso', 'admin', 11)

    flash('Cancelamento de reserva realizado com sucesso', 'info')

    return redirect(url_for('reserva', id_reserva=id_reserva))


@app.route('/pagamento/<int:id_pagamento>')
@login_required
def pagamento(id_pagamento):
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 1)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))

    # parametros
    cur.execute('select id_parametro, descricao, valor from ger_parametro where id_modulo = 3')
    parametros = cur.fetchall()

    permite_estorno = ''
    permite_cancelar = ''

    for parametro in parametros:
        if parametro['descricao'] == 'PERMITE_ESTORNO':
            permite_estorno = parametro['valor']
        elif parametro['descricao'] == 'PERMITE_CANCELAR':
            permite_cancelar = parametro['valor']

    cur.execute('select * from fin_pagamento where id_pagamento = %s', (id_pagamento,))
    pagamento = cur.fetchone()

    cur.execute('select * from fin_formapagto where status = %s', ('A',))
    formas = cur.fetchall()

    cur.execute('select * from fin_condpagto where status = %s', ('A',))
    condicoes = cur.fetchall()

    cur.execute('select * from rsv_hospedagem where id_hospedagem = %s', (pagamento['id_hospedagem'],))
    hospedagem = cur.fetchone()

    cur.execute('select nome from rsv_hospede where id_hospede = %s', (hospedagem['id_hospede'],))
    pagador = cur.fetchone()

    cur.execute('select * from rsv_servicohospedagem where id_hospedagem = %s', (hospedagem['id_hospedagem'],))
    servicos = cur.fetchall()

    hoje = datetime.datetime.today()

    valor_servicos = 0.0
    for servico in servicos:
        valor_servicos += servico['valor']

    conn.close()

    return render_template('pagamento.html', pagamento=pagamento, hospedagem=hospedagem,
                           servicos=servicos, valor_servicos=valor_servicos, pagador=pagador,
                           hoje=hoje, formas=formas, condicoes=condicoes, permite_estorno=permite_estorno,
                           permite_cancelar=permite_cancelar)


@app.post('/baixa_pagamento')
@login_required
def baixa_pagamento():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 1)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))

    id_pagamento = request.form.get('id_pagamento')
    forma = request.form.get('forma')
    cond = request.form.get('cond')

    cur.execute('select parcelas from fin_condpagto where id_condpagto = %s', (cond,))
    condicao = cur.fetchone()

    cur.execute('update fin_pagamento set status = %s, id_formapagto = %s, id_condpagto = %s, dataalteracao = %s, '
                'usuarioalteracao = %s, parcela = %s where id_pagamento = %s',
                ('Q', forma, cond, datetime.datetime.now(), 'admin', condicao['parcelas'], id_pagamento,))

    conn.commit()

    flash(f'pagamento {id_pagamento} baixado com sucesso!', 'info')

    conn.close()

    grava_log(f'pagamento {id_pagamento} confirmado (baixado)', 'admin', 1)

    return redirect(url_for('pagamento', id_pagamento=id_pagamento))


@app.post('/estorna_pagamento')
@login_required
def estorna_pagamento():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 2)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    id_pagamento = request.form.get('id_pagamento')
    motivo = request.form.get('motivo')

    cur.execute('select * from fin_pagamento where id_pagamento = %s', (id_pagamento,))
    pagamento = cur.fetchone()

    cur.execute('update fin_pagamento set status = %s where id_pagamento = %s', ('A', id_pagamento,))

    cur.execute('insert into fin_estorno(id_pagamento, dataestorno, usuarioestorno, motivo, valorliquido, '
                'valorbruto, valordesconto) values(%s, %s, %s, %s, %s, %s, %s)',
                (id_pagamento, datetime.datetime.now(), 'admin', motivo, pagamento['valorliquido'],
                 pagamento['valorbruto'], pagamento['valordesconto']))

    conn.commit()

    grava_log(f'pagamento {id_pagamento} estornado', 'admin', 2)

    flash(f'pagamento {id_pagamento} estornado', 'info')

    return redirect(url_for('pagamento', id_pagamento=id_pagamento))


@app.post('/cancela_pagamento')
@login_required
def cancela_pagamento():

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 5)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    id_pagamento = request.form.get('id_pagamento')
    motivo = request.form.get('motivo')

    cur.execute('update fin_pagamento set status = %s, datacancelamento = %s, usuariocancelamento = %s'
                ' where id_pagamento = %s', ('C', datetime.datetime.now(), 'admin', id_pagamento,))

    cur.execute('insert into fin_cancelamento(id_pagamento, datacancelamento, usuariocancelamento, motivo) '
                'values(%s, %s, %s, %s)',
                (id_pagamento, datetime.datetime.now(), 'admin', motivo,))

    conn.commit()

    grava_log(f'pagamento {id_pagamento} cancelado', 'admin', 5)

    flash(f'pagamento {id_pagamento} cancelado', 'info')

    return redirect(url_for('pagamento', id_pagamento=id_pagamento))


@app.post('/cadastra_forma_pagto')
@login_required
def cadastra_forma_pagto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 3)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    descricao = request.form.get('descricao')
    perdesconto = request.form.get('perdesconto')
    pertaxa = request.form.get('pertaxa')

    # verifica se já existe a forma
    cur.execute('select * from fin_formapagto where lower(descricao) = %s', (descricao.lower(),))
    forma = cur.fetchall()

    print(forma)

    if len(forma) > 0:
        flash(f'Forma de pagamento {descricao} já está cadastrada. Verifique.', 'info')
        conn.close()
        return redirect(url_for('financeiro'))

    cur.execute('insert into fin_formapagto(descricao, perdesconto, pertaxa, datacriacao, usuariocriacao, '
                'id_hotel, status) '
                'values(%s, %s, %s, %s, %s, %s, %s)',
                (descricao, perdesconto, pertaxa, datetime.datetime.now(), 'admin', 1, 'A',))

    conn.commit()

    grava_log(f'forma de pagamento {descricao} criada', 'admin', 3)

    flash(f'forma de pagamento {descricao} criada', 'info')

    conn.close()

    return redirect(url_for('financeiro'))


@app.post('/cadastra_condicao_pagto')
@login_required
def cadastra_condicao_pagto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 4)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    descricao = request.form.get('descricao')
    perdesconto = request.form.get('perdesconto')
    pertaxa = request.form.get('pertaxa')
    parcelas = request.form.get('parcelas')

    # verifica se já existe a forma
    cur.execute('select * from fin_condpagto where lower(descricao) = %s', (descricao.lower(),))
    cond = cur.fetchall()

    if len(cond) > 0:
        flash(f'Forma de pagamento {descricao} já está cadastrada. Verifique.', 'info')
        conn.close()
        return redirect(url_for('financeiro'))

    cur.execute('insert into fin_condpagto(descricao, perdesconto, pertaxa, parcelas, datacriacao, usuariocriacao, '
                'id_hotel, status) '
                'values(%s, %s, %s, %s, %s, %s, %s, %s)',
                (descricao, perdesconto, pertaxa, parcelas, datetime.datetime.now(), 'admin', 1, 'A',))

    conn.commit()

    grava_log(f'condição de pagamento {descricao} criada', 'admin', 3)

    flash(f'condição de pagamento {descricao} criada', 'info')

    conn.close()

    return redirect(url_for('financeiro'))


@app.post('/atualiza_condicao_pagto')
@login_required
def atualiza_condicao_pagto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 4)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    id_condpagto = request.form.get('id_condpagto')
    perdesconto = request.form.get('perdesconto')
    pertaxa = request.form.get('pertaxa')
    parcelas = request.form.get('parcelas')
    status = request.form.get('status')

    cur.execute('select * from fin_condpagto where id_condpagto = %s', (id_condpagto,))
    cond = cur.fetchone()

    print(cond)

    lista_alterados = []

    if float(perdesconto) != float(cond['perdesconto'] if cond['perdesconto'] is not None else 0):
        lista_alterados.append({
            'campo': 'perdesconto',
            'novo': perdesconto,
            'antigo': cond['perdesconto']
        })
    if float(pertaxa) != float(cond['pertaxa']):
        lista_alterados.append({
            'campo': 'pertaxa',
            'novo': pertaxa,
            'antigo': cond['pertaxa']
        })
    if int(parcelas) != int(cond['parcelas']):
        lista_alterados.append({
            'campo': 'parcelas',
            'novo': parcelas,
            'antigo': cond['parcelas']
        })
    if status != cond['status']:
        lista_alterados.append({
            'campo': 'status',
            'novo': status,
            'antigo': cond['status']
        })

    cur.execute('update fin_condpagto set perdesconto = %s, pertaxa = %s, parcelas = %s, status = %s, '
                'dataalteracao = %s, usuarioalteracao = %s where id_condpagto = %s',
                (perdesconto, pertaxa, parcelas, status, datetime.datetime.now(), 'admin', id_condpagto,))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'na condição de pagamento {cond["descricao"]}', 'admin', 3)

    conn.close()

    return redirect(url_for('financeiro'))


@app.post('/atualiza_forma_pagto')
@login_required
def atualiza_forma_pagto():
    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    # validação de nível de acesso do usuário
    acesso = valida_permissao(session['id_usuario'] , 3 , 3)
    if not acesso: 
        conn.close()
        flash('usuário sem acesso a aplicação. Verifique o nível de acesso' , 'info')
        return redirect(url_for('financeiro'))
    
    id_formapagto = request.form.get('id_formapagto')
    perdesconto = request.form.get('perdesconto')
    pertaxa = request.form.get('pertaxa')
    status = request.form.get('status')

    cur.execute('select * from fin_formapagto where id_formapagto = %s', (id_formapagto,))
    forma = cur.fetchone()

    lista_alterados = []

    if float(perdesconto) != float(forma['perdesconto'] if forma['perdesconto'] is not None else 0):
        lista_alterados.append({
            'campo': 'perdesconto',
            'novo': perdesconto,
            'antigo': forma['perdesconto']
        })
    if float(pertaxa) != float(forma['pertaxa']):
        lista_alterados.append({
            'campo': 'pertaxa',
            'novo': pertaxa,
            'antigo': forma['pertaxa']
        })
    if status != forma['status']:
        lista_alterados.append({
            'campo': 'status',
            'novo': status,
            'antigo': forma['status']
        })

    cur.execute('update fin_formapagto set perdesconto = %s, pertaxa = %s, status = %s, '
                'dataalteracao = %s, usuarioalteracao = %s where id_formapagto = %s',
                (perdesconto, pertaxa, status, datetime.datetime.now(), 'admin', id_formapagto,))

    conn.commit()

    for alteracao in lista_alterados:
        grava_log(f'alterado {alteracao["campo"]} de {alteracao["antigo"]} para {alteracao["novo"]} '
                  f'na forma de pagamento {forma["descricao"]}', 'admin', 3)

    conn.close()

    return redirect(url_for('financeiro'))


@app.route('/calendario/<int:mes>/<int:ano>')
@login_required
def calendario(mes, ano):

    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    dados = list()

    c = Calendar()

    for dia in [x for x in c.itermonthdates(ano, mes) if x.month == mes]:
        dados.append(dia)

    dias_mes = len(dados)

    primeiro_dia_semana = dados[0].weekday()

    print(primeiro_dia_semana)

    dias = []

    conn = conecta_bd()
    cur = conn.cursor(dictionary=True)

    cur.execute('select a.id_reserva, b.nome, c.nroquarto, a.datacheckin, a.datacheckout '
                'from rsv_reserva a inner join rsv_hospede b on a.id_hospede = b.id_hospede '
                'inner join rsv_quarto c on a.id_quarto = c.id_quarto '
                'where ((month(a.datacheckin) = %s and year(a.datacheckin) = %s) '
                'or (month(a.datacheckout) = %s and year(a.datacheckout) = %s)) and '
                'a.status <> %s', (mes, ano, mes, ano, 'C',))

    reservas = cur.fetchall()

    print(reservas)

    for i in range(42):
        dias.append([i - (primeiro_dia_semana - 1)])

    # dias[0:primeiro_dia_semana] = [0]
    # dias[dados[0].weekday()] = ['primeiro dia']

    for i in range(primeiro_dia_semana):
        dias[i] = [0]

    print(dias)

    for dia in dias:
        if dia[0] > dias_mes:
            dia[0] = 0
        print(dia)

    mes_ant = meses[mes - 2]
    mes_pos = meses[mes] if mes < 12 else meses[0]

    index_dia = dias.index([1])

    for reserva in reservas:
        # mais de um dia de reserva no mesmo mês:
        if ((reserva['datacheckin'].day != reserva['datacheckout'].day) and
                reserva['datacheckin'].month == reserva['datacheckout'].month):
            intervalo = reserva['datacheckout'].day - reserva['datacheckin'].day
            for i in range(intervalo + 1):
                dias[(reserva['datacheckin'].day + (index_dia - 1)) + i].append({
                    'nome': reserva['nome'],
                    'quarto': reserva['nroquarto'],
                    'id_reserva': reserva['id_reserva'] if reserva['id_reserva'] else 0
                })
        # Reservas que viram de um mês para outro
        elif reserva['datacheckin'].month != reserva['datacheckout'].month:
            # tratamento para mês anterior
            if reserva['datacheckin'].month < mes:
                intervalo = reserva['datacheckout'].day
                print('AQUI')
                print(intervalo)
                for i in range(intervalo):
                    dias[index_dia + i].append({
                        'nome': reserva['nome'],
                        'quarto': reserva['nroquarto'],
                        'id_reserva': reserva['id_reserva'] if reserva['id_reserva'] else 0
                    })
            # tratamento para mês atual
            else:
                intervalo = dias_mes - reserva['datacheckin'].day
                for i in range(intervalo + 1):
                    dias[reserva['datacheckin'].day + index_dia - 1 + i].append({
                        'nome': reserva['nome'],
                        'quarto': reserva['nroquarto'],
                        'id_reserva': reserva['id_reserva'] if reserva['id_reserva'] else 0
                    })
        else:
            dias[reserva['datacheckin'].day + (index_dia - 1)].append({
                'nome': reserva['nome'],
                'quarto': reserva['nroquarto'],
                'id_reserva': reserva['id_reserva'] if reserva['id_reserva'] else 0
            })

    conn.close()

    return render_template('calendario.html', primeiro_dia_semana=primeiro_dia_semana,
                           dias=dias, mes=mes, mes_atual=meses[mes - 1], mes_ant=mes_ant, mes_pos=mes_pos,
                           ano=ano, ano_ant=ano - 1 if mes == 1 else ano, ano_pos=ano if mes < 12 else ano + 1)

