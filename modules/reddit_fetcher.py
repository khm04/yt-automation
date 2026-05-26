import random
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

STORY_STYLES = [
    ("AmItheAsshole", "AITA"),
    ("tifu", "TIFU"),
    ("relationship_advice", "relationship drama"),
    ("confessions", "confession"),
    ("TrueOffMyChest", "true story"),
]


def fetch_story() -> dict:
    """Generate a viral Reddit-style story using Gemini."""
    subreddit, style = random.choice(STORY_STYLES)

    prompt = (
        f"Write a viral Reddit {style} story in first person. "
        "It must feel real, emotional, and relatable. "
        "Include a clear conflict, strong emotions, and a satisfying or shocking resolution. "
        "Write ONLY the story body (300-500 words). No title, no labels, no commentary. "
        "Make it the kind of story people screenshot and share."
    )

    title_prompt = (
        f"Write a clickbait Reddit-style title for a {style} post. "
        "Make it shocking, relatable, or controversial. Under 15 words. "
        "No quotes, no labels, just the title."
    )

    model = genai.GenerativeModel("gemini-2.5-flash")
    body = model.generate_content(prompt).text.strip()
    title = model.generate_content(title_prompt).text.strip()

    return {
        "title": title,
        "body": body,
        "url": f"https://reddit.com/r/{subreddit}",
        "subreddit": subreddit,
    }
