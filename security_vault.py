import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# GVN MASTER ALGO - AI SECURITY VAULT (AES-256 equivalent)
# This module handles encryption and decryption of sensitive broker credentials.

class SecurityVault:
    def __init__(self):
        self.key = os.getenv("GVN_MASTER_KEY")
        if not self.key:
            # Generate a new key if it doesn't exist (Only for first-time setup)
            self.key = Fernet.generate_key().decode()
            print(f"⚠️ WARNING: GVN_MASTER_KEY not found in .env. Generated new key: {self.key}")
            print("Please add this key to your .env file as GVN_MASTER_KEY=your_key")
        
        self.cipher_suite = Fernet(self.key.encode())

    def encrypt(self, plain_text):
        """Encrypts plain text to a secure token."""
        if not plain_text:
            return None
        return self.cipher_suite.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_token):
        """Decrypts a secure token back to plain text."""
        if not encrypted_token:
            return None
        try:
            return self.cipher_suite.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            print(f"❌ Decryption Error: {e}")
            return None

# Global instance
vault = SecurityVault()
