from flask import Flask, request, render_template, send_file, abort
import yt_dlp
import os
import re
import threading
import time
import subprocess

app = Flask(__name__)

def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form['url']
    quality = request.form['quality']
    start_time = request.form.get('start_time', '') or '00:00:00'  # Default start time if not provided

    ydl_opts = {
        'format': quality,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            duration_seconds = str(video_info.get('duration', 0))
            end_time = request.form.get('end_time', '') or duration_seconds
            

            ydl_opts['outtmpl'] = f"downloads/%(title)s.%(ext)s"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                video_info = ydl.extract_info(url, download=False)
                video_title = sanitize_filename(video_info['title'])
                video_ext = video_info['ext']
                original_file = f"downloads/{video_title}.{video_ext}"

                
                if not os.path.isfile(original_file):
                    print(f"File not found: {original_file}")
                    abort(404, description="File not found")

                if start_time != '00:00:00' or end_time != duration_seconds:
                    trimmed_file = trim_video(original_file, start_time, end_time)
                    file_path = trimmed_file
                else:
                    file_path = original_file

                print(f"Sending file: {file_path}")
                
                schedule_deletion(file_path , original_file)
                return send_file(file_path, as_attachment=True)

    except Exception as e:
        print(f"Error: {e}")
        abort(500, description="An error occurred while downloading the video")

def trim_video(input_file, start_time, end_time):
    
    output_file = os.path.splitext(input_file)[0] + "_trimmed" + os.path.splitext(input_file)[1]

    
    cmd = [
        'ffmpeg', '-i', input_file,
        '-ss', start_time, '-to', end_time,
        '-c:v', 'copy', '-c:a', 'copy',
        '-strict', 'experimental', output_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Trimmed video saved: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error trimming video: {e}")
        raise RuntimeError("Failed to trim video")

def schedule_deletion(file_path , original_file):
    def delete_file(file_path):
        time.sleep(30)  
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                os.remove(original_file)

                print(f"Deleted video: {file_path}")
        except Exception as e:
            print(f"Error deleting video: {e}")

    # Start deletion thread
    deletion_thread = threading.Thread(target=delete_file, args=(file_path,))
    deletion_thread.start()

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(debug=True, port=8080)
