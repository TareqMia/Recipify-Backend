# api/routes.py
import json
import logging
import os
from datetime import datetime
from typing import List

import boto3
import dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from yt_dlp import YoutubeDL

from models.schemas import ContentCategory, VideoRequest, VideoResponse, VideoContent, NutritionRequest, NutritionLabel, NutritionIngredient, NutritionResponse
from services.recipe_service import RecipeService
from services.transcript_service import TranscriptService
from services.video_service import VideoService
from services.firebase_service import FirebaseService
from services.nutrition_service import NutritionService
from services.nutrition_service_v2 import NutritionServiceV2

from logger import logger
from pyinstrument import Profiler
from api.dependencies import get_yt_dlp_client

# Load environment variables
dotenv.load_dotenv()

router = APIRouter()

def get_bedrock_client():
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
@router.get("/hello/")
async def hello():
    return {"message": "testing enpoint"}

def get_recipe_service() -> RecipeService:
    return RecipeService()

@router.post("/videos/", response_model=VideoResponse)
async def process_video(
    video: VideoRequest,
    yt_dlp_client: YoutubeDL = Depends(get_yt_dlp_client),
    transcript_service: TranscriptService = Depends(),
    recipe_service: RecipeService = Depends(get_recipe_service),
    nutrition_service: NutritionServiceV2 = Depends(),
):
    logger.info(f"Processing video URL: {video.url}")
    
    try:
        # Initialize VideoService with the yt-dlp client
        video_service = VideoService(yt_dlp_client=yt_dlp_client)
        
        logger.info(f"Starting to process video URL: {video.url}")
        video_id = video_service.extract_video_id(video.url)
        if not video_id:
            logger.error(f"Failed to extract video ID from URL: {video.url}")
            raise HTTPException(status_code=400, detail="Invalid YouTube video URL")

        # Check if video exists in Firebase
        logger.info(f"Checking if video {video_id} exists in Firebase")
        cached_data = FirebaseService.get_recipe(video_id)
        if cached_data:
            try:
                logger.info(f"Video {video_id} already processed, returning cached data.")
                response = VideoResponse(**cached_data)
                print(f"\n=== CACHED VIDEO RESPONSE ===")
                if response.nutrition:
                    print(f"Nutrition data present:")
                    print(f"Total calories: {response.nutrition.total.calories}")
                    print(f"Total protein: {response.nutrition.total.protein.amount}g")
                else:
                    print("No nutrition data in cached response")
                return response
            except ValidationError as ve:
                logger.error(f"Validation error with cached data: {ve}")
                # Proceed to process the video

        # Process the video as it's not cached
        logger.info(f"Video {video_id} not found in cache, processing...")

        title, description, duration = video_service.get_video_info(video_id)
        logger.info(f"Fetched video info: Title='{title}', Duration={duration}")

        transcript = await transcript_service.get_transcript(video_id)
        if not transcript:
            logger.warning(f"No transcript found for video {video_id}.")
            raise HTTPException(status_code=404, detail="Transcript not found for the video.")

        video_content = VideoContent(
            title=title,
            description=description,
            transcript=transcript
        )

        # Classify the video content
        classification = recipe_service.classify_video_content(video_content)

        video_data = {
            "video_id": video_id,
            "title": title,
            "description": description,
            "transcript": transcript,
            "is_recipe_video": classification.is_recipe == ContentCategory.recipe,
            "created_at": datetime.utcnow().isoformat()
        }

        if classification.is_recipe == ContentCategory.recipe:
            processed_data = video_service.process_recipe_for_llm(title, description, transcript)
            recipe = classification.recipe_details
            
            # Ensure keywords are included in recipe data
            if recipe and 'keywords' not in recipe:
                recipe['keywords'] = classification.suggested_tags
            
            video_data.update({
                "processed_data": json.dumps({
                    "classification": classification.model_dump(),
                    "llm_prompt": processed_data.get('prompt', '')
                }),
                "recipe": recipe,
                "nutrition": None  # Don't calculate nutrition facts initially
            })
        else:
            video_data.update({
                "processed_data": json.dumps({
                    "classification": classification.model_dump_json()
                }),
                "recipe": None,
                "nutrition": None
            })

        # Store the processed data in Firebase
        FirebaseService.store_recipe(video_id, video_data)

        return VideoResponse(**video_data)

    except Exception as e:
        error_message = str(e)
        if "Sign in to confirm you're not a bot" in error_message:
            logger.error(f"YouTube bot detection triggered: {error_message}")
            raise HTTPException(
                status_code=429,
                detail="YouTube has detected automated access. Please try again later or provide authentication cookies."
            )
        logger.error(f"Error processing video: {error_message}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the video."
        )
        
@router.post("/nutrition/", response_model=NutritionResponse)
async def get_nutrition_facts(
    request: NutritionRequest,
    nutrition_service: NutritionServiceV2 = Depends()
):
    try:
        logger.info(f"Calculating nutrition facts for {len(request.ingredients)} ingredients")
        logger.info(f"Request: {request}")
        nutrition_response =  nutrition_service.calculate_nutrition(request.ingredients)
        logger.info(f"Nutrition Respinse: {nutrition_response}")
        
        # Log the response before returning
        logger.info("\nPer ingredient breakdown:")
        
        return nutrition_response
    except Exception as e:
        logger.error(f"Error calculating nutrition facts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while calculating nutrition facts"
        )
        
@router.get("/recipes/{user_id}")
async def get_user_recipes(
    user_id: str,
    firebase_service: FirebaseService = Depends()
):
    """
    Get all recipes for a specific user
    """
    try:
        # Get all recipes for the user from Firebase
        recipes = firebase_service.get_user_recipes(user_id)
        logger.info(f"Retrieved {len(recipes)} recipes from Firebase")
        
        if not recipes:
            return []

        return recipes
        
    except Exception as e:
        logger.error(f"Error fetching recipes for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching recipes for user {user_id}"
        )
        
        
@router.delete("/recipes/{user_id}/{video_id}") 
async def delete_user_recipe(
    user_id: str,
    video_id: str,
    firebase_service: FirebaseService = Depends()
):
    """
    Delete a recipe for a specific user
    """
    try:
        # Delete the recipe from Firebase
      
        logger.info(f"Deleted recipe {video_id} for user {user_id}")
        firebase_service.delete_recipe(user_id, video_id)
        return {"message": "Recipe deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting recipe {video_id} for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting recipe {video_id} for user {user_id}"
        )
    