def test_mqtt_connection(mqtt_broker="localhost", mqtt_port=1883, timeout=5):
    """
    Test MQTT connection to broker within the application.
    
    Args:
        mqtt_broker (str): MQTT broker hostname or IP
        mqtt_port (int): MQTT broker port
        timeout (int): Connection timeout in seconds
        
    Returns:
        dict: Results containing success status, connection time, and any error message
    """
    import time
    import paho.mqtt.client as mqtt
    import threading
    import logging
    
    logger = logging.getLogger('mqtt_connection')
    
    # Results dictionary
    result = {
        'success': False,
        'connection_time': None,
        'error': None,
        'broker_info': f"{mqtt_broker}:{mqtt_port}"
    }
    
    # Connection flag and event
    connected = False
    connection_event = threading.Event()
    
    # Define callbacks
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            logger.info(f"Successfully connected to MQTT broker at {mqtt_broker}:{mqtt_port}")
            connection_event.set()
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            result['error'] = error_msg
            connection_event.set()
    
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
    
    # Create client with unique ID
    import uuid
    client_id = f"mqtt-test-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        # Record start time
        start_time = time.time()
        
        # Connect to broker with timeout
        client.connect_async(mqtt_broker, mqtt_port, 60)
        
        # Start network loop in background thread
        client.loop_start()
        
        # Wait for connection or timeout
        if connection_event.wait(timeout):
            # Calculate connection time
            connection_time = time.time() - start_time
            result['connection_time'] = round(connection_time, 3)
            result['success'] = connected
        else:
            # Connection timeout
            result['error'] = f"Connection timeout after {timeout} seconds"
            logger.error(f"MQTT connection timeout after {timeout} seconds")
    
    except Exception as e:
        # Handle connection exceptions
        error_msg = str(e)
        result['error'] = error_msg
        logger.error(f"Error connecting to MQTT broker: {error_msg}")
    
    finally:
        # Clean up
        client.loop_stop()
        if connected:
            client.disconnect()
    
    return result