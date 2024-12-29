import asyncio
import aiohttp
import json
from typing import List, Dict, Union
from dataclasses import dataclass

@dataclass
class Ingredient:
    name: str
    amount: float
    unit: str

class USDANutritionCalculator:
    def __init__(self, api_key: str, max_concurrent: int = 5):
        self.api_key = api_key
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.nutrient_ids = {
            'calories': 'Energy',
            'protein': 'Protein',
            'carbs': 'Carbohydrate, by difference',
            'fat': 'Total lipid (fat)',
            'fiber': 'Fiber, total dietary'
        }

    async def search_food(self, session: aiohttp.ClientSession, query: str) -> Dict:
        """Search for a food item in the USDA database."""
        async with self.semaphore:
            endpoint = f"{self.base_url}/foods/search"
            params = {
                "api_key": self.api_key,
                "query": query,
                "dataType": ["Survey (FNDDS)"],
                "pageSize": 1
            }
            
            async with session.get(endpoint, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def get_nutrients(self, session: aiohttp.ClientSession, food_id: int) -> Dict[str, float]:
        """Get nutritional information for a specific food ID."""
        async with self.semaphore:
            endpoint = f"{self.base_url}/food/{food_id}"
            params = {"api_key": self.api_key}
            
            async with session.get(endpoint, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
            nutrients = {name: 0.0 for name in self.nutrient_ids.keys()}
            
            for nutrient in data.get("foodNutrients", []):
                nutrient_name = nutrient.get("nutrient", {}).get("name")
                for key, value in self.nutrient_ids.items():
                    if value == nutrient_name:
                        nutrients[key] = nutrient.get("amount", 0)
                        
            return nutrients

    async def process_ingredient(self, session: aiohttp.ClientSession, ingredient: Ingredient) -> Dict:
        """Process a single ingredient to get its nutritional information."""
        try:
            # Search for the ingredient
            search_result = await self.search_food(session, ingredient.name)
            if not search_result.get("foods"):
                print(f"Warning: No results found for {ingredient.name}")
                return None
            
            food = search_result["foods"][0]
            food_id = food["fdcId"]
            
            # Get nutrients per 100g
            nutrients_per_100g = await self.get_nutrients(session, food_id)
            
            # Convert amount to grams if necessary
            amount_in_grams = self._convert_to_grams(ingredient.amount, ingredient.unit)
            
            # Calculate nutrients for this ingredient
            conversion_factor = amount_in_grams / 100
            ingredient_nutrients = {
                key: value * conversion_factor 
                for key, value in nutrients_per_100g.items()
            }
            
            return {
                "name": ingredient.name,
                "amount": ingredient.amount,
                "unit": ingredient.unit,
                "calories": round(ingredient_nutrients["calories"], 1),
                "protein": round(ingredient_nutrients["protein"], 1),
                "carbs": round(ingredient_nutrients["carbs"], 1),
                "fat": round(ingredient_nutrients["fat"], 1),
                "fiber": round(ingredient_nutrients["fiber"], 1)
            }
            
        except Exception as e:
            print(f"Error processing {ingredient.name}: {str(e)}")
            return None

    async def calculate_recipe_nutrition(self, ingredients: List[Ingredient]) -> Dict:
        """Calculate total nutrition for a list of ingredients using async requests."""
        async with aiohttp.ClientSession() as session:
            # Process all ingredients concurrently
            tasks = [self.process_ingredient(session, ingredient) for ingredient in ingredients]
            results = await asyncio.gather(*tasks)
            
            # Filter out None results and calculate totals
            results = [r for r in results if r is not None]
            
            recipe_details = {
                "total_calories": sum(item["calories"] for item in results),
                "total_protein": sum(item["protein"] for item in results),
                "total_carbs": sum(item["carbs"] for item in results),
                "total_fat": sum(item["fat"] for item in results),
                "total_fiber": sum(item["fiber"] for item in results),
                "ingredients": results
            }
            
            # Round totals
            for key in recipe_details:
                if key != "ingredients" and isinstance(recipe_details[key], (int, float)):
                    recipe_details[key] = round(recipe_details[key], 1)
                    
            return recipe_details

    def _convert_to_grams(self, amount: float, unit: str) -> float:
        """Convert common units to grams (simplified conversion)."""
        conversions = {
            "g": 1,
            "kg": 1000,
            "oz": 28.35,
            "lb": 453.59,
            "cup": 236.588,  # Assumes cup of water
            "tbsp": 14.787,
            "tsp": 4.929
        }
        
        unit = unit.lower()
        if not unit:  # Handle empty unit case
            return amount  # Assume grams if no unit specified
        
        if unit not in conversions:
            raise ValueError(f"Unsupported unit: {unit}")
            
        return amount * conversions[unit]

async def main():
    api_key = "54Xr2PlBppXtRnZiBNIseOGbRSgw6RQsQIfUR1b9"
    
    ingredients = [
        Ingredient("English cucumber", 1, "cup"),
        Ingredient("canned tuna", 170, "g"),
        Ingredient("light cream cheese", 1, "tbsp"),
        Ingredient("red onion", 0.25, "cup"),
        Ingredient("light mayonnaise", 2, "tbsp"),
        Ingredient("dill", 1, "tsp"),
        Ingredient("dijon mustard", 1, "tbsp"),
        Ingredient("black pepper", 1, "tsp"),
        Ingredient("lemon juice", 1, "tsp"),
        Ingredient("avocado", 0.5, "")
    ]
    
    calculator = USDANutritionCalculator(api_key)
    result = await calculator.calculate_recipe_nutrition(ingredients)
    
    print("\nRecipe Nutrition Breakdown:")
    print("-" * 60)
    print("Per Ingredient:")
    for item in result["ingredients"]:
        print(f"\n{item['name']} ({item['amount']} {item['unit']}):")
        print(f"  Calories: {item['calories']}kcal")
        print(f"  Protein: {item['protein']}g")
        print(f"  Carbs: {item['carbs']}g")
        print(f"  Fat: {item['fat']}g")
        print(f"  Fiber: {item['fiber']}g")
    
    print("\nTotals:")
    print("-" * 60)
    print(f"Total Calories: {result['total_calories']}kcal")
    print(f"Total Protein: {result['total_protein']}g")
    print(f"Total Carbs: {result['total_carbs']}g")
    print(f"Total Fat: {result['total_fat']}g")
    print(f"Total Fiber: {result['total_fiber']}g")

if __name__ == "__main__":
    asyncio.run(main())