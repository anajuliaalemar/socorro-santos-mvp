import pytest
from app import app, db, ServicoEspecializado, ContatoTriagem

@pytest.fixture
def client():
    # Configura o app em modo de teste com banco SQLite em memória
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Popula com dados de teste para os testes de integração
            servico = ServicoEspecializado(
                titulo="Avaliação Neuropsicopedagógica",
                descricao_curta="Teste de serviço",
                modalidade="Presencial",
                publico_alvo="Crianças"
            )
            db.session.add(servico)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

# ==========================================
# TESTES UNITÁRIOS E DE INTEGRAÇÃO
# ==========================================

def test_home_page(client):
    """Teste Unitário/Integração: Rota principal '/' carrega com sucesso."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Socorro Santos" in response.data

def test_criacao_servico_model(client):
    """Teste Unitário: Modelo ORM ServicoEspecializado grava no banco corretamente."""
    with app.app_context():
        servico = ServicoEspecializado.query.filter_by(titulo="Avaliação Neuropsicopedagógica").first()
        assert servico is not None
        assert servico.modalidade == "Presencial"

def test_triagem_sucesso(client):
    """Teste de Integração: Envio de formulário válido persiste e gera link WhatsApp."""
    data = {
        'nome_responsavel': 'Ana Cristina',
        'email': 'ana.cristina@email.com',
        'telefone': '(61) 99999-7777',
        'perfil_paciente': 'Criança',
        'servico_interesse_id': 1,
        'mensagem_inicial': 'Gostaria de agendar triagem'
    }
    response = client.post('/api/triagem', data=data)
    assert response.status_code == 201
    
    json_data = response.get_json()
    assert json_data['sucesso'] is True
    assert json_data['nome_responsavel'] == 'Ana Cristina'
    assert 'api.whatsapp.com' in json_data['link_whatsapp']

def test_triagem_validacao_email_invalido(client):
    """Teste de Integração/Segurança: Bloqueia e-mail malformado no servidor (OWASP)."""
    data = {
        'nome_responsavel': 'Ana Cristina',
        'email': 'email-invalido',
        'telefone': '(61) 99999-7777',
        'perfil_paciente': 'Criança',
        'servico_interesse_id': 1
    }
    response = client.post('/api/triagem', data=data)
    assert response.status_code == 400
    assert response.get_json()['sucesso'] is False

def test_triagem_campos_obrigatorios_ausentes(client):
    """Teste de Segurança: Bloqueia envio sem campos obrigatórios."""
    data = {
        'nome_responsavel': '',
        'email': 'teste@email.com'
    }
    response = client.post('/api/triagem', data=data)
    assert response.status_code == 400
    assert response.get_json()['sucesso'] is False