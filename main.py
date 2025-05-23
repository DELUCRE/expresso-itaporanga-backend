import os
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, request, jsonify
from models.models import db, Entrega, AtualizacaoStatus, Usuario
from routes.user import user_bp
from routes.auth import auth_bp
from routes.entregas import entregas_bp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import entregas

app = FastAPI()

app.include_router(entregas.router)

app = FastAPI()

origins = [
    "https://expresso-itaporanga-frontend.vercel.app",  # Substitua pelo domínio real do seu frontend
    "https://*.vercel.app"  # Permite pré-visualizações da Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static')) 
CORS (app, resource={r"/*":{"origins":"*"}}, supports_credentials=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(entregas_bp, url_prefix="/api")

# Configuração do banco de dados para ambiente de produção
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://logistica_user:password@localhost:5432/logistica_db')
# Corrigir URL do PostgreSQL se necessário (para compatibilidade com Render)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

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

@app.route('/init-db', methods=['GET'])
def init_db():
    try:
        db.create_all()
        return jsonify({"message": "Banco de dados inicializado com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create-admin', methods=['GET'])
def create_admin():
    try:
        # Verificar se o usuário já existe
        existing_user = Usuario.query.filter_by(username='admin').first()
        if existing_user:
            # Atualizar o perfil se o usuário já existe
            existing_user.perfil = 'admin'
            db.session.commit()
            return jsonify({"message": "Usuário admin atualizado com perfil 'admin'!"}), 200
           
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
                destinatario="Livraria Central",
                origem="Porto Alegre, RS",
                destino="Florianópolis, SC",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(days=2),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() + timedelta(days=3),
                tipo_produto="Livros",
                peso=15.5,
                km=476.2,
                preco=350.00
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
                data_prevista_entrega=datetime.now() - timedelta(days=2),
                tipo_produto="Eletrônicos",
                peso=78.9,
                km=310.5,
                preco=690.00,
                motivo_atraso="Condições climáticas adversas"
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
                data_prevista_entrega=datetime.now() + timedelta(days=1),
                tipo_produto="Material didático",
                peso=45.2,
                km=12.3,
                preco=180.00
            ),
            Entrega(
                codigo_rastreio="ATR70497128",
                remetente="Empresa ABC Ltda",
                destinatario="Mercado Central",
                origem="São Paulo, SP",
                destino="Rio de Janeiro, RJ",
                status="Atrasado",
                data_criacao=datetime.now() - timedelta(days=4),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=1),
                tipo_produto="Alimentos",
                peso=120.5,
                km=430.8,
                preco=850.00,
                motivo_atraso="Congestionamento na rodovia"
            ),
            Entrega(
                codigo_rastreio="ASDFGHJKL",
                remetente="Tech Solutions SP",
                destinatario="Hospital Esperança",
                origem="São Paulo",
                destino="Recife",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=10),
                data_atualizacao=datetime.now() - timedelta(days=2),
                data_prevista_entrega=datetime.now() + timedelta(days=5),
                tipo_produto="Equipamentos médicos",
                peso=230.0,
                km=2680.5,
                preco=3200.00
            ),
            Entrega(
                codigo_rastreio="BRT9876543",
                remetente="Fazenda Orgânica",
                destinatario="Supermercado Natural",
                origem="Brasília, DF",
                destino="Goiânia, GO",
                status="Em processamento",
                data_criacao=datetime.now() - timedelta(days=1),
                data_atualizacao=datetime.now() - timedelta(hours=12),
                data_prevista_entrega=datetime.now() + timedelta(days=2),
                tipo_produto="Alimentos orgânicos",
                peso=85.3,
                km=209.0,
                preco=420.00
            ),
            Entrega(
                codigo_rastreio="QWER12345",
                remetente="Fábrica de Móveis",
                destinatario="Loja de Decoração",
                origem="Belo Horizonte, MG",
                destino="Vitória, ES",
                status="Pendente",
                data_criacao=datetime.now() - timedelta(hours=8),
                data_atualizacao=datetime.now() - timedelta(hours=6),
                data_prevista_entrega=datetime.now() + timedelta(days=4),
                tipo_produto="Móveis",
                peso=320.0,
                km=524.0,
                preco=1200.00
            ),
            Entrega(
                codigo_rastreio="ZXC098765",
                remetente="Distribuidora Têxtil",
                destinatario="Confecção Moda Verão",
                origem="Fortaleza, CE",
                destino="Natal, RN",
                status="Em trânsito",
                data_criacao=datetime.now() - timedelta(days=3),
                data_atualizacao=datetime.now() - timedelta(hours=18),
                data_prevista_entrega=datetime.now() + timedelta(days=1),
                tipo_produto="Tecidos",
                peso=180.0,
                km=537.0,
                preco=780.00
            ),
            Entrega(
                codigo_rastreio="MNB567890",
                remetente="Laboratório Farmacêutico",
                destinatario="Rede de Farmácias",
                origem="Campinas, SP",
                destino="Ribeirão Preto, SP",
                status="Problema na entrega",
                data_criacao=datetime.now() - timedelta(days=6),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=2),
                tipo_produto="Medicamentos",
                peso=35.0,
                km=206.0,
                preco=950.00,
                motivo_atraso="Endereço incorreto"
            ),
            Entrega(
                codigo_rastreio="POI123456",
                remetente="Editora Educacional",
                destinatario="Escola Municipal",
                origem="São Paulo, SP",
                destino="Campinas, SP",
                status="Aguardando retirada",
                data_criacao=datetime.now() - timedelta(days=5),
                data_atualizacao=datetime.now() - timedelta(days=1),
                data_prevista_entrega=datetime.now() - timedelta(days=1),
                tipo_produto="Material escolar",
                peso=150.0,
                km=99.0,
                preco=480.00
            )
        ]
        
        # Criar 10 entregas concluídas
        entregas_concluidas = [
            Entrega(
                codigo_rastreio="ENT123456",
                remetente="Distribuidora de Bebidas",
                destinatario="Restaurante Gourmet",
                origem="São Paulo, SP",
                destino="Santos, SP",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=15),
                data_atualizacao=datetime.now() - timedelta(days=13),
                data_prevista_entrega=datetime.now() - timedelta(days=13),
                tipo_produto="Bebidas",
                peso=120.0,
                km=79.0,
                preco=350.00
            ),
            Entrega(
                codigo_rastreio="ENT234567",
                remetente="Fábrica de Calçados",
                destinatario="Loja de Sapatos",
                origem="Novo Hamburgo, RS",
                destino="Porto Alegre, RS",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=20),
                data_atualizacao=datetime.now() - timedelta(days=18),
                data_prevista_entrega=datetime.now() - timedelta(days=18),
                tipo_produto="Calçados",
                peso=85.0,
                km=42.0,
                preco=280.00
            ),
            Entrega(
                codigo_rastreio="DEV123456",
                remetente="Loja Online",
                destinatario="Cliente Final",
                origem="Rio de Janeiro, RJ",
                destino="Niterói, RJ",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=25),
                data_atualizacao=datetime.now() - timedelta(days=20),
                data_prevista_entrega=datetime.now() - timedelta(days=22),
                tipo_produto="Eletrônicos",
                peso=3.5,
                km=13.0,
                preco=120.00,
                motivo_devolucao="Cliente recusou o recebimento"
            ),
            Entrega(
                codigo_rastreio="ENT345678",
                remetente="Indústria de Cosméticos",
                destinatario="Salão de Beleza",
                origem="Diadema, SP",
                destino="São Paulo, SP",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=18),
                data_atualizacao=datetime.now() - timedelta(days=16),
                data_prevista_entrega=datetime.now() - timedelta(days=16),
                tipo_produto="Cosméticos",
                peso=25.0,
                km=17.0,
                preco=180.00
            ),
            Entrega(
                codigo_rastreio="ENT456789",
                remetente="Distribuidora de Alimentos",
                destinatario="Supermercado",
                origem="Curitiba, PR",
                destino="Joinville, SC",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=22),
                data_atualizacao=datetime.now() - timedelta(days=19),
                data_prevista_entrega=datetime.now() - timedelta(days=19),
                tipo_produto="Alimentos",
                peso=450.0,
                km=117.0,
                preco=780.00
            ),
            Entrega(
                codigo_rastreio="DEV234567",
                remetente="Loja de Roupas",
                destinatario="Cliente Residencial",
                origem="Belo Horizonte, MG",
                destino="Contagem, MG",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=30),
                data_atualizacao=datetime.now() - timedelta(days=25),
                data_prevista_entrega=datetime.now() - timedelta(days=28),
                tipo_produto="Vestuário",
                peso=2.0,
                km=21.0,
                preco=90.00,
                motivo_devolucao="Produto com defeito"
            ),
            Entrega(
                codigo_rastreio="ENT567890",
                remetente="Fábrica de Brinquedos",
                destinatario="Loja de Presentes",
                origem="Recife, PE",
                destino="Olinda, PE",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=17),
                data_atualizacao=datetime.now() - timedelta(days=15),
                data_prevista_entrega=datetime.now() - timedelta(days=15),
                tipo_produto="Brinquedos",
                peso=45.0,
                km=11.0,
                preco=220.00
            ),
            Entrega(
                codigo_rastreio="ENT678901",
                remetente="Distribuidora de Livros",
                destinatario="Biblioteca Municipal",
                origem="Brasília, DF",
                destino="Goiânia, GO",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=28),
                data_atualizacao=datetime.now() - timedelta(days=25),
                data_prevista_entrega=datetime.now() - timedelta(days=25),
                tipo_produto="Livros",
                peso=320.0,
                km=209.0,
                preco=950.00
            ),
            Entrega(
                codigo_rastreio="ENT789012",
                remetente="Fábrica de Eletrônicos",
                destinatario="Loja de Informática",
                origem="Manaus, AM",
                destino="Belém, PA",
                status="Entregue",
                data_criacao=datetime.now() - timedelta(days=35),
                data_atualizacao=datetime.now() - timedelta(days=30),
                data_prevista_entrega=datetime.now() - timedelta(days=30),
                tipo_produto="Eletrônicos",
                peso=180.0,
                km=1290.0,
                preco=3800.00
            ),
            Entrega(
                codigo_rastreio="DEV345678",
                remetente="E-commerce",
                destinatario="Cliente Final",
                origem="Salvador, BA",
                destino="Feira de Santana, BA",
                status="Devolvido",
                data_criacao=datetime.now() - timedelta(days=40),
                data_atualizacao=datetime.now() - timedelta(days=35),
                data_prevista_entrega=datetime.now() - timedelta(days=38),
                tipo_produto="Smartphone",
                peso=0.5,
                km=108.0,
                preco=150.00,
                motivo_devolucao="Endereço não localizado"
            )
        ]
        
        # Adicionar todas as entregas ao banco de dados
        todas_entregas = entregas_atuais + entregas_concluidas
        for entrega in todas_entregas:
            db.session.add(entrega)
        db.session.commit()
        
        # Adicionar histórico de status para cada entrega
        for entrega in todas_entregas:
            # Primeiro status: Pendente (para todas as entregas)
            db.session.add(AtualizacaoStatus(
                entrega_id=entrega.id,
                status="Pendente",
                timestamp=entrega.data_criacao,
                observacoes="Entrega registrada no sistema"  # Corrigido para 'observacoes'
            ))
            
            # Segundo status: Em processamento (para todas exceto as que ainda estão pendentes)
            if entrega.status != "Pendente":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Em processamento",
                    timestamp=entrega.data_criacao + timedelta(hours=2),
                    observacoes="Entrega em processamento no centro de distribuição"  # Corrigido para 'observacoes'
                ))
            
            # Terceiro status: Em trânsito (para entregas que saíram para entrega)
            if entrega.status in ["Em trânsito", "Atrasado", "Entregue", "Devolvido", "Aguardando retirada", "Problema na entrega"]:
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Em trânsito",
                    timestamp=entrega.data_criacao + timedelta(hours=5),
                    observacoes="Entrega saiu para distribuição"  # Corrigido para 'observacoes'
                ))
            
            # Status específicos baseados no status atual da entrega
            if entrega.status == "Atrasado":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Atrasado",
                    timestamp=entrega.data_prevista_entrega + timedelta(hours=1),
                    observacoes=f"Entrega atrasada: {entrega.motivo_atraso or 'Motivo não especificado'}"  # Corrigido para 'observacoes'
                ))
            
            elif entrega.status == "Aguardando retirada":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Aguardando retirada",
                    timestamp=entrega.data_atualizacao,
                    observacoes="Entrega disponível para retirada no ponto de coleta"  # Corrigido para 'observacoes'
                ))
            
            elif entrega.status == "Problema na entrega":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Problema na entrega",
                    timestamp=entrega.data_atualizacao,
                    observacoes=f"Problema identificado: {entrega.motivo_atraso or 'Endereço incorreto'}"  # Corrigido para 'observacoes'
                ))
            
            elif entrega.status == "Entregue":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Entregue",
                    timestamp=entrega.data_atualizacao,
                    observacoes="Entrega realizada com sucesso"  # Corrigido para 'observacoes'
                ))
            
            elif entrega.status == "Devolvido":
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Em trânsito para devolução",
                    timestamp=entrega.data_atualizacao - timedelta(days=2),
                    observacoes=f"Iniciando processo de devolução: {entrega.motivo_devolucao or 'Motivo não especificado'}"  # Corrigido para 'observacoes'
                ))
                
                db.session.add(AtualizacaoStatus(
                    entrega_id=entrega.id,
                    status="Devolvido",
                    timestamp=entrega.data_atualizacao,
                    observacoes=f"Entrega devolvida ao remetente: {entrega.motivo_devolucao or 'Motivo não especificado'}"  # Corrigido para 'observacoes'
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
        motoristas_criados = []
        for m in motoristas:
            # Verificar se o motorista já existe
            existing = Usuario.query.filter_by(username=m["username"]).first()
            if existing:
                motoristas_criados.append(existing)
                continue
                
            # Criar novo motorista
            from werkzeug.security import generate_password_hash
            novo_motorista = Usuario(
                username=m["username"],
                password_hash=generate_password_hash(m["password"]),
                perfil=m["perfil"]
            )
            db.session.add(novo_motorista)
            db.session.commit()
            motoristas_criados.append(novo_motorista)
        
        # Associar motoristas às entregas
        entregas = Entrega.query.all()
        for i, entrega in enumerate(entregas):
            # Distribuir as entregas entre os motoristas
            motorista_index = i % len(motoristas_criados)
            entrega.motorista_id = motoristas_criados[motorista_index].id
        
        db.session.commit()
        
        return jsonify({
            "message": "Motoristas criados e associados às entregas com sucesso!",
            "motoristas": [m.username for m in motoristas_criados],
            "entregas_atualizadas": len(entregas)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api-info', methods=['GET'])
def api_info():
    # Obter a URL base da requisição
    base_url = request.url_root
    
    # Listar todos os endpoints disponíveis
    endpoints = {
        "entregas": f"{base_url}api/entregas",
        "usuarios": f"{base_url}api/usuarios",
        "relatorio_desempenho": f"{base_url}api/relatorio/desempenho",
        "relatorio_qualidade": f"{base_url}api/relatorio/qualidade",
        "auth_login": f"{base_url}auth/login",
        "auth_register": f"{base_url}auth/register",
        "auth_status": f"{base_url}auth/status"
    }
    
    return jsonify({
        "api_base_url": base_url,
        "endpoints": endpoints,
        "cors_enabled": True,
        "frontend_instructions": "Use estas URLs completas no frontend para acessar a API"
    }), 200
        
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
