import random
import requests
from config import REDDIT_USER_AGENT, SUBREDDITS, POSTS_LIMIT

MIN_BODY_LENGTH = 300


def fetch_story() -> dict:
    """Fetch a viral story from Reddit using public JSON API (no auth needed)."""
    subreddit_name = random.choice(SUBREDDITS)
    url = f"https://www.reddit.com/r/{subreddit_name}/top.json?limit={POSTS_LIMIT}&t=day"

    headers = {"User-Agent": REDDIT_USER_AGENT}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    posts = response.json()["data"]["children"]

    candidates = []
    for item in posts:
        post = item["data"]
        if (
            not post.get("stickied")
            and post.get("selftext")
            and len(post["selftext"]) >= MIN_BODY_LENGTH
            and not post.get("over_18")
        ):
            candidates.append(post)

    if not candidates:
        raise ValueError(f"No suitable posts found in r/{subreddit_name}")

    post = random.choice(candidates)

    return {
        "title": post["title"],
        "body": post["selftext"][:3000],
        "url": f"https://reddit.com{post['permalink']}",
        "subreddit": subreddit_name,
    }
