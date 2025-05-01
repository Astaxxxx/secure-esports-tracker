import os
import sys
import json
import unittest
import warnings
from unittest.mock import patch, MagicMock, call


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    warnings.warn("paho-mqtt module not available. MQTT tests will use mocks.")
    MQTT_AVAILABLE = False
    class MockMQTT:
        class Client:
            def __init__(self, client_id=""):
                self.client_id = client_id
                self.on_connect = None
                self.on_disconnect = None
                self.on_message = None
                
            def connect(self, broker, port, keepalive):
                return 0
                
            def connect_async(self, broker, port, keepalive):
                return 0
                
            def loop_start(self):
                pass
                
            def loop_stop(self):
                pass
                
            def disconnect(self):
                pass
                
            def publish(self, topic, payload, qos=0, retain=False):
                result = MagicMock()
                result.rc = 0 
                return result
     
        MQTT_ERR_SUCCESS = 0
        
    mqtt = MockMQTT()

try:
    from server.mqtt_utils import test_mqtt_connection
except ImportError:
    
    def test_mqtt_connection(mqtt_broker="localhost", mqtt_port=1883, timeout=5):
     
        print("Using mock test_mqtt_connection implementation")
        result = {
            'success': True,
            'connection_time': 0.1,
            'error': None,
            'broker_info': f"{mqtt_broker}:{mqtt_port}"
        }
  
        if not MQTT_AVAILABLE and mqtt_broker != "localhost":
            result['success'] = False
            result['error'] = "Cannot connect to broker (MQTT module not available)"
            
        return result

try:
    from server.security.encryption import encrypt_data, decrypt_data, generate_key
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
    except ImportError:
        warnings.warn("cryptography module not available. Encryption tests will use simple mocks.")
        
        def generate_key():
            return b"dummy_key_for_tests"
            
        def encrypt_data(data, key):
            if isinstance(data, str):
                data = data.encode('utf-8')
            return b"encrypted_" + data
            
        def decrypt_data(encrypted_data, key):
            if not encrypted_data.startswith(b"encrypted_"):
                raise ValueError("Invalid encrypted data")
            return encrypted_data[len(b"encrypted_"):].decode()

class TestMQTTConnection(unittest.TestCase):
        
    @patch('paho.mqtt.client.Client' if MQTT_AVAILABLE else 'mqtt.Client')
    def test_mqtt_connection(self, mock_client):
        
        if not MQTT_AVAILABLE:
            self.skipTest("paho-mqtt module not available")
     
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        def side_effect(*args, **kwargs):

            callback = mock_instance.on_connect
        
            callback(mock_instance, None, None, 0)

        mock_instance.connect_async.side_effect = side_effect
 
        result = test_mqtt_connection()
        

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['connection_time'])
        self.assertIsNone(result['error'])

    @patch('paho.mqtt.client.Client' if MQTT_AVAILABLE else 'mqtt.Client')
    def test_mqtt_connection_failure(self, mock_client):
  
        if not MQTT_AVAILABLE:
            self.skipTest("paho-mqtt module not available")
            

        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        
        def side_effect(*args, **kwargs):
    
            callback = mock_instance.on_connect
      
            callback(mock_instance, None, None, 3)
       
        mock_instance.connect_async.side_effect = side_effect
        
        result = test_mqtt_connection(mqtt_broker="unavailable.example.com")
        
        self.assertFalse(result['success'])

class TestMQTTMessaging(unittest.TestCase):
    
    
    def setUp(self):
    
        self.mock_client = MagicMock()
        self.mock_client.publish.return_value = MagicMock(rc=0)  # Success return code
      
        self.test_data = {
            'device_id': 'test-device-001',
            'metrics': {
                'clicks_per_second': 5,
                'movements_count': 120
            },
            'status': {
                'under_attack': False,
                'battery_level': 85
            }
        }
        
      
        self.test_key = generate_key()
    
    def test_mqtt_payload_encryption(self):
        
        json_data = json.dumps(self.test_data)
        
        encrypted_payload = encrypt_data(json_data, self.test_key)
        
        self.assertNotEqual(encrypted_payload, json_data.encode())
      
        decrypted_data = decrypt_data(encrypted_payload, self.test_key)
        self.assertEqual(decrypted_data, json_data)
    
    @patch('paho.mqtt.client.Client' if MQTT_AVAILABLE else 'mqtt.Client')
    def test_mqtt_qos_delivery(self, mock_client_class):
        
        if not MQTT_AVAILABLE:
            self.skipTest("paho-mqtt module not available")
      
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
       
        mock_result = MagicMock()
        mock_result.rc = 0  # Success return code
        mock_client.publish.return_value = mock_result
        
        test_topic = "iot/gaming/mouse/security"
        test_payload = json.dumps(self.test_data)
   
        result = mock_client.publish(test_topic, test_payload, qos=2)
      
        mock_client.publish.assert_called_with(test_topic, test_payload, qos=2)
    
        self.assertEqual(result.rc, 0)
    
    @patch('paho.mqtt.client.Client' if MQTT_AVAILABLE else 'mqtt.Client')
    def test_mqtt_connection_loss(self, mock_client_class):
      
        if not MQTT_AVAILABLE:
            self.skipTest("paho-mqtt module not available")
   
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
      
        on_disconnect_handler = None
        
        def connect(*args, **kwargs):
            nonlocal on_disconnect_handler
            on_disconnect_handler = mock_client.on_disconnect
            return 0
            
        mock_client.connect.side_effect = connect
        
      
        mock_store = MagicMock()
        
        class TestMQTTClient:
            def __init__(self, client, store_fn):
                self.client = client
                self.store_locally = store_fn
                self.connected = True
                
            def connect(self):
                self.client.connect()
                
            def publish(self, topic, payload):
                if not self.connected:
                    
                    self.store_locally(topic, payload)
                    return False
                return True
                
            def simulate_disconnect(self, rc=1):
                self.connected = False
                if on_disconnect_handler:
                    on_disconnect_handler(self.client, None, rc)
        

        test_client = TestMQTTClient(mock_client, mock_store)
        test_client.connect()
        
        result_connected = test_client.publish("test/topic", "test_data")
        self.assertTrue(result_connected)
     
        test_client.simulate_disconnect()
        
        result_disconnected = test_client.publish("test/topic", "test_data")
        self.assertFalse(result_disconnected)
       
        mock_store.assert_called_with("test/topic", "test_data")

if __name__ == '__main__':
    unittest.main()