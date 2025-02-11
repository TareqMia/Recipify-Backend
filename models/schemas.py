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

    def get_clean_name(self) -> str:
        """Get clean ingredient name for API search"""
        # Remove amounts and units if present at start
        name = re.sub(r'^\d+/\d+|\d*\.?\d+\s*[a-zA-Z]*\s+', '', self.name)
        # Remove content in parentheses
        name = re.sub(r'\s*\([^)]*\)', '', name)
        # Remove common prep instructions
        name = re.sub(r'\b(chopped|diced|sliced|minced|thinly|fresh)\b', '', name, flags=re.IGNORECASE)
        return name.strip()

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
    # Weight units
    GRAM = "g"
    KILOGRAM = "kg"
    OUNCE = "oz"
    POUND = "lb"
    
    # Volume units
    MILLILITER = "ml"
    LITER = "l"
    CUP = "cup"
    TABLESPOON = "tbsp"
    TEASPOON = "tsp"
    
    # Count units
    WHOLE = "whole"
    PIECE = "piece"
    SERVING = "serving"
    
    # Small amounts
    PINCH = "pinch"
    
    # Empty
    NONE = ""

    @classmethod
    def get_weight_in_grams(cls, amount: float, unit: str, ingredient_name: str = "") -> float:
        """Convert a unit to grams for nutrition calculation"""
        # Common ingredient weights
        ingredient_weights = {
            "egg": 50,  # 50g per large egg
            "eggs": 50,  # 50g per large egg
            "avocado": 170,  # 170g per medium avocado
            "onion": 110,  # 110g per medium onion
            "cottage cheese": 226,  # 226g per cup/serving of cottage cheese
        }

        # First check if this is a common ingredient with known weight
        ingredient_name = ingredient_name.lower()
        for item, weight in ingredient_weights.items():
            if item in ingredient_name:
                return amount * weight

        # If not a common ingredient, use unit conversion
        conversion_map = {
            cls.GRAM: 1,
            cls.KILOGRAM: 1000,
            cls.OUNCE: 28.3495,
            cls.POUND: 453.592,
            cls.MILLILITER: 1,
            cls.LITER: 1000,
            cls.CUP: 236.588,
            cls.TABLESPOON: 14.7868,
            cls.TEASPOON: 4.92892,
            cls.SERVING: 100,
            cls.PINCH: 0.5,
            cls.NONE: 100,  # Default to 100g if no unit specified
        }
        
        return amount * conversion_map.get(unit, 100)

class RecipeIngredient(BaseModel):
    amount: float
    unit: MeasurementUnit 
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
                
        # Clean ingredient text
        ingredient = ingredient.strip()
        ingredient = re.sub(r'\s*\([^)]*\)', '', ingredient)  # Remove parenthetical notes
        
        # Clean and validate unit
        unit = MeasurementUnit.NONE
        if unit_str:
            unit_str = unit_str.strip().lower()
            try:
                unit = MeasurementUnit(unit_str)
            except ValueError:
                # If unit is not valid, it might be part of the ingredient name
                ingredient = f"{unit_str} {ingredient}"
                
        return cls(
            amount=amount,
            unit=unit,
            ingredient=ingredient.strip()
        )

    def get_weight_in_grams(self) -> float:
        """Get the weight of this ingredient in grams"""
        return MeasurementUnit.get_weight_in_grams(self.amount, self.unit, self.ingredient)

class Recipe(BaseModel):
    name: str
    description: str
    ingredients: List[RecipeIngredient]  # List of ingredients with measurements
    instructions: List[str]  # List of step-by-step instructions
    prep_time: int  # In minutes
    cook_time: int  # In minutes
    servings: int
    serving_suggestions: Optional[List[str]] = []
    keywords: List[str] = []
    
    # Additional fields
    cuisine: Optional[str] = None
    course: Optional[str] = None
    difficulty: Optional[str] = None
    allergens: Optional[List[str]] = []
    dietary_tags: Optional[List[str]] = []
    equipment: Optional[List[str]] = []
    tips: Optional[List[str]] = []
    total_time: Optional[int] = None  # in minutes
    ingredient_substitutions: Optional[Dict[str, str]] = {}  # ingredient -> substitute mapping

    @field_validator('ingredients')
    @classmethod
    def validate_ingredients(cls, v):
        if not isinstance(v, list):
            raise ValueError("Ingredients must be a list")
            
        formatted_ingredients = []
        for ing in v:
            if isinstance(ing, RecipeIngredient):
                # Convert RecipeIngredient to string
                parts = []
                if ing.amount > 0:
                    parts.append(str(ing.amount))
                if ing.unit != MeasurementUnit.NONE:
                    parts.append(str(ing.unit))
                parts.append(ing.ingredient)
                formatted_ingredients.append(" ".join(parts).strip())
            elif isinstance(ing, dict):
                try:
                    # Create RecipeIngredient and convert to string
                    recipe_ing = RecipeIngredient(
                        amount=float(ing.get("amount", 0)),
                        unit=ing.get("unit", MeasurementUnit.NONE),
                        ingredient=ing.get("ingredient", ing.get("item", ""))
                    )
                    parts = []
                    if recipe_ing.amount > 0:
                        parts.append(str(recipe_ing.amount))
                    if recipe_ing.unit != MeasurementUnit.NONE:
                        parts.append(str(recipe_ing.unit))
                    parts.append(recipe_ing.ingredient)
                    formatted_ingredients.append(" ".join(parts).strip())
                except (ValueError, TypeError):
                    # If conversion fails, use string as is
                    formatted_ingredients.append(str(ing))
            elif isinstance(ing, str):
                formatted_ingredients.append(ing)
            else:
                formatted_ingredients.append(str(ing))
                
        return formatted_ingredients

    model_config = ConfigDict(from_attributes=True)

class IngredientNutrition(BaseModel):
    ingredient: NutritionIngredient
    nutrition: Optional[NutritionLabel] = None
    matched_food: Optional[str] = None  # Store the matched food description
    converted_amount: Optional[float] = None  # Store the converted amount in grams

class NutritionResponse(BaseModel):
    ingredients: Optional[List[IngredientNutrition]] = []
    total: Optional[NutritionLabel] = None
    ingredient_details: Optional[List[Dict[str, Any]]] = []  # Store detailed ingredient matching info

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


