import os
import cv2
import time
import logging
import shutil
import numpy as np
from PIL import Image as PILImage
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from reportlab.lib import utils
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import yt_dlp as youtube_dl

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
FRAME_INTERVAL = 2  # Capture frame every 2 seconds
MAX_IMAGE_SIZE = (800, 600)  # Maximum image dimensions
IMAGE_QUALITY = 85  # JPEG quality


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname == "youtu.be":
            return parsed_url.path[1:]
        if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                return parse_qs(parsed_url.query)["v"][0]
            if parsed_url.path[:7] == "/embed/":
                return parsed_url.path.split("/")[2]
            if parsed_url.path[:3] == "/v/":
                return parsed_url.path.split("/")[2]
    except Exception as e:
        logging.error(f"Error extracting video ID: {e}")
        return None
    return None


def get_video_info(url):
    """Get video information using yt-dlp."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Untitled"),
                "author": info.get("uploader", "Unknown"),
                "length": info.get("duration", 0),
                "description": info.get("description", ""),
                "url": url,
            }
    except Exception as e:
        logging.error(f"Error getting video info: {e}")
        raise


def download_youtube_video(url, output_path):
    """Download YouTube video using yt-dlp."""
    ydl_opts = {
        "format": "best[height<=720]",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise


def process_frame(frame):
    """Process and optimize a single frame."""
    try:
        frame = cv2.resize(frame, MAX_IMAGE_SIZE, interpolation=cv2.INTER_AREA)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image and optimize
        image = PILImage.fromarray(frame_rgb)
        image = image.convert("RGB")

        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
        img_byte_arr.seek(0)

        return img_byte_arr
    except Exception as e:
        logging.error(f"Error processing frame: {e}")
        return None


def extract_frames(video_path):
    """Extract frames from video."""
    frames = []
    timestamps = []

    try:
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_count / fps
            if current_time % FRAME_INTERVAL == 0:
                processed_frame = process_frame(frame)
                if processed_frame:
                    frames.append(processed_frame)
                    timestamps.append(current_time)

            frame_count += 1

        cap.release()
        return frames, timestamps
    except Exception as e:
        logging.error(f"Error extracting frames: {e}")
        return [], []


def extract_detailed_transcript(video_id):
    """Extract and process video transcript."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        detailed_transcript = []

        for entry in transcript:
            start_time = int(entry["start"])
            duration = max(1, int(entry["duration"]))  # Ensure duration is at least 1
            text = entry["text"]

            words = text.split()
            if not words:  # Skip empty entries
                continue

            words_per_second = max(1, len(words) // duration)

            for second in range(duration):
                current_time = start_time + second
                word_start = min(second * words_per_second, len(words))
                word_end = min((second + 1) * words_per_second, len(words))

                current_text = " ".join(words[word_start:word_end])

                if current_text.strip():
                    detailed_transcript.append(
                        {
                            "start": current_time,
                            "text": current_text,
                        }
                    )

        return sorted(detailed_transcript, key=lambda x: x["start"])
    except Exception as e:
        logging.error(f"Error fetching transcript: {e}")
        return []


def generate_pdf(video_info, transcript, frames, timestamps, output_path):
    """Generate PDF with video content."""
    try:
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Add title
        story.append(Paragraph(video_info["title"], styles["Title"]))

        # Add video information
        story.append(
            Paragraph(
                f"Author: {video_info['author']}<br/>Duration: {video_info['length']} seconds",
                styles["Normal"],
            )
        )

        # Add transcript and frames
        frame_index = 0
        for entry in transcript:
            timestamp = entry["start"]
            story.append(Paragraph(f"[{timestamp}s] {entry['text']}", styles["Normal"]))

            while frame_index < len(frames) and timestamps[frame_index] <= timestamp:
                img_data = frames[frame_index]
                img = utils.ImageReader(img_data)
                img_width, img_height = img.getSize()
                aspect = img_height / float(img_width)

                img_width = doc.width
                img_height = img_width * aspect

                story.append(Image(img_data, width=img_width, height=img_height))
                story.append(Spacer(1, 10))
                frame_index += 1

        doc.build(story)
        return True
    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return False
