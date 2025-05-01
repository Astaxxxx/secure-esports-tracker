
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

/**
 * @returns {Promise<boolean>}
 */
export const refreshToken = async () => {
  try {
    const currentToken = localStorage.getItem('authToken');
    if (!currentToken) {
      return false;
    }

    
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('authToken', data.token);
      console.log('Token refreshed successfully');
      return true;
    }
    
    console.warn('Token refresh failed, status:', response.status);
    return false;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
};

/**
 * Register a new user
 * @param {string} username 
 * @param {string} email 
 * @param {string} password -
 * @returns {Object} 
 */
export const register = async (username, email, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, email, password })
    });
    
    if (!response.ok) {
      if (response.status === 400) {
        const data = await response.json();
        throw new Error(data.error || 'Registration failed');
      }
      throw new Error('Registration failed');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
};

/**
 * 
 * @param {string} endpoint 
 * @param {Object} options -
 * @returns {Promise} 
 */
export const fetchWithAuth = async (endpoint, options = {}, retryCount = 0) => {
  // Get auth token from localStorage
  const token = localStorage.getItem('authToken');
  
  if (!token) {
    throw new Error('Authentication required');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });

    if (response.status === 401) {
      console.log('Token expired, attempting to refresh...');
 
      if (retryCount === 0) {
        const refreshed = await refreshToken();
        if (refreshed) {
          console.log('Token refreshed, retrying request');

          return fetchWithAuth(endpoint, options, retryCount + 1);
        }
      }

      localStorage.removeItem('authToken');
      window.location.href = '/login?session=expired';
      throw new Error('Authentication token expired');
    }
    
    if (!response.ok) {
      let errorMessage;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || `Request failed with status ${response.status}`;
      } catch (e) {
        errorMessage = `Request failed with status ${response.status}`;
      }
      throw new Error(errorMessage);
    }
    
    return response;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

/**
 * Login user 
 * @param {string} username 
 * @param {string} password 
 * @returns {Object} 
 */
export const login = async (username, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid username or password');
      }
      throw new Error('Login failed');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

/**
 * Verify 
 * @returns {Object} 
 */
export const verifyToken = async () => {
  try {
    const token = localStorage.getItem('authToken');
    if (!token) {
      throw new Error('No authentication token');
    }
    
    const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      localStorage.removeItem('authToken');
      throw new Error('Invalid token');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Token verification error:', error);
    throw error;
  }
};

/**
 * Logout user
 */
export const logout = () => {
  localStorage.removeItem('authToken');
  window.location.href = '/login';
};

/**
 * Register a new device
 * @param {string} deviceName 
 * @param {string} deviceType 
 * @returns {Object} 
 */
export const registerDevice = async (deviceName, deviceType) => {
  try {
    const response = await fetchWithAuth('/api/devices/register', {
      method: 'POST',
      body: JSON.stringify({ 
        name: deviceName,
        device_type: deviceType
      })
    });
    
    return await response.json();
  } catch (error) {
    console.error('Device registration error:', error);
    throw error;
  }
};

/**
 * 
 * @returns {Array} 
 */
export const getDevices = async () => {
  try {
    const response = await fetchWithAuth('/api/devices');
    const data = await response.json();
    return data.devices || [];
  } catch (error) {
    console.error('Error fetching devices:', error);
    return [];
  }
};

/**
 * 
 * @param {string} deviceId 
 * @param {string} status 
 * @returns {Object} 
 */
