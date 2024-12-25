import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime

def export_recipes_to_json():
    """
    Connects to Firebase Firestore, retrieves all documents from the 'recipes' collection,
    and exports them to a JSON file named 'recipes.json'.
    """

    # Path to your Firebase service account key
    service_account_path = 'recipify-9e8e7-firebase-adminsdk-ocdn4-64a5bd2b68.json'

    # Initialize Firebase app
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        print("Firebase app already initialized.")

    db = firestore.client()

    # Reference to the 'recipes' collection
    recipes_ref = db.collection('recipes')

    try:
        # Fetch all documents in the 'recipes' collection
        docs = recipes_ref.stream()

        recipes = {}
        for doc in docs:
            recipes[doc.id] = doc.to_dict()

        # Specify the output JSON file path
        output_file = 'recipes.json'

        # Custom function to handle non-serializable objects
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        # Write the data to the JSON file with custom serialization
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=4, default=serialize)

        print(f"Successfully exported recipes to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    export_recipes_to_json() 