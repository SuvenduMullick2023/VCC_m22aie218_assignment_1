from flask import Flask, request, jsonify, render_template
import requests
import os
from groq import Groq
import config

app = Flask(__name__)

# API keys (Ensure they exist in config.py)
NEWSDATA_API_KEY = config.NEWSDATA_API_KEY
GROQ_API_KEY = config.GROQ_API_KEY

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

def content_summarise(prompt): 
    """Generates a summarized response using Groq API"""
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an expert news editor. Summarize the following news in 10 points:\n" + prompt},
            {"role": "user", "content": "Summarize the news in 10 points"}
        ],

        temperature=0.7,
        max_tokens=1024,
        top_p=1
    )

    return completion.choices[0].message.content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/news', methods=['GET'])
def get_news():
    country = request.args.get('country', '').strip()

    if not country:
        return jsonify({"error": "Country name is required"}), 400

    try:
        # Fetch news from NewsData API
        news_url = f"https://newsdata.io/api/1/latest?apikey={NEWSDATA_API_KEY}&q={country}"
        news_response = requests.get(news_url).json()

        if "results" not in news_response:
            return jsonify({"error": "Failed to fetch news"}), 500

        articles = news_response.get("results", [])[:10]  # Get top 10 articles
        if not articles:
            return jsonify({"error": "No news found"}), 404

        # Extract headlines
        headlines = [article.get("title", "No Title") for article in articles]
        summary_prompt = "\n".join(headlines) + "\nSummarize these headlines in simple terms."

        # Summarize the news
        summarized_news = content_summarise(summary_prompt)

        return jsonify({"summarized_news": summarized_news})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
