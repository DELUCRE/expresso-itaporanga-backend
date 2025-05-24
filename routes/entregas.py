from flask import Blueprint, request, jsonify
from models.models import db, Entrega, AtualizacaoStatus, Usuario
from datetime import datetime

# Definir o blueprint
entregas_bp = Blueprint('entregas', __name__)

@entregas_bp.route('/entregas', methods=['GET'])
def get_entregas():
    try:
        # Obter todas as entregas
        entregas = Entrega.query.all()
        
        # Converter para dicionário
        entregas_dict = []
        for e in entregas:
            entregas_dict.append({
                'id': e.id,
                'codigo_rastreio': e.codigo_rastreio,
                'remetente': e.remetente,
                'destinatario': e.destinatario,
                'origem': e.origem,
                'destino': e.destino,
                'status': e.status,
                'data_criacao': e.data_criacao.isoformat() if e.data_criacao else None,
                'data_atualizacao': e.data_atualizacao.isoformat() if e.data_atualizacao else None,
                'data_prevista_entrega': e.data_prevista_entrega.isoformat() if e.data_prevista_entrega else None
            })
        
        return jsonify(entregas_dict), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>', methods=['GET'])
def get_entrega(codigo_rastreio):
    try:
        # Buscar entrega pelo código de rastreio
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        
        if not entrega:
            return jsonify({'error': 'Entrega não encontrada'}), 404
        
        # Buscar atualizações de status
        atualizacoes = AtualizacaoStatus.query.filter_by(entrega_id=entrega.id).order_by(AtualizacaoStatus.timestamp).all()
        
        # Converter atualizações para dicionário
        atualizacoes_dict = []
        for a in atualizacoes:
            atualizacoes_dict.append({
                'id': a.id,
                'status': a.status,
                'timestamp': a.timestamp.isoformat() if a.timestamp else None,
                'observacoes': a.observacoes
            })
        
        # Buscar motorista (se existir)
        motorista = None
        if hasattr(entrega, 'motorista_id') and entrega.motorista_id:
            motorista_obj = Usuario.query.get(entrega.motorista_id)
            if motorista_obj:
                motorista = {
                    'id': motorista_obj.id,
                    'nome': motorista_obj.username
                }
        
        # Converter entrega para dicionário
        entrega_dict = {
            'id': entrega.id,
            'codigo_rastreio': entrega.codigo_rastreio,
            'remetente': entrega.remetente,
            'destinatario': entrega.destinatario,
            'origem': entrega.origem,
            'destino': entrega.destino,
            'status': entrega.status,
            'data_criacao': entrega.data_criacao.isoformat() if entrega.data_criacao else None,
            'data_atualizacao': entrega.data_atualizacao.isoformat() if entrega.data_atualizacao else None,
            'data_prevista_entrega': entrega.data_prevista_entrega.isoformat() if entrega.data_prevista_entrega else None,
            'motorista': motorista,
            'atualizacoes': atualizacoes_dict
        }
        
        return jsonify(entrega_dict), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/entregas', methods=['POST'])
