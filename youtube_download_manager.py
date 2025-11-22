#!/usr/bin/env python3
"""
YouTube Download Manager
Manages parallel YouTube audio downloads with queue, retry logic, and comprehensive logging.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
import yt_dlp

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of a download task."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """Represents a YouTube download task."""
    video_id: str
    video_url: str
    cache_file: Path
    status: DownloadStatus = DownloadStatus.QUEUED
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_size_bytes: int = 0


class YouTubeDownloadManager:
    """
    Manages parallel YouTube audio downloads with queue and retry logic.
    """
    
    def __init__(
        self,
        cache_dir: Path,
        youtube_cache_manager,
        max_parallel: int = 3,
        download_timeout: int = 300
    ):
        """
        Initialize download manager.
        
        Args:
            cache_dir: Directory to store cached files
            youtube_cache_manager: YouTubeCacheManager instance for LRU management
            max_parallel: Maximum number of parallel downloads
            download_timeout: Timeout for individual downloads in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.youtube_cache = youtube_cache_manager
        self.max_parallel = max(1, min(10, max_parallel))  # Clamp between 1-10
        self.download_timeout = download_timeout
        
        # Download tracking
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.download_queue: asyncio.Queue = asyncio.Queue()
        self.download_locks: Dict[str, asyncio.Lock] = {}
        self.download_semaphore = asyncio.Semaphore(self.max_parallel)
        
        # Statistics
        self.total_downloads = 0
        self.successful_downloads = 0
        self.failed_downloads = 0
        
        # Worker tasks
        self.workers: list[asyncio.Task] = []
        self.running = False
        
        logger.info(
            f"🔧 [DOWNLOAD-MGR] Initialized with max_parallel={self.max_parallel}, "
            f"timeout={self.download_timeout}s"
        )
    
    async def start_workers(self):
        """Start background worker tasks for processing downloads."""
        if self.running:
            return
        
        self.running = True
        self.workers = [
            asyncio.create_task(self._download_worker(i))
            for i in range(self.max_parallel)
        ]
        logger.info(f"🔧 [DOWNLOAD-MGR] Started {self.max_parallel} worker tasks")
    
    async def stop_workers(self):
        """Stop all background worker tasks."""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("🔧 [DOWNLOAD-MGR] Stopped all worker tasks")
    
    async def _download_worker(self, worker_id: int):
        """
        Background worker that processes download tasks from the queue.
        
        Args:
            worker_id: Unique identifier for this worker
        """
        logger.info(f"👷 [WORKER-{worker_id}] Started")
        
        while self.running:
            try:
                # Get next task from queue (with timeout to allow checking running flag)
                try:
                    task = await asyncio.wait_for(
                        self.download_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the download
                logger.info(
                    f"👷 [WORKER-{worker_id}] Processing {task.video_id} "
                    f"(attempt {task.attempts + 1}/{task.max_attempts})"
                )
                
                async with self.download_semaphore:
                    await self._execute_download(task, worker_id)
                
                # Mark task as done
                self.download_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info(f"👷 [WORKER-{worker_id}] Cancelled")
                break
            except Exception as e:
                logger.error(f"👷 [WORKER-{worker_id}] Unexpected error: {e}")
        
        logger.info(f"👷 [WORKER-{worker_id}] Stopped")
    
    async def _execute_download(self, task: DownloadTask, worker_id: int):
        """
        Execute the actual download for a task.
        
        Args:
            task: Download task to execute
            worker_id: ID of the worker executing this download
        """
        task.attempts += 1
        task.status = DownloadStatus.DOWNLOADING
        task.started_at = datetime.utcnow()
        
        log_prefix = f"⬇️  [WORKER-{worker_id}|{task.video_id}]"
        
        try:
            logger.info(f"{log_prefix} Starting download (attempt {task.attempts}/{task.max_attempts})")
            
            # Clean up any partial downloads
            for pattern in [f"{task.video_id}*"]:
                for old_file in self.cache_dir.glob(pattern):
                    if '.part' in old_file.name or '.ytdl' in old_file.name or 'Frag' in old_file.name:
                        try:
                            old_file.unlink()
                            logger.debug(f"{log_prefix} Cleaned up: {old_file.name}")
                        except Exception as e:
                            logger.warning(f"{log_prefix} Could not delete {old_file.name}: {e}")
            
            # Cleanup cache if needed (estimate 10MB for new file)
            self.youtube_cache.cleanup_if_needed(10 * 1024 * 1024)
            
            # Download with yt-dlp
            def download_audio():
                ydl_opts = {
                    # Prefer smaller audio formats: opus (best compression), m4a, then fallback
                    'format': 'bestaudio[ext=opus]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                    'outtmpl': str(task.cache_file.with_suffix('.%(ext)s')),
                    'quiet': False,
                    'no_warnings': False,
                    'logger': logger,
                    # Enhanced extractor args to bypass YouTube blocks
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web'],  # Try android client first, fallback to web
                            'player_skip': ['webpage', 'configs'],  # Skip unnecessary fetches
                        }
                    },
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    },
                    'nocheckcertificate': True,
                    'geo_bypass': True,
                    'prefer_free_formats': True,
                    'postprocessors': [],
                    # Retry settings
                    'retries': 3,
                    'fragment_retries': 5,
                    'skip_unavailable_fragments': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(task.video_url, download=True)
            
            # Run download with timeout
            info = await asyncio.wait_for(
                asyncio.to_thread(download_audio),
                timeout=self.download_timeout
            )
            
            if not info:
                raise Exception("yt-dlp returned no info")
            
            # Find the downloaded file
            cache_file = task.cache_file
            if not cache_file.exists():
                for ext in ['.webm', '.m4a', '.mp4', '.opus', '.ogg']:
                    alt_file = cache_file.with_suffix(ext)
                    if alt_file.exists():
                        cache_file = alt_file
                        logger.debug(f"{log_prefix} Found file with extension: {ext}")
                        break
            
            if not cache_file.exists():
                raise Exception("Downloaded file not found")
            
            # Verify file is not empty
            file_size = cache_file.stat().st_size
            if file_size == 0:
                cache_file.unlink()
                raise Exception("Downloaded file is empty")
            
            file_size_mb = file_size / 1024 / 1024
            task.file_size_bytes = file_size
            
            # Add to cache manager
            self.youtube_cache.add_file(task.video_id, cache_file.name, file_size)
            
            # Mark as completed
            task.status = DownloadStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Update statistics
            self.total_downloads += 1
            self.successful_downloads += 1
            
            duration = (task.completed_at - task.started_at).total_seconds()
            logger.info(
                f"{log_prefix} ✅ Download completed: {cache_file.name} "
                f"({file_size_mb:.2f} MB in {duration:.1f}s)"
            )
            
        except asyncio.TimeoutError:
            task.status = DownloadStatus.FAILED
            task.error = f"Download timeout after {self.download_timeout}s"
            logger.error(f"{log_prefix} ❌ Timeout after {self.download_timeout}s")
            
            # Retry if attempts remaining
            if task.attempts < task.max_attempts:
                logger.info(f"{log_prefix} Retrying... ({task.attempts}/{task.max_attempts})")
                await self.download_queue.put(task)
            else:
                self.total_downloads += 1
                self.failed_downloads += 1
                logger.error(f"{log_prefix} ❌ Failed after {task.max_attempts} attempts")
            
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            logger.error(f"{log_prefix} ❌ Error: {e}")
            
            # Clean up failed files
            for ext in ['.webm', '.m4a', '.mp4', '.opus', '.ogg']:
                failed_file = task.cache_file.with_suffix(ext)
                if failed_file.exists():
                    try:
                        failed_file.unlink()
                        logger.debug(f"{log_prefix} Cleaned up failed file: {failed_file.name}")
                    except:
                        pass
            
            # Retry if attempts remaining
            if task.attempts < task.max_attempts:
                # Exponential backoff before retry
                backoff_delay = min(2 ** task.attempts, 30)  # Max 30 seconds
                logger.info(
                    f"{log_prefix} Retrying in {backoff_delay}s... "
                    f"({task.attempts}/{task.max_attempts})"
                )
                await asyncio.sleep(backoff_delay)
                await self.download_queue.put(task)
            else:
                self.total_downloads += 1
                self.failed_downloads += 1
                logger.error(f"{log_prefix} ❌ Failed after {task.max_attempts} attempts: {e}")
        
        finally:
            # Remove from active downloads
            if task.video_id in self.active_downloads:
                del self.active_downloads[task.video_id]
    
    async def download_video(
        self,
        video_id: str,
        priority: bool = False
    ) -> Optional[Path]:
        """
        Queue a video for download or return cached file if available.
        
        Args:
            video_id: YouTube video ID
            priority: If True, add to front of queue
            
        Returns:
            Path to cached file if already available, None if queued for download
        """
        # Check if already cached
        cached_file = self.youtube_cache.get_cached_file(video_id)
        if cached_file:
            logger.debug(f"📦 [DOWNLOAD-MGR] {video_id} already cached")
            return cached_file
        
        # Check if already downloading or queued
        if video_id in self.active_downloads:
            logger.debug(f"⏳ [DOWNLOAD-MGR] {video_id} already in queue/downloading")
            return None
        
        # Create download task
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        cache_file = self.cache_dir / f"{video_id}.webm"
        
        task = DownloadTask(
            video_id=video_id,
            video_url=video_url,
            cache_file=cache_file
        )
        
        self.active_downloads[video_id] = task
        
        # Add to queue
        if priority:
            # For priority, we'd need a priority queue - for now just add normally
            logger.info(f"🔥 [DOWNLOAD-MGR] Queuing {video_id} (priority)")
        else:
            logger.info(f"➕ [DOWNLOAD-MGR] Queuing {video_id}")
        
        await self.download_queue.put(task)
        
        return None
    
    async def download_playlist(
        self,
        video_ids: list[str],
        current_index: int = 0
    ):
        """
        Queue multiple videos for download with priority for current and next tracks.
        
        Args:
            video_ids: List of YouTube video IDs
            current_index: Index of currently playing track (gets highest priority)
        """
        if not video_ids:
            return
        
        logger.info(
            f"📋 [DOWNLOAD-MGR] Queuing playlist: {len(video_ids)} tracks, "
            f"current index: {current_index}"
        )
        
        # Download current track first (if not cached)
        if 0 <= current_index < len(video_ids):
            await self.download_video(video_ids[current_index], priority=True)
        
        # Download next 2 tracks with priority
        for i in range(current_index + 1, min(current_index + 3, len(video_ids))):
            await self.download_video(video_ids[i], priority=True)
        
        # Queue remaining tracks in background
        for i, video_id in enumerate(video_ids):
            if i < current_index or i >= current_index + 3:
                await self.download_video(video_id, priority=False)
    
    def get_download_status(self, video_id: str) -> Optional[DownloadTask]:
        """Get status of a download task."""
        return self.active_downloads.get(video_id)
    
    def get_statistics(self) -> Dict:
        """Get download statistics."""
        active_count = len([
            t for t in self.active_downloads.values()
            if t.status == DownloadStatus.DOWNLOADING
        ])
        queued_count = len([
            t for t in self.active_downloads.values()
            if t.status == DownloadStatus.QUEUED
        ])
        
        return {
            'total_downloads': self.total_downloads,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'success_rate': (
                self.successful_downloads / self.total_downloads * 100
                if self.total_downloads > 0 else 0
            ),
            'active_downloads': active_count,
            'queued_downloads': queued_count,
            'max_parallel': self.max_parallel,
        }
    
    def update_max_parallel(self, new_max: int):
        """
        Update maximum parallel downloads.
        Note: Requires restart of workers to take effect.
        
        Args:
            new_max: New maximum parallel downloads (1-10)
        """
        old_max = self.max_parallel
        self.max_parallel = max(1, min(10, new_max))
        self.download_semaphore = asyncio.Semaphore(self.max_parallel)
        
        logger.info(
            f"🔧 [DOWNLOAD-MGR] Max parallel downloads updated: {old_max} → {self.max_parallel}"
        )
