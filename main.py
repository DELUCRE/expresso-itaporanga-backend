import os
import sys
from datetime import datetime, timedelta # Adicionado timedelta para manipulação de datas
from sqlalchemy import func, case, and_, or_, text # type: ignore

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request, jsonify # type: ignore # Adicionado request e jsonify
from src.models.models import db, Entrega, AtualizacaoStatus, Usuario # type: ignore
from src.routes.user import user_bp # type: ignore
from src.routes.auth import auth_bp # type: ignore
from src.routes.entregas import entregas_bp # type: ignore

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(entregas_bp, url_prefix="/api") # Register entregas blueprint under /api
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://logistica_user:password@localhost/logistica_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Função auxiliar para verificar autenticação
def check_auth():
    # Implementação simplificada - em produção, use autenticação real
    return None  # Retorna None se autenticado, ou uma resposta de erro se não

# Novo endpoint para o formulário de contato
@app.route('/api/contato', methods=['POST'])
def handle_contact_form():
    try:
        data = request.form # Usar request.form para dados de formulário padrão
        nome = data.get('name')
        email = data.get('email')
        assunto = data.get('subject')
        mensagem = data.get('message')

        if not all([nome, email, assunto, mensagem]):
            return jsonify({'error': 'Todos os campos são obrigatórios.'}), 400

        # Formata a mensagem para salvar no arquivo
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"""Timestamp: {timestamp}
Nome: {nome}
Email: {email}
Assunto: {assunto}
Mensagem: {mensagem}
---------------------------------------------------
"""

        # Salva a mensagem no arquivo mensagens_contato.txt
        # O arquivo será criado no mesmo diretório do main.py (pasta src)
        with open(os.path.join(os.path.dirname(__file__), 'mensagens_contato.txt'), 'a', encoding='utf-8') as f:
            f.write(log_message)

        return jsonify({'success': 'Mensagem recebida com sucesso!'}), 200
    except Exception as e:
        app.logger.error(f"Erro ao processar formulário de contato: {e}")
        return jsonify({'error': 'Erro interno ao processar sua mensagem.'}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html', mimetype='text/html')
        else:
            return "index.html not found", 404

# FUNÇÃO CORRIGIDA: Endpoint para obter histórico de status de uma entrega
@app.route('/api/entregas/<entrega_id>/historico', methods=['GET'])
def get_entrega_historico(entrega_id):
    try:
        # Verificar se a entrega existe
        entrega = db.session.query(Entrega).filter_by(id=entrega_id).first()
        if not entrega:
            return jsonify({"error": "Entrega não encontrada"}), 404
        
        # Buscar histórico de status
        historico = db.session.query(AtualizacaoStatus).filter_by(entrega_id=entrega_id).order_by(AtualizacaoStatus.timestamp.desc()).all()
        
        # Converter para formato JSON
        resultado = []
        for item in historico:
            resultado.append({
                'id': item.id,
                'entrega_id': item.entrega_id,
                'status': item.status,
                'timestamp': item.timestamp.isoformat() if item.timestamp else None,
                'localizacao': item.localizacao,
                'observacoes': item.observacoes,
                'motivo_atraso': item.motivo_atraso,
                'motivo_devolucao': item.motivo_devolucao
            })
        
        # Retornar como JSON com cabeçalho correto
        response = jsonify(resultado)
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        # Tratar erros e retornar como JSON
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/relatorio/desempenho', methods=['GET'])
def relatorio_desempenho():
    try:
        # Verificar se o usuário está logado
        auth_response = check_auth()
        if auth_response:
            return auth_response
            
        # Obter parâmetros de filtro
        periodo = request.args.get('periodo', 'mes')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Definir período padrão (mês atual) se não especificado
        hoje = datetime.now()
        if not data_inicio or not data_fim:
            if periodo == 'mes':
                data_inicio = datetime(hoje.year, hoje.month, 1)
                # Último dia do mês atual
                if hoje.month == 12:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
            elif periodo == 'trimestre':
                # Primeiro dia do trimestre atual
                trimestre_atual = ((hoje.month - 1) // 3) + 1
                data_inicio = datetime(hoje.year, (trimestre_atual - 1) * 3 + 1, 1)
                if trimestre_atual == 4:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, trimestre_atual * 3 + 1, 1) - timedelta(days=1)
            elif periodo == 'ano':
                data_inicio = datetime(hoje.year, 1, 1)
                data_fim = datetime(hoje.year, 12, 31)
            else:
                # Período personalizado - usar últimos 30 dias como padrão
                data_inicio = hoje - timedelta(days=30)
                data_fim = hoje
        else:
            # Converter strings para objetos datetime
            try:
                data_inicio = datetime.fromisoformat(data_inicio.replace('Z', '+00:00'))
                data_fim = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Formato de data inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)"}), 400
        
        # Consultar entregas no período especificado
        entregas = Entrega.query.filter(
            Entrega.data_criacao >= data_inicio,
            Entrega.data_criacao <= data_fim
        ).all()
        
        # Calcular KPIs de desempenho
        total_entregas = len(entregas)
        entregas_no_prazo = sum(1 for e in entregas if e.status == 'Entregue' and 
                               (e.data_prevista_entrega is None or 
                                e.data_atualizacao <= e.data_prevista_entrega))
        entregas_atrasadas = sum(1 for e in entregas if e.status == 'Entregue' and 
                                e.data_prevista_entrega is not None and 
                                e.data_atualizacao > e.data_prevista_entrega)
        entregas_devolvidas = sum(1 for e in entregas if e.status == 'Devolvido')
        entregas_pendentes = sum(1 for e in entregas if e.status not in ['Entregue', 'Devolvido'])
        
        # Calcular percentuais
        taxa_entrega = (entregas_no_prazo / total_entregas * 100) if total_entregas > 0 else 0
        taxa_atraso = (entregas_atrasadas / total_entregas * 100) if total_entregas > 0 else 0
        taxa_devolucao = (entregas_devolvidas / total_entregas * 100) if total_entregas > 0 else 0
        
        # Calcular tempo médio de entrega (em dias)
        tempos_entrega = []
        for e in entregas:
            if e.status == 'Entregue':
                # Encontrar a atualização de status "Entregue"
                entregue = AtualizacaoStatus.query.filter_by(
                    entrega_id=e.id, 
                    status='Entregue'
                ).order_by(AtualizacaoStatus.timestamp.desc()).first()
                
                if entregue:
                    # Calcular diferença em dias
                    delta = entregue.timestamp - e.data_criacao
                    tempos_entrega.append(delta.total_seconds() / (60 * 60 * 24))  # Converter para dias
        
        tempo_medio_entrega = sum(tempos_entrega) / len(tempos_entrega) if tempos_entrega else 0
        
        # Calcular KPIs avançados (se os campos estiverem disponíveis)
        km_total = sum(e.km for e in entregas if e.km is not None)
        peso_total = sum(e.peso for e in entregas if e.peso is not None)
        receita_total = sum(e.preco for e in entregas if e.preco is not None)
        
        # Calcular KPIs derivados
        custo_por_km = receita_total / km_total if km_total > 0 else 0
        receita_por_entrega = receita_total / total_entregas if total_entregas > 0 else 0
        
        # Agrupar por motorista (se disponível)
        desempenho_motoristas = []
        if any(e.motorista_id is not None for e in entregas):
            # Obter todos os motoristas que têm entregas no período
            motorista_ids = set(e.motorista_id for e in entregas if e.motorista_id is not None)
            for m_id in motorista_ids:
                motorista = Usuario.query.get(m_id)
                if not motorista:
                    continue
                    
                # Filtrar entregas deste motorista
                entregas_motorista = [e for e in entregas if e.motorista_id == m_id]
                total_motorista = len(entregas_motorista)
                entregas_no_prazo_motorista = sum(1 for e in entregas_motorista 
                                                if e.status == 'Entregue' and 
                                                (e.data_prevista_entrega is None or 
                                                 e.data_atualizacao <= e.data_prevista_entrega))
                
                # Calcular taxa de entrega no prazo deste motorista
                taxa_entrega_motorista = (entregas_no_prazo_motorista / total_motorista * 100) if total_motorista > 0 else 0
                
                desempenho_motoristas.append({
                    'id': m_id,
                    'nome': motorista.username,
                    'total_entregas': total_motorista,
                    'entregas_no_prazo': entregas_no_prazo_motorista,
                    'taxa_entrega': taxa_entrega_motorista
                })
        
        # Calcular entregas por dia (para o gráfico)
        entregas_por_dia = []
        # Criar um dicionário para contar entregas por dia
        contagem_por_dia = {}
        for e in entregas:
            data_str = e.data_criacao.strftime('%Y-%m-%d')
            contagem_por_dia[data_str] = contagem_por_dia.get(data_str, 0) + 1
        
        # Converter para o formato esperado pelo frontend
        for data_str, total in contagem_por_dia.items():
            entregas_por_dia.append({
                'data': data_str,
                'total': total
            })
        
        # Ordenar por data
        entregas_por_dia.sort(key=lambda x: x['data'])
        
        # Calcular distribuição de status
        distribuicao_status = []
        status_count = {}
        for e in entregas:
            status_count[e.status] = status_count.get(e.status, 0) + 1
        
        # Converter para o formato esperado pelo frontend
        for status, total in status_count.items():
            distribuicao_status.append({
                'status': status,
                'total': total
            })
        
        # Preparar resposta com os campos adicionais esperados pelo frontend
        response = {
            'periodo': {
                'inicio': data_inicio.isoformat(),
                'fim': data_fim.isoformat()
            },
            'kpis_gerais': {
                'total_entregas': total_entregas,
                'entregas_no_prazo': entregas_no_prazo,
                'entregas_atrasadas': entregas_atrasadas,
                'entregas_devolvidas': entregas_devolvidas,
                'entregas_pendentes': entregas_pendentes,
                'taxa_entrega': taxa_entrega,
                'taxa_atraso': taxa_atraso,
                'taxa_devolucao': taxa_devolucao,
                'tempo_medio_entrega': tempo_medio_entrega
            },
            'kpis_avancados': {
                'km_total': km_total,
                'peso_total': peso_total,
                'receita_total': receita_total,
                'custo_por_km': custo_por_km,
                'receita_por_entrega': receita_por_entrega
            },
            'desempenho_motoristas': desempenho_motoristas,
            # Campos adicionais esperados pelo frontend
            'entregas_por_dia': entregas_por_dia,
            'distribuicao_status': distribuicao_status
        }
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório de desempenho: {str(e)}")
        return jsonify({"error": f"Erro ao gerar relatório: {str(e)}"}), 500

