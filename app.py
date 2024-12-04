import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required

from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from cinema import create_app, db
from cinema.models import Usuario, Filme, Cinema, Alimento, Sala, Sessao, CompraAlimento, CompraSessao, Carrinho, AssentoComprado

from functools import wraps


app = create_app()

# Configuração de sessão permanente
app.permanent_session_lifetime = timedelta(days=7)


def login_required(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Você precisa estar logado para acessar esta página.", "warning")
            return redirect(url_for('login')) # Redireciona para login se não estiver logado
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('is_admin') is not True:
            flash("Acesso restrito para administradores.", "danger")
            return redirect(url_for('perfil')) # Redireciona para a página inicial se não for admin
        return f(*args, **kwargs)
    return decorated_function


# Página inicial
@app.route('/')
def inicio():
    return render_template('Inicio.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Verifica se o usuário já está logado
    if current_user.is_authenticated:
        return redirect(url_for('logado'))  # Redireciona para a página logada, se já estiver logado

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()  # Verifica se o e-mail já está registrado

        if usuario and check_password_hash(usuario.senha, senha):  # Compara a senha
            login_user(usuario)  # Usa o login_user do Flask-Login
            return redirect(url_for('logado'))
        else:
            flash("Credenciais inválidas. Tente novamente.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    logout_user()  # Encerra a sessão do usuário
    return redirect(url_for('login'))


#logado
@app.route('/logado')
@login_required
def logado():
    return render_template('logado.html')


# Cadastro 
@app.route('/cadastrar-se', methods=['GET', 'POST'])
def criar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        data_nascimento_str = request.form['data_nascimento']

        if Usuario.query.filter_by(email=email).first(): # Verifica se o e-mail já está registrado
            flash("E-mail já registrado. Tente outro.", "warning") # Retorna se o e-mail já existe
            return redirect(url_for('criar_usuario'))

        is_admin = email == 'sofiarodriguessilva2@gmail.com' # Define o admin com base no email
        data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
        senha_hash = generate_password_hash(senha)
        novo_usuario = Usuario(nome, email, senha_hash, data_nascimento, is_admin)

        db.session.add(novo_usuario) # Adiciona o novo usuário ao banco de dados
        db.session.commit() #atualiza o banco de dados
        flash("Cadastro realizado com sucesso! Faça login para continuar.", "success")
        return redirect(url_for('login'))
    return render_template('criarUsuario.html')

# Perfil
@app.route('/perfil')
@login_required
def perfil():
    usuario = current_user  # Obtém o usuário atual
    return render_template('perfil.html', usuario=current_user)

# Mostrar todos os usuarios, caso o usuario seja admin
@app.route('/usuarios')
@login_required
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('listarUsuarios.html', usuarios=usuarios)

# Deletar usuário
@app.route('/deletar_usuario', methods=['GET', 'POST'])
@login_required
def deletar_usuario():
    usuario_atual = Usuario.query.get(current_user.id)

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            flash("E-mail não encontrado.", "danger")
            return redirect(url_for('deletar_usuario'))

        if usuario.id != usuario_atual.id:
            flash("Não é permitido deletar a conta de outro usuário.", "danger")
            return redirect(url_for('deletar_usuario'))

        if check_password_hash(usuario.senha, senha):
            db.session.delete(usuario)
            db.session.commit()
            flash("Conta deletada com sucesso.", "success")
            return redirect(url_for('inicio'))
        else:
            flash("Senha incorreta.", "danger")
            return redirect(url_for('deletar_usuario'))

    return render_template('deletarUsuario.html')



# Atualizar usuário
@app.route('/usuario/atualizar', methods=['GET', 'POST'])
@login_required
def atualizar_usuario():
    usuario = Usuario.query.get(current_user.id)

    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        senha_nova = request.form['senha_nova']
        novo_email = request.form['email']

        if not check_password_hash(usuario.senha, senha_atual):
            flash("Senha atual incorreta.", "danger")
            return redirect(url_for('atualizar_usuario'))

        if novo_email != usuario.email and Usuario.query.filter_by(email=novo_email).first():
            flash("Este e-mail já está registrado.", "warning")
            return redirect(url_for('atualizar_usuario'))

        usuario.nome = request.form['nome']
        usuario.email = novo_email
        usuario.senha = generate_password_hash(senha_nova)
        usuario.data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date()

        db.session.commit()
        flash("Dados atualizados com sucesso.", "success")
        return redirect(url_for('perfil'))

    return render_template('atualizarUsuario.html', usuario=usuario)

#Filmes
@app.route('/gerenciar_filmes')
@login_required
@admin_required
def gerenciar_filmes():
    filmes = Filme.query.all()  # Busca todos os filmes cadastrados
    return render_template('filmes.html', filmes=filmes)

#Adicionar os filmes
@app.route('/adicionar_filmes', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_filmes():
    if request.method == 'POST':
        titulo = request.form['titulo']
        duracao = request.form['duracao']
        classificacao = request.form['classificacao']
        genero = request.form['genero']
        data_lancamento = datetime.strptime(request.form['data_lancamento'], '%Y-%m-%d')
        foto = request.files['foto']

        # Verifica se a foto foi enviada
        if foto:
            foto_filename = secure_filename(foto.filename)
            foto.save(os.path.join('cinema', 'static', 'img', 'uploads', foto_filename))
        else:
            foto_filename = None

        novo_filme = Filme(titulo=titulo, duracao=duracao, classificacao=classificacao, genero=genero, data_lancamento=data_lancamento, foto=foto_filename)

        try:
            db.session.add(novo_filme)
            db.session.commit()
            flash('Filme adicionado com sucesso!', 'success')
            return redirect(url_for('adicionar_filmes'))
        except Exception as e:
            db.session.rollback()
            flash('Ocorreu um erro ao adicionar o filme. Tente novamente.', 'danger')

    return render_template('criarFilme.html')

#listar todos os filmes
@app.route('/listar_filmes', methods=['GET'])
@login_required
def listar_filmes():
    filmes = Filme.query.all()  # Recupera todos os filmes no banco de dados
    return render_template('listar_filmes.html', filmes=filmes)  # Renderiza a página e passa os filmes para o template

#deletar filme
@app.route('/deletar_filme', methods=['GET', 'POST'])
@login_required
@admin_required
def deletar_filme():
    if request.method == 'POST':
        nome_filme = request.form['nome_filme'] #pede o nome do filme
        senha_admin = request.form['senha_admin'] #pede a senha

        filme = Filme.query.filter_by(titulo=nome_filme).first()# Busca o filme pelo nome
        if not filme:
            flash("Filme não encontrado.", "warning")
            return redirect(url_for('deletar_filme'))

        admin = Usuario.query.get(current_user.id) # Verifica se a senha do admin está correta
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('deletar_filme'))

        try:
            db.session.delete(filme) #deleta o filme
            db.session.commit()#atualiza o banco de dados
            flash("Filme deletado com sucesso.", "success")
            return redirect(url_for('listar_filmes'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao deletar o filme. Tente novamente.", "danger")
    
    return render_template('deletar_filme.html')


#atualizar dados do filme
@app.route('/atualizar_filme', methods=['GET', 'POST'])
@login_required
@admin_required
def atualizar_filme():
    
    usuario = current_user  # Certifique-se de definir a variável 'usuario'
    if request.method == 'POST':
        nome_filme = request.form['nome_filme']  # Nome do filme a ser atualizado
        senha_admin = request.form['senha_admin']  # Senha do admin

        # Busca o filme pelo nome
        filme = Filme.query.filter_by(titulo=nome_filme).first()
        if not filme:
            flash("Filme não encontrado.", "warning")
            return redirect(url_for('atualizar_filme'))

        # Verifica a senha do admin
        admin = Usuario.query.get(current_user.id)
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('atualizar_filme'))

        # Atualiza os dados do filme
        filme.titulo = request.form['titulo']
        filme.duracao = request.form['duracao']
        filme.classificacao = request.form['classificacao']
        filme.genero = request.form['genero']
        filme.data_lancamento = datetime.strptime(request.form['data_lancamento'], '%Y-%m-%d')

        # Processa a nova foto, se enviada
        foto = request.files['foto']
        if foto:
            foto_filename = secure_filename(foto.filename)
            foto.save(os.path.join('cinema', 'static', 'img', 'uploads', foto_filename))
            filme.foto = foto_filename

        try:
            db.session.commit()  # Salva as mudanças no banco de dados
            flash('Filme atualizado com sucesso!', 'success')
            return redirect(url_for('gerenciar_filmes'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar o filme. Tente novamente.', 'danger')

    return render_template('atualizar_filme.html', usuario=usuario)


#cinema
@app.route('/gerenciar_cinemas')
@login_required
@admin_required
def gerenciar_cinemas():
    cinema = Cinema.query.all()  # Busca todos os filmes cadastrados
    return render_template('cinemas.html', cinema=cinema)

#Adicionar cinema
@app.route('/adicionar_cinema', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_cinema():
    if request.method == 'POST':
        nome = request.form['nome']
        local = request.form['local']
        capacidade = request.form['capacidade']

        novo_cinema = Cinema(nome=nome, local=local, capacidade=capacidade)

        try:
            db.session.add(novo_cinema)
            db.session.commit()
            flash('Cinema adicionado com sucesso!', 'success')
            return redirect(url_for('adicionar_cinema'))
        except Exception as e:
            db.session.rollback()
            flash('Ocorreu um erro ao adicionar o cinema. Tente novamente.', 'danger')

    return render_template('adicionar_cinema.html')

#atualizar dados do filme
@app.route('/atualizar_cinema', methods=['GET', 'POST'])
@login_required
@admin_required
def atualizar_cinema():
    if request.method == 'POST':
        nome_cinema = request.form['nome_cinema']  # Nome do filme a ser atualizado
        senha_admin = request.form['senha_admin']  # Senha do admin

        # Busca o filme pelo nome
        cinema = Cinema.query.filter_by(nome=nome_cinema).first()
        if not cinema:
            flash("Cinema não encontrado.", "warning")
            return redirect(url_for('atualizar_cinema'))

        # Verifica a senha do admin
        admin = Usuario.query.get(current_user.id)
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('atualizar_filme'))

        # Atualiza os dados do filme
        cinema.nome = request.form['nome']
        cinema.local = request.form['local']
        cinema.capacidade = request.form['capacidade']

        try:
            db.session.commit()  # Salva as mudanças no banco de dados
            flash('Cinema atualizado com sucesso!', 'success')
            return redirect(url_for('gerenciar_cinemas'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar o cinema. Tente novamente.', 'danger')

    return render_template('atualizar_cinema.html')

#deleta o cinema
@app.route('/deletar_cinema', methods=['GET', 'POST'])
@login_required
@admin_required
def deletar_cinema():
    if request.method == 'POST':
        nome_cinema = request.form['nome_cinema'] #pede o nome do filme
        senha_admin = request.form['senha_admin'] #pede a senha

        cinema = Cinema.query.filter_by(nome=nome_cinema).first()# Busca o filme pelo nome
        if not cinema:
            flash("Filme não encontrado.", "warning")
            return redirect(url_for('deletar_cinema'))

        admin = Usuario.query.get(current_user.id) # Verifica se a senha do admin está correta
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('deletar_cinema'))

        try:
            db.session.delete(cinema) #deleta o filme
            db.session.commit()#atualiza o banco de dados
            flash("Cinema deletado com sucesso.", "success")
            return redirect(url_for('gerenciar_cinemas'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao deletar o cinema. Tente novamente.", "danger")
    
    return render_template('deletarCinema.html')


#salas
@app.route('/gerenciar_salas')
@login_required
@admin_required
def gerenciar_salas():
    salas = Sala.query.all()  # Busca todas as salas cadastradas
    return render_template('salas.html', salas=salas)  # Tabela de Salas

#Adicionar sala
@app.route('/adicionar_sala', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_sala():
    if request.method == 'POST':
        numero = request.form['numero']
        capacidade = request.form['capacidade']
        cinema_id = request.form['cinema_id']  # Captura o ID do cinema selecionado

        nova_sala = Sala(numero=numero, capacidade=capacidade, cinema_id=cinema_id)

        try:
            db.session.add(nova_sala)
            db.session.commit()
            flash('Sala adicionada com sucesso!', 'success')
            return redirect(url_for('gerenciar_salas'))  # Redireciona para a lista de salas
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao adicionar a sala: {e}', 'danger')

    # Recupera os cinemas existentes para exibição no formulário
    cinemas = Cinema.query.all()
    return render_template('adicionar_sala.html', cinemas=cinemas)

#atualizar salas
@app.route('/atualizar_sala', methods=['GET', 'POST'])
@login_required
@admin_required
def atualizar_sala():
    if request.method == 'POST':
        numero_sala = request.form['numero_sala']
        senha_admin = request.form['senha_admin']

        # Busca o filme pelo nome
        sala = Sala.query.filter_by(numero=numero_sala).first()
        if not sala:
            flash("Sala não encontrada.", "warning")
            return redirect(url_for('atualizar_sala'))

        # Verifica a senha do admin
        admin = Usuario.query.get(current_user.id)
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('atualizar_filme'))

        # Atualiza os dados do filme
        sala.numero = request.form['novo_numero']
        sala.capacidade = request.form['nova_capacidade']

        try:
            db.session.commit()  # Salva as mudanças no banco de dados
            flash('Sala atualizada com sucesso!', 'success')
            return redirect(url_for('gerenciar_salas'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar a sala. Tente novamente.', 'danger')

    return render_template('atualizar_sala.html')

#deletar sala
@app.route('/deletar_sala', methods=['GET', 'POST'])
@login_required
@admin_required
def deletar_sala():
    if request.method == 'POST':
        numero_sala = request.form['numero_sala'] #pede o nome do filme
        senha_admin = request.form['senha_admin'] #pede a senha

        sala = Sala.query.filter_by(numero=numero_sala).first()# Busca o filme pelo nome
        if not sala:
            flash("Sala não encontrada.", "warning")
            return redirect(url_for('deletar_sala'))

        admin = Usuario.query.get(current_user.id) # Verifica se a senha do admin está correta
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('deletar_sala'))

        try:
            db.session.delete(sala) #deleta o filme
            db.session.commit()#atualiza o banco de dados
            flash("Sala deletada com sucesso.", "success")
            return redirect(url_for('gerenciar_salas'))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao deletar a sala. Tente novamente.", "danger")
    
    return render_template('deletarSala.html')


#sessões
@app.route('/gerenciar_sessoes')
@login_required
@admin_required
def gerenciar_sessoes():
    sessao = Sessao.query.all()  # Busca todas as sessoes cadastradas
    return render_template('sessao.html', sessao=sessao)  # Tabela de sessoes

@app.route('/sessoes')
@login_required
def ver_Sessoes():
    sessao = Sessao.query.all()  # Busca todas as sessoes cadastradas
    return render_template('listar_sessoes.html', sessao=sessao)  # Tabela de sessoes

#adicionar sessoes
@app.route('/adicionar_sessao', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_sessao():
    if request.method == 'POST':
        filme_id = request.form['filme_id']  # ID do filme selecionado
        sala_id = request.form['sala_id']  # ID da sala selecionada
        horario = request.form['horario']  # Horário da sessão
        preco = request.form['preco']  # Preço do ingresso

        horario = datetime.strptime(horario, "%Y-%m-%dT%H:%M")
        nova_sessao = Sessao(filme_id=filme_id, sala_id=sala_id, horario=horario, preco=preco) # Cria uma nova sessão

        try:
            db.session.add(nova_sessao)
            db.session.commit()
            flash('Sessão adicionada com sucesso!', 'success')
            return redirect(url_for('gerenciar_sessoes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao adicionar a sessão: {e}', 'danger')

    filmes = Filme.query.all() # Busca filmes e salas disponíveis para o formulário
    salas = Sala.query.all()

    return render_template('adicionar_sessao.html', filmes=filmes, salas=salas)

#atualizar sessao
@app.route('/atualizar_sessao', methods=['GET', 'POST'])
@login_required
@admin_required
def atualizar_sessao():
    if request.method == 'POST':
        nome_filme = request.form['nome_filme']
        horario = request.form['horario']

        try:
            horario = datetime.strptime(horario, "%Y-%m-%dT%H:%M")
            sessao = Sessao.query.join(Filme).filter(Filme.titulo == nome_filme, Sessao.horario == horario).first()# Busca a sessão pelo nome do filme e horário

            if not sessao:
                flash('Sessão não encontrada.', 'warning')
                return redirect(url_for('gerenciar_sessoes'))

            # Atualiza os dados da sessão
            sessao.filme_id = request.form['filme_id']
            sessao.sala_id = request.form['sala_id']
            sessao.preco = float(request.form['preco'])

            db.session.commit()
            flash('Sessão atualizada com sucesso!', 'success')
            return redirect(url_for('gerenciar_sessoes'))

        except ValueError:
            flash('Formato inválido para data/hora ou preço.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao atualizar a sessão: {e}', 'danger')

    else:
        sessao_id = request.args.get('id')
        if sessao_id:
            sessao = Sessao.query.get(sessao_id)
            if sessao:
                sessao.horario_formatado = sessao.horario.strftime('%Y-%m-%dT%H:%M')  # Formata ao horario
            else:
                flash("Sessão não encontrada.", "warning")
                return redirect(url_for('gerenciar_sessoes'))
        else:
            sessao = None
    
    filmes = Filme.query.all()# Busca filmes e salas para exibir no formulário
    salas = Sala.query.all()

    return render_template('atualizar_sessao.html', filmes=filmes, salas=salas, sessao=sessao)

#deletar sessao
@app.route('/deletar_sessao', methods=['GET', 'POST'])
@login_required
@admin_required
def deletar_sessao():
    if request.method == 'POST':
        nome_filme = request.form['nome_filme']
        horario_str = request.form['horario']

        try:
            horario = datetime.strptime(horario_str, "%Y-%m-%dT%H:%M")# Converte a string de horário para datetime
            # Busca a sessão pelo nome do filme e horário
            sessao = Sessao.query.join(Filme).filter(Filme.titulo == nome_filme, Sessao.horario == horario).first()

            if not sessao:
                flash('Sessão não encontrada.', 'warning')
                return redirect(url_for('gerenciar_sessoes'))

            # Deleta a sessão
            db.session.delete(sessao)
            db.session.commit()
            flash('Sessão deletada com sucesso!', 'success')
            return redirect(url_for('gerenciar_sessoes'))

        except ValueError:
            flash('Formato inválido para data/hora.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao deletar a sessão: {e}', 'danger')

    filmes = Filme.query.all()
    return render_template('deletarSessao.html', filmes=filmes)


#Alimentos
@app.route('/gerenciar_alimentos')
@login_required
@admin_required
def gerenciar_alimentos():
    alimentos = Alimento.query.all()  # Busca todas as salas cadastradas
    return render_template('alimento.html', alimentos=alimentos)  # Tabela de Salas

@app.route('/alimentos')
@login_required
def ver_alimentos():
    carrinho = Carrinho.query.filter_by(usuario_id=current_user.id).first()
    alimentos = Alimento.query.all()  # Busca todas as sessoes cadastradas
    return render_template('listar_alimentos.html', alimentos=alimentos, carrinho=carrinho)  # Tabela de sessoes

#adicionar alimentos
@app.route('/adicionar_alimentos', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_alimentos():
    if request.method == 'POST':
        nome = request.form['nome']
        preco = request.form['preco']  
        tipoDeAlimentos = request.form['tipoDeAlimentos']

        novo_alimento = Alimento(nome=nome, preco=preco, tipoDeAlimentos=tipoDeAlimentos) # Cria um novo alimento

        try:
            db.session.add(novo_alimento)
            db.session.commit()
            flash('Alimento adicionada com sucesso!', 'success')
            return redirect(url_for('gerenciar_alimentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao adicionar o alimento: {e}', 'danger')

    return render_template('adicionar_alimento.html')

#atualizar alimento
@app.route('/atualizar_alimentos', methods=['GET', 'POST'])
@login_required
@admin_required
def atualizar_alimentos():
    if request.method == 'POST':
        nome = request.form['nome']  # Nome do alimento a ser atualizado
        senha_admin = request.form['senha_admin']  # Senha do admin

        # Busca o alimento pelo nome
        alimento = Alimento.query.filter_by(nome=nome).first()
        if not alimento:
            flash("Alimento não encontrado.", "warning")
            return redirect(url_for('gerenciar_alimentos'))

        # Verifica a senha do admin
        admin = Usuario.query.get(current_user.id)
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('atualizar_alimentos'))  # Mantém na página de atualização

        # Atualiza os dados do alimento
        alimento.preco = request.form['preco']
        alimento.tipoDeAlimentos = request.form['tipoDeAlimentos']

        try:
            db.session.commit()  # Salva as mudanças no banco de dados
            flash('Alimento atualizado com sucesso!', 'success')
            return redirect(url_for('gerenciar_alimentos'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar o alimento. Tente novamente.', 'danger')

    nome_alimento = request.args.get('nome')
    alimento = Alimento.query.filter_by(nome=nome_alimento).first()

    return render_template('atualizar_alimento.html', alimento=alimento)

#deletar alimentos
@app.route('/deletar_alimentos', methods=['GET', 'POST'])
@login_required
@admin_required
def deletar_alimentos():
    if request.method == 'POST':
        nome = request.form['nome']  # Nome do alimento a ser deletado
        senha_admin = request.form['senha_admin']  # Senha do admin

        # Busca o alimento pelo nome
        alimento = Alimento.query.filter_by(nome=nome).first()
        if not alimento:
            flash("Alimento não encontrado.", "warning")
            return redirect(url_for('gerenciar_alimentos'))  # Redireciona para a página de gerenciamento

        # Verifica a senha do admin
        admin = Usuario.query.get(current_user.id)
        if not check_password_hash(admin.senha, senha_admin):
            flash("Senha incorreta. Tente novamente.", "danger")
            return redirect(url_for('deletar_alimentos'))  # Mantém na página de deleção

        # Deleta o alimento do banco de dados
        try:
            db.session.delete(alimento)
            db.session.commit()  # Confirma a deleção
            flash('Alimento deletado com sucesso!', 'success')
            return redirect(url_for('gerenciar_alimentos'))  # Redireciona para a página de gerenciamento
        except Exception as e:
            db.session.rollback()  # Caso ocorra um erro, desfaz a operação
            flash(f'Erro ao deletar o alimento: {e}', 'danger')
            return redirect(url_for('gerenciar_alimentos'))

    return render_template('deletar_alimento.html')  # Exibe o formulário de deleção

#comprar assentos
@app.route('/comprar_assento', methods=['GET', 'POST'])
@login_required
def comprar_assento():
    sessao = None  # Inicializa a variável 'sessao' para ser usada no template.

    # Captura o parâmetro 'sessao_id' da URL
    sessao_id = request.args.get('sessao_id')
    
    # Verifica se 'sessao_id' foi fornecido
    if sessao_id:
        sessao = Sessao.query.get(sessao_id)  # Busca a sessão no banco de dados

        if not sessao:
            return "Sessão não encontrada", 404

    if request.method == 'POST':
        assento = request.form['assento']  # Número do assento
        # Se a sessão foi encontrada, criamos o assento comprado
        if sessao:
            novo_item = AssentoComprado(sessao_id=sessao.id, assento=assento)
            db.session.add(novo_item)
            db.session.commit()
            return redirect(url_for('ver_carrinho'))  # Redireciona para o carrinho

    # Retorna o template com a sessão
    return render_template('comprar_assento.html', sessao=sessao)

@app.route('/ver_carrinho')
@login_required
def ver_carrinho():
    carrinho = Carrinho(usuario_id=current_user.id)
    db.session.add(carrinho)
    db.session.commit()

    # Armazena o carrinho_id na sessão
    session['carrinho_id'] = carrinho.id

    flash("Carrinho criado com sucesso!", "success")
    carrinho = Carrinho.query.filter_by(usuario_id=current_user.id).first()  # Filtra o carrinho do usuário logado
    return render_template('ver_carrinho.html', carrinho=carrinho)

@app.route('/adicionar_alimento_carrinho', methods=['GET', 'POST'])
@login_required
def adicionar_alimento_carrinho():
    carrinho = Carrinho.query.filter_by(usuario_id=current_user.id).first()
    if request.method == 'POST':
        # Verificando se o campo alimento_id existe no formulário
        if 'alimento_id' not in request.form:
            flash("O alimento não foi selecionado corretamente.", "danger")
            return redirect(url_for('adicionar_alimento_carrinho'))  # Redireciona se o campo não existir

        carrinho_id = carrinho.id if carrinho else None
        alimento_id = request.form['alimento_id']
        nome = request.form['nome']
        quantidade = int(request.form['quantidade'])
        preco_unitario = float(request.form['preco_unitario'])
        subtotal = quantidade * preco_unitario

        compra_alimento = CompraAlimento(carrinho_id=carrinho_id, alimento_id=alimento_id, nome=nome, quantidade=quantidade, preco_unitario=preco_unitario, subtotal=subtotal)

        try:
            db.session.add(compra_alimento)
            db.session.commit()
            flash("Alimento adicionado ao carrinho com sucesso!", "success")
            return redirect(url_for('ver_carrinho', carrinho_id=carrinho_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao adicionar alimento ao carrinho: {e}", "danger")
            return redirect(url_for('adicionar_alimento_carrinho'))

    alimentos = Alimento.query.all()
    return render_template('listar_alimentos.html', alimentos=alimentos, carrinho=carrinho)


@app.route('/adicionar_item_carrinho', methods=['GET', 'POST'])
@login_required
def adicionar_item_carrinho():
    # Recupera o carrinho_id da sessão
    carrinho_id = session.get('carrinho_id')

    if carrinho_id is None:
        flash("Carrinho não encontrado!", "danger")
        return redirect(url_for('criar_carrinho'))

    carrinho = Carrinho.query.get_or_404(carrinho_id)

    if request.method == 'POST':
        tipo_item = request.form['tipo_item']
        descricao = request.form['descricao']
        quantidade = int(request.form['quantidade'])
        preco_unitario = float(request.form['preco_unitario'])
        subtotal = quantidade * preco_unitario

        item_carrinho = ItemCarrinho(
            carrinho_id=carrinho.id, 
            tipo_item=tipo_item, 
            descricao=descricao, 
            quantidade=quantidade, 
            preco_unitario=preco_unitario, 
            subtotal=subtotal
        )

        try:
            db.session.add(item_carrinho)
            db.session.commit()
            flash("Item adicionado ao carrinho com sucesso!", "success")
            return redirect(url_for('ver_carrinho', carrinho_id=carrinho.id))  # Redireciona para a página do carrinho
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao adicionar item ao carrinho: {e}", "danger")
            return redirect(url_for('adicionar_item_carrinho'))

    return render_template('listar_alimentos.html')


@app.route('/remover_item_carrinho', methods=['POST'])
@login_required
def remover_item_carrinho():
    assento_a_remover = request.form['assento']  # Pegando o assento a ser removido do carrinho

    carrinho = Carrinho.query.filter_by(usuario_id=current_user.id).first()  # Pegando o carrinho do usuário
    if carrinho:
        item_a_remover = ItemCarrinho.query.filter_by(carrinho_id=carrinho.id, assento=assento_a_remover).first()
        if item_a_remover:
            db.session.delete(item_a_remover)
            db.session.commit()
            flash("Assento removido do carrinho com sucesso!", "success")
        else:
            flash("Assento não encontrado no carrinho.", "warning")
    else:
        flash("Carrinho não encontrado.", "warning")

    return redirect(url_for('ver_carrinho'))



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)
