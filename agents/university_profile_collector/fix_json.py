#!/usr/bin/env python3
"""Fix malformed JSON in cornell_university.json"""
import json
import re

path = '/Users/cvsubramanian/CascadeProjects/graphrag/agents/college_counselor/agents/university_profile_collector/research/cornell_university.json'

with open(path, 'r') as f:
    content = f.read()

print(f"Original size: {len(content)} bytes")

# The issue is: \\\" (escaped backslash + quote) should be just \" (escaped quote)
# This happens when LLM double-escapes quotes
# Pattern: backslash-backslash-quote should become just backslash-quote

# Fix order matters!
# First fix \\\" to just \" (escaped quote)
content = content.replace('\\\\"', '"')  # This replaces \\" with "

# Then fix escaped newlines  
content = content.replace('\\\\n', '\\n')
content = content.replace('\\\\t', '\\t')

# Try to parse
try:
    data = json.loads(content)
    print("✅ JSON is now valid!")
    
    # Save fixed version
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Verify
    with open(path) as f:
        verify = json.load(f)
    
    print(f"✅ Saved and verified JSON")
    
    # Print summary
    print(f"\n=== PROFILE SUMMARY ===")
    print(f"University: {verify.get('_id')}")
    colleges = verify.get('academic_structure', {}).get('colleges', [])
    total_majors = sum(len(c.get('majors', [])) for c in colleges)
    print(f"Colleges: {len(colleges)}, Total majors: {total_majors}")
    print(f"Scholarships: {len(verify.get('financials', {}).get('scholarships', []))}")
    print(f"File size: {len(json.dumps(verify))} chars")
    
except json.JSONDecodeError as e:
    print(f"❌ Still broken at line {e.lineno}, col {e.colno}: {e.msg}")
    lines = content.split('\n')
    if 0 < e.lineno <= len(lines):
        line = lines[e.lineno - 1]
        start = max(0, e.colno - 80)
        end = min(len(line), e.colno + 20)
        print(f"Context: ...{line[start:end]}...")
