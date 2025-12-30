#!/usr/bin/env python3
"""
Repair corrupted JSON files using multiple strategies.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

RESEARCH_DIR = Path(__file__).parent / "research"

# Files with known JSON issues
CORRUPTED_FILES = [
    "belmont_university.json",
    "bowling_green_state_university.json", 
    "georgia_state_university.json",
    "mercer_university.json",
    "morgan_state_university.json",
    "pace_university.json",
    "samford_university.json",
    "suny_binghamton_university.json",
    "tennessee_tech_university.json",
    "university_of_akron.json",
    "university_of_maine.json",
    "university_of_mississippi.json",
    "university_of_montana.json",
    "university_of_north_dakota.json",
    "university_of_wyoming.json",
    "wayne_state_university.json",
    "west_virginia_university.json",
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def repair_json(content: str) -> str:
    """Apply multiple repair strategies to fix JSON."""
    
    # 1. Fix invalid escape sequences (like \N, \S, etc.)
    # Replace invalid escapes with their literal characters
    def fix_escape(match):
        char = match.group(1)
        if char in 'bfnrtu"\\/':
            return match.group(0)  # Valid escape, keep it
        return char  # Invalid escape, just keep the character
    
    content = re.sub(r'\\([^bfnrtu"\\/])', fix_escape, content)
    
    # 2. Remove control characters (except valid ones)
    # Keep: \n \r \t, remove others
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    
    # 3. Fix trailing commas
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    # 4. Fix missing commas between properties (common pattern)
    # Look for: "value"  "nextkey": - missing comma
    content = re.sub(r'"\s*\n\s*"([^"]+)":', r'",\n"\1":', content)
    
    # 5. Fix missing colons (rarer)
    # This is risky so we skip it
    
    return content

def process_file(filepath: Path) -> tuple[bool, str]:
    """Process a single file and attempt repair."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Read error: {e}"
    
    # Try parsing first
    try:
        json.loads(content)
        return True, "Already valid JSON"
    except json.JSONDecodeError:
        pass
    
    # Apply repairs
    repaired = repair_json(content)
    
    try:
        data = json.loads(repaired)
        # Write back formatted
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        return True, "Repaired successfully"
    except json.JSONDecodeError as e:
        return False, f"Could not repair: {e}"

def main():
    log(f"Attempting to repair {len(CORRUPTED_FILES)} corrupted JSON files...")
    
    repaired = 0
    failed = 0
    
    for fname in CORRUPTED_FILES:
        filepath = RESEARCH_DIR / fname
        if not filepath.exists():
            log(f"⚠️ {fname}: File not found")
            continue
        
        success, msg = process_file(filepath)
        if success and "Repaired" in msg:
            log(f"✅ {fname}: {msg}")
            repaired += 1
        elif success:
            log(f"ℹ️ {fname}: {msg}")
        else:
            log(f"❌ {fname}: {msg}")
            failed += 1
    
    log(f"\n📊 Summary: Repaired {repaired}, Failed {failed}")

if __name__ == "__main__":
    main()
