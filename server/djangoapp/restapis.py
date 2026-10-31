import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()
sentiment_analyzer_url = os.getenv("sentiment_analyzer_url", default="http://localhost:5050/")
logger = logging.getLogger(__name__)


def analyze_review_sentiments(text):
    try:
        response = requests.post(
            sentiment_analyzer_url.rstrip("/") + "/analyze",
            json={"text": text},
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json()
        sentiment = payload.get("sentiment")
        if sentiment in {"positive", "neutral", "negative"}:
            return sentiment
        logger.warning("Sentiment service returned an invalid sentiment value")
    except (requests.RequestException, ValueError, AttributeError) as error:
        logger.warning(
            "Sentiment service is unavailable or returned an invalid response (%s)",
            type(error).__name__,
        )
    return None