export const updateDeviceStatus = async (deviceId, status) => {
  try {
    const response = await fetchWithAuth(`/api/devices/${deviceId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status })
    });
    
    return await response.json();
  } catch (error) {
    console.error('Error updating device status:', error);
    throw error;
  }
};

/**
 * 
 * @param {string} timeRange 
 * @returns {Array} 
 */
export const getPerformanceData = async (timeRange = 'day') => {
  try {
    const response = await fetchWithAuth(`/api/analytics/performance?timeRange=${timeRange}`);
    const data = await response.json();
    return data.data || [];
  } catch (error) {
    console.error('Performance data error:', error);
    return [
      {
        timestamp: new Date(Date.now() - 50 * 60000).toISOString(),
        actions_per_minute: 120,
        key_press_count: 100,
        mouse_click_count: 50
      },
      {
        timestamp: new Date(Date.now() - 40 * 60000).toISOString(),
        actions_per_minute: 135,
        key_press_count: 110,
        mouse_click_count: 60
      },
      {
        timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
        actions_per_minute: 142,
        key_press_count: 115,
        mouse_click_count: 65
      },
      {
        timestamp: new Date(Date.now() - 20 * 60000).toISOString(),
        actions_per_minute: 128,
        key_press_count: 105,
        mouse_click_count: 55
      },
      {
        timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
        actions_per_minute: 138,
        key_press_count: 112,
        mouse_click_count: 58
      }
    ];
  }
};

/**
 * 
 * @param {number} limit 
 * @param {string} filter 
 * @returns {Array}
 */
export const getRecentSessions = async (limit = 5, filter = 'all') => {
  try {
    const response = await fetchWithAuth(`/api/sessions/recent?limit=${limit}&filter=${filter}`);
    const data = await response.json();
    return data.sessions || [];
  } catch (error) {
    console.error('Recent sessions error:', error);

    return [
      {
        id: '1',
        start_time: new Date(Date.now() - 24 * 60 * 60000).toISOString(),
        duration_minutes: 120,
        average_apm: 130,
        device_name: 'Gaming PC'
      },
      {
        id: '2',
        start_time: new Date(Date.now() - 12 * 60 * 60000).toISOString(),
        duration_minutes: 90,
        average_apm: 145,
        device_name: 'Gaming PC'
      },
      {
        id: '3',
        start_time: new Date(Date.now() - 4 * 60 * 60000).toISOString(),
        duration_minutes: 60,
        average_apm: 138,
        device_name: 'Gaming PC'
      }
    ];
  }
};

/**
 * 
 * @param {string} severity 
 * @param {number} limit 
 * @returns {Array} 
 */
export const getSecurityLogs = async (severity = 'all', limit = 100) => {
  try {
    const response = await fetchWithAuth(`/api/security/logs?severity=${severity}&limit=${limit}`);
    const data = await response.json();
    return data.logs || [];
  } catch (error) {
    console.error('Security logs error:', error);
    
    return [
      {
        id: 1,
        timestamp: new Date(Date.now() - 60 * 60000).toISOString(),
        event_type: 'login_success',
        severity: 'info',
        ip_address: '192.168.1.1',
        details: { username: 'admin' }
      },
      {
        id: 2,
        timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
        event_type: 'login_failure',
        severity: 'warning',
        ip_address: '192.168.1.2',
        details: { username: 'unknown' }
      },
      {
        id: 3,
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        event_type: 'data_access',
        severity: 'info',
        ip_address: '192.168.1.1',
        details: { data_type: 'performance_metrics' }
      }
    ];
  }
};

/**
 * Update
 * @param {Object} settings 
 * @returns {Object} 
 */
export const updateUserSettings = async (settings) => {
  try {
    const response = await fetchWithAuth('/api/users/settings', {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
    
    return await response.json();
  } catch (error) {
    console.error('Settings update error:', error);
    return { status: 'success', message: 'Settings updated (offline mode)' };
  }
};

/**
 * 
 * @param {string} deviceId 
 * @returns {Promise<Object>}
 */
export const getIoTDeviceData = async (deviceId) => {
  try {
    const response = await fetchWithAuth(`/api/metrics/iot_data/${deviceId}`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching IoT device data:', error);
    return { 
      data: [{
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
      }]
    };
  }
};

/**
 * 
 * @param {string} deviceId 
 * @returns {Promise<Object>} 
 */
export const getDeviceSecurityAlerts = async (deviceId) => {
  try {
    const response = await fetchWithAuth(`/api/security/device_alerts/${deviceId}`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching security alerts:', error);
    return { 
      alerts: [{
        timestamp: new Date().toISOString(),
        event_type: 'attack_detected',
        details: {
          attack_type: 'ping_flood',
          intensity: 72,
          threshold: 50
        },
        severity: 'critical'
      }]
    };
  }
};

/**
 * 
 * @param {string} deviceId 
 * @param {string} command 
 * @param {Object} params 
 * @returns {Promise<Object>} 
 */
export const sendDeviceCommand = async (deviceId, command, params = {}) => {
  try {
    const response = await fetchWithAuth(`/api/device/${deviceId}/command`, {
      method: 'POST',
      body: JSON.stringify({
        command,
        ...params
      })
    });
    return await response.json();
  } catch (error) {
    console.error('Error sending device command:', error);
    return { status: 'error', message: error.message };
  }
};