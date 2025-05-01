def test_mqtt_connection(mqtt_broker="localhost", mqtt_port=1883, timeout=5):

    import time
    import paho.mqtt.client as mqtt
    import threading
    import logging
    
    logger = logging.getLogger('mqtt_connection')
 
    result = {
        'success': False,
        'connection_time': None,
        'error': None,
        'broker_info': f"{mqtt_broker}:{mqtt_port}"
    }

    connected = False
    connection_event = threading.Event()
  
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
   
    import uuid
    client_id = f"mqtt-test-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id)
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
      
        start_time = time.time()
    
        client.connect_async(mqtt_broker, mqtt_port, 60)
        
        client.loop_start()
        
        if connection_event.wait(timeout):

            connection_time = time.time() - start_time
            result['connection_time'] = round(connection_time, 3)
            result['success'] = connected
        else:
        
            result['error'] = f"Connection timeout after {timeout} seconds"
            logger.error(f"MQTT connection timeout after {timeout} seconds")
    
    except Exception as e:

        error_msg = str(e)
        result['error'] = error_msg
        logger.error(f"Error connecting to MQTT broker: {error_msg}")
    
    finally:
        client.loop_stop()
        if connected:
            client.disconnect()
    
    return result