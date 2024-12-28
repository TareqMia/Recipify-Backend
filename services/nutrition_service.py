import os
import re
from typing import List, Dict, Any, Tuple
import requests
from models.schemas import NutritionIngredient, NutritionLabel, NutrientInfo

class NutritionService:
    def __init__(self):
        self.api_key = os.getenv('FDC_API_KEY')
        self.base_url = 'https://api.nal.usda.gov/fdc/v1'
        
        # FDC nutrient ID mapping
        self.nutrient_map = {
            'calories': 1008,        # Energy (kcal)
            'total_fat': 1004,       # Total lipids (fat)
            'saturated_fat': 1258,   # Fatty acids, total saturated
            'trans_fat': 1257,       # Fatty acids, total trans
            'cholesterol': 1253,     # Cholesterol
            'sodium': 1093,          # Sodium
            'total_carbohydrates': 1005,  # Carbohydrate, by difference
            'dietary_fiber': 1079,    # Fiber, total dietary
            'total_sugars': 2000,     # Sugars, total
            'added_sugars': 1235,     # Added Sugars
            'protein': 1003,          # Protein
            'vitamin_d': 1114,        # Vitamin D
            'calcium': 1087,          # Calcium
            'iron': 1089,             # Iron
            'potassium': 1092         # Potassium
        }
        
    def search_food(self, query: str) -> Dict[str, Any]:
        """Search for a food item in the FDC database"""
        endpoint = f"{self.base_url}/foods/search"
        params = {
            'api_key': self.api_key,
            'query': query,
            'dataType': ['Survey (FNDDS)'],
            'pageSize': 1
        }
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_food_nutrients(self, fdc_id: str) -> Dict[str, Any]:
        """Get detailed nutrient information for a food item"""
        endpoint = f"{self.base_url}/food/{fdc_id}"
        params = {
            'api_key': self.api_key
        }
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    def convert_to_grams(self, amount: float, unit: str) -> float:
        """Convert various units to grams"""
        conversion_factors = {
            'g': 1,
            'kg': 1000,
            'mg': 0.001,
            'oz': 28.3495,
            'lb': 453.592,
            'ml': 1,  # Assuming density of 1g/ml for liquids
            'l': 1000,
            'cup': 236.588,
            'tbsp': 14.7868,
            'tsp': 4.92892
        }
        
        unit = unit.lower()
        if unit not in conversion_factors:
            return amount  # Return original amount if unit not recognized
            
        return amount * conversion_factors[unit]
    
    def parse_ingredient_string(self, ingredient_string: str) -> List[NutritionIngredient]:
        """Parse a comma-separated ingredient string into individual ingredients"""
        ingredients = []
        
        # Split by comma
        items = [item.strip() for item in ingredient_string.split(',')]
        
        for item in items:
            # Parse amount and unit from item
            match = re.match(r'^((?:\d+(?:/\d+)?|\d*\.\d+)\s*(?:tsp|tbsp|cup|g|oz|lb|ml)?)?\s*(.+)$', item, re.IGNORECASE)
            if match:
                amount_unit, name = match.groups()
                
                if amount_unit:
                    # Parse fraction if present
                    amount_parts = amount_unit.strip().split()
                    amount_str = amount_parts[0]
                    unit = amount_parts[1] if len(amount_parts) > 1 else None
                    
                    # Convert fraction to decimal
                    if '/' in amount_str:
                        num, denom = amount_str.split('/')
                        amount = float(num) / float(denom)
                    else:
                        amount = float(amount_str)
                else:
                    amount = None
                    unit = None
                
                ingredients.append(NutritionIngredient(
                    name=name.strip(),
                    amount=amount,
                    unit=unit
                ))
        
        return ingredients

    def calculate_nutrition(self, ingredients: List[NutritionIngredient]) -> NutritionLabel:
        """Calculate nutrition facts for a list of ingredients"""
        total_nutrients = {
            'calories': 0,
            'total_fat': 0,
            'saturated_fat': 0,
            'trans_fat': 0,
            'cholesterol': 0,
            'sodium': 0,
            'total_carbohydrates': 0,
            'dietary_fiber': 0,
            'total_sugars': 0,
            'added_sugars': 0,
            'protein': 0,
            'vitamin_d': 0,
            'calcium': 0,
            'iron': 0,
            'potassium': 0
        }
        
        total_weight = 0
        
        for ingredient in ingredients:
            try:
                # If the ingredient name contains commas, it might be multiple ingredients
                if ',' in ingredient.name:
                    parsed_ingredients = self.parse_ingredient_string(ingredient.name)
                    for parsed_ing in parsed_ingredients:
                        self._process_single_ingredient(parsed_ing, total_nutrients, total_weight)
                else:
                    self._process_single_ingredient(ingredient, total_nutrients, total_weight)
                    
            except Exception as e:
                print(f"Error processing ingredient {ingredient.name}: {str(e)}")
                continue
        
        # Create and return the nutrition label
        return NutritionLabel(
            serving_size=NutrientInfo(amount=total_weight, unit="g"),
            calories=round(total_nutrients['calories'], 1),
            total_fat=NutrientInfo(amount=round(total_nutrients['total_fat'], 1), unit="g"),
            saturated_fat=NutrientInfo(amount=round(total_nutrients['saturated_fat'], 1), unit="g"),
            trans_fat=NutrientInfo(amount=round(total_nutrients['trans_fat'], 1), unit="g"),
            cholesterol=NutrientInfo(amount=round(total_nutrients['cholesterol'], 1), unit="mg"),
            sodium=NutrientInfo(amount=round(total_nutrients['sodium'], 1), unit="mg"),
            total_carbohydrates=NutrientInfo(amount=round(total_nutrients['total_carbohydrates'], 1), unit="g"),
            dietary_fiber=NutrientInfo(amount=round(total_nutrients['dietary_fiber'], 1), unit="g"),
            total_sugars=NutrientInfo(amount=round(total_nutrients['total_sugars'], 1), unit="g"),
            added_sugars=NutrientInfo(amount=round(total_nutrients['added_sugars'], 1), unit="g"),
            protein=NutrientInfo(amount=round(total_nutrients['protein'], 1), unit="g"),
            vitamin_d=NutrientInfo(amount=round(total_nutrients['vitamin_d'], 1), unit="mcg"),
            calcium=NutrientInfo(amount=round(total_nutrients['calcium'], 1), unit="mg"),
            iron=NutrientInfo(amount=round(total_nutrients['iron'], 1), unit="mg"),
            potassium=NutrientInfo(amount=round(total_nutrients['potassium'], 1), unit="mg")
        ) 

    def _process_single_ingredient(self, ingredient: NutritionIngredient, total_nutrients: Dict[str, float], total_weight: float):
        """Process a single ingredient and update the total nutrients"""
        # Search for the ingredient in FDC
        search_result = self.search_food(ingredient.name)
        
        if not search_result.get('foods'):
            print(f"No results found for ingredient: {ingredient.name}")
            return
            
        food = search_result['foods'][0]
        nutrients = self.get_food_nutrients(food['fdcId'])
        
        # Get serving size information
        serving_size = None
        portions = nutrients.get('foodPortions', [])
        if portions:
            for portion in portions:
                if portion.get('measureUnit', {}).get('name', '').lower() in ['serving', 'piece', 'cup']:
                    serving_size = portion
                    break
            if not serving_size:
                serving_size = portions[0]
        
        # Calculate amount in grams
        if ingredient.amount and ingredient.unit:
            amount_in_grams = self.convert_to_grams(ingredient.amount, ingredient.unit)
        elif serving_size:
            amount_in_grams = serving_size.get('gramWeight', 100)
        else:
            amount_in_grams = 100
        
        total_weight += amount_in_grams
        
        # Process nutrients
        for nutrient in nutrients.get('foodNutrients', []):
            nutrient_id = nutrient.get('nutrient', {}).get('id')
            amount = nutrient.get('amount', 0)
            
            for our_key, fdc_id in self.nutrient_map.items():
                if nutrient_id == fdc_id:
                    converted_amount = (amount * amount_in_grams) / 100
                    total_nutrients[our_key] += converted_amount
                    break 