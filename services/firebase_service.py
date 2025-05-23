import hashlib 
from core.firebase import db 
from typing import Dict, Any, List
from datetime import datetime
from fastapi import HTTPException
from logger import logger
from google.cloud import firestore

class FirebaseService: 
    
    @staticmethod 
    def hash_url(url: str) -> str: 
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    @staticmethod 
    def store_recipe(video_id: str, data: Dict[str, Any]): 
        try:
            document_id = video_id
            document_ref = db.collection('recipes').document(document_id)
            document = document_ref.get() 
            
            if document.exists:
                return document_id
            
            data['created_at'] = datetime.now()
            data['video_id'] = video_id
            
            document_ref.set(data) 
            return document_id
        
        except Exception as e: 
            raise HTTPException(status_code=500, detail=f"Failed to store recipe: {str(e)}")
    
    @staticmethod
    def get_recipe(video_id: str) -> dict | None:
        document_id = video_id
        document_ref = db.collection('recipes').document(document_id)
        document = document_ref.get()
        
        if document.exists:
            logger.info(f"Document exists: {document.id}")
            data = document.to_dict()
            # Keep 'created_at' as string to avoid serialization issues
            required_fields = ['video_id', 'title', 'description', 'transcript', 'created_at']
            if all(field in data for field in required_fields):
                return data
            else:
                logger.error(f"Cached data missing required fields: {data}")
                return None
        return None
    
    @staticmethod
    def get_user_recipes(user_id: str) -> List[dict]:
        """Get all recipes for a specific user"""
        logger.info(f"Fetching recipes for user: {user_id}")
        
        recipes = []
        recipes_ref = db.collection('user_recipes')
        query = recipes_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        for doc in query.stream():
            recipes.append(doc.to_dict())
            
        return recipes
    
    @staticmethod 
    def delete_recipe(user_id: str, video_id: str) -> None:
        """Delete a recipe for a specific user"""
        logger.info(f"Deleting recipe {video_id} for user {user_id}")
        
        recipe_ref = db.collection('user_recipes').document(f"{user_id}_{video_id}")
        recipe_ref.delete()
        
        return {"message": "Recipe deleted successfully"}
    
    @staticmethod 
    def get_user_cookbooks(user_id: str) -> List[dict]:
        """Get all cookbooks for a user

        Args:
            user_id (str): _description_

        Returns:
            List[dict]: _description_
        """
        
        logger.info(f"Fetching all cookbooks for user {user_id}")
        cookbooks = [] 
        cookbooks_ref = db.collection('cookbooks') 
        query = cookbooks_ref.where('owner_id', '==', user_id)
        
        for doc in query.stream():
            cookbooks.append(doc.to_dict())
            
        return cookbooks
            
        