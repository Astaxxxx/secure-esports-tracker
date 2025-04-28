#!/usr/bin/env python3
"""
Test MQTT Connection for Secure Esports Equipment Performance Tracker
Tests the MQTT connectivity between simulated devices and broker
"""

import unittest
import time
import os
import sys
import json
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import uuid
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules from project
from simulations.simulated_gaming_mouse_mqtt import SimulatedGamingMouse
from server.mqtt_subscriber import MQTTSubscriber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='mqtt_tests.log'
)
logger = logging.getLogger('mqtt_tests')

class TestMQTTConnection(unittest.TestCase):
    """Test suite for MQTT connection and communication"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        cls.mqtt_broker = os.environ.get('MQTT_BROKER', 'localhost')
        cls.mqtt_port = int(os.environ.get('MQTT_PORT', 1883))
        cls.topic_prefix = "test/iot/gaming"
        
        # Generate unique device ID for testing to avoid conflicts
        cls.test_device_id = f"test-device-{uuid.uuid4().hex[:8]}"
        
        # Start a test client to verify broker connection
        cls.test_client = mqtt.Client(client_id=f"mqtt-test-{uuid.uuid4().hex[:8]}")
        cls.is_connected = False
        
        # Define callbacks for test client
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"Test client connected to MQTT broker at {cls.mqtt_broker}:{cls.mqtt_port}")
                cls.is_connected = True
            else:
                logger.error(f"Failed to connect test client to MQTT broker with code: {rc}")

        cls.test_client.on_connect = on_connect
        
        # Try to connect to broker
        try:
            cls.test_client.connect(cls.mqtt_broker, cls.mqtt_port, 60)
            cls.test_client.loop_start()
            
            # Wait up to 5 seconds for connection
            start_time = time.time()
            while not cls.is_connected and time.time() - start_time < 5:
                time.sleep(0.1)
                
            if not cls.is_connected:
                logger.error("Could not connect to MQTT broker for testing")
                raise Exception("MQTT broker connection failed")
                
        except Exception as e:
            logger.error(f"Error setting up MQTT test environment: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done"""
        if hasattr(cls, 'test_client'):
            cls.test_client.loop_stop()
            cls.test_client.disconnect()
        
        # Additional cleanup here if needed
        logger.info("MQTT test environment cleaned up")
    
    def setUp(self):
        """Set up each test"""
        # Create a simulated device for testing
        self.device = SimulatedGamingMouse(
            device_id=self.test_device_id,
            mqtt_broker=self.mqtt_broker,
            mqtt_port=self.mqtt_port,
            mqtt_topic_prefix=f"{self.topic_prefix}/mouse",
            send_interval=0.5  # Faster updates for testing
        )
        
        # Message tracking variables
        self.received_messages = []
        self.message_received_event = threading.Event()
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'device') and self.device.running:
            self.device.stop()
        
        # Clear message tracking
        self.received_messages = []
        self.message_received_event.clear()
        
        # Sleep briefly to ensure cleanup completes
        time.sleep(0.5)
    
    def test_mqtt_connection(self):
        """Test that device can connect to MQTT broker"""
        # Setup message handlers for test validation
        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                self.received_messages.append({
                    'topic': msg.topic,
                    'payload': payload
                })
                # Set event when message received
                self.message_received_event.set()
            except json.JSONDecodeError:
                logger.error(f"Received malformed message: {msg.payload}")
        
        # Subscribe to status topic
        status_topic = f"{self.topic_prefix}/mouse/{self.test_device_id}/status"
        self.test_client.subscribe(status_topic)
        self.test_client.on_message = on_message
        
        # Start the device
        self.assertTrue(self.device.start(), "Device failed to start")
        
        # Wait for status message (up to 5 seconds)
        self.message_received_event.wait(5)
        
        # Verify we received status message
        self.assertTrue(len(self.received_messages) > 0, "No messages received")
        
        # Find status message
        status_message = None
        for msg in self.received_messages:
            if msg['topic'] == status_topic:
                status_message = msg
                break
        
        self.assertIsNotNone(status_message, "Status message not received")
        self.assertEqual(status_message['payload']['status'], "online")
        self.assertEqual(status_message['payload']['device_id'], self.test_device_id)
        
        logger.info(f"Successfully verified MQTT connection for device {self.test_device_id}")
    
    def test_mqtt_data_transmission(self):
        """Test that device can transmit data via MQTT"""
        # Clear previous messages
        self.received_messages = []
        self.message_received_event.clear()
        
        # Setup message handlers for test validation
        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                self.received_messages.append({
                    'topic': msg.topic,
                    'payload': payload
                })
                # Set event when message received
                self.message_received_event.set()
            except json.JSONDecodeError:
                logger.error(f"Received malformed message: {msg.payload}")
        
        # Subscribe to data topic
        data_topic = f"{self.topic_prefix}/mouse/{self.test_device_id}/data"
        self.test_client.subscribe(data_topic)
        self.test_client.on_message = on_message
        
        # Start the device
        self.assertTrue(self.device.start(), "Device failed to start")
        
        # Wait for data message (up to 5 seconds)
        self.message_received_event.wait(5)
        
        # Wait a bit longer to collect more messages
        time.sleep(2)
        
        # Verify we received data messages
        self.assertTrue(len(self.received_messages) > 0, "No data messages received")
        
        # Find data messages
        data_messages = [msg for msg in self.received_messages if msg['topic'] == data_topic]
        
        self.assertTrue(len(data_messages) > 0, "No data messages received on data topic")
        
        # Verify data message structure
        data_message = data_messages[0]
        self.assertEqual(data_message['payload']['device_id'], self.test_device_id)
        self.assertIn('metrics', data_message['payload'])
        self.assertIn('status', data_message['payload'])
        
        # Verify metrics fields
        metrics = data_message['payload']['metrics']
        self.assertIn('clicks_per_second', metrics)
        self.assertIn('dpi', metrics)
        self.assertIn('polling_rate', metrics)
        
        logger.info(f"Successfully verified MQTT data transmission for device {self.test_device_id}")
    
    def test_mqtt_bidirectional_communication(self):
        """Test that device can receive commands via MQTT"""
        # Start the device
        self.assertTrue(self.device.start(), "Device failed to start")
        
        # Wait for connection to establish
        time.sleep(1)
        
        # Initial DPI value should be 16000
        self.assertEqual(self.device.dpi, 16000)
        
        # Send command to change DPI
        control_topic = f"{self.topic_prefix}/mouse/{self.test_device_id}/control"
        command = {
            'command': 'set_dpi',
            'value': 8000
        }
        
        # Publish command
        result = self.test_client.publish(control_topic, json.dumps(command), qos=1)
        self.assertEqual(result.rc, mqtt.MQTT_ERR_SUCCESS)
        
        # Wait for command to be processed
        time.sleep(2)
        
        # Verify DPI was changed
        self.assertEqual(self.device.dpi, 8000)
        
        logger.info(f"Successfully verified MQTT bidirectional communication for device {self.test_device_id}")
    
    def test_mqtt_connection_resilience(self):
        """Test that device can handle MQTT broker disconnection and reconnection"""
        # Start the device
        self.assertTrue(self.device.start(), "Device failed to start")
        
        # Wait for connection to establish
        time.sleep(1)
        
        # Verify device is connected
        self.assertTrue(self.device.connected)
        
        # Simulate broker disconnection
        self.device.client.disconnect()
        
        # Wait for disconnection to register
        time.sleep(1)
        
        # Verify device is not connected
        self.assertFalse(self.device.connected)
        
        # Reconnect manually
        self.device.client.connect(self.mqtt_broker, self.mqtt_port, 60)
        
        # Wait for reconnection
        time.sleep(2)
        
        # Verify device is connected again
        self.assertTrue(self.device.connected)
        
        logger.info(f"Successfully verified MQTT connection resilience for device {self.test_device_id}")


if __name__ == '__main__':
    unittest.main()