from youtube_transcript_api import YouTubeTranscriptApi
from fastapi import HTTPException
import asyncio
from functools import partial
import re
import cleantext
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from string import punctuation
from heapq import nlargest
from collections import defaultdict

class TranscriptService:

    @staticmethod
    async def get_transcript(video_id: str) -> str:
        """
        Fetches and cleans the transcript of a YouTube video by its ID.

        Args:
            video_id (str): The ID of the YouTube video.

        Returns:
            str: The cleaned transcript text.
        """
        try:
            loop = asyncio.get_running_loop()
            transcript_list: list[dict] = await loop.run_in_executor(
                None,
                partial(YouTubeTranscriptApi.get_transcript, video_id)
            )
            # Clean emojis from each text entry
            cleaned_text: str = ' '.join(
                cleantext.clean(entry['text'], no_emoji=True)
                for entry in transcript_list
            )
            return cleaned_text
        
        except YouTubeTranscriptApi.CouldNotRetrieveTranscript as e:
            raise HTTPException(
                status_code=404,
                detail=f"Could not get transcript: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}"
            )

    @staticmethod
    def generate_summary(text: str, ratio: float = 0.5) -> str:
        """
        Generate summary using frequency-based extractive summarization.
        """
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        
        # Tokenize the text
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        
        # Remove stopwords and punctuation
        stop_words = set(stopwords.words('english') + list(punctuation))
        word_freq = defaultdict(int)
        
        for word in words:
            if word not in stop_words:
                word_freq[word] += 1
                
        # Calculate sentence scores
        sent_scores = defaultdict(int)
        for sent in sentences:
            for word in word_tokenize(sent.lower()):
                if word in word_freq:
                    sent_scores[sent] += word_freq[word]
                    
        # Select top sentences while maintaining order
        select_length = max(1, int(len(sentences) * ratio))
        top_sents = nlargest(select_length, sent_scores, key=sent_scores.get)
        
        # Sort sentences by their original position
        ordered_sents = [sent for sent in sentences if sent in top_sents]
        
        return ' '.join(ordered_sents)

    @staticmethod
    async def get_transcript_summary(video_id: str, ratio: float = 0.5) -> str:
        """
        Fetches the transcript of a YouTube video and generates a summary.

        Args:
            video_id (str): The ID of the YouTube video.
            ratio (float): The ratio of sentences to include in the summary.

        Returns:
            str: The summarized transcript text.
        """
        transcript = await TranscriptService.get_transcript(video_id)
        summary = TranscriptService.generate_summary(transcript, ratio)
        return summary