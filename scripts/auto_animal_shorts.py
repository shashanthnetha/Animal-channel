"""
Autonomous Animal & Nature YouTube Shorts Publisher.

Orchestrates the entire pipeline:
1. Chooses/generates an unrepeated, curiosity-driven animal/nature topic.
2. Writes a high-retention 25-40s 5-phase storytelling script.
3. Extracts realistic wildlife stock footage keywords.
4. Synthesizes voiceover, generates subtitles with pop spring animation.
5. Composites 9:16 vertical video with royalty-free ambient BGM.
6. Generates high-CTR title, description, and viral hashtags.
7. Uploads directly to YouTube Shorts via YouTube Data API v3.
8. Logs record to history/uploaded_shorts.json.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from loguru import logger

from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode, VideoParams
from app.services import animal_channel, task as task_service
from app.utils import utils
from scripts.youtube_uploader import upload_video_to_youtube, YouTubeUploadError


HISTORY_FILE = ROOT_DIR / "history" / "uploaded_shorts.json"
DEFAULT_VOICE = "en-US-ChristopherNeural"  # Professional documentary tone


def apply_env_overrides_to_config():
    """
    Bridge environment variables (e.g. from GitHub Actions secrets)
    into MoneyPrinterTurbo runtime config.
    """
    # Pexels / Pixabay keys
    pexels_key = os.getenv("PEXELS_API_KEY") or os.getenv("PEXELS_API_KEYS")
    if pexels_key:
        keys = [k.strip() for k in pexels_key.split(",") if k.strip()]
        config.app["pexels_api_keys"] = keys
        logger.info(f"Loaded {len(keys)} Pexels API key(s) from environment.")

    pixabay_key = os.getenv("PIXABAY_API_KEY") or os.getenv("PIXABAY_API_KEYS")
    if pixabay_key:
        keys = [k.strip() for k in pixabay_key.split(",") if k.strip()]
        config.app["pixabay_api_keys"] = keys
        logger.info(f"Loaded {len(keys)} Pixabay API key(s) from environment.")

    # LLM Providers & Keys
    provider_set = False
    explicit_provider = os.getenv("LLM_PROVIDER")

    if os.getenv("GROQ_API_KEY"):
        config.app["groq_api_key"] = os.getenv("GROQ_API_KEY").strip()
        config.app["groq_model_name"] = (
            os.getenv("LLM_MODEL_NAME")
            or os.getenv("GROQ_MODEL_NAME")
            or "qwen/qwen3.8-27b"
        ).strip()
        if not explicit_provider and not provider_set:
            config.app["llm_provider"] = "groq"
            provider_set = True

    if os.getenv("GEMINI_API_KEY"):
        config.app["gemini_api_key"] = os.getenv("GEMINI_API_KEY").strip()
        if not explicit_provider and not provider_set:
            config.app["llm_provider"] = "gemini"
            provider_set = True

    if os.getenv("OPENAI_API_KEY"):
        config.app["openai_api_key"] = os.getenv("OPENAI_API_KEY").strip()
        if not explicit_provider and not provider_set:
            config.app["llm_provider"] = "openai"
            provider_set = True

    if os.getenv("DEEPSEEK_API_KEY"):
        config.app["deepseek_api_key"] = os.getenv("DEEPSEEK_API_KEY").strip()
        if not explicit_provider and not provider_set:
            config.app["llm_provider"] = "deepseek"
            provider_set = True

    if os.getenv("MOONSHOT_API_KEY"):
        config.app["moonshot_api_key"] = os.getenv("MOONSHOT_API_KEY").strip()
        if not explicit_provider and not provider_set:
            config.app["llm_provider"] = "moonshot"
            provider_set = True

    if explicit_provider:
        config.app["llm_provider"] = explicit_provider.strip().lower()

    active_provider = config.app.get("llm_provider", "groq")
    model_name_env = os.getenv("LLM_MODEL_NAME")
    if model_name_env:
        config.app[f"{active_provider}_model_name"] = model_name_env.strip()

    active_model = config.app.get(f"{active_provider}_model_name", "")
    logger.info(f"Active LLM Provider: {active_provider} (Model: {active_model})")



def load_history(history_path: Path = HISTORY_FILE) -> list[dict[str, Any]]:
    """Load previously published video records."""
    if not history_path.exists():
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                return data
    except Exception as exc:
        logger.warning(f"Could not read history file {history_path}: {exc}")
    return []


def save_history_record(record: dict[str, Any], history_path: Path = HISTORY_FILE) -> None:
    """Append a new video record to the history file."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history(history_path)
    history.append(record)
    with open(history_path, "w", encoding="utf-8") as fp:
        json.dump(history, fp, indent=2, ensure_ascii=False)
    logger.info(f"Updated history log at {history_path} (total: {len(history)} entries)")


