import hashlib 
from core.firebase import db 
from typing import Dict, Any
from datetime import datetime
from fastapi import HTTPException
import logging

class FirebaseService: 
    
    @staticmethod 
    def hash_url(url: str) -> str: 
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    @staticmethod 
    def store_recipe(url: str, data: Dict[str, Any]): 
        try:
            document_id = FirebaseService.hash_url(url)
            document_ref = db.collection('recipes').document(document_id)
            document = document_ref.get() 
            
            if document.exists:
                return document_id
            
            data['created_at'] = datetime.now()
            data['video_url'] = url
            
            document_ref.set(data) 
            return document_id
        except Exception as e: 
            raise HTTPException(status_code=500, detail=f"Failed to store recipe: {str(e)}")
    
    @staticmethod
    def get_recipe(url: str) -> dict | None:
        document_id = FirebaseService.hash_url(url)
        document_ref = db.collection('recipes').document(document_id)
        document = document_ref.get()
        
        if document.exists:
            data = document.to_dict()
            # Keep 'created_at' as string to avoid serialization issues
            required_fields = ['video_id', 'title', 'description', 'transcript', 'created_at']
            if all(field in data for field in required_fields):
                return data
            else:
                logging.error(f"Cached data missing required fields: {data}")
                return None
        return None