from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

def get_transcript(url):
    # Extract video ID from URL
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        video_id = parsed_url.path[1:]
    else:
        video_id = parse_qs(parsed_url.query)['v'][0]
        
    # Get and combine transcript pieces
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    return ' '.join(entry['text'] for entry in transcript_list)

# Example usage
video_url = "https://www.youtube.com/watch?v=xnmz0u71xLk&list=LL&index=19&ab_channel=SarahBanh"
print(get_transcript(video_url))