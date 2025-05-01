import os
import time
import uuid
import json
import logging
import hashlib
import base64
from datetime import datetime, timedelta

import jwt
from cryptography.fernet import Fernet

logger = logging.getLogger('security.key_manager')

class KeyManager:

    def __init__(self, key_store_path=None):
        self.key_store_path = key_store_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'data',
            'keys'
        )
        
        os.makedirs(self.key_store_path, exist_ok=True)

        os.chmod(self.key_store_path, 0o700)

        self.master_key = self._load_or_create_master_key()

        self.jwt_key = self._load_or_create_jwt_key()

        self.token_cache = {}
        self.admin_tokens = set()
        
        logger.info("Key Manager initialized")
        
    def _load_or_create_master_key(self):
        master_key_path = os.path.join(self.key_store_path, 'master.key')
        
        try:
            if os.path.exists(master_key_path):
                with open(master_key_path, 'rb') as f:
                    key = f.read()
                    return key
            else:
                key = Fernet.generate_key()
                
                # Save to file with secure permissions
                with open(master_key_path, 'wb') as f:
                    f.write(key)
                os.chmod(master_key_path, 0o600)
                
                logger.info("Generated new master key")
                return key
                
        except Exception as e:
            logger.critical(f"Failed to load or create master key: {e}")
            raise
            
    def _load_or_create_jwt_key(self):
        jwt_key_path = os.path.join(self.key_store_path, 'jwt.key')
        
        try:
            if os.path.exists(jwt_key_path):
                with open(jwt_key_path, 'rb') as f:
                    key = f.read()
                    return key
            else:
                key = os.urandom(32)
                with open(jwt_key_path, 'wb') as f:
                    f.write(key)
                os.chmod(jwt_key_path, 0o600)
                
                logger.info("Generated new JWT signing key")
                return key
                
        except Exception as e:
            logger.critical(f"Failed to load or create JWT key: {e}")
            raise
            
    def generate_device_key(self):
        return Fernet.generate_key()
        
    def encrypt_with_master(self, data):
        """Encrypt data with the master key"""
        cipher = Fernet(self.master_key)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        return cipher.encrypt(data)
        
    def decrypt_with_master(self, encrypted_data):

        cipher = Fernet(self.master_key)
        return cipher.decrypt(encrypted_data)
        
    def generate_token(self, client_id, is_admin=False):

        now = datetime.utcnow()
        expiry = now + timedelta(minutes=30)

        payload = {
            'sub': client_id,
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
            'jti': str(uuid.uuid4()) 
        }
        
        if is_admin:
            payload['role'] = 'admin'
            
        token = jwt.encode(payload, self.jwt_key, algorithm='HS256')
        
        self.token_cache[token] = {
            'client_id': client_id,
            'expiry': expiry
        }
        
        if is_admin:
            self.admin_tokens.add(token)
            
        logger.info(f"Generated token for client: {client_id}")
        return token
        
    def validate_token(self, token, client_id=None):
        try:
            if token in self.token_cache:
                cache_entry = self.token_cache[token]

                if cache_entry['expiry'] < datetime.utcnow():
                    del self.token_cache[token]
                    if token in self.admin_tokens:
                        self.admin_tokens.remove(token)
                    return False

                if client_id and cache_entry['client_id'] != client_id:
                    return False
                    
                return True

            payload = jwt.decode(token, self.jwt_key, algorithms=['HS256'])
            if 'exp' in payload and datetime.utcfromtimestamp(payload['exp']) < datetime.utcnow():
                return False
            if client_id and payload['sub'] != client_id:
                return False

            self.token_cache[token] = {
                'client_id': payload['sub'],
                'expiry': datetime.utcfromtimestamp(payload['exp'])
            }
            
            if 'role' in payload and payload['role'] == 'admin':
                self.admin_tokens.add(token)
                
            return True
            
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token validation attempt")
            return False
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
            
    def is_admin_token(self, token):
 
        if token in self.admin_tokens:
            return True
            
        try:
            payload = jwt.decode(token, self.jwt_key, algorithms=['HS256'])
            return 'role' in payload and payload['role'] == 'admin'
        except:
            return False
            
    def revoke_token(self, token):
 
        if token in self.token_cache:
            del self.token_cache[token]
            
        if token in self.admin_tokens:
            self.admin_tokens.remove(token)
            
    def rotate_master_key(self):
        old_key = self.master_key
        new_key = Fernet.generate_key()

        master_key_path = os.path.join(self.key_store_path, 'master.key')
        with open(master_key_path, 'wb') as f:
            f.write(new_key)
            
        self.master_key = new_key
        logger.info("Master key rotated")
        
        return old_key, new_key
        
    def cleanup_expired_tokens(self):

        now = datetime.utcnow()
        expired_tokens = [
            token for token, data in self.token_cache.items()
            if data['expiry'] < now
        ]
        
        for token in expired_tokens:
            del self.token_cache[token]
            if token in self.admin_tokens:
                self.admin_tokens.remove(token)
                
        return len(expired_tokens)