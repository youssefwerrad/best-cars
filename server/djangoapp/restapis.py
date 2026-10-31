import os

import requests
from dotenv import load_dotenv

load_dotenv()
sentiment_analyzer_url = os.getenv("sentiment_analyzer_url", default="http://localhost:5050/")


def analyze_review_sentiments(text):
    try:
        r = requests.get(sentiment_analyzer_url + "analyze/" + text, timeout=3)
        return r.json().get("sentiment", "neutral")
    except Exception:
        return "neutral"
