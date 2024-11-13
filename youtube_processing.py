from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_info(url):
    """
    Quickly extract title and description from a YouTube video URL
    
    Args:
        url (str): YouTube video URL
        
    Returns:
        tuple: (title, description) of the video
    """
    # Configure yt-dlp options for maximum speed
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        # Only request specific metadata fields
        'skip_download': True,
        # Specify exactly which fields to extract
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash', 'comments', 'related_videos'],
            }
        },
        # Only get these fields
        'default_search': 'error',
        'writeinfojson': False,
        'writesubtitles': False,
        'writethumbnail': False,
        'writedescription': False,
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Extract only basic metadata
            info = ydl.extract_info(url, download=False, process=False)
            
            # Get title and description
            title = info.get('title', 'No title available')
            description = info.get('description', 'No description available')
            
            return title, description
            
    except Exception as e:
        return f"Error: {str(e)}", None

# Example usage
if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=xnmz0u71xLk&list=LL&index=19&ab_channel=SarahBanh"
    title, description = get_video_info(video_url)
    
    print("Title:", title)
    print("\nDescription:", description)