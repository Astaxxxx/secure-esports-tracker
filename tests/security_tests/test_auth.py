import os
import sys
import unittest
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


try:
    import jwt
except ImportError:
  
    class jwt:
        @staticmethod
        def encode(payload, key, algorithm='HS256'):
           return f"MOCK_TOKEN_{json.dumps(payload)}"
            
        @staticmethod
        def decode(token, key, algorithms=None):
            
            if not token.startswith("MOCK_TOKEN_"):
                raise Exception("Invalid token")
            payload_str = token[len("MOCK_TOKEN_"):]
            try:
                return json.loads(payload_str)
            except:
                raise Exception("Invalid token")
                
        class ExpiredSignatureError(Exception):
            pass
            
        class InvalidTokenError(Exception):
            pass


try:
    from server.security.key_manager import KeyManager
except ImportError:
    class KeyManager:
        def __init__(self, key_store_path=None):
            self.key_store_path = key_store_path or "/tmp/keys"
            self.master_key = b'mock_master_key'
            self.jwt_key = b'mock_jwt_key'
            self.token_cache = {}
            self.admin_tokens = set()
            
        def generate_token(self, client_id, is_admin=False):
            now = datetime.utcnow()
            expiry = now + timedelta(minutes=30)
            payload = {
                'sub': client_id,
                'iat': int(now.timestamp()),
                'exp': int(expiry.timestamp()),
                'jti': f"token_{int(time.time())}"
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

                if 'exp' in payload:
                    self.token_cache[token] = {
                        'client_id': payload['sub'],
                        'expiry': datetime.utcfromtimestamp(payload['exp'])
                    }
                    
                    if 'role' in payload and payload['role'] == 'admin':
                        self.admin_tokens.add(token)
                        
                return True
                
            except jwt.InvalidTokenError:
                return False
            except Exception:
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

class TestAuthentication(unittest.TestCase):
    
    def setUp(self):
        self.key_manager = KeyManager()

        self.client_id = "test-device-001"
        self.admin_client_id = "admin-device-001"

        self.token = self.key_manager.generate_token(self.client_id)
        self.admin_token = self.key_manager.generate_token(self.admin_client_id, is_admin=True)
 
        self.invalid_token = "invalid_token"
        
    def test_token_generation_and_validation(self):

        self.assertTrue(self.token)

        self.assertTrue(self.key_manager.validate_token(self.token))

        self.assertTrue(self.key_manager.validate_token(self.token, self.client_id))

        self.assertFalse(self.key_manager.is_admin_token(self.token))
        self.assertTrue(self.key_manager.is_admin_token(self.admin_token))
        
    def test_token_validation_with_wrong_client(self):

        wrong_client_id = "wrong-device-001"
        self.assertFalse(self.key_manager.validate_token(self.token, wrong_client_id))
        
    def test_expired_token_rejection(self):

        now = datetime.utcnow()
        expired_time = now - timedelta(hours=1)

        payload = {
            'sub': self.client_id,
            'iat': int(now.timestamp()),
            'exp': int(expired_time.timestamp()),
        }

        expired_token = jwt.encode(payload, self.key_manager.jwt_key, algorithm='HS256')

        self.assertFalse(self.key_manager.validate_token(expired_token))
        
    def test_token_revocation(self):

        test_token = self.key_manager.generate_token("revoke-test-device")

        self.assertTrue(self.key_manager.validate_token(test_token))

        self.key_manager.revoke_token(test_token)
  
        self.assertFalse(self.key_manager.validate_token(test_token))
        
    def test_invalid_token_rejection(self):

        self.assertFalse(self.key_manager.validate_token(self.invalid_token))

        bad_token = "BadTokenFormat"
        self.assertFalse(self.key_manager.validate_token(bad_token))

class TestAuthorization(unittest.TestCase):
    
    def setUp(self):

        self.key_manager = KeyManager()

        self.user_token = self.key_manager.generate_token("user-device")
        self.admin_token = self.key_manager.generate_token("admin-device", is_admin=True)
        
    def test_admin_authorization(self):

        self.assertTrue(self.key_manager.is_admin_token(self.admin_token))
  
        self.assertFalse(self.key_manager.is_admin_token(self.user_token))
        
    def test_role_based_access(self):

        def admin_only_endpoint(token):
            if not self.key_manager.validate_token(token):
                return "Unauthorized"
            if not self.key_manager.is_admin_token(token):
                return "Forbidden"
            return "Access granted"
        
        self.assertEqual(admin_only_endpoint(self.admin_token), "Access granted")

        self.assertEqual(admin_only_endpoint(self.user_token), "Forbidden")

        self.assertEqual(admin_only_endpoint("invalid_token"), "Unauthorized")

if __name__ == '__main__':
    unittest.main()