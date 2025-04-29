from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    perfil = db.Column(db.String(50), nullable=False, default='operador')

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
    data_atualizacao = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow) # onupdate might need trigger in Flask-SQLAlchemy or manual update

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
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }

class AtualizacaoStatus(db.Model):
    __tablename__ = 'atualizacoes_status'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas.id'), nullable=False)
    timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    localizacao = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<AtualizacaoStatus {self.id} para Entrega {self.entrega_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'entrega_id': self.entrega_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'localizacao': self.localizacao,
            'observacoes': self.observacoes
        }

