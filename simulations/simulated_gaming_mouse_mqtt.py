import time
import random
import json
import threading
import argparse
import paho.mqtt.client as mqtt
from datetime import datetime
import os
import numpy as np
from collections import defaultdict

class SimulatedGamingMouse:
    
    def __init__(self, device_id="mouse-001", mqtt_broker="localhost", mqtt_port=1883, 
                 mqtt_topic_prefix="iot/gaming/mouse", send_interval=1):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.send_interval = send_interval
        self.dpi = 16000
        self.polling_rate = 1000  # Hz
        self.button_count = 8
        self.running = False
        self.session_id = None
        self.screen_width = 1920
 
        self.position_heatmap = np.zeros((self.screen_height//10, self.screen_width//10))
        self.click_heatmap = np.zeros((self.screen_height//10, self.screen_width//10))
  
        self.clicks_per_second = 0
        self.movement_data = []
        self.connected = False
        
        self.ping_count = 0
        self.ping_threshold = 50 
        self.under_attack = False
        self.attack_start_time = None
        self.attack_cooldown = False
        self.attack_cooldown_until = 0
        self.attack_min_duration = 5 
        
        self.client = mqtt.Client(client_id=f"simulated-{self.device_id}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        self.data_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/data"
        self.status_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/status"
        self.security_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/security"
        self.control_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/control"
        self.heatmap_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/heatmap"
        
    def _on_connect(self, client, userdata, flags, rc):
        
        if rc == 0:
            print(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.connected = True
         
            self.client.subscribe(self.control_topic)
            self.client.on_message = self._on_message
        
            self._publish_status("online")
        else:
            print(f"Failed to connect to MQTT broker with code: {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        
        print(f"Disconnected from MQTT broker with code: {rc}")
        self.connected = False
    
    def _on_message(self, client, userdata, msg):
       
        try:
            payload = json.loads(msg.payload)
            if msg.topic == self.control_topic:
                self._handle_control_message(payload)
        except json.JSONDecodeError:
            print(f"Received malformed message: {msg.payload}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def _handle_control_message(self, payload):
      
        if 'command' in payload:
            command = payload['command']
            print(f"Received command: {command}")
            
            if command == 'set_dpi':
                if 'value' in payload:
                    self.dpi = payload['value']
                    print(f"DPI set to {self.dpi}")
                    self._publish_status("dpi_changed")
            
            elif command == 'set_polling_rate':
                if 'value' in payload:
                    self.polling_rate = payload['value']
                    print(f"Polling rate set to {self.polling_rate} Hz")
                    self._publish_status("polling_rate_changed")
            
            elif command == 'restart':
                print("Restarting device...")
                self._publish_status("restarting")
                self.stop()
                time.sleep(2)
                self.start()
            
            elif command == 'trigger_attack':
                duration = payload.get('duration', 5)
                print(f"Manually triggering attack simulation for {duration} seconds")
                self._simulate_attack(duration)
    
    def start(self):
       
        self.running = True
        self.session_id = f"session_{int(time.time())}"
        
        mqtt_result = test_mqtt_connection(
        mqtt_broker=self.mqtt_broker,
        mqtt_port=self.mqtt_port
        )
    
        if not mqtt_result['success']:
            logger.error(f"Cannot start simulation - MQTT broker unreachable: {mqtt_result['error']}")
            self.running = False
            return False
  
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False
      
        self.main_thread = threading.Thread(target=self._run)
        self.main_thread.daemon = True
        self.main_thread.start()
        
        self.network_thread = threading.Thread(target=self._monitor_network)
        self.network_thread.daemon = True
        self.network_thread.start()
        
        self.heatmap_thread = threading.Thread(target=self._heatmap_publisher)
        self.heatmap_thread.daemon = True
        self.heatmap_thread.start()
        
        print(f"Simulated gaming mouse started with ID: {self.device_id}")
        print(f"Session ID: {self.session_id}")
        print(f"Simulating network traffic and attack detection...")
        return True
        
    def stop(self):
        
        if self.running:
            self.running = False
            
            if self.connected:
                self._publish_status("offline")
           
            self.client.loop_stop()
            self.client.disconnect()
            
            if hasattr(self, 'main_thread') and self.main_thread.is_alive():
                self.main_thread.join(timeout=2)
            if hasattr(self, 'network_thread') and self.network_thread.is_alive():
                self.network_thread.join(timeout=2)
            if hasattr(self, 'heatmap_thread') and self.heatmap_thread.is_alive():
                self.heatmap_thread.join(timeout=2)
                
            print("Simulated gaming mouse stopped")
        
    def _generate_performance_data(self):
   
        hour = datetime.now().hour
        if 9 <= hour <= 22:  
            self.clicks_per_second = random.randint(1, 6)
        else:  
            self.clicks_per_second = random.randint(0, 2)
     
        for _ in range(self.clicks_per_second):
            x = random.randint(0, self.screen_width)
            y = random.randint(0, self.screen_height)
            
   
            grid_x = min(x // 10, self.position_heatmap.shape[1]-1)
            grid_y = min(y // 10, self.position_heatmap.shape[0]-1)
            
     
            self.position_heatmap[grid_y, grid_x] += 1
            
            # Update click heatmap (only clicks)
            if random.random() < 0.3:  # 30% chance this movement has a click
                self.click_heatmap[grid_y, grid_x] += 1
            
            self.movement_data.append({
                'x': x,
                'y': y,
                'timestamp': time.time()
            })
          
        self.movement_data = self.movement_data[-100:]
        
        avg_click_distance = 0
        if len(self.movement_data) > 1:
            distances = []
            for i in range(1, len(self.movement_data)):
                prev = self.movement_data[i-1]
                curr = self.movement_data[i]
                distance = ((curr['x'] - prev['x'])**2 + (curr['y'] - prev['y'])**2)**0.5
                distances.append(distance)
            if distances:
                avg_click_distance = sum(distances) / len(distances)
        

        base_temp = 28.0  
        activity_factor = (self.clicks_per_second / 6) * 8
        device_temperature = base_temp + activity_factor
        
        if self.under_attack:
            device_temperature += 3.5  
        
        return {
            'device_id': self.device_id,
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'clicks_per_second': self.clicks_per_second,
                'movements_count': len(self.movement_data),
                'dpi': self.dpi,
                'polling_rate': self.polling_rate,
                'avg_click_distance': round(avg_click_distance, 2),
                'button_count': self.button_count,
                'device_temperature': round(device_temperature, 1)
            },
            'status': {
                'under_attack': self.under_attack,
                'attack_duration': self._get_attack_duration() if self.under_attack else 0,
                'battery_level': random.randint(20, 100),  # Simulate battery level
                'connection_quality': random.randint(70, 100) if not self.under_attack else random.randint(30, 60)
            }
        }
        
    def _get_attack_duration(self):
   
        if self.attack_start_time:
            return int(time.time() - self.attack_start_time)
        return 0
    
    def _publish_data(self, data):
    
        if not self.connected:
            return False
            
        try:
            payload = json.dumps(data)
            result = self.client.publish(self.data_topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing data: {e}")
            return False
    
    def _publish_status(self, status):
        
        if not self.connected and status != "offline":
            return False
            
        try:
            payload = json.dumps({
                'device_id': self.device_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            })
            result = self.client.publish(self.status_topic, payload, qos=1, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing status: {e}")
            return False
    
    def _publish_security_alert(self, alert_type, details):
        """Publish security alert via MQTT"""
        if not self.connected:
            return False
            
        try:
            payload = json.dumps({
                'device_id': self.device_id,
                'alert_type': alert_type,
                'timestamp': datetime.now().isoformat(),
                'details': details
            })
            result = self.client.publish(self.security_topic, payload, qos=2)  
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing security alert: {e}")
            return False
    
    def _publish_heatmap(self):
        if not self.connected:
            return False
            
        try:
            position_max = max(1, np.max(self.position_heatmap))
            click_max = max(1, np.max(self.click_heatmap))
            
            normalized_position = (self.position_heatmap / position_max * 100).astype(int).tolist()
            normalized_clicks = (self.click_heatmap / click_max * 100).astype(int).tolist()
            
            payload = json.dumps({
                'device_id': self.device_id,
                'timestamp': datetime.now().isoformat(),
                'position_heatmap': normalized_position,
                'click_heatmap': normalized_clicks,
                'resolution': {
                    'width': self.screen_width // 10,
                    'height': self.screen_height // 10
                }
            })
            result = self.client.publish(self.heatmap_topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing heatmap data: {e}")
            return False
    
    def _heatmap_publisher(self):
        while self.running:
            try:

                time.sleep(5)
                self._publish_heatmap()
            except Exception as e:
                print(f"Error in heatmap publisher: {e}")
    
    def _simulate_attack(self, duration=5):
       
        if not self.under_attack:
            self.under_attack = True
            self.attack_start_time = time.time()
            attack_intensity = random.randint(70, 100)
            print(f"⚠️ ALERT: Device is under attack! Received {attack_intensity} pings in 1 second")
            
            self._publish_security_alert('attack_detected', {
                'attack_type': 'ping_flood',
                'intensity': attack_intensity,
                'threshold': self.ping_threshold
            })
      
            def resolve_attack():
                time.sleep(duration)
                if self.under_attack:
                    attack_duration = self._get_attack_duration()
                    self.under_attack = False
                    self.attack_start_time = None
                    print(f" Attack stopped. Duration: {attack_duration} seconds")
                   
                    self._publish_security_alert('attack_resolved', {
                        'attack_type': 'ping_flood',
                        'duration': attack_duration
                    })
                    
                    self.attack_cooldown = True
                    self.attack_cooldown_until = time.time() + 10  
                
        
            attack_thread = threading.Thread(target=resolve_attack)
            attack_thread.daemon = True
            attack_thread.start()
    
    def _monitor_network(self):
     
        while self.running:
            try:
              
                self.ping_count = 0
                
               
                if self.attack_cooldown and time.time() > self.attack_cooldown_until:
                    self.attack_cooldown = False
                
               
                if not self.under_attack and not self.attack_cooldown and random.random() < 0.05:
                    self._simulate_attack(random.randint(5, 10))
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"Error monitoring network: {e}")
                time.sleep(1)
    
    def _run(self):
        
        while self.running:
            #
            data = self._generate_performance_data()
            self._publish_data(data)
            
            time.sleep(self.send_interval)


class SimulatedGamingKeyboard:
    
    def __init__(self, device_id="keyboard-001", mqtt_broker="localhost", mqtt_port=1883, 
                 mqtt_topic_prefix="iot/gaming/keyboard", send_interval=1):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self.send_interval = send_interval
        self.polling_rate = 1000  # Hz
        self.key_count = 104      # Full keyboard with numpad
        self.running = False
        self.session_id = None
        
        self.key_usage = defaultdict(int)
        self.commonly_used_keys = ['W', 'A', 'S', 'D', 'SPACE', 'SHIFT', 'CTRL', 'E', 'R', 'F']
        
        self.keypresses_per_second = 0
        self.key_events = []
        self.connected = False
        s
        self.suspicious_events = 0
        self.event_threshold = 50  
        self.under_attack = False
        self.attack_start_time = None
        self.attack_cooldown = False
        self.attack_cooldown_until = 0
        self.attack_min_duration = 5  
      
        self.illumination_mode = "reactive" 
        self.illumination_color = "rgb(255, 0, 0)"  
        self.illumination_brightness = 80 
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=f"simulated-{self.device_id}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # Set up MQTT topics
        self.data_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/data"
        self.status_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/status"
        self.security_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/security"
        self.control_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/control"
        self.keymap_topic = f"{self.mqtt_topic_prefix}/{self.device_id}/keymap"
        
    def _on_connect(self, client, userdata, flags, rc):
        
        if rc == 0:
            print(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.connected = True
          
            self.client.subscribe(self.control_topic)
            self.client.on_message = self._on_message
            
            self._publish_status("online")
        else:
            print(f"Failed to connect to MQTT broker with code: {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        
        print(f"Disconnected from MQTT broker with code: {rc}")
        self.connected = False
    
    def _on_message(self, client, userdata, msg):
       
        try:
            payload = json.loads(msg.payload)
            if msg.topic == self.control_topic:
                self._handle_control_message(payload)
        except json.JSONDecodeError:
            print(f"Received malformed message: {msg.payload}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def _handle_control_message(self, payload):
    
        if 'command' in payload:
            command = payload['command']
            print(f"Received command: {command}")
            
            if command == 'set_illumination':
                self.illumination_mode = payload.get('mode', self.illumination_mode)
                self.illumination_color = payload.get('color', self.illumination_color)
                self.illumination_brightness = payload.get('brightness', self.illumination_brightness)
                print(f"Illumination set to {self.illumination_mode} mode, {self.illumination_color}, {self.illumination_brightness}% brightness")
                self._publish_status("illumination_changed")
            
            elif command == 'set_polling_rate':
                if 'value' in payload:
                    self.polling_rate = payload['value']
                    print(f"Polling rate set to {self.polling_rate} Hz")
                    self._publish_status("polling_rate_changed")
            
            elif command == 'restart':
                print("Restarting device...")
                self._publish_status("restarting")
                self.stop()
                time.sleep(2)
                self.start()
            
            elif command == 'trigger_attack':
                duration = payload.get('duration', 5)
                print(f"Manually triggering attack simulation for {duration} seconds")
                self._simulate_attack(duration)
    
    def start(self):
      
        self.running = True
        self.session_id = f"session_{int(time.time())}"
    
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False
        
        self.main_thread = threading.Thread(target=self._run)
        self.main_thread.daemon = True
        self.main_thread.start()
        
        self.network_thread = threading.Thread(target=self._monitor_network)
        self.network_thread.daemon = True
        self.network_thread.start()
    
        self.keymap_thread = threading.Thread(target=self._keymap_publisher)
        self.keymap_thread.daemon = True
        self.keymap_thread.start()
        
        print(f"Simulated gaming keyboard started with ID: {self.device_id}")
        print(f"Session ID: {self.session_id}")
        print(f"Simulating keyboard activity and attack detection...")
        return True
        
    def stop(self):
    
        if self.running:
            self.running = False
           
            if self.connected:
                self._publish_status("offline")
                
            self.client.loop_stop()
            self.client.disconnect()
      
            if hasattr(self, 'main_thread') and self.main_thread.is_alive():
                self.main_thread.join(timeout=2)
            if hasattr(self, 'network_thread') and self.network_thread.is_alive():
                self.network_thread.join(timeout=2)
            if hasattr(self, 'keymap_thread') and self.keymap_thread.is_alive():
                self.keymap_thread.join(timeout=2)
                
            print("Simulated gaming keyboard stopped")
    
    def _generate_performance_data(self):
    
        hour = datetime.now().hour
        if 9 <= hour <= 22:  
            self.keypresses_per_second = random.randint(2, 8)
        else: 
            self.keypresses_per_second = random.randint(0, 3)
   
        for _ in range(self.keypresses_per_second):
         
            if random.random() < 0.8:
                key = random.choice(self.commonly_used_keys)
            else:
                key = chr(random.randint(65, 90))  
            
           
            self.key_usage[key] += 1
           
            self.key_events.append({
                'key': key,
                'event_type': 'press' if random.random() < 0.5 else 'release',
                'timestamp': time.time()
            })
            
        # Keep only the latest 200 key events
        self.key_events = self.key_events[-200:]
      
        avg_hold_duration = random.uniform(80, 150)  # milliseconds
        
        # Calculate rollover capability (simultaneous keys pressed)
        current_rollover = min(10, random.randint(1, self.keypresses_per_second + 2))
        
        base_temp = 27.0  # Base temperature in °C
        activity_factor = (self.keypresses_per_second / 8) * 7  # Scale activity to temperature increase
        device_temperature = base_temp + activity_factor
        
        # Increase temperature during attacks
        if self.under_attack:
            device_temperature += 3.0  # Attack causes additional heat
        
        return {
            'device_id': self.device_id,
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'keypresses_per_second': self.keypresses_per_second,
                'keys_pressed_count': len(self.key_events),
                'avg_hold_duration_ms': round(avg_hold_duration, 1),
                'polling_rate': self.polling_rate,
                'current_rollover': current_rollover,
                'max_rollover': 10,  
                'device_temperature': round(device_temperature, 1)
            },
            'status': {
                'under_attack': self.under_attack,
                'attack_duration': self._get_attack_duration() if self.under_attack else 0,
                'battery_level': 100,  # Usually wired, but could be wireless
                'connection_quality': random.randint(80, 100) if not self.under_attack else random.randint(40, 70),
                'illumination': {
                    'mode': self.illumination_mode,
                    'color': self.illumination_color,
                    'brightness': self.illumination_brightness
                }
            }
        }
        
    def _get_attack_duration(self):
        
        if self.attack_start_time:
            return int(time.time() - self.attack_start_time)
        return 0
    
    def _publish_data(self, data):
   
        if not self.connected:
            return False
            
        try:
            payload = json.dumps(data)
            result = self.client.publish(self.data_topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing data: {e}")
            return False
    
    def _publish_status(self, status):
       
        if not self.connected and status != "offline":
            return False
            
        try:
            payload = json.dumps({
                'device_id': self.device_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            })
            result = self.client.publish(self.status_topic, payload, qos=1, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing status: {e}")
            return False
    
    def _publish_security_alert(self, alert_type, details):
       
        if not self.connected:
            return False
            
        try:
            payload = json.dumps({
                'device_id': self.device_id,
                'alert_type': alert_type,
                'timestamp': datetime.now().isoformat(),
                'details': details
            })
            result = self.client.publish(self.security_topic, payload, qos=2)  # Use QoS 2 for security alerts
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing security alert: {e}")
            return False
    
    def _publish_keymap(self):
      
        if not self.connected:
            return False
            
        try:
           
            total_presses = sum(self.key_usage.values()) or 1  
          
            keymap_data = {}
            for key, count in self.key_usage.items():
                percentage = (count / total_presses) * 100
                keymap_data[key] = round(percentage, 1)
            
            payload = json.dumps({
                'device_id': self.device_id,
                'timestamp': datetime.now().isoformat(),
                'keymap': keymap_data,
                'total_keypresses': sum(self.key_usage.values())
            })
            result = self.client.publish(self.keymap_topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"Error publishing keymap data: {e}")
            return False
    
    def _keymap_publisher(self):
        
        while self.running:
            try:
                # Publish every 5 seconds
                time.sleep(5)
                self._publish_keymap()
            except Exception as e:
                print(f"Error in keymap publisher: {e}")
    
    def _simulate_attack(self, duration=5):
        
        if not self.under_attack:
            self.under_attack = True
            self.attack_start_time = time.time()
            attack_intensity = random.randint(70, 100)
            print(f" ALERT: Keyboard is under attack! Detected {attack_intensity} suspicious events in 1 second")
            
            # Publish attack alert
            self._publish_security_alert('attack_detected', {
                'attack_type': 'key_injection',
                'intensity': attack_intensity,
                'threshold': self.event_threshold
            })
          
            def resolve_attack():
                time.sleep(duration)
                if self.under_attack:
                    attack_duration = self._get_attack_duration()
                    self.under_attack = False
                    self.attack_start_time = None
                    print(f"✓ Attack stopped. Duration: {attack_duration} seconds")
              
                    self._publish_security_alert('attack_resolved', {
                        'attack_type': 'key_injection',
                        'duration': attack_duration
                    })
                    
                    self.attack_cooldown = True
                    self.attack_cooldown_until = time.time() + 10 
              
            attack_thread = threading.Thread(target=resolve_attack)
            attack_thread.daemon = True
            attack_thread.start()
    
    def _monitor_network(self):
        
        while self.running:
            try:
                self.suspicious_events = 0
                
                if self.attack_cooldown and time.time() > self.attack_cooldown_until:
                    self.attack_cooldown = False
           
                if not self.under_attack and not self.attack_cooldown and random.random() < 0.05:
                    self._simulate_attack(random.randint(5, 10)) 
              
                time.sleep(1)
                
            except Exception as e:
                print(f"Error monitoring keyboard: {e}")
                time.sleep(1)
    
    def _run(self):
        """Main execution loop"""
        while self.running:
            #
            data = self._generate_performance_data()
            self._publish_data(data)
         
            time.sleep(self.send_interval)


def main():
    parser = argparse.ArgumentParser(description='Simulated IoT Gaming Devices with MQTT')
    parser.add_argument('--type', default='mouse', choices=['mouse', 'keyboard', 'both'], help='Device type to simulate')
    parser.add_argument('--id', default=None, help='Device ID (optional, defaults to type-specific ID)')
    parser.add_argument('--broker', default='localhost', help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--interval', type=float, default=1.0, help='Data sending interval in seconds')
    args = parser.parse_args()
    
    devices = []
    
    try:
        if args.type == 'mouse' or args.type == 'both':
            mouse_id = args.id if args.id and args.type == 'mouse' else 'mouse-001'
            mouse = SimulatedGamingMouse(
                device_id=mouse_id,
                mqtt_broker=args.broker,
                mqtt_port=args.port,
                mqtt_topic_prefix="iot/gaming/mouse",
                send_interval=args.interval
            )
            if mouse.start():
                devices.append(mouse)
            else:
                print("Failed to start mouse simulation")
                
        if args.type == 'keyboard' or args.type == 'both':
            keyboard_id = args.id if args.id and args.type == 'keyboard' else 'keyboard-001'
            keyboard = SimulatedGamingKeyboard(
                device_id=keyboard_id,
                mqtt_broker=args.broker,
                mqtt_port=args.port,
                mqtt_topic_prefix="iot/gaming/keyboard",
                send_interval=args.interval
            )
            if keyboard.start():
                devices.append(keyboard)
            else:
                print("Failed to start keyboard simulation")
        
        if not devices:
            print("No devices were started. Exiting.")
            return 1
            

        print(f"Running {len(devices)} simulated IoT gaming device(s)...")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("Stopping simulation...")
                for device in devices:
                    device.stop()
                break
                
    except Exception as e:
        print(f"Error: {e}")
        for device in devices:
            device.stop()
        return 1
        
    return 0

if __name__ == "__main__":
    main()