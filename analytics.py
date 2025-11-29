import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import json

class AnalisadorDados:
    """Classe para análise de dados e big data"""
    
    def __init__(self, colecao_leituras):
        self.colecao = colecao_leituras
    
    def obter_dataframe(self, dias: int = 30) -> pd.DataFrame:
        """Obtém dados dos últimos N dias como DataFrame"""
        data_inicio = datetime.utcnow() - timedelta(days=dias)
        
        leituras = list(self.colecao.find({
            "timestamp": {"$gte": data_inicio.isoformat()}
        }, {"_id": 0}).sort("timestamp", 1))
        
        if not leituras:
            return pd.DataFrame()
        
        df = pd.DataFrame(leituras)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def analisar_padroes(self, dias: int = 30) -> Dict:
        """
        Analisa padrões de geração de lixo
        
        Returns:
            Dict com análises
        """
        df = self.obter_dataframe(dias)
        
        if df.empty:
            return {"erro": "Sem dados"}
        
        # Extrair informações de tempo
        df['hora'] = df['timestamp'].dt.hour
        df['dia_semana'] = df['timestamp'].dt.day_name()
        df['data'] = df['timestamp'].dt.date
        
        analises = {
            # Geração por hora do dia
            "geração_por_hora": df.groupby('hora')['peso_kg'].agg([
                ('total', 'sum'),
                ('media', 'mean'),
                ('ocorrencias', 'count')
            ]).to_dict(),
            
            # Geração por dia da semana
            "geração_por_dia_semana": df.groupby('dia_semana')['peso_kg'].agg([
                ('total', 'sum'),
                ('media', 'mean')
            ]).to_dict(),
            
            # Estatísticas gerais
            "estatisticas": {
                "total_gerado": float(df['peso_kg'].sum()),
                "media_diaria": float(df.groupby('data')['peso_kg'].sum().mean()),
                "pico_maximo": float(df['peso_kg'].max()),
                "pico_minimo": float(df['peso_kg'].min()),
                "desvio_padrao": float(df['peso_kg'].std()),
                "mediana": float(df['peso_kg'].median()),
            },
            
            # Dia com mais geração
            "dia_maior_geracao": str(df.loc[df['peso_kg'].sum().groupby(df['data']).idxmax()]),
            
            # Hora de pico
            "hora_pico": int(df.groupby('hora')['peso_kg'].sum().idxmax()),
            
            # Temperatura média
            "temperatura_media": float(df['temperatura'].mean()) if 'temperatura' in df.columns else 0,
            
            # Umidade média
            "umidade_media": float(df['umidade'].mean()) if 'umidade' in df.columns else 0
        }
        
        return analises
    
    def prever_geracao(self, dias_futuros: int = 7) -> Dict:
        """
        Predição de geração de lixo usando Machine Learning
        
        Args:
            dias_futuros: Número de dias a predizer
            
        Returns:
            Dict com predições
        """
        df = self.obter_dataframe(dias=90)  # Usar 90 dias para treinar
        
        if len(df) < 10:
            return {"erro": "Dados insuficientes para predição"}
        
        # Preparar dados
        df['data'] = df['timestamp'].dt.date
        df_diario = df.groupby('data')['peso_kg'].sum().reset_index()
        df_diario['dia_numero'] = range(len(df_diario))
        
        # Treinar modelo
        X = df_diario[['dia_numero']].values
        y = df_diario['peso_kg'].values
        
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        # Fazer predições
        dias_treino = len(df_diario)
        X_futuro = np.array([[dias_treino + i] for i in range(dias_futuros)])
        predicoes = modelo.predict(X_futuro)
        
        # Garantir valores positivos
        predicoes = np.maximum(predicoes, 0)
        
        return {
            "modelo": "Linear Regression",
            "treino_dias": dias_treino,
            "r2_score": float(modelo.score(X, y)),
            "predicoes": [
                {
                    "dia": i + 1,
                    "peso_previsto_kg": float(max(0, pred)),
                    "data_estimada": (datetime.utcnow() + timedelta(days=i+1)).isoformat()
                }
                for i, pred in enumerate(predicoes)
            ],
            "confianca": "Alta" if modelo.score(X, y) > 0.7 else "Média" if modelo.score(X, y) > 0.4 else "Baixa"
        }
    
    def detectar_anomalias(self, sensibilidade: float = 2.0) -> List[Dict]:
        """
        Detecta anomalias nos dados (picos anormais)
        
        Args:
            sensibilidade: Número de desvios padrão para considerar anomalia
            
        Returns:
            Lista de anomalias detectadas
        """
        df = self.obter_dataframe(dias=30)
        
        if df.empty:
            return []
        
        media = df['peso_kg'].mean()
        desvio = df['peso_kg'].std()
        limite = media + (sensibilidade * desvio)
        
        anomalias = df[df['peso_kg'] > limite].to_dict('records')
        
        resultado = []
        for anomalia in anomalias:
            resultado.append({
                "timestamp": anomalia['timestamp'],
                "peso_kg": float(anomalia['peso_kg']),
                "desvios_padrao": float((anomalia['peso_kg'] - media) / desvio),
                "severidade": "Crítica" if anomalia['peso_kg'] > limite * 1.5 else "Alta"
            })
        
        return resultado
    
    def comparar_periodos(self, periodo1_dias: int = 7, 
                         periodo2_dias: int = 14) -> Dict:
        """
        Compara duas períodos diferentes
        
        Returns:
            Comparação e variações
        """
        df = self.obter_dataframe(dias=30)
        
        if df.empty:
            return {"erro": "Sem dados"}
        
        agora = datetime.utcnow()
        
        # Período 1
        data_inicio_p1 = agora - timedelta(days=periodo1_dias)
        df_p1 = df[df['timestamp'] >= data_inicio_p1]
        total_p1 = df_p1['peso_kg'].sum()
        media_p1 = df_p1['peso_kg'].mean()
        
        # Período 2
        data_inicio_p2 = agora - timedelta(days=periodo1_dias + periodo2_dias)
        data_fim_p2 = agora - timedelta(days=periodo1_dias)
        df_p2 = df[(df['timestamp'] >= data_inicio_p2) & (df['timestamp'] < data_fim_p2)]
        total_p2 = df_p2['peso_kg'].sum()
        media_p2 = df_p2['peso_kg'].mean()
        
        # Calcular variação
        variacao_total = ((total_p1 - total_p2) / total_p2 * 100) if total_p2 > 0 else 0
        variacao_media = ((media_p1 - media_p2) / media_p2 * 100) if media_p2 > 0 else 0
        
        return {
            "periodo1": {
                "dias": periodo1_dias,
                "total_kg": float(total_p1),
                "media_kg": float(media_p1),
                "ocorrencias": len(df_p1)
            },
            "periodo2": {
                "dias": periodo2_dias,
                "total_kg": float(total_p2),
                "media_kg": float(media_p2),
                "ocorrencias": len(df_p2)
            },
            "variacao": {
                "total_percentual": float(variacao_total),
                "media_percentual": float(variacao_media),
                "tendencia": "Aumento" if variacao_total > 0 else "Redução"
            }
        }
    
    def gerar_relatorio_executivo(self) -> Dict:
        """Gera relatório executivo com todas as análises"""
        
        return {
            "timestamp_geracao": datetime.utcnow().isoformat(),
            "titulo": "Relatório Executivo - Geração de Resíduos",
            "padroes": self.analisar_padroes(dias=30),
            "predicoes": self.prever_geracao(dias_futuros=7),
            "anomalias": self.detectar_anomalias(),
            "comparacao": self.comparar_periodos(periodo1_dias=7, periodo2_dias=7),
            "recomendacoes": self._gerar_recomendacoes()
        }
    
    def _gerar_recomendacoes(self) -> List[str]:
        """Gera recomendações baseado nas análises"""
        recomendacoes = []
        
        analises = self.analisar_padroes()
        
        if analises.get("hora_pico"):
            recomendacoes.append(
                f"Reforçar coleta às {analises['hora_pico']}h (horário de pico)"
            )
        
        anomalias = self.detectar_anomalias()
        if anomalias:
            recomendacoes.append(
                f"Investigar {len(anomalias)} anomalias detectadas"
            )
        
        return recomendacoes if recomendacoes else ["Sistema operando dentro dos padrões"]


class GeradorRelatorios:
    """Classe para gerar relatórios em diferentes formatos"""
    
    def __init__(self, analisador: AnalisadorDados):
        self.analisador = analisador
    
    def gerar_json(self) -> str:
        """Gera relatório em JSON"""
        relatorio = self.analisador.gerar_relatorio_executivo()
        return json.dumps(relatorio, indent=2, ensure_ascii=False)
    
    def gerar_csv(self) -> str:
        """Gera relatório em CSV"""
        df = self.analisador.obter_dataframe(dias=30)
        
        if df.empty:
            return "Sem dados disponíveis"
        
        return df[['timestamp', 'peso_kg', 'temperatura', 'umidade', 'sensor_id']].to_csv(index=False)