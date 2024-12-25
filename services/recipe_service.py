import logging
from typing import Optional, Tuple
import instructor
from anthropic import AnthropicBedrock
from pydantic import ValidationError

from models.schemas import Recipe, VideoContent, RecipeClassification
from recipe_classifier import classify_video_content
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
            classification = classify_video_content(video_content)
            logging.info("Successfully classified video content")
            return classification
        except Exception as e:
            logging.error(f"Error during video classification: {str(e)}")
            raise

    async def generate_recipe(self, video_url: str, prompt: str) -> Optional[Recipe]:
        """
        Generate a recipe using Claude based on the provided prompt.
        
        Args:
            video_url: The URL of the video being processed
            prompt: The prompt generated from the video content
            
        Returns:
            Recipe object if generation is successful, else None
        """
        analysis_prompt = f"""
        Generate a detailed recipe based on the following information:

        {prompt}

        Ensure the recipe includes:
        - Ingredients list with measurements
        - Step-by-step cooking instructions
        - Estimated preparation and cooking time
        - Serving suggestions
        - Keywords for the recipe
        """

        try:
            logging.info(f"Generating recipe for video URL: {video_url}")
            
            response = self.client.messages.create(
                model="anthropic.claude-3-haiku-20240307-v1:0",
                max_tokens=1024,
                response_model=Recipe,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a culinary expert specializing in creating detailed and easy-to-follow recipes based on provided information."""
                    },
                    {"role": "user", "content": analysis_prompt}
                ]
            )

            logging.info(f"Recipe generated successfully for video URL: {video_url}")
            return response

        except ValidationError as ve:
            logging.error(f"Validation error while parsing Recipe: {ve}")
            return None
        except Exception as e:
            logging.error(f"Error generating recipe: {str(e)}")
            return None
        