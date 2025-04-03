import requests
from urllib.parse import parse_qs, urlparse
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.base_url = "https://www.youtube.com"
        self.search_url = f"{self.base_url}/results"
        self.video_url = f"{self.base_url}/embed"
        self.watch_url = f"{self.base_url}/watch"
        self.fallback_patterns = [
            "embed",
            "watch",
            "shorts"
        ]

    def _extract_video_id(self, html_content):
        logger.debug("Starting video information extraction")
        # Enhanced patterns for better metadata extraction
        patterns = {
            'video_id': r'\"videoId\":\"([^\"]{11})\"',
            'title': r'\"title\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\"\}\]',
            'channel': r'\"ownerText\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\"',
            # Enhanced channel ID pattern to catch more formats
            'channel_id': r'\"channelId\":\"([^\"]+?)\"',
            'views': r'\"viewCountText\":\{\"simpleText\":\"([^\"]+?)\"',
            'duration': r'\"lengthText\":\{\"simpleText\":\"([^\"]+?)\"',
            'publish_time': r'\"publishedTimeText\":\{\"simpleText\":\"([^\"]+?)\"',
            'description': r'\"descriptionSnippet\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\"'
        }

        # Extract all patterns
        matches = {
            key: list(re.finditer(pattern, html_content))
            for key, pattern in patterns.items()
        }

        logger.debug(f"Found matches - Videos: {len(matches['video_id'])}")

        videos = []
        seen_videos = set()

        for i in range(min(len(matches['video_id']), 60)):  # Increased limit to show more videos
            try:
                video_id = matches['video_id'][i].group(1)

                # Skip duplicates
                if video_id in seen_videos:
                    continue
                seen_videos.add(video_id)

                # Extract all available metadata
                video_data = {
                    'id': video_id,
                    'title': matches['title'][i].group(1) if i < len(matches['title']) else "Untitled",
                    'thumbnail': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    'channel': matches['channel'][i].group(1) if i < len(matches['channel']) else "Unknown Channel",
                    'channel_id': matches['channel_id'][i].group(1) if i < len(matches['channel_id']) else "",
                    'views': matches['views'][i].group(1) if i < len(matches['views']) else "No view count",
                    'duration': matches['duration'][i].group(1) if i < len(matches['duration']) else "Unknown duration",
                    'publish_time': matches['publish_time'][i].group(1) if i < len(matches['publish_time']) else "",
                    'description': matches['description'][i].group(1) if i < len(matches['description']) else ""
                }
                videos.append(video_data)
                logger.debug(f"Successfully extracted video: {video_data['title']}")
            except Exception as e:
                logger.error(f"Error extracting video data: {str(e)}")
                continue

        return videos

    def _extract_channel_info(self, html_content):
        """Extract channel information from search results"""
        logger.debug("Starting channel information extraction")
        
        # Enhanced patterns for channel data
        patterns = {
            'channel_id': r'\"channelId\":\"([^\"]+?)\"',
            'channel_name': r'\"title\":\{\"simpleText\":\"([^\"]+?)\"\}',
            'subscriber_count': r'\"subscriberCountText\":\{\"simpleText\":\"([^\"]+?)\"',
            'thumbnail': r'\"thumbnail\":\{\"thumbnails\":\[\{\"url\":\"([^\"]+?)\"',
            'description': r'\"descriptionSnippet\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\"',
            'handle': r'\"ownerText\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\",\"navigationEndpoint\":\{\"commandMetadata\":\{\"webCommandMetadata\":\{\"url\":\"\\\/(@[^\"]+?)\"'
        }
        
        # Extract all patterns
        matches = {
            key: list(re.finditer(pattern, html_content))
            for key, pattern in patterns.items()
        }
        
        logger.debug(f"Found matches - Channels: {len(matches['channel_id'])}")
        
        channels = []
        seen_channels = set()
        
        for i in range(min(len(matches['channel_id']), 30)):
            try:
                channel_id = matches['channel_id'][i].group(1)
                
                # Skip duplicates
                if channel_id in seen_channels:
                    continue
                seen_channels.add(channel_id)
                
                # Extract channel data
                channel_data = {
                    'id': channel_id,
                    'name': matches['channel_name'][i].group(1) if i < len(matches['channel_name']) else "Unknown Channel",
                    'thumbnail': matches['thumbnail'][i].group(1) if i < len(matches['thumbnail']) else "",
                    'subscriber_count': matches['subscriber_count'][i].group(1) if i < len(matches['subscriber_count']) else "Unknown subscribers",
                    'description': matches['description'][i].group(1) if i < len(matches['description']) else ""
                }
                
                # Add handle if available (for better channel navigation)
                if 'handle' in matches and i < len(matches['handle']):
                    try:
                        channel_data['handle'] = matches['handle'][i].group(2)
                    except (IndexError, AttributeError):
                        pass
                
                channels.append(channel_data)
                logger.debug(f"Successfully extracted channel: {channel_data['name']}")
            except Exception as e:
                logger.error(f"Error extracting channel data: {str(e)}")
                continue
                
        return channels

    def search(self, query: str, search_type="videos") -> dict:
        try:
            logger.debug(f"Searching for query: {query}, type: {search_type}")
            
            # Set parameters based on search type
            if search_type == "channels":
                # Filter for channels
                sp_param = "EgIQAg%3D%3D"
            else:
                # Default filter for videos
                sp_param = "CAISAhAB"
                
            # Enhanced search parameters
            params = {
                'search_query': query,
                'sp': sp_param,
                'app': 'desktop',
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(self.search_url, params=params, headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                logger.debug("Successfully received search results from YouTube")
                
                if search_type == "channels":
                    results = self._extract_channel_info(response.text)
                    return {'channels': results[:15], 'search_type': 'channels', 'total_results': len(results)}
                else:
                    videos = self._extract_video_id(response.text)
                    return {'results': videos[:20], 'search_type': 'videos', 'total_results': len(videos)}
            else:
                logger.error(f"YouTube search failed with status code: {response.status_code}")
                return {'results': [], 'search_type': search_type}

        except requests.RequestException as e:
            logger.error(f"Search request failed: {str(e)}")
            raise

    def get_video_url(self, video_id: str) -> dict:
        """Get video URL with availability check and metadata"""
        logger.debug(f"Attempting to get video URL for ID: {video_id}")

        # Try different URL patterns and collect video metadata
        video_info = {
            'url': None,
            'is_restricted': False,
            'error_message': None
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # First try to get video info
        try:
            info_url = f"{self.base_url}/watch?v={video_id}"
            response = requests.get(info_url, headers=headers)

            if "age-restricted" in response.text.lower():
                video_info['is_restricted'] = True
                video_info['error_message'] = "This video is age-restricted"
            elif "unavailable" in response.text.lower():
                video_info['error_message'] = "This video is unavailable"
        except requests.RequestException as e:
            logger.warning(f"Failed to check video info: {str(e)}")

        # Try different URL patterns if video isn't clearly restricted
        if not video_info['is_restricted']:
            for pattern in self.fallback_patterns:
                try:
                    if pattern == "embed":
                        url = f"{self.base_url}/embed/{video_id}?autoplay=1&rel=0&modestbranding=1"
                    elif pattern == "watch":
                        url = f"{self.base_url}/watch?v={video_id}"
                    else:
                        url = f"{self.base_url}/shorts/{video_id}"

                    response = requests.head(url, headers=headers, allow_redirects=True)
                    if response.status_code == 200:
                        video_info['url'] = url
                        logger.debug(f"Successfully found working URL pattern: {pattern}")
                        break

                except requests.RequestException as e:
                    logger.warning(f"Failed to access {pattern} URL for video {video_id}: {str(e)}")
                    continue

        # If no URL was found but no specific error was detected
        if not video_info['url'] and not video_info['error_message']:
            video_info['error_message'] = "This video is currently unavailable in your region"

        return video_info

    def get_channel_videos(self, channel_id: str) -> dict:
        """Fetch videos for a specific channel"""
        if not channel_id:
            logger.error("Channel ID is required")
            return {'error': 'Channel ID is required'}

        try:
            logger.debug(f"Fetching videos for channel: {channel_id}")
            # Try multiple URL formats for channels
            channel_urls = []
            
            # Handle both @ handles and channel IDs
            if channel_id.startswith('@'):
                channel_urls.append(f"{self.base_url}/{channel_id}/videos")
            elif channel_id.startswith('UC'):
                channel_urls.append(f"{self.base_url}/channel/{channel_id}/videos")
            else:
                # Try all formats if the channel ID format is unclear
                channel_urls = [
                    f"{self.base_url}/c/{channel_id}/videos",
                    f"{self.base_url}/channel/{channel_id}/videos",
                    f"{self.base_url}/@{channel_id}/videos",
                    f"{self.base_url}/user/{channel_id}/videos"
                ]

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # Try all URL formats until one works
            html_content = None
            for url in channel_urls:
                try:
                    logger.debug(f"Trying channel URL: {url}")
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        html_content = response.text
                        logger.debug(f"Successfully received channel page HTML from {url}")
                        break
                except requests.RequestException as e:
                    logger.warning(f"Failed to access {url}: {str(e)}")
                    continue

            if not html_content:
                logger.error("All channel URL formats failed")
                return {'error': 'Channel not found or unavailable'}

            # Extract channel information with multiple patterns
            channel_title_pattern = r'\"title\":\"([^\"]+?)\"'
            
            # Try multiple subscriber count patterns
            subscriber_patterns = [
                r'\"subscriberCountText\":\{\"simpleText\":\"([^\"]+?)\"',
                r'\"subscriberCountText\":\{\"runs\":\[\{\"text\":\"([^\"]+?)\"',
                r'subscribers\":\{\"simpleText\":\"([^\"]+?)\"',
                r'\"subCount\":\"([^\"]+?)\"'
            ]

            channel_title_match = re.search(channel_title_pattern, html_content)
            
            # Try all subscriber patterns
            subscriber_match = None
            for pattern in subscriber_patterns:
                subscriber_match = re.search(pattern, html_content)
                if subscriber_match:
                    logger.debug(f"Found subscriber count with pattern: {pattern}")
                    break

            # Check if we got valid channel data
            if not channel_title_match:
                logger.error("Could not find channel title in response")
                return {'error': 'Channel not found'}

            # Extract videos using the same pattern as search results
            videos = self._extract_video_id(html_content)
            
            # Format videos with consistent metadata for display
            for video in videos:
                # Make sure view count is properly formatted
                if 'views' in video and video['views']:
                    if not any(substring in video['views'].lower() for substring in ['views', 'view']):
                        video['views'] = f"{video['views']} views"
            
            # Get as many videos as we can extract, up to 50
            max_videos = 50
            
            channel_data = {
                'id': channel_id,
                'title': channel_title_match.group(1) if channel_title_match else "Unknown Channel",
                'subscriber_count': subscriber_match.group(1) if subscriber_match else "Unknown subscribers",
                'videos': videos[:max_videos],  # Show more videos for better channel browsing
                'video_count': len(videos)  # Store the total number of videos we found
            }

            if not channel_data['videos']:
                logger.warning("No videos found for channel")
                return {'error': 'No videos found for this channel'}

            logger.debug(f"Successfully extracted {len(channel_data['videos'])} videos for channel")
            return channel_data

        except Exception as e:
            logger.error(f"Channel fetch request failed: {str(e)}")
            return {'error': f'Failed to fetch channel data: {str(e)}'}