@app.route('/api/relatorio/qualidade', methods=['GET'])
def relatorio_qualidade():
    try:
        # Verificar se o usuário está logado
        auth_response = check_auth()
        if auth_response:
            return auth_response
            
        # Obter parâmetros de filtro
        periodo = request.args.get('periodo', 'mes')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Definir período padrão (mês atual) se não especificado
        hoje = datetime.now()
        if not data_inicio or not data_fim:
            if periodo == 'mes':
                data_inicio = datetime(hoje.year, hoje.month, 1)
                # Último dia do mês atual
                if hoje.month == 12:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
            elif periodo == 'trimestre':
                # Primeiro dia do trimestre atual
                trimestre_atual = ((hoje.month - 1) // 3) + 1
                data_inicio = datetime(hoje.year, (trimestre_atual - 1) * 3 + 1, 1)
                if trimestre_atual == 4:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, trimestre_atual * 3 + 1, 1) - timedelta(days=1)
            elif periodo == 'ano':
                data_inicio = datetime(hoje.year, 1, 1)
                data_fim = datetime(hoje.year, 12, 31)
            else:
                # Período personalizado - usar últimos 30 dias como padrão
                data_inicio = hoje - timedelta(days=30)
                data_fim = hoje
        else:
            # Converter strings para objetos datetime
            try:
                data_inicio = datetime.fromisoformat(data_inicio.replace('Z', '+00:00'))
                data_fim = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Formato de data inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)"}), 400
        
        # Consultar entregas no período especificado
        entregas = Entrega.query.filter(
            Entrega.data_criacao >= data_inicio,
            Entrega.data_criacao <= data_fim
        ).all()
        
        # Analisar motivos de atraso
        motivos_atraso = {}
        for e in entregas:
            if e.motivo_atraso:
                motivo = e.motivo_atraso.strip()
                motivos_atraso[motivo] = motivos_atraso.get(motivo, 0) + 1
        
        # Analisar motivos de devolução
        motivos_devolucao = {}
        for e in entregas:
            if e.motivo_devolucao:
                motivo = e.motivo_devolucao.strip()
                motivos_devolucao[motivo] = motivos_devolucao.get(motivo, 0) + 1
        
        # Contar problemas por região (usando o campo destino como região)
        problemas_por_regiao = {}
        for e in entregas:
            if e.status in ['Atrasado', 'Problema na entrega', 'Devolvido']:
                regiao = e.destino.split(',')[-1].strip() if ',' in e.destino else e.destino
                problemas_por_regiao[regiao] = problemas_por_regiao.get(regiao, 0) + 1
        
        # Calcular totais para KPIs
        total_problemas = sum(1 for e in entregas if e.status == 'Problema na entrega')
        total_atrasos = sum(1 for e in entregas if e.status == 'Atrasado')
        total_devolucoes = sum(1 for e in entregas if e.status == 'Devolvido')
        
        # Combinar motivos de atraso e devolução para o gráfico de motivos de problemas
        motivos_problemas = []
        for motivo, quantidade in motivos_atraso.items():
            motivos_problemas.append({
                'motivo': f"Atraso: {motivo}",
                'total': quantidade
            })
        
        for motivo, quantidade in motivos_devolucao.items():
            motivos_problemas.append({
                'motivo': f"Devolução: {motivo}",
                'total': quantidade
            })
        
        # Preparar resposta com os campos adicionais esperados pelo frontend
        response = {
            'periodo': {
                'inicio': data_inicio.isoformat(),
                'fim': data_fim.isoformat()
            },
            'motivos_atraso': [{'motivo': k, 'quantidade': v} for k, v in motivos_atraso.items()],
            'motivos_devolucao': [{'motivo': k, 'quantidade': v} for k, v in motivos_devolucao.items()],
            'problemas_por_regiao': [{'regiao': k, 'quantidade': v} for k, v in problemas_por_regiao.items()],
            # Campos adicionais esperados pelo frontend
            'total_problemas': total_problemas,
            'total_atrasos': total_atrasos,
            'total_devolucoes': total_devolucoes,
            'motivos_problemas': motivos_problemas
        }
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório de qualidade: {str(e)}")
        return jsonify({"error": f"Erro ao gerar relatório: {str(e)}"}), 500

