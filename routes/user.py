from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models.models import db, Usuario

# Definir o blueprint
user_bp = Blueprint('user', _name_)

@user_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    try:
        # Obter todos os usuários
        usuarios = Usuario.query.all()
        
        # Converter para dicionário
        usuarios_dict = []
        for u in usuarios:
            usuarios_dict.append({
                'id': u.id,
                'username': u.username,
                'perfil': u.perfil
            })
        
        return jsonify(usuarios_dict), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/usuarios/<int:id>', methods=['GET'])
def get_usuario(id):
    try:
        # Buscar usuário pelo ID
        usuario = Usuario.query.get(id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Converter para dicionário
        usuario_dict = {
            'id': usuario.id,
            'username': usuario.username,
            'perfil': usuario.perfil
        }
        
        return jsonify(usuario_dict), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/usuarios', methods=['POST'])
def create_usuario():
    try:
        data = request.get_json()
        
        # Verificar se todos os campos necessários estão presentes
        if not all(k in data for k in ('username', 'password')):
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Verificar se o usuário já existe
        if Usuario.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Nome de usuário já existe'}), 400
        
        # Criar novo usuário
        novo_usuario = Usuario(
            username=data['username'],
            password_hash=generate_password_hash(data['password']),
            perfil=data.get('perfil', 'usuario')  # Perfil padrão é 'usuario'
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'id': novo_usuario.id,
            'username': novo_usuario.username
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    try:
        data = request.get_json()
        
        # Buscar usuário pelo ID
        usuario = Usuario.query.get(id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Atualizar campos
        if 'username' in data:
            # Verificar se o novo username já existe
            existing = Usuario.query.filter_by(username=data['username']).first()
            if existing and existing.id != id:
                return jsonify({'error': 'Nome de usuário já existe'}), 400
            usuario.username = data['username']
        
        if 'password' in data:
            usuario.password_hash = generate_password_hash(data['password'])
        
        if 'perfil' in data:
            usuario.perfil = data['perfil']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário atualizado com sucesso',
            'id': usuario.id,
            'username': usuario.username
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/usuarios/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    try:
        # Buscar usuário pelo ID
        usuario = Usuario.query.get(id)
        
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário excluído com sucesso'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
