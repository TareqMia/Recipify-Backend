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

    @staticmethod
    async def generate_summary(text: str, ratio: float = 0.5) -> str:
        TranscriptService.initialize_nltk()

        logger.debug("Starting summary generation...")

        # Tokenize sentences and words
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())

        # Calculate word frequencies
        word_freq = defaultdict(int)
        for word in words:
            if word not in TranscriptService._stop_words:
                word_freq[word] += 1

        if not word_freq:
            logger.warning("No valid words found for frequency analysis.")
            return ''

        # Calculate sentence scores
        sent_scores = defaultdict(int)
        for sent in sentences:
            for word in word_tokenize(sent.lower()):
                if word in word_freq:
                    sent_scores[sent] += word_freq[word]

        if not sent_scores:
            logger.warning("No sentence scores computed.")
            return ''

        # Determine number of sentences for summary
        select_length = max(1, int(len(sentences) * ratio))
        logger.debug(f"Selecting top {select_length} sentences for summary.")

        # Select top sentences
        top_sents = nlargest(select_length, sent_scores, key=sent_scores.get)

        # Sort selected sentences by their original order
        ordered_sents = sorted(top_sents, key=lambda s: sentences.index(s))

        summary = ' '.join(ordered_sents)
        logger.debug("Summary generation completed.")
        return summary

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

    @classmethod
    async def generate_summary_textrank(text: str, ratio: float = 0.3) -> str:
        TranscriptService.initialize_nltk()

        logger.debug("Starting TextRank summary generation...")

        sentences = sent_tokenize(text)
        if not sentences:
            logger.warning("No sentences found for TextRank summarization.")
            return ''

        # Build similarity matrix
        similarity = defaultdict(dict)
        for i, j in combinations(range(len(sentences)), 2):
            sent1 = sentences[i]
            sent2 = sentences[j]
            words1 = set(word_tokenize(sent1.lower())) - cls._stop_words
            words2 = set(word_tokenize(sent2.lower())) - cls._stop_words
            common = words1.intersection(words2)
            if common:
                similarity[i][j] = len(common) / (len(words1) + len(words2))
                similarity[j][i] = similarity[i][j]

        # Create graph
        graph = nx.Graph(similarity)
        scores = nx.pagerank_numpy(graph)

        # Rank sentences
        ranked_sentences = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)

        select_length = max(1, int(len(sentences) * ratio))
        selected_sentences = sorted(ranked_sentences[:select_length], key=lambda x: sentences.index(x[1]))

        summary = ' '.join([s for score, s in selected_sentences])
        logger.debug("TextRank summary generation completed.")
        return summary