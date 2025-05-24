from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    _tablename_ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    perfil = db.Column(db.String(20), default='usuario')  # 'admin', 'usuario', 'motorista'
    
    # Relacionamento com entregas (um motorista pode ter várias entregas)
    entregas = db.relationship('Entrega', backref='motorista', lazy=True, foreign_keys='Entrega.motorista_id')
    
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
    status = db.Column(db.String(30), nullable=False, default='Registrado')
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_prevista_entrega = db.Column(db.DateTime)
    
    # Campos opcionais
    motivo_atraso = db.Column(db.String(200))
    motivo_devolucao = db.Column(db.String(200))
    km = db.Column(db.Float)  # Distância em km
    peso = db.Column(db.Float)  # Peso em kg
    preco = db.Column(db.Float)  # Preço/valor da entrega
    
    # Relacionamentos
    motorista_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    atualizacoes = db.relationship('AtualizacaoStatus', backref='entrega', lazy=True, cascade='all, delete-orphan')
    
    def _repr_(self):
        return f'<Entrega {self.codigo_rastreio}>'

class AtualizacaoStatus(db.Model):
    _tablename_ = 'atualizacoes_status'
    
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    
    def _repr_(self):
        return f'<AtualizacaoStatus {self.id} - {self.status}>'
