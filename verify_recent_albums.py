#!/usr/bin/env python3
"""
Quick verification script for recent albums
Verifies albums from the last 7 days
"""

import asyncio
import sys
from datetime import datetime, timedelta
from db_manager import AlbumsDatabase
from batch_verifier import BatchVerifier

async def main():
    print("=" * 70)
    print("QUICK ALBUM VERIFICATION")
    print("=" * 70)
    
    # Connect to database
    db = AlbumsDatabase()
    db.connect()
    db.create_tables()
    
    # Get date range (last 7 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    print(f"\n📅 Verifying albums from {start_date} to {end_date}")
    print(f"   This will check YouTube and Bandcamp links...")
    print(f"   Estimated time: ~2-3 seconds per album")
    
    # Get albums to verify
    cursor = db.connection.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM albums
        WHERE release_date BETWEEN ? AND ?
        AND (youtube_url IS NOT NULL OR bandcamp_url IS NOT NULL)
        AND (playable_verified = 0 OR playable_verified IS NULL)
    ''', (str(start_date), str(end_date)))
    
    count = cursor.fetchone()[0]
    print(f"\n📊 Found {count} albums to verify")
    
    if count == 0:
        print("\n✓ No albums need verification!")
        db.close()
        return
    
    print(f"\n⏱️  This will take approximately {count * 2.5 / 60:.1f} minutes")
    print("\nStarting verification...")
    print("-" * 70)
    
    # Run verification
    verifier = BatchVerifier(db, headless=True)
    
    try:
        await verifier.initialize()
        stats = await verifier.verify_date_range(
            str(start_date),
            str(end_date),
            min_similarity=75
        )
        
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
        print(f"  Total albums processed: {stats['total']}")
        print(f"  ✓ Successfully verified: {stats['verified']}")
        print(f"    - YouTube: {stats['youtube_count']}")
        print(f"    - Bandcamp: {stats['bandcamp_count']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print("=" * 70)
        
        if stats['verified'] > 0:
            print("\n✓ You can now create playlists for these dates!")
            print(f"   Try: http://localhost:8000/api/playlist/dynamic?period_type=day&period_key={end_date}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await verifier.close()
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
