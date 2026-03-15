import os
from google import genai
from dotenv import load_dotenv

load_dotenv()


def generate_post(title, description):

    api_key = os.getenv("GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a tech thought leader writing on LinkedIn.

Write a professional LinkedIn post about the following AI news.

Title: {title}
Description: {description}

Rules:
- 120–150 words
- Professional tone
- Add 2–3 relevant emojis
- End with a question to drive engagement
- Include 3 hashtags related to AI
"""

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )

    return response.text