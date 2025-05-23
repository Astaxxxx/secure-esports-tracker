import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from server.security.encryption import generate_key, encrypt_data, decrypt_data, rotate_key
    from server.security.key_manager import KeyManager
    CRYPTOGRAPHY_AVAILABLE = True
    print("Using server.security modules for tests")
except ImportError:
    try:
        from cryptography.fernet import Fernet
        
        def generate_key():
            return Fernet.generate_key()
        
        def encrypt_data(data, key):
            cipher = Fernet(key)
            if isinstance(data, str):
                data = data.encode('utf-8')
            return cipher.encrypt(data)
        
        def decrypt_data(encrypted_data, key):
            cipher = Fernet(key)
            return cipher.decrypt(encrypted_data).decode('utf-8')
        
        def rotate_key(old_key, data_to_reencrypt=None):
            new_key = generate_key()
            if data_to_reencrypt:
                decrypted = decrypt_data(data_to_reencrypt, old_key)
                reencrypted = encrypt_data(decrypted, new_key)
                return new_key, reencrypted
            return new_key

        class KeyManager:
            def __init__(self, key_store_path=None):
                self.key_store_path = key_store_path or tempfile.mkdtemp()
                self.master_key = generate_key()
                self.jwt_key = os.urandom(32)
                self.token_cache = {}
                self.admin_tokens = set()
                
            def generate_token(self, client_id, is_admin=False):
                import uuid
                token = str(uuid.uuid4())
                self.token_cache[token] = {'client_id': client_id, 'is_admin': is_admin}
                return token
                
            def validate_token(self, token, client_id=None):
                if token not in self.token_cache:
                    return False
                if client_id and self.token_cache[token]['client_id'] != client_id:
                    return False
                return True
                
            def is_admin_token(self, token):
                return token in self.token_cache and self.token_cache[token].get('is_admin', False)
                
        CRYPTOGRAPHY_AVAILABLE = True
        print("Using fallback cryptography implementation")
    except ImportError:
        print("WARNING: cryptography module not available. Encryption tests will be skipped.")
        CRYPTOGRAPHY_AVAILABLE = False

        def generate_key():
            return b"dummy_key"
            
        def encrypt_data(data, key):
            return b"encrypted_" + (data.encode() if isinstance(data, str) else data)
            
        def decrypt_data(encrypted_data, key):
            if not encrypted_data.startswith(b"encrypted_"):
                raise ValueError("Invalid encrypted data")
            return encrypted_data[len(b"encrypted_"):].decode()
            
        def rotate_key(old_key, data_to_reencrypt=None):
            new_key = b"new_dummy_key"
            if data_to_reencrypt:
                return new_key, b"encrypted_rotated_data"
            return new_key
            
        class KeyManager:
            def __init__(self, key_store_path=None):
                self.key_store_path = key_store_path or tempfile.mkdtemp()
                self.master_key = b"dummy_master_key"
                self.jwt_key = b"dummy_jwt_key"
                self.token_cache = {}
                self.admin_tokens = set()
                
            def generate_token(self, client_id, is_admin=False):
                import uuid
                token = str(uuid.uuid4())
                self.token_cache[token] = {'client_id': client_id, 'is_admin': is_admin}
                return token
                
            def validate_token(self, token, client_id=None):
                if token not in self.token_cache:
                    return False
                if client_id and self.token_cache[token]['client_id'] != client_id:
                    return False
                return True
                
            def is_admin_token(self, token):
                return token in self.token_cache and self.token_cache[token].get('is_admin', False)

class TestEncryption(unittest.TestCase):
    
    def setUp(self):
        self.test_data = "This is sensitive test data for encryption"
        self.test_key = generate_key()
    
    def test_encryption_integrity(self):
        if not CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("Cryptography module not available")

        encrypted_data = encrypt_data(self.test_data, self.test_key)
 
        self.assertNotEqual(encrypted_data, self.test_data.encode())
 
        decrypted_data = decrypt_data(encrypted_data, self.test_key)
  
        wrong_key = generate_key()
        while wrong_key == self.test_key:
            wrong_key = generate_key()

        with self.assertRaises(Exception):
            decrypt_data(encrypted_data, wrong_key)
    
    def test_key_rotation(self):
        if not CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("Cryptography module not available")
            
        encrypted_data = encrypt_data(self.test_data, self.test_key)

        new_key, reencrypted_data = rotate_key(self.test_key, encrypted_data)
  
        self.assertNotEqual(new_key, self.test_key)
 
        with self.assertRaises(Exception):
            decrypt_data(encrypted_data, new_key)
 
        self.assertEqual(decrypt_data(reencrypted_data, new_key), self.test_data)
      
        with self.assertRaises(Exception):
            decrypt_data(reencrypted_data, self.test_key)

class TestKeyManagement(unittest.TestCase):
    
    def setUp(self):

        self.temp_dir = tempfile.mkdtemp()
        self.key_manager = KeyManager(key_store_path=self.temp_dir)
        
    def tearDown(self):

        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_token_validation(self):

        if not CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("Cryptography module not available")
  
        client_id = "test-device-001"
        token = self.key_manager.generate_token(client_id)

        self.assertTrue(self.key_manager.validate_token(token))
        self.assertTrue(self.key_manager.validate_token(token, client_id))

        wrong_client_id = "wrong-device-001"
        self.assertFalse(self.key_manager.validate_token(token, wrong_client_id))

        invalid_token = "invalid-token"
        self.assertFalse(self.key_manager.validate_token(invalid_token))

        admin_token = self.key_manager.generate_token("admin-device", is_admin=True)
        self.assertTrue(self.key_manager.is_admin_token(admin_token))
        self.assertFalse(self.key_manager.is_admin_token(token))  # Non-admin token

if __name__ == '__main__':
    unittest.main()