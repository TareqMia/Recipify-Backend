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
import re

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
    quantity: float
    unit: str
    

class Recipe(BaseModel):
    name: str
    instructions: List[str]
    ingredients: List[Ingredient]  # Eac    h ingredient is a dict with amount, unit, ingredient, and notes
    keywords: List[str]
    servings: int  # Changed from serving_size to servings
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
    
def parse_ingredient(ingredient_str, known_units=None, qualitative_amounts=None):

    # Define default known units (you can extend this set as needed)
    if known_units is None:
        known_units = {
            "oz", "tsp", "tbsp", "cup", "cups", "g", "kg", "lb", "ml", "l",
            "teaspoon", "teaspoons", "tablespoon", "tablespoons", "pinch", "can"
        }
    # Phrases that indicate a qualitative (non-numeric) quantity.
    if qualitative_amounts is None:
        qualitative_amounts = ["a pinch", "a handful", "to taste", "as needed"]

    # Initialize result dictionary.
    result = {"amount": "", "unit": "", "ingredient": "", "notes": ""}
    
    # Remove leading/trailing whitespace.
    ingredient_str = ingredient_str.strip()
    
    # --- 1. Extract Parenthetical Information (Notes) ---
    # e.g., in "5 oz (140 g) dark chocolate", extract "(140 g)"
    parenthetical_notes = re.findall(r'\(.*?\)', ingredient_str)
    if parenthetical_notes:
        # Join all parentheticals (if there are several) into the "notes" field.
        result["notes"] = " ".join(parenthetical_notes)
        # Remove parentheticals from the main string.
        ingredient_str = re.sub(r'\(.*?\)', '', ingredient_str).strip()
    
    # --- 2. Handle Cases With a Comma but No Numeric Quantity ---
    # e.g. "salt, to taste" or "fresh basil leaves, for garnish"
    numeric_amount_pattern = r'(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)'
    if not re.search(numeric_amount_pattern, ingredient_str) and ',' in ingredient_str:
        parts = [part.strip() for part in ingredient_str.split(',', 1)]
        result["ingredient"] = parts[0]
        if len(parts) > 1:
            # Append the comma portion to the notes.
            extra_note = parts[1]
            if result["notes"]:
                result["notes"] += " " + extra_note
            else:
                result["notes"] = extra_note
        return result

    # --- 3. Check for Qualitative Amounts at the Start ---
    # e.g., "a pinch of salt" or "a handful of basil"
    lower_str = ingredient_str.lower()
    for phrase in qualitative_amounts:
        if lower_str.startswith(phrase):
            result["amount"] = phrase
            # Remove the phrase (and an optional following "of") from the ingredient description.
            rem = ingredient_str[len(phrase):].strip()
            if rem.lower().startswith("of "):
                rem = rem[3:].strip()
            result["ingredient"] = rem
            return result

    # --- 4. Check for Range Quantities ---
    # e.g., "2-3 carrots" or "1 to 2 teaspoons vanilla extract"
    range_pattern = r'^(?P<amount>\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?)\s+(?P<rest>.+)$'
    m = re.match(range_pattern, ingredient_str)
    if m:
        result["amount"] = m.group("amount")
        rest_str = m.group("rest")
        tokens = rest_str.split()
        # If the first token of the remainder is a known unit, separate it.
        if tokens and tokens[0].lower() in known_units:
            result["unit"] = tokens[0]
            result["ingredient"] = " ".join(tokens[1:])
        else:
            result["ingredient"] = rest_str
        return result

    # --- 5. Try Numeric Patterns ---
    # Define a regex fragment for numeric amounts (including mixed fractions, simple fractions, or decimals)
    numeric_amount = r'(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)'
    
    # Pattern A: "amount unit ingredient"
    pattern_amount_first = re.compile(
        r'^\s*(?P<amount>' + numeric_amount + r')\s+'
        r'(?P<unit>\S+)?\s*'
        r'(?P<ingredient>.+)$'
    )
    # Pattern B: "unit amount ingredient" (e.g., "tsp 4 chicken")
    pattern_unit_first = re.compile(
        r'^\s*(?P<unit>\S+)\s+'
        r'(?P<amount>' + numeric_amount + r')\s+'
        r'(?P<ingredient>.+)$'
    )
    
    # Try Pattern B (unit first) first:
    m = pattern_unit_first.match(ingredient_str)
    if m:
        unit_candidate = m.group("unit")
        if unit_candidate.lower() in known_units:
            result["unit"] = unit_candidate
            result["amount"] = m.group("amount")
            result["ingredient"] = m.group("ingredient")
            return result
    
    # Next try Pattern A (amount first):
    m = pattern_amount_first.match(ingredient_str)
    if m:
        result["amount"] = m.group("amount")
        unit_candidate = m.group("unit") if m.group("unit") else ""
        # If the token following the amount is a known unit, use it.
        if unit_candidate and unit_candidate.lower() in known_units:
            result["unit"] = unit_candidate
            result["ingredient"] = m.group("ingredient")
        else:
            # Otherwise, treat that token as part of the ingredient description.
            if unit_candidate:
                result["ingredient"] = unit_candidate + " " + m.group("ingredient")
            else:
                result["ingredient"] = m.group("ingredient")
        return result

    # --- 6. Fallback ---
    # If nothing above matched, assume the entire string is the ingredient description.
    result["ingredient"] = ingredient_str
    return result
    
    
def classify_recipe_video_gemini(video_content: VideoContent) -> RecipeClassification:
    title = video_content.title[:100]
    description = video_content.description
    transcript = video_content.transcript
    
    
    analysis_prompt = f"""
    Analyze this cooking video content and extract recipe details IF IT IS A RECIPE. If not, return empty:

    Title: {title}
    Description: {description}
    Transcript excerpt: {transcript}
    
    Be descriptive when the instructions or transcript aren't too detailed (not too wordy).  
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
         
        # turn response.text into a json object
        data = json.loads(response.text) 
        return data
        
       
        
    except Exception as e:
        print(f"Error during video classification: {str(e)}")
        raise

