from youtube_transcript_api import YouTubeTranscriptApi
from fastapi import HTTPException

class TranscriptService:
    @staticmethod
    def get_transcript(video_id: str) -> str:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join(entry['text'] for entry in transcript_list)
        
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Could not get transcript: {str(e)}"
            )