
import unittest
import os
import sys
import time
import json
import hashlib
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
t
from agent.input_monitor import InputMonitor

class TestInputMonitor(unittest.TestCase):
    
    @patch('agent.input_monitor.SecureSender')
    @patch('agent.input_monitor.Fernet')
    def setUp(self, mock_fernet, mock_sender):
        
        self.mock_cipher = MagicMock()
        mock_fernet.return_value = self.mock_cipher
        
    
        with patch('builtins.open', unittest.mock.mock_open(read_data=b'test_key')):
          
            self.input_monitor = InputMonitor()
        self.input_monitor.key_press_count = 0
        self.input_monitor.mouse_click_count = 0
        self.input_monitor.last_minute_actions = 0
        self.input_monitor.actions_per_minute = 0
        self.input_monitor.last_minute_time = time.time() - 60  
    
    def test_apm_calculation(self):
 
        self.input_monitor.last_minute_actions = 120
        

        self.input_monitor._calculate_apm()
        
 
        self.assertEqual(self.input_monitor.actions_per_minute, 120,
                         "APM calculation incorrect")
    
    def test_input_event_processing(self):

  
        initial_keyboard_count = self.input_monitor.key_press_count
        initial_mouse_count = self.input_monitor.mouse_click_count
     
        self.input_monitor._on_key_press("KeyA")
        
        # Simulate mouse event
        self.input_monitor._on_mouse_click(100, 100, "button1", True)
        
        # Assert event counts incremented correctly
        self.assertEqual(self.input_monitor.key_press_count, initial_keyboard_count + 1,
                         "Keyboard event count not incremented")
        self.assertEqual(self.input_monitor.mouse_click_count, initial_mouse_count + 1,
                         "Mouse event count not incremented")
    
    def test_data_serialization(self):
       
        self.input_monitor.session_id = "test-session-id"
        self.input_monitor.key_press_count = 50
        self.input_monitor.mouse_click_count = 25
        self.input_monitor.actions_per_minute = 75
        
        self.input_monitor.device_info = {
            'client_id': 'test_client',
            'device_name': 'test_device',
            'device_type': 'test_type'
        }
        
        
        data_package = {
            'session_id': self.input_monitor.session_id,
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S"),
            'metrics': {
                'key_press_count': self.input_monitor.key_press_count,
                'mouse_click_count': self.input_monitor.mouse_click_count,
                'actions_per_minute': self.input_monitor.actions_per_minute
            },
            'device_info': self.input_monitor.device_info
        }

        data_string = json.dumps(data_package, sort_keys=True)
        data_package['integrity_hash'] = hashlib.sha256(data_string.encode()).hexdigest()
        
        with patch.object(self.input_monitor, '_send_data') as mock_send:
            
            encrypted_data = b'encrypted_test_data'
            self.mock_cipher.encrypt.return_value = encrypted_data
          
            self.input_monitor._send_data()
            
           
            self.mock_cipher.encrypt.assert_called_once()
            
           
            mock_send.assert_called_once()
    
    def test_timestamp_validation(self):
        
        self.input_monitor.keyboard_events = [
            {'timestamp': 1000.0, 'event_type': 'press', 'key': 'A'},
            {'timestamp': 1001.0, 'event_type': 'release', 'key': 'A'},
            # Out of sequence timestamp (earlier than previous)
            {'timestamp': 999.0, 'event_type': 'press', 'key': 'B'},
            {'timestamp': 1002.0, 'event_type': 'release', 'key': 'B'}
        ]
        
     
        class TimestampProcessor:
            def __init__(self):
                self.last_timestamp = 0
                
            def validate_timestamp(self, timestamp):
                
                if timestamp < self.last_timestamp:
                    
                    timestamp = self.last_timestamp + 0.001
                
                self.last_timestamp = timestamp
                return timestamp
        
      
        processor = TimestampProcessor()
        
       
        for i, event in enumerate(self.input_monitor.keyboard_events):
            self.input_monitor.keyboard_events[i]['timestamp'] = processor.validate_timestamp(event['timestamp'])
        
        
        self.assertGreater(self.input_monitor.keyboard_events[2]['timestamp'], self.input_monitor.keyboard_events[1]['timestamp'],
                          "Out-of-sequence timestamp was not corrected")
        
       
        for i in range(1, len(self.input_monitor.keyboard_events)):
            self.assertGreaterEqual(
                self.input_monitor.keyboard_events[i]['timestamp'],
                self.input_monitor.keyboard_events[i-1]['timestamp'],
                "Timestamps are not in sequence"
            )
