from typing import Tuple, Optional, Dict
from fastapi import HTTPException
from yt_dlp import YoutubeDL
import re
from logger import logger
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

class VideoService:
    def __init__(self, yt_dlp_client: Optional[YoutubeDL] = None):
        self.yt_dlp_client = yt_dlp_client
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

    def extract_video_id(self, url: str) -> Optional[str]:
        # YouTube URL patterns
        patterns = [
            r'(?:v=|/v/|youtu\.be/|/embed/)([^&?/]+)',
            r'youtube.com/shorts/([^&?/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, video_id: str) -> Tuple[str, str, int]:
        """
        Get video information using YouTube Data API
        """
        try:
            # Call the YouTube Data API
            request = self.youtube.videos().list(
                part="snippet,contentDetails",
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                logger.error(f"No video found for ID: {video_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Video not found with ID: {video_id}"
                )

            video_info = response['items'][0]
            snippet = video_info['snippet']
            content_details = video_info['contentDetails']

            # Extract duration in ISO 8601 format and convert to seconds
            duration_str = content_details['duration']
            duration = self._parse_duration(duration_str)

            title = snippet.get('title', '')
            description = snippet.get('description', '')

            logger.info(f"Successfully retrieved video info - Title: {title}, Duration: {duration}")
            return title, description, duration

        except HttpError as e:
            error_message = str(e)
            logger.error(f"YouTube API error: {error_message}")
            if "quotaExceeded" in error_message:
                raise HTTPException(
                    status_code=429,
                    detail="YouTube API quota exceeded. Please try again later."
                )
            raise HTTPException(
                status_code=500,
                detail=f"YouTube API error: {error_message}"
            )
        except Exception as e:
            logger.error(f"Error fetching video info: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching video info: {str(e)}"
            )

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration to seconds
        Example: PT1H2M10S -> 3730 seconds
        """
        try:
            import isodate
            return int(isodate.parse_duration(duration_str).total_seconds())
        except ImportError:
            logger.warning("isodate package not installed, falling back to regex parsing")
            try:
                # Basic regex parsing for duration
                hours = minutes = seconds = 0
                
                # Extract hours, minutes, seconds from PT#H#M#S format
                h_match = re.search(r'(\d+)H', duration_str)
                m_match = re.search(r'(\d+)M', duration_str)
                s_match = re.search(r'(\d+)S', duration_str)
                
                if h_match: hours = int(h_match.group(1))
                if m_match: minutes = int(m_match.group(1))
                if s_match: seconds = int(s_match.group(1))
                
                total_seconds = hours * 3600 + minutes * 60 + seconds
                return total_seconds
            except Exception as e:
                logger.error(f"Error parsing duration {duration_str}: {str(e)}")
                return 0
        except Exception as e:
            logger.error(f"Error parsing duration {duration_str}: {str(e)}")
            return 0

    def process_recipe_for_llm(self, title: str, description: str, transcript: str) -> Dict:
        context = {
            "title": title,
            "description": description[:1000],
            "transcript": transcript[:4000]
        }
        
        prompt = f"""
        Title: {context['title']}

        Description: {context['description']}

        Transcript excerpt: {context['transcript']}
        """
        
        return {
            "context": context,
            "prompt": prompt
        }