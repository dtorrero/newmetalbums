#!/usr/bin/env python3
"""
Clean old YouTube cache files.
Usage: python clean_youtube_cache.py [--days N]
"""

import os
import time
from pathlib import Path
import argparse

def clean_cache(days_old=30):
    """Remove cache files older than specified days"""
    cache_dir = Path("youtube_cache")
    
    if not cache_dir.exists():
        print("Cache directory doesn't exist")
        return
    
    # First, clean up all partial downloads (regardless of age)
    partial_count = 0
    partial_size = 0
    for pattern in ["*.part", "*.ytdl"]:
        for file_path in cache_dir.glob(pattern):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                file_path.unlink()
                partial_count += 1
                partial_size += file_size
                print(f"Removed partial: {file_path.name} ({file_size / 1024 / 1024:.2f} MB)")
    
    if partial_count > 0:
        print(f"Cleaned up {partial_count} partial downloads ({partial_size / 1024 / 1024:.2f} MB)\n")
    
    # Now clean old complete files
    now = time.time()
    cutoff = now - (days_old * 86400)  # Convert days to seconds
    
    removed_count = 0
    removed_size = 0
    
    for file_path in cache_dir.glob("*"):
        if file_path.is_file() and not file_path.name.endswith(('.part', '.ytdl')):
            file_age = file_path.stat().st_mtime
            if file_age < cutoff:
                file_size = file_path.stat().st_size
                file_path.unlink()
                removed_count += 1
                removed_size += file_size
                print(f"Removed old: {file_path.name} ({file_size / 1024 / 1024:.2f} MB)")
    
    print(f"\nTotal: Removed {removed_count} old files ({removed_size / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean old YouTube cache files")
    parser.add_argument("--days", type=int, default=30, help="Remove files older than N days (default: 30)")
    args = parser.parse_args()
    
    clean_cache(args.days)
