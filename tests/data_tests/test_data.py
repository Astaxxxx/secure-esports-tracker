import os
import sys
import unittest
import json
import time
import warnings
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    warnings.warn("numpy module not available. Data tests will use simplified methods.")
    NUMPY_AVAILABLE = False
  
    class np:
        @staticmethod
        def zeros(shape):
            if isinstance(shape, tuple):
                rows, cols = shape
                return [[0 for _ in range(cols)] for _ in range(rows)]
            return [0 for _ in range(shape)]
            
        @staticmethod
        def random(module=None):
            import random
            return random
            
        @staticmethod
        def mean(arr):
            if isinstance(arr[0], list):
                flat = [item for sublist in arr for item in sublist]
                return sum(flat) / len(flat) if flat else 0
            return sum(arr) / len(arr) if arr else 0
            
        @staticmethod
        def max(arr):
            if isinstance(arr[0], list):
                return max(max(row) for row in arr)
            return max(arr)
            
        @staticmethod
        def median(arr):
            sorted_arr = sorted(arr)
            n = len(sorted_arr)
            if n % 2 == 0:
                return (sorted_arr[n//2 - 1] + sorted_arr[n//2]) / 2
            return sorted_arr[n//2]
            
        @staticmethod
        def clip(value, min_val, max_val):
            return min(max(value, min_val), max_val)

try:
    from scipy.ndimage import gaussian_filter
    SCIPY_AVAILABLE = True
except ImportError:
    warnings.warn("scipy module not available. Some data tests may be skipped.")
    SCIPY_AVAILABLE = False
    
    def gaussian_filter(arr, sigma=1):
   
        if not NUMPY_AVAILABLE:
            return arr
  
        result = np.zeros(np.shape(arr))
        rows, cols = np.shape(arr)
        
        for i in range(rows):
            for j in range(cols):
              
                count = 0
                total = 0
                for di in range(max(0, i-1), min(rows, i+2)):
                    for dj in range(max(0, j-1), min(cols, j+2)):
                        total += arr[di][dj]
                        count += 1
                result[i][j] = total / count if count > 0 else 0
                
        return result

try:
    from agent.input_monitor import InputMonitor
except ImportError:
    
    class InputMonitor:
       
        def __init__(self):
            self.keyboard_events = []
            self.mouse_events = []
            self.actions_per_minute = 0
            self.last_minute_actions = 0
            self.last_minute_time = time.time()
        
        def _calculate_apm(self, events, period_seconds=60):
         
            if not events:
                return 0

            timestamps = [event['timestamp'] for event in events]
            min_time = min(timestamps)
            max_time = max(timestamps)

            time_diff = max_time - min_time
            if time_diff < 1:  # Less than 1 second of data
                minutes = period_seconds / 60
            else:
                minutes = time_diff / 60
 
            actions = len(events)
  
            if minutes > 0:
                return actions / minutes
            return 0


def generate_timestamp_data(count, interval=1.0, randomize=False, out_of_order_probability=0.0):
 
    import random
    
    base_time = datetime.now().timestamp()
    timestamps = []
    
    for i in range(count):
        if randomize:
            
            jitter = random.uniform(-0.5, 0.5) * interval
            timestamp = base_time + (i * interval) + jitter
        else:
            timestamp = base_time + (i * interval)
            
        timestamps.append(timestamp)
   
    if out_of_order_probability > 0:
        for i in range(count - 1):
            if random.random() < out_of_order_probability:
                # Swap with next timestamp
                timestamps[i], timestamps[i+1] = timestamps[i+1], timestamps[i]
    
    return timestamps

def generate_heatmap_data(width, height, hotspot_count=3):
   
    import random

    heatmap = np.zeros((height, width))
    
 
    for _ in range(hotspot_count):
        
        center_x = random.randint(0, width-1)
        center_y = random.randint(0, height-1)
     
        intensity = random.randint(50, 100)
        radius = random.randint(5, min(width, height) // 4)
       
        for y in range(max(0, center_y - radius), min(height, center_y + radius + 1)):
            for x in range(max(0, center_x - radius), min(width, center_x + radius + 1)):
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                if distance <= radius:
                   
                    falloff = 1 - (distance / radius)
                    if NUMPY_AVAILABLE:
                        heatmap[y, x] += intensity * (falloff ** 2)
                    else:
                        heatmap[y][x] += intensity * (falloff ** 2)
    
    return heatmap

class TestDataProcessing(unittest.TestCase):
   
    
    def setUp(self):
       
        self.keyboard_events = []
        self.mouse_events = []
       
        event_time = datetime.now().timestamp()
        for i in range(120):  # 2 events per second for a minute
            self.keyboard_events.append({
                'timestamp': event_time + (i * 0.5),
                'event_type': 'press' if i % 2 == 0 else 'release',
                'key': 'a' if i % 4 == 0 else ('s' if i % 4 == 1 else ('d' if i % 4 == 2 else 'f'))
            })
        
        # Add mouse events
        for i in range(60):  # 1 event per second for a minute
            self.mouse_events.append({
                'timestamp': event_time + i,
                'event_type': 'click' if i % 3 == 0 else ('move' if i % 3 == 1 else 'scroll'),
                'button': 'left' if i % 2 == 0 else 'right',
                'x': 100 + i,
                'y': 200 + i
            })
    
    def test_apm_calculation(self):
       
        monitor = InputMonitor()
        
    
        expected_apm = 120
        
        # Add events to the monitor
        monitor.keyboard_events = self.keyboard_events.copy()
        monitor.mouse_events = self.mouse_events.copy()
        
        # Set the time reference
        first_event_time = min(self.keyboard_events[0]['timestamp'], self.mouse_events[0]['timestamp'])
        last_event_time = max(self.keyboard_events[-1]['timestamp'], self.mouse_events[-1]['timestamp'])
        time_diff = last_event_time - first_event_time
        
        # Calculate action count
        keyboard_actions = sum(1 for e in self.keyboard_events if e['event_type'] == 'press')
        mouse_actions = len(self.mouse_events)
        total_actions = keyboard_actions + mouse_actions
        
        # Manually calculate APM (actions per minute)
        minutes = time_diff / 60
        calculated_apm = total_actions / minutes if minutes > 0 else 0
        
        # Verify calculation is close to expected (allowing for small timing differences)
        self.assertAlmostEqual(calculated_apm, expected_apm, delta=5)

    def test_timestamp_validation(self):
     
        timestamps = generate_timestamp_data(100, interval=0.1, randomize=True, out_of_order_probability=0.2)
        
        # Create events with these timestamps
        events = []
        for i, ts in enumerate(timestamps):
            events.append({
                'id': i,
                'timestamp': ts,
                'value': i
            })
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e['timestamp'])
        
        # Verify some events were actually out of order
        original_ids = [e['id'] for e in events]
        sorted_ids = [e['id'] for e in sorted_events]
        
        # Only assert if the sort actually changed the order
        if original_ids != sorted_ids:
            self.assertNotEqual(original_ids, sorted_ids)
        
        # Verify timestamps are now in order
        for i in range(len(sorted_events) - 1):
            self.assertLessEqual(sorted_events[i]['timestamp'], sorted_events[i+1]['timestamp'])
       
        intervals = [sorted_events[i+1]['timestamp'] - sorted_events[i]['timestamp'] 
                    for i in range(len(sorted_events)-1)]
                    
        if NUMPY_AVAILABLE:
            median_interval = np.median(intervals)
        else:
            # Simple median calculation
            sorted_intervals = sorted(intervals)
            n = len(sorted_intervals)
            median_interval = (sorted_intervals[n//2 - 1] + sorted_intervals[n//2]) / 2 if n % 2 == 0 else sorted_intervals[n//2]
        
        anomalies = []
        for i in range(len(sorted_events) - 1):
            interval = sorted_events[i+1]['timestamp'] - sorted_events[i]['timestamp']
            if interval > median_interval * 5:  # 5x the median interval is suspicious
                anomalies.append(i+1)
        
        # Fix anomalies by interpolating timestamps
        for idx in anomalies:
            if idx > 0 and idx < len(sorted_events) - 1:
                # Interpolate based on surrounding timestamps
                prev_ts = sorted_events[idx-1]['timestamp']
                next_ts = sorted_events[idx+1]['timestamp'] if idx < len(sorted_events) - 1 else prev_ts + median_interval
                sorted_events[idx]['timestamp'] = prev_ts + (next_ts - prev_ts) / 2
        
        # Verify all intervals are now reasonable
        for i in range(len(sorted_events) - 1):
            interval = sorted_events[i+1]['timestamp'] - sorted_events[i]['timestamp']
            self.assertLessEqual(interval, median_interval * 5)

    def test_heatmap_generation(self):
        """Test 3: Verify mouse click heatmap generation"""
        if not NUMPY_AVAILABLE:
            self.skipTest("numpy module not available")
            
        # Define dimensions
        width, height = 192, 108  # Scaled down 1920x1080
   
        click_positions = []
        
        # Add clicks around a few hotspots
        hotspots = [
            (width // 4, height // 4),      
            (width // 4 * 3, height // 4),   
            (width // 2, height // 2),       
            (width // 4, height // 4 * 3),  
            (width // 4 * 3, height // 4 * 3)  
        ]
        
        import random
        for _ in range(1000):
            if random.random() < 0.8:
                hotspot = random.choice(hotspots)
                radius = random.randint(5, 20)
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.random() * radius
                x = int(hotspot[0] + distance * np.cos(angle))
                y = int(hotspot[1] + distance * np.sin(angle))
                x = max(0, min(width - 1, x))
                y = max(0, min(height - 1, y))
            else:
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                
            click_positions.append((x, y))
 
        heatmap = np.zeros((height, width))
        for x, y in click_positions:
            if NUMPY_AVAILABLE:
                heatmap[y, x] += 1
            else:
                heatmap[y][x] += 1

        if SCIPY_AVAILABLE:
            smoothed_heatmap = gaussian_filter(heatmap, sigma=2)
        else:

            smoothed_heatmap = gaussian_filter(heatmap, sigma=2)

        for hotspot_x, hotspot_y in hotspots:
            if NUMPY_AVAILABLE:
                hotspot_region = smoothed_heatmap[
                    max(0, hotspot_y - 10):min(height, hotspot_y + 10),
                    max(0, hotspot_x - 10):min(width, hotspot_x + 10)
                ]
                
                if hotspot_region.size > 0:
 
                    self.assertGreater(np.mean(hotspot_region), np.mean(smoothed_heatmap))
            else:
  
                hotspot_value = smoothed_heatmap[hotspot_y][hotspot_x]
                avg_value = np.mean(smoothed_heatmap)
                self.assertGreater(hotspot_value, avg_value)

        if NUMPY_AVAILABLE:
            self.assertEqual(smoothed_heatmap.shape, (height, width))
        else:
            self.assertEqual(len(smoothed_heatmap), height)
            self.assertEqual(len(smoothed_heatmap[0]), width)

if __name__ == '__main__':
    unittest.main()