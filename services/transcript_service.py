import asyncio
import logging
from functools import partial
from typing import List, Dict

from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
from fastapi import HTTPException
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from string import punctuation
from heapq import nlargest
from collections import defaultdict

import cleantext
import networkx as nx
from itertools import combinations

# Configure logging
logger = logging.getLogger(__name__)
class TranscriptService:
    _stop_words = set()
    _nltk_initialized = False

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
        
        except CouldNotRetrieveTranscript as e:
            return 'no transcript'
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