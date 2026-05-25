from unittest.mock import patch, MagicMock
from modules.reddit_fetcher import fetch_story


def _make_response(posts_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"children": [{"data": p} for p in posts_data]}
    }
    return mock_resp


def test_fetch_story_returns_title_and_body():
    post = {
        "title": "I accidentally told my boss I hated him",
        "selftext": "So this happened last Tuesday at work..." + "x" * 300,
        "permalink": "/r/tifu/comments/abc123",
        "stickied": False,
        "over_18": False,
    }

    with patch("modules.reddit_fetcher.requests.get", return_value=_make_response([post])):
        result = fetch_story()

    assert "title" in result
    assert "body" in result
    assert len(result["body"]) > 10


def test_fetch_story_filters_short_posts():
    short = {
        "title": "Short",
        "selftext": "Too short",
        "permalink": "/r/tifu/comments/short",
        "stickied": False,
        "over_18": False,
    }
    long = {
        "title": "Long enough story",
        "selftext": "x" * 500,
        "permalink": "/r/tifu/comments/xyz",
        "stickied": False,
        "over_18": False,
    }

    with patch("modules.reddit_fetcher.requests.get", return_value=_make_response([short, long])):
        result = fetch_story()

    assert result["title"] == "Long enough story"
