import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializar aplicação
app = Flask(__name__)
CORS(app, origins=["https://expresso-itaporanga-frontend.vercel.app", "http://localhost:5000"], supports_credentials=True)

# Configuração do banco de dados
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_padrao')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///logistica.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Corrigir URL do PostgreSQL se necessário (para compatibilidade com Render)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')

# Inicializar banco de dados
db = SQLAlchemy(app)

# Modelos sem relacionamentos para evitar problemas de chave estrangeira
class Usuario(db.Model):
    _tablename_ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    perfil = db.Column(db.String(20), default='usuario')
    
    def _repr_(self):
        return f'<Usuario {self.username}>'

class Entrega(db.Model):
    _tablename_ = 'entregas'
    id = db.Column(db.Integer, primary_key=True)
    codigo_rastreio = db.Column(db.String(20), unique=True, nullable=False)
    remetente = db.Column(db.String(100), nullable=False)
    destinatario = db.Column(db.String(100), nullable=False)
    origem = db.Column(db.String(100), nullable=False)
    destino = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Pendente')
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_prevista = db.Column(db.DateTime)
    data_conclusao = db.Column(db.DateTime)
    motorista_id = db.Column(db.Integer)  # Sem ForeignKey
    motivo_devolucao = db.Column(db.Text)
    
    def _repr_(self):
        return f'<Entrega {self.codigo_rastreio}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'codigo_rastreio': self.codigo_rastreio,
            'remetente': self.remetente,
            'destinatario': self.destinatario,
            'origem': self.origem,
            'destino': self.destino,
            'status': self.status,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S'),
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M:%S'),
            'data_prevista': self.data_prevista.strftime('%Y-%m-%d %H:%M:%S') if self.data_prevista else None,
            'data_conclusao': self.data_conclusao.strftime('%Y-%m-%d %H:%M:%S') if self.data_conclusao else None,
            'motorista_id': self.motorista_id,
            'motivo_devolucao': self.motivo_devolucao
        }

class AtualizacaoStatus(db.Model):
    _tablename_ = 'atualizacoes_status'
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, nullable=False)  # Sem ForeignKey
    status = db.Column(db.String(30), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    
    def _repr_(self):
        return f'<AtualizacaoStatus {self.id} - {self.status}>'

# Endpoint para limpar e recriar o banco de dados
@app.route('/reset-db', methods=['GET'])
def reset_db():
    try:
        # Remover todas as tabelas
        db.drop_all()
        
        # Recriar todas as tabelas
        db.create_all()
        
        return jsonify({"message": "Banco de dados resetado com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para criar usuário admin
@app.route('/create-admin', methods=['GET'])
def create_admin():
    try:
        # Criar usuário admin
        admin = Usuario(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            perfil='admin'
        )
        db.session.add(admin)
        db.session.commit()
        return jsonify({"message": "Usuário admin criado com sucesso! Username: admin, Senha: admin123"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint para criar dados de exemplo
@app.route('/create-sample-data', methods=['GET'])
def create_sample_data():
    try:
        # Criar entregas de exemplo
        entregas = [
            Entrega(
                codigo_rastreio="TRACK001",
                remetente="Empresa A",
                destinatario="Cliente 1",
                origem="São Paulo, SP",
                destino="Rio de Janeiro, RJ",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(days=2),
                data_prevista=datetime.now() + timedelta(days=3)
            ),
            Entrega(
                codigo_rastreio="TRACK002",
                remetente="Empresa B",
                destinatario="Cliente 2",
                origem="Curitiba, PR",
                destino="Florianópolis, SC",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=3),
                data_prevista=datetime.now() + timedelta(days=1)
            ),
            Entrega(
                codigo_rastreio="TRACK003",
                remetente="Empresa C",
                destinatario="Cliente 3",
                origem="Belo Horizonte, MG",
                destino="Brasília, DF",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=5),
                data_prevista=datetime.now() - timedelta(days=1),
                data_conclusao=datetime.now() - timedelta(days=1)
            )
        ]
        
        for entrega in entregas:
            db.session.add(entrega)
        
        db.session.commit()
        
        return jsonify({"message": "Dados de exemplo criados com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Endpoint de teste
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "API está funcionando!"}), 200

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
        
        user = Usuario.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 401
        
        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Senha incorreta"}), 401
        
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": {
                "id": user.id,
                "username": user.username,
                "perfil": user.perfil
            }
        }), 200
    except Exception as e:
        print(f"Erro no login: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/auth/status', methods=['GET'])
def status():
    return jsonify({
        "status": "authenticated",
        "user": {
            "username": "admin",
            "perfil": "admin"
        }
    }), 200

# Rotas de entregas
@app.route('/entregas', methods=['GET'])
def get_entregas():
    entregas = Entrega.query.all()
    return jsonify([entrega.to_dict() for entrega in entregas]), 200

@app.route('/entregas/<codigo_rastreio>', methods=['GET'])
def get_entrega(codigo_rastreio):
    entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
    if not entrega:
        return jsonify({"error": "Entrega não encontrada"}), 404
    return jsonify(entrega.to_dict()), 200

# Rotas de relatório
@app.route('/relatorio/desempenho', methods=['GET'])
def relatorio_desempenho():
    # Dados de exemplo para o relatório de desempenho
    return jsonify({
        'total_entregas': 20,
        'tempo_medio': 3.5,
        'taxa_entrega': 85,
        'taxa_devolucao': 15
    }), 200

@app.route('/relatorio/qualidade', methods=['GET'])
def relatorio_qualidade():
    # Dados de exemplo para o relatório de qualidade
    return jsonify({
        'avaliacao_media': 4.5,
        'reclamacoes': 3,
        'elogios': 12,
        'problemas_por_regiao': [
            {'regiao': 'SP', 'quantidade': 1},
            {'regiao': 'RJ', 'quantidade': 1},
            {'regiao': 'SC', 'quantidade': 1}
        ]
    }), 200

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
