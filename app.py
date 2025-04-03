import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from youtube_service import YouTubeService
from download_service import DownloadService
from cache import Cache
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import json
import requests
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "youtube_proxy_secret_key")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize services
youtube_service = YouTubeService()
download_service = DownloadService()  # Initialize download service

# Initialize cache with specific settings
search_cache = Cache(ttl_seconds=3600, max_size=100, prefix="search")  # 1 hour TTL for searches

# Import models after db initialization
from models import User, SearchHistory, Video, UserVideo

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Forms for authentication
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

with app.app_context():
    try:
        # Create database tables
        db.create_all()
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        # Continue running the app even if database connection fails
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'channels')  # Default to searching for channels
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    cache_key = f"{search_type}:{query.lower()}"  # Normalize the cache key
    cached_results = search_cache.get(cache_key)

    if cached_results:
        logger.debug(f"Cache hit for {search_type} search query: {query}")
        return jsonify(cached_results)

    try:
        results = youtube_service.search(query, search_type=search_type)
        search_cache.set(cache_key, results)
        logger.debug(f"Cache miss for {search_type} search query: {query}, fetched and cached new results")

        try:
            # Save search history with user_id if authenticated
            search_history = SearchHistory(
                query=query,
                results_count=len(results.get('results', [])) if search_type == 'videos' else len(results.get('channels', [])),
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(search_history)

            # Save video information only if searching for videos
            if search_type == 'videos':
                for video in results.get('results', []):
                    try:
                        db_video = Video(
                            id=video['id'],
                            title=video['title'],
                            thumbnail_url=video['thumbnail'],
                            search_query=search_history
                        )
                        db.session.add(db_video)
                    except Exception as video_error:
                        logger.warning(f"Skipping duplicate video {video['id']}: {str(video_error)}")
                        continue

            db.session.commit()
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            db.session.rollback()
            # Continue with the search even if the database operation fails
            
        return jsonify(results)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to fetch search results'}), 500

@app.route('/channel/')
@app.route('/channel/<channel_id>')
def channel(channel_id=None):
    if not channel_id or channel_id.strip() == '':
        logger.error("No channel ID provided")
        return render_template('index.html', focus_channels=True)

    try:
        logger.debug(f"Fetching channel data for ID: {channel_id}")
        channel_data = youtube_service.get_channel_videos(channel_id)

        if channel_data.get('error'):
            logger.error(f"Error fetching channel: {channel_data['error']}")
            return render_template('error.html', error=channel_data['error']), 404

        return render_template('channel.html', channel=channel_data)
    except Exception as e:
        logger.error(f"Channel fetch error: {str(e)}")
        return render_template('error.html', error="Failed to fetch channel data"), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.route('/video/download-options/<video_id>')
def video_download_options(video_id):
    """Get available download options for a video"""
    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400
    
    try:
        streams_data = download_service.get_available_streams(video_id)
        return jsonify(streams_data)
    except Exception as e:
        logger.error(f"Download options error: {str(e)}")
        return jsonify({'error': 'Failed to get download options'}), 500

@app.route('/video/download/<video_id>')
def download_video(video_id):
    """Download a video with the specified itag"""
    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400
    
    itag = request.args.get('itag')
    if not itag:
        return jsonify({'error': 'Stream itag is required'}), 400
    
    try:
        logger.info(f"Attempting to download video {video_id} with itag {itag}")
        
        # First, get the video information for backup purposes
        streams_data = download_service.get_available_streams(video_id)
        
        # Try multiple methods in sequence until one works
        
        # Method 1: Try standard itag-based download
        result = download_service.download_video(video_id, int(itag))
        
        if not result['success'] or 'thumbnail' in result.get('file_path', '').lower():
            # Method 2: Direct download with best quality
            logger.warning(f"Itag download failed for {video_id}, trying direct download")
            result = download_service.direct_download(video_id, 'best')
        
        if not result['success'] or 'thumbnail' in result.get('file_path', '').lower():
            # Method 3: Direct download with format selected based on itag type
            logger.warning(f"Direct download failed for {video_id}, trying format-specific download")
            
            # Choose format based on requested itag
            if int(itag) in [22, 18]:  # Video formats
                format_code = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:  # Audio formats
                format_code = 'bestaudio[ext=m4a]/bestaudio/best'
                
            result = download_service.direct_download(video_id, format_code)
        
        # Always ensure we return a success response with fallback to thumbnail if needed
        if not result['success'] and streams_data['success']:
            # If all methods fail but we have video info, return a thumbnail at minimum
            logger.warning(f"All download methods failed for {video_id}, falling back to thumbnail")
            title = streams_data.get('title', 'Unknown Video')
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            thumbnail_path = os.path.join(download_service.download_folder, f"{video_id}_thumbnail.jpg")
            
            # Try to download the thumbnail as last resort
            try:
                thumbnail_response = requests.get(thumbnail_url)
                if thumbnail_response.ok:
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_response.content)
                        
                result = {
                    'success': True,
                    'title': title,
                    'file_path': os.path.join('static', 'downloads', f"{video_id}_thumbnail.jpg"),
                    'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                    'mime_type': 'image/jpeg',
                    'note': 'Could not download video due to YouTube restrictions. Downloaded thumbnail instead.'
                }
            except Exception as thumb_error:
                logger.error(f"Even thumbnail download failed: {str(thumb_error)}")
                return jsonify({'success': False, 'error': 'All download methods failed'}), 400
        
        # Return the result of whichever method succeeded
        return jsonify(result)
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': f'Failed to download video: {str(e)}'}), 500

@app.route('/downloads/<path:filename>')
def download_file(filename):
    """Serve downloaded files"""
    return send_from_directory(download_service.download_folder, filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
            
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')
        return redirect(next_page)
        
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
        
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/my-videos')
@login_required
def my_videos():
    user_videos = current_user.user_videos
    return render_template('my_videos.html', user_videos=user_videos)

@app.route('/search-history')
@login_required
def search_history():
    """View search history for the current user"""
    # Get user's search history
    if current_user.is_authenticated:
        user_searches = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.timestamp.desc()).all()
    else:
        user_searches = []
        
    # Get some global popular searches (limited to 10)
    popular_searches = SearchHistory.query.filter(
        (SearchHistory.user_id != current_user.id) | (SearchHistory.user_id.is_(None))
    ).group_by(
        SearchHistory.query
    ).order_by(
        db.func.count(SearchHistory.id).desc()
    ).limit(10).all()
    
    return render_template('search_history.html', 
                          user_searches=user_searches, 
                          popular_searches=popular_searches)

@app.route('/clear-search-history', methods=['POST'])
@login_required
def clear_search_history():
    """Clear all search history for the current user"""
    try:
        # Delete all search history records for this user
        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Search history cleared successfully.', 'success')
    except Exception as e:
        logger.error(f"Error clearing search history: {str(e)}")
        db.session.rollback()
        flash('An error occurred while clearing search history.', 'danger')
    
    return redirect(url_for('search_history'))

@app.route('/delete-search/<int:search_id>', methods=['POST'])
@login_required
def delete_search(search_id):
    """Delete a specific search history entry"""
    try:
        # Find the search entry
        search = SearchHistory.query.get_or_404(search_id)
        
        # Ensure the search belongs to the current user
        if search.user_id != current_user.id:
            flash('You do not have permission to delete this search.', 'danger')
            return redirect(url_for('search_history'))
        
        # Delete the search
        db.session.delete(search)
        db.session.commit()
        flash('Search deleted successfully.', 'success')
    except Exception as e:
        logger.error(f"Error deleting search: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the search.', 'danger')
    
    return redirect(url_for('search_history'))

@app.route('/save-video/<video_id>', methods=['POST'])
@login_required
def save_video(video_id):
    """Save a video to user's collection or update download status"""
    try:
        video_data = request.get_json()
        
        # Get video from database or create a new one
        video = Video.query.get(video_id)
        if not video:
            # If video doesn't exist in our database yet, create it
            video = Video(
                id=video_id,
                title=video_data.get('title', 'Unknown Title'),
                thumbnail_url=video_data.get('thumbnail', '')
            )
            db.session.add(video)
            # Flush to get the video ID
            db.session.flush()
        
        # Check if user already has this video
        existing = UserVideo.query.filter_by(
            user_id=current_user.id,
            video_id=video_id
        ).first()
        
        if not existing:
            # Create a new user video entry
            user_video = UserVideo(
                user_id=current_user.id,
                video_id=video_id,
                custom_title=video_data.get('custom_title', video.title),
                notes=video_data.get('notes', '')
            )
            
            # Set download status if provided
            if video_data.get('downloaded'):
                user_video.downloaded = True
                user_video.download_date = datetime.utcnow()
                user_video.download_quality = video_data.get('download_quality', 'Unknown')
            
            db.session.add(user_video)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Video saved to your collection'})
        else:
            # Update existing video if necessary
            if video_data.get('downloaded'):
                existing.downloaded = True
                existing.download_date = datetime.utcnow()
                if video_data.get('download_quality'):
                    existing.download_quality = video_data.get('download_quality')
                db.session.commit()
                return jsonify({'success': True, 'message': 'Video marked as downloaded'})
            else:
                return jsonify({'success': False, 'message': 'Video already in your collection'})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving video: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving video: {str(e)}'}), 500

@app.route('/update-video/<int:user_video_id>', methods=['POST'])
@login_required
def update_video(user_video_id):
    """Update user video details"""
    user_video = UserVideo.query.get_or_404(user_video_id)
    
    # Ensure the video belongs to the current user
    if user_video.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if 'custom_title' in data:
        user_video.custom_title = data['custom_title']
    if 'notes' in data:
        user_video.notes = data['notes']
    if 'favorite' in data:
        user_video.favorite = data['favorite']
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Video details updated'})

@app.route('/delete-video/<int:user_video_id>', methods=['POST'])
@login_required
def delete_video(user_video_id):
    """Remove a video from user's collection"""
    user_video = UserVideo.query.get_or_404(user_video_id)
    
    # Ensure the video belongs to the current user
    if user_video.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    db.session.delete(user_video)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Video removed from your collection'})

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500