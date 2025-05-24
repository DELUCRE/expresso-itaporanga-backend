from flask import Blueprint, request, jsonify, session
from models.models import db, Usuario
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from models.models import Usuario

# Definir o blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    perfil = data.get("perfil", "operador") # Default to 'operador'

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if Usuario.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    new_user = Usuario(username=username, perfil=perfil)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user": new_user.to_dict()}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = Usuario.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Store user info in session
    session["user_id"] = user.id
    session["username"] = user.username
    session["perfil"] = user.perfil

    return jsonify({"message": "Login successful", "user": user.to_dict()}), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Clear session data
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("perfil", None)
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route("/status", methods=["GET"])
def status():
    user_id = session.get("user_id")
    if user_id:
        user = Usuario.query.get(user_id)
        if user:
            return jsonify({"logged_in": True, "user": user.to_dict()}), 200
    return jsonify({"logged_in": False}), 200

