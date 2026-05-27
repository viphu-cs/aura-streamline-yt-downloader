import sys
import os
import logging

# Reconfigure stdout/stderr to UTF-8 to prevent encoding issues when printing Thai characters on Windows command prompt
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass # Older python versions might not support reconfigure

logging.basicConfig(level=logging.INFO)

# Append workspace path to ensure local modules can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from downloader import YTDownloader

def main():
    print("Testing YTDownloader initialization...")
    downloader = YTDownloader()
    
    print("\n1. Checking local/system FFmpeg status...")
    has_ffmpeg = downloader.check_ffmpeg()
    print(f"Has FFmpeg already: {has_ffmpeg}")
    
    if not has_ffmpeg:
        print("\n2. Testing automated FFmpeg download...")
        def progress_cb(status, percent, msg):
            print(f"[{status.upper()}] {percent}% - {msg}")
            
        success = downloader.download_ffmpeg(progress_callback=progress_cb)
        print(f"\nFFmpeg installation success: {success}")
        print(f"FFmpeg binary exists: {os.path.exists(downloader.ffmpeg_path)}")
        print(f"FFprobe binary exists: {os.path.exists(downloader.ffprobe_path)}")
        
        # Re-check
        print(f"Re-check check_ffmpeg(): {downloader.check_ffmpeg()}")
    else:
        print("\nFFmpeg already installed. Skipping download test.")
        
    print("\n3. Testing YouTube video metadata fetching...")
    # Fetch a short, public domain or extremely standard video (e.g., standard YouTube video)
    test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"  # Big Buck Bunny
    try:
        info = downloader.fetch_video_info(test_url)
        parsed = downloader.parse_formats(info)
        print("\nSuccessfully fetched video metadata!")
        print(f"Title: {parsed['title']}")
        print(f"Channel: {parsed['channel']}")
        print(f"Duration: {parsed['duration']} seconds")
        print("\nAvailable resolutions:")
        for res in parsed['resolutions']:
            print(f" - {res['label']} (size: {res['size_mb']:.1f} MB, format_id: {res['format_id']})")
        if parsed['best_audio']:
            print(f"Best Audio: {parsed['best_audio']['abr']} kbps")
    except Exception as e:
        print(f"\nError fetching metadata: {e}")

if __name__ == "__main__":
    main()
