import hashlib 
from core.firebase import db 
from typing import Dict, Any
from datetime import datetime
from fastapi import HTTPException
from logger import logger

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