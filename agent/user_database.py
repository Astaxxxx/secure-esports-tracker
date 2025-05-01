import os
import json
import base64
import logging
import hashlib
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='user_database.log'
)
logger = logging.getLogger('user_database')

class UserDatabase:
    
    def __init__(self, db_path=None, encryption_key=None):
    
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data',
            'users.db'
        )
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
  
        self.encryption_key = encryption_key or self._load_or_create_key()

        self._init_database()
        
        logger.info("User database initialized")
    
    def _load_or_create_key(self):
        key_path = os.path.join(os.path.dirname(self.db_path), 'user_db.key')
        
        try:
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    key = f.read()
                    logger.info("Loaded encryption key from file")
                    return key
            else:
                key = Fernet.generate_key()
                
                # Save to file with secure permissions
                with open(key_path, 'wb') as f:
                    f.write(key)
                os.chmod(key_path, 0o600)  # Secure file permissions
                
                logger.info("Generated new encryption key")
                return key
                
        except Exception as e:
            logger.critical(f"Failed to load or create encryption key: {e}")
            raise
    
    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login TEXT,
                encrypted_data TEXT,
                active INTEGER DEFAULT 1
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT,
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                details TEXT,
                severity TEXT DEFAULT 'info',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database schema initialized")

            if not self.get_user_count():
                self.create_user('admin', 'admin@example.com', 'admin', role='admin')
                logger.info("Created default admin user")
                
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            raise
    
    def create_user(self, username, email, password, role='user'):

        try:
            salt = os.urandom(16)
            salt_b64 = base64.b64encode(salt).decode('utf-8')

            password_hash = self._hash_password(password, salt)

            user_data = {
                'preferences': {},
                'security_questions': [],
                'creation_info': {'date': datetime.now().isoformat()}
            }
            encrypted_data = self._encrypt_data(json.dumps(user_data))

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, salt, role, created_at, encrypted_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                email,
                password_hash,
                salt_b64,
                role,
                datetime.now().isoformat(),
                encrypted_data
            ))
            
            user_id = cursor.lastrowid

            cursor.execute('''
            INSERT INTO security_events (user_id, event_type, timestamp, details, severity)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                'user_created',
                datetime.now().isoformat(),
                json.dumps({'username': username, 'role': role}),
                'info'
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created new user: {username} (role: {role})")
            return user_id
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: users.username" in str(e):
                logger.warning(f"Failed to create user: Username '{username}' already exists")
                raise ValueError(f"Username '{username}' already exists")
            elif "UNIQUE constraint failed: users.email" in str(e):
                logger.warning(f"Failed to create user: Email '{email}' already exists")
                raise ValueError(f"Email '{email}' already exists")
            else:
                logger.error(f"Database integrity error: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    def verify_user(self, username, password):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, username, email, password_hash, salt, role, encrypted_data, last_login
            FROM users
            WHERE username = ? AND active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            
            if not user:
                logger.warning(f"Login attempt for non-existent user: {username}")
                return False, None
                
            user_id, db_username, email, stored_hash, salt_b64, role, encrypted_data, last_login = user

            salt = base64.b64decode(salt_b64)
    
            calculated_hash = self._hash_password(password, salt)
            
            if calculated_hash != stored_hash:

                cursor.execute('''
                INSERT INTO security_events (user_id, event_type, timestamp, severity)
                VALUES (?, ?, ?, ?)
                ''', (
                    user_id,
                    'login_failed',
                    datetime.now().isoformat(),
                    'warning'
                ))
                
                conn.commit()
                conn.close()
                
                logger.warning(f"Failed login attempt for user: {username}")
                return False, None

            user_data = json.loads(self._decrypt_data(encrypted_data))

            cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now().isoformat(), user_id))

            cursor.execute('''
            INSERT INTO security_events (user_id, event_type, timestamp, severity)
            VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                'login_success',
                datetime.now().isoformat(),
                'info'
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successful login for user: {username}")

            return True, {
                'id': user_id,
                'username': db_username,
                'email': email,
                'role': role,
                'last_login': last_login,
                'preferences': user_data.get('preferences', {})
            }
            
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            if 'conn' in locals():
                conn.close()
            return False, None
    
    def update_user(self, user_id, data):

        try:
            updatable_fields = ['email', 'password', 'role', 'active']
            update_parts = []
            params = []
            
            for field in updatable_fields:
                if field in data:
                    if field == 'password':
 
                        salt = os.urandom(16)
                        salt_b64 = base64.b64encode(salt).decode('utf-8')
                        password_hash = self._hash_password(data['password'], salt)
                        update_parts.append('password_hash = ?')
                        update_parts.append('salt = ?')
                        params.append(password_hash)
                        params.append(salt_b64)
                    else:
                        update_parts.append(f'{field} = ?')
                        params.append(data[field])
            
            if not update_parts:
                logger.warning(f"No valid fields to update for user {user_id}")
                return False
   
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = f'''
            UPDATE users SET {', '.join(update_parts)} WHERE id = ?
            '''
            params.append(user_id)
            
            cursor.execute(query, params)
            
            if 'encrypted_data' in data:
                encrypted_data = self._encrypt_data(json.dumps(data['encrypted_data']))
                cursor.execute('''
                UPDATE users SET encrypted_data = ? WHERE id = ?
                ''', (encrypted_data, user_id))

            event_details = {field: data[field] for field in data if field != 'password' and field != 'encrypted_data'}
            if 'password' in data:
                event_details['password'] = 'updated'
                
            cursor.execute('''
            INSERT INTO security_events (user_id, event_type, timestamp, details, severity)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                'user_updated',
                datetime.now().isoformat(),
                json.dumps(event_details),
                'info'
            ))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            if success:
                logger.info(f"Updated user {user_id}: {', '.join(update_parts)}")
            else:
                logger.warning(f"No changes made for user {user_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def get_user_by_id(self, user_id):
 
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, username, email, role, created_at, last_login, encrypted_data, active
            FROM users
            WHERE id = ?
            ''', (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return None
                
            user_id, username, email, role, created_at, last_login, encrypted_data, active = user

            user_data = json.loads(self._decrypt_data(encrypted_data))
            
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'role': role,
                'created_at': created_at,
                'last_login': last_login,
                'active': bool(active),
                'preferences': user_data.get('preferences', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def get_user_by_username(self, username):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, username, email, role, created_at, last_login, encrypted_data, active
            FROM users
            WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return None
                
            user_id, username, email, role, created_at, last_login, encrypted_data, active = user
 
            user_data = json.loads(self._decrypt_data(encrypted_data))
            
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'role': role,
                'created_at': created_at,
                'last_login': last_login,
                'active': bool(active),
                'preferences': user_data.get('preferences', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def get_all_users(self, active_only=True):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
            SELECT id, username, email, role, created_at, last_login, active
            FROM users
            '''
            
            if active_only:
                query += ' WHERE active = 1'
                
            cursor.execute(query)
            
            users = []
            for row in cursor.fetchall():
                user_id, username, email, role, created_at, last_login, active = row
                users.append({
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'role': role,
                    'created_at': created_at,
                    'last_login': last_login,
                    'active': bool(active)
                })
            
            conn.close()
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def delete_user(self, user_id):
  
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
 
            cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                logger.warning(f"Attempted to delete non-existent user ID: {user_id}")
                return False
                
            username = result[0]
 
            cursor.execute('''
            UPDATE users SET active = 0 WHERE id = ?
            ''', (user_id,))

            cursor.execute('''
            INSERT INTO security_events (user_id, event_type, timestamp, details, severity)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                'user_deleted',
                datetime.now().isoformat(),
                json.dumps({'username': username}),
                'warning'
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted user {user_id} ({username})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def create_session(self, user_id, token, expires_at, ip_address=None):
        """Create a new session for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO sessions (user_id, token, created_at, expires_at, last_activity, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                token,
                datetime.now().isoformat(),
                expires_at.isoformat(),
                datetime.now().isoformat(),
                ip_address
            ))
            
            session_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created new session for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def validate_session(self, token):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            SELECT s.id, s.user_id, s.expires_at, u.username, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND u.active = 1
            ''', (token,))
            
            session = cursor.fetchone()
            
            if not session:
                conn.close()
                logger.warning(f"Invalid session token: {token[:10]}...")
                return None
                
            session_id, user_id, expires_at, username, role = session

            if datetime.fromisoformat(expires_at) < datetime.now():
                cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
                conn.commit()
                conn.close()
                logger.warning(f"Expired session token for user {user_id}")
                return None

            cursor.execute('''
            UPDATE sessions SET last_activity = ? WHERE id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            return {
                'user_id': user_id,
                'username': username,
                'role': role
            }
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def delete_session(self, token):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
            
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                logger.info(f"Deleted session: {token[:10]}...")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def log_security_event(self, event_type, user_id=None, ip_address=None, details=None, severity='info'):
 
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            details_json = None
            if details:
                if isinstance(details, dict):
                    details_json = json.dumps(details)
                else:
                    details_json = str(details)
            
            cursor.execute('''
            INSERT INTO security_events (user_id, event_type, timestamp, ip_address, details, severity)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                event_type,
                datetime.now().isoformat(),
                ip_address,
                details_json,
                severity
            ))
            
            event_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            level = logging.INFO
            if severity == 'warning':
                level = logging.WARNING
            elif severity == 'critical':
                level = logging.CRITICAL
                
            logger.log(level, f"Security event: {event_type} (user: {user_id}, severity: {severity})")
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            if 'conn' in locals():
                conn.close()
            return None
    
    def get_security_events(self, user_id=None, event_type=None, severity=None, limit=100):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT id, user_id, event_type, timestamp, ip_address, details, severity FROM security_events'
            conditions = []
            params = []
            
            if user_id:
                conditions.append('user_id = ?')
                params.append(user_id)
            
            if event_type:
                conditions.append('event_type = ?')
                params.append(event_type)
            
            if severity:
                conditions.append('severity = ?')
                params.append(severity)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
                
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            events = []
            for row in cursor.fetchall():
                event_id, user_id, event_type, timestamp, ip_address, details, severity = row
                
                details_data = None
                if details:
                    try:
                        details_data = json.loads(details)
                    except:
                        details_data = details
                
                events.append({
                    'id': event_id,
                    'user_id': user_id,
                    'event_type': event_type,
                    'timestamp': timestamp,
                    'ip_address': ip_address,
                    'details': details_data,
                    'severity': severity
                })
            
            conn.close()
            return events
            
        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def get_user_count(self):

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            if 'conn' in locals():
                conn.close()
            return 0
    
    def _hash_password(self, password, salt):

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        
        hash_bytes = kdf.derive(password.encode('utf-8'))
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def _encrypt_data(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        cipher = Fernet(self.encryption_key)
        return cipher.encrypt(data).decode('utf-8')
    
    def _decrypt_data(self, encrypted_data):

        cipher = Fernet(self.encryption_key)
        decrypted = cipher.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')
    
def get_user_database(db_path=None, encryption_key=None):

    return UserDatabase(db_path, encryption_key)

if __name__ == "__main__":
    db = get_user_database()
 
    try:
        db.create_user('admin', 'admin@example.com', 'admin', role='admin')
        print("Created admin user")
    except ValueError as e:
        print(f"Note: {e}")

    success, user = db.verify_user('admin', 'admin')
    if success:
        print(f"Login successful: {user['username']} (role: {user['role']})")
    else:
        print("Login failed")