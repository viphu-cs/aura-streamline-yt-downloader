import queue
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor

class DownloadQueueManager:
    def __init__(self, downloader, history_db, on_update_callback=None):
        self.downloader = downloader
        self.history_db = history_db
        self.on_update_callback = on_update_callback
        
        # Thread-safe structures
        self.items = [] # List to preserve order and store metadata of all items (active & completed)
        self.item_map = {} # Map of uuid -> item dict
        self.download_queue = queue.Queue()
        
        self.worker_thread = None
        self.is_running = False
        self.current_item_id = None
        self.cancel_requested = False

    def add_item(self, title, url, format_id, format_label, is_audio, size="Unknown"):
        """Adds a new item to the manager list and queues it for downloading."""
        item_id = str(uuid.uuid4())
        item = {
            "id": item_id,
            "title": title,
            "url": url,
            "format_id": format_id,
            "format_label": format_label,
            "is_audio": is_audio,
            "status": "Waiting",
            "progress": 0,
            "speed": "0 KB/s",
            "eta": "Waiting",
            "size": size,
            "file_path": None,
            "error_msg": None
        }
        self.items.append(item)
        self.item_map[item_id] = item
        
        # Queue the ID to be processed sequentially
        self.download_queue.put(item_id)
        
        logging.info(f"Queued item: {title}")
        self.trigger_update()
        
        # Auto-start worker if not already running
        if not self.is_running:
            self.start_worker()
            
        return item_id

    def trigger_update(self):
        """Calls the update callback to refresh the UI."""
        if self.on_update_callback:
            # We schedule this inside the UI thread if possible,
            # or just call it directly (we'll make sure UI side handles it thread-safely)
            try:
                self.on_update_callback()
            except Exception as e:
                logging.error(f"Error executing queue update callback: {e}")

    def start_worker(self):
        """Starts the background worker thread if not running."""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logging.info("Queue worker thread started.")

    def stop_worker(self):
        """Stops the worker thread."""
        self.is_running = False
        # Send sentinel to queue to unblock it if it's waiting
        self.download_queue.put(None)
        
    def cancel_item(self, item_id):
        """Cancels a waiting or downloading item."""
        if item_id not in self.item_map:
            return
            
        item = self.item_map[item_id]
        
        if item["status"] == "Waiting":
            item["status"] = "Cancelled"
            item["eta"] = "Cancelled"
            logging.info(f"Cancelled waiting item: {item['title']}")
            self.trigger_update()
        elif item["id"] == self.current_item_id:
            # For the currently downloading item, we'll signal cancellation
            # yt-dlp doesn't have an easy cancel mid-download unless we raise an exception or kill its subprocess
            # Let's set cancel flag which can be checked inside the progress hook
            self.cancel_requested = True
            item["status"] = "Cancelling..."
            logging.info(f"Requesting cancellation for active download: {item['title']}")
            self.trigger_update()

    def _progress_hook(self, d):
        """yt-dlp progress hook called during download."""
        if not self.current_item_id or self.current_item_id not in self.item_map:
            return
            
        item = self.item_map[self.current_item_id]
        
        # Check if cancellation requested
        if self.cancel_requested:
            raise Exception("Download cancelled by user")
            
        if d['status'] == 'downloading':
            # Parse progress
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            
            percent = 0
            if total > 0:
                percent = int((downloaded / total) * 100)
                
            speed = d.get('speed')
            speed_str = "0 KB/s"
            if speed:
                if speed > 1024*1024:
                    speed_str = f"{speed / (1024*1024):.1f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                    
            eta = d.get('eta')
            eta_str = "--:--"
            if eta:
                mins, secs = divmod(eta, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    eta_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
                else:
                    eta_str = f"{mins:02d}:{secs:02d}"
                    
            total_mb = total / (1024 * 1024) if total else 0
            size_str = f"{total_mb:.1f} MB" if total_mb else "Unknown"
            
            # Update item
            item["status"] = "Downloading"
            item["progress"] = percent
            item["speed"] = speed_str
            item["eta"] = eta_str
            if size_str != "Unknown":
                item["size"] = size_str
                
            self.trigger_update()
            
        elif d['status'] == 'finished':
            # Note: finished means the downloading part of this specific stream is done.
            # Post-processing (like merging) may still happen, which is handled in the main function.
            item["progress"] = 99
            item["status"] = "Processing..."
            item["eta"] = "Merging streams..."
            item["speed"] = "0 KB/s"
            self.trigger_update()

    def _worker_loop(self):
        """Sequential download processing loop running in background."""
        while self.is_running:
            try:
                # Wait for next item ID with timeout so thread can check is_running
                item_id = self.download_queue.get(timeout=2)
            except queue.Empty:
                continue
                
            if item_id is None:
                # Sentinel to stop worker
                break
                
            item = self.item_map.get(item_id)
            if not item or item["status"] in ("Cancelled", "Completed"):
                self.download_queue.task_done()
                continue
                
            self.current_item_id = item_id
            self.cancel_requested = False
            
            item["status"] = "Starting"
            item["eta"] = "Connecting..."
            self.trigger_update()
            
            try:
                logging.info(f"Worker starting download of: {item['title']}")
                # Run the download blocking inside this thread
                file_path = self.downloader.download_video(
                    url=item["url"],
                    format_id=item["format_id"],
                    is_audio=item["is_audio"],
                    progress_hook=self._progress_hook
                )
                
                # Check for cancellation that might have sneaked through
                if self.cancel_requested:
                    raise Exception("Download cancelled by user")
                    
                # Success
                item["status"] = "Completed"
                item["progress"] = 100
                item["speed"] = "--"
                item["eta"] = "Completed"
                item["file_path"] = file_path
                
                # Add to SQLite History DB
                # Estimate size from file if possible
                try:
                    if os.path.exists(file_path):
                        size_bytes = os.path.getsize(file_path)
                        item["size"] = f"{size_bytes / (1024*1024):.1f} MB"
                except:
                    pass
                    
                self.history_db.add_record(
                    title=item["title"],
                    url=item["url"],
                    format_name=item["format_label"],
                    file_path=file_path,
                    file_size=item["size"]
                )
                logging.info(f"Worker completed download of: {item['title']}")
                
            except Exception as e:
                logging.error(f"Worker failed download of {item['title']}: {e}")
                if self.cancel_requested or "cancelled" in str(e).lower():
                    item["status"] = "Cancelled"
                    item["progress"] = 0
                    item["speed"] = "--"
                    item["eta"] = "Cancelled"
                else:
                    item["status"] = "Failed"
                    item["progress"] = 0
                    item["speed"] = "--"
                    item["eta"] = "Failed"
                    item["error_msg"] = str(e)
                    
            self.current_item_id = None
            self.cancel_requested = False
            self.download_queue.task_done()
            self.trigger_update()
            
        self.is_running = False
        logging.info("Queue worker thread stopped.")
