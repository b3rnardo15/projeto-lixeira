# ♻️ Lixeira Inteligente - Smart Waste Management System

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28.1-red)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

Sistema completo de **monitoramento em tempo real de lixeira inteligente** com IoT, Dashboard interativo, API REST e autenticação segura com MFA.

---

## 🎯 Visão Geral

**Lixeira Inteligente** é um projeto full-stack que integra:

- **ESP32 + Sensor de Peso** - Coleta dados em tempo real
- **ThingSpeak** - Sincronização na nuvem
- **MongoDB Atlas** - Armazenamento de dados
- **Flask API** - Backend com autenticação JWT + MFA
- **Streamlit Dashboard** - Interface visual interativa
- **Render** - Deployment em produção

### Funcionalidades Principais

✅ **Monitoramento em Tempo Real**
- Peso atual da lixeira
- Histórico de leituras
- Alertas de capacidade (85%, 95%)

✅ **Dashboard Interativo**
- Gráficos dinâmicos com Plotly
- Exportação de dados (CSV/PDF)
- Análise de padrões (hora, dia da semana)
- Detecção de anomalias

✅ **Autenticação Segura**
- Login com JWT
- MFA (Google Authenticator)
- Controle de permissões (Admin, Gestor, Usuário)

✅ **API REST Completa**
- CRUD de leituras
- Gerenciar usuários
- Gerar QR Codes para MFA
- Logs de auditoria

---

## 📁 Estrutura do Projeto

```
projeto-lixeira/
│
├── api/                          # Backend Flask
│   ├── app.py                    # Aplicação principal
│   ├── app_v2.py                 # Versão com MFA
│   ├── auth.py                   # Autenticação JWT
│   ├── mfa.py                    # Multi-Factor Authentication
│   ├── thingspeak_integration.py # Integração ThingSpeak
│   ├── requirements.txt           # Dependências
│   ├── Procfile                  # Para deploy Render
│   └── .env.example              # Variáveis de exemplo
│
├── dashboard/                    # Frontend Streamlit
│   ├── dashboard.py              # Dashboard principal
│   ├── requirements.txt           # Dependências
│   ├── .streamlit/
│   │   └── config.toml           # Configuração Streamlit
│   └── .env.example              # Variáveis de exemplo
│
├── .gitignore                    # Arquivos ignorados
├── .env.example                  # Template de variáveis
├── README.md                     # Esta documentação
└── docs/                         # Documentação adicional
```

---

## 🚀 Quick Start Local

### Pré-requisitos

- Python 3.9+
- MongoDB Atlas (conta gratuita)
- ThingSpeak (conta gratuita)
- Git

### 1️⃣ Clone o Repositório

```bash
git clone https://github.com/b3rnardo15/projeto-lixeira.git
cd projeto-lixeira
```

### 2️⃣ Configure as Variáveis de Ambiente

```bash
# Na raiz
cp .env.example .env

# Edita .env com suas credenciais
nano .env
```

### 3️⃣ Setup da API

```bash
cd api

# Cria ambiente virtual
python -m venv venv

# Ativa venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instala dependências
pip install -r requirements.txt

# Roda a API (porta 5000)
python app_v2.py
```

### 4️⃣ Setup do Dashboard

Em outro terminal:

```bash
cd dashboard

# Cria ambiente virtual
python -m venv venv

# Ativa venv (conforme seu SO)
.\venv\Scripts\activate

# Instala dependências
pip install -r requirements.txt

# Roda o dashboard (porta 8501)
streamlit run dashboard.py
```

### 5️⃣ Acesse

- **API**: http://localhost:5000
- **Dashboard**: http://localhost:8501

**Credenciais Demo:**
- Usuário: `admin`
- Senha: `admin123`

---

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env` na raiz com:

```env
# ========== MONGODB ==========
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/lixeira_inteligente

# ========== THINGSPEAK ==========
THINGSPEAK_API_KEY=your_api_key_here
THINGSPEAK_CHANNEL_ID=your_channel_id_here

# ========== FLASK API ==========
FLASK_ENV=production
SECRET_KEY=your_secret_key_change_in_production
API_URL=http://localhost:5000

# ========== JWT ==========
JWT_SECRET_KEY=your_jwt_secret_key_here

# ========== STREAMLIT ==========
STREAMLIT_SERVER_PORT=8501
STREAMLIT_LOGGER_LEVEL=info

# ========== ENVIRONMENT ==========
ENVIRONMENT=production
DEBUG=false
```

---

## 📊 Endpoints da API

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/login` | Login do usuário |
| POST | `/api/logout` | Logout |
| POST | `/api/criar-usuario` | Criar novo usuário (Admin) |

### Leituras

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/leituras` | Listar leituras |
| POST | `/api/leituras` | Adicionar leitura |
| GET | `/api/leituras/<id>` | Obter leitura específica |

### MFA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/mfa/gerar-qrcode` | Gerar QR Code MFA |
| POST | `/api/mfa/ativar` | Ativar MFA |
| POST | `/api/mfa/verificar` | Verificar código MFA |

