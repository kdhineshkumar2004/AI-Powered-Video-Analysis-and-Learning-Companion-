from flask import Flask, request, jsonify, send_file, render_template
from main_script import extract_video_id, get_video_info, download_youtube_video, extract_detailed_transcript, extract_frames, generate_pdf  
import os
import shutil
import logging

app = Flask(__name__)

# Render the frontend
@app.route('/')
def index():
    return render_template('index.html')

# API route for analyzing the YouTube video
@app.route('/analyze', methods=['POST'])
def analyze_video():
    try:
        youtube_url = request.json.get('url')
        if not youtube_url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        output_folder = f"analysis_{video_id}"
        os.makedirs(output_folder, exist_ok=True)

        video_info = get_video_info(youtube_url)
        if video_info['length'] > 7200:  # 60 minutes
            return jsonify({'error': 'Video duration exceeds 2 hours'}), 400

        video_path = os.path.join(output_folder, "video.mp4")
        download_youtube_video(youtube_url, video_path)

        transcript = extract_detailed_transcript(video_id)
        if not transcript:
            return jsonify({'error': 'No transcript available for this video'}), 400

        frames, timestamps = extract_frames(video_path)
        if not frames:
            return jsonify({'error': 'Error extracting frames from the video'}), 500

        pdf_path = os.path.join(output_folder, "analysis.pdf")
        success = generate_pdf(video_info, transcript, frames, timestamps, pdf_path)
        if not success:
            return jsonify({'error': 'Error generating the PDF'}), 500

        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        logging.error(f"Error analyzing video: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        try:
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
        except Exception as cleanup_error:
            logging.error(f"Error cleaning up: {cleanup_error}")

if __name__ == '__main__':
    app.run(debug=True)
