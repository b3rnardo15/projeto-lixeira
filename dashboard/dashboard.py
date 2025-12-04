import streamlit as st
import pymongo
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import certifi
import requests
from pytz import UTC 
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import csv

load_dotenv()

st.set_page_config(
    page_title="Dashboard - SmartBin",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== TEMA CUSTOMIZADO ==========
def set_theme():
    """Configura o tema visual do dashboard"""
    theme_mode = st.sidebar.radio(
        "🎨 Tema",
        ["☀️ Claro", "🌙 Escuro"],
        horizontal=True
    )
    
    if theme_mode == "☀️ Claro":
        st.markdown("""
        <style>
            :root {
                --primary-color: #10b981;
                --secondary-color: #059669;
            }
            .stMetric {
                background-color: #f0fdf4;
                border-radius: 8px;
                padding: 10px;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            :root {
                --primary-color: #10b981;
                --secondary-color: #059669;
            }
            .stMetric {
                background-color: rgba(16, 185, 129, 0.1);
                border-radius: 8px;
                padding: 10px;
            }
        </style>
        """, unsafe_allow_html=True)
    
    return theme_mode == "☀️ Claro"

# ========== CONEXÃO MONGODB ==========
@st.cache_resource
def init_connection():
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        st.error("MONGODB_URI nao configurada")
        return None
    
    try:
        return pymongo.MongoClient(mongo_uri, tlsCAFile=certifi.where())
    except Exception as e:
        st.error(f"Erro MongoDB: {e}")
        return None

client = init_connection()
if client:
    try:
        db = client['lixeira_inteligente']
        collection_leituras = db['leituras']
        collection_usuarios = db['usuarios']
        collection_auditoria = db['auditoria']
    except Exception as e:
        st.error(f"Erro ao acessar database: {e}")
        st.stop()
else:
    st.stop()

# ========== SESSÃO ==========
def inicializar_sessao():
    if 'usuario_logado' not in st.session_state:
        st.session_state.usuario_logado = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'mfa_requerido' not in st.session_state:
        st.session_state.mfa_requerido = False
    if 'mfa_qr_code' not in st.session_state:
        st.session_state.mfa_qr_code = None
    if 'mfa_secret' not in st.session_state:
        st.session_state.mfa_secret = None

inicializar_sessao()

API_URL = "https://projeto-lixeira.onrender.com"

# ========== AUTENTICAÇÃO ==========
def fazer_login(username: str, senha: str):
    try:
        response = requests.post(f"{API_URL}/api/login", json={"username": username, "senha": senha})
        if response.status_code == 200:
            dados = response.json()
            st.session_state.usuario_logado = username
            st.session_state.token = dados['token']
            st.session_state.role = dados['usuario'].get('role', 'usuario')
            st.session_state.mfa_requerido = dados.get('requer_mfa', False)
            return True, "login realizado"
        else:
            return False, response.json().get('erro', 'erro no login')
    except Exception as e:
        return False, f"Erro: {e}"

def fazer_logout():
    st.session_state.usuario_logado = None
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.mfa_qr_code = None
    st.session_state.mfa_secret = None

def tela_login():
    st.markdown("# ♻️ Dashboard - SmartBin")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### acesso ao sistema")
        
        if st.session_state.mfa_requerido:
            st.warning("🔐 mfa ativado para sua conta")
            codigo_mfa = st.text_input("codigo mfa (6 digitos)", placeholder="000000")
            
            if st.button("✓ verificar mfa"):
                try:
                    response = requests.post(
                        f"{API_URL}/api/mfa/verificar",
                        json={"username": st.session_state.usuario_logado, "codigo": codigo_mfa}
                    )
                    if response.status_code == 200:
                        st.success("✓ mfa verificado!")
                        st.session_state.mfa_requerido = False
                        st.rerun()
                    else:
                        st.error("✗ codigo mfa invalido")
                except Exception as e:
                    st.error(f"erro: {e}")
        else:
            username = st.text_input("👤 usuario", placeholder="heurykteste")
            senha = st.text_input("🔑 senha", type="password", placeholder="heuryk123")
            
            if st.button("📲 entrar", use_container_width=True):
                sucesso, mensagem = fazer_login(username, senha)
                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)
    
    st.markdown("---")
    st.info("💡 demo: heurykteste / heuryk123")

