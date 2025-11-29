import json
from datetime import datetime, timedelta
from typing import Dict, List

class AnalisadorDados:
    """Classe para análise de dados usando MongoDB puro (sem pandas)"""

    def __init__(self, colecao_leituras):
        self.colecao = colecao_leituras

    def analisar_padroes(self, dias: int = 30) -> Dict:
        """Analisa padrões de geração de lixo"""
        try:
            data_inicio = datetime.utcnow() - timedelta(days=dias)
            
            leituras = list(self.colecao.find({
                "timestamp": {"$gte": data_inicio.isoformat()}
            }, {"_id": 0}).sort("timestamp", -1))

            if not leituras:
                return {"erro": "Sem dados"}

            # Estatísticas gerais
            pesos = [l.get('peso_kg', 0) for l in leituras]
            total = sum(pesos)
            media = total / len(pesos) if pesos else 0
            maximo = max(pesos) if pesos else 0
            minimo = min(pesos) if pesos else 0

            # Calcular desvio padrão
            variancia = sum((x - media) ** 2 for x in pesos) / len(pesos) if pesos else 0
            desvio = variancia ** 0.5

            return {
                "estatisticas": {
                    "total_gerado": round(total, 2),
                    "media_por_leitura": round(media, 2),
                    "pico_maximo": round(maximo, 2),
                    "pico_minimo": round(minimo, 2),
                    "desvio_padrao": round(desvio, 2),
                    "total_leituras": len(leituras),
                    "dias_analise": dias
                },
                "sensores": list(set(l.get('sensor_id', 'desconhecido') for l in leituras))
            }
        except Exception as e:
            return {"erro": str(e)}

    def prever_geracao(self, dias_futuros: int = 7) -> Dict:
        """Predição simples baseada em média histórica"""
        try:
            data_inicio = datetime.utcnow() - timedelta(days=90)
            
            leituras = list(self.colecao.find({
                "timestamp": {"$gte": data_inicio.isoformat()}
            }, {"_id": 0}).sort("timestamp", 1))

            if len(leituras) < 10:
                return {"erro": "Dados insuficientes para predição"}

            pesos = [l.get('peso_kg', 0) for l in leituras]
            media_diaria = sum(pesos) / len(pesos)

            predicoes = []
            for i in range(dias_futuros):
                data_futura = datetime.utcnow() + timedelta(days=i+1)
                predicoes.append({
                    "dia": i + 1,
                    "peso_previsto_kg": round(media_diaria, 2),
                    "data_estimada": data_futura.isoformat(),
                    "metodo": "media_historica"
                })

            return {
                "modelo": "Média Histórica",
                "treino_dias": 90,
                "media_historica_kg": round(media_diaria, 2),
                "predicoes": predicoes,
                "confianca": "Média"
            }
        except Exception as e:
            return {"erro": str(e)}

    def detectar_anomalias(self, sensibilidade: float = 2.0) -> List[Dict]:
        """Detecta anomalias nos dados (picos anormais)"""
        try:
            data_inicio = datetime.utcnow() - timedelta(days=30)
            
            leituras = list(self.colecao.find({
                "timestamp": {"$gte": data_inicio.isoformat()}
            }, {"_id": 0}).sort("timestamp", -1))

            if not leituras:
                return []

            pesos = [l.get('peso_kg', 0) for l in leituras]
            media = sum(pesos) / len(pesos)
            
            # Desvio padrão
            variancia = sum((x - media) ** 2 for x in pesos) / len(pesos)
            desvio = variancia ** 0.5
            
            limite = media + (sensibilidade * desvio)
            
            anomalias = []
            for leitura in leituras:
                peso = leitura.get('peso_kg', 0)
                if peso > limite:
                    anomalias.append({
                        "timestamp": leitura.get('timestamp'),
                        "peso_kg": round(peso, 2),
                        "sensor_id": leitura.get('sensor_id'),
                        "desvios_padrao": round((peso - media) / desvio, 2) if desvio > 0 else 0,
                        "severidade": "Crítica" if peso > limite * 1.5 else "Alta"
                    })

            return anomalias
        except Exception as e:
            return [{"erro": str(e)}]

    def gerar_relatorio_executivo(self) -> Dict:
        """Gera relatório executivo resumido"""
        try:
            padroes = self.analisar_padroes(dias=30)
            predicoes = self.prever_geracao(dias=7)
            anomalias = self.detectar_anomalias()

            return {
                "data_geracao": datetime.utcnow().isoformat(),
                "periodo": "30 dias",
                "resumo": padroes.get("estatisticas", {}),
                "proximas_predicoes": predicoes.get("predicoes", [])[:3],
                "alertas_criticos": [a for a in anomalias if a.get("severidade") == "Crítica"][:5],
                "total_anomalias": len(anomalias)
            }
        except Exception as e:
            return {"erro": str(e)}


class GeradorRelatorios:
    """Gerador de relatórios em diferentes formatos"""

    def __init__(self, analisador_dados):
        self.analisador = analisador_dados

    def gerar_csv(self) -> str:
        """Gera relatório em formato CSV"""
        try:
            leituras = list(self.analisador.colecao.find({}, {"_id": 0}).sort("timestamp", -1).limit(1000))
            
            if not leituras:
                return "timestamp,sensor_id,peso_kg,temperatura,umidade\n"

            csv = "timestamp,sensor_id,peso_kg,temperatura,umidade\n"
            for leitura in leituras:
                csv += f"{leitura.get('timestamp', '')},{leitura.get('sensor_id', '')},{leitura.get('peso_kg', 0)},{leitura.get('temperatura', 0)},{leitura.get('umidade', 0)}\n"
            
            return csv
        except Exception as e:
            return f"erro,{str(e)}\n"