def create_entrega():
    try:
        data = request.get_json()
        
        # Verificar se todos os campos necessários estão presentes
        required_fields = ['codigo_rastreio', 'remetente', 'destinatario', 'origem', 'destino']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Verificar se já existe uma entrega com o mesmo código de rastreio
        if Entrega.query.filter_by(codigo_rastreio=data['codigo_rastreio']).first():
            return jsonify({'error': 'Código de rastreio já existe'}), 400
        
        # Criar nova entrega
        nova_entrega = Entrega(
            codigo_rastreio=data['codigo_rastreio'],
            remetente=data['remetente'],
            destinatario=data['destinatario'],
            origem=data['origem'],
            destino=data['destino'],
            status='Registrado',
            data_criacao=datetime.now(),
            data_atualizacao=datetime.now()
        )
        
        # Adicionar data prevista de entrega se fornecida
        if 'data_prevista_entrega' in data and data['data_prevista_entrega']:
            try:
                nova_entrega.data_prevista_entrega = datetime.fromisoformat(data['data_prevista_entrega'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Formato de data inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Adicionar motorista se fornecido
        if 'motorista_id' in data and data['motorista_id']:
            motorista = Usuario.query.get(data['motorista_id'])
            if not motorista or motorista.perfil != 'motorista':
                return jsonify({'error': 'Motorista não encontrado ou inválido'}), 400
            nova_entrega.motorista_id = data['motorista_id']
        
        db.session.add(nova_entrega)
        db.session.commit()
        
        # Adicionar primeira atualização de status
        atualizacao = AtualizacaoStatus(
            entrega_id=nova_entrega.id,
            status='Registrado',
            timestamp=datetime.now(),
            observacoes='Entrega registrada no sistema'
        )
        
        db.session.add(atualizacao)
        db.session.commit()
        
        return jsonify({
            'message': 'Entrega criada com sucesso',
            'id': nova_entrega.id,
            'codigo_rastreio': nova_entrega.codigo_rastreio
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>', methods=['PUT'])
def update_entrega(codigo_rastreio):
    try:
        data = request.get_json()
        
        # Buscar entrega pelo código de rastreio
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        
        if not entrega:
            return jsonify({'error': 'Entrega não encontrada'}), 404
        
        # Atualizar campos
        if 'remetente' in data:
            entrega.remetente = data['remetente']
        if 'destinatario' in data:
            entrega.destinatario = data['destinatario']
        if 'origem' in data:
            entrega.origem = data['origem']
        if 'destino' in data:
            entrega.destino = data['destino']
        if 'status' in data:
            entrega.status = data['status']
        if 'data_prevista_entrega' in data and data['data_prevista_entrega']:
            try:
                entrega.data_prevista_entrega = datetime.fromisoformat(data['data_prevista_entrega'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Formato de data inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)'}), 400
        if 'motorista_id' in data:
            if data['motorista_id']:
                motorista = Usuario.query.get(data['motorista_id'])
                if not motorista or motorista.perfil != 'motorista':
                    return jsonify({'error': 'Motorista não encontrado ou inválido'}), 400
            entrega.motorista_id = data['motorista_id']
        
        # Atualizar data de atualização
        entrega.data_atualizacao = datetime.now()
        
        db.session.commit()
        
        # Adicionar nova atualização de status se o status foi alterado
        if 'status' in data:
            atualizacao = AtualizacaoStatus(
                entrega_id=entrega.id,
                status=data['status'],
                timestamp=datetime.now(),
                observacoes=data.get('observacoes', f'Status atualizado para {data["status"]}')
            )
            
            db.session.add(atualizacao)
            db.session.commit()
        
        return jsonify({
            'message': 'Entrega atualizada com sucesso',
            'id': entrega.id,
            'codigo_rastreio': entrega.codigo_rastreio
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entregas_bp.route('/entregas/<codigo_rastreio>/status', methods=['POST'])
def add_status(codigo_rastreio):
    try:
        data = request.get_json()
        
        # Verificar se todos os campos necessários estão presentes
        if 'status' not in data:
            return jsonify({'error': 'Status não fornecido'}), 400
        
        # Buscar entrega pelo código de rastreio
        entrega = Entrega.query.filter_by(codigo_rastreio=codigo_rastreio).first()
        
        if not entrega:
            return jsonify({'error': 'Entrega não encontrada'}), 404
        
        # Adicionar nova atualização de status
        atualizacao = AtualizacaoStatus(
            entrega_id=entrega.id,
            status=data['status'],
            timestamp=datetime.now(),
            observacoes=data.get('observacoes', '')
        )
        
        # Atualizar status da entrega
        entrega.status = data['status']
        entrega.data_atualizacao = datetime.now()
        
        # Adicionar motivo de atraso ou devolução se fornecido
        if data['status'] == 'Atrasado' and 'motivo' in data:
            entrega.motivo_atraso = data['motivo']
        elif data['status'] == 'Devolvido' and 'motivo' in data:
            entrega.motivo_devolucao = data['motivo']
        
        db.session.add(atualizacao)
        db.session.commit()
        
        return jsonify({
            'message': 'Status adicionado com sucesso',
            'id': atualizacao.id,
            'status': atualizacao.status
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
