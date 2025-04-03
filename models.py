from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User's videos (those they've downloaded or saved)
    user_videos = db.relationship('UserVideo', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    results_count = db.Column(db.Integer)
    
    # Add user relationship (optional - to track who made the search)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('searches', lazy=True))

class Video(db.Model):
    id = db.Column(db.String(20), primary_key=True)  # YouTube video ID
    title = db.Column(db.String(200), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    search_query_id = db.Column(db.Integer, db.ForeignKey('search_history.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    search_query = db.relationship('SearchHistory', backref=db.backref('videos', lazy=True))
    
    # User videos relationship
    user_videos = db.relationship('UserVideo', backref='video', lazy=True, cascade="all, delete-orphan")

class UserVideo(db.Model):
    """Association table between users and videos with additional metadata"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), db.ForeignKey('video.id'), nullable=False)
    
    # Custom fields users can edit
    custom_title = db.Column(db.String(200))
    notes = db.Column(db.Text)
    favorite = db.Column(db.Boolean, default=False)
    
    # Download information
    downloaded = db.Column(db.Boolean, default=False)
    download_date = db.Column(db.DateTime, nullable=True)
    download_path = db.Column(db.String(500), nullable=True)
    download_quality = db.Column(db.String(20), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserVideo {self.user_id}:{self.video_id}>'
