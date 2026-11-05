import os
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configurações de Segurança e Banco de Dados
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-desenvolvimento-socorro-santos')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///socorro_santos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELAGEM DE DADOS (ORM SQLAlchemy)
# ==========================================

class ServicoEspecializado(db.Model):
    __tablename__ = 'servicos_especializados'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(120), nullable=False, unique=True)
    descricao_curta = db.Column(db.String(255), nullable=False)
    modalidade = db.Column(db.String(50), nullable=False)  # Presencial, Online, Híbrido
    publico_alvo = db.Column(db.String(100), nullable=False)
    status_ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    contatos = db.relationship('ContatoTriagem', backref='servico_rel', lazy=True)

class ContatoTriagem(db.Model):
    __tablename__ = 'contatos_triagem'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome_responsavel = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    perfil_paciente = db.Column(db.String(50), nullable=False)  # Criança, Adolescente, Adulto
    servico_interesse_id = db.Column(db.Integer, db.ForeignKey('servicos_especializados.id'), nullable=False)
    mensagem_inicial = db.Column(db.Text, nullable=True)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(30), default='Pendente', nullable=False)

# ==========================================
# ROTAS E REGRAS DE NEGÓCIO
# ==========================================

@app.route('/')
def index():
    # Consulta serviços ativos no banco SQLite
    servicos = ServicoEspecializado.query.filter_by(status_ativo=True).all()
    return render_template('index.html', servicos=servicos)

@app.route('/api/triagem', methods=['POST'])
def registrar_triagem():
    try:
        data = request.form if request.form else request.get_json()
        
        nome = data.get('nome_responsavel', '').strip()
        email = data.get('email', '').strip()
        telefone = data.get('telefone', '').strip()
        perfil = data.get('perfil_paciente', '').strip()
        servico_id = data.get('servico_interesse_id')
        mensagem = data.get('mensagem_inicial', '').strip()

        # Validações no Servidor (OWASP RNF02)
        if not nome or not email or not telefone or not perfil or not servico_id:
            return jsonify({'sucesso': False, 'erro': 'Todos os campos obrigatórios devem ser preenchidos.'}), 400

        # Validação sintática de E-mail
        padrao_email = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(padrao_email, email):
            return jsonify({'sucesso': False, 'erro': 'Informe um e-mail com formato válido.'}), 400

        # Gravação no Banco de Dados
        novo_contato = ContatoTriagem(
            nome_responsavel=nome,
            email=email,
            telefone=telefone,
            perfil_paciente=perfil,
            servico_interesse_id=int(servico_id),
            mensagem_inicial=mensagem,
            status='Pendente'
        )
        
        db.session.add(novo_contato)
        db.session.commit()

        # Recupera o título do serviço selecionado
        servico = ServicoEspecializado.query.get(servico_id)
        nome_servico = servico.titulo if servico else "Atendimento Especializado"

        # Constrói o link formatado para o WhatsApp de Socorro Santos
        texto_whatsapp = (
            f"Olá Socorro Santos! Me chamo *{nome}* e acabei de solicitar uma triagem pelo site.\n\n"
            f"• *Perfil:* {perfil}\n"
            f"• *Serviço de Interesse:* {nome_servico}\n"
            f"• *E-mail:* {email}\n"
            f"• *Telefone:* {telefone}\n"
        )
        if mensagem:
            texto_whatsapp += f"• *Observação:* {mensagem}\n"

        # Número fictício para direcionamento
        numero_whatsapp = "5561999998888" 
        link_whatsapp = f"https://api.whatsapp.com/send?phone={numero_whatsapp}&text={re.sub(' ', '%20', texto_whatsapp)}"

        return jsonify({
            'sucesso': True,
            'mensagem': 'Triagem gravada com sucesso!',
            'nome_responsavel': nome,
            'servico_nome': nome_servico,
            'link_whatsapp': link_whatsapp
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': 'Erro interno ao processar a solicitação.'}), 500

# Popula o banco com os serviços iniciais caso esteja vazio
def inicializar_banco():
    with app.app_context():
        db.create_all()
        if ServicoEspecializado.query.count() == 0:
            servico1 = ServicoEspecializado(
                titulo="Avaliação Neuropsicopedagógica",
                descricao_curta="Investigação técnica completa para identificação de Altas Habilidades / Superdotação e dupla excepcionalidade.",
                modalidade="Presencial e Online",
                publico_alvo="Crianças, Adolescentes e Adultos"
            )
            servico2 = ServicoEspecializado(
                titulo="Orientação Parental e Escolar",
                descricao_curta="Diretrizes práticas para adequação curricular, acolhimento familiar e direitos pedagógicos.",
                modalidade="Online",
                publico_alvo="Pais e Educadores"
            )
            db.session.add_all([servico1, servico2])
            db.session.commit()

if __name__ == '__main__':
    inicializar_banco()
    app.run(debug=True, host='0.0.0.0', port=5000)