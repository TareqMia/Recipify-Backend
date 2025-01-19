# api/routes.py
import json
import logging
import os
from datetime import datetime

import boto3
import dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from models.schemas import ContentCategory, VideoRequest, VideoResponse, VideoContent, NutritionRequest, NutritionLabel, NutritionIngredient, NutritionResponse
from services.recipe_service import RecipeService
from services.transcript_service import TranscriptService
from services.video_service import VideoService
from services.firebase_service import FirebaseService
from services.nutrition_service import NutritionService

from logger import logger
from pyinstrument import Profiler

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
    video_service: VideoService = Depends(),
    transcript_service: TranscriptService = Depends(),
    recipe_service: RecipeService = Depends(get_recipe_service),
    nutrition_service: NutritionService = Depends(),
):
    logger.info(f"Processing video URL: {video.url}")
    
    try:
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
                # Proceed to process the video anew

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

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the video."
        )
        
@router.post("/nutrition/", response_model=NutritionResponse)
def get_nutrition_facts(
    request: NutritionRequest,
    nutrition_service: NutritionService = Depends()
):
    try:
        logger.info(f"Calculating nutrition facts for {len(request.ingredients)} ingredients")
        nutrition_response = nutrition_service.calculate_nutrition(request.ingredients)
        
        # Log the response before returning
        logger.info("\n=== NUTRITION ENDPOINT RESPONSE ===")
        logger.info(f"Total calories: {nutrition_response.total.calories}")
        logger.info(f"Total protein: {nutrition_response.total.protein.amount}g")
        logger.info(f"Total fat: {nutrition_response.total.total_fat.amount}g")
        logger.info(f"Total carbs: {nutrition_response.total.total_carbohydrates.amount}g")
        logger.info("\nPer ingredient breakdown:")
        for ing in nutrition_response.ingredients:
            logger.info(f"\n{ing.ingredient.name}:")
            logger.info(f"  Calories: {ing.nutrition.calories}")
            logger.info(f"  Protein: {ing.nutrition.protein.amount}g")
            logger.info(f"  Fat: {ing.nutrition.total_fat.amount}g")
            logger.info(f"  Carbs: {ing.nutrition.total_carbohydrates.amount}g")
        
        # Print the raw response model
        logger.info("\nRaw response model:")
        logger.info(nutrition_response.model_dump_json(indent=2))
        
        return nutrition_response
    except Exception as e:
        logger.error(f"Error calculating nutrition facts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while calculating nutrition facts"
        )
        
    
        
    