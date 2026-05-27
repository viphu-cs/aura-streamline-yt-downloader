import os
import sys
import zipfile
import requests
import threading
import logging
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YTDownloader:
    FFMPEG_ZIP_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    def __init__(self, download_dir=None):
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.bin_dir = os.path.join(self.project_dir, "bin")
        
        # Set default download directory to User's Downloads folder if not specified
        if not download_dir:
            self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            self.download_dir = download_dir
            
        os.makedirs(self.bin_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Setup paths for FFmpeg
        self.ffmpeg_path = os.path.join(self.bin_dir, "ffmpeg.exe")
        self.ffprobe_path = os.path.join(self.bin_dir, "ffprobe.exe")
        
    def check_ffmpeg(self):
        """Check if FFmpeg and FFprobe are available either in PATH or in the local bin folder."""
        # Check system PATH first
        import shutil
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            logging.info("FFmpeg found in system PATH.")
            return True
            
        # Check local bin directory
        if os.path.exists(self.ffmpeg_path) and os.path.exists(self.ffprobe_path):
            logging.info(f"FFmpeg found in local bin directory: {self.bin_dir}")
            return True
            
        return False
        
    def download_ffmpeg(self, progress_callback=None):
        """Downloads the static FFmpeg package for Windows and extracts ffmpeg.exe and ffprobe.exe."""
        if self.check_ffmpeg():
            if progress_callback:
                progress_callback("ready", 100, "FFmpeg is already installed.")
            return True
            
        logging.info("FFmpeg not found. Starting download...")
        if progress_callback:
            progress_callback("downloading", 0, "กำลังดาวน์โหลด FFmpeg (สำหรับรวมไฟล์ความละเอียดสูง)...")
            
        zip_path = os.path.join(self.bin_dir, "ffmpeg.zip")
        
        try:
            # Download file using requests with stream
            response = requests.get(self.FFMPEG_ZIP_URL, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            percent = int((downloaded / total_size) * 100)
                            progress_callback("downloading", percent, f"กำลังดาวน์โหลด FFmpeg: {percent}% ({downloaded/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB)")
            
            if progress_callback:
                progress_callback("extracting", 95, "กำลังติดตั้ง FFmpeg...")
                
            logging.info("FFmpeg downloaded successfully. Extracting binaries...")
            
            # Extract only ffmpeg.exe and ffprobe.exe
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    filename = file_info.filename
                    if filename.endswith("ffmpeg.exe"):
                        # Extract as ffmpeg.exe directly to bin
                        with zip_ref.open(file_info) as source, open(self.ffmpeg_path, 'wb') as target:
                            target.write(source.read())
                        logging.info("Extracted ffmpeg.exe")
                    elif filename.endswith("ffprobe.exe"):
                        # Extract as ffprobe.exe directly to bin
                        with zip_ref.open(file_info) as source, open(self.ffprobe_path, 'wb') as target:
                            target.write(source.read())
                        logging.info("Extracted ffprobe.exe")
                        
            # Clean up the zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            logging.info("FFmpeg installed successfully.")
            if progress_callback:
                progress_callback("ready", 100, "ติดตั้ง FFmpeg สำเร็จ!")
            return True
            
        except Exception as e:
            logging.error(f"Failed to download/install FFmpeg: {e}")
            if progress_callback:
                progress_callback("error", 0, f"เกิดข้อผิดพลาดในการติดตั้ง FFmpeg: {str(e)}")
            if os.path.exists(zip_path):
                try: os.remove(zip_path)
                except: pass
            return False

    def get_ffmpeg_dir(self):
        """Returns the directory containing FFmpeg, or None if it should use system PATH."""
        # If we have it locally, return local bin folder
        if os.path.exists(self.ffmpeg_path) and os.path.exists(self.ffprobe_path):
            return self.bin_dir
        return None

    def fetch_video_info(self, url):
        """Fetches metadata for a YouTube URL (video or playlist)."""
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'ffmpeg_location': self.get_ffmpeg_dir(),
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return info
            except Exception as e:
                logging.error(f"Error fetching video info: {e}")
                raise e

    def parse_formats(self, info):
        """Parses available formats from video info to show user-friendly resolution options."""
        if 'entries' in info:
            # It's a playlist, return info as is
            return {"type": "playlist", "title": info.get('title'), "entries": list(info.get('entries', []))}
            
        formats = info.get('formats', [])
        title = info.get('title')
        thumbnail = info.get('thumbnail')
        duration = info.get('duration')
        channel = info.get('uploader')
        
        # We want to group by resolution: 1080p, 720p, 480p, 360p, and audio only
        # YouTube separates high-quality video and audio, so we'll present:
        # - Best video+audio combined (if any, usually max 720p)
        # - High quality video-only streams, which we will merge with the best audio stream
        # Let's map resolution height to names
        resolutions = {}
        
        # Audio formats
        audio_formats = []
        
        for f in formats:
            # Check if audio only
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                audio_formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'abr': f.get('abr', 0) or 0,
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                })
                continue
                
            # Check if video format
            height = f.get('height')
            if height:
                res_name = f"{height}p"
                fps = f.get('fps', '')
                if fps and fps > 30:
                    res_name += f"{fps}"
                    
                # We want to keep the best quality format for each resolution height
                codec = f.get('vcodec', '')
                # Prioritize mp4/avc1 or vp9/webm
                # We store format info
                if res_name not in resolutions:
                    resolutions[res_name] = []
                    
                resolutions[res_name].append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'height': height,
                    'vcodec': codec,
                    'acodec': f.get('acodec', 'none'),
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                    'fps': f.get('fps'),
                })
                
        # Now, let's select the best format for each standard resolution category
        best_resolutions = {}
        standard_heights = [144, 240, 360, 480, 720, 1080, 1440, 2160]
        
        for res_name, stream_list in resolutions.items():
            # Extract height integer
            try:
                h = int(''.join(filter(str.isdigit, res_name)))
            except:
                continue
                
            # Find the best one in stream_list (e.g. largest filesize or mp4)
            best_stream = max(stream_list, key=lambda x: (x['filesize'], x['ext'] == 'mp4'))
            
            # Label
            label = f"{h}p"
            if best_stream['fps'] and best_stream['fps'] > 30:
                label += f"{int(best_stream['fps'])}"
                
            # Estimate size
            size_mb = best_stream['filesize'] / (1024 * 1024) if best_stream['filesize'] else 0
            
            best_resolutions[h] = {
                'label': label,
                'height': h,
                'format_id': best_stream['format_id'],
                'ext': best_stream['ext'],
                'acodec': best_stream['acodec'],
                'size_mb': size_mb,
            }
            
        # Sort resolutions descending
        sorted_res = sorted(best_resolutions.values(), key=lambda x: x['height'], reverse=True)
        
        # Best audio
        best_audio = None
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: (x['abr'], x['filesize']))
            
        return {
            "type": "video",
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "channel": channel,
            "resolutions": sorted_res,
            "best_audio": best_audio,
        }

    def download_video(self, url, format_id, is_audio=False, progress_hook=None, postprocess_hook=None):
        """Downloads a video with the specified format_id and merges with audio if necessary."""
        # Verify FFmpeg is downloaded if downloading high res or audio conversion is needed
        self.download_ffmpeg()
        
        ffmpeg_dir = self.get_ffmpeg_dir()
        
        ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_dir,
            'progress_hooks': [progress_hook] if progress_hook else [],
            'postprocessor_hooks': [postprocess_hook] if postprocess_hook else [],
        }
        
        if is_audio:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # Check if format_id already has video and audio specified (e.g. has '+' inside)
            if '+' in str(format_id):
                ydl_opts['format'] = format_id
            else:
                # Prioritize m4a audio stream (AAC) which is 100% compatible with Windows Media Player / native players
                # and fall back to bestaudio or best if m4a isn't available
                ydl_opts['format'] = f'{format_id}+bestaudio[ext=m4a]/bestaudio/best'
                
            ydl_opts['merge_output_format'] = 'mp4'
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                # Return final downloaded path
                filename = ydl.prepare_filename(info)
                # If audio extraction was done, ext changes to mp3
                if is_audio:
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                return filename
            except Exception as e:
                logging.error(f"Download failed: {e}")
                raise e