---

## 🛠️ Tecnologias

### Backend

- **Flask** - Web framework
- **PyJWT** - Autenticação JWT
- **PyOTP** - Geração de QR Codes para MFA
- **MongoDB** - Banco de dados NoSQL
- **Gunicorn** - WSGI server

### Frontend

- **Streamlit** - Framework para dashboard
- **Plotly** - Gráficos interativos
- **Pandas** - Processamento de dados
- **ReportLab** - Geração de PDFs

### Integração

- **ESP32** - Microcontrolador IoT
- **ThingSpeak** - Plataforma IoT
- **MongoDB Atlas** - Banco na nuvem

---

## 📦 Dependências

### API (`api/requirements.txt`)

```
flask==2.3.3
flask-cors==4.0.0
pymongo==4.5.0
PyJWT==2.8.0
bcrypt==4.0.1
pyotp==2.9.0
qrcode==7.4.2
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

### Dashboard (`dashboard/requirements.txt`)

```
streamlit==1.28.1
pymongo==4.5.0
pandas==2.0.3
plotly==5.16.1
reportlab==4.0.4
requests==2.31.0
python-dotenv==1.0.0
```

---

## 🚀 Deploy no Render

### Pré-requisitos

1. Conta no [Render](https://render.com)
2. Repositório no GitHub (já feito ✅)
3. Variáveis de ambiente configuradas

### 1️⃣ Deploy da API (Flask)

```
1. Entre em https://render.com
2. Clique em "New +" → "Web Service"
3. Conecte seu GitHub
4. Configure:
   - Name: lixeira-api
   - Runtime: Python 3.9
   - Build Command: cd api && pip install -r requirements.txt
   - Start Command: cd api && gunicorn app_v2:app
   - Port: 5000
5. Clique em "Advanced"
6. Add Environment Variable:
   - MONGODB_URI: [sua URI MongoDB]
   - SECRET_KEY: [gere uma chave aleatória]
   - JWT_SECRET_KEY: [outra chave aleatória]
7. Deploy!
```

**URL da API**: `https://lixeira-api.onrender.com`

### 2️⃣ Deploy do Dashboard (Streamlit)

```
1. Clique em "New +" → "Web Service"
2. Mesmo repositório GitHub
3. Configure:
   - Name: lixeira-dashboard
   - Runtime: Python 3.9
   - Build Command: cd dashboard && pip install -r requirements.txt
   - Start Command: cd dashboard && streamlit run dashboard.py --server.port=8501
   - Port: 8501
4. Add Environment Variables:
   - MONGODB_URI: [sua URI MongoDB]
   - API_URL: https://lixeira-api.onrender.com
5. Deploy!
```

**URL do Dashboard**: `https://lixeira-dashboard.onrender.com`

### 3️⃣ Verifiando o Deploy

```bash
# Testa a API
curl https://lixeira-api.onrender.com/api/health

# Acessa o Dashboard
https://lixeira-dashboard.onrender.com
```

---

## 🔧 Troubleshooting

### Erro: "Cannot connect to MongoDB"

✅ Verificar `MONGODB_URI` nas variáveis de ambiente
✅ Whitelist seu IP no MongoDB Atlas
✅ Testar conexão localmente

### Erro: "Module not found"

✅ Verificar `requirements.txt` está atualizado
✅ Limpar build cache no Render

### Dashboard muito lento

✅ Aumentar poder computacional no Render
✅ Otimizar queries do MongoDB
✅ Adicionar cache no Streamlit

---

## 📝 Logs e Monitoramento

### No Render

- Acesse **Logs** na dashboard do seu serviço
- Monitore CPU, memória e requisições
- Configure alertas para downtime

### No MongoDB Atlas

- Acesse **Atlas Monitoring** para ver performance
- Analise queries lentas
- Monitore espaço em disco

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

---

## 👤 Autor

**Bernardo** - [@b3rnardo15](https://github.com/b3rnardo15)

---

## 📞 Suporte

Para dúvidas ou problemas:

1. Abra uma [Issue](https://github.com/b3rnardo15/projeto-lixeira/issues)
2. Verifique a [documentação](./docs/)
3. Entre em contato

---

## 🎓 Próximas Implementações

- [ ] Notificações em tempo real (WebSocket)
- [ ] Machine Learning para previsão de enchimento
- [ ] Aplicativo mobile (React Native)
- [ ] Integração com múltiplos sensores
- [ ] Dashboard administrativo avançado
- [ ] Relatórios automáticos por email

---

## 📚 Documentação Adicional

Veja a pasta `docs/` para:

- [Setup Detalhado](./docs/setup.md)
- [API Reference](./docs/api.md)
- [Troubleshooting](./docs/troubleshooting.md)
- [Deploy Guide](./docs/deployment.md)

---

** Se este projeto foi útil, considere dar uma estrela no GitHub!**

Made with  by Bernardo
