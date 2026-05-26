import random
import requests
from config import REDDIT_USER_AGENT, SUBREDDITS, POSTS_LIMIT

MIN_BODY_LENGTH = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def fetch_story() -> dict:
    """Fetch a viral story from Reddit using public JSON API (no auth needed)."""
    subreddits = SUBREDDITS.copy()
    random.shuffle(subreddits)

    for subreddit_name in subreddits:
        for time_filter in ["day", "week"]:
            url = f"https://www.reddit.com/r/{subreddit_name}/top.json?limit={POSTS_LIMIT}&t={time_filter}"
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 403:
                    continue
                response.raise_for_status()
            except Exception:
                continue

            posts = response.json().get("data", {}).get("children", [])
            candidates = [
                item["data"] for item in posts
                if not item["data"].get("stickied")
                and item["data"].get("selftext")
                and len(item["data"]["selftext"]) >= MIN_BODY_LENGTH
                and not item["data"].get("over_18")
            ]
            if candidates:
                post = random.choice(candidates)
                return {
                    "title": post["title"],
                    "body": post["selftext"][:3000],
                    "url": f"https://reddit.com{post['permalink']}",
                    "subreddit": subreddit_name,
                }

    raise ValueError("Could not fetch a story from any subreddit — all returned 403 or no candidates")
