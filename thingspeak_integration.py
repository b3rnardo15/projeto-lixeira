import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import certifi
import time
from threading import Thread

load_dotenv()

#  CONFIGURAÇÕES THINGSPEAK 
THINGSPEAK_CHANNEL_ID = "3185970"  # Seu Channel ID
THINGSPEAK_API_KEY = "9TTBK97R2SUBNYIN"  # Read API Key
THINGSPEAK_BASE_URL = "https://api.thingspeak.com/channels"

# CONFIGURAÇÕES MONGODB 
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = 'lixeira_inteligente'
COLLECTION_NAME = 'leituras'

#  CONFIGURAÇÕES INTEGRAÇÃO 
INTERVALO_COLETA = 60  # A cada 60 segundos


class ThingSpeakIntegration:
    """Classe para integração com ThingSpeak"""

    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.conectar_mongodb()

    def conectar_mongodb(self):
        """Conecta ao MongoDB"""
        try:
            self.mongo_client = pymongo.MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
            self.db = self.mongo_client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            print("✅ Conectado ao MongoDB")
        except Exception as e:
            print(f"❌ Erro ao conectar MongoDB: {e}")

    def buscar_dados_thingspeak(self):
        """
        Busca os últimos dados do ThingSpeak
        Retorna: dict com os dados ou None
        """
        try:
            url = f"{THINGSPEAK_BASE_URL}/{THINGSPEAK_CHANNEL_ID}/feeds.json"
            params = {
                'api_key': THINGSPEAK_API_KEY,
                'results': 1  # Pega só a última leitura
            }

            print(f"🔍 DEBUG: Tentando acessar: {url}")
            print(f"🔍 DEBUG: Parâmetros: {params}")

            response = requests.get(url, params=params, timeout=10)
            
            print(f"🔍 DEBUG: Status Code: {response.status_code}")
            print(f"🔍 DEBUG: Response: {response.text}")

            response.raise_for_status()

            dados = response.json()
            print(f"🔍 DEBUG: JSON recebido: {dados}")

            if 'feeds' in dados and len(dados['feeds']) > 0:
                feed = dados['feeds'][0]
                print(f"🔍 DEBUG: Feed encontrado: {feed}")
                
                return {
                    'field1': float(feed.get('field1', 0)),
                    'timestamp_thingspeak': feed.get('created_at'),
                    'channel_id': THINGSPEAK_CHANNEL_ID,
                    'fonte': 'thingspeak'
                }
            else:
                print("⚠️  DEBUG: Nenhum feed encontrado ou 'feeds' vazio")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar do ThingSpeak: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return None

    def formatar_para_mongodb(self, dados_ts):
        """
        Formata dados do ThingSpeak para o formato do MongoDB
        """
        if not dados_ts:
            return None

        return {
            'peso_kg': dados_ts['field1'],
            'sensor_id': 'esp32-lixeira-001',
            'temperatura': 0.0,  # Pode adicionar campo field2, field3 etc
            'umidade': 0.0,
            'localizacao': 'entrada',
            'timestamp': datetime.utcnow(),
            'timestamp_thingspeak': dados_ts['timestamp_thingspeak'],
            'fonte': 'thingspeak',
            'status': 'ativo'
        }

    def salvar_no_mongodb(self, documento):
        """Salva o documento no MongoDB"""
        try:
            resultado = self.collection.insert_one(documento)
            print(f"✅ Dado salvo - ID: {resultado.inserted_id}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
            return False

    def verificar_duplicata(self, timestamp_ts):
        """Verifica se o timestamp já existe para evitar duplicatas"""
        try:
            existe = self.collection.find_one({
                'timestamp_thingspeak': timestamp_ts
            })
            return existe is not None
        except Exception as e:
            print(f"❌ Erro ao verificar duplicata: {e}")
            return False

    def sincronizar(self):
        """Sincroniza um ciclo de dados"""
        try:
            print(f"\n🔄 Sincronizando dados do ThingSpeak... ({datetime.now()})")

            # Busca dados do ThingSpeak
            dados_ts = self.buscar_dados_thingspeak()

            if not dados_ts:
                print("⚠️  Nenhum dado novo no ThingSpeak")
                return False

            # Verifica duplicata
            if self.verificar_duplicata(dados_ts['timestamp_thingspeak']):
                print("⏭️  Dado já existe, pulando...")
                return False

            # Formata para MongoDB
            documento = self.formatar_para_mongodb(dados_ts)

            # Salva
            if self.salvar_no_mongodb(documento):
                print(f"📊 Peso: {documento['peso_kg']:.2f} kg")
                return True

            return False

        except Exception as e:
            print(f"❌ Erro na sincronização: {e}")
            return False

    def iniciar_monitoramento(self):
        """
        Inicia monitoramento contínuo em thread separada
        """
        print(f"🚀 Iniciando monitoramento ThingSpeak (a cada {INTERVALO_COLETA}s)")

        def loop_monitoramento():
            while True:
                try:
                    self.sincronizar()
                    time.sleep(INTERVALO_COLETA)
                except Exception as e:
                    print(f"❌ Erro no loop: {e}")
                    time.sleep(INTERVALO_COLETA)

        # Inicia em thread daemon (fecha com a app)
        thread = Thread(target=loop_monitoramento, daemon=True)
        thread.start()
        print("✅ Thread de monitoramento iniciada")

    def parar(self):
        """Desconecta do MongoDB"""
        if self.mongo_client:
            self.mongo_client.close()
            print("✅ MongoDB desconectado")


# INSTÂNCIA GLOBAL
thingspeak_integration = None


def inicializar_thingspeak():
    """Inicializa a integração com ThingSpeak"""
    global thingspeak_integration
    try:
        thingspeak_integration = ThingSpeakIntegration()
        thingspeak_integration.iniciar_monitoramento()
        print("✅ Integração ThingSpeak inicializada")
        return True
    except Exception as e:
        print(f"❌ Erro ao inicializar ThingSpeak: {e}")
        return False


def sincronizar_agora():
    """Força sincronização imediata (útil para testes)"""
    if thingspeak_integration:
        return thingspeak_integration.sincronizar()
    return False


if __name__ == "__main__":
    # Teste local
    print("🧪 Testando integração ThingSpeak...\n")

    ts = ThingSpeakIntegration()

    # Testa leitura
    print("1️⃣  Testando busca do ThingSpeak...")
    dados = ts.buscar_dados_thingspeak()

    if dados:
        print(f"✅ Dados obtidos: {dados}")

        # Testa formatação
        print("\n2️⃣  Testando formatação...")
        doc = ts.formatar_para_mongodb(dados)
        print(f"✅ Documento: {doc}")

        # Testa duplicata
        print("\n3️⃣  Testando verificação de duplicata...")
        tem_duplicata = ts.verificar_duplicata(dados['timestamp_thingspeak'])
        print(f"Tem duplicata? {tem_duplicata}")

        # Testa save
        print("\n4️⃣  Testando salvamento...")
        ts.salvar_no_mongodb(doc)

    else:
        print("❌ Nenhum dado obtido")

    ts.parar()