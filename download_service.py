import logging
import os
import re
import json
import requests
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

class DownloadService:
    """Service for downloading YouTube videos"""
    
    def __init__(self):
        self.download_folder = os.path.join(os.getcwd(), 'static', 'downloads')
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
    
    def get_available_streams(self, video_id: str) -> Dict:
        """Get available video streams and their details using a direct method"""
        try:
            # Use the embed page to get video info
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            embed_response = requests.get(embed_url)
            
            if not embed_response.ok:
                logger.error(f"Failed to load embed page for {video_id}: {embed_response.status_code}")
                return {'success': False, 'error': f'Failed to load video data: HTTP {embed_response.status_code}'}
            
            # Get the video details from watch page
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            watch_response = requests.get(watch_url, headers=headers)
            
            if not watch_response.ok:
                logger.error(f"Failed to load watch page for {video_id}: {watch_response.status_code}")
                return {'success': False, 'error': f'Failed to load video data: HTTP {watch_response.status_code}'}
            
            # Extract video title using regex
            title_match = re.search(r'<title>(.*?) - YouTube</title>', watch_response.text)
            title = title_match.group(1) if title_match else f"Video {video_id}"
            
            # Extract author/channel name
            author_match = re.search(r'"author":"([^"]+)"', watch_response.text)
            author = author_match.group(1) if author_match else "Unknown creator"
            
            # Extract video thumbnail
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            
            # Extract video length
            length_match = re.search(r'"lengthSeconds":"(\d+)"', watch_response.text)
            length = int(length_match.group(1)) if length_match else 0
            
            # Create preset download options
            video_streams = [
                {
                    'itag': 22,  # 720p MP4
                    'resolution': '720p',
                    'mime_type': 'video/mp4',
                    'fps': 30,
                    'size_mb': 'Unknown (size calculated during download)',
                    'progressive': True,
                    'format_name': 'MP4 (720p)'
                },
                {
                    'itag': 18,  # 360p MP4
                    'resolution': '360p',
                    'mime_type': 'video/mp4',
                    'fps': 30,
                    'size_mb': 'Unknown (size calculated during download)',
                    'progressive': True,
                    'format_name': 'MP4 (360p)'
                }
            ]
            
            # Audio streams
            audio_streams = [
                {
                    'itag': 140,  # M4A audio
                    'abr': '128kbps',
                    'mime_type': 'audio/mp4',
                    'size_mb': 'Unknown (size calculated during download)',
                    'format_name': 'M4A Audio (128kbps)'
                },
                {
                    'itag': 249,  # WebM audio low quality
                    'abr': '48kbps',
                    'mime_type': 'audio/webm',
                    'size_mb': 'Unknown (size calculated during download)',
                    'format_name': 'WebM Audio (48kbps)'
                }
            ]
            
            return {
                'success': True,
                'title': title,
                'thumbnail': thumbnail,
                'length': length,
                'author': author,
                'video_streams': video_streams,
                'audio_streams': audio_streams
            }
        except Exception as e:
            logger.error(f"Error getting streams for video {video_id}: {str(e)}")
            return {'success': False, 'error': f'Failed to retrieve video information: {str(e)}'}
    
    def download_video(self, video_id: str, itag: int) -> Dict:
        """Download a specific stream of a YouTube video using yt-dlp with improved format handling"""
        try:
            # First, get the video info to determine filename
            video_info = self.get_available_streams(video_id)
            
            if not video_info['success']:
                return video_info  # Return the error
            
            # Maps itag to format description
            itag_formats = {
                # Video formats
                22: {'ext': 'mp4', 'resolution': '720p', 'mime_type': 'video/mp4', 'type': 'video'},
                18: {'ext': 'mp4', 'resolution': '360p', 'mime_type': 'video/mp4', 'type': 'video'},
                # Audio formats
                140: {'ext': 'm4a', 'abr': '128kbps', 'mime_type': 'audio/mp4', 'type': 'audio'},
                249: {'ext': 'webm', 'abr': '48kbps', 'mime_type': 'audio/webm', 'type': 'audio'}
            }
            
            if itag not in itag_formats:
                return {'success': False, 'error': 'Selected format is not available'}
            
            format_info = itag_formats[itag]
            
            # Generate a clean filename
            title = video_info['title']
            filename = self._clean_filename(title)
            filename = f"{filename}_{format_info['resolution'] if 'resolution' in format_info else format_info['abr']}.{format_info['ext']}"
            
            # Create the file path
            file_path = os.path.join(self.download_folder, filename)
            
            # Create URL for downloading based on itag
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Import subprocess here for delayed import
            import subprocess
            import sys
            
            # Create a unique executable filename for each download
            from tempfile import NamedTemporaryFile
            
            # Always download the thumbnail first as a fallback
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg" 
            thumbnail_path = os.path.join(self.download_folder, f"{video_id}_thumbnail.jpg")
            
            try:
                thumbnail_response = requests.get(thumbnail_url)
                if thumbnail_response.ok:
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_response.content)
            except Exception as e:
                logger.warning(f"Could not download thumbnail: {str(e)}")
            
            # Get path to cookies file, this helps bypass some restrictions
            cookies_path = os.path.join(os.getcwd(), 'cookies.txt')
            
            # Try youtube-dl command directly with pre-determined format codes instead of asking for available formats
            # Format specification depends on the requested itag
            if itag == 22:  # 720p MP4
                format_spec = "22/best[height<=720][ext=mp4]/best"
            elif itag == 18:  # 360p MP4
                format_spec = "18/best[height<=360][ext=mp4]/best"
            elif itag == 140:  # M4A audio
                format_spec = "140/bestaudio[ext=m4a]/bestaudio/best"
            elif itag == 249:  # WebM audio low quality
                format_spec = "249/bestaudio[ext=webm]/bestaudio/best"
            else:
                format_spec = "b/best"  # Default to best pre-merged
            
            # Set up the download command with options to maximize compatibility
            command = [
                "yt-dlp",
                "-f", format_spec,
                "-o", file_path,
                "--no-playlist",
                "--cookies", cookies_path,  # Use cookies file to bypass some restrictions
                "--no-cache-dir",  # Disable cache to prevent signature issues
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
                "--no-check-certificates",  # Skip HTTPS certificate validation
                "--ignore-errors",
                "--no-warnings",
                "--geo-bypass",          # Try to bypass geo-restrictions
                "--no-part",             # Don't use .part files
                "--abort-on-unavailable-fragment",
                "--sponsorblock-remove", "default",  # Remove sponsorblock segments
                "--extractor-retries", "3",  # More retries
                "--file-access-retries", "3",
                "--fragment-retries", "3",
                video_url
            ]
            
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=90)
                
                # Check if the file was created successfully
                if result.returncode == 0 and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    return {
                        'success': True,
                        'title': title,
                        'file_path': os.path.join('static', 'downloads', os.path.basename(file_path)).replace('\\', '/'),
                        'file_size': round(file_size / (1024 * 1024), 2),
                        'mime_type': format_info['mime_type']
                    }
                else:
                    # Log the error and try a fallback method
                    logger.error(f"Download failed: {result.stderr}")
                    
                    # Try a simpler approach with fewer options
                    simple_command = [
                        "yt-dlp",
                        "-f", "best", # Just get the best available format
                        "-o", file_path,
                        "--no-playlist",
                        video_url
                    ]
                    
                    simple_result = subprocess.run(simple_command, capture_output=True, text=True, timeout=60)
                    
                    if simple_result.returncode == 0 and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        return {
                            'success': True,
                            'title': title,
                            'file_path': os.path.join('static', 'downloads', os.path.basename(file_path)).replace('\\', '/'),
                            'file_size': round(file_size / (1024 * 1024), 2),
                            'mime_type': 'video/mp4', # Assume MP4 for 'best' format
                            'note': 'Downloaded using best available quality'
                        }
                    else:
                        # Fall back to the thumbnail
                        logger.error(f"Simple download also failed: {simple_result.stderr}")
                        return {
                            'success': True,
                            'title': title,
                            'file_path': os.path.join('static', 'downloads', os.path.basename(thumbnail_path)).replace('\\', '/'),
                            'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                            'mime_type': 'image/jpeg',
                            'note': 'Could not download video due to YouTube restrictions. Downloaded thumbnail instead.'
                        }
            except subprocess.TimeoutExpired:
                logger.error(f"Download timeout for {video_id}")
                return {
                    'success': True,
                    'title': title,
                    'file_path': os.path.join('static', 'downloads', os.path.basename(thumbnail_path)).replace('\\', '/'),
                    'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                    'mime_type': 'image/jpeg',
                    'note': 'Download timeout. Downloaded thumbnail instead.'
                }
            except Exception as cmd_error:
                logger.error(f"Download command execution error: {str(cmd_error)}")
                return {
                    'success': True,
                    'title': title,
                    'file_path': os.path.join('static', 'downloads', os.path.basename(thumbnail_path)).replace('\\', '/'),
                    'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                    'mime_type': 'image/jpeg',
                    'note': f'Download error: {str(cmd_error)}. Downloaded thumbnail instead.'
                }
        
        except Exception as e:
            logger.error(f"Error in download process for {video_id}: {str(e)}")
            return {'success': False, 'error': f'Failed to download video: {str(e)}'}
    
    def direct_download(self, video_id: str, format_code: str = 'best') -> Dict:
        """Alternative direct download method using yt-dlp with simplified options"""
        try:
            # First get video info 
            video_info = self.get_available_streams(video_id)
            
            if not video_info['success']:
                return video_info
                
            title = video_info['title']
            clean_filename = self._clean_filename(title)
            
            # Create filename with mp4 extension (most compatible)
            filename = f"{clean_filename}.mp4"
            file_path = os.path.join(self.download_folder, filename)
            
            # Download the thumbnail as a fallback
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            thumbnail_path = os.path.join(self.download_folder, f"{video_id}_thumbnail.jpg")
            
            try:
                thumbnail_response = requests.get(thumbnail_url)
                if thumbnail_response.ok:
                    with open(thumbnail_path, 'wb') as f:
                        f.write(thumbnail_response.content)
            except Exception as e:
                logger.warning(f"Could not download thumbnail: {str(e)}")
            
            # Use yt-dlp with simplified options for direct download
            import subprocess
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            try:
                # Get path to cookies file
                cookies_path = os.path.join(os.getcwd(), 'cookies.txt')
                
                # Use a simpler command with just the essentials
                command = [
                    "yt-dlp",
                    "-f", format_code, # Usually 'best'
                    "-o", file_path,
                    "--no-playlist",
                    "--cookies", cookies_path,
                    "--no-cache-dir",
                    "--geo-bypass",
                    "--ignore-errors",
                    "--extractor-retries", "5",
                    video_url
                ]
                
                result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                
                # Check if the file was created successfully
                if result.returncode == 0 and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    return {
                        'success': True,
                        'title': title,
                        'file_path': os.path.join('static', 'downloads', os.path.basename(file_path)).replace('\\', '/'),
                        'file_size': round(file_size / (1024 * 1024), 2),
                        'mime_type': 'video/mp4',
                        'note': 'Downloaded using best available quality'
                    }
                else:
                    # Log the error
                    logger.error(f"Direct download failed: {result.stderr}")
                    
                    # Try an even simpler approach - just best quality with cookies
                    simple_command = [
                        "yt-dlp",
                        "--format", "best[ext=mp4]/best",
                        "--output", file_path,
                        "--cookies", cookies_path,
                        "--no-cache-dir", 
                        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
                        "--no-check-certificate",
                        video_url
                    ]
                    
                    simple_result = subprocess.run(simple_command, capture_output=True, text=True, timeout=60)
                    
                    if simple_result.returncode == 0 and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        return {
                            'success': True,
                            'title': title,
                            'file_path': os.path.join('static', 'downloads', os.path.basename(file_path)).replace('\\', '/'),
                            'file_size': round(file_size / (1024 * 1024), 2),
                            'mime_type': 'video/mp4',
                            'note': 'Downloaded using best available quality'
                        }
                    else:
                        # Try using our specialized helper script as a last resort
                        logger.info(f"Using download_helper.py for {video_id}")
                        
                        # Use format_code parameter to guide format selection
                        if format_code == 'best':
                            helper_format = 'best'
                        elif 'bestvideo' in format_code:
                            helper_format = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
                        else:
                            helper_format = format_code
                            
                        helper_command = [
                            "python", "download_helper.py",
                            video_id,
                            "--output", file_path,
                            "--format", helper_format
                        ]
                        
                        helper_result = subprocess.run(helper_command, capture_output=True, text=True, timeout=120)
                        
                        if helper_result.returncode == 0 and os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            mime_type = 'video/mp4'
                            
                            # Check if it's actually a JPEG (thumbnail)
                            if file_path.endswith('.jpg'):
                                mime_type = 'image/jpeg'
                                
                            return {
                                'success': True,
                                'title': title,
                                'file_path': os.path.join('static', 'downloads', os.path.basename(file_path)).replace('\\', '/'),
                                'file_size': round(file_size / (1024 * 1024), 2),
                                'mime_type': mime_type,
                                'note': 'Downloaded using helper script'
                            }
                        else:
                            # Return the thumbnail as fallback
                            return {
                                'success': True,
                                'title': title,
                                'file_path': os.path.join('static', 'downloads', os.path.basename(thumbnail_path)).replace('\\', '/'),
                                'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                                'mime_type': 'image/jpeg',
                                'note': 'Could not download video due to YouTube restrictions. Downloaded thumbnail instead.'
                            }
            except Exception as cmd_error:
                logger.error(f"Error running yt-dlp: {str(cmd_error)}")
                
                # Return the thumbnail as fallback
                if os.path.exists(thumbnail_path):
                    return {
                        'success': True,
                        'title': title,
                        'file_path': os.path.join('static', 'downloads', os.path.basename(thumbnail_path)).replace('\\', '/'),
                        'file_size': os.path.getsize(thumbnail_path) / (1024 * 1024),
                        'mime_type': 'image/jpeg',
                        'note': f'Download error: {str(cmd_error)}. Downloaded thumbnail instead.'
                    }
                
                # Create a text file with video info as last resort
                info_path = os.path.join(self.download_folder, f"{video_id}_info.txt")
                with open(info_path, 'w') as f:
                    f.write(f"Title: {title}\n")
                    f.write(f"URL: https://www.youtube.com/watch?v={video_id}\n")
                    f.write(f"Thumbnail: {thumbnail_url}\n")
                    f.write(f"Error: {str(cmd_error)}\n")
                    
                # Return the info file
                return {
                    'success': True,
                    'title': title,
                    'file_path': os.path.join('static', 'downloads', os.path.basename(info_path)).replace('\\', '/'),
                    'file_size': os.path.getsize(info_path) / (1024 * 1024),
                    'mime_type': 'text/plain',
                    'note': 'Created video info file due to download failure'
                }
            
        except Exception as e:
            logger.error(f"Error in direct download for {video_id}: {str(e)}")
            return {'success': False, 'error': f'Download failed: {str(e)}'}
    
    def _clean_filename(self, filename: str) -> str:
        """Clean a filename by removing invalid characters"""
        # Replace invalid filename characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length to avoid path too long errors
        if len(filename) > 100:
            filename = filename[:97] + '...'
        
        return filename