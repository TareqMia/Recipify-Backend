from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re
from datetime import datetime
from typing import List

class NutrientInfo(BaseModel):
    amount: float
    unit: str

class NutritionIngredient(BaseModel):
    name: str
    amount: Optional[float] = None
    unit: Optional[str] = None

    @field_validator('amount', mode='before')
    @classmethod
    def parse_amount(cls, v):
        if isinstance(v, str):
            # Extract number from string like '170g'
            match = re.match(r'(\d+(?:\.\d+)?)', v)
            if match:
                return float(match.group(1))
        return v

    @field_validator('unit', mode='before')
    @classmethod
    def parse_unit(cls, v):
        if isinstance(v, str) and any(c.isalpha() for c in v):
            # Extract unit from string like '170g'
            match = re.match(r'\d+(?:\.\d+)?(\w+)', v)
            if match:
                return match.group(1)
        return v

class NutritionRequest(BaseModel):
    ingredients: List[NutritionIngredient]
    serving_size: Optional[NutrientInfo] = Field(
        default_factory=lambda: NutrientInfo(amount=100.0, unit="g"),
        description="Desired serving size for the nutrition facts"
    )

class NutritionLabel(BaseModel):
    serving_size: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=100.0, unit="g"))
    calories: float = 0.0
    total_fat: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    saturated_fat: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    trans_fat: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    cholesterol: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mg"))
    sodium: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mg"))
    total_carbohydrates: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    dietary_fiber: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    total_sugars: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    added_sugars: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    protein: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="g"))
    vitamin_d: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mcg"))
    calcium: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mg"))
    iron: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mg"))
    potassium: NutrientInfo = Field(default_factory=lambda: NutrientInfo(amount=0.0, unit="mg"))

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
    
    
class MeasurementUnit(str, Enum):
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"
    CUP = "cup"
    TABLESPOON = "tbsp"
    TEASPOON = "tsp"
    OUNCE = "oz"
    POUND = "lb"
    PIECE = "piece"
    SERVING = "serving"
    PINCH = "pinch"
    NONE = ""

class RecipeIngredient(BaseModel):
    amount: float = 0
    unit: MeasurementUnit = MeasurementUnit.NONE
    ingredient: str

    @classmethod
    def from_string(cls, ingredient_str: str) -> 'RecipeIngredient':
        # Handle fractions and decimals
        fraction_pattern = r'(\d+/\d+|\d*\.?\d+)?\s*([a-zA-Z]+\s+)?(.+)'
        match = re.match(fraction_pattern, ingredient_str)
        
        if not match:
            return cls(amount=0, unit=MeasurementUnit.NONE, ingredient=ingredient_str.strip())
            
        amount_str, unit_str, ingredient = match.groups()
        
        # Convert fraction to float
        amount = 0
        if amount_str:
            if '/' in str(amount_str):
                num, denom = amount_str.split('/')
                amount = float(num) / float(denom)
            else:
                amount = float(amount_str)
                
        # Clean and validate unit
        unit = MeasurementUnit.NONE
        if unit_str:
            unit_str = unit_str.strip().lower()
            try:
                unit = MeasurementUnit(unit_str)
            except ValueError:
                # If unit is not valid, it might be part of the ingredient name
                ingredient = f"{unit_str} {ingredient}"
                
        # Clean ingredient text
        ingredient = ingredient.strip()
        ingredient = re.sub(r'\s*\([^)]*\)', '', ingredient)  # Remove parenthetical notes
        
        return cls(
            amount=amount,
            unit=unit,
            ingredient=ingredient.strip()
        )

class Recipe(BaseModel):
    ingredients: List[Union[str, Dict[str, Any], RecipeIngredient]]
    instructions: List[str]
    preparation_time: Optional[int] = None
    cooking_time: Optional[int] = None
    servings: Optional[int] = None
    serving_size: Optional[NutrientInfo] = Field(
        default_factory=lambda: NutrientInfo(amount=100.0, unit="g"),
        description="Serving size for the recipe"
    )
    serving_suggestions: Optional[List[str]] = None
    keywords: Optional[List[str]] = []

    @field_validator('ingredients')
    @classmethod
    def validate_ingredients(cls, v):
        if not isinstance(v, list):
            raise ValueError("Ingredients must be a list")
            
        formatted_ingredients = []
        for ing in v:
            if isinstance(ing, RecipeIngredient):
                formatted = ing
            elif isinstance(ing, dict):
                try:
                    formatted = RecipeIngredient(
                        amount=float(ing.get("amount", 0)),
                        unit=ing.get("unit", MeasurementUnit.NONE),
                        ingredient=ing.get("ingredient", ing.get("item", ""))
                    )
                except (ValueError, TypeError):
                    # If conversion fails, treat as a string
                    formatted = RecipeIngredient.from_string(str(ing))
            elif isinstance(ing, str):
                formatted = RecipeIngredient.from_string(ing)
            else:
                formatted = RecipeIngredient.from_string(str(ing))
                
            formatted_ingredients.append(formatted)
        return formatted_ingredients

    model_config = ConfigDict(from_attributes=True)

class IngredientNutrition(BaseModel):
    ingredient: NutritionIngredient
    nutrition: Optional[NutritionLabel] = None

class NutritionResponse(BaseModel):
    ingredients: Optional[List[IngredientNutrition]] = []
    total: Optional[NutritionLabel] = None

class VideoResponse(BaseModel):
    video_id: str
    title: str
    description: str
    transcript: str
    processed_data: Optional[str]
    is_recipe_video: bool
    recipe: Optional[Recipe]
    nutrition: Optional[NutritionResponse] = None
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