@app.route('/api/relatorio/excel', methods=['GET'])
def gerar_relatorio_excel():
    try:
        # Verificar se o usuário está logado
        auth_response = check_auth()
        if auth_response:
            return auth_response
            
        # Obter parâmetros de filtro
        periodo = request.args.get('periodo', 'mes')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Definir período padrão (mês atual) se não especificado
        hoje = datetime.now()
        if not data_inicio or not data_fim:
            if periodo == 'mes':
                data_inicio = datetime(hoje.year, hoje.month, 1)
                # Último dia do mês atual
                if hoje.month == 12:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
            elif periodo == 'trimestre':
                # Primeiro dia do trimestre atual
                trimestre_atual = ((hoje.month - 1) // 3) + 1
                data_inicio = datetime(hoje.year, (trimestre_atual - 1) * 3 + 1, 1)
                if trimestre_atual == 4:
                    data_fim = datetime(hoje.year + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(hoje.year, trimestre_atual * 3 + 1, 1) - timedelta(days=1)
            elif periodo == 'ano':
                data_inicio = datetime(hoje.year, 1, 1)
                data_fim = datetime(hoje.year, 12, 31)
            else:
                # Período personalizado - usar últimos 30 dias como padrão
                data_inicio = hoje - timedelta(days=30)
                data_fim = hoje
        else:
            # Converter strings para objetos datetime
            try:
                data_inicio = datetime.fromisoformat(data_inicio.replace('Z', '+00:00'))
                data_fim = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Formato de data inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)"}), 400
                
        # Aqui implementaria a geração do arquivo Excel
        # Por simplicidade, retornamos um erro indicando que a funcionalidade não está implementada
        return jsonify({"error": "Funcionalidade de exportação para Excel ainda não implementada"}), 501
        
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório Excel: {str(e)}")
        return jsonify({"error": f"Erro ao gerar relatório Excel: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)