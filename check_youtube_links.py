#!/usr/bin/env python3
"""Check YouTube embed URLs from the database"""
import sqlite3

db_path = 'data/albums.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get verified YouTube URLs from Oct 23, 2025
cursor.execute("""
    SELECT 
        album_name, 
        band_name, 
        youtube_embed_url,
        youtube_verified_title,
        youtube_verification_score,
        youtube_embed_type
    FROM albums 
    WHERE release_date = '2025-10-23' 
    AND youtube_embed_url IS NOT NULL
    ORDER BY youtube_verification_score DESC
""")

results = cursor.fetchall()

print("\n" + "="*80)
print("VERIFIED YOUTUBE LINKS FOR 2025-10-23")
print("="*80 + "\n")

if not results:
    print("❌ No verified YouTube links found for this date")
else:
    for i, row in enumerate(results, 1):
        album_name, band_name, embed_url, verified_title, score, embed_type = row
        print(f"{i}. {band_name} - {album_name}")
        print(f"   Verified Title: {verified_title}")
        print(f"   Match Score: {score}%")
        print(f"   Type: {embed_type}")
        print(f"   Embed URL: {embed_url}")
        print(f"   Test in browser: {embed_url.replace('/embed/', '/watch?v=').replace('videoseries?list=', 'playlist?list=')}")
        print()

print(f"Total verified: {len(results)}")
print("="*80 + "\n")

conn.close()
