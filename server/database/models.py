import os
import uuid
import hashlib
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)

    devices = db.relationship('Device', backref='owner', lazy=True)
    
    def set_password(self, password):

        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:150000')
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    client_id = db.Column(db.String(36), unique=True, nullable=False)
    client_secret = db.Column(db.String(64), nullable=False)
    encryption_key = db.Column(db.String(64), nullable=False, default=lambda: os.urandom(32).hex())
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50))  
    status = db.Column(db.String(20), default='pending')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime)

    sessions = db.relationship('Session', backref='device', lazy=True)
    
    def __repr__(self):
        return f'<Device {self.name} ({self.client_id[:8]})>'

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)

    metrics = db.relationship('PerformanceMetric', backref='session', lazy=True)
    
    def __repr__(self):
        return f'<Session {self.session_id[:8]}>'
        
    def calculate_duration(self):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = int(delta.total_seconds())
        return self.duration_seconds

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50))
    publisher = db.Column(db.String(100))

    sessions = db.relationship('Session', backref='game', lazy=True)
    
    def __repr__(self):
        return f'<Game {self.name}>'

class PerformanceMetric(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    key_press_count = db.Column(db.Integer, default=0)
    mouse_click_count = db.Column(db.Integer, default=0)
    actions_per_minute = db.Column(db.Integer, default=0)

    average_response_time_ms = db.Column(db.Float)
    key_hold_duration_ms = db.Column(db.Float)
    mouse_travel_distance_px = db.Column(db.Float)
    
    def __repr__(self):
        return f'<Metric {self.id} - APM: {self.actions_per_minute}>'

class SecurityEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)  
    ip_address = db.Column(db.String(45))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    details = db.Column(db.Text)
    severity = db.Column(db.String(20), default='info') 
    
    def __repr__(self):
        return f'<SecurityEvent {self.id} - {self.event_type}>'