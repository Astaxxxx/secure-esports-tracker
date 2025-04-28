
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the function to test
from server.mqtt_utils import test_mqtt_connection

class TestMQTTConnection(unittest.TestCase):
    """Test cases for MQTT connection functionality"""
    
    @patch('server.mqtt_utils.mqtt.Client')
    def test_successful_connection(self, mock_client):
        """Test successful MQTT connection"""
        # Set up mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Simulate successful connection
        def simulate_connection(client, userdata, flags, rc):
            client.on_connect(client, userdata, flags, 0)
            
        mock_instance.connect_async.side_effect = lambda *args: simulate_connection(mock_instance, None, None, 0)
        
        # Run the test
        result = test_mqtt_connection()
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['connection_time'])
        self.assertIsNone(result['error'])
    
    @patch('server.mqtt_utils.mqtt.Client')
    def test_failed_connection(self, mock_client):
        """Test failed MQTT connection"""
        # Set up mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Simulate failed connection
        def simulate_connection(client, userdata, flags, rc):
            client.on_connect(client, userdata, flags, 3)
            
        mock_instance.connect_async.side_effect = lambda *args: simulate_connection(mock_instance, None, None, 3)
        
        # Run the test
        result = test_mqtt_connection()
        
        # Verify results
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Server unavailable")

if __name__ == '__main__':
    unittest.main()