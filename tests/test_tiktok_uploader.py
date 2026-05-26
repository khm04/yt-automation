"""
Unit tests for modules/tiktok_uploader.py
Uses unittest.mock to avoid real HTTP calls.
"""

import os
import math
import unittest
from unittest.mock import MagicMock, mock_open, patch

from modules.tiktok_uploader import (
    CHUNK_SIZE,
    _build_caption,
    _get_access_token,
    check_publish_status,
    init_upload,
    refresh_access_token,
    upload_chunks,
    upload_to_tiktok,
)


class TestBuildCaption(unittest.TestCase):
    def test_includes_title_and_hashtags(self):
        cap = _build_caption("My Story", ["reddit", "tifu", "storytime"])
        self.assertIn("My Story", cap)
        self.assertIn("#reddit", cap)
        self.assertIn("#tifu", cap)

    def test_truncates_to_2200(self):
        long_title = "x" * 3000
        cap = _build_caption(long_title, [])
        self.assertLessEqual(len(cap), 2200)

    def test_hashtag_no_spaces(self):
        cap = _build_caption("T", ["hello world"])
        self.assertIn("#helloworld", cap)


class TestGetAccessToken(unittest.TestCase):
    def test_returns_env_token_when_set(self):
        with patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok123"}):
            self.assertEqual(_get_access_token(), "tok123")

    def test_calls_refresh_when_no_access_token(self):
        env = {"TIKTOK_ACCESS_TOKEN": "", "TIKTOK_REFRESH_TOKEN": "rft"}
        with patch.dict(os.environ, env), \
             patch("modules.tiktok_uploader.refresh_access_token", return_value="refreshed") as mock_refresh:
            token = _get_access_token()
        mock_refresh.assert_called_once()
        self.assertEqual(token, "refreshed")


class TestRefreshAccessToken(unittest.TestCase):
    def test_raises_when_credentials_missing(self):
        env = {"TIKTOK_ACCESS_TOKEN": "", "TIKTOK_REFRESH_TOKEN": "",
               "TIKTOK_CLIENT_KEY": "", "TIKTOK_CLIENT_SECRET": ""}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(RuntimeError):
                refresh_access_token()

    def test_returns_access_token_on_success(self):
        env = {
            "TIKTOK_CLIENT_KEY": "ck",
            "TIKTOK_CLIENT_SECRET": "cs",
            "TIKTOK_REFRESH_TOKEN": "rft",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new_tok"}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, env), \
             patch("requests.post", return_value=mock_response):
            token = refresh_access_token()
        self.assertEqual(token, "new_tok")

    def test_raises_on_api_error_field(self):
        env = {
            "TIKTOK_CLIENT_KEY": "ck",
            "TIKTOK_CLIENT_SECRET": "cs",
            "TIKTOK_REFRESH_TOKEN": "rft",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = MagicMock()

        with patch.dict(os.environ, env), \
             patch("requests.post", return_value=mock_response):
            with self.assertRaises(RuntimeError):
                refresh_access_token()


class TestInitUpload(unittest.TestCase):
    def _mock_post(self, publish_id="pub123", upload_url="https://upload.example.com"):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": {"publish_id": publish_id, "upload_url": upload_url},
            "error": {"code": "ok"},
        }
        return mock_resp

    def test_returns_publish_id_and_upload_url(self):
        with patch("requests.post", return_value=self._mock_post()):
            data = init_upload("tok", 1024 * 1024, "My Title", ["reddit"])
        self.assertEqual(data["publish_id"], "pub123")
        self.assertEqual(data["upload_url"], "https://upload.example.com")

    def test_raises_on_api_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"error": {"code": "access_token_invalid", "message": "bad"}}
        with patch("requests.post", return_value=mock_resp):
            with self.assertRaises(RuntimeError):
                init_upload("bad_tok", 100, "T", [])

    def test_chunk_count_in_payload(self):
        captured = {}

        def fake_post(url, **kwargs):
            captured["payload"] = kwargs.get("json", {})
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "data": {"publish_id": "x", "upload_url": "u"},
                "error": {"code": "ok"},
            }
            return resp

        video_size = CHUNK_SIZE * 3 + 500  # 3 full chunks + 1 partial
        with patch("requests.post", side_effect=fake_post):
            init_upload("tok", video_size, "T", [])

        self.assertEqual(
            captured["payload"]["source_info"]["total_chunk_count"], 4
        )


