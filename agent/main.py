import os
import sys
import time
import logging
import argparse
from input_monitor import InputMonitor
from secure_sender import SecureSender
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE
)
logger = logging.getLogger('main')

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Secure Esports Equipment Performance Tracker Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  main.py start        - Start monitoring keyboard and mouse inputs
  main.py test         - Test connection to server
  main.py status       - Check agent status
  main.py info         - Display configuration information
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    mqtt_test_parser = subparsers.add_parser('mqtt-test', help='Test MQTT broker connection')
    
    start_parser = subparsers.add_parser('start', help='Start monitoring inputs')
    start_parser.add_argument('--offline', action='store_true', help='Start in offline mode')
    
    test_parser = subparsers.add_parser('test', help='Test connection to server')
    
    status_parser = subparsers.add_parser('status', help='Check agent status')
    
    info_parser = subparsers.add_parser('info', help='Display configuration information')
    
    return parser.parse_args()

def start_agent(offline=False):
    print("Starting Secure Esports Equipment Performance Tracker Agent...")
    print(f"Device: {config.DEVICE_NAME} ({config.DEVICE_TYPE})")
    
    try:
        monitor = InputMonitor()
        if offline:
            monitor.offline_mode = True
            print("Starting in offline mode (data will be stored locally)")
        monitor.start()
    except KeyboardInterrupt:
        print("\nAgent stopped by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"Error: {e}")
        return 1
    return 0

def test_connection():

    print(f"Testing connection to server: {config.SERVER_URL}")
    
    try:
        sender = SecureSender(config.SERVER_URL, config.CLIENT_ID, config.CLIENT_SECRET)
        result = sender.test_connection()
        
        if result:
            print("\n Connection test successful!")
            print(" Authentication successful!")
            return 0
        else:
            print("\n Connection test failed!")
            return 1
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        print(f"\n Error: {e}")
        return 1

def check_status():
    
    print("Secure Esports ")
    print("--------------------------------------------------------")
    
    try:
        sender = SecureSender(config.SERVER_URL, config.CLIENT_ID, config.CLIENT_SECRET)
        server_reachable = sender.test_connection()
    except:
        server_reachable = False
    
    local_data_dir = os.path.join(config.DATA_DIR, 'local_data')
    has_local_data = os.path.exists(local_data_dir) and len(os.listdir(local_data_dir)) > 0
    
    print(f"Server connection:  {'Connected' if server_reachable else ' Not connected'}")
    print(f"Local data storage: {'Yes' if has_local_data else ' No'}")
    print(f"Data directory:     {config.DATA_DIR}")
    print(f"Log file:           {config.LOG_FILE}")
    
    return 0

def show_info():
    print("Secure Esports Equipment Performance Tracker Agent Information")
    print("-----------------------------------------------------------")
    print(f"Device Name:        {config.DEVICE_NAME}")
    print(f"Device Type:        {config.DEVICE_TYPE}")
    print(f"Client ID:          {config.CLIENT_ID}")
    print(f"Server URL:         {config.SERVER_URL}")
    print(f"Privacy Mode:       {'Enabled' if config.PRIVACY_MODE else 'Disabled'}")
    print(f"Data Directory:     {config.DATA_DIR}")
    print(f"Log File:           {config.LOG_FILE}")
    
    return 0

def test_mqtt_connection_cmd():
    ""
    print(f"Testing MQTT connection to {config.MQTT_BROKER}:{config.MQTT_PORT}...")
    
    result = test_mqtt_connection(config.MQTT_BROKER, config.MQTT_PORT)
    
    if result['success']:
        print(f"\n MQTT connection test successful!")
        print(f" Connected in {result['connection_time']} seconds")
        return 0
    else:
        print(f"\n MQTT connection test failed!")
        print(f" Error: {result['error']}")
        return 1
    
def main():
    """Main entry point"""
    args = parse_arguments()
    
    if not args.command:
        # If no command provided, show help
        print("Please specify a command. Use --help for more information.")
        return 1
    
    # Execute the requested command
    if args.command == 'start':
        return start_agent(args.offline)
    elif args.command == 'test':
        return test_connection()
    elif args.command == 'mqtt-test':
        return test_mqtt_connection_cmd()
    elif args.command == 'status':
        return check_status()
    elif args.command == 'info':
        return show_info()
    else:
        print(f"Unknown command: {args.command}")
        return 1

if __name__ == "__main__":
    sys.exit(main())