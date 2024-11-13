from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "YouTube Recipe API" 
    
    YDL_OPTIONS: dict = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash', 'comments', 'related_videos'],
            }
        },
        'default_search': 'error',
        'writeinfojson': False,
        'writesubtitles': False,
        'writethumbnail': False,
        'writedescription': False,
    }
    
    
    
settings = Settings()