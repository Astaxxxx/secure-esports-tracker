import json
import time
import hmac
import base64
import logging
import hashlib
import requests
import os
import queue
import threading
from datetime import datetime, timedelta
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE
)
logger = logging.getLogger('secure_sender')

class SecureSender:
    
    def __init__(self, server_url, client_id, client_secret=None):
        self.server_url = server_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_token = None
        self.token_expiry = 0
        self.max_retries = 5
        self.retry_backoff_factor = 1.5  
        self.initial_retry_delay = 1.0   
        self.max_retry_delay = 30.0      
        self.offline_mode = False
        self.pending_data_queue = queue.Queue()
        self.sender_thread_running = True
        self.sender_thread = threading.Thread(target=self._background_sender)
        self.sender_thread.daemon = True
        self.sender_thread.start()
        if not self.client_secret:
            self._load_client_secret()      
        logger.info("Secure sender initialized")
           
    def _load_client_secret(self):
        try:
            credentials_file = os.path.join(config.DATA_DIR, "credentials.dat")
            if os.path.exists(credentials_file):
                with open(credentials_file, 'r') as f:
                    for line in f:
                        if line.startswith("CLIENT_SECRET="):
                            self.client_secret = line.strip().split("=", 1)[1]
                            return
            logger.warning("Client secret not found in credentials file")
        except Exception as e:
            logger.error(f"Error loading client secret: {e}")
        
    def authenticate(self, force_retry=False):
        if self.offline_mode and not force_retry:
            logger.info("Operating in offline mode, authentication skipped")
            return True
            
        retry_count = 0
        retry_delay = self.initial_retry_delay
        
        while retry_count < self.max_retries:
            try:
                timestamp = str(int(time.time()))

                auth_data = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'timestamp': timestamp,
                    'device_type': config.DEVICE_TYPE,
                    'device_name': config.DEVICE_NAME
                }
                
                signature = hmac.new(
                    self.client_secret.encode(),
                    f"{self.client_id}:{timestamp}".encode(),
                    hashlib.sha256
                ).hexdigest()
                
                auth_data['signature'] = signature
                
                try:
                    response = requests.post(
                        f"{self.server_url}/api/auth/token",
                        json=auth_data,
                        headers={
                            'Content-Type': 'application/json',
                            'X-Client-ID': self.client_id
                        },
                        timeout=10,  
                        verify=config.TLS_VERIFY
                    )
                    
                    if response.status_code == 200:
                        auth_response = response.json()
                        self.auth_token = auth_response.get('token')
                        expires_in = auth_response.get('expires_in', 1500)
                        self.token_expiry = time.time() + expires_in
                        logger.info("Authentication successful")
                        self.offline_mode = False
                        return True
                    elif response.status_code == 400 and "Client secret required for registration" in response.text:
                        if not self.client_secret:
                            logger.error("Client secret required but not available")
                            raise Exception("Client secret required for registration")
                    else:
                        logger.error(f"Authentication failed: {response.status_code} - {response.text}")

                        if response.status_code in [401, 403]:
                            return False

                except (requests.exceptions.ConnectionError, 
                        requests.exceptions.Timeout,
                        requests.exceptions.RequestException) as e:
                    logger.error(f"Network error during authentication: {e}")
        
                retry_count += 1
                if retry_count >= self.max_retries:
                    break
                    
                logger.info(f"Retrying authentication in {retry_delay:.1f} seconds (attempt {retry_count}/{self.max_retries})")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * self.retry_backoff_factor, self.max_retry_delay)
                
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                retry_count += 1
                if retry_count >= self.max_retries:
                    break
                    
                logger.info(f"Retrying authentication in {retry_delay:.1f} seconds (attempt {retry_count}/{self.max_retries})")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * self.retry_backoff_factor, self.max_retry_delay)
        
        # go to offline mode if needed 
        logger.error("Authentication failed after max retries, switching to offline mode")
        self.offline_mode = True
        return False
    
    def send_data(self, encrypted_data):
        self.pending_data_queue.put({
            'data': encrypted_data,
            'timestamp': time.time(),
            'retry_count': 0
        })
        return True 
    
    def _background_sender(self):

        while self.sender_thread_running:
            try:

                try:
                    item = self.pending_data_queue.get(timeout=1.0)
                except queue.Empty:

                    continue
                success = self._send_data_item(item)
                if not success:
                    if item['retry_count'] < self.max_retries:
                        item['retry_count'] += 1
                        delay = min(
                            self.initial_retry_delay * (self.retry_backoff_factor ** (item['retry_count'] - 1)), 
                            self.max_retry_delay
                        )
                        logger.info(f"Scheduling retry {item['retry_count']}/{self.max_retries} in {delay:.1f} seconds")
                        time.sleep(delay)
                        self.pending_data_queue.put(item)
                    else:
                        logger.warning(f"Max retries exceeded, storing data locally")
                        self._store_data_locally(item['data'])
                self.pending_data_queue.task_done()
            except Exception as e:
                logger.error(f"Error in background sender thread: {e}")
                time.sleep(1.0)
    
    def _send_data_item(self, item):
        encrypted_data = item['data']
        try:
            if self.offline_mode:
                if time.time() - item['timestamp'] > 300:
                    self.authenticate(force_retry=True)
                if self.offline_mode:
                    self._store_data_locally(encrypted_data)
                    return True  

            if not self.auth_token or time.time() > self.token_expiry:
                if not self.authenticate():
                    # If authentication fails, store data locally
                    logger.warning("Authentication failed, storing data locally")
                    self._store_data_locally(encrypted_data)
                    return True  
            encoded_data = base64.b64encode(encrypted_data).decode('utf-8')
            payload = {
                'data': encoded_data,
                'timestamp': datetime.now().isoformat(),
                'client_id': self.client_id,
                'data_type': 'performance_metrics'
            }
            request_data = json.dumps(payload, sort_keys=True)
            request_signature = hmac.new(
                self.client_secret.encode(),
                request_data.encode(),
                hashlib.sha256
            ).hexdigest()
            try:
                response = requests.post(
                    f"{self.server_url}/api/metrics/upload",
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Client-ID': self.client_id,
                        'X-Request-Signature': request_signature,
                        'Authorization': f"Bearer {self.auth_token}"
                    },
                    timeout=15,  
                    verify=config.TLS_VERIFY
                )
                if response.status_code == 200:
                    logger.info("Data successfully sent to server")
                    return True
                    
                if response.status_code == 401:
                    logger.info("Token expired, re-authenticating")
                    self.auth_token = None
                    if self.authenticate():
                        return False
                    else:
                        self._store_data_locally(encrypted_data)
                        return True
                logger.warning(f"Data upload failed: {response.status_code} - {response.text}")
                return False
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                logger.error(f"Network error sending data: {e}")
                return False
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            return False
        
    def _store_data_locally(self, encrypted_data):
        try:
            import os
            import time
            local_data_dir = os.path.join(config.DATA_DIR, 'local_data')
            os.makedirs(local_data_dir, exist_ok=True)
            timestamp = int(time.time())
            filename = f"{timestamp}_{self.client_id}.dat"
            filepath = os.path.join(local_data_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(encrypted_data)
            logger.info(f"Data stored locally: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to store data locally: {e}")
            return False
    
    def sync_local_data(self):
        if self.offline_mode:
            logger.info("Still in offline mode, skipping sync")
            return 0
        try:
            import os
            import glob 
            local_data_dir = os.path.join(config.DATA_DIR, 'local_data')
            if not os.path.exists(local_data_dir):
                return 0
            data_files = glob.glob(os.path.join(local_data_dir, '*.dat'))
            if not data_files:
                return 0    
            logger.info(f"Found {len(data_files)} locally stored data files to sync")
            if not self.auth_token or time.time() > self.token_expiry:
                if not self.authenticate():
                    logger.warning("Cannot authenticate to sync local data")
                    return 0
            files_synced = 0
            for file_path in data_files:
                try:
                    with open(file_path, 'rb') as f:
                        encrypted_data = f.read()
                    item = {
                        'data': encrypted_data,
                        'timestamp': time.time(),
                        'retry_count': 0
                    }
                    success = self._send_data_item(item)
                    
                    if success:
                        os.remove(file_path)
                        logger.info(f"Successfully synced and removed: {file_path}")
                        files_synced += 1
                except Exception as e:
                    logger.error(f"Error syncing file {file_path}: {e}")
            return files_synced     
        except Exception as e:
            logger.error(f"Error in sync_local_data: {e}")
            return 0
        
    def test_connection(self, max_retries=3):
        try:
            logger.info(f"Testing connection to server: {self.server_url}")
            retry_count = 0
            retry_delay = self.initial_retry_delay
            while retry_count <= max_retries:
                try:
                    response = requests.get(
                        self.server_url,
                        timeout=10,
                        verify=config.TLS_VERIFY
                    )
                    logger.info(f"Server connection successful: {response.status_code}")
                    if self.authenticate():
                        logger.info("Authentication test successful")
                        print("✓ Connection test successful!")
                        print("✓ Authentication successful!")
                        return True
                    else:
                        logger.error("Authentication test failed")
                        print("✗ Authentication failed")
                        return False     
                except requests.exceptions.RequestException as e:
                    logger.error(f"Server connection failed (attempt {retry_count+1}/{max_retries+1}): {e}")

                    if retry_count >= max_retries:
                        print(f"Cannot connect to server at {self.server_url}")
                        print("Please check if the server is running and accessible.")
                        return False

                    retry_count += 1
                    print(f"Retrying connection in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * self.retry_backoff_factor, self.max_retry_delay)
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            print(f"✗ Connection test failed: {e}")
            return False
            
    def stop(self):
        if hasattr(self, 'sender_thread_running'):
            self.sender_thread_running = False
            if hasattr(self, 'sender_thread') and self.sender_thread.is_alive():
                self.sender_thread.join(timeout=2.0)
            while not self.pending_data_queue.empty():
                try:
                    item = self.pending_data_queue.get(block=False)
                    self._store_data_locally(item['data'])
                    self.pending_data_queue.task_done()
                except queue.Empty:
                    break