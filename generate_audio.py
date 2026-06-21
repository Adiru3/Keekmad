#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import subprocess

def ensure_gtts():
    try:
        from gtts import gTTS
        return gTTS
    except ImportError:
        print("gTTS is not installed. Installing it via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gtts"])
            from gtts import gTTS
            print("gTTS successfully installed!")
            return gTTS
        except Exception as e:
            print(f"Error: Failed to install gtts library automatically. Please run 'pip install gtts' manually. Details: {e}")
            sys.exit(1)

def main():
    gTTS = ensure_gtts()

    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, 'index.html')
    audio_dir = os.path.join(script_dir, 'audio')

    if not os.path.exists(html_path):
        print(f"Error: index.html not found at {html_path}")
        print("Please place generate_audio.py in the same folder as index.html.")
        sys.exit(1)

    # Create audio directory if it doesn't exist
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
        print(f"Created audio directory at {audio_dir}")

    # Read index.html
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find STUDY_MATERIALS block
    start_match = re.search(r'const\s+STUDY_MATERIALS\s*=\s*\[', content)
    if not start_match:
        print("Error: STUDY_MATERIALS block not found in index.html")
        sys.exit(1)

    start_idx = start_match.end() - 1
    brackets = 0
    end_idx = -1
    for i in range(start_idx, len(content)):
        if content[i] == '[':
            brackets += 1
        elif content[i] == ']':
            brackets -= 1
            if brackets == 0:
                end_idx = i + 1
                break

    if end_idx == -1:
        print("Error: Could not find closing bracket for STUDY_MATERIALS")
        sys.exit(1)

    js_block = content[start_idx:end_idx]

    themes = []
    current_theme = None
    current_topic = None
    in_bullets = False

    for line in js_block.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # Check themeNum
        theme_num_match = re.search(r'themeNum:\s*(\d+)', line)
        if theme_num_match:
            current_theme = {
                'themeNum': int(theme_num_match.group(1)),
                'topics': []
            }
            themes.append(current_theme)
            continue
            
        # Check num (topic number)
        topic_num_match = re.search(r'num:\s*([\d\.]+)', line)
        if topic_num_match:
            current_topic = {
                'num': topic_num_match.group(1),
                'bullets': []
            }
            if current_theme:
                current_theme['topics'].append(current_topic)
            continue
            
        # Check bullets start
        if 'bullets: [' in line:
            in_bullets = True
            continue
            
        # Check bullets end
        if in_bullets and ']' in line:
            in_bullets = False
            continue
            
        # If in bullets, extract bullet text
        if in_bullets:
            bullet_match = re.search(r'^["\'](.*)["\'],?$', line)
            if not bullet_match:
                bullet_match = re.search(r'["\'](.*)["\']', line)
            if bullet_match:
                bullet_text = bullet_match.group(1)
                # Unescape quotes
                bullet_text = bullet_text.replace('\\"', '"').replace("\\'", "'").replace('\\`', '`')
                if current_topic:
                    current_topic['bullets'].append(bullet_text)

    # Perform downloads
    total_files = 0
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0

    # Count total
    for theme in themes:
        for topic in theme['topics']:
            total_files += len(topic['bullets'])

    print(f"Parsed {len(themes)} themes. Found {total_files} facts to check/generate.")
    print("Starting processing. Press Ctrl+C to abort...")

    for theme in themes:
        theme_num = theme['themeNum']
        for topic in theme['topics']:
            topic_num = topic['num']
            for bullet_idx, bullet_html in enumerate(topic['bullets']):
                # Clean HTML tags and remove extra spaces
                clean_text = re.sub(r'<[^>]*>', '', bullet_html).strip()
                
                # Check for empty text
                if not clean_text:
                    continue
                
                # Form filepath
                filename = f"bullet_{theme_num}_{topic_num}_{bullet_idx}.mp3"
                filepath = os.path.join(audio_dir, filename)

                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    skipped_count += 1
                else:
                    try:
                        print(f"[{downloaded_count+skipped_count+failed_count+1}/{total_files}] Downloading: {filename} -> '{clean_text[:40]}...'")
                        tts = gTTS(text=clean_text, lang='uk')
                        tts.save(filepath)
                        downloaded_count += 1
                        time.sleep(0.35)  # Be gentle to Google TTS service
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")
                        failed_count += 1
                        time.sleep(1.0)  # Sleep longer on error

    print("\n" + "="*40)
    print(" PROCESSING COMPLETE")
    print("="*40)
    print(f"Total facts checked: {total_files}")
    print(f"Successfully downloaded: {downloaded_count}")
    print(f"Skipped (already exists): {skipped_count}")
    if failed_count > 0:
        print(f"Failed to download: {failed_count}")
    print(f"Audio files directory: {audio_dir}")
    print("="*40)
    print("Done! You can now open index.html locally or deploy to GitHub Pages.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess aborted by user.")
