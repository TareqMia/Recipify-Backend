# api/routes.py
from fastapi import APIRouter, HTTPException
from models.schemas import VideoRequest, VideoResponse
from services.video_service import VideoService
from services.transcript_service import TranscriptService

router = APIRouter()

@router.post("/videos/", response_model=VideoResponse)
async def process_video(video: VideoRequest):
    try:
        # Extract video ID from URL for consistency
        video_id = VideoService.extract_video_id(video.url)
        if not video_id:
            raise ValueError("Could not extract valid YouTube video ID")

        # Get video metadata
        title, description = VideoService.get_video_info(video_id)
        
        # Get transcript
        transcript = TranscriptService.get_transcript(video_id)
        
        # Only process recipe data if it's likely a recipe video
        processed_data = VideoService.process_recipe_for_llm(
            title, description, transcript
        )
        
        return VideoResponse(
            title=title,
            description=description,
            transcript=transcript,
            processed_data=processed_data
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )