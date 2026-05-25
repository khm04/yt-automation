import os
import uuid
from datetime import datetime
from config import OUTPUT_DIR, VIDEOS_PER_DAY
from modules.reddit_fetcher import fetch_story
from modules.script_writer import rewrite_as_script, generate_title_and_tags
from modules.voice_generator import generate_voice
from modules.video_assembler import assemble_video
from modules.uploader import upload_to_youtube

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_single_video(video_index: int = 0):
    """Run the full pipeline for one video. Returns YouTube video ID."""
    video_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{OUTPUT_DIR}/{timestamp}_{video_id}"

    print(f"\n{'='*50}")
    print(f"Starting video {video_id}")

    # Step 1: Fetch story
    print("Fetching Reddit story...")
    story = fetch_story()
    print(f"   Got: {story['title'][:60]}...")

    # Step 2: Rewrite as script (retry until audio hits 60s)
    print("Rewriting with Gemini...")
    script = rewrite_as_script(story["title"], story["body"])
    meta = generate_title_and_tags(script)
    print(f"   Title: {meta['title']}")

    # Step 3: Generate voice
    print("Generating voice...")
    audio_path = generate_voice(script, f"{base_name}.mp3")

    # Step 4: Assemble video (raises ValueError if audio < 60s)
    print("Assembling video with FFmpeg...")
    attempt = 0
    video_path = None
    while attempt < 3:
        try:
            video_path = assemble_video(
                audio_path, script, f"{base_name}.mp4",
                subreddit=story["subreddit"],
                story_title=story["title"],
                video_index=video_index,
            )
            break
        except ValueError as e:
            attempt += 1
            print(f"   {e} — expanding script (attempt {attempt})...")
            from modules.script_writer import expand_script
            script = expand_script(script)
            audio_path = generate_voice(script, f"{base_name}.mp3")

    if video_path is None:
        raise RuntimeError("Could not generate a 60s+ video after 3 attempts")

    # Step 5: Upload to YouTube (skip in dry-run mode)
    if os.getenv("DRY_RUN"):
        print(f"   DRY RUN — video saved at: {video_path}")
        return video_path

    print("Uploading to YouTube...")
    description = (
        f"{script[:200]}...\n\n"
        f"Original story: {story['url']}\n\n"
        "#shorts #reddit #story #viral"
    )
    yt_id = upload_to_youtube(
        video_path=video_path,
        title=meta["title"],
        description=description,
        tags=meta["tags"] + ["shorts", "reddit", "viral", "story"],
    )
    print(f"   Uploaded: https://youtube.com/watch?v={yt_id}")

    os.remove(audio_path)
    os.remove(video_path)
    srt_path = video_path.replace(".mp4", ".srt")
    if os.path.exists(srt_path):
        os.remove(srt_path)

    return yt_id


def main():
    print(f"Starting automated pipeline — {VIDEOS_PER_DAY} videos")
    results = []

    # Use current hour to determine video index so each trigger uses correct background
    from datetime import datetime as _dt
    base_index = int(os.getenv("VIDEO_INDEX_OVERRIDE", str(_dt.utcnow().hour // 6 % len(__import__('config').GAMEPLAY_VIDEOS))))

    for i in range(VIDEOS_PER_DAY):
        print(f"\nVideo {i + 1} of {VIDEOS_PER_DAY}")
        try:
            yt_id = run_single_video(video_index=base_index + i)
            results.append({"status": "success", "id": yt_id})
        except Exception as e:
            print(f"   Failed: {e}")
            results.append({"status": "failed", "error": str(e)})

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n{'='*50}")
    print(f"Done. {success}/{VIDEOS_PER_DAY} videos uploaded successfully.")


if __name__ == "__main__":
    main()
