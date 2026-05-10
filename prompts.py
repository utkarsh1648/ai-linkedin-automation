"""
AI Prompt Configuration
------------------------
Prompts are loaded from plain-text files in the `prompts/` directory.
To customize a prompt, simply edit the corresponding .txt file — no Python knowledge needed.

Available .txt files:
  prompts/select_top_trending.txt       → SELECT_TOP_TRENDING_PROMPT
  prompts/generate_social_post.txt      → GENERATE_SOCIAL_POST_PROMPT
  prompts/generate_newsletter_intro.txt → GENERATE_NEWSLETTER_INTRO_PROMPT

Dynamic placeholders (replaced at runtime by the code):
  {article_count}   - Total number of articles being analyzed
  {count}           - Number of top articles to select
  {articles_list}   - Numbered list of article headlines/summaries
  {articles_text}   - Full text of selected articles
"""

from utils.prompt_loader import load_prompt

SELECT_TOP_TRENDING_PROMPT = load_prompt("select_top_trending")
GENERATE_SOCIAL_POST_PROMPT = load_prompt("generate_social_post")
GENERATE_NEWSLETTER_INTRO_PROMPT = load_prompt("generate_newsletter_intro")

PROMPT_LIST = [
    SELECT_TOP_TRENDING_PROMPT,
    GENERATE_SOCIAL_POST_PROMPT,
    GENERATE_NEWSLETTER_INTRO_PROMPT,
]
