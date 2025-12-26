#!/usr/bin/env python3
"""Ingest only specific university files."""
import json
import requests
import sys
import os
from pathlib import Path

CLOUD_FUNCTION_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

def ingest_file(filepath: str) -> bool:
    """Ingest a single university profile."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            print(f"✅ {Path(filepath).stem}")
            return True
        else:
            print(f"❌ {Path(filepath).stem}: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ {Path(filepath).stem}: {e}")
        return False

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("Usage: python ingest_specific.py file1.json file2.json ...")
        sys.exit(1)
    
    success = 0
    for f in files:
        if ingest_file(f):
            success += 1
    
    print(f"\nIngested: {success}/{len(files)}")
