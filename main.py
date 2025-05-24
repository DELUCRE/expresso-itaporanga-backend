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

# Modelos
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
    motorista_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    motivo_devolucao = db.Column(db.Text)
    
    atualizacoes = db.relationship('AtualizacaoStatus', backref='entrega', lazy=True, cascade="all, delete-orphan")
    
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
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    
    def _repr_(self):
        return f'<AtualizacaoStatus {self.id} - {self.status}>'

# Rotas de teste
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "API está funcionando!"}), 200

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
    
    user = Usuario.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Usuário ou senha inválidos"}), 401
    
    return jsonify({
        "message": "Login realizado com sucesso",
        "user": {
            "id": user.id,
            "username": user.username,
            "perfil": user.perfil
        }
    }), 200

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    perfil = data.get('perfil', 'usuario')
    
    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400
    
    if Usuario.query.filter_by(username=username).first():
        return jsonify({"error": "Usuário já existe"}), 400
    
    user = Usuario(
        username=username,
        password_hash=generate_password_hash(password),
        perfil=perfil
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "message": "Usuário criado com sucesso",
        "user": {
            "id": user.id,
            "username": user.username,
            "perfil": user.perfil
        }
    }), 201

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

# Rota para criar dados de exemplo
@app.route('/create-sample-data', methods=['GET'])
def create_sample_data():
    try:
        # Limpar dados existentes para evitar duplicações
        AtualizacaoStatus.query.delete()
        Entrega.query.delete()
        
        # Atualizar usuário admin para ter perfil correto
        admin = Usuario.query.filter_by(username='admin').first()
        if admin:
            admin.perfil = 'admin'
        else:
            admin = Usuario(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                perfil='admin'
            )
            db.session.add(admin)
        
        db.session.commit()
        
        # Criar 10 entregas atuais (não concluídas)
        entregas_atuais = [
            Entrega(
                codigo_rastreio="TRACK163630",
                remetente="Distribuidora de Livros",
                destinatario="Livraria",
                origem="Porto Alegre, RS",
                destino="Florianópolis, SC",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(days=2),
                data_prevista=datetime.now() + timedelta(days=3),
                motorista_id=admin.id
            ),
            Entrega(
                codigo_rastreio="ATR13359540",
                remetente="Indústria Nacional",
                destinatario="Loja de Departamentos",
                origem="Curitiba, PR",
                destino="Florianópolis, SC",
                status="Atrasado",
                data_criacao=datetime.now() - timedelta(days=5),
                data_prevista=datetime.now() - timedelta(days=1),
                motorista_id=admin.id
            ),
            # Adicione mais entregas conforme necessário
        ]
        
        # Criar 10 entregas concluídas
        entregas_concluidas = [
            Entrega(
                codigo_rastreio="COMP12345",
                remetente="Fábrica de Eletrônicos",
                destinatario="Loja de Informática",
                origem="São Paulo, SP",
                destino="Campinas, SP",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=10),
                data_prevista=datetime.now() - timedelta(days=7),
                data_conclusao=datetime.now() - timedelta(days=6),
                motorista_id=admin.id
            ),
            Entrega(
                codigo_rastreio="DEV98765",
                remetente="Loja Online",
                destinatario="Cliente Final",
                origem="Rio de Janeiro, RJ",
                destino="Niterói, RJ",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=8),
                data_prevista=datetime.now() - timedelta(days=5),
                data_conclusao=datetime.now() - timedelta(days=4),
                motivo_devolucao="Endereço não encontrado",
                motorista_id=admin.id
            ),
            # Adicione mais entregas concluídas conforme necessário
        ]
        
        todas_entregas = entregas_atuais + entregas_concluidas
        
        for entrega in todas_entregas:
            db.session.add(entrega)
        
        db.session.commit()
        
        # Adicionar atualizações de status para cada entrega
        for entrega in todas_entregas:
            db.session.add(AtualizacaoStatus(
                entrega_id=entrega.id,
                status="Registrado",
                timestamp=entrega.data_criacao,
                observacoes="Entrega registrada no sistema"
            ))
            
            if entrega.status == "Entregue":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Em trânsito",
                    timestamp=entrega.data_criacao + timedelta(days=1),
                    observacoes="Entrega saiu para entrega"
                ))
                
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Entregue",
                    timestamp=entrega.data_conclusao,
                    observacoes="Entrega realizada com sucesso"
                ))
            
            elif entrega.status == "Devolvido":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Em trânsito",
                    timestamp=entrega.data_criacao + timedelta(days=1),
                    observacoes="Entrega saiu para entrega"
                ))
                
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Problema na entrega",
                    timestamp=entrega.data_conclusao - timedelta(hours=2),
                    observacoes=f"Problema na entrega: {entrega.motivo_devolucao or 'Motivo não especificado'}"
                ))
                
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Devolvido",
                    timestamp=entrega.data_conclusao,
                    observacoes=f"Entrega devolvida ao remetente: {entrega.motivo_devolucao or 'Motivo não especificado'}"
                ))
        
        db.session.commit()
        
        return jsonify({
            "message": "Dados de exemplo criados com sucesso!",
            "entregas_atuais": len(entregas_atuais),
            "entregas_concluidas": len(entregas_concluidas),
            "total_entregas": len(todas_entregas)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Criar tabelas do banco de dados
with app.app_context():
    db.create_all()

# Rota para criar motoristas
@app.route('/create-drivers', methods=['GET'])
def create_drivers():
    try:
        # Criar motoristas
        motoristas = [
            {
                "username": "motorista1",
                "password": "senha123",
                "nome": "João Silva",
                "perfil": "motorista"
            },
            {
                "username": "motorista2",
                "password": "senha123",
                "nome": "Maria Oliveira",
                "perfil": "motorista"
            },
            {
                "username": "motorista3",
                "password": "senha123",
                "nome": "Carlos Santos",
                "perfil": "motorista"
            },
            {
                "username": "motorista4",
                "password": "senha123",
                "nome": "Ana Pereira",
                "perfil": "motorista"
            },
            {
                "username": "motorista5",
                "password": "senha123",
                "nome": "Pedro Souza",
                "perfil": "motorista"
            }
        ]
        
        for motorista_data in motoristas:
            # Verificar se o motorista já existe
            motorista = Usuario.query.filter_by(username=motorista_data["username"]).first()
            if not motorista:
                motorista = Usuario(
                    username=motorista_data["username"],
                    password_hash=generate_password_hash(motorista_data["password"]),
                    perfil=motorista_data["perfil"]
                )
                db.session.add(motorista)
        
        db.session.commit()
        
        # Atualizar entregas para associar motoristas
        entregas = Entrega.query.all()
        motoristas = Usuario.query.filter_by(perfil="motorista").all()
        
        if motoristas:
            for i, entrega in enumerate(entregas):
                entrega.motorista_id = motoristas[i % len(motoristas)].id
            
            db.session.commit()
        
        return jsonify({
            "message": "Motoristas criados e associados às entregas com sucesso!",
            "entregas_atualizadas": len(entregas),
            "motoristas": [m.username for m in motoristas]
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Rota para informações da API
@app.route('/api-info', methods=['GET'])
def api_info():
    base_url = request.url_root
    
    endpoints = {
        "auth_login": f"{base_url}auth/login",
        "auth_register": f"{base_url}auth/register",
        "auth_status": f"{base_url}auth/status",
        "entregas": f"{base_url}entregas",
        "relatorio_desempenho": f"{base_url}relatorio/desempenho",
        "relatorio_qualidade": f"{base_url}relatorio/qualidade",
        "usuarios": f"{base_url}usuarios"
    }
    
    return jsonify({
        "api_base_url": base_url,
        "endpoints": endpoints,
        "cors_enabled": True,
        "frontend_instructions": "Use estas URLs completas no frontend para acessar a API"
    }), 200

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
