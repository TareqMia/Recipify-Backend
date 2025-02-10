import logging
from typing import Optional, Tuple
import instructor
from anthropic import AnthropicBedrock
from pydantic import ValidationError

from models.schemas import Recipe, VideoContent, RecipeClassification
from recipe_classifier import classify_video_content, classify_recipe_video_gemini
from cohere import Client 

# Initialize the Anthropic client globally
anthropic_bedrock_client = AnthropicBedrock()
client = instructor.from_anthropic(anthropic_bedrock_client)

class RecipeService:
    def __init__(self):
        """
        Initialize RecipeService using the global client.
        """
        self.client = client

    def classify_video_content(self, video_content: VideoContent) -> RecipeClassification:
        """
        Use the classification method from recipe_classifier.py.
        
        Args:
            video_content: VideoContent object containing title, description, and transcript
            
        Returns:
            RecipeClassification object with analysis results
        """
        try:
            #classification = classify_video_content(video_content)
            classification = classify_recipe_video_gemini(video_content)
            logging.info("Successfully classified video content")
            return classification
        except Exception as e:
            print(f"Error during video classification: {str(e)}")
            raise

    async def generate_recipe(self, video_url: str, prompt: str) -> Optional[Recipe]:
        """
        Generate a recipe using Claude based on the provided prompt.
        """
        # Truncate prompt content
        truncated_prompt = prompt[:3000]  # Limit prompt length
        
        analysis_prompt = f"""
        Based on this content, generate a recipe in the following EXACT format:

        {truncated_prompt}

        Your response MUST include ALL these fields in a structured format:
        - name: The recipe name
        - description: A brief description
        - ingredients: A list of ingredients with measurements
        - instructions: A numbered list of cooking steps
        - prep_time: Preparation time in minutes (just the number)
        - cook_time: Cooking time in minutes (just the number)
        - servings: Number of servings (just the number)
        - serving_suggestions: [Optional] List of serving suggestions
        - keywords: List of 2-3 relevant recipe tags

        Ensure ALL fields are present and properly formatted.
        """

        try:
            logging.info(f"Generating recipe for video URL: {video_url}")
            
            response = self.client.messages.create(
                model="anthropic.claude-3-haiku-20240307-v1:0",
                max_tokens=4096,
                temperature=0.7,
                response_model=Recipe,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a culinary expert who creates recipes. 
                        Always include all required fields: name, description, ingredients (list), 
                        instructions (list), prep_time (number), cook_time (number), servings (number), 
                        serving_suggestions (list), and keywords (list)."""
                    },
                    {"role": "user", "content": analysis_prompt}
                ]
            )

            # Validate the response structure
            if not isinstance(response.ingredients, list) or not isinstance(response.instructions, list):
                logging.error("Invalid response structure - missing required lists")
                return None

            logging.info(f"Recipe generated successfully for video URL: {video_url}")
            return response

        except ValidationError as ve:
            logging.error(f"Validation error while parsing Recipe: {ve}")
            return None
        except Exception as e:
            logging.error(f"Error generating recipe: {str(e)}")
            return None
        