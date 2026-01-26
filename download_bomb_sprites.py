"""
Download script for bomb sprites from WikiTide
Run this script to download all bomb sprites to the correct directory.
"""
import urllib.request
import os
from pathlib import Path

# URLs der Bomb-Sprites
SPRITE_URLS = {
    'gem_bomb.png': 'https://static.wikitide.net/shminerwiki/0/05/Gem_Bomb.png',
    'cherry_bomb.png': 'https://static.wikitide.net/shminerwiki/1/1b/Cherry_Bomb.png',
    'battery_bomb.png': 'https://static.wikitide.net/shminerwiki/5/5d/Battery_Bomb.png',
    'd20_bomb.png': 'https://static.wikitide.net/shminerwiki/e/eb/D20_Bomb.png',
    'founders_bomb.png': 'https://static.wikitide.net/shminerwiki/5/5f/Founders_Bomb.png',
}

# Zielverzeichnis
TARGET_DIR = Path(__file__).parent / 'ObeliskGemEV' / 'sprites' / 'common'
TARGET_DIR.mkdir(parents=True, exist_ok=True)

def download_sprites():
    """Download all bomb sprites"""
    print("Downloading bomb sprites...")
    print(f"Target directory: {TARGET_DIR}")
    print()
    
    for filename, url in SPRITE_URLS.items():
        target_path = TARGET_DIR / filename
        try:
            print(f"Downloading {filename}...", end=' ')
            urllib.request.urlretrieve(url, target_path)
            print(f"✓ Success")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    print()
    print("Download complete!")

if __name__ == '__main__':
    download_sprites()
