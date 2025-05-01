import unittest
import os
import sys
import time
import json
import threading
import paho.mqtt.client as mqtt
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from server.app import app as flask_app
from server.routes.security import register_security_routes
from simulations.simulated_gaming_mouse import SimulatedGamingMouse

class AlertSystemIntegrationTest(unittest.TestCase):
  
    
    @classmethod
    def setUpClass(cls):
      
        cls.app = flask_app.test_client()
        flask_app.config['TESTING'] = True
 
        cls.mqtt_client = mqtt.Client(client_id="test-subscriber")
        cls.mqtt_client.on_connect = cls._on_connect
        cls.mqtt_client.on_message = cls._on_message
        cls.received_messages = []
        cls.alert_received_event = threading.Event()
    
        try:
            cls.mqtt_client.connect("localhost", 1883, 60)
            cls.mqtt_client.loop_start()
        except Exception as e:
            print(f"WARNING: Could not connect to MQTT broker: {e}")
            print("Tests will run but MQTT functionality will be mocked")
            cls.mqtt_available = False
        else:
            cls.mqtt_available = True
    
    @classmethod
    def tearDownClass(cls):
       
        if cls.mqtt_available:
            cls.mqtt_client.loop_stop()
            cls.mqtt_client.disconnect()
    
    @classmethod
    def _on_connect(cls, client, userdata, flags, rc):
      
        if rc == 0:
            print("Connected to MQTT broker")
           
            client.subscribe("iot/gaming/+/+/security")
        else:
            print(f"Failed to connect to MQTT broker with code: {rc}")
    
    @classmethod
    def _on_message(cls, client, userdata, msg):
      
        try:
            payload = json.loads(msg.payload)
            print(f"Received MQTT message on topic {msg.topic}: {payload}")
            cls.received_messages.append({
                'topic': msg.topic,
                'payload': payload
            })
            
      
            if 'alert_type' in payload and payload['alert_type'] == 'attack_detected':
                cls.alert_received_event.set()
                
        except json.JSONDecodeError:
            print(f"Received malformed message: {msg.payload}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def setUp(self):
       
        self.__class__.received_messages = []
        self.__class__.alert_received_event.clear()
   
        self.test_device_id = f"test-mouse-{int(time.time())}"
        
        self.device = SimulatedGamingMouse(
            device_id=self.test_device_id,
            mqtt_broker="localhost",
            mqtt_port=1883,
            mqtt_topic_prefix="iot/gaming/mouse"
        )
    
    def tearDown(self):
    
        if hasattr(self, 'device') and self.device.running:
            self.device.stop()
    
    def test_attack_detection_to_notification(self):
    
        if not self.__class__.mqtt_available:
            self.skipTest("MQTT broker not available")
     
        self.device.start()
        time.sleep(2) 

        print("Triggering simulated attack...")
        self.device._simulate_attack(duration=5)
   
        alert_received = self.__class__.alert_received_event.wait(10)
        self.assertTrue(alert_received, "Alert notification was not received")
        
     
        security_alerts = [msg for msg in self.__class__.received_messages 
                          if '/security' in msg['topic']]
        self.assertGreater(len(security_alerts), 0, "No security alerts received")
      
        alert = security_alerts[0]['payload']
        self.assertEqual(alert['device_id'], self.test_device_id)
        self.assertEqual(alert['alert_type'], 'attack_detected')
        self.assertIn('details', alert)
        self.assertIn('attack_type', alert['details'])
        
       
        response = self.app.get(f'/api/debug/device_alerts/{self.test_device_id}')
        self.assertEqual(response.status_code, 200)
     
        response_data = json.loads(response.data)
        self.assertIn('alerts', response_data)
        self.assertGreater(len(response_data['alerts']), 0, "No alerts found in server")
 
        server_alert = response_data['alerts'][0]
        self.assertEqual(server_alert['event_type'], 'attack_detected')
        self.assertEqual(server_alert['severity'], 'critical')
   
        resolution_timeout = time.time() + 10
        resolution_alert_found = False
        
        while time.time() < resolution_timeout and not resolution_alert_found:
         
            for msg in self.__class__.received_messages:
                payload = msg['payload']
                if 'alert_type' in payload and payload['alert_type'] == 'attack_resolved':
                    resolution_alert_found = True
                    break
            
            if not resolution_alert_found:
                time.sleep(0.5)
        
        self.assertTrue(resolution_alert_found, "Attack resolution notification was not received")
       
        response = self.app.get(f'/api/debug/device_alerts/{self.test_device_id}')
        response_data = json.loads(response.data)
       
        resolution_in_server = False
        for alert in response_data['alerts']:
            if 'event_type' in alert and alert['event_type'] == 'attack_resolved':
                resolution_in_server = True
                break
        
        self.assertTrue(resolution_in_server, "Attack resolution not recorded in server")
    
    def test_dashboard_api_integration(self):
       
        mock_alert = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'attack_detected',
            'details': {
                'attack_type': 'ping_flood',
                'intensity': 75,
                'threshold': 50
            },
            'severity': 'critical'
        }
      
        if not hasattr(flask_app, 'device_alerts'):
            flask_app.device_alerts = {}
        
        if self.test_device_id not in flask_app.device_alerts:
            flask_app.device_alerts[self.test_device_id] = []
            
        flask_app.device_alerts[self.test_device_id].append(mock_alert)
       
        response = self.app.get(f'/api/debug/device_alerts/{self.test_device_id}')
        self.assertEqual(response.status_code, 200)
     
        response_data = json.loads(response.data)
        self.assertIn('alerts', response_data)
        self.assertEqual(len(response_data['alerts']), 1, "Alert not found in server response")
        
        # Verify alert details
        alert = response_data['alerts'][0]
        self.assertEqual(alert['event_type'], 'attack_detected')
        self.assertEqual(alert['severity'], 'critical')
        self.assertIn('details', alert)
        self.assertIn('attack_type', alert['details'])
        self.assertEqual(alert['details']['attack_type'], 'ping_flood')
        

        del flask_app.device_alerts[self.test_device_id]

if __name__ == '__main__':
    unittest.main()