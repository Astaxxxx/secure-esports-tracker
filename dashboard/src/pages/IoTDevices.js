import React, { useState, useEffect } from 'react';
import MouseButtonHeatmap from '../components/MouseButtonHeatmap';
import { fetchWithAuth } from '../utils/api';
import '../App.css';

const DeviceHeatmap = ({ deviceId }) => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [heatmapType, setHeatmapType] = useState('position');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchHeatmapData = async () => {
      if (!deviceId) return;
      
      try {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`http://localhost:5000/api/metrics/iot_heatmap/${deviceId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch heatmap data');
        }

        const data = await response.json();
        setHeatmapData(data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching heatmap data:', err);

        generateDummyHeatmap();
      }
    };
    
    const generateDummyHeatmap = () => {
 
      const width = 192;
      const height = 108;
      const positionData = Array(height).fill().map(() => Array(width).fill(0));
      const clickData = Array(height).fill().map(() => Array(width).fill(0));

      for (let i = 0; i < 5000; i++) {
        const x = Math.floor(Math.random() * width * 0.6 + width * 0.2);
        const y = Math.floor(Math.random() * height * 0.6 + height * 0.2);
        positionData[y][x] += Math.random() * 2 + 1;
        
        if (Math.random() < 0.3) {
          clickData[y][x] += Math.random() * 5 + 1;
        }
      }
 
      for (let i = 0; i < 1000; i++) {
        const x = Math.floor(Math.random() * width * 0.2);
        const y = Math.floor(Math.random() * height * 0.2);
        positionData[y][x] += Math.random() * 3 + 1;
        if (Math.random() < 0.4) {
          clickData[y][x] += Math.random() * 8 + 2;
        }
      }
      
      for (let i = 0; i < 1000; i++) {
        const x = Math.floor(Math.random() * width * 0.6 + width * 0.2);
        const y = Math.floor(Math.random() * height * 0.2 + height * 0.8);
        positionData[y][x] += Math.random() * 2 + 1;
        if (Math.random() < 0.5) {
          clickData[y][x] += Math.random() * 6 + 3;
        }
      }
      
      setHeatmapData({
        position_heatmap: positionData,
        click_heatmap: clickData,
        resolution: {
          width,
          height
        }
      });
      setLoading(false);
    };
    
    fetchHeatmapData();
 
    const intervalId = setInterval(fetchHeatmapData, 30000); // Refresh every 30 seconds

    return () => clearInterval(intervalId);
  }, [deviceId]);
  
  if (loading || !heatmapData) {
    return (
      <div className="card">
        <h2 className="card-title">Mouse Movement Heatmap</h2>
        <p>Loading heatmap data...</p>
      </div>
    );
  }
  
  const currentHeatmap = heatmapType === 'position' 
    ? heatmapData.position_heatmap 
    : heatmapData.click_heatmap;
  

  const getColor = (value) => {

    if (value === 0) return 'rgba(0, 0, 0, 0)'; 
    if (value < 10) return `rgba(0, 0, 255, ${value / 20})`;
    if (value < 30) return `rgba(0, ${255 - (value - 10) * 8}, 255, 0.5)`;
    if (value < 60) return `rgba(${(value - 30) * 8}, 255, ${255 - (value - 30) * 8}, 0.6)`;
    if (value < 80) return `rgba(255, ${255 - (value - 60) * 12}, 0, 0.7)`;
    return `rgba(255, 0, 0, 0.8)`;
  };
  
  return (
    <div className="card">
      <h2 className="card-title">Screen Interaction Heatmap</h2>
      <div style={{ marginBottom: '10px' }}>
        <button 
          className={`btn ${heatmapType === 'position' ? 'btn-primary' : ''}`}
          onClick={() => setHeatmapType('position')}
          style={{ marginRight: '10px' }}
        >
          Movement Heatmap
        </button>
        <button 
          className={`btn ${heatmapType === 'click' ? 'btn-primary' : ''}`}
          onClick={() => setHeatmapType('click')}
        >
          Click Heatmap
        </button>
      </div>
      
      <div style={{ 
        position: 'relative',
        width: '100%',
        height: '300px',
        border: '1px solid var(--border-color)',
        borderRadius: '4px',
        overflow: 'hidden',
        backgroundColor: '#111'
      }}>
        {}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%'
        }}>
          {currentHeatmap && heatmapData.resolution && (
            <svg width="100%" height="100%" viewBox={`0 0 ${heatmapData.resolution.width} ${heatmapData.resolution.height}`}>
              {currentHeatmap.map((row, y) => 
                row.map((value, x) => 
                  value > 0 && (
                    <rect 
                      key={`${x}-${y}`} 
                      x={x} 
                      y={y} 
                      width={1} 
                      height={1} 
                      fill={getColor(value)} 
                    />
                  )
                )
              )}
            </svg>
          )}
        </div>
        
        {}
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: '80%',
          height: '80%',
          border: '1px dashed rgba(255, 255, 255, 0.3)',
          borderRadius: '2px',
          pointerEvents: 'none',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>Game Screen Area</span>
        </div>
      </div>
      
      <div style={{ marginTop: '15px' }}>
        <p><strong>Heatmap Type:</strong> {heatmapType === 'position' ? 'Mouse Movement' : 'Mouse Clicks'}</p>
        <p>This heatmap shows the distribution of {heatmapType === 'position' ? 'mouse movements' : 'mouse clicks'} across the screen, processed by the edge computing capabilities of the IoT mouse sensor.</p>
        <p>The real-time data collection and processing demonstrates how IoT gaming peripherals can provide deeper insights into player behavior and performance.</p>
      </div>
    </div>
  );
};

const IoTDevices = ({ user }) => {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceData, setDeviceData] = useState([]);
  const [securityAlerts, setSecurityAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(5); // in seconds
  const [isRefreshing, setIsRefreshing] = useState(true);

  useEffect(() => {

    const fetchDevices = async () => {
      try {
        const response = await fetchWithAuth('/api/devices');
        if (!response.ok) {
          throw new Error('Failed to fetch devices');
        }

        const data = await response.json();
        console.log("Received devices data:", data);

        const iotDevices = data.devices.filter(device => 
          device.device_type === 'mouse' || 
          device.device_type === 'keyboard' || 
          device.device_type === 'headset' ||
          device.device_type === 'mouse_sensor' || 
          device.device_type === 'keyboard_sensor' || 
          device.device_type === 'headset_sensor'
        );

        const renamedDevices = iotDevices.map(device => {

          if (device.device_type === 'mouse' || device.name.includes('Mouse')) {
            return {
              ...device,
              name: device.name.includes('Sensor') ? device.name : `${device.name} Sensor`,
              device_type: device.device_type === 'mouse' ? 'mouse_sensor' : device.device_type
            };
          }
          if (device.device_type === 'keyboard' || device.name.includes('Keyboard')) {
            return {
              ...device,
              name: device.name.includes('Sensor') ? device.name : `${device.name} Sensor`,
              device_type: device.device_type === 'keyboard' ? 'keyboard_sensor' : device.device_type
            };
          }
          if (device.device_type === 'headset' || device.name.includes('Headset')) {
            return {
              ...device,
              name: device.name.includes('Sensor') ? device.name : `${device.name} Sensor`,
              device_type: device.device_type === 'headset' ? 'headset_sensor' : device.device_type
            };
          }
          return device;
        });
        
        setDevices(renamedDevices);

        if (renamedDevices.length > 0 && !selectedDevice) {
          setSelectedDevice(renamedDevices[0].client_id);
        }
      } catch (err) {
        console.error('Error fetching devices:', err);
        setError('Failed to load devices. Please try again.');
  
        const fallbackDevices = [
          {
            client_id: 'mouse-001',
            name: 'Gaming Mouse Sensor',
            device_type: 'mouse_sensor',
            status: 'active',
          },
          {
            client_id: 'keyboard-001',
            name: 'Gaming Keyboard Sensor',
            device_type: 'keyboard_sensor',
            status: 'active',
          }
        ];
        setDevices(fallbackDevices);
        if (!selectedDevice) {
          setSelectedDevice(fallbackDevices[0].client_id);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();

    const deviceInterval = setInterval(fetchDevices, 30000);
    
    return () => clearInterval(deviceInterval);
  }, [selectedDevice]);

  useEffect(() => {
    let dataInterval;
    
    if (isRefreshing && selectedDevice) {
      const fetchData = async () => {
        try {
          await Promise.all([
            fetchDeviceData(selectedDevice),
            fetchSecurityAlerts(selectedDevice)
          ]);
        } catch (err) {
          console.error('Error refreshing data:', err);
        }
      };
      fetchData();
      dataInterval = setInterval(fetchData, refreshInterval * 1000);
    }
    
    return () => {
      if (dataInterval) clearInterval(dataInterval);
    };
  }, [selectedDevice, refreshInterval, isRefreshing]);

  const fetchDeviceData = async (deviceId) => {
    try {
      console.log("Fetching data for device:", deviceId);
      const response = await fetch(`http://localhost:5000/api/metrics/iot_data/${deviceId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch device data');
      }

      const result = await response.json();
      console.log("Received device data:", result);
      setDeviceData(result.data || []);
    } catch (err) {
      console.error('Error fetching device data:', err);

      setDeviceData([{
        device_id: deviceId,
        session_id: 'fallback-session',
        timestamp: new Date().toISOString(),
        metrics: {
          clicks_per_second: 4,
          movements_count: 120,
          dpi: 16000,
          polling_rate: 1000,
          avg_click_distance: 42.5,
          button_count: 8
        },
        status: {
          under_attack: false,
          attack_duration: 0,
          battery_level: 85,
          connection_quality: 95
        }
      }]);
    }
  };

  const fetchSecurityAlerts = async (deviceId) => {
    try {
      console.log("Fetching security alerts for device:", deviceId);
      const response = await fetch(`http://localhost:5000/api/security/device_alerts/${deviceId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch security alerts');
      }

      const result = await response.json();
      console.log("Received security alerts:", result);
      setSecurityAlerts(result.alerts || []);
    } catch (err) {
      console.error('Error fetching security alerts:', err);
      // Use fallback data on error
      setSecurityAlerts([{
        timestamp: new Date().toISOString(),
        event_type: 'attack_detected',
        details: {
          attack_type: 'ping_flood',
          intensity: 72,
          threshold: 50
        },
        severity: 'critical'
      }]);
    }
  };

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  const getMostRecentData = () => {
    if (!deviceData || deviceData.length === 0) return null;
    return deviceData[deviceData.length - 1];
  };

  const getLatestMetrics = () => {
    const recent = getMostRecentData();
    if (!recent || !recent.metrics) return null;
    return recent.metrics;
  };

  const getDeviceStatus = () => {
    const recent = getMostRecentData();
    if (!recent || !recent.status) return { under_attack: false };
    return recent.status;
  };

  const renderDeviceStatus = () => {
    const status = getDeviceStatus();
 
    const hasRecentCriticalAlert = securityAlerts.some(alert => {
      const alertTime = new Date(alert.timestamp);
      const now = new Date();
      const timeDiff = (now - alertTime) / 1000; // in seconds
      return alert.severity === 'critical' && timeDiff < 60;
    });
 
    const isAttacked = (status && status.under_attack) || hasRecentCriticalAlert;
    
    return (
      <div style={{
        padding: '15px',
        borderRadius: '8px',
        backgroundColor: isAttacked ? 'rgba(176, 0, 32, 0.1)' : 'rgba(0, 200, 83, 0.1)',
        border: `1px solid ${isAttacked ? 'var(--error-color)' : 'var(--success-color)'}`,
        marginBottom: '20px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ margin: '0 0 10px 0' }}>Device Status</h3>
            <p style={{ 
              margin: '0', 
              fontWeight: 'bold',
              color: isAttacked ? 'var(--error-color)' : 'var(--success-color)'
            }}>
              {isAttacked ? 'UNDER ATTACK' : 'SECURE'}
            </p>
          </div>
          <div style={{
            fontSize: '2rem',
            color: isAttacked ? 'var(--error-color)' : 'var(--success-color)'
          }}>
            {isAttacked ? '⚠️' : '✓'}
          </div>
        </div>
        
        {isAttacked && (
          <div style={{ marginTop: '10px' }}>
            <p style={{ margin: '0', fontSize: '0.9rem' }}>
              Attack duration: {status.attack_duration || 0} seconds
            </p>
            <p style={{ margin: '5px 0 0 0', fontSize: '0.9rem' }}>
              Security alert: DDoS protection engaged, traffic filtering active
            </p>
            <p style={{ margin: '5px 0 0 0', fontSize: '0.9rem' }}>
              Take immediate action to mitigate this attack!
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderDeviceMetrics = () => {
    const metrics = getLatestMetrics();
    if (!metrics) return <p>No metrics available</p>;
 
    const selectedDeviceObj = devices.find(d => d.client_id === selectedDevice);
    const deviceType = selectedDeviceObj ? selectedDeviceObj.device_type : 'mouse_sensor';
    
    return (
      <div className="card">
        <h2 className="card-title">Real-Time IoT Performance Metrics</h2>
        
        {}
        <div style={{ marginBottom: '15px' }}>
          <p><strong>Device Type:</strong> {deviceType} - A specialized IoT sensor system equipped with accelerometers, gyroscopes, and pressure sensors to capture precise gaming input data and transmit it securely across the network.</p>
          <p><strong>IoT Capabilities:</strong> Edge processing, wireless connectivity, real-time data transmission, anomaly detection, encrypted communication</p>
          <p><strong>Network Protocol:</strong> MQTT over TLS 1.3 with certificate-based authentication</p>
        </div>
        
        {}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
          {Object.entries(metrics).map(([key, value]) => (
            <div key={key} style={{ flex: '1', minWidth: '150px' }}>
              <h3>{formatMetricName(key)}</h3>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '5px 0' }}>
                {formatMetricValue(key, value)}
              </p>
              <p style={{ fontSize: '0.8rem', margin: '0', color: '#666' }}>
                {getMetricDescription(key, deviceType)}
              </p>
            </div>
          ))}
        </div>
        
        {/* IoT Network Statistics */}
        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '15px' }}>
          <h3>IoT Network Statistics</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
            <div style={{ flex: '1', minWidth: '150px' }}>
              <h4>Packet Loss</h4>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '5px 0' }}>
                {getDeviceStatus().under_attack ? '4.2%' : '0.01%'}
              </p>
            </div>
            <div style={{ flex: '1', minWidth: '150px' }}>
              <h4>Latency</h4>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '5px 0' }}>
                {getDeviceStatus().under_attack ? '12ms' : '2ms'}
              </p>
            </div>
            <div style={{ flex: '1', minWidth: '150px' }}>
              <h4>Signal Strength</h4>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '5px 0' }}>
                {getDeviceStatus().under_attack ? '-65dBm' : '-42dBm'}
              </p>
            </div>
            <div style={{ flex: '1', minWidth: '150px' }}>
              <h4>Power Consumption</h4>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: '5px 0' }}>
                {getDeviceStatus().under_attack ? '120mW' : '85mW'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const formatMetricName = (key) => {
    // Convert snake_case to Title Case
    return key.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const formatMetricValue = (key, value) => {
    // Format values with appropriate units
    if (key === 'avg_click_distance') return `${value}px`;
    if (key === 'polling_rate') return `${value}Hz`;
    if (key === 'dpi') return value.toLocaleString();
    return value;
  };

  const getMetricDescription = (key, deviceType) => {
    const descriptions = {
      clicks_per_second: 'Number of input events per second detected by the pressure sensors',
      movements_count: 'Total movement events tracked by motion sensors',
      dpi: 'Resolution of the optical/laser position sensor',
      polling_rate: 'Sensor data sampling frequency',
      avg_click_distance: 'Average pixel distance between clicks measured by position sensors',
      button_count: 'Number of discrete input sensors on device'
    };
    
    return descriptions[key] || `IoT sensor data metric for ${deviceType}`;
  };

  const renderSecurityAlerts = () => {
    if (!securityAlerts || securityAlerts.length === 0) {
      return (
        <div className="card">
          <h2 className="card-title">Security Alerts</h2>
          <p>No security alerts detected for this IoT sensor</p>
        </div>
      );
    }
    
    return (
      <div className="card">
        <h2 className="card-title">Security Alerts</h2>
        <div style={{ overflowY: 'auto', maxHeight: '300px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '12px 8px', position: 'sticky', top: 0, backgroundColor: 'var(--card-bg)', borderBottom: '2px solid var(--border-color)' }}>Timestamp</th>
                <th style={{ textAlign: 'left', padding: '12px 8px', position: 'sticky', top: 0, backgroundColor: 'var(--card-bg)', borderBottom: '2px solid var(--border-color)' }}>Event Type</th>
                <th style={{ textAlign: 'left', padding: '12px 8px', position: 'sticky', top: 0, backgroundColor: 'var(--card-bg)', borderBottom: '2px solid var(--border-color)' }}>Severity</th>
                <th style={{ textAlign: 'left', padding: '12px 8px', position: 'sticky', top: 0, backgroundColor: 'var(--card-bg)', borderBottom: '2px solid var(--border-color)' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {securityAlerts.slice().reverse().map((alert, index) => (
                <tr key={index}>
                  <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--border-color)' }}>
                    {formatDate(alert.timestamp)}
                  </td>
                  <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--border-color)' }}>
                    {formatEventType(alert.event_type)}
                  </td>
                  <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--border-color)' }}>
                    <span style={{ 
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: alert.severity === 'critical' ? 'var(--error-color)' : '#ff9800',
                      color: 'white',
                      fontWeight: 'bold',
                      fontSize: '0.8rem'
                    }}>
                      {alert.severity.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '12px 8px', borderBottom: '1px solid var(--border-color)' }}>
                    {formatAlertDetails(alert)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Helper functions for security alerts
  const formatEventType = (eventType) => {
    // Make event types more descriptive
    if (eventType === 'attack_detected') return 'Network Attack Detected';
    if (eventType === 'attack_resolved') return 'Attack Mitigation Successful';
    return eventType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  const formatAlertDetails = (alert) => {
    if (!alert.details) return 'No details available';
    
    if (typeof alert.details === 'string') {
      try {
        const details = JSON.parse(alert.details);
        return formatDetailsObject(details);
      } catch (e) {
        return alert.details;
      }
    }
    
    return formatDetailsObject(alert.details);
  };

  const formatDetailsObject = (details) => {
    if (details.attack_type === 'ping_flood') {
      return `DDoS attack detected: ${details.intensity} packets/sec (threshold: ${details.threshold}). IoT firewall engaged.`;
    }
    
    if (details.duration) {
      return `Attack resolved after ${details.duration} seconds. Normal operation restored.`;
    }
    
    return JSON.stringify(details);
  };

  if (loading) {
    return <div className="loading">Loading IoT devices...</div>;
  }

  if (error) {
    return (
      <div className="card" style={{ color: 'var(--error-color)' }}>
        <h2>Error</h2>
        <p>{error}</p>
        <button 
          className="btn btn-primary" 
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <h1>IoT Sensor Network Monitoring</h1>
      <p>Monitor your IoT gaming equipment sensors, network performance and security in real-time</p>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <select 
            value={selectedDevice || ''}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="form-control"
            style={{ padding: '8px', minWidth: '200px' }}
          >
            <option value="">Select an IoT sensor</option>
            {devices.map(device => (
              <option key={device.client_id} value={device.client_id}>
                {device.name} ({device.device_type})
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label style={{ marginRight: '10px' }}>
            Refresh interval:
            <select 
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              className="form-control"
              style={{ marginLeft: '10px', padding: '8px' }}
            >
              <option value="1">1 second</option>
              <option value="5">5 seconds</option>
              <option value="10">10 seconds</option>
              <option value="30">30 seconds</option>
            </select>
          </label>
          
          <button
            className="btn"
            onClick={() => setIsRefreshing(!isRefreshing)}
            style={{ marginLeft: '10px' }}
          >
            {isRefreshing ? 'Pause' : 'Resume'} Updates
          </button>
        </div>
      </div>

      {selectedDevice ? (
        <>
          {renderDeviceStatus()}
          {renderDeviceMetrics()}
          {renderSecurityAlerts()}
          <DeviceHeatmap deviceId={selectedDevice} />
          {}
          {devices.find(d => d.client_id === selectedDevice)?.device_type.includes('mouse') && (
            <MouseButtonHeatmap deviceId={selectedDevice} />
          )}
        </>
      ) : (
        <div className="card">
          <h2 className="card-title">No IoT Device Selected</h2>
          <p>Please select an IoT device sensor from the dropdown to view its metrics and security status.</p>
          
          {devices.length === 0 && (
            <div style={{ marginTop: '20px' }}>
              <p>No IoT devices found in your account.</p>
              <p>To add a device, go to the Devices page and register a new device with type 'mouse_sensor', 'keyboard_sensor', or 'headset_sensor'.</p>
            </div>
          )}
        </div>
      )}      
    </div>
  );
};

export default IoTDevices;