import pyotp
import qrcode
from io import BytesIO
import base64
import time

class GerenciadorMFA:
    def __init__(self, colecao_usuarios):
        self.colecao = colecao_usuarios
        self.secrets_temporarios = {}
    
    def gerar_secret_mfa(self, username: str):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        self.secrets_temporarios[username] = secret
        
        print(f"\n[GERAR_SECRET] Username: {username}")
        print(f"[GERAR_SECRET] Secret: {secret}")
        
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name='Lixeira Inteligente'
        )
        
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{img_str}"
        }
    
    def ativar_mfa(self, username: str, secret: str, codigo: str):
        try:
            if secret is None:
                secret = self.secrets_temporarios.get(username)
                if not secret:
                    return {"success": False, "erro": "gere um qr code primeiro"}
            
            totp = pyotp.TOTP(secret)
            timestamp_atual = int(time.time())
            
            print(f"\n[ATIVAR_MFA] Username: {username}")
            print(f"[ATIVAR_MFA] Secret: {secret}")
            print(f"[ATIVAR_MFA] Codigo fornecido: {codigo}")
            print(f"[ATIVAR_MFA] Timestamp: {timestamp_atual}")
            
            # tentar com TODOS os codigos dos ultimos 10 periodos
            for i in range(-10, 11):
                timestamp_teste = timestamp_atual + (i * 30)
                codigo_esperado = pyotp.TOTP(secret).at(timestamp_teste)
                print(f"  testando: {codigo_esperado}")
                
                if codigo == codigo_esperado:
                    print(f"[ATIVAR_MFA] SUCESSO! Codigo bateu!")
                    self.colecao.update_one(
                        {"username": username},
                        {"$set": {"mfa_ativado": True, "mfa_secret": secret}}
                    )
                    
                    if username in self.secrets_temporarios:
                        del self.secrets_temporarios[username]
                    
                    return {"success": True, "mensagem": "MFA ativado com sucesso!"}
            
            print(f"[ATIVAR_MFA] FALHOU - codigo nao bateu com nenhum teste")
            return {"success": False, "erro": "codigo mfa invalido"}
        
        except Exception as e:
            print(f"[ATIVAR_MFA] EXCECAO: {str(e)}")
            return {"success": False, "erro": str(e)}
    
    def verificar_codigo_mfa(self, username: str, codigo: str):
        try:
            usuario = self.colecao.find_one({"username": username})
            
            if not usuario or not usuario.get("mfa_ativado"):
                return {"success": True, "mfa_requerido": False}
            
            secret = usuario.get("mfa_secret")
            if not secret:
                return {"success": False, "erro": "secret nao encontrado"}
            
            totp = pyotp.TOTP(secret)
            timestamp_atual = int(time.time())
            
            print(f"\n[VERIFICACAO] Username: {username}")
            print(f"[VERIFICACAO] Secret: {secret}")
            print(f"[VERIFICACAO] Codigo fornecido: {codigo}")
            print(f"[VERIFICACAO] Timestamp: {timestamp_atual}")
            
            # tentar com TODOS os codigos dos ultimos 10 periodos
            for i in range(-10, 11):
                timestamp_teste = timestamp_atual + (i * 30)
                codigo_esperado = pyotp.TOTP(secret).at(timestamp_teste)
                print(f"  testando: {codigo_esperado}")
                
                if codigo == codigo_esperado:
                    print(f"[VERIFICACAO] SUCESSO!")
                    return {"success": True, "mfa_requerido": True, "verificado": True}
            
            print(f"[VERIFICACAO] FALHOU")
            return {"success": False, "erro": "codigo mfa invalido"}
        
        except Exception as e:
            print(f"[VERIFICACAO] EXCECAO: {str(e)}")
            return {"success": False, "erro": str(e)}