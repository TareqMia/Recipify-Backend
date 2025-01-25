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
        description="If it's a recipe, extracted key recipe information such as ingredients, instructions, etc.",
        default=None
    )
    
def classify_video_content(video_content: VideoContent) -> RecipeClassification:
    """Classify video content using Claude"""
    
    # Truncate content to fit within token limits
    title = video_content.title[:200]
    description = video_content.description[:500]
    transcript = video_content.transcript[:2000]
    
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
        "keywords": List of 2-3 relevant keywords
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
        logger.error(f"Error during video classification: {str(e)}")
        raise

# Example usage
def main():
    # Example video content
    sample_video = VideoContent(
        title="High Protein Kimchi Noodle Recipe #healthyrecipesY",
        description="Full recipe 🍝 ⇩ \n\nIngredients:\n- 1 tbsp Gochujang\n- 1 tbsp brown sugar\n- 1/2 tbsp Rice Vinegar\n- 1 tbsp Soy Sauce\n- 1 tbsp Gochugaru\n- 100g Kimchi\n- 30g Green Onion\n- 1 tbsp minced garlic\n- 100g Sempio korean high protein noodles (20g protein 360 calories)\n- 150g light canned tuna\nrecipe inspo: @__cookim_\n\nMakes 1 serving: 650 calories, 52g Protein, 105g Carbs, 4g Fat\n\nHow to make it yourself:\n1. Dice your green onions\n2. Cook the noodles in boiling water and once cooked, let it rest in cool water\n3. In a bowl, add your canned tuna, brown sugar, gochugaru, minced garlic, gochujang, kimchi, rice vinegar, soy sauce, the cooked noodles, and the diced green onions.\n\nI saw this recipe on my feed and knew making a few small changes would make this the perfect high protein and low calorie recipe!\n\n📩 Save this Spicy Tuna Noodle recipe to make for later and if you make it, post it and tag me in it! I'd love to see how you liked the recipe :)\n\n#highproteinmeals #lowcalorie #mealprep #weightlossmeals #healthyrecipes #koreanfood #asianfood #noodles",
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
   
