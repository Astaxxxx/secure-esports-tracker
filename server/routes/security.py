def register_security_routes(app):

    @app.route('/api/security/alert', methods=['POST', 'OPTIONS'])
    def receive_security_alert():

        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            from utils.sanitize import sanitize_input
            
            data = sanitize_input(app.request.json)
            device_id = data.get('device_id')
            event_type = data.get('event_type')
            details = data.get('details')
            
            if not device_id or not event_type:
                return app.jsonify({'error': 'Missing required fields'}), 400

            severity = 'critical' if event_type == 'attack_detected' else 'warning'

            app.logger.info(f"SECURITY EVENT: iot_{event_type} - {details}")
  
            app.log_security_event(f'iot_{event_type}', details, severity=severity)
  
            if not hasattr(app, 'device_alerts'):
                app.device_alerts = {}
                
            if device_id not in app.device_alerts:
                app.device_alerts[device_id] = []
                
            from datetime import datetime
            
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'details': details,
                'severity': severity
            }
            
            app.device_alerts[device_id].append(alert_data)
            
            app.device_alerts[device_id] = app.device_alerts[device_id][-100:]
            
            return app.jsonify({'status': 'success'})
            
        except Exception as e:
            app.logger.error(f"Error processing security alert: {e}")
            return app.jsonify({'error': 'Internal server error', 'details': str(e)}), 500
        
    @app.route('/api/security/device_alerts/<device_id>', methods=['GET', 'OPTIONS'])
    @app.route_decorator.require_auth
    def get_device_security_alerts(device_id):

        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            if not hasattr(app, 'device_alerts') or device_id not in app.device_alerts:
                return app.jsonify({'alerts': []})
                
            return app.jsonify({'alerts': app.device_alerts[device_id]})
            
        except Exception as e:
            app.logger.error(f"Error retrieving device alerts: {e}")
            return app.jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    @app.route('/api/metrics/iot_data', methods=['POST', 'OPTIONS'])
    def receive_iot_data():

        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            from utils.sanitize import sanitize_input
            
            data = sanitize_input(app.request.json)
            device_id = data.get('device_id')
            
            if not device_id:
                return app.jsonify({'error': 'Missing device ID'}), 400

            if not hasattr(app, 'iot_data'):
                app.iot_data = {}
                
            if device_id not in app.iot_data:
                app.iot_data[device_id] = []
                
            app.iot_data[device_id].append(data)
            app.iot_data[device_id] = app.iot_data[device_id][-100:]
            
            return app.jsonify({'status': 'success'})
            
        except Exception as e:
            app.logger.error(f"Error processing IoT data: {e}")
            return app.jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    @app.route('/api/metrics/iot_data/<device_id>', methods=['GET', 'OPTIONS'])
    @app.route_decorator.require_auth
    def get_iot_data(device_id):

        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            if not hasattr(app, 'iot_data') or device_id not in app.iot_data:
                return app.jsonify({'data': []})
                
            return app.jsonify({'data': app.iot_data[device_id]})
            
        except Exception as e:
            app.logger.error(f"Error retrieving IoT data: {e}")
            return app.jsonify({'error': 'Internal server error', 'details': str(e)}), 500

    return [
        receive_security_alert,
        get_device_security_alerts,
        receive_iot_data,
        get_iot_data
    ]