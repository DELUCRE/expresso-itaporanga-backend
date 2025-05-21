from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model): # Renomeado para Usuario para corresponder ao schema
    __tablename__ = 'usuarios' # Especifica o nome da tabela

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
            # Não retornar password_hash
        }

