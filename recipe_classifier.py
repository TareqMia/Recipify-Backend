from anthropic import AnthropicBedrock
import os
import json
import dotenv
import instructor
from pydantic import BaseModel, Field 
from enum import Enum
from typing import List, Optional 

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
    
def classify_video_content(video_content: VideoContent) -> RecipeClassification:
    """
    Analyze video content using Claude to determine if it's recipe-related.
    
    Args:
        video_content: VideoContent object containing title, description, and transcript
        
    Returns:
        RecipeClassification object with analysis results
    """
    analysis_prompt = f"""
    Please analyze this video content to determine if it's a recipe:
    
    TITLE: {video_content.title}
    
    DESCRIPTION: {video_content.description}
    
    TRANSCRIPT: {video_content.transcript}
    
    Determine if this is a recipe video by analyzing:
    1. Presence of ingredient lists
    2. Cooking instructions or steps
    3. Kitchen/cooking terminology
    4. Food-related terminology
    5. Teaching/instructional language related to food preparation
    """
    
    response = client.messages.create(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        max_tokens=1024,
        response_model=RecipeClassification,
        messages=[
            {
                "role": "system",
                "content": """You are a video content analyzer specializing in identifying recipe content.
                Look for key indicators like:
                - Lists of ingredients
                - Cooking instructions
                - Measurements and quantities
                - Cooking techniques
                - Kitchen equipment mentions
                - Food preparation terminology"""
            },
            {"role": "user", "content": analysis_prompt}
        ]
    )
    
    return response

# Example usage
def main():
    # Example video content
    sample_video = VideoContent(
        title="High Protein Kimchi Noodle Recipe #healthyrecipesY",
        description="Full recipe 🍝 ⇩ \n\nIngredients:\n- 1 tbsp Gochujang\n- 1 tbsp brown sugar\n- 1/2 tbsp Rice Vinegar\n- 1 tbsp Soy Sauce\n- 1 tbsp Gochugaru\n- 100g Kimchi\n- 30g Green Onion\n- 1 tbsp minced garlic\n- 100g Sempio korean high protein noodles (20g protein 360 calories)\n- 150g light canned tuna\nrecipe inspo: @__cookim_\n\nMakes 1 serving: 650 calories, 52g Protein, 105g Carbs, 4g Fat\n\nHow to make it yourself:\n1. Dice your green onions\n2. Cook the noodles in boiling water and once cooked, let it rest in cool water\n3. In a bowl, add your canned tuna, brown sugar, gochugaru, minced garlic, gochujang, kimchi, rice vinegar, soy sauce, the cooked noodles, and the diced green onions.\n\nI saw this recipe on my feed and knew making a few small changes would make this the perfect high protein and low calorie recipe!\n\n📩 Save this Spicy Tuna Noodle recipe to make for later and if you make it, post it and tag me in it! I’d love to see how you liked the recipe :)\n\n#highproteinmeals #lowcalorie #mealprep #weightlossmeals #healthyrecipes #koreanfood #asianfood #noodles",
        transcript="welcome back to i can't eat enough protein the series where i share with you tasty high protein dishes that take less than 30 minutes to make and today let's make korean kimchi noodles but packed with over 50 g of protein a few weeks ago i was scrolling through my for you page and stumbled upon a viral kimchi noodle recipe that looks so good and so easy to make that i knew i had to try it but i feel like i can take it one step further and turn it into a high protein dish that's perfect for our series these specific noodles from senel are 360 calories for 20 g of protein and they taste really good too so here instead of using regular old noodles i'm going to use these korean high protein noodles that are honestly such a hidden gem that i found at my local korean market we'll then pair that with some canant tuna since it's one of the leanest most convenient protein sources out there and goes perfect with these noodles and the kimchi as always the four recipes in the caption let me know what you think woo"
    )
    
    try:
        # Classify the video
        result = classify_video_content(sample_video)
        print(result.model_dump_json(indent=2))
        
        # Validate the results
        assert isinstance(result, RecipeClassification)
        if result.is_recipe == ContentCategory.recipe:
            print("\nRecipe detected!")
            print(f"Confidence Level: {result.confidence_level}")
            print(f"Confidence Score: {result.confidence_score}")
            print("\nRecipe Indicators:")
            for indicator in result.recipe_indicators:
                print(f"- {indicator}")
    
    except Exception as e:
        print(f"Error during classification: {str(e)}")

if __name__ == "__main__":
    main()
   
