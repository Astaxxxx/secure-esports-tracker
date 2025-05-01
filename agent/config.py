import os
import uuid
import socket
import hashlib
import base64
from cryptography.fernet import Fernet 

SERVER_URL = "http://localhost:5000"  
hostname = socket.gethostname()
mac_addresses = []
try:
    import uuid
    from getmac import get_mac_address
    primary_mac = get_mac_address()
    if primary_mac:
        mac_addresses.append(primary_mac)
except:

    try:
        import netifaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            try:
                mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
                if mac and mac != '00:00:00:00:00:00':
                    mac_addresses.append(mac)
            except:
                pass
    except:

        pass

if mac_addresses:

    id_seed = mac_addresses[0] + hostname
    client_id_hash = hashlib.sha256(id_seed.encode()).digest()
    CLIENT_ID = str(uuid.UUID(bytes=client_id_hash[:16]))
else:

    CLIENT_ID = str(uuid.uuid4())

key = Fernet.generate_key()
CLIENT_SECRET = base64.b64encode(key).decode('utf-8')

DEVICE_NAME = socket.gethostname()
DEVICE_TYPE = "Gaming PC"  

DATA_DIR = os.path.join(os.path.expanduser("~"), ".secure-esports-tracker")
KEY_FILE = os.path.join(DATA_DIR, "encryption.key")
LOG_FILE = os.path.join(DATA_DIR, "agent.log")

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as key_file:
        key_file.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except:
        pass  
TLS_VERIFY = True 
DATA_RETENTION_DAYS = 30  
PRIVACY_MODE = True  
credentials_file = os.path.join(DATA_DIR, "credentials.dat")
if not os.path.exists(credentials_file):
    try:
        with open(credentials_file, 'w') as f:
            f.write(f"CLIENT_ID={CLIENT_ID}\n")
            f.write(f"CLIENT_SECRET={CLIENT_SECRET}\n")
        try:
            os.chmod(credentials_file, 0o600)
        except:
            pass  
    except Exception as e:
        print(f"Error saving credentials: {e}")

print(f"Client ID: {CLIENT_ID}")
print(f"Device Name: {DEVICE_NAME}")
print(f"Device Type: {DEVICE_TYPE}")
print(f"Data Directory: {DATA_DIR}")
print(f"Server URL: {SERVER_URL}")