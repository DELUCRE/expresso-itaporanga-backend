import os
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from models.models import db, Entrega, AtualizacaoStatus, Usuario

# Criar a aplicação Flask
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app, resources={r"/": {"origins": ""}}, supports_credentials=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Configuração do banco de dados para ambiente de produção
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://logistica_user:password@localhost:5432/logistica_db')
# Corrigir URL do PostgreSQL se necessário (para compatibilidade com Render)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Importar blueprints após definir app
from routes.auth import auth_bp
from routes.entregas import entregas_bp
from routes.user import user_bp

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(entregas_bp, url_prefix="/api")
app.register_blueprint(user_bp, url_prefix="/api")

# Função auxiliar para verificar autenticação
def check_auth():
    # Implementação simplificada - em produção, use autenticação real
    return None  # Retorna None se autenticado, ou uma resposta de erro se não

# Novo endpoint para o formulário de contato
@app.route('/api/contato', methods=['POST'])
def handle_contact_form():
    try:
        data = request.form
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
        with open(os.path.join(os.path.dirname(_file_), 'mensagens_contato.txt'), 'a', encoding='utf-8') as f:
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
        km_total = sum(e.km for e in entregas if hasattr(e, 'km') and e.km is not None)
        peso_total = sum(e.peso for e in entregas if hasattr(e, 'peso') and e.peso is not None)
        receita_total = sum(e.preco for e in entregas if hasattr(e, 'preco') and e.preco is not None)
        
        # Calcular KPIs derivados
        custo_por_km = receita_total / km_total if km_total > 0 else 0
        receita_por_entrega = receita_total / total_entregas if total_entregas > 0 else 0
        
        # Agrupar por motorista (se disponível)
        desempenho_motoristas = []
        if any(hasattr(e, 'motorista_id') and e.motorista_id is not None for e in entregas):
            # Obter todos os motoristas que têm entregas no período
            motorista_ids = set(e.motorista_id for e in entregas if hasattr(e, 'motorista_id') and e.motorista_id is not None)
            for m_id in motorista_ids:
                motorista = Usuario.query.get(m_id)
                if not motorista:
                    continue
                    
                # Filtrar entregas deste motorista
                entregas_motorista = [e for e in entregas if hasattr(e, 'motorista_id') and e.motorista_id == m_id]
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
            if hasattr(e, 'motivo_atraso') and e.motivo_atraso:
                motivo = e.motivo_atraso.strip()
                motivos_atraso[motivo] = motivos_atraso.get(motivo, 0) + 1
        
        # Analisar motivos de devolução
        motivos_devolucao = {}
        for e in entregas:
            if hasattr(e, 'motivo_devolucao') and e.motivo_devolucao:
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
                'quantidade': quantidade
            })
        
        for motivo, quantidade in motivos_devolucao.items():
            motivos_problemas.append({
                'motivo': f"Devolução: {motivo}",
                'quantidade': quantidade
            })
        
        # Ordenar por quantidade (decrescente)
        motivos_problemas.sort(key=lambda x: x['quantidade'], reverse=True)
        
        # Converter problemas por região para o formato esperado pelo frontend
        problemas_regiao = []
        for regiao, quantidade in problemas_por_regiao.items():
            problemas_regiao.append({
                'regiao': regiao,
                'quantidade': quantidade
            })
        
        # Ordenar por quantidade (decrescente)
        problemas_regiao.sort(key=lambda x: x['quantidade'], reverse=True)
        
        # Preparar resposta
        response = {
            'periodo': {
                'inicio': data_inicio.isoformat(),
                'fim': data_fim.isoformat()
            },
            'kpis_qualidade': {
                'total_problemas': total_problemas,
                'total_atrasos': total_atrasos,
                'total_devolucoes': total_devolucoes
            },
            'motivos_problemas': motivos_problemas,
            'problemas_por_regiao': problemas_regiao
        }
        
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório de qualidade: {str(e)}")
        return jsonify({"error": f"Erro ao gerar relatório: {str(e)}"}), 500

