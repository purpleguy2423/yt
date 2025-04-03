#!/usr/bin/env python
"""
YouTube download helper script
This is a specialized script for downloading videos from YouTube
when standard methods fail
"""

import argparse
import os
import sys
import subprocess
import re
import json
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("download_helper.log")
    ]
)
logger = logging.getLogger("download_helper")

class YouTubeDownloader:
    """Helper class for downloading YouTube videos with multiple fallback approaches"""
    
    def __init__(self):
        # Default paths
        self.cookies_path = os.path.join(os.getcwd(), 'cookies.txt')
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
    
    def download(self, video_id, output_path, format_code="best"):
        """Download a YouTube video using multiple fallback methods"""
        logger.info(f"Attempting to download video {video_id} with format {format_code}")
        
        # Create the URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Try to download with yt-dlp using our custom options
        success = self._download_with_ytdlp(video_url, output_path, format_code)
        
        if not success:
            # Try fallback method 1: Use a different format specification
            logger.info("First method failed, trying alternative format specification")
            success = self._download_with_ytdlp(
                video_url, 
                output_path, 
                f"bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            )
        
        if not success:
            # Try fallback method 2: Use a very basic approach
            logger.info("Second method failed, trying basic download")
            success = self._download_basic(video_url, output_path)
        
        if not success:
            # Try fallback method 3: Use cookies and embed URL instead
            logger.info("All direct methods failed, trying embed URL with cookies")
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            success = self._download_with_ytdlp(embed_url, output_path, "best")
        
        # Last resort: try to get just the thumbnail
        if not success:
            logger.info("All download methods failed, trying to download thumbnail")
            return self._download_thumbnail(video_id, output_path)
        
        return os.path.exists(output_path)
    
    def _download_with_ytdlp(self, url, output_path, format_code):
        """Download using yt-dlp with specified options"""
        try:
            command = [
                "yt-dlp",
                "-f", format_code,
                "-o", output_path,
                "--cookies", self.cookies_path,
                "--no-playlist",
                "--no-cache-dir",
                "--geo-bypass",
                "--no-warnings",
                "--no-check-certificate",
                "--user-agent", self.user_agent,
                "--referer", "https://www.youtube.com/",
                "--continue",
                "--no-part",
                "--force-overwrites",
                url
            ]
            
            logger.info(f"Running command: {' '.join(command)}")
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=120
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Download succeeded: {output_path}")
                return True
            else:
                logger.error(f"Download failed with error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error in yt-dlp download: {str(e)}")
            return False
    
    def _download_basic(self, url, output_path):
        """Attempt a very basic download with minimal options"""
        try:
            command = [
                "yt-dlp",
                "--format", "best",
                "--output", output_path,
                url
            ]
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            return result.returncode == 0 and os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Error in basic download: {str(e)}")
            return False
    
    def _download_thumbnail(self, video_id, original_output_path):
        """Download the video thumbnail as a fallback"""
        try:
            # Extract file path info
            output_dir = os.path.dirname(original_output_path)
            # Create the thumbnail path with jpg extension
            thumbnail_path = os.path.join(output_dir, f"{video_id}_thumbnail.jpg")
            
            # Try to get the maxresdefault thumbnail first
            url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            response = requests.get(url)
            
            if not response.ok:
                # Try the hqdefault if maxresdefault isn't available
                url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                response = requests.get(url)
            
            if response.ok:
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded thumbnail as fallback: {thumbnail_path}")
                return True
            else:
                logger.error("Failed to download thumbnail")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {str(e)}")
            return False
            
def main():
    """Main function to handle command line usage"""
    parser = argparse.ArgumentParser(description="Download YouTube videos with multiple fallback methods")
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--format", "-f", default="best", help="Format code to download")
    
    args = parser.parse_args()
    
    downloader = YouTubeDownloader()
    success = downloader.download(args.video_id, args.output, args.format)
    
    if success:
        print(f"Download completed successfully: {args.output}")
        return 0
    else:
        print("Download failed after all attempts")
        return 1

if __name__ == "__main__":
    sys.exit(main())