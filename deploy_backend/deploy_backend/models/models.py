from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(50), nullable=False, default='operador')

    # Relacionamento com entregas (para motoristas)
    entregas_atribuidas = db.relationship('Entrega', backref='motorista', lazy=True, foreign_keys='Entrega.motorista_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'perfil': self.perfil
        }

class Entrega(db.Model):
    __tablename__ = 'entregas'

    id = db.Column(db.Integer, primary_key=True)
    codigo_rastreio = db.Column(db.String(50), unique=True, nullable=False)
    remetente = db.Column(db.Text, nullable=False)
    destinatario = db.Column(db.Text, nullable=False)
    origem = db.Column(db.Text, nullable=False)
    destino = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    data_criacao = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    data_atualizacao = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Novos campos adicionados
    data_prevista_entrega = db.Column(db.TIMESTAMP, nullable=True)
    tipo_produto = db.Column(db.String(100), nullable=True)
    peso = db.Column(db.Float, nullable=True)
    km = db.Column(db.Float, nullable=True)
    preco = db.Column(db.Float, nullable=True)
    motorista_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    motivo_atraso = db.Column(db.Text, nullable=True)
    motivo_devolucao = db.Column(db.Text, nullable=True)

    # Relacionamento com AtualizacoesStatus
    atualizacoes = db.relationship('AtualizacaoStatus', backref='entrega', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
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
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
            'data_prevista_entrega': self.data_prevista_entrega.isoformat() if self.data_prevista_entrega else None,
            'tipo_produto': self.tipo_produto,
            'peso': self.peso,
            'km': self.km,
            'preco': self.preco,
            'motorista_id': self.motorista_id,
            'motorista_nome': self.motorista.username if self.motorista else None,
            'motivo_atraso': self.motivo_atraso,
            'motivo_devolucao': self.motivo_devolucao
        }

class AtualizacaoStatus(db.Model):
    __tablename__ = 'atualizacoes_status'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas.id'), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    localizacao = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Novos campos adicionados
    motivo_atraso = db.Column(db.Text, nullable=True)
    motivo_devolucao = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<AtualizacaoStatus {self.id} para Entrega {self.entrega_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'entrega_id': self.entrega_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'localizacao': self.localizacao,
            'observacoes': self.observacoes,
            'motivo_atraso': self.motivo_atraso,
            'motivo_devolucao': self.motivo_devolucao
        }
