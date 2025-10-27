#!/usr/bin/env python3
"""
YouTube Cache Manager
Manages YouTube audio cache with LRU (Least Recently Used) eviction policy.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class YouTubeCacheManager:
    """Manages YouTube audio cache with size limits and LRU eviction."""
    
    def __init__(self, cache_dir: str = "youtube_cache", max_size_gb: float = 5.0):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cached files
            max_size_gb: Maximum cache size in gigabytes (can use decimals, e.g., 2.5)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
        
        # Clean up orphaned files (files without metadata entries)
        self._cleanup_orphaned_files()
        
        logger.info(f"📦 [CACHE] Initialized with max size: {max_size_gb:.2f} GB ({self.max_size_bytes:,} bytes)")
    
    def _load_metadata(self) -> Dict:
        """Load cache metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    logger.info(f"📦 [CACHE] Loaded metadata for {len(metadata)} cached files")
                    return metadata
            except Exception as e:
                logger.error(f"📦 [CACHE] Error loading metadata: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """Save cache metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"📦 [CACHE] Error saving metadata: {e}")
    
    def _cleanup_orphaned_files(self):
        """Remove files that exist but aren't in metadata."""
        try:
            all_files = set(f.name for f in self.cache_dir.iterdir() if f.is_file() and f.name != 'cache_metadata.json')
            tracked_files = set(entry['filename'] for entry in self.metadata.values())
            orphaned = all_files - tracked_files
            
            if orphaned:
                logger.info(f"📦 [CACHE] Found {len(orphaned)} orphaned files, cleaning up...")
                for filename in orphaned:
                    try:
                        (self.cache_dir / filename).unlink()
                        logger.info(f"📦 [CACHE] Deleted orphaned file: {filename}")
                    except Exception as e:
                        logger.error(f"📦 [CACHE] Error deleting {filename}: {e}")
        except Exception as e:
            logger.error(f"📦 [CACHE] Error during orphan cleanup: {e}")
    
    def get_total_size(self) -> int:
        """Calculate total cache size in bytes."""
        total = 0
        for video_id, entry in self.metadata.items():
            file_path = self.cache_dir / entry['filename']
            if file_path.exists():
                total += file_path.stat().st_size
            else:
                # File missing, remove from metadata
                logger.warning(f"📦 [CACHE] File missing for {video_id}, removing from metadata")
                del self.metadata[video_id]
        
        self._save_metadata()
        return total
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_size = self.get_total_size()
        file_count = len(self.metadata)
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'total_size_gb': total_size / (1024 * 1024 * 1024),
            'max_size_bytes': self.max_size_bytes,
            'max_size_gb': self.max_size_bytes / (1024 * 1024 * 1024),
            'usage_percent': (total_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0,
            'file_count': file_count,
            'available_bytes': max(0, self.max_size_bytes - total_size),
            'available_gb': max(0, (self.max_size_bytes - total_size) / (1024 * 1024 * 1024))
        }
    
    def _get_lru_files(self) -> List[Tuple[str, Dict]]:
        """Get files sorted by last access time (oldest first)."""
        items = []
        for video_id, entry in self.metadata.items():
            items.append((video_id, entry))
        
        # Sort by last_accessed (oldest first)
        items.sort(key=lambda x: x[1]['last_accessed'])
        return items
    
    def cleanup_if_needed(self, new_file_size_estimate: int = 10 * 1024 * 1024):
        """
        Remove LRU files if cache would exceed limit.
        
        Args:
            new_file_size_estimate: Estimated size of new file to be added (default 10MB)
        """
        current_size = self.get_total_size()
        
        if current_size + new_file_size_estimate <= self.max_size_bytes:
            logger.info(f"📦 [CACHE] Space available: {(self.max_size_bytes - current_size) / (1024*1024):.2f} MB")
            return
        
        logger.info(f"📦 [CACHE] Cache cleanup needed. Current: {current_size / (1024*1024):.2f} MB, Max: {self.max_size_bytes / (1024*1024):.2f} MB")
        
        # Get files sorted by LRU
        lru_files = self._get_lru_files()
        
        # Delete files until we have enough space
        target_size = self.max_size_bytes - new_file_size_estimate
        deleted_count = 0
        freed_space = 0
        
        for video_id, entry in lru_files:
            if current_size <= target_size:
                break
            
            file_path = self.cache_dir / entry['filename']
            if file_path.exists():
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    current_size -= file_size
                    freed_space += file_size
                    deleted_count += 1
                    logger.info(f"📦 [CACHE] Deleted LRU file: {entry['filename']} ({file_size / (1024*1024):.2f} MB)")
                except Exception as e:
                    logger.error(f"📦 [CACHE] Error deleting {entry['filename']}: {e}")
            
            # Remove from metadata
            del self.metadata[video_id]
        
        self._save_metadata()
        logger.info(f"📦 [CACHE] Cleanup complete: Deleted {deleted_count} files, freed {freed_space / (1024*1024):.2f} MB")
    
    def mark_accessed(self, video_id: str):
        """Update last_accessed timestamp for a file."""
        if video_id in self.metadata:
            self.metadata[video_id]['last_accessed'] = datetime.utcnow().isoformat()
            self._save_metadata()
            logger.debug(f"📦 [CACHE] Updated access time for {video_id}")
    
    def add_file(self, video_id: str, filename: str, size_bytes: int):
        """
        Add new file to cache metadata.
        
        Args:
            video_id: YouTube video ID
            filename: Name of cached file
            size_bytes: Size of file in bytes
        """
        now = datetime.utcnow().isoformat()
        self.metadata[video_id] = {
            'filename': filename,
            'size_bytes': size_bytes,
            'last_accessed': now,
            'download_date': now
        }
        self._save_metadata()
        logger.info(f"📦 [CACHE] Added {filename} to cache ({size_bytes / (1024*1024):.2f} MB)")
    
    def get_cached_file(self, video_id: str) -> Optional[Path]:
        """
        Get cached file path if it exists.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Path to cached file or None if not found
        """
        if video_id in self.metadata:
            file_path = self.cache_dir / self.metadata[video_id]['filename']
            if file_path.exists():
                self.mark_accessed(video_id)
                return file_path
            else:
                # File missing, remove from metadata
                logger.warning(f"📦 [CACHE] Cached file missing for {video_id}, removing from metadata")
                del self.metadata[video_id]
                self._save_metadata()
        
        return None
    
    def clear_cache(self):
        """Clear entire cache (delete all files and metadata)."""
        logger.info(f"📦 [CACHE] Clearing entire cache...")
        deleted_count = 0
        
        for video_id, entry in list(self.metadata.items()):
            file_path = self.cache_dir / entry['filename']
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"📦 [CACHE] Error deleting {entry['filename']}: {e}")
        
        self.metadata = {}
        self._save_metadata()
        logger.info(f"📦 [CACHE] Cache cleared: Deleted {deleted_count} files")
    
    def update_max_size(self, new_max_size_gb: float):
        """
        Update maximum cache size and cleanup if needed.
        
        Args:
            new_max_size_gb: New maximum size in gigabytes
        """
        old_size_gb = self.max_size_bytes / (1024 * 1024 * 1024)
        self.max_size_bytes = int(new_max_size_gb * 1024 * 1024 * 1024)
        
        logger.info(f"📦 [CACHE] Max size updated: {old_size_gb:.2f} GB → {new_max_size_gb:.2f} GB")
        
        # If new size is smaller, cleanup immediately
        if new_max_size_gb < old_size_gb:
            self.cleanup_if_needed(0)
