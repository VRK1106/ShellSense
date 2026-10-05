import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PREFIX = "ENC:"

class VaultService:
    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        return isinstance(value, str) and value.startswith(PREFIX)

    @classmethod
    def encrypt_value(cls, plain_text: str, master_password: str) -> str:
        """
        Encrypts plain_text using master_password with PBKDF2-derived Fernet (AES-128-CBC + HMAC).
        Returns string in format: ENC:<base64_salt>:<ciphertext>
        """
        if not plain_text or not master_password:
            return plain_text
        
        # If already encrypted, don't double encrypt
        if cls.is_encrypted(plain_text):
            return plain_text

        salt = os.urandom(16)
        key = cls._derive_key(master_password, salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(plain_text.encode('utf-8'))
        
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        cipher_str = ciphertext.decode('utf-8')
        return f"{PREFIX}{salt_b64}:{cipher_str}"

    @classmethod
    def decrypt_value(cls, enc_value: str, master_password: str):
        """
        Decrypts enc_value using master_password.
        Returns decrypted string if successful, or None if incorrect password or error.
        """
        if not cls.is_encrypted(enc_value):
            return enc_value
            
        if not master_password:
            return None

        try:
            raw_payload = enc_value[len(PREFIX):]
            parts = raw_payload.split(":", 1)
            if len(parts) != 2:
                return None
                
            salt_b64, cipher_str = parts
            salt = base64.b64decode(salt_b64.encode('utf-8'))
            key = cls._derive_key(master_password, salt)
            fernet = Fernet(key)
            decrypted = fernet.decrypt(cipher_str.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception:
            return None