# Endpoints para dados de demonstração
@app.route('/api/relatorio/desempenho-demo', methods=['GET'])
def relatorio_desempenho_demo():
    try:
        response = {
            'periodo': {
                'inicio': '2025-04-01T00:00:00',
                'fim': '2025-04-30T23:59:59'
            },
            'kpis_gerais': {
                'total_entregas': 120,
                'entregas_no_prazo': 95,
                'entregas_atrasadas': 15,
                'entregas_devolvidas': 10,
                'entregas_pendentes': 5,
                'taxa_entrega': 79.2,
                'taxa_atraso': 12.5,
                'taxa_devolucao': 8.3,
                'tempo_medio_entrega': 2.3
            },
            'kpis_avancados': {
                'km_total': 5430,
                'peso_total': 2150,
                'receita_total': 15800,
                'custo_por_km': 2.91,
                'receita_por_entrega': 131.67
            },
            'desempenho_motoristas': [
                {
                    'id': 1,
                    'nome': 'João Silva',
                    'total_entregas': 40,
                    'entregas_no_prazo': 35,
                    'taxa_entrega': 87.5
                },
                {
                    'id': 2,
                    'nome': 'Maria Oliveira',
                    'total_entregas': 35,
                    'entregas_no_prazo': 30,
                    'taxa_entrega': 85.7
                },
                {
                    'id': 3,
                    'nome': 'Carlos Santos',
                    'total_entregas': 45,
                    'entregas_no_prazo': 30,
                    'taxa_entrega': 66.7
                }
            ],
            'entregas_por_dia': [
                {'data': '2025-04-01', 'total': 5},
                {'data': '2025-04-02', 'total': 7},
                {'data': '2025-04-03', 'total': 4},
                {'data': '2025-04-04', 'total': 6},
                {'data': '2025-04-05', 'total': 3},
                {'data': '2025-04-06', 'total': 2},
                {'data': '2025-04-07', 'total': 8},
                {'data': '2025-04-08', 'total': 5},
                {'data': '2025-04-09', 'total': 6},
                {'data': '2025-04-10', 'total': 7},
                {'data': '2025-04-11', 'total': 4},
                {'data': '2025-04-12', 'total': 3},
                {'data': '2025-04-13', 'total': 2},
                {'data': '2025-04-14', 'total': 5},
                {'data': '2025-04-15', 'total': 6},
                {'data': '2025-04-16', 'total': 7},
                {'data': '2025-04-17', 'total': 5},
                {'data': '2025-04-18', 'total': 4},
                {'data': '2025-04-19', 'total': 3},
                {'data': '2025-04-20', 'total': 2},
                {'data': '2025-04-21', 'total': 6},
                {'data': '2025-04-22', 'total': 5},
                {'data': '2025-04-23', 'total': 4},
                {'data': '2025-04-24', 'total': 3},
                {'data': '2025-04-25', 'total': 5},
                {'data': '2025-04-26', 'total': 2},
                {'data': '2025-04-27', 'total': 1},
                {'data': '2025-04-28', 'total': 4},
                {'data': '2025-04-29', 'total': 5},
                {'data': '2025-04-30', 'total': 6}
            ],
            'distribuicao_status': [
                {'status': 'Entregue', 'total': 95},
                {'status': 'Atrasado', 'total': 15},
                {'status': 'Devolvido', 'total': 10},
                {'status': 'Pendente', 'total': 5}
            ]
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/relatorio/qualidade-demo', methods=['GET'])
def relatorio_qualidade_demo():
    try:
        response = {
            'periodo': {
                'inicio': '2025-04-01T00:00:00',
                'fim': '2025-04-30T23:59:59'
            },
            'kpis_qualidade': {
                'total_problemas': 8,
                'total_atrasos': 15,
                'total_devolucoes': 10
            },
            'motivos_problemas': [
                {'motivo': 'Atraso: Condições climáticas', 'quantidade': 7},
                {'motivo': 'Atraso: Trânsito intenso', 'quantidade': 5},
                {'motivo': 'Atraso: Problema no veículo', 'quantidade': 3},
                {'motivo': 'Devolução: Destinatário ausente', 'quantidade': 5},
                {'motivo': 'Devolução: Endereço incorreto', 'quantidade': 3},
                {'motivo': 'Devolução: Recusa do destinatário', 'quantidade': 2}
            ],
            'problemas_por_regiao': [
                {'regiao': 'SP', 'quantidade': 10},
                {'regiao': 'RJ', 'quantidade': 8},
                {'regiao': 'MG', 'quantidade': 6},
                {'regiao': 'RS', 'quantidade': 5},
                {'regiao': 'PR', 'quantidade': 4}
            ]
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-admin', methods=['GET'])
def create_admin():
    try:
        # Verificar se o usuário já existe
        existing_user = Usuario.query.filter_by(username='admin').first()
        if existing_user:
            return jsonify({"message": "Usuário admin já existe!"}), 200
        
        # Criar usuário admin
        from werkzeug.security import generate_password_hash
        admin = Usuario(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            perfil='admin'  # Adicionar perfil admin
        )
        db.session.add(admin)
        db.session.commit()
        return jsonify({"message": "Usuário admin criado com sucesso! Username: admin, Senha: admin123, Perfil: admin"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-sample-data', methods=['GET'])
def create_sample_data():
    try:
        # Limpar dados existentes para evitar duplicações
        AtualizacaoStatus.query.delete()
        Entrega.query.delete()
        
        # Atualizar usuário admin para ter perfil correto
        admin = Usuario.query.filter_by(username='admin').first()
        if admin:
            admin.perfil = 'admin'
        else:
            from werkzeug.security import generate_password_hash
            admin = Usuario(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                perfil='admin'
            )
            db.session.add(admin)
        
        db.session.commit()
        
        # Criar 10 entregas atuais (não concluídas)
        entregas_atuais = [
            Entrega(
                codigo_rastreio="TRACK163630",
                remetente="Distribuidora de Livros",
                destinatario="Livraria",
                origem="Porto Alegre, RS",
                destino="Florianópolis, SC",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(days=2),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() + timedelta(days=1)
            ),
            Entrega(
                codigo_rastreio="ATR13359540",
                remetente="Indústria Nacional",
                destinatario="Loja de Departamentos",
                origem="Curitiba, PR",
                destino="Florianópolis, SC",
                status="Atrasado",
                data_criacao=datetime.now() - timedelta(days=5),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=2)
            ),
            Entrega(
                codigo_rastreio="DA1AB1EU",
                remetente="Gráfica Nordeste",
                destinatario="Universidade Federal do Ceará",
                origem="Fortaleza",
                destino="Fortaleza",
                status="Aguardando retirada",
                data_criacao=datetime.now() - timedelta(days=3),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() + timedelta(days=1)
            ),
            Entrega(
                codigo_rastreio="ATR70497128",
                remetente="Empresa ABC Ltda",
                destinatario="Mercado Central",
                origem="São Paulo, SP",
                destino="Rio de Janeiro, RJ",
                status="Atrasado",
                data_criacao=datetime.now() - timedelta(days=5),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=2)
            ),
            Entrega(
                codigo_rastreio="ASDFGHJKL",
                remetente="Tech Solutions SP",
                destinatario="Hospital Esperança",
                origem="São Paulo",
                destino="Recife",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=15),
                data_atualizacao=datetime.now() - timedelta(days=10),
                data_prevista_entrega=datetime.now() - timedelta(days=8)
            ),
            Entrega(
                codigo_rastreio="QWERTYUIOP",
                remetente="Fábrica de Móveis",
                destinatario="Loja de Decoração",
                origem="Belo Horizonte, MG",
                destino="Brasília, DF",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(days=1),
                data_atualizacao=datetime.now(),
                data_prevista_entrega=datetime.now() + timedelta(days=3)
            ),
            Entrega(
                codigo_rastreio="ZXCVBNM123",
                remetente="Distribuidora de Alimentos",
                destinatario="Restaurante Gourmet",
                origem="Campinas, SP",
                destino="São Paulo, SP",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=2),
                data_atualizacao=datetime.now() - timedelta(hours=12),
                data_prevista_entrega=datetime.now() + timedelta(hours=6)
            ),
            Entrega(
                codigo_rastreio="POIUYT7890",
                remetente="Laboratório Farmacêutico",
                destinatario="Farmácia Popular",
                origem="Goiânia, GO",
                destino="Anápolis, GO",
                status="Aguardando retirada",
                data_criacao=datetime.now() - timedelta(days=4),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=1)
            ),
            Entrega(
                codigo_rastreio="LKJHGF5432",
                remetente="Editora Educacional",
                destinatario="Escola Municipal",
                origem="Salvador, BA",
                destino="Feira de Santana, BA",
                status="Problema na entrega",
                data_criacao=datetime.now() - timedelta(days=7),
                data_atualizacao=datetime.now() - timedelta(days=2),
                data_prevista_entrega=datetime.now() - timedelta(days=3),
                motivo_atraso="Endereço incompleto"
            ),
            Entrega(
                codigo_rastreio="MNBVCXZ0987",
                remetente="Loja de Eletrônicos",
                destinatario="Cliente Final",
                origem="Manaus, AM",
                destino="Belém, PA",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=5),
                data_atualizacao=datetime.now() - timedelta(days=2),
                data_prevista_entrega=datetime.now() + timedelta(days=2)
            )
        ]
        
        # Criar 10 entregas concluídas
        entregas_concluidas = [
            Entrega(
                codigo_rastreio="ENTREGA001",
                remetente="Fábrica de Calçados",
                destinatario="Loja de Sapatos",
                origem="Novo Hamburgo, RS",
                destino="Porto Alegre, RS",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=15),
                data_atualizacao=datetime.now() - timedelta(days=12),
                data_prevista_entrega=datetime.now() - timedelta(days=13)
            ),
            Entrega(
                codigo_rastreio="ENTREGA002",
                remetente="Distribuidora de Bebidas",
                destinatario="Supermercado",
                origem="Ribeirão Preto, SP",
                destino="São Carlos, SP",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=10),
                data_atualizacao=datetime.now() - timedelta(days=8),
                data_prevista_entrega=datetime.now() - timedelta(days=7)
            ),
            Entrega(
                codigo_rastreio="ENTREGA003",
                remetente="Indústria Têxtil",
                destinatario="Loja de Roupas",
                origem="Blumenau, SC",
                destino="Joinville, SC",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=12),
                data_atualizacao=datetime.now() - timedelta(days=10),
                data_prevista_entrega=datetime.now() - timedelta(days=9)
            ),
            Entrega(
                codigo_rastreio="ENTREGA004",
                remetente="Fábrica de Chocolates",
                destinatario="Confeitaria",
                origem="Gramado, RS",
                destino="Caxias do Sul, RS",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=8),
                data_atualizacao=datetime.now() - timedelta(days=6),
                data_prevista_entrega=datetime.now() - timedelta(days=5)
            ),
            Entrega(
                codigo_rastreio="ENTREGA005",
                remetente="Distribuidora de Materiais",
                destinatario="Construtora",
                origem="Recife, PE",
                destino="Olinda, PE",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=20),
                data_atualizacao=datetime.now() - timedelta(days=17),
                data_prevista_entrega=datetime.now() - timedelta(days=18)
            ),
            Entrega(
                codigo_rastreio="DEVOL001",
                remetente="Loja Online",
                destinatario="Cliente Residencial",
                origem="São Paulo, SP",
                destino="Campinas, SP",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=18),
                data_atualizacao=datetime.now() - timedelta(days=15),
                data_prevista_entrega=datetime.now() - timedelta(days=16),
                motivo_devolucao="Destinatário ausente"
            ),
            Entrega(
                codigo_rastreio="DEVOL002",
                remetente="Loja de Informática",
                destinatario="Escritório Comercial",
                origem="Curitiba, PR",
                destino="Londrina, PR",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=14),
                data_atualizacao=datetime.now() - timedelta(days=10),
                data_prevista_entrega=datetime.now() - timedelta(days=12),
                motivo_devolucao="Endereço não localizado"
            ),
            Entrega(
                codigo_rastreio="ENTREGA006",
                remetente="Distribuidora de Livros",
                destinatario="Biblioteca Municipal",
                origem="Belo Horizonte, MG",
                destino="Contagem, MG",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=25),
                data_atualizacao=datetime.now() - timedelta(days=22),
                data_prevista_entrega=datetime.now() - timedelta(days=23)
            ),
            Entrega(
                codigo_rastreio="DEVOL003",
                remetente="Loja de Presentes",
                destinatario="Cliente Residencial",
                origem="Fortaleza, CE",
                destino="Caucaia, CE",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=30),
                data_atualizacao=datetime.now() - timedelta(days=25),
                data_prevista_entrega=datetime.now() - timedelta(days=28),
                motivo_devolucao="Recusado pelo destinatário"
            ),
            Entrega(
                codigo_rastreio="ENTREGA007",
                remetente="Indústria de Cosméticos",
                destinatario="Salão de Beleza",
                origem="Rio de Janeiro, RJ",
                destino="Niterói, RJ",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=22),
                data_atualizacao=datetime.now() - timedelta(days=20),
                data_prevista_entrega=datetime.now() - timedelta(days=19)
            )
        ]
        
        # Juntar todas as entregas
        todas_entregas = entregas_atuais + entregas_concluidas
        
        # Adicionar ao banco de dados
        for entrega in todas_entregas:
            db.session.add(entrega)
        
        db.session.commit()
        
        # Adicionar atualizações de status para cada entrega
        for entrega in todas_entregas:
            # Adicionar status inicial "Registrado"
            db.session.add(AtualizacaoStatus(
                entrega_id=entrega.id,
                status="Registrado",
                timestamp=entrega.data_criacao,
                observacoes="Entrega registrada no sistema"
            ))
            
            # Adicionar status intermediário "Em trânsito" para todas as entregas
            db.session.add(AtualizacaoStatus(
                entrega_id=entrega.id,
                status="Em trânsito",
                timestamp=entrega.data_criacao + timedelta(hours=random.randint(1, 24)),
                observacoes="Entrega em rota de distribuição"
            ))
            
            # Adicionar status final baseado no status atual da entrega
            if entrega.status == "Entregue":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Entregue",
                    timestamp=entrega.data_atualizacao,
                    observacoes="Entrega realizada com sucesso"
                ))
            elif entrega.status == "Devolvido":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Problema na entrega",
                    timestamp=entrega.data_atualizacao - timedelta(days=1),
                    observacoes=f"Problema na entrega: {entrega.motivo_devolucao or 'Motivo não especificado'}"
                ))
                
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Devolvido",
                    timestamp=entrega.data_atualizacao,
                    observacoes=f"Entrega devolvida ao remetente: {entrega.motivo_devolucao or 'Motivo não especificado'}"
                ))
        
        db.session.commit()
        
        return jsonify({
            "message": "Dados de exemplo criados com sucesso!",
            "entregas_atuais": len(entregas_atuais),
            "entregas_concluidas": len(entregas_concluidas),
            "total_entregas": len(todas_entregas)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/create-drivers', methods=['GET'])
def create_drivers():
    try:
        import random
        
        # Criar motoristas
        motoristas = [
            {
                "username": "motorista1",
                "password": "senha123",
                "nome": "João Silva",
                "perfil": "motorista"
            },
            {
                "username": "motorista2",
                "password": "senha123",
                "nome": "Maria Oliveira",
                "perfil": "motorista"
            },
            {
                "username": "motorista3",
                "password": "senha123",
                "nome": "Carlos Santos",
                "perfil": "motorista"
            },
            {
                "username": "motorista4",
                "password": "senha123",
                "nome": "Ana Pereira",
                "perfil": "motorista"
            },
            {
                "username": "motorista5",
                "password": "senha123",
                "nome": "Roberto Almeida",
                "perfil": "motorista"
            }
        ]
        
        # Adicionar motoristas ao banco de dados
        from werkzeug.security import generate_password_hash
        motoristas_criados = []
        
        for m in motoristas:
            # Verificar se o motorista já existe
            existing = Usuario.query.filter_by(username=m["username"]).first()
            if existing:
                existing.perfil = m["perfil"]
                motoristas_criados.append(existing)
                continue
                
            # Criar novo motorista
            motorista = Usuario(
                username=m["username"],
                password_hash=generate_password_hash(m["password"]),
                perfil=m["perfil"]
            )
            db.session.add(motorista)
            motoristas_criados.append(motorista)
        
        db.session.commit()
        
        # Associar motoristas às entregas
        entregas = Entrega.query.all()
        for entrega in entregas:
            # Atribuir um motorista aleatório
            motorista = random.choice(motoristas_criados)
            entrega.motorista_id = motorista.id
        
        db.session.commit()
        
        return jsonify({
            "message": "Motoristas criados e associados às entregas com sucesso!",
            "entregas_atualizadas": len(entregas),
            "motoristas": [m["username"] for m in motoristas]
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api-info', methods=['GET'])
def api_info():
    base_url = "https://expresso-itaporanga-api.onrender.com"
    
    endpoints = {
        "auth_login": f"{base_url}/auth/login",
        "auth_status": f"{base_url}/auth/status",
        "entregas": f"{base_url}/api/entregas",
        "relatorio_desempenho": f"{base_url}/api/relatorio/desempenho",
        "relatorio_qualidade": f"{base_url}/api/relatorio/qualidade",
        "usuarios": f"{base_url}/api/usuarios",
        "auth_register": f"{base_url}/auth/register"
    }
    
    return jsonify({
        "api_base_url": base_url,
        "endpoints": endpoints,
        "cors_enabled": True,
        "frontend_instructions": "Use estas URLs completas no frontend para acessar a API"
    }), 200

if __name__ == '_main_':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
