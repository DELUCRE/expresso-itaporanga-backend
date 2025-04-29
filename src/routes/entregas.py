from flask import Blueprint, request, jsonify, session
from src.models.models import db, Entrega, AtualizacaoStatus, Usuario
from functools import wraps
from datetime import datetime

entregas_bp = Blueprint("entregas", __name__)

# Decorator for checking user login and profile
def login_required(required_perfil=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401
            
            user = Usuario.query.get(user_id)
            if not user:
                 return jsonify({"error": "User not found"}), 401 # Should not happen if session is valid

            # Check profile if required
            if required_perfil:
                # Allow admin full access, otherwise check specific profile
                if user.perfil != 'admin' and user.perfil != required_perfil:
                    return jsonify({"error": "Insufficient permissions"}), 403
            
            # Make user object available to the route if needed (optional)
            # request.user = user 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@entregas_bp.route("/entregas", methods=["POST"])
@login_required(required_perfil='operador') # Only operadores or admins can create
def create_entrega():
    data = request.get_json()
    codigo_rastreio = data.get("codigo_rastreio")
    remetente = data.get("remetente")
    destinatario = data.get("destinatario")
    origem = data.get("origem")
    destino = data.get("destino")

    if not all([codigo_rastreio, remetente, destinatario, origem, destino]):
        return jsonify({"error": "Missing required fields"}), 400

    if Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first():
        return jsonify({"error": "Tracking code already exists"}), 409

    nova_entrega = Entrega(
        codigo_rastreio=codigo_rastreio,
        remetente=remetente,
        destinatario=destinatario,
        origem=origem,
        destino=destino,
        status="Pendente" # Initial status
    )
    db.session.add(nova_entrega)
    
    # Add initial status update
    nova_atualizacao = AtualizacaoStatus(
        entrega=nova_entrega, 
        status="Pendente", 
        observacoes="Entrega registrada no sistema"
    )
    db.session.add(nova_atualizacao)
    
    db.session.commit()

    return jsonify({"message": "Delivery created successfully", "entrega": nova_entrega.to_dict()}), 201

@entregas_bp.route("/entregas", methods=["GET"])
@login_required() # Any logged-in user can list deliveries (adjust permissions if needed)
def get_entregas():
    # Basic listing, add pagination later if needed
    entregas = Entrega.query.order_by(Entrega.data_criacao.desc()).all()
    return jsonify([entrega.to_dict() for entrega in entregas]), 200

@entregas_bp.route("/entregas/<string:codigo_rastreio>", methods=["GET"])
@login_required() # Any logged-in user can view a specific delivery
def get_entrega_by_codigo(codigo_rastreio):
    entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
    if not entrega:
        return jsonify({"error": "Delivery not found"}), 404
    
    # Include status history
    atualizacoes = AtualizacaoStatus.query.filter_by(entrega_id=entrega.id).order_by(AtualizacaoStatus.timestamp.asc()).all()
    entrega_dict = entrega.to_dict()
    entrega_dict['historico_status'] = [atualizacao.to_dict() for atualizacao in atualizacoes]
    
    return jsonify(entrega_dict), 200

@entregas_bp.route("/entregas/<string:codigo_rastreio>/status", methods=["PUT"])
@login_required(required_perfil='operador') # Only operadores or admins can update status
def update_entrega_status(codigo_rastreio):
    entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
    if not entrega:
        return jsonify({"error": "Delivery not found"}), 404

    data = request.get_json()
    novo_status = data.get("status")
    localizacao = data.get("localizacao")
    observacoes = data.get("observacoes")

    if not novo_status:
        return jsonify({"error": "New status is required"}), 400

    # Update the main status on the Entrega object
    entrega.status = novo_status
    # Manually update data_atualizacao as onupdate might not work as expected with all DBs/ORM setups
    entrega.data_atualizacao = datetime.utcnow() 

    # Add a new status update entry
    nova_atualizacao = AtualizacaoStatus(
        entrega_id=entrega.id,
        status=novo_status,
        localizacao=localizacao,
        observacoes=observacoes
    )
    db.session.add(nova_atualizacao)
    db.session.commit()

    return jsonify({"message": "Delivery status updated successfully", "entrega": entrega.to_dict()}), 200

