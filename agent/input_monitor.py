import time
import json
import uuid
import hashlib
import logging
import threading
import os
import socket
from datetime import datetime
from pynput import keyboard, mouse
from cryptography.fernet import Fernet
from secure_sender import SecureSender
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE
)
logger = logging.getLogger('input_monitor')

class InputMonitor:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.keyboard_events = []
        self.mouse_events = []
        self.key_press_count = 0
        self.mouse_click_count = 0
        self.actions_per_minute = 0
        self.last_minute_actions = 0
        self.last_minute_time = time.time()
        self.offline_mode = False
        
        try:
            with open(config.KEY_FILE, 'rb') as key_file:
                key = key_file.read()
                self.cipher = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
            raise
        
        self.sender = SecureSender(config.SERVER_URL, config.CLIENT_ID, config.CLIENT_SECRET)
        self.running = True
        self.apm_thread = threading.Thread(target=self._calculate_apm)
        self.apm_thread.daemon = True
        self.apm_thread.start()
        os.makedirs(os.path.join(config.DATA_DIR, 'local_data'), exist_ok=True)
        self.iot_devices = {}
        self.iot_thread = threading.Thread(target=self._monitor_iot_devices)
        self.iot_thread.daemon = True
        self.iot_thread.start()

        logger.info(f"Input monitoring session started: {self.session_id}")
        
    def start(self):
        if not self.sender.test_connection():
            logger.warning("Server connection failed. Starting in offline mode.")
            self.offline_mode = True
            print("Running in offline mode - data will be stored locally")
        else:
            self.offline_mode = False
            print("Connected to server - data will be uploaded in real-time")
            
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        try:
            print(f"Input monitoring started. Press Ctrl+C to stop.")
            while self.running:

                time.sleep(10)
                self._send_data()
                if not self.offline_mode:
                    self.sender.sync_local_data()
        except KeyboardInterrupt:
            print("\nStopping input monitoring...")
            self.stop()
        except Exception as e:
            logger.error(f"Error in input monitor main loop: {e}")
            self.stop()
            
    def stop(self):
        self.running = False
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        try:
            self._send_data(final=True)  
        except Exception as e:
            logger.error(f"Error sending final data: {e}")
        
        logger.info(f"Input monitoring session ended: {self.session_id}")
        print("Input monitoring stopped.")

    def _on_key_press(self, key):
        try:
            event = {
                'timestamp': time.time(),
                'event_type': 'press',
                'key': str(key) if not config.PRIVACY_MODE else 'key_press'
            }
            self.keyboard_events.append(event)
            self.key_press_count += 1
            self.last_minute_actions += 1

            logger.debug(f"Key press recorded (count: {self.key_press_count})")
        except Exception as e:
            logger.error(f"Error handling key press: {e}")

    def _on_key_release(self, key):
        try:
            event = {
                'timestamp': time.time(),
                'event_type': 'release',
                'key': str(key) if not config.PRIVACY_MODE else 'key_release'
            }
            self.keyboard_events.append(event)
            logger.debug("Key release recorded")
        except Exception as e:
            logger.error(f"Error handling key release: {e}")

    def _on_mouse_move(self, x, y):
        try:
            if len(self.mouse_events) % 5 == 0:
                event = {
                    'timestamp': time.time(),
                    'event_type': 'move',
                    'x': x,
                    'y': y
                }
                self.mouse_events.append(event)
            logger.debug("Mouse move recorded")
        except Exception as e:
            logger.error(f"Error handling mouse move: {e}")

    def _on_mouse_click(self, x, y, button, pressed):
        try:
            event = {
                'timestamp': time.time(),
                'event_type': 'click',
                'button': str(button),
                'pressed': pressed,
                'x': x,
                'y': y
            }
            self.mouse_events.append(event)
            if pressed:
                self.mouse_click_count += 1
                self.last_minute_actions += 1
            logger.debug(f"Mouse click recorded (count: {self.mouse_click_count})")
        except Exception as e:
            logger.error(f"Error handling mouse click: {e}")

    def _on_mouse_scroll(self, x, y, dx, dy):
        try:
            event = {
                'timestamp': time.time(),
                'event_type': 'scroll',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy
            }
            self.mouse_events.append(event)
            self.last_minute_actions += 1
            logger.debug("Mouse scroll recorded")
        except Exception as e:
            logger.error(f"Error handling mouse scroll: {e}")

    def _calculate_apm(self):
        while self.running:
            try:
                current_time = time.time()
                elapsed = current_time - self.last_minute_time
                
                if elapsed >= 60:
                    self.actions_per_minute = self.last_minute_actions
                    self.last_minute_actions = 0
                    self.last_minute_time = current_time
                    logger.info(f"Current APM: {self.actions_per_minute}")
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error calculating APM: {e}")

    def _send_data(self, final=False):
 
        try:
            if not (self.keyboard_events or self.mouse_events) and not final:
                return

            data_package = {
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'metrics': {
                    'key_press_count': self.key_press_count,
                    'mouse_click_count': self.mouse_click_count,
                    'actions_per_minute': self.actions_per_minute
                },
                'device_info': {
                    'client_id': config.CLIENT_ID,
                    'device_name': config.DEVICE_NAME,
                    'device_type': config.DEVICE_TYPE
                }
            }

            data_string = json.dumps(data_package, sort_keys=True)
            data_package['integrity_hash'] = hashlib.sha256(data_string.encode()).hexdigest()

            encrypted_data = self.cipher.encrypt(json.dumps(data_package).encode())
 
            response = self.sender.send_data(encrypted_data)
            
            if response and response.status_code == 200:
                logger.info("Data successfully sent to server")

                self.keyboard_events = []
                self.mouse_events = []
            elif not response and self.offline_mode:
                logger.info("Data stored locally (offline mode)")
                # Clear events since they've been stored locally
                self.keyboard_events = []
                self.mouse_events = []
            else:
                logger.warning(f"Failed to send data: {response}")
                
        except Exception as e:
            logger.error(f"Error sending data: {e}")

    def _monitor_iot_devices(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', 5001))
                sock.listen(5)
                
                while self.running:
                    client, addr = sock.accept()
                    data = client.recv(1024)
                    if data:
                        self._process_iot_data(data)
                    client.close()
                    
            except Exception as e:
                logger.error(f"Error monitoring IoT devices: {e}")
                time.sleep(5)  

    def _process_iot_data(self, data):
        try:
            data = json.loads(data.decode())
            
            if 'attack_source' in data:
                logger.warning(f"Attack detected on {data['device_type']}: {data['packet_count']} packets from {data['attack_source']}")
                self._send_attack_data(data)
            else:
                device_type = data['device_type']
                self.iot_devices[device_type] = data['metrics']
                logger.info(f"Received metrics from {device_type}: {data['metrics']}")         
        except Exception as e:
            logger.error(f"Error processing IoT data: {e}")
    def _send_attack_data(self, attack_data): 
        try:
            data_package = {
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'attack_data': attack_data,
                'device_info': {
                    'client_id': config.CLIENT_ID,
                    'device_name': config.DEVICE_NAME,
                    'device_type': config.DEVICE_TYPE
                }
            }   
            encrypted_data = self.cipher.encrypt(json.dumps(data_package).encode())
            self.sender.send_data(encrypted_data)   
        except Exception as e:
            logger.error(f"Error sending attack data: {e}")
if __name__ == "__main__":
    try:
        monitor = InputMonitor()
        monitor.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.critical(f"Fatal error in input monitor: {e}")
        print(f"Error: {e}")