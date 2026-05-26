import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

PROMPT_TEMPLATE = """
You are a viral YouTube Shorts scriptwriter. Rewrite this Reddit story as a dramatic,
engaging narration script for a faceless YouTube channel.

Rules:
- Start with a HOOK that grabs attention in the first 3 seconds (e.g. "You will NOT believe what happened...")
- Write EXACTLY 180-200 words — no more, no less (this is critical for video length)
- Use short punchy sentences with NO filler words
- NO long pauses — keep the energy up the entire time
- Build tension and emotion fast
- End with a satisfying conclusion or cliffhanger
- Write ONLY the narration — no stage directions, no titles, no labels
- Do NOT include any hashtags

Story title: {title}

Story: {body}

Write the script now (180-200 words exactly):
"""


def rewrite_as_script(title: str, body: str) -> str:
    """Rewrite a Reddit story as a dramatic YouTube Shorts script."""
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = PROMPT_TEMPLATE.format(title=title, body=body)
    response = model.generate_content(prompt)
    script = response.text.strip()

    if not script:
        raise ValueError("Gemini returned empty script")

    # If too short, ask Gemini to expand
    word_count = len(script.split())
    if word_count < 175:
        expand_prompt = f"""This script is too short ({word_count} words). Expand it to exactly 185 words by adding more emotional detail, reactions, and tension. Keep the same story and style. No hashtags.

Script:
{script}

Rewrite it now at exactly 185 words:"""
        response = model.generate_content(expand_prompt)
        script = response.text.strip()

    return script


def expand_script(script: str) -> str:
    """Expand a short script to hit 60s audio length."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""This narration script is too short. Expand it to exactly 200 words by adding more emotional reactions, tension, and detail. Keep the same story, same style, no hashtags, no stage directions.

Script:
{script}

Rewrite at exactly 200 words:"""
    response = model.generate_content(prompt)
    return response.text.strip()


def generate_reddit_title(script: str) -> str:
    """Generate a Reddit-style post title that matches the actual script content."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""Read this narration script and write a Reddit post title for it.
Make it sound like a real Reddit post — shocking, emotional, or controversial.
Under 12 words. No quotes. No labels. Just the title.

Script (first 300 chars):
{script[:300]}

Write the Reddit title now:"""
    return model.generate_content(prompt).text.strip()


def generate_title_and_tags(script: str) -> dict:
    """Generate a YouTube title and tags from the script."""
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
Based on this YouTube Shorts script, generate:
1. A clickbait YouTube title (max 70 characters, no quotes)
2. 10 relevant tags separated by commas

Script:
{script[:500]}

Reply in exactly this format:
TITLE: your title here
TAGS: tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10
"""
    response = model.generate_content(prompt)
    lines = response.text.strip().split("\n")

    title = ""
    tags = []
    for line in lines:
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip() for t in line.replace("TAGS:", "").split(",")]

    return {"title": title, "tags": tags}
