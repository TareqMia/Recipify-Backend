import os
import re
from typing import List, Dict, Any, Optional
import requests
from decimal import Decimal
from fractions import Fraction
from models.schemas import (
    NutritionIngredient,
    NutritionLabel,
    NutrientInfo,
    NutritionResponse,
    IngredientNutrition
)

class NutritionServiceV2:
    def __init__(self):
        self.api_key = os.getenv('FDC_API_KEY')
        self.base_url = 'https://api.nal.usda.gov/fdc/v1'
        
        # FDC food mappings for common ingredients
        self.food_mappings = {
            'potatoes': '170026',  # Raw potato
            'water': '174858',     # Drinking water
            'salt': '173468',      # Table salt
            'baking soda': '171405', # Sodium bicarbonate
            'parmesan cheese': '171242', # Parmesan cheese
            'butter': '173430',    # Butter, unsalted
            'milk': '746782',      # Milk, whole
            'whole milk': '746782', # Milk, whole
            '2% milk': '746786',   # Milk, reduced fat (2%)
            '1% milk': '746784',   # Milk, low fat (1%)
            'skim milk': '746783', # Milk, nonfat
        }
        
        # Updated nutrient IDs based on latest FDC API
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

        # Density values for common liquids (g/ml)
        self.liquid_density = {
            'water': 1.0,
            'milk': 1.03,
            'olive oil': 0.92,
            'vegetable oil': 0.92,
            'honey': 1.42,
            'maple syrup': 1.37,
            'soy sauce': 1.1,
            'vinegar': 1.01,
            'default': 1.0
        }

        # Standard serving sizes in grams
        self.serving_sizes = {
            # Proteins
            'chicken breast': 85,  # 3 oz
            'salmon': 85,  # 3 oz
            'beef': 85,  # 3 oz
            'egg': 50,  # 1 large egg
            
            # Vegetables
            'potato': 150,  # 1 medium potato
            'potatoes': 150,  # 1 medium potato
            'onion': 110,  # 1 medium
            'tomato': 123,  # 1 medium
            'carrot': 61,  # 1 medium
            'lettuce': 47,  # 1 cup shredded
            'spinach': 30,  # 1 cup raw
            'avocado': 50,  # 1/3 medium
            
            # Dairy
            'cheese': 28,  # 1 oz
            'parmesan cheese': 5,  # 1 tbsp
            'butter': 14.2,  # 1 tbsp
            'milk': 244,  # 1 cup
            'yogurt': 170,  # 6 oz
            
            # Seasonings and Others
            'salt': 6,  # 1 tsp
            'pepper': 2,  # 1 tsp
            'herbs': 1,  # 1 tsp dried
            'spices': 2,  # 1 tsp
            'baking soda': 4.6,  # 1 tsp
            
            # Default
            'default': 30
        }

        # Volume to mass conversion (grams)
        self.volume_conversion = {
            'cup': 236.588,
            'tbsp': 14.787,
            'tsp': 4.929,
            'fl oz': 29.574,
            'ml': 1,
            'l': 1000,
            'pint': 473.176,
            'quart': 946.353,
            'gallon': 3785.41
        }

        # Weight conversion to grams
        self.weight_conversion = {
            'g': 1,
            'kg': 1000,
            'mg': 0.001,
            'oz': 28.3495,
            'lb': 453.592,
            'pound': 453.592
        }

    def parse_amount(self, amount_str: str) -> float:
        """Convert various amount formats to float"""
        if not amount_str:
            return 1.0

        # Remove any parentheses and their contents
        amount_str = re.sub(r'\([^)]*\)', '', amount_str).strip()

        # Handle mixed numbers (e.g., "1 1/2")
        parts = amount_str.split()
        if len(parts) == 2 and '/' in parts[1]:
            whole = float(parts[0])
            frac = float(Fraction(parts[1]))
            return whole + frac

        # Handle fractions
        if '/' in amount_str:
            return float(Fraction(amount_str))

        # Handle decimal numbers
        try:
            return float(amount_str)
        except ValueError:
            return 1.0

    def get_density_factor(self, ingredient: str) -> float:
        """Get density factor for liquid ingredients"""
        ingredient = ingredient.lower()
        for liquid, density in self.liquid_density.items():
            if liquid in ingredient:
                return density
        return self.liquid_density['default']

    def convert_to_grams(self, amount: float, unit: Optional[str], ingredient: str) -> float:
        """Convert ingredient amount to grams"""
        if not unit:
            # Check if it's a known ingredient with standard serving
            ingredient_lower = ingredient.lower()
            for known_ingredient, serving_size in self.serving_sizes.items():
                if known_ingredient in ingredient_lower:
                    return amount * serving_size
            return amount * self.serving_sizes['default']

        unit = unit.lower().strip()

        # Handle weight units
        if unit in self.weight_conversion:
            return amount * self.weight_conversion[unit]

        # Special handling for common ingredients with volume measurements
        ingredient_lower = ingredient.lower()
        
        # Handle volume units for specific ingredients
        if unit in self.volume_conversion:
            if ingredient_lower in ['water']:
                # Water: 1 cup = 236.588g (density of 1)
                return amount * self.volume_conversion[unit]
            elif ingredient_lower in ['salt', 'baking soda']:
                if unit == 'tsp':
                    return amount * self.serving_sizes[ingredient_lower]
                elif unit == 'tbsp':
                    return amount * (self.serving_sizes[ingredient_lower] * 3)
            elif ingredient_lower in ['butter', 'parmesan cheese']:
                if unit == 'tbsp':
                    return amount * self.serving_sizes[ingredient_lower]
                elif unit == 'cup':
                    return amount * (self.serving_sizes[ingredient_lower] * 16)
            elif 'potato' in ingredient_lower and unit == 'cup':
                return amount * 150  # 1 cup diced potato ≈ 150g
            else:
                # Default volume conversion
                volume_in_ml = amount * self.volume_conversion[unit]
                density = self.get_density_factor(ingredient)
                return volume_in_ml * density

        # Handle special cases
        if unit in ['pinch', 'dash']:
            return amount * 0.5  # Approximately 0.5g
        if unit == 'handful':
            return amount * 30  # Approximately 30g

        return amount * self.serving_sizes['default']

    def search_food(self, query: str) -> Dict[str, Any]:
        """Search for a food item in the FDC database with improved matching"""
        # Special case for water
        if query.lower() == 'water':
            return {
                'foods': [{
                    'fdcId': 'water',
                    'description': 'Water',
                    'dataType': 'Custom'
                }]
            }

        # First check if we have a direct mapping
        query_lower = query.lower()
        if query_lower in self.food_mappings:
            return {
                'foods': [{
                    'fdcId': self.food_mappings[query_lower],
                    'description': query,
                    'dataType': 'SR Legacy'
                }]
            }

        # Clean and standardize the query
        query = re.sub(r'\([^)]*\)', '', query)  # Remove parentheses and their contents
        query = query.strip()

        endpoint = f"{self.base_url}/foods/search"
        params = {
            'api_key': self.api_key,
            'query': query,
            'dataType': ['Survey (FNDDS)', 'Foundation', 'SR Legacy'],
            'pageSize': 25  # Increased to get more potential matches
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            result = response.json()

            if not result.get('foods'):
                return {'foods': []}

            # Score and sort results for better matching
            scored_foods = []
            query_words = set(query.lower().split())
            
            # Define scoring weights
            EXACT_MATCH_BONUS = 100
            WORD_MATCH_WEIGHT = 10
            LENGTH_PENALTY_WEIGHT = 2
            MODIFIER_PENALTY_WEIGHT = 15
            PREFERRED_CATEGORY_BONUS = 20
            BRAND_PENALTY = 10
            PREPARED_FOOD_PENALTY = 25  # New penalty for prepared foods
            
            for food in result['foods']:
                description = food['description'].lower()
                description_words = set(description.split())
                data_type = food.get('dataType', '').lower()
                
                # Initialize score components
                score = 0
                
                # 1. Exact match bonus
                if query_lower == description:
                    score += EXACT_MATCH_BONUS
                
                # 2. Word matching score
                matching_words = query_words.intersection(description_words)
                word_match_score = len(matching_words) * WORD_MATCH_WEIGHT
                # Extra points if matching words are in the same order
                if all(word in description for word in query_lower.split()):
                    word_match_score *= 1.5
                score += word_match_score
                
                # 3. Length penalty (prefer shorter, more specific descriptions)
                length_penalty = len(description_words) * LENGTH_PENALTY_WEIGHT
                score -= length_penalty
                
                # 4. Preferred data type bonus
                if data_type in ['sr legacy', 'foundation']:
                    score += PREFERRED_CATEGORY_BONUS
                
                # 5. Brand name penalty
                if 'brand' in data_type or 'branded' in data_type:
                    score -= BRAND_PENALTY
                
                # 6. Prepared food penalty - penalize items that are prepared dishes
                prepared_food_penalty = 0
                prepared_indicators = ['sandwich', 'dish', 'recipe', 'prepared', 'with', 'served', 'in', 'on']
                for indicator in prepared_indicators:
                    if indicator in description:
                        prepared_food_penalty += PREPARED_FOOD_PENALTY
                score -= prepared_food_penalty
                
                # 7. Modifier penalties for basic ingredients
                modifier_penalty = 0
                basic_ingredients = {
                    'milk': ['coconut', 'almond', 'soy', 'oat', 'rice', 'goat', 'flavored'],
                    'cheese': ['processed', 'food', 'product', 'substitute'],
                    'butter': ['substitute', 'spread', 'margarine'],
                    'cream': ['substitute', 'non-dairy', 'imitation'],
                    'oil': ['blend', 'substitute'],
                    'flour': ['blend', 'mix'],
                    'sugar': ['substitute', 'blend', 'artificial']
                }
                
                for basic_ing, modifiers in basic_ingredients.items():
                    if basic_ing in query_lower:
                        for modifier in modifiers:
                            if modifier in description and modifier not in query_lower:
                                modifier_penalty += MODIFIER_PENALTY_WEIGHT
                
                score -= modifier_penalty
                
                # 8. Preparation method matching
                prep_methods = ['raw', 'cooked', 'boiled', 'baked', 'fried', 'steamed', 'fresh']
                query_preps = [method for method in prep_methods if method in query_lower]
                desc_preps = [method for method in prep_methods if method in description]
                
                # Prefer items with matching preparation methods
                if query_preps and desc_preps:
                    if set(query_preps) == set(desc_preps):
                        score += 15
                elif not query_preps and 'raw' in description:
                    # If no prep method specified in query, prefer raw/fresh items
                    score += 10
                
                # Store detailed scoring for debugging
                scored_foods.append((score, {
                    'fdcId': food.get('fdcId'),
                    'description': food.get('description'),
                    'dataType': food.get('dataType'),
                    'score': score,
                    'score_breakdown': {
                        'word_match': word_match_score,
                        'length_penalty': length_penalty,
                        'modifier_penalty': modifier_penalty,
                        'prepared_food_penalty': prepared_food_penalty,
                        'data_type': data_type,
                        'matching_words': list(matching_words)
                    }
                }))

            # Sort by score in descending order
            scored_foods.sort(key=lambda x: x[0], reverse=True)
            
            # Print top matches for debugging
            print("\nTop 3 matches for", query)
            for score, food in scored_foods[:3]:
                print(f"Score {score:.1f}: {food['description']} ({food['dataType']})")
                print(f"Breakdown: {food['score_breakdown']}")
            
            # Return the best match if found
            if scored_foods:
                return {'foods': [scored_foods[0][1]]}
            return {'foods': []}
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching for food: {str(e)}")
            return {'foods': []}

    def get_food_nutrients(self, fdc_id: str) -> Dict[str, float]:
        """Get detailed nutrient information with improved error handling"""
        # Special case for water
        if fdc_id == 'water':
            return {
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

        endpoint = f"{self.base_url}/food/{fdc_id}"
        params = {'api_key': self.api_key}

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching nutrients: {str(e)}")
            return {}

        nutrients = {}
        for nutrient in result.get('foodNutrients', []):
            nutrient_id = None
            amount = None

            # Handle different API response formats
            if 'nutrient' in nutrient:
                nutrient_id = nutrient['nutrient'].get('id')
                amount = nutrient.get('amount')
            elif 'nutrientId' in nutrient:
                nutrient_id = nutrient['nutrientId']
                amount = nutrient.get('value')

            if nutrient_id is not None and amount is not None:
                try:
                    nutrient_id = int(nutrient_id)
                    for our_key, fdc_id in self.nutrient_map.items():
                        if nutrient_id == fdc_id:
                            nutrients[our_key] = float(amount)
                            break
                except (ValueError, TypeError):
                    continue

        return nutrients

    def parse_ingredient_string(self, ingredient_string: str) -> List[NutritionIngredient]:
        """Parse ingredient string with improved recognition of formats"""
        ingredients = []
        
        # Split by comma, handling parentheses
        items = re.findall(r'([^,()]+(?:\([^)]*\)[^,]*)?)', ingredient_string)
        
        for item in items:
            item = item.strip()
            if not item:
                continue

            # Enhanced regex pattern to catch more formats
            pattern = r'^((?:\d*\s*\d+/\d+|\d+(?:\.\d+)?)?)\s*((?:cup|tbsp|tsp|g|oz|lb|ml|l|pound|pinch|dash|handful)s?)?\s*(?:of\s+)?(.+)$'
            match = re.match(pattern, item, re.IGNORECASE)
            
            if match:
                amount_str, unit, name = match.groups()
                amount = self.parse_amount(amount_str) if amount_str else None
                
                ingredients.append(NutritionIngredient(
                    name=name.strip(),
                    amount=amount,
                    unit=unit.strip() if unit else None
                ))

        return ingredients

    def calculate_nutrition(self, ingredients: List[NutritionIngredient]) -> NutritionResponse:
        """Calculate nutrition facts with improved accuracy"""
        ingredient_nutrients = []
        ingredient_details = []  # New list to store detailed matching info
        total_nutrients = {key: 0 for key in self.nutrient_map.keys()}
        total_weight = 0

        print(f"\n=== Starting nutrition calculation for {len(ingredients)} ingredients ===")
        
        for ingredient in ingredients:
            try:
                print(f"\nProcessing ingredient: {ingredient.name}")
                
                # Convert amount to grams
                amount_in_grams = self.convert_to_grams(
                    ingredient.amount or 1.0,
                    ingredient.unit,
                    ingredient.name
                )
                print(f"Converted amount: {amount_in_grams}g")
                
                # Search for ingredient
                print(f"Searching for: {ingredient.name}")
                search_result = self.search_food(ingredient.name)
                if not search_result.get('foods'):
                    print(f"No food match found for: {ingredient.name}")
                    continue

                matched_food = search_result['foods'][0]
                print(f"Matched food: {matched_food.get('description')}")

                # Store detailed matching info
                ingredient_details.append({
                    'original_ingredient': ingredient.dict(),
                    'matched_food': matched_food.get('description'),
                    'matched_id': matched_food.get('fdcId'),
                    'data_type': matched_food.get('dataType'),
                    'converted_amount': amount_in_grams,
                    'original_amount': ingredient.amount,
                    'original_unit': ingredient.unit,
                })

                # Get nutrients
                nutrients = self.get_food_nutrients(str(matched_food['fdcId']))
                if not nutrients:
                    print(f"No nutrients found for: {ingredient.name}")
                    continue

                # Calculate ingredient nutrients
                ingredient_nutrient_values = {}
                for nutrient_key in total_nutrients.keys():
                    if nutrient_key in nutrients:
                        converted_amount = (nutrients[nutrient_key] * amount_in_grams) / 100
                        ingredient_nutrient_values[nutrient_key] = converted_amount
                        total_nutrients[nutrient_key] += converted_amount
                        print(f"  {nutrient_key}: {converted_amount}")

                total_weight += amount_in_grams

                # Create nutrition label for ingredient
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

                ingredient_nutrients.append(IngredientNutrition(
                    ingredient=ingredient,
                    nutrition=ingredient_label,
                    matched_food=matched_food.get('description'),
                    converted_amount=amount_in_grams
                ))
                print(f"Successfully processed {ingredient.name}")

            except Exception as e:
                print(f"Error processing ingredient {ingredient.name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue

        print(f"\nTotal nutrients calculated: {total_nutrients}")
        
        # Create total nutrition label
        total_label = NutritionLabel(
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

        return NutritionResponse(
            ingredients=ingredient_nutrients,
            total=total_label,
            ingredient_details=ingredient_details
        ) 