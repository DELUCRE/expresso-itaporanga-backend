from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models.models import db, Usuario

# Definir o blueprint
auth_bp = Blueprint('auth', _name_)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Verificar se todos os campos necessários estão presentes
    if not all(k in data for k in ('username', 'password')):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    # Verificar se o usuário já existe
    if Usuario.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Nome de usuário já existe'}), 400
    
    # Criar novo usuário
    new_user = Usuario(
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        perfil=data.get('perfil', 'usuario')  # Perfil padrão é 'usuario'
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'Usuário registrado com sucesso'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Verificar se todos os campos necessários estão presentes
    if not all(k in data for k in ('username', 'password')):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    # Buscar usuário
    user = Usuario.query.filter_by(username=data['username']).first()
    
    # Verificar se o usuário existe e a senha está correta
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    # Aqui você implementaria a lógica de sessão/token
    # Por simplicidade, apenas retornamos os dados do usuário
    return jsonify({
        'message': 'Login bem-sucedido',
        'user': {
            'id': user.id,
            'username': user.username,
            'perfil': user.perfil
        }
    }), 200

@auth_bp.route('/status', methods=['GET'])
def status():
    # Simulação de verificação de autenticação
    # Em uma implementação real, você verificaria o token/sessão
    
    # Simulando um usuário autenticado
    return jsonify({
        'logged_in': True,
        'user': {
            'id': 1,
            'username': 'admin',
            'perfil': 'admin'
        }
    }), 200
