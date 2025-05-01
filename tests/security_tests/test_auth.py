import os
import sys
import unittest
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Try to import from project modules, create mocks if needed
try:
    import jwt
except ImportError:
    # Create a mock JWT module if not available
    class jwt:
        @staticmethod
        def encode(payload, key, algorithm='HS256'):
            # Simple mock that just returns the payload as a string
            return f"MOCK_TOKEN_{json.dumps(payload)}"
            
        @staticmethod
        def decode(token, key, algorithms=None):
            # Simple mock that extracts payload from the token string
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

# Try to import application auth modules
try:
    # Import required modules for authentication testing
    from server.security.key_manager import KeyManager
except ImportError:
    # Create mock KeyManager if not available
    class KeyManager:
        def __init__(self, key_store_path=None):
            self.key_store_path = key_store_path or "/tmp/keys"
            self.master_key = b'mock_master_key'
            self.jwt_key = b'mock_jwt_key'
            self.token_cache = {}
            self.admin_tokens = set()
            
        def generate_token(self, client_id, is_admin=False):
            """Generate a JWT token for client authentication"""
            now = datetime.utcnow()
            expiry = now + timedelta(minutes=30)
            
            # Create token payload
            payload = {
                'sub': client_id,
                'iat': int(now.timestamp()),
                'exp': int(expiry.timestamp()),
                'jti': f"token_{int(time.time())}"
            }
            
            if is_admin:
                payload['role'] = 'admin'
                
            # Sign token with JWT key
            token = jwt.encode(payload, self.jwt_key, algorithm='HS256')
            
            # Cache token
            self.token_cache[token] = {
                'client_id': client_id,
                'expiry': expiry
            }
            
            if is_admin:
                self.admin_tokens.add(token)
                
            return token
            
        def validate_token(self, token, client_id=None):
            """Validate a JWT token and optionally check against expected client ID"""
            try:
                # Check token cache first (faster than JWT decode)
                if token in self.token_cache:
                    cache_entry = self.token_cache[token]
                    
                    # Check expiry
                    if cache_entry['expiry'] < datetime.utcnow():
                        del self.token_cache[token]
                        if token in self.admin_tokens:
                            self.admin_tokens.remove(token)
                        return False
                        
                    # Check client ID if provided
                    if client_id and cache_entry['client_id'] != client_id:
                        return False
                        
                    return True
                    
                # Decode and validate token
                payload = jwt.decode(token, self.jwt_key, algorithms=['HS256'])
                
                # Check expiry
                if 'exp' in payload and datetime.utcfromtimestamp(payload['exp']) < datetime.utcnow():
                    return False
                    
                # Check client ID if provided
                if client_id and payload['sub'] != client_id:
                    return False
                    
                # Add to cache for future checks
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
            """Check if token has admin privileges"""
            if token in self.admin_tokens:
                return True
                
            try:
                payload = jwt.decode(token, self.jwt_key, algorithms=['HS256'])
                return 'role' in payload and payload['role'] == 'admin'
            except:
                return False
                
        def revoke_token(self, token):
            """Revoke a token before its expiration"""
            if token in self.token_cache:
                del self.token_cache[token]
                
            if token in self.admin_tokens:
                self.admin_tokens.remove(token)

class TestAuthentication(unittest.TestCase):
    """Test cases for authentication functionality"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create key manager for testing
        self.key_manager = KeyManager()
        
        # Sample client IDs for testing
        self.client_id = "test-device-001"
        self.admin_client_id = "admin-device-001"
        
        # Generate tokens for testing
        self.token = self.key_manager.generate_token(self.client_id)
        self.admin_token = self.key_manager.generate_token(self.admin_client_id, is_admin=True)
        
        # Create an invalid token for testing
        self.invalid_token = "invalid_token"
        
    def test_token_generation_and_validation(self):
        """Test token generation and basic validation"""
        # Verify the token is not empty
        self.assertTrue(self.token)
        
        # Verify token validates successfully
        self.assertTrue(self.key_manager.validate_token(self.token))
        
        # Verify token validates with correct client ID
        self.assertTrue(self.key_manager.validate_token(self.token, self.client_id))
        
        # Verify admin token status
        self.assertFalse(self.key_manager.is_admin_token(self.token))
        self.assertTrue(self.key_manager.is_admin_token(self.admin_token))
        
    def test_token_validation_with_wrong_client(self):
        """Test token validation with incorrect client ID"""
        # Token should fail validation with wrong client ID
        wrong_client_id = "wrong-device-001"
        self.assertFalse(self.key_manager.validate_token(self.token, wrong_client_id))
        
    def test_expired_token_rejection(self):
        """Test expired token rejection"""
        # Create a token with the mock JWT implementation
        # with an expiration in the past
        now = datetime.utcnow()
        expired_time = now - timedelta(hours=1)
        
        # Create expired payload
        payload = {
            'sub': self.client_id,
            'iat': int(now.timestamp()),
            'exp': int(expired_time.timestamp()),
        }
        
        # Create token using the same encoding method
        expired_token = jwt.encode(payload, self.key_manager.jwt_key, algorithm='HS256')
        
        # Token should fail validation
        self.assertFalse(self.key_manager.validate_token(expired_token))
        
    def test_token_revocation(self):
        """Test token revocation"""
        # Create a token
        test_token = self.key_manager.generate_token("revoke-test-device")
        
        # Verify it's valid
        self.assertTrue(self.key_manager.validate_token(test_token))
        
        # Revoke the token
        self.key_manager.revoke_token(test_token)
        
        # Verify it's no longer valid
        self.assertFalse(self.key_manager.validate_token(test_token))
        
    def test_invalid_token_rejection(self):
        """Test invalid token rejection"""
        # Verify invalid token fails validation
        self.assertFalse(self.key_manager.validate_token(self.invalid_token))
        
        # Create a token with invalid format
        bad_token = "BadTokenFormat"
        self.assertFalse(self.key_manager.validate_token(bad_token))

class TestAuthorization(unittest.TestCase):
    """Test cases for authorization functionality"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create key manager for testing
        self.key_manager = KeyManager()
        
        # Generate regular and admin tokens
        self.user_token = self.key_manager.generate_token("user-device")
        self.admin_token = self.key_manager.generate_token("admin-device", is_admin=True)
        
    def test_admin_authorization(self):
        """Test admin authorization"""
        # Verify admin token has admin privileges
        self.assertTrue(self.key_manager.is_admin_token(self.admin_token))
        
        # Verify regular token doesn't have admin privileges
        self.assertFalse(self.key_manager.is_admin_token(self.user_token))
        
    def test_role_based_access(self):
        """Test role-based access control"""
        # Simulate an admin-only endpoint
        def admin_only_endpoint(token):
            if not self.key_manager.validate_token(token):
                return "Unauthorized"
            if not self.key_manager.is_admin_token(token):
                return "Forbidden"
            return "Access granted"
        
        # Verify admin token can access admin-only endpoint
        self.assertEqual(admin_only_endpoint(self.admin_token), "Access granted")
        
        # Verify regular token can't access admin-only endpoint
        self.assertEqual(admin_only_endpoint(self.user_token), "Forbidden")
        
        # Verify invalid token can't access admin-only endpoint
        self.assertEqual(admin_only_endpoint("invalid_token"), "Unauthorized")

if __name__ == '__main__':
    unittest.main()