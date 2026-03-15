import requests
import os
from dotenv import load_dotenv
load_dotenv()


def get_ai_news():

    api_key = os.getenv("NEWS_API_KEY")

    url = f"https://newsapi.org/v2/everything?q=artificial intelligence&sortBy=publishedAt&language=en&apiKey={api_key}"

    response = requests.get(url)

    data = response.json()

    articles = data["articles"]

    if not articles:
        return "AI News", "No latest AI news found."

    article = articles[0]

    title = article["title"]
    description = article["description"]

    return title, description