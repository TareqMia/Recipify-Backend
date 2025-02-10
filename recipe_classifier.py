from anthropic import AnthropicBedrock
import os
import json
import dotenv
from fastapi import logger
import instructor
from pydantic import BaseModel, Field 
from enum import Enum
from typing import List, Optional 
from google import genai

dotenv.load_dotenv()

anthropic_bedrock_client = AnthropicBedrock() 
client = instructor.from_anthropic(anthropic_bedrock_client) 

class ContentCategory(str, Enum):
    recipe = "recipe"
    not_a_recipe = "not_a_recipe"
    
class RecipeConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"  
    LOW = "LOW"
    
class Ingredient(BaseModel):
    name: str
    quantity: Optional[float]
    unit: Optional[str]
    notes: Optional[str]
    name_for_fdc_api: str
    substitute_ingredient: Optional[str]

class Recipe(BaseModel):
    recipe_name: str
    instructions: List[str]
    ingredients: List[Ingredient]
    keywords: List[str]
    serving_size: int
    serving_tips: List[str]
    
    # # Timing and difficulty
    prep_time: Optional[int]   # in minutes
    cook_time: Optional[int]   # in minutes
    total_time: Optional[int]  # in minutes
    difficulty: Optional[str]
    
    # # Cuisine and course
    cuisine: Optional[str]
    course: Optional[str]
    
    # # Allergen warnings and dietary tags
    allergens: List[str]
    dietary_tags: List[str]
    
    # # Additional descriptive fields
    description: Optional[str]
    
    # # Equipment or special instructions
    equipment: List[str]
    tips: List[str]
    
class VideoContent(BaseModel):
    title: str
    description: str
    transcript: str
    
    
class RecipeClassification(BaseModel):
    is_recipe: ContentCategory
    confidence_level: RecipeConfidenceLevel
    confidence_score: float = Field(ge=0, le=1)
    recipe_indicators: List[str] 
    suggested_tags: List[str] 
    recipe_details: Recipe
    
def classify_video_content(video_content: VideoContent) -> RecipeClassification:
    """Classify video content using Claude"""
    
    # Truncate content to fit within token limits
    title = video_content.title[:200]
    description = video_content.description
    transcript = video_content.transcript
    
    analysis_prompt = f"""
    Analyze this cooking video content and extract recipe details:

    Title: {title}
    Description: {description}
    Transcript excerpt: {transcript}

    Provide a structured response with these EXACT fields:
    - is_recipe: "recipe" if this is a recipe video, "not_a_recipe" if not
    - confidence_level: "HIGH", "MEDIUM", or "LOW"
    - confidence_score: A number between 0 and 1
    - recipe_indicators: List of phrases that indicate this is a recipe
    - suggested_tags: List of relevant tags
    - recipe_details: {{
        "name": Recipe name,
        "description": Brief description,
        "ingredients": List of ingredients with measurements,
        "instructions": List of numbered steps,
        "prep_time": Time in minutes (number),
        "cook_time": Time in minutes (number),
        "servings": Number of servings (number),
        "serving_suggestions": List of serving suggestions,
        "keywords": List of 2-5 relevant keywords
    }}

    Ensure ALL fields are present and properly formatted.
    """

    try:
        response = client.messages.create(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            max_tokens=4096,
            temperature=0.7,
            response_model=RecipeClassification,
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary expert who analyzes cooking videos and provides structured recipe classifications with ALL required fields."
                },
                {"role": "user", "content": analysis_prompt}
            ]
        )
        return response
    except Exception as e:
        print(f"Error during video classification: {str(e)}")
        raise
    
    
def classify_recipe_video_gemini(video_content: VideoContent) -> RecipeClassification:
    title = video_content.title[:100]
    description = video_content.description
    transcript = video_content.transcript
    
    
    analysis_prompt = f"""
    Analyze this cooking video content and extract recipe details IF IT IS A RECIPE. If not, return empty:

    Title: {title}
    Description: {description}
    Transcript excerpt: {transcript}
    
    """
    
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    
    try:
    
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=analysis_prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': RecipeClassification.model_json_schema()
            },
        )
        
        print("====================================")
        print(response)
        # turn response.text into a json object
        
        return json.loads(response.text)
        
       
        
    except Exception as e:
        print(f"Error during video classification: {str(e)}")
        raise

    

    

    
    
    
    
    



   
