import os
import re
from typing import List, Dict, Any, Tuple
import requests
from models.schemas import (
    NutritionIngredient, 
    NutritionLabel, 
    NutrientInfo,
    NutritionResponse,
    IngredientNutrition
)

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
        # Map common ingredients to specific search terms
        search_map = {
            'eggs': 'Egg, whole, raw, fresh',
            'avocado': 'Avocados, raw, all commercial varieties',
            'cottage cheese': 'Cheese, cottage, lowfat, 2% milkfat',
            'chile lime seasoning': 'Spices, chili powder',
            'everything bagel seasoning': 'Spices, sesame seeds',
            'hot sauce': 'Sauce, hot chile, sriracha',
        }
        
        # Use mapped search term if available
        search_query = search_map.get(query.lower(), query)
        
        endpoint = f"{self.base_url}/foods/search"
        params = {
            'api_key': self.api_key,
            'query': search_query,
            'dataType': ['Survey (FNDDS)', 'Foundation', 'SR Legacy'],
            'pageSize': 1
        }
        
        print(f"\n=== FOOD SEARCH REQUEST ===")
        print(f"Endpoint: {endpoint}")
        print(f"Query: {search_query}")
        print(f"Params: {params}")
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        result = response.json()
        
        print(f"\n=== FOOD SEARCH RESPONSE ===")
        print(f"Status Code: {response.status_code}")
        print(f"Foods found: {len(result.get('foods', []))}")
        if result.get('foods'):
            print(f"First food match: {result['foods'][0].get('description')}")
            print(f"Food ID: {result['foods'][0].get('fdcId')}")
        else:
            print("No foods found")
        
        return result
    
    def get_food_nutrients(self, fdc_id: str) -> Dict[str, Any]:
        """Get detailed nutrient information for a food item"""
        endpoint = f"{self.base_url}/food/{fdc_id}"
        params = {
            'api_key': self.api_key
        }
        
        print(f"\n=== NUTRIENT REQUEST ===")
        print(f"Endpoint: {endpoint}")
        print(f"Food ID: {fdc_id}")
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        result = response.json()
        
        print(f"\n=== NUTRIENT RESPONSE ===")
        print(f"Status Code: {response.status_code}")
        print(f"Raw nutrients: {result.get('foodNutrients', [])[:2]}...")  # Print first few nutrients
        print(f"Number of nutrients: {len(result.get('foodNutrients', []))}")
        
        # Extract nutrients we care about
        found_nutrients = {}
        for nutrient in result.get('foodNutrients', []):
            print(f"\nProcessing nutrient: {nutrient}")  # Print each nutrient being processed
            
            # Try different possible nutrient ID locations in the response
            nutrient_id = None
            amount = None
            
            # Handle different API response formats
            if 'nutrient' in nutrient:
                nutrient_id = nutrient['nutrient'].get('id')
                amount = nutrient.get('amount')
                print(f"Found nutrient ID from 'nutrient': {nutrient_id}, amount: {amount}")
            elif 'nutrientId' in nutrient:
                nutrient_id = nutrient['nutrientId']
                amount = nutrient.get('value')
                print(f"Found nutrient ID from 'nutrientId': {nutrient_id}, amount: {amount}")
            else:
                print("No nutrient ID found in this entry")
                continue
                
            if nutrient_id is None or amount is None:
                print("Missing nutrient ID or amount")
                continue
                
            # Convert nutrient ID to integer for comparison
            try:
                nutrient_id = int(nutrient_id)
                print(f"Converted nutrient ID to int: {nutrient_id}")
            except (ValueError, TypeError):
                print(f"Failed to convert nutrient ID to int: {nutrient_id}")
                continue
            
            # Map the nutrient to our format
            for our_key, fdc_id in self.nutrient_map.items():
                if nutrient_id == fdc_id:
                    found_nutrients[our_key] = amount
                    print(f"Mapped nutrient {nutrient_id} to {our_key} with amount {amount}")
                    break
        
        print("\nExtracted nutrients:")
        for key, value in found_nutrients.items():
            print(f"  {key}: {value}")
            
        return found_nutrients
    
    def convert_to_grams(self, amount: float, unit: str) -> float:
        """Convert various units to grams"""
        print(f"\n=== UNIT CONVERSION ===")
        print(f"Converting {amount} {unit} for {self.current_ingredient}")
        
        if amount is None:
            print("No amount specified, using default serving size")
            # Use smaller defaults for seasonings
            if 'seasoning' in self.current_ingredient.lower() or 'spice' in self.current_ingredient.lower():
                return 5  # 5g default for seasonings
            return 100  # Default serving size for other ingredients
            
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
            'tsp': 4.92892,
            'serving': {
                'cottage cheese': 113,  # 1/2 cup serving
                'hot sauce': 15,  # 1 tbsp serving
                'seasoning': 5,  # 1 tsp serving
                'default': 100
            },
            'whole': {
                'egg': 50,  # 50g per large egg
                'eggs': 50,
                'avocado': 170,  # 170g per medium avocado
                'onion': 110,  # 110g per medium onion
                'cilantro': 10,  # 10g per serving
            }
        }
        
        if not unit:
            # If no unit but ingredient is a known whole item, treat as 'whole'
            for item in conversion_factors['whole'].keys():
                if item in self.current_ingredient.lower():
                    print(f"No unit specified but found whole item match: {item}")
                    return amount * conversion_factors['whole'][item]
            
            # Use serving size for seasonings
            if 'seasoning' in self.current_ingredient.lower() or 'spice' in self.current_ingredient.lower():
                print("No unit specified for seasoning, using 5g serving")
                return amount * 5
                
            print("No unit specified, using default 100g")
            return amount * 100  # Default to 100g if no unit specified
            
        unit = unit.lower()
        
        # Handle whole items
        if unit == 'whole':
            for item, weight in conversion_factors['whole'].items():
                if item in self.current_ingredient.lower():
                    print(f"Converting whole {item} to {weight}g each")
                    return amount * weight
            print("Unknown whole item, using default 100g")
            return amount * 100  # Default if no specific weight found
            
        # Handle servings
        if unit == 'serving':
            for item, weight in conversion_factors['serving'].items():
                if item in self.current_ingredient.lower():
                    print(f"Converting serving of {item} to {weight}g")
                    return amount * weight
            return amount * conversion_factors['serving']['default']
            
        # Handle standard units
        if unit in conversion_factors:
            print(f"Converting {unit} to grams using factor: {conversion_factors[unit]}")
            return amount * conversion_factors[unit]
            
        print(f"Unknown unit {unit}, using default factor of 1")
        return amount * 1  # Default to 1 if unit not found
    
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

    def calculate_nutrition(self, ingredients: List[NutritionIngredient]) -> NutritionResponse:
        """Calculate nutrition facts for a list of ingredients"""
        print("\n=== STARTING NUTRITION CALCULATION ===")
        print(f"Number of ingredients: {len(ingredients)}")
        for i, ing in enumerate(ingredients, 1):
            print(f"{i}. {ing.name} - Amount: {ing.amount} {ing.unit or 'whole' if ing.amount else 'serving'}")
        
        ingredient_nutrients = []
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
                print(f"\n=== PROCESSING INGREDIENT: {ingredient.name} ===")
                print(f"Amount: {ingredient.amount} {ingredient.unit}")
                
                # Store current ingredient name for convert_to_grams
                self.current_ingredient = ingredient.name
                
                # Get clean ingredient name for API search
                clean_name = ingredient.get_clean_name()
                print(f"Clean name for search: {clean_name}")
                
                # Search for the ingredient in FDC
                search_result = self.search_food(clean_name)
                
                if not search_result.get('foods'):
                    print(f"\nTrying fallback search with original name: {ingredient.name}")
                    search_result = self.search_food(ingredient.name)
                    if not search_result.get('foods'):
                        print(f"No results found for either clean name or original name")
                        continue
                    
                food = search_result['foods'][0]
                print(f"Using food: {food.get('description')} (ID: {food.get('fdcId')})")
                
                # Get nutrients for this food
                nutrients = self.get_food_nutrients(food['fdcId'])
                print(f"\nRetrieved nutrients: {nutrients}")
                
                # Calculate amount in grams
                amount_in_grams = self.convert_to_grams(ingredient.amount, ingredient.unit)
                print(f"\nConverted amount: {amount_in_grams}g")
                
                total_weight += amount_in_grams
                
                # Calculate nutrients for this ingredient
                ingredient_nutrient_values = {}
                for nutrient_key in total_nutrients.keys():
                    if nutrient_key in nutrients:
                        # Convert nutrient amount from per 100g to actual amount
                        converted_amount = (nutrients[nutrient_key] * amount_in_grams) / 100
                        ingredient_nutrient_values[nutrient_key] = converted_amount
                        total_nutrients[nutrient_key] += converted_amount
                        print(f"  {nutrient_key}: {converted_amount}")
                    else:
                        print(f"  {nutrient_key}: not found in nutrients")
                        ingredient_nutrient_values[nutrient_key] = 0
                
                print(f"\nIngredient nutrient values: {ingredient_nutrient_values}")
                
                # Create nutrition label for this ingredient
                ingredient_label = NutritionLabel(
                    serving_size=NutrientInfo(amount=amount_in_grams, unit="g"),
                    calories=round(ingredient_nutrient_values.get('calories', 0), 1),
                    total_fat=NutrientInfo(amount=round(ingredient_nutrient_values.get('total_fat', 0), 1), unit="g"),
                    saturated_fat=NutrientInfo(amount=round(ingredient_nutrient_values.get('saturated_fat', 0), 1), unit="g"),
                    trans_fat=NutrientInfo(amount=round(ingredient_nutrient_values.get('trans_fat', 0), 1), unit="g"),
                    cholesterol=NutrientInfo(amount=round(ingredient_nutrient_values.get('cholesterol', 0), 1), unit="mg"),
                    sodium=NutrientInfo(amount=round(ingredient_nutrient_values.get('sodium', 0), 1), unit="mg"),
                    total_carbohydrates=NutrientInfo(amount=round(ingredient_nutrient_values.get('total_carbohydrates', 0), 1), unit="g"),
                    dietary_fiber=NutrientInfo(amount=round(ingredient_nutrient_values.get('dietary_fiber', 0), 1), unit="g"),
                    total_sugars=NutrientInfo(amount=round(ingredient_nutrient_values.get('total_sugars', 0), 1), unit="g"),
                    added_sugars=NutrientInfo(amount=round(ingredient_nutrient_values.get('added_sugars', 0), 1), unit="g"),
                    protein=NutrientInfo(amount=round(ingredient_nutrient_values.get('protein', 0), 1), unit="g"),
                    vitamin_d=NutrientInfo(amount=round(ingredient_nutrient_values.get('vitamin_d', 0), 1), unit="mcg"),
                    calcium=NutrientInfo(amount=round(ingredient_nutrient_values.get('calcium', 0), 1), unit="mg"),
                    iron=NutrientInfo(amount=round(ingredient_nutrient_values.get('iron', 0), 1), unit="mg"),
                    potassium=NutrientInfo(amount=round(ingredient_nutrient_values.get('potassium', 0), 1), unit="mg")
                )
                
                print(f"\nCreated ingredient label: {ingredient_label}")
                
                ingredient_nutrients.append(IngredientNutrition(
                    ingredient=ingredient,
                    nutrition=ingredient_label
                ))
                    
            except Exception as e:
                print(f"Error processing ingredient {ingredient.name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        print(f"\nTotal nutrients before final label: {total_nutrients}")
        
        # Create total nutrition label
        total_label = NutritionLabel(
            serving_size=NutrientInfo(amount=total_weight, unit="g"),
            calories=round(total_nutrients['calories'], 1),
            total_fat=NutrientInfo(amount=round(total_nutrients['total_fat'], 0), unit="g"),
            saturated_fat=NutrientInfo(amount=round(total_nutrients['saturated_fat'], 0), unit="g"),
            trans_fat=NutrientInfo(amount=round(total_nutrients['trans_fat'], 0), unit="g"),
            cholesterol=NutrientInfo(amount=round(total_nutrients['cholesterol'], 0), unit="mg"),
            sodium=NutrientInfo(amount=round(total_nutrients['sodium'], 0), unit="mg"),
            total_carbohydrates=NutrientInfo(amount=round(total_nutrients['total_carbohydrates'], 0), unit="g"),
            dietary_fiber=NutrientInfo(amount=round(total_nutrients['dietary_fiber'], 0), unit="g"),
            total_sugars=NutrientInfo(amount=round(total_nutrients['total_sugars'], 0), unit="g"),
            added_sugars=NutrientInfo(amount=round(total_nutrients['added_sugars'], 0), unit="g"),
            protein=NutrientInfo(amount=round(total_nutrients['protein'], 0), unit="g"),
            vitamin_d=NutrientInfo(amount=round(total_nutrients['vitamin_d'], 0), unit="mcg"),
            calcium=NutrientInfo(amount=round(total_nutrients['calcium'], 0), unit="mg"),
            iron=NutrientInfo(amount=round(total_nutrients['iron'], 0), unit="mg"),
            potassium=NutrientInfo(amount=round(total_nutrients['potassium'], 0), unit="mg")
        )
        
        response = NutritionResponse(
            ingredients=ingredient_nutrients,
            total=total_label
        )
        
        print("\n=== FINAL NUTRITION RESPONSE ===")
        print(f"Response object: {response}")
        print("\nIngredients:")
        for ing in response.ingredients:
            print(f"\n{ing.ingredient.name} ({ing.ingredient.amount} {ing.ingredient.unit or 'whole'}):")
            print(f"  Calories: {ing.nutrition.calories}")
            print(f"  Protein: {ing.nutrition.protein.amount}g")
            print(f"  Total Fat: {ing.nutrition.total_fat.amount}g")
            print(f"  Total Carbs: {ing.nutrition.total_carbohydrates.amount}g")
            
        print("\nTotal Nutrition:")
        print(f"Calories: {response.total.calories}")
        print(f"Protein: {response.total.protein.amount}g")
        print(f"Total Fat: {response.total.total_fat.amount}g")
        print(f"Total Carbs: {response.total.total_carbohydrates.amount}g")
        
        return response 