import os
import json
import time
import logging
import threading
import ssl
from datetime import datetime
import paho.mqtt.client as mqtt
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',  
    filename='mqtt_subscriber.log'
)
logger = logging.getLogger('mqtt_subscriber')

class MQTTSubscriber:

    def __init__(self, mqtt_broker="localhost", mqtt_port=1883, 
                 mqtt_topic_prefix="iot/gaming/mouse", db_uri=None,
                 use_tls=False, ca_cert=None, client_cert=None, client_key=None):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.db_uri = db_uri or os.environ.get('DB_URI', 'sqlite:///iot_devices.db')
        self.running = False

        self.use_tls = use_tls
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key

        self.client_id = f"server-subscriber-{hashlib.sha256(os.urandom(32)).hexdigest()[:8]}"
        
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if self.use_tls:
            self.client.tls_set(
                ca_certs=self.ca_cert,
                certfile=self.client_cert,
                keyfile=self.client_key,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None
            )

        mqtt_username = os.environ.get('MQTT_USERNAME')
        mqtt_password = os.environ.get('MQTT_PASSWORD')
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)
    
    def _on_connect(self, client, userdata, flags, rc):
        
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
        
            client.subscribe(f"{self.mqtt_topic_prefix}/+/security", qos=2)  
            client.subscribe(f"{self.mqtt_topic_prefix}/+/data", qos=1)
            client.subscribe(f"{self.mqtt_topic_prefix}/+/status", qos=1)
            
            logger.info(f"Subscribed to topics: {self.mqtt_topic_prefix}/+/data, /status, /security")
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
    
    def _on_message(self, client, userdata, msg):

        try:
    
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 3:
                logger.warning(f"Received message with invalid topic format: {msg.topic}")
                return
                
            device_id = topic_parts[-2]
            message_type = topic_parts[-1]
   
            if not self._is_valid_identifier(device_id):
                logger.warning(f"Received message with invalid device ID: {device_id}")
                return
     
            try:
                if len(msg.payload) > 10240: 
                    logger.warning(f"Message payload too large ({len(msg.payload)} bytes) from {device_id}")
                    return
                    
                payload = json.loads(msg.payload)

                if not isinstance(payload, dict):
                    logger.warning(f"Invalid payload format from {device_id}: not a JSON object")
                    return

                payload = self._sanitize_payload(payload)

                if message_type == 'data':
                    self._process_data_message(device_id, payload)
                elif message_type == 'status':
                    self._process_status_message(device_id, payload)
                elif message_type == 'security':
                    self._process_security_message(device_id, payload)
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON payload from {device_id}")
                return
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def _is_valid_identifier(self, identifier):

        import re
 
        pattern = r'^[a-zA-Z0-9\-_]+$'
        return bool(re.match(pattern, identifier))
    
    def _sanitize_payload(self, payload):
    
        if isinstance(payload, dict):
            return {k: self._sanitize_payload(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload]
        elif isinstance(payload, str):
           
            return payload.replace('<', '&lt;').replace('>', '&gt;')
        else:
            return payload
    
    def start(self):
        self.running = True
   
        import signal
        def signal_handler(sig, frame):
            logger.info("Received signal to shut down")
            self.stop()
            import sys
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            try:
                logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
                self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
                self.client.loop_start()
                
                time.sleep(2)

                if not self.client.is_connected():
                    logger.warning("Failed to connect, retrying...")
                    retry_count += 1
                    time.sleep(2 ** retry_count)  
                    continue
                    
                logger.info("MQTT subscriber started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to MQTT broker: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Maximum retry attempts reached, giving up")
                    self.running = False
                    return False
                    
                time.sleep(2 ** retry_count) 
        
        return False
    
    def stop(self):

        if self.running:
            self.running = False
            
            try:
                logger.info("Disconnecting from MQTT broker")
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("MQTT subscriber stopped")
            except Exception as e:
                logger.error(f"Error stopping MQTT subscriber: {str(e)}")

def test_mqtt_connection(mqtt_broker="localhost", mqtt_port=1883, timeout=5,
                         use_tls=False, ca_cert=None, client_cert=None, client_key=None):

    import time
    import paho.mqtt.client as mqtt
    import threading
    import hashlib
    
    client_id = f"mqtt-test-{hashlib.sha256(os.urandom(32)).hexdigest()[:8]}"

    result = {
        'success': False,
        'connection_time': None,
        'error': None,
        'broker_info': f"{mqtt_broker}:{mqtt_port}"
    }
  
    connected = False
    connection_event = threading.Event()

    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            logger.info(f"Successfully connected to MQTT broker at {mqtt_broker}:{mqtt_port}")
            connection_event.set()
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            result['error'] = error_msg
            connection_event.set()
    
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
 
    client = mqtt.Client(client_id=client_id)

    if use_tls:
        try:
            client.tls_set(
                ca_certs=ca_cert,
                certfile=client_cert,
                keyfile=client_key,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None
            )
        except Exception as e:
            result['error'] = f"TLS setup error: {str(e)}"
            return result

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        start_time = time.time()
 
        client.connect_async(mqtt_broker, mqtt_port, 60)
        
        client.loop_start()

        if connection_event.wait(timeout):

            connection_time = time.time() - start_time
            result['connection_time'] = round(connection_time, 3)
            result['success'] = connected
        else:
            result['error'] = f"Connection timeout after {timeout} seconds"
            logger.error(f"MQTT connection timeout after {timeout} seconds")
    
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        logger.error(f"Error connecting to MQTT broker: {error_msg}")
    
    finally:

        client.loop_stop()
        if connected:
            client.disconnect()
    
    return result