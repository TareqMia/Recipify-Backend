from yt_dlp import YoutubeDL 
from fastapi import HTTPException 
from core.config import settings
import re
from typing import Optional

class VideoService:
    YDL_OPTIONS = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'no_playlist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'cookiesfrombrowser': ('chrome',),  # Use cookies from Chrome browser
    }
    
    @staticmethod 
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various YouTube URL formats.
        Returns None if no valid ID is found.
        """
        patterns = [
            r'(?:v=|\/)([\w-]{11})(?:\?|&|\/|$)',  # Standard and embedded URLs
            r'(?:youtu\.be\/)([\w-]{11})',          # Short URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def get_video_info(video_id: str) -> tuple[str, str, int]:
        try:
            with YoutubeDL(VideoService.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                title = info.get("title", "No title available")
                description = info.get("description", "No description available")
                duration = info.get("duration", 0)
                return title, description, duration
                
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Error fetching video info: {str(e)}"
            )
            
    
    @staticmethod
    def process_recipe_for_llm(title: str, description: str, transcript: str) -> dict:
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