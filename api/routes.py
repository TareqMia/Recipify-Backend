# api/routes.py
import json
import logging
import os
from datetime import datetime

import boto3
import dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from models.schemas import ContentCategory, VideoRequest, VideoResponse, VideoContent
from services.recipe_service import RecipeService
from services.transcript_service import TranscriptService
from services.video_service import VideoService
from services.firebase_service import FirebaseService

from logger import logger
from pyinstrument import Profiler 

dotenv.load_dotenv()

router = APIRouter()

def get_bedrock_client():
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

def get_recipe_service() -> RecipeService:
    return RecipeService()

@router.post("/videos/")
async def process_video(
    video: VideoRequest,
    video_service: VideoService = Depends(),
    transcript_service: TranscriptService = Depends(),
    recipe_service: RecipeService = Depends(get_recipe_service),
):
    with Profiler() as profiler:
        logger.info(f"Processing video URL: {video.url}")
    try:
        # TODO: Handle case for large videos  
          
        logger.info(f"Starting to process video URL: {video.url}")
        video_id = video_service.extract_video_id(video.url)
        if not video_id:
            logging.error(f"Failed to extract video ID from URL: {video.url}")
            raise ValueError("Could not extract valid YouTube video ID")

        # Check if video exists in Firebase
        logger.info(f"Checking if video {video_id} exists in Firebase")
        cached_data = FirebaseService.get_recipe(video_id)
        logging.info(f"Cached data retrieved: {cached_data}")
        if cached_data:
            try:
                logger.info(f"Video {video_id} already processed, returning cached data.")
                return VideoResponse(**cached_data)
            except ValidationError as ve:
                logging.error(f"Validation error with cached data: {ve}")
                # Optionally, choose to process the video anew

        # If video not found in either database, process it
        logger.info(f"Video {video_id} not found in cache, processing...")

        logger.info(f"Fetching video info for {video_id}")
        title, description, duration = video_service.get_video_info(video_id) 
        logger.info(f"Duration: {duration}")
        logger.info(f"Fetching transcript for {video_id}")
        transcript = await transcript_service.get_transcript(video_id)

        # TODO: Handle case where no transcript or descr is found
        # Create VideoContent object
        video_content = VideoContent(
            title=title,
            description=description,
            transcript=transcript
        )

        # First, classify the video
        classification = recipe_service.classify_video_content(video_content)
    
        
        # Prepare initial video data
        video_data = {
            "video_id": video_id,
            "title": title,
            "description": description,
            "transcript": transcript,
            "is_recipe_video": classification.is_recipe == ContentCategory.recipe,
            "created_at": datetime.utcnow().isoformat()
        }

        # If it's a recipe, generate the recipe
        if classification.is_recipe == ContentCategory.recipe:
            processed_data = video_service.process_recipe_for_llm(
                title, description, transcript
            )

            recipe = classification.recipe_details
            
            
            video_data.update({
                "processed_data": json.dumps({
                    "classification": classification.model_dump(),
                    "llm_prompt": processed_data['prompt']
                }),
                "recipe": recipe if recipe else None
            })
        else:
            video_data.update({
                "processed_data": json.dumps({
                    "classification": classification.model_dump_json()
                }),
                "recipe": None
            })

        # Store data and return response
        FirebaseService.store_recipe(video_id, video_data)

        return video_data
    
       

    except Exception as e:
        logging.error(f"Error processing video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the video: {str(e)}"
        )
        
    
        
    