#!/usr/bin/env python3
"""
Album Verification Tool
Verify YouTube and Bandcamp links for albums in the database

Usage:
  python verify_albums.py --date 2025-10-07
  python verify_albums.py --start 2025-10-01 --end 2025-10-07
  python verify_albums.py --all
  python verify_albums.py --force --date 2025-10-07  # Re-verify already verified albums
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from db_manager import AlbumsDatabase
from batch_verifier import BatchVerifier

def parse_args():
    parser = argparse.ArgumentParser(
        description='Verify playable URLs for albums',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify albums from a specific date
  python verify_albums.py --date 2025-10-07
  
  # Verify albums from a date range
  python verify_albums.py --start 2025-10-01 --end 2025-10-07
  
  # Verify all unverified albums
  python verify_albums.py --all
  
  # Force re-verification of already verified albums
  python verify_albums.py --force --date 2025-10-07
  
  # Adjust similarity threshold (default: 75)
  python verify_albums.py --date 2025-10-07 --threshold 60
        """
    )
    
    # Date options (mutually exclusive)
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--date', type=str, help='Verify albums from specific date (YYYY-MM-DD)')
    date_group.add_argument('--start', type=str, help='Start date for range (use with --end)')
    date_group.add_argument('--all', action='store_true', help='Verify all unverified albums')
    
    parser.add_argument('--end', type=str, help='End date for range (use with --start)')
    parser.add_argument('--force', action='store_true', help='Re-verify already verified albums')
    parser.add_argument('--threshold', type=int, default=75, help='Minimum similarity score (0-100, default: 75)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between albums in seconds (default: 2.0)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Validate arguments
    if args.start and not args.end:
        print("❌ Error: --start requires --end")
        sys.exit(1)
    
    if args.end and not args.start:
        print("❌ Error: --end requires --start")
        sys.exit(1)
    
    if args.threshold < 0 or args.threshold > 100:
        print("❌ Error: --threshold must be between 0 and 100")
        sys.exit(1)
    
    print("=" * 70)
    print("ALBUM VERIFICATION TOOL")
    print("=" * 70)
    
    # Connect to database
    db = AlbumsDatabase()
    db.connect()
    db.create_tables()
    
    # Determine date range
    if args.date:
        start_date = args.date
        end_date = args.date
        print(f"\n📅 Mode: Single date ({args.date})")
    elif args.start:
        start_date = args.start
        end_date = args.end
        print(f"\n📅 Mode: Date range ({start_date} to {end_date})")
    else:  # --all
        cursor = db.connection.cursor()
        cursor.execute("SELECT MIN(release_date), MAX(release_date) FROM albums")
        start_date, end_date = cursor.fetchone()
        print(f"\n📅 Mode: All albums ({start_date} to {end_date})")
    
    # Get albums to verify
    cursor = db.connection.cursor()
    
    if args.force:
        print("🔄 Force mode: Will re-verify already verified albums")
        query = '''
            SELECT COUNT(*) FROM albums
            WHERE release_date BETWEEN ? AND ?
            AND (youtube_url IS NOT NULL OR bandcamp_url IS NOT NULL)
        '''
    else:
        query = '''
            SELECT COUNT(*) FROM albums
            WHERE release_date BETWEEN ? AND ?
            AND (youtube_url IS NOT NULL OR bandcamp_url IS NOT NULL)
            AND (playable_verified = 0 OR playable_verified IS NULL)
        '''
    
    cursor.execute(query, (start_date, end_date))
    count = cursor.fetchone()[0]
    
    print(f"\n📊 Albums to verify: {count}")
    
    if count == 0:
        print("\n✓ No albums need verification!")
        db.close()
        return
    
    # Show statistics
    cursor.execute('''
        SELECT COUNT(*) FROM albums
        WHERE release_date BETWEEN ? AND ?
        AND youtube_url IS NOT NULL AND youtube_url != 'N/A'
    ''', (start_date, end_date))
    youtube_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM albums
        WHERE release_date BETWEEN ? AND ?
        AND bandcamp_url IS NOT NULL AND bandcamp_url != 'N/A'
    ''', (start_date, end_date))
    bandcamp_count = cursor.fetchone()[0]
    
    print(f"   - With YouTube links: {youtube_count}")
    print(f"   - With Bandcamp links: {bandcamp_count}")
    
    # Estimate time
    estimated_minutes = (count * args.delay) / 60
    print(f"\n⏱️  Estimated time: {estimated_minutes:.1f} minutes")
    print(f"   Settings:")
    print(f"   - Similarity threshold: {args.threshold}%")
    print(f"   - Delay between albums: {args.delay}s")
    print(f"   - Headless mode: {args.headless}")
    
    # Confirm
    print("\n" + "-" * 70)
    response = input("Continue with verification? (y/n): ")
    if response.lower() != 'y':
        print("❌ Verification cancelled")
        db.close()
        return
    
    print("\n🚀 Starting verification...")
    print("-" * 70)
    
    # Run verification
    verifier = BatchVerifier(db, headless=args.headless)
    
    try:
        await verifier.initialize()
        
        # If force mode, temporarily clear verification status
        if args.force:
            cursor.execute('''
                UPDATE albums
                SET playable_verified = 0,
                    youtube_embed_url = NULL,
                    bandcamp_embed_url = NULL
                WHERE release_date BETWEEN ? AND ?
            ''', (start_date, end_date))
            db.connection.commit()
            print("🔄 Cleared previous verification data\n")
        
        stats = await verifier.verify_date_range(
            start_date,
            end_date,
            min_similarity=args.threshold
        )
        
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
        print(f"  Total albums processed: {stats['total']}")
        print(f"  ✓ Successfully verified: {stats['verified']}")
        print(f"    - YouTube: {stats['youtube_count']}")
        print(f"    - Bandcamp: {stats['bandcamp_count']}")
        print(f"  ✗ Failed: {stats['failed']}")
        
        if stats.get('errors', 0) > 0:
            print(f"  ⚠️  Connection errors: {stats['errors']}")
        
        if stats['verified'] > 0:
            success_rate = (stats['verified'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  📊 Success rate: {success_rate:.1f}%")
        
        print("=" * 70)
        
        if stats['verified'] > 0:
            print("\n✓ Albums are now ready for playlists!")
            print(f"\n📝 Next steps:")
            print(f"   1. Start the web server: python start_dev.py")
            print(f"   2. Test playlist API:")
            print(f"      curl 'http://localhost:8000/api/playlist/dynamic?period_type=day&period_key={end_date}'")
            print(f"   3. Or use the frontend Play button on the date view")
        else:
            print("\n⚠️  No albums were successfully verified")
            print("   Possible reasons:")
            print("   - YouTube/Bandcamp links don't contain the actual album")
            print("   - Album names don't match closely enough")
            print("   - Try lowering --threshold (e.g., --threshold 60)")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        print("   Partial results have been saved to database")
    except Exception as e:
        print(f"\n\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await verifier.close()
        db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
