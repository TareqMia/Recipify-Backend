from typing import Optional
from yt_dlp import YoutubeDL
import os
from logger import logger

def get_yt_dlp_client() -> YoutubeDL:
    """
    Creates and returns a configured YoutubeDL client with cookie file
    """
    try:
        cookie_file = os.getenv('YOUTUBE_COOKIES_FILE')
        if cookie_file and os.path.exists(cookie_file):
            logger.info(f"Using cookie file: {cookie_file}")
        else:
            logger.warning("Cookie file not found or not specified")
            cookie_file = None

        ydl_opts = {
            'quiet': False,  # Enable output for debugging
            'no_warnings': False,  # Show warnings
            'extract_flat': True,
            'cookiefile': cookie_file,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
            },
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_requests': 1,
            'ignoreerrors': False,  # Don't ignore errors for debugging
            'no_color': True,
            'verbose': True,  # Add verbose output
        }
            
        return YoutubeDL(ydl_opts)
    except Exception as e:
        logger.error(f"Error setting up YoutubeDL client: {str(e)}")
        raise
