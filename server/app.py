import re  
import os
import json
import hmac
import time
import uuid
import base64
import logging
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, abort, render_template, Response, current_app
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

from security_middleware import setup_security_headers

from utils.sanitize import sanitize_input

import routes.security

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
    filename='server.log'
)
logger = logging.getLogger('server')

app = Flask(__name__)

app = setup_security_headers(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secure-esports-tracker-secret-key')
app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', 'secure_esports.db')
app.config['JWT_KEY'] = os.environ.get('JWT_KEY', 'secure-esports-tracker-jwt-key-for-development')
app.config['CLIENT_SECRETS'] = {}  
app.iot_data = {}
app.device_alerts = {}

CORS(app, 
    resources={r"/*": {"origins": ["http://localhost:3000", "https://dashboard.example.com"]}}, 
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Client-ID", "X-Request-Signature"],
    supports_credentials=True
)

app.iot_data['mouse-001'] = [
    {
        'device_id': 'mouse-001',
        'session_id': 'test-session',
        'timestamp': datetime.now().isoformat(),
        'metrics': {
            'clicks_per_second': 4,
            'movements_count': 120,
            'dpi': 16000,
            'polling_rate': 1000,
            'avg_click_distance': 42.5,
            'button_count': 8
        },
        'status': {
            'under_attack': False,
            'attack_duration': 0,
            'battery_level': 85,
            'connection_quality': 95
        }
    }
]

app.device_alerts['mouse-001'] = [
    {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'attack_detected',
        'details': {
            'attack_type': 'ping_flood',
            'intensity': 72,
            'threshold': 50
        },
        'severity': 'critical'
    }
]

users = {
    'admin': {
        'password': generate_password_hash('admin'),
        'role': 'admin'
    },
    'user': {
        'password': generate_password_hash('user'),
        'role': 'user'
    }
}

devices = {
    'device_1': {
        'client_id': 'device_1',
        'client_secret': 'secret_1',
        'name': 'Gaming PC',
        'device_type': 'system',
        'status': 'active',
        'registered_at': datetime.utcnow().isoformat()
    },
    'device_2': {
        'client_id': 'device_2',
        'client_secret': 'secret_2',
        'name': 'Gaming Keyboard',
        'device_type': 'keyboard',
        'status': 'active',
        'registered_at': datetime.utcnow().isoformat()
    },
    'mouse-001': {
        'client_id': 'mouse-001',
        'client_secret': 'secret_mouse',
        'name': 'Gaming Mouse',
        'device_type': 'mouse',
        'status': 'active',
        'registered_at': datetime.utcnow().isoformat()
    }
}

metrics = {}  
sessions = {}  

security_events = []

@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():

    if request.method == 'OPTIONS':
        return '', 204
 
    data = sanitize_input(request.json)
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password required'}), 400

    if username in users:
        return jsonify({'error': 'Username already exists'}), 400

    users[username] = {
        'password': generate_password_hash(password),
        'email': email,
        'role': 'user' 
    }
    
    log_security_event('user_registered', {'username': username})
    
    return jsonify({
        'message': 'Registration successful',
        'username': username
    })

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 204
            
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            log_security_event('auth_failure', {'reason': 'missing_token', 'ip': request.remote_addr})
            return jsonify({'error': 'Authentication required'}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            if not isinstance(app.config['JWT_KEY'], bytes) and isinstance(app.config['JWT_KEY'], str):
                jwt_key = app.config['JWT_KEY'].encode('utf-8')
            else:
                jwt_key = app.config['JWT_KEY']
                
            payload = jwt.decode(
                token, 
                jwt_key, 
                algorithms=['HS256'],
                options={"verify_signature": True, "verify_exp": True}
            )
            
            request.user = payload
            logger.debug(f"Auth successful for user: {payload.get('sub')}")
            
        except jwt.ExpiredSignatureError:
            log_security_event('auth_failure', {'reason': 'expired_token'})
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError as e:
            log_security_event('auth_failure', {'reason': 'invalid_token', 'details': str(e)})
            return jsonify({'error': 'Invalid token', 'details': str(e)}), 401
        except Exception as e:
            log_security_event('auth_failure', {'reason': 'exception', 'details': str(e)})
            return jsonify({'error': 'Authentication error', 'details': str(e)}), 500
            
        return f(*args, **kwargs)
    return decorated

def verify_signature(f):
    @wraps(f)
    def decorated(*args, **kwargs):
  
        if request.method == 'OPTIONS':
            return '', 204
            
        client_id = request.headers.get('X-Client-ID')
        signature = request.headers.get('X-Request-Signature')
        
        if not client_id or not signature:
            log_security_event('signature_failure', {'reason': 'missing_headers'})
            return jsonify({'error': 'Missing required headers'}), 400

        client_secret = app.config['CLIENT_SECRETS'].get(client_id)
        if not client_secret:
            if client_id in devices:
                client_secret = devices[client_id].get('client_secret')
                app.config['CLIENT_SECRETS'][client_id] = client_secret
            else:
                log_security_event('signature_failure', {'reason': 'unknown_client', 'client_id': client_id})
                return jsonify({'error': 'Unknown client'}), 401

        request_data = json.dumps(request.json, sort_keys=True)
        expected_signature = hmac.new(
            client_secret.encode(),
            request_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            log_security_event('signature_failure', {'reason': 'invalid_signature', 'client_id': client_id})
            return jsonify({'error': 'Invalid signature'}), 401
            
        return f(*args, **kwargs)
    return decorated

def log_security_event(event_type, details=None, severity='info'):
    timestamp = datetime.now().isoformat()
    
    event = {
        'timestamp': timestamp,
        'event_type': event_type,
        'ip_address': request.remote_addr if request else None,
        'details': details,
        'severity': 'warning' if event_type.startswith('auth_failure') or event_type.startswith('signature_failure') else severity
    }
    
    security_events.append(event)
    logger.info(f"SECURITY EVENT: {event_type} - {details}")

app.log_security_event = log_security_event
class RouteDecorator:
    def __init__(self):
        self.require_auth = require_auth
        self.verify_signature = verify_signature
        
app.route_decorator = RouteDecorator()

security_routes = routes.security.register_security_routes(app)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>Secure Esports Tracker</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
            </style>
        </head>
        <body>
            <h1>Secure Esports Equipment Performance Tracker</h1>
            <p>Server is running. API endpoints available at /api/</p>
            <h2>Available endpoints:</h2>
            <ul>
                <li>/api/auth/login - User login</li>
                <li>/api/auth/token - Device authentication</li>
                <li>/api/auth/verify - Verify authentication token</li>
                <li>/api/metrics/upload - Upload performance metrics</li>
                <li>/api/analytics/performance - Get performance data</li>
                <li>/api/devices - Manage and view devices</li>
                <li>/api/sessions/recent - View recent sessions</li>
                <li>/api/security/logs - View security logs (admin only)</li>
                <li>/api/security/alert - Receive security alerts from IoT devices</li>
                <li>/api/security/device_alerts/:device_id - Get security alerts for a device</li>
                <li>/api/metrics/iot_data - Submit IoT device data</li>
                <li>/api/metrics/iot_data/:device_id - Get IoT device data</li>
            </ul>
        </body>
    </html>
    """

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():

    if request.method == 'OPTIONS':
        return '', 204

    data = sanitize_input(request.json)
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    user = users.get(username)
    
    if not user or not check_password_hash(user['password'], password):
        log_security_event('login_failure', {'username': username})
        return jsonify({'error': 'Invalid credentials'}), 401

    now = datetime.utcnow()
    token_data = {
        'sub': username,
        'role': user['role'],
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=24)).timestamp()),
        'jti': str(uuid.uuid4())  #
    }

    token = jwt.encode(token_data, app.config['JWT_KEY'], algorithm='HS256')
    
    log_security_event('login_success', {'username': username})
    
    return jsonify({
        'token': token,
        'user': {
            'username': username,
            'role': user['role']
        }
    })

@app.route('/api/auth/verify', methods=['GET', 'OPTIONS'])
def verify_token():

    if request.method == 'OPTIONS':
        return '', 204
        
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401
        
    token = auth_header.split(' ')[1]
    
    try:

        if not isinstance(app.config['JWT_KEY'], bytes) and isinstance(app.config['JWT_KEY'], str):
            jwt_key = app.config['JWT_KEY'].encode('utf-8')
        else:
            jwt_key = app.config['JWT_KEY']
            
        payload = jwt.decode(token, jwt_key, algorithms=['HS256'])

        username = payload.get('sub')
        role = payload.get('role', 'user')
        
        return jsonify({
            'username': username,
            'role': role
        })
        
    except jwt.ExpiredSignatureError:
        log_security_event('token_verification', {'status': 'expired'})
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError as e:
        log_security_event('token_verification', {'status': 'invalid', 'details': str(e)})
        return jsonify({'error': 'Invalid token', 'details': str(e)}), 401
    except Exception as e:
        log_security_event('token_verification', {'status': 'error', 'details': str(e)})
        return jsonify({'error': 'Verification error', 'details': str(e)}), 500

@app.route('/api/auth/token', methods=['POST', 'OPTIONS'])
def get_token():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = sanitize_input(request.json)
        client_id = data.get('client_id')
        timestamp = data.get('timestamp')
        signature = data.get('signature')
        client_secret = data.get('client_secret')
        nonce = data.get('nonce')  
        
        if not client_id or not timestamp:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            log_security_event('auth_failure', {'reason': 'timestamp_invalid', 'client_id': client_id})
            return jsonify({'error': 'Timestamp expired'}), 401

        device = devices.get(client_id)
        
        if not device:
            if not client_secret:
                return jsonify({'error': 'Client secret required for registration'}), 400
                
            device = {
                'client_id': client_id,
                'client_secret': client_secret,
                'name': f"Device {client_id[:8]}",
                'status': 'active',
                'registered_at': datetime.utcnow().isoformat(),
                'device_type': data.get('device_type', 'unknown')
            }
            devices[client_id] = device
            app.config['CLIENT_SECRETS'][client_id] = client_secret
            log_security_event('device_registered', {'client_id': client_id})
        else:
            if signature:
                signature_data = f"{client_id}:{timestamp}"
                if nonce:
                    signature_data += f":{nonce}"
                    
                expected_signature = hmac.new(
                    device['client_secret'].encode(),
                    signature_data.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    log_security_event('auth_failure', {'reason': 'signature_invalid', 'client_id': client_id})
                    return jsonify({'error': 'Invalid signature'}), 401

        now = datetime.utcnow()
        token_data = {
            'sub': client_id,
            'type': 'device',
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=30)).timestamp()),
            'jti': str(uuid.uuid4())  
        }
        
        token = jwt.encode(token_data, app.config['JWT_KEY'], algorithm='HS256')
        log_security_event('auth_success', {'client_id': client_id})
        
        return jsonify({
            'token': token,
            'expires_in': 1800  
        })
        
    except Exception as e:
        logger.error(f"Error in token generation: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/metrics/upload', methods=['POST', 'OPTIONS'])
@require_auth
@verify_signature
def upload_metrics():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = sanitize_input(request.json)
        client_id = data.get('client_id')
        encoded_data = data.get('data')
        
        if not client_id or not encoded_data:
            return jsonify({'error': 'Missing required parameters'}), 400
        encrypted_data = base64.b64decode(encoded_data)

        device = devices.get(client_id)
        if not device:
            return jsonify({'error': 'Unknown device'}), 401

        timestamp = datetime.utcnow().isoformat()
        if client_id not in metrics:
            metrics[client_id] = []
            
        metrics[client_id].append({
            'timestamp': timestamp,
            'encrypted_data': encrypted_data
        })

        log_security_event('data_received', {
            'client_id': client_id,
            'data_size': len(encoded_data)
        })
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing metrics: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    

@app.route('/api/analytics/performance', methods=['GET', 'OPTIONS'])
@require_auth
def get_performance():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        time_range = request.args.get('timeRange', 'day')
        
        now = datetime.now()
        sample_data = [
            {
                'timestamp': (now - timedelta(minutes=50)).isoformat(),
                'actions_per_minute': 120,
                'key_press_count': 100,
                'mouse_click_count': 50
            },
            {
                'timestamp': (now - timedelta(minutes=40)).isoformat(),
                'actions_per_minute': 135,
                'key_press_count': 110,
                'mouse_click_count': 60
            },
            {
                'timestamp': (now - timedelta(minutes=30)).isoformat(),
                'actions_per_minute': 142,
                'key_press_count': 115,
                'mouse_click_count': 65
            },
            {
                'timestamp': (now - timedelta(minutes=20)).isoformat(),
                'actions_per_minute': 128,
                'key_press_count': 105,
                'mouse_click_count': 55
            },
            {
                'timestamp': (now - timedelta(minutes=10)).isoformat(),
                'actions_per_minute': 138,
                'key_press_count': 112,
                'mouse_click_count': 58
            }
        ]
        
        import random
        for item in sample_data:
            item['actions_per_minute'] += random.randint(-5, 5)
            item['key_press_count'] += random.randint(-3, 3)
            item['mouse_click_count'] += random.randint(-2, 2)
        
        return jsonify({'data': sample_data})
        
    except Exception as e:
        logger.error(f"Error retrieving performance data: {e}")
  
        fallback_data = [
            {
                'timestamp': datetime.now().isoformat(),
                'actions_per_minute': 100,
                'key_press_count': 80,
                'mouse_click_count': 40
            }
        ]
        return jsonify({'data': fallback_data, 'error': str(e)})
@app.route('/api/security/logs', methods=['GET', 'OPTIONS'])
@require_auth
def get_security_logs():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        if request.user.get('role') != 'admin':
            log_security_event('access_denied', {'endpoint': 'security/logs'})
            return jsonify({'error': 'Admin access required'}), 403

        severity = request.args.get('severity', 'all')
        
        if severity == 'all':
            filtered_logs = security_events
        else:
            filtered_logs = [log for log in security_events if log.get('severity') == severity]
            
        return jsonify({'logs': filtered_logs})
        
    except Exception as e:
        logger.error(f"Error retrieving security logs: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/devices', methods=['GET', 'OPTIONS'])
@require_auth
def get_devices():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        user_devices = []
        for device_id, device in devices.items():
            device_info = {
                'client_id': device_id,
                'name': device.get('name', f"Device {device_id[:8]}"),
                'device_type': device.get('device_type', 'unknown'),
                'status': device.get('status', 'active'),
                'registered_at': device.get('registered_at', datetime.utcnow().isoformat())
            }
            user_devices.append(device_info)
        
        return jsonify({'devices': user_devices})
        
    except Exception as e:
        logger.error(f"Error retrieving devices: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/devices/register', methods=['POST', 'OPTIONS'])
@require_auth
def register_device():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = sanitize_input(request.json)
        device_name = data.get('name')
        device_type = data.get('device_type', 'unknown')
        
        if not device_name:
            return jsonify({'error': 'Device name is required'}), 400

        client_id = str(uuid.uuid4())
        client_secret = base64.b64encode(os.urandom(32)).decode('utf-8')

        devices[client_id] = {
            'client_id': client_id,
            'client_secret': client_secret,
            'name': device_name,
            'device_type': device_type,
            'status': 'active',
            'registered_at': datetime.utcnow().isoformat()
        }
        
        log_security_event('device_registered', {
            'client_id': client_id,
            'device_name': device_name,
            'device_type': device_type
        })
        return jsonify({
            'client_id': client_id,
            'client_secret': client_secret,
            'name': device_name,
            'device_type': device_type,
            'status': 'active'
        })
        
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/sessions/recent', methods=['GET', 'OPTIONS'])
@require_auth
def get_recent_sessions():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        filter_type = request.args.get('filter', 'all')
        recent_sessions = [
            {
                'id': '1',
                'start_time': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'duration_minutes': 120,
                'average_apm': 130,
                'device_name': 'Gaming PC'
            },
            {
                'id': '2',
                'start_time': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                'duration_minutes': 90,
                'average_apm': 145,
                'device_name': 'Gaming PC'
            },
            {
                'id': '3',
                'start_time': (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                'duration_minutes': 60,
                'average_apm': 138,
                'device_name': 'Gaming PC'
            }
        ]

        if filter_type == 'week':
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_sessions = [s for s in recent_sessions if datetime.fromisoformat(s['start_time']) > week_ago]
        elif filter_type == 'month':
            month_ago = datetime.utcnow() - timedelta(days=30)
            recent_sessions = [s for s in recent_sessions if datetime.fromisoformat(s['start_time']) > month_ago]
        
        return jsonify({'sessions': recent_sessions})
        
    except Exception as e:
        logger.error(f"Error retrieving recent sessions: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/devices/stats', methods=['GET', 'OPTIONS'])
@require_auth
def get_device_stats():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:

        device_stats = [
            {
                'device_name': 'Gaming PC',
                'usage_percentage': 0.75,
                'average_apm': 135,
                'total_sessions': 12
            },
            {
                'device_name': 'Laptop',
                'usage_percentage': 0.25,
                'average_apm': 110,
                'total_sessions': 4
            }
        ]
        
        return jsonify({'devices': device_stats})
        
    except Exception as e:
        logger.error(f"Error retrieving device statistics: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/users/settings', methods=['PUT', 'OPTIONS'])
@require_auth
def update_user_settings():

    if request.method == 'OPTIONS':
        return '', 204
        
    try:

        data = sanitize_input(request.json)
        username = request.user.get('sub')

        return jsonify({'status': 'success', 'message': 'Settings updated'})
        
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/device/<device_id>/command', methods=['POST', 'OPTIONS'])
@require_auth
def send_device_command(device_id):

    if request.method == 'OPTIONS':
        return '', 204
        
    try:

        from utils.sanitize import sanitize_input, is_safe_path

        if not re.match(r'^[a-zA-Z0-9\-_]+$', device_id):
            return jsonify({'error': 'Invalid device ID format'}), 400
            
        data = sanitize_input(request.json)
        command = data.get('command')
        
        if not command:
            return jsonify({'error': 'Command required'}), 400

        if device_id not in devices:
            return jsonify({'error': 'Device not found'}), 404
        log_security_event('device_command', {
            'device_id': device_id,
            'command': command,
            'parameters': data
        })
        
        return jsonify({
            'status': 'success', 
            'message': f'Command {command} sent to device {device_id}'
        })
        
    except Exception as e:
        logger.error(f"Error sending device command: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

if __name__ == '__main__':
    print("Starting Secure Esports Equipment Performance Tracker Server...")
    print("Server available at http://localhost:5000")
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)