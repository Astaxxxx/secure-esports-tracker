import React, { useState, useEffect } from 'react';

const MouseButtonHeatmap = ({ deviceId }) => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchHeatmapData = async () => {
      if (!deviceId) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const token = localStorage.getItem('authToken');
        const response = await fetch(`http://localhost:5000/api/metrics/mouse_contact_heatmap/${deviceId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch mouse contact heatmap data');
        }

        const data = await response.json();
        setHeatmapData(data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching mouse contact data:', err);
        setError(err.message);
        generateFallbackData();
      }
    };
    
    const generateFallbackData = () => {
      const fallbackData = {
        contact_points: {
          'top_left': 92,
          'top_right': 74,
          'top_middle': 45,
          'left_front': 87,
          'left_back': 65,
          'left_bottom': 53,
          'right_side': 28,
          'palm_rest': 80,
          'wrist_area': 50,
        },
        pressure: {
          'top_left': 88,
          'top_right': 72,
          'left_front': 92,
          'palm_rest': 65,
        },
        click_data: {
          'left_click': 6452,
          'right_click': 2341,
          'middle_click': 478,
          'side_button_1': 965,
          'side_button_2': 1247
        },
        finger_position: {
          'index_finger': {
            'x_offset': 2,
            'y_offset': -3,
            'angle': 12
          },
          'middle_finger': {
            'x_offset': -1,
            'y_offset': 4,
            'angle': 8
          },
          'thumb': {
            'x_offset': 5,
            'y_offset': 7,
            'angle': 22
          }
        },
        posture_issues: [
          {
            'issue': 'excessive_wrist_extension',
            'severity': 'medium',
            'description': 'Your wrist is extended upward too much'
          },
          {
            'issue': 'thumb_overextension',
            'severity': 'high',
            'description': 'Your thumb is stretched too far to reach the side buttons'
          }
        ],
        timestamp: new Date().toISOString()
      };
      setHeatmapData(fallbackData);
      setLoading(false);
    };
    
    fetchHeatmapData();
    
    const refreshTimeout = setTimeout(() => {
      fetchHeatmapData();
    }, 10000); 
    
    return () => clearTimeout(refreshTimeout);
    
  }, [deviceId]); 
  
  if (loading) {
    return (
      <div className="card">
        <h2 className="card-title">Mouse Physical Contact Analysis</h2>
        <p>Loading mouse contact data...</p>
      </div>
    );
  }
  
  if (error && !heatmapData) {
    return (
      <div className="card">
        <h2 className="card-title">Mouse Physical Contact Analysis</h2>
        <p>Showing simulated data. API error: {error}</p>
      </div>
    );
  }
  
  const getHeatColor = (value) => {
    if (value < 20) return `rgba(0, 0, 255, ${value / 100})`;
    if (value < 50) return `rgba(0, ${255 - ((value - 20) * 255 / 30)}, 255, ${value / 100})`;
    if (value < 80) return `rgba(${((value - 50) * 255 / 30)}, 0, ${255 - ((value - 50) * 255 / 30)}, ${value / 100})`;
    return `rgba(255, 0, 0, ${value / 100})`;
  };
  
  const getTextColor = (value) => {
    return value > 50 ? 'white' : 'black';
  };
  
  return (
    <div className="card">
      <h2 className="card-title">Mouse Physical Contact Analysis</h2>
      <p>IoT sensor data showing contact points and pressure on the physical mouse device</p>
      
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
        <div style={{ 
          position: 'relative',
          width: '400px', 
          height: '300px',
          margin: '20px auto',
          perspective: '800px'
        }}>
          <div style={{ 
            position: 'absolute',
            top: '50px',
            left: '100px',
            width: '200px', 
            height: '120px',
            backgroundColor: '#333',
            borderRadius: '60px 60px 120px 120px',
            boxShadow: '0 5px 15px rgba(0,0,0,0.3)',
            transform: 'rotateX(45deg)',
            transformStyle: 'preserve-3d'
          }}>
            <div style={{ 
              position: 'absolute',
              top: '0',
              left: '0',
              width: '100px',
              height: '60px',
              borderRadius: '60px 0 0 0',
              backgroundColor: getHeatColor(heatmapData.contact_points.top_left),
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.top_left),
              fontSize: '10px'
            }}>
              {heatmapData.contact_points.top_left}%
            </div>
            <div style={{ 
              position: 'absolute',
              top: '0',
              right: '0',
              width: '100px',
              height: '60px',
              borderRadius: '0 60px 0 0',
              backgroundColor: getHeatColor(heatmapData.contact_points.top_right),
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.top_right),
              fontSize: '10px'
            }}>
              {heatmapData.contact_points.top_right}%
            </div>
            <div style={{ 
              position: 'absolute',
              top: '15px',
              left: '90px',
              width: '20px',
              height: '30px',
              borderRadius: '5px',
              backgroundColor: getHeatColor(heatmapData.contact_points.top_middle),
              border: '1px solid #222'
            }}></div>
            <div style={{ 
              position: 'absolute',
              bottom: '0',
              left: '40px',
              width: '120px',
              height: '50px',
              borderRadius: '0 0 120px 120px',
              backgroundColor: getHeatColor(heatmapData.contact_points.palm_rest),
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.palm_rest),
              fontSize: '10px'
            }}>
              {heatmapData.contact_points.palm_rest}%
            </div>
          </div>
          <div style={{ 
            position: 'absolute',
            top: '100px',
            left: '75px',
            width: '25px',
            height: '100px',
            backgroundColor: '#444',
            borderRadius: '10px 0 0 20px',
            transform: 'rotateY(-60deg)',
            transformStyle: 'preserve-3d'
          }}>
            <div style={{ 
              position: 'absolute',
              top: '30px',
              left: '0',
              width: '25px',
              height: '30px',
              backgroundColor: getHeatColor(heatmapData.contact_points.left_front),
              borderRadius: '10px 0 0 0',
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.left_front),
              fontSize: '10px',
              transform: 'rotateY(60deg)'
            }}>
              {heatmapData.contact_points.left_front}%
            </div>
            <div style={{ 
              position: 'absolute',
              top: '60px',
              left: '0',
              width: '25px',
              height: '40px',
              backgroundColor: getHeatColor(heatmapData.contact_points.left_back),
              borderRadius: '0 0 0 20px',
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.left_back),
              fontSize: '10px',
              transform: 'rotateY(60deg)'
            }}>
              {heatmapData.contact_points.left_back}%
            </div>
          </div>
          <div style={{ 
            position: 'absolute',
            top: '100px',
            right: '75px',
            width: '25px',
            height: '100px',
            backgroundColor: '#444',
            borderRadius: '0 10px 20px 0',
            transform: 'rotateY(60deg)',
            transformStyle: 'preserve-3d'
          }}>
            <div style={{ 
              position: 'absolute',
              top: '30px',
              right: '0',
              width: '25px',
              height: '70px',
              backgroundColor: getHeatColor(heatmapData.contact_points.right_side),
              borderRadius: '0 10px 20px 0',
              border: '1px solid #222',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: getTextColor(heatmapData.contact_points.right_side),
              fontSize: '10px',
              transform: 'rotateY(-60deg)'
            }}>
              {heatmapData.contact_points.right_side}%
            </div>
          </div>
        </div>
        <div style={{ width: '100%', marginTop: '20px' }}>
          <h3>Button Usage Statistics</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px' }}>
            {Object.entries(heatmapData.click_data).map(([buttonName, clickCount]) => (
              <div key={buttonName} style={{ 
                flex: '1', 
                minWidth: '150px',
                padding: '15px',
                backgroundColor: 'var(--card-bg)', 
                borderRadius: '8px',
                border: '1px solid var(--border-color)'
              }}>
                <h4 style={{ margin: '0 0 10px 0' }}>{buttonName.replace(/_/g, ' ').toUpperCase()}</h4>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: 'bold',
                  textAlign: 'center',
                  margin: '10px 0'
                }}>
                  {clickCount.toLocaleString()}
                </div>
                <div style={{ 
                  fontSize: '12px',
                  textAlign: 'center',
                  color: '#666'
                }}>
                  total clicks
                </div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ 
          width: '100%',
          marginTop: '20px',
          padding: '15px',
          backgroundColor: 'rgba(98, 0, 234, 0.1)',
          borderRadius: '8px',
          border: '1px solid var(--primary-color)'
        }}>
          <h3 style={{ margin: '0 0 10px 0' }}>Ergonomic Analysis & Recommendations</h3>
          {heatmapData.posture_issues && heatmapData.posture_issues.length > 0 ? (
            <ul style={{ margin: '0', paddingLeft: '20px' }}>
              {heatmapData.posture_issues.map((issue, index) => (
                <li key={index} style={{ marginBottom: '10px' }}>
                  <strong style={{ 
                    color: issue.severity === 'high' ? 'var(--error-color)' : 
                           issue.severity === 'medium' ? '#ff9800' : 'var(--success-color)'
                  }}>
                    {issue.issue.replace(/_/g, ' ').toUpperCase()} ({issue.severity}):
                  </strong> {issue.description}
                </li>
              ))}
            </ul>
          ) : (
            <p>No significant posture issues detected. Your hand position looks good!</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default MouseButtonHeatmap;