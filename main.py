from services.news_fetcher import get_ai_news
from services.gemini_generator import generate_post
from services.buffer_poster import post_to_linkedin
from services.slack_notifier import send_slack_notification


def run_pipeline():

    print("Fetching AI news...")

    title, description = get_ai_news()

    print("Generating LinkedIn post using Gemini...")

    post = generate_post(title, description)

    print("Generated Post:\n")
    print(post)

    response = send_slack_notification(post)
    print("Post sent to Slack for approval.")
    print(response)

    # print("\nPosting to LinkedIn via Buffer...")

    # response = post_to_linkedin(post)

    # print(response)


if __name__ == "__main__":
    run_pipeline()