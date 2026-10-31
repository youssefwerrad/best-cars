import os

import requests
from dotenv import load_dotenv

load_dotenv()
sentiment_analyzer_url = os.getenv("sentiment_analyzer_url", default="http://localhost:5050/")


def analyze_review_sentiments(text):
    try:
        response = requests.post(
            sentiment_analyzer_url.rstrip("/") + "/analyze",
            json={"text": text},
            timeout=3,
        )
        response.raise_for_status()
        sentiment = response.json().get("sentiment")
        return sentiment if sentiment in {"positive", "neutral", "negative"} else "neutral"
    except Exception:
        return "neutral"
