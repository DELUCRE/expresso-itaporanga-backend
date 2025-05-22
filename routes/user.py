from flask import Blueprint, jsonify, request
from models.models import Usuario, db

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = Usuario.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    
    data = request.json
    user = Usuario(username=data["username"], email=data["email"]) # Use Usuario
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = Usuario.query.get_or_404(user_id) # Use Usuario
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = Usuario.query.get_or_404(user_id) # Use Usuario
    data = request.json
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = Usuario.query.get_or_404(user_id) # Use Usuario
    db.session.delete(user)
    db.session.commit()
    return '', 204
