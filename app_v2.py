from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import certifi
from bson import ObjectId
from functools import wraps


from auth import UsuarioAuth, Audit
from analytics import AnalisadorDados, GeradorRelatorios
from mfa import GerenciadorMFA


load_dotenv()


app = Flask(__name__)
CORS(app)


# conexao mongodb
MONGO_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['lixeira_inteligente']


# collections
collection_leituras = db['leituras']
collection_usuarios = db['usuarios']
collection_audit = db['auditoria']


# instancia de modulos
auth = UsuarioAuth(collection_usuarios)
audit = Audit(collection_audit)
analisador = AnalisadorDados(collection_leituras)
gerador_relatorios = GeradorRelatorios(analisador)
mfa = GerenciadorMFA(collection_usuarios)


# usuarios logados (sessao)
usuarios_logados = {}


# middleware de autenticacao
def verificar_autenticacao(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        rotas_publicas = ['/', '/api/saude', '/api/login', '/api/criar-usuario', '/api/mfa/verificar']
        
        if request.path in rotas_publicas:
            return f(*args, **kwargs)
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or token not in usuarios_logados:
            return jsonify({"erro": "Nao autorizado"}), 401
        
        return f(*args, **kwargs)
    
    return decorada


# rotas publicas


@app.route('/')
def home():
    return jsonify({
        "status": "API Lixeira Inteligente v2.0",
        "versao": "2.0.0",
        "integracoes": ["Cloud", "Seguranca", "Big Data", "IoT", "MFA"]
    })


@app.route('/api/saude', methods=['GET'])
def saude():
    try:
        client.admin.command('ping')
        return jsonify({
            "status": "Ok",
            "mongodb": "Conectado",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"status": "Erro", "erro": str(e)}), 500


# autenticacao


@app.route('/api/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        username = dados.get('username')
        senha = dados.get('senha')
        
        if not username or not senha:
            return jsonify({"erro": "username e senha obrigatorios"}), 400
        
        resultado = auth.autenticar(username, senha)
        
        if resultado['success']:
            token = resultado['token']
            usuarios_logados[token] = username
            
            audit.registrar(username, "LOGIN", "usuario fez login", "sucesso")
            
            usuario_doc = collection_usuarios.find_one({"username": username})
            mfa_ativado = usuario_doc.get("mfa_ativado", False) if usuario_doc else False
            
            return jsonify({
                "sucesso": True,
                "token": token,
                "usuario": resultado['usuario'],
                "mfa_ativado": mfa_ativado,
                "requer_mfa": mfa_ativado
            }), 200
        else:
            audit.registrar(username, "LOGIN", f"Falha: {resultado['erro']}", "erro")
            return jsonify({"sucesso": False, "erro": resultado['erro']}), 401
            
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/criar-usuario', methods=['POST'])
@verificar_autenticacao
def criar_usuario():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        usuario_doc = collection_usuarios.find_one({"username": usuario_logado})
        if usuario_doc.get('role') != 'admin':
            audit.registrar(usuario_logado, "CREATE_USER", "tentativa nao autorizada", "erro")
            return jsonify({"erro": "apenas admin pode criar usuarios"}), 403
        
        dados = request.get_json()
        resultado = auth.criar_usuario(
            username=dados.get('username'),
            senha=dados.get('senha'),
            nome=dados.get('nome'),
            role=dados.get('role', 'usuario'),
            email=dados.get('email')
        )
        
        audit.registrar(usuario_logado, "CREATE_USER", f"criado usuario: {dados.get('username')}", "sucesso")
        
        return jsonify(resultado), 201 if resultado['success'] else 400
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/usuarios', methods=['GET'])
@verificar_autenticacao
def listar_usuarios():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        usuario_doc = collection_usuarios.find_one({"username": usuario_logado})
        if usuario_doc.get('role') not in ['admin', 'gestor']:
            return jsonify({"erro": "sem permissao"}), 403
        
        usuarios = auth.listar_usuarios()
        
        audit.registrar(usuario_logado, "READ", "listou usuarios", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "total": len(usuarios),
            "usuarios": usuarios
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# dados


@app.route('/api/dados', methods=['POST'])
def receber_dados():
    try:
        dados = request.get_json()
        
        required_fields = ['peso_kg', 'sensor_id']
        if not all(field in dados for field in required_fields):
            return jsonify({"erro": "campos obrigatorios faltando"}), 400
        
        documento = {
            "timestamp": dados.get('timestamp', datetime.utcnow().isoformat()),
            "peso_kg": float(dados['peso_kg']),
            "sensor_id": dados.get('sensor_id'),
            "temperatura": float(dados.get('temperatura', 0)),
            "umidade": float(dados.get('umidade', 0)),
            "localizacao": dados.get('localizacao', 'nao especificado')
        }
        
        resultado = collection_leituras.insert_one(documento)
        
        audit.registrar("ESP32", "CREATE", f"dado recebido de {dados.get('sensor_id')}", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "id": str(resultado.inserted_id),
            "mensagem": "dados recebidos"
        }), 201
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/leituras', methods=['GET'])
@verificar_autenticacao
def obter_leituras():
    try:
        limite = int(request.args.get('limite', 100))
        sensor_id = request.args.get('sensor_id')
        
        filtro = {}
        if sensor_id:
            filtro['sensor_id'] = sensor_id
        
        leituras = list(collection_leituras.find(
            filtro,
            {'_id': 0}
        ).sort('timestamp', -1).limit(limite))
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "READ", f"consultou {len(leituras)} leituras", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "total": len(leituras),
            "leituras": leituras
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/estatisticas', methods=['GET'])
@verificar_autenticacao
def obter_estatisticas():
    try:
        sensor_id = request.args.get('sensor_id', None)
        
        filtro_stage = {}
        if sensor_id:
            filtro_stage = {"$match": {"sensor_id": sensor_id}}
        
        pipeline = []
        if filtro_stage:
            pipeline.append(filtro_stage)
        
        pipeline.append({
            "$group": {
                "_id": None,
                "peso_medio": {"$avg": "$peso_kg"},
                "peso_total": {"$sum": "$peso_kg"},
                "peso_maximo": {"$max": "$peso_kg"},
                "peso_minimo": {"$min": "$peso_kg"},
                "temperatura_media": {"$avg": "$temperatura"},
                "umidade_media": {"$avg": "$umidade"},
                "total_leituras": {"$sum": 1}
            }
        })
        
        resultado = list(collection_leituras.aggregate(pipeline))
        
        if resultado:
            stats = resultado[0]
            stats.pop('_id', None)
            
            for chave in stats:
                if isinstance(stats[chave], float):
                    stats[chave] = round(stats[chave], 2)
            
            return jsonify({
                "sucesso": True,
                "sensor_filtro": sensor_id if sensor_id else "todos",
                "estatisticas": stats
            }), 200
        else:
            return jsonify({
                "sucesso": True,
                "estatisticas": {
                    "peso_medio": 0,
                    "peso_total": 0,
                    "peso_maximo": 0,
                    "peso_minimo": 0,
                    "temperatura_media": 0,
                    "umidade_media": 0,
                    "total_leituras": 0
                }
            }), 200
            
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/sensores', methods=['GET'])
@verificar_autenticacao
def listar_sensores():
    try:
        sensores = collection_leituras.distinct('sensor_id')
        return jsonify({
            "sucesso": True,
            "total_sensores": len(sensores),
            "sensores": sensores
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# analytics


@app.route('/api/analytics/padroes', methods=['GET'])
@verificar_autenticacao
def padroes_geracao():
    try:
        dias = int(request.args.get('dias', 30))
        
        padroes = analisador.analisar_padroes(dias=dias)
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "ANALYZE", f"analise de padroes ({dias} dias)", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "padroes": padroes
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/analytics/predicoes', methods=['GET'])
@verificar_autenticacao
def predicoes():
    try:
        dias = int(request.args.get('dias', 7))
        
        predicoes_result = analisador.prever_geracao(dias_futuros=dias)
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "ANALYZE", f"predicao ({dias} dias)", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "predicoes": predicoes_result
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/analytics/anomalias', methods=['GET'])
@verificar_autenticacao
def detectar_anomalias():
    try:
        sensibilidade = float(request.args.get('sensibilidade', 2.0))
        
        anomalias = analisador.detectar_anomalias(sensibilidade=sensibilidade)
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "ANALYZE", "deteccao de anomalias", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "total_anomalias": len(anomalias),
            "anomalias": anomalias
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# relatorios


@app.route('/api/relatorios/executivo', methods=['GET'])
@verificar_autenticacao
def relatorio_executivo():
    try:
        relatorio = analisador.gerar_relatorio_executivo()
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "EXPORT", "relatorio executivo gerado", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "relatorio": relatorio
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/relatorios/csv', methods=['GET'])
@verificar_autenticacao
def relatorio_csv():
    try:
        csv_data = gerador_relatorios.gerar_csv()
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        audit.registrar(usuario_logado, "EXPORT", "relatorio csv exportado", "sucesso")
        
        return csv_data, 200, {
            'Content-Disposition': 'attachment; filename="relatorio_lixeira.csv"',
            'Content-Type': 'text/csv'
        }
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# mfa


@app.route('/api/mfa/gerar-qrcode', methods=['POST'])
@verificar_autenticacao
def gerar_qrcode_mfa():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        resultado = mfa.gerar_secret_mfa(usuario_logado)
        
        audit.registrar(usuario_logado, "MFA_SETUP", "iniciou configuracao de mfa", "sucesso")
        
        return jsonify({
            "sucesso": True,
            "secret": resultado['secret'],
            "qr_code": resultado['qr_code']
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/mfa/ativar', methods=['POST'])
@verificar_autenticacao
def ativar_mfa_endpoint():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        dados = request.get_json()
        codigo = dados.get('codigo')
        
        resultado = mfa.ativar_mfa(usuario_logado, None, codigo)
        
        if resultado['success']:
            audit.registrar(usuario_logado, "MFA_ATIVADO", "mfa ativado com sucesso", "sucesso")
            return jsonify({"sucesso": True, "mensagem": resultado['mensagem']}), 200
        else:
            audit.registrar(usuario_logado, "MFA_ATIVACAO", f"falha: {resultado['erro']}", "erro")
            return jsonify({"sucesso": False, "erro": resultado['erro']}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/mfa/debug', methods=['GET'])
@verificar_autenticacao
def debug_mfa():
    """Debug endpoint - mostra secret temporário guardado"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        secret_temporario = mfa.secrets_temporarios.get(usuario_logado)
        
        if not secret_temporario:
            return jsonify({
                "usuario": usuario_logado,
                "secret_temporario": None,
                "mensagem": "nenhum secret temporario guardado"
            }), 200
        
        import pyotp
        import time
        totp = pyotp.TOTP(secret_temporario)
        codigo_agora = totp.now()
        timestamp = int(time.time())
        
        return jsonify({
            "usuario": usuario_logado,
            "secret_temporario": secret_temporario,
            "codigo_esperado_agora": codigo_agora,
            "timestamp": timestamp,
            "mensagem": "use este codigo para testar a ativacao"
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/mfa/verificar', methods=['POST'])
def verificar_mfa():
    try:
        dados = request.get_json()
        username = dados.get('username')
        codigo = dados.get('codigo')
        
        resultado = mfa.verificar_codigo_mfa(username, codigo)
        
        return jsonify(resultado), 200 if resultado['success'] else 401
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# auditoria


@app.route('/api/auditoria/logs', methods=['GET'])
@verificar_autenticacao
def auditoria_logs():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        usuario_logado = usuarios_logados.get(token)
        
        usuario_doc = collection_usuarios.find_one({"username": usuario_logado})
        if usuario_doc.get('role') != 'admin':
            return jsonify({"erro": "apenas admin pode acessar auditoria"}), 403
        
        limite = int(request.args.get('limite', 100))
        
        logs = audit.listar_logs(limite=limite)
        
        return jsonify({
            "sucesso": True,
            "total": len(logs),
            "logs": logs
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# tratamento de erros


@app.errorhandler(404)
def nao_encontrado(error):
    return jsonify({"erro": "endpoint nao encontrado"}), 404


@app.errorhandler(500)
def erro_servidor(error):
    return jsonify({"erro": "erro interno do servidor"}), 500


# main


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True') == 'True'
    
    print(f"iniciando api na porta {port}")
    print("integracoes: Cloud, Seguranca, Big Data, IoT, MFA")
    
    app.run(host='0.0.0.0', port=port, debug=debug)