import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

PREFIX = "ENC:"
GCM_PREFIX = "ENC:GCM:"

class VaultService:
    @staticmethod
    def _derive_raw_key(password: str, salt: bytes, length: int = 32) -> bytes:
        """Derives raw 256-bit key using PBKDF2HMAC-SHA256 (100,000 iterations)."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(password.encode('utf-8'))

    @staticmethod
    def _derive_fernet_key(password: str, salt: bytes) -> bytes:
        raw = VaultService._derive_raw_key(password, salt, length=32)
        return base64.urlsafe_b64encode(raw)

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        return isinstance(value, str) and value.startswith(PREFIX)

    @classmethod
    def encrypt_value(cls, plain_text: str, master_password: str) -> str:
        """
        Encrypts plain_text using AES-GCM-256 with PBKDF2.
        Compatible with WebCrypto API standards.
        Format: ENC:GCM:<salt_b64>:<iv_b64>:<ciphertext_with_tag_b64>
        """
        if not plain_text or not master_password:
            return plain_text
        
        if cls.is_encrypted(plain_text):
            return plain_text

        salt = os.urandom(16)
        iv = os.urandom(12)  # Standard 96-bit IV for AES-GCM
        key = cls._derive_raw_key(master_password, salt, length=32)
        
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(iv, plain_text.encode('utf-8'), None)
        
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        cipher_b64 = base64.b64encode(ciphertext).decode('utf-8')
        
        return f"{GCM_PREFIX}{salt_b64}:{iv_b64}:{cipher_b64}"

    @classmethod
    def decrypt_value(cls, enc_value: str, master_password: str):
        """
        Decrypts enc_value using master_password.
        Supports both modern AES-GCM (ENC:GCM:...) and legacy Fernet (ENC:<salt>:<ciphertext>).
        Returns decrypted string if successful, or None if incorrect password or error.
        """
        if not cls.is_encrypted(enc_value):
            return enc_value
            
        if not master_password:
            return None

        # 1. Check for modern AES-GCM format
        if enc_value.startswith(GCM_PREFIX):
            try:
                raw_payload = enc_value[len(GCM_PREFIX):]
                parts = raw_payload.split(":", 2)
                if len(parts) != 3:
                    return None
                    
                salt_b64, iv_b64, cipher_b64 = parts
                salt = base64.b64decode(salt_b64.encode('utf-8'))
                iv = base64.b64decode(iv_b64.encode('utf-8'))
                ciphertext = base64.b64decode(cipher_b64.encode('utf-8'))
                
                key = cls._derive_raw_key(master_password, salt, length=32)
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(iv, ciphertext, None)
                return decrypted.decode('utf-8')
            except Exception:
                return None

        # 2. Fallback to legacy Fernet format: ENC:<salt_b64>:<cipher_str>
        try:
            raw_payload = enc_value[len(PREFIX):]
            parts = raw_payload.split(":", 1)
            if len(parts) != 2:
                return None
                
            salt_b64, cipher_str = parts
            salt = base64.b64decode(salt_b64.encode('utf-8'))
            key = cls._derive_fernet_key(master_password, salt)
            fernet = Fernet(key)
            decrypted = fernet.decrypt(cipher_str.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception:
            return None