def run_animal_shorts_pipeline(
    custom_topic: Optional[str] = None,
    pillar_id: Optional[str] = None,
    voice_name: str = DEFAULT_VOICE,
    voice_rate: float = 0.8,
    bgm_volume: float = 0.08,
    privacy_status: str = "public",
    video_source: str = "pexels",
    dry_run: bool = False,
    no_upload: bool = False,
) -> dict[str, Any]:
    """
    Executes the full automated pipeline.
    """
    logger.info("🌿 Starting Animal & Nature Autonomous Shorts Engine...")
    logger.info(f"Audio Settings: Voice Rate = {voice_rate}x, BGM Volume = {bgm_volume}")
    apply_env_overrides_to_config()

    # Step 1: Topic selection
    history = load_history()
    past_titles = [item.get("title", "") for item in history]

    if custom_topic:
        logger.info(f"Using provided custom topic: {custom_topic}")
        topic_data = {
            "subject": custom_topic,
            "hook_angle": f"The astonishing facts about {custom_topic}",
            "target_animal": custom_topic,
            "short_title": f"{custom_topic[:45]} 🐾",
        }
    else:
        logger.info("Generating a fresh, curiosity-driven topic using LLM...")
        topic_data = animal_channel.generate_curiosity_topic(
            history_titles=past_titles,
            pillar_id=pillar_id,
        )

    subject = topic_data["subject"]
    hook_angle = topic_data.get("hook_angle", "")
    short_title = topic_data.get("short_title", subject)
    target_animal = topic_data.get("target_animal", subject)

    logger.info(f"Target Subject: {subject}")
    logger.info(f"Hook Angle: {hook_angle}")

    # Step 2: Script Generation (25-40s 5-phase story)
    logger.info("Writing high-retention 5-phase script...")
    time.sleep(2)
    script = animal_channel.generate_animal_script(
        topic_subject=subject,
        hook_angle=hook_angle,
        language="en",
    )
    logger.info(f"Generated Script:\n{script}")

    # Step 3: Wildlife Visual Keywords Extraction
    logger.info("Extracting visual search keywords for stock footage...")
    time.sleep(2)
    terms = animal_channel.extract_animal_visual_terms(
        script=script,
        target_animal=target_animal,
        amount=6,
    )
    logger.info(f"Visual Terms: {terms}")

    # Step 4: SEO Metadata (Title, Description, Hashtags)
    logger.info("Generating viral YouTube Shorts metadata...")
    time.sleep(2)
    metadata = animal_channel.generate_youtube_shorts_metadata(
        video_subject=subject,
        script=script,
        short_title=short_title,
    )
    logger.info(f"Shorts Title: {metadata['title']}")
    logger.info(f"Tags: {metadata['tags']}")

    if dry_run:
        logger.warning("Dry-run mode enabled. Skipping video rendering and upload.")
        return {
            "topic": topic_data,
            "script": script,
            "terms": terms,
            "metadata": metadata,
            "status": "dry_run_complete",
        }

    # Step 5: Render Video via Core Engine
    task_id = utils.get_uuid()
    logger.info(f"Creating video rendering task: {task_id}")

    params = VideoParams(
        video_subject=subject,
        video_script=script,
        video_terms=terms,
        video_aspect=VideoAspect.portrait,  # 9:16
        video_concat_mode=VideoConcatMode.sequential,
        video_clip_duration=4,
        video_clip_speed=1.0,
        match_materials_to_script=True,
        video_count=1,
        video_source=video_source,
        video_language="en",
        voice_name=voice_name,
        voice_volume=1.0,
        voice_rate=voice_rate,
        bgm_type="random",
        bgm_volume=bgm_volume,
        subtitle_enabled=True,
        subtitle_position="bottom",
        custom_position=75.0,
        subtitle_display_mode="sentence",
        subtitle_animation="pop_spring",
        font_size=60,
        text_fore_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=2.0,
        n_threads=2,
    )

    result = task_service.start(task_id, params, stop_at="video")
    if not result or not result.get("videos"):
        error_msg = f"Task {task_id} failed to produce video output."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    final_video_path = result["videos"][0]
    logger.success(f"🎬 Video generated successfully: {final_video_path}")

    # Step 6: Direct YouTube Upload
    upload_result = None
    if not no_upload:
        logger.info("🚀 Uploading Short directly to YouTube Data API v3...")
        try:
            upload_result = upload_video_to_youtube(
                video_path=final_video_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category_id="15",  # 15 = Pets & Animals
                privacy_status=privacy_status,
                made_for_kids=False,
            )
        except Exception as exc:
            logger.error(f"YouTube upload failed: {exc}")
            upload_result = {"success": False, "error": str(exc)}
    else:
        logger.info("Upload skipped due to --no-upload flag.")
        upload_result = {"success": True, "skipped": True}

    # Step 7: Record History
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "task_id": task_id,
        "subject": subject,
        "title": metadata["title"],
        "video_path": final_video_path,
        "youtube_video_id": upload_result.get("video_id") if upload_result else None,
        "youtube_url": upload_result.get("video_url") if upload_result else None,
        "privacy_status": privacy_status,
        "terms": terms,
        "upload_status": upload_result.get("success", False) if upload_result else False,
    }
    save_history_record(record)

    logger.success("✨ Autonomous Animal Shorts pipeline completed!")
    return record


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Animal & Nature YouTube Shorts Generator & Publisher"
    )
    parser.add_argument("--topic", default=None, help="Custom animal/nature topic override")
    parser.add_argument("--pillar", default=None, help="Content pillar id (superpowers, intelligence, deep_sea, etc.)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"TTS Voice name (default: {DEFAULT_VOICE})")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="YouTube privacy status")
    parser.add_argument("--source", default="pexels", help="Video source (pexels, pixabay, coverr, local)")
    parser.add_argument("--voice-rate", type=float, default=float(os.getenv("VOICE_RATE", "0.8")), help="Voiceover speech rate multiplier (default: 0.8)")
    parser.add_argument("--bgm-volume", type=float, default=float(os.getenv("BGM_VOLUME", "0.08")), help="Background music volume multiplier (default: 0.08)")
    parser.add_argument("--dry-run", action="store_true", help="Generate topic and script only without rendering")
    parser.add_argument("--no-upload", action="store_true", help="Render video without uploading to YouTube")

    args = parser.parse_args()
    privacy_val = (args.privacy or "public").strip("'\"").strip()
    topic_val = args.topic.strip("'\"").strip() if args.topic else None

    try:
        record = run_animal_shorts_pipeline(
            custom_topic=topic_val,
            pillar_id=args.pillar,
            voice_name=args.voice,
            voice_rate=args.voice_rate,
            bgm_volume=args.bgm_volume,
            privacy_status=privacy_val,
            video_source=args.source,
            dry_run=args.dry_run,
            no_upload=args.no_upload,
        )
        print(json.dumps(record, indent=2))
    except Exception as exc:
        logger.exception(f"Pipeline failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
