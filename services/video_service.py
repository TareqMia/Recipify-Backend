from yt_dlp import YoutubeDL 
from fastapi import HTTPException 
from core.config import settings
import re
from typing import Optional

class VideoService:
    
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
            with YoutubeDL(settings.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(video_id, download=False, process=False)
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