import json
import boto3
import os
import dotenv
import logging

dotenv.load_dotenv()

def call_llama_model(prompt, max_tokens=400, temperature=0.7):
    """
    Call the Llama 3 model through Amazon Bedrock.
    
    Args:
        prompt (str): The input prompt for the model
        max_tokens (int): Maximum number of tokens to generate
        temperature (float): Controls randomness in the output (0.0 to 1.0)
        
    Returns:
        str: The model's response text
    """
    try:
        bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        # Prepare the request body
        request_body = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
        }

        # Make the API call using the ARN
        response = bedrock_client.invoke_model(
            modelId='arn:aws:bedrock:us-east-1:060795930312:inference-profile/us.meta.llama3-2-1b-instruct-v1:0',
            body=json.dumps(request_body)
        )

        # Parse the response
        response_body = json.loads(response['body'].read())
        return response_body['generation']
    except Exception as e:
        logging.error(f"Error calling the model: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    test_prompt = "Explain quantum computing in simple terms."
    try:
        response = call_llama_model(test_prompt)
        print("Model Response:", response)
    except Exception as e:
        print(f"Error calling the model: {str(e)}")