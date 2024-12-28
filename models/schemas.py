from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime
from typing import List

class NutritionIngredient(BaseModel):
    name: str
    amount: Optional[float] = None
    unit: Optional[str] = None

class NutritionRequest(BaseModel):
    ingredients: List[NutritionIngredient]

class NutrientInfo(BaseModel):
    amount: float
    unit: str

class NutritionLabel(BaseModel):
    serving_size: NutrientInfo
    calories: float
    total_fat: NutrientInfo
    saturated_fat: NutrientInfo
    trans_fat: NutrientInfo
    cholesterol: NutrientInfo
    sodium: NutrientInfo
    total_carbohydrates: NutrientInfo
    dietary_fiber: NutrientInfo
    total_sugars: NutrientInfo
    added_sugars: NutrientInfo
    protein: NutrientInfo
    vitamin_d: NutrientInfo
    calcium: NutrientInfo
    iron: NutrientInfo
    potassium: NutrientInfo

class VideoRequest(BaseModel):
    url: str

    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v):
        pattern = r'^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(?:-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?$'
        
        match = re.search(pattern, v)
        if not match:
            raise ValueError("Invalid YouTube URL")
            
        # Video ID is in group 5 of the match
        video_id = match.group(5)
        return v
    
    
class Ingredient(BaseModel):
    item: str
    amount: Union[int, float]
    unit: Optional[str] = None

class Recipe(BaseModel):
    ingredients: List[Union[str, Dict[str, Union[str, int, float]], Ingredient]]
    instructions: List[str]
    preparation_time: Optional[int] = None
    cooking_time: Optional[int] = None
    servings: Optional[int] = None
    serving_suggestions: Optional[List[str]] = None
    keywords: Optional[List[str]] = []

    def __init__(self, **data):
        # Convert ingredient dictionaries to strings if needed
        if 'ingredients' in data:
            ingredients = []
            for ing in data['ingredients']:
                if isinstance(ing, dict):
                    # Format ingredient string based on available fields
                    amount = ing.get('amount', '')
                    unit = ing.get('unit', '')
                    item = ing.get('item', '')
                    ingredients.append(f"{amount} {unit} {item}".strip())
                else:
                    ingredients.append(ing)
            data['ingredients'] = ingredients
        super().__init__(**data)

    class Config:
        form_attributes = True

class VideoResponse(BaseModel):
    video_id: str
    title: str
    description: str
    transcript: str
    processed_data: Optional[str]
    is_recipe_video: bool
    recipe: Optional[Recipe]
    nutrition: Optional[NutritionLabel] = None
    created_at: datetime
    
class ContentCategory(str, Enum):
    recipe = "recipe"
    not_a_recipe = "not_a_recipe"
    
class RecipeConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"  
    LOW = "LOW"
    
class VideoContent(BaseModel):
    title: str
    description: str
    transcript: str
    
class RecipeClassification(BaseModel):
    is_recipe: ContentCategory
    confidence_level: RecipeConfidenceLevel
    confidence_score: float = Field(ge=0, le=1)
    recipe_indicators: List[str] = Field(
        description="Key phrases or elements that indicate recipe content"
    )
    suggested_tags: List[str] = Field(
        description="Suggested tags for the video content"
    )
    recipe_details: Optional[dict] = Field(
        description="If it's a recipe, extracted key recipe information",
        default=None
    )