class TestUploadChunks(unittest.TestCase):
    def test_single_chunk_upload(self):
        fake_data = b"x" * 1024  # 1 KB — fits in one chunk
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        m = mock_open(read_data=fake_data)
        with patch("builtins.open", m), \
             patch("requests.put", return_value=mock_resp) as mock_put:
            upload_chunks("https://upload.example.com", "fake.mp4", len(fake_data))

        mock_put.assert_called_once()
        call_headers = mock_put.call_args[1]["headers"]
        self.assertIn("Content-Range", call_headers)
        self.assertEqual(call_headers["Content-Range"], f"bytes 0-{len(fake_data)-1}/{len(fake_data)}")

    def test_raises_on_bad_status(self):
        fake_data = b"x" * 100
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"

        m = mock_open(read_data=fake_data)
        with patch("builtins.open", m), \
             patch("requests.put", return_value=mock_resp):
            with self.assertRaises(RuntimeError):
                upload_chunks("https://upload.example.com", "fake.mp4", len(fake_data))

    def test_multiple_chunks(self):
        video_size = int(CHUNK_SIZE * 2.5)
        fake_data = b"a" * video_size
        mock_resp = MagicMock()
        mock_resp.status_code = 206

        m = mock_open(read_data=fake_data)
        with patch("builtins.open", m), \
             patch("requests.put", return_value=mock_resp) as mock_put:
            upload_chunks("https://u", "f.mp4", video_size)

        expected_chunks = math.ceil(video_size / CHUNK_SIZE)
        self.assertEqual(mock_put.call_count, expected_chunks)


class TestCheckPublishStatus(unittest.TestCase):
    def _make_resp(self, status):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = {"data": {"status": status}}
        return r

    def test_returns_on_complete(self):
        with patch("requests.post", return_value=self._make_resp("PUBLISH_COMPLETE")):
            result = check_publish_status("tok", "pub123")
        self.assertEqual(result, "PUBLISH_COMPLETE")

    def test_raises_on_failed(self):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"data": {"status": "FAILED", "fail_reason": "bad_video"}}
        with patch("requests.post", return_value=resp):
            with self.assertRaises(RuntimeError):
                check_publish_status("tok", "pub123")

    def test_polls_multiple_times(self):
        responses = [
            self._make_resp("PROCESSING_UPLOAD"),
            self._make_resp("PROCESSING_DOWNLOAD"),
            self._make_resp("PUBLISH_COMPLETE"),
        ]
        with patch("requests.post", side_effect=responses), \
             patch("time.sleep"):
            result = check_publish_status("tok", "pub123", poll_interval=0)
        self.assertEqual(result, "PUBLISH_COMPLETE")

    def test_raises_on_timeout(self):
        with patch("requests.post", return_value=self._make_resp("PROCESSING_UPLOAD")), \
             patch("time.sleep"):
            with self.assertRaises(RuntimeError):
                check_publish_status("tok", "pub123", max_retries=2, poll_interval=0)


class TestUploadToTiktok(unittest.TestCase):
    def test_raises_environment_error_when_no_credentials(self):
        env = {"TIKTOK_ACCESS_TOKEN": "", "TIKTOK_REFRESH_TOKEN": ""}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(EnvironmentError):
                upload_to_tiktok("video.mp4", "Title", ["tag"])

    def test_full_happy_path(self):
        env = {"TIKTOK_ACCESS_TOKEN": "tok", "TIKTOK_REFRESH_TOKEN": ""}
        video_size = 1024

        with patch.dict(os.environ, env, clear=False), \
             patch("os.path.getsize", return_value=video_size), \
             patch("modules.tiktok_uploader.init_upload",
                   return_value={"publish_id": "pub1", "upload_url": "https://up"}
                   ) as mock_init, \
             patch("modules.tiktok_uploader.upload_chunks") as mock_chunks, \
             patch("modules.tiktok_uploader.check_publish_status",
                   return_value="PUBLISH_COMPLETE") as mock_status:

            url = upload_to_tiktok("video.mp4", "My Title", ["reddit"])

        mock_init.assert_called_once_with("tok", video_size, "My Title", ["reddit"])
        mock_chunks.assert_called_once_with("https://up", "video.mp4", video_size)
        mock_status.assert_called_once_with("tok", "pub1")
        self.assertIn("tiktok.com", url)


if __name__ == "__main__":
    unittest.main()
