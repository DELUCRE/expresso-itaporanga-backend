from flask import Blueprint, request, jsonify
from models.models import db, Entrega, AtualizacaoStatus, Usuario
from datetime import datetime
from sqlalchemy import desc
from fastapi import APIRouter
from models.entrega import Entrega  # Certifique-se de que o modelo Entrega está definido corretamente
from extensions import db

class Entrega(db.Model):
    _tablename_ = 'entregas'
    
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, nullable=False)
    data_entrega = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "funcionario_id": self.funcionario_id,
            "data_entrega": self.data_entrega.isoformat(),
            "status": self.status
        }

router = APIRouter()

@router.get("/entregas")
async def listar_entregas():
    # Lógica para obter as entregas do banco de dados
    return {"entregas": [...]}

entregas_bp = Blueprint('entregas', __name__)

@entregas_bp.route('/entregas', methods=['GET'])
def get_entregas():
    try:
        entregas = Entrega.query.order_by(desc(Entrega.data_criacao)).all()
        return jsonify([entrega.to_dict() for entrega in entregas])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>', methods=['GET'])
def get_entrega(codigo_rastreio):
    try:
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        if not entrega:
            return jsonify({"error": "Entrega não encontrada"}), 404
        
        entrega_dict = entrega.to_dict()
        
        # Adicionar histórico de status
        historico = AtualizacaoStatus.query.filter_by(entrega_id=entrega.id).order_by(desc(AtualizacaoStatus.timestamp)).all()
        entrega_dict['historico_status'] = [hist.to_dict() for hist in historico]
        
        return jsonify(entrega_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@entregas_bp.route('/entregas', methods=['POST'])
def create_entrega():
    try:
        data = request.json
        
        # Validar campos obrigatórios
        required_fields = ['codigo_rastreio', 'remetente', 'destinatario', 'origem', 'destino']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Campo obrigatório: {field}"}), 400
        
        # Verificar se já existe entrega com o mesmo código de rastreio
        existing = Entrega.query.filter_by(codigo_rastreio=data['codigo_rastreio']).first()
        if existing:
            return jsonify({"error": "Já existe uma entrega com este código de rastreio"}), 400
        
        # Processar data_prevista_entrega se fornecida
        data_prevista_entrega = None
        if data.get('data_prevista_entrega'):
            try:
                data_prevista_entrega = datetime.fromisoformat(data['data_prevista_entrega'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Formato de data inválido para data_prevista_entrega"}), 400
        
        # Verificar motorista_id se fornecido
        motorista_id = None
        if data.get('motorista_id'):
            motorista = Usuario.query.filter_by(id=data['motorista_id']).first()
            if not motorista:
                return jsonify({"error": "Motorista não encontrado"}), 400
            motorista_id = motorista.id
        
        # Criar nova entrega com todos os campos
        nova_entrega = Entrega(
            codigo_rastreio=data['codigo_rastreio'],
            remetente=data['remetente'],
            destinatario=data['destinatario'],
            origem=data['origem'],
            destino=data['destino'],
            status='Pendente',
            data_prevista_entrega=data_prevista_entrega,
            tipo_produto=data.get('tipo_produto'),
            peso=data.get('peso'),
            km=data.get('km'),
            preco=data.get('preco'),
            motorista_id=motorista_id,
            motivo_atraso=data.get('motivo_atraso'),
            motivo_devolucao=data.get('motivo_devolucao')
        )
        
        db.session.add(nova_entrega)
        db.session.commit()
        
        # Criar primeiro registro de histórico
        primeiro_status = AtualizacaoStatus(
            entrega_id=nova_entrega.id,
            status='Pendente',
            localizacao=data.get('origem'),
            observacoes="Entrega registrada no sistema"
        )
        
        db.session.add(primeiro_status)
        db.session.commit()
        
        return jsonify({"message": "Entrega criada com sucesso", "entrega": nova_entrega.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>', methods=['PUT'])
def update_entrega(codigo_rastreio):
    try:
        data = request.json
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        if not entrega:
            return jsonify({"error": "Entrega não encontrada"}), 404
        
        # Atualizar campos básicos
        if 'remetente' in data:
            entrega.remetente = data['remetente']
        if 'destinatario' in data:
            entrega.destinatario = data['destinatario']
        if 'origem' in data:
            entrega.origem = data['origem']
        if 'destino' in data:
            entrega.destino = data['destino']
        
        # Atualizar novos campos
        if 'data_prevista_entrega' in data:
            if data['data_prevista_entrega']:
                try:
                    entrega.data_prevista_entrega = datetime.fromisoformat(data['data_prevista_entrega'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({"error": "Formato de data inválido para data_prevista_entrega"}), 400
            else:
                entrega.data_prevista_entrega = None
                
        if 'tipo_produto' in data:
            entrega.tipo_produto = data['tipo_produto']
        if 'peso' in data:
            entrega.peso = data['peso']
        if 'km' in data:
            entrega.km = data['km']
        if 'preco' in data:
            entrega.preco = data['preco']
            
        if 'motorista_id' in data:
            if data['motorista_id']:
                motorista = Usuario.query.filter_by(id=data['motorista_id']).first()
                if not motorista:
                    return jsonify({"error": "Motorista não encontrado"}), 400
                entrega.motorista_id = motorista.id
            else:
                entrega.motorista_id = None
                
        if 'motivo_atraso' in data:
            entrega.motivo_atraso = data['motivo_atraso']
        if 'motivo_devolucao' in data:
            entrega.motivo_devolucao = data['motivo_devolucao']
        
        # Atualizar data_atualizacao
        entrega.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({"message": "Entrega atualizada com sucesso", "entrega": entrega.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>/status', methods=['PUT'])
def update_status(codigo_rastreio):
    try:
        data = request.json
        if not data.get('status'):
            return jsonify({"error": "Status é obrigatório"}), 400
        
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        if not entrega:
            return jsonify({"error": "Entrega não encontrada"}), 404
        
        # Atualizar status da entrega
        entrega.status = data['status']
        entrega.data_atualizacao = datetime.utcnow()
        
        # Registrar motivos específicos se fornecidos
        if data['status'] == 'Atrasado' and data.get('motivo_atraso'):
            entrega.motivo_atraso = data['motivo_atraso']
        
        if data['status'] == 'Devolvido' and data.get('motivo_devolucao'):
            entrega.motivo_devolucao = data['motivo_devolucao']
        
        # Criar novo registro de histórico
        novo_status = AtualizacaoStatus(
            entrega_id=entrega.id,
            status=data['status'],
            localizacao=data.get('localizacao'),
            observacoes=data.get('observacoes'),
            motivo_atraso=data.get('motivo_atraso') if data['status'] == 'Atrasado' else None,
            motivo_devolucao=data.get('motivo_devolucao') if data['status'] == 'Devolvido' else None
        )
        
        db.session.add(novo_status)
        db.session.commit()
        
        return jsonify({"message": "Status atualizado com sucesso", "entrega": entrega.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@entregas_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    try:
        perfil = request.args.get('perfil')
        query = Usuario.query
        
        if perfil:
            query = query.filter_by(perfil=perfil)
            
        usuarios = query.all()
        return jsonify([usuario.to_dict() for usuario in usuarios])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
