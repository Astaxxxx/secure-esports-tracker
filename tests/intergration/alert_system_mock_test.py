import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from simulations.simulated_gaming_mouse import SimulatedGamingMouse
from dashboard.src.utils.api import getDeviceSecurityAlerts

class AlertSystemMockTest(unittest.TestCase):
    
    def setUp(self):
       
        self.test_device_id = "test-mouse-001"
        t
        self.mqtt_patcher = patch('paho.mqtt.client.Client')
        self.mock_mqtt = self.mqtt_patcher.start()
        
        self.mock_mqtt_instance = MagicMock()
        self.mock_mqtt.return_value = self.mock_mqtt_instance
        
        self.mock_mqtt_instance.publish = MagicMock(return_value=MagicMock(rc=0))
       
        def mock_connect_async(*args):
            
            self.mock_mqtt_instance.on_connect(self.mock_mqtt_instance, None, None, 0)
            
        self.mock_mqtt_instance.connect_async.side_effect = mock_connect_async
    
    def tearDown(self):
       
        self.mqtt_patcher.stop()
    
    def test_attack_alert_mqtt_publishing(self):
       
        device = SimulatedGamingMouse(
            device_id=self.test_device_id,
            mqtt_broker="localhost",
            mqtt_port=1883,
            mqtt_topic_prefix="iot/gaming/mouse"
        )
       
        device.start()
       
        device._simulate_attack(duration=3)
       
        security_topic = f"iot/gaming/mouse/{self.test_device_id}/security"
        
        security_alert_calls = [
            call_args for call_args in self.mock_mqtt_instance.publish.call_args_list
            if call_args[0][0] == security_topic
        ]
        
        self.assertGreater(len(security_alert_calls), 0, "No security alert published")
        
        alert_call = security_alert_calls[0]
        alert_payload = json.loads(alert_call[0][1])
        
        self.assertEqual(alert_payload['device_id'], self.test_device_id)
        self.assertEqual(alert_payload['alert_type'], 'attack_detected')
        self.assertIn('details', alert_payload)
        self.assertEqual(alert_payload['details']['attack_type'], 'ping_flood')
        
        device.stop()
    
    @patch('requests.get')
    def test_dashboard_api_fetch_alerts(self, mock_get):
       
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'alerts': [
                {
                    'timestamp': '2025-04-27T10:15:30.123456',
                    'event_type': 'attack_detected',
                    'details': {
                        'attack_type': 'ping_flood',
                        'intensity': 75,
                        'threshold': 50
                    },
                    'severity': 'critical'
                },
                {
                    'timestamp': '2025-04-27T10:15:40.123456',
                    'event_type': 'attack_resolved',
                    'details': {
                        'attack_type': 'ping_flood',
                        'duration': 10
                    },
                    'severity': 'info'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        with patch('dashboard.src.utils.api.localStorage', MagicMock()) as mock_storage:
            mock_storage.getItem.return_value = 'test-token'
            
            result = getDeviceSecurityAlerts(self.test_device_id)
            
            mock_get.assert_called_once()
            self.assertEqual(
                mock_get.call_args[0][0],
                f'http://localhost:5000/api/security/device_alerts/{self.test_device_id}'
            )
            
            self.assertEqual(len(result['alerts']), 2)
            self.assertEqual(result['alerts'][0]['event_type'], 'attack_detected')
            self.assertEqual(result['alerts'][1]['event_type'], 'attack_resolved')
    
    @patch('dashboard.src.utils.api.fetchWithAuth')
    def test_notify_user_on_attack(self, mock_fetch):
      
        with patch('dashboard.src.components.NotificationHandler.Notification', MagicMock()) as mock_notification:
            mock_notification_instance = MagicMock()
            mock_notification.return_value = mock_notification_instance
            
            mock_fetch.return_value = MagicMock()
            mock_fetch.return_value.json.return_value = {
                'alerts': [
                    {
                        'timestamp': '2025-04-27T10:15:30.123456',
                        'event_type': 'attack_detected',
                        'details': {
                            'attack_type': 'ping_flood',
                            'intensity': 75
                        },
                        'severity': 'critical'
                    }
                ]
            }
            
            from dashboard.src.components.NotificationHandler import checkForAttacks
         
            mock_props = {
                'selectedDevice': self.test_device_id,
                'notificationsEnabled': True
            }
         
            checkForAttacks(mock_props)
          
            mock_notification.assert_called_once()
            notification_args = mock_notification.call_args[0]
            self.assertEqual(notification_args[0], 'Security Alert')
            self.assertIn('attack detected', notification_args[1])
            self.assertIn('ping_flood', notification_args[1])

if __name__ == '__main__':
    unittest.main()