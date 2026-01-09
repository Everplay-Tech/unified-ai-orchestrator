"""Encryption utilities for secrets and passwords"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption key (should be stored securely in production)
_encryption_key: Optional[bytes] = None


def get_encryption_key() -> bytes:
    """Get or generate encryption key"""
    global _encryption_key
    
    if _encryption_key is None:
        # Try to get from environment
        key_str = os.getenv("ENCRYPTION_KEY")
        if key_str:
            _encryption_key = key_str.encode()
        else:
            # Generate a new key (should be stored securely!)
            _encryption_key = Fernet.generate_key()
            print("WARNING: Generated new encryption key. Set ENCRYPTION_KEY environment variable in production!")
    
    return _encryption_key


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypt a secret string
    
    Args:
        plaintext: Secret to encrypt
    
    Returns:
        Base64-encoded encrypted string
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_secret(encrypted_str: str) -> str:
    """
    Decrypt a secret string
    
    Args:
        encrypted_str: Base64-encoded encrypted string
    
    Returns:
        Decrypted plaintext
    """
    try:
        encrypted = base64.b64decode(encrypted_str.encode())
        key = get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt secret: {e}")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2
    
    Args:
        password: Password to derive key from
        salt: Optional salt (will generate if not provided)
    
    Returns:
        Derived encryption key
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key