# ========== BUSCAR DADOS ==========
@st.cache_data(ttl=10)
def get_data(dias=7, limite=1000):
    """Busca dados dos últimos N dias - SEM problemas de timezone"""
    try:
        leituras = list(collection_leituras.find(
            {},
            {'_id': 0}
        ).sort('_id', -1).limit(limite))
        
        if not leituras:
            return pd.DataFrame()
        
        df = pd.DataFrame(leituras)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        
        df = df.dropna(subset=['timestamp'])
        
        if df.empty:
            return pd.DataFrame()
        
        data_inicio = datetime.utcnow().replace(tzinfo=UTC) - timedelta(days=dias)
        df = df[df['timestamp'] >= data_inicio]
        
        df = df.sort_values('timestamp')
        
        df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

# ========== EXPORTAR CSV ==========
def exportar_csv(df):
    """Exporta dados para CSV"""
    csv_buffer = BytesIO()
    df_export = df.copy()
    df_export.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

# ========== EXPORTAR PDF ==========
def exportar_pdf(df, stats):
    """Exporta dados para PDF com formatação bonita"""
    try:
        # Criar PDF em memória
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        # Container de elementos
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#10b981'),
            spaceAfter=12,
            alignment=1  # Centro
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            spaceAfter=10
        )
        
        # Título
        story.append(Paragraph("♻️ RELATÓRIO - LIXEIRA INTELIGENTE", title_style))
        story.append(Paragraph(f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Seção de Estatísticas
        story.append(Paragraph("📊 ESTATÍSTICAS", heading_style))
        
        stats_data = [
            ['Métrica', 'Valor'],
            ['Peso Atual', f"{stats['atual']:.3f} kg"],
            ['Peso Máximo (24h)', f"{stats['maximo']:.3f} kg"],
            ['Peso Mínimo (24h)', f"{stats['minimo']:.3f} kg"],
            ['Média (24h)', f"{stats['media']:.3f} kg"],
            ['Percentual Capacidade', f"{stats['percentual']:.1f}%"],
            ['Total de Leituras', f"{stats['total']}"],
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')])
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Seção de Dados Detalhados
        story.append(Paragraph("📋 DADOS DETALHADOS", heading_style))
        
        # Preparar dados da tabela
        data_table = [['Horário', 'Peso (kg)', '% Capacidade', 'Sensor']]
        for _, row in df.tail(20).iterrows():
            data_table.append([
                str(row['timestamp'])[:19],
                f"{float(row['peso_kg']):.3f}",
                f"{(float(row['peso_kg'])/10.0)*100:.1f}%",
                str(row.get('sensor_id', 'N/A'))
            ])
        
        details_table = Table(data_table, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Rodapé
        footer_text = f"Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
        story.append(Paragraph(f"<i>{footer_text}</i>", styles['Normal']))
        
        # Gerar PDF
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

# ========== GRÁFICOS ==========
def criar_grafico_combo(df):
    """Gráfico Combo (Linha + Barra) com peso real"""
    if df.empty or 'peso_kg' not in df.columns:
        st.warning("📊 Sem dados para exibir")
        return
    
    try:
        df_sorted = df.sort_values('timestamp').tail(100)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_sorted['timestamp'],
            y=df_sorted['peso_kg'],
            name='Peso (kg)',
            marker=dict(
                color=df_sorted['peso_kg'],
                colorscale='RdYlGn_r',
                cmid=5,
                colorbar=dict(title="Peso (kg)")
            ),
            opacity=0.6,
            xaxis='x',
            yaxis='y'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_sorted['timestamp'],
            y=df_sorted['peso_kg'],
            name='Tendência',
            mode='lines+markers',
            line=dict(color='#2180CD', width=3),
            marker=dict(size=6),
            xaxis='x',
            yaxis='y'
        ))
        
        fig.add_hline(
            y=10.0,
            line_dash="dash",
            line_color="red",
            annotation_text="Capacidade Máxima (10kg)",
            annotation_position="right"
        )
        
        fig.add_hline(
            y=8.5,
            line_dash="dash",
            line_color="orange",
            annotation_text="Alerta (85%)",
            annotation_position="right"
        )
        
        fig.update_layout(
            title='📊 Histórico de Peso - Últimas Leituras',
            xaxis_title='Data/Hora',
            yaxis_title='Peso (kg)',
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f3f4f6'),
            height=450,
            showlegend=True,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"erro ao plotar: {e}")

def criar_grafico_barras(df_group, titulo, xlabel, ylabel):
    """Gráfico de barras genérico"""
    if df_group.empty:
        return None
    
    try:
        fig = px.bar(
            df_group,
            title=titulo,
            labels={xlabel: xlabel, ylabel: ylabel},
            text=ylabel
        )
        
        fig.update_traces(
            marker=dict(color='#10b981', line=dict(color='#059669', width=2)),
            textposition='auto'
        )
        
        fig.update_layout(
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f3f4f6'),
            height=350,
            showlegend=False
        )
        
        return fig
    except Exception as e:
        st.warning(f"erro ao plotar: {e}")
        return None

# ========== DASHBOARD PRINCIPAL ==========
def dashboard_principal():
    st.title("♻️ Dashboard Inteligente de Resíduos v4.0")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👤 {st.session_state.usuario_logado} · **{st.session_state.role.upper()}**")
    
    with col3:
        if st.button("🚪 logout", use_container_width=True):
            fazer_logout()
            st.rerun()
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "📈 Big Data",
        "🤖 Predições",
        "⚠️ Anomalias",
        "⚙️ Admin"
    ])
    
    # ========== TAB 1: DASHBOARD ==========
    with tab1:
        st.markdown("## 📡 Monitoramento em Tempo Real")
        
        periodo = st.slider("Selecione período (dias):", 1, 30, 7, key="periodo_slider")
        
        df = get_data(dias=periodo)
        
        if df.empty:
            st.warning("❌ Nenhum dado disponível no período selecionado")
            st.info(f"ℹ️ Total de documentos no banco: {collection_leituras.count_documents({})}")
        else:
            st.success(f"✅ {len(df)} leituras encontradas!")
            
            if not df.empty and 'peso_kg' in df.columns:
                peso_atual = float(df['peso_kg'].iloc[-1]) if len(df) > 0 else 0
                peso_maximo = float(df['peso_kg'].max())
                peso_minimo = float(df['peso_kg'].min())
                peso_media = float(df['peso_kg'].mean())
                percentual = (peso_atual / 10.0) * 100
                
                # Stats para exportação
                stats = {
                    'atual': peso_atual,
                    'maximo': peso_maximo,
                    'minimo': peso_minimo,
                    'media': peso_media,
                    'percentual': percentual,
                    'total': len(df)
                }
                
                # ========== CARDS ==========
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="⚖️ Peso Atual",
                        value=f"{peso_atual:.3f} kg",
                        delta=f"{percentual:.1f}% de 10kg",
                        delta_color="inverse"
                    )
                
                with col2:
                    st.metric(
                        label="📈 Peso Máximo",
                        value=f"{peso_maximo:.3f} kg",
                        delta=f"{(peso_maximo/10.0)*100:.1f}%"
                    )
                
                with col3:
                    st.metric(
                        label="📉 Peso Mínimo",
                        value=f"{peso_minimo:.3f} kg",
                        delta=f"{(peso_minimo/10.0)*100:.1f}%"
                    )
                
                with col4:
                    st.metric(
                        label="📊 Média",
                        value=f"{peso_media:.3f} kg",
                        delta=f"{(peso_media/10.0)*100:.1f}%"
                    )
                
                st.markdown("---")
                
                # ========== EXPORTAR ==========
                st.subheader("📥 Exportar Dados")
                
                col_csv, col_pdf = st.columns(2)
                
                with col_csv:
                    csv_data = exportar_csv(df)
                    st.download_button(
                        label="📄 Baixar CSV",
                        data=csv_data,
                        file_name=f"lixeira_dados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_pdf:
                    pdf_data = exportar_pdf(df, stats)
                    if pdf_data:
                        st.download_button(
                            label="📑 Baixar PDF",
                            data=pdf_data,
                            file_name=f"lixeira_relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                
                st.markdown("---")
                
                # ========== STATUS DE ALERTA ==========
                if percentual >= 95:
                    st.error(f"🔴 CRÍTICO: {percentual:.1f}% de capacidade!")
                elif percentual >= 85:
                    st.warning(f"🟠 ALERTA: {percentual:.1f}% de capacidade!")
                else:
                    st.success(f"🟢 NORMAL: {percentual:.1f}% de capacidade!")
                
                st.markdown("---")
                
                # ========== GRÁFICO COMBO ==========
                st.subheader("📈 Gráfico de Peso (Linha + Barra)")
                criar_grafico_combo(df)
                
                st.markdown("---")
                
                # ========== TABELA DE DADOS ==========
                st.subheader("📋 Histórico Completo")
                
                try:
                    df_display = pd.DataFrame([{
                        'Horário': pd.to_datetime(l['timestamp']).strftime('%d/%m %H:%M:%S') if pd.notna(l.get('timestamp')) else 'N/A',
                        'Peso (kg)': f"{float(l['peso_kg']):.3f}" if 'peso_kg' in l else 'N/A',
                        '% Capacidade': f"{(float(l['peso_kg'])/10.0)*100:.1f}%" if 'peso_kg' in l else 'N/A',
                        'Sensor': l.get('sensor_id', 'N/A'),
                    } for l in reversed(df.to_dict('records'))])
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Erro ao exibir tabela: {e}")
    
    # ========== TAB 2: BIG DATA ==========
    with tab2:
        st.markdown("## 📊 Análise de Padrões")
        
        periodo = st.slider("Selecione período (dias):", 1, 30, 7, key="periodo_slider_big_data")
        df = get_data(dias=periodo)
        
        if not df.empty and 'peso_kg' in df.columns:
            try:
                df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df['hora'] = df['timestamp_dt'].dt.hour
                df['dia_semana'] = df['timestamp_dt'].dt.day_name()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    geracao_hora = df.groupby('hora')['peso_kg'].sum().reset_index()
                    fig_hora = criar_grafico_barras(geracao_hora, '⏰ Geração por Hora', 'hora', 'peso_kg')
                    if fig_hora:
                        st.plotly_chart(fig_hora, use_container_width=True)
                
                with col2:
                    geracao_dia = df.groupby('dia_semana')['peso_kg'].sum().reset_index()
                    fig_dia = criar_grafico_barras(geracao_dia, '📅 Geração por Dia', 'dia_semana', 'peso_kg')
                    if fig_dia:
                        st.plotly_chart(fig_dia, use_container_width=True)
                
                st.markdown("### 📊 Estatísticas Descritivas")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📈 Máximo", f"{df['peso_kg'].max():.3f} kg")
                with col2:
                    st.metric("📉 Mínimo", f"{df['peso_kg'].min():.3f} kg")
                with col3:
                    st.metric("📌 Mediana", f"{df['peso_kg'].median():.3f} kg")
                with col4:
                    st.metric("📊 Desvio Padrão", f"{df['peso_kg'].std():.3f} kg")
                
            except Exception as e:
                st.error(f"Erro na análise: {e}")
    
    # ========== TAB 3: PREDIÇÕES ==========
    with tab3:
        st.markdown("## 🤖 Predições com ML")
        st.info("🔄 Módulo de predições com machine learning está pronto na API v2.0")
    
    # ========== TAB 4: ANOMALIAS ==========
    with tab4:
        st.markdown("## ⚠️ Detecção de Anomalias")
        
        periodo = st.slider("Selecione período (dias):", 1, 30, 7, key="periodo_slider_anomalias")
        df = get_data(dias=periodo)
        
        if not df.empty and 'peso_kg' in df.columns:
            media = df['peso_kg'].mean()
            desvio = df['peso_kg'].std()
            limite = media + (2 * desvio)
            
            anomalias = df[df['peso_kg'] > limite]
            
            if len(anomalias) > 0:
                st.warning(f"🚨 Atenção: **{len(anomalias)}** anomalias detectadas")
                st.dataframe(
                    anomalias[['timestamp', 'peso_kg', 'sensor_id']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("✅ Nenhuma anomalia detectada")
    
    # ========== TAB 5: ADMIN ==========
    with tab5:
        if st.session_state.role == 'admin':
            st.markdown("## ⚙️ Painel Administrativo")
            
            sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                "👥 Usuários",
                "🔐 MFA",
                "📋 Auditoria",
                "ℹ️ Sistema"
            ])
            
            # ========== SUB_TAB1: USUÁRIOS ==========
            with sub_tab1:
                st.markdown("### 👥 Gerenciar Usuários")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    usuarios = list(collection_usuarios.find({}, {'_id': 0, 'hash_senha': 0, 'salt': 0}))
                    if usuarios:
                        df_usuarios = pd.DataFrame(usuarios)
                        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("### ➕ Novo Usuário")
                    
                    novo_username = st.text_input("Username")
                    novo_nome = st.text_input("Nome Completo")
                    novo_senha = st.text_input("Senha", type="password")
                    novo_role = st.selectbox("Role", ["usuario", "gestor", "admin"])
                    novo_email = st.text_input("Email")
                    
                    if st.button("✓ Criar Usuário", use_container_width=True):
                        try:
                            response = requests.post(
                                f"{API_URL}/api/criar-usuario",
                                json={
                                    "username": novo_username,
                                    "senha": novo_senha,
                                    "nome": novo_nome,
                                    "role": novo_role,
                                    "email": novo_email
                                },
                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                            )
                            
                            if response.status_code == 201:
                                st.success("✓ Usuário criado com sucesso")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(response.json().get('erro', 'erro ao criar'))
                        except Exception as e:
                            st.error(f"erro: {e}")
            
            # ========== SUB_TAB2: MFA ==========
            with sub_tab2:
                st.markdown("### 🔐 Gerenciar MFA")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Status MFA")
                    usuarios = list(collection_usuarios.find({}, {'_id': 0, 'username': 1, 'mfa_ativado': 1}))
                    if usuarios:
                        for usuario in usuarios:
                            mfa_status = "✅ ativado" if usuario.get('mfa_ativado') else "❌ desativado"
                            st.write(f"**{usuario['username']}**: {mfa_status}")
                
                with col2:
                    st.markdown("#### Ativar MFA")
                    usuarios = list(collection_usuarios.find({}, {'_id': 0, 'username': 1}))
                    usernames = [u['username'] for u in usuarios]
                    usuario_selecionado = st.selectbox("Usuário", usernames, key="mfa_user_select")
                    
                    if st.button("📱 Gerar QR Code", key="btn_gerar_qr", use_container_width=True):
                        try:
                            response = requests.post(
                                f"{API_URL}/api/mfa/gerar-qrcode",
                                headers={"Authorization": f"Bearer {st.session_state.token}"}
                            )
                            
                            if response.status_code == 200:
                                dados = response.json()
                                st.session_state.mfa_qr_code = dados['qr_code']
                                st.session_state.mfa_secret = dados['secret']
                                st.success("✓ QR Code gerado! Escaneia no Google Authenticator")
                            else:
                                st.error("erro ao gerar qr code")
                        except Exception as e:
                            st.error(f"erro: {e}")
                
                if st.session_state.mfa_qr_code:
                    st.markdown("#### 1️⃣ Escanear QR Code")
                    qr_code_img = st.session_state.mfa_qr_code
                    if qr_code_img.startswith('data:image'):
                        img_data = qr_code_img.split(',')[1]
                        st.image(f"data:image/png;base64,{img_data}", width=250)
                    
                    st.markdown("#### 2️⃣ Digitar Código")
                    codigo = st.text_input("Código (6 dígitos)", max_chars=6, key="mfa_codigo_input")
                    
                    if len(codigo) == 6:
                        if st.button("✓ Ativar MFA", key="btn_ativar_mfa", use_container_width=True):
                            try:
                                response_ativar = requests.post(
                                    f"{API_URL}/api/mfa/ativar",
                                    json={"codigo": codigo},
                                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                                )
                                
                                if response_ativar.status_code == 200:
                                    st.success("✓ MFA ativado com sucesso!")
                                    st.session_state.mfa_qr_code = None
                                    st.session_state.mfa_secret = None
                                    st.cache_data.clear()
                                    import time
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"erro: {response_ativar.json().get('erro', 'erro desconhecido')}")
                            except Exception as e:
                                st.error(f"erro na requisição: {e}")
                    else:
                        st.info(f"📝 Digite 6 dígitos ({len(codigo)}/6)")
            
            # ========== SUB_TAB3: AUDITORIA ==========
            with sub_tab3:
                st.markdown("### 📋 Logs de Auditoria")
                
                logs = list(collection_auditoria.find({}, {'_id': 0}).sort('timestamp', -1).limit(50))
                
                if logs:
                    st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
            
            # ========== SUB_TAB4: SISTEMA ==========
            with sub_tab4:
                st.markdown("### ℹ️ Informações do Sistema")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    df_all = get_data(dias=30)
                    st.metric("📊 Total de Leituras", len(df_all))
                    usuarios_count = len(list(collection_usuarios.find({})))
                    st.metric("👥 Usuários Cadastrados", usuarios_count)
                
                with col2:
                    logs_count = len(list(collection_auditoria.find({})))
                    st.metric("📋 Logs de Auditoria", logs_count)
                    total_docs = collection_leituras.count_documents({})
                    st.metric("📈 Documentos MongoDB", total_docs)
        
        else:
            st.error("❌ Acesso restrito a administradores")

def main():
    tema_claro = set_theme()
    
    if st.session_state.usuario_logado and not st.session_state.mfa_requerido:
        dashboard_principal()
    else:
        tela_login()

if __name__ == "__main__":
    main()