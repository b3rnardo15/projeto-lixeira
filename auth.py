"""
Módulo de Autenticação e Autorização
Segurança da Informação - Projeto Integrador
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class UsuarioAuth:
    """Classe para gerenciar usuários e autenticação"""
    
    def __init__(self, colecao_usuarios):
        """
        Inicializa o sistema de auth
        
        Args:
            colecao_usuarios: Collection MongoDB para usuários
        """
        self.colecao = colecao_usuarios
        self._criar_usuario_admin()
    
    def _criar_usuario_admin(self):
        """Cria usuário admin padrão se não existir"""
        admin_existe = self.colecao.find_one({"username": "admin"})
        
        if not admin_existe:
            self.criar_usuario(
                username="admin",
                senha="admin123",
                nome="Administrador",
                role="admin",
                email="admin@lixeira.local"
            )
            print("✅ Usuário admin criado padrão")
    
    @staticmethod
    def _hash_senha(senha: str, salt: Optional[str] = None) -> tuple:
        """
        Hash seguro da senha com salt
        
        Args:
            senha: Senha em texto plano
            salt: Salt opcional (gerado se não fornecido)
            
        Returns:
            (hash, salt)
        """
        if not salt:
            salt = secrets.token_hex(16)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            senha.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100k iterations
        )
        hash_hex = hash_obj.hex()
        
        return hash_hex, salt
    
    def criar_usuario(self, username: str, senha: str, nome: str, 
                     role: str = "usuario", email: str = None) -> Dict:
        """
        Cria novo usuário
        
        Args:
            username: Nome de usuário único
            senha: Senha em texto plano
            nome: Nome completo
            role: Papel (admin, gestor, usuario)
            email: Email do usuário
            
        Returns:
            Dict com resultado
        """
        # Verificar se username já existe
        if self.colecao.find_one({"username": username}):
            return {"success": False, "erro": "Usuário já existe"}
        
        # Hash da senha
        hash_senha, salt = self._hash_senha(senha)
        
        usuario = {
            "username": username,
            "hash_senha": hash_senha,
            "salt": salt,
            "nome": nome,
            "role": role,
            "email": email,
            "criado_em": datetime.utcnow().isoformat(),
            "ultimo_login": None,
            "ativo": True
        }
        
        try:
            resultado = self.colecao.insert_one(usuario)
            return {
                "success": True,
                "id": str(resultado.inserted_id),
                "mensagem": f"Usuário {username} criado com sucesso"
            }
        except Exception as e:
            return {"success": False, "erro": str(e)}
    
    def autenticar(self, username: str, senha: str) -> Dict:
        """
        Autentica usuário
        
        Args:
            username: Nome de usuário
            senha: Senha em texto plano
            
        Returns:
            Dict com sucesso e token
        """
        usuario = self.colecao.find_one({"username": username})
        
        if not usuario:
            return {"success": False, "erro": "Usuário não encontrado"}
        
        if not usuario.get("ativo"):
            return {"success": False, "erro": "Usuário desativado"}
        
        # Verificar senha
        hash_verificacao, _ = self._hash_senha(senha, usuario["salt"])
        
        if hash_verificacao != usuario["hash_senha"]:
            return {"success": False, "erro": "Senha incorreta"}
        
        # Atualizar último login
        self.colecao.update_one(
            {"username": username},
            {"$set": {"ultimo_login": datetime.utcnow().isoformat()}}
        )
        
        # Gerar token (em produção, usar JWT)
        token = secrets.token_urlsafe(32)
        
        return {
            "success": True,
            "token": token,
            "usuario": {
                "username": usuario["username"],
                "nome": usuario["nome"],
                "role": usuario["role"],
                "email": usuario["email"]
            }
        }
    
    def verificar_permissoes(self, username: str, acao: str) -> bool:
        """
        Verifica se usuário tem permissão para ação
        
        Args:
            username: Nome de usuário
            acao: Ação a realizar (criar, deletar, etc)
            
        Returns:
            True se autorizado
        """
        usuario = self.colecao.find_one({"username": username})
        
        if not usuario:
            return False
        
        role = usuario.get("role", "usuario")
        
        # Definir permissões por role
        permissoes = {
            "admin": ["criar", "ler", "atualizar", "deletar", "exportar", "analisar"],
            "gestor": ["ler", "atualizar", "exportar", "analisar"],
            "usuario": ["ler"]
        }
        
        acoes_permitidas = permissoes.get(role, [])
        return acao in acoes_permitidas
    
    def listar_usuarios(self) -> list:
        """Lista todos os usuários"""
        usuarios = list(self.colecao.find({}, {
            "_id": 0,
            "hash_senha": 0,
            "salt": 0
        }))
        return usuarios
    
    def deletar_usuario(self, username: str) -> Dict:
        """Deleta um usuário"""
        resultado = self.colecao.delete_one({"username": username})
        
        if resultado.deleted_count > 0:
            return {"success": True, "mensagem": "Usuário deletado"}
        else:
            return {"success": False, "erro": "Usuário não encontrado"}
    
    def atualizar_senha(self, username: str, senha_nova: str) -> Dict:
        """Atualiza senha do usuário"""
        hash_nova, salt_novo = self._hash_senha(senha_nova)
        
        resultado = self.colecao.update_one(
            {"username": username},
            {"$set": {
                "hash_senha": hash_nova,
                "salt": salt_novo
            }}
        )
        
        if resultado.modified_count > 0:
            return {"success": True, "mensagem": "Senha atualizada"}
        else:
            return {"success": False, "erro": "Usuário não encontrado"}


class Audit:
    """Classe para logging de auditoria (Segurança)"""
    
    def __init__(self, colecao_audit):
        self.colecao = colecao_audit
    
    def registrar(self, usuario: str, acao: str, descricao: str, 
                  status: str = "sucesso", dados_senseis: bool = False):
        """
        Registra ação de usuário
        
        Args:
            usuario: Username que realizou ação
            acao: Tipo de ação (CREATE, READ, UPDATE, DELETE)
            descricao: Descrição da ação
            status: sucesso ou erro
            dados_senseis: Se contém dados sensíveis (não logs)
        """
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "usuario": usuario,
            "acao": acao,
            "descricao": descricao,
            "status": status,
            "dados_senseis": dados_senseis
        }
        
        self.colecao.insert_one(log)
    
    def listar_logs(self, usuario: str = None, limite: int = 100) -> list:
        """Lista logs de auditoria"""
        filtro = {}
        if usuario:
            filtro["usuario"] = usuario
        
        logs = list(self.colecao.find(
            filtro,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limite))
        
        return logs