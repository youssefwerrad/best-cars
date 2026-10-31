from flask import Flask, jsonify, request
from nltk.sentiment import SentimentIntensityAnalyzer
app = Flask("Sentiment Analyzer")

sia = SentimentIntensityAnalyzer()


@app.get('/')
def home():
    return "Welcome to the Sentiment Analyzer. \
    Send POST /analyze with a JSON text field to get the sentiment"


def _sentiment(input_txt):

    scores = sia.polarity_scores(input_txt)
    pos = float(scores['pos'])
    neg = float(scores['neg'])
    neu = float(scores['neu'])
    res = "positive"
    if (neg > pos and neg > neu):
        res = "negative"
    elif (neu > neg and neu > pos):
        res = "neutral"
    return res


@app.get('/analyze/<path:input_txt>')
def analyze_sentiment(input_txt):
    return jsonify({"sentiment": _sentiment(input_txt)})


@app.post('/analyze')
def analyze_sentiment_json():
    data = request.get_json(silent=True) or {}
    input_txt = data.get("text")
    if not isinstance(input_txt, str):
        return jsonify({"message": "A text string is required."}), 400
    return jsonify({"sentiment": _sentiment(input_txt)})


if __name__ == "__main__":
    app.run(debug=True